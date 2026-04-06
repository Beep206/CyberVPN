use std::{
    collections::{HashMap, VecDeque},
    net::SocketAddr,
    path::Path,
    time::{Duration, Instant},
};

use axum::{
    extract::State,
    routing::{get, post},
    Json, Router,
};
use chrono::Utc;
use helix_runtime::{spawn_client, ClientConfig, ClientHandle, StreamTarget, TransportRoute};
use tokio::{
    io::{AsyncReadExt, AsyncWriteExt},
    net::{tcp::OwnedReadHalf, TcpListener, TcpStream},
    sync::{Notify, RwLock},
};

use crate::engine::{
    error::AppError,
    helix::config::{
        HelixSidecarBenchActionReport, HelixSidecarConfig, HelixSidecarHealth,
        HelixSidecarTelemetry, HelixStreamTelemetrySample,
    },
};

const SOCKS_VERSION: u8 = 0x05;
const SOCKS_CMD_CONNECT: u8 = 0x01;
const SOCKS_ATYP_IPV4: u8 = 0x01;
const SOCKS_ATYP_DOMAIN: u8 = 0x03;
const SOCKS_ATYP_IPV6: u8 = 0x04;
const SOCKS_REP_SUCCEEDED: u8 = 0x00;
const SOCKS_REP_GENERAL_FAILURE: u8 = 0x01;
const SOCKS_REP_COMMAND_NOT_SUPPORTED: u8 = 0x07;
const LOCAL_PROXY_BUFFER_SIZE: usize = 64 * 1024;
const RECENT_RTT_SAMPLES_LIMIT: usize = 20;
const RECENT_STREAM_TELEMETRY_LIMIT: usize = 32;
const CLIENT_READY_POLL_INTERVAL: Duration = Duration::from_millis(10);
const FAILOVER_MONITOR_INTERVAL: Duration = Duration::from_millis(250);
const STANDBY_MAINTENANCE_INTERVAL: Duration = Duration::from_millis(300);
const STREAM_RECONNECT_GRACE: Duration = Duration::from_secs(3);
const SIDECAR_CONNECT_TIMEOUT_CEILING: Duration = Duration::from_secs(4);
const SIDECAR_RECONNECT_DELAY: Duration = Duration::from_millis(250);
const STANDBY_SCORE_HYSTERESIS: i32 = 35;
const STANDBY_CONTINUITY_HEDGE: i32 = 80;

#[derive(Debug, Clone)]
struct ActiveSidecarClient {
    handle: ClientHandle,
    route: TransportRoute,
    probe_latency_ms: Option<u32>,
    score: i32,
}

#[derive(Debug, Clone)]
struct RouteSelection {
    route: TransportRoute,
    probe_latency_ms: Option<u32>,
    score: i32,
}

#[derive(Debug, Clone, Default)]
struct RouteQualityRecord {
    last_probe_latency_ms: Option<u32>,
    last_ping_rtt_ms: Option<u32>,
    successful_activations: u32,
    failed_activations: u32,
    failover_count: u32,
    healthy_observations: u32,
    consecutive_failures: u32,
    total_bytes_sent: u64,
    total_bytes_received: u64,
    last_observed_bytes_sent: u64,
    last_observed_bytes_received: u64,
    continuity_grace_entries: u32,
    successful_continuity_recovers: u32,
    successful_cross_route_recovers: u32,
    failed_continuity_recovers: u32,
    last_continuity_recovery_ms: Option<u32>,
    last_cross_route_recovery_ms: Option<u32>,
    last_score: Option<i32>,
    quarantined_until: Option<Instant>,
    last_failure_at: Option<Instant>,
}

type RouteQualityBook = std::sync::Arc<RwLock<HashMap<String, RouteQualityRecord>>>;
type SidecarClientSlot = std::sync::Arc<RwLock<Option<ActiveSidecarClient>>>;
type StandbyWakeSignal = std::sync::Arc<Notify>;
type ContinuityGraceState = std::sync::Arc<RwLock<Option<ContinuityGraceWindow>>>;

#[derive(Debug, Clone)]
struct ActiveStreamTelemetry {
    stream_id: u64,
    target_authority: String,
    opened_at: chrono::DateTime<Utc>,
    bytes_sent: u64,
    bytes_received: u64,
    peak_frame_queue_depth: u32,
    peak_inbound_queue_depth: u32,
}

#[derive(Debug, Default)]
struct SidecarPerfBook {
    recent_rtt_ms: VecDeque<u32>,
    active_streams: HashMap<u64, ActiveStreamTelemetry>,
    recent_streams: VecDeque<HelixStreamTelemetrySample>,
}

type SidecarPerfState = std::sync::Arc<RwLock<SidecarPerfBook>>;

#[derive(Debug, Clone)]
struct SidecarState {
    config: HelixSidecarConfig,
    started_at: chrono::DateTime<Utc>,
    active_client: std::sync::Arc<RwLock<ActiveSidecarClient>>,
    standby_client: SidecarClientSlot,
    standby_wake_signal: StandbyWakeSignal,
    continuity_grace: ContinuityGraceState,
    route_quality: RouteQualityBook,
    perf: SidecarPerfState,
}

#[derive(Debug, Clone)]
struct ContinuityGraceWindow {
    route_endpoint_ref: String,
    started_at: tokio::time::Instant,
    grace_budget: Duration,
}

fn route_policy_penalty(policy_tag: &str) -> i32 {
    let normalized = policy_tag.to_ascii_lowercase();
    if normalized.contains("primary") {
        -30
    } else if normalized.contains("preferred") || normalized.contains("stable") {
        -15
    } else if normalized.contains("fallback") {
        20
    } else if normalized.contains("backup") {
        35
    } else if normalized.contains("canary") {
        10
    } else {
        0
    }
}

fn failure_penalty_decay_basis_points(record: &RouteQualityRecord) -> i32 {
    let Some(last_failure_at) = record.last_failure_at else {
        return 100;
    };
    let Some(age) = Instant::now().checked_duration_since(last_failure_at) else {
        return 100;
    };

    if age >= Duration::from_secs(90) {
        10
    } else if age >= Duration::from_secs(60) {
        20
    } else if age >= Duration::from_secs(30) {
        35
    } else if age >= Duration::from_secs(15) {
        55
    } else if age >= Duration::from_secs(5) {
        75
    } else {
        100
    }
}

fn apply_decay_basis_points(value: i32, basis_points: i32) -> i32 {
    value.saturating_mul(basis_points).saturating_div(100)
}

fn continuity_recovery_attempts(record: &RouteQualityRecord) -> u32 {
    record.continuity_grace_entries.max(
        record
            .successful_continuity_recovers
            .saturating_add(record.failed_continuity_recovers),
    )
}

fn continuity_efficiency_basis_points(record: &RouteQualityRecord) -> i32 {
    let attempts = continuity_recovery_attempts(record);
    if attempts == 0 {
        return 0;
    }

    i32::try_from(
        record
            .successful_continuity_recovers
            .saturating_mul(100)
            .saturating_div(attempts),
    )
    .unwrap_or_default()
}

fn continuity_efficiency_adjustment(record: &RouteQualityRecord) -> (i32, i32) {
    let attempts = continuity_recovery_attempts(record);
    if attempts < 3 {
        return (0, 0);
    }

    let efficiency_basis_points = continuity_efficiency_basis_points(record);
    let bonus = efficiency_basis_points.saturating_sub(55).saturating_mul(2);
    let penalty = 65_i32
        .saturating_sub(efficiency_basis_points)
        .max(0)
        .saturating_mul(3);

    (bonus, penalty)
}

fn continuity_trust_score(record: Option<&RouteQualityRecord>) -> i32 {
    let Some(record) = record else {
        return 0;
    };

    let (efficiency_bonus, efficiency_penalty) = continuity_efficiency_adjustment(record);

    i32::try_from(record.successful_continuity_recovers.min(8))
        .unwrap_or(8)
        .saturating_mul(22)
        .saturating_add(
            i32::try_from(record.healthy_observations.min(24))
                .unwrap_or(24)
                .saturating_mul(3),
        )
        .saturating_add(
            i32::try_from(record.successful_activations.min(8))
                .unwrap_or(8)
                .saturating_mul(8),
        )
        .saturating_add(
            i32::try_from(record.successful_cross_route_recovers.min(6))
                .unwrap_or(6)
                .saturating_mul(26),
        )
        .saturating_add(
            record
                .last_cross_route_recovery_ms
                .map(|latency_ms| {
                    let normalized = 900_u32.saturating_sub(latency_ms.min(900)) / 45;
                    i32::try_from(normalized).unwrap_or_default()
                })
                .unwrap_or_default(),
        )
        .saturating_add(efficiency_bonus)
        .saturating_sub(
            i32::try_from(record.failed_continuity_recovers.min(8))
                .unwrap_or(8)
                .saturating_mul(18),
        )
        .saturating_sub(
            i32::try_from(record.consecutive_failures.min(8))
                .unwrap_or(8)
                .saturating_mul(20),
        )
        .saturating_sub(efficiency_penalty)
}

fn should_replace_ready_standby(
    existing_endpoint_ref: &str,
    existing_score: i32,
    candidate: &RouteSelection,
    quality_snapshot: &HashMap<String, RouteQualityRecord>,
) -> bool {
    if existing_endpoint_ref == candidate.route.endpoint_ref {
        return false;
    }

    let score_advantage = existing_score.saturating_sub(candidate.score);
    if score_advantage <= 0 {
        return false;
    }
    if score_advantage < STANDBY_SCORE_HYSTERESIS {
        return false;
    }

    let existing_trust = continuity_trust_score(quality_snapshot.get(existing_endpoint_ref));
    let candidate_trust =
        continuity_trust_score(quality_snapshot.get(&candidate.route.endpoint_ref));
    if existing_trust > candidate_trust && score_advantage < STANDBY_CONTINUITY_HEDGE {
        return false;
    }

    true
}

fn compute_route_score(
    route: &crate::engine::helix::config::HelixManifestRoute,
    probe_latency_ms: u32,
    record: Option<&RouteQualityRecord>,
) -> i32 {
    let probe_penalty = i32::try_from(probe_latency_ms).unwrap_or(i32::MAX / 4);
    let preference_penalty = route.preference.max(0).saturating_mul(3);
    let policy_penalty = route_policy_penalty(route.policy_tag.as_str());

    let (
        rtt_penalty,
        failure_penalty,
        stability_bonus,
        historical_probe_penalty,
        continuity_bonus,
        continuity_penalty,
        continuity_efficiency_penalty,
        quarantine_penalty,
        continuity_efficiency_bonus,
    ) = if let Some(record) = record {
        let (continuity_efficiency_bonus, continuity_efficiency_penalty) =
            continuity_efficiency_adjustment(record);
        let failure_decay_basis_points = failure_penalty_decay_basis_points(record);
        let rtt_penalty = record
            .last_ping_rtt_ms
            .map(|rtt_ms| i32::try_from(rtt_ms / 2).unwrap_or(i32::MAX / 8))
            .unwrap_or_default();
        let failure_penalty = apply_decay_basis_points(
            i32::try_from(record.consecutive_failures.min(8))
                .unwrap_or(8)
                .saturating_mul(180)
                + i32::try_from(record.failed_activations.min(8))
                    .unwrap_or(8)
                    .saturating_mul(50)
                + i32::try_from(record.failover_count.min(8))
                    .unwrap_or(8)
                    .saturating_mul(70),
            failure_decay_basis_points,
        );
        let throughput_bonus = if record.total_bytes_received + record.total_bytes_sent >= 1_048_576
        {
            24
        } else if record.total_bytes_received + record.total_bytes_sent >= 131_072 {
            12
        } else {
            0
        };
        let stability_bonus = i32::try_from(record.successful_activations.min(8))
            .unwrap_or(8)
            .saturating_mul(14)
            + i32::try_from(record.healthy_observations.min(24))
                .unwrap_or(24)
                .saturating_mul(5)
            + throughput_bonus;
        let historical_probe_penalty = record
            .last_probe_latency_ms
            .map(|latency_ms| i32::try_from(latency_ms / 4).unwrap_or(i32::MAX / 8))
            .unwrap_or_default();
        let continuity_bonus = i32::try_from(record.successful_continuity_recovers.min(8))
            .unwrap_or(8)
            .saturating_mul(18)
            + i32::try_from(record.successful_cross_route_recovers.min(6))
                .unwrap_or(6)
                .saturating_mul(24)
            + record
                .last_continuity_recovery_ms
                .map(|latency_ms| {
                    let normalized = 900_u32.saturating_sub(latency_ms.min(900)) / 30;
                    i32::try_from(normalized).unwrap_or_default()
                })
                .unwrap_or_default()
            + record
                .last_cross_route_recovery_ms
                .map(|latency_ms| {
                    let normalized = 1_200_u32.saturating_sub(latency_ms.min(1_200)) / 40;
                    i32::try_from(normalized).unwrap_or_default()
                })
                .unwrap_or_default();
        let failed_conversion_penalty = apply_decay_basis_points(
            i32::try_from(record.failed_continuity_recovers.min(8))
                .unwrap_or(8)
                .saturating_mul(32),
            failure_decay_basis_points,
        );
        let continuity_conversion_penalty = apply_decay_basis_points(
            i32::try_from(
                record
                    .continuity_grace_entries
                    .saturating_sub(record.successful_continuity_recovers)
                    .min(8),
            )
            .unwrap_or(8)
            .saturating_mul(12),
            failure_decay_basis_points,
        );
        let quarantine_penalty = record
            .quarantined_until
            .and_then(|until| until.checked_duration_since(Instant::now()))
            .map(|remaining| {
                let remaining_ms = i32::try_from(remaining.as_millis().min(6_000)).unwrap_or(6_000);
                10_000 + remaining_ms.saturating_div(2)
            })
            .unwrap_or_default();

        (
            rtt_penalty,
            failure_penalty,
            stability_bonus,
            historical_probe_penalty,
            continuity_bonus,
            failed_conversion_penalty + continuity_conversion_penalty,
            continuity_efficiency_penalty,
            quarantine_penalty,
            continuity_efficiency_bonus,
        )
    } else {
        (0, 0, 0, 0, 0, 0, 0, 0, 0)
    };

    ((probe_penalty
        + preference_penalty
        + policy_penalty
        + rtt_penalty
        + failure_penalty
        + historical_probe_penalty
        + continuity_penalty
        + continuity_efficiency_penalty
        + quarantine_penalty)
        - stability_bonus
        - continuity_bonus
        - continuity_efficiency_bonus)
        .max(0)
}

fn continuity_grace_budget(record: Option<&RouteQualityRecord>) -> Duration {
    let mut budget_ms: i32 = 1_200;

    if let Some(record) = record {
        let failure_decay_basis_points = failure_penalty_decay_basis_points(record);
        budget_ms = budget_ms
            .saturating_add(
                i32::try_from(record.successful_continuity_recovers.min(6))
                    .unwrap_or(6)
                    .saturating_mul(220),
            )
            .saturating_add(
                i32::try_from(record.healthy_observations.min(12))
                    .unwrap_or(12)
                    .saturating_mul(20),
            )
            .saturating_sub(apply_decay_basis_points(
                i32::try_from(record.consecutive_failures.min(6))
                    .unwrap_or(6)
                    .saturating_mul(180),
                failure_decay_basis_points,
            ))
            .saturating_sub(apply_decay_basis_points(
                i32::try_from(record.failed_activations.min(8))
                    .unwrap_or(8)
                    .saturating_mul(60),
                failure_decay_basis_points,
            ))
            .saturating_sub(apply_decay_basis_points(
                i32::try_from(record.failed_continuity_recovers.min(6))
                    .unwrap_or(6)
                    .saturating_mul(220),
                failure_decay_basis_points,
            ));
    }

    Duration::from_millis(u64::try_from(budget_ms.clamp(700, 3_000)).unwrap_or(1_200))
}

