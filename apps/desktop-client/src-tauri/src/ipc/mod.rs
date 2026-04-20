pub mod models;

use crate::engine::error::AppError;
use crate::engine::manager::ProcessManager;
use crate::engine::parser;
use crate::engine::store;
use crate::engine::{helix, helix::client};
use models::{ConnectionStatus, ProfileGroup, ProxyNode};
use std::sync::{
    atomic::{AtomicU64, Ordering},
    Arc,
};
use std::time::{SystemTime, UNIX_EPOCH};
use tauri::{AppHandle, Emitter, Manager, State};
use tokio::sync::RwLock;

pub struct AppState {
    pub status: RwLock<ConnectionStatus>,
    pub process_manager: Arc<ProcessManager>,
    pub connection_attempt: AtomicU64,
}

fn emit_connection_lifecycle_event(app: &AppHandle, event: &str, payload: serde_json::Value) {
    let _ = app.emit(
        "connection-lifecycle",
        serde_json::json!({
            "event": event,
            "payload": payload,
        }),
    );
}

fn emit_connection_options_event(app: &AppHandle, options: &models::LastConnectionOptions) {
    let _ = app.emit("connection-options", options.clone());
}

fn begin_connection_attempt(state: &AppState) -> u64 {
    state.connection_attempt.fetch_add(1, Ordering::SeqCst) + 1
}

fn invalidate_connection_attempts(state: &AppState) -> u64 {
    state.connection_attempt.fetch_add(1, Ordering::SeqCst) + 1
}

fn is_connection_attempt_current(state: &AppState, attempt_id: u64) -> bool {
    state.connection_attempt.load(Ordering::SeqCst) == attempt_id
}

pub(crate) fn emit_connection_status_event(
    app: &AppHandle,
    status: ConnectionStatus,
) -> Result<(), AppError> {
    app.emit("connection-status", status)?;
    let _ = crate::tray::setup(app);
    Ok(())
}

fn current_timestamp_ms() -> Option<u64> {
    SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .ok()
        .and_then(|duration| u64::try_from(duration.as_millis()).ok())
}

fn sanitize_source_surface(source_surface: Option<&str>, default_surface: &str) -> String {
    let candidate = source_surface
        .unwrap_or(default_surface)
        .trim()
        .to_lowercase();
    if candidate.is_empty() {
        return default_surface.to_string();
    }

    let sanitized = candidate
        .chars()
        .filter(|character| {
            character.is_ascii_alphanumeric() || *character == '-' || *character == '_'
        })
        .take(32)
        .collect::<String>();

    if sanitized.is_empty() {
        default_surface.to_string()
    } else {
        sanitized
    }
}

fn derive_last_connection_options(
    store_data: &store::AppDataStore,
) -> models::LastConnectionOptions {
    let mut options = store_data.last_connection_options.clone();
    let profile_exists = |profile_id: &str| {
        store_data
            .profiles
            .iter()
            .any(|profile| profile.id == profile_id)
    };
    if options.active_core.trim().is_empty() {
        options.active_core = store_data.active_core.clone();
    }
    if options.profile_id.is_none() {
        options.profile_id = store_data.active_profile_id.clone();
    }
    options.favorite_profile_ids = options
        .favorite_profile_ids
        .into_iter()
        .filter(|profile_id| profile_exists(profile_id))
        .collect();
    if options
        .last_stable_profile_id
        .as_deref()
        .is_some_and(|profile_id| !profile_exists(profile_id))
    {
        options.last_stable_profile_id = None;
        options.last_stable_connected_at = None;
    }
    options
}

fn persist_last_connection_options<F>(
    app: &AppHandle,
    mutator: F,
) -> Result<models::LastConnectionOptions, AppError>
where
    F: FnOnce(&mut store::AppDataStore, &mut models::LastConnectionOptions),
{
    let mut store_data = store::load_store(app)?;
    let mut options = derive_last_connection_options(&store_data);
    mutator(&mut store_data, &mut options);
    if options.active_core.trim().is_empty() {
        options.active_core = store_data.active_core.clone();
    }
    store_data.last_connection_options = options.clone();
    store::save_store(app, &store_data)?;
    emit_connection_options_event(app, &options);
    Ok(options)
}

fn resolve_profile_id_for_connect(
    store_data: &store::AppDataStore,
    preferred_profile_id: Option<&str>,
) -> Option<String> {
    let profile_exists = |profile_id: &str| {
        store_data
            .profiles
            .iter()
            .any(|profile| profile.id == profile_id)
    };

    if let Some(profile_id) = preferred_profile_id.filter(|profile_id| profile_exists(profile_id)) {
        return Some(profile_id.to_string());
    }

    if let Some(profile_id) = store_data
        .active_profile_id
        .as_deref()
        .filter(|profile_id| profile_exists(profile_id))
    {
        return Some(profile_id.to_string());
    }

    if let Some(profile_id) = store_data
        .last_connection_options
        .profile_id
        .as_deref()
        .filter(|profile_id| profile_exists(profile_id))
    {
        return Some(profile_id.to_string());
    }

    store_data
        .profiles
        .first()
        .map(|profile| profile.id.clone())
}

pub(crate) async fn connect_with_last_options(
    source_surface: &str,
    app: AppHandle,
    state: State<'_, AppState>,
) -> Result<(), AppError> {
    let store_data = store::load_store(&app)?;
    let profile_id =
        resolve_profile_id_for_connect(&store_data, None).ok_or_else(|| AppError::Actionable {
            error: "No saved desktop profile is available for reconnect".to_string(),
            resolution:
                "Import or create a profile before using tray, hotkey, or remote reconnect."
                    .to_string(),
        })?;
    let tun_mode = store_data.last_connection_options.tun_mode;
    let system_proxy = store_data.last_connection_options.system_proxy;
    connect_profile_internal(
        profile_id,
        tun_mode,
        system_proxy,
        source_surface,
        app,
        state,
    )
    .await
}

async fn reset_connection_state(
    app: &AppHandle,
    state: &State<'_, AppState>,
) -> Result<(), AppError> {
    let previous_status = state.status.read().await.clone();
    let mut store_data = store::load_store(app)?;
    if store_data.active_profile_id.is_some() {
        store_data.active_profile_id = None;
        store::save_store(app, &store_data)?;
    }
    let _ = crate::engine::sys::stats::flush_session(app);
    if state.process_manager.is_running().await {
        state.process_manager.stop().await?;
    }
    crate::engine::sysproxy::clear_system_proxy().ok();

    let mut status_lock = state.status.write().await;
    status_lock.status = "disconnected".to_string();
    status_lock.active_id = None;
    status_lock.active_core = None;
    status_lock.proxy_url = None;
    status_lock.up_bytes = 0;
    status_lock.down_bytes = 0;
    status_lock.message = None;
    emit_connection_status_event(app, status_lock.clone())?;

    if previous_status.status != "disconnected" {
        let _ = crate::engine::diagnostics::record_event(
            app,
            crate::engine::diagnostics::DiagnosticLevel::Info,
            "vpn.disconnect",
            "Connection state reset to disconnected",
            serde_json::json!({
                "previous_status": previous_status.status,
                "previous_core": previous_status.active_core,
                "previous_proxy_url": previous_status.proxy_url,
            }),
        );
    }

    emit_connection_lifecycle_event(
        app,
        "disconnect_completed",
        serde_json::json!({
            "status": "disconnected",
        }),
    );

    Ok(())
}

fn spawn_helix_runtime_event(
    app: &AppHandle,
    report: crate::engine::helix::config::HelixRuntimeEventReport,
) {
    let app_handle = app.clone();
    tauri::async_runtime::spawn(async move {
        if let Err(error) = crate::engine::helix::report_runtime_event(&app_handle, report).await {
            eprintln!("Helix runtime event report failed: {}", error);
        }
    });
}

fn helix_queue_pressure_json(
    queue_pressure: Option<&crate::engine::helix::config::HelixQueuePressureSummary>,
) -> Option<serde_json::Value> {
    queue_pressure.map(|pressure| {
        serde_json::json!({
            "frame_queue_depth": pressure.frame_queue_depth,
            "frame_queue_peak": pressure.frame_queue_peak,
            "active_streams": pressure.active_streams,
            "pending_open_streams": pressure.pending_open_streams,
            "max_concurrent_streams": pressure.max_concurrent_streams,
            "recent_rtt_p50_ms": pressure.recent_rtt_p50_ms,
            "recent_rtt_p95_ms": pressure.recent_rtt_p95_ms,
            "recent_stream_peak_frame_queue_depth": pressure.recent_stream_peak_frame_queue_depth,
            "recent_stream_peak_inbound_queue_depth": pressure.recent_stream_peak_inbound_queue_depth,
        })
    })
}

fn helix_continuity_json(
    continuity: Option<&crate::engine::helix::config::HelixContinuitySummary>,
) -> Option<serde_json::Value> {
    continuity.map(|continuity| {
        serde_json::json!({
            "grace_active": continuity.grace_active,
            "grace_route_endpoint_ref": continuity.grace_route_endpoint_ref,
            "grace_remaining_ms": continuity.grace_remaining_ms,
            "active_streams": continuity.active_streams,
            "pending_open_streams": continuity.pending_open_streams,
            "active_route_quarantined": continuity.active_route_quarantined,
            "active_route_quarantine_remaining_ms": continuity.active_route_quarantine_remaining_ms,
            "continuity_grace_entries": continuity.continuity_grace_entries,
            "successful_continuity_recovers": continuity.successful_continuity_recovers,
            "failed_continuity_recovers": continuity.failed_continuity_recovers,
            "last_continuity_recovery_ms": continuity.last_continuity_recovery_ms,
            "successful_cross_route_recovers": continuity.successful_cross_route_recovers,
            "last_cross_route_recovery_ms": continuity.last_cross_route_recovery_ms,
        })
    })
}

fn i32_from_usize(value: usize) -> i32 {
    i32::try_from(value).unwrap_or(i32::MAX)
}

fn i32_from_u32(value: u32) -> i32 {
    i32::try_from(value).unwrap_or(i32::MAX)
}

fn default_canonical_order_limit() -> u32 {
    20
}

fn normalize_canonical_order_limit(limit: Option<u32>) -> u32 {
    limit
        .unwrap_or_else(default_canonical_order_limit)
        .clamp(1, 50)
}

struct HelixBenchmarkPayloadArgs<'a> {
    benchmark_kind: &'a str,
    baseline_core: Option<&'a str>,
    target_count: Option<usize>,
    successful_targets: Option<usize>,
    attempts: Option<u32>,
    successes: Option<u32>,
    failures: Option<u32>,
    throughput_kbps: Option<f64>,
    relative_throughput_ratio_vs_baseline: Option<f64>,
    median_connect_latency_ms: Option<i32>,
    median_first_byte_latency_ms: Option<i32>,
    median_open_to_first_byte_gap_ms: Option<i32>,
    p95_open_to_first_byte_gap_ms: Option<i32>,
    relative_open_to_first_byte_gap_ratio_vs_baseline: Option<f64>,
    queue_pressure: Option<&'a crate::engine::helix::config::HelixQueuePressureSummary>,
}

fn build_helix_benchmark_payload(
    args: HelixBenchmarkPayloadArgs<'_>,
) -> crate::engine::helix::config::HelixRuntimeEventPayload {
    crate::engine::helix::config::HelixRuntimeEventPayload {
        stage: Some("benchmark".to_string()),
        runtime: Some("embedded-sidecar".to_string()),
        requested_core: Some("helix".to_string()),
        benchmark: Some(
            crate::engine::helix::config::HelixRuntimeEventBenchmarkEvidence {
                benchmark_kind: Some(args.benchmark_kind.to_string()),
                baseline_core: args.baseline_core.map(ToOwned::to_owned),
                target_count: args.target_count.map(i32_from_usize),
                successful_targets: args.successful_targets.map(i32_from_usize),
                attempts: args.attempts.map(i32_from_u32),
                successes: args.successes.map(i32_from_u32),
                failures: args.failures.map(i32_from_u32),
                throughput_kbps: args.throughput_kbps,
                relative_throughput_ratio_vs_baseline: args.relative_throughput_ratio_vs_baseline,
                median_connect_latency_ms: args.median_connect_latency_ms,
                median_first_byte_latency_ms: args.median_first_byte_latency_ms,
                median_open_to_first_byte_gap_ms: args.median_open_to_first_byte_gap_ms,
                p95_open_to_first_byte_gap_ms: args.p95_open_to_first_byte_gap_ms,
                relative_open_to_first_byte_gap_ratio_vs_baseline: args
                    .relative_open_to_first_byte_gap_ratio_vs_baseline,
                frame_queue_peak: args
                    .queue_pressure
                    .map(|pressure| pressure.frame_queue_peak),
                recent_rtt_p95_ms: args
                    .queue_pressure
                    .and_then(|pressure| pressure.recent_rtt_p95_ms),
                active_streams: args.queue_pressure.map(|pressure| pressure.active_streams),
                pending_open_streams: args
                    .queue_pressure
                    .map(|pressure| pressure.pending_open_streams),
            },
        ),
        ..Default::default()
    }
}

