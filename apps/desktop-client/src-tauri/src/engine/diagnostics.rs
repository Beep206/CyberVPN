use std::{
    fs::{self, OpenOptions},
    io::{Read, Write},
    path::{Path, PathBuf},
};

use chrono::Utc;
use serde::{Deserialize, Serialize};
use serde_json::{json, Value};
use tauri::{AppHandle, Emitter, Manager};

use crate::{
    engine::{
        error::AppError,
        helix::config::{
            HelixPreparedRuntime, HelixRecoveryBenchmarkReport, HelixResolvedManifest,
            HelixSidecarHealth, HelixSidecarTelemetry, TransportBenchmarkComparisonReport,
            TransportBenchmarkMatrixReport, TransportBenchmarkReport,
        },
        lifecycle::StartupRecoveryInfo,
        store::{self, AppDataStore},
        sys::net::get_local_ip,
    },
    ipc::models::{ConnectionStatus, ProxyNode, Subscription},
};

const DIAGNOSTICS_DIR_NAME: &str = "diagnostics";
const SUPPORT_BUNDLES_DIR_NAME: &str = "support-bundles";
const EVENTS_LOG_NAME: &str = "events.jsonl";
const EVENTS_LOG_ROTATED_NAME: &str = "events.previous.jsonl";
const CORE_RUNTIME_LOG_NAME: &str = "core-runtime.log";
const CORE_RUNTIME_LOG_ROTATED_NAME: &str = "core-runtime.previous.log";
const HELIX_RUNTIME_LOG_NAME: &str = "helix-runtime.log";
const HELIX_RUNTIME_LOG_ROTATED_NAME: &str = "helix-runtime.previous.log";
const MAX_LOG_BYTES: u64 = 2 * 1024 * 1024;
const DEFAULT_RECENT_LIMIT: usize = 120;
const DEFAULT_LOG_TAIL_LIMIT: usize = 200;
const MAX_LOG_LINE_LEN: usize = 4_096;

#[derive(Debug, Clone, Copy, Serialize, Deserialize)]
#[serde(rename_all = "lowercase")]
pub enum DiagnosticLevel {
    Debug,
    Info,
    Warn,
    Error,
}

