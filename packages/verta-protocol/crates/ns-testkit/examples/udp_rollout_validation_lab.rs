use ns_testkit::{prefer_verta_env_input_path, repo_root, verta_output_path};
use serde::{Deserialize, Serialize};
use std::env;
use std::fs;
use std::path::PathBuf;
use std::process::Command;
use std::time::Instant;

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
enum OutputFormat {
    Text,
    Json,
}

#[derive(Debug, Default)]
struct ValidationArgs {
    format: Option<OutputFormat>,
    summary_path: Option<PathBuf>,
}

#[derive(Debug, Clone, Copy)]
struct ValidationCommandSpec {
    label: &'static str,
    command: &'static [&'static str],
}

const UDP_ROLLOUT_VALIDATION_SUMMARY_VERSION: u8 = 20;

#[derive(Debug, Serialize)]
struct ValidationCommandResult {
    label: String,
    status: &'static str,
    exit_code: Option<i32>,
    duration_ms: u128,
    command: Vec<String>,
}

#[derive(Debug, Deserialize)]
struct PerfCaseSummary {
    label: String,
    candidate_ns: u128,
    allowed_ns: u128,
    passed: bool,
}

#[derive(Debug, Deserialize)]
struct UdpPerfGateSummary {
    all_passed: bool,
    results: Vec<PerfCaseSummary>,
}

#[derive(Debug, Deserialize)]
struct UdpFuzzSmokeSummary {
    all_passed: bool,
}

#[derive(Debug, Deserialize)]
struct UdpInteropLabSummary {
    #[serde(default)]
    summary_version: Option<u8>,
    #[serde(default)]
    udp_blocked_fallback_surface_passed: Option<bool>,
    #[serde(default)]
    datagram_only_unavailable_rejection_surface_passed: Option<bool>,
    #[serde(default)]
    policy_disabled_fallback_surface_passed: Option<bool>,
    #[serde(default)]
    queue_pressure_surface_passed: Option<bool>,
    #[serde(default)]
    transport_fallback_integrity_surface_passed: Option<bool>,
    #[serde(default)]
    required_no_silent_fallback_profile_count: Option<usize>,
    #[serde(default)]
    required_no_silent_fallback_passed_count: Option<usize>,
}

#[derive(Debug, Serialize)]
struct UdpRolloutValidationSummary {
    summary_version: u8,
    profile: &'static str,
    all_passed: bool,
    cli_surface_consistency_passed: bool,
    startup_contract_validation_passed: bool,
    negotiated_limit_validation_passed: bool,
    selected_datagram_lifecycle_passed: bool,
    mtu_ceiling_delivery_stable: bool,
    fallback_flow_guard_rejection_stable: bool,
    udp_blocked_fallback_surface_passed: bool,
    policy_disabled_fallback_round_trip_stable: bool,
    datagram_only_unavailable_rejection_stable: bool,
    repeated_queue_pressure_sticky: bool,
    queue_pressure_surface_passed: bool,
    reordering_no_silent_fallback_passed: bool,
    prolonged_impairment_no_silent_fallback: bool,
    prolonged_repeated_impairment_stable: bool,
    longer_impairment_recovery_stable: bool,
    shutdown_sequence_stable: bool,
    post_close_rejection_stable: bool,
    associated_stream_guard_recovery_stable: bool,
    oversized_payload_guard_recovery_stable: bool,
    reordered_after_close_rejection_stable: bool,
    clean_shutdown_stable: bool,
    policy_disabled_fallback_surface_passed: Option<bool>,
    interop_udp_blocked_fallback_surface_passed: Option<bool>,
    interop_queue_pressure_surface_passed: Option<bool>,
    interop_transport_fallback_integrity_surface_passed: Option<bool>,
    interop_required_no_silent_fallback_profile_count: Option<usize>,
    interop_required_no_silent_fallback_passed_count: Option<usize>,
    fuzz_smoke_all_passed: Option<bool>,
    perf_summary_all_passed: Option<bool>,
    queue_full_reject_threshold_passed: Option<bool>,
    queue_recovery_send_threshold_passed: Option<bool>,
    repeated_queue_recovery_send_threshold_passed: Option<bool>,
    flow_burst_reject_threshold_passed: Option<bool>,
    session_burst_reject_threshold_passed: Option<bool>,
    queue_saturation_surface_passed: Option<bool>,
    queue_saturation_worst_case: Option<String>,
    queue_saturation_worst_utilization_pct: Option<u128>,
    queue_guard_headroom_passed: Option<bool>,
    queue_guard_headroom_band: Option<&'static str>,
    queue_guard_headroom_missing_count: usize,
    queue_guard_rejection_path_passed: Option<bool>,
    queue_guard_recovery_path_passed: Option<bool>,
    queue_guard_burst_path_passed: Option<bool>,
    queue_guard_limiting_path: Option<&'static str>,
    sticky_selection_surface_passed: bool,
    degradation_surface_passed: bool,
    transport_fallback_integrity_surface_passed: bool,
    rollout_surface_passed: Option<bool>,
    surface_count_total: usize,
    surface_count_passed: usize,
    surface_count_failed: usize,
    failed_surface_keys: Vec<String>,
    command_count: usize,
    passed_command_count: usize,
    failed_command_count: usize,
    fuzz_smoke_summary_path: Option<String>,
    interop_summary_path: Option<String>,
    perf_summary_path: Option<String>,
    results: Vec<ValidationCommandResult>,
}