fn report_helix_benchmark_summary(
    app: &AppHandle,
    report: &crate::engine::helix::config::TransportBenchmarkReport,
) {
    if report.active_core != "helix" {
        return;
    }

    spawn_helix_runtime_event(
        app,
        crate::engine::helix::config::HelixRuntimeEventReport {
            event_kind: crate::engine::helix::config::HelixRuntimeEventKind::Benchmark,
            active_core: "helix".to_string(),
            fallback_core: None,
            latency_ms: report.median_first_byte_latency_ms,
            route_count: None,
            reason: Some("single benchmark evidence".to_string()),
            payload: build_helix_benchmark_payload(HelixBenchmarkPayloadArgs {
                benchmark_kind: "single",
                baseline_core: None,
                target_count: Some(1),
                successful_targets: Some(1),
                attempts: Some(report.attempts),
                successes: Some(report.successes),
                failures: Some(report.failures),
                throughput_kbps: report.average_throughput_kbps,
                relative_throughput_ratio_vs_baseline: None,
                median_connect_latency_ms: report.median_connect_latency_ms,
                median_first_byte_latency_ms: report.median_first_byte_latency_ms,
                median_open_to_first_byte_gap_ms: report.median_open_to_first_byte_gap_ms,
                p95_open_to_first_byte_gap_ms: report.p95_open_to_first_byte_gap_ms,
                relative_open_to_first_byte_gap_ratio_vs_baseline: None,
                queue_pressure: report.helix_queue_pressure.as_ref(),
            }),
        },
    );
}

fn report_helix_comparison_summary(
    app: &AppHandle,
    report: &crate::engine::helix::config::TransportBenchmarkComparisonReport,
) {
    let Some(entry) = report.entries.iter().find(|entry| {
        entry.effective_core.as_deref() == Some("helix") || entry.requested_core == "helix"
    }) else {
        return;
    };
    let Some(benchmark) = entry.benchmark.as_ref() else {
        return;
    };

    spawn_helix_runtime_event(
        app,
        crate::engine::helix::config::HelixRuntimeEventReport {
            event_kind: crate::engine::helix::config::HelixRuntimeEventKind::Benchmark,
            active_core: "helix".to_string(),
            fallback_core: None,
            latency_ms: benchmark.median_first_byte_latency_ms,
            route_count: None,
            reason: Some("comparison benchmark evidence".to_string()),
            payload: build_helix_benchmark_payload(HelixBenchmarkPayloadArgs {
                benchmark_kind: "comparison",
                baseline_core: report.baseline_core.as_deref(),
                target_count: Some(1),
                successful_targets: Some(1),
                attempts: Some(benchmark.attempts),
                successes: Some(benchmark.successes),
                failures: Some(benchmark.failures),
                throughput_kbps: benchmark.average_throughput_kbps,
                relative_throughput_ratio_vs_baseline: entry.relative_throughput_ratio,
                median_connect_latency_ms: benchmark.median_connect_latency_ms,
                median_first_byte_latency_ms: benchmark.median_first_byte_latency_ms,
                median_open_to_first_byte_gap_ms: benchmark.median_open_to_first_byte_gap_ms,
                p95_open_to_first_byte_gap_ms: benchmark.p95_open_to_first_byte_gap_ms,
                relative_open_to_first_byte_gap_ratio_vs_baseline: entry
                    .relative_open_to_first_byte_gap_ratio,
                queue_pressure: benchmark.helix_queue_pressure.as_ref(),
            }),
        },
    );
}

fn report_helix_matrix_summary(
    app: &AppHandle,
    report: &crate::engine::helix::config::TransportBenchmarkMatrixReport,
) {
    let Some(summary) = report
        .core_summaries
        .iter()
        .find(|summary| summary.core == "helix")
    else {
        return;
    };

    if summary.completed_targets == 0 {
        return;
    }

    spawn_helix_runtime_event(
        app,
        crate::engine::helix::config::HelixRuntimeEventReport {
            event_kind: crate::engine::helix::config::HelixRuntimeEventKind::Benchmark,
            active_core: "helix".to_string(),
            fallback_core: None,
            latency_ms: summary.median_first_byte_latency_ms,
            route_count: None,
            reason: Some("target matrix benchmark evidence".to_string()),
            payload: build_helix_benchmark_payload(HelixBenchmarkPayloadArgs {
                benchmark_kind: "matrix",
                baseline_core: report.baseline_core.as_deref(),
                target_count: Some(report.targets.len()),
                successful_targets: Some(summary.completed_targets as usize),
                attempts: None,
                successes: None,
                failures: Some(summary.failed_targets),
                throughput_kbps: summary.average_throughput_kbps,
                relative_throughput_ratio_vs_baseline: summary.average_relative_throughput_ratio,
                median_connect_latency_ms: summary.median_connect_latency_ms,
                median_first_byte_latency_ms: summary.median_first_byte_latency_ms,
                median_open_to_first_byte_gap_ms: summary.median_open_to_first_byte_gap_ms,
                p95_open_to_first_byte_gap_ms: None,
                relative_open_to_first_byte_gap_ratio_vs_baseline: summary
                    .average_relative_open_to_first_byte_gap_ratio,
                queue_pressure: None,
            }),
        },
    );
}

fn report_helix_recovery_summary(
    app: &AppHandle,
    report: &crate::engine::helix::config::HelixRecoveryBenchmarkReport,
) {
    let Some(benchmark) = report.post_recovery_benchmark.as_ref() else {
        return;
    };

    spawn_helix_runtime_event(
        app,
        crate::engine::helix::config::HelixRuntimeEventReport {
            event_kind: crate::engine::helix::config::HelixRuntimeEventKind::Benchmark,
            active_core: "helix".to_string(),
            fallback_core: None,
            latency_ms: report
                .proxy_ready_latency_ms
                .or(benchmark.median_first_byte_latency_ms),
            route_count: report
                .health_after
                .as_ref()
                .map(|health| health.route_count),
            reason: Some(format!("recovery benchmark evidence ({})", report.mode)),
            payload: build_helix_benchmark_payload(HelixBenchmarkPayloadArgs {
                benchmark_kind: "recovery",
                baseline_core: None,
                target_count: Some(1),
                successful_targets: Some(if report.recovered { 1 } else { 0 }),
                attempts: Some(benchmark.attempts),
                successes: Some(benchmark.successes),
                failures: Some(benchmark.failures),
                throughput_kbps: benchmark.average_throughput_kbps,
                relative_throughput_ratio_vs_baseline: None,
                median_connect_latency_ms: benchmark.median_connect_latency_ms,
                median_first_byte_latency_ms: benchmark.median_first_byte_latency_ms,
                median_open_to_first_byte_gap_ms: benchmark.median_open_to_first_byte_gap_ms,
                p95_open_to_first_byte_gap_ms: benchmark.p95_open_to_first_byte_gap_ms,
                relative_open_to_first_byte_gap_ratio_vs_baseline: None,
                queue_pressure: benchmark.helix_queue_pressure.as_ref(),
            }),
        },
    );
}

fn maybe_record_transport_benchmark_warning(
    app: &AppHandle,
    report: &crate::engine::helix::config::TransportBenchmarkReport,
) {
    let queue_pressure = report.helix_queue_pressure.as_ref();
    let gap_degraded = report
        .median_open_to_first_byte_gap_ms
        .is_some_and(|gap| gap >= 250)
        || report
            .p95_open_to_first_byte_gap_ms
            .is_some_and(|gap| gap >= 450);
    let queue_degraded = queue_pressure.is_some_and(|pressure| pressure.frame_queue_peak >= 16);
    let rtt_degraded = queue_pressure
        .and_then(|pressure| pressure.recent_rtt_p95_ms)
        .is_some_and(|rtt| rtt >= 200);

    if !(gap_degraded || queue_degraded || rtt_degraded) {
        return;
    }

    let _ = crate::engine::diagnostics::record_event(
        app,
        crate::engine::diagnostics::DiagnosticLevel::Warn,
        "transport.performance",
        format!(
            "{} benchmark shows latency or queue pressure",
            report.active_core
        ),
        serde_json::json!({
            "run_id": report.run_id,
            "active_core": report.active_core,
            "median_open_to_first_byte_gap_ms": report.median_open_to_first_byte_gap_ms,
            "p95_open_to_first_byte_gap_ms": report.p95_open_to_first_byte_gap_ms,
            "average_throughput_kbps": report.average_throughput_kbps,
            "frame_queue_peak": queue_pressure.map(|pressure| pressure.frame_queue_peak),
            "recent_rtt_p95_ms": queue_pressure.and_then(|pressure| pressure.recent_rtt_p95_ms),
            "helix_continuity": helix_continuity_json(report.helix_continuity.as_ref()),
        }),
    );
}

fn maybe_record_transport_matrix_warning(
    app: &AppHandle,
    report: &crate::engine::helix::config::TransportBenchmarkMatrixReport,
) {
    let Some(helix_summary) = report
        .core_summaries
        .iter()
        .find(|summary| summary.core == "helix")
    else {
        return;
    };

    let degraded = helix_summary.failed_targets > 0
        || helix_summary
            .average_relative_open_to_first_byte_gap_ratio
            .is_some_and(|ratio| ratio >= 1.20);

    if !degraded {
        return;
    }

    let _ = crate::engine::diagnostics::record_event(
        app,
        crate::engine::diagnostics::DiagnosticLevel::Warn,
        "transport.performance",
        "Helix matrix comparison shows regression against the shared target set",
        serde_json::json!({
            "run_id": report.run_id,
            "baseline_core": report.baseline_core,
            "target_count": report.targets.len(),
            "helix_failed_targets": helix_summary.failed_targets,
            "helix_median_open_to_first_byte_gap_ms": helix_summary.median_open_to_first_byte_gap_ms,
            "helix_average_relative_open_to_first_byte_gap_ratio": helix_summary.average_relative_open_to_first_byte_gap_ratio,
            "helix_average_throughput_kbps": helix_summary.average_throughput_kbps,
        }),
    );
}

fn maybe_record_helix_recovery_warning(
    app: &AppHandle,
    report: &crate::engine::helix::config::HelixRecoveryBenchmarkReport,
) {
    let degraded = !report.recovered
        || report
            .ready_recovery_latency_ms
            .is_some_and(|latency| latency >= 120)
        || report
            .proxy_ready_latency_ms
            .is_some_and(|latency| latency >= 200)
        || report
            .proxy_ready_open_to_first_byte_gap_ms
            .is_some_and(|gap| gap >= 80);

    if !degraded {
        return;
    }

    let _ = crate::engine::diagnostics::record_event(
        app,
        crate::engine::diagnostics::DiagnosticLevel::Warn,
        "transport.performance",
        "Helix recovery drill exceeded the preferred latency envelope",
        serde_json::json!({
            "run_id": report.run_id,
            "mode": report.mode,
            "recovered": report.recovered,
            "route_before": report.route_before,
            "route_after": report.route_after,
            "ready_recovery_latency_ms": report.ready_recovery_latency_ms,
            "proxy_ready_latency_ms": report.proxy_ready_latency_ms,
            "proxy_ready_open_to_first_byte_gap_ms": report.proxy_ready_open_to_first_byte_gap_ms,
            "same_route_recovered": report.same_route_recovered,
            "continuity_after": helix_continuity_json(report.continuity_after.as_ref()),
            "action_message": report.action.as_ref().and_then(|action| action.message.clone()),
        }),
    );
}

#[tauri::command]
pub async fn get_profiles(app: AppHandle) -> Result<Vec<ProxyNode>, AppError> {
    let store_data = store::load_store(&app)?;
    Ok(store_data.profiles)
}

#[tauri::command]
pub async fn add_profile(profile: ProxyNode, app: AppHandle) -> Result<(), AppError> {
    profile.validate().map_err(AppError::System)?;
    let mut store_data = store::load_store(&app)?;
    store_data.profiles.push(profile);
    store::save_store(&app, &store_data)?;
    Ok(())
}

#[tauri::command]
pub async fn get_routing_rules(app: AppHandle) -> Result<Vec<models::RoutingRule>, AppError> {
    let store_data = store::load_store(&app)?;
    Ok(store_data.routing_rules)
}

