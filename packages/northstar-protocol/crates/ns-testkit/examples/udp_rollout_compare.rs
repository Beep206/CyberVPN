use ns_testkit::{
    UDP_ROLLOUT_DECISION_SCOPE_HOST, UDP_ROLLOUT_OPERATOR_VERDICT_FAMILY,
    UDP_ROLLOUT_OPERATOR_VERDICT_SCHEMA, UDP_ROLLOUT_OPERATOR_VERDICT_SCHEMA_VERSION, repo_root,
    summarize_rollout_gate_state, udp_wan_lab_profile_slugs,
    udp_wan_lab_required_no_silent_fallback_profile_slugs,
};
use serde::{Deserialize, Serialize};
use std::collections::BTreeSet;
use std::env;
use std::fs;
use std::path::PathBuf;

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
enum OutputFormat {
    Text,
    Json,
}

const UDP_FUZZ_SMOKE_SUMMARY_VERSION: u8 = 1;
const UDP_PERF_GATE_SUMMARY_VERSION: u8 = 1;
const UDP_INTEROP_LAB_SUMMARY_VERSION: u8 = 5;
const UDP_ROLLOUT_VALIDATION_SUMMARY_VERSION: u8 = 20;
const UDP_ACTIVE_FUZZ_SUMMARY_VERSION: u8 = 1;
const UDP_ROLLOUT_COMPARISON_SUMMARY_VERSION: u8 = 14;

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
enum ComparisonProfile {
    Readiness,
    StagedRollout,
}

impl ComparisonProfile {
    fn as_str(self) -> &'static str {
        match self {
            Self::Readiness => "readiness",
            Self::StagedRollout => "staged_rollout",
        }
    }

    fn active_fuzz_required(self) -> bool {
        matches!(self, Self::StagedRollout)
    }
}

#[derive(Debug, Default)]
struct ComparisonArgs {
    format: Option<OutputFormat>,
    summary_path: Option<PathBuf>,
    host_label: Option<String>,
    profile: Option<ComparisonProfile>,
}

#[derive(Debug, Deserialize)]
struct UdpFuzzSmokeSummary {
    #[serde(default)]
    summary_version: Option<u8>,
    all_passed: bool,
}

#[derive(Debug, Deserialize)]
struct UdpPerfGateSummary {
    #[serde(default)]
    summary_version: Option<u8>,
    all_passed: bool,
}

#[derive(Debug, Deserialize)]
struct UdpInteropLabSummary {
    #[serde(default)]
    summary_version: Option<u8>,
    all_passed: bool,
    profile_count: usize,
    #[serde(default)]
    profile_slugs: Vec<String>,
    #[serde(default)]
    failed_profile_slugs: Vec<String>,
    #[serde(default)]
    explicit_fallback_profile_count: usize,
    #[serde(default)]
    udp_blocked_fallback_surface_passed: Option<bool>,
    #[serde(default)]
    required_no_silent_fallback_profile_count: usize,
    #[serde(default)]
    required_no_silent_fallback_passed_count: usize,
    #[serde(default)]
    required_no_silent_fallback_profile_slugs: Vec<String>,
    #[serde(default)]
    queue_pressure_surface_passed: bool,
    #[serde(default)]
    transport_fallback_integrity_surface_passed: bool,
    #[serde(default)]
    policy_disabled_fallback_surface_passed: Option<bool>,
}

#[derive(Debug, Deserialize)]
struct UdpRolloutValidationSummary {
    #[serde(default)]
    summary_version: Option<u8>,
    all_passed: bool,
    cli_surface_consistency_passed: bool,
    startup_contract_validation_passed: bool,
    negotiated_limit_validation_passed: bool,
    #[serde(default)]
    selected_datagram_lifecycle_passed: bool,
    #[serde(default)]
    udp_blocked_fallback_surface_passed: bool,
    repeated_queue_pressure_sticky: bool,
    prolonged_impairment_no_silent_fallback: bool,
    #[serde(default)]
    prolonged_repeated_impairment_stable: bool,
    #[serde(default)]
    longer_impairment_recovery_stable: bool,
    #[serde(default)]
    shutdown_sequence_stable: bool,
    post_close_rejection_stable: bool,
    clean_shutdown_stable: bool,
    #[serde(default)]
    policy_disabled_fallback_surface_passed: Option<bool>,
    #[serde(default)]
    policy_disabled_fallback_round_trip_stable: bool,
    queue_saturation_surface_passed: Option<bool>,
    queue_saturation_worst_case: Option<String>,
    queue_saturation_worst_utilization_pct: Option<u128>,
    queue_guard_headroom_passed: Option<bool>,
    queue_guard_headroom_band: Option<String>,
    queue_guard_headroom_missing_count: usize,
    queue_guard_rejection_path_passed: Option<bool>,
    queue_guard_recovery_path_passed: Option<bool>,
    queue_guard_burst_path_passed: Option<bool>,
    queue_guard_limiting_path: Option<String>,
    sticky_selection_surface_passed: bool,
    degradation_surface_passed: bool,
    #[serde(default)]
    transport_fallback_integrity_surface_passed: bool,
    rollout_surface_passed: Option<bool>,
    surface_count_total: usize,
    surface_count_passed: usize,
    surface_count_failed: usize,
    #[serde(default)]
    failed_surface_keys: Vec<String>,
}

#[derive(Debug, Deserialize)]
struct UdpActiveFuzzTargetSummary {
    target: String,
    status: String,
}

#[derive(Debug, Deserialize)]
struct UdpActiveFuzzSummary {
    #[serde(default)]
    summary_version: Option<u8>,
    all_passed: bool,
    #[serde(default)]
    results: Vec<UdpActiveFuzzTargetSummary>,
}

#[derive(Debug, Serialize)]
struct SummaryPresence {
    path: Option<String>,
    present: bool,
    passed: Option<bool>,
}

#[derive(Debug, Serialize)]
struct ReasonDetail {
    code: String,
    reason_key: String,
    family: &'static str,
    source: &'static str,
}

#[derive(Debug, Serialize)]
struct UdpRolloutComparisonSummary {
    summary_version: u8,
    comparison_schema: &'static str,
    comparison_schema_version: u8,
    verdict_family: &'static str,
    decision_scope: &'static str,
    decision_label: String,
    profile: &'static str,
    host_label: String,
    verdict: &'static str,
    evidence_state: &'static str,
    gate_state: &'static str,
    gate_state_reason: &'static str,
    gate_state_reason_family: &'static str,
    active_fuzz_required: bool,
    required_inputs: Vec<String>,
    considered_inputs: Vec<String>,
    missing_required_inputs: Vec<String>,
    missing_required_input_count: usize,
    required_input_count: usize,
    required_input_missing_count: usize,
    required_input_failed_count: usize,
    required_input_unready_count: usize,
    required_input_present_count: usize,
    required_input_passed_count: usize,
    required_summaries: Vec<String>,
    considered_summaries: Vec<String>,
    all_required_inputs_present: bool,
    all_required_inputs_passed: bool,
    all_required_summaries_present: bool,
    all_required_summaries_passed: bool,
    blocking_reason_count: usize,
    blocking_reason_key_count: usize,
    blocking_reason_family_count: usize,
    blocking_reason_key_counts: std::collections::BTreeMap<String, usize>,
    blocking_reason_family_counts: std::collections::BTreeMap<String, usize>,
    advisory_reason_count: usize,
    cli_surface_consistency_passed: Option<bool>,
    startup_contract_validation_passed: Option<bool>,
    negotiated_limit_validation_passed: Option<bool>,
    selected_datagram_lifecycle_passed: Option<bool>,
    queue_saturation_surface_passed: Option<bool>,
    queue_saturation_worst_case: Option<String>,
    queue_saturation_worst_utilization_pct: Option<u128>,
    queue_guard_headroom_passed: Option<bool>,
    queue_guard_headroom_band: Option<String>,
    queue_guard_headroom_missing_count: usize,
    queue_guard_rejection_path_passed: Option<bool>,
    queue_guard_recovery_path_passed: Option<bool>,
    queue_guard_burst_path_passed: Option<bool>,
    queue_guard_limiting_path: Option<String>,
    queue_guard_tight_hold_count: usize,
    queue_pressure_hold_count: usize,
    sticky_selection_surface_passed: Option<bool>,
    degradation_surface_passed: Option<bool>,
    degradation_hold_count: usize,
    degradation_hold_subjects: Vec<String>,
    transport_fallback_integrity_surface_passed: Option<bool>,
    rollout_surface_passed: Option<bool>,
    surface_count_total: Option<usize>,
    surface_count_passed: Option<usize>,
    surface_count_failed: Option<usize>,
    failed_surface_keys: Vec<String>,
    repeated_queue_pressure_sticky: Option<bool>,
    prolonged_impairment_no_silent_fallback: Option<bool>,
    prolonged_repeated_impairment_stable: Option<bool>,
    longer_impairment_recovery_stable: Option<bool>,
    shutdown_sequence_stable: Option<bool>,
    post_close_rejection_stable: Option<bool>,
    clean_shutdown_stable: Option<bool>,
    interop_profile_count: Option<usize>,
    interop_profile_slugs: Vec<String>,
    interop_failed_profile_slugs: Vec<String>,
    interop_required_no_silent_fallback_profile_slugs: Vec<String>,
    interop_profile_contract_passed: Option<bool>,
    udp_blocked_fallback_surface_passed: Option<bool>,
    explicit_fallback_profile_count: usize,
    policy_disabled_fallback_surface_passed: Option<bool>,
    policy_disabled_fallback_round_trip_stable: Option<bool>,
    interop_failed_profile_count: usize,
    active_fuzz_failed_targets: Vec<String>,
    smoke: SummaryPresence,
    perf: SummaryPresence,
    interop: SummaryPresence,
    rollout_validation: SummaryPresence,
    active_fuzz: SummaryPresence,
    blocking_reasons: Vec<String>,
    blocking_reason_keys: Vec<String>,
    blocking_reason_families: Vec<String>,
    blocking_reason_details: Vec<ReasonDetail>,
    advisory_reasons: Vec<String>,
}

