use serde::{Deserialize, Serialize};

use crate::engine::error::AppError;

fn default_helix_health_bind_addr() -> String {
    "127.0.0.1:38991".to_string()
}

fn default_helix_health_url() -> String {
    "http://127.0.0.1:38991/healthz".to_string()
}

fn default_helix_proxy_bind_addr() -> String {
    "127.0.0.1:38990".to_string()
}

fn default_helix_proxy_url() -> String {
    "socks5://127.0.0.1:38990".to_string()
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
#[serde(rename_all = "kebab-case")]
pub enum EngineCore {
    SingBox,
    Xray,
    #[serde(alias = "private-transport")]
    Helix,
}

impl EngineCore {
    pub fn as_str(&self) -> &'static str {
        match self {
            Self::SingBox => "sing-box",
            Self::Xray => "xray",
            Self::Helix => "helix",
        }
    }

    pub fn is_stable(&self) -> bool {
        matches!(self, Self::SingBox | Self::Xray)
    }
}

impl TryFrom<&str> for EngineCore {
    type Error = AppError;

    fn try_from(value: &str) -> Result<Self, Self::Error> {
        match value {
            "sing-box" => Ok(Self::SingBox),
            "xray" => Ok(Self::Xray),
            "helix" | "private-transport" => Ok(Self::Helix),
            _ => Err(AppError::System(format!(
                "Invalid proxy engine core selected: {value}"
            ))),
        }
    }
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct SupportedTransportProfile {
    pub profile_family: String,
    pub min_transport_profile_version: i32,
    pub max_transport_profile_version: i32,
    pub supported_policy_versions: Vec<i32>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct HelixCapabilityDefaults {
    pub schema_version: String,
    pub client_family: String,
    pub default_channel: String,
    pub supported_protocol_versions: Vec<i32>,
    pub supported_transport_profiles: Vec<SupportedTransportProfile>,
    pub required_capabilities: Vec<String>,
    pub fallback_cores: Vec<String>,
    pub rollout_channels: Vec<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct HelixResolveManifestRequest {
    pub desktop_client_id: String,
    pub trace_id: String,
    pub channel: Option<String>,
    pub supported_protocol_versions: Vec<i32>,
    pub supported_transport_profiles: Vec<SupportedTransportProfile>,
    pub preferred_fallback_core: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct HelixManifestSubject {
    pub user_id: String,
    pub desktop_client_id: String,
    pub entitlement_id: String,
    pub channel: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct HelixManifestTransport {
    pub transport_family: String,
    pub protocol_version: i32,
    pub session_mode: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct HelixManifestTransportProfile {
    pub transport_profile_id: String,
    pub profile_family: String,
    pub profile_version: i32,
    pub policy_version: i32,
    pub deprecation_state: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct HelixManifestCompatibilityWindow {
    pub profile_family: String,
    pub min_transport_profile_version: i32,
    pub max_transport_profile_version: i32,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct HelixManifestHealthPolicy {
    pub startup_timeout_seconds: i32,
    pub runtime_unhealthy_threshold: i32,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct HelixManifestCapabilityProfile {
    pub required_capabilities: Vec<String>,
    pub fallback_core: String,
    pub health_policy: HelixManifestHealthPolicy,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct HelixManifestRoute {
    pub endpoint_ref: String,
    pub dial_host: String,
    pub dial_port: u16,
    pub server_name: Option<String>,
    pub preference: i32,
    pub policy_tag: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct HelixManifestCredentials {
    pub key_id: String,
    pub token: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct HelixSignature {
    pub alg: String,
    pub key_id: String,
    pub sig: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct HelixManifestIntegrity {
    pub manifest_hash: String,
    pub signature: HelixSignature,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct HelixManifestObservability {
    pub trace_id: String,
    pub metrics_namespace: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct HelixManifestDocument {
    pub schema_version: String,
    pub manifest_id: String,
    pub rollout_id: String,
    pub issued_at: String,
    pub expires_at: String,
    pub subject: HelixManifestSubject,
    pub transport: HelixManifestTransport,
    pub transport_profile: HelixManifestTransportProfile,
    pub compatibility_window: HelixManifestCompatibilityWindow,
    pub capability_profile: HelixManifestCapabilityProfile,
    pub routes: Vec<HelixManifestRoute>,
    pub credentials: HelixManifestCredentials,
    pub integrity: HelixManifestIntegrity,
    pub observability: HelixManifestObservability,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct HelixResolvedManifest {
    pub manifest_version_id: String,
    pub manifest: HelixManifestDocument,
    pub selected_profile_policy: Option<HelixSelectedProfilePolicy>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct HelixSelectedProfilePolicy {
    pub observed_events: i32,
    pub connect_success_rate: f64,
    pub fallback_rate: f64,
    pub continuity_success_rate: f64,
    pub cross_route_recovery_rate: f64,
    pub policy_score: i32,
    pub degraded: bool,
    pub advisory_state: String,
    pub recommended_action: Option<String>,
    pub selection_eligible: bool,
    pub new_session_issuable: bool,
    pub new_session_posture: String,
    #[serde(default)]
    pub suppression_window_active: bool,
    #[serde(default)]
    pub suppression_reason: Option<String>,
    #[serde(default)]
    pub suppression_observation_count: i32,
    #[serde(default)]
    pub suppressed_until: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct HelixSidecarConfig {
    pub schema_version: String,
    pub manifest_id: String,
    pub manifest_version_id: String,
    pub rollout_id: String,
    #[serde(default = "default_helix_health_bind_addr")]
    pub health_bind_addr: String,
    #[serde(default = "default_helix_health_url")]
    pub health_url: String,
    #[serde(default = "default_helix_proxy_bind_addr")]
    pub proxy_bind_addr: String,
    #[serde(default = "default_helix_proxy_url")]
    pub proxy_url: String,
    pub transport_family: String,
    pub session_mode: String,
    pub transport_profile_id: String,
    pub profile_family: String,
    pub profile_version: i32,
    pub policy_version: i32,
    pub compatibility_window: HelixManifestCompatibilityWindow,
    pub fallback_core: String,
    pub required_capabilities: Vec<String>,
    pub startup_timeout_seconds: i32,
    pub runtime_unhealthy_threshold: i32,
    pub credentials: HelixManifestCredentials,
    pub routes: Vec<HelixManifestRoute>,
    pub observability: HelixManifestObservability,
    pub integrity: HelixManifestIntegrity,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct HelixPreparedRuntime {
    pub manifest_id: String,
    pub manifest_version_id: String,
    pub rollout_id: String,
    pub transport_profile_id: String,
    pub config_path: String,
    pub sidecar_path: String,
    pub binary_available: bool,
    #[serde(default = "default_helix_health_url")]
    pub health_url: String,
    #[serde(default = "default_helix_proxy_url")]
    pub proxy_url: String,
    pub fallback_core: String,
    pub route_count: usize,
    pub startup_timeout_seconds: i32,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct HelixSidecarHealth {
    pub schema_version: String,
    pub status: String,
    pub ready: bool,
    pub connected: bool,
    pub manifest_id: String,
    pub rollout_id: String,
    pub transport_profile_id: String,
    pub route_count: usize,
    pub proxy_url: String,
    pub session_id: Option<String>,
    pub remote_addr: Option<String>,
    pub active_route_endpoint_ref: Option<String>,
    pub active_route_probe_latency_ms: Option<u32>,
    #[serde(default)]
    pub active_route_score: Option<i32>,
    #[serde(default)]
    pub standby_route_endpoint_ref: Option<String>,
    #[serde(default)]
    pub standby_route_probe_latency_ms: Option<u32>,
    #[serde(default)]
    pub standby_route_score: Option<i32>,
    #[serde(default)]
    pub standby_ready: bool,
    #[serde(default)]
    pub continuity_grace_active: bool,
    #[serde(default)]
    pub continuity_grace_route_endpoint_ref: Option<String>,
    #[serde(default)]
    pub continuity_grace_remaining_ms: Option<i32>,
    #[serde(default)]
    pub active_route_continuity_grace_entries: u32,
    #[serde(default)]
    pub active_route_successful_continuity_recovers: u32,
    #[serde(default)]
    pub active_route_failed_continuity_recovers: u32,
    #[serde(default)]
    pub active_route_last_continuity_recovery_ms: Option<i32>,
    #[serde(default)]
    pub active_route_successful_cross_route_recovers: u32,
    #[serde(default)]
    pub active_route_last_cross_route_recovery_ms: Option<i32>,
    #[serde(default)]
    pub active_route_quarantined: bool,
    #[serde(default)]
    pub active_route_quarantine_remaining_ms: Option<i32>,
    #[serde(default)]
    pub active_route_successful_activations: u32,
    #[serde(default)]
    pub active_route_failed_activations: u32,
    #[serde(default)]
    pub active_route_failover_count: u32,
    #[serde(default)]
    pub active_route_healthy_observations: u32,
    pub last_ping_rtt_ms: Option<u32>,
    pub active_streams: u64,
    #[serde(default)]
    pub pending_open_streams: u64,
    #[serde(default)]
    pub max_concurrent_streams: u64,
    #[serde(default)]
    pub frame_queue_depth: u32,
    #[serde(default)]
    pub frame_queue_peak: u32,
    pub bytes_sent: u64,
    pub bytes_received: u64,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct HelixStreamTelemetrySample {
    pub stream_id: u64,
    pub target_authority: String,
    pub opened_at: String,
    pub closed_at: Option<String>,
    pub duration_ms: Option<u64>,
    pub bytes_sent: u64,
    pub bytes_received: u64,
    pub peak_frame_queue_depth: u32,
    pub peak_inbound_queue_depth: u32,
    pub close_reason: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct HelixSidecarTelemetry {
    pub schema_version: String,
    pub collected_at: String,
    pub health: HelixSidecarHealth,
    #[serde(default)]
    pub recent_rtt_ms: Vec<u32>,
    #[serde(default)]
    pub recent_streams: Vec<HelixStreamTelemetrySample>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct HelixRuntimeState {
    pub backend_url: Option<String>,
    pub desktop_client_id: String,
    pub last_manifest: Option<HelixResolvedManifest>,
    pub last_prepared_runtime: Option<HelixPreparedRuntime>,
    pub last_fallback_reason: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TransportBenchmarkRequest {
    pub proxy_url: Option<String>,
    pub target_host: Option<String>,
    pub target_port: Option<u16>,
    pub target_path: Option<String>,
    pub attempts: Option<u32>,
    pub download_bytes_limit: Option<usize>,
    pub connect_timeout_ms: Option<u64>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TransportBenchmarkComparisonRequest {
    pub profile_id: String,
    #[serde(default)]
    pub cores: Vec<EngineCore>,
    pub benchmark: TransportBenchmarkRequest,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TransportBenchmarkMatrixTarget {
    pub label: String,
    pub host: String,
    pub port: u16,
    pub path: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TransportBenchmarkMatrixRequest {
    pub profile_id: String,
    #[serde(default)]
    pub cores: Vec<EngineCore>,
    pub targets: Vec<TransportBenchmarkMatrixTarget>,
    pub benchmark: TransportBenchmarkRequest,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TransportBenchmarkSample {
    pub attempt: u32,
    pub success: bool,
    pub connect_latency_ms: Option<i32>,
    pub first_byte_latency_ms: Option<i32>,
    pub bytes_read: u64,
    pub bytes_written: u64,
    pub throughput_kbps: Option<f64>,
    pub error: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct HelixQueuePressureSummary {
    pub frame_queue_depth: u32,
    pub frame_queue_peak: u32,
    pub active_streams: u64,
    pub pending_open_streams: u64,
    pub max_concurrent_streams: u64,
    pub recent_rtt_p50_ms: Option<i32>,
    pub recent_rtt_p95_ms: Option<i32>,
    pub recent_stream_peak_frame_queue_depth: Option<u32>,
    pub recent_stream_peak_inbound_queue_depth: Option<u32>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct HelixContinuitySummary {
    pub grace_active: bool,
    pub grace_route_endpoint_ref: Option<String>,
    pub grace_remaining_ms: Option<i32>,
    pub active_streams: u64,
    pub pending_open_streams: u64,
    pub active_route_quarantined: bool,
    pub active_route_quarantine_remaining_ms: Option<i32>,
    pub continuity_grace_entries: u32,
    pub successful_continuity_recovers: u32,
    pub failed_continuity_recovers: u32,
    pub last_continuity_recovery_ms: Option<i32>,
    pub successful_cross_route_recovers: u32,
    pub last_cross_route_recovery_ms: Option<i32>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TransportBenchmarkReport {
    pub schema_version: String,
    pub run_id: String,
    pub generated_at: String,
    pub active_core: String,
    pub proxy_url: String,
    pub target_host: String,
    pub target_port: u16,
    pub target_path: String,
    pub attempts: u32,
    pub successes: u32,
    pub failures: u32,
    pub median_connect_latency_ms: Option<i32>,
    pub p95_connect_latency_ms: Option<i32>,
    pub median_first_byte_latency_ms: Option<i32>,
    pub p95_first_byte_latency_ms: Option<i32>,
    pub median_open_to_first_byte_gap_ms: Option<i32>,
    pub p95_open_to_first_byte_gap_ms: Option<i32>,
    pub average_throughput_kbps: Option<f64>,
    #[serde(default)]
    pub helix_queue_pressure: Option<HelixQueuePressureSummary>,
    #[serde(default)]
    pub helix_continuity: Option<HelixContinuitySummary>,
    pub bytes_read_total: u64,
    pub bytes_written_total: u64,
    pub samples: Vec<TransportBenchmarkSample>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TransportBenchmarkComparisonEntry {
    pub requested_core: String,
    pub effective_core: Option<String>,
    pub benchmark: Option<TransportBenchmarkReport>,
    pub error: Option<String>,
    pub relative_connect_latency_ratio: Option<f64>,
    pub relative_first_byte_latency_ratio: Option<f64>,
    pub relative_open_to_first_byte_gap_ratio: Option<f64>,
    pub relative_throughput_ratio: Option<f64>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TransportBenchmarkComparisonReport {
    pub schema_version: String,
    pub run_id: String,
    pub generated_at: String,
    pub profile_id: String,
    pub baseline_core: Option<String>,
    pub entries: Vec<TransportBenchmarkComparisonEntry>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TransportBenchmarkMatrixTargetReport {
    pub label: String,
    pub host: String,
    pub port: u16,
    pub path: String,
    pub comparison: TransportBenchmarkComparisonReport,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TransportBenchmarkMatrixCoreSummary {
    pub core: String,
    pub completed_targets: u32,
    pub failed_targets: u32,
    pub median_connect_latency_ms: Option<i32>,
    pub median_first_byte_latency_ms: Option<i32>,
    pub median_open_to_first_byte_gap_ms: Option<i32>,
    pub average_throughput_kbps: Option<f64>,
    pub average_relative_connect_latency_ratio: Option<f64>,
    pub average_relative_first_byte_latency_ratio: Option<f64>,
    pub average_relative_open_to_first_byte_gap_ratio: Option<f64>,
    pub average_relative_throughput_ratio: Option<f64>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TransportBenchmarkMatrixReport {
    pub schema_version: String,
    pub run_id: String,
    pub generated_at: String,
    pub profile_id: String,
    pub baseline_core: Option<String>,
    pub targets: Vec<TransportBenchmarkMatrixTargetReport>,
    pub core_summaries: Vec<TransportBenchmarkMatrixCoreSummary>,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
#[serde(rename_all = "kebab-case")]
pub enum HelixRecoveryBenchmarkMode {
    Failover,
    Reconnect,
}

impl HelixRecoveryBenchmarkMode {
    pub fn as_str(&self) -> &'static str {
        match self {
            Self::Failover => "failover",
            Self::Reconnect => "reconnect",
        }
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct HelixRecoveryBenchmarkRequest {
    pub profile_id: String,
    pub mode: HelixRecoveryBenchmarkMode,
    pub benchmark: TransportBenchmarkRequest,
    pub recovery_timeout_ms: Option<u64>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct HelixSidecarBenchActionReport {
    pub schema_version: String,
    pub action: String,
    pub success: bool,
    pub route_before: Option<String>,
    pub route_after: Option<String>,
    pub recovery_latency_ms: Option<i32>,
    pub message: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct HelixRecoveryBenchmarkReport {
    pub schema_version: String,
    pub run_id: String,
    pub generated_at: String,
    pub profile_id: String,
    pub mode: String,
    pub proxy_url: String,
    pub route_before: Option<String>,
    pub route_after: Option<String>,
    pub ready_recovery_latency_ms: Option<i32>,
    pub proxy_ready_latency_ms: Option<i32>,
    pub proxy_ready_open_to_first_byte_gap_ms: Option<i32>,
    #[serde(default)]
    pub proxy_ready_measurement: Option<String>,
    #[serde(default)]
    pub proxy_ready_probe: Option<TransportBenchmarkSample>,
    pub recovered: bool,
    #[serde(default)]
    pub same_route_recovered: Option<bool>,
    pub health_before: Option<HelixSidecarHealth>,
    pub health_after: Option<HelixSidecarHealth>,
    #[serde(default)]
    pub continuity_before: Option<HelixContinuitySummary>,
    #[serde(default)]
    pub continuity_after: Option<HelixContinuitySummary>,
    pub telemetry_before: Option<HelixSidecarTelemetry>,
    pub telemetry_after: Option<HelixSidecarTelemetry>,
    pub action: Option<HelixSidecarBenchActionReport>,
    pub post_recovery_benchmark: Option<TransportBenchmarkReport>,
    pub error: Option<String>,
}

#[derive(Debug, Clone, Default, Serialize, Deserialize)]
pub struct HelixRuntimeEventRecoveryEvidence {
    pub same_route_recovered: Option<bool>,
    pub ready_recovery_latency_ms: Option<i32>,
    pub proxy_ready_latency_ms: Option<i32>,
    pub proxy_ready_open_to_first_byte_gap_ms: Option<i32>,
    pub successful_cross_route_recovers: Option<u32>,
    pub last_cross_route_recovery_ms: Option<i32>,
}

#[derive(Debug, Clone, Default, Serialize, Deserialize)]
pub struct HelixRuntimeEventContinuityEvidence {
    pub active_streams: Option<u64>,
    pub pending_open_streams: Option<u64>,
    pub continuity_grace_active: Option<bool>,
    pub continuity_grace_route_endpoint_ref: Option<String>,
    pub continuity_grace_remaining_ms: Option<i32>,
    pub continuity_grace_entries: Option<u32>,
    pub successful_continuity_recovers: Option<u32>,
    pub failed_continuity_recovers: Option<u32>,
    pub last_continuity_recovery_ms: Option<i32>,
    pub successful_cross_route_recovers: Option<u32>,
    pub last_cross_route_recovery_ms: Option<i32>,
    pub active_route_quarantined: Option<bool>,
    pub active_route_quarantine_remaining_ms: Option<i32>,
    pub active_route_endpoint_ref: Option<String>,
    pub active_route_score: Option<i32>,
}

impl From<&HelixSidecarHealth> for HelixRuntimeEventContinuityEvidence {
    fn from(health: &HelixSidecarHealth) -> Self {
        Self {
            active_streams: Some(health.active_streams),
            pending_open_streams: Some(health.pending_open_streams),
            continuity_grace_active: Some(health.continuity_grace_active),
            continuity_grace_route_endpoint_ref: health.continuity_grace_route_endpoint_ref.clone(),
            continuity_grace_remaining_ms: health.continuity_grace_remaining_ms,
            continuity_grace_entries: Some(health.active_route_continuity_grace_entries),
            successful_continuity_recovers: Some(
                health.active_route_successful_continuity_recovers,
            ),
            failed_continuity_recovers: Some(health.active_route_failed_continuity_recovers),
            last_continuity_recovery_ms: health.active_route_last_continuity_recovery_ms,
            successful_cross_route_recovers: Some(
                health.active_route_successful_cross_route_recovers,
            ),
            last_cross_route_recovery_ms: health.active_route_last_cross_route_recovery_ms,
            active_route_quarantined: Some(health.active_route_quarantined),
            active_route_quarantine_remaining_ms: health.active_route_quarantine_remaining_ms,
            active_route_endpoint_ref: health.active_route_endpoint_ref.clone(),
            active_route_score: health.active_route_score,
        }
    }
}

#[derive(Debug, Clone, Default, Serialize, Deserialize)]
pub struct HelixRuntimeEventBenchmarkEvidence {
    pub benchmark_kind: Option<String>,
    pub baseline_core: Option<String>,
    pub target_count: Option<i32>,
    pub successful_targets: Option<i32>,
    pub attempts: Option<i32>,
    pub successes: Option<i32>,
    pub failures: Option<i32>,
    pub throughput_kbps: Option<f64>,
    pub relative_throughput_ratio_vs_baseline: Option<f64>,
    pub median_connect_latency_ms: Option<i32>,
    pub median_first_byte_latency_ms: Option<i32>,
    pub median_open_to_first_byte_gap_ms: Option<i32>,
    pub p95_open_to_first_byte_gap_ms: Option<i32>,
    pub relative_open_to_first_byte_gap_ratio_vs_baseline: Option<f64>,
    pub frame_queue_peak: Option<u32>,
    pub recent_rtt_p95_ms: Option<i32>,
    pub active_streams: Option<u64>,
    pub pending_open_streams: Option<u64>,
}

#[derive(Debug, Clone, Default, Serialize, Deserialize)]
pub struct HelixRuntimeEventPayload {
    pub stage: Option<String>,
    pub runtime: Option<String>,
    pub requested_core: Option<String>,
    pub status: Option<String>,
    pub proxy_url: Option<String>,
    pub reason_code: Option<String>,
    pub recovery: Option<HelixRuntimeEventRecoveryEvidence>,
    pub continuity: Option<HelixRuntimeEventContinuityEvidence>,
    pub benchmark: Option<HelixRuntimeEventBenchmarkEvidence>,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
#[serde(rename_all = "lowercase")]
pub enum HelixRuntimeEventKind {
    Ready,
    Fallback,
    Disconnect,
    Benchmark,
}

impl HelixRuntimeEventKind {
    pub fn as_str(&self) -> &'static str {
        match self {
            Self::Ready => "ready",
            Self::Fallback => "fallback",
            Self::Disconnect => "disconnect",
            Self::Benchmark => "benchmark",
        }
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct HelixRuntimeEventRequest {
    pub schema_version: String,
    pub desktop_client_id: String,
    pub manifest_version_id: String,
    pub rollout_id: String,
    pub transport_profile_id: String,
    pub event_kind: HelixRuntimeEventKind,
    pub active_core: String,
    pub fallback_core: Option<String>,
    pub latency_ms: Option<i32>,
    pub route_count: Option<i32>,
    pub reason: Option<String>,
    #[serde(default = "default_runtime_event_payload")]
    pub payload: HelixRuntimeEventPayload,
}

fn default_runtime_event_payload() -> HelixRuntimeEventPayload {
    HelixRuntimeEventPayload::default()
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct HelixRuntimeEventReport {
    pub event_kind: HelixRuntimeEventKind,
    pub active_core: String,
    pub fallback_core: Option<String>,
    pub latency_ms: Option<i32>,
    pub route_count: Option<usize>,
    pub reason: Option<String>,
    #[serde(default = "default_runtime_event_payload")]
    pub payload: HelixRuntimeEventPayload,
}

pub fn default_desktop_capabilities() -> HelixCapabilityDefaults {
    HelixCapabilityDefaults {
        schema_version: "1.1".to_string(),
        client_family: "desktop-tauri".to_string(),
        default_channel: "lab".to_string(),
        supported_protocol_versions: vec![1],
        supported_transport_profiles: vec![
            SupportedTransportProfile {
                profile_family: "edge-hybrid".to_string(),
                min_transport_profile_version: 1,
                max_transport_profile_version: 4,
                supported_policy_versions: vec![4, 5, 6, 7],
            },
            SupportedTransportProfile {
                profile_family: "edge-stateful".to_string(),
                min_transport_profile_version: 1,
                max_transport_profile_version: 2,
                supported_policy_versions: vec![2, 3],
            },
        ],
        required_capabilities: vec![
            "protocol.v1".to_string(),
            "fallback.auto".to_string(),
            "sidecar.sigverify".to_string(),
            "proxy.socks5.connect".to_string(),
        ],
        fallback_cores: vec!["sing-box".to_string(), "xray".to_string()],
        rollout_channels: vec![
            "lab".to_string(),
            "canary".to_string(),
            "stable".to_string(),
        ],
    }
}

pub fn ensure_manifest_compatible(
    manifest: &HelixManifestDocument,
    local_capabilities: &HelixCapabilityDefaults,
) -> Result<(), AppError> {
    if !local_capabilities
        .supported_protocol_versions
        .contains(&manifest.transport.protocol_version)
    {
        return Err(AppError::System(format!(
            "Unsupported Helix protocol version: {}",
            manifest.transport.protocol_version
        )));
    }

    let profile_supported =
        local_capabilities
            .supported_transport_profiles
            .iter()
            .any(|supported| {
                supported.profile_family == manifest.transport_profile.profile_family
                    && manifest.transport_profile.profile_version
                        >= supported.min_transport_profile_version
                    && manifest.transport_profile.profile_version
                        <= supported.max_transport_profile_version
                    && supported
                        .supported_policy_versions
                        .contains(&manifest.transport_profile.policy_version)
            });

    if !profile_supported {
        return Err(AppError::System(format!(
            "Unsupported transport profile window: {} v{} policy {}",
            manifest.transport_profile.profile_family,
            manifest.transport_profile.profile_version,
            manifest.transport_profile.policy_version
        )));
    }

    if manifest.compatibility_window.profile_family != manifest.transport_profile.profile_family {
        return Err(AppError::System(
            "Manifest compatibility window family does not match transport profile family"
                .to_string(),
        ));
    }

    if manifest.transport_profile.profile_version
        < manifest.compatibility_window.min_transport_profile_version
        || manifest.transport_profile.profile_version
            > manifest.compatibility_window.max_transport_profile_version
    {
        return Err(AppError::System(
            "Manifest transport profile version falls outside the declared compatibility window"
                .to_string(),
        ));
    }

    Ok(())
}

#[cfg(test)]
mod tests {
    use super::{
        default_desktop_capabilities, ensure_manifest_compatible, EngineCore,
        HelixManifestCapabilityProfile, HelixManifestCompatibilityWindow, HelixManifestCredentials,
        HelixManifestDocument, HelixManifestHealthPolicy, HelixManifestIntegrity,
        HelixManifestObservability, HelixManifestRoute, HelixManifestSubject,
        HelixManifestTransport, HelixManifestTransportProfile, HelixSignature,
    };

    fn sample_manifest(profile_version: i32, policy_version: i32) -> HelixManifestDocument {
        HelixManifestDocument {
            schema_version: "1.1".to_string(),
            manifest_id: "manifest-1".to_string(),
            rollout_id: "rollout-lab-1".to_string(),
            issued_at: "2026-03-31T09:00:00Z".to_string(),
            expires_at: "2026-03-31T10:00:00Z".to_string(),
            subject: HelixManifestSubject {
                user_id: "user-1".to_string(),
                desktop_client_id: "desktop-1".to_string(),
                entitlement_id: "subscription:user-1".to_string(),
                channel: "lab".to_string(),
            },
            transport: HelixManifestTransport {
                transport_family: "helix".to_string(),
                protocol_version: 1,
                session_mode: "hybrid".to_string(),
            },
            transport_profile: HelixManifestTransportProfile {
                transport_profile_id: "ptp-lab-edge-v2".to_string(),
                profile_family: "edge-hybrid".to_string(),
                profile_version,
                policy_version,
                deprecation_state: "active".to_string(),
            },
            compatibility_window: HelixManifestCompatibilityWindow {
                profile_family: "edge-hybrid".to_string(),
                min_transport_profile_version: 1,
                max_transport_profile_version: 4,
            },
            capability_profile: HelixManifestCapabilityProfile {
                required_capabilities: vec!["protocol.v1".to_string()],
                fallback_core: "sing-box".to_string(),
                health_policy: HelixManifestHealthPolicy {
                    startup_timeout_seconds: 15,
                    runtime_unhealthy_threshold: 3,
                },
            },
            routes: vec![HelixManifestRoute {
                endpoint_ref: "pt-lab-node".to_string(),
                dial_host: "127.0.0.1".to_string(),
                dial_port: 9443,
                server_name: Some("pt-lab-node.local".to_string()),
                preference: 10,
                policy_tag: "primary".to_string(),
            }],
            credentials: HelixManifestCredentials {
                key_id: "sig-key-test".to_string(),
                token: "pt_tok_123".to_string(),
            },
            integrity: HelixManifestIntegrity {
                manifest_hash: "sha256:1234".to_string(),
                signature: HelixSignature {
                    alg: "ed25519".to_string(),
                    key_id: "sig-key-test".to_string(),
                    sig: "signed".to_string(),
                },
            },
            observability: HelixManifestObservability {
                trace_id: "trace-1".to_string(),
                metrics_namespace: "helix".to_string(),
            },
        }
    }

    #[test]
    fn accepts_manifest_with_supported_profile_window() {
        let capabilities = default_desktop_capabilities();
        let manifest = sample_manifest(2, 4);
        assert!(ensure_manifest_compatible(&manifest, &capabilities).is_ok());
    }

    #[test]
    fn rejects_manifest_with_unsupported_policy_version() {
        let capabilities = default_desktop_capabilities();
        let manifest = sample_manifest(2, 99);
        assert!(ensure_manifest_compatible(&manifest, &capabilities).is_err());
    }

    #[test]
    fn parses_helix_core_name() {
        let core = EngineCore::try_from("helix").expect("Helix core");
        assert_eq!(core.as_str(), "helix");
        assert!(!core.is_stable());
    }

    #[test]
    fn parses_legacy_private_transport_core_name() {
        let core = EngineCore::try_from("private-transport").expect("legacy Helix core");
        assert_eq!(core.as_str(), "helix");
        assert!(!core.is_stable());
    }
}