#[tauri::command]
pub async fn add_routing_rule(rule: models::RoutingRule, app: AppHandle) -> Result<(), AppError> {
    rule.validate().map_err(AppError::System)?;
    let mut store_data = store::load_store(&app)?;
    store_data.routing_rules.push(rule);
    store::save_store(&app, &store_data)?;
    Ok(())
}

#[tauri::command]
pub async fn update_routing_rule(
    rule: models::RoutingRule,
    app: AppHandle,
) -> Result<(), AppError> {
    rule.validate().map_err(AppError::System)?;
    let mut store_data = store::load_store(&app)?;
    if let Some(existing) = store_data
        .routing_rules
        .iter_mut()
        .find(|r| r.id == rule.id)
    {
        *existing = rule;
        store::save_store(&app, &store_data)?;
    }
    Ok(())
}

#[tauri::command]
pub async fn delete_routing_rule(id: String, app: AppHandle) -> Result<(), AppError> {
    let mut store_data = store::load_store(&app)?;
    store_data.routing_rules.retain(|r| r.id != id);
    store::save_store(&app, &store_data)?;
    Ok(())
}

#[tauri::command]
pub async fn apply_routing_fix(
    domain: String,
    app: AppHandle,
    state: State<'_, AppState>,
) -> Result<(), AppError> {
    let mut store_data = store::load_store(&app)?;

    // Quick deduplication
    let already_exists = store_data
        .routing_rules
        .iter()
        .any(|r| r.domains.contains(&domain) || r.domain_keyword.contains(&domain));

    if !already_exists {
        let rule = models::RoutingRule {
            id: uuid::Uuid::new_v4().to_string(),
            enabled: true,
            domains: vec![format!("domain:{}", domain)],
            ips: vec![],
            outbound: "proxy".to_string(),
            process_name: vec![],
            port_range: vec![],
            network: None,
            domain_keyword: vec![],
            domain_regex: vec![],
        };
        store_data.routing_rules.push(rule);
        store::save_store(&app, &store_data)?;
    }

    // Checking state gracefully
    let (status, active_id) = {
        let lock = state.status.read().await;
        (lock.status.clone(), lock.active_id.clone())
    };

    if status == "connecting" || status == "disconnecting" {
        // Do not interrupt an active connection attempt to prevent race conditions
        return Ok(());
    } else if status == "connected" {
        let store_data = store::load_store(&app)?;
        if let Some(profile_id) = resolve_profile_id_for_connect(&store_data, active_id.as_deref())
        {
            let tun_mode = store_data.last_connection_options.tun_mode;
            let system_proxy = store_data.last_connection_options.system_proxy;
            disconnect_internal("routing-rule-reconnect", app.clone(), state).await?;
            let reconnect_state = app.state::<AppState>();
            connect_profile_internal(
                profile_id,
                tun_mode,
                system_proxy,
                "routing-rule-reconnect",
                app.clone(),
                reconnect_state,
            )
            .await?;
        }
    }

    Ok(())
}

#[tauri::command]
pub async fn test_all_latencies(app: AppHandle) -> Result<(), AppError> {
    use futures::stream::StreamExt;

    let mut store_data = store::load_store(&app)?;

    // We clone the profiles so we can borrow them across async tasks
    let profiles_clone = store_data.profiles.clone();

    let results = futures::stream::iter(profiles_clone.into_iter().enumerate().map(
        |(index, node)| async move {
            let ping = crate::engine::ping::test_latency(&node).await.unwrap_or(0);
            (index, ping)
        },
    ))
    .buffer_unordered(15) // Max 15 concurrent tests
    .collect::<Vec<(usize, u32)>>()
    .await;

    for (index, ping) in results {
        if ping > 0 {
            store_data.profiles[index].ping = Some(ping);
        } else {
            // Either failed or timeout. Set to 0 or leave as is. We set to 0 to indicate error.
            store_data.profiles[index].ping = Some(0);
        }
    }

    store::save_store(&app, &store_data)?;
    app.emit("profiles-updated", ())?;

    Ok(())
}

#[tauri::command]
pub async fn parse_clipboard_link(link: String) -> Result<ProxyNode, AppError> {
    parser::parse_link(&link)
}

#[tauri::command]
pub async fn connect_profile(
    id: String,
    tun_mode: bool,
    system_proxy: bool,
    source_surface: Option<String>,
    app: AppHandle,
    state: State<'_, AppState>,
) -> Result<(), AppError> {
    let source_surface = sanitize_source_surface(source_surface.as_deref(), "dashboard");
    connect_profile_internal(id, tun_mode, system_proxy, &source_surface, app, state).await
}