const VALIDATION_COMMANDS: &[ValidationCommandSpec] = &[
    ValidationCommandSpec {
        label: "clientd_cli_surfaces",
        command: &["cargo", "test", "-p", "ns-clientd", "--all-targets"],
    },
    ValidationCommandSpec {
        label: "nsctl_cli_surfaces",
        command: &["cargo", "test", "-p", "nsctl", "--all-targets"],
    },
    ValidationCommandSpec {
        label: "gatewayd_cli_surfaces",
        command: &["cargo", "test", "-p", "ns-gatewayd", "--all-targets"],
    },
    ValidationCommandSpec {
        label: "repeated_queue_pressure_sticky",
        command: &[
            "cargo",
            "test",
            "-p",
            "ns-carrier-h3",
            "repeated_queue_pressure_keeps_selected_datagram_transport_without_silent_fallback",
            "--lib",
            "--",
            "--nocapture",
        ],
    },
    ValidationCommandSpec {
        label: "reordering_no_silent_fallback",
        command: &[
            "cargo",
            "test",
            "-p",
            "ns-carrier-h3",
            "--test",
            "live_udp",
            "loopback_h3_datagrams_tolerate_bounded_reordering_without_fallback",
            "--",
            "--nocapture",
        ],
    },
    ValidationCommandSpec {
        label: "longer_impairment_recovery_stable",
        command: &[
            "cargo",
            "test",
            "-p",
            "ns-carrier-h3",
            "--test",
            "live_udp",
            "loopback_h3_datagrams_continue_after_repeated_bounded_loss",
            "--",
            "--nocapture",
        ],
    },
    ValidationCommandSpec {
        label: "mtu_ceiling_delivery_stable",
        command: &[
            "cargo",
            "test",
            "-p",
            "ns-carrier-h3",
            "--test",
            "live_udp",
            "loopback_h3_datagrams_accept_payload_at_effective_mtu_ceiling",
            "--",
            "--nocapture",
        ],
    },
    ValidationCommandSpec {
        label: "fallback_flow_guard_rejection_stable",
        command: &[
            "cargo",
            "test",
            "-p",
            "ns-carrier-h3",
            "--test",
            "live_udp",
            "loopback_udp_fallback_rejects_wrong_flow_id_with_protocol_violation_close",
            "--",
            "--nocapture",
        ],
    },
    ValidationCommandSpec {
        label: "udp_blocked_fallback_surface_passed",
        command: &[
            "cargo",
            "test",
            "-p",
            "ns-carrier-h3",
            "--test",
            "live_udp",
            "loopback_udp_stream_fallback_round_trips_when_carrier_support_is_unavailable",
            "--",
            "--nocapture",
        ],
    },
    ValidationCommandSpec {
        label: "policy_disabled_fallback_round_trip_stable",
        command: &[
            "cargo",
            "test",
            "-p",
            "ns-carrier-h3",
            "--test",
            "live_udp",
            "loopback_udp_stream_fallback_round_trips_when_rollout_disables_datagrams",
            "--",
            "--nocapture",
        ],
    },
    ValidationCommandSpec {
        label: "datagram_only_unavailable_rejection_stable",
        command: &[
            "cargo",
            "test",
            "-p",
            "ns-carrier-h3",
            "--test",
            "live_udp",
            "loopback_udp_flow_rejects_datagram_only_requests_when_datagrams_are_unavailable",
            "--",
            "--nocapture",
        ],
    },
    ValidationCommandSpec {
        label: "clean_shutdown_stable",
        command: &[
            "cargo",
            "test",
            "-p",
            "ns-carrier-h3",
            "--test",
            "live_udp",
            "loopback_h3_datagrams_round_trip_after_udp_flow_open",
            "--",
            "--nocapture",
        ],
    },
    ValidationCommandSpec {
        label: "prolonged_impairment_no_silent_fallback",
        command: &[
            "cargo",
            "test",
            "-p",
            "ns-carrier-h3",
            "--test",
            "live_udp",
            "loopback_h3_datagrams_tolerate_delayed_delivery_and_short_black_hole_without_fallback",
            "--",
            "--nocapture",
        ],
    },
    ValidationCommandSpec {
        label: "post_close_rejection_stable",
        command: &[
            "cargo",
            "test",
            "-p",
            "ns-carrier-h3",
            "--test",
            "live_udp",
            "loopback_h3_datagrams_reject_unknown_flows_after_close",
            "--",
            "--nocapture",
        ],
    },
    ValidationCommandSpec {
        label: "associated_stream_guard_recovery_stable",
        command: &[
            "cargo",
            "test",
            "-p",
            "ns-carrier-h3",
            "--test",
            "live_udp",
            "loopback_h3_datagrams_reject_wrong_associated_stream_and_recover",
            "--",
            "--nocapture",
        ],
    },
    ValidationCommandSpec {
        label: "oversized_payload_guard_recovery_stable",
        command: &[
            "cargo",
            "test",
            "-p",
            "ns-carrier-h3",
            "--test",
            "live_udp",
            "loopback_h3_datagrams_reject_oversized_payloads_and_keep_flow_state",
            "--",
            "--nocapture",
        ],
    },
    ValidationCommandSpec {
        label: "reordered_after_close_rejection_stable",
        command: &[
            "cargo",
            "test",
            "-p",
            "ns-carrier-h3",
            "--test",
            "live_udp",
            "loopback_h3_datagrams_reject_reordered_after_close_without_fallback",
            "--",
            "--nocapture",
        ],
    },
    ValidationCommandSpec {
        label: "selected_datagram_lifecycle_stable",
        command: &[
            "cargo",
            "test",
            "-p",
            "ns-carrier-h3",
            "--test",
            "live_udp",
            "loopback_h3_datagrams_round_trip_after_udp_flow_open",
            "--",
            "--nocapture",
        ],
    },
];

