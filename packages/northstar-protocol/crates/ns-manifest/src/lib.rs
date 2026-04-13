#![forbid(unsafe_code)]

use base64::Engine as _;
use ed25519_dalek::pkcs8::{DecodePrivateKey, DecodePublicKey};
use ed25519_dalek::{Signature, Signer, SigningKey, Verifier, VerifyingKey};
use ns_core::{
    CarrierKind, CarrierProfileId, MANIFEST_SCHEMA_VERSION, ManifestId, SESSION_CORE_VERSION,
    ValidationError,
};
use serde::{Deserialize, Serialize};
use serde_json::Value;
use sha2::{Digest, Sha256};
use std::collections::{BTreeMap, BTreeSet, HashMap};
use thiserror::Error;
use time::OffsetDateTime;
use url::Url;

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct ManifestDocument {
    pub schema_version: u16,
    pub manifest_id: String,
    #[serde(with = "time::serde::rfc3339")]
    pub generated_at: OffsetDateTime,
    #[serde(with = "time::serde::rfc3339")]
    pub expires_at: OffsetDateTime,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub user: Option<ManifestUser>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub device_policy: Option<DevicePolicy>,
    pub client_constraints: ClientConstraints,
    pub token_service: TokenService,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub refresh: Option<RefreshPolicy>,
    pub carrier_profiles: Vec<CarrierProfile>,
    pub endpoints: Vec<GatewayEndpoint>,
    pub routing: RoutingPolicy,
    pub retry_policy: RetryPolicy,
    pub telemetry: TelemetryPolicy,
    pub signature: ManifestSignature,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct ManifestUser {
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub account_id: Option<String>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub plan_id: Option<String>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub display_name: Option<String>,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct DevicePolicy {
    pub max_devices: u32,
    pub require_device_binding: bool,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct ClientConstraints {
    pub min_client_version: String,
    pub recommended_client_version: String,
    pub allowed_core_versions: Vec<u64>,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct TokenService {
    pub url: Url,
    pub issuer: String,
    pub jwks_url: Url,
    pub session_token_ttl_seconds: u64,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum RefreshMode {
    OpaqueSecret,
    SignedProof,
    BootstrapOnly,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct RefreshPolicy {
    pub mode: RefreshMode,
    pub credential: String,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub rotation_hint_seconds: Option<u64>,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum ManifestCarrierKind {
    H3,
}

impl ManifestCarrierKind {
    pub fn into_core(self) -> CarrierKind {
        match self {
            Self::H3 => CarrierKind::H3,
        }
    }
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "UPPERCASE")]
pub enum HttpTemplateMethod {
    Connect,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct HttpTemplate {
    pub method: HttpTemplateMethod,
    pub path: String,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum ZeroRttPolicy {
    Disabled,
    Allow,
    ForceDisabled,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct ConnectBackoff {
    pub initial_ms: u64,
    pub max_ms: u64,
    pub jitter: f64,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct CarrierProfile {
    pub id: String,
    pub carrier_kind: ManifestCarrierKind,
    pub origin_host: String,
    pub origin_port: u16,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub sni: Option<String>,
    pub alpn: Vec<String>,
    pub control_template: HttpTemplate,
    pub relay_template: HttpTemplate,
    #[serde(default, skip_serializing_if = "BTreeMap::is_empty")]
    pub headers: BTreeMap<String, String>,
    pub datagram_enabled: bool,
    pub heartbeat_interval_ms: u64,
    pub idle_timeout_ms: u64,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub zero_rtt_policy: Option<ZeroRttPolicy>,
    pub connect_backoff: ConnectBackoff,
}

impl CarrierProfile {
    pub fn profile_id(&self) -> Result<CarrierProfileId, ValidationError> {
        CarrierProfileId::new(self.id.clone())
    }

    pub fn carrier_kind_id(&self) -> u64 {
        self.carrier_kind.clone().into_core().id()
    }
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct GatewayEndpoint {
    pub id: String,
    pub host: String,
    pub port: u16,
    pub region: String,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub routing_group: Option<String>,
    pub carrier_profile_ids: Vec<String>,
    pub priority: u16,
    pub weight: u16,
    #[serde(default, skip_serializing_if = "Vec::is_empty")]
    pub tags: Vec<String>,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum RoutingSelectionMode {
    LatencyWeighted,
    PriorityFirst,
    StickyRegion,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum RoutingFailoverMode {
    SameRegionThenGlobal,
    Global,
    StrictRegion,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct RoutingPolicy {
    pub selection_mode: RoutingSelectionMode,
    pub failover_mode: RoutingFailoverMode,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct RetryPolicy {
    pub connect_attempts: u64,
    pub initial_backoff_ms: u64,
    pub max_backoff_ms: u64,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct TelemetryPolicy {
    pub allow_client_reports: bool,
    pub sample_rate: f64,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct ManifestSignature {
    pub alg: String,
    pub key_id: String,
    pub value: String,
}

#[derive(Debug, Clone)]
pub struct ManifestSigner {
    key_id: String,
    signing_key: SigningKey,
}

#[derive(Debug, Clone, Default)]
pub struct ManifestTrustStore {
    keys: HashMap<String, VerifyingKey>,
}

impl ManifestTrustStore {
    pub fn insert(&mut self, key_id: impl Into<String>, key: VerifyingKey) {
        self.keys.insert(key_id.into(), key);
    }

    pub fn insert_public_key_pem(
        &mut self,
        key_id: impl Into<String>,
        pem: &[u8],
    ) -> Result<(), ManifestError> {
        let pem = std::str::from_utf8(pem).map_err(|_| ManifestError::PublicKeyPem)?;
        let key =
            VerifyingKey::from_public_key_pem(pem).map_err(|_| ManifestError::PublicKeyPem)?;
        self.insert(key_id, key);
        Ok(())
    }

    fn key_for(&self, key_id: &str) -> Result<&VerifyingKey, ManifestError> {
        self.keys
            .get(key_id)
            .ok_or(ManifestError::UnknownSignatureKey(key_id.to_owned()))
    }
}

impl ManifestSigner {
    pub fn new(key_id: impl Into<String>, signing_key: SigningKey) -> Self {
        Self {
            key_id: key_id.into(),
            signing_key,
        }
    }

    pub fn from_ed_pem(key_id: impl Into<String>, pem: &[u8]) -> Result<Self, ManifestError> {
        let pem = std::str::from_utf8(pem).map_err(|_| ManifestError::PrivateKeyPem)?;
        let signing_key =
            SigningKey::from_pkcs8_pem(pem).map_err(|_| ManifestError::PrivateKeyPem)?;
        Ok(Self::new(key_id, signing_key))
    }

    pub fn key_id(&self) -> &str {
        &self.key_id
    }

    pub fn verifying_key(&self) -> VerifyingKey {
        self.signing_key.verifying_key()
    }

    pub fn sign(&self, manifest: &mut ManifestDocument) -> Result<(), ManifestError> {
        manifest.signature.alg = "EdDSA".to_owned();
        manifest.signature.key_id = self.key_id.clone();
        manifest.signature.value = self.sign_document(manifest)?;
        Ok(())
    }

    pub fn sign_document(&self, manifest: &ManifestDocument) -> Result<String, ManifestError> {
        let signing_input = manifest.canonical_signing_input()?;
        let signature = self.signing_key.sign(&signing_input);
        Ok(base64::engine::general_purpose::URL_SAFE_NO_PAD.encode(signature.to_bytes()))
    }
}

impl ManifestDocument {
    pub fn parse_json(input: &str) -> Result<Self, ManifestError> {
        serde_json::from_str(input).map_err(ManifestError::Json)
    }

    pub fn parse_and_verify_json(
        input: &str,
        trust_store: &ManifestTrustStore,
        now: OffsetDateTime,
    ) -> Result<Self, ManifestError> {
        let manifest = Self::parse_json(input)?;
        manifest.validate(now)?;
        manifest.verify_signature(trust_store)?;
        Ok(manifest)
    }

    pub fn validate(&self, now: OffsetDateTime) -> Result<(), ManifestError> {
        if self.schema_version != MANIFEST_SCHEMA_VERSION {
            return Err(ManifestError::UnsupportedSchemaVersion(self.schema_version));
        }
        if self.generated_at >= self.expires_at {
            return Err(ManifestError::InvalidFreshnessWindow);
        }
        if self.expires_at <= now {
            return Err(ManifestError::ExpiredManifest);
        }

        ManifestId::new(self.manifest_id.clone())?;
        if let Some(user) = &self.user {
            validate_optional_bounded_string(
                "user.account_id",
                user.account_id.as_deref(),
                1,
                128,
            )?;
            validate_optional_bounded_string("user.plan_id", user.plan_id.as_deref(), 1, 128)?;
            validate_optional_bounded_string(
                "user.display_name",
                user.display_name.as_deref(),
                1,
                128,
            )?;
        }
        if let Some(device_policy) = &self.device_policy
            && !(1..=64).contains(&device_policy.max_devices)
        {
            return Err(ManifestError::FieldOutOfRange {
                field: "device_policy.max_devices",
                min: 1,
                max: 64,
                actual: u64::from(device_policy.max_devices),
            });
        }

        validate_bounded_string(
            "client_constraints.min_client_version",
            &self.client_constraints.min_client_version,
            1,
            32,
        )?;
        validate_bounded_string(
            "client_constraints.recommended_client_version",
            &self.client_constraints.recommended_client_version,
            1,
            32,
        )?;
        if self.client_constraints.allowed_core_versions.is_empty() {
            return Err(ManifestError::NoAllowedCoreVersions);
        }
        if !self
            .client_constraints
            .allowed_core_versions
            .iter()
            .any(|version| *version == u64::from(SESSION_CORE_VERSION))
        {
            return Err(ManifestError::CurrentCoreVersionNotAllowed);
        }

        validate_bounded_string("token_service.issuer", &self.token_service.issuer, 1, 128)?;
        if !(30..=3600).contains(&self.token_service.session_token_ttl_seconds) {
            return Err(ManifestError::FieldOutOfRange {
                field: "token_service.session_token_ttl_seconds",
                min: 30,
                max: 3600,
                actual: self.token_service.session_token_ttl_seconds,
            });
        }
        if let Some(refresh) = &self.refresh {
            validate_bounded_string("refresh.credential", &refresh.credential, 1, 4096)?;
            if let Some(rotation_hint_seconds) = refresh.rotation_hint_seconds
                && !(60..=31_536_000).contains(&rotation_hint_seconds)
            {
                return Err(ManifestError::FieldOutOfRange {
                    field: "refresh.rotation_hint_seconds",
                    min: 60,
                    max: 31_536_000,
                    actual: rotation_hint_seconds,
                });
            }
        }

        if self.carrier_profiles.is_empty() {
            return Err(ManifestError::NoCarrierProfiles);
        }
        if self.endpoints.is_empty() {
            return Err(ManifestError::NoEndpoints);
        }
        if self.signature.alg != "EdDSA" {
            return Err(ManifestError::UnsupportedSignatureAlgorithm(
                self.signature.alg.clone(),
            ));
        }
        validate_bounded_string("signature.key_id", &self.signature.key_id, 1, 128)?;
        validate_bounded_string("signature.value", &self.signature.value, 32, 8192)?;

        let mut profile_ids = BTreeSet::new();
        for profile in &self.carrier_profiles {
            validate_bounded_string("carrier_profiles[].id", &profile.id, 1, 128)?;
            if !profile_ids.insert(profile.id.clone()) {
                return Err(ManifestError::DuplicateCarrierProfileId(profile.id.clone()));
            }
            validate_bounded_string(
                "carrier_profiles[].origin_host",
                &profile.origin_host,
                1,
                255,
            )?;
            if profile.origin_port == 0 {
                return Err(ManifestError::EmptyField("carrier_profiles[].origin_port"));
            }
            validate_optional_bounded_string(
                "carrier_profiles[].sni",
                profile.sni.as_deref(),
                1,
                255,
            )?;
            if profile.alpn.is_empty() {
                return Err(ManifestError::EmptyField("carrier_profiles[].alpn"));
            }
            for alpn in &profile.alpn {
                validate_bounded_string("carrier_profiles[].alpn[]", alpn, 1, 16)?;
            }
            validate_bounded_string(
                "carrier_profiles[].control_template.path",
                &profile.control_template.path,
                1,
                256,
            )?;
            validate_bounded_string(
                "carrier_profiles[].relay_template.path",
                &profile.relay_template.path,
                1,
                256,
            )?;
            if !(5_000..=300_000).contains(&profile.heartbeat_interval_ms) {
                return Err(ManifestError::FieldOutOfRange {
                    field: "carrier_profiles[].heartbeat_interval_ms",
                    min: 5_000,
                    max: 300_000,
                    actual: profile.heartbeat_interval_ms,
                });
            }
            if !(10_000..=1_800_000).contains(&profile.idle_timeout_ms) {
                return Err(ManifestError::FieldOutOfRange {
                    field: "carrier_profiles[].idle_timeout_ms",
                    min: 10_000,
                    max: 1_800_000,
                    actual: profile.idle_timeout_ms,
                });
            }
            validate_connect_backoff(&profile.connect_backoff)?;
            for (header_name, header_value) in &profile.headers {
                validate_bounded_string("carrier_profiles[].headers.keys", header_name, 1, 1024)?;
                validate_bounded_string(
                    "carrier_profiles[].headers.values",
                    header_value,
                    0,
                    1024,
                )?;
            }
        }

        let mut any_usable_endpoint = false;
        for endpoint in &self.endpoints {
            validate_bounded_string("endpoints[].id", &endpoint.id, 1, 128)?;
            validate_bounded_string("endpoints[].host", &endpoint.host, 1, 255)?;
            validate_bounded_string("endpoints[].region", &endpoint.region, 1, 64)?;
            validate_optional_bounded_string(
                "endpoints[].routing_group",
                endpoint.routing_group.as_deref(),
                1,
                64,
            )?;
            if endpoint.carrier_profile_ids.is_empty() {
                return Err(ManifestError::EndpointWithoutCarrierProfile(
                    endpoint.id.clone(),
                ));
            }
            if endpoint.weight == 0 {
                return Err(ManifestError::EmptyField("endpoints[].weight"));
            }
            for tag in &endpoint.tags {
                validate_bounded_string("endpoints[].tags[]", tag, 1, 64)?;
            }
            for carrier_profile_id in &endpoint.carrier_profile_ids {
                validate_bounded_string(
                    "endpoints[].carrier_profile_ids[]",
                    carrier_profile_id,
                    1,
                    128,
                )?;
                if !profile_ids.contains(carrier_profile_id) {
                    return Err(ManifestError::UnknownCarrierProfileReference {
                        endpoint_id: endpoint.id.clone(),
                        carrier_profile_id: carrier_profile_id.clone(),
                    });
                }
                any_usable_endpoint = true;
            }
        }
        if !any_usable_endpoint {
            return Err(ManifestError::NoUsableEndpointCarrierProfilePair);
        }

        if self.retry_policy.connect_attempts == 0 {
            return Err(ManifestError::EmptyField("retry_policy.connect_attempts"));
        }
        if self.retry_policy.initial_backoff_ms == 0 {
            return Err(ManifestError::EmptyField("retry_policy.initial_backoff_ms"));
        }
        if self.retry_policy.max_backoff_ms == 0 {
            return Err(ManifestError::EmptyField("retry_policy.max_backoff_ms"));
        }
        if self.retry_policy.initial_backoff_ms > self.retry_policy.max_backoff_ms {
            return Err(ManifestError::InvalidBackoffWindow);
        }
        if !(0.0..=1.0).contains(&self.telemetry.sample_rate) {
            return Err(ManifestError::InvalidSampleRate(self.telemetry.sample_rate));
        }

        Ok(())
    }

    pub fn etag(&self) -> Result<String, ManifestError> {
        let json = serde_json::to_vec(self).map_err(ManifestError::Json)?;
        let digest = Sha256::digest(json);
        Ok(format!("m:sha256:{digest:x}"))
    }

    pub fn carrier_profile(&self, profile_id: &CarrierProfileId) -> Option<&CarrierProfile> {
        self.carrier_profiles
            .iter()
            .find(|profile| profile.id == profile_id.as_str())
    }

    pub fn endpoints_for_profile(&self, profile_id: &CarrierProfileId) -> Vec<&GatewayEndpoint> {
        self.endpoints
            .iter()
            .filter(|endpoint| {
                endpoint
                    .carrier_profile_ids
                    .iter()
                    .any(|candidate| candidate == profile_id.as_str())
            })
            .collect()
    }

    pub fn canonical_signing_input(&self) -> Result<Vec<u8>, ManifestError> {
        let mut canonical = serde_json::to_value(self).map_err(ManifestError::Json)?;
        let signature = canonical
            .get_mut("signature")
            .and_then(Value::as_object_mut)
            .ok_or(ManifestError::CanonicalizationInvariant)?;
        signature.remove("value");
        serde_jcs::to_vec(&canonical).map_err(ManifestError::Canonicalization)
    }

    pub fn signature_bytes(&self) -> Result<Vec<u8>, ManifestError> {
        base64::engine::general_purpose::URL_SAFE_NO_PAD
            .decode(self.signature.value.as_bytes())
            .map_err(|_| ManifestError::InvalidSignatureEncoding)
    }

    pub fn verify_signature(&self, trust_store: &ManifestTrustStore) -> Result<(), ManifestError> {
        let signing_input = self.canonical_signing_input()?;
        let signature_bytes = self.signature_bytes()?;
        self.verify_detached_signature(&signing_input, &signature_bytes, trust_store)
    }

    pub fn verify_detached_signature(
        &self,
        signing_input: &[u8],
        signature_bytes: &[u8],
        trust_store: &ManifestTrustStore,
    ) -> Result<(), ManifestError> {
        let key = trust_store.key_for(&self.signature.key_id)?;
        let signature = Signature::from_slice(signature_bytes)
            .map_err(|_| ManifestError::InvalidSignatureBytes)?;
        key.verify(signing_input, &signature)
            .map_err(|_| ManifestError::SignatureVerificationFailed)
    }
}

fn validate_bounded_string(
    field: &'static str,
    value: &str,
    min: usize,
    max: usize,
) -> Result<(), ManifestError> {
    let len = value.len();
    if len < min || len > max {
        return Err(ManifestError::FieldLength {
            field,
            min,
            max,
            actual: len,
        });
    }
    if min > 0 && value.trim().is_empty() {
        return Err(ManifestError::EmptyField(field));
    }
    Ok(())
}

fn validate_optional_bounded_string(
    field: &'static str,
    value: Option<&str>,
    min: usize,
    max: usize,
) -> Result<(), ManifestError> {
    if let Some(value) = value {
        validate_bounded_string(field, value, min, max)?;
    }
    Ok(())
}

fn validate_connect_backoff(connect_backoff: &ConnectBackoff) -> Result<(), ManifestError> {
    if !(50..=60_000).contains(&connect_backoff.initial_ms) {
        return Err(ManifestError::FieldOutOfRange {
            field: "carrier_profiles[].connect_backoff.initial_ms",
            min: 50,
            max: 60_000,
            actual: connect_backoff.initial_ms,
        });
    }
    if !(50..=600_000).contains(&connect_backoff.max_ms) {
        return Err(ManifestError::FieldOutOfRange {
            field: "carrier_profiles[].connect_backoff.max_ms",
            min: 50,
            max: 600_000,
            actual: connect_backoff.max_ms,
        });
    }
    if connect_backoff.initial_ms > connect_backoff.max_ms {
        return Err(ManifestError::InvalidBackoffWindow);
    }
    if !(0.0..=1.0).contains(&connect_backoff.jitter) {
        return Err(ManifestError::InvalidJitter(connect_backoff.jitter));
    }

    Ok(())
}

#[derive(Debug, Error)]
pub enum ManifestError {
    #[error("manifest json was invalid: {0}")]
    Json(serde_json::Error),
    #[error("validation failed: {0}")]
    Validation(#[from] ValidationError),
    #[error("manifest canonicalization failed: {0}")]
    Canonicalization(serde_json::Error),
    #[error("unsupported manifest schema version {0}")]
    UnsupportedSchemaVersion(u16),
    #[error("manifest freshness window is invalid")]
    InvalidFreshnessWindow,
    #[error("manifest has expired")]
    ExpiredManifest,
    #[error("client constraints did not allow any core version")]
    NoAllowedCoreVersions,
    #[error("the current Northstar core version is not allowed by the manifest")]
    CurrentCoreVersionNotAllowed,
    #[error("manifest did not include any carrier profiles")]
    NoCarrierProfiles,
    #[error("manifest did not include any endpoints")]
    NoEndpoints,
    #[error("unsupported manifest signature algorithm {0}")]
    UnsupportedSignatureAlgorithm(String),
    #[error("{0} must not be empty")]
    EmptyField(&'static str),
    #[error("{field} must be between {min} and {max} bytes, got {actual}")]
    FieldLength {
        field: &'static str,
        min: usize,
        max: usize,
        actual: usize,
    },
    #[error("{field} must be between {min} and {max}, got {actual}")]
    FieldOutOfRange {
        field: &'static str,
        min: u64,
        max: u64,
        actual: u64,
    },
    #[error("carrier profile id {0} was duplicated")]
    DuplicateCarrierProfileId(String),
    #[error("endpoint {0} did not reference any carrier profile")]
    EndpointWithoutCarrierProfile(String),
    #[error("endpoint {endpoint_id} referenced unknown carrier profile {carrier_profile_id}")]
    UnknownCarrierProfileReference {
        endpoint_id: String,
        carrier_profile_id: String,
    },
    #[error("manifest did not contain any usable endpoint/profile pairs")]
    NoUsableEndpointCarrierProfilePair,
    #[error("retry or connect-backoff window was invalid")]
    InvalidBackoffWindow,
    #[error("connect jitter {0} was outside 0.0..=1.0")]
    InvalidJitter(f64),
    #[error("telemetry sample rate {0} was outside 0.0..=1.0")]
    InvalidSampleRate(f64),
    #[error("signature key {0} is not trusted")]
    UnknownSignatureKey(String),
    #[error("manifest signature value was not valid base64url without padding")]
    InvalidSignatureEncoding,
    #[error("signature bytes were not a valid Ed25519 signature")]
    InvalidSignatureBytes,
    #[error("manifest signature verification failed")]
    SignatureVerificationFailed,
    #[error("manifest canonicalization invariant failed")]
    CanonicalizationInvariant,
    #[error("manifest signing key PEM was invalid")]
    PrivateKeyPem,
    #[error("manifest verification key PEM was invalid")]
    PublicKeyPem,
}

#[cfg(test)]
mod tests {
    use super::*;

    fn sample_manifest() -> ManifestDocument {
        ManifestDocument {
            schema_version: 1,
            manifest_id: "sha256:man-2026-04-01-001".to_owned(),
            generated_at: OffsetDateTime::from_unix_timestamp(1_700_000_000)
                .expect("fixture timestamp should be valid"),
            expires_at: OffsetDateTime::from_unix_timestamp(1_700_021_600)
                .expect("fixture timestamp should be valid"),
            user: Some(ManifestUser {
                account_id: Some("acct-1".to_owned()),
                plan_id: Some("plan-pro".to_owned()),
                display_name: None,
            }),
            device_policy: Some(DevicePolicy {
                max_devices: 2,
                require_device_binding: true,
            }),
            client_constraints: ClientConstraints {
                min_client_version: "0.1.0".to_owned(),
                recommended_client_version: "0.1.0".to_owned(),
                allowed_core_versions: vec![1],
            },
            token_service: TokenService {
                url: Url::parse("https://bridge.example/v0/token/exchange")
                    .expect("fixture url should parse"),
                issuer: "bridge.example".to_owned(),
                jwks_url: Url::parse("https://bridge.example/.well-known/jwks.json")
                    .expect("fixture url should parse"),
                session_token_ttl_seconds: 300,
            },
            refresh: Some(RefreshPolicy {
                mode: RefreshMode::OpaqueSecret,
                credential: "bootstrap-only-redacted".to_owned(),
                rotation_hint_seconds: Some(86_400),
            }),
            carrier_profiles: vec![CarrierProfile {
                id: "carrier-primary".to_owned(),
                carrier_kind: ManifestCarrierKind::H3,
                origin_host: "edge.example.net".to_owned(),
                origin_port: 443,
                sni: Some("edge.example.net".to_owned()),
                alpn: vec!["h3".to_owned()],
                control_template: HttpTemplate {
                    method: HttpTemplateMethod::Connect,
                    path: "/control".to_owned(),
                },
                relay_template: HttpTemplate {
                    method: HttpTemplateMethod::Connect,
                    path: "/relay".to_owned(),
                },
                headers: BTreeMap::new(),
                datagram_enabled: false,
                heartbeat_interval_ms: 15_000,
                idle_timeout_ms: 60_000,
                zero_rtt_policy: Some(ZeroRttPolicy::Disabled),
                connect_backoff: ConnectBackoff {
                    initial_ms: 500,
                    max_ms: 10_000,
                    jitter: 0.2,
                },
            }],
            endpoints: vec![GatewayEndpoint {
                id: "edge-1".to_owned(),
                host: "edge.example.net".to_owned(),
                port: 443,
                region: "eu-central".to_owned(),
                routing_group: Some("primary".to_owned()),
                carrier_profile_ids: vec!["carrier-primary".to_owned()],
                priority: 10,
                weight: 100,
                tags: vec!["stable".to_owned()],
            }],
            routing: RoutingPolicy {
                selection_mode: RoutingSelectionMode::LatencyWeighted,
                failover_mode: RoutingFailoverMode::SameRegionThenGlobal,
            },
            retry_policy: RetryPolicy {
                connect_attempts: 3,
                initial_backoff_ms: 500,
                max_backoff_ms: 10_000,
            },
            telemetry: TelemetryPolicy {
                allow_client_reports: true,
                sample_rate: 0.05,
            },
            signature: ManifestSignature {
                alg: "EdDSA".to_owned(),
                key_id: "manifest-key-1".to_owned(),
                value: "c2lnbmF0dXJlLXBlbmRpbmctdGVzdC1zaWduYXR1cmU".to_owned(),
            },
        }
    }

    #[test]
    fn rejects_unsupported_schema() {
        let mut manifest = sample_manifest();
        manifest.schema_version = 2;

        let error = manifest
            .validate(
                OffsetDateTime::from_unix_timestamp(1_700_000_100)
                    .expect("fixture timestamp should be valid"),
            )
            .expect_err("unsupported schema version should be rejected");

        assert!(matches!(error, ManifestError::UnsupportedSchemaVersion(2)));
    }

    #[test]
    fn filters_endpoints_by_profile() {
        let manifest = sample_manifest();
        let endpoints = manifest.endpoints_for_profile(
            &CarrierProfileId::new("carrier-primary")
                .expect("fixture carrier profile should be valid"),
        );
        assert_eq!(endpoints.len(), 1);
        assert_eq!(endpoints[0].id, "edge-1");
    }

    #[test]
    fn canonical_signing_input_omits_signature_value() {
        let mut manifest = sample_manifest();
        manifest.signature.value = "should-not-affect-signing-input".to_owned();
        let canonical = manifest
            .canonical_signing_input()
            .expect("canonical manifest input should render");
        let rendered = String::from_utf8(canonical).expect("canonical bytes should be valid UTF-8");

        assert!(rendered.contains("\"key_id\":\"manifest-key-1\""));
        assert!(!rendered.contains("\"value\""));
        assert!(!rendered.contains("should-not-affect-signing-input"));
    }

    #[test]
    fn signer_round_trips_manifest_document() {
        let mut manifest = sample_manifest();
        let signer = ManifestSigner::new("manifest-key-1", SigningKey::from_bytes(&[3_u8; 32]));
        signer
            .sign(&mut manifest)
            .expect("manifest should sign with the deterministic test key");

        let mut trust_store = ManifestTrustStore::default();
        trust_store.insert("manifest-key-1", signer.verifying_key());

        manifest
            .verify_signature(&trust_store)
            .expect("signed manifest should verify successfully");
    }

    #[test]
    fn rejects_unknown_endpoint_profile_reference() {
        let mut manifest = sample_manifest();
        manifest.endpoints[0].carrier_profile_ids = vec!["missing-profile".to_owned()];

        let error = manifest
            .validate(
                OffsetDateTime::from_unix_timestamp(1_700_000_100)
                    .expect("fixture timestamp should be valid"),
            )
            .expect_err("endpoint should not be allowed to reference a missing profile");

        assert!(matches!(
            error,
            ManifestError::UnknownCarrierProfileReference { .. }
        ));
    }
}