pub(crate) async fn connect_profile_internal(
    id: String,
    tun_mode: bool,
    system_proxy: bool,
    source_surface: &str,
    app: AppHandle,
    state: State<'_, AppState>,
) -> Result<(), AppError> {
    let attempt_id = begin_connection_attempt(&state);
    let requested_profile_id = id.clone();
    let result: Result<(), AppError> = async {
        // 1. Fetch profile
        let mut store_data = store::load_store(&app)?;
        let profile = store_data
            .profiles
            .iter()
            .find(|p| p.id == id)
            .cloned()
            .ok_or_else(|| AppError::System("Profile not found".to_string()))?;

        let app_dir = crate::engine::store::get_app_dir(&app)?;
        #[allow(unused_variables)]
        let log_path = app_dir.join("run.log");

        #[allow(unused_mut, unused_assignments)]
        let mut log_path_opt = None;
        let requested_core =
            crate::engine::helix::config::EngineCore::try_from(store_data.active_core.as_str())?;
        let mut effective_core = requested_core.clone();
        let mut helix_runtime = None;
        let mut helix_launch_started_at = None;

        store_data.active_profile_id = Some(id.clone());
        store_data.last_connection_options.profile_id = Some(id.clone());
        store_data.last_connection_options.tun_mode = tun_mode;
        store_data.last_connection_options.system_proxy = system_proxy;
        store_data.last_connection_options.active_core = requested_core.as_str().to_string();
        store_data.last_connection_options.source_surface = source_surface.to_string();
        store_data.last_connection_options.last_action = Some("connect_requested".to_string());
        store_data.last_connection_options.last_requested_at = current_timestamp_ms();
        store::save_store(&app, &store_data)?;
        emit_connection_options_event(&app, &store_data.last_connection_options);

        #[cfg(target_os = "windows")]
        {
            if tun_mode && !crate::engine::sys::is_elevated() {
                let _ = tokio::fs::remove_file(&log_path).await;
                log_path_opt = Some(log_path.as_path());
            }
        }

        // 4. Update status to connecting
        {
            let mut status_lock = state.status.write().await;
            status_lock.status = "connecting".to_string();
            status_lock.active_id = Some(id.clone());
            status_lock.active_core = Some(requested_core.as_str().to_string());
            status_lock.proxy_url = None;
            status_lock.message = if matches!(
                requested_core,
                crate::engine::helix::config::EngineCore::Helix
            ) && tun_mode
            {
                Some(
                    "Helix currently uses the embedded SOCKS5 runtime while TUN support is still pending."
                        .to_string(),
                )
            } else {
                None
            };
            emit_connection_status_event(&app, status_lock.clone())?;
        }
        let _ = crate::engine::diagnostics::record_event(
            &app,
            crate::engine::diagnostics::DiagnosticLevel::Info,
            "vpn.connect",
            "Connection requested from desktop client",
            serde_json::json!({
                "profile_id": id,
                "requested_core": requested_core.as_str(),
                "tun_mode": tun_mode,
                "system_proxy": system_proxy,
                "source_surface": source_surface,
            }),
        );

        if tun_mode {
            crate::engine::sys::ensure_wintun(&app)?;
        }

        if !is_connection_attempt_current(&state, attempt_id) {
            return Ok(());
        }

        let (launched_core, launched_proxy_url) = loop {
            let (bin_path, config_path, core_name, launch_tun_mode, runtime_monitor, proxy_url) = if matches!(
                effective_core,
                crate::engine::helix::config::EngineCore::Helix
            ) {
                match crate::engine::helix::prepare_runtime_for_launch(&app).await {
                    Ok(prepared_runtime) => {
                        helix_runtime = Some(prepared_runtime.clone());
                        helix_launch_started_at = Some(std::time::Instant::now());
                        (
                            std::path::PathBuf::from(&prepared_runtime.sidecar_path),
                            std::path::PathBuf::from(&prepared_runtime.config_path),
                            effective_core.as_str().to_string(),
                            false,
                            Some(crate::engine::manager::RuntimeMonitorConfig {
                                health_url: prepared_runtime.health_url.clone(),
                            }),
                            Some(prepared_runtime.proxy_url.clone()),
                        )
                    }
                    Err(error) => {
                        let fallback_core = crate::engine::helix::fallback_core_from_store(&app)?;
                        let fallback_core =
                            crate::engine::helix::config::EngineCore::try_from(fallback_core.as_str())?;
                        let reason = format!(
                            "Helix runtime preparation failed: {}. Falling back to {}.",
                            error,
                            fallback_core.as_str()
                        );
                        crate::engine::helix::record_runtime_fallback(
                            &app,
                            fallback_core.as_str(),
                            &reason,
                        )?;
                        let _ = app.emit("helix-fallback", reason);
                        spawn_helix_runtime_event(
                            &app,
                            crate::engine::helix::config::HelixRuntimeEventReport {
                                event_kind:
                                    crate::engine::helix::config::HelixRuntimeEventKind::Fallback,
                                active_core: fallback_core.as_str().to_string(),
                                fallback_core: Some(fallback_core.as_str().to_string()),
                                latency_ms: None,
                                route_count: None,
                                reason: Some(
                                    "Helix runtime preparation failed before sidecar launch"
                                        .to_string(),
                                ),
                                payload: crate::engine::helix::config::HelixRuntimeEventPayload {
                                    stage: Some("prepare".to_string()),
                                    requested_core: Some("helix".to_string()),
                                    runtime: Some("embedded-sidecar".to_string()),
                                    reason_code: Some("runtime-prepare-failed".to_string()),
                                    ..Default::default()
                                },
                            },
                        );
                        effective_core = fallback_core;
                        continue;
                    }
                }
            } else {
                let mut effective_privacy_shield_level = store_data.privacy_shield_level.clone();
                if effective_privacy_shield_level != "disabled" {
                    if let Err(error) = crate::engine::sys::adblock::ensure_blocklists(
                        &app,
                        &effective_privacy_shield_level,
                    )
                    .await
                    {
                        let fallback_message = format!(
                            "Privacy Shield assets are unavailable: {}. Continuing without local blocklist.",
                            error
                        );
                        let _ = crate::engine::diagnostics::record_event(
                            &app,
                            crate::engine::diagnostics::DiagnosticLevel::Warn,
                            "vpn.connect",
                            "Privacy Shield assets unavailable; continuing without local blocklist",
                            serde_json::json!({
                                "requested_level": effective_privacy_shield_level,
                                "error": error.to_string(),
                            }),
                        );
                        eprintln!("{fallback_message}");
                        effective_privacy_shield_level = "disabled".to_string();
                    }
                }

                let bin_path = if matches!(
                    effective_core,
                    crate::engine::helix::config::EngineCore::Xray
                ) {
                    crate::engine::provision::ensure_xray_binary(&app).await?
                } else {
                    crate::engine::provision::ensure_sing_box_binary(&app).await?
                };

                let config_json = if let Some(custom_json_str) = &store_data.custom_config {
                    println!("Using Custom JSON Override for sing-box configuration.");
                    serde_json::from_str::<serde_json::Value>(custom_json_str).map_err(|e| {
                        AppError::System(format!("Custom JSON config parse error: {}", e))
                    })?
                } else {
                    crate::engine::config::generate_singbox_config(
                        &profile,
                        &store_data.profiles,
                        tun_mode,
                        &store_data.routing_rules,
                        log_path_opt,
                        store_data.local_socks_port,
                        store_data.allow_lan,
                        &store_data.split_tunneling_apps,
                        &store_data.split_tunneling_mode,
                        store_data.stealth_mode_enabled,
                        store_data.pqc_enforcement_mode,
                        &effective_privacy_shield_level,
                        Some(app_dir.as_path()),
                    )
                };

                let config_path = app_dir.join("run.json");

                if matches!(
                    effective_core,
                    crate::engine::helix::config::EngineCore::SingBox
                ) {
                    let pqc_active =
                        profile.pqc_enabled.unwrap_or(false) || store_data.pqc_enforcement_mode;
                    if pqc_active {
                        crate::engine::provision::check_pqc_support(&app).await?;
                    }
                }

                tokio::fs::write(&config_path, serde_json::to_string_pretty(&config_json)?).await?;

                let local_proxy_url = format!(
                    "socks5://127.0.0.1:{}",
                    store_data.local_socks_port.unwrap_or(2080)
                );

                (
                    bin_path,
                    config_path,
                    effective_core.as_str().to_string(),
                    tun_mode,
                    None,
                    Some(local_proxy_url),
                )
            };

            if let Err(error) = state
                .process_manager
                .start(
                    app.clone(),
                    bin_path,
                    config_path,
                    launch_tun_mode,
                    &core_name,
                    runtime_monitor,
                )
                .await
            {
                if matches!(
                    effective_core,
                    crate::engine::helix::config::EngineCore::Helix
                ) {
                    let fallback_core = helix_runtime
                        .as_ref()
                        .map(|runtime| runtime.fallback_core.clone())
                        .unwrap_or_else(|| "sing-box".to_string());
                    let fallback_core =
                        crate::engine::helix::config::EngineCore::try_from(fallback_core.as_str())?;
                    let reason = format!(
                        "Helix sidecar failed to launch: {}. Falling back to {}.",
                        error,
                        fallback_core.as_str()
                    );
                    let latency_ms = helix_launch_started_at
                        .as_ref()
                        .and_then(|started| i32::try_from(started.elapsed().as_millis()).ok());
                    crate::engine::helix::record_runtime_fallback(
                        &app,
                        fallback_core.as_str(),
                        &reason,
                    )?;
                    let _ = app.emit("helix-fallback", reason);
                    spawn_helix_runtime_event(
                        &app,
                        crate::engine::helix::config::HelixRuntimeEventReport {
                            event_kind: crate::engine::helix::config::HelixRuntimeEventKind::Fallback,
                            active_core: fallback_core.as_str().to_string(),
                            fallback_core: Some(fallback_core.as_str().to_string()),
                            latency_ms,
                            route_count: helix_runtime.as_ref().map(|runtime| runtime.route_count),
                            reason: Some("Helix sidecar launch failed".to_string()),
                            payload: crate::engine::helix::config::HelixRuntimeEventPayload {
                                stage: Some("launch".to_string()),
                                requested_core: Some("helix".to_string()),
                                runtime: Some("embedded-sidecar".to_string()),
                                reason_code: Some("sidecar-launch-failed".to_string()),
                                ..Default::default()
                            },
                        },
                    );
                    effective_core = fallback_core;
                    continue;
                }

                let mut status_lock = state.status.write().await;
                status_lock.status = "error".to_string();
                status_lock.active_core = Some(effective_core.as_str().to_string());
                status_lock.proxy_url = None;
                status_lock.message = Some(error.to_string());
                emit_connection_status_event(&app, status_lock.clone())?;
                return Err(error);
            }

            if !is_connection_attempt_current(&state, attempt_id) {
                let _ = state.process_manager.stop().await;
                return Ok(());
            }

            if matches!(
                effective_core,
                crate::engine::helix::config::EngineCore::Helix
            ) {
                let prepared_runtime = helix_runtime
                    .as_ref()
                    .ok_or_else(|| AppError::System("Helix runtime was not prepared".to_string()))?;

                match crate::engine::helix::health::await_runtime_ready(prepared_runtime).await {
                    Ok(health) => {
                        let latency_ms = helix_launch_started_at
                            .as_ref()
                            .and_then(|started| i32::try_from(started.elapsed().as_millis()).ok());
                        spawn_helix_runtime_event(
                            &app,
                            crate::engine::helix::config::HelixRuntimeEventReport {
                                event_kind: crate::engine::helix::config::HelixRuntimeEventKind::Ready,
                                active_core: "helix".to_string(),
                                fallback_core: None,
                                latency_ms,
                                route_count: Some(health.route_count),
                                reason: None,
                                payload: crate::engine::helix::config::HelixRuntimeEventPayload {
                                    stage: Some("ready".to_string()),
                                    runtime: Some("embedded-sidecar".to_string()),
                                    status: Some(health.status.clone()),
                                    proxy_url: Some(prepared_runtime.proxy_url.clone()),
                                    continuity: Some((&health).into()),
                                    ..Default::default()
                                },
                            },
                        );
                        break (
                            effective_core.clone(),
                            Some(prepared_runtime.proxy_url.clone()),
                        );
                    }
                    Err(error) => {
                        let _ = state.process_manager.stop().await;
                        let fallback_core = crate::engine::helix::config::EngineCore::try_from(
                            prepared_runtime.fallback_core.as_str(),
                        )?;
                        let reason = format!(
                            "Helix sidecar health gate failed: {}. Falling back to {}.",
                            error,
                            fallback_core.as_str()
                        );
                        let latency_ms = helix_launch_started_at
                            .as_ref()
                            .and_then(|started| i32::try_from(started.elapsed().as_millis()).ok());
                        crate::engine::helix::record_runtime_fallback(
                            &app,
                            fallback_core.as_str(),
                            &reason,
                        )?;
                        let _ = app.emit("helix-fallback", reason);
                        spawn_helix_runtime_event(
                            &app,
                            crate::engine::helix::config::HelixRuntimeEventReport {
                                event_kind:
                                    crate::engine::helix::config::HelixRuntimeEventKind::Fallback,
                                active_core: fallback_core.as_str().to_string(),
                                fallback_core: Some(fallback_core.as_str().to_string()),
                                latency_ms,
                                route_count: Some(prepared_runtime.route_count),
                                reason: Some("Helix sidecar failed readiness health gate".to_string()),
                                payload: crate::engine::helix::config::HelixRuntimeEventPayload {
                                    stage: Some("health-gate".to_string()),
                                    requested_core: Some("helix".to_string()),
                                    runtime: Some("embedded-sidecar".to_string()),
                                    proxy_url: Some(prepared_runtime.proxy_url.clone()),
                                    reason_code: Some("health-gate-timeout".to_string()),
                                    ..Default::default()
                                },
                            },
                        );
                        effective_core = fallback_core;
                        continue;
                    }
                }
            }

            break (effective_core.clone(), proxy_url);
        };

        if !is_connection_attempt_current(&state, attempt_id) {
            let _ = state.process_manager.stop().await;
            return Ok(());
        }

        // Phase 30: Telemetry sync barrier
        let _ = crate::engine::sys::stats::flush_session(&app);
        let country = crate::engine::sys::stats::resolve_ip_country(&profile.server);
        let session_protocol = if matches!(
            launched_core,
            crate::engine::helix::config::EngineCore::Helix
        ) {
            "helix".to_string()
        } else {
            profile.protocol.clone()
        };
        crate::engine::sys::stats::start_session(session_protocol, country);

        if matches!(
            launched_core,
            crate::engine::helix::config::EngineCore::Helix
        ) {
            if let Some(proxy_url) = &launched_proxy_url {
                if let Err(error) = crate::engine::sysproxy::set_system_proxy_from_url(proxy_url) {
                    eprintln!("Failed to set Helix system proxy: {}", error);
                }
            }
        } else if system_proxy && !tun_mode && launched_core.is_stable() {
            let port = store_data.local_socks_port.unwrap_or(2080);
            if let Err(e) = crate::engine::sysproxy::set_system_proxy(port) {
                eprintln!("Failed to set system proxy: {}", e);
            }
        } else {
            crate::engine::sysproxy::clear_system_proxy().ok();
        }

        if launched_core.is_stable() {
            if let Some(proxy_url) = launched_proxy_url.as_deref() {
                let readiness_timeout = if tun_mode {
                    std::time::Duration::from_secs(20)
                } else {
                    std::time::Duration::from_secs(8)
                };
                if let Err(error) = crate::engine::helix::benchmark::wait_for_proxy_ready(
                    proxy_url,
                    readiness_timeout,
                )
                .await
                {
                    let _ = state.process_manager.stop().await;
                    return Err(AppError::System(format!(
                        "VPN runtime did not become ready for proxy traffic: {}",
                        error
                    )));
                }

                if let Err(error) = crate::engine::helix::benchmark::wait_for_proxy_first_byte_ready(
                    proxy_url,
                    "example.com",
                    80,
                    "/",
                    readiness_timeout,
                    std::time::Duration::from_secs(if tun_mode { 5 } else { 4 }),
                )
                .await
                {
                    let _ = state.process_manager.stop().await;
                    return Err(AppError::System(format!(
                        "VPN runtime became reachable locally but failed real traffic readiness probe: {}",
                        error
                    )));
                }
            }
        }

        if !is_connection_attempt_current(&state, attempt_id) {
            let _ = state.process_manager.stop().await;
            return Ok(());
        }

        // 6. Update status to connected
        {
            let mut persisted_store = store::load_store(&app)?;
            persisted_store.active_profile_id = Some(id.clone());
            persisted_store.last_connection_options.profile_id = Some(id.clone());
            persisted_store.last_connection_options.tun_mode = tun_mode;
            persisted_store.last_connection_options.system_proxy = system_proxy;
            persisted_store.last_connection_options.active_core = launched_core.as_str().to_string();
            persisted_store.last_connection_options.source_surface = source_surface.to_string();
            persisted_store.last_connection_options.last_stable_profile_id = Some(id.clone());
            persisted_store.last_connection_options.last_stable_connected_at =
                current_timestamp_ms();
            persisted_store.last_connection_options.last_action = Some("connected".to_string());
            persisted_store.last_connection_options.last_connected_at = current_timestamp_ms();
            store::save_store(&app, &persisted_store)?;
            emit_connection_options_event(&app, &persisted_store.last_connection_options);

            let mut status_lock = state.status.write().await;
            status_lock.status = "connected".to_string();
            status_lock.active_core = Some(launched_core.as_str().to_string());
            status_lock.proxy_url = launched_proxy_url.clone();
            status_lock.message = if matches!(
                launched_core,
                crate::engine::helix::config::EngineCore::Helix
            ) {
                Some("Helix is active through the embedded SOCKS5 runtime.".to_string())
            } else {
                None
            };
            emit_connection_status_event(&app, status_lock.clone())?;
        }
        let _ = crate::engine::diagnostics::record_event(
            &app,
            crate::engine::diagnostics::DiagnosticLevel::Info,
            "vpn.connect",
            "Connection established",
            serde_json::json!({
                "profile_id": profile.id,
                "effective_core": launched_core.as_str(),
                "proxy_url": launched_proxy_url,
                "tun_mode": tun_mode,
                "system_proxy": system_proxy,
                "source_surface": source_surface,
            }),
        );

        Ok(())
    }
    .await;

    if !is_connection_attempt_current(&state, attempt_id) {
        if result.is_err() {
            let _ = crate::engine::diagnostics::record_event(
                &app,
                crate::engine::diagnostics::DiagnosticLevel::Info,
                "vpn.connect",
                "Ignored stale connection attempt result",
                serde_json::json!({
                    "profile_id": requested_profile_id,
                    "tun_mode": tun_mode,
                    "system_proxy": system_proxy,
                    "source_surface": source_surface,
                    "attempt_id": attempt_id,
                }),
            );
        }
        return Ok(());
    }

    if let Err(error) = &result {
        let error_message = error.to_string();
        let _ = persist_last_connection_options(&app, |store_data, options| {
            options.profile_id = Some(requested_profile_id.clone());
            options.tun_mode = tun_mode;
            options.system_proxy = system_proxy;
            options.active_core = store_data.active_core.clone();
            options.source_surface = source_surface.to_string();
            options.last_action = Some("connect_failed".to_string());
            options.last_requested_at = current_timestamp_ms();
        });
        {
            let mut status_lock = state.status.write().await;
            status_lock.status = "error".to_string();
            status_lock.active_id = Some(requested_profile_id.clone());
            status_lock.proxy_url = None;
            status_lock.message = Some(error_message.clone());
            let _ = emit_connection_status_event(&app, status_lock.clone());
        }

        let _ = crate::engine::diagnostics::record_event(
            &app,
            crate::engine::diagnostics::DiagnosticLevel::Error,
            "vpn.connect",
            "Connection request failed",
            serde_json::json!({
                "profile_id": requested_profile_id,
                "tun_mode": tun_mode,
                "system_proxy": system_proxy,
                "source_surface": source_surface,
                "error": error_message,
            }),
        );
    }

    result
}

#[tauri::command]
pub async fn disconnect(
    source_surface: Option<String>,
    app: AppHandle,
    state: State<'_, AppState>,
) -> Result<(), AppError> {
    let source_surface = sanitize_source_surface(source_surface.as_deref(), "dashboard");
    disconnect_internal(&source_surface, app, state).await
}