fn main() -> Result<(), Box<dyn std::error::Error>> {
    let args = parse_args(env::args().skip(1))?;
    let repo_root = repo_root();
    let mut results = Vec::with_capacity(VALIDATION_COMMANDS.len());

    for spec in VALIDATION_COMMANDS {
        results.push(run_command(&repo_root, *spec)?);
    }

    let summary = build_validation_summary(
        results,
        read_json_summary::<UdpFuzzSmokeSummary>(
            "VERTA_UDP_FUZZ_SMOKE_SUMMARY_PATH",
            "VERTA_UDP_FUZZ_SMOKE_SUMMARY_PATH",
            "udp-fuzz-smoke-summary.json",
        )?,
        read_json_summary::<UdpInteropLabSummary>(
            "VERTA_UDP_INTEROP_SUMMARY_PATH",
            "VERTA_UDP_INTEROP_SUMMARY_PATH",
            "udp-interop-lab-summary.json",
        )?,
        read_json_summary::<UdpPerfGateSummary>(
            "VERTA_UDP_PERF_SUMMARY_PATH",
            "VERTA_UDP_PERF_SUMMARY_PATH",
            "udp-perf-gate-summary.json",
        )?,
        env_summary_path(
            "VERTA_UDP_FUZZ_SMOKE_SUMMARY_PATH",
            "VERTA_UDP_FUZZ_SMOKE_SUMMARY_PATH",
            "udp-fuzz-smoke-summary.json",
        ),
        env_summary_path(
            "VERTA_UDP_INTEROP_SUMMARY_PATH",
            "VERTA_UDP_INTEROP_SUMMARY_PATH",
            "udp-interop-lab-summary.json",
        ),
        env_summary_path(
            "VERTA_UDP_PERF_SUMMARY_PATH",
            "VERTA_UDP_PERF_SUMMARY_PATH",
            "udp-perf-gate-summary.json",
        ),
    );

    let summary_path = args.summary_path.unwrap_or_else(default_summary_path);
    if let Some(parent) = summary_path.parent() {
        fs::create_dir_all(parent)?;
    }
    fs::write(&summary_path, serde_json::to_vec_pretty(&summary)?)?;

    match args.format.unwrap_or(OutputFormat::Text) {
        OutputFormat::Text => {
            println!("Verta UDP rollout validation summary:");
            for result in &summary.results {
                println!(
                    "- {label}: {status} in {duration_ms}ms",
                    label = result.label,
                    status = result.status,
                    duration_ms = result.duration_ms,
                );
            }
            println!(
                "- sticky_selection_surface_passed: {}",
                summary.sticky_selection_surface_passed
            );
            println!(
                "- selected_datagram_lifecycle_passed: {}",
                summary.selected_datagram_lifecycle_passed
            );
            println!(
                "- mtu_ceiling_delivery_stable: {}",
                summary.mtu_ceiling_delivery_stable
            );
            println!(
                "- fallback_flow_guard_rejection_stable: {}",
                summary.fallback_flow_guard_rejection_stable
            );
            println!(
                "- udp_blocked_fallback_surface_passed: {}",
                summary.udp_blocked_fallback_surface_passed
            );
            println!(
                "- policy_disabled_fallback_round_trip_stable: {}",
                summary.policy_disabled_fallback_round_trip_stable
            );
            println!(
                "- queue_pressure_surface_passed: {}",
                summary.queue_pressure_surface_passed
            );
            println!(
                "- reordering_no_silent_fallback_passed: {}",
                summary.reordering_no_silent_fallback_passed
            );
            println!(
                "- longer_impairment_recovery_stable: {}",
                summary.longer_impairment_recovery_stable
            );
            println!(
                "- shutdown_sequence_stable: {}",
                summary.shutdown_sequence_stable
            );
            println!(
                "- associated_stream_guard_recovery_stable: {}",
                summary.associated_stream_guard_recovery_stable
            );
            println!(
                "- oversized_payload_guard_recovery_stable: {}",
                summary.oversized_payload_guard_recovery_stable
            );
            println!(
                "- reordered_after_close_rejection_stable: {}",
                summary.reordered_after_close_rejection_stable
            );
            println!(
                "- datagram_only_unavailable_rejection_stable: {}",
                summary.datagram_only_unavailable_rejection_stable
            );
            println!(
                "- prolonged_repeated_impairment_stable: {}",
                summary.prolonged_repeated_impairment_stable
            );
            println!(
                "- degradation_surface_passed: {}",
                summary.degradation_surface_passed
            );
            println!(
                "- transport_fallback_integrity_surface_passed: {}",
                summary.transport_fallback_integrity_surface_passed
            );
            if let Some(policy_disabled_fallback_surface_passed) =
                summary.policy_disabled_fallback_surface_passed
            {
                println!(
                    "- policy_disabled_fallback_surface_passed: {policy_disabled_fallback_surface_passed}"
                );
            }
            if let Some(interop_udp_blocked_fallback_surface_passed) =
                summary.interop_udp_blocked_fallback_surface_passed
            {
                println!(
                    "- interop_udp_blocked_fallback_surface_passed: {interop_udp_blocked_fallback_surface_passed}"
                );
            }
            if let Some(interop_queue_pressure_surface_passed) =
                summary.interop_queue_pressure_surface_passed
            {
                println!(
                    "- interop_queue_pressure_surface_passed: {interop_queue_pressure_surface_passed}"
                );
            }
            if let Some(interop_transport_fallback_integrity_surface_passed) =
                summary.interop_transport_fallback_integrity_surface_passed
            {
                println!(
                    "- interop_transport_fallback_integrity_surface_passed: {interop_transport_fallback_integrity_surface_passed}"
                );
            }
            println!(
                "- command_counts: total={} passed={} failed={}",
                summary.command_count, summary.passed_command_count, summary.failed_command_count
            );
            println!(
                "- surface_counts: total={} passed={} failed={}",
                summary.surface_count_total,
                summary.surface_count_passed,
                summary.surface_count_failed
            );
            if summary.failed_surface_keys.is_empty() {
                println!("- failed_surface_keys: none");
            } else {
                println!(
                    "- failed_surface_keys: {}",
                    summary.failed_surface_keys.join(", ")
                );
            }
            if let Some(rollout_surface_passed) = summary.rollout_surface_passed {
                println!("- rollout_surface_passed: {rollout_surface_passed}");
            }
            if let Some(queue_saturation_worst_case) = &summary.queue_saturation_worst_case {
                println!(
                    "- queue_saturation_worst_case: {} ({}%)",
                    queue_saturation_worst_case,
                    summary.queue_saturation_worst_utilization_pct.unwrap_or(0)
                );
            }
            if let Some(queue_guard_headroom_band) = summary.queue_guard_headroom_band {
                println!(
                    "- queue_guard_headroom_band: {} (passed={})",
                    queue_guard_headroom_band,
                    summary.queue_guard_headroom_passed.unwrap_or(false)
                );
            }
            println!(
                "- queue_guard_headroom_missing_count: {}",
                summary.queue_guard_headroom_missing_count
            );
            if let Some(queue_guard_limiting_path) = summary.queue_guard_limiting_path {
                println!("- queue_guard_limiting_path: {queue_guard_limiting_path}");
            }
            println!("machine_readable_summary={}", summary_path.display());
        }
        OutputFormat::Json => {
            println!("{}", serde_json::to_string_pretty(&summary)?);
        }
    }

    if summary.failed_command_count > 0 {
        return Err("one or more UDP rollout validation commands failed".into());
    }
    if summary.surface_count_failed > 0 {
        return Err("one or more UDP rollout validation surfaces failed".into());
    }

    Ok(())
}

