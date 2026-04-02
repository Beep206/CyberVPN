use std::{fmt, str::FromStr};

use chrono::{DateTime, Utc};
use serde::{Deserialize, Serialize};
use serde_json::Value;
use sqlx::FromRow;
use uuid::Uuid;

use crate::error::AppError;
use crate::transport_profiles::model::TransportProfilePolicySummary;

#[derive(Debug, Clone, Copy, Serialize, Deserialize, PartialEq, Eq)]
#[serde(rename_all = "lowercase")]
pub enum RolloutChannel {
    Lab,
    Canary,
    Stable,
}

impl RolloutChannel {
    pub fn as_str(self) -> &'static str {
        match self {
            Self::Lab => "lab",
            Self::Canary => "canary",
            Self::Stable => "stable",
        }
    }
}

impl fmt::Display for RolloutChannel {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        formatter.write_str(self.as_str())
    }
}

impl FromStr for RolloutChannel {
    type Err = AppError;

    fn from_str(value: &str) -> Result<Self, Self::Err> {
        match value {
            "lab" => Ok(Self::Lab),
            "canary" => Ok(Self::Canary),
            "stable" => Ok(Self::Stable),
            _ => Err(AppError::BadRequest(format!(
                "unsupported rollout channel: {value}"
            ))),
        }
    }
}

#[derive(Debug, Clone, Copy, Serialize, Deserialize, PartialEq, Eq)]
#[serde(rename_all = "lowercase")]
pub enum RolloutDesiredState {
    Running,
    Paused,
    Revoked,
    Completed,
}

impl RolloutDesiredState {
    pub fn as_str(self) -> &'static str {
        match self {
            Self::Running => "running",
            Self::Paused => "paused",
            Self::Revoked => "revoked",
            Self::Completed => "completed",
        }
    }
}

#[derive(Debug, Clone, Serialize, Deserialize, FromRow)]
pub struct NodeRegistryRecord {
    pub service_node_id: Uuid,
    pub remnawave_node_id: String,
    pub node_name: String,
    pub hostname: Option<String>,
    pub transport_port: Option<i32>,
    pub transport_enabled: bool,
    pub rollout_channel: String,
    pub node_group: String,
    pub adapter_node_label: String,
    pub last_heartbeat_at: Option<DateTime<Utc>>,
    pub daemon_version: Option<String>,
    pub active_rollout_id: Option<String>,
    pub last_synced_at: DateTime<Utc>,
    pub created_at: DateTime<Utc>,
    pub updated_at: DateTime<Utc>,
}