fn route_quarantine_duration(record: &RouteQualityRecord) -> Duration {
    let duration_ms = 900_u64
        .saturating_add(u64::from(record.failed_continuity_recovers.min(8)).saturating_mul(450))
        .saturating_add(u64::from(record.consecutive_failures.min(8)).saturating_mul(250))
        .saturating_add(u64::from(record.failed_activations.min(8)).saturating_mul(120))
        .clamp(800, 8_000);

    Duration::from_millis(duration_ms)
}

async fn record_successful_activation(
    route_quality: &RouteQualityBook,
    route: &TransportRoute,
    probe_latency_ms: Option<u32>,
    score: i32,
) {
    let mut quality = route_quality.write().await;
    let entry = quality.entry(route.endpoint_ref.clone()).or_default();
    entry.last_probe_latency_ms = probe_latency_ms;
    entry.successful_activations = entry.successful_activations.saturating_add(1);
    entry.consecutive_failures = 0;
    entry.last_score = Some(score);
    entry.last_observed_bytes_sent = 0;
    entry.last_observed_bytes_received = 0;
    entry.quarantined_until = None;
}

async fn record_continuity_grace_started(
    route_quality: &RouteQualityBook,
    route: &TransportRoute,
) -> RouteQualityRecord {
    let mut quality = route_quality.write().await;
    let entry = quality.entry(route.endpoint_ref.clone()).or_default();
    entry.continuity_grace_entries = entry.continuity_grace_entries.saturating_add(1);
    entry.clone()
}

async fn record_successful_continuity_recovery(
    route_quality: &RouteQualityBook,
    route: &TransportRoute,
    recovery_latency_ms: u32,
) -> RouteQualityRecord {
    let mut quality = route_quality.write().await;
    let entry = quality.entry(route.endpoint_ref.clone()).or_default();
    entry.successful_continuity_recovers = entry.successful_continuity_recovers.saturating_add(1);
    entry.failed_continuity_recovers = entry.failed_continuity_recovers.saturating_sub(1);
    entry.last_continuity_recovery_ms = Some(recovery_latency_ms);
    entry.consecutive_failures = 0;
    entry.quarantined_until = None;
    entry.clone()
}

async fn record_successful_cross_route_recovery(
    route_quality: &RouteQualityBook,
    route: &TransportRoute,
    recovery_latency_ms: u32,
) -> RouteQualityRecord {
    let mut quality = route_quality.write().await;
    let entry = quality.entry(route.endpoint_ref.clone()).or_default();
    entry.successful_cross_route_recovers = entry.successful_cross_route_recovers.saturating_add(1);
    entry.last_cross_route_recovery_ms = Some(recovery_latency_ms);
    entry.consecutive_failures = 0;
    entry.quarantined_until = None;
    entry.last_failure_at = None;
    entry.clone()
}

async fn record_failed_continuity_recovery(
    route_quality: &RouteQualityBook,
    route: &TransportRoute,
) -> RouteQualityRecord {
    let mut quality = route_quality.write().await;
    let entry = quality.entry(route.endpoint_ref.clone()).or_default();
    entry.failed_continuity_recovers = entry.failed_continuity_recovers.saturating_add(1);
    entry.quarantined_until = Some(Instant::now() + route_quarantine_duration(entry));
    entry.last_failure_at = Some(Instant::now());
    entry.clone()
}

async fn record_quality_observation(
    route_quality: &RouteQualityBook,
    route: &TransportRoute,
    probe_latency_ms: Option<u32>,
    snapshot: &helix_runtime::SessionSnapshot,
    score: i32,
) -> RouteQualityRecord {
    let mut quality = route_quality.write().await;
    let entry = quality.entry(route.endpoint_ref.clone()).or_default();

    entry.last_probe_latency_ms = probe_latency_ms;
    entry.last_ping_rtt_ms = snapshot.last_ping_rtt_ms;
    entry.healthy_observations = entry.healthy_observations.saturating_add(1);
    entry.consecutive_failures = 0;
    entry.quarantined_until = None;
    entry.total_bytes_sent = entry.total_bytes_sent.saturating_add(
        snapshot
            .bytes_sent
            .saturating_sub(entry.last_observed_bytes_sent),
    );
    entry.total_bytes_received = entry.total_bytes_received.saturating_add(
        snapshot
            .bytes_received
            .saturating_sub(entry.last_observed_bytes_received),
    );
    entry.last_observed_bytes_sent = snapshot.bytes_sent;
    entry.last_observed_bytes_received = snapshot.bytes_received;
    entry.last_score = Some(score);

    entry.clone()
}

async fn record_route_failure(
    route_quality: &RouteQualityBook,
    route: &TransportRoute,
    probe_latency_ms: Option<u32>,
    snapshot: Option<&helix_runtime::SessionSnapshot>,
    score: i32,
) -> RouteQualityRecord {
    let mut quality = route_quality.write().await;
    let entry = quality.entry(route.endpoint_ref.clone()).or_default();

    entry.last_probe_latency_ms = probe_latency_ms;
    entry.failed_activations = entry.failed_activations.saturating_add(1);
    entry.failover_count = entry.failover_count.saturating_add(1);
    entry.consecutive_failures = entry.consecutive_failures.saturating_add(1);
    if let Some(snapshot) = snapshot {
        entry.last_ping_rtt_ms = snapshot.last_ping_rtt_ms;
        entry.total_bytes_sent = entry.total_bytes_sent.saturating_add(
            snapshot
                .bytes_sent
                .saturating_sub(entry.last_observed_bytes_sent),
        );
        entry.total_bytes_received = entry.total_bytes_received.saturating_add(
            snapshot
                .bytes_received
                .saturating_sub(entry.last_observed_bytes_received),
        );
        entry.last_observed_bytes_sent = snapshot.bytes_sent;
        entry.last_observed_bytes_received = snapshot.bytes_received;
    }
    entry.last_score = Some(score);
    entry.quarantined_until = Some(Instant::now() + route_quarantine_duration(entry));
    entry.last_failure_at = Some(Instant::now());

    entry.clone()
}

async fn record_failed_activation(
    route_quality: &RouteQualityBook,
    route: &TransportRoute,
    probe_latency_ms: Option<u32>,
    score: i32,
) -> RouteQualityRecord {
    let mut quality = route_quality.write().await;
    let entry = quality.entry(route.endpoint_ref.clone()).or_default();

    entry.last_probe_latency_ms = probe_latency_ms;
    entry.failed_activations = entry.failed_activations.saturating_add(1);
    entry.consecutive_failures = entry.consecutive_failures.saturating_add(1);
    entry.last_score = Some(score);
    entry.quarantined_until = Some(Instant::now() + route_quarantine_duration(entry));
    entry.last_failure_at = Some(Instant::now());

    entry.clone()
}

async fn record_rtt_sample(perf: &SidecarPerfState, rtt_ms: Option<u32>) {
    let Some(rtt_ms) = rtt_ms else {
        return;
    };

    let mut guard = perf.write().await;
    guard.recent_rtt_ms.push_back(rtt_ms);
    while guard.recent_rtt_ms.len() > RECENT_RTT_SAMPLES_LIMIT {
        guard.recent_rtt_ms.pop_front();
    }
}

async fn record_stream_open(perf: &SidecarPerfState, stream_id: u64, target_authority: String) {
    let mut guard = perf.write().await;
    guard.active_streams.insert(
        stream_id,
        ActiveStreamTelemetry {
            stream_id,
            target_authority,
            opened_at: Utc::now(),
            bytes_sent: 0,
            bytes_received: 0,
            peak_frame_queue_depth: 0,
            peak_inbound_queue_depth: 0,
        },
    );
}

async fn record_stream_uplink_sample(
    perf: &SidecarPerfState,
    stream_id: u64,
    bytes_sent: usize,
    frame_queue_depth: Option<u32>,
) {
    let mut guard = perf.write().await;
    let Some(entry) = guard.active_streams.get_mut(&stream_id) else {
        return;
    };

    entry.bytes_sent = entry
        .bytes_sent
        .saturating_add(u64::try_from(bytes_sent).unwrap_or(u64::MAX));
    if let Some(frame_queue_depth) = frame_queue_depth {
        entry.peak_frame_queue_depth = entry.peak_frame_queue_depth.max(frame_queue_depth);
    }
}

async fn record_stream_downlink_sample(
    perf: &SidecarPerfState,
    stream_id: u64,
    bytes_received: usize,
    frame_queue_depth: Option<u32>,
) {
    let mut guard = perf.write().await;
    let Some(entry) = guard.active_streams.get_mut(&stream_id) else {
        return;
    };

    entry.bytes_received = entry
        .bytes_received
        .saturating_add(u64::try_from(bytes_received).unwrap_or(u64::MAX));
    if let Some(frame_queue_depth) = frame_queue_depth {
        entry.peak_inbound_queue_depth = entry.peak_inbound_queue_depth.max(frame_queue_depth);
    }
}

async fn finalize_stream_telemetry(
    perf: &SidecarPerfState,
    stream_id: u64,
    close_reason: impl Into<String>,
) {
    let close_reason = close_reason.into();
    let mut guard = perf.write().await;
    let Some(entry) = guard.active_streams.remove(&stream_id) else {
        return;
    };

    let closed_at = Utc::now();
    let duration_ms = closed_at
        .signed_duration_since(entry.opened_at)
        .to_std()
        .ok()
        .and_then(|duration| u64::try_from(duration.as_millis()).ok());

    guard.recent_streams.push_back(HelixStreamTelemetrySample {
        stream_id: entry.stream_id,
        target_authority: entry.target_authority,
        opened_at: entry.opened_at.to_rfc3339(),
        closed_at: Some(closed_at.to_rfc3339()),
        duration_ms,
        bytes_sent: entry.bytes_sent,
        bytes_received: entry.bytes_received,
        peak_frame_queue_depth: entry.peak_frame_queue_depth,
        peak_inbound_queue_depth: entry.peak_inbound_queue_depth,
        close_reason: Some(close_reason),
    });
    while guard.recent_streams.len() > RECENT_STREAM_TELEMETRY_LIMIT {
        guard.recent_streams.pop_front();
    }
}

async fn sidecar_telemetry(state: &SidecarState) -> HelixSidecarTelemetry {
    let health = sidecar_health(state).await;
    let (recent_rtt_ms, recent_streams) = {
        let perf = state.perf.read().await;
        (
            perf.recent_rtt_ms.iter().copied().collect(),
            perf.recent_streams.iter().cloned().rev().collect(),
        )
    };
    HelixSidecarTelemetry {
        schema_version: "1.0".to_string(),
        collected_at: Utc::now().to_rfc3339(),
        health,
        recent_rtt_ms,
        recent_streams,
    }
}

pub fn run_from_current_args() -> Result<bool, AppError> {
    let args = std::env::args().collect::<Vec<_>>();
    let Some(config_path) = parse_config_path(&args) else {
        return Ok(false);
    };

    let config_contents = std::fs::read_to_string(config_path)?;
    let config = match serde_json::from_str::<HelixSidecarConfig>(&config_contents) {
        Ok(config) => config,
        Err(_) => return Ok(false),
    };

    let runtime = tokio::runtime::Builder::new_multi_thread()
        .enable_all()
        .build()
        .map_err(|error| AppError::System(format!("Failed to build sidecar runtime: {error}")))?;
    runtime.block_on(async move { run_sidecar(config).await })?;

    Ok(true)
}

fn parse_config_path(args: &[String]) -> Option<&Path> {
    for window in args.windows(3) {
        if window.first()? == "run" && window.get(1)? == "-c" {
            return Some(Path::new(window.get(2)?));
        }
    }

    None
}

async fn run_sidecar(config: HelixSidecarConfig) -> Result<(), AppError> {
    let route_quality = std::sync::Arc::new(RwLock::new(HashMap::new()));
    let perf = std::sync::Arc::new(RwLock::new(SidecarPerfBook::default()));
    let selection = select_client_route(&config, &route_quality).await?;
    let selected_route_endpoint_ref = selection.route.endpoint_ref.clone();
    let client_handle = spawn_sidecar_client(&config, selection.route.clone());
    wait_until_client_ready(&client_handle, config.startup_timeout_seconds).await?;
    record_successful_activation(
        &route_quality,
        &selection.route,
        selection.probe_latency_ms,
        selection.score,
    )
    .await;
    let active_client = std::sync::Arc::new(RwLock::new(ActiveSidecarClient {
        handle: client_handle,
        route: selection.route,
        probe_latency_ms: selection.probe_latency_ms,
        score: selection.score,
    }));
    let standby_client: SidecarClientSlot = std::sync::Arc::new(RwLock::new(None));
    let standby_wake_signal: StandbyWakeSignal = std::sync::Arc::new(Notify::new());
    let continuity_grace: ContinuityGraceState = std::sync::Arc::new(RwLock::new(None));

    let health_bind_addr = config
        .health_bind_addr
        .parse::<SocketAddr>()
        .map_err(|error| AppError::System(format!("Invalid sidecar health bind addr: {error}")))?;
    let proxy_bind_addr = config
        .proxy_bind_addr
        .parse::<SocketAddr>()
        .map_err(|error| AppError::System(format!("Invalid sidecar proxy bind addr: {error}")))?;

    let health_listener = TcpListener::bind(health_bind_addr).await?;
    let proxy_listener = TcpListener::bind(proxy_bind_addr).await?;

    println!(
        "Helix sidecar starting profile={} route={} latency_ms={:?} health={} proxy={}",
        config.transport_profile_id,
        selected_route_endpoint_ref,
        selection.probe_latency_ms,
        config.health_url,
        config.proxy_url
    );

    let failover_config = config.clone();
    let state = SidecarState {
        config: config.clone(),
        started_at: Utc::now(),
        active_client: active_client.clone(),
        standby_client: standby_client.clone(),
        standby_wake_signal: standby_wake_signal.clone(),
        continuity_grace: continuity_grace.clone(),
        route_quality: route_quality.clone(),
        perf: perf.clone(),
    };
    let router = Router::new()
        .route("/healthz", get(healthz))
        .route("/readyz", get(readyz))
        .route("/telemetry", get(telemetry))
        .route("/bench/failover", post(bench_failover))
        .route("/bench/reconnect", post(bench_reconnect))
        .with_state(state);

    let proxy_task = tokio::spawn(run_proxy_accept_loop_with_active_client(
        proxy_listener,
        active_client.clone(),
        perf.clone(),
    ));
    let standby_task = tokio::spawn(run_standby_route_maintainer(
        config.clone(),
        active_client.clone(),
        standby_client.clone(),
        standby_wake_signal.clone(),
        route_quality.clone(),
    ));
    let failover_task = tokio::spawn(run_failover_monitor(
        failover_config,
        active_client.clone(),
        standby_client.clone(),
        standby_wake_signal.clone(),
        continuity_grace,
        route_quality,
        perf,
    ));

    axum::serve(health_listener, router)
        .with_graceful_shutdown(wait_for_shutdown())
        .await
        .map_err(AppError::Io)?;

    proxy_task.abort();
    standby_task.abort();
    failover_task.abort();
    let active_handle = { active_client.read().await.handle.clone() };
    let standby_handle = {
        standby_client
            .write()
            .await
            .take()
            .map(|client| client.handle)
    };
    active_handle.shutdown().await;
    if let Some(standby_handle) = standby_handle {
        standby_handle.shutdown().await;
    }
    Ok(())
}

