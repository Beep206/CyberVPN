use std::{
    collections::HashMap,
    time::{Duration, Instant},
};

use chrono::Utc;
use tokio::{
    io::{AsyncReadExt, AsyncWriteExt},
    net::TcpStream,
    time::timeout,
};
use url::Url;

use crate::engine::{
    error::AppError,
    helix::config::{
        EngineCore, HelixContinuitySummary, HelixQueuePressureSummary, HelixRecoveryBenchmarkMode,
        HelixSidecarBenchActionReport, HelixSidecarHealth, HelixSidecarTelemetry,
        TransportBenchmarkComparisonEntry, TransportBenchmarkComparisonReport,
        TransportBenchmarkMatrixCoreSummary, TransportBenchmarkMatrixReport,
        TransportBenchmarkMatrixTarget, TransportBenchmarkMatrixTargetReport,
        TransportBenchmarkReport, TransportBenchmarkRequest, TransportBenchmarkSample,
    },
    store::{self, AppDataStore},
};

const DEFAULT_TARGET_HOST: &str = "example.com";
const DEFAULT_TARGET_PORT: u16 = 80;
const DEFAULT_TARGET_PATH: &str = "/";
const DEFAULT_ATTEMPTS: u32 = 5;
const DEFAULT_DOWNLOAD_LIMIT: usize = 32 * 1024;
const DEFAULT_CONNECT_TIMEOUT_MS: u64 = 2_500;
const SOCKS_VERSION: u8 = 0x05;
const SOCKS_CMD_CONNECT: u8 = 0x01;
const SOCKS_ATYP_IPV4: u8 = 0x01;
const SOCKS_ATYP_DOMAIN: u8 = 0x03;
const SOCKS_ATYP_IPV6: u8 = 0x04;
const PROXY_READY_POLL_INTERVAL: Duration = Duration::from_millis(10);

#[derive(Debug, Clone)]
pub(crate) struct ResolvedTransportBenchmarkRequest {
    pub target_host: String,
    pub target_port: u16,
    pub target_path: String,
    pub attempts: u32,
    pub download_bytes_limit: usize,
    pub connect_timeout: Duration,
}

pub(crate) fn resolve_transport_benchmark_request(
    request: &TransportBenchmarkRequest,
) -> ResolvedTransportBenchmarkRequest {
    ResolvedTransportBenchmarkRequest {
        target_host: request
            .target_host
            .clone()
            .unwrap_or_else(|| DEFAULT_TARGET_HOST.to_string()),
        target_port: request.target_port.unwrap_or(DEFAULT_TARGET_PORT),
        target_path: normalize_target_path(
            request
                .target_path
                .clone()
                .unwrap_or_else(|| DEFAULT_TARGET_PATH.to_string()),
        ),
        attempts: request.attempts.unwrap_or(DEFAULT_ATTEMPTS).clamp(1, 20),
        download_bytes_limit: request
            .download_bytes_limit
            .unwrap_or(DEFAULT_DOWNLOAD_LIMIT)
            .clamp(1024, 512 * 1024),
        connect_timeout: Duration::from_millis(
            request
                .connect_timeout_ms
                .unwrap_or(DEFAULT_CONNECT_TIMEOUT_MS)
                .clamp(500, 10_000),
        ),
    }
}

pub async fn run_transport_benchmark(
    app: &tauri::AppHandle,
    request: TransportBenchmarkRequest,
) -> Result<TransportBenchmarkReport, AppError> {
    let store_data = store::load_store(app)?;
    let active_core = EngineCore::try_from(store_data.active_core.as_str())?;
    let resolved = resolve_transport_benchmark_request(&request);
    let proxy_url =
        resolve_proxy_url_for_core(&store_data, &active_core, request.proxy_url.clone())?;

    let mut samples = Vec::new();
    for attempt in 1..=resolved.attempts {
        let sample = benchmark_proxy_endpoint(
            &proxy_url,
            &resolved.target_host,
            resolved.target_port,
            &resolved.target_path,
            attempt,
            resolved.download_bytes_limit,
            resolved.connect_timeout,
        )
        .await;
        samples.push(sample);
    }

    let successes =
        u32::try_from(samples.iter().filter(|sample| sample.success).count()).unwrap_or(u32::MAX);
    let failures = resolved.attempts.saturating_sub(successes);

    let connect_latencies = samples
        .iter()
        .filter_map(|sample| sample.connect_latency_ms)
        .collect::<Vec<_>>();
    let first_byte_latencies = samples
        .iter()
        .filter_map(|sample| sample.first_byte_latency_ms)
        .collect::<Vec<_>>();
    let open_to_first_byte_gaps = samples
        .iter()
        .filter_map(sample_open_to_first_byte_gap_ms)
        .collect::<Vec<_>>();
    let throughput_values = samples
        .iter()
        .filter_map(|sample| sample.throughput_kbps)
        .collect::<Vec<_>>();
    let bytes_read_total = samples.iter().fold(0_u64, |total, sample| {
        total.saturating_add(sample.bytes_read)
    });
    let bytes_written_total = samples.iter().fold(0_u64, |total, sample| {
        total.saturating_add(sample.bytes_written)
    });
    let helix_queue_pressure = if matches!(active_core, EngineCore::Helix) {
        if let Some(runtime) = store_data.helix_last_prepared_runtime.as_ref() {
            fetch_helix_sidecar_telemetry(&runtime.health_url)
                .await
                .ok()
                .map(|telemetry| summarize_helix_queue_pressure(&telemetry))
        } else {
            None
        }
    } else {
        None
    };
    let helix_continuity = if matches!(active_core, EngineCore::Helix) {
        if let Some(runtime) = store_data.helix_last_prepared_runtime.as_ref() {
            fetch_helix_sidecar_health(&runtime.health_url)
                .await
                .ok()
                .map(|health| summarize_helix_continuity(&health))
        } else {
            None
        }
    } else {
        None
    };

    Ok(TransportBenchmarkReport {
        schema_version: "1.0".to_string(),
        run_id: format!("bench-{}", uuid::Uuid::new_v4().simple()),
        generated_at: Utc::now().to_rfc3339(),
        active_core: active_core.as_str().to_string(),
        proxy_url,
        target_host: resolved.target_host,
        target_port: resolved.target_port,
        target_path: resolved.target_path,
        attempts: resolved.attempts,
        successes,
        failures,
        median_connect_latency_ms: percentile_i32(&connect_latencies, 0.50),
        p95_connect_latency_ms: percentile_i32(&connect_latencies, 0.95),
        median_first_byte_latency_ms: percentile_i32(&first_byte_latencies, 0.50),
        p95_first_byte_latency_ms: percentile_i32(&first_byte_latencies, 0.95),
        median_open_to_first_byte_gap_ms: percentile_i32(&open_to_first_byte_gaps, 0.50),
        p95_open_to_first_byte_gap_ms: percentile_i32(&open_to_first_byte_gaps, 0.95),
        average_throughput_kbps: average_f64(&throughput_values),
        helix_queue_pressure,
        helix_continuity,
        bytes_read_total,
        bytes_written_total,
        samples,
    })
}