fn main() -> Result<(), Box<dyn std::error::Error>> {
    let args = parse_args(env::args().skip(1))?;
    let profile = args
        .profile
        .or_else(|| {
            env::var("NORTHSTAR_UDP_ROLLOUT_COMPARE_PROFILE")
                .ok()
                .and_then(|value| parse_profile(&value).ok())
        })
        .unwrap_or(ComparisonProfile::Readiness);
    let smoke = load_summary::<UdpFuzzSmokeSummary>("NORTHSTAR_UDP_FUZZ_SMOKE_SUMMARY_PATH")?;
    let perf = load_summary::<UdpPerfGateSummary>("NORTHSTAR_UDP_PERF_SUMMARY_PATH")?;
    let interop = load_summary::<UdpInteropLabSummary>("NORTHSTAR_UDP_INTEROP_SUMMARY_PATH")?;
    let rollout = load_summary::<UdpRolloutValidationSummary>(
        "NORTHSTAR_UDP_ROLLOUT_VALIDATION_SUMMARY_PATH",
    )?;
    let active_fuzz =
        load_summary::<UdpActiveFuzzSummary>("NORTHSTAR_UDP_ACTIVE_FUZZ_SUMMARY_PATH")?;
    let summary = build_comparison_summary(
        profile,
        args.host_label
            .or_else(|| env::var("NORTHSTAR_UDP_ROLLOUT_HOST_LABEL").ok())
            .unwrap_or_else(|| "local".to_owned()),
        smoke,
        perf,
        interop,
        rollout,
        active_fuzz,
    );

    let summary_path = args.summary_path.unwrap_or_else(default_summary_path);
    if let Some(parent) = summary_path.parent() {
        fs::create_dir_all(parent)?;
    }
    fs::write(&summary_path, serde_json::to_vec_pretty(&summary)?)?;

    match args.format.unwrap_or(OutputFormat::Text) {
        OutputFormat::Text => {
            println!("Northstar UDP rollout comparison summary:");
            println!("- host_label: {}", summary.host_label);
            println!("- profile: {}", summary.profile);
            println!("- verdict: {}", summary.verdict);
            println!("- comparison_schema: {}", summary.comparison_schema);
            println!(
                "- comparison_schema_version: {}",
                summary.comparison_schema_version
            );
            println!("- verdict_family: {}", summary.verdict_family);
            println!("- decision_scope: {}", summary.decision_scope);
            println!("- decision_label: {}", summary.decision_label);
            println!("- evidence_state: {}", summary.evidence_state);
            println!("- gate_state: {}", summary.gate_state);
            println!("- gate_state_reason: {}", summary.gate_state_reason);
            println!(
                "- gate_state_reason_family: {}",
                summary.gate_state_reason_family
            );
            println!("- active_fuzz_required: {}", summary.active_fuzz_required);
            println!(
                "- required_summary_labels: {}",
                summary.required_summaries.join(", ")
            );
            println!("- required_inputs: {}", summary.required_inputs.join(", "));
            println!(
                "- considered_inputs: {}",
                summary.considered_inputs.join(", ")
            );
            if summary.missing_required_inputs.is_empty() {
                println!("- missing_required_inputs: none");
            } else {
                println!(
                    "- missing_required_inputs: {}",
                    summary.missing_required_inputs.join(", ")
                );
            }
            println!(
                "- missing_required_input_count: {}",
                summary.missing_required_input_count
            );
            println!(
                "- required_input_missing_count: {}",
                summary.required_input_missing_count
            );
            println!(
                "- all_required_inputs: present={} passed={}",
                summary.all_required_inputs_present, summary.all_required_inputs_passed
            );
            println!(
                "- required_input_counts: total={} present={} passed={}",
                summary.required_input_count,
                summary.required_input_present_count,
                summary.required_input_passed_count
            );
            println!(
                "- required_input_failed_count: {}",
                summary.required_input_failed_count
            );
            println!(
                "- required_input_unready_count: {}",
                summary.required_input_unready_count
            );
            println!(
                "- required_summaries: present={} passed={}",
                summary.all_required_summaries_present, summary.all_required_summaries_passed
            );
            if let Some(selected_datagram_lifecycle_passed) =
                summary.selected_datagram_lifecycle_passed
            {
                println!(
                    "- selected_datagram_lifecycle_passed: {selected_datagram_lifecycle_passed}"
                );
            }
            if let Some(rollout_surface_passed) = summary.rollout_surface_passed {
                println!("- rollout_surface_passed: {rollout_surface_passed}");
            }
            if let Some(sticky_selection_surface_passed) = summary.sticky_selection_surface_passed {
                println!("- sticky_selection_surface_passed: {sticky_selection_surface_passed}");
            }
            if let Some(degradation_surface_passed) = summary.degradation_surface_passed {
                println!("- degradation_surface_passed: {degradation_surface_passed}");
            }
            if summary.degradation_hold_subjects.is_empty() {
                println!("- degradation_hold_subjects: none");
            } else {
                println!(
                    "- degradation_hold_subjects: {}",
                    summary.degradation_hold_subjects.join(", ")
                );
            }
            println!(
                "- degradation_hold_count: {}",
                summary.degradation_hold_count
            );
            println!(
                "- queue_guard_tight_hold_count: {}",
                summary.queue_guard_tight_hold_count
            );
            println!(
                "- queue_pressure_hold_count: {}",
                summary.queue_pressure_hold_count
            );
            if let Some(longer_impairment_recovery_stable) =
                summary.longer_impairment_recovery_stable
            {
                println!(
                    "- longer_impairment_recovery_stable: {longer_impairment_recovery_stable}"
                );
            }
            if let Some(shutdown_sequence_stable) = summary.shutdown_sequence_stable {
                println!("- shutdown_sequence_stable: {shutdown_sequence_stable}");
            }
            if let Some(prolonged_repeated_impairment_stable) =
                summary.prolonged_repeated_impairment_stable
            {
                println!(
                    "- prolonged_repeated_impairment_stable: {prolonged_repeated_impairment_stable}"
                );
            }
            if let Some(queue_guard_headroom_band) = &summary.queue_guard_headroom_band {
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
            if let Some(queue_guard_limiting_path) = &summary.queue_guard_limiting_path {
                println!("- queue_guard_limiting_path: {queue_guard_limiting_path}");
            }
            if let Some(queue_saturation_worst_case) = &summary.queue_saturation_worst_case {
                println!(
                    "- queue_saturation_worst_case: {} ({}%)",
                    queue_saturation_worst_case,
                    summary.queue_saturation_worst_utilization_pct.unwrap_or(0)
                );
            }
            if let Some(surface_count_total) = summary.surface_count_total {
                println!(
                    "- surface_counts: total={} passed={} failed={}",
                    surface_count_total,
                    summary.surface_count_passed.unwrap_or_default(),
                    summary.surface_count_failed.unwrap_or_default()
                );
            }
            if summary.failed_surface_keys.is_empty() {
                println!("- failed_surface_keys: none");
            } else {
                println!(
                    "- failed_surface_keys: {}",
                    summary.failed_surface_keys.join(", ")
                );
            }
            if summary.active_fuzz_failed_targets.is_empty() {
                println!("- active_fuzz_failed_targets: none");
            } else {
                println!(
                    "- active_fuzz_failed_targets: {}",
                    summary.active_fuzz_failed_targets.join(", ")
                );
            }
            if summary.interop_profile_slugs.is_empty() {
                println!("- interop_profile_slugs: none");
            } else {
                println!(
                    "- interop_profile_slugs: {}",
                    summary.interop_profile_slugs.join(", ")
                );
            }
            if summary.interop_failed_profile_slugs.is_empty() {
                println!("- interop_failed_profile_slugs: none");
            } else {
                println!(
                    "- interop_failed_profile_slugs: {}",
                    summary.interop_failed_profile_slugs.join(", ")
                );
            }
            if summary
                .interop_required_no_silent_fallback_profile_slugs
                .is_empty()
            {
                println!("- interop_required_no_silent_fallback_profile_slugs: none");
            } else {
                println!(
                    "- interop_required_no_silent_fallback_profile_slugs: {}",
                    summary
                        .interop_required_no_silent_fallback_profile_slugs
                        .join(", ")
                );
            }
            if let Some(interop_profile_contract_passed) = summary.interop_profile_contract_passed {
                println!("- interop_profile_contract_passed: {interop_profile_contract_passed}");
            }
            println!(
                "- explicit_fallback_profile_count: {}",
                summary.explicit_fallback_profile_count
            );
            if let Some(policy_disabled_fallback_surface_passed) =
                summary.policy_disabled_fallback_surface_passed
            {
                println!(
                    "- policy_disabled_fallback_surface_passed: {policy_disabled_fallback_surface_passed}"
                );
            }
            if let Some(udp_blocked_fallback_surface_passed) =
                summary.udp_blocked_fallback_surface_passed
            {
                println!(
                    "- udp_blocked_fallback_surface_passed: {udp_blocked_fallback_surface_passed}"
                );
            }
            if let Some(policy_disabled_fallback_round_trip_stable) =
                summary.policy_disabled_fallback_round_trip_stable
            {
                println!(
                    "- policy_disabled_fallback_round_trip_stable: {policy_disabled_fallback_round_trip_stable}"
                );
            }
            println!(
                "- interop_failed_profile_count: {}",
                summary.interop_failed_profile_count
            );
            if let Some(transport_fallback_integrity_surface_passed) =
                summary.transport_fallback_integrity_surface_passed
            {
                println!(
                    "- transport_fallback_integrity_surface_passed: {transport_fallback_integrity_surface_passed}"
                );
            }
            if summary.blocking_reasons.is_empty() {
                println!("- blocking_reasons: none");
            } else {
                println!(
                    "- blocking_reasons: {}",
                    summary.blocking_reasons.join(", ")
                );
            }
            if summary.blocking_reason_family_counts.is_empty() {
                println!("- blocking_reason_family_counts: none");
            } else {
                println!(
                    "- blocking_reason_family_counts: {}",
                    summary
                        .blocking_reason_family_counts
                        .iter()
                        .map(|(family, count)| format!("{family}={count}"))
                        .collect::<Vec<_>>()
                        .join(", ")
                );
            }
            if summary.blocking_reason_families.is_empty() {
                println!("- blocking_reason_families: none");
            } else {
                println!(
                    "- blocking_reason_families: {}",
                    summary.blocking_reason_families.join(", ")
                );
            }
            if summary.blocking_reason_key_counts.is_empty() {
                println!("- blocking_reason_key_counts: none");
            } else {
                println!(
                    "- blocking_reason_key_counts: {}",
                    summary
                        .blocking_reason_key_counts
                        .iter()
                        .map(|(key, count)| format!("{key}={count}"))
                        .collect::<Vec<_>>()
                        .join(", ")
                );
            }
            if summary.blocking_reason_keys.is_empty() {
                println!("- blocking_reason_keys: none");
            } else {
                println!(
                    "- blocking_reason_keys: {}",
                    summary.blocking_reason_keys.join(", ")
                );
            }
            println!(
                "- reason_counts: blocking={} advisory={}",
                summary.blocking_reason_count, summary.advisory_reason_count
            );
            println!(
                "- blocking_reason_key_count: {}",
                summary.blocking_reason_key_count
            );
            println!(
                "- blocking_reason_family_count: {}",
                summary.blocking_reason_family_count
            );
            if summary.advisory_reasons.is_empty() {
                println!("- advisory_reasons: none");
            } else {
                println!(
                    "- advisory_reasons: {}",
                    summary.advisory_reasons.join(", ")
                );
            }
            println!("machine_readable_summary={}", summary_path.display());
        }
        OutputFormat::Json => {
            println!("{}", serde_json::to_string_pretty(&summary)?);
        }
    }

    if summary.verdict != "ready" {
        return Err("udp rollout comparison is not ready".into());
    }

    Ok(())
}

#[derive(Debug)]
struct LoadedSummary<T> {
    path: Option<String>,
    present: bool,
    summary: Option<T>,
}

fn build_comparison_summary(
    profile: ComparisonProfile,
    host_label: String,
    smoke: LoadedSummary<UdpFuzzSmokeSummary>,
    perf: LoadedSummary<UdpPerfGateSummary>,
    interop: LoadedSummary<UdpInteropLabSummary>,
    rollout: LoadedSummary<UdpRolloutValidationSummary>,
    active_fuzz: LoadedSummary<UdpActiveFuzzSummary>,
) -> UdpRolloutComparisonSummary {
    let decision_label = host_label.clone();
    let smoke_passed = smoke.summary.as_ref().map(|summary| summary.all_passed);
    let perf_passed = perf.summary.as_ref().map(|summary| summary.all_passed);
    let interop_passed = interop.summary.as_ref().map(|summary| summary.all_passed);
    let active_fuzz_passed = active_fuzz
        .summary
        .as_ref()
        .map(|summary| summary.all_passed);
    let active_fuzz_failed_targets = active_fuzz
        .summary
        .as_ref()
        .map(|summary| {
            summary
                .results
                .iter()
                .filter(|result| result.status != "passed")
                .map(|result| result.target.clone())
                .collect::<Vec<_>>()
        })
        .unwrap_or_default();
    let smoke_summary_version = smoke
        .summary
        .as_ref()
        .and_then(|summary| summary.summary_version);
    let perf_summary_version = perf
        .summary
        .as_ref()
        .and_then(|summary| summary.summary_version);
    let interop_summary_version = interop
        .summary
        .as_ref()
        .and_then(|summary| summary.summary_version);
    let expected_required_no_silent_fallback_profile_slugs =
        udp_wan_lab_required_no_silent_fallback_profile_slugs()
            .into_iter()
            .map(str::to_owned)
            .collect::<Vec<_>>();
    let expected_required_no_silent_fallback_profile_set =
        expected_required_no_silent_fallback_profile_slugs
            .iter()
            .cloned()
            .collect::<BTreeSet<_>>();
    let interop_summary = interop
        .summary
        .as_ref()
        .filter(|summary| summary.summary_version == Some(UDP_INTEROP_LAB_SUMMARY_VERSION));
    let interop_required_no_silent_fallback_profile_slugs = interop_summary
        .map(|summary| summary.required_no_silent_fallback_profile_slugs.clone())
        .unwrap_or_default();
    let interop_required_no_silent_fallback_profile_set =
        interop_required_no_silent_fallback_profile_slugs
            .iter()
            .cloned()
            .collect::<BTreeSet<_>>();
    let rollout_summary_version = rollout
        .summary
        .as_ref()
        .and_then(|summary| summary.summary_version);
    let active_fuzz_summary_version = active_fuzz
        .summary
        .as_ref()
        .and_then(|summary| summary.summary_version);
    let interop_contract_valid = interop_summary
        .map(interop_summary_contract_valid)
        .unwrap_or(false);
    let interop_profile_contract_passed = interop_summary.map(interop_summary_contract_valid);
    let rollout_summary = rollout
        .summary
        .as_ref()
        .filter(|summary| summary.summary_version == Some(UDP_ROLLOUT_VALIDATION_SUMMARY_VERSION));
    let rollout_passed = rollout_summary.map(|summary| summary.all_passed);
    let queue_guard_headroom_passed =
        rollout_summary.and_then(|summary| summary.queue_guard_headroom_passed);
    let queue_guard_headroom_band =
        rollout_summary.and_then(|summary| summary.queue_guard_headroom_band.as_ref().cloned());
    let queue_guard_headroom_missing_count = rollout_summary
        .map(|summary| {
            summary.queue_guard_headroom_missing_count
                + usize::from(summary.queue_guard_headroom_passed.is_none())
        })
        .unwrap_or(usize::from(rollout.present));
    let udp_blocked_fallback_surface_passed = match (
        interop_summary.and_then(|summary| summary.udp_blocked_fallback_surface_passed),
        rollout_summary.map(|summary| summary.udp_blocked_fallback_surface_passed),
    ) {
        (Some(interop_passed), Some(rollout_passed)) => Some(interop_passed && rollout_passed),
        (Some(false), _) | (_, Some(false)) => Some(false),
        (Some(true), None) | (None, Some(true)) => None,
        (None, None) => None,
    };
    let policy_disabled_fallback_round_trip_stable =
        rollout_summary.map(|summary| summary.policy_disabled_fallback_round_trip_stable);
    let transport_fallback_integrity_surface_passed =
        rollout_summary.map(|summary| summary.transport_fallback_integrity_surface_passed);
    let queue_pressure_hold_count = usize::from(
        interop_summary.map(|summary| summary.queue_pressure_surface_passed) == Some(false),
    );
    let required_summaries = required_summaries_for_profile(profile);
    let considered_summaries = vec![
        "smoke".to_owned(),
        "perf".to_owned(),
        "interop".to_owned(),
        "rollout_validation".to_owned(),
        "active_fuzz".to_owned(),
    ];
    let required_inputs = required_summaries.clone();
    let considered_inputs = considered_summaries.clone();
    let required_input_present = |label: &str| match label {
        "smoke" => smoke.present,
        "perf" => perf.present,
        "interop" => interop.present,
        "rollout_validation" => rollout.present,
        "active_fuzz" => active_fuzz.present,
        other => panic!("unsupported required summary label {other}"),
    };
    let required_input_version = |label: &str| match label {
        "smoke" => smoke_summary_version,
        "perf" => perf_summary_version,
        "interop" => interop_summary_version,
        "rollout_validation" => rollout_summary_version,
        "active_fuzz" => active_fuzz_summary_version,
        other => panic!("unsupported required summary label {other}"),
    };
    let missing_required_inputs = required_summaries
        .iter()
        .filter(|label| !required_input_present(label))
        .cloned()
        .collect::<Vec<_>>();
    let missing_required_input_count = missing_required_inputs.len();

    let mut blocking_reasons = Vec::new();
    let mut blocking_reason_details = Vec::new();
    for label in &required_summaries {
        let present = required_input_present(label);
        if !present {
            push_reason(
                &mut blocking_reasons,
                &mut blocking_reason_details,
                "summary_presence_missing",
                format!("missing_{label}_summary"),
                "summary_presence",
                summary_source(label),
            );
            continue;
        }
        let version = required_input_version(label);
        let expected_version = expected_summary_version(label);
        if version.is_none() {
            push_reason(
                &mut blocking_reasons,
                &mut blocking_reason_details,
                "summary_version_missing",
                format!("{label}_summary_version_missing"),
                "summary_version",
                summary_source(label),
            );
        } else if version != Some(expected_version) {
            push_reason(
                &mut blocking_reasons,
                &mut blocking_reason_details,
                "summary_version_unsupported",
                format!("{label}_summary_version_unsupported"),
                "summary_version",
                summary_source(label),
            );
        }
    }

    let all_required_summaries_present = required_summaries
        .iter()
        .all(|label| required_input_present(label));
    let all_required_summary_versions_supported = required_summaries
        .iter()
        .all(|label| required_input_version(label) == Some(expected_summary_version(label)));
    let required_input_passed = |label: &str| match label {
        "smoke" => {
            smoke.present
                && smoke_summary_version == Some(UDP_FUZZ_SMOKE_SUMMARY_VERSION)
                && smoke_passed.unwrap_or(false)
        }
        "perf" => {
            perf.present
                && perf_summary_version == Some(UDP_PERF_GATE_SUMMARY_VERSION)
                && perf_passed.unwrap_or(false)
        }
        "interop" => {
            interop.present
                && interop_summary_version == Some(UDP_INTEROP_LAB_SUMMARY_VERSION)
                && interop_contract_valid
                && interop_passed.unwrap_or(false)
        }
        "rollout_validation" => {
            rollout.present
                && rollout_summary_version == Some(UDP_ROLLOUT_VALIDATION_SUMMARY_VERSION)
                && rollout_passed.unwrap_or(false)
                && rollout_summary
                    .map(|summary| summary.surface_count_total > 0)
                    .unwrap_or(false)
                && rollout_summary
                    .map(|summary| summary.cli_surface_consistency_passed)
                    .unwrap_or(false)
                && rollout_summary
                    .map(|summary| summary.startup_contract_validation_passed)
                    .unwrap_or(false)
                && rollout_summary
                    .map(|summary| summary.negotiated_limit_validation_passed)
                    .unwrap_or(false)
                && rollout_summary
                    .map(|summary| summary.selected_datagram_lifecycle_passed)
                    .unwrap_or(false)
                && policy_disabled_fallback_round_trip_stable.unwrap_or(false)
                && rollout_summary
                    .map(|summary| summary.sticky_selection_surface_passed)
                    .unwrap_or(false)
                && rollout_summary
                    .map(|summary| summary.degradation_surface_passed)
                    .unwrap_or(false)
                && rollout_summary
                    .and_then(|summary| summary.rollout_surface_passed)
                    .unwrap_or(false)
                && rollout_summary
                    .map(|summary| summary.longer_impairment_recovery_stable)
                    .unwrap_or(false)
                && rollout_summary
                    .map(|summary| summary.prolonged_repeated_impairment_stable)
                    .unwrap_or(false)
                && rollout_summary
                    .map(|summary| summary.shutdown_sequence_stable)
                    .unwrap_or(false)
                && queue_guard_headroom_passed.unwrap_or(false)
        }
        "active_fuzz" => {
            active_fuzz.present
                && active_fuzz_summary_version == Some(UDP_ACTIVE_FUZZ_SUMMARY_VERSION)
                && active_fuzz_passed.unwrap_or(false)
        }
        other => panic!("unsupported required summary label {other}"),
    };
    let required_input_count = required_summaries.len();
    let required_input_present_count = required_summaries
        .iter()
        .filter(|label| required_input_present(label))
        .count();
    let required_input_passed_count = required_summaries
        .iter()
        .filter(|label| required_input_passed(label))
        .count();
    let all_required_summaries_passed = required_input_passed_count == required_input_count;

    if smoke.present && !smoke_passed.unwrap_or(false) {
        push_reason(
            &mut blocking_reasons,
            &mut blocking_reason_details,
            "summary_result_failed",
            "smoke_summary_failed",
            "summary_result",
            "smoke",
        );
    }
    if perf.present && !perf_passed.unwrap_or(false) {
        push_reason(
            &mut blocking_reasons,
            &mut blocking_reason_details,
            "summary_result_failed",
            "perf_summary_failed",
            "summary_result",
            "perf",
        );
    }
    if interop.present && !interop_passed.unwrap_or(false) {
        push_reason(
            &mut blocking_reasons,
            &mut blocking_reason_details,
            "summary_result_failed",
            "interop_summary_failed",
            "summary_result",
            "interop",
        );
    }
    if interop.present
        && interop_summary_version == Some(UDP_INTEROP_LAB_SUMMARY_VERSION)
        && !interop_contract_valid
    {
        push_reason(
            &mut blocking_reasons,
            &mut blocking_reason_details,
            "summary_contract_invalid",
            "interop_summary_contract_invalid",
            "summary_contract",
            "interop",
        );
    }
    if interop.present
        && interop_summary_version == Some(UDP_INTEROP_LAB_SUMMARY_VERSION)
        && interop_required_no_silent_fallback_profile_set
            != expected_required_no_silent_fallback_profile_set
    {
        push_reason(
            &mut blocking_reasons,
            &mut blocking_reason_details,
            "interop_required_no_silent_fallback_profile_set_mismatch",
            "interop_required_no_silent_fallback_profile_set_mismatch",
            "summary_contract",
            "interop",
        );
    }
    let policy_disabled_fallback_surface_passed = interop
        .summary
        .as_ref()
        .and_then(|summary| summary.policy_disabled_fallback_surface_passed)
        .or_else(|| {
            rollout_summary.and_then(|summary| summary.policy_disabled_fallback_surface_passed)
        });
    if policy_disabled_fallback_surface_passed == Some(false) {
        push_reason(
            &mut blocking_reasons,
            &mut blocking_reason_details,
            "policy_disabled_fallback_surface_failed",
            "policy_disabled_fallback_surface_failed",
            "interop",
            "interop",
        );
    }
    if udp_blocked_fallback_surface_passed == Some(false) {
        push_reason(
            &mut blocking_reasons,
            &mut blocking_reason_details,
            "udp_blocked_fallback_surface_failed",
            "udp_blocked_fallback_surface_failed",
            "transport",
            "interop",
        );
    }
    if policy_disabled_fallback_round_trip_stable == Some(false) {
        push_reason(
            &mut blocking_reasons,
            &mut blocking_reason_details,
            "policy_disabled_fallback_round_trip_surface_failed",
            "policy_disabled_fallback_round_trip_surface_failed",
            "transport",
            "rollout_validation",
        );
    }
    if interop_summary.map(|summary| summary.queue_pressure_surface_passed) == Some(false) {
        push_reason(
            &mut blocking_reasons,
            &mut blocking_reason_details,
            "queue_pressure_surface_failed",
            "queue_pressure_surface_failed",
            "queue_guard",
            "interop",
        );
    }
    if interop_summary.map(|summary| summary.transport_fallback_integrity_surface_passed)
        == Some(false)
    {
        push_reason(
            &mut blocking_reasons,
            &mut blocking_reason_details,
            "transport_fallback_integrity_surface_failed",
            "interop_transport_fallback_integrity_surface_failed",
            "transport",
            "interop",
        );
    }
    if rollout.present && !rollout_passed.unwrap_or(false) {
        push_reason(
            &mut blocking_reasons,
            &mut blocking_reason_details,
            "summary_result_failed",
            "rollout_validation_summary_failed",
            "summary_result",
            "rollout_validation",
        );
    }
    if profile.active_fuzz_required() && active_fuzz.present && !active_fuzz_passed.unwrap_or(false)
    {
        push_reason(
            &mut blocking_reasons,
            &mut blocking_reason_details,
            "summary_result_failed",
            "active_fuzz_summary_failed",
            "summary_result",
            "active_fuzz",
        );
    }
    if rollout_summary.map(|summary| summary.selected_datagram_lifecycle_passed) == Some(false) {
        push_reason(
            &mut blocking_reasons,
            &mut blocking_reason_details,
            "selected_datagram_lifecycle_failed",
            "selected_datagram_lifecycle_failed",
            "surface",
            "rollout_validation",
        );
    }
    if rollout_summary.map(|summary| summary.sticky_selection_surface_passed) == Some(false) {
        push_reason(
            &mut blocking_reasons,
            &mut blocking_reason_details,
            "sticky_selection_surface_failed",
            "sticky_selection_surface_failed",
            "surface",
            "rollout_validation",
        );
    }
    if rollout_summary.and_then(|summary| summary.rollout_surface_passed) == Some(false) {
        push_reason(
            &mut blocking_reasons,
            &mut blocking_reason_details,
            "rollout_surface_failed",
            "rollout_surface_failed",
            "surface",
            "rollout_validation",
        );
    }
    if rollout_summary.map(|summary| summary.degradation_surface_passed) != Some(true) {
        push_reason(
            &mut blocking_reasons,
            &mut blocking_reason_details,
            "degradation_surface_failed",
            "degradation_surface_failed",
            "degradation",
            "rollout_validation",
        );
    }
    if transport_fallback_integrity_surface_passed == Some(false) {
        push_reason(
            &mut blocking_reasons,
            &mut blocking_reason_details,
            "transport_fallback_integrity_surface_failed",
            "transport_fallback_integrity_surface_failed",
            "transport",
            "rollout_validation",
        );
    }
    if rollout_summary.and_then(|summary| summary.queue_saturation_surface_passed) != Some(true) {
        push_reason(
            &mut blocking_reasons,
            &mut blocking_reason_details,
            "queue_saturation_surface_failed",
            "queue_saturation_surface_failed",
            "queue_guard",
            "rollout_validation",
        );
    }
    if rollout.present && queue_guard_headroom_passed.is_none() {
        push_reason(
            &mut blocking_reasons,
            &mut blocking_reason_details,
            "missing_queue_guard_headroom_surface",
            "missing_queue_guard_headroom_surface",
            "queue_guard",
            "rollout_validation",
        );
    }
    if queue_guard_headroom_band.as_deref() == Some("exhausted") {
        push_reason(
            &mut blocking_reasons,
            &mut blocking_reason_details,
            "queue_guard_headroom_exhausted",
            "queue_guard_headroom_exhausted",
            "queue_guard",
            "rollout_validation",
        );
    } else if queue_guard_headroom_passed == Some(false) {
        push_reason(
            &mut blocking_reasons,
            &mut blocking_reason_details,
            "queue_guard_headroom_failed",
            "queue_guard_headroom_failed",
            "queue_guard",
            "rollout_validation",
        );
    }
    if rollout_summary.map(|summary| summary.cli_surface_consistency_passed) != Some(true) {
        push_reason(
            &mut blocking_reasons,
            &mut blocking_reason_details,
            "cli_surface_consistency_failed",
            "cli_surface_consistency_failed",
            "validation",
            "rollout_validation",
        );
    }
    if rollout_summary.map(|summary| summary.startup_contract_validation_passed) != Some(true) {
        push_reason(
            &mut blocking_reasons,
            &mut blocking_reason_details,
            "startup_contract_validation_failed",
            "startup_contract_validation_failed",
            "validation",
            "rollout_validation",
        );
    }
    if rollout_summary.map(|summary| summary.negotiated_limit_validation_passed) != Some(true) {
        push_reason(
            &mut blocking_reasons,
            &mut blocking_reason_details,
            "negotiated_limit_validation_failed",
            "negotiated_limit_validation_failed",
            "validation",
            "rollout_validation",
        );
    }
    if rollout_summary.map(|summary| summary.longer_impairment_recovery_stable) != Some(true) {
        push_reason(
            &mut blocking_reasons,
            &mut blocking_reason_details,
            "longer_impairment_recovery_stable_failed",
            "longer_impairment_recovery_stable_failed",
            "degradation",
            "rollout_validation",
        );
    }
    if rollout_summary.map(|summary| summary.prolonged_repeated_impairment_stable) != Some(true) {
        push_reason(
            &mut blocking_reasons,
            &mut blocking_reason_details,
            "prolonged_repeated_impairment_stable_failed",
            "prolonged_repeated_impairment_stable_failed",
            "degradation",
            "rollout_validation",
        );
    }
    if rollout_summary.map(|summary| summary.shutdown_sequence_stable) != Some(true) {
        push_reason(
            &mut blocking_reasons,
            &mut blocking_reason_details,
            "shutdown_sequence_stable_failed",
            "shutdown_sequence_stable_failed",
            "degradation",
            "rollout_validation",
        );
    }

    let advisory_reasons = Vec::new();
    let queue_guard_tight_hold_count =
        usize::from(queue_guard_headroom_band.as_deref() == Some("tight"));
    if queue_guard_tight_hold_count > 0 {
        push_reason(
            &mut blocking_reasons,
            &mut blocking_reason_details,
            "queue_guard_headroom_tight",
            "queue_guard_headroom_tight",
            "queue_guard",
            "rollout_validation",
        );
    }

    let evidence_state =
        if all_required_summaries_present && all_required_summary_versions_supported {
            "complete"
        } else {
            "incomplete"
        };
    let gate_state = if !all_required_summaries_passed || !blocking_reasons.is_empty() {
        "blocked"
    } else {
        "passed"
    };
    let verdict = if all_required_summaries_present
        && all_required_summaries_passed
        && blocking_reasons.is_empty()
    {
        "ready"
    } else {
        "hold"
    };
    let all_required_inputs_passed = all_required_summaries_passed;
    let mut blocking_reason_key_counts = std::collections::BTreeMap::new();
    let mut blocking_reason_family_counts = std::collections::BTreeMap::new();
    for detail in &blocking_reason_details {
        *blocking_reason_key_counts
            .entry(detail.reason_key.clone())
            .or_insert(0) += 1;
        *blocking_reason_family_counts
            .entry(detail.family.to_owned())
            .or_insert(0) += 1;
    }
    let mut blocking_reason_keys = blocking_reason_key_counts
        .keys()
        .cloned()
        .collect::<Vec<_>>();
    blocking_reason_keys.sort();
    let mut blocking_reason_families = blocking_reason_family_counts
        .keys()
        .cloned()
        .collect::<Vec<_>>();
    blocking_reason_families.sort();
    let degradation_hold_subjects =
        if rollout_summary.map(|summary| summary.degradation_surface_passed) == Some(false)
            || queue_guard_tight_hold_count > 0
        {
            vec![host_label.clone()]
        } else {
            Vec::new()
        };
    let degradation_hold_count = degradation_hold_subjects.len();
    let required_input_missing_count = missing_required_input_count;
    let required_input_failed_count =
        required_input_count.saturating_sub(required_input_passed_count);
    let required_input_unready_count =
        required_input_failed_count.saturating_sub(required_input_missing_count);
    let blocking_reason_key_count = blocking_reason_key_counts.len();
    let blocking_reason_family_count = blocking_reason_family_counts.len();
    let summary_contract_invalid_count = blocking_reason_details
        .iter()
        .filter(|detail| detail.family == "summary_contract")
        .count();
    let (gate_state_reason, gate_state_reason_family) = summarize_rollout_gate_state(
        required_input_missing_count,
        summary_contract_invalid_count,
        required_input_unready_count,
        degradation_hold_count,
        blocking_reasons.len(),
    );

    UdpRolloutComparisonSummary {
        summary_version: UDP_ROLLOUT_COMPARISON_SUMMARY_VERSION,
        comparison_schema: UDP_ROLLOUT_OPERATOR_VERDICT_SCHEMA,
        comparison_schema_version: UDP_ROLLOUT_OPERATOR_VERDICT_SCHEMA_VERSION,
        verdict_family: UDP_ROLLOUT_OPERATOR_VERDICT_FAMILY,
        decision_scope: UDP_ROLLOUT_DECISION_SCOPE_HOST,
        decision_label,
        profile: profile.as_str(),
        host_label,
        verdict,
        evidence_state,
        gate_state,
        gate_state_reason,
        gate_state_reason_family,
        active_fuzz_required: profile.active_fuzz_required(),
        required_inputs,
        considered_inputs,
        missing_required_inputs,
        missing_required_input_count,
        required_input_count,
        required_input_missing_count,
        required_input_failed_count,
        required_input_unready_count,
        required_input_present_count,
        required_input_passed_count,
        required_summaries,
        considered_summaries,
        all_required_inputs_present: all_required_summaries_present,
        all_required_inputs_passed,
        all_required_summaries_present,
        all_required_summaries_passed,
        blocking_reason_count: blocking_reasons.len(),
        blocking_reason_key_count,
        blocking_reason_family_count,
        blocking_reason_key_counts,
        blocking_reason_family_counts,
        advisory_reason_count: advisory_reasons.len(),
        cli_surface_consistency_passed: rollout_summary
            .map(|summary| summary.cli_surface_consistency_passed),
        startup_contract_validation_passed: rollout_summary
            .map(|summary| summary.startup_contract_validation_passed),
        negotiated_limit_validation_passed: rollout_summary
            .map(|summary| summary.negotiated_limit_validation_passed),
        selected_datagram_lifecycle_passed: rollout_summary
            .map(|summary| summary.selected_datagram_lifecycle_passed),
        queue_saturation_surface_passed: rollout_summary
            .and_then(|summary| summary.queue_saturation_surface_passed),
        queue_saturation_worst_case: rollout_summary
            .and_then(|summary| summary.queue_saturation_worst_case.as_ref().cloned()),
        queue_saturation_worst_utilization_pct: rollout_summary
            .and_then(|summary| summary.queue_saturation_worst_utilization_pct),
        queue_guard_headroom_passed,
        queue_guard_headroom_band,
        queue_guard_headroom_missing_count,
        queue_guard_rejection_path_passed: rollout_summary
            .and_then(|summary| summary.queue_guard_rejection_path_passed),
        queue_guard_recovery_path_passed: rollout_summary
            .and_then(|summary| summary.queue_guard_recovery_path_passed),
        queue_guard_burst_path_passed: rollout_summary
            .and_then(|summary| summary.queue_guard_burst_path_passed),
        queue_guard_limiting_path: rollout_summary
            .and_then(|summary| summary.queue_guard_limiting_path.as_ref().cloned()),
        queue_guard_tight_hold_count,
        queue_pressure_hold_count,
        sticky_selection_surface_passed: rollout_summary
            .map(|summary| summary.sticky_selection_surface_passed),
        degradation_surface_passed: rollout_summary
            .map(|summary| summary.degradation_surface_passed),
        degradation_hold_count,
        degradation_hold_subjects,
        transport_fallback_integrity_surface_passed,
        rollout_surface_passed: rollout_summary.and_then(|summary| summary.rollout_surface_passed),
        surface_count_total: rollout_summary.map(|summary| summary.surface_count_total),
        surface_count_passed: rollout_summary.map(|summary| summary.surface_count_passed),
        surface_count_failed: rollout_summary.map(|summary| summary.surface_count_failed),
        failed_surface_keys: rollout_summary
            .map(|summary| summary.failed_surface_keys.clone())
            .unwrap_or_default(),
        repeated_queue_pressure_sticky: rollout_summary
            .map(|summary| summary.repeated_queue_pressure_sticky),
        prolonged_impairment_no_silent_fallback: rollout_summary
            .map(|summary| summary.prolonged_impairment_no_silent_fallback),
        prolonged_repeated_impairment_stable: rollout_summary
            .map(|summary| summary.prolonged_repeated_impairment_stable),
        longer_impairment_recovery_stable: rollout_summary
            .map(|summary| summary.longer_impairment_recovery_stable),
        shutdown_sequence_stable: rollout_summary.map(|summary| summary.shutdown_sequence_stable),
        post_close_rejection_stable: rollout_summary
            .map(|summary| summary.post_close_rejection_stable),
        clean_shutdown_stable: rollout_summary.map(|summary| summary.clean_shutdown_stable),
        interop_profile_count: interop
            .summary
            .as_ref()
            .map(|summary| summary.profile_count),
        interop_profile_slugs: interop
            .summary
            .as_ref()
            .map(|summary| summary.profile_slugs.clone())
            .unwrap_or_default(),
        interop_failed_profile_slugs: interop
            .summary
            .as_ref()
            .map(|summary| summary.failed_profile_slugs.clone())
            .unwrap_or_default(),
        interop_required_no_silent_fallback_profile_slugs,
        interop_profile_contract_passed,
        udp_blocked_fallback_surface_passed,
        explicit_fallback_profile_count: interop
            .summary
            .as_ref()
            .map(|summary| summary.explicit_fallback_profile_count)
            .unwrap_or_default(),
        policy_disabled_fallback_surface_passed,
        policy_disabled_fallback_round_trip_stable,
        interop_failed_profile_count: interop
            .summary
            .as_ref()
            .map(|summary| summary.failed_profile_slugs.len())
            .unwrap_or_default(),
        active_fuzz_failed_targets,
        smoke: SummaryPresence {
            path: smoke.path,
            present: smoke.present,
            passed: smoke_passed,
        },
        perf: SummaryPresence {
            path: perf.path,
            present: perf.present,
            passed: perf_passed,
        },
        interop: SummaryPresence {
            path: interop.path,
            present: interop.present,
            passed: interop_passed,
        },
        rollout_validation: SummaryPresence {
            path: rollout.path,
            present: rollout.present,
            passed: rollout_passed,
        },
        active_fuzz: SummaryPresence {
            path: active_fuzz.path,
            present: active_fuzz.present,
            passed: active_fuzz_passed,
        },
        blocking_reasons,
        blocking_reason_keys,
        blocking_reason_families,
        blocking_reason_details,
        advisory_reasons,
    }
}

fn required_summaries_for_profile(profile: ComparisonProfile) -> Vec<String> {
    let mut required = vec![
        "smoke".to_owned(),
        "perf".to_owned(),
        "interop".to_owned(),
        "rollout_validation".to_owned(),
    ];
    if profile.active_fuzz_required() {
        required.push("active_fuzz".to_owned());
    }
    required
}

fn summary_source(label: &str) -> &'static str {
    match label {
        "smoke" => "smoke",
        "perf" => "perf",
        "interop" => "interop",
        "rollout_validation" => "rollout_validation",
        "active_fuzz" => "active_fuzz",
        other => panic!("unsupported summary source {other}"),
    }
}