fn spawn_sidecar_client(config: &HelixSidecarConfig, route: TransportRoute) -> ClientHandle {
    let connect_timeout =
        Duration::from_secs(u64::try_from(config.startup_timeout_seconds.max(3)).unwrap_or(3))
            .min(SIDECAR_CONNECT_TIMEOUT_CEILING);

    spawn_client(ClientConfig {
        manifest_id: config.manifest_id.clone(),
        transport_profile_id: config.transport_profile_id.clone(),
        profile_family: config.profile_family.clone(),
        profile_version: config.profile_version,
        policy_version: config.policy_version,
        session_mode: config.session_mode.clone(),
        token: config.credentials.token.clone(),
        route,
        connect_timeout,
        heartbeat_interval: Duration::from_secs(5),
        reconnect_delay: SIDECAR_RECONNECT_DELAY,
    })
}

async fn wait_until_client_ready(
    client_handle: &ClientHandle,
    startup_timeout_seconds: i32,
) -> Result<(), AppError> {
    let deadline = tokio::time::Instant::now()
        + Duration::from_secs(u64::try_from(startup_timeout_seconds.max(1)).unwrap_or(1));

    loop {
        let snapshot = client_handle.snapshot().await;
        if snapshot.ready {
            return Ok(());
        }

        if tokio::time::Instant::now() >= deadline {
            return Err(AppError::System(format!(
                "Helix client did not become ready before {} seconds (status={}, connected={}, route={:?}, remote_addr={:?}, last_error={})",
                startup_timeout_seconds,
                snapshot.status,
                snapshot.connected,
                snapshot.active_route,
                snapshot.remote_addr,
                snapshot
                    .last_error
                    .unwrap_or_else(|| "none".to_string()),
            )));
        }

        tokio::time::sleep(CLIENT_READY_POLL_INTERVAL).await;
    }
}

async fn run_failover_monitor(
    config: HelixSidecarConfig,
    active_client: std::sync::Arc<RwLock<ActiveSidecarClient>>,
    standby_client: SidecarClientSlot,
    standby_wake_signal: StandbyWakeSignal,
    continuity_grace: ContinuityGraceState,
    route_quality: RouteQualityBook,
    perf: SidecarPerfState,
) {
    let mut interval = tokio::time::interval(FAILOVER_MONITOR_INTERVAL);
    interval.set_missed_tick_behavior(tokio::time::MissedTickBehavior::Skip);
    let unhealthy_threshold = u32::try_from(config.runtime_unhealthy_threshold.max(1)).unwrap_or(1);
    let mut consecutive_unhealthy_checks = 0_u32;
    let mut continuity_grace_window: Option<ContinuityGraceWindow> = None;

    loop {
        interval.tick().await;

        let client_handle = { active_client.read().await.handle.clone() };
        let snapshot = client_handle.snapshot().await;
        if snapshot.ready && snapshot.status == "ready" {
            record_rtt_sample(&perf, snapshot.last_ping_rtt_ms).await;
            let (route, probe_latency_ms) = {
                let active = active_client.read().await;
                (active.route.clone(), active.probe_latency_ms)
            };
            if let Some(grace) = continuity_grace_window.take() {
                if grace.route_endpoint_ref == route.endpoint_ref {
                    let recovery_latency_ms =
                        u32::try_from(grace.started_at.elapsed().as_millis()).unwrap_or(u32::MAX);
                    let _ = record_successful_continuity_recovery(
                        &route_quality,
                        &route,
                        recovery_latency_ms,
                    )
                    .await;
                }
            }
            *continuity_grace.write().await = None;
            let route_record_snapshot =
                { route_quality.read().await.get(&route.endpoint_ref).cloned() };
            let score = compute_route_score(
                &crate::engine::helix::config::HelixManifestRoute {
                    endpoint_ref: route.endpoint_ref.clone(),
                    dial_host: route.dial_host.clone(),
                    dial_port: route.dial_port,
                    server_name: route.server_name.clone(),
                    preference: route.preference,
                    policy_tag: route.policy_tag.clone(),
                },
                probe_latency_ms.unwrap_or_default(),
                route_record_snapshot.as_ref(),
            );
            let _ = record_quality_observation(
                &route_quality,
                &route,
                probe_latency_ms,
                &snapshot,
                score,
            )
            .await;
            active_client.write().await.score = score;
            consecutive_unhealthy_checks = 0;
            continuity_grace_window = None;
            *continuity_grace.write().await = None;
            continue;
        }

        consecutive_unhealthy_checks = consecutive_unhealthy_checks.saturating_add(1);
        if consecutive_unhealthy_checks < unhealthy_threshold {
            continue;
        }
        consecutive_unhealthy_checks = 0;

        let (route, probe_latency_ms, score) = {
            let active = active_client.read().await;
            (active.route.clone(), active.probe_latency_ms, active.score)
        };
        let route_record_snapshot =
            { route_quality.read().await.get(&route.endpoint_ref).cloned() };

        let continuity_grace_expired = if should_preserve_route_continuity(&snapshot) {
            let hold_same_route = match continuity_grace_window.as_ref() {
                Some(grace) if grace.route_endpoint_ref == route.endpoint_ref => {
                    grace.started_at.elapsed() < grace.grace_budget
                }
                _ => {
                    let grace = ContinuityGraceWindow {
                        route_endpoint_ref: route.endpoint_ref.clone(),
                        started_at: tokio::time::Instant::now(),
                        grace_budget: continuity_grace_budget(route_record_snapshot.as_ref()),
                    };
                    let _ = record_continuity_grace_started(&route_quality, &route).await;
                    continuity_grace_window = Some(grace.clone());
                    *continuity_grace.write().await = Some(grace);
                    true
                }
            };

            if hold_same_route {
                continue;
            }
            true
        } else {
            false
        };
        if continuity_grace_expired {
            let _ = record_failed_continuity_recovery(&route_quality, &route).await;
        }
        continuity_grace_window = None;
        *continuity_grace.write().await = None;

        let _ = record_route_failure(
            &route_quality,
            &route,
            probe_latency_ms,
            Some(&snapshot),
            score,
        )
        .await;

        match attempt_route_failover(&config, &active_client, &standby_client, &route_quality).await
        {
            Ok(true) => standby_wake_signal.notify_one(),
            Ok(false) => {}
            Err(error) => eprintln!("Helix route failover failed: {error}"),
        }
    }
}

fn should_preserve_route_continuity(snapshot: &helix_runtime::SessionSnapshot) -> bool {
    snapshot.active_streams > 0 || snapshot.pending_open_streams > 0
}

async fn run_standby_route_maintainer(
    config: HelixSidecarConfig,
    active_client: std::sync::Arc<RwLock<ActiveSidecarClient>>,
    standby_client: SidecarClientSlot,
    standby_wake_signal: StandbyWakeSignal,
    route_quality: RouteQualityBook,
) {
    let mut interval = tokio::time::interval(STANDBY_MAINTENANCE_INTERVAL);
    interval.set_missed_tick_behavior(tokio::time::MissedTickBehavior::Skip);

    loop {
        tokio::select! {
            _ = interval.tick() => {}
            _ = standby_wake_signal.notified() => {}
        }

        let active_route_endpoint_ref = { active_client.read().await.route.endpoint_ref.clone() };
        let quality_snapshot = route_quality.read().await.clone();
        let selection = match select_client_route_excluding(
            &config,
            &route_quality,
            Some(active_route_endpoint_ref.as_str()),
        )
        .await
        {
            Ok(selection) => selection,
            Err(_) => {
                let stale_handle = {
                    standby_client
                        .write()
                        .await
                        .take()
                        .map(|client| client.handle)
                };
                if let Some(stale_handle) = stale_handle {
                    stale_handle.shutdown().await;
                }
                continue;
            }
        };

        let existing_standby = { standby_client.read().await.clone() };
        if let Some(existing_standby) = existing_standby {
            if existing_standby.route.endpoint_ref == active_route_endpoint_ref {
                let stale_handle = {
                    standby_client
                        .write()
                        .await
                        .take()
                        .map(|client| client.handle)
                };
                if let Some(stale_handle) = stale_handle {
                    stale_handle.shutdown().await;
                }
                continue;
            }

            if existing_standby.route.endpoint_ref == selection.route.endpoint_ref {
                let snapshot = existing_standby.handle.snapshot().await;
                if snapshot.ready {
                    let mut guard = standby_client.write().await;
                    if let Some(standby_client) = guard.as_mut() {
                        if standby_client.route.endpoint_ref == selection.route.endpoint_ref {
                            standby_client.probe_latency_ms = selection.probe_latency_ms;
                            standby_client.score = selection.score;
                        }
                    }
                    continue;
                }
            }

            let snapshot = existing_standby.handle.snapshot().await;
            if snapshot.ready
                && !should_replace_ready_standby(
                    existing_standby.route.endpoint_ref.as_str(),
                    existing_standby.score,
                    &selection,
                    &quality_snapshot,
                )
            {
                continue;
            }
        }

        let next_handle = spawn_sidecar_client(&config, selection.route.clone());
        if let Err(error) =
            wait_until_client_ready(&next_handle, config.startup_timeout_seconds).await
        {
            let _ = record_failed_activation(
                &route_quality,
                &selection.route,
                selection.probe_latency_ms,
                selection.score,
            )
            .await;
            eprintln!(
                "Helix standby route warm-up failed for {}: {error}",
                selection.route.endpoint_ref
            );
            next_handle.shutdown().await;
            continue;
        }

        let previous_handle = {
            let mut guard = standby_client.write().await;
            let previous_handle = guard.take().map(|client| client.handle);
            *guard = Some(ActiveSidecarClient {
                handle: next_handle,
                route: selection.route,
                probe_latency_ms: selection.probe_latency_ms,
                score: selection.score,
            });
            previous_handle
        };

        if let Some(previous_handle) = previous_handle {
            previous_handle.shutdown().await;
        }
    }
}

async fn attempt_route_failover(
    config: &HelixSidecarConfig,
    active_client: &std::sync::Arc<RwLock<ActiveSidecarClient>>,
    standby_client: &SidecarClientSlot,
    route_quality: &RouteQualityBook,
) -> Result<bool, AppError> {
    let failover_started = Instant::now();
    let (current_route, current_handle) = {
        let active = active_client.read().await;
        (active.route.clone(), active.handle.clone())
    };
    let current_endpoint_ref = current_route.endpoint_ref.clone();
    let continuity_sensitive = should_preserve_route_continuity(&current_handle.snapshot().await);
    let promoted_standby = { standby_client.read().await.clone() };
    if let Some(promoted_standby) = promoted_standby {
        let snapshot = promoted_standby.handle.snapshot().await;
        if snapshot.ready && promoted_standby.route.endpoint_ref != current_endpoint_ref {
            let promoted_route = promoted_standby.route.clone();
            record_successful_activation(
                route_quality,
                &promoted_route,
                promoted_standby.probe_latency_ms,
                promoted_standby.score,
            )
            .await;

            let previous_handle = {
                let mut standby_guard = standby_client.write().await;
                let Some(promoted_standby) = standby_guard.take() else {
                    return Ok(false);
                };
                if promoted_standby.route.endpoint_ref == current_endpoint_ref {
                    let stale_handle = promoted_standby.handle;
                    drop(standby_guard);
                    stale_handle.shutdown().await;
                    return Ok(false);
                }

                let mut active_guard = active_client.write().await;
                println!(
                    "Helix route failover promoting warm standby {} -> {}",
                    active_guard.route.endpoint_ref, promoted_standby.route.endpoint_ref
                );
                let previous_handle = active_guard.handle.clone();
                *active_guard = promoted_standby;
                previous_handle
            };
            let recovery_latency_ms =
                u32::try_from(failover_started.elapsed().as_millis()).unwrap_or(u32::MAX);
            if continuity_sensitive {
                let _ = record_successful_cross_route_recovery(
                    route_quality,
                    &promoted_route,
                    recovery_latency_ms,
                )
                .await;
            }

            previous_handle.shutdown().await;
            return Ok(true);
        }

        if !snapshot.ready || promoted_standby.route.endpoint_ref == current_endpoint_ref {
            let stale_handle = {
                standby_client
                    .write()
                    .await
                    .take()
                    .map(|client| client.handle)
            };
            if let Some(stale_handle) = stale_handle {
                stale_handle.shutdown().await;
            }
        }
    }

    let selection = match select_client_route_excluding(
        config,
        route_quality,
        Some(current_endpoint_ref.as_str()),
    )
    .await
    {
        Ok(route) => route,
        Err(_) => return Ok(false),
    };

    let next_route = selection.route.clone();
    let next_handle = spawn_sidecar_client(config, next_route.clone());
    if let Err(error) = wait_until_client_ready(&next_handle, config.startup_timeout_seconds).await
    {
        let _ = record_failed_activation(
            route_quality,
            &next_route,
            selection.probe_latency_ms,
            selection.score,
        )
        .await;
        next_handle.shutdown().await;
        return Err(error);
    }
    record_successful_activation(
        route_quality,
        &next_route,
        selection.probe_latency_ms,
        selection.score,
    )
    .await;

    let previous_handle = {
        let mut guard = active_client.write().await;
        if guard.route.endpoint_ref == selection.route.endpoint_ref {
            next_handle.shutdown().await;
            return Ok(false);
        }

        println!(
            "Helix route failover switching {} -> {}",
            guard.route.endpoint_ref, next_route.endpoint_ref
        );

        let previous_handle = guard.handle.clone();
        *guard = ActiveSidecarClient {
            handle: next_handle,
            route: next_route.clone(),
            probe_latency_ms: selection.probe_latency_ms,
            score: selection.score,
        };
        previous_handle
    };
    let recovery_latency_ms =
        u32::try_from(failover_started.elapsed().as_millis()).unwrap_or(u32::MAX);
    if continuity_sensitive {
        let _ =
            record_successful_cross_route_recovery(route_quality, &next_route, recovery_latency_ms)
                .await;
    }

    previous_handle.shutdown().await;
    Ok(true)
}

async fn attempt_active_route_reconnect(
    config: &HelixSidecarConfig,
    active_client: &std::sync::Arc<RwLock<ActiveSidecarClient>>,
    route_quality: &RouteQualityBook,
) -> Result<bool, AppError> {
    let (current_route, current_probe_latency_ms, current_score) = {
        let active = active_client.read().await;
        (active.route.clone(), active.probe_latency_ms, active.score)
    };

    let next_handle = spawn_sidecar_client(config, current_route.clone());
    if let Err(error) = wait_until_client_ready(&next_handle, config.startup_timeout_seconds).await
    {
        let _ = record_failed_activation(
            route_quality,
            &current_route,
            current_probe_latency_ms,
            current_score,
        )
        .await;
        next_handle.shutdown().await;
        return Err(error);
    }

    record_successful_activation(
        route_quality,
        &current_route,
        current_probe_latency_ms,
        current_score,
    )
    .await;

    let previous_handle = {
        let mut guard = active_client.write().await;
        let previous_handle = guard.handle.clone();
        guard.handle = next_handle;
        previous_handle
    };

    previous_handle.shutdown().await;
    Ok(true)
}

