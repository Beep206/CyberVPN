#![forbid(unsafe_code)]

use ns_auth::{MintedTokenRequest, SessionTokenSigner};
use ns_core::{DeviceBindingId, ManifestId, ValidationError};
use ns_manifest::{
    CarrierProfile as ManifestCarrierProfile, ClientConstraints, DevicePolicy, GatewayEndpoint,
    ManifestDocument, ManifestSignature, ManifestSigner, ManifestUser, RefreshPolicy, RetryPolicy,
    RoutingPolicy, TelemetryPolicy, TokenService,
};
use ns_remnawave_adapter::{
    AccountLifecycle, AccountSnapshot, AdapterWebhookEffect, BootstrapSubject, NorthstarAccess,
    RemnawaveAdapter, VerifiedWebhookPayload, WebhookAuthenticator, WebhookVerificationConfig,
    WebhookVerificationError, WebhookVerificationInput, verify_webhook_input,
};
use ns_storage::{
    BootstrapGrantConsumeOutcome, BootstrapGrantRecord, BridgeStore,
    DeviceRegistrationStoreOutcome, DeviceRegistrationStoreRequest, RefreshCredentialRecord,
    StorageError, StoredDeviceRecord, StoredDeviceStatus,
};
use serde::{Deserialize, Serialize};
use serde_json::Value;
use sha2::{Digest, Sha256};
use std::fmt::Write as _;
use thiserror::Error;
use time::{Duration, OffsetDateTime};
use uuid::Uuid;
use zeroize::Zeroizing;

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub enum DeviceStatus {
    Active,
    Revoked,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct DeviceRecord {
    pub device_id: String,
    pub account_id: String,
    pub status: DeviceStatus,
    pub platform: String,
    pub client_version: String,
    pub install_channel: Option<String>,
    pub device_name: Option<String>,
    pub first_seen_at_unix: i64,
    pub last_seen_at_unix: i64,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct BridgeManifestContext {
    pub device_policy: Option<DevicePolicy>,
    pub client_constraints: ClientConstraints,
    pub token_service: TokenService,
    pub refresh: Option<RefreshPolicy>,
    pub routing: RoutingPolicy,
    pub retry_policy: RetryPolicy,
    pub telemetry: TelemetryPolicy,
}

pub type BridgeCarrierProfile = ManifestCarrierProfile;
pub type BridgeGatewayEndpoint = GatewayEndpoint;

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct ManifestCompileInput {
    pub account: AccountSnapshot,
    pub device: Option<DeviceRecord>,
    pub context: BridgeManifestContext,
    pub carrier_profiles: Vec<BridgeCarrierProfile>,
    pub endpoints: Vec<BridgeGatewayEndpoint>,
    pub manifest_ttl: Duration,
}

#[derive(Debug, Clone, PartialEq)]
pub struct BridgeManifestTemplate {
    pub context: BridgeManifestContext,
    pub carrier_profiles: Vec<BridgeCarrierProfile>,
    pub endpoints: Vec<BridgeGatewayEndpoint>,
    pub manifest_ttl: Duration,
    pub bootstrap_grant_ttl: Duration,
}

impl BridgeManifestTemplate {
    pub fn compile_input(
        &self,
        account: AccountSnapshot,
        device: Option<DeviceRecord>,
    ) -> ManifestCompileInput {
        ManifestCompileInput {
            account,
            device,
            context: self.context.clone(),
            carrier_profiles: self.carrier_profiles.clone(),
            endpoints: self.endpoints.clone(),
            manifest_ttl: self.manifest_ttl,
        }
    }
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct DeviceRegistrationRequest {
    pub manifest_id: ManifestId,
    pub device_id: DeviceBindingId,
    pub device_name: Option<String>,
    pub platform: String,
    pub client_version: String,
    pub install_channel: Option<String>,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct DeviceRegistrationResult {
    pub device: DeviceRecord,
    pub refresh_credential: String,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct TokenExchangeInput {
    pub manifest_id: ManifestId,
    pub device_id: DeviceBindingId,
    pub client_version: String,
    pub core_version: u64,
    pub carrier_profile_id: String,
    pub requested_capabilities: Vec<u64>,
    pub refresh_credential: String,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct TokenExchangeResult {
    pub session_token: String,
    pub expires_at: OffsetDateTime,
    pub policy_epoch: u64,
}

#[derive(Debug, Clone, PartialEq)]
pub enum DeviceRegistrationAuthContext {
    Bootstrap {
        snapshot: AccountSnapshot,
        manifest_id: ManifestId,
    },
    Refresh {
        snapshot: AccountSnapshot,
        manifest_id: ManifestId,
        device_id: DeviceBindingId,
    },
}

pub struct BridgeDomain<A, S> {
    adapter: A,
    store: S,
    manifest_signer: ManifestSigner,
    token_signer: SessionTokenSigner,
    session_token_ttl: Duration,
}

impl<A, S> BridgeDomain<A, S>
where
    A: RemnawaveAdapter,
    S: BridgeStore,
{
    pub fn new(
        adapter: A,
        store: S,
        manifest_signer: ManifestSigner,
        token_signer: SessionTokenSigner,
        session_token_ttl: Duration,
    ) -> Self {
        Self {
            adapter,
            store,
            manifest_signer,
            token_signer,
            session_token_ttl,
        }
    }

    pub async fn resolve_bootstrap(
        &self,
        subject: &BootstrapSubject,
    ) -> Result<AccountSnapshot, BridgeDomainError> {
        let snapshot = self.adapter.resolve_bootstrap_subject(subject).await?;
        Self::authorize_snapshot(&snapshot)?;
        Ok(snapshot)
    }

    pub fn authorize_snapshot(snapshot: &AccountSnapshot) -> Result<(), BridgeDomainError> {
        if !snapshot.northstar_access.northstar_enabled {
            return Err(BridgeDomainError::NorthstarDisabled);
        }

        match snapshot.lifecycle {
            AccountLifecycle::Active => Ok(()),
            AccountLifecycle::Disabled => Err(BridgeDomainError::AccountDisabled),
            AccountLifecycle::Revoked => Err(BridgeDomainError::AccountRevoked),
            AccountLifecycle::Expired => Err(BridgeDomainError::AccountExpired),
            AccountLifecycle::Limited => Err(BridgeDomainError::AccountLimited),
        }
    }

    pub fn compile_manifest(
        &self,
        input: ManifestCompileInput,
        now: OffsetDateTime,
    ) -> Result<ManifestDocument, BridgeDomainError> {
        Self::authorize_snapshot(&input.account)?;

        let account = &input.account;
        let access = &account.northstar_access;
        let expires_at = now + input.manifest_ttl;
        let manifest_id = format!("man-{}-{}", now.unix_timestamp(), access.policy_epoch);

        let manifest = ManifestDocument {
            schema_version: 1,
            manifest_id,
            generated_at: now,
            expires_at,
            user: manifest_user(account),
            device_policy: input.context.device_policy,
            client_constraints: input.context.client_constraints,
            token_service: input.context.token_service,
            refresh: input.context.refresh,
            carrier_profiles: input.carrier_profiles,
            endpoints: input.endpoints,
            routing: input.context.routing,
            retry_policy: input.context.retry_policy,
            telemetry: input.context.telemetry,
            signature: ManifestSignature {
                alg: "EdDSA".to_owned(),
                key_id: self.manifest_signer.key_id().to_owned(),
                value: String::new(),
            },
        };
        let mut manifest = manifest;
        self.manifest_signer.sign(&mut manifest)?;
        manifest.validate(now)?;

        Ok(manifest)
    }

    pub async fn compile_manifest_for_bootstrap(
        &self,
        subject: &BootstrapSubject,
        template: &BridgeManifestTemplate,
        now: OffsetDateTime,
    ) -> Result<ManifestDocument, BridgeDomainError> {
        let snapshot = self.resolve_bootstrap(subject).await?;
        let credential = Zeroizing::new(format!("btg_{}", Uuid::new_v4().simple()));
        let mut input = template.compile_input(snapshot.clone(), None);
        input.context.refresh = Some(RefreshPolicy {
            mode: ns_manifest::RefreshMode::BootstrapOnly,
            credential: credential.to_string(),
            rotation_hint_seconds: Some(
                u64::try_from(template.bootstrap_grant_ttl.whole_seconds().max(60))
                    .map_err(|_| BridgeDomainError::InvalidBootstrapGrantTtl)?,
            ),
        });
        let manifest = self.compile_manifest(input, now)?;
        self.store
            .store_bootstrap_grant(
                &credential,
                BootstrapGrantRecord {
                    account_id: snapshot.account_id,
                    manifest_id: ManifestId::new(manifest.manifest_id.clone())?,
                    expires_at_unix: (now + template.bootstrap_grant_ttl).unix_timestamp(),
                },
            )
            .await?;
        Ok(manifest)
    }

    pub async fn compile_manifest_for_refresh(
        &self,
        refresh_credential: &str,
        template: &BridgeManifestTemplate,
        now: OffsetDateTime,
    ) -> Result<ManifestDocument, BridgeDomainError> {
        let (snapshot, record) = self
            .resolve_refresh_snapshot(refresh_credential, true)
            .await?;
        let mut input = template.compile_input(snapshot, None);
        if let Some(refresh) = &mut input.context.refresh {
            if refresh.mode != ns_manifest::RefreshMode::BootstrapOnly {
                refresh.credential = refresh_credential.to_owned();
            }
        }
        let manifest = self.compile_manifest(input, now)?;
        self.store
            .store_refresh_credential(
                refresh_credential,
                RefreshCredentialRecord {
                    manifest_id: ManifestId::new(manifest.manifest_id.clone())?,
                    ..record
                },
            )
            .await?;
        Ok(manifest)
    }

    pub async fn register_device(
        &self,
        snapshot: &AccountSnapshot,
        request: DeviceRegistrationRequest,
        now: OffsetDateTime,
    ) -> Result<DeviceRegistrationResult, BridgeDomainError> {
        Self::authorize_snapshot(snapshot)?;
        validate_platform(&request.platform)?;
        validate_client_version(&request.client_version)?;

        let credential = Zeroizing::new(format!("rfr_{}", Uuid::new_v4().simple()));
        let outcome = self
            .store
            .register_device_with_refresh(DeviceRegistrationStoreRequest {
                device: StoredDeviceRecord {
                    account_id: snapshot.account_id.clone(),
                    device_id: request.device_id.clone(),
                    status: StoredDeviceStatus::Active,
                },
                refresh_credential: credential.to_string(),
                refresh_record: ns_storage::RefreshCredentialRecord {
                    account_id: snapshot.account_id.clone(),
                    device_id: request.device_id.clone(),
                    manifest_id: request.manifest_id.clone(),
                    revoked: false,
                },
                max_devices: snapshot.northstar_access.device_limit,
            })
            .await?;
        match outcome {
            DeviceRegistrationStoreOutcome::Stored => {}
            DeviceRegistrationStoreOutcome::DeviceRevoked => {
                return Err(BridgeDomainError::DeviceRevoked);
            }
            DeviceRegistrationStoreOutcome::DeviceLimitReached { max_devices } => {
                return Err(BridgeDomainError::DeviceLimitReached { max_devices });
            }
        }

        let device = DeviceRecord {
            device_id: request.device_id.as_str().to_owned(),
            account_id: snapshot.account_id.clone(),
            status: DeviceStatus::Active,
            platform: request.platform,
            client_version: request.client_version,
            install_channel: request.install_channel,
            device_name: request.device_name,
            first_seen_at_unix: now.unix_timestamp(),
            last_seen_at_unix: now.unix_timestamp(),
        };

        Ok(DeviceRegistrationResult {
            device,
            refresh_credential: credential.to_string(),
        })
    }

    pub async fn resolve_device_registration_auth(
        &self,
        credential: &str,
        now: OffsetDateTime,
    ) -> Result<DeviceRegistrationAuthContext, BridgeDomainError> {
        match self
            .store
            .consume_bootstrap_grant(credential, now.unix_timestamp())
            .await
        {
            Ok(BootstrapGrantConsumeOutcome::Consumed(record)) => {
                let snapshot = self
                    .adapter
                    .fetch_account_snapshot(&record.account_id)
                    .await?;
                Self::authorize_snapshot(&snapshot)?;
                return Ok(DeviceRegistrationAuthContext::Bootstrap {
                    snapshot,
                    manifest_id: record.manifest_id,
                });
            }
            Ok(BootstrapGrantConsumeOutcome::Expired(_)) => {
                return Err(BridgeDomainError::BootstrapCredentialExpired);
            }
            Err(StorageError::BootstrapGrantNotFound) => {}
            Err(error) => return Err(BridgeDomainError::Storage(error)),
        }

        let (snapshot, record) = self.resolve_refresh_snapshot(credential, false).await?;
        Ok(DeviceRegistrationAuthContext::Refresh {
            snapshot,
            manifest_id: record.manifest_id,
            device_id: record.device_id,
        })
    }

    pub async fn register_device_with_auth(
        &self,
        auth: DeviceRegistrationAuthContext,
        request: DeviceRegistrationRequest,
        now: OffsetDateTime,
    ) -> Result<DeviceRegistrationResult, BridgeDomainError> {
        match &auth {
            DeviceRegistrationAuthContext::Bootstrap {
                snapshot,
                manifest_id,
            } => {
                if manifest_id.as_str() != request.manifest_id.as_str() {
                    return Err(BridgeDomainError::BootstrapCredentialManifestMismatch);
                }
                self.register_device(snapshot, request, now).await
            }
            DeviceRegistrationAuthContext::Refresh {
                snapshot,
                manifest_id,
                device_id,
            } => {
                if manifest_id.as_str() != request.manifest_id.as_str() {
                    return Err(BridgeDomainError::RefreshCredentialManifestMismatch);
                }
                if device_id.as_str() != request.device_id.as_str() {
                    return Err(BridgeDomainError::DeviceIdMismatch);
                }
                self.register_device(snapshot, request, now).await
            }
        }
    }

    pub async fn exchange_token(
        &self,
        snapshot: &AccountSnapshot,
        input: TokenExchangeInput,
        now: OffsetDateTime,
    ) -> Result<TokenExchangeResult, BridgeDomainError> {
        Self::authorize_snapshot(snapshot)?;
        ensure_access_allows(&snapshot.northstar_access, &input)?;

        let record = self
            .store
            .load_refresh_credential(&input.refresh_credential)
            .await?;
        if record.revoked {
            return Err(BridgeDomainError::RefreshCredentialRevoked);
        }
        if record.account_id != snapshot.account_id {
            return Err(BridgeDomainError::RefreshCredentialAccountMismatch);
        }
        if record.device_id.as_str() != input.device_id.as_str() {
            return Err(BridgeDomainError::DeviceIdMismatch);
        }
        if record.manifest_id.as_str() != input.manifest_id.as_str() {
            return Err(BridgeDomainError::RefreshCredentialManifestMismatch);
        }
        let device = self
            .store
            .load_device(&snapshot.account_id, &input.device_id)
            .await?;
        match device {
            Some(device) if device.status == StoredDeviceStatus::Revoked => {
                return Err(BridgeDomainError::DeviceRevoked);
            }
            Some(_) => {}
            None => return Err(BridgeDomainError::DeviceBindingRequired),
        }

        let minted = self.token_signer.mint(
            MintedTokenRequest {
                subject: snapshot.account_id.clone(),
                device_id: input.device_id.clone(),
                manifest_id: record.manifest_id.clone(),
                policy_epoch: snapshot.northstar_access.policy_epoch,
                core_versions: snapshot.northstar_access.allowed_core_versions.clone(),
                carrier_profiles: snapshot.northstar_access.allowed_carrier_profiles.clone(),
                capabilities: snapshot.northstar_access.allowed_capabilities.clone(),
                session_modes: vec!["tcp".to_owned(), "udp".to_owned()],
                region_scope: snapshot.northstar_access.preferred_regions.first().cloned(),
                token_max_relay_streams: Some(32),
                token_max_udp_flows: Some(8),
                token_max_udp_payload: Some(1200),
            },
            now,
            self.session_token_ttl,
        )?;

        Ok(TokenExchangeResult {
            session_token: minted.token,
            expires_at: minted.expires_at,
            policy_epoch: snapshot.northstar_access.policy_epoch,
        })
    }

    pub async fn exchange_token_for_refresh(
        &self,
        input: TokenExchangeInput,
        now: OffsetDateTime,
    ) -> Result<TokenExchangeResult, BridgeDomainError> {
        let (snapshot, _) = self
            .resolve_refresh_snapshot(&input.refresh_credential, true)
            .await?;
        self.exchange_token(&snapshot, input, now).await
    }

    pub fn webhook_reconcile_hint(effect: AdapterWebhookEffect) -> String {
        match effect {
            AdapterWebhookEffect::Noop => "noop".to_owned(),
            AdapterWebhookEffect::InvalidateAccount { account_id } => {
                format!("invalidate-account:{account_id}")
            }
            AdapterWebhookEffect::ReconcileAccount { account_id, reason } => {
                format!("reconcile-account:{account_id}:{reason}")
            }
            AdapterWebhookEffect::ReconcileAll { reason } => format!("reconcile-all:{reason}"),
            AdapterWebhookEffect::Snapshot(snapshot) => {
                format!("snapshot:{}", snapshot.account_id)
            }
        }
    }

    pub async fn ingest_verified_webhook(
        &self,
        input: WebhookVerificationInput<'_>,
        authenticator: &dyn WebhookAuthenticator,
        payload: VerifiedWebhookPayload,
        now: OffsetDateTime,
        config: WebhookVerificationConfig,
    ) -> Result<AdapterWebhookEffect, BridgeDomainError> {
        verify_webhook_input(input.clone(), authenticator, now, config)?;
        let fingerprint = webhook_fingerprint(
            input.timestamp_header,
            input.body,
            &payload.event_type,
            payload.account_id.as_deref(),
        );
        let is_new = self.store.remember_webhook(&fingerprint).await?;
        if !is_new {
            return Err(BridgeDomainError::DuplicateWebhookDelivery);
        }
        self.adapter
            .ingest_verified_webhook(payload)
            .await
            .map_err(BridgeDomainError::Adapter)
    }

    async fn resolve_refresh_snapshot(
        &self,
        refresh_credential: &str,
        enforce_device_state: bool,
    ) -> Result<(AccountSnapshot, RefreshCredentialRecord), BridgeDomainError> {
        let record = self
            .store
            .load_refresh_credential(refresh_credential)
            .await?;
        if record.revoked {
            return Err(BridgeDomainError::RefreshCredentialRevoked);
        }
        let snapshot = self
            .adapter
            .fetch_account_snapshot(&record.account_id)
            .await?;
        Self::authorize_snapshot(&snapshot)?;
        if enforce_device_state {
            match self
                .store
                .load_device(&snapshot.account_id, &record.device_id)
                .await?
            {
                Some(device) if device.status == StoredDeviceStatus::Revoked => {
                    return Err(BridgeDomainError::DeviceRevoked);
                }
                Some(_) => {}
                None => return Err(BridgeDomainError::DeviceBindingRequired),
            }
        }
        Ok((snapshot, record))
    }
}

fn ensure_access_allows(
    access: &NorthstarAccess,
    input: &TokenExchangeInput,
) -> Result<(), BridgeDomainError> {
    if !access.allowed_core_versions.contains(&input.core_version) {
        return Err(BridgeDomainError::CoreVersionNotAllowed(input.core_version));
    }
    if !access
        .allowed_carrier_profiles
        .iter()
        .any(|profile| profile == &input.carrier_profile_id)
    {
        return Err(BridgeDomainError::CarrierProfileNotAllowed(
            input.carrier_profile_id.clone(),
        ));
    }
    if input.requested_capabilities.iter().any(|requested| {
        !access
            .allowed_capabilities
            .iter()
            .any(|allowed| allowed == requested)
    }) {
        return Err(BridgeDomainError::CapabilityNotAllowed);
    }

    Ok(())
}

fn validate_platform(value: &str) -> Result<(), BridgeDomainError> {
    if value.trim().is_empty() {
        return Err(BridgeDomainError::Validation(ValidationError::Empty {
            field: "platform",
        }));
    }
    Ok(())
}

fn validate_client_version(value: &str) -> Result<(), BridgeDomainError> {
    if value.trim().is_empty() {
        return Err(BridgeDomainError::Validation(ValidationError::Empty {
            field: "client_version",
        }));
    }
    Ok(())
}

pub fn hash_refresh_credential(secret: &str) -> String {
    let digest = Sha256::digest(secret.as_bytes());
    let mut rendered = String::from("sha256:");
    for byte in digest {
        let _ = write!(&mut rendered, "{byte:02x}");
    }
    rendered
}

fn manifest_user(account: &AccountSnapshot) -> Option<ManifestUser> {
    let metadata = account.metadata.as_ref();
    let user = ManifestUser {
        account_id: Some(account.account_id.clone()),
        plan_id: metadata
            .and_then(|value| metadata_string(value, "plan_id"))
            .or_else(|| metadata.and_then(|value| metadata_string(value, "plan"))),
        display_name: metadata
            .and_then(|value| metadata_string(value, "display_name"))
            .or_else(|| metadata.and_then(|value| metadata_string(value, "name"))),
    };

    if user.account_id.is_some() || user.plan_id.is_some() || user.display_name.is_some() {
        Some(user)
    } else {
        None
    }
}

fn metadata_string(value: &Value, field: &str) -> Option<String> {
    value
        .as_object()
        .and_then(|object| object.get(field))
        .and_then(Value::as_str)
        .map(ToOwned::to_owned)
}

pub fn webhook_fingerprint(
    timestamp_header: &str,
    body: &[u8],
    event_type: &str,
    account_id: Option<&str>,
) -> String {
    let body_digest = Sha256::digest(body);
    let scope = account_id.unwrap_or("global");
    let mut rendered = format!("evt:{event_type}:ts:{timestamp_header}:scope:{scope}:sha256:");
    for byte in body_digest {
        let _ = write!(&mut rendered, "{byte:02x}");
    }
    rendered
}

#[derive(Debug, Error)]
pub enum BridgeDomainError {
    #[error("validation failed: {0}")]
    Validation(#[from] ValidationError),
    #[error("manifest compilation failed: {0}")]
    Manifest(#[from] ns_manifest::ManifestError),
    #[error("token minting failed: {0}")]
    Auth(#[from] ns_auth::AuthError),
    #[error("remnawave adapter failed: {0}")]
    Adapter(#[from] ns_remnawave_adapter::AdapterError),
    #[error("bridge storage failed: {0}")]
    Storage(#[from] StorageError),
    #[error("webhook verification failed: {0}")]
    WebhookVerification(#[from] WebhookVerificationError),
    #[error("northstar access is disabled for this account")]
    NorthstarDisabled,
    #[error("account is disabled")]
    AccountDisabled,
    #[error("account is revoked")]
    AccountRevoked,
    #[error("account is expired")]
    AccountExpired,
    #[error("account is limited")]
    AccountLimited,
    #[error("requested core version {0} is not allowed")]
    CoreVersionNotAllowed(u64),
    #[error("requested carrier profile {0} is not allowed")]
    CarrierProfileNotAllowed(String),
    #[error("requested capabilities exceed account policy")]
    CapabilityNotAllowed,
    #[error("refresh credential is revoked")]
    RefreshCredentialRevoked,
    #[error("refresh credential belongs to a different account")]
    RefreshCredentialAccountMismatch,
    #[error("refresh credential does not match the requested manifest")]
    RefreshCredentialManifestMismatch,
    #[error("refresh credential does not match the requesting device")]
    DeviceIdMismatch,
    #[error("device binding is required before token exchange")]
    DeviceBindingRequired,
    #[error("device is revoked")]
    DeviceRevoked,
    #[error("device limit {max_devices} reached")]
    DeviceLimitReached { max_devices: u32 },
    #[error("duplicate webhook delivery was rejected")]
    DuplicateWebhookDelivery,
    #[error("bootstrap credential has expired")]
    BootstrapCredentialExpired,
    #[error("bootstrap credential does not match the requested manifest")]
    BootstrapCredentialManifestMismatch,
    #[error("bootstrap grant ttl must be a positive duration")]
    InvalidBootstrapGrantTtl,
}

#[cfg(test)]
mod tests {
    use super::*;
    use ed25519_dalek::SigningKey;
    use ed25519_dalek::pkcs8::EncodePrivateKey;
    use ns_core::Capability;
    use ns_remnawave_adapter::{
        FakeAdapterCall, FakeRemnawaveAdapter, NorthstarAccess, WebhookVerificationError,
    };
    use ns_storage::{
        BridgeStore, InMemoryBridgeStore, RefreshCredentialRecord, StoredDeviceRecord,
        StoredDeviceStatus,
    };
    use serde::Deserialize;
    use std::fs;
    use std::path::PathBuf;

    struct AcceptAllWebhookAuthenticator;

    impl WebhookAuthenticator for AcceptAllWebhookAuthenticator {
        fn verify(
            &self,
            _timestamp_header: &str,
            signature_header: &str,
            _body: &[u8],
        ) -> Result<(), WebhookVerificationError> {
            match signature_header {
                "sig-ok" => Ok(()),
                _ => Err(WebhookVerificationError::InvalidSignature),
            }
        }
    }

    #[derive(Debug, Deserialize)]
    struct DuplicateWebhookFixture {
        body: String,
        payload: VerifiedWebhookPayload,
        signature_header: String,
        timestamp_header: String,
    }

    fn active_snapshot() -> AccountSnapshot {
        AccountSnapshot {
            account_id: "acct-1".to_owned(),
            bootstrap_subjects: vec![BootstrapSubject::ShortUuid("sub-1".to_owned())],
            lifecycle: AccountLifecycle::Active,
            northstar_access: NorthstarAccess {
                northstar_enabled: true,
                policy_epoch: 7,
                device_limit: Some(2),
                allowed_core_versions: vec![1],
                allowed_carrier_profiles: vec!["carrier-primary".to_owned()],
                allowed_capabilities: vec![Capability::TcpRelay.id(), Capability::UdpRelay.id()],
                rollout_cohort: Some("alpha".to_owned()),
                preferred_regions: vec!["eu-central".to_owned()],
            },
            metadata: None,
            observed_at_unix: 1_700_000_000,
            source_version: Some("2.7.4".to_owned()),
        }
    }

    fn bridge_with_store(
        store: InMemoryBridgeStore,
    ) -> BridgeDomain<FakeRemnawaveAdapter, InMemoryBridgeStore> {
        bridge_with_adapter(
            FakeRemnawaveAdapter::with_account(
                BootstrapSubject::ShortUuid("sub-1".to_owned()),
                active_snapshot(),
            ),
            store,
        )
    }

    fn bridge_with_adapter(
        adapter: FakeRemnawaveAdapter,
        store: InMemoryBridgeStore,
    ) -> BridgeDomain<FakeRemnawaveAdapter, InMemoryBridgeStore> {
        let token_signing_key = SigningKey::from_bytes(&[12_u8; 32]);
        let pem = token_signing_key
            .to_pkcs8_pem(Default::default())
            .expect("test signing key should encode");
        let signer = SessionTokenSigner::from_ed_pem(
            "bridge.example",
            "northstar-gateway",
            "kid-1",
            pem.as_bytes(),
        )
        .expect("test bridge signer should initialize");
        let manifest_signer =
            ManifestSigner::new("bridge-manifest-key", SigningKey::from_bytes(&[14_u8; 32]));

        BridgeDomain::new(
            adapter,
            store,
            manifest_signer,
            signer,
            Duration::seconds(300),
        )
    }

    fn bridge() -> BridgeDomain<FakeRemnawaveAdapter, InMemoryBridgeStore> {
        bridge_with_store(InMemoryBridgeStore::default())
    }

    fn load_duplicate_webhook_fixture() -> DuplicateWebhookFixture {
        let mut root = PathBuf::from(env!("CARGO_MANIFEST_DIR"));
        root.pop();
        root.pop();
        let fixture = fs::read_to_string(
            root.join("fixtures/remnawave/webhook/BG-WEBHOOK-DUPLICATE-006.json"),
        )
        .expect("duplicate-webhook fixture should be readable");

        serde_json::from_str(&fixture).expect("duplicate-webhook fixture should parse")
    }

    #[tokio::test]
    async fn registers_device_and_exchanges_token() {
        let domain = bridge();
        let snapshot = active_snapshot();
        let manifest_id =
            ManifestId::new("man-2026-04-01-001").expect("fixture manifest id should be valid");

        let registration = domain
            .register_device(
                &snapshot,
                DeviceRegistrationRequest {
                    manifest_id: manifest_id.clone(),
                    device_id: DeviceBindingId::new("device-1")
                        .expect("fixture device binding id should be valid"),
                    device_name: Some("Workstation".to_owned()),
                    platform: "windows".to_owned(),
                    client_version: "0.1.0".to_owned(),
                    install_channel: Some("stable".to_owned()),
                },
                OffsetDateTime::from_unix_timestamp(1_700_000_000)
                    .expect("fixture timestamp should be valid"),
            )
            .await
            .expect("device registration should succeed");

        let exchange = domain
            .exchange_token(
                &snapshot,
                TokenExchangeInput {
                    manifest_id,
                    device_id: DeviceBindingId::new("device-1")
                        .expect("fixture device binding id should be valid"),
                    client_version: "0.1.0".to_owned(),
                    core_version: 1,
                    carrier_profile_id: "carrier-primary".to_owned(),
                    requested_capabilities: vec![Capability::TcpRelay.id()],
                    refresh_credential: registration.refresh_credential,
                },
                OffsetDateTime::from_unix_timestamp(1_700_000_010)
                    .expect("fixture timestamp should be valid"),
            )
            .await
            .expect("token exchange should succeed");

        assert_eq!(exchange.policy_epoch, 7);
        assert!(exchange.session_token.starts_with("ey"));
    }

    #[test]
    fn hashes_refresh_credentials_without_echoing_the_secret() {
        let digest = hash_refresh_credential("rfr_secret_value");
        assert!(digest.starts_with("sha256:"));
        assert!(!digest.contains("rfr_secret_value"));
    }

    #[tokio::test]
    async fn rejects_revoked_refresh_credential_during_token_exchange() {
        let store = InMemoryBridgeStore::default();
        let manifest_id =
            ManifestId::new("man-2026-04-01-001").expect("fixture manifest id should be valid");
        let device_id =
            DeviceBindingId::new("device-1").expect("fixture device binding id should be valid");
        store
            .store_refresh_credential(
                "rfr_revoked_fixture",
                RefreshCredentialRecord {
                    account_id: "acct-1".to_owned(),
                    device_id: device_id.clone(),
                    manifest_id: manifest_id.clone(),
                    revoked: true,
                },
            )
            .await
            .expect("revoked refresh credential should store");
        let domain = bridge_with_store(store);
        let snapshot = active_snapshot();

        let error = domain
            .exchange_token(
                &snapshot,
                TokenExchangeInput {
                    manifest_id,
                    device_id,
                    client_version: "0.1.0".to_owned(),
                    core_version: 1,
                    carrier_profile_id: "carrier-primary".to_owned(),
                    requested_capabilities: vec![Capability::TcpRelay.id()],
                    refresh_credential: "rfr_revoked_fixture".to_owned(),
                },
                OffsetDateTime::from_unix_timestamp(1_700_000_010)
                    .expect("fixture timestamp should be valid"),
            )
            .await
            .expect_err("revoked refresh credential should be rejected");

        assert!(matches!(error, BridgeDomainError::RefreshCredentialRevoked));
    }

    #[tokio::test]
    async fn rejects_device_registration_when_the_limit_is_reached() {
        let domain = bridge();
        let snapshot = active_snapshot();
        let manifest_id =
            ManifestId::new("man-2026-04-01-001").expect("fixture manifest id should be valid");

        for device in ["device-1", "device-2"] {
            domain
                .register_device(
                    &snapshot,
                    DeviceRegistrationRequest {
                        manifest_id: manifest_id.clone(),
                        device_id: DeviceBindingId::new(device)
                            .expect("fixture device binding id should be valid"),
                        device_name: Some(format!("Device {device}")),
                        platform: "windows".to_owned(),
                        client_version: "0.1.0".to_owned(),
                        install_channel: Some("stable".to_owned()),
                    },
                    OffsetDateTime::from_unix_timestamp(1_700_000_000)
                        .expect("fixture timestamp should be valid"),
                )
                .await
                .expect("device registration within the limit should succeed");
        }

        let error = domain
            .register_device(
                &snapshot,
                DeviceRegistrationRequest {
                    manifest_id,
                    device_id: DeviceBindingId::new("device-3")
                        .expect("fixture device binding id should be valid"),
                    device_name: Some("Overflow Device".to_owned()),
                    platform: "windows".to_owned(),
                    client_version: "0.1.0".to_owned(),
                    install_channel: Some("stable".to_owned()),
                },
                OffsetDateTime::from_unix_timestamp(1_700_000_100)
                    .expect("fixture timestamp should be valid"),
            )
            .await
            .expect_err("device registration past the account limit should fail");

        assert!(matches!(
            error,
            BridgeDomainError::DeviceLimitReached { max_devices: 2 }
        ));
    }

    #[tokio::test]
    async fn rejects_revoked_device_during_token_exchange() {
        let store = InMemoryBridgeStore::default();
        let manifest_id =
            ManifestId::new("man-2026-04-01-001").expect("fixture manifest id should be valid");
        let device_id =
            DeviceBindingId::new("device-2").expect("fixture device binding id should be valid");
        store
            .upsert_device(StoredDeviceRecord {
                account_id: "acct-1".to_owned(),
                device_id: device_id.clone(),
                status: StoredDeviceStatus::Revoked,
            })
            .await
            .expect("revoked device should store");
        store
            .store_refresh_credential(
                "rfr_revoked_device",
                RefreshCredentialRecord {
                    account_id: "acct-1".to_owned(),
                    device_id: device_id.clone(),
                    manifest_id: manifest_id.clone(),
                    revoked: false,
                },
            )
            .await
            .expect("refresh credential should store");
        let domain = bridge_with_store(store);
        let snapshot = active_snapshot();

        let error = domain
            .exchange_token(
                &snapshot,
                TokenExchangeInput {
                    manifest_id,
                    device_id,
                    client_version: "0.1.0".to_owned(),
                    core_version: 1,
                    carrier_profile_id: "carrier-primary".to_owned(),
                    requested_capabilities: vec![Capability::TcpRelay.id()],
                    refresh_credential: "rfr_revoked_device".to_owned(),
                },
                OffsetDateTime::from_unix_timestamp(1_700_000_010)
                    .expect("fixture timestamp should be valid"),
            )
            .await
            .expect_err("revoked device should be rejected before token minting");

        assert!(matches!(error, BridgeDomainError::DeviceRevoked));
    }

    #[tokio::test]
    async fn rejects_duplicate_verified_webhook_delivery() {
        let fixture = load_duplicate_webhook_fixture();
        let adapter = FakeRemnawaveAdapter::with_account(
            BootstrapSubject::ShortUuid("sub-1".to_owned()),
            active_snapshot(),
        );
        adapter.push_webhook_effect(AdapterWebhookEffect::ReconcileAccount {
            account_id: "acct-1".to_owned(),
            reason: "duplicate-check".to_owned(),
        });
        let domain = bridge_with_adapter(adapter.clone(), InMemoryBridgeStore::default());
        let now = OffsetDateTime::from_unix_timestamp(1_775_002_200)
            .expect("fixture timestamp should be valid");

        let effect = domain
            .ingest_verified_webhook(
                WebhookVerificationInput {
                    signature_header: &fixture.signature_header,
                    timestamp_header: &fixture.timestamp_header,
                    body: fixture.body.as_bytes(),
                },
                &AcceptAllWebhookAuthenticator,
                fixture.payload.clone(),
                now,
                WebhookVerificationConfig {
                    max_skew: Duration::seconds(30),
                },
            )
            .await
            .expect("first verified webhook delivery should succeed");
        assert!(matches!(
            effect,
            AdapterWebhookEffect::ReconcileAccount { .. }
        ));

        let error = domain
            .ingest_verified_webhook(
                WebhookVerificationInput {
                    signature_header: &fixture.signature_header,
                    timestamp_header: &fixture.timestamp_header,
                    body: fixture.body.as_bytes(),
                },
                &AcceptAllWebhookAuthenticator,
                fixture.payload,
                now,
                WebhookVerificationConfig {
                    max_skew: Duration::seconds(30),
                },
            )
            .await
            .expect_err("duplicate verified webhook delivery should be rejected");

        assert!(matches!(error, BridgeDomainError::DuplicateWebhookDelivery));
        assert_eq!(
            adapter
                .calls()
                .into_iter()
                .filter(|call| matches!(call, FakeAdapterCall::IngestWebhook { .. }))
                .count(),
            1
        );
    }
}