fn build_validation_summary(
    results: Vec<ValidationCommandResult>,
    fuzz_smoke_summary: Option<UdpFuzzSmokeSummary>,
    interop_summary: Option<UdpInteropLabSummary>,
    perf_summary: Option<UdpPerfGateSummary>,
    fuzz_smoke_summary_path: Option<String>,
    interop_summary_path: Option<String>,
    perf_summary_path: Option<String>,
) -> UdpRolloutValidationSummary {
    let interop_summary_version = interop_summary
        .as_ref()
        .and_then(|summary| summary.summary_version);
    let queue_full_reject_threshold_passed =
        perf_case_passed(perf_summary.as_ref(), "H3DatagramSocket.queue_full_reject");
    let queue_recovery_send_threshold_passed = perf_case_passed(
        perf_summary.as_ref(),
        "H3DatagramSocket.queue_recovery_send",
    );
    let repeated_queue_recovery_send_threshold_passed = perf_case_passed(
        perf_summary.as_ref(),
        "H3DatagramSocket.repeated_queue_recovery_send",
    );
    let flow_burst_reject_threshold_passed =
        perf_case_passed(perf_summary.as_ref(), "H3DatagramSocket.flow_burst_reject");
    let session_burst_reject_threshold_passed = perf_case_passed(
        perf_summary.as_ref(),
        "H3DatagramSocket.session_burst_reject",
    );
    let perf_summary_all_passed = perf_summary.as_ref().map(|summary| summary.all_passed);
    let fuzz_smoke_all_passed = fuzz_smoke_summary
        .as_ref()
        .map(|summary| summary.all_passed);
    let queue_saturation_labels = [
        "H3DatagramSocket.queue_full_reject",
        "H3DatagramSocket.queue_recovery_send",
        "H3DatagramSocket.repeated_queue_recovery_send",
        "H3DatagramSocket.flow_burst_reject",
        "H3DatagramSocket.session_burst_reject",
    ];
    let queue_saturation_worst_result =
        perf_case_with_highest_utilization(perf_summary.as_ref(), &queue_saturation_labels);
    let queue_saturation_worst_case =
        queue_saturation_worst_result.map(|result| result.label.clone());
    let queue_saturation_worst_utilization_pct = queue_saturation_worst_result.map(utilization_pct);
    let queue_guard_rejection_path_passed = match (
        queue_full_reject_threshold_passed,
        flow_burst_reject_threshold_passed,
        session_burst_reject_threshold_passed,
    ) {
        (Some(queue_full), Some(flow_burst), Some(session_burst)) => {
            Some(queue_full && flow_burst && session_burst)
        }
        _ => None,
    };
    let queue_guard_recovery_path_passed = match (
        queue_recovery_send_threshold_passed,
        repeated_queue_recovery_send_threshold_passed,
    ) {
        (Some(queue_recovery), Some(repeated_queue_recovery)) => {
            Some(queue_recovery && repeated_queue_recovery)
        }
        _ => None,
    };
    let queue_guard_burst_path_passed = match (
        flow_burst_reject_threshold_passed,
        session_burst_reject_threshold_passed,
    ) {
        (Some(flow_burst), Some(session_burst)) => Some(flow_burst && session_burst),
        _ => None,
    };
    let queue_guard_limiting_path = limiting_path(
        queue_saturation_worst_case.as_deref(),
        queue_guard_rejection_path_passed,
        queue_guard_recovery_path_passed,
        queue_guard_burst_path_passed,
    );
    let queue_saturation_surface_passed = match (
        queue_full_reject_threshold_passed,
        queue_recovery_send_threshold_passed,
        repeated_queue_recovery_send_threshold_passed,
        flow_burst_reject_threshold_passed,
        session_burst_reject_threshold_passed,
    ) {
        (
            Some(queue_full),
            Some(queue_recovery),
            Some(repeated_queue_recovery),
            Some(flow_burst_reject),
            Some(session_burst_reject),
        ) => Some(
            queue_full
                && queue_recovery
                && repeated_queue_recovery
                && flow_burst_reject
                && session_burst_reject,
        ),
        _ => None,
    };
    let queue_guard_headroom_band = match (
        queue_saturation_surface_passed,
        queue_saturation_worst_utilization_pct,
    ) {
        (Some(true), Some(utilization)) if utilization < 85 => Some("healthy"),
        (Some(true), Some(utilization)) if utilization < 100 => Some("tight"),
        (Some(_), Some(_)) => Some("exhausted"),
        _ => None,
    };
    let queue_guard_headroom_passed = queue_guard_headroom_band.map(|band| band != "exhausted");
    let queue_guard_headroom_missing_count = usize::from(queue_guard_headroom_passed.is_none());
    let cli_surface_consistency_passed = all_passed(
        &results,
        &[
            "clientd_cli_surfaces",
            "nsctl_cli_surfaces",
            "gatewayd_cli_surfaces",
        ],
    );
    let startup_contract_validation_passed = all_passed(
        &results,
        &[
            "clientd_cli_surfaces",
            "nsctl_cli_surfaces",
            "gatewayd_cli_surfaces",
        ],
    );
    let mtu_ceiling_delivery_stable = all_passed(&results, &["mtu_ceiling_delivery_stable"]);
    let fallback_flow_guard_rejection_stable =
        all_passed(&results, &["fallback_flow_guard_rejection_stable"]);
    let udp_blocked_fallback_surface_passed =
        all_passed(&results, &["udp_blocked_fallback_surface_passed"]);
    let policy_disabled_fallback_round_trip_stable =
        all_passed(&results, &["policy_disabled_fallback_round_trip_stable"]);
    let datagram_only_unavailable_rejection_stable =
        all_passed(&results, &["datagram_only_unavailable_rejection_stable"]);
    let negotiated_limit_validation_passed = all_passed(
        &results,
        &[
            "clientd_cli_surfaces",
            "nsctl_cli_surfaces",
            "mtu_ceiling_delivery_stable",
        ],
    );
    let selected_datagram_lifecycle_passed =
        all_passed(&results, &["selected_datagram_lifecycle_stable"]);
    let repeated_queue_pressure_sticky = all_passed(&results, &["repeated_queue_pressure_sticky"]);
    let reordering_no_silent_fallback_passed =
        all_passed(&results, &["reordering_no_silent_fallback"]);
    let prolonged_impairment_no_silent_fallback =
        all_passed(&results, &["prolonged_impairment_no_silent_fallback"]);
    let prolonged_repeated_impairment_stable = all_passed(
        &results,
        &[
            "prolonged_impairment_no_silent_fallback",
            "longer_impairment_recovery_stable",
        ],
    );
    let longer_impairment_recovery_stable =
        all_passed(&results, &["longer_impairment_recovery_stable"]);
    let post_close_rejection_stable = all_passed(&results, &["post_close_rejection_stable"]);
    let associated_stream_guard_recovery_stable =
        all_passed(&results, &["associated_stream_guard_recovery_stable"]);
    let oversized_payload_guard_recovery_stable =
        all_passed(&results, &["oversized_payload_guard_recovery_stable"]);
    let reordered_after_close_rejection_stable =
        all_passed(&results, &["reordered_after_close_rejection_stable"]);
    let clean_shutdown_stable = all_passed(&results, &["clean_shutdown_stable"]);
    let interop_udp_blocked_fallback_surface_passed = interop_summary
        .as_ref()
        .filter(|_| interop_summary_version == Some(5))
        .and_then(|summary| summary.udp_blocked_fallback_surface_passed);
    let policy_disabled_fallback_surface_passed = interop_summary
        .as_ref()
        .filter(|_| interop_summary_version == Some(5))
        .and_then(|summary| summary.policy_disabled_fallback_surface_passed);
    let interop_datagram_only_unavailable_rejection_surface_passed = interop_summary
        .as_ref()
        .filter(|_| interop_summary_version == Some(5))
        .and_then(|summary| summary.datagram_only_unavailable_rejection_surface_passed);
    let interop_queue_pressure_surface_passed = interop_summary
        .as_ref()
        .filter(|_| interop_summary_version == Some(5))
        .and_then(|summary| summary.queue_pressure_surface_passed);
    let interop_transport_fallback_integrity_surface_passed = interop_summary
        .as_ref()
        .filter(|_| interop_summary_version == Some(5))
        .and_then(|summary| {
            summary
                .transport_fallback_integrity_surface_passed
                .map(|passed| {
                    passed
                        && summary.udp_blocked_fallback_surface_passed == Some(true)
                        && matches!(
                            (
                                summary.required_no_silent_fallback_profile_count,
                                summary.required_no_silent_fallback_passed_count,
                            ),
                            (Some(total), Some(passed_count))
                                if total > 0 && total == passed_count
                        )
                })
        });
    let interop_required_no_silent_fallback_profile_count = interop_summary
        .as_ref()
        .filter(|_| interop_summary_version == Some(5))
        .and_then(|summary| summary.required_no_silent_fallback_profile_count);
    let interop_required_no_silent_fallback_passed_count = interop_summary
        .as_ref()
        .filter(|_| interop_summary_version == Some(5))
        .and_then(|summary| summary.required_no_silent_fallback_passed_count);
    let shutdown_sequence_stable = all_passed(
        &results,
        &[
            "clean_shutdown_stable",
            "post_close_rejection_stable",
            "associated_stream_guard_recovery_stable",
            "reordered_after_close_rejection_stable",
        ],
    );
    let sticky_selection_surface_passed = all_passed(
        &results,
        &[
            "selected_datagram_lifecycle_stable",
            "repeated_queue_pressure_sticky",
            "reordering_no_silent_fallback",
            "prolonged_impairment_no_silent_fallback",
            "post_close_rejection_stable",
            "associated_stream_guard_recovery_stable",
            "oversized_payload_guard_recovery_stable",
            "reordered_after_close_rejection_stable",
            "clean_shutdown_stable",
        ],
    );
    let queue_pressure_surface_passed =
        repeated_queue_pressure_sticky && interop_queue_pressure_surface_passed.unwrap_or(true);
    let degradation_surface_passed = selected_datagram_lifecycle_passed
        && queue_pressure_surface_passed
        && reordering_no_silent_fallback_passed
        && prolonged_impairment_no_silent_fallback
        && prolonged_repeated_impairment_stable
        && longer_impairment_recovery_stable
        && shutdown_sequence_stable
        && post_close_rejection_stable
        && associated_stream_guard_recovery_stable
        && oversized_payload_guard_recovery_stable
        && reordered_after_close_rejection_stable
        && clean_shutdown_stable;
    let transport_fallback_integrity_surface_passed = degradation_surface_passed
        && fallback_flow_guard_rejection_stable
        && udp_blocked_fallback_surface_passed
        && policy_disabled_fallback_round_trip_stable
        && datagram_only_unavailable_rejection_stable
        && interop_udp_blocked_fallback_surface_passed == Some(true)
        && policy_disabled_fallback_surface_passed == Some(true)
        && interop_datagram_only_unavailable_rejection_surface_passed == Some(true)
        && interop_transport_fallback_integrity_surface_passed.unwrap_or(true);
    let rollout_surface_passed = queue_saturation_surface_passed.map(|queue_surface| {
        queue_surface
            && queue_pressure_surface_passed
            && transport_fallback_integrity_surface_passed
    });
    let passed_command_count = results
        .iter()
        .filter(|result| result.status == "passed")
        .count();
    let failed_command_count = results.len().saturating_sub(passed_command_count);
    let mut failed_surface_keys = Vec::new();
    let mut surface_statuses = vec![
        (
            "cli_surface_consistency_passed",
            cli_surface_consistency_passed,
        ),
        (
            "startup_contract_validation_passed",
            startup_contract_validation_passed,
        ),
        (
            "negotiated_limit_validation_passed",
            negotiated_limit_validation_passed,
        ),
        (
            "selected_datagram_lifecycle_passed",
            selected_datagram_lifecycle_passed,
        ),
        ("mtu_ceiling_delivery_stable", mtu_ceiling_delivery_stable),
        (
            "fallback_flow_guard_rejection_stable",
            fallback_flow_guard_rejection_stable,
        ),
        (
            "udp_blocked_fallback_surface_passed",
            udp_blocked_fallback_surface_passed,
        ),
        (
            "policy_disabled_fallback_round_trip_stable",
            policy_disabled_fallback_round_trip_stable,
        ),
        (
            "datagram_only_unavailable_rejection_stable",
            datagram_only_unavailable_rejection_stable,
        ),
        (
            "repeated_queue_pressure_sticky",
            repeated_queue_pressure_sticky,
        ),
        (
            "queue_pressure_surface_passed",
            queue_pressure_surface_passed,
        ),
        (
            "reordering_no_silent_fallback_passed",
            reordering_no_silent_fallback_passed,
        ),
        (
            "prolonged_impairment_no_silent_fallback",
            prolonged_impairment_no_silent_fallback,
        ),
        (
            "prolonged_repeated_impairment_stable",
            prolonged_repeated_impairment_stable,
        ),
        (
            "longer_impairment_recovery_stable",
            longer_impairment_recovery_stable,
        ),
        ("shutdown_sequence_stable", shutdown_sequence_stable),
        ("post_close_rejection_stable", post_close_rejection_stable),
        (
            "reordered_after_close_rejection_stable",
            reordered_after_close_rejection_stable,
        ),
        (
            "associated_stream_guard_recovery_stable",
            associated_stream_guard_recovery_stable,
        ),
        (
            "oversized_payload_guard_recovery_stable",
            oversized_payload_guard_recovery_stable,
        ),
        ("clean_shutdown_stable", clean_shutdown_stable),
        (
            "sticky_selection_surface_passed",
            sticky_selection_surface_passed,
        ),
        ("degradation_surface_passed", degradation_surface_passed),
        (
            "transport_fallback_integrity_surface_passed",
            transport_fallback_integrity_surface_passed,
        ),
    ];
    if let Some(policy_disabled_fallback_surface_passed) = policy_disabled_fallback_surface_passed {
        surface_statuses.push((
            "policy_disabled_fallback_surface_passed",
            policy_disabled_fallback_surface_passed,
        ));
    }
    if let Some(queue_surface) = queue_saturation_surface_passed {
        surface_statuses.push(("queue_saturation_surface_passed", queue_surface));
    }
    if let Some(rollout_surface) = rollout_surface_passed {
        surface_statuses.push(("rollout_surface_passed", rollout_surface));
    }
    for (key, passed) in &surface_statuses {
        if !passed {
            failed_surface_keys.push((*key).to_owned());
        }
    }
    let surface_count_total = surface_statuses.len();
    let surface_count_failed = failed_surface_keys.len();
    let surface_count_passed = surface_count_total.saturating_sub(surface_count_failed);

    UdpRolloutValidationSummary {
        summary_version: UDP_ROLLOUT_VALIDATION_SUMMARY_VERSION,
        profile: "compatible_host_rollout_validation",
        all_passed: results.iter().all(|result| result.status == "passed"),
        cli_surface_consistency_passed,
        startup_contract_validation_passed,
        negotiated_limit_validation_passed,
        selected_datagram_lifecycle_passed,
        mtu_ceiling_delivery_stable,
        fallback_flow_guard_rejection_stable,
        udp_blocked_fallback_surface_passed,
        policy_disabled_fallback_round_trip_stable,
        datagram_only_unavailable_rejection_stable,
        repeated_queue_pressure_sticky,
        queue_pressure_surface_passed,
        reordering_no_silent_fallback_passed,
        prolonged_impairment_no_silent_fallback,
        prolonged_repeated_impairment_stable,
        longer_impairment_recovery_stable,
        shutdown_sequence_stable,
        post_close_rejection_stable,
        associated_stream_guard_recovery_stable,
        oversized_payload_guard_recovery_stable,
        reordered_after_close_rejection_stable,
        clean_shutdown_stable,
        policy_disabled_fallback_surface_passed,
        interop_udp_blocked_fallback_surface_passed,
        interop_queue_pressure_surface_passed,
        interop_transport_fallback_integrity_surface_passed,
        interop_required_no_silent_fallback_profile_count,
        interop_required_no_silent_fallback_passed_count,
        fuzz_smoke_all_passed,
        perf_summary_all_passed,
        queue_full_reject_threshold_passed,
        queue_recovery_send_threshold_passed,
        repeated_queue_recovery_send_threshold_passed,
        flow_burst_reject_threshold_passed,
        session_burst_reject_threshold_passed,
        queue_saturation_surface_passed,
        queue_saturation_worst_case,
        queue_saturation_worst_utilization_pct,
        queue_guard_headroom_passed,
        queue_guard_headroom_band,
        queue_guard_headroom_missing_count,
        queue_guard_rejection_path_passed,
        queue_guard_recovery_path_passed,
        queue_guard_burst_path_passed,
        queue_guard_limiting_path,
        sticky_selection_surface_passed,
        degradation_surface_passed,
        transport_fallback_integrity_surface_passed,
        rollout_surface_passed,
        surface_count_total,
        surface_count_passed,
        surface_count_failed,
        failed_surface_keys,
        command_count: results.len(),
        passed_command_count,
        failed_command_count,
        fuzz_smoke_summary_path,
        interop_summary_path,
        perf_summary_path,
        results,
    }
}