async fn select_client_route(
    config: &HelixSidecarConfig,
    route_quality: &RouteQualityBook,
) -> Result<RouteSelection, AppError> {
    select_client_route_excluding(config, route_quality, None).await
}

async fn select_client_route_excluding(
    config: &HelixSidecarConfig,
    route_quality: &RouteQualityBook,
    excluded_endpoint_ref: Option<&str>,
) -> Result<RouteSelection, AppError> {
    if config.routes.is_empty() {
        return Err(AppError::System(
            "Helix sidecar requires at least one route".to_string(),
        ));
    }

    let probe_timeout_ms = u64::try_from(config.startup_timeout_seconds.max(1))
        .unwrap_or(1)
        .saturating_mul(250)
        .clamp(400, 1_500);
    let probe_timeout = Duration::from_millis(probe_timeout_ms);
    let quality_snapshot = route_quality.read().await.clone();
    let mut best_route: Option<RouteSelection> = None;
    let mut probe_failures = Vec::new();

    let mut candidate_routes = config.routes.clone();
    candidate_routes.sort_by_key(|route| route.preference);

    for route in candidate_routes {
        if excluded_endpoint_ref.is_some_and(|excluded| excluded == route.endpoint_ref.as_str()) {
            continue;
        }

        match probe_manifest_route(&route, probe_timeout).await {
            Ok(latency_ms) => {
                let score = compute_route_score(
                    &route,
                    latency_ms,
                    quality_snapshot.get(&route.endpoint_ref),
                );
                let selection = RouteSelection {
                    route: TransportRoute {
                        endpoint_ref: route.endpoint_ref.clone(),
                        dial_host: route.dial_host.clone(),
                        dial_port: route.dial_port,
                        server_name: route.server_name.clone(),
                        preference: route.preference,
                        policy_tag: route.policy_tag.clone(),
                    },
                    probe_latency_ms: Some(latency_ms),
                    score,
                };

                let should_replace = best_route
                    .as_ref()
                    .map(|best| {
                        score < best.score
                            || (score == best.score
                                && latency_ms < best.probe_latency_ms.unwrap_or(u32::MAX))
                            || (score == best.score
                                && latency_ms == best.probe_latency_ms.unwrap_or(u32::MAX)
                                && route.preference < best.route.preference)
                    })
                    .unwrap_or(true);

                if should_replace {
                    best_route = Some(selection);
                }
            }
            Err(error) => {
                probe_failures.push(format!("{}: {}", route.endpoint_ref, error));
            }
        }
    }

    if let Some(selection) = best_route {
        return Ok(selection);
    }

    Err(AppError::System(format!(
        "No Helix routes passed startup probing: {}",
        probe_failures.join("; ")
    )))
}

async fn probe_manifest_route(
    route: &crate::engine::helix::config::HelixManifestRoute,
    probe_timeout: Duration,
) -> Result<u32, AppError> {
    let started_at = Instant::now();
    let stream = tokio::time::timeout(
        probe_timeout,
        TcpStream::connect((route.dial_host.as_str(), route.dial_port)),
    )
    .await
    .map_err(|_| {
        AppError::System(format!(
            "probe timeout while dialing {}",
            route.endpoint_ref
        ))
    })?
    .map_err(|error| {
        AppError::System(format!(
            "probe connect failed for {}: {error}",
            route.endpoint_ref
        ))
    })?;
    let _ = stream.set_nodelay(true);
    drop(stream);

    Ok(u32::try_from(started_at.elapsed().as_millis()).unwrap_or(u32::MAX))
}

#[cfg(test)]
pub(crate) async fn run_proxy_accept_loop(
    listener: TcpListener,
    client_handle: ClientHandle,
) -> Result<(), AppError> {
    let active_client = std::sync::Arc::new(RwLock::new(ActiveSidecarClient {
        handle: client_handle,
        route: TransportRoute {
            endpoint_ref: "static-client".to_string(),
            dial_host: "127.0.0.1".to_string(),
            dial_port: 0,
            server_name: None,
            preference: 0,
            policy_tag: "static".to_string(),
        },
        probe_latency_ms: None,
        score: 0,
    }));
    run_proxy_accept_loop_with_active_client(
        listener,
        active_client,
        std::sync::Arc::new(RwLock::new(SidecarPerfBook::default())),
    )
    .await
}

async fn run_proxy_accept_loop_with_active_client(
    listener: TcpListener,
    active_client: std::sync::Arc<RwLock<ActiveSidecarClient>>,
    perf: SidecarPerfState,
) -> Result<(), AppError> {
    loop {
        let (stream, remote_addr) = listener.accept().await?;
        let client_handle = { active_client.read().await.handle.clone() };
        let perf = perf.clone();
        tokio::spawn(async move {
            if let Err(error) = handle_proxy_connection(stream, client_handle, perf).await {
                eprintln!("Helix proxy error from {remote_addr}: {error}");
            }
        });
    }
}

async fn handle_proxy_connection(
    mut stream: TcpStream,
    client_handle: ClientHandle,
    perf: SidecarPerfState,
) -> Result<(), AppError> {
    let _ = stream.set_nodelay(true);
    let target = negotiate_socks5_connect(&mut stream).await?;
    let mut remote_stream = match client_handle.open_stream(target.clone()).await {
        Ok(stream) => stream,
        Err(error) => {
            send_socks5_reply(&mut stream, SOCKS_REP_GENERAL_FAILURE).await?;
            return Err(AppError::from(error));
        }
    };
    record_stream_open(&perf, remote_stream.stream_id(), target.authority()).await;

    send_socks5_reply(&mut stream, SOCKS_REP_SUCCEEDED).await?;

    let remote_writer = remote_stream.writer();
    let (local_reader, mut local_writer) = stream.into_split();
    let uplink = tokio::spawn({
        let perf = perf.clone();
        let client_handle = client_handle.clone();
        let stream_id = remote_stream.stream_id();
        async move {
            forward_local_to_remote(local_reader, remote_writer, client_handle, perf, stream_id)
                .await
        }
    });

    while let Some(data) = remote_stream.recv().await {
        let stream_id = remote_stream.stream_id();
        let frame_queue_depth = client_handle.snapshot().await.frame_queue_depth;
        record_stream_downlink_sample(&perf, stream_id, data.len(), Some(frame_queue_depth)).await;
        local_writer.write_all(&data).await?;
    }

    let _ = local_writer.shutdown().await;
    let _ = remote_stream.close("remote-closed").await;
    finalize_stream_telemetry(&perf, remote_stream.stream_id(), "remote-closed").await;

    match uplink.await {
        Ok(result) => {
            if let Err(error) = result {
                finalize_stream_telemetry(
                    &perf,
                    remote_stream.stream_id(),
                    format!("uplink-error: {error}"),
                )
                .await;
                return Err(error);
            }
        }
        Err(error) => {
            finalize_stream_telemetry(
                &perf,
                remote_stream.stream_id(),
                format!("uplink-task-failed: {error}"),
            )
            .await;
            return Err(AppError::System(format!(
                "Helix uplink task failed: {error}"
            )));
        }
    }

    Ok(())
}

async fn forward_local_to_remote(
    mut local_reader: OwnedReadHalf,
    remote_writer: helix_runtime::ClientStreamWriter,
    client_handle: ClientHandle,
    perf: SidecarPerfState,
    stream_id: u64,
) -> Result<(), AppError> {
    let mut buffer = vec![0_u8; LOCAL_PROXY_BUFFER_SIZE];
    loop {
        let read = local_reader.read(&mut buffer).await?;
        if read == 0 {
            let _ = remote_writer.finish().await;
            finalize_stream_telemetry(&perf, stream_id, "local-finish").await;
            return Ok(());
        }

        send_with_reconnect_grace(&remote_writer, &client_handle, buffer[..read].to_vec()).await?;
        let frame_queue_depth = client_handle.snapshot().await.frame_queue_depth;
        record_stream_uplink_sample(&perf, stream_id, read, Some(frame_queue_depth)).await;
    }
}

async fn send_with_reconnect_grace(
    remote_writer: &helix_runtime::ClientStreamWriter,
    client_handle: &ClientHandle,
    data: Vec<u8>,
) -> Result<(), AppError> {
    let deadline = tokio::time::Instant::now() + STREAM_RECONNECT_GRACE;

    loop {
        let last_error = match remote_writer.send(data.clone()).await {
            Ok(()) => return Ok(()),
            Err(error) => error.to_string(),
        };

        if tokio::time::Instant::now() >= deadline {
            return Err(AppError::System(format!(
                "Helix uplink failed after reconnect grace window: {}",
                last_error,
            )));
        }

        tokio::time::sleep(CLIENT_READY_POLL_INTERVAL).await;
        let snapshot = client_handle.snapshot().await;
        if snapshot.ready && snapshot.connected {
            continue;
        }
    }
}

async fn negotiate_socks5_connect(stream: &mut TcpStream) -> Result<StreamTarget, AppError> {
    let mut greeting = [0_u8; 2];
    stream.read_exact(&mut greeting).await?;
    if greeting[0] != SOCKS_VERSION {
        return Err(AppError::System(format!(
            "unsupported SOCKS version: {}",
            greeting[0]
        )));
    }

    let method_count = usize::from(greeting[1]);
    let mut methods = vec![0_u8; method_count];
    stream.read_exact(&mut methods).await?;
    if !methods.contains(&0x00) {
        stream.write_all(&[SOCKS_VERSION, 0xFF]).await?;
        return Err(AppError::System(
            "SOCKS5 client does not support no-auth method".to_string(),
        ));
    }

    stream.write_all(&[SOCKS_VERSION, 0x00]).await?;

    let mut header = [0_u8; 4];
    stream.read_exact(&mut header).await?;
    if header[0] != SOCKS_VERSION {
        return Err(AppError::System(
            "invalid SOCKS5 request version".to_string(),
        ));
    }

    if header[1] != SOCKS_CMD_CONNECT {
        send_socks5_reply(stream, SOCKS_REP_COMMAND_NOT_SUPPORTED).await?;
        return Err(AppError::System(
            "SOCKS5 request command is not supported".to_string(),
        ));
    }

    let host = match header[3] {
        SOCKS_ATYP_IPV4 => {
            let mut octets = [0_u8; 4];
            stream.read_exact(&mut octets).await?;
            std::net::Ipv4Addr::from(octets).to_string()
        }
        SOCKS_ATYP_DOMAIN => {
            let mut len = [0_u8; 1];
            stream.read_exact(&mut len).await?;
            let mut domain = vec![0_u8; usize::from(len[0])];
            stream.read_exact(&mut domain).await?;
            String::from_utf8(domain).map_err(|error| {
                AppError::System(format!("invalid SOCKS5 domain target: {error}"))
            })?
        }
        SOCKS_ATYP_IPV6 => {
            let mut octets = [0_u8; 16];
            stream.read_exact(&mut octets).await?;
            std::net::Ipv6Addr::from(octets).to_string()
        }
        atyp => {
            send_socks5_reply(stream, SOCKS_REP_GENERAL_FAILURE).await?;
            return Err(AppError::System(format!(
                "unsupported SOCKS5 address type: {atyp}"
            )));
        }
    };

    let mut port_bytes = [0_u8; 2];
    stream.read_exact(&mut port_bytes).await?;
    let port = u16::from_be_bytes(port_bytes);

    Ok(StreamTarget::new(host, port))
}

async fn send_socks5_reply(stream: &mut TcpStream, code: u8) -> Result<(), AppError> {
    stream
        .write_all(&[SOCKS_VERSION, code, 0x00, SOCKS_ATYP_IPV4, 0, 0, 0, 0, 0, 0])
        .await?;
    Ok(())
}

async fn healthz(State(state): State<SidecarState>) -> Json<HelixSidecarHealth> {
    Json(sidecar_health(&state).await)
}

async fn readyz(State(state): State<SidecarState>) -> Json<HelixSidecarHealth> {
    Json(sidecar_health(&state).await)
}

async fn telemetry(State(state): State<SidecarState>) -> Json<HelixSidecarTelemetry> {
    Json(sidecar_telemetry(&state).await)
}

async fn bench_failover(State(state): State<SidecarState>) -> Json<HelixSidecarBenchActionReport> {
    Json(run_bench_action(&state, "failover").await)
}

async fn bench_reconnect(State(state): State<SidecarState>) -> Json<HelixSidecarBenchActionReport> {
    Json(run_bench_action(&state, "reconnect").await)
}

async fn sidecar_health(state: &SidecarState) -> HelixSidecarHealth {
    let _uptime = Utc::now() - state.started_at;
    let (
        client_handle,
        active_route_endpoint_ref,
        active_route_probe_latency_ms,
        active_route_score,
    ) = {
        let active_client = state.active_client.read().await;
        (
            active_client.handle.clone(),
            active_client.route.endpoint_ref.clone(),
            active_client.probe_latency_ms,
            active_client.score,
        )
    };
    let (
        standby_route_endpoint_ref,
        standby_route_probe_latency_ms,
        standby_route_score,
        standby_ready,
    ) = {
        let standby_client = state.standby_client.read().await.clone();
        match standby_client {
            Some(standby_client) => {
                let snapshot = standby_client.handle.snapshot().await;
                (
                    Some(standby_client.route.endpoint_ref),
                    standby_client.probe_latency_ms,
                    Some(standby_client.score),
                    snapshot.ready,
                )
            }
            None => (None, None, None, false),
        }
    };
    let snapshot = client_handle.snapshot().await;
    let route_quality = state
        .route_quality
        .read()
        .await
        .get(&active_route_endpoint_ref)
        .cloned()
        .unwrap_or_default();
    let active_route_quarantine_remaining_ms = route_quality
        .quarantined_until
        .and_then(|until| until.checked_duration_since(Instant::now()))
        .map(|remaining| i32::try_from(remaining.as_millis()).unwrap_or(i32::MAX));
    let (continuity_grace_route_endpoint_ref, continuity_grace_remaining_ms) = {
        let continuity_grace = state.continuity_grace.read().await.clone();
        match continuity_grace {
            Some(grace) => {
                let remaining = grace
                    .grace_budget
                    .saturating_sub(grace.started_at.elapsed());
                (
                    Some(grace.route_endpoint_ref),
                    Some(i32::try_from(remaining.as_millis()).unwrap_or(i32::MAX)),
                )
            }
            None => (None, None),
        }
    };

    HelixSidecarHealth {
        schema_version: "1.0".to_string(),
        status: if snapshot.ready {
            "ready".to_string()
        } else if snapshot.connected {
            "connecting".to_string()
        } else {
            "degraded".to_string()
        },
        ready: snapshot.ready,
        connected: snapshot.connected,
        manifest_id: state.config.manifest_id.clone(),
        rollout_id: state.config.rollout_id.clone(),
        transport_profile_id: state.config.transport_profile_id.clone(),
        route_count: state.config.routes.len(),
        proxy_url: state.config.proxy_url.clone(),
        session_id: snapshot.session_id,
        remote_addr: snapshot.remote_addr,
        active_route_endpoint_ref: Some(active_route_endpoint_ref),
        active_route_probe_latency_ms,
        active_route_score: Some(active_route_score),
        standby_route_endpoint_ref,
        standby_route_probe_latency_ms,
        standby_route_score,
        standby_ready,
        continuity_grace_active: continuity_grace_route_endpoint_ref.is_some(),
        continuity_grace_route_endpoint_ref,
        continuity_grace_remaining_ms,
        active_route_continuity_grace_entries: route_quality.continuity_grace_entries,
        active_route_successful_continuity_recovers: route_quality.successful_continuity_recovers,
        active_route_failed_continuity_recovers: route_quality.failed_continuity_recovers,
        active_route_last_continuity_recovery_ms: route_quality
            .last_continuity_recovery_ms
            .map(|value| i32::try_from(value).unwrap_or(i32::MAX)),
        active_route_successful_cross_route_recovers: route_quality.successful_cross_route_recovers,
        active_route_last_cross_route_recovery_ms: route_quality
            .last_cross_route_recovery_ms
            .map(|value| i32::try_from(value).unwrap_or(i32::MAX)),
        active_route_quarantined: active_route_quarantine_remaining_ms.is_some(),
        active_route_quarantine_remaining_ms,
        active_route_successful_activations: route_quality.successful_activations,
        active_route_failed_activations: route_quality.failed_activations,
        active_route_failover_count: route_quality.failover_count,
        active_route_healthy_observations: route_quality.healthy_observations,
        last_ping_rtt_ms: snapshot.last_ping_rtt_ms,
        active_streams: snapshot.active_streams,
        pending_open_streams: snapshot.pending_open_streams,
        max_concurrent_streams: snapshot.max_concurrent_streams,
        frame_queue_depth: snapshot.frame_queue_depth,
        frame_queue_peak: snapshot.frame_queue_peak,
        bytes_sent: snapshot.bytes_sent,
        bytes_received: snapshot.bytes_received,
    }
}