fn expected_summary_version(label: &str) -> u8 {
    match label {
        "smoke" => UDP_FUZZ_SMOKE_SUMMARY_VERSION,
        "perf" => UDP_PERF_GATE_SUMMARY_VERSION,
        "interop" => UDP_INTEROP_LAB_SUMMARY_VERSION,
        "rollout_validation" => UDP_ROLLOUT_VALIDATION_SUMMARY_VERSION,
        "active_fuzz" => UDP_ACTIVE_FUZZ_SUMMARY_VERSION,
        other => panic!("unsupported summary version label {other}"),
    }
}

fn push_reason(
    reasons: &mut Vec<String>,
    details: &mut Vec<ReasonDetail>,
    reason_key: &str,
    code: impl Into<String>,
    family: &'static str,
    source: &'static str,
) {
    let code = code.into();
    reasons.push(code.clone());
    details.push(ReasonDetail {
        code,
        reason_key: reason_key.to_owned(),
        family,
        source,
    });
}

fn load_summary<T: for<'de> Deserialize<'de>>(
    env_key: &str,
) -> Result<LoadedSummary<T>, Box<dyn std::error::Error>> {
    let path = env::var_os(env_key)
        .map(PathBuf::from)
        .unwrap_or_else(|| default_input_path(env_key));
    if !path.exists() {
        return Ok(LoadedSummary {
            path: Some(path.display().to_string()),
            present: false,
            summary: None,
        });
    }

    Ok(LoadedSummary {
        path: Some(path.display().to_string()),
        present: true,
        summary: Some(serde_json::from_slice(&fs::read(&path)?)?),
    })
}