pub(crate) fn resolve_proxy_url_for_core(
    store_data: &AppDataStore,
    active_core: &EngineCore,
    override_proxy_url: Option<String>,
) -> Result<String, AppError> {
    if let Some(proxy_url) = override_proxy_url {
        return Ok(proxy_url);
    }

    if matches!(active_core, EngineCore::Helix) {
        return store_data
            .helix_last_prepared_runtime
            .as_ref()
            .map(|runtime| runtime.proxy_url.clone())
            .ok_or_else(|| AppError::Actionable {
                error: "Helix runtime is not prepared".to_string(),
                resolution: "Resolve and prepare the Helix runtime before starting a benchmark."
                    .to_string(),
            });
    }

    Ok(format!(
        "socks5://127.0.0.1:{}",
        store_data.local_socks_port.unwrap_or(2080)
    ))
}

pub(crate) async fn wait_for_proxy_ready(
    proxy_url: &str,
    ready_timeout: Duration,
) -> Result<(), AppError> {
    let deadline = tokio::time::Instant::now() + ready_timeout;

    loop {
        match probe_socks5_ready(proxy_url, Duration::from_millis(750)).await {
            Ok(()) => return Ok(()),
            Err(error) => {
                if tokio::time::Instant::now() >= deadline {
                    return Err(AppError::System(format!(
                        "Proxy endpoint did not become ready in time: {error}"
                    )));
                }
            }
        }

        tokio::time::sleep(PROXY_READY_POLL_INTERVAL).await;
    }
}

pub(crate) async fn wait_for_proxy_first_byte_ready(
    proxy_url: &str,
    target_host: &str,
    target_port: u16,
    target_path: &str,
    ready_timeout: Duration,
    attempt_timeout: Duration,
) -> Result<TransportBenchmarkSample, AppError> {
    let deadline = tokio::time::Instant::now() + ready_timeout;
    let mut last_error = None;

    loop {
        let now = tokio::time::Instant::now();
        if now >= deadline {
            let message = last_error.unwrap_or_else(|| {
                "Proxy endpoint did not become ready for first-byte traffic in time".to_string()
            });
            return Err(AppError::System(message));
        }

        let remaining = deadline.saturating_duration_since(now);
        let probe_timeout = if attempt_timeout < remaining {
            attempt_timeout
        } else {
            remaining
        };

        match benchmark_proxy_endpoint_inner(
            proxy_url,
            target_host,
            target_port,
            target_path,
            4 * 1024,
            probe_timeout,
            true,
        )
        .await
        {
            Ok(sample) => return Ok(sample),
            Err(error) => last_error = Some(error.to_string()),
        }

        tokio::time::sleep(PROXY_READY_POLL_INTERVAL).await;
    }
}

pub(crate) fn default_comparison_cores() -> Vec<EngineCore> {
    vec![EngineCore::Helix, EngineCore::SingBox, EngineCore::Xray]
}

pub(crate) fn finalize_comparison_report(
    profile_id: String,
    mut entries: Vec<TransportBenchmarkComparisonEntry>,
) -> TransportBenchmarkComparisonReport {
    let baseline_index = preferred_baseline_index(&entries);
    let baseline_core = baseline_index.and_then(|index| entries[index].effective_core.clone());
    let baseline_report = baseline_index.and_then(|index| entries[index].benchmark.clone());

    if let Some(baseline_report) = baseline_report.as_ref() {
        for entry in &mut entries {
            let Some(report) = entry.benchmark.as_ref() else {
                continue;
            };

            entry.relative_connect_latency_ratio = ratio_optional_i32(
                report.median_connect_latency_ms,
                baseline_report.median_connect_latency_ms,
            );
            entry.relative_first_byte_latency_ratio = ratio_optional_i32(
                report.median_first_byte_latency_ms,
                baseline_report.median_first_byte_latency_ms,
            );
            entry.relative_open_to_first_byte_gap_ratio = ratio_optional_i32(
                report.median_open_to_first_byte_gap_ms,
                baseline_report.median_open_to_first_byte_gap_ms,
            );
            entry.relative_throughput_ratio = ratio_optional_f64(
                report.average_throughput_kbps,
                baseline_report.average_throughput_kbps,
            );
        }
    }

    TransportBenchmarkComparisonReport {
        schema_version: "1.0".to_string(),
        run_id: format!("bench-compare-{}", uuid::Uuid::new_v4().simple()),
        generated_at: Utc::now().to_rfc3339(),
        profile_id,
        baseline_core,
        entries,
    }
}

pub(crate) fn finalize_matrix_report(
    profile_id: String,
    target_reports: Vec<TransportBenchmarkMatrixTargetReport>,
) -> TransportBenchmarkMatrixReport {
    let baseline_core = most_common_baseline(&target_reports);
    let mut per_core = HashMap::<String, Vec<&TransportBenchmarkComparisonEntry>>::new();

    for target in &target_reports {
        for entry in &target.comparison.entries {
            let core = entry
                .effective_core
                .clone()
                .unwrap_or_else(|| entry.requested_core.clone());
            per_core.entry(core).or_default().push(entry);
        }
    }

    let mut core_summaries = per_core
        .into_iter()
        .map(|(core, entries)| summarize_matrix_core(core, &entries))
        .collect::<Vec<_>>();
    core_summaries.sort_by(|left, right| left.core.cmp(&right.core));

    TransportBenchmarkMatrixReport {
        schema_version: "1.0".to_string(),
        run_id: format!("bench-matrix-{}", uuid::Uuid::new_v4().simple()),
        generated_at: Utc::now().to_rfc3339(),
        profile_id,
        baseline_core,
        targets: target_reports,
        core_summaries,
    }
}