async fn run_bench_action(state: &SidecarState, action: &str) -> HelixSidecarBenchActionReport {
    let started_at = Instant::now();
    let (route_before, continuity_sensitive) = {
        let active = state.active_client.read().await;
        let snapshot = active.handle.snapshot().await;
        (
            Some(active.route.endpoint_ref.clone()),
            should_preserve_route_continuity(&snapshot),
        )
    };

    let result = match action {
        "failover" => attempt_route_failover(
            &state.config,
            &state.active_client,
            &state.standby_client,
            &state.route_quality,
        )
        .await
        .map(|switched| {
            if switched {
                state.standby_wake_signal.notify_one();
            }
            if switched {
                "failover completed".to_string()
            } else {
                "no alternate healthy route available".to_string()
            }
        }),
        "reconnect" => attempt_active_route_reconnect(
            &state.config,
            &state.active_client,
            &state.route_quality,
        )
        .await
        .map(|_| {
            state.standby_wake_signal.notify_one();
            "route reconnect completed".to_string()
        }),
        _ => Err(AppError::System(format!(
            "Unsupported Helix bench action: {action}"
        ))),
    };

    let route_after = Some(state.active_client.read().await.route.endpoint_ref.clone());
    let recovery_latency_ms = i32::try_from(started_at.elapsed().as_millis()).unwrap_or(i32::MAX);

    match result {
        Ok(message) => {
            if !continuity_sensitive {
                let recovery_latency_u32 =
                    u32::try_from(recovery_latency_ms.max(0)).unwrap_or(u32::MAX);
                if let Some(route_after_ref) = route_after.as_deref() {
                    let route = {
                        let active = state.active_client.read().await;
                        (active.route.endpoint_ref == route_after_ref).then(|| active.route.clone())
                    };

                    if let Some(route) = route {
                        let _ = record_successful_continuity_recovery(
                            &state.route_quality,
                            &route,
                            recovery_latency_u32,
                        )
                        .await;

                        if route_before.as_deref() != route_after.as_deref() {
                            let _ = record_successful_cross_route_recovery(
                                &state.route_quality,
                                &route,
                                recovery_latency_u32,
                            )
                            .await;
                        }
                    }
                }
            }

            HelixSidecarBenchActionReport {
                schema_version: "1.0".to_string(),
                action: action.to_string(),
                success: true,
                route_before,
                route_after,
                recovery_latency_ms: Some(recovery_latency_ms),
                message: Some(message),
            }
        }
        Err(error) => HelixSidecarBenchActionReport {
            schema_version: "1.0".to_string(),
            action: action.to_string(),
            success: false,
            route_before,
            route_after,
            recovery_latency_ms: Some(recovery_latency_ms),
            message: Some(error.to_string()),
        },
    }
}

async fn wait_for_shutdown() {
    let _ = tokio::signal::ctrl_c().await;
}

#[cfg(test)]
mod tests {
    use std::{
        collections::HashMap,
        net::SocketAddr,
        time::{Duration, Instant},
    };

    use chrono::Utc;
    use helix_runtime::{
        spawn_client, spawn_server, ClientConfig, ClientHandle, ServerConfig, StreamTarget,
        TransportRoute,
    };
    use tokio::{
        io::{AsyncReadExt, AsyncWriteExt},
        net::{TcpListener, TcpStream},
        sync::{Notify, RwLock},
    };

    use super::{
        attempt_route_failover, compute_route_score, continuity_grace_budget,
        continuity_trust_score, handle_proxy_connection, parse_config_path, probe_manifest_route,
        record_successful_activation, run_failover_monitor, select_client_route,
        should_replace_ready_standby, sidecar_health, spawn_sidecar_client, ActiveSidecarClient,
        ContinuityGraceWindow, RouteQualityRecord, RouteSelection, SidecarPerfBook, SidecarState,
        SOCKS_VERSION,
    };
    use crate::engine::helix::config::{
        HelixManifestCompatibilityWindow, HelixManifestCredentials, HelixManifestIntegrity,
        HelixManifestObservability, HelixSidecarConfig, HelixSignature,
    };
    fn sample_sidecar_config(server_addr: SocketAddr) -> HelixSidecarConfig {
        HelixSidecarConfig {
            schema_version: "1.0".to_string(),
            manifest_id: "manifest-1".to_string(),
            manifest_version_id: "manifest-version-1".to_string(),
            rollout_id: "rollout-1".to_string(),
            health_bind_addr: "127.0.0.1:38991".to_string(),
            health_url: "http://127.0.0.1:38991/healthz".to_string(),
            proxy_bind_addr: "127.0.0.1:38990".to_string(),
            proxy_url: "socks5://127.0.0.1:38990".to_string(),
            transport_family: "helix".to_string(),
            session_mode: "hybrid".to_string(),
            transport_profile_id: "ptp-lab-edge-v2".to_string(),
            profile_family: "edge-hybrid".to_string(),
            profile_version: 2,
            policy_version: 4,
            compatibility_window: HelixManifestCompatibilityWindow {
                profile_family: "edge-hybrid".to_string(),
                min_transport_profile_version: 1,
                max_transport_profile_version: 4,
            },
            fallback_core: "sing-box".to_string(),
            required_capabilities: vec!["protocol.v1".to_string()],
            startup_timeout_seconds: 15,
            runtime_unhealthy_threshold: 3,
            credentials: HelixManifestCredentials {
                key_id: "sig-key-1".to_string(),
                token: "shared-session-token".to_string(),
            },
            routes: vec![crate::engine::helix::config::HelixManifestRoute {
                endpoint_ref: "node-lab-01".to_string(),
                dial_host: server_addr.ip().to_string(),
                dial_port: server_addr.port(),
                server_name: Some("node-lab-01.local".to_string()),
                preference: 10,
                policy_tag: "primary".to_string(),
            }],
            observability: HelixManifestObservability {
                trace_id: "trace-1".to_string(),
                metrics_namespace: "helix".to_string(),
            },
            integrity: HelixManifestIntegrity {
                manifest_hash: "sha256:1234".to_string(),
                signature: HelixSignature {
                    alg: "ed25519".to_string(),
                    key_id: "sig-key-1".to_string(),
                    sig: "signed".to_string(),
                },
            },
        }
    }

    async fn spawn_upstream_echo_server() -> SocketAddr {
        let upstream_listener = TcpListener::bind("127.0.0.1:0")
            .await
            .expect("bind upstream echo");
        let upstream_addr = upstream_listener.local_addr().expect("upstream addr");
        tokio::spawn(async move {
            loop {
                let Ok((mut stream, _)) = upstream_listener.accept().await else {
                    break;
                };
                tokio::spawn(async move {
                    let mut buffer = [0_u8; 4096];
                    loop {
                        match stream.read(&mut buffer).await {
                            Ok(0) => break,
                            Ok(read) => {
                                if stream.write_all(&buffer[..read]).await.is_err() {
                                    break;
                                }
                            }
                            Err(_) => break,
                        }
                    }
                });
            }
        });
        upstream_addr
    }

    #[test]
    fn recognizes_sidecar_cli_shape() {
        let args = vec![
            "desktop-client".to_string(),
            "run".to_string(),
            "-c".to_string(),
            "runtime.json".to_string(),
        ];

        let path = parse_config_path(&args).expect("runtime config path");
        assert_eq!(path.to_string_lossy(), "runtime.json");
    }

    #[test]
    fn recognizes_sidecar_cli_shape_with_extra_arguments() {
        let args = vec![
            "desktop-client".to_string(),
            "--flag".to_string(),
            "run".to_string(),
            "-c".to_string(),
            "runtime.json".to_string(),
            "--another-flag".to_string(),
        ];

        let path = parse_config_path(&args).expect("runtime config path");
        assert_eq!(path.to_string_lossy(), "runtime.json");
    }

    #[test]
    fn ignores_non_sidecar_cli_shape() {
        let args = vec!["desktop-client".to_string()];
        assert!(parse_config_path(&args).is_none());
    }

    #[tokio::test]
    async fn selects_reachable_route_when_first_candidate_fails_probe() {
        let reachable_listener = TcpListener::bind("127.0.0.1:0")
            .await
            .expect("bind reachable listener");
        let reachable_addr = reachable_listener.local_addr().expect("reachable addr");

        let unavailable_listener = TcpListener::bind("127.0.0.1:0")
            .await
            .expect("bind unavailable listener");
        let unavailable_port = unavailable_listener
            .local_addr()
            .expect("unavailable addr")
            .port();
        drop(unavailable_listener);

        let mut config = sample_sidecar_config(reachable_addr);
        config.routes = vec![
            crate::engine::helix::config::HelixManifestRoute {
                endpoint_ref: "node-unavailable".to_string(),
                dial_host: "127.0.0.1".to_string(),
                dial_port: unavailable_port,
                server_name: Some("node-unavailable.local".to_string()),
                preference: 5,
                policy_tag: "primary".to_string(),
            },
            crate::engine::helix::config::HelixManifestRoute {
                endpoint_ref: "node-reachable".to_string(),
                dial_host: reachable_addr.ip().to_string(),
                dial_port: reachable_addr.port(),
                server_name: Some("node-reachable.local".to_string()),
                preference: 10,
                policy_tag: "fallback".to_string(),
            },
        ];

        let route_quality = std::sync::Arc::new(RwLock::new(HashMap::new()));
        let selection = select_client_route(&config, &route_quality)
            .await
            .expect("route");
        assert_eq!(selection.route.endpoint_ref, "node-reachable");
        assert!(selection.probe_latency_ms.is_some());
    }

    #[tokio::test]
    async fn probe_manifest_route_returns_latency_for_reachable_candidate() {
        let listener = TcpListener::bind("127.0.0.1:0")
            .await
            .expect("bind probe listener");
        let addr = listener.local_addr().expect("probe addr");

        let latency_ms = probe_manifest_route(
            &crate::engine::helix::config::HelixManifestRoute {
                endpoint_ref: "node-probe".to_string(),
                dial_host: addr.ip().to_string(),
                dial_port: addr.port(),
                server_name: Some("node-probe.local".to_string()),
                preference: 10,
                policy_tag: "primary".to_string(),
            },
            Duration::from_secs(1),
        )
        .await
        .expect("probe latency");

        assert!(latency_ms <= 1_000);
    }

    #[tokio::test]
    async fn policy_scoring_prefers_primary_tag_when_quality_history_is_equal() {
        let listener = TcpListener::bind("127.0.0.1:0")
            .await
            .expect("bind shared listener");
        let addr = listener.local_addr().expect("listener addr");

        let mut config = sample_sidecar_config(addr);
        config.routes = vec![
            crate::engine::helix::config::HelixManifestRoute {
                endpoint_ref: "node-primary".to_string(),
                dial_host: addr.ip().to_string(),
                dial_port: addr.port(),
                server_name: Some("node-primary.local".to_string()),
                preference: 10,
                policy_tag: "primary".to_string(),
            },
            crate::engine::helix::config::HelixManifestRoute {
                endpoint_ref: "node-fallback".to_string(),
                dial_host: addr.ip().to_string(),
                dial_port: addr.port(),
                server_name: Some("node-fallback.local".to_string()),
                preference: 10,
                policy_tag: "fallback".to_string(),
            },
        ];

        let route_quality = std::sync::Arc::new(RwLock::new(HashMap::new()));
        let selection = select_client_route(&config, &route_quality)
            .await
            .expect("route selection");

        assert_eq!(selection.route.endpoint_ref, "node-primary");
    }

    #[tokio::test]
    async fn policy_scoring_prefers_route_with_better_quality_history() {
        let listener = TcpListener::bind("127.0.0.1:0")
            .await
            .expect("bind shared listener");
        let addr = listener.local_addr().expect("listener addr");

        let mut config = sample_sidecar_config(addr);
        config.routes = vec![
            crate::engine::helix::config::HelixManifestRoute {
                endpoint_ref: "node-primary".to_string(),
                dial_host: addr.ip().to_string(),
                dial_port: addr.port(),
                server_name: Some("node-primary.local".to_string()),
                preference: 5,
                policy_tag: "primary".to_string(),
            },
            crate::engine::helix::config::HelixManifestRoute {
                endpoint_ref: "node-secondary".to_string(),
                dial_host: addr.ip().to_string(),
                dial_port: addr.port(),
                server_name: Some("node-secondary.local".to_string()),
                preference: 15,
                policy_tag: "fallback".to_string(),
            },
        ];

        let route_quality = std::sync::Arc::new(RwLock::new(HashMap::from([
            (
                "node-primary".to_string(),
                RouteQualityRecord {
                    last_probe_latency_ms: Some(4),
                    last_ping_rtt_ms: Some(35),
                    successful_activations: 0,
                    failed_activations: 3,
                    failover_count: 2,
                    healthy_observations: 1,
                    consecutive_failures: 3,
                    total_bytes_sent: 0,
                    total_bytes_received: 0,
                    last_observed_bytes_sent: 0,
                    last_observed_bytes_received: 0,
                    continuity_grace_entries: 0,
                    successful_continuity_recovers: 0,
                    successful_cross_route_recovers: 0,
                    failed_continuity_recovers: 3,
                    last_continuity_recovery_ms: None,
                    last_cross_route_recovery_ms: None,
                    last_score: Some(580),
                    quarantined_until: None,
                    last_failure_at: None,
                },
            ),
            (
                "node-secondary".to_string(),
                RouteQualityRecord {
                    last_probe_latency_ms: Some(6),
                    last_ping_rtt_ms: Some(8),
                    successful_activations: 4,
                    failed_activations: 0,
                    failover_count: 0,
                    healthy_observations: 16,
                    consecutive_failures: 0,
                    total_bytes_sent: 96_000,
                    total_bytes_received: 512_000,
                    last_observed_bytes_sent: 0,
                    last_observed_bytes_received: 0,
                    continuity_grace_entries: 2,
                    successful_continuity_recovers: 2,
                    successful_cross_route_recovers: 1,
                    failed_continuity_recovers: 0,
                    last_continuity_recovery_ms: Some(210),
                    last_cross_route_recovery_ms: Some(180),
                    last_score: Some(48),
                    quarantined_until: None,
                    last_failure_at: None,
                },
            ),
        ])));

        let selection = select_client_route(&config, &route_quality)
            .await
            .expect("route selection");

        assert_eq!(selection.route.endpoint_ref, "node-secondary");
    }