#[derive(Debug, Clone)]
pub struct NodeUpsertInput {
    pub remnawave_node_id: String,
    pub node_name: String,
    pub hostname: Option<String>,
    pub adapter_node_label: String,
    pub last_synced_at: DateTime<Utc>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PublishRolloutBatchRequest {
    pub rollout_id: String,
    pub batch_id: String,
    pub channel: RolloutChannel,
    pub manifest_version: String,
    pub target_node_ids: Vec<String>,
    #[serde(default = "default_true")]
    pub pause_on_rollback_spike: bool,
    #[serde(default = "default_true")]
    pub revoke_on_manifest_error: bool,
}

fn default_true() -> bool {
    true
}

#[derive(Debug, Clone, Serialize, Deserialize, FromRow)]
pub struct RolloutBatchRecord {
    pub rollout_id: String,
    pub channel: String,
    pub desired_state: String,
    pub batch_id: String,
    pub manifest_version: String,
    pub target_nodes: i32,
    pub completed_nodes: i32,
    pub failed_nodes: i32,
    pub desktop_connect_success_rate: f64,
    pub desktop_fallback_rate: f64,
    pub pause_on_rollback_spike: bool,
    pub revoke_on_manifest_error: bool,
    pub published_at: DateTime<Utc>,
    pub created_at: DateTime<Utc>,
    pub updated_at: DateTime<Utc>,
}

#[derive(Debug, Clone, Serialize)]
pub struct RolloutStateResponse {
    pub schema_version: &'static str,
    pub rollout_id: String,
    pub channel: String,
    pub desired_state: String,
    pub published_at: DateTime<Utc>,
    pub current_batch: RolloutBatchSummary,
    pub nodes: RolloutNodeSummary,
    pub desktop: RolloutDesktopSummary,
    pub policy: RolloutPolicySummary,
}

#[derive(Debug, Clone, Serialize)]
pub struct RolloutBatchSummary {
    pub batch_id: String,
    pub manifest_version: String,
    pub target_nodes: i32,
    pub completed_nodes: i32,
    pub failed_nodes: i32,
}

#[derive(Debug, Clone, Serialize)]
pub struct RolloutNodeSummary {
    pub healthy: i64,
    pub stale: i64,
    pub rolled_back: i64,
}

#[derive(Debug, Clone, Serialize)]
pub struct RolloutDesktopSummary {
    pub connect_success_rate: f64,
    pub fallback_rate: f64,
    pub continuity_observed_events: i32,
    pub continuity_success_rate: f64,
    pub cross_route_recovery_rate: f64,
    pub benchmark_observed_events: i32,
    pub throughput_evidence_observed_events: i32,
    pub average_benchmark_throughput_kbps: Option<f64>,
    pub average_relative_throughput_ratio: Option<f64>,
    pub average_relative_open_to_first_byte_gap_ratio: Option<f64>,
}

#[derive(Debug, Clone, Serialize)]
pub struct RolloutPolicySummary {
    pub pause_on_rollback_spike: bool,
    pub revoke_on_manifest_error: bool,
    pub active_transport_profile_id: Option<String>,
    pub active_profile_policy: Option<TransportProfilePolicySummary>,
    pub recommended_transport_profile_id: Option<String>,
    pub healthy_candidate_count: i32,
    pub eligible_candidate_count: i32,
    pub suppressed_candidate_count: i32,
    pub active_profile_suppressed: bool,
    pub channel_posture: String,
    pub automatic_reaction: String,
    pub applied_automatic_reaction: Option<String>,
    pub applied_transport_profile_id: Option<String>,
    pub automatic_reaction_trigger_reason: Option<String>,
    pub automatic_reaction_updated_at: Option<DateTime<Utc>>,
    pub pause_recommended: bool,
    pub profile_rotation_recommended: bool,
    pub recommended_action: Option<String>,
}

#[derive(Debug, Clone, Serialize)]
pub struct RolloutCanaryThresholdSummary {
    pub min_connect_success_rate: f64,
    pub max_fallback_rate: f64,
    pub min_continuity_observations: i32,
    pub require_throughput_evidence: bool,
    pub min_relative_throughput_ratio: f64,
    pub max_relative_open_to_first_byte_gap_ratio: f64,
    pub min_continuity_success_rate: f64,
    pub min_cross_route_recovery_rate: f64,
}

#[derive(Debug, Clone, Serialize)]
pub struct RolloutCanarySnapshotSummary {
    pub desired_state: String,
    pub failed_nodes: i32,
    pub rolled_back_nodes: i64,
    pub connect_success_rate: f64,
    pub fallback_rate: f64,
    pub continuity_observed_events: i32,
    pub continuity_success_rate: f64,
    pub cross_route_recovery_rate: f64,
    pub benchmark_observed_events: i32,
    pub throughput_evidence_observed_events: i32,
    pub average_benchmark_throughput_kbps: Option<f64>,
    pub average_relative_throughput_ratio: Option<f64>,
    pub average_relative_open_to_first_byte_gap_ratio: Option<f64>,
    pub channel_posture: String,
    pub active_profile_advisory_state: Option<String>,
    pub active_profile_new_session_posture: Option<String>,
    pub applied_automatic_reaction: Option<String>,
    pub applied_transport_profile_id: Option<String>,
}

#[derive(Debug, Clone, Serialize)]
pub struct RolloutCanaryEvidenceResponse {
    pub schema_version: &'static str,
    pub rollout_id: String,
    pub channel: String,
    pub evaluated_at: DateTime<Utc>,
    pub decision: String,
    pub reasons: Vec<String>,
    pub evidence_gaps: Vec<String>,
    pub recommended_follow_up_action: Option<String>,
    pub recommended_follow_up_severity: Option<String>,
    pub recommended_follow_up_tasks: Vec<String>,
    pub thresholds: RolloutCanaryThresholdSummary,
    pub snapshot: RolloutCanarySnapshotSummary,
}

#[derive(Debug, Clone, FromRow)]
pub struct RolloutPolicyActuationRecord {
    pub rollout_id: String,
    pub channel: String,
    pub reaction: String,
    pub target_transport_profile_id: Option<String>,
    pub trigger_reason: Option<String>,
    pub applied: bool,
    pub created_at: DateTime<Utc>,
    pub updated_at: DateTime<Utc>,
    pub cleared_at: Option<DateTime<Utc>>,
}

#[derive(Debug, Clone, FromRow)]
pub struct RolloutHealthCounts {
    pub healthy: i64,
    pub stale: i64,
    pub rolled_back: i64,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct NodeHeartbeatTransportProfile {
    pub transport_profile_id: String,
    pub profile_family: String,
    pub profile_version: i32,
    pub policy_version: i32,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct NodeHeartbeatDaemon {
    pub version: String,
    pub instance_id: String,
    pub status: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct NodeHeartbeatBundle {
    pub active_version: String,
    pub pending_version: Option<String>,
    pub last_known_good_version: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct NodeHeartbeatHealth {
    pub ready: bool,
    pub runtime_healthy: bool,
    pub apply_state: String,
    pub latency_ms: i32,
    pub reason: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct NodeHeartbeatCounters {
    pub rollback_total: i32,
    pub apply_fail_total: i32,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct NodeHeartbeatRequest {
    pub schema_version: String,
    pub heartbeat_id: Uuid,
    pub node_id: String,
    pub rollout_id: String,
    pub observed_at: DateTime<Utc>,
    pub transport_profile: NodeHeartbeatTransportProfile,
    pub daemon: NodeHeartbeatDaemon,
    pub bundle: NodeHeartbeatBundle,
    pub health: NodeHeartbeatHealth,
    pub counters: NodeHeartbeatCounters,
    pub capabilities: Vec<String>,
}

#[derive(Debug, Clone, Copy, Serialize, Deserialize, PartialEq, Eq)]
#[serde(rename_all = "lowercase")]
pub enum DesktopRuntimeEventKind {
    Ready,
    Fallback,
    Disconnect,
    Benchmark,
}

impl DesktopRuntimeEventKind {
    pub fn as_str(self) -> &'static str {
        match self {
            Self::Ready => "ready",
            Self::Fallback => "fallback",
            Self::Disconnect => "disconnect",
            Self::Benchmark => "benchmark",
        }
    }
}

#[derive(Debug, Clone, Copy, Serialize, Deserialize, PartialEq, Eq)]
#[serde(rename_all = "kebab-case")]
pub enum DesktopRuntimeCore {
    #[serde(alias = "private-transport")]
    Helix,
    SingBox,
    Xray,
}

impl DesktopRuntimeCore {
    pub fn as_str(self) -> &'static str {
        match self {
            Self::Helix => "helix",
            Self::SingBox => "sing-box",
            Self::Xray => "xray",
        }
    }

    pub fn is_stable(self) -> bool {
        matches!(self, Self::SingBox | Self::Xray)
    }
}

#[derive(Debug, Clone, Default, Serialize, Deserialize)]
pub struct DesktopRuntimeEventRecoveryEvidence {
    pub same_route_recovered: Option<bool>,
    pub ready_recovery_latency_ms: Option<i32>,
    pub proxy_ready_latency_ms: Option<i32>,
    pub proxy_ready_open_to_first_byte_gap_ms: Option<i32>,
    pub successful_cross_route_recovers: Option<i32>,
    pub last_cross_route_recovery_ms: Option<i32>,
}

impl DesktopRuntimeEventRecoveryEvidence {
    fn has_values(&self) -> bool {
        self.same_route_recovered.is_some()
            || self.ready_recovery_latency_ms.is_some()
            || self.proxy_ready_latency_ms.is_some()
            || self.proxy_ready_open_to_first_byte_gap_ms.is_some()
            || self.successful_cross_route_recovers.is_some()
            || self.last_cross_route_recovery_ms.is_some()
    }

    pub fn evidence_totals(&self) -> DesktopRuntimeEventEvidenceTotals {
        if let Some(same_route_recovered) = self.same_route_recovered {
            return DesktopRuntimeEventEvidenceTotals {
                continuity_attempts: 1,
                continuity_successes: 1,
                cross_route_successes: u64::from(!same_route_recovered),
            };
        }

        DesktopRuntimeEventEvidenceTotals::default()
    }
}

#[derive(Debug, Clone, Default, Serialize, Deserialize)]
pub struct DesktopRuntimeEventContinuityEvidence {
    pub active_streams: Option<i64>,
    pub pending_open_streams: Option<i64>,
    pub continuity_grace_active: Option<bool>,
    pub continuity_grace_route_endpoint_ref: Option<String>,
    pub continuity_grace_remaining_ms: Option<i32>,
    pub continuity_grace_entries: Option<i32>,
    pub successful_continuity_recovers: Option<i32>,
    pub failed_continuity_recovers: Option<i32>,
    pub last_continuity_recovery_ms: Option<i32>,
    pub successful_cross_route_recovers: Option<i32>,
    pub last_cross_route_recovery_ms: Option<i32>,
    pub active_route_quarantined: Option<bool>,
    pub active_route_quarantine_remaining_ms: Option<i32>,
    pub active_route_endpoint_ref: Option<String>,
    pub active_route_score: Option<i32>,
}

impl DesktopRuntimeEventContinuityEvidence {
    fn has_values(&self) -> bool {
        self.active_streams.is_some()
            || self.pending_open_streams.is_some()
            || self.continuity_grace_active.is_some()
            || self.continuity_grace_route_endpoint_ref.is_some()
            || self.continuity_grace_remaining_ms.is_some()
            || self.continuity_grace_entries.is_some()
            || self.successful_continuity_recovers.is_some()
            || self.failed_continuity_recovers.is_some()
            || self.last_continuity_recovery_ms.is_some()
            || self.successful_cross_route_recovers.is_some()
            || self.last_cross_route_recovery_ms.is_some()
            || self.active_route_quarantined.is_some()
            || self.active_route_quarantine_remaining_ms.is_some()
            || self.active_route_endpoint_ref.is_some()
            || self.active_route_score.is_some()
    }

    pub fn evidence_totals(&self) -> DesktopRuntimeEventEvidenceTotals {
        let continuity_successes = positive_i32_count(self.successful_continuity_recovers);
        let failed_continuity_recovers = positive_i32_count(self.failed_continuity_recovers);

        DesktopRuntimeEventEvidenceTotals {
            continuity_attempts: continuity_successes.saturating_add(failed_continuity_recovers),
            continuity_successes,
            cross_route_successes: positive_i32_count(self.successful_cross_route_recovers),
        }
    }
}

#[derive(Debug, Clone, Default, Serialize, Deserialize)]
pub struct DesktopRuntimeEventBenchmarkEvidence {
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
    pub frame_queue_peak: Option<i32>,
    pub recent_rtt_p95_ms: Option<i32>,
    pub active_streams: Option<i64>,
    pub pending_open_streams: Option<i64>,
}

impl DesktopRuntimeEventBenchmarkEvidence {
    fn has_values(&self) -> bool {
        self.benchmark_kind.is_some()
            || self.baseline_core.is_some()
            || self.target_count.is_some()
            || self.successful_targets.is_some()
            || self.attempts.is_some()
            || self.successes.is_some()
            || self.failures.is_some()
            || self.throughput_kbps.is_some()
            || self.relative_throughput_ratio_vs_baseline.is_some()
            || self.median_connect_latency_ms.is_some()
            || self.median_first_byte_latency_ms.is_some()
            || self.median_open_to_first_byte_gap_ms.is_some()
            || self.p95_open_to_first_byte_gap_ms.is_some()
            || self.relative_open_to_first_byte_gap_ratio_vs_baseline.is_some()
            || self.frame_queue_peak.is_some()
            || self.recent_rtt_p95_ms.is_some()
            || self.active_streams.is_some()
            || self.pending_open_streams.is_some()
    }
}

#[derive(Debug, Clone, Default, Serialize, Deserialize)]
pub struct DesktopRuntimeEventPayload {
    pub stage: Option<String>,
    pub runtime: Option<String>,
    pub requested_core: Option<String>,
    pub status: Option<String>,
    pub proxy_url: Option<String>,
    pub reason_code: Option<String>,
    pub recovery: Option<DesktopRuntimeEventRecoveryEvidence>,
    pub continuity: Option<DesktopRuntimeEventContinuityEvidence>,
    pub benchmark: Option<DesktopRuntimeEventBenchmarkEvidence>,
}

impl DesktopRuntimeEventPayload {
    pub fn from_value_lossy(payload: Value) -> Self {
        let mut typed = serde_json::from_value::<Self>(payload.clone()).unwrap_or_default();
        let Some(object) = payload.as_object() else {
            return typed;
        };

        if typed.recovery.is_none() {
            let recovery = DesktopRuntimeEventRecoveryEvidence {
                same_route_recovered: bool_field(object, "same_route_recovered"),
                ready_recovery_latency_ms: int_field(object, "ready_recovery_latency_ms"),
                proxy_ready_latency_ms: int_field(object, "proxy_ready_latency_ms"),
                proxy_ready_open_to_first_byte_gap_ms: int_field(
                    object,
                    "proxy_ready_open_to_first_byte_gap_ms",
                ),
                successful_cross_route_recovers: int_field(
                    object,
                    "successful_cross_route_recovers",
                ),
                last_cross_route_recovery_ms: int_field(object, "last_cross_route_recovery_ms"),
            };

            if recovery.has_values() {
                typed.recovery = Some(recovery);
            }
        }

        if typed.continuity.is_none() {
            let continuity = DesktopRuntimeEventContinuityEvidence {
                active_streams: int64_field(object, "active_streams"),
                pending_open_streams: int64_field(object, "pending_open_streams"),
                continuity_grace_active: bool_field(object, "continuity_grace_active"),
                continuity_grace_route_endpoint_ref: string_field(
                    object,
                    "continuity_grace_route_endpoint_ref",
                ),
                continuity_grace_remaining_ms: int_field(object, "continuity_grace_remaining_ms"),
                continuity_grace_entries: int_field(object, "continuity_grace_entries"),
                successful_continuity_recovers: int_field(object, "successful_continuity_recovers"),
                failed_continuity_recovers: int_field(object, "failed_continuity_recovers"),
                last_continuity_recovery_ms: int_field(object, "last_continuity_recovery_ms"),
                successful_cross_route_recovers: int_field(
                    object,
                    "successful_cross_route_recovers",
                ),
                last_cross_route_recovery_ms: int_field(object, "last_cross_route_recovery_ms"),
                active_route_quarantined: bool_field(object, "active_route_quarantined"),
                active_route_quarantine_remaining_ms: int_field(
                    object,
                    "active_route_quarantine_remaining_ms",
                ),
                active_route_endpoint_ref: string_field(object, "active_route_endpoint_ref"),
                active_route_score: int_field(object, "active_route_score"),
            };

            if continuity.has_values() {
                typed.continuity = Some(continuity);
            }
        }

        if typed.benchmark.is_none() {
            let benchmark = DesktopRuntimeEventBenchmarkEvidence {
                benchmark_kind: string_field(object, "benchmark_kind"),
                baseline_core: string_field(object, "baseline_core"),
                target_count: int_field(object, "target_count"),
                successful_targets: int_field(object, "successful_targets"),
                attempts: int_field(object, "attempts"),
                successes: int_field(object, "successes"),
                failures: int_field(object, "failures"),
                throughput_kbps: float_field(object, "throughput_kbps"),
                relative_throughput_ratio_vs_baseline: float_field(
                    object,
                    "relative_throughput_ratio_vs_baseline",
                ),
                median_connect_latency_ms: int_field(object, "median_connect_latency_ms"),
                median_first_byte_latency_ms: int_field(object, "median_first_byte_latency_ms"),
                median_open_to_first_byte_gap_ms: int_field(
                    object,
                    "median_open_to_first_byte_gap_ms",
                ),
                p95_open_to_first_byte_gap_ms: int_field(
                    object,
                    "p95_open_to_first_byte_gap_ms",
                ),
                relative_open_to_first_byte_gap_ratio_vs_baseline: float_field(
                    object,
                    "relative_open_to_first_byte_gap_ratio_vs_baseline",
                ),
                frame_queue_peak: int_field(object, "frame_queue_peak"),
                recent_rtt_p95_ms: int_field(object, "recent_rtt_p95_ms"),
                active_streams: int64_field(object, "active_streams"),
                pending_open_streams: int64_field(object, "pending_open_streams"),
            };

            if benchmark.has_values() {
                typed.benchmark = Some(benchmark);
            }
        }

        typed
    }

    pub fn evidence_totals(&self) -> DesktopRuntimeEventEvidenceTotals {
        let continuity_totals = self
            .continuity
            .as_ref()
            .map_or_else(DesktopRuntimeEventEvidenceTotals::default, |continuity| {
                continuity.evidence_totals()
            });
        if continuity_totals.continuity_attempts > 0 || continuity_totals.cross_route_successes > 0
        {
            return continuity_totals;
        }

        self.recovery
            .as_ref()
            .map_or_else(DesktopRuntimeEventEvidenceTotals::default, |recovery| {
                recovery.evidence_totals()
            })
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DesktopRuntimeEventRequest {
    pub schema_version: String,
    pub event_id: Uuid,
    pub user_id: String,
    pub desktop_client_id: String,
    pub manifest_version_id: Uuid,
    pub rollout_id: String,
    pub transport_profile_id: String,
    pub event_kind: DesktopRuntimeEventKind,
    pub active_core: DesktopRuntimeCore,
    pub fallback_core: Option<DesktopRuntimeCore>,
    pub latency_ms: Option<i32>,
    pub route_count: Option<i32>,
    pub reason: Option<String>,
    pub observed_at: DateTime<Utc>,
    #[serde(default = "default_event_payload")]
    pub payload: DesktopRuntimeEventPayload,
}

fn default_event_payload() -> DesktopRuntimeEventPayload {
    DesktopRuntimeEventPayload::default()
}

#[derive(Debug, Clone, Copy, Default, PartialEq, Eq)]
pub struct DesktopRuntimeEventEvidenceTotals {
    pub continuity_attempts: u64,
    pub continuity_successes: u64,
    pub cross_route_successes: u64,
}

impl DesktopRuntimeEventEvidenceTotals {
    pub fn accumulate(&mut self, other: Self) {
        self.continuity_attempts = self
            .continuity_attempts
            .saturating_add(other.continuity_attempts);
        self.continuity_successes = self
            .continuity_successes
            .saturating_add(other.continuity_successes);
        self.cross_route_successes = self
            .cross_route_successes
            .saturating_add(other.cross_route_successes);
    }

    pub fn continuity_success_rate(&self) -> f64 {
        if self.continuity_attempts == 0 {
            0.0
        } else {
            self.continuity_successes as f64 / self.continuity_attempts as f64
        }
    }

    pub fn cross_route_recovery_rate(&self) -> f64 {
        if self.continuity_attempts == 0 {
            0.0
        } else {
            self.cross_route_successes as f64 / self.continuity_attempts as f64
        }
    }
}

fn bool_field(object: &serde_json::Map<String, Value>, key: &str) -> Option<bool> {
    object.get(key).and_then(Value::as_bool)
}

fn int_field(object: &serde_json::Map<String, Value>, key: &str) -> Option<i32> {
    object
        .get(key)
        .and_then(Value::as_i64)
        .and_then(|value| i32::try_from(value).ok())
}

fn int64_field(object: &serde_json::Map<String, Value>, key: &str) -> Option<i64> {
    object.get(key).and_then(Value::as_i64)
}

fn float_field(object: &serde_json::Map<String, Value>, key: &str) -> Option<f64> {
    object.get(key).and_then(Value::as_f64)
}

fn string_field(object: &serde_json::Map<String, Value>, key: &str) -> Option<String> {
    object
        .get(key)
        .and_then(Value::as_str)
        .map(ToOwned::to_owned)
}

fn positive_i32_count(value: Option<i32>) -> u64 {
    value.unwrap_or_default().max(0) as u64
}

#[derive(Debug, Clone, Serialize)]
pub struct DesktopRuntimeEventAck {
    pub status: &'static str,
    pub rollout_id: String,
    pub event_kind: String,
}