fn summarize_matrix_core(
    core: String,
    entries: &[&TransportBenchmarkComparisonEntry],
) -> TransportBenchmarkMatrixCoreSummary {
    let successful_reports = entries
        .iter()
        .filter_map(|entry| entry.benchmark.as_ref())
        .collect::<Vec<_>>();
    let completed_targets = u32::try_from(successful_reports.len()).unwrap_or(u32::MAX);
    let failed_targets =
        u32::try_from(entries.len().saturating_sub(successful_reports.len())).unwrap_or(u32::MAX);

    let connect_latencies = successful_reports
        .iter()
        .filter_map(|report| report.median_connect_latency_ms)
        .collect::<Vec<_>>();
    let first_byte_latencies = successful_reports
        .iter()
        .filter_map(|report| report.median_first_byte_latency_ms)
        .collect::<Vec<_>>();
    let throughput_values = successful_reports
        .iter()
        .filter_map(|report| report.average_throughput_kbps)
        .collect::<Vec<_>>();
    let gap_values = successful_reports
        .iter()
        .filter_map(|report| report.median_open_to_first_byte_gap_ms)
        .collect::<Vec<_>>();
    let connect_ratios = entries
        .iter()
        .filter_map(|entry| entry.relative_connect_latency_ratio)
        .collect::<Vec<_>>();
    let first_byte_ratios = entries
        .iter()
        .filter_map(|entry| entry.relative_first_byte_latency_ratio)
        .collect::<Vec<_>>();
    let gap_ratios = entries
        .iter()
        .filter_map(|entry| entry.relative_open_to_first_byte_gap_ratio)
        .collect::<Vec<_>>();
    let throughput_ratios = entries
        .iter()
        .filter_map(|entry| entry.relative_throughput_ratio)
        .collect::<Vec<_>>();

    TransportBenchmarkMatrixCoreSummary {
        core,
        completed_targets,
        failed_targets,
        median_connect_latency_ms: percentile_i32(&connect_latencies, 0.50),
        median_first_byte_latency_ms: percentile_i32(&first_byte_latencies, 0.50),
        median_open_to_first_byte_gap_ms: percentile_i32(&gap_values, 0.50),
        average_throughput_kbps: average_f64(&throughput_values),
        average_relative_connect_latency_ratio: average_f64(&connect_ratios),
        average_relative_first_byte_latency_ratio: average_f64(&first_byte_ratios),
        average_relative_open_to_first_byte_gap_ratio: average_f64(&gap_ratios),
        average_relative_throughput_ratio: average_f64(&throughput_ratios),
    }
}

fn sample_open_to_first_byte_gap_ms(sample: &TransportBenchmarkSample) -> Option<i32> {
    match (sample.connect_latency_ms, sample.first_byte_latency_ms) {
        (Some(connect), Some(first_byte)) => Some(first_byte.saturating_sub(connect).max(0)),
        _ => None,
    }
}

fn summarize_helix_queue_pressure(telemetry: &HelixSidecarTelemetry) -> HelixQueuePressureSummary {
    let recent_rtt = telemetry
        .recent_rtt_ms
        .iter()
        .filter_map(|value| i32::try_from(*value).ok())
        .collect::<Vec<_>>();
    let recent_stream_frame_peaks = telemetry
        .recent_streams
        .iter()
        .map(|stream| stream.peak_frame_queue_depth)
        .collect::<Vec<_>>();
    let recent_stream_inbound_peaks = telemetry
        .recent_streams
        .iter()
        .map(|stream| stream.peak_inbound_queue_depth)
        .collect::<Vec<_>>();

    HelixQueuePressureSummary {
        frame_queue_depth: telemetry.health.frame_queue_depth,
        frame_queue_peak: telemetry.health.frame_queue_peak,
        active_streams: telemetry.health.active_streams,
        pending_open_streams: telemetry.health.pending_open_streams,
        max_concurrent_streams: telemetry.health.max_concurrent_streams,
        recent_rtt_p50_ms: percentile_i32(&recent_rtt, 0.50),
        recent_rtt_p95_ms: percentile_i32(&recent_rtt, 0.95),
        recent_stream_peak_frame_queue_depth: recent_stream_frame_peaks.into_iter().max(),
        recent_stream_peak_inbound_queue_depth: recent_stream_inbound_peaks.into_iter().max(),
    }
}

pub(crate) fn summarize_helix_continuity(health: &HelixSidecarHealth) -> HelixContinuitySummary {
    HelixContinuitySummary {
        grace_active: health.continuity_grace_active,
        grace_route_endpoint_ref: health.continuity_grace_route_endpoint_ref.clone(),
        grace_remaining_ms: health.continuity_grace_remaining_ms,
        active_streams: health.active_streams,
        pending_open_streams: health.pending_open_streams,
        active_route_quarantined: health.active_route_quarantined,
        active_route_quarantine_remaining_ms: health.active_route_quarantine_remaining_ms,
        continuity_grace_entries: health.active_route_continuity_grace_entries,
        successful_continuity_recovers: health.active_route_successful_continuity_recovers,
        failed_continuity_recovers: health.active_route_failed_continuity_recovers,
        last_continuity_recovery_ms: health.active_route_last_continuity_recovery_ms,
        successful_cross_route_recovers: health.active_route_successful_cross_route_recovers,
        last_cross_route_recovery_ms: health.active_route_last_cross_route_recovery_ms,
    }
}

fn most_common_baseline(target_reports: &[TransportBenchmarkMatrixTargetReport]) -> Option<String> {
    let mut counts = HashMap::<String, u32>::new();
    for target in target_reports {
        if let Some(core) = target.comparison.baseline_core.as_ref() {
            *counts.entry(core.clone()).or_default() += 1;
        }
    }

    counts
        .into_iter()
        .max_by_key(|(_, count)| *count)
        .map(|(core, _)| core)
}