    #[test]
    fn continuity_grace_budget_shrinks_when_history_shows_failed_recovers() {
        let stable = RouteQualityRecord {
            healthy_observations: 10,
            successful_continuity_recovers: 3,
            ..RouteQualityRecord::default()
        };
        let degraded = RouteQualityRecord {
            healthy_observations: 2,
            failed_continuity_recovers: 4,
            failed_activations: 2,
            consecutive_failures: 2,
            ..RouteQualityRecord::default()
        };

        assert!(continuity_grace_budget(Some(&degraded)) < continuity_grace_budget(Some(&stable)));
    }

    #[test]
    fn continuity_grace_budget_recovers_when_failure_history_ages_out() {
        let recent_failures = RouteQualityRecord {
            healthy_observations: 6,
            successful_continuity_recovers: 2,
            failed_continuity_recovers: 3,
            failed_activations: 3,
            consecutive_failures: 2,
            last_failure_at: Some(std::time::Instant::now() - Duration::from_secs(2)),
            ..RouteQualityRecord::default()
        };
        let aged_failures = RouteQualityRecord {
            healthy_observations: 6,
            successful_continuity_recovers: 2,
            failed_continuity_recovers: 3,
            failed_activations: 3,
            consecutive_failures: 2,
            last_failure_at: Some(std::time::Instant::now() - Duration::from_secs(95)),
            ..RouteQualityRecord::default()
        };

        assert!(
            continuity_grace_budget(Some(&aged_failures))
                > continuity_grace_budget(Some(&recent_failures))
        );
    }

    #[tokio::test]
    async fn policy_scoring_penalizes_failed_continuity_history() {
        let listener = TcpListener::bind("127.0.0.1:0")
            .await
            .expect("bind shared listener");
        let addr = listener.local_addr().expect("listener addr");

        let mut config = sample_sidecar_config(addr);
        config.routes = vec![
            crate::engine::helix::config::HelixManifestRoute {
                endpoint_ref: "node-primary".to_string(),
                dial_host: addr.ip().to_string(),
                dial_port: addr.port(),
                server_name: Some("node-primary.local".to_string()),
                preference: 5,
                policy_tag: "primary".to_string(),
            },
            crate::engine::helix::config::HelixManifestRoute {
                endpoint_ref: "node-secondary".to_string(),
                dial_host: addr.ip().to_string(),
                dial_port: addr.port(),
                server_name: Some("node-secondary.local".to_string()),
                preference: 10,
                policy_tag: "fallback".to_string(),
            },
        ];

        let route_quality = std::sync::Arc::new(RwLock::new(HashMap::from([
            (
                "node-primary".to_string(),
                RouteQualityRecord {
                    last_probe_latency_ms: Some(3),
                    last_ping_rtt_ms: Some(8),
                    successful_activations: 3,
                    healthy_observations: 10,
                    continuity_grace_entries: 5,
                    successful_continuity_recovers: 1,
                    failed_continuity_recovers: 4,
                    last_score: Some(120),
                    ..RouteQualityRecord::default()
                },
            ),
            (
                "node-secondary".to_string(),
                RouteQualityRecord {
                    last_probe_latency_ms: Some(5),
                    last_ping_rtt_ms: Some(14),
                    successful_activations: 3,
                    healthy_observations: 8,
                    continuity_grace_entries: 2,
                    successful_continuity_recovers: 2,
                    failed_continuity_recovers: 0,
                    last_continuity_recovery_ms: Some(180),
                    last_score: Some(40),
                    ..RouteQualityRecord::default()
                },
            ),
        ])));

        let selection = select_client_route(&config, &route_quality)
            .await
            .expect("route selection");

        assert_eq!(selection.route.endpoint_ref, "node-secondary");
    }

    #[tokio::test]
    async fn policy_scoring_re_admits_route_after_failure_history_ages_out() {
        let listener = TcpListener::bind("127.0.0.1:0")
            .await
            .expect("bind shared listener");
        let addr = listener.local_addr().expect("listener addr");

        let mut config = sample_sidecar_config(addr);
        config.routes = vec![
            crate::engine::helix::config::HelixManifestRoute {
                endpoint_ref: "node-primary".to_string(),
                dial_host: addr.ip().to_string(),
                dial_port: addr.port(),
                server_name: Some("node-primary.local".to_string()),
                preference: 5,
                policy_tag: "primary".to_string(),
            },
            crate::engine::helix::config::HelixManifestRoute {
                endpoint_ref: "node-secondary".to_string(),
                dial_host: addr.ip().to_string(),
                dial_port: addr.port(),
                server_name: Some("node-secondary.local".to_string()),
                preference: 10,
                policy_tag: "fallback".to_string(),
            },
        ];

        let route_quality = std::sync::Arc::new(RwLock::new(HashMap::from([
            (
                "node-primary".to_string(),
                RouteQualityRecord {
                    last_probe_latency_ms: Some(8),
                    last_ping_rtt_ms: Some(10),
                    successful_activations: 7,
                    failed_activations: 4,
                    failover_count: 2,
                    healthy_observations: 20,
                    consecutive_failures: 3,
                    successful_continuity_recovers: 3,
                    failed_continuity_recovers: 2,
                    last_continuity_recovery_ms: Some(140),
                    last_failure_at: Some(std::time::Instant::now() - Duration::from_secs(95)),
                    ..RouteQualityRecord::default()
                },
            ),
            (
                "node-secondary".to_string(),
                RouteQualityRecord {
                    last_probe_latency_ms: Some(16),
                    last_ping_rtt_ms: Some(14),
                    successful_activations: 2,
                    healthy_observations: 6,
                    successful_continuity_recovers: 1,
                    last_continuity_recovery_ms: Some(240),
                    ..RouteQualityRecord::default()
                },
            ),
        ])));

        let selection = select_client_route(&config, &route_quality)
            .await
            .expect("route selection");

        assert_eq!(selection.route.endpoint_ref, "node-primary");
    }

    #[test]
    fn continuity_trust_prefers_route_with_cross_route_recovery_history() {
        let cross_route_trusted = RouteQualityRecord {
            healthy_observations: 6,
            successful_activations: 2,
            successful_continuity_recovers: 1,
            successful_cross_route_recovers: 2,
            last_cross_route_recovery_ms: Some(140),
            ..RouteQualityRecord::default()
        };
        let same_route_only = RouteQualityRecord {
            healthy_observations: 8,
            successful_activations: 3,
            successful_continuity_recovers: 1,
            ..RouteQualityRecord::default()
        };

        assert!(
            continuity_trust_score(Some(&cross_route_trusted))
                > continuity_trust_score(Some(&same_route_only))
        );
    }

    #[test]
    fn continuity_trust_prefers_higher_efficiency_when_raw_success_counts_are_similar() {
        let noisy_route = RouteQualityRecord {
            healthy_observations: 10,
            successful_activations: 4,
            continuity_grace_entries: 10,
            successful_continuity_recovers: 4,
            failed_continuity_recovers: 6,
            ..RouteQualityRecord::default()
        };
        let efficient_route = RouteQualityRecord {
            healthy_observations: 7,
            successful_activations: 3,
            continuity_grace_entries: 4,
            successful_continuity_recovers: 4,
            failed_continuity_recovers: 0,
            ..RouteQualityRecord::default()
        };

        assert!(
            continuity_trust_score(Some(&efficient_route))
                > continuity_trust_score(Some(&noisy_route))
        );
    }

    #[test]
    fn compute_route_score_penalizes_poor_continuity_efficiency() {
        let route = crate::engine::helix::config::HelixManifestRoute {
            endpoint_ref: "node-primary".to_string(),
            dial_host: "127.0.0.1".to_string(),
            dial_port: 9443,
            server_name: Some("node-primary.local".to_string()),
            preference: 5,
            policy_tag: "primary".to_string(),
        };
        let inefficient = RouteQualityRecord {
            last_probe_latency_ms: Some(6),
            last_ping_rtt_ms: Some(12),
            successful_activations: 4,
            healthy_observations: 12,
            continuity_grace_entries: 8,
            successful_continuity_recovers: 2,
            failed_continuity_recovers: 6,
            ..RouteQualityRecord::default()
        };
        let efficient = RouteQualityRecord {
            last_probe_latency_ms: Some(6),
            last_ping_rtt_ms: Some(12),
            successful_activations: 4,
            healthy_observations: 12,
            continuity_grace_entries: 4,
            successful_continuity_recovers: 4,
            failed_continuity_recovers: 0,
            ..RouteQualityRecord::default()
        };

        assert!(
            compute_route_score(&route, 8, Some(&efficient))
                < compute_route_score(&route, 8, Some(&inefficient))
        );
    }

    #[test]
    fn ready_standby_replacement_uses_score_hysteresis() {
        let quality_snapshot = HashMap::from([
            (
                "node-existing".to_string(),
                RouteQualityRecord {
                    healthy_observations: 12,
                    successful_continuity_recovers: 2,
                    successful_activations: 4,
                    ..RouteQualityRecord::default()
                },
            ),
            (
                "node-candidate".to_string(),
                RouteQualityRecord {
                    healthy_observations: 9,
                    successful_continuity_recovers: 1,
                    successful_activations: 3,
                    ..RouteQualityRecord::default()
                },
            ),
        ]);
        let candidate = RouteSelection {
            route: TransportRoute {
                endpoint_ref: "node-candidate".to_string(),
                dial_host: "127.0.0.1".to_string(),
                dial_port: 9444,
                server_name: Some("node-candidate.local".to_string()),
                preference: 8,
                policy_tag: "fallback".to_string(),
            },
            probe_latency_ms: Some(9),
            score: 92,
        };

        assert!(!should_replace_ready_standby(
            "node-existing",
            118,
            &candidate,
            &quality_snapshot,
        ));
    }

    #[test]
    fn ready_standby_replacement_respects_continuity_trust() {
        let quality_snapshot = HashMap::from([
            (
                "node-existing".to_string(),
                RouteQualityRecord {
                    healthy_observations: 18,
                    successful_continuity_recovers: 4,
                    successful_activations: 5,
                    ..RouteQualityRecord::default()
                },
            ),
            (
                "node-candidate".to_string(),
                RouteQualityRecord {
                    healthy_observations: 4,
                    successful_continuity_recovers: 0,
                    failed_continuity_recovers: 1,
                    successful_activations: 1,
                    ..RouteQualityRecord::default()
                },
            ),
        ]);
        let candidate = RouteSelection {
            route: TransportRoute {
                endpoint_ref: "node-candidate".to_string(),
                dial_host: "127.0.0.1".to_string(),
                dial_port: 9444,
                server_name: Some("node-candidate.local".to_string()),
                preference: 8,
                policy_tag: "fallback".to_string(),
            },
            probe_latency_ms: Some(8),
            score: 70,
        };

        assert!(!should_replace_ready_standby(
            "node-existing",
            128,
            &candidate,
            &quality_snapshot,
        ));
        assert!(should_replace_ready_standby(
            "node-existing",
            180,
            &candidate,
            &quality_snapshot,
        ));
    }

    #[tokio::test]
    async fn policy_scoring_deprioritizes_quarantined_route() {
        let listener = TcpListener::bind("127.0.0.1:0")
            .await
            .expect("bind shared listener");
        let addr = listener.local_addr().expect("listener addr");

        let mut config = sample_sidecar_config(addr);
        config.routes = vec![
            crate::engine::helix::config::HelixManifestRoute {
                endpoint_ref: "node-primary".to_string(),
                dial_host: addr.ip().to_string(),
                dial_port: addr.port(),
                server_name: Some("node-primary.local".to_string()),
                preference: 5,
                policy_tag: "primary".to_string(),
            },
            crate::engine::helix::config::HelixManifestRoute {
                endpoint_ref: "node-secondary".to_string(),
                dial_host: addr.ip().to_string(),
                dial_port: addr.port(),
                server_name: Some("node-secondary.local".to_string()),
                preference: 10,
                policy_tag: "fallback".to_string(),
            },
        ];

        let route_quality = std::sync::Arc::new(RwLock::new(HashMap::from([
            (
                "node-primary".to_string(),
                RouteQualityRecord {
                    last_probe_latency_ms: Some(2),
                    last_ping_rtt_ms: Some(6),
                    successful_activations: 5,
                    healthy_observations: 18,
                    successful_continuity_recovers: 3,
                    last_continuity_recovery_ms: Some(120),
                    quarantined_until: Some(std::time::Instant::now() + Duration::from_secs(5)),
                    ..RouteQualityRecord::default()
                },
            ),
            (
                "node-secondary".to_string(),
                RouteQualityRecord {
                    last_probe_latency_ms: Some(5),
                    last_ping_rtt_ms: Some(12),
                    successful_activations: 4,
                    healthy_observations: 10,
                    successful_continuity_recovers: 1,
                    last_continuity_recovery_ms: Some(240),
                    ..RouteQualityRecord::default()
                },
            ),
        ])));

        let selection = select_client_route(&config, &route_quality)
            .await
            .expect("route selection");

        assert_eq!(selection.route.endpoint_ref, "node-secondary");
    }

    #[tokio::test]
    async fn sidecar_health_exposes_selected_route_metadata() {
        let config = sample_sidecar_config("127.0.0.1:9443".parse().expect("server addr"));
        let state = SidecarState {
            config,
            started_at: Utc::now(),
            active_client: std::sync::Arc::new(RwLock::new(ActiveSidecarClient {
                handle: spawn_client(ClientConfig {
                    manifest_id: "manifest-1".to_string(),
                    transport_profile_id: "ptp-lab-edge-v2".to_string(),
                    profile_family: "edge-hybrid".to_string(),
                    profile_version: 2,
                    policy_version: 4,
                    session_mode: "hybrid".to_string(),
                    token: "shared-session-token".to_string(),
                    route: TransportRoute {
                        endpoint_ref: "node-lab-01".to_string(),
                        dial_host: "127.0.0.1".to_string(),
                        dial_port: 1,
                        server_name: Some("node-lab-01.local".to_string()),
                        preference: 10,
                        policy_tag: "primary".to_string(),
                    },
                    connect_timeout: Duration::from_millis(50),
                    heartbeat_interval: Duration::from_millis(50),
                    reconnect_delay: Duration::from_millis(50),
                }),
                route: TransportRoute {
                    endpoint_ref: "node-lab-01".to_string(),
                    dial_host: "127.0.0.1".to_string(),
                    dial_port: 9443,
                    server_name: Some("node-lab-01.local".to_string()),
                    preference: 10,
                    policy_tag: "primary".to_string(),
                },
                probe_latency_ms: Some(12),
                score: 24,
            })),
            standby_client: std::sync::Arc::new(RwLock::new(None)),
            standby_wake_signal: std::sync::Arc::new(Notify::new()),
            continuity_grace: std::sync::Arc::new(RwLock::new(None)),
            route_quality: std::sync::Arc::new(RwLock::new(HashMap::from([(
                "node-lab-01".to_string(),
                RouteQualityRecord {
                    last_probe_latency_ms: Some(12),
                    last_ping_rtt_ms: Some(9),
                    successful_activations: 2,
                    failed_activations: 0,
                    failover_count: 0,
                    healthy_observations: 5,
                    consecutive_failures: 0,
                    total_bytes_sent: 1024,
                    total_bytes_received: 2048,
                    last_observed_bytes_sent: 128,
                    last_observed_bytes_received: 256,
                    continuity_grace_entries: 1,
                    successful_continuity_recovers: 1,
                    successful_cross_route_recovers: 1,
                    failed_continuity_recovers: 0,
                    last_continuity_recovery_ms: Some(180),
                    last_cross_route_recovery_ms: Some(145),
                    last_score: Some(24),
                    quarantined_until: None,
                    last_failure_at: None,
                },
            )]))),
            perf: std::sync::Arc::new(RwLock::new(SidecarPerfBook::default())),
        };

        let health = sidecar_health(&state).await;
        assert_eq!(
            health.active_route_endpoint_ref.as_deref(),
            Some("node-lab-01")
        );
        assert_eq!(health.active_route_probe_latency_ms, Some(12));
        assert_eq!(health.active_route_score, Some(24));
        assert_eq!(health.standby_route_endpoint_ref, None);
        assert_eq!(health.standby_route_probe_latency_ms, None);
        assert_eq!(health.standby_route_score, None);
        assert!(!health.standby_ready);
        assert!(!health.continuity_grace_active);
        assert_eq!(health.continuity_grace_route_endpoint_ref, None);
        assert_eq!(health.continuity_grace_remaining_ms, None);
        assert!(!health.active_route_quarantined);
        assert_eq!(health.active_route_quarantine_remaining_ms, None);
        assert_eq!(health.active_route_continuity_grace_entries, 1);
        assert_eq!(health.active_route_successful_continuity_recovers, 1);
        assert_eq!(health.active_route_failed_continuity_recovers, 0);
        assert_eq!(health.active_route_last_continuity_recovery_ms, Some(180));
        assert_eq!(health.active_route_successful_cross_route_recovers, 1);
        assert_eq!(health.active_route_last_cross_route_recovery_ms, Some(145));
        assert_eq!(health.active_route_successful_activations, 2);
        assert_eq!(health.active_route_healthy_observations, 5);

        let active_handle = { state.active_client.read().await.handle.clone() };
        active_handle.shutdown().await;
    }