pub(crate) async fn disconnect_internal(
    source_surface: &str,
    app: AppHandle,
    state: State<'_, AppState>,
) -> Result<(), AppError> {
    invalidate_connection_attempts(&state);
    let previous_status = state.status.read().await.clone();
    if previous_status.status == "disconnected" || previous_status.status == "disconnecting" {
        return Ok(());
    }

    let store_data = store::load_store(&app)?;
    if store_data.active_core == "helix" && store_data.helix_last_manifest.is_some() {
        spawn_helix_runtime_event(
            &app,
            crate::engine::helix::config::HelixRuntimeEventReport {
                event_kind: crate::engine::helix::config::HelixRuntimeEventKind::Disconnect,
                active_core: "helix".to_string(),
                fallback_core: None,
                latency_ms: None,
                route_count: store_data
                    .helix_last_prepared_runtime
                    .as_ref()
                    .map(|runtime| runtime.route_count),
                reason: None,
                payload: crate::engine::helix::config::HelixRuntimeEventPayload {
                    stage: Some("disconnect".to_string()),
                    runtime: Some("embedded-sidecar".to_string()),
                    ..Default::default()
                },
            },
        );
    }

    let _ = crate::engine::diagnostics::record_event(
        &app,
        crate::engine::diagnostics::DiagnosticLevel::Info,
        "vpn.disconnect",
        "Disconnect requested from desktop client",
        serde_json::json!({
            "active_core": store_data.active_core.clone(),
            "source_surface": source_surface,
        }),
    );

    {
        let mut status_lock = state.status.write().await;
        status_lock.status = "disconnecting".to_string();
        status_lock.message = Some("Stopping VPN runtime...".to_string());
        emit_connection_status_event(&app, status_lock.clone())?;
    }

    emit_connection_lifecycle_event(
        &app,
        "disconnect_started",
        serde_json::json!({
            "active_id": previous_status.active_id.clone(),
            "active_core": previous_status.active_core.clone(),
            "source_surface": source_surface,
        }),
    );

    match reset_connection_state(&app, &state).await {
        Ok(()) => {
            let _ = persist_last_connection_options(&app, |_store_data, options| {
                options.source_surface = source_surface.to_string();
                options.last_action = Some("disconnected".to_string());
                options.last_disconnected_at = current_timestamp_ms();
            });
            Ok(())
        }
        Err(error) => {
            let error_message = format!("Disconnect failed: {}", error);
            {
                let mut status_lock = state.status.write().await;
                status_lock.status = "error".to_string();
                status_lock.active_id = previous_status.active_id;
                status_lock.active_core = previous_status.active_core;
                status_lock.proxy_url = previous_status.proxy_url;
                status_lock.up_bytes = previous_status.up_bytes;
                status_lock.down_bytes = previous_status.down_bytes;
                status_lock.message = Some(error_message.clone());
                let _ = emit_connection_status_event(&app, status_lock.clone());
            }

            emit_connection_lifecycle_event(
                &app,
                "disconnect_failed",
                serde_json::json!({
                    "error": error_message,
                    "source_surface": source_surface,
                }),
            );

            let _ = crate::engine::diagnostics::record_event(
                &app,
                crate::engine::diagnostics::DiagnosticLevel::Error,
                "vpn.disconnect",
                "Disconnect failed",
                serde_json::json!({
                    "error": error.to_string(),
                    "active_core": store_data.active_core.clone(),
                    "source_surface": source_surface,
                }),
            );

            Err(error)
        }
    }
}

#[tauri::command]
pub async fn get_connection_status(
    state: State<'_, AppState>,
) -> Result<ConnectionStatus, AppError> {
    let status_lock = state.status.read().await;
    Ok(status_lock.clone())
}

#[tauri::command]
pub async fn get_last_connection_options(
    app: AppHandle,
) -> Result<models::LastConnectionOptions, AppError> {
    let store_data = store::load_store(&app)?;
    Ok(derive_last_connection_options(&store_data))
}

#[tauri::command]
pub async fn save_last_connection_options(
    options: models::LastConnectionOptions,
    app: AppHandle,
) -> Result<models::LastConnectionOptions, AppError> {
    let source_surface =
        sanitize_source_surface(Some(options.source_surface.as_str()), "dashboard");
    let profile_id = options
        .profile_id
        .filter(|profile_id| !profile_id.trim().is_empty());
    let tun_mode = options.tun_mode;
    let system_proxy = options.system_proxy;
    let favorite_profile_ids = {
        let mut deduped = Vec::new();

        for profile_id in options.favorite_profile_ids {
            let candidate = profile_id.trim();
            if candidate.is_empty() || deduped.iter().any(|stored| stored == candidate) {
                continue;
            }

            deduped.push(candidate.to_string());

            if deduped.len() >= 24 {
                break;
            }
        }

        deduped
    };
    let last_stable_profile_id = options
        .last_stable_profile_id
        .filter(|profile_id| !profile_id.trim().is_empty());
    let last_stable_connected_at = options.last_stable_connected_at;
    let last_action = options.last_action;
    let last_requested_at = options.last_requested_at;
    let last_connected_at = options.last_connected_at;
    let last_disconnected_at = options.last_disconnected_at;
    let active_core =
        if crate::engine::helix::config::EngineCore::try_from(options.active_core.as_str()).is_ok()
        {
            options.active_core
        } else {
            store::load_store(&app)?.active_core
        };

    persist_last_connection_options(&app, |_store_data, stored_options| {
        stored_options.profile_id = profile_id;
        stored_options.tun_mode = tun_mode;
        stored_options.system_proxy = system_proxy;
        stored_options.active_core = active_core;
        stored_options.source_surface = source_surface;
        stored_options.favorite_profile_ids = favorite_profile_ids;
        stored_options.last_stable_profile_id = last_stable_profile_id;
        stored_options.last_stable_connected_at = last_stable_connected_at;
        stored_options.last_action = last_action;
        stored_options.last_requested_at = last_requested_at;
        stored_options.last_connected_at = last_connected_at;
        stored_options.last_disconnected_at = last_disconnected_at;
    })
}

#[tauri::command]
pub async fn get_desktop_diagnostics_snapshot(
    app: AppHandle,
    state: State<'_, AppState>,
) -> Result<crate::engine::diagnostics::DesktopDiagnosticsSnapshot, AppError> {
    let connection_status = state.status.read().await.clone();
    crate::engine::diagnostics::collect_snapshot(&app, connection_status).await
}

#[tauri::command]
pub async fn export_desktop_support_bundle(
    app: AppHandle,
    state: State<'_, AppState>,
) -> Result<crate::engine::diagnostics::SupportBundleExportResult, AppError> {
    let connection_status = state.status.read().await.clone();
    crate::engine::diagnostics::export_support_bundle(&app, connection_status).await
}

#[tauri::command]
pub async fn clear_desktop_diagnostics_logs(app: AppHandle) -> Result<(), AppError> {
    crate::engine::diagnostics::clear_diagnostics_logs(&app)
}

#[tauri::command]
pub async fn get_subscriptions(app: AppHandle) -> Result<Vec<models::Subscription>, AppError> {
    let store_data = store::load_store(&app)?;
    Ok(store_data.subscriptions)
}

#[tauri::command]
pub async fn add_subscription(sub: models::Subscription, app: AppHandle) -> Result<(), AppError> {
    let mut store_data = store::load_store(&app)?;
    store_data.subscriptions.push(sub);
    store::save_store(&app, &store_data)?;
    Ok(())
}

#[tauri::command]
pub async fn update_subscription(sub_id: String, app: AppHandle) -> Result<(), AppError> {
    let mut store_data = store::load_store(&app)?;

    // Find the subscription URL
    let url = {
        let sub = store_data
            .subscriptions
            .iter()
            .find(|s| s.id == sub_id)
            .ok_or_else(|| AppError::System("Subscription not found".to_string()))?;
        sub.url.clone()
    };

    // Fetch new nodes
    let mut new_nodes = crate::engine::subscription::fetch_and_parse_subscription(&url).await?;

    // Assign sub_id
    for node in &mut new_nodes {
        node.subscription_id = Some(sub_id.clone());
    }

    // Sweep old nodes
    store_data
        .profiles
        .retain(|p| p.subscription_id.as_deref() != Some(sub_id.as_str()));

    // Append new nodes
    store_data.profiles.extend(new_nodes);

    // Update timestamp
    if let Some(sub) = store_data.subscriptions.iter_mut().find(|s| s.id == sub_id) {
        let now = std::time::SystemTime::now()
            .duration_since(std::time::UNIX_EPOCH)
            .map_err(|error| {
                AppError::System(format!(
                    "System clock is before UNIX_EPOCH while updating subscription timestamp: {error}"
                ))
            })?;
        sub.last_updated = Some(now.as_secs());
    }

    store::save_store(&app, &store_data)?;
    Ok(())
}

#[tauri::command]
pub async fn scan_screen_for_qr() -> Result<ProxyNode, AppError> {
    crate::engine::qr::scan_screen_for_qr().await
}

#[tauri::command]
pub async fn generate_link(node: ProxyNode) -> Result<String, AppError> {
    Ok(crate::engine::parser::generate_link(&node))
}

#[tauri::command]
pub async fn get_custom_config(app: AppHandle) -> Result<Option<String>, AppError> {
    let store_data = store::load_store(&app)?;
    Ok(store_data.custom_config)
}

#[tauri::command]
pub async fn save_custom_config(config: Option<String>, app: AppHandle) -> Result<(), AppError> {
    if let Some(ref json_str) = config {
        // Zero-cost validation
        serde_json::from_str::<serde::de::IgnoredAny>(json_str)
            .map_err(|e| AppError::System(format!("Invalid JSON configuration: {}", e)))?;
    }
    let mut store_data = store::load_store(&app)?;
    store_data.custom_config = config;
    store::save_store(&app, &store_data)?;
    Ok(())
}

#[tauri::command]
pub async fn get_local_socks_port(app: AppHandle) -> Result<Option<u16>, AppError> {
    let store_data = store::load_store(&app)?;
    Ok(store_data.local_socks_port)
}

#[tauri::command]
pub async fn save_local_socks_port(port: Option<u16>, app: AppHandle) -> Result<(), AppError> {
    let mut store_data = store::load_store(&app)?;
    store_data.local_socks_port = port;
    store::save_store(&app, &store_data)?;
    Ok(())
}

#[tauri::command]
pub async fn get_allow_lan(app: AppHandle) -> Result<bool, AppError> {
    let store_data = store::load_store(&app)?;
    Ok(store_data.allow_lan)
}

#[tauri::command]
pub async fn save_allow_lan(allow: bool, app: AppHandle) -> Result<(), AppError> {
    let mut store_data = store::load_store(&app)?;
    store_data.allow_lan = allow;
    store::save_store(&app, &store_data)?;
    Ok(())
}

#[tauri::command]
pub async fn get_groups(app: AppHandle) -> Result<Vec<ProfileGroup>, AppError> {
    let store_data = store::load_store(&app)?;
    Ok(store_data.groups)
}

#[tauri::command]
pub async fn add_group(group: ProfileGroup, app: AppHandle) -> Result<(), AppError> {
    let mut store_data = store::load_store(&app)?;
    store_data.groups.push(group);
    store::save_store(&app, &store_data)?;
    Ok(())
}

#[tauri::command]
pub async fn delete_group(id: String, app: AppHandle) -> Result<(), AppError> {
    let mut store_data = store::load_store(&app)?;
    store_data.groups.retain(|g| g.id != id);
    for p in store_data.profiles.iter_mut() {
        if let Some(ref gid) = p.group_id {
            if gid == &id {
                p.group_id = None;
            }
        }
    }
    store::save_store(&app, &store_data)?;
    Ok(())
}

#[tauri::command]
pub async fn set_node_group(
    node_id: String,
    group_id: Option<String>,
    app: AppHandle,
) -> Result<(), AppError> {
    let mut store_data = store::load_store(&app)?;
    if let Some(node) = store_data.profiles.iter_mut().find(|n| n.id == node_id) {
        node.group_id = group_id;
        store::save_store(&app, &store_data)?;
    }
    Ok(())
}

#[tauri::command]
pub async fn update_geo_assets(app: AppHandle) -> Result<(), AppError> {
    crate::engine::provision::update_geo_assets(&app).await
}

#[tauri::command]
pub async fn get_active_core(app: AppHandle) -> Result<String, AppError> {
    let store_data = tokio::task::spawn_blocking(move || store::load_store(&app))
        .await
        .map_err(|e| AppError::System(format!("Tokio spawn blocking failed: {}", e)))??;
    Ok(store_data.active_core)
}