pub(crate) async fn fetch_helix_sidecar_health(
    health_url: &str,
) -> Result<HelixSidecarHealth, AppError> {
    fetch_sidecar_json(health_url).await
}

pub(crate) async fn fetch_helix_sidecar_telemetry(
    health_url: &str,
) -> Result<HelixSidecarTelemetry, AppError> {
    let telemetry_url = derive_sidecar_endpoint_url(health_url, "/telemetry")?;
    fetch_sidecar_json(&telemetry_url).await
}

pub(crate) async fn trigger_helix_sidecar_action(
    health_url: &str,
    mode: &HelixRecoveryBenchmarkMode,
) -> Result<HelixSidecarBenchActionReport, AppError> {
    let endpoint = match mode {
        HelixRecoveryBenchmarkMode::Failover => "/bench/failover",
        HelixRecoveryBenchmarkMode::Reconnect => "/bench/reconnect",
    };
    let action_url = derive_sidecar_endpoint_url(health_url, endpoint)?;
    let client = reqwest::Client::builder()
        .timeout(Duration::from_secs(15))
        .build()?;
    let response = client.post(action_url).send().await?;
    let response = response.error_for_status()?;
    let report = response.json::<HelixSidecarBenchActionReport>().await?;
    Ok(report)
}

pub(crate) fn normalize_matrix_target(
    target: &TransportBenchmarkMatrixTarget,
    benchmark: &TransportBenchmarkRequest,
) -> TransportBenchmarkRequest {
    let mut request = benchmark.clone();
    request.target_host = Some(target.host.clone());
    request.target_port = Some(target.port);
    request.target_path = Some(normalize_target_path(
        target
            .path
            .clone()
            .unwrap_or_else(|| DEFAULT_TARGET_PATH.to_string()),
    ));
    request
}

async fn fetch_sidecar_json<T>(url: &str) -> Result<T, AppError>
where
    T: serde::de::DeserializeOwned,
{
    let client = reqwest::Client::builder()
        .timeout(Duration::from_millis(1_500))
        .build()?;
    let response = client.get(url).send().await?;
    let response = response.error_for_status()?;
    Ok(response.json::<T>().await?)
}

fn derive_sidecar_endpoint_url(health_url: &str, path: &str) -> Result<String, AppError> {
    let mut url = Url::parse(health_url)
        .map_err(|error| AppError::System(format!("Invalid Helix health URL: {error}")))?;
    url.set_path(path);
    Ok(url.to_string())
}

fn normalize_target_path(path: String) -> String {
    if path.starts_with('/') {
        path
    } else {
        format!("/{path}")
    }
}

pub(crate) async fn benchmark_proxy_endpoint(
    proxy_url: &str,
    target_host: &str,
    target_port: u16,
    target_path: &str,
    attempt: u32,
    download_bytes_limit: usize,
    connect_timeout: Duration,
) -> TransportBenchmarkSample {
    match benchmark_proxy_endpoint_inner(
        proxy_url,
        target_host,
        target_port,
        target_path,
        download_bytes_limit,
        connect_timeout,
        false,
    )
    .await
    {
        Ok(sample) => TransportBenchmarkSample { attempt, ..sample },
        Err(error) => TransportBenchmarkSample {
            attempt,
            success: false,
            connect_latency_ms: None,
            first_byte_latency_ms: None,
            bytes_read: 0,
            bytes_written: 0,
            throughput_kbps: None,
            error: Some(error.to_string()),
        },
    }
}

async fn probe_socks5_ready(proxy_url: &str, connect_timeout: Duration) -> Result<(), AppError> {
    let proxy = Url::parse(proxy_url)
        .map_err(|error| AppError::System(format!("Invalid benchmark proxy URL: {error}")))?;
    let proxy_host = proxy
        .host_str()
        .ok_or_else(|| AppError::System("Benchmark proxy URL is missing a host".to_string()))?;
    let proxy_port = proxy
        .port_or_known_default()
        .ok_or_else(|| AppError::System("Benchmark proxy URL is missing a port".to_string()))?;

    let mut stream = timeout(
        connect_timeout,
        TcpStream::connect((proxy_host, proxy_port)),
    )
    .await
    .map_err(|_| AppError::System("Timed out while probing benchmark proxy".to_string()))??;
    let _ = stream.set_nodelay(true);

    timeout(
        connect_timeout,
        stream.write_all(&[SOCKS_VERSION, 0x01, 0x00]),
    )
    .await
    .map_err(|_| AppError::System("Timed out during SOCKS5 readiness greeting".to_string()))??;

    let mut reply = [0_u8; 2];
    timeout(connect_timeout, stream.read_exact(&mut reply))
        .await
        .map_err(|_| AppError::System("Timed out during SOCKS5 readiness reply".to_string()))??;

    if reply != [SOCKS_VERSION, 0x00] {
        return Err(AppError::System(format!(
            "SOCKS5 readiness probe failed with reply {:?}",
            reply
        )));
    }

    Ok(())
}