    #[tokio::test]
    async fn sidecar_health_exposes_active_route_quarantine_metadata() {
        let config = sample_sidecar_config("127.0.0.1:9443".parse().expect("server addr"));
        let state = SidecarState {
            config,
            started_at: Utc::now(),
            active_client: std::sync::Arc::new(RwLock::new(ActiveSidecarClient {
                handle: spawn_client(ClientConfig {
                    manifest_id: "manifest-1".to_string(),
                    transport_profile_id: "ptp-lab-edge-v2".to_string(),
                    profile_family: "edge-hybrid".to_string(),
                    profile_version: 2,
                    policy_version: 4,
                    session_mode: "hybrid".to_string(),
                    token: "shared-session-token".to_string(),
                    route: TransportRoute {
                        endpoint_ref: "node-lab-01".to_string(),
                        dial_host: "127.0.0.1".to_string(),
                        dial_port: 1,
                        server_name: Some("node-lab-01.local".to_string()),
                        preference: 10,
                        policy_tag: "primary".to_string(),
                    },
                    connect_timeout: Duration::from_millis(50),
                    heartbeat_interval: Duration::from_millis(50),
                    reconnect_delay: Duration::from_millis(50),
                }),
                route: TransportRoute {
                    endpoint_ref: "node-lab-01".to_string(),
                    dial_host: "127.0.0.1".to_string(),
                    dial_port: 9443,
                    server_name: Some("node-lab-01.local".to_string()),
                    preference: 10,
                    policy_tag: "primary".to_string(),
                },
                probe_latency_ms: Some(12),
                score: 24,
            })),
            standby_client: std::sync::Arc::new(RwLock::new(None)),
            standby_wake_signal: std::sync::Arc::new(Notify::new()),
            continuity_grace: std::sync::Arc::new(RwLock::new(None)),
            route_quality: std::sync::Arc::new(RwLock::new(HashMap::from([(
                "node-lab-01".to_string(),
                RouteQualityRecord {
                    quarantined_until: Some(std::time::Instant::now() + Duration::from_secs(2)),
                    ..RouteQualityRecord::default()
                },
            )]))),
            perf: std::sync::Arc::new(RwLock::new(SidecarPerfBook::default())),
        };

        let health = sidecar_health(&state).await;
        assert!(health.active_route_quarantined);
        assert!(health
            .active_route_quarantine_remaining_ms
            .is_some_and(|remaining_ms| remaining_ms > 0 && remaining_ms <= 2_000));

        let active_handle = { state.active_client.read().await.handle.clone() };
        active_handle.shutdown().await;
    }

    #[tokio::test]
    async fn sidecar_health_exposes_continuity_grace_metadata() {
        let config = sample_sidecar_config("127.0.0.1:9443".parse().expect("server addr"));
        let state = SidecarState {
            config,
            started_at: Utc::now(),
            active_client: std::sync::Arc::new(RwLock::new(ActiveSidecarClient {
                handle: spawn_client(ClientConfig {
                    manifest_id: "manifest-1".to_string(),
                    transport_profile_id: "ptp-lab-edge-v2".to_string(),
                    profile_family: "edge-hybrid".to_string(),
                    profile_version: 2,
                    policy_version: 4,
                    session_mode: "hybrid".to_string(),
                    token: "shared-session-token".to_string(),
                    route: TransportRoute {
                        endpoint_ref: "node-lab-01".to_string(),
                        dial_host: "127.0.0.1".to_string(),
                        dial_port: 1,
                        server_name: Some("node-lab-01.local".to_string()),
                        preference: 10,
                        policy_tag: "primary".to_string(),
                    },
                    connect_timeout: Duration::from_millis(50),
                    heartbeat_interval: Duration::from_millis(50),
                    reconnect_delay: Duration::from_millis(50),
                }),
                route: TransportRoute {
                    endpoint_ref: "node-lab-01".to_string(),
                    dial_host: "127.0.0.1".to_string(),
                    dial_port: 9443,
                    server_name: Some("node-lab-01.local".to_string()),
                    preference: 10,
                    policy_tag: "primary".to_string(),
                },
                probe_latency_ms: Some(12),
                score: 24,
            })),
            standby_client: std::sync::Arc::new(RwLock::new(None)),
            standby_wake_signal: std::sync::Arc::new(Notify::new()),
            continuity_grace: std::sync::Arc::new(RwLock::new(Some(ContinuityGraceWindow {
                route_endpoint_ref: "node-lab-01".to_string(),
                started_at: tokio::time::Instant::now(),
                grace_budget: Duration::from_secs(3),
            }))),
            route_quality: std::sync::Arc::new(RwLock::new(HashMap::new())),
            perf: std::sync::Arc::new(RwLock::new(SidecarPerfBook::default())),
        };

        let health = sidecar_health(&state).await;
        assert!(health.continuity_grace_active);
        assert_eq!(
            health.continuity_grace_route_endpoint_ref.as_deref(),
            Some("node-lab-01")
        );
        assert!(health
            .continuity_grace_remaining_ms
            .is_some_and(|remaining_ms| remaining_ms > 0 && remaining_ms <= 3_000));

        let active_handle = { state.active_client.read().await.handle.clone() };
        active_handle.shutdown().await;
    }

    #[tokio::test]
    async fn attempt_route_failover_swaps_to_next_healthy_route() {
        let server_primary = spawn_server(ServerConfig {
            bind_addrs: vec!["127.0.0.1:0".parse::<SocketAddr>().expect("bind addr")],
            transport_profile_id: "ptp-lab-edge-v2".to_string(),
            profile_family: "edge-hybrid".to_string(),
            profile_version: 2,
            policy_version: 4,
            session_mode: "hybrid".to_string(),
            token: "shared-session-token".to_string(),
            heartbeat_timeout: Duration::from_secs(2),
            allow_private_targets: true,
        })
        .await
        .expect("spawn primary server");
        let primary_addr = server_primary
            .snapshot()
            .await
            .bound_addrs
            .first()
            .expect("primary addr")
            .parse::<SocketAddr>()
            .expect("primary socket addr");

        let server_secondary = spawn_server(ServerConfig {
            bind_addrs: vec!["127.0.0.1:0".parse::<SocketAddr>().expect("bind addr")],
            transport_profile_id: "ptp-lab-edge-v2".to_string(),
            profile_family: "edge-hybrid".to_string(),
            profile_version: 2,
            policy_version: 4,
            session_mode: "hybrid".to_string(),
            token: "shared-session-token".to_string(),
            heartbeat_timeout: Duration::from_secs(2),
            allow_private_targets: true,
        })
        .await
        .expect("spawn secondary server");
        let secondary_addr = server_secondary
            .snapshot()
            .await
            .bound_addrs
            .first()
            .expect("secondary addr")
            .parse::<SocketAddr>()
            .expect("secondary socket addr");

        let mut config = sample_sidecar_config(primary_addr);
        config.routes = vec![
            crate::engine::helix::config::HelixManifestRoute {
                endpoint_ref: "node-primary".to_string(),
                dial_host: primary_addr.ip().to_string(),
                dial_port: primary_addr.port(),
                server_name: Some("node-primary.local".to_string()),
                preference: 5,
                policy_tag: "primary".to_string(),
            },
            crate::engine::helix::config::HelixManifestRoute {
                endpoint_ref: "node-secondary".to_string(),
                dial_host: secondary_addr.ip().to_string(),
                dial_port: secondary_addr.port(),
                server_name: Some("node-secondary.local".to_string()),
                preference: 10,
                policy_tag: "fallback".to_string(),
            },
        ];

        let initial_route = TransportRoute {
            endpoint_ref: "node-primary".to_string(),
            dial_host: primary_addr.ip().to_string(),
            dial_port: primary_addr.port(),
            server_name: Some("node-primary.local".to_string()),
            preference: 5,
            policy_tag: "primary".to_string(),
        };
        let initial_handle = spawn_sidecar_client(&config, initial_route.clone());
        wait_until_ready(&initial_handle, Duration::from_secs(3)).await;

        let active_client = std::sync::Arc::new(RwLock::new(ActiveSidecarClient {
            handle: initial_handle,
            route: initial_route,
            probe_latency_ms: Some(1),
            score: 1,
        }));
        let standby_client = std::sync::Arc::new(RwLock::new(None));

        server_primary.shutdown().await;
        tokio::time::sleep(Duration::from_millis(300)).await;

        let route_quality = std::sync::Arc::new(RwLock::new(HashMap::new()));
        let switched =
            attempt_route_failover(&config, &active_client, &standby_client, &route_quality)
                .await
                .expect("route failover");
        assert!(switched);

        let active_route = active_client.read().await.route.endpoint_ref.clone();
        assert_eq!(active_route, "node-secondary");
        assert!(route_quality.read().await.get("node-secondary").is_some());

        let active_handle = active_client.read().await.handle.clone();
        wait_until_ready(&active_handle, Duration::from_secs(3)).await;

        active_handle.shutdown().await;
        server_secondary.shutdown().await;
    }

    #[tokio::test]
    async fn attempt_route_failover_promotes_ready_warm_standby() {
        let server_primary = spawn_server(ServerConfig {
            bind_addrs: vec!["127.0.0.1:0".parse::<SocketAddr>().expect("bind addr")],
            transport_profile_id: "ptp-lab-edge-v2".to_string(),
            profile_family: "edge-hybrid".to_string(),
            profile_version: 2,
            policy_version: 4,
            session_mode: "hybrid".to_string(),
            token: "shared-session-token".to_string(),
            heartbeat_timeout: Duration::from_secs(2),
            allow_private_targets: true,
        })
        .await
        .expect("spawn primary server");
        let primary_addr = server_primary
            .snapshot()
            .await
            .bound_addrs
            .first()
            .expect("primary addr")
            .parse::<SocketAddr>()
            .expect("primary socket addr");

        let server_secondary = spawn_server(ServerConfig {
            bind_addrs: vec!["127.0.0.1:0".parse::<SocketAddr>().expect("bind addr")],
            transport_profile_id: "ptp-lab-edge-v2".to_string(),
            profile_family: "edge-hybrid".to_string(),
            profile_version: 2,
            policy_version: 4,
            session_mode: "hybrid".to_string(),
            token: "shared-session-token".to_string(),
            heartbeat_timeout: Duration::from_secs(2),
            allow_private_targets: true,
        })
        .await
        .expect("spawn secondary server");
        let secondary_addr = server_secondary
            .snapshot()
            .await
            .bound_addrs
            .first()
            .expect("secondary addr")
            .parse::<SocketAddr>()
            .expect("secondary socket addr");

        let mut config = sample_sidecar_config(primary_addr);
        config.routes = vec![
            crate::engine::helix::config::HelixManifestRoute {
                endpoint_ref: "node-primary".to_string(),
                dial_host: primary_addr.ip().to_string(),
                dial_port: primary_addr.port(),
                server_name: Some("node-primary.local".to_string()),
                preference: 5,
                policy_tag: "primary".to_string(),
            },
            crate::engine::helix::config::HelixManifestRoute {
                endpoint_ref: "node-secondary".to_string(),
                dial_host: secondary_addr.ip().to_string(),
                dial_port: secondary_addr.port(),
                server_name: Some("node-secondary.local".to_string()),
                preference: 10,
                policy_tag: "fallback".to_string(),
            },
        ];

        let primary_route = TransportRoute {
            endpoint_ref: "node-primary".to_string(),
            dial_host: primary_addr.ip().to_string(),
            dial_port: primary_addr.port(),
            server_name: Some("node-primary.local".to_string()),
            preference: 5,
            policy_tag: "primary".to_string(),
        };
        let primary_handle = spawn_sidecar_client(&config, primary_route.clone());
        wait_until_ready(&primary_handle, Duration::from_secs(3)).await;

        let secondary_route = TransportRoute {
            endpoint_ref: "node-secondary".to_string(),
            dial_host: secondary_addr.ip().to_string(),
            dial_port: secondary_addr.port(),
            server_name: Some("node-secondary.local".to_string()),
            preference: 10,
            policy_tag: "fallback".to_string(),
        };
        let standby_handle = spawn_sidecar_client(&config, secondary_route.clone());
        wait_until_ready(&standby_handle, Duration::from_secs(3)).await;

        let active_client = std::sync::Arc::new(RwLock::new(ActiveSidecarClient {
            handle: primary_handle,
            route: primary_route,
            probe_latency_ms: Some(1),
            score: 1,
        }));
        let standby_client = std::sync::Arc::new(RwLock::new(Some(ActiveSidecarClient {
            handle: standby_handle,
            route: secondary_route,
            probe_latency_ms: Some(2),
            score: 12,
        })));
        let route_quality = std::sync::Arc::new(RwLock::new(HashMap::new()));

        server_primary.shutdown().await;
        tokio::time::sleep(Duration::from_millis(150)).await;

        let started_at = Instant::now();
        let switched =
            attempt_route_failover(&config, &active_client, &standby_client, &route_quality)
                .await
                .expect("warm standby failover");
        let elapsed = started_at.elapsed();

        assert!(switched);
        assert!(
            elapsed < Duration::from_millis(120),
            "warm standby promotion took too long: {elapsed:?}"
        );
        assert_eq!(
            active_client.read().await.route.endpoint_ref,
            "node-secondary"
        );
        assert!(standby_client.read().await.is_none());

        let active_handle = active_client.read().await.handle.clone();
        wait_until_ready(&active_handle, Duration::from_secs(2)).await;

        active_handle.shutdown().await;
        server_secondary.shutdown().await;
    }