fn parse_args(
    arguments: impl IntoIterator<Item = String>,
) -> Result<ComparisonArgs, Box<dyn std::error::Error>> {
    let mut parsed = ComparisonArgs::default();
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
            "--host-label" => {
                parsed.host_label = Some(iter.next().ok_or("--host-label requires a label value")?);
            }
            "--profile" => {
                let value = iter
                    .next()
                    .ok_or("--profile requires either readiness or staged_rollout")?;
                parsed.profile = Some(parse_profile(&value)?);
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

fn parse_profile(value: &str) -> Result<ComparisonProfile, Box<dyn std::error::Error>> {
    match value {
        "readiness" => Ok(ComparisonProfile::Readiness),
        "staged_rollout" => Ok(ComparisonProfile::StagedRollout),
        other => Err(format!("unsupported --profile value {other}").into()),
    }
}

fn print_usage() {
    eprintln!(
        "Usage: cargo run -p ns-testkit --example udp_rollout_compare -- [--format text|json] [--summary-path <path>] [--host-label <label>] [--profile readiness|staged_rollout]"
    );
}

fn interop_summary_contract_valid(summary: &UdpInteropLabSummary) -> bool {
    let expected_profiles = udp_wan_lab_profile_slugs()
        .into_iter()
        .map(str::to_owned)
        .collect::<BTreeSet<_>>();
    let expected_required_profiles = udp_wan_lab_required_no_silent_fallback_profile_slugs()
        .into_iter()
        .map(str::to_owned)
        .collect::<BTreeSet<_>>();
    let actual_profiles = summary
        .profile_slugs
        .iter()
        .cloned()
        .collect::<BTreeSet<_>>();
    let actual_required_profiles = summary
        .required_no_silent_fallback_profile_slugs
        .iter()
        .cloned()
        .collect::<BTreeSet<_>>();
    let failed_profiles = summary
        .failed_profile_slugs
        .iter()
        .cloned()
        .collect::<BTreeSet<_>>();
    let failed_required_count = summary
        .failed_profile_slugs
        .iter()
        .filter(|slug| expected_required_profiles.contains(*slug))
        .count();
    let required_profiles_passed = summary.required_no_silent_fallback_passed_count
        == expected_required_profiles
            .len()
            .saturating_sub(failed_required_count);
    let udp_blocked_fallback_failed = failed_profiles.contains("udp-blocked-fallback");
    let queue_pressure_failed = failed_profiles.contains("queue-pressure-sticky");
    let policy_disabled_fallback_failed = failed_profiles.contains("policy-disabled-fallback");
    let transport_fallback_integrity_expected = summary.queue_pressure_surface_passed
        && summary.udp_blocked_fallback_surface_passed == Some(true)
        && summary.policy_disabled_fallback_surface_passed == Some(true)
        && required_profiles_passed;

    summary.profile_count == expected_profiles.len()
        && actual_profiles == expected_profiles
        && failed_profiles.is_subset(&actual_profiles)
        && summary.all_passed == failed_profiles.is_empty()
        && summary.required_no_silent_fallback_profile_count == expected_required_profiles.len()
        && actual_required_profiles == expected_required_profiles
        && summary.required_no_silent_fallback_passed_count
            <= summary.required_no_silent_fallback_profile_count
        && required_profiles_passed
        && summary.explicit_fallback_profile_count
            == summary
                .profile_count
                .saturating_sub(summary.required_no_silent_fallback_profile_count)
        && summary.udp_blocked_fallback_surface_passed == Some(!udp_blocked_fallback_failed)
        && summary.queue_pressure_surface_passed != queue_pressure_failed
        && summary.policy_disabled_fallback_surface_passed == Some(!policy_disabled_fallback_failed)
        && summary.transport_fallback_integrity_surface_passed
            == transport_fallback_integrity_expected
}

fn default_summary_path() -> PathBuf {
    repo_root()
        .join("target")
        .join("northstar")
        .join("udp-rollout-comparison-summary.json")
}

fn default_input_path(env_key: &str) -> PathBuf {
    let file_name = match env_key {
        "NORTHSTAR_UDP_FUZZ_SMOKE_SUMMARY_PATH" => "udp-fuzz-smoke-summary.json",
        "NORTHSTAR_UDP_PERF_SUMMARY_PATH" => "udp-perf-gate-summary.json",
        "NORTHSTAR_UDP_INTEROP_SUMMARY_PATH" => "udp-interop-lab-summary.json",
        "NORTHSTAR_UDP_ROLLOUT_VALIDATION_SUMMARY_PATH" => "udp-rollout-validation-summary.json",
        "NORTHSTAR_UDP_ACTIVE_FUZZ_SUMMARY_PATH" => "udp-active-fuzz-summary.json",
        other => panic!("unsupported summary env key {other}"),
    };
    repo_root().join("target").join("northstar").join(file_name)
}

#[cfg(test)]
mod tests {
    use super::{
        ComparisonProfile, LoadedSummary, UDP_INTEROP_LAB_SUMMARY_VERSION,
        UDP_ROLLOUT_COMPARISON_SUMMARY_VERSION, UDP_ROLLOUT_OPERATOR_VERDICT_SCHEMA_VERSION,
        UDP_ROLLOUT_VALIDATION_SUMMARY_VERSION, UdpFuzzSmokeSummary, UdpInteropLabSummary,
        UdpPerfGateSummary, UdpRolloutValidationSummary, build_comparison_summary,
    };
    use ns_testkit::{
        udp_wan_lab_profile_slugs, udp_wan_lab_required_no_silent_fallback_profile_slugs,
    };

    fn loaded<T>(summary: T) -> LoadedSummary<T> {
        LoadedSummary {
            path: Some("target/northstar/test-summary.json".to_owned()),
            present: true,
            summary: Some(summary),
        }
    }

    fn rollout_summary() -> UdpRolloutValidationSummary {
        UdpRolloutValidationSummary {
            summary_version: Some(UDP_ROLLOUT_VALIDATION_SUMMARY_VERSION),
            all_passed: true,
            cli_surface_consistency_passed: true,
            startup_contract_validation_passed: true,
            negotiated_limit_validation_passed: true,
            selected_datagram_lifecycle_passed: true,
            udp_blocked_fallback_surface_passed: true,
            repeated_queue_pressure_sticky: true,
            prolonged_impairment_no_silent_fallback: true,
            prolonged_repeated_impairment_stable: true,
            longer_impairment_recovery_stable: true,
            shutdown_sequence_stable: true,
            post_close_rejection_stable: true,
            clean_shutdown_stable: true,
            policy_disabled_fallback_surface_passed: Some(true),
            policy_disabled_fallback_round_trip_stable: true,
            queue_saturation_surface_passed: Some(true),
            queue_saturation_worst_case: Some(
                "H3DatagramSocket.repeated_queue_recovery_send".to_owned(),
            ),
            queue_saturation_worst_utilization_pct: Some(20),
            queue_guard_headroom_passed: Some(true),
            queue_guard_headroom_band: Some("healthy".to_owned()),
            queue_guard_headroom_missing_count: 0,
            queue_guard_rejection_path_passed: Some(true),
            queue_guard_recovery_path_passed: Some(true),
            queue_guard_burst_path_passed: Some(true),
            queue_guard_limiting_path: Some("recovery".to_owned()),
            sticky_selection_surface_passed: true,
            degradation_surface_passed: true,
            transport_fallback_integrity_surface_passed: true,
            rollout_surface_passed: Some(true),
            surface_count_total: 19,
            surface_count_passed: 19,
            surface_count_failed: 0,
            failed_surface_keys: Vec::new(),
        }
    }

    fn interop_summary() -> UdpInteropLabSummary {
        let profile_slugs = udp_wan_lab_profile_slugs()
            .into_iter()
            .map(str::to_owned)
            .collect::<Vec<_>>();
        let required_profile_slugs = udp_wan_lab_required_no_silent_fallback_profile_slugs()
            .into_iter()
            .map(str::to_owned)
            .collect::<Vec<_>>();
        UdpInteropLabSummary {
            summary_version: Some(UDP_INTEROP_LAB_SUMMARY_VERSION),
            all_passed: true,
            profile_count: profile_slugs.len(),
            profile_slugs,
            failed_profile_slugs: Vec::new(),
            explicit_fallback_profile_count: 3,
            udp_blocked_fallback_surface_passed: Some(true),
            required_no_silent_fallback_profile_count: required_profile_slugs.len(),
            required_no_silent_fallback_passed_count: required_profile_slugs.len(),
            required_no_silent_fallback_profile_slugs: required_profile_slugs,
            queue_pressure_surface_passed: true,
            transport_fallback_integrity_surface_passed: true,
            policy_disabled_fallback_surface_passed: Some(true),
        }
    }

    #[test]
    fn readiness_profile_emits_ready_operator_verdict_schema() {
        let summary = build_comparison_summary(
            ComparisonProfile::Readiness,
            "windows-latest-rollout".to_owned(),
            loaded(UdpFuzzSmokeSummary {
                summary_version: Some(1),
                all_passed: true,
            }),
            loaded(UdpPerfGateSummary {
                summary_version: Some(1),
                all_passed: true,
            }),
            loaded(interop_summary()),
            loaded(rollout_summary()),
            LoadedSummary {
                path: Some("target/northstar/udp-active-fuzz-summary.json".to_owned()),
                present: false,
                summary: None,
            },
        );

        assert_eq!(summary.profile, "readiness");
        assert_eq!(
            summary.summary_version,
            UDP_ROLLOUT_COMPARISON_SUMMARY_VERSION
        );
        assert_eq!(summary.verdict, "ready");
        assert_eq!(summary.evidence_state, "complete");
        assert_eq!(summary.gate_state, "passed");
        assert_eq!(summary.comparison_schema, "udp_rollout_operator_verdict");
        assert_eq!(
            summary.comparison_schema_version,
            UDP_ROLLOUT_OPERATOR_VERDICT_SCHEMA_VERSION
        );
        assert_eq!(summary.verdict_family, "udp_rollout_operator_decision");
        assert_eq!(summary.decision_scope, "host");
        assert_eq!(summary.decision_label, "windows-latest-rollout");
        assert_eq!(summary.required_summaries.len(), 4);
        assert_eq!(summary.required_inputs.len(), 4);
        assert_eq!(summary.required_input_count, 4);
        assert_eq!(summary.required_input_missing_count, 0);
        assert_eq!(summary.required_input_failed_count, 0);
        assert_eq!(summary.required_input_unready_count, 0);
        assert_eq!(summary.required_input_present_count, 4);
        assert_eq!(summary.required_input_passed_count, 4);
        assert!(summary.missing_required_inputs.is_empty());
        assert_eq!(summary.missing_required_input_count, 0);
        assert!(summary.all_required_inputs_present);
        assert!(summary.all_required_inputs_passed);
        assert_eq!(summary.gate_state_reason, "all_required_inputs_passed");
        assert_eq!(summary.gate_state_reason_family, "ready");
        assert_eq!(summary.blocking_reason_count, 0);
        assert_eq!(summary.blocking_reason_key_count, 0);
        assert_eq!(summary.blocking_reason_family_count, 0);
        assert_eq!(summary.advisory_reason_count, 0);
        assert!(summary.blocking_reason_key_counts.is_empty());
        assert!(summary.blocking_reason_family_counts.is_empty());
        assert_eq!(
            summary.queue_guard_limiting_path.as_deref(),
            Some("recovery")
        );
        assert_eq!(summary.degradation_surface_passed, Some(true));
        assert_eq!(summary.degradation_hold_count, 0);
        assert!(summary.degradation_hold_subjects.is_empty());
        assert_eq!(summary.surface_count_total, Some(19));
        assert_eq!(summary.surface_count_failed, Some(0));
        assert_eq!(summary.queue_guard_tight_hold_count, 0);
        assert_eq!(summary.queue_pressure_hold_count, 0);
        assert!(summary.failed_surface_keys.is_empty());
        assert_eq!(summary.blocking_reasons.len(), 0);
        assert!(summary.blocking_reason_keys.is_empty());
        assert!(summary.blocking_reason_families.is_empty());
        assert_eq!(summary.selected_datagram_lifecycle_passed, Some(true));
        assert_eq!(summary.prolonged_repeated_impairment_stable, Some(true));
        assert_eq!(summary.udp_blocked_fallback_surface_passed, Some(true));
        assert_eq!(summary.explicit_fallback_profile_count, 3);
        assert_eq!(summary.policy_disabled_fallback_surface_passed, Some(true));
        assert_eq!(
            summary.policy_disabled_fallback_round_trip_stable,
            Some(true)
        );
        assert_eq!(summary.interop_failed_profile_count, 0);
        assert_eq!(
            summary.transport_fallback_integrity_surface_passed,
            Some(true)
        );
        assert_eq!(summary.interop_profile_slugs.len(), 14);
        assert_eq!(
            summary
                .interop_required_no_silent_fallback_profile_slugs
                .len(),
            11
        );
        assert!(summary.interop_failed_profile_slugs.is_empty());
    }

    #[test]
    fn staged_rollout_profile_fails_closed_without_active_fuzz_evidence() {
        let summary = build_comparison_summary(
            ComparisonProfile::StagedRollout,
            "ubuntu-latest-staged".to_owned(),
            loaded(UdpFuzzSmokeSummary {
                summary_version: Some(1),
                all_passed: true,
            }),
            loaded(UdpPerfGateSummary {
                summary_version: Some(1),
                all_passed: true,
            }),
            loaded(interop_summary()),
            loaded(rollout_summary()),
            LoadedSummary {
                path: Some("target/northstar/udp-active-fuzz-summary.json".to_owned()),
                present: false,
                summary: None,
            },
        );

        assert_eq!(summary.profile, "staged_rollout");
        assert_eq!(summary.verdict, "hold");
        assert_eq!(summary.evidence_state, "incomplete");
        assert_eq!(summary.gate_state, "blocked");
        assert!(summary.active_fuzz_required);
        assert!(!summary.all_required_inputs_present);
        assert!(!summary.all_required_inputs_passed);
        assert!(
            summary
                .blocking_reasons
                .iter()
                .any(|reason| reason == "missing_active_fuzz_summary")
        );
        assert!(summary.blocking_reason_details.iter().any(|detail| {
            detail.code == "missing_active_fuzz_summary"
                && detail.reason_key == "summary_presence_missing"
        }));
    }

    #[test]
    fn readiness_profile_holds_on_stale_smoke_summary_version() {
        let summary = build_comparison_summary(
            ComparisonProfile::Readiness,
            "ubuntu-latest-rollout".to_owned(),
            loaded(UdpFuzzSmokeSummary {
                summary_version: Some(0),
                all_passed: true,
            }),
            loaded(UdpPerfGateSummary {
                summary_version: Some(1),
                all_passed: true,
            }),
            loaded(interop_summary()),
            loaded(rollout_summary()),
            LoadedSummary {
                path: Some("target/northstar/udp-active-fuzz-summary.json".to_owned()),
                present: false,
                summary: None,
            },
        );

        assert_eq!(summary.verdict, "hold");
        assert_eq!(summary.evidence_state, "incomplete");
        assert!(
            summary
                .blocking_reasons
                .iter()
                .any(|reason| reason == "smoke_summary_version_unsupported")
        );
        assert_eq!(
            summary
                .blocking_reason_key_counts
                .get("summary_version_unsupported")
                .copied(),
            Some(1)
        );
        assert_eq!(summary.required_input_present_count, 4);
        assert_eq!(summary.required_input_passed_count, 3);
    }

    #[test]
    fn readiness_profile_holds_when_longer_impairment_recovery_is_not_stable() {
        let mut rollout = rollout_summary();
        rollout.longer_impairment_recovery_stable = false;
        rollout.prolonged_repeated_impairment_stable = false;
        rollout.degradation_surface_passed = false;
        rollout.transport_fallback_integrity_surface_passed = false;
        rollout.rollout_surface_passed = Some(false);
        rollout.failed_surface_keys = vec![
            "prolonged_repeated_impairment_stable".to_owned(),
            "longer_impairment_recovery_stable".to_owned(),
            "degradation_surface_passed".to_owned(),
            "transport_fallback_integrity_surface_passed".to_owned(),
            "rollout_surface_passed".to_owned(),
        ];
        rollout.surface_count_failed = rollout.failed_surface_keys.len();
        rollout.surface_count_passed = rollout
            .surface_count_total
            .saturating_sub(rollout.surface_count_failed);

        let summary = build_comparison_summary(
            ComparisonProfile::Readiness,
            "macos-latest-rollout".to_owned(),
            loaded(UdpFuzzSmokeSummary {
                summary_version: Some(1),
                all_passed: true,
            }),
            loaded(UdpPerfGateSummary {
                summary_version: Some(1),
                all_passed: true,
            }),
            loaded(interop_summary()),
            loaded(rollout),
            LoadedSummary {
                path: Some("target/northstar/udp-active-fuzz-summary.json".to_owned()),
                present: false,
                summary: None,
            },
        );

        assert_eq!(summary.verdict, "hold");
        assert!(
            summary
                .blocking_reasons
                .iter()
                .any(|reason| reason == "longer_impairment_recovery_stable_failed")
        );
        assert!(
            summary
                .blocking_reasons
                .iter()
                .any(|reason| reason == "prolonged_repeated_impairment_stable_failed")
        );
        assert_eq!(summary.required_input_passed_count, 3);
    }

    #[test]
    fn readiness_profile_holds_when_transport_fallback_integrity_surface_fails() {
        let mut rollout = rollout_summary();
        rollout.transport_fallback_integrity_surface_passed = false;
        rollout.rollout_surface_passed = Some(false);
        rollout.failed_surface_keys = vec![
            "transport_fallback_integrity_surface_passed".to_owned(),
            "rollout_surface_passed".to_owned(),
        ];
        rollout.surface_count_failed = rollout.failed_surface_keys.len();
        rollout.surface_count_passed = rollout
            .surface_count_total
            .saturating_sub(rollout.surface_count_failed);

        let summary = build_comparison_summary(
            ComparisonProfile::Readiness,
            "linux-rollout".to_owned(),
            loaded(UdpFuzzSmokeSummary {
                summary_version: Some(1),
                all_passed: true,
            }),
            loaded(UdpPerfGateSummary {
                summary_version: Some(1),
                all_passed: true,
            }),
            loaded(interop_summary()),
            loaded(rollout),
            LoadedSummary {
                path: Some("target/northstar/udp-active-fuzz-summary.json".to_owned()),
                present: false,
                summary: None,
            },
        );

        assert_eq!(summary.verdict, "hold");
        assert_eq!(
            summary.transport_fallback_integrity_surface_passed,
            Some(false)
        );
        assert!(
            summary
                .blocking_reasons
                .iter()
                .any(|reason| reason == "transport_fallback_integrity_surface_failed")
        );
    }

    #[test]
    fn readiness_profile_holds_when_udp_blocked_fallback_surface_drifts() {
        let summary = build_comparison_summary(
            ComparisonProfile::Readiness,
            "linux-rollout".to_owned(),
            loaded(UdpFuzzSmokeSummary {
                summary_version: Some(1),
                all_passed: true,
            }),
            loaded(UdpPerfGateSummary {
                summary_version: Some(1),
                all_passed: true,
            }),
            loaded(UdpInteropLabSummary {
                all_passed: false,
                failed_profile_slugs: vec!["udp-blocked-fallback".to_owned()],
                required_no_silent_fallback_passed_count:
                    udp_wan_lab_required_no_silent_fallback_profile_slugs().len(),
                udp_blocked_fallback_surface_passed: Some(false),
                transport_fallback_integrity_surface_passed: false,
                ..interop_summary()
            }),
            loaded(rollout_summary()),
            LoadedSummary {
                path: Some("target/northstar/udp-active-fuzz-summary.json".to_owned()),
                present: false,
                summary: None,
            },
        );

        assert_eq!(summary.verdict, "hold");
        assert_eq!(summary.gate_state, "blocked");
        assert_eq!(summary.required_input_failed_count, 1);
        assert_eq!(summary.required_input_unready_count, 1);
        assert_eq!(summary.gate_state_reason, "required_inputs_unready");
        assert_eq!(summary.gate_state_reason_family, "gating");
        assert_eq!(summary.udp_blocked_fallback_surface_passed, Some(false));
        assert!(
            summary
                .blocking_reasons
                .iter()
                .any(|reason| reason == "udp_blocked_fallback_surface_failed")
        );
    }

    #[test]
    fn readiness_profile_holds_when_policy_disabled_fallback_surface_fails() {
        let summary = build_comparison_summary(
            ComparisonProfile::Readiness,
            "windows-latest-rollout".to_owned(),
            loaded(UdpFuzzSmokeSummary {
                summary_version: Some(1),
                all_passed: true,
            }),
            loaded(UdpPerfGateSummary {
                summary_version: Some(1),
                all_passed: true,
            }),
            loaded(UdpInteropLabSummary {
                all_passed: false,
                failed_profile_slugs: vec!["policy-disabled-fallback".to_owned()],
                required_no_silent_fallback_passed_count:
                    udp_wan_lab_required_no_silent_fallback_profile_slugs().len(),
                transport_fallback_integrity_surface_passed: false,
                policy_disabled_fallback_surface_passed: Some(false),
                ..interop_summary()
            }),
            loaded(rollout_summary()),
            LoadedSummary {
                path: Some("target/northstar/udp-active-fuzz-summary.json".to_owned()),
                present: false,
                summary: None,
            },
        );

        assert_eq!(summary.verdict, "hold");
        assert_eq!(summary.gate_state, "blocked");
        assert_eq!(summary.required_input_failed_count, 1);
        assert_eq!(summary.required_input_unready_count, 1);
        assert_eq!(summary.gate_state_reason, "required_inputs_unready");
        assert_eq!(summary.gate_state_reason_family, "gating");
        assert_eq!(summary.policy_disabled_fallback_surface_passed, Some(false));
        assert_eq!(
            summary.interop_failed_profile_slugs,
            vec!["policy-disabled-fallback".to_owned()]
        );
        assert!(
            summary
                .blocking_reasons
                .iter()
                .any(|reason| reason == "policy_disabled_fallback_surface_failed")
        );
    }
}