async fn benchmark_proxy_endpoint_inner(
    proxy_url: &str,
    target_host: &str,
    target_port: u16,
    target_path: &str,
    download_bytes_limit: usize,
    connect_timeout: Duration,
    stop_after_first_byte: bool,
) -> Result<TransportBenchmarkSample, AppError> {
    let proxy = Url::parse(proxy_url)
        .map_err(|error| AppError::System(format!("Invalid benchmark proxy URL: {error}")))?;
    let proxy_host = proxy
        .host_str()
        .ok_or_else(|| AppError::System("Benchmark proxy URL is missing a host".to_string()))?;
    let proxy_port = proxy
        .port_or_known_default()
        .ok_or_else(|| AppError::System("Benchmark proxy URL is missing a port".to_string()))?;

    let connect_started = Instant::now();
    let mut stream = timeout(
        connect_timeout,
        TcpStream::connect((proxy_host, proxy_port)),
    )
    .await
    .map_err(|_| AppError::System("Timed out while connecting to benchmark proxy".to_string()))??;
    let _ = stream.set_nodelay(true);
    perform_socks5_connect(&mut stream, target_host, target_port, connect_timeout).await?;
    let connect_latency_ms =
        i32::try_from(connect_started.elapsed().as_millis()).unwrap_or(i32::MAX);

    let request_body = format!(
        "GET {target_path} HTTP/1.1\r\nHost: {target_host}\r\nUser-Agent: CyberVPN-Benchmark\r\nConnection: close\r\n\r\n"
    );
    let bytes_written = u64::try_from(request_body.len()).unwrap_or(u64::MAX);
    let download_started = Instant::now();
    timeout(connect_timeout, stream.write_all(request_body.as_bytes()))
        .await
        .map_err(|_| AppError::System("Timed out while sending benchmark request".to_string()))??;

    let mut buffer = vec![0_u8; 16 * 1024];
    let mut bytes_read = 0_u64;
    let mut first_byte_latency_ms = None;

    loop {
        let read = match timeout(connect_timeout, stream.read(&mut buffer)).await {
            Ok(Ok(read)) => read,
            Ok(Err(error)) => {
                return Err(AppError::System(format!(
                    "Benchmark read through proxy failed: {error}"
                )));
            }
            Err(_) => {
                if bytes_read == 0 {
                    return Err(AppError::System(
                        "Timed out while waiting for benchmark response bytes".to_string(),
                    ));
                }
                break;
            }
        };

        if read == 0 {
            break;
        }

        if first_byte_latency_ms.is_none() {
            first_byte_latency_ms =
                Some(i32::try_from(download_started.elapsed().as_millis()).unwrap_or(i32::MAX));
            if stop_after_first_byte {
                bytes_read = bytes_read.saturating_add(u64::try_from(read).unwrap_or(u64::MAX));
                break;
            }
        }

        bytes_read = bytes_read.saturating_add(u64::try_from(read).unwrap_or(u64::MAX));
        if usize::try_from(bytes_read).unwrap_or(usize::MAX) >= download_bytes_limit {
            break;
        }
    }

    let total_download_seconds = download_started.elapsed().as_secs_f64();
    let throughput_kbps = if total_download_seconds > 0.0 && bytes_read > 0 {
        Some(((bytes_read as f64) * 8.0 / 1000.0) / total_download_seconds)
    } else {
        None
    };

    Ok(TransportBenchmarkSample {
        attempt: 0,
        success: true,
        connect_latency_ms: Some(connect_latency_ms),
        first_byte_latency_ms,
        bytes_read,
        bytes_written,
        throughput_kbps,
        error: None,
    })
}

async fn perform_socks5_connect(
    stream: &mut TcpStream,
    target_host: &str,
    target_port: u16,
    connect_timeout: Duration,
) -> Result<(), AppError> {
    timeout(
        connect_timeout,
        stream.write_all(&[SOCKS_VERSION, 0x01, 0x00]),
    )
    .await
    .map_err(|_| AppError::System("Timed out during SOCKS5 greeting".to_string()))??;

    let mut method_reply = [0_u8; 2];
    timeout(connect_timeout, stream.read_exact(&mut method_reply))
        .await
        .map_err(|_| AppError::System("Timed out waiting for SOCKS5 method reply".to_string()))??;
    if method_reply != [SOCKS_VERSION, 0x00] {
        return Err(AppError::System(format!(
            "SOCKS5 proxy rejected no-auth negotiation: {:?}",
            method_reply
        )));
    }

    let mut request = vec![SOCKS_VERSION, SOCKS_CMD_CONNECT, 0x00];
    if let Ok(ipv4) = target_host.parse::<std::net::Ipv4Addr>() {
        request.push(SOCKS_ATYP_IPV4);
        request.extend_from_slice(&ipv4.octets());
    } else if let Ok(ipv6) = target_host.parse::<std::net::Ipv6Addr>() {
        request.push(SOCKS_ATYP_IPV6);
        request.extend_from_slice(&ipv6.octets());
    } else {
        let host_bytes = target_host.as_bytes();
        let host_len = u8::try_from(host_bytes.len()).map_err(|_| {
            AppError::System("SOCKS5 benchmark target host is too long".to_string())
        })?;
        request.push(SOCKS_ATYP_DOMAIN);
        request.push(host_len);
        request.extend_from_slice(host_bytes);
    }
    request.extend_from_slice(&target_port.to_be_bytes());

    timeout(connect_timeout, stream.write_all(&request))
        .await
        .map_err(|_| AppError::System("Timed out sending SOCKS5 connect request".to_string()))??;

    let mut reply_head = [0_u8; 4];
    timeout(connect_timeout, stream.read_exact(&mut reply_head))
        .await
        .map_err(|_| {
            AppError::System("Timed out waiting for SOCKS5 connect reply".to_string())
        })??;
    if reply_head[0] != SOCKS_VERSION || reply_head[1] != 0x00 {
        return Err(AppError::System(format!(
            "SOCKS5 connect failed with reply code {}",
            reply_head[1]
        )));
    }

    match reply_head[3] {
        SOCKS_ATYP_IPV4 => {
            let mut tail = [0_u8; 6];
            timeout(connect_timeout, stream.read_exact(&mut tail))
                .await
                .map_err(|_| {
                    AppError::System("Timed out reading SOCKS5 IPv4 connect tail".to_string())
                })??;
        }
        SOCKS_ATYP_IPV6 => {
            let mut tail = [0_u8; 18];
            timeout(connect_timeout, stream.read_exact(&mut tail))
                .await
                .map_err(|_| {
                    AppError::System("Timed out reading SOCKS5 IPv6 connect tail".to_string())
                })??;
        }
        SOCKS_ATYP_DOMAIN => {
            let mut len = [0_u8; 1];
            timeout(connect_timeout, stream.read_exact(&mut len))
                .await
                .map_err(|_| {
                    AppError::System("Timed out reading SOCKS5 domain length".to_string())
                })??;
            let mut tail = vec![0_u8; usize::from(len[0]) + 2];
            timeout(connect_timeout, stream.read_exact(&mut tail))
                .await
                .map_err(|_| {
                    AppError::System("Timed out reading SOCKS5 domain connect tail".to_string())
                })??;
        }
        atyp => {
            return Err(AppError::System(format!(
                "SOCKS5 proxy returned unsupported reply address type: {atyp}"
            )));
        }
    }

    Ok(())
}