fn parse_args(
    arguments: impl IntoIterator<Item = String>,
) -> Result<ValidationArgs, Box<dyn std::error::Error>> {
    let mut parsed = ValidationArgs::default();
    let mut iter = arguments.into_iter();
    while let Some(argument) = iter.next() {
        match argument.as_str() {
            "--format" => {
                let value = iter.next().ok_or("--format requires either text or json")?;
                parsed.format = Some(match value.as_str() {
                    "text" => OutputFormat::Text,
                    "json" => OutputFormat::Json,
                    other => return Err(format!("unsupported --format value {other}").into()),
                });
            }
            "--summary-path" => {
                let value = iter
                    .next()
                    .ok_or("--summary-path requires a filesystem path")?;
                parsed.summary_path = Some(PathBuf::from(value));
            }
            "--help" | "-h" => {
                print_usage();
                std::process::exit(0);
            }
            other => return Err(format!("unrecognized argument {other}").into()),
        }
    }
    Ok(parsed)
}

fn print_usage() {
    eprintln!(
        "Usage: cargo run -p ns-testkit --example udp_rollout_validation_lab -- [--format text|json] [--summary-path <path>]"
    );
}

fn run_command(
    repo_root: &std::path::Path,
    spec: ValidationCommandSpec,
) -> Result<ValidationCommandResult, Box<dyn std::error::Error>> {
    let started_at = Instant::now();
    let status = Command::new(spec.command[0])
        .args(&spec.command[1..])
        .current_dir(repo_root)
        .status()?;
    Ok(ValidationCommandResult {
        label: spec.label.to_owned(),
        status: if status.success() { "passed" } else { "failed" },
        exit_code: status.code(),
        duration_ms: started_at.elapsed().as_millis(),
        command: spec
            .command
            .iter()
            .map(|value| (*value).to_owned())
            .collect(),
    })
}