    #[tokio::test]
    async fn failover_monitor_switches_route_and_records_quality_history() {
        let server_primary = spawn_server(ServerConfig {
            bind_addrs: vec!["127.0.0.1:0".parse::<SocketAddr>().expect("bind addr")],
            transport_profile_id: "ptp-lab-edge-v2".to_string(),
            profile_family: "edge-hybrid".to_string(),
            profile_version: 2,
            policy_version: 4,
            session_mode: "hybrid".to_string(),
            token: "shared-session-token".to_string(),
            heartbeat_timeout: Duration::from_secs(2),
            allow_private_targets: true,
        })
        .await
        .expect("spawn primary server");
        let primary_addr = server_primary
            .snapshot()
            .await
            .bound_addrs
            .first()
            .expect("primary addr")
            .parse::<SocketAddr>()
            .expect("primary socket addr");

        let server_secondary = spawn_server(ServerConfig {
            bind_addrs: vec!["127.0.0.1:0".parse::<SocketAddr>().expect("bind addr")],
            transport_profile_id: "ptp-lab-edge-v2".to_string(),
            profile_family: "edge-hybrid".to_string(),
            profile_version: 2,
            policy_version: 4,
            session_mode: "hybrid".to_string(),
            token: "shared-session-token".to_string(),
            heartbeat_timeout: Duration::from_secs(2),
            allow_private_targets: true,
        })
        .await
        .expect("spawn secondary server");
        let secondary_addr = server_secondary
            .snapshot()
            .await
            .bound_addrs
            .first()
            .expect("secondary addr")
            .parse::<SocketAddr>()
            .expect("secondary socket addr");

        let mut config = sample_sidecar_config(primary_addr);
        config.runtime_unhealthy_threshold = 1;
        config.routes = vec![
            crate::engine::helix::config::HelixManifestRoute {
                endpoint_ref: "node-primary".to_string(),
                dial_host: primary_addr.ip().to_string(),
                dial_port: primary_addr.port(),
                server_name: Some("node-primary.local".to_string()),
                preference: 5,
                policy_tag: "primary".to_string(),
            },
            crate::engine::helix::config::HelixManifestRoute {
                endpoint_ref: "node-secondary".to_string(),
                dial_host: secondary_addr.ip().to_string(),
                dial_port: secondary_addr.port(),
                server_name: Some("node-secondary.local".to_string()),
                preference: 10,
                policy_tag: "fallback".to_string(),
            },
        ];

        let initial_route = TransportRoute {
            endpoint_ref: "node-primary".to_string(),
            dial_host: primary_addr.ip().to_string(),
            dial_port: primary_addr.port(),
            server_name: Some("node-primary.local".to_string()),
            preference: 5,
            policy_tag: "primary".to_string(),
        };
        let initial_handle = spawn_sidecar_client(&config, initial_route.clone());
        wait_until_ready(&initial_handle, Duration::from_secs(3)).await;

        let route_quality = std::sync::Arc::new(RwLock::new(HashMap::new()));
        let active_client = std::sync::Arc::new(RwLock::new(ActiveSidecarClient {
            handle: initial_handle,
            route: initial_route.clone(),
            probe_latency_ms: Some(1),
            score: 1,
        }));
        let standby_client = std::sync::Arc::new(RwLock::new(None));
        record_successful_activation(&route_quality, &initial_route, Some(1), 1).await;

        let monitor_task = tokio::spawn(run_failover_monitor(
            config.clone(),
            active_client.clone(),
            standby_client.clone(),
            std::sync::Arc::new(Notify::new()),
            std::sync::Arc::new(RwLock::new(None)),
            route_quality.clone(),
            std::sync::Arc::new(RwLock::new(SidecarPerfBook::default())),
        ));

        server_primary.shutdown().await;

        let deadline = tokio::time::Instant::now() + Duration::from_secs(6);
        loop {
            let current_route = active_client.read().await.route.endpoint_ref.clone();
            if current_route == "node-secondary" {
                break;
            }

            assert!(
                tokio::time::Instant::now() < deadline,
                "failover monitor did not switch to the secondary route"
            );
            tokio::time::sleep(Duration::from_millis(150)).await;
        }

        monitor_task.abort();

        let quality_snapshot = route_quality.read().await.clone();
        assert_eq!(
            quality_snapshot
                .get("node-primary")
                .map(|record| record.failover_count),
            Some(1)
        );
        assert_eq!(
            quality_snapshot
                .get("node-primary")
                .map(|record| record.failed_continuity_recovers),
            Some(0)
        );
        assert_eq!(
            quality_snapshot
                .get("node-secondary")
                .map(|record| record.successful_activations),
            Some(1)
        );

        let active_handle = active_client.read().await.handle.clone();
        active_handle.shutdown().await;
        server_secondary.shutdown().await;
    }

    #[tokio::test]
    async fn failover_monitor_preserves_route_continuity_grace_for_active_streams() {
        let upstream_addr = spawn_upstream_echo_server().await;

        let server_primary = spawn_server(ServerConfig {
            bind_addrs: vec!["127.0.0.1:0".parse::<SocketAddr>().expect("bind addr")],
            transport_profile_id: "ptp-lab-edge-v2".to_string(),
            profile_family: "edge-hybrid".to_string(),
            profile_version: 2,
            policy_version: 4,
            session_mode: "hybrid".to_string(),
            token: "shared-session-token".to_string(),
            heartbeat_timeout: Duration::from_secs(2),
            allow_private_targets: true,
        })
        .await
        .expect("spawn primary server");
        let primary_addr = server_primary
            .snapshot()
            .await
            .bound_addrs
            .first()
            .expect("primary addr")
            .parse::<SocketAddr>()
            .expect("primary socket addr");

        let server_secondary = spawn_server(ServerConfig {
            bind_addrs: vec!["127.0.0.1:0".parse::<SocketAddr>().expect("bind addr")],
            transport_profile_id: "ptp-lab-edge-v2".to_string(),
            profile_family: "edge-hybrid".to_string(),
            profile_version: 2,
            policy_version: 4,
            session_mode: "hybrid".to_string(),
            token: "shared-session-token".to_string(),
            heartbeat_timeout: Duration::from_secs(2),
            allow_private_targets: true,
        })
        .await
        .expect("spawn secondary server");
        let secondary_addr = server_secondary
            .snapshot()
            .await
            .bound_addrs
            .first()
            .expect("secondary addr")
            .parse::<SocketAddr>()
            .expect("secondary socket addr");

        let mut config = sample_sidecar_config(primary_addr);
        config.runtime_unhealthy_threshold = 1;
        config.routes = vec![
            crate::engine::helix::config::HelixManifestRoute {
                endpoint_ref: "node-primary".to_string(),
                dial_host: primary_addr.ip().to_string(),
                dial_port: primary_addr.port(),
                server_name: Some("node-primary.local".to_string()),
                preference: 5,
                policy_tag: "primary".to_string(),
            },
            crate::engine::helix::config::HelixManifestRoute {
                endpoint_ref: "node-secondary".to_string(),
                dial_host: secondary_addr.ip().to_string(),
                dial_port: secondary_addr.port(),
                server_name: Some("node-secondary.local".to_string()),
                preference: 10,
                policy_tag: "fallback".to_string(),
            },
        ];

        let initial_route = TransportRoute {
            endpoint_ref: "node-primary".to_string(),
            dial_host: primary_addr.ip().to_string(),
            dial_port: primary_addr.port(),
            server_name: Some("node-primary.local".to_string()),
            preference: 5,
            policy_tag: "primary".to_string(),
        };
        let initial_handle = spawn_sidecar_client(&config, initial_route.clone());
        wait_until_ready(&initial_handle, Duration::from_secs(3)).await;

        let mut continuity_stream = initial_handle
            .open_stream(StreamTarget::new(
                upstream_addr.ip().to_string(),
                upstream_addr.port(),
            ))
            .await
            .expect("open continuity stream");
        let continuity_writer = continuity_stream.writer();
        continuity_writer
            .send(b"continuity-check".to_vec())
            .await
            .expect("write continuity probe");
        let echoed = tokio::time::timeout(Duration::from_secs(2), continuity_stream.recv())
            .await
            .expect("wait for continuity echo")
            .expect("continuity echo payload");
        assert_eq!(echoed, b"continuity-check");

        let route_quality = std::sync::Arc::new(RwLock::new(HashMap::new()));
        let active_client = std::sync::Arc::new(RwLock::new(ActiveSidecarClient {
            handle: initial_handle.clone(),
            route: initial_route.clone(),
            probe_latency_ms: Some(1),
            score: 1,
        }));
        let standby_client = std::sync::Arc::new(RwLock::new(None));
        record_successful_activation(&route_quality, &initial_route, Some(1), 1).await;

        let monitor_task = tokio::spawn(run_failover_monitor(
            config.clone(),
            active_client.clone(),
            standby_client.clone(),
            std::sync::Arc::new(Notify::new()),
            std::sync::Arc::new(RwLock::new(None)),
            route_quality.clone(),
            std::sync::Arc::new(RwLock::new(SidecarPerfBook::default())),
        ));

        server_primary.shutdown().await;

        tokio::time::sleep(Duration::from_millis(900)).await;
        assert_eq!(
            active_client.read().await.route.endpoint_ref,
            "node-primary",
            "monitor should hold same-route continuity grace while streams are active",
        );

        let deadline = tokio::time::Instant::now() + Duration::from_secs(7);
        loop {
            let current_route = active_client.read().await.route.endpoint_ref.clone();
            if current_route == "node-secondary" {
                break;
            }

            assert!(
                tokio::time::Instant::now() < deadline,
                "failover monitor did not escalate to the fallback route after continuity grace",
            );
            tokio::time::sleep(Duration::from_millis(150)).await;
        }

        monitor_task.abort();

        let quality_snapshot = route_quality.read().await.clone();
        assert_eq!(
            quality_snapshot
                .get("node-primary")
                .map(|record| record.continuity_grace_entries),
            Some(1)
        );
        assert_eq!(
            quality_snapshot
                .get("node-primary")
                .map(|record| record.failed_continuity_recovers),
            Some(1)
        );
        assert_eq!(
            quality_snapshot
                .get("node-secondary")
                .map(|record| record.successful_cross_route_recovers),
            Some(1)
        );
        assert!(quality_snapshot
            .get("node-secondary")
            .and_then(|record| record.last_cross_route_recovery_ms)
            .is_some());

        let _ = continuity_stream.close("test-complete").await;
        initial_handle.shutdown().await;
        server_secondary.shutdown().await;
    }

    #[tokio::test]
    async fn socks5_proxy_bridges_secure_transport_stream() {
        let upstream_listener = TcpListener::bind("127.0.0.1:0")
            .await
            .expect("bind upstream echo");
        let upstream_addr = upstream_listener.local_addr().expect("upstream addr");
        tokio::spawn(async move {
            loop {
                let Ok((mut stream, _)) = upstream_listener.accept().await else {
                    break;
                };
                tokio::spawn(async move {
                    let mut buffer = [0_u8; 4096];
                    loop {
                        match stream.read(&mut buffer).await {
                            Ok(0) => break,
                            Ok(read) => {
                                if stream.write_all(&buffer[..read]).await.is_err() {
                                    break;
                                }
                            }
                            Err(_) => break,
                        }
                    }
                });
            }
        });

        let server = spawn_server(ServerConfig {
            bind_addrs: vec!["127.0.0.1:0".parse::<SocketAddr>().expect("bind addr")],
            transport_profile_id: "ptp-lab-edge-v2".to_string(),
            profile_family: "edge-hybrid".to_string(),
            profile_version: 2,
            policy_version: 4,
            session_mode: "hybrid".to_string(),
            token: "shared-session-token".to_string(),
            heartbeat_timeout: Duration::from_secs(2),
            allow_private_targets: true,
        })
        .await
        .expect("spawn server");
        let server_addr = server
            .snapshot()
            .await
            .bound_addrs
            .first()
            .expect("bound addr")
            .parse::<SocketAddr>()
            .expect("socket addr");

        let config = sample_sidecar_config(server_addr);
        let client_handle = spawn_client(ClientConfig {
            manifest_id: config.manifest_id.clone(),
            transport_profile_id: config.transport_profile_id.clone(),
            profile_family: config.profile_family.clone(),
            profile_version: config.profile_version,
            policy_version: config.policy_version,
            session_mode: config.session_mode.clone(),
            token: config.credentials.token.clone(),
            route: TransportRoute {
                endpoint_ref: "node-lab-01".to_string(),
                dial_host: server_addr.ip().to_string(),
                dial_port: server_addr.port(),
                server_name: Some("node-lab-01.local".to_string()),
                preference: 10,
                policy_tag: "primary".to_string(),
            },
            connect_timeout: Duration::from_secs(2),
            heartbeat_interval: Duration::from_millis(150),
            reconnect_delay: Duration::from_millis(100),
        });

        wait_until_ready(&client_handle, Duration::from_secs(3)).await;

        let proxy_listener = TcpListener::bind("127.0.0.1:0")
            .await
            .expect("bind proxy listener");
        let proxy_addr = proxy_listener.local_addr().expect("proxy addr");
        let proxy_client_handle = client_handle.clone();
        tokio::spawn(async move {
            if let Ok((stream, _)) = proxy_listener.accept().await {
                handle_proxy_connection(
                    stream,
                    proxy_client_handle,
                    std::sync::Arc::new(RwLock::new(SidecarPerfBook::default())),
                )
                .await
                .expect("handle proxy connection");
            }
        });

        let mut proxy_client = TcpStream::connect(proxy_addr).await.expect("connect proxy");
        proxy_client
            .write_all(&[SOCKS_VERSION, 0x01, 0x00])
            .await
            .expect("write greeting");
        let mut method_reply = [0_u8; 2];
        proxy_client
            .read_exact(&mut method_reply)
            .await
            .expect("method reply");
        assert_eq!(method_reply, [SOCKS_VERSION, 0x00]);

        let mut request = vec![SOCKS_VERSION, 0x01, 0x00, 0x01];
        let upstream_ip = match upstream_addr.ip() {
            std::net::IpAddr::V4(ip) => ip.octets(),
            std::net::IpAddr::V6(_) => panic!("expected ipv4 upstream in sidecar socks test"),
        };
        request.extend_from_slice(&upstream_ip);
        request.extend_from_slice(&upstream_addr.port().to_be_bytes());
        proxy_client
            .write_all(&request)
            .await
            .expect("connect request");

        let mut connect_reply = [0_u8; 10];
        proxy_client
            .read_exact(&mut connect_reply)
            .await
            .expect("connect reply");
        assert_eq!(connect_reply[0], SOCKS_VERSION);
        assert_eq!(connect_reply[1], 0x00);

        proxy_client
            .write_all(b"cybervpn-socks-e2e")
            .await
            .expect("proxy payload");
        let mut echoed = vec![0_u8; "cybervpn-socks-e2e".len()];
        proxy_client
            .read_exact(&mut echoed)
            .await
            .expect("echoed payload");
        assert_eq!(echoed, b"cybervpn-socks-e2e");

        client_handle.shutdown().await;
        server.shutdown().await;
    }

    async fn wait_until_ready(client_handle: &ClientHandle, timeout: Duration) {
        let deadline = tokio::time::Instant::now() + timeout;
        loop {
            if client_handle.snapshot().await.ready {
                return;
            }

            assert!(
                tokio::time::Instant::now() < deadline,
                "sidecar client handle was not ready before timeout"
            );

            tokio::time::sleep(Duration::from_millis(50)).await;
        }
    }
}