#[tauri::command]
pub async fn save_active_core(core: String, app: AppHandle) -> Result<(), AppError> {
    let _ = crate::engine::helix::config::EngineCore::try_from(core.as_str())?;

    let app_for_store = app.clone();
    let core_for_store = core.clone();
    tokio::task::spawn_blocking(move || {
        let mut store_data = store::load_store(&app_for_store)?;
        store_data.active_core = core_for_store;
        store_data.last_connection_options.active_core = store_data.active_core.clone();
        store::save_store(&app_for_store, &store_data)?;
        Ok::<(), AppError>(())
    })
    .await
    .map_err(|e| AppError::System(format!("Tokio spawn blocking failed: {}", e)))??;

    let store_data = store::load_store(&app)?;
    emit_connection_options_event(&app, &store_data.last_connection_options);

    Ok(())
}

#[tauri::command]
pub async fn get_helix_capabilities(
) -> Result<crate::engine::helix::config::HelixCapabilityDefaults, AppError> {
    Ok(crate::engine::helix::local_capabilities())
}

#[tauri::command]
pub async fn get_helix_manifest(
    app: AppHandle,
) -> Result<Option<crate::engine::helix::config::HelixResolvedManifest>, AppError> {
    crate::engine::helix::get_stored_manifest(&app)
}

#[tauri::command]
pub async fn get_helix_runtime_state(
    app: AppHandle,
) -> Result<crate::engine::helix::config::HelixRuntimeState, AppError> {
    crate::engine::helix::get_runtime_state(&app)
}

#[tauri::command]
pub async fn get_canonical_customer_profile(app: AppHandle) -> Result<serde_json::Value, AppError> {
    let (base_url, access_token, _) = helix::get_authenticated_backend_context(&app)?;
    client::fetch_authenticated_get(&base_url, &access_token, "/api/v1/mobile/auth/me").await
}

#[tauri::command]
pub async fn get_canonical_current_entitlements(
    app: AppHandle,
) -> Result<serde_json::Value, AppError> {
    let (base_url, access_token, _) = helix::get_authenticated_backend_context(&app)?;
    client::fetch_authenticated_get(&base_url, &access_token, "/api/v1/entitlements/current").await
}

#[tauri::command]
pub async fn get_canonical_current_service_state(
    app: AppHandle,
) -> Result<serde_json::Value, AppError> {
    let (base_url, access_token, runtime_state) = helix::get_authenticated_backend_context(&app)?;
    client::fetch_authenticated_post_json(
        &base_url,
        &access_token,
        "/api/v1/access-delivery-channels/current/service-state",
        &serde_json::json!({
            "provider_name": "remnawave",
            "channel_type": "desktop_manifest",
            "channel_subject_ref": runtime_state.desktop_client_id,
        }),
    )
    .await
}

#[tauri::command]
pub async fn get_canonical_orders(
    limit: Option<u32>,
    app: AppHandle,
) -> Result<Vec<serde_json::Value>, AppError> {
    let (base_url, access_token, _) = helix::get_authenticated_backend_context(&app)?;
    let order_limit = normalize_canonical_order_limit(limit);
    let path = format!("/api/v1/orders?limit={order_limit}&offset=0");
    client::fetch_authenticated_get(&base_url, &access_token, &path).await
}

#[tauri::command]
pub async fn resolve_helix_manifest(
    base_url: String,
    access_token: String,
    preferred_fallback_core: Option<String>,
    app: AppHandle,
) -> Result<crate::engine::helix::config::HelixResolvedManifest, AppError> {
    if base_url.trim().is_empty() {
        return Err(AppError::Actionable {
            error: "Helix backend URL is required".to_string(),
            resolution: "Provide the authenticated backend base URL before resolving a manifest."
                .to_string(),
        });
    }

    if access_token.trim().is_empty() {
        return Err(AppError::Actionable {
            error: "Helix access token is required".to_string(),
            resolution: "Sign in or paste a valid bearer token for the backend facade.".to_string(),
        });
    }

    let manifest = crate::engine::helix::resolve_manifest_for_desktop(
        &app,
        &base_url,
        &access_token,
        preferred_fallback_core,
    )
    .await?;

    let _ = crate::engine::diagnostics::record_event(
        &app,
        crate::engine::diagnostics::DiagnosticLevel::Info,
        "helix.manifest",
        "Resolved compatible Helix manifest",
        serde_json::json!({
            "rollout_id": manifest.manifest.rollout_id,
            "manifest_version_id": manifest.manifest_version_id,
            "transport_profile_id": manifest.manifest.transport_profile.transport_profile_id,
            "route_count": manifest.manifest.routes.len(),
            "selected_profile_policy": manifest.selected_profile_policy.as_ref().map(|policy| serde_json::json!({
                "policy_score": policy.policy_score,
                "advisory_state": policy.advisory_state,
                "selection_eligible": policy.selection_eligible,
                "new_session_issuable": policy.new_session_issuable,
                "new_session_posture": policy.new_session_posture,
                "suppression_window_active": policy.suppression_window_active,
                "suppression_reason": policy.suppression_reason,
                "suppression_observation_count": policy.suppression_observation_count,
                "suppressed_until": policy.suppressed_until,
                "connect_success_rate": policy.connect_success_rate,
                "fallback_rate": policy.fallback_rate,
                "continuity_success_rate": policy.continuity_success_rate,
                "cross_route_recovery_rate": policy.cross_route_recovery_rate,
            })),
        }),
    );

    if let Some(policy) = manifest.selected_profile_policy.as_ref() {
        if policy.advisory_state != "healthy" {
            let _ = crate::engine::diagnostics::record_event(
                &app,
                crate::engine::diagnostics::DiagnosticLevel::Warn,
                "helix.manifest",
                "Helix manifest resolved with an advisory transport profile state",
                serde_json::json!({
                    "rollout_id": manifest.manifest.rollout_id,
                    "manifest_version_id": manifest.manifest_version_id,
                    "transport_profile_id": manifest.manifest.transport_profile.transport_profile_id,
                    "policy_score": policy.policy_score,
                    "advisory_state": policy.advisory_state,
                    "selection_eligible": policy.selection_eligible,
                    "new_session_issuable": policy.new_session_issuable,
                    "new_session_posture": policy.new_session_posture,
                    "suppression_window_active": policy.suppression_window_active,
                    "suppression_reason": policy.suppression_reason,
                    "suppression_observation_count": policy.suppression_observation_count,
                    "suppressed_until": policy.suppressed_until,
                    "recommended_action": policy.recommended_action,
                    "connect_success_rate": policy.connect_success_rate,
                    "fallback_rate": policy.fallback_rate,
                    "continuity_success_rate": policy.continuity_success_rate,
                    "cross_route_recovery_rate": policy.cross_route_recovery_rate,
                }),
            );
        }
    }

    Ok(manifest)
}

#[tauri::command]
pub async fn prepare_helix_runtime(
    app: AppHandle,
) -> Result<crate::engine::helix::config::HelixPreparedRuntime, AppError> {
    let prepared_runtime = crate::engine::helix::prepare_runtime_for_launch(&app).await?;
    let _ = crate::engine::diagnostics::record_event(
        &app,
        crate::engine::diagnostics::DiagnosticLevel::Info,
        "helix.runtime",
        "Prepared Helix desktop runtime",
        serde_json::json!({
            "manifest_version_id": prepared_runtime.manifest_version_id,
            "transport_profile_id": prepared_runtime.transport_profile_id,
            "route_count": prepared_runtime.route_count,
            "binary_available": prepared_runtime.binary_available,
            "health_url": prepared_runtime.health_url,
            "proxy_url": prepared_runtime.proxy_url,
        }),
    );
    Ok(prepared_runtime)
}

#[tauri::command]
pub async fn run_transport_benchmark(
    request: crate::engine::helix::config::TransportBenchmarkRequest,
    app: AppHandle,
) -> Result<crate::engine::helix::config::TransportBenchmarkReport, AppError> {
    let report = crate::engine::helix::benchmark::run_transport_benchmark(&app, request).await?;
    let mut store_data = store::load_store(&app)?;
    store_data.helix_last_benchmark_report = Some(report.clone());
    store::save_store(&app, &store_data)?;
    let _ = crate::engine::diagnostics::record_event(
        &app,
        crate::engine::diagnostics::DiagnosticLevel::Info,
        "helix.benchmark",
        "Transport benchmark completed",
        serde_json::json!({
            "run_id": report.run_id,
            "active_core": report.active_core,
            "successes": report.successes,
            "failures": report.failures,
            "target_host": report.target_host,
            "target_port": report.target_port,
            "median_connect_latency_ms": report.median_connect_latency_ms,
            "median_first_byte_latency_ms": report.median_first_byte_latency_ms,
            "median_open_to_first_byte_gap_ms": report.median_open_to_first_byte_gap_ms,
            "p95_open_to_first_byte_gap_ms": report.p95_open_to_first_byte_gap_ms,
            "average_throughput_kbps": report.average_throughput_kbps,
            "helix_queue_pressure": helix_queue_pressure_json(report.helix_queue_pressure.as_ref()),
            "helix_continuity": helix_continuity_json(report.helix_continuity.as_ref()),
        }),
    );
    maybe_record_transport_benchmark_warning(&app, &report);
    report_helix_benchmark_summary(&app, &report);
    Ok(report)
}

#[tauri::command]
pub async fn run_transport_core_comparison(
    request: crate::engine::helix::config::TransportBenchmarkComparisonRequest,
    app: AppHandle,
    state: State<'_, AppState>,
) -> Result<crate::engine::helix::config::TransportBenchmarkComparisonReport, AppError> {
    if request.profile_id.trim().is_empty() {
        return Err(AppError::Actionable {
            error: "Benchmark comparison requires a profile id".to_string(),
            resolution:
                "Select the desktop profile or node id that should be used for the stable-core comparison."
                    .to_string(),
        });
    }

    let benchmark_request = request.benchmark.clone();
    let mut requested_cores = if request.cores.is_empty() {
        crate::engine::helix::benchmark::default_comparison_cores()
    } else {
        request.cores
    };
    requested_cores.dedup();

    let original_active_core = store::load_store(&app)?.active_core;
    reset_connection_state(&app, &state).await?;

    let mut entries = Vec::new();

    for requested_core in requested_cores {
        {
            let mut store_data = store::load_store(&app)?;
            store_data.active_core = requested_core.as_str().to_string();
            store::save_store(&app, &store_data)?;
        }

        let comparison_entry = match connect_profile_internal(
            request.profile_id.clone(),
            false,
            false,
            "transport-core-comparison",
            app.clone(),
            state.clone(),
        )
        .await
        {
            Ok(()) => {
                let store_data = store::load_store(&app)?;
                let effective_core = crate::engine::helix::config::EngineCore::try_from(
                    store_data.active_core.as_str(),
                )?;
                let proxy_url = crate::engine::helix::benchmark::resolve_proxy_url_for_core(
                    &store_data,
                    &effective_core,
                    benchmark_request.proxy_url.clone(),
                )?;
                let benchmark = match crate::engine::helix::benchmark::wait_for_proxy_ready(
                    &proxy_url,
                    std::time::Duration::from_secs(5),
                )
                .await
                {
                    Ok(()) => crate::engine::helix::benchmark::run_transport_benchmark(
                        &app,
                        benchmark_request.clone(),
                    )
                    .await
                    .map(Some),
                    Err(error) => Err(error),
                };

                match benchmark {
                    Ok(benchmark) => {
                        crate::engine::helix::config::TransportBenchmarkComparisonEntry {
                            requested_core: requested_core.as_str().to_string(),
                            effective_core: benchmark
                                .as_ref()
                                .map(|report| report.active_core.clone()),
                            benchmark,
                            error: None,
                            relative_connect_latency_ratio: None,
                            relative_first_byte_latency_ratio: None,
                            relative_open_to_first_byte_gap_ratio: None,
                            relative_throughput_ratio: None,
                        }
                    }
                    Err(error) => crate::engine::helix::config::TransportBenchmarkComparisonEntry {
                        requested_core: requested_core.as_str().to_string(),
                        effective_core: Some(effective_core.as_str().to_string()),
                        benchmark: None,
                        error: Some(error.to_string()),
                        relative_connect_latency_ratio: None,
                        relative_first_byte_latency_ratio: None,
                        relative_open_to_first_byte_gap_ratio: None,
                        relative_throughput_ratio: None,
                    },
                }
            }
            Err(error) => crate::engine::helix::config::TransportBenchmarkComparisonEntry {
                requested_core: requested_core.as_str().to_string(),
                effective_core: None,
                benchmark: None,
                error: Some(error.to_string()),
                relative_connect_latency_ratio: None,
                relative_first_byte_latency_ratio: None,
                relative_open_to_first_byte_gap_ratio: None,
                relative_throughput_ratio: None,
            },
        };

        entries.push(comparison_entry);
        reset_connection_state(&app, &state).await?;
    }

    {
        let mut store_data = store::load_store(&app)?;
        store_data.active_core = original_active_core;
        store::save_store(&app, &store_data)?;
    }

    let report =
        crate::engine::helix::benchmark::finalize_comparison_report(request.profile_id, entries);

    {
        let mut store_data = store::load_store(&app)?;
        store_data.helix_last_comparison_report = Some(report.clone());
        store::save_store(&app, &store_data)?;
    }

    let _ = crate::engine::diagnostics::record_event(
        &app,
        crate::engine::diagnostics::DiagnosticLevel::Info,
        "helix.benchmark",
        "Transport core comparison completed",
        serde_json::json!({
            "run_id": report.run_id,
            "profile_id": report.profile_id,
            "baseline_core": report.baseline_core,
            "entry_count": report.entries.len(),
            "entries": report.entries.iter().map(|entry| serde_json::json!({
                "requested_core": entry.requested_core,
                "effective_core": entry.effective_core,
                "median_open_to_first_byte_gap_ms": entry.benchmark.as_ref().and_then(|benchmark| benchmark.median_open_to_first_byte_gap_ms),
                "relative_open_to_first_byte_gap_ratio": entry.relative_open_to_first_byte_gap_ratio,
                "frame_queue_peak": entry
                    .benchmark
                    .as_ref()
                    .and_then(|benchmark| benchmark.helix_queue_pressure.as_ref())
                    .map(|pressure| pressure.frame_queue_peak),
                "recent_rtt_p95_ms": entry
                    .benchmark
                    .as_ref()
                    .and_then(|benchmark| benchmark.helix_queue_pressure.as_ref())
                    .and_then(|pressure| pressure.recent_rtt_p95_ms),
                "helix_continuity": entry
                    .benchmark
                    .as_ref()
                    .and_then(|benchmark| helix_continuity_json(benchmark.helix_continuity.as_ref())),
                "error": entry.error,
            })).collect::<Vec<_>>(),
        }),
    );
    report_helix_comparison_summary(&app, &report);

    Ok(report)
}