fn percentile_i32(values: &[i32], percentile: f64) -> Option<i32> {
    if values.is_empty() {
        return None;
    }

    let mut sorted = values.to_vec();
    sorted.sort_unstable();
    let index = ((sorted.len() as f64 * percentile).ceil() as usize)
        .saturating_sub(1)
        .min(sorted.len().saturating_sub(1));
    Some(sorted[index])
}

fn average_f64(values: &[f64]) -> Option<f64> {
    if values.is_empty() {
        return None;
    }

    Some(values.iter().sum::<f64>() / values.len() as f64)
}

fn preferred_baseline_index(entries: &[TransportBenchmarkComparisonEntry]) -> Option<usize> {
    for preferred_core in ["sing-box", "xray", "helix"] {
        if let Some(index) = entries.iter().position(|entry| {
            entry.error.is_none() && entry.effective_core.as_deref() == Some(preferred_core)
        }) {
            return Some(index);
        }
    }

    entries.iter().position(|entry| entry.error.is_none())
}

fn ratio_optional_i32(candidate: Option<i32>, baseline: Option<i32>) -> Option<f64> {
    match (candidate, baseline) {
        (Some(candidate), Some(baseline)) if baseline > 0 => {
            Some(candidate as f64 / baseline as f64)
        }
        _ => None,
    }
}

fn ratio_optional_f64(candidate: Option<f64>, baseline: Option<f64>) -> Option<f64> {
    match (candidate, baseline) {
        (Some(candidate), Some(baseline)) if baseline > 0.0 => Some(candidate / baseline),
        _ => None,
    }
}

#[cfg(test)]
mod tests {
    use std::{net::SocketAddr, time::Duration};

    use helix_runtime::{spawn_client, spawn_server, ClientConfig, ServerConfig, TransportRoute};
    use tokio::{
        io::{AsyncReadExt, AsyncWriteExt},
        net::TcpListener,
    };

    use crate::engine::helix::config::{
        EngineCore, TransportBenchmarkComparisonEntry, TransportBenchmarkMatrixTargetReport,
        TransportBenchmarkReport,
    };

    use crate::engine::helix::sidecar::run_proxy_accept_loop;

    use super::{
        benchmark_proxy_endpoint, default_comparison_cores, finalize_comparison_report,
        finalize_matrix_report, normalize_target_path, percentile_i32,
        wait_for_proxy_first_byte_ready,
    };

    #[test]
    fn normalizes_target_path() {
        assert_eq!(normalize_target_path("/health".to_string()), "/health");
        assert_eq!(normalize_target_path("metrics".to_string()), "/metrics");
    }

    #[test]
    fn computes_percentiles() {
        let values = vec![10, 20, 30, 40, 50];
        assert_eq!(percentile_i32(&values, 0.50), Some(30));
        assert_eq!(percentile_i32(&values, 0.95), Some(50));
    }

    #[test]
    fn uses_stable_core_as_comparison_baseline_when_available() {
        let report = finalize_comparison_report(
            "profile-1".to_string(),
            vec![
                TransportBenchmarkComparisonEntry {
                    requested_core: "helix".to_string(),
                    effective_core: Some("helix".to_string()),
                    benchmark: Some(TransportBenchmarkReport {
                        schema_version: "1.0".to_string(),
                        run_id: "pt".to_string(),
                        generated_at: "2026-03-31T12:00:00Z".to_string(),
                        active_core: "helix".to_string(),
                        proxy_url: "socks5://127.0.0.1:38990".to_string(),
                        target_host: "example.com".to_string(),
                        target_port: 80,
                        target_path: "/".to_string(),
                        attempts: 5,
                        successes: 5,
                        failures: 0,
                        median_connect_latency_ms: Some(35),
                        p95_connect_latency_ms: Some(50),
                        median_first_byte_latency_ms: Some(55),
                        p95_first_byte_latency_ms: Some(70),
                        median_open_to_first_byte_gap_ms: Some(20),
                        p95_open_to_first_byte_gap_ms: Some(20),
                        average_throughput_kbps: Some(5000.0),
                        helix_queue_pressure: None,
                        helix_continuity: None,
                        bytes_read_total: 1024,
                        bytes_written_total: 512,
                        samples: Vec::new(),
                    }),
                    error: None,
                    relative_connect_latency_ratio: None,
                    relative_first_byte_latency_ratio: None,
                    relative_open_to_first_byte_gap_ratio: None,
                    relative_throughput_ratio: None,
                },
                TransportBenchmarkComparisonEntry {
                    requested_core: "sing-box".to_string(),
                    effective_core: Some("sing-box".to_string()),
                    benchmark: Some(TransportBenchmarkReport {
                        schema_version: "1.0".to_string(),
                        run_id: "sb".to_string(),
                        generated_at: "2026-03-31T12:00:00Z".to_string(),
                        active_core: "sing-box".to_string(),
                        proxy_url: "socks5://127.0.0.1:2080".to_string(),
                        target_host: "example.com".to_string(),
                        target_port: 80,
                        target_path: "/".to_string(),
                        attempts: 5,
                        successes: 5,
                        failures: 0,
                        median_connect_latency_ms: Some(25),
                        p95_connect_latency_ms: Some(35),
                        median_first_byte_latency_ms: Some(40),
                        p95_first_byte_latency_ms: Some(55),
                        median_open_to_first_byte_gap_ms: Some(15),
                        p95_open_to_first_byte_gap_ms: Some(20),
                        average_throughput_kbps: Some(4000.0),
                        helix_queue_pressure: None,
                        helix_continuity: None,
                        bytes_read_total: 1024,
                        bytes_written_total: 512,
                        samples: Vec::new(),
                    }),
                    error: None,
                    relative_connect_latency_ratio: None,
                    relative_first_byte_latency_ratio: None,
                    relative_open_to_first_byte_gap_ratio: None,
                    relative_throughput_ratio: None,
                },
            ],
        );

        assert_eq!(report.baseline_core.as_deref(), Some("sing-box"));
        assert_eq!(
            report.entries[0].relative_connect_latency_ratio,
            Some(35.0 / 25.0)
        );
        assert_eq!(
            report.entries[0].relative_throughput_ratio,
            Some(5000.0 / 4000.0)
        );
    }