impl DiagnosticLevel {
    pub fn as_str(self) -> &'static str {
        match self {
            Self::Debug => "debug",
            Self::Info => "info",
            Self::Warn => "warn",
            Self::Error => "error",
        }
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DiagnosticEntry {
    pub id: String,
    pub timestamp: String,
    pub level: String,
    pub source: String,
    pub message: String,
    #[serde(default = "default_payload")]
    pub payload: Value,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct HelixDiagnosticsSnapshot {
    pub backend_url: Option<String>,
    pub desktop_client_id: Option<String>,
    pub last_fallback_reason: Option<String>,
    pub last_manifest_version_id: Option<String>,
    pub last_rollout_id: Option<String>,
    pub transport_profile_id: Option<String>,
    pub prepared_route_count: Option<usize>,
    pub health_url: Option<String>,
    pub proxy_url: Option<String>,
    pub live_health: Option<HelixSidecarHealth>,
    pub live_telemetry: Option<HelixSidecarTelemetry>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DesktopDiagnosticsSnapshot {
    pub collected_at: String,
    pub app_name: String,
    pub app_version: String,
    pub package_name: String,
    pub platform: String,
    pub app_dir: String,
    pub diagnostics_dir: String,
    pub support_bundle_dir: String,
    pub store_path: String,
    pub lifecycle: StartupRecoveryInfo,
    pub connection_status: ConnectionStatus,
    pub active_core: String,
    pub active_profile_id: Option<String>,
    pub local_ip: Option<String>,
    pub local_socks_port: Option<u16>,
    pub allow_lan: bool,
    pub profile_count: usize,
    pub routing_rule_count: usize,
    pub subscription_count: usize,
    pub split_tunneling_mode: String,
    pub split_tunneling_app_count: usize,
    pub smart_connect_enabled: bool,
    pub stealth_mode_enabled: bool,
    pub pqc_enforcement_mode: bool,
    pub privacy_shield_level: String,
    pub last_benchmark_run_id: Option<String>,
    pub last_comparison_run_id: Option<String>,
    pub last_matrix_run_id: Option<String>,
    pub last_recovery_run_id: Option<String>,
    pub helix: HelixDiagnosticsSnapshot,
    pub recent_entries: Vec<DiagnosticEntry>,
    pub core_log_tail: Vec<String>,
    pub helix_log_tail: Vec<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SupportBundleExportResult {
    pub archive_path: String,
    pub exported_at: String,
    pub event_count: usize,
    pub includes_core_log: bool,
    pub includes_helix_log: bool,
}

#[derive(Debug, Clone, Serialize)]
struct SupportBundleReport {
    snapshot: DesktopDiagnosticsSnapshot,
    profiles: Vec<RedactedProfileSummary>,
    subscriptions: Vec<RedactedSubscriptionSummary>,
    helix_manifest: Option<RedactedHelixManifest>,
    helix_runtime: Option<RedactedPreparedRuntime>,
    helix_performance_summary: Value,
    last_benchmark_report: Option<TransportBenchmarkReport>,
    last_comparison_report: Option<TransportBenchmarkComparisonReport>,
    last_matrix_report: Option<TransportBenchmarkMatrixReport>,
    last_recovery_report: Option<HelixRecoveryBenchmarkReport>,
}

#[derive(Debug, Clone, Serialize)]
struct RedactedProfileSummary {
    id: String,
    name: String,
    server: String,
    port: u16,
    protocol: String,
    network: Option<String>,
    tls: Option<String>,
    sni: Option<String>,
    fingerprint: Option<String>,
    group_id: Option<String>,
    ping: Option<u32>,
    pqc_enabled: Option<bool>,
}

#[derive(Debug, Clone, Serialize)]
struct RedactedSubscriptionSummary {
    id: String,
    name: String,
    host: Option<String>,
    auto_update: bool,
    last_updated: Option<u64>,
}

#[derive(Debug, Clone, Serialize)]
struct RedactedHelixManifest {
    manifest_version_id: String,
    manifest_id: String,
    rollout_id: String,
    transport_profile_id: String,
    profile_family: String,
    profile_version: i32,
    policy_version: i32,
    route_count: usize,
    fallback_core: String,
    metrics_namespace: String,
    trace_id: String,
}

#[derive(Debug, Clone, Serialize)]
struct RedactedPreparedRuntime {
    manifest_id: String,
    manifest_version_id: String,
    rollout_id: String,
    transport_profile_id: String,
    config_path: String,
    sidecar_path: String,
    binary_available: bool,
    health_url: String,
    proxy_url: String,
    fallback_core: String,
    route_count: usize,
    startup_timeout_seconds: i32,
}

fn percentile_u32(values: &[u32], percentile: f64) -> Option<u32> {
    if values.is_empty() {
        return None;
    }

    let mut sorted = values.to_vec();
    sorted.sort_unstable();
    let safe_percentile = percentile.clamp(0.0, 1.0);
    let index = ((sorted.len() as f64 * safe_percentile).ceil() as usize)
        .saturating_sub(1)
        .min(sorted.len().saturating_sub(1));
    sorted.get(index).copied()
}

fn build_helix_performance_summary(
    snapshot: &DesktopDiagnosticsSnapshot,
    store_data: &AppDataStore,
) -> Value {
    let comparison_helix_entry =
        store_data
            .helix_last_comparison_report
            .as_ref()
            .and_then(|report| {
                report.entries.iter().find(|entry| {
                    entry.requested_core == "helix"
                        || entry.effective_core.as_deref() == Some("helix")
                })
            });
    let matrix_helix_summary = store_data
        .helix_last_matrix_report
        .as_ref()
        .and_then(|report| {
            report
                .core_summaries
                .iter()
                .find(|summary| summary.core == "helix")
        });
    let live_telemetry = snapshot.helix.live_telemetry.as_ref();
    let recent_rtt_ms = live_telemetry
        .map(|telemetry| telemetry.recent_rtt_ms.as_slice())
        .unwrap_or(&[]);

    json!({
        "collected_at": snapshot.collected_at,
        "active_core": snapshot.active_core,
        "active_profile_id": snapshot.active_profile_id,
        "last_runs": {
            "benchmark_run_id": snapshot.last_benchmark_run_id,
            "comparison_run_id": snapshot.last_comparison_run_id,
            "matrix_run_id": snapshot.last_matrix_run_id,
            "recovery_run_id": snapshot.last_recovery_run_id,
        },
        "live_health": snapshot.helix.live_health.as_ref().map(|health| {
            json!({
                "status": health.status,
                "ready": health.ready,
                "active_route_endpoint_ref": health.active_route_endpoint_ref,
                "active_route_score": health.active_route_score,
                "last_ping_rtt_ms": health.last_ping_rtt_ms,
                "standby_route_endpoint_ref": health.standby_route_endpoint_ref,
                "standby_ready": health.standby_ready,
                "frame_queue_depth": health.frame_queue_depth,
                "frame_queue_peak": health.frame_queue_peak,
                "pending_open_streams": health.pending_open_streams,
                "max_concurrent_streams": health.max_concurrent_streams,
                "active_streams": health.active_streams,
                "route_count": health.route_count,
                "bytes_sent": health.bytes_sent,
                "bytes_received": health.bytes_received,
            })
        }),
        "live_telemetry": live_telemetry.map(|telemetry| {
            json!({
                "collected_at": telemetry.collected_at,
                "recent_rtt_samples": telemetry.recent_rtt_ms.len(),
                "recent_rtt_p50_ms": percentile_u32(recent_rtt_ms, 0.5),
                "recent_rtt_p95_ms": percentile_u32(recent_rtt_ms, 0.95),
                "recent_stream_samples": telemetry.recent_streams.len(),
                "sample_peak_frame_queue_depth": telemetry.recent_streams.iter().map(|stream| stream.peak_frame_queue_depth).max(),
                "sample_peak_inbound_queue_depth": telemetry.recent_streams.iter().map(|stream| stream.peak_inbound_queue_depth).max(),
                "sample_total_bytes": telemetry
                    .recent_streams
                    .iter()
                    .fold(0_u64, |total, stream| {
                        total
                            .saturating_add(stream.bytes_sent)
                            .saturating_add(stream.bytes_received)
                    }),
            })
        }),
        "last_benchmark": store_data.helix_last_benchmark_report.as_ref().map(|report| {
            json!({
                "run_id": report.run_id,
                "active_core": report.active_core,
                "successes": report.successes,
                "failures": report.failures,
                "median_connect_latency_ms": report.median_connect_latency_ms,
                "median_first_byte_latency_ms": report.median_first_byte_latency_ms,
                "median_open_to_first_byte_gap_ms": report.median_open_to_first_byte_gap_ms,
                "p95_open_to_first_byte_gap_ms": report.p95_open_to_first_byte_gap_ms,
                "average_throughput_kbps": report.average_throughput_kbps,
                "queue_pressure": report.helix_queue_pressure.clone(),
            })
        }),
        "last_comparison": store_data.helix_last_comparison_report.as_ref().map(|report| {
            json!({
                "run_id": report.run_id,
                "baseline_core": report.baseline_core,
                "entry_count": report.entries.len(),
                "helix_relative_connect_latency_ratio": comparison_helix_entry.and_then(|entry| entry.relative_connect_latency_ratio),
                "helix_relative_first_byte_latency_ratio": comparison_helix_entry.and_then(|entry| entry.relative_first_byte_latency_ratio),
                "helix_relative_open_to_first_byte_gap_ratio": comparison_helix_entry.and_then(|entry| entry.relative_open_to_first_byte_gap_ratio),
                "helix_relative_throughput_ratio": comparison_helix_entry.and_then(|entry| entry.relative_throughput_ratio),
                "helix_queue_pressure": comparison_helix_entry
                    .and_then(|entry| entry.benchmark.as_ref())
                    .and_then(|benchmark| benchmark.helix_queue_pressure.clone()),
            })
        }),
        "last_matrix": store_data.helix_last_matrix_report.as_ref().map(|report| {
            json!({
                "run_id": report.run_id,
                "baseline_core": report.baseline_core,
                "target_count": report.targets.len(),
                "helix_completed_targets": matrix_helix_summary.map(|summary| summary.completed_targets),
                "helix_failed_targets": matrix_helix_summary.map(|summary| summary.failed_targets),
                "helix_median_connect_latency_ms": matrix_helix_summary.and_then(|summary| summary.median_connect_latency_ms),
                "helix_median_first_byte_latency_ms": matrix_helix_summary.and_then(|summary| summary.median_first_byte_latency_ms),
                "helix_median_open_to_first_byte_gap_ms": matrix_helix_summary.and_then(|summary| summary.median_open_to_first_byte_gap_ms),
                "helix_average_relative_open_to_first_byte_gap_ratio": matrix_helix_summary.and_then(|summary| summary.average_relative_open_to_first_byte_gap_ratio),
                "helix_average_throughput_kbps": matrix_helix_summary.and_then(|summary| summary.average_throughput_kbps),
            })
        }),
        "last_recovery": store_data.helix_last_recovery_report.as_ref().map(|report| {
            json!({
                "run_id": report.run_id,
                "mode": report.mode,
                "recovered": report.recovered,
                "route_before": report.route_before,
                "route_after": report.route_after,
                "ready_recovery_latency_ms": report.ready_recovery_latency_ms,
                "proxy_ready_latency_ms": report.proxy_ready_latency_ms,
                "proxy_ready_open_to_first_byte_gap_ms": report.proxy_ready_open_to_first_byte_gap_ms,
                "action_recovery_latency_ms": report.action.as_ref().and_then(|action| action.recovery_latency_ms),
                "action_message": report.action.as_ref().and_then(|action| action.message.clone()),
                "post_recovery_gap_ms": report
                    .post_recovery_benchmark
                    .as_ref()
                    .and_then(|benchmark| benchmark.median_open_to_first_byte_gap_ms),
                "post_recovery_queue_pressure": report
                    .post_recovery_benchmark
                    .as_ref()
                    .and_then(|benchmark| benchmark.helix_queue_pressure.clone()),
            })
        }),
    })
}

pub fn record_event(
    app: &AppHandle,
    level: DiagnosticLevel,
    source: impl Into<String>,
    message: impl Into<String>,
    payload: Value,
) -> Result<(), AppError> {
    let entry = DiagnosticEntry {
        id: uuid::Uuid::new_v4().to_string(),
        timestamp: Utc::now().to_rfc3339(),
        level: level.as_str().to_string(),
        source: source.into(),
        message: message.into(),
        payload,
    };

    let serialized = serde_json::to_string(&entry)?;
    append_line_with_rotation(
        &diagnostics_file_path(app, EVENTS_LOG_NAME)?,
        &diagnostics_file_path(app, EVENTS_LOG_ROTATED_NAME)?,
        &(serialized + "\n"),
    )?;
    let _ = app.emit("desktop-diagnostic", entry);
    Ok(())
}

pub fn append_core_runtime_log(
    app: &AppHandle,
    core_name: &str,
    stream: &str,
    line: &str,
) -> Result<(), AppError> {
    let sanitized = sanitize_log_line(line);
    let timestamp = Utc::now().to_rfc3339();
    let formatted = format!("[{timestamp}] [{core_name}/{stream}] {sanitized}\n");
    let (current_path, rotated_path) = if core_name == "helix" {
        (
            diagnostics_file_path(app, HELIX_RUNTIME_LOG_NAME)?,
            diagnostics_file_path(app, HELIX_RUNTIME_LOG_ROTATED_NAME)?,
        )
    } else {
        (
            diagnostics_file_path(app, CORE_RUNTIME_LOG_NAME)?,
            diagnostics_file_path(app, CORE_RUNTIME_LOG_ROTATED_NAME)?,
        )
    };

    append_line_with_rotation(&current_path, &rotated_path, &formatted)?;

    if should_promote_raw_log_to_event(stream, line) {
        let payload = json!({
            "core": core_name,
            "stream": stream,
        });
        let level = classify_log_level(stream, line);
        let message = sanitized.chars().take(240).collect::<String>();
        let _ = record_event(app, level, format!("runtime.{core_name}"), message, payload);
    }

    Ok(())
}

pub async fn collect_snapshot(
    app: &AppHandle,
    connection_status: ConnectionStatus,
) -> Result<DesktopDiagnosticsSnapshot, AppError> {
    let store_data = store::load_store(app)?;
    let app_dir = store::get_app_dir(app)?;
    let diagnostics_dir = diagnostics_dir(app)?;
    let support_bundle_dir = support_bundle_dir(app)?;
    let store_path = store::get_store_path(app)?;
    let live_health = fetch_live_helix_health(&store_data).await;
    let live_telemetry = fetch_live_helix_telemetry(&store_data).await;
    let lifecycle = store_data.last_startup_recovery.clone().unwrap_or_default();

    Ok(DesktopDiagnosticsSnapshot {
        collected_at: Utc::now().to_rfc3339(),
        app_name: "CyberVPN Desktop".to_string(),
        app_version: env!("CARGO_PKG_VERSION").to_string(),
        package_name: env!("CARGO_PKG_NAME").to_string(),
        platform: std::env::consts::OS.to_string(),
        app_dir: app_dir.display().to_string(),
        diagnostics_dir: diagnostics_dir.display().to_string(),
        support_bundle_dir: support_bundle_dir.display().to_string(),
        store_path: store_path.display().to_string(),
        lifecycle,
        connection_status,
        active_core: store_data.active_core.clone(),
        active_profile_id: store_data.active_profile_id.clone(),
        local_ip: get_local_ip(),
        local_socks_port: store_data.local_socks_port,
        allow_lan: store_data.allow_lan,
        profile_count: store_data.profiles.len(),
        routing_rule_count: store_data.routing_rules.len(),
        subscription_count: store_data.subscriptions.len(),
        split_tunneling_mode: store_data.split_tunneling_mode.clone(),
        split_tunneling_app_count: store_data.split_tunneling_apps.len(),
        smart_connect_enabled: store_data.smart_connect_enabled,
        stealth_mode_enabled: store_data.stealth_mode_enabled,
        pqc_enforcement_mode: store_data.pqc_enforcement_mode,
        privacy_shield_level: store_data.privacy_shield_level.clone(),
        last_benchmark_run_id: store_data
            .helix_last_benchmark_report
            .as_ref()
            .map(|report| report.run_id.clone()),
        last_comparison_run_id: store_data
            .helix_last_comparison_report
            .as_ref()
            .map(|report| report.run_id.clone()),
        last_matrix_run_id: store_data
            .helix_last_matrix_report
            .as_ref()
            .map(|report| report.run_id.clone()),
        last_recovery_run_id: store_data
            .helix_last_recovery_report
            .as_ref()
            .map(|report| report.run_id.clone()),
        helix: HelixDiagnosticsSnapshot {
            backend_url: store_data.helix_backend_url.clone(),
            desktop_client_id: store_data.helix_desktop_client_id.clone(),
            last_fallback_reason: store_data.helix_last_fallback_reason.clone(),
            last_manifest_version_id: store_data
                .helix_last_manifest
                .as_ref()
                .map(|manifest| manifest.manifest_version_id.clone()),
            last_rollout_id: store_data
                .helix_last_manifest
                .as_ref()
                .map(|manifest| manifest.manifest.rollout_id.clone()),
            transport_profile_id: store_data.helix_last_manifest.as_ref().map(|manifest| {
                manifest
                    .manifest
                    .transport_profile
                    .transport_profile_id
                    .clone()
            }),
            prepared_route_count: store_data
                .helix_last_prepared_runtime
                .as_ref()
                .map(|runtime| runtime.route_count),
            health_url: store_data
                .helix_last_prepared_runtime
                .as_ref()
                .map(|runtime| runtime.health_url.clone()),
            proxy_url: store_data
                .helix_last_prepared_runtime
                .as_ref()
                .map(|runtime| runtime.proxy_url.clone()),
            live_health,
            live_telemetry,
        },
        recent_entries: load_recent_entries(app, DEFAULT_RECENT_LIMIT)?,
        core_log_tail: read_log_tail(
            &diagnostics_file_path(app, CORE_RUNTIME_LOG_NAME)?,
            &diagnostics_file_path(app, CORE_RUNTIME_LOG_ROTATED_NAME)?,
            DEFAULT_LOG_TAIL_LIMIT,
        )?,
        helix_log_tail: read_log_tail(
            &diagnostics_file_path(app, HELIX_RUNTIME_LOG_NAME)?,
            &diagnostics_file_path(app, HELIX_RUNTIME_LOG_ROTATED_NAME)?,
            DEFAULT_LOG_TAIL_LIMIT,
        )?,
    })
}

pub async fn export_support_bundle(
    app: &AppHandle,
    connection_status: ConnectionStatus,
) -> Result<SupportBundleExportResult, AppError> {
    let snapshot = collect_snapshot(app, connection_status).await?;
    let store_data = store::load_store(app)?;
    let support_dir = support_bundle_dir(app)?;
    fs::create_dir_all(&support_dir)?;

    let archive_name = format!(
        "cybervpn-support-{}.zip",
        Utc::now().format("%Y%m%d-%H%M%S")
    );
    let archive_path = support_dir.join(archive_name);
    let file = fs::File::create(&archive_path)?;
    let mut zip = zip::ZipWriter::new(file);
    let options = zip::write::SimpleFileOptions::default()
        .compression_method(zip::CompressionMethod::Deflated);

    let report = SupportBundleReport {
        snapshot: snapshot.clone(),
        profiles: redact_profiles(&store_data.profiles),
        subscriptions: redact_subscriptions(&store_data.subscriptions),
        helix_manifest: store_data
            .helix_last_manifest
            .as_ref()
            .map(redact_helix_manifest),
        helix_runtime: store_data
            .helix_last_prepared_runtime
            .as_ref()
            .map(redact_prepared_runtime),
        helix_performance_summary: build_helix_performance_summary(&snapshot, &store_data),
        last_benchmark_report: store_data.helix_last_benchmark_report.clone(),
        last_comparison_report: store_data.helix_last_comparison_report.clone(),
        last_matrix_report: store_data.helix_last_matrix_report.clone(),
        last_recovery_report: store_data.helix_last_recovery_report.clone(),
    };

    write_zip_json(&mut zip, "support-report.json", &report, options)?;
    write_zip_json(
        &mut zip,
        "helix-performance-summary.json",
        &report.helix_performance_summary,
        options,
    )?;

    maybe_write_file_into_zip(
        &mut zip,
        &diagnostics_file_path(app, EVENTS_LOG_NAME)?,
        "logs/events.jsonl",
        options,
    )?;
    maybe_write_file_into_zip(
        &mut zip,
        &diagnostics_file_path(app, EVENTS_LOG_ROTATED_NAME)?,
        "logs/events.previous.jsonl",
        options,
    )?;
    maybe_write_file_into_zip(
        &mut zip,
        &diagnostics_file_path(app, CORE_RUNTIME_LOG_NAME)?,
        "logs/core-runtime.log",
        options,
    )?;
    maybe_write_file_into_zip(
        &mut zip,
        &diagnostics_file_path(app, CORE_RUNTIME_LOG_ROTATED_NAME)?,
        "logs/core-runtime.previous.log",
        options,
    )?;
    maybe_write_file_into_zip(
        &mut zip,
        &diagnostics_file_path(app, HELIX_RUNTIME_LOG_NAME)?,
        "logs/helix-runtime.log",
        options,
    )?;
    maybe_write_file_into_zip(
        &mut zip,
        &diagnostics_file_path(app, HELIX_RUNTIME_LOG_ROTATED_NAME)?,
        "logs/helix-runtime.previous.log",
        options,
    )?;
    maybe_write_file_into_zip(
        &mut zip,
        &app.path()
            .app_data_dir()
            .map_err(|error| AppError::System(format!("Failed to resolve app data dir: {error}")))?
            .join("usage_history.json"),
        "logs/usage_history.json",
        options,
    )?;

    zip.finish()?;

    let includes_core_log =
        archive_contains_any(app, &[CORE_RUNTIME_LOG_NAME, CORE_RUNTIME_LOG_ROTATED_NAME])?;
    let includes_helix_log = archive_contains_any(
        app,
        &[HELIX_RUNTIME_LOG_NAME, HELIX_RUNTIME_LOG_ROTATED_NAME],
    )?;

    let result = SupportBundleExportResult {
        archive_path: archive_path.display().to_string(),
        exported_at: Utc::now().to_rfc3339(),
        event_count: snapshot.recent_entries.len(),
        includes_core_log,
        includes_helix_log,
    };

    let _ = record_event(
        app,
        DiagnosticLevel::Info,
        "diagnostics.export",
        "Desktop support bundle exported",
        json!({
            "archive_path": result.archive_path,
            "event_count": result.event_count,
            "includes_core_log": result.includes_core_log,
            "includes_helix_log": result.includes_helix_log,
        }),
    );

    Ok(result)
}

pub fn clear_diagnostics_logs(app: &AppHandle) -> Result<(), AppError> {
    for name in [
        EVENTS_LOG_NAME,
        EVENTS_LOG_ROTATED_NAME,
        CORE_RUNTIME_LOG_NAME,
        CORE_RUNTIME_LOG_ROTATED_NAME,
        HELIX_RUNTIME_LOG_NAME,
        HELIX_RUNTIME_LOG_ROTATED_NAME,
    ] {
        let path = diagnostics_file_path(app, name)?;
        if path.exists() {
            fs::remove_file(path)?;
        }
    }

    let _ = record_event(
        app,
        DiagnosticLevel::Info,
        "diagnostics",
        "Desktop diagnostics logs cleared",
        json!({}),
    );

    Ok(())
}

fn redact_profiles(profiles: &[ProxyNode]) -> Vec<RedactedProfileSummary> {
    profiles
        .iter()
        .map(|profile| RedactedProfileSummary {
            id: profile.id.clone(),
            name: profile.name.clone(),
            server: profile.server.clone(),
            port: profile.port,
            protocol: profile.protocol.clone(),
            network: profile.network.clone(),
            tls: profile.tls.clone(),
            sni: profile.sni.clone(),
            fingerprint: profile.fingerprint.clone(),
            group_id: profile.group_id.clone(),
            ping: profile.ping,
            pqc_enabled: profile.pqc_enabled,
        })
        .collect()
}

fn redact_subscriptions(subscriptions: &[Subscription]) -> Vec<RedactedSubscriptionSummary> {
    subscriptions
        .iter()
        .map(|subscription| RedactedSubscriptionSummary {
            id: subscription.id.clone(),
            name: subscription.name.clone(),
            host: url::Url::parse(&subscription.url)
                .ok()
                .and_then(|parsed| parsed.host_str().map(|host| host.to_string())),
            auto_update: subscription.auto_update,
            last_updated: subscription.last_updated,
        })
        .collect()
}

fn redact_helix_manifest(manifest: &HelixResolvedManifest) -> RedactedHelixManifest {
    RedactedHelixManifest {
        manifest_version_id: manifest.manifest_version_id.clone(),
        manifest_id: manifest.manifest.manifest_id.clone(),
        rollout_id: manifest.manifest.rollout_id.clone(),
        transport_profile_id: manifest
            .manifest
            .transport_profile
            .transport_profile_id
            .clone(),
        profile_family: manifest.manifest.transport_profile.profile_family.clone(),
        profile_version: manifest.manifest.transport_profile.profile_version,
        policy_version: manifest.manifest.transport_profile.policy_version,
        route_count: manifest.manifest.routes.len(),
        fallback_core: manifest.manifest.capability_profile.fallback_core.clone(),
        metrics_namespace: manifest.manifest.observability.metrics_namespace.clone(),
        trace_id: manifest.manifest.observability.trace_id.clone(),
    }
}

fn redact_prepared_runtime(runtime: &HelixPreparedRuntime) -> RedactedPreparedRuntime {
    RedactedPreparedRuntime {
        manifest_id: runtime.manifest_id.clone(),
        manifest_version_id: runtime.manifest_version_id.clone(),
        rollout_id: runtime.rollout_id.clone(),
        transport_profile_id: runtime.transport_profile_id.clone(),
        config_path: runtime.config_path.clone(),
        sidecar_path: runtime.sidecar_path.clone(),
        binary_available: runtime.binary_available,
        health_url: runtime.health_url.clone(),
        proxy_url: runtime.proxy_url.clone(),
        fallback_core: runtime.fallback_core.clone(),
        route_count: runtime.route_count,
        startup_timeout_seconds: runtime.startup_timeout_seconds,
    }
}

async fn fetch_live_helix_health(store_data: &AppDataStore) -> Option<HelixSidecarHealth> {
    let health_url = store_data
        .helix_last_prepared_runtime
        .as_ref()
        .map(|runtime| runtime.health_url.clone())?;

    let client = reqwest::Client::builder()
        .timeout(std::time::Duration::from_millis(1200))
        .build()
        .ok()?;

    let response = client.get(&health_url).send().await.ok()?;
    let response = response.error_for_status().ok()?;
    response.json::<HelixSidecarHealth>().await.ok()
}

async fn fetch_live_helix_telemetry(store_data: &AppDataStore) -> Option<HelixSidecarTelemetry> {
    let health_url = store_data
        .helix_last_prepared_runtime
        .as_ref()
        .map(|runtime| runtime.health_url.clone())?;
    let telemetry_url = sidecar_endpoint_url(&health_url, "/telemetry")?;

    let client = reqwest::Client::builder()
        .timeout(std::time::Duration::from_millis(1200))
        .build()
        .ok()?;

    let response = client.get(telemetry_url).send().await.ok()?;
    let response = response.error_for_status().ok()?;
    response.json::<HelixSidecarTelemetry>().await.ok()
}

fn sidecar_endpoint_url(health_url: &str, endpoint_path: &str) -> Option<String> {
    let mut url = url::Url::parse(health_url).ok()?;
    url.set_path(endpoint_path);
    Some(url.to_string())
}

fn diagnostics_dir(app: &AppHandle) -> Result<PathBuf, AppError> {
    let dir = store::get_app_dir(app)?.join(DIAGNOSTICS_DIR_NAME);
    if !dir.exists() {
        fs::create_dir_all(&dir)?;
    }
    Ok(dir)
}

fn support_bundle_dir(app: &AppHandle) -> Result<PathBuf, AppError> {
    let dir = store::get_app_dir(app)?.join(SUPPORT_BUNDLES_DIR_NAME);
    if !dir.exists() {
        fs::create_dir_all(&dir)?;
    }
    Ok(dir)
}

fn diagnostics_file_path(app: &AppHandle, file_name: &str) -> Result<PathBuf, AppError> {
    Ok(diagnostics_dir(app)?.join(file_name))
}

fn append_line_with_rotation(
    current_path: &Path,
    rotated_path: &Path,
    line: &str,
) -> Result<(), AppError> {
    if let Some(parent) = current_path.parent() {
        fs::create_dir_all(parent)?;
    }

    if current_path.exists() {
        let current_size = fs::metadata(current_path)?.len();
        if current_size >= MAX_LOG_BYTES {
            if rotated_path.exists() {
                fs::remove_file(rotated_path)?;
            }
            fs::rename(current_path, rotated_path)?;
        }
    }

    let mut file = OpenOptions::new()
        .create(true)
        .append(true)
        .open(current_path)?;
    file.write_all(line.as_bytes())?;
    Ok(())
}

fn sanitize_log_line(line: &str) -> String {
    let trimmed = line.trim();
    let mut sanitized = trimmed.to_string();
    if sanitized.len() > MAX_LOG_LINE_LEN {
        sanitized.truncate(MAX_LOG_LINE_LEN);
        sanitized.push_str(" ...[truncated]");
    }
    sanitized
}

fn should_promote_raw_log_to_event(stream: &str, line: &str) -> bool {
    let lowered = line.to_ascii_lowercase();
    stream.eq_ignore_ascii_case("stderr")
        || lowered.contains("error")
        || lowered.contains("panic")
        || lowered.contains("failed")
        || lowered.contains("degraded")
        || lowered.contains("fallback")
}

fn classify_log_level(stream: &str, line: &str) -> DiagnosticLevel {
    let lowered = line.to_ascii_lowercase();
    if stream.eq_ignore_ascii_case("stderr")
        || lowered.contains("panic")
        || lowered.contains("fatal")
        || lowered.contains("error")
        || lowered.contains("failed")
    {
        DiagnosticLevel::Error
    } else if lowered.contains("warn")
        || lowered.contains("degraded")
        || lowered.contains("fallback")
    {
        DiagnosticLevel::Warn
    } else {
        DiagnosticLevel::Info
    }
}

fn default_payload() -> Value {
    Value::Object(Default::default())
}

fn load_recent_entries(app: &AppHandle, limit: usize) -> Result<Vec<DiagnosticEntry>, AppError> {
    let mut entries = Vec::new();
    for path in [
        diagnostics_file_path(app, EVENTS_LOG_ROTATED_NAME)?,
        diagnostics_file_path(app, EVENTS_LOG_NAME)?,
    ] {
        if !path.exists() {
            continue;
        }

        let contents = fs::read_to_string(path)?;
        for line in contents.lines() {
            if line.trim().is_empty() {
                continue;
            }
            if let Ok(entry) = serde_json::from_str::<DiagnosticEntry>(line) {
                entries.push(entry);
            }
        }
    }

    if entries.len() > limit {
        entries = entries.split_off(entries.len() - limit);
    }

    entries.reverse();
    Ok(entries)
}

fn read_log_tail(
    current_path: &Path,
    rotated_path: &Path,
    limit: usize,
) -> Result<Vec<String>, AppError> {
    let mut lines = Vec::new();
    for path in [rotated_path, current_path] {
        if !path.exists() {
            continue;
        }

        let contents = fs::read_to_string(path)?;
        for line in contents.lines() {
            if !line.trim().is_empty() {
                lines.push(line.to_string());
            }
        }
    }

    if lines.len() > limit {
        lines = lines.split_off(lines.len() - limit);
    }

    lines.reverse();
    Ok(lines)
}

fn write_zip_json<T: Serialize>(
    zip: &mut zip::ZipWriter<fs::File>,
    path: &str,
    value: &T,
    options: zip::write::SimpleFileOptions,
) -> Result<(), AppError> {
    zip.start_file(path, options)?;
    let payload = serde_json::to_vec_pretty(value)?;
    zip.write_all(&payload)?;
    Ok(())
}

fn maybe_write_file_into_zip(
    zip: &mut zip::ZipWriter<fs::File>,
    source_path: &Path,
    archive_path: &str,
    options: zip::write::SimpleFileOptions,
) -> Result<(), AppError> {
    if !source_path.exists() {
        return Ok(());
    }

    let mut contents = Vec::new();
    fs::File::open(source_path)?.read_to_end(&mut contents)?;
    zip.start_file(archive_path, options)?;
    zip.write_all(&contents)?;
    Ok(())
}

fn archive_contains_any(app: &AppHandle, files: &[&str]) -> Result<bool, AppError> {
    for file in files {
        if diagnostics_file_path(app, file)?.exists() {
            return Ok(true);
        }
    }
    Ok(false)
}