#[tauri::command]
pub async fn run_transport_target_matrix_comparison(
    request: crate::engine::helix::config::TransportBenchmarkMatrixRequest,
    app: AppHandle,
    state: State<'_, AppState>,
) -> Result<crate::engine::helix::config::TransportBenchmarkMatrixReport, AppError> {
    if request.profile_id.trim().is_empty() {
        return Err(AppError::Actionable {
            error: "Target matrix comparison requires a profile id".to_string(),
            resolution:
                "Select the desktop profile that should be used for the Helix/stable target matrix."
                    .to_string(),
        });
    }

    if request.targets.is_empty() {
        return Err(AppError::Actionable {
            error: "Target matrix comparison requires at least one target".to_string(),
            resolution:
                "Provide one or more benchmark targets so every core is measured against the same matrix."
                    .to_string(),
        });
    }

    let mut target_reports = Vec::new();
    for target in &request.targets {
        let benchmark_request =
            crate::engine::helix::benchmark::normalize_matrix_target(target, &request.benchmark);
        let comparison = run_transport_core_comparison(
            crate::engine::helix::config::TransportBenchmarkComparisonRequest {
                profile_id: request.profile_id.clone(),
                cores: request.cores.clone(),
                benchmark: benchmark_request.clone(),
            },
            app.clone(),
            state.clone(),
        )
        .await?;

        target_reports.push(
            crate::engine::helix::config::TransportBenchmarkMatrixTargetReport {
                label: target.label.clone(),
                host: target.host.clone(),
                port: target.port,
                path: benchmark_request
                    .target_path
                    .unwrap_or_else(|| "/".to_string()),
                comparison,
            },
        );
    }

    let report =
        crate::engine::helix::benchmark::finalize_matrix_report(request.profile_id, target_reports);

    {
        let mut store_data = store::load_store(&app)?;
        store_data.helix_last_matrix_report = Some(report.clone());
        store::save_store(&app, &store_data)?;
    }

    let _ = crate::engine::diagnostics::record_event(
        &app,
        crate::engine::diagnostics::DiagnosticLevel::Info,
        "helix.benchmark",
        "Transport target matrix comparison completed",
        serde_json::json!({
            "run_id": report.run_id,
            "profile_id": report.profile_id,
            "target_count": report.targets.len(),
            "baseline_core": report.baseline_core,
            "core_summaries": report.core_summaries.iter().map(|summary| serde_json::json!({
                "core": summary.core,
                "completed_targets": summary.completed_targets,
                "failed_targets": summary.failed_targets,
                "median_connect_latency_ms": summary.median_connect_latency_ms,
                "median_first_byte_latency_ms": summary.median_first_byte_latency_ms,
                "median_open_to_first_byte_gap_ms": summary.median_open_to_first_byte_gap_ms,
                "average_throughput_kbps": summary.average_throughput_kbps,
                "average_relative_open_to_first_byte_gap_ratio": summary.average_relative_open_to_first_byte_gap_ratio,
            })).collect::<Vec<_>>(),
            "targets": report.targets.iter().map(|target| {
                let helix_entry = target
                    .comparison
                    .entries
                    .iter()
                    .find(|entry| entry.effective_core.as_deref() == Some("helix") || entry.requested_core == "helix");
                serde_json::json!({
                    "label": target.label,
                    "host": target.host,
                    "port": target.port,
                    "path": target.path,
                    "helix_gap_ms": helix_entry
                        .and_then(|entry| entry.benchmark.as_ref())
                        .and_then(|benchmark| benchmark.median_open_to_first_byte_gap_ms),
                    "helix_gap_ratio": helix_entry.and_then(|entry| entry.relative_open_to_first_byte_gap_ratio),
                    "helix_continuity": helix_entry
                        .and_then(|entry| entry.benchmark.as_ref())
                        .and_then(|benchmark| helix_continuity_json(benchmark.helix_continuity.as_ref())),
                })
            }).collect::<Vec<_>>(),
        }),
    );
    maybe_record_transport_matrix_warning(&app, &report);
    report_helix_matrix_summary(&app, &report);

    Ok(report)
}

#[tauri::command]
pub async fn run_helix_recovery_benchmark(
    request: crate::engine::helix::config::HelixRecoveryBenchmarkRequest,
    app: AppHandle,
    state: State<'_, AppState>,
) -> Result<crate::engine::helix::config::HelixRecoveryBenchmarkReport, AppError> {
    if request.profile_id.trim().is_empty() {
        return Err(AppError::Actionable {
            error: "Helix recovery benchmark requires a profile id".to_string(),
            resolution:
                "Select the desktop profile that should be used for the Helix recovery drill."
                    .to_string(),
        });
    }

    let original_active_core = store::load_store(&app)?.active_core;
    reset_connection_state(&app, &state).await?;

    let run_result = async {
        {
            let mut store_data = store::load_store(&app)?;
            store_data.active_core = "helix".to_string();
            store::save_store(&app, &store_data)?;
        }

        connect_profile_internal(
            request.profile_id.clone(),
            false,
            false,
            "helix-recovery-benchmark",
            app.clone(),
            state.clone(),
        )
        .await?;

        let store_data = store::load_store(&app)?;
        if store_data.active_core != "helix" {
            return Err(AppError::Actionable {
                error: "Helix recovery benchmark could not keep Helix active".to_string(),
                resolution:
                    "Resolve a compatible Helix manifest and make sure the Helix runtime starts without immediate fallback."
                        .to_string(),
            });
        }

        let prepared_runtime = store_data.helix_last_prepared_runtime.ok_or_else(|| {
            AppError::System("Helix runtime was not prepared for the recovery drill".to_string())
        })?;
        let resolved_benchmark =
            crate::engine::helix::benchmark::resolve_transport_benchmark_request(
                &request.benchmark,
            );

        crate::engine::helix::benchmark::wait_for_proxy_ready(
            &prepared_runtime.proxy_url,
            std::time::Duration::from_secs(6),
        )
        .await?;

        let health_before =
            crate::engine::helix::benchmark::fetch_helix_sidecar_health(&prepared_runtime.health_url)
                .await
                .ok();
        let telemetry_before =
            crate::engine::helix::benchmark::fetch_helix_sidecar_telemetry(
                &prepared_runtime.health_url,
            )
            .await
            .ok();

        let action =
            crate::engine::helix::benchmark::trigger_helix_sidecar_action(
                &prepared_runtime.health_url,
                &request.mode,
            )
            .await?;

        let recovery_timeout = std::time::Duration::from_millis(
            request
                .recovery_timeout_ms
                .unwrap_or(12_000)
                .clamp(1_000, 30_000),
        );
        let proxy_probe_started_at = std::time::Instant::now();
        let probe_attempt_timeout = if resolved_benchmark.connect_timeout
            < std::time::Duration::from_millis(750)
        {
            resolved_benchmark.connect_timeout
        } else {
            std::time::Duration::from_millis(750)
        };
        let proxy_ready_result =
            crate::engine::helix::benchmark::wait_for_proxy_first_byte_ready(
                &prepared_runtime.proxy_url,
                &resolved_benchmark.target_host,
                resolved_benchmark.target_port,
                &resolved_benchmark.target_path,
                recovery_timeout,
                probe_attempt_timeout,
            )
            .await;
        let proxy_ready_probe = proxy_ready_result.as_ref().ok().cloned();
        let proxy_ready_latency_ms = proxy_ready_probe.as_ref().map(|_| {
            let post_action_latency_ms =
                i32::try_from(proxy_probe_started_at.elapsed().as_millis()).unwrap_or(i32::MAX);
            action
                .recovery_latency_ms
                .map(|base| base.saturating_add(post_action_latency_ms))
                .unwrap_or(post_action_latency_ms)
        });
        let proxy_ready_error = proxy_ready_result
            .as_ref()
            .err()
            .map(std::string::ToString::to_string);

        let health_after =
            crate::engine::helix::benchmark::fetch_helix_sidecar_health(&prepared_runtime.health_url)
                .await
                .ok();
        let telemetry_after =
            crate::engine::helix::benchmark::fetch_helix_sidecar_telemetry(
                &prepared_runtime.health_url,
            )
            .await
            .ok();

        let recovered = action.success && proxy_ready_probe.is_some();
        let same_route_recovered = if recovered {
            match (action.route_before.as_ref(), action.route_after.as_ref()) {
                (Some(route_before), Some(route_after)) => Some(route_before == route_after),
                _ => None,
            }
        } else {
            None
        };
        let benchmark_result = if recovered {
            crate::engine::helix::benchmark::run_transport_benchmark(
                &app,
                request.benchmark.clone(),
            )
            .await
            .ok()
        } else {
            None
        };
        let continuity_before = health_before
            .as_ref()
            .map(crate::engine::helix::benchmark::summarize_helix_continuity);
        let continuity_after = health_after
            .as_ref()
            .map(crate::engine::helix::benchmark::summarize_helix_continuity);

        Ok(crate::engine::helix::config::HelixRecoveryBenchmarkReport {
            schema_version: "1.0".to_string(),
            run_id: format!("bench-recovery-{}", uuid::Uuid::new_v4().simple()),
            generated_at: chrono::Utc::now().to_rfc3339(),
            profile_id: request.profile_id.clone(),
            mode: request.mode.as_str().to_string(),
            proxy_url: prepared_runtime.proxy_url,
            route_before: action.route_before.clone(),
            route_after: action.route_after.clone(),
            ready_recovery_latency_ms: action.recovery_latency_ms,
            proxy_ready_latency_ms,
            proxy_ready_open_to_first_byte_gap_ms: proxy_ready_probe
                .as_ref()
                .and_then(|sample| match (sample.connect_latency_ms, sample.first_byte_latency_ms) {
                    (Some(connect), Some(first_byte)) => {
                        Some(first_byte.saturating_sub(connect).max(0))
                    }
                    _ => None,
                }),
            proxy_ready_measurement: Some(
                "time-to-first-byte-through-socks-probe".to_string(),
            ),
            proxy_ready_probe,
            recovered,
            same_route_recovered,
            health_before,
            health_after,
            continuity_before,
            continuity_after,
            telemetry_before,
            telemetry_after,
            action: Some(action.clone()),
            post_recovery_benchmark: benchmark_result,
            error: proxy_ready_error,
        })
    }
    .await;

    let reset_result = reset_connection_state(&app, &state).await;
    let restore_result = {
        let mut store_data = store::load_store(&app)?;
        store_data.active_core = original_active_core;
        store::save_store(&app, &store_data)
    };
    reset_result?;
    restore_result?;

    let report = run_result?;
    {
        let mut store_data = store::load_store(&app)?;
        store_data.helix_last_recovery_report = Some(report.clone());
        store::save_store(&app, &store_data)?;
    }

    let _ = crate::engine::diagnostics::record_event(
        &app,
        crate::engine::diagnostics::DiagnosticLevel::Info,
        "helix.benchmark",
        "Helix recovery benchmark completed",
        serde_json::json!({
            "run_id": report.run_id,
            "profile_id": report.profile_id,
            "mode": report.mode,
            "recovered": report.recovered,
            "route_before": report.route_before,
            "route_after": report.route_after,
            "ready_recovery_latency_ms": report.ready_recovery_latency_ms,
            "proxy_ready_latency_ms": report.proxy_ready_latency_ms,
            "proxy_ready_open_to_first_byte_gap_ms": report.proxy_ready_open_to_first_byte_gap_ms,
            "same_route_recovered": report.same_route_recovered,
            "continuity_before": helix_continuity_json(report.continuity_before.as_ref()),
            "continuity_after": report.continuity_after.as_ref().map(|continuity| serde_json::json!({
                "grace_active": continuity.grace_active,
                "grace_route_endpoint_ref": continuity.grace_route_endpoint_ref,
                "grace_remaining_ms": continuity.grace_remaining_ms,
                "continuity_grace_entries": continuity.continuity_grace_entries,
                "successful_continuity_recovers": continuity.successful_continuity_recovers,
                "successful_cross_route_recovers": continuity.successful_cross_route_recovers,
                "last_continuity_recovery_ms": continuity.last_continuity_recovery_ms,
                "last_cross_route_recovery_ms": continuity.last_cross_route_recovery_ms,
            })),
            "post_recovery_median_open_to_first_byte_gap_ms": report
                .post_recovery_benchmark
                .as_ref()
                .and_then(|benchmark| benchmark.median_open_to_first_byte_gap_ms),
            "post_recovery_queue_peak": report
                .post_recovery_benchmark
                .as_ref()
                .and_then(|benchmark| benchmark.helix_queue_pressure.as_ref())
                .map(|pressure| pressure.frame_queue_peak),
            "post_recovery_rtt_p95_ms": report
                .post_recovery_benchmark
                .as_ref()
                .and_then(|benchmark| benchmark.helix_queue_pressure.as_ref())
                .and_then(|pressure| pressure.recent_rtt_p95_ms),
        }),
    );
    maybe_record_helix_recovery_warning(&app, &report);
    report_helix_recovery_summary(&app, &report);

    Ok(report)
}