    #[test]
    fn exposes_default_comparison_core_order() {
        assert_eq!(
            default_comparison_cores(),
            vec![EngineCore::Helix, EngineCore::SingBox, EngineCore::Xray,]
        );
    }

    #[test]
    fn finalizes_matrix_report_with_core_summaries() {
        let report = finalize_matrix_report(
            "profile-1".to_string(),
            vec![
                TransportBenchmarkMatrixTargetReport {
                    label: "edge-a".to_string(),
                    host: "example.com".to_string(),
                    port: 80,
                    path: "/".to_string(),
                    comparison: finalize_comparison_report(
                        "profile-1".to_string(),
                        vec![
                            TransportBenchmarkComparisonEntry {
                                requested_core: "helix".to_string(),
                                effective_core: Some("helix".to_string()),
                                benchmark: Some(TransportBenchmarkReport {
                                    schema_version: "1.0".to_string(),
                                    run_id: "helix-a".to_string(),
                                    generated_at: "2026-04-01T00:00:00Z".to_string(),
                                    active_core: "helix".to_string(),
                                    proxy_url: "socks5://127.0.0.1:38990".to_string(),
                                    target_host: "example.com".to_string(),
                                    target_port: 80,
                                    target_path: "/".to_string(),
                                    attempts: 3,
                                    successes: 3,
                                    failures: 0,
                                    median_connect_latency_ms: Some(18),
                                    p95_connect_latency_ms: Some(25),
                                    median_first_byte_latency_ms: Some(41),
                                    p95_first_byte_latency_ms: Some(60),
                                    median_open_to_first_byte_gap_ms: Some(23),
                                    p95_open_to_first_byte_gap_ms: Some(35),
                                    average_throughput_kbps: Some(6200.0),
                                    helix_queue_pressure: None,
                                    helix_continuity: None,
                                    bytes_read_total: 4096,
                                    bytes_written_total: 512,
                                    samples: Vec::new(),
                                }),
                                error: None,
                                relative_connect_latency_ratio: None,
                                relative_first_byte_latency_ratio: None,
                                relative_open_to_first_byte_gap_ratio: None,
                                relative_throughput_ratio: None,
                            },
                            TransportBenchmarkComparisonEntry {
                                requested_core: "sing-box".to_string(),
                                effective_core: Some("sing-box".to_string()),
                                benchmark: Some(TransportBenchmarkReport {
                                    schema_version: "1.0".to_string(),
                                    run_id: "sing-a".to_string(),
                                    generated_at: "2026-04-01T00:00:00Z".to_string(),
                                    active_core: "sing-box".to_string(),
                                    proxy_url: "socks5://127.0.0.1:2080".to_string(),
                                    target_host: "example.com".to_string(),
                                    target_port: 80,
                                    target_path: "/".to_string(),
                                    attempts: 3,
                                    successes: 3,
                                    failures: 0,
                                    median_connect_latency_ms: Some(12),
                                    p95_connect_latency_ms: Some(20),
                                    median_first_byte_latency_ms: Some(30),
                                    p95_first_byte_latency_ms: Some(45),
                                    median_open_to_first_byte_gap_ms: Some(18),
                                    p95_open_to_first_byte_gap_ms: Some(25),
                                    average_throughput_kbps: Some(5800.0),
                                    helix_queue_pressure: None,
                                    helix_continuity: None,
                                    bytes_read_total: 4096,
                                    bytes_written_total: 512,
                                    samples: Vec::new(),
                                }),
                                error: None,
                                relative_connect_latency_ratio: None,
                                relative_first_byte_latency_ratio: None,
                                relative_open_to_first_byte_gap_ratio: None,
                                relative_throughput_ratio: None,
                            },
                        ],
                    ),
                },
                TransportBenchmarkMatrixTargetReport {
                    label: "edge-b".to_string(),
                    host: "example.org".to_string(),
                    port: 443,
                    path: "/bench".to_string(),
                    comparison: finalize_comparison_report(
                        "profile-1".to_string(),
                        vec![
                            TransportBenchmarkComparisonEntry {
                                requested_core: "helix".to_string(),
                                effective_core: Some("helix".to_string()),
                                benchmark: Some(TransportBenchmarkReport {
                                    schema_version: "1.0".to_string(),
                                    run_id: "helix-b".to_string(),
                                    generated_at: "2026-04-01T00:00:00Z".to_string(),
                                    active_core: "helix".to_string(),
                                    proxy_url: "socks5://127.0.0.1:38990".to_string(),
                                    target_host: "example.org".to_string(),
                                    target_port: 443,
                                    target_path: "/bench".to_string(),
                                    attempts: 3,
                                    successes: 3,
                                    failures: 0,
                                    median_connect_latency_ms: Some(20),
                                    p95_connect_latency_ms: Some(28),
                                    median_first_byte_latency_ms: Some(50),
                                    p95_first_byte_latency_ms: Some(64),
                                    median_open_to_first_byte_gap_ms: Some(30),
                                    p95_open_to_first_byte_gap_ms: Some(36),
                                    average_throughput_kbps: Some(6100.0),
                                    helix_queue_pressure: None,
                                    helix_continuity: None,
                                    bytes_read_total: 4096,
                                    bytes_written_total: 512,
                                    samples: Vec::new(),
                                }),
                                error: None,
                                relative_connect_latency_ratio: None,
                                relative_first_byte_latency_ratio: None,
                                relative_open_to_first_byte_gap_ratio: None,
                                relative_throughput_ratio: None,
                            },
                            TransportBenchmarkComparisonEntry {
                                requested_core: "sing-box".to_string(),
                                effective_core: Some("sing-box".to_string()),
                                benchmark: Some(TransportBenchmarkReport {
                                    schema_version: "1.0".to_string(),
                                    run_id: "sing-b".to_string(),
                                    generated_at: "2026-04-01T00:00:00Z".to_string(),
                                    active_core: "sing-box".to_string(),
                                    proxy_url: "socks5://127.0.0.1:2080".to_string(),
                                    target_host: "example.org".to_string(),
                                    target_port: 443,
                                    target_path: "/bench".to_string(),
                                    attempts: 3,
                                    successes: 3,
                                    failures: 0,
                                    median_connect_latency_ms: Some(15),
                                    p95_connect_latency_ms: Some(24),
                                    median_first_byte_latency_ms: Some(35),
                                    p95_first_byte_latency_ms: Some(48),
                                    median_open_to_first_byte_gap_ms: Some(20),
                                    p95_open_to_first_byte_gap_ms: Some(24),
                                    average_throughput_kbps: Some(6000.0),
                                    helix_queue_pressure: None,
                                    helix_continuity: None,
                                    bytes_read_total: 4096,
                                    bytes_written_total: 512,
                                    samples: Vec::new(),
                                }),
                                error: None,
                                relative_connect_latency_ratio: None,
                                relative_first_byte_latency_ratio: None,
                                relative_open_to_first_byte_gap_ratio: None,
                                relative_throughput_ratio: None,
                            },
                        ],
                    ),
                },
            ],
        );

        assert_eq!(report.baseline_core.as_deref(), Some("sing-box"));
        assert_eq!(report.targets.len(), 2);
        let helix_summary = report
            .core_summaries
            .iter()
            .find(|summary| summary.core == "helix")
            .expect("helix summary");
        assert_eq!(helix_summary.completed_targets, 2);
        assert_eq!(helix_summary.failed_targets, 0);
        assert_eq!(helix_summary.median_connect_latency_ms, Some(18));
    }