fn all_passed(results: &[ValidationCommandResult], labels: &[&str]) -> bool {
    labels.iter().all(|label| {
        results
            .iter()
            .find(|result| result.label == *label)
            .is_some_and(|result| result.status == "passed")
    })
}

fn limiting_path(
    worst_case: Option<&str>,
    rejection_passed: Option<bool>,
    recovery_passed: Option<bool>,
    burst_passed: Option<bool>,
) -> Option<&'static str> {
    let failed_families = [
        rejection_passed
            .is_some_and(|passed| !passed)
            .then_some("rejection"),
        recovery_passed
            .is_some_and(|passed| !passed)
            .then_some("recovery"),
        burst_passed
            .is_some_and(|passed| !passed)
            .then_some("burst"),
    ]
    .into_iter()
    .flatten()
    .collect::<Vec<_>>();

    match failed_families.len() {
        0 => worst_case.and_then(|label| {
            if label.contains("queue_full_reject") {
                Some("rejection")
            } else if label.contains("queue_recovery_send") {
                Some("recovery")
            } else if label.contains("burst_reject") {
                Some("burst")
            } else {
                None
            }
        }),
        1 => failed_families.first().copied(),
        _ => Some("mixed"),
    }
}

fn default_summary_path() -> PathBuf {
    verta_output_path("udp-rollout-validation-summary.json")
}

fn env_summary_path(canonical_key: &str, legacy_key: &str, file_name: &str) -> Option<String> {
    let path = prefer_verta_env_input_path(canonical_key, legacy_key, file_name);
    path.exists().then(|| path.display().to_string())
}

fn read_json_summary<T: for<'de> Deserialize<'de>>(
    canonical_key: &str,
    legacy_key: &str,
    file_name: &str,
) -> Result<Option<T>, Box<dyn std::error::Error>> {
    let path = prefer_verta_env_input_path(canonical_key, legacy_key, file_name);
    if !path.exists() {
        return Ok(None);
    }
    Ok(Some(serde_json::from_slice(&fs::read(path)?)?))
}

fn perf_case_passed(summary: Option<&UdpPerfGateSummary>, label: &str) -> Option<bool> {
    summary.and_then(|summary| {
        summary
            .results
            .iter()
            .find(|result| result.label == label)
            .map(|result| result.passed)
    })
}

fn perf_case_with_highest_utilization<'a>(
    summary: Option<&'a UdpPerfGateSummary>,
    labels: &[&str],
) -> Option<&'a PerfCaseSummary> {
    summary.and_then(|summary| {
        summary
            .results
            .iter()
            .filter(|result| labels.iter().any(|label| result.label == *label))
            .max_by_key(|result| utilization_pct(result))
    })
}

fn utilization_pct(result: &PerfCaseSummary) -> u128 {
    if result.allowed_ns == 0 {
        return 0;
    }
    result.candidate_ns.saturating_mul(100) / result.allowed_ns
}

#[cfg(test)]
mod tests {
    use super::{
        PerfCaseSummary, UDP_ROLLOUT_VALIDATION_SUMMARY_VERSION, UdpInteropLabSummary,
        UdpPerfGateSummary, ValidationCommandResult, build_validation_summary,
    };

    fn passed_result(label: &str) -> ValidationCommandResult {
        ValidationCommandResult {
            label: label.to_owned(),
            status: "passed",
            exit_code: Some(0),
            duration_ms: 1,
            command: vec!["cargo".to_owned(), "test".to_owned()],
        }
    }

    fn failed_result(label: &str) -> ValidationCommandResult {
        ValidationCommandResult {
            label: label.to_owned(),
            status: "failed",
            exit_code: Some(1),
            duration_ms: 1,
            command: vec!["cargo".to_owned(), "test".to_owned()],
        }
    }

