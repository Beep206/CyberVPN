#![forbid(unsafe_code)]

mod http;

use async_trait::async_trait;
use serde::{Deserialize, Serialize};
use serde_json::Value;
use std::collections::{HashMap, VecDeque};
use std::sync::{Arc, Mutex};
use thiserror::Error;
use time::{Duration, OffsetDateTime};

pub use http::{HttpRemnawaveAdapter, HttpRemnawaveAdapterConfig};

#[derive(Debug, Clone, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub enum BootstrapSubject {
    ShortUuid(String),
    BridgeAlias(String),
    SignedEnvelope(String),
}

impl BootstrapSubject {
    pub fn as_str(&self) -> &str {
        match self {
            Self::ShortUuid(value) | Self::BridgeAlias(value) | Self::SignedEnvelope(value) => {
                value
            }
        }
    }

    pub fn validate(&self) -> Result<(), AdapterError> {
        if self.as_str().trim().is_empty() {
            return Err(AdapterError::InvalidData("bootstrap_subject"));
        }

        Ok(())
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum AccountLifecycle {
    Active,
    Disabled,
    Revoked,
    Expired,
    Limited,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct VertaAccess {
    pub verta_enabled: bool,
    pub policy_epoch: u64,
    pub device_limit: Option<u32>,
    pub allowed_core_versions: Vec<u64>,
    pub allowed_carrier_profiles: Vec<String>,
    pub allowed_capabilities: Vec<u64>,
    pub rollout_cohort: Option<String>,
    pub preferred_regions: Vec<String>,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct AccountSnapshot {
    pub account_id: String,
    pub bootstrap_subjects: Vec<BootstrapSubject>,
    pub lifecycle: AccountLifecycle,
    pub verta_access: VertaAccess,
    pub metadata: Option<Value>,
    pub observed_at_unix: i64,
    pub source_version: Option<String>,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct VerifiedWebhookPayload {
    pub event_id: String,
    pub event_type: String,
    pub account_id: Option<String>,
    pub occurred_at_unix: i64,
    pub payload: Value,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub enum AdapterWebhookEffect {
    Noop,
    InvalidateAccount { account_id: String },
    ReconcileAccount { account_id: String, reason: String },
    ReconcileAll { reason: String },
    Snapshot(Box<AccountSnapshot>),
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum FakeAdapterCall {
    ResolveBootstrap {
        subject: BootstrapSubject,
    },
    FetchAccount {
        account_id: String,
    },
    FetchMetadata {
        account_id: String,
    },
    UpsertMetadata {
        account_id: String,
    },
    IngestWebhook {
        event_type: String,
        account_id: Option<String>,
    },
}

#[derive(Debug, Clone)]
pub struct WebhookVerificationInput<'a> {
    pub signature_header: &'a str,
    pub timestamp_header: &'a str,
    pub body: &'a [u8],
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct WebhookVerificationConfig {
    pub max_skew: Duration,
}

impl Default for WebhookVerificationConfig {
    fn default() -> Self {
        Self {
            max_skew: Duration::minutes(5),
        }
    }
}

#[derive(Debug, Error, Clone, PartialEq, Eq)]
pub enum AdapterError {
    #[error("not found")]
    NotFound,
    #[error("unauthorized")]
    Unauthorized,
    #[error("rate limited")]
    RateLimited,
    #[error("schema drift")]
    SchemaDrift,
    #[error("unavailable")]
    Unavailable,
    #[error("timeout")]
    Timeout,
    #[error("invalid data in {0}")]
    InvalidData(&'static str),
    #[error("conflict")]
    Conflict,
}

#[derive(Debug, Error, Clone, PartialEq, Eq)]
pub enum WebhookVerificationError {
    #[error("missing signature header")]
    MissingSignature,
    #[error("missing timestamp header")]
    MissingTimestamp,
    #[error("timestamp header was not a valid unix timestamp")]
    InvalidTimestamp,
    #[error("webhook timestamp is outside the accepted freshness window")]
    StaleTimestamp,
    #[error("signature verification failed")]
    InvalidSignature,
}

pub trait WebhookAuthenticator: Send + Sync {
    fn verify(
        &self,
        timestamp_header: &str,
        signature_header: &str,
        body: &[u8],
    ) -> Result<(), WebhookVerificationError>;
}

#[async_trait]
pub trait RemnawaveAdapter: Send + Sync {
    async fn resolve_bootstrap_subject(
        &self,
        subject: &BootstrapSubject,
    ) -> Result<AccountSnapshot, AdapterError>;

    async fn fetch_account_snapshot(
        &self,
        account_id: &str,
    ) -> Result<AccountSnapshot, AdapterError>;

    async fn fetch_user_metadata(&self, account_id: &str) -> Result<Option<Value>, AdapterError>;

    async fn upsert_user_metadata(
        &self,
        account_id: &str,
        patch: Value,
    ) -> Result<(), AdapterError>;

    async fn ingest_verified_webhook(
        &self,
        payload: VerifiedWebhookPayload,
    ) -> Result<AdapterWebhookEffect, AdapterError>;
}

pub fn verify_webhook_input(
    input: WebhookVerificationInput<'_>,
    authenticator: &dyn WebhookAuthenticator,
    now: OffsetDateTime,
    config: WebhookVerificationConfig,
) -> Result<(), WebhookVerificationError> {
    if input.signature_header.trim().is_empty() {
        return Err(WebhookVerificationError::MissingSignature);
    }
    if input.timestamp_header.trim().is_empty() {
        return Err(WebhookVerificationError::MissingTimestamp);
    }

    let timestamp = input
        .timestamp_header
        .parse::<i64>()
        .map_err(|_| WebhookVerificationError::InvalidTimestamp)?;
    let occurred_at = OffsetDateTime::from_unix_timestamp(timestamp)
        .map_err(|_| WebhookVerificationError::InvalidTimestamp)?;
    let skew = now - occurred_at;
    if skew.abs() > config.max_skew {
        return Err(WebhookVerificationError::StaleTimestamp);
    }

    authenticator.verify(input.timestamp_header, input.signature_header, input.body)
}

#[derive(Clone, Default)]
pub struct FakeRemnawaveAdapter {
    state: Arc<Mutex<FakeAdapterState>>,
}

#[derive(Default)]
struct FakeAdapterState {
    accounts_by_subject: HashMap<BootstrapSubject, AccountSnapshot>,
    accounts_by_id: HashMap<String, AccountSnapshot>,
    metadata_by_account: HashMap<String, Value>,
    webhook_effects: VecDeque<AdapterWebhookEffect>,
    calls: Vec<FakeAdapterCall>,
    next_error: Option<AdapterError>,
}

impl FakeRemnawaveAdapter {
    pub fn with_account(subject: BootstrapSubject, snapshot: AccountSnapshot) -> Self {
        let adapter = Self::default();
        {
            let mut state = adapter.state.lock().expect("fake adapter poisoned");
            state.accounts_by_subject.insert(subject, snapshot.clone());
            state
                .accounts_by_id
                .insert(snapshot.account_id.clone(), snapshot);
        }
        adapter
    }

    pub fn push_webhook_effect(&self, effect: AdapterWebhookEffect) {
        let mut state = self.state.lock().expect("fake adapter poisoned");
        state.webhook_effects.push_back(effect);
    }

    pub fn fail_next(&self, error: AdapterError) {
        let mut state = self.state.lock().expect("fake adapter poisoned");
        state.next_error = Some(error);
    }

    pub fn calls(&self) -> Vec<FakeAdapterCall> {
        self.state
            .lock()
            .expect("fake adapter poisoned")
            .calls
            .clone()
    }

    fn take_next_error(state: &mut FakeAdapterState) -> Result<(), AdapterError> {
        if let Some(error) = state.next_error.take() {
            return Err(error);
        }

        Ok(())
    }
}

#[async_trait]
impl RemnawaveAdapter for FakeRemnawaveAdapter {
    async fn resolve_bootstrap_subject(
        &self,
        subject: &BootstrapSubject,
    ) -> Result<AccountSnapshot, AdapterError> {
        subject.validate()?;

        let mut state = self.state.lock().expect("fake adapter poisoned");
        Self::take_next_error(&mut state)?;
        state.calls.push(FakeAdapterCall::ResolveBootstrap {
            subject: subject.clone(),
        });

        state
            .accounts_by_subject
            .get(subject)
            .cloned()
            .ok_or(AdapterError::NotFound)
    }

    async fn fetch_account_snapshot(
        &self,
        account_id: &str,
    ) -> Result<AccountSnapshot, AdapterError> {
        let mut state = self.state.lock().expect("fake adapter poisoned");
        Self::take_next_error(&mut state)?;
        state.calls.push(FakeAdapterCall::FetchAccount {
            account_id: account_id.to_owned(),
        });

        state
            .accounts_by_id
            .get(account_id)
            .cloned()
            .ok_or(AdapterError::NotFound)
    }

    async fn fetch_user_metadata(&self, account_id: &str) -> Result<Option<Value>, AdapterError> {
        let mut state = self.state.lock().expect("fake adapter poisoned");
        Self::take_next_error(&mut state)?;
        state.calls.push(FakeAdapterCall::FetchMetadata {
            account_id: account_id.to_owned(),
        });
        Ok(state.metadata_by_account.get(account_id).cloned())
    }

    async fn upsert_user_metadata(
        &self,
        account_id: &str,
        patch: Value,
    ) -> Result<(), AdapterError> {
        let mut state = self.state.lock().expect("fake adapter poisoned");
        Self::take_next_error(&mut state)?;
        state.calls.push(FakeAdapterCall::UpsertMetadata {
            account_id: account_id.to_owned(),
        });
        state
            .metadata_by_account
            .insert(account_id.to_owned(), patch);
        Ok(())
    }

    async fn ingest_verified_webhook(
        &self,
        payload: VerifiedWebhookPayload,
    ) -> Result<AdapterWebhookEffect, AdapterError> {
        let mut state = self.state.lock().expect("fake adapter poisoned");
        Self::take_next_error(&mut state)?;
        state.calls.push(FakeAdapterCall::IngestWebhook {
            event_type: payload.event_type.clone(),
            account_id: payload.account_id.clone(),
        });

        Ok(state
            .webhook_effects
            .pop_front()
            .unwrap_or(AdapterWebhookEffect::Noop))
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    struct AcceptAllWebhookAuthenticator;

    impl WebhookAuthenticator for AcceptAllWebhookAuthenticator {
        fn verify(
            &self,
            _timestamp_header: &str,
            _signature_header: &str,
            _body: &[u8],
        ) -> Result<(), WebhookVerificationError> {
            Ok(())
        }
    }

    fn active_snapshot() -> AccountSnapshot {
        AccountSnapshot {
            account_id: "acct-1".to_owned(),
            bootstrap_subjects: vec![BootstrapSubject::ShortUuid("sub-1".to_owned())],
            lifecycle: AccountLifecycle::Active,
            verta_access: VertaAccess {
                verta_enabled: true,
                policy_epoch: 7,
                device_limit: Some(2),
                allowed_core_versions: vec![1],
                allowed_carrier_profiles: vec!["carrier-primary".to_owned()],
                allowed_capabilities: vec![1, 2],
                rollout_cohort: Some("alpha".to_owned()),
                preferred_regions: vec!["eu-central".to_owned()],
            },
            metadata: None,
            observed_at_unix: 1_700_000_000,
            source_version: Some("2.7.4".to_owned()),
        }
    }

    #[tokio::test]
    async fn fake_adapter_resolves_known_bootstrap_subject() {
        let adapter = FakeRemnawaveAdapter::with_account(
            BootstrapSubject::ShortUuid("sub-1".to_owned()),
            active_snapshot(),
        );

        let snapshot = adapter
            .resolve_bootstrap_subject(&BootstrapSubject::ShortUuid("sub-1".to_owned()))
            .await
            .expect("known bootstrap subject should resolve");

        assert_eq!(snapshot.account_id, "acct-1");
        assert_eq!(adapter.calls().len(), 1);
    }

    #[test]
    fn webhook_timestamp_must_be_fresh() {
        let now = OffsetDateTime::from_unix_timestamp(1_700_000_000)
            .expect("fixture timestamp should be valid");
        let result = verify_webhook_input(
            WebhookVerificationInput {
                signature_header: "sig",
                timestamp_header: "1699999000",
                body: b"{}",
            },
            &AcceptAllWebhookAuthenticator,
            now,
            WebhookVerificationConfig {
                max_skew: Duration::seconds(30),
            },
        );

        assert!(matches!(
            result,
            Err(WebhookVerificationError::StaleTimestamp)
        ));
    }
}
