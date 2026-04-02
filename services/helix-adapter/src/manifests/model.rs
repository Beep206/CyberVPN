use chrono::{DateTime, Utc};
use serde::{Deserialize, Serialize};
use sqlx::FromRow;
use uuid::Uuid;

use crate::node_registry::model::RolloutChannel;

#[derive(Debug, Clone, Serialize)]
pub struct ManifestSubject {
    pub user_id: String,
    pub desktop_client_id: String,
    pub entitlement_id: String,
    pub channel: RolloutChannel,
}

#[derive(Debug, Clone, Serialize)]
pub struct ManifestTransport {
    pub transport_family: &'static str,
    pub protocol_version: i32,
    pub session_mode: String,
}

#[derive(Debug, Clone, Serialize)]
pub struct ManifestTransportProfile {
    pub transport_profile_id: String,
    pub profile_family: String,
    pub profile_version: i32,
    pub policy_version: i32,
    pub deprecation_state: String,
}

#[derive(Debug, Clone, Serialize)]
pub struct ManifestCompatibilityWindow {
    pub profile_family: String,
    pub min_transport_profile_version: i32,
    pub max_transport_profile_version: i32,
}

#[derive(Debug, Clone, Serialize)]
pub struct ManifestHealthPolicy {
    pub startup_timeout_seconds: i32,
    pub runtime_unhealthy_threshold: i32,
}

#[derive(Debug, Clone, Serialize)]
pub struct ManifestCapabilityProfile {
    pub required_capabilities: Vec<String>,
    pub fallback_core: String,
    pub health_policy: ManifestHealthPolicy,
}

#[derive(Debug, Clone, Serialize)]
pub struct ManifestRoute {
    pub endpoint_ref: String,
    pub dial_host: String,
    pub dial_port: u16,
    pub server_name: Option<String>,
    pub preference: i32,
    pub policy_tag: String,
}

#[derive(Debug, Clone, Serialize)]
pub struct ManifestCredentials {
    pub key_id: String,
    pub token: String,
}

#[derive(Debug, Clone, Serialize)]
pub struct ManifestSignature {
    pub alg: &'static str,
    pub key_id: String,
    pub sig: String,
}

#[derive(Debug, Clone, Serialize)]
pub struct ManifestIntegrity {
    pub manifest_hash: String,
    pub signature: ManifestSignature,
}

#[derive(Debug, Clone, Serialize)]
pub struct ManifestObservability {
    pub trace_id: String,
    pub metrics_namespace: String,
}

#[derive(Debug, Clone, Serialize)]
pub struct UnsignedManifestDocument {
    pub schema_version: &'static str,
    pub manifest_id: Uuid,
    pub rollout_id: String,
    pub issued_at: DateTime<Utc>,
    pub expires_at: DateTime<Utc>,
    pub subject: ManifestSubject,
    pub transport: ManifestTransport,
    pub transport_profile: ManifestTransportProfile,
    pub compatibility_window: ManifestCompatibilityWindow,
    pub capability_profile: ManifestCapabilityProfile,
    pub routes: Vec<ManifestRoute>,
    pub credentials: ManifestCredentials,
    pub observability: ManifestObservability,
}

#[derive(Debug, Clone, Serialize)]
pub struct ManifestDocument {
    pub schema_version: &'static str,
    pub manifest_id: Uuid,
    pub rollout_id: String,
    pub issued_at: DateTime<Utc>,
    pub expires_at: DateTime<Utc>,
    pub subject: ManifestSubject,
    pub transport: ManifestTransport,
    pub transport_profile: ManifestTransportProfile,
    pub compatibility_window: ManifestCompatibilityWindow,
    pub capability_profile: ManifestCapabilityProfile,
    pub routes: Vec<ManifestRoute>,
    pub credentials: ManifestCredentials,
    pub integrity: ManifestIntegrity,
    pub observability: ManifestObservability,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SupportedTransportProfile {
    pub profile_family: String,
    pub min_transport_profile_version: i32,
    pub max_transport_profile_version: i32,
    pub supported_policy_versions: Vec<i32>,
}

#[derive(Debug, Clone, Deserialize)]
pub struct ResolveManifestRequest {
    pub user_id: String,
    pub desktop_client_id: String,
    pub entitlement_id: String,
    pub trace_id: String,
    pub channel: Option<RolloutChannel>,
    pub supported_protocol_versions: Option<Vec<i32>>,
    pub supported_transport_profiles: Option<Vec<SupportedTransportProfile>>,
    pub preferred_fallback_core: Option<String>,
}

#[derive(Debug, Clone, Serialize)]
pub struct ResolveManifestResponse {
    pub manifest_version_id: Uuid,
    pub manifest: ManifestDocument,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub selected_profile_policy:
        Option<crate::transport_profiles::model::TransportProfilePolicySummary>,
}

#[derive(Debug, Clone, Serialize)]
pub struct ClientCapabilityDefaults {
    pub schema_version: &'static str,
    pub client_family: &'static str,
    pub default_channel: RolloutChannel,
    pub supported_protocol_versions: Vec<i32>,
    pub supported_transport_profiles: Vec<SupportedTransportProfile>,
    pub required_capabilities: Vec<String>,
    pub fallback_cores: Vec<String>,
    pub rollout_channels: Vec<RolloutChannel>,
}

#[derive(Debug, Clone)]
pub struct ManifestRenderInput {
    pub rollout_id: String,
    pub issued_at: DateTime<Utc>,
    pub expires_at: DateTime<Utc>,
    pub subject: ManifestSubject,
    pub trace_id: String,
    pub routes: Vec<ManifestRoute>,
    pub effective_fallback_core: String,
    pub key_id: String,
    pub session_token: String,
    pub selected_profile: crate::transport_profiles::model::TransportProfileRecord,
}

#[derive(Debug, Clone, Serialize, FromRow)]
pub struct ManifestVersionRecord {
    pub manifest_version_id: Uuid,
    pub manifest_id: Uuid,
    pub rollout_id: String,
    pub manifest_template_version: String,
    pub transport_profile_id: Option<String>,
    pub profile_family: Option<String>,
    pub profile_version: Option<i32>,
    pub policy_version: Option<i32>,
    pub subject_user_id: String,
    pub desktop_client_id: String,
    pub entitlement_id: String,
    pub channel: String,
    pub protocol_version: i32,
    pub manifest_hash: String,
    pub signature_alg: String,
    pub signature_key_id: String,
    pub signature: String,
    pub revoked_at: Option<DateTime<Utc>>,
    pub created_at: DateTime<Utc>,
}