    fn full_pass_results() -> Vec<ValidationCommandResult> {
        vec![
            passed_result("clientd_cli_surfaces"),
            passed_result("nsctl_cli_surfaces"),
            passed_result("gatewayd_cli_surfaces"),
            passed_result("repeated_queue_pressure_sticky"),
            passed_result("reordering_no_silent_fallback"),
            passed_result("longer_impairment_recovery_stable"),
            passed_result("mtu_ceiling_delivery_stable"),
            passed_result("fallback_flow_guard_rejection_stable"),
            passed_result("udp_blocked_fallback_surface_passed"),
            passed_result("policy_disabled_fallback_round_trip_stable"),
            passed_result("datagram_only_unavailable_rejection_stable"),
            passed_result("clean_shutdown_stable"),
            passed_result("prolonged_impairment_no_silent_fallback"),
            passed_result("post_close_rejection_stable"),
            passed_result("associated_stream_guard_recovery_stable"),
            passed_result("oversized_payload_guard_recovery_stable"),
            passed_result("reordered_after_close_rejection_stable"),
            passed_result("selected_datagram_lifecycle_stable"),
        ]
    }

    fn passing_perf_summary() -> UdpPerfGateSummary {
        UdpPerfGateSummary {
            all_passed: true,
            results: vec![
                PerfCaseSummary {
                    label: "H3DatagramSocket.queue_full_reject".to_owned(),
                    candidate_ns: 10,
                    allowed_ns: 100,
                    passed: true,
                },
                PerfCaseSummary {
                    label: "H3DatagramSocket.queue_recovery_send".to_owned(),
                    candidate_ns: 20,
                    allowed_ns: 100,
                    passed: true,
                },
                PerfCaseSummary {
                    label: "H3DatagramSocket.repeated_queue_recovery_send".to_owned(),
                    candidate_ns: 25,
                    allowed_ns: 100,
                    passed: true,
                },
                PerfCaseSummary {
                    label: "H3DatagramSocket.flow_burst_reject".to_owned(),
                    candidate_ns: 15,
                    allowed_ns: 100,
                    passed: true,
                },
                PerfCaseSummary {
                    label: "H3DatagramSocket.session_burst_reject".to_owned(),
                    candidate_ns: 18,
                    allowed_ns: 100,
                    passed: true,
                },
            ],
        }
    }

    fn passing_interop_summary() -> UdpInteropLabSummary {
        UdpInteropLabSummary {
            summary_version: Some(5),
            udp_blocked_fallback_surface_passed: Some(true),
            datagram_only_unavailable_rejection_surface_passed: Some(true),
            policy_disabled_fallback_surface_passed: Some(true),
            queue_pressure_surface_passed: Some(true),
            transport_fallback_integrity_surface_passed: Some(true),
            required_no_silent_fallback_profile_count: Some(
                ns_testkit::udp_wan_lab_required_no_silent_fallback_profile_slugs().len(),
            ),
            required_no_silent_fallback_passed_count: Some(
                ns_testkit::udp_wan_lab_required_no_silent_fallback_profile_slugs().len(),
            ),
        }
    }

    #[test]
    fn rollout_validation_summary_marks_degradation_surfaces_failed_when_shutdown_signal_fails() {
        let mut results = full_pass_results();
        results.retain(|result| result.label != "clean_shutdown_stable");
        results.push(failed_result("clean_shutdown_stable"));

        let summary = build_validation_summary(
            results,
            None,
            Some(passing_interop_summary()),
            Some(passing_perf_summary()),
            None,
            None,
            None,
        );

        assert!(!summary.clean_shutdown_stable);
        assert!(!summary.shutdown_sequence_stable);
        assert!(!summary.degradation_surface_passed);
        assert!(
            summary
                .failed_surface_keys
                .iter()
                .any(|key| key == "clean_shutdown_stable")
        );
        assert!(
            summary
                .failed_surface_keys
                .iter()
                .any(|key| key == "shutdown_sequence_stable")
        );
        assert!(
            summary
                .failed_surface_keys
                .iter()
                .any(|key| key == "degradation_surface_passed")
        );
    }

    #[test]
    fn rollout_validation_summary_reports_surface_counts_from_derived_statuses() {
        let summary = build_validation_summary(
            full_pass_results(),
            None,
            Some(passing_interop_summary()),
            Some(passing_perf_summary()),
            None,
            None,
            None,
        );

        assert_eq!(
            summary.summary_version,
            UDP_ROLLOUT_VALIDATION_SUMMARY_VERSION
        );
        assert_eq!(summary.surface_count_failed, 0);
        assert!(summary.failed_surface_keys.is_empty());
        assert_eq!(summary.surface_count_total, summary.surface_count_passed);
        assert!(summary.degradation_surface_passed);
        assert!(summary.queue_pressure_surface_passed);
        assert!(summary.mtu_ceiling_delivery_stable);
        assert!(summary.fallback_flow_guard_rejection_stable);
        assert!(summary.udp_blocked_fallback_surface_passed);
        assert!(summary.policy_disabled_fallback_round_trip_stable);
        assert!(summary.oversized_payload_guard_recovery_stable);
        assert!(summary.reordered_after_close_rejection_stable);
        assert_eq!(
            summary.interop_udp_blocked_fallback_surface_passed,
            Some(true)
        );
        assert_eq!(summary.interop_queue_pressure_surface_passed, Some(true));
        assert!(summary.transport_fallback_integrity_surface_passed);
        assert_eq!(
            summary.interop_transport_fallback_integrity_surface_passed,
            Some(true)
        );
        assert_eq!(summary.queue_guard_headroom_band, Some("healthy"));
        assert_eq!(summary.queue_guard_headroom_missing_count, 0);
    }

    #[test]
    fn rollout_validation_summary_marks_transport_fallback_integrity_failed_when_reordering_fails()
    {
        let mut results = full_pass_results();
        results.retain(|result| result.label != "reordering_no_silent_fallback");
        results.push(failed_result("reordering_no_silent_fallback"));

        let summary = build_validation_summary(
            results,
            None,
            Some(passing_interop_summary()),
            Some(passing_perf_summary()),
            None,
            None,
            None,
        );

        assert!(!summary.reordering_no_silent_fallback_passed);
        assert!(!summary.degradation_surface_passed);
        assert!(!summary.transport_fallback_integrity_surface_passed);
        assert_eq!(summary.rollout_surface_passed, Some(false));
        assert!(
            summary
                .failed_surface_keys
                .iter()
                .any(|key| key == "reordering_no_silent_fallback_passed")
        );
        assert!(
            summary
                .failed_surface_keys
                .iter()
                .any(|key| key == "transport_fallback_integrity_surface_passed")
        );
    }