#[tauri::command]
pub async fn get_installed_apps() -> Result<Vec<models::AppInfo>, AppError> {
    crate::engine::sys::apps::get_installed_apps().await
}

#[tauri::command]
pub async fn get_split_tunneling_apps(app: tauri::AppHandle) -> Result<Vec<String>, AppError> {
    let store = tokio::task::spawn_blocking(move || crate::engine::store::load_store(&app))
        .await
        .map_err(|e| AppError::System(format!("Tokio error: {}", e)))??;
    Ok(store.split_tunneling_apps)
}

#[tauri::command]
pub async fn save_split_tunneling_apps(
    apps: Vec<String>,
    app: tauri::AppHandle,
) -> Result<(), AppError> {
    tokio::task::spawn_blocking(move || {
        let mut store = crate::engine::store::load_store(&app)?;
        store.split_tunneling_apps = apps;
        crate::engine::store::save_store(&app, &store)
    })
    .await
    .map_err(|e| AppError::System(format!("Tokio error: {}", e)))??;
    Ok(())
}

#[tauri::command]
pub async fn get_split_tunneling_mode(app: tauri::AppHandle) -> Result<String, AppError> {
    let store = tokio::task::spawn_blocking(move || crate::engine::store::load_store(&app))
        .await
        .map_err(|e| AppError::System(format!("Tokio error: {}", e)))??;
    Ok(store.split_tunneling_mode)
}

#[tauri::command]
pub async fn save_split_tunneling_mode(
    mode: String,
    app: tauri::AppHandle,
) -> Result<(), AppError> {
    if mode != "allow" && mode != "disallow" {
        return Err(AppError::System("Invalid mode".to_string()));
    }
    tokio::task::spawn_blocking(move || {
        let mut store = crate::engine::store::load_store(&app)?;
        store.split_tunneling_mode = mode;
        crate::engine::store::save_store(&app, &store)
    })
    .await
    .map_err(|e| AppError::System(format!("Tokio error: {}", e)))??;
    Ok(())
}

#[tauri::command]
pub async fn get_stealth_mode(app: tauri::AppHandle) -> Result<bool, AppError> {
    let store = tokio::task::spawn_blocking(move || crate::engine::store::load_store(&app))
        .await
        .map_err(|e| AppError::System(format!("Tokio error: {}", e)))??;
    Ok(store.stealth_mode_enabled)
}

#[tauri::command]
pub async fn save_stealth_mode(enabled: bool, app: tauri::AppHandle) -> Result<(), AppError> {
    tokio::task::spawn_blocking(move || {
        let mut store = crate::engine::store::load_store(&app)?;
        store.stealth_mode_enabled = enabled;
        crate::engine::store::save_store(&app, &store)
    })
    .await
    .map_err(|e| AppError::System(format!("Tokio error: {}", e)))??;
    Ok(())
}

#[tauri::command]
pub async fn get_pqc_enforcement_mode(app: tauri::AppHandle) -> Result<bool, AppError> {
    let store = tokio::task::spawn_blocking(move || crate::engine::store::load_store(&app))
        .await
        .map_err(|e| AppError::System(format!("Tokio error: {}", e)))??;
    Ok(store.pqc_enforcement_mode)
}

#[tauri::command]
pub async fn save_pqc_enforcement_mode(
    enabled: bool,
    app: tauri::AppHandle,
) -> Result<(), AppError> {
    tokio::task::spawn_blocking(move || {
        let mut store = crate::engine::store::load_store(&app)?;
        store.pqc_enforcement_mode = enabled;
        crate::engine::store::save_store(&app, &store)
    })
    .await
    .map_err(|e| AppError::System(format!("Tokio error: {}", e)))??;
    Ok(())
}

#[tauri::command]
pub async fn audit_quantum_readiness(
    app: tauri::AppHandle,
) -> Result<Vec<models::AuditResult>, AppError> {
    let store_data = tokio::task::spawn_blocking(move || crate::engine::store::load_store(&app))
        .await
        .map_err(|e| AppError::System(format!("Tokio error: {}", e)))??;

    let pqc_enforcement = store_data.pqc_enforcement_mode;

    let results: Vec<models::AuditResult> = store_data
        .profiles
        .iter()
        .map(|node| {
            let pqc_active = node.pqc_enabled.unwrap_or(false) || pqc_enforcement;

            let status = match node.protocol.as_str() {
                "vless" | "wireguard" if pqc_active => "Ready",
                "hysteria2" | "tuic" => "Partially Ready",
                _ => "Not Ready",
            };

            models::AuditResult {
                id: node.id.clone(),
                name: node.name.clone(),
                protocol: node.protocol.clone(),
                status: status.to_string(),
            }
        })
        .collect();

    Ok(results)
}

#[tauri::command]
pub async fn get_privacy_shield_level(app: tauri::AppHandle) -> Result<String, AppError> {
    let store = tokio::task::spawn_blocking(move || crate::engine::store::load_store(&app))
        .await
        .map_err(|e| AppError::System(format!("Tokio error: {}", e)))??;
    Ok(store.privacy_shield_level)
}

#[tauri::command]
pub async fn set_privacy_shield_level(
    level: String,
    app: tauri::AppHandle,
) -> Result<(), AppError> {
    let requested_level = level.clone();
    let app_for_store = app.clone();
    tokio::task::spawn_blocking(move || {
        let mut store = crate::engine::store::load_store(&app_for_store)?;
        store.privacy_shield_level = level;
        crate::engine::store::save_store(&app_for_store, &store)
    })
    .await
    .map_err(|e| AppError::System(format!("Tokio error: {}", e)))??;

    if requested_level != "disabled" {
        crate::engine::sys::adblock::download_blocklists(&app, &requested_level).await?;
    }

    Ok(())
}

#[tauri::command]
pub async fn force_update_blocklists(app: tauri::AppHandle) -> Result<(), AppError> {
    let level = get_privacy_shield_level(app.clone()).await?;
    crate::engine::sys::adblock::download_blocklists(&app, &level).await?;
    Ok(())
}

#[tauri::command]
pub async fn get_threat_count(state: State<'_, AppState>) -> Result<u64, AppError> {
    use std::sync::atomic::Ordering;
    Ok(state
        .process_manager
        .threats_blocked
        .load(Ordering::Relaxed))
}

#[tauri::command]
pub async fn get_smart_connect_status(app: tauri::AppHandle) -> Result<bool, AppError> {
    let store = tokio::task::spawn_blocking(move || crate::engine::store::load_store(&app))
        .await
        .map_err(|e| AppError::System(format!("Tokio error: {}", e)))??;
    Ok(store.smart_connect_enabled)
}

#[tauri::command]
pub async fn set_smart_connect_status(
    enabled: bool,
    app: tauri::AppHandle,
) -> Result<(), AppError> {
    tokio::task::spawn_blocking(move || {
        let mut store = crate::engine::store::load_store(&app)?;
        store.smart_connect_enabled = enabled;
        crate::engine::store::save_store(&app, &store)
    })
    .await
    .map_err(|e| AppError::System(format!("Tokio error: {}", e)))??;
    Ok(())
}

#[tauri::command]
pub async fn get_network_rules(
    app: tauri::AppHandle,
) -> Result<
    std::collections::HashMap<String, crate::engine::sys::net_monitor::NetworkProfile>,
    AppError,
> {
    let store = tokio::task::spawn_blocking(move || crate::engine::store::load_store(&app))
        .await
        .map_err(|e| AppError::System(format!("Tokio error: {}", e)))??;
    Ok(store.network_rules)
}

#[tauri::command]
pub async fn update_network_rule(
    ssid: String,
    profile: crate::engine::sys::net_monitor::NetworkProfile,
    app: tauri::AppHandle,
) -> Result<(), AppError> {
    tokio::task::spawn_blocking(move || {
        let mut store = crate::engine::store::load_store(&app)?;
        store.network_rules.insert(ssid, profile);
        crate::engine::store::save_store(&app, &store)
    })
    .await
    .map_err(|e| AppError::System(format!("Tokio error: {}", e)))??;
    Ok(())
}

#[tauri::command]
pub async fn run_stealth_diagnostics(
    node_id: String,
    app: tauri::AppHandle,
) -> Result<crate::engine::sys::diagnostics::CensorshipReport, AppError> {
    let store = crate::engine::store::load_store(&app)?;
    let node = store
        .profiles
        .into_iter()
        .find(|p| p.id == node_id)
        .ok_or_else(|| AppError::System("Node not found".into()))?;
    crate::engine::sys::diagnostics::run_stealth_diagnostics(node, app).await
}

#[tauri::command]
pub async fn apply_stealth_fix(
    node_id: String,
    recommended_protocol: String,
    app: tauri::AppHandle,
    state: tauri::State<'_, crate::ipc::AppState>,
) -> Result<(), AppError> {
    let mut store = crate::engine::store::load_store(&app)?;
    let tun_mode = store.last_connection_options.tun_mode;
    let system_proxy = store.last_connection_options.system_proxy;
    if let Some(node) = store.profiles.iter_mut().find(|p| p.id == node_id) {
        if recommended_protocol == "xhttp"
            || recommended_protocol == "vless-reality"
            || recommended_protocol == "wireguard"
        {
            node.protocol = recommended_protocol;
        } else if recommended_protocol == "vless-stealth" {
            node.protocol = "vless".to_string();
            store.stealth_mode_enabled = true;
        }
    }
    crate::engine::store::save_store(&app, &store)?;
    // Reconnect to apply the altered node and stealth profile
    crate::ipc::connect_profile_internal(
        node_id,
        tun_mode,
        system_proxy,
        "stealth-fix",
        app.clone(),
        state,
    )
    .await?;
    Ok(())
}

#[tauri::command]
pub async fn start_remote_server(app: tauri::AppHandle) -> Result<String, AppError> {
    crate::engine::sys::remote_control::start_remote_server(app).await
}

#[tauri::command]
pub async fn stop_remote_server() -> Result<(), AppError> {
    crate::engine::sys::remote_control::stop_remote_server().await;
    Ok(())
}

// Removed redundant wrappers, these are exposed natively by `crate::engine::sys::net` and `discovery`