    #[tokio::test]
    async fn benchmarks_helix_socks_proxy_path() {
        let upstream_listener = TcpListener::bind("127.0.0.1:0")
            .await
            .expect("bind http upstream");
        let upstream_addr = upstream_listener.local_addr().expect("upstream addr");
        tokio::spawn(async move {
            loop {
                let Ok((mut stream, _)) = upstream_listener.accept().await else {
                    break;
                };
                tokio::spawn(async move {
                    let mut request = [0_u8; 4096];
                    let _ = stream.read(&mut request).await;
                    let body = b"cybervpn benchmark payload";
                    let response = format!(
                        "HTTP/1.1 200 OK\r\nContent-Length: {}\r\nConnection: close\r\n\r\n",
                        body.len()
                    );
                    let _ = stream.write_all(response.as_bytes()).await;
                    let _ = stream.write_all(body).await;
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

        let client = spawn_client(ClientConfig {
            manifest_id: "manifest-1".to_string(),
            transport_profile_id: "ptp-lab-edge-v2".to_string(),
            profile_family: "edge-hybrid".to_string(),
            profile_version: 2,
            policy_version: 4,
            session_mode: "hybrid".to_string(),
            token: "shared-session-token".to_string(),
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

        let deadline = tokio::time::Instant::now() + Duration::from_secs(3);
        while !client.snapshot().await.ready {
            assert!(tokio::time::Instant::now() < deadline);
            tokio::time::sleep(Duration::from_millis(50)).await;
        }

        let proxy_listener = TcpListener::bind("127.0.0.1:0")
            .await
            .expect("bind proxy listener");
        let proxy_addr = proxy_listener.local_addr().expect("proxy addr");
        tokio::spawn(run_proxy_accept_loop(proxy_listener, client.clone()));

        let sample = benchmark_proxy_endpoint(
            &format!("socks5://{}", proxy_addr),
            "127.0.0.1",
            upstream_addr.port(),
            "/",
            1,
            4 * 1024,
            Duration::from_secs(2),
        )
        .await;

        assert!(sample.success);
        assert!(sample.connect_latency_ms.is_some());
        assert!(sample.first_byte_latency_ms.is_some());
        assert!(sample.bytes_read > 0);

        client.shutdown().await;
        server.shutdown().await;
    }

    #[tokio::test]
    async fn waits_for_first_byte_ready_on_helix_proxy_path() {
        let upstream_listener = TcpListener::bind("127.0.0.1:0")
            .await
            .expect("bind probe upstream");
        let upstream_addr = upstream_listener.local_addr().expect("upstream addr");
        tokio::spawn(async move {
            loop {
                let Ok((mut stream, _)) = upstream_listener.accept().await else {
                    break;
                };
                tokio::spawn(async move {
                    let mut request = [0_u8; 4096];
                    let _ = stream.read(&mut request).await;
                    let body = b"probe";
                    let response = format!(
                        "HTTP/1.1 200 OK\r\nContent-Length: {}\r\nConnection: close\r\n\r\n",
                        body.len()
                    );
                    let _ = stream.write_all(response.as_bytes()).await;
                    let _ = stream.write_all(body).await;
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

        let client = spawn_client(ClientConfig {
            manifest_id: "manifest-1".to_string(),
            transport_profile_id: "ptp-lab-edge-v2".to_string(),
            profile_family: "edge-hybrid".to_string(),
            profile_version: 2,
            policy_version: 4,
            session_mode: "hybrid".to_string(),
            token: "shared-session-token".to_string(),
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

        let deadline = tokio::time::Instant::now() + Duration::from_secs(3);
        while !client.snapshot().await.ready {
            assert!(tokio::time::Instant::now() < deadline);
            tokio::time::sleep(Duration::from_millis(50)).await;
        }

        let proxy_listener = TcpListener::bind("127.0.0.1:0")
            .await
            .expect("bind proxy listener");
        let proxy_addr = proxy_listener.local_addr().expect("proxy addr");
        tokio::spawn(run_proxy_accept_loop(proxy_listener, client.clone()));

        let sample = wait_for_proxy_first_byte_ready(
            &format!("socks5://{}", proxy_addr),
            "127.0.0.1",
            upstream_addr.port(),
            "/",
            Duration::from_secs(2),
            Duration::from_millis(500),
        )
        .await
        .expect("first-byte probe");

        assert!(sample.success);
        assert!(sample.connect_latency_ms.is_some());
        assert!(sample.first_byte_latency_ms.is_some());
        assert!(sample.bytes_read > 0);

        client.shutdown().await;
        server.shutdown().await;
    }
}