    #[test]
    fn rollout_validation_summary_marks_negotiated_limit_validation_failed_when_mtu_ceiling_fails()
    {
        let mut results = full_pass_results();
        results.retain(|result| result.label != "mtu_ceiling_delivery_stable");
        results.push(failed_result("mtu_ceiling_delivery_stable"));

        let summary = build_validation_summary(
            results,
            None,
            Some(passing_interop_summary()),
            Some(passing_perf_summary()),
            None,
            None,
            None,
        );

        assert!(!summary.mtu_ceiling_delivery_stable);
        assert!(!summary.negotiated_limit_validation_passed);
        assert!(
            summary
                .failed_surface_keys
                .iter()
                .any(|key| key == "mtu_ceiling_delivery_stable")
        );
        assert!(
            summary
                .failed_surface_keys
                .iter()
                .any(|key| key == "negotiated_limit_validation_passed")
        );
    }

    #[test]
    fn rollout_validation_summary_marks_transport_fallback_integrity_failed_when_fallback_flow_guard_fails()
     {
        let mut results = full_pass_results();
        results.retain(|result| result.label != "fallback_flow_guard_rejection_stable");
        results.push(failed_result("fallback_flow_guard_rejection_stable"));

        let summary = build_validation_summary(
            results,
            None,
            Some(passing_interop_summary()),
            Some(passing_perf_summary()),
            None,
            None,
            None,
        );

        assert!(!summary.fallback_flow_guard_rejection_stable);
        assert!(!summary.transport_fallback_integrity_surface_passed);
        assert!(
            summary
                .failed_surface_keys
                .iter()
                .any(|key| key == "fallback_flow_guard_rejection_stable")
        );
        assert!(
            summary
                .failed_surface_keys
                .iter()
                .any(|key| key == "transport_fallback_integrity_surface_passed")
        );
    }

    #[test]
    fn rollout_validation_summary_marks_transport_fallback_integrity_failed_when_blocked_fallback_surface_fails()
     {
        let mut results = full_pass_results();
        results.retain(|result| result.label != "udp_blocked_fallback_surface_passed");
        results.push(failed_result("udp_blocked_fallback_surface_passed"));

        let summary = build_validation_summary(
            results,
            None,
            Some(passing_interop_summary()),
            Some(passing_perf_summary()),
            None,
            None,
            None,
        );

        assert!(!summary.udp_blocked_fallback_surface_passed);
        assert!(summary.degradation_surface_passed);
        assert!(!summary.transport_fallback_integrity_surface_passed);
        assert_eq!(summary.rollout_surface_passed, Some(false));
        assert!(
            summary
                .failed_surface_keys
                .iter()
                .any(|key| key == "udp_blocked_fallback_surface_passed")
        );
        assert!(
            summary
                .failed_surface_keys
                .iter()
                .any(|key| key == "transport_fallback_integrity_surface_passed")
        );
    }

    #[test]
    fn rollout_validation_summary_keeps_degradation_green_when_policy_disabled_fallback_round_trip_fails()
     {
        let mut results = full_pass_results();
        results.retain(|result| result.label != "policy_disabled_fallback_round_trip_stable");
        results.push(failed_result("policy_disabled_fallback_round_trip_stable"));

        let summary = build_validation_summary(
            results,
            None,
            Some(passing_interop_summary()),
            Some(passing_perf_summary()),
            None,
            None,
            None,
        );

        assert!(!summary.policy_disabled_fallback_round_trip_stable);
        assert!(summary.degradation_surface_passed);
        assert!(!summary.transport_fallback_integrity_surface_passed);
        assert_eq!(summary.rollout_surface_passed, Some(false));
        assert!(
            summary
                .failed_surface_keys
                .iter()
                .any(|key| key == "policy_disabled_fallback_round_trip_stable")
        );
        assert!(
            summary
                .failed_surface_keys
                .iter()
                .any(|key| key == "transport_fallback_integrity_surface_passed")
        );
    }

    #[test]
    fn rollout_validation_summary_marks_shutdown_and_degradation_failed_when_reordered_after_close_signal_fails()
     {
        let mut results = full_pass_results();
        results.retain(|result| result.label != "reordered_after_close_rejection_stable");
        results.push(failed_result("reordered_after_close_rejection_stable"));

        let summary = build_validation_summary(
            results,
            None,
            Some(passing_interop_summary()),
            Some(passing_perf_summary()),
            None,
            None,
            None,
        );

        assert!(!summary.reordered_after_close_rejection_stable);
        assert!(!summary.shutdown_sequence_stable);
        assert!(!summary.degradation_surface_passed);
        assert!(!summary.transport_fallback_integrity_surface_passed);
        assert!(
            summary
                .failed_surface_keys
                .iter()
                .any(|key| key == "reordered_after_close_rejection_stable")
        );
    }

    #[test]
    fn rollout_validation_summary_marks_degradation_failed_when_oversized_payload_guard_fails() {
        let mut results = full_pass_results();
        results.retain(|result| result.label != "oversized_payload_guard_recovery_stable");
        results.push(failed_result("oversized_payload_guard_recovery_stable"));

        let summary = build_validation_summary(
            results,
            None,
            Some(passing_interop_summary()),
            Some(passing_perf_summary()),
            None,
            None,
            None,
        );

        assert!(!summary.oversized_payload_guard_recovery_stable);
        assert!(!summary.sticky_selection_surface_passed);
        assert!(!summary.degradation_surface_passed);
        assert!(!summary.transport_fallback_integrity_surface_passed);
        assert!(
            summary
                .failed_surface_keys
                .iter()
                .any(|key| key == "oversized_payload_guard_recovery_stable")
        );
    }

    #[test]
    fn rollout_validation_summary_distrusts_interop_blocked_fallback_when_surface_drifts() {
        let mut interop = passing_interop_summary();
        interop.udp_blocked_fallback_surface_passed = Some(false);

        let summary = build_validation_summary(
            full_pass_results(),
            None,
            Some(interop),
            Some(passing_perf_summary()),
            None,
            None,
            None,
        );

        assert_eq!(
            summary.interop_udp_blocked_fallback_surface_passed,
            Some(false)
        );
        assert_eq!(
            summary.interop_transport_fallback_integrity_surface_passed,
            Some(false)
        );
        assert!(!summary.transport_fallback_integrity_surface_passed);
        assert!(
            summary
                .failed_surface_keys
                .iter()
                .any(|key| key == "transport_fallback_integrity_surface_passed")
        );
    }

    #[test]
    fn rollout_validation_summary_distrusts_interop_fallback_integrity_when_required_counts_drift()
    {
        let mut interop = passing_interop_summary();
        interop.required_no_silent_fallback_passed_count = Some(
            ns_testkit::udp_wan_lab_required_no_silent_fallback_profile_slugs()
                .len()
                .saturating_sub(1),
        );

        let summary = build_validation_summary(
            full_pass_results(),
            None,
            Some(interop),
            Some(passing_perf_summary()),
            None,
            None,
            None,
        );

        assert_eq!(
            summary.interop_transport_fallback_integrity_surface_passed,
            Some(false)
        );
        assert!(!summary.transport_fallback_integrity_surface_passed);
        assert!(
            summary
                .failed_surface_keys
                .iter()
                .any(|key| key == "transport_fallback_integrity_surface_passed")
        );
    }
}
