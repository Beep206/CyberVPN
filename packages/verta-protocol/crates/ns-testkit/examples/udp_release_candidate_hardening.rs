use ns_testkit::{
    UDP_INTEROP_PROFILE_CATALOG_SOURCE_LANE_COMPATIBLE_HOST,
    UDP_ROLLOUT_DECISION_SCOPE_RELEASE_CANDIDATE_CONSOLIDATION,
    UDP_ROLLOUT_DECISION_SCOPE_RELEASE_CANDIDATE_HARDENING, UDP_ROLLOUT_OPERATOR_VERDICT_FAMILY,
    UDP_ROLLOUT_OPERATOR_VERDICT_SCHEMA, UDP_ROLLOUT_OPERATOR_VERDICT_SCHEMA_VERSION,
    blocking_reason_accounting_consistent, prefer_verta_input_path, rollout_queue_hold_host_count,
    rollout_queue_hold_input_count, rollout_queue_hold_present, summarize_rollout_gate_state,
    udp_wan_lab_required_no_silent_fallback_profile_slugs, verta_output_path,
};
use serde::{Deserialize, Serialize};
use std::collections::{BTreeMap, BTreeSet};
use std::env;
use std::fs;
use std::path::{Path, PathBuf};

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
enum OutputFormat {
    Text,
    Json,
}

#[derive(Debug, Default)]
struct ReleaseCandidateHardeningArgs {
    format: Option<OutputFormat>,
    summary_path: Option<PathBuf>,
    release_candidate_consolidation: Option<PathBuf>,
    linux_validation: Option<PathBuf>,
    macos_validation: Option<PathBuf>,
    windows_validation: Option<PathBuf>,
}

const UDP_RELEASE_CANDIDATE_CONSOLIDATION_SUMMARY_VERSION: u8 = 2;
const UDP_ROLLOUT_VALIDATION_SUMMARY_VERSION: u8 = 19;
const UDP_RELEASE_CANDIDATE_HARDENING_SUMMARY_VERSION: u8 = 3;

#[derive(Debug, Deserialize)]
struct ReleaseCandidateConsolidationSummaryInput {
    #[serde(default)]
    summary_version: Option<u8>,
    comparison_schema: String,
    comparison_schema_version: u8,
    verdict_family: String,
    decision_scope: String,
    decision_label: String,
    profile: String,
    verdict: String,
    evidence_state: String,
    gate_state: String,
    gate_state_reason: String,
    gate_state_reason_family: String,
    active_fuzz_required: bool,
    #[serde(default)]
    required_inputs: Vec<String>,
    #[serde(default)]
    considered_inputs: Vec<String>,
    #[serde(default)]
    missing_required_inputs: Vec<String>,
    #[serde(default)]
    missing_required_input_count: usize,
    required_input_count: usize,
    #[serde(default)]
    required_input_missing_count: usize,
    #[serde(default)]
    required_input_failed_count: usize,
    #[serde(default)]
    required_input_unready_count: usize,
    required_input_present_count: usize,
    required_input_passed_count: usize,
    all_required_inputs_present: bool,
    all_required_inputs_passed: bool,
    blocking_reason_count: usize,
    #[serde(default)]
    blocking_reason_key_count: usize,
    #[serde(default)]
    blocking_reason_family_count: usize,
    #[serde(default)]
    blocking_reason_key_counts: BTreeMap<String, usize>,
    #[serde(default)]
    blocking_reason_family_counts: BTreeMap<String, usize>,
    #[serde(default)]
    degradation_hold_count: usize,
    #[serde(default)]
    degradation_hold_subjects: Vec<String>,
    #[serde(default)]
    queue_guard_headroom_band_counts: BTreeMap<String, usize>,
    #[serde(default)]
    queue_guard_headroom_missing_count: usize,
    #[serde(default)]
    queue_guard_tight_hold_count: usize,
    #[serde(default)]
    queue_pressure_hold_count: usize,
    #[serde(default)]
    queue_hold_input_count: usize,
    #[serde(default)]
    queue_hold_host_count: usize,
    #[serde(default)]
    queue_guard_limiting_path_counts: BTreeMap<String, usize>,
    #[serde(default)]
    interop_profile_contract_passed: bool,
    #[serde(default)]
    interop_profile_catalog_contract_passed: bool,
    #[serde(default)]
    interop_profile_catalog_schema_version: u8,
    #[serde(default)]
    interop_profile_catalog_host_labels: Vec<String>,
    #[serde(default)]
    interop_profile_catalog_source_lane: String,
    #[serde(default)]
    interop_required_no_silent_fallback_profile_slugs: Vec<String>,
    #[serde(default)]
    interop_failed_profile_slugs: Vec<String>,
    #[serde(default)]
    interop_failed_profile_count: usize,
    #[serde(default)]
    explicit_fallback_profile_count: usize,
    #[serde(default)]
    policy_disabled_fallback_surface_passed: Option<bool>,
    #[serde(default)]
    transport_fallback_integrity_surface_passed: Option<bool>,
    #[serde(default)]
    blocking_reasons: Vec<String>,
    #[serde(default)]
    blocking_reason_keys: Vec<String>,
    #[serde(default)]
    blocking_reason_families: Vec<String>,
}

#[derive(Debug, Deserialize)]
struct RolloutValidationSummaryInput {
    #[serde(default)]
    summary_version: Option<u8>,
    profile: String,
    all_passed: bool,
    cli_surface_consistency_passed: bool,
    startup_contract_validation_passed: bool,
    negotiated_limit_validation_passed: bool,
    selected_datagram_lifecycle_passed: bool,
    mtu_ceiling_delivery_stable: bool,
    fallback_flow_guard_rejection_stable: bool,
    udp_blocked_fallback_surface_passed: bool,
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
    #[serde(default)]
    policy_disabled_fallback_surface_passed: Option<bool>,
    #[serde(default)]
    policy_disabled_fallback_round_trip_stable: bool,
    transport_fallback_integrity_surface_passed: bool,
    rollout_surface_passed: Option<bool>,
    surface_count_total: usize,
    surface_count_passed: usize,
    surface_count_failed: usize,
    #[serde(default)]
    failed_surface_keys: Vec<String>,
    command_count: usize,
    passed_command_count: usize,
    failed_command_count: usize,
    #[serde(default)]
    queue_guard_headroom_band: Option<String>,
    #[serde(default)]
    queue_guard_headroom_missing_count: usize,
    #[serde(default)]
    queue_guard_limiting_path: Option<String>,
    sticky_selection_surface_passed: bool,
    degradation_surface_passed: bool,
}

#[derive(Debug)]
struct LoadedSummaryInput<T> {
    input_label: String,
    present: bool,
    parse_error: Option<String>,
    summary: Option<T>,
}

type LoadedReleaseCandidateConsolidationInput =
    LoadedSummaryInput<ReleaseCandidateConsolidationSummaryInput>;
type LoadedValidationInput = LoadedSummaryInput<RolloutValidationSummaryInput>;

#[derive(Debug, Serialize)]
struct UdpReleaseCandidateHardeningSummary {
    summary_version: u8,
    comparison_schema: &'static str,
    comparison_schema_version: u8,
    verdict_family: &'static str,
    decision_scope: &'static str,
    decision_label: &'static str,
    profile: &'static str,
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
    all_required_inputs_present: bool,
    all_required_inputs_passed: bool,
    blocking_reason_count: usize,
    blocking_reason_key_count: usize,
    blocking_reason_family_count: usize,
    blocking_reason_key_counts: BTreeMap<String, usize>,
    blocking_reason_family_counts: BTreeMap<String, usize>,
    advisory_reason_count: usize,
    release_candidate_consolidation_present: bool,
    release_candidate_consolidation_passed: bool,
    validation_count: usize,
    validation_passed_count: usize,
    validation_failed_count: usize,
    validation_labels: Vec<String>,
    validation_command_count_total: usize,
    validation_command_failed_total: usize,
    validation_surface_count_total: usize,
    validation_surface_failed_total: usize,
    validation_mtu_ceiling_passed_count: usize,
    validation_fallback_flow_guard_rejection_passed_count: usize,
    validation_oversized_payload_guard_recovery_passed_count: usize,
    validation_policy_disabled_fallback_round_trip_passed_count: usize,
    degradation_hold_count: usize,
    degradation_hold_subjects: Vec<String>,
    queue_guard_headroom_band_counts: BTreeMap<String, usize>,
    queue_guard_headroom_missing_count: usize,
    queue_guard_tight_hold_count: usize,
    queue_pressure_hold_count: usize,
    queue_hold_input_count: usize,
    queue_hold_host_count: usize,
    queue_guard_limiting_path_counts: BTreeMap<String, usize>,
    interop_profile_contract_passed: bool,
    interop_profile_catalog_contract_passed: bool,
    interop_profile_catalog_schema_version: u8,
    interop_profile_catalog_host_labels: Vec<String>,
    interop_profile_catalog_source_lane: String,
    interop_required_no_silent_fallback_profile_slugs: Vec<String>,
    interop_failed_profile_slugs: Vec<String>,
    interop_failed_profile_count: usize,
    explicit_fallback_profile_count: usize,
    policy_disabled_fallback_surface_passed: Option<bool>,
    policy_disabled_fallback_round_trip_stable: Option<bool>,
    transport_fallback_integrity_surface_passed: Option<bool>,
    failed_validation_surface_keys: Vec<String>,
    blocking_reasons: Vec<String>,
    blocking_reason_keys: Vec<String>,
    blocking_reason_families: Vec<String>,
    advisory_reasons: Vec<String>,
}

fn main() -> Result<(), Box<dyn std::error::Error>> {
    let args = parse_args(env::args().skip(1))?;
    let summary = build_release_candidate_hardening_summary(
        load_input::<ReleaseCandidateConsolidationSummaryInput>(
            "release_candidate_consolidation",
            &args
                .release_candidate_consolidation
                .unwrap_or_else(default_release_candidate_consolidation_input),
        ),
        vec![
            load_input::<RolloutValidationSummaryInput>(
                "linux_validation",
                &args
                    .linux_validation
                    .unwrap_or_else(default_linux_validation_input),
            ),
            load_input::<RolloutValidationSummaryInput>(
                "macos_validation",
                &args
                    .macos_validation
                    .unwrap_or_else(default_macos_validation_input),
            ),
            load_input::<RolloutValidationSummaryInput>(
                "windows_validation",
                &args
                    .windows_validation
                    .unwrap_or_else(default_windows_validation_input),
            ),
        ],
    );

    let summary_path = args.summary_path.unwrap_or_else(default_summary_path);
    if let Some(parent) = summary_path.parent() {
        fs::create_dir_all(parent)?;
    }
    fs::write(&summary_path, serde_json::to_vec_pretty(&summary)?)?;

    match args.format.unwrap_or(OutputFormat::Text) {
        OutputFormat::Text => print_text_summary(&summary, &summary_path),
        OutputFormat::Json => println!("{}", serde_json::to_string_pretty(&summary)?),
    }

    if summary.verdict != "ready" {
        return Err("udp release candidate hardening is not ready".into());
    }

    Ok(())
}

fn build_release_candidate_hardening_summary(
    release_candidate_consolidation: LoadedReleaseCandidateConsolidationInput,
    validations: Vec<LoadedValidationInput>,
) -> UdpReleaseCandidateHardeningSummary {
    let required_inputs = vec![
        "release_candidate_consolidation".to_owned(),
        "linux_validation".to_owned(),
        "macos_validation".to_owned(),
        "windows_validation".to_owned(),
    ];
    let considered_inputs = required_inputs.clone();
    let expected_required_profile_set = udp_wan_lab_required_no_silent_fallback_profile_slugs()
        .into_iter()
        .map(str::to_owned)
        .collect::<BTreeSet<_>>();

    let mut present_required_inputs = BTreeSet::new();
    let mut passed_required_inputs = BTreeSet::new();
    let mut blocking_reasons = Vec::new();
    let mut blocking_reason_key_counts = BTreeMap::new();
    let mut blocking_reason_family_counts = BTreeMap::new();
    let advisory_reasons = Vec::new();
    let mut queue_guard_headroom_band_counts = BTreeMap::new();
    let mut queue_guard_limiting_path_counts = BTreeMap::new();
    let mut degradation_hold_subjects = Vec::new();
    let mut validation_labels = Vec::new();
    let mut failed_validation_surface_keys = Vec::new();
    let mut validation_command_count_total = 0usize;
    let mut validation_command_failed_total = 0usize;
    let mut validation_surface_count_total = 0usize;
    let mut validation_surface_failed_total = 0usize;
    let mut validation_mtu_ceiling_passed_count = 0usize;
    let mut validation_fallback_flow_guard_rejection_passed_count = 0usize;
    let mut validation_oversized_payload_guard_recovery_passed_count = 0usize;
    let mut validation_policy_disabled_fallback_round_trip_passed_count = 0usize;
    let mut queue_guard_headroom_missing_count = 0usize;
    let mut queue_guard_tight_hold_count = 0usize;
    let mut queue_pressure_hold_count = 0usize;
    let mut validation_queue_hold_inputs = Vec::new();
    let mut interop_required_no_silent_fallback_profile_set = BTreeSet::new();
    let mut interop_failed_profile_set = BTreeSet::new();
    let mut explicit_fallback_profile_count = 0usize;
    let mut interop_profile_contract_passed = false;
    let mut interop_profile_catalog_contract_passed = false;
    let mut interop_profile_catalog_schema_version = 0u8;
    let mut interop_profile_catalog_host_labels = Vec::new();
    let mut interop_profile_catalog_source_lane = String::new();
    let mut policy_disabled_fallback_surface_passed = Some(true);
    let mut policy_disabled_fallback_round_trip_stable = Some(true);
    let mut transport_fallback_integrity_surface_passed = Some(true);
    let mut all_consumed_inputs_contract_valid = true;
    let mut consolidation_queue_hold_present = false;

    let release_candidate_consolidation_present = release_candidate_consolidation.present;
    if release_candidate_consolidation_present {
        present_required_inputs.insert("release_candidate_consolidation".to_owned());
    }
    let release_candidate_consolidation_passed = if let Some(summary) =
        release_candidate_consolidation.summary.as_ref()
    {
        queue_guard_headroom_missing_count += summary.queue_guard_headroom_missing_count;
        queue_guard_tight_hold_count += summary.queue_guard_tight_hold_count;
        queue_pressure_hold_count += summary.queue_pressure_hold_count;
        consolidation_queue_hold_present = rollout_queue_hold_present(
            summary.queue_guard_headroom_missing_count,
            summary.queue_guard_tight_hold_count,
            summary.queue_pressure_hold_count,
        ) || summary.queue_hold_input_count > 0
            || summary.queue_hold_host_count > 0;
        merge_counts(
            &mut queue_guard_headroom_band_counts,
            &summary.queue_guard_headroom_band_counts,
        );
        merge_counts(
            &mut queue_guard_limiting_path_counts,
            &summary.queue_guard_limiting_path_counts,
        );
        interop_required_no_silent_fallback_profile_set.extend(
            summary
                .interop_required_no_silent_fallback_profile_slugs
                .iter()
                .cloned(),
        );
        interop_failed_profile_set.extend(summary.interop_failed_profile_slugs.iter().cloned());
        explicit_fallback_profile_count =
            explicit_fallback_profile_count.max(summary.explicit_fallback_profile_count);
        interop_profile_contract_passed = summary.interop_profile_contract_passed;
        interop_profile_catalog_contract_passed = summary.interop_profile_catalog_contract_passed;
        interop_profile_catalog_schema_version = summary.interop_profile_catalog_schema_version;
        interop_profile_catalog_host_labels = summary.interop_profile_catalog_host_labels.clone();
        interop_profile_catalog_source_lane = summary.interop_profile_catalog_source_lane.clone();
        policy_disabled_fallback_surface_passed = merge_optional_bool(
            policy_disabled_fallback_surface_passed,
            summary.policy_disabled_fallback_surface_passed,
        );
        transport_fallback_integrity_surface_passed = merge_optional_bool(
            transport_fallback_integrity_surface_passed,
            summary.transport_fallback_integrity_surface_passed,
        );
        if summary.degradation_hold_count > 0 {
            degradation_hold_subjects.push("release_candidate_consolidation".to_owned());
            degradation_hold_subjects.extend(summary.degradation_hold_subjects.iter().cloned());
        }

        if release_candidate_consolidation.present
            && release_candidate_consolidation.parse_error.is_none()
            && release_candidate_consolidation_summary_contract_valid(summary)
            && summary.verdict == "ready"
            && summary.evidence_state == "complete"
            && summary.gate_state == "passed"
            && summary.active_fuzz_required
            && summary.all_required_inputs_present
            && summary.all_required_inputs_passed
            && summary.blocking_reason_count == 0
            && summary.degradation_hold_count == 0
            && summary.queue_hold_input_count == 0
            && summary.queue_hold_host_count == 0
            && !rollout_queue_hold_present(
                summary.queue_guard_headroom_missing_count,
                summary.queue_guard_tight_hold_count,
                summary.queue_pressure_hold_count,
            )
            && summary.policy_disabled_fallback_surface_passed == Some(true)
            && summary.transport_fallback_integrity_surface_passed == Some(true)
            && summary.interop_profile_contract_passed
            && summary.interop_profile_catalog_contract_passed
        {
            passed_required_inputs.insert("release_candidate_consolidation".to_owned());
            true
        } else {
            false
        }
    } else {
        false
    };

    if !release_candidate_consolidation.present {
        push_reason(
            &mut blocking_reasons,
            &mut blocking_reason_key_counts,
            &mut blocking_reason_family_counts,
            "missing_release_candidate_consolidation",
            "missing_required_input",
            "summary_presence",
        );
    } else if let Some(error) = release_candidate_consolidation.parse_error.as_ref() {
        all_consumed_inputs_contract_valid = false;
        push_reason(
            &mut blocking_reasons,
            &mut blocking_reason_key_counts,
            &mut blocking_reason_family_counts,
            &format!("release_candidate_consolidation_parse_error:{error}"),
            "input_parse_error",
            "summary_contract",
        );
    } else if let Some(summary) = release_candidate_consolidation.summary.as_ref() {
        if !release_candidate_consolidation_summary_contract_valid(summary) {
            all_consumed_inputs_contract_valid = false;
            push_reason(
                &mut blocking_reasons,
                &mut blocking_reason_key_counts,
                &mut blocking_reason_family_counts,
                "release_candidate_consolidation_summary_contract_invalid",
                "input_contract_invalid",
                "summary_contract",
            );
        } else if !release_candidate_consolidation_passed {
            push_reason(
                &mut blocking_reasons,
                &mut blocking_reason_key_counts,
                &mut blocking_reason_family_counts,
                "release_candidate_consolidation_not_ready",
                "input_not_ready",
                if consolidation_queue_hold_present {
                    "capacity"
                } else if summary.degradation_hold_count > 0 {
                    "degradation"
                } else {
                    "gating"
                },
            );
        }
    }

    let mut validation_passed_count = 0usize;
    for input in validations {
        validation_labels.push(input.input_label.clone());
        if input.present {
            present_required_inputs.insert(input.input_label.clone());
        }

        let passed = if let Some(summary) = input.summary.as_ref() {
            validation_command_count_total += summary.command_count;
            validation_command_failed_total += summary.failed_command_count;
            validation_surface_count_total += summary.surface_count_total;
            validation_surface_failed_total += summary.surface_count_failed;
            queue_guard_headroom_missing_count += summary.queue_guard_headroom_missing_count;
            if let Some(band) = summary.queue_guard_headroom_band.as_ref() {
                increment_count(&mut queue_guard_headroom_band_counts, band);
            }
            if summary.queue_guard_headroom_band.as_deref() == Some("tight") {
                queue_guard_tight_hold_count += 1;
            }
            if !summary.queue_pressure_surface_passed {
                queue_pressure_hold_count += 1;
            }
            if let Some(limiting_path) = summary.queue_guard_limiting_path.as_ref() {
                increment_count(&mut queue_guard_limiting_path_counts, limiting_path);
            }
            if summary.mtu_ceiling_delivery_stable {
                validation_mtu_ceiling_passed_count += 1;
            }
            if summary.fallback_flow_guard_rejection_stable {
                validation_fallback_flow_guard_rejection_passed_count += 1;
            }
            if summary.oversized_payload_guard_recovery_stable {
                validation_oversized_payload_guard_recovery_passed_count += 1;
            }
            if summary.policy_disabled_fallback_round_trip_stable {
                validation_policy_disabled_fallback_round_trip_passed_count += 1;
            }
            if validation_has_degradation_hold(summary) {
                degradation_hold_subjects.push(input.input_label.clone());
            }
            if rollout_queue_hold_present(
                summary.queue_guard_headroom_missing_count,
                usize::from(summary.queue_guard_headroom_band.as_deref() == Some("tight")),
                usize::from(!summary.queue_pressure_surface_passed),
            ) {
                validation_queue_hold_inputs.push((
                    summary.queue_guard_headroom_missing_count,
                    usize::from(summary.queue_guard_headroom_band.as_deref() == Some("tight")),
                    usize::from(!summary.queue_pressure_surface_passed),
                ));
            }
            failed_validation_surface_keys.extend(
                summary
                    .failed_surface_keys
                    .iter()
                    .map(|key| format!("{}:{key}", input.input_label)),
            );
            policy_disabled_fallback_surface_passed = merge_optional_bool(
                policy_disabled_fallback_surface_passed,
                summary.policy_disabled_fallback_surface_passed,
            );
            policy_disabled_fallback_round_trip_stable = merge_optional_bool(
                policy_disabled_fallback_round_trip_stable,
                Some(summary.policy_disabled_fallback_round_trip_stable),
            );
            transport_fallback_integrity_surface_passed = merge_optional_bool(
                transport_fallback_integrity_surface_passed,
                Some(summary.transport_fallback_integrity_surface_passed),
            );

            if input.present
                && input.parse_error.is_none()
                && validation_summary_contract_valid(summary)
                && validation_summary_passed(summary)
            {
                passed_required_inputs.insert(input.input_label.clone());
                validation_passed_count += 1;
                true
            } else {
                false
            }
        } else {
            false
        };

        if !input.present {
            push_reason(
                &mut blocking_reasons,
                &mut blocking_reason_key_counts,
                &mut blocking_reason_family_counts,
                &format!("missing_{}", input.input_label),
                "missing_required_input",
                "summary_presence",
            );
        } else if let Some(error) = input.parse_error.as_ref() {
            all_consumed_inputs_contract_valid = false;
            push_reason(
                &mut blocking_reasons,
                &mut blocking_reason_key_counts,
                &mut blocking_reason_family_counts,
                &format!("{}:validation_parse_error:{error}", input.input_label),
                "input_parse_error",
                "summary_contract",
            );
        } else if let Some(summary) = input.summary.as_ref() {
            if !validation_summary_contract_valid(summary) {
                all_consumed_inputs_contract_valid = false;
                push_reason(
                    &mut blocking_reasons,
                    &mut blocking_reason_key_counts,
                    &mut blocking_reason_family_counts,
                    &format!("{}:validation_summary_contract_invalid", input.input_label),
                    "input_contract_invalid",
                    "summary_contract",
                );
            } else if !passed {
                push_reason(
                    &mut blocking_reasons,
                    &mut blocking_reason_key_counts,
                    &mut blocking_reason_family_counts,
                    &format!("{}_not_ready", input.input_label),
                    "input_not_ready",
                    if rollout_queue_hold_present(
                        summary.queue_guard_headroom_missing_count,
                        usize::from(summary.queue_guard_headroom_band.as_deref() == Some("tight")),
                        usize::from(!summary.queue_pressure_surface_passed),
                    ) {
                        "capacity"
                    } else if validation_has_degradation_hold(summary) {
                        "degradation"
                    } else {
                        "gating"
                    },
                );
            }
        }
    }

    let validation_count = validation_labels.len();
    let validation_failed_count = validation_count.saturating_sub(validation_passed_count);
    let queue_hold_host_count = rollout_queue_hold_host_count(validation_queue_hold_inputs.clone());
    let mut queue_hold_inputs = validation_queue_hold_inputs;
    if consolidation_queue_hold_present {
        queue_hold_inputs.push((
            queue_guard_headroom_missing_count,
            queue_guard_tight_hold_count,
            queue_pressure_hold_count,
        ));
    }
    let queue_hold_input_count = rollout_queue_hold_input_count(queue_hold_inputs);

    if validation_count > 0 && validation_mtu_ceiling_passed_count < validation_count {
        push_reason(
            &mut blocking_reasons,
            &mut blocking_reason_key_counts,
            &mut blocking_reason_family_counts,
            "release_candidate_hardening_mtu_ceiling_delivery_surface_failed",
            "mtu_ceiling_delivery_surface_failed",
            "degradation",
        );
    }
    if validation_count > 0
        && validation_fallback_flow_guard_rejection_passed_count < validation_count
    {
        push_reason(
            &mut blocking_reasons,
            &mut blocking_reason_key_counts,
            &mut blocking_reason_family_counts,
            "release_candidate_hardening_fallback_flow_guard_rejection_surface_failed",
            "fallback_flow_guard_rejection_surface_failed",
            "degradation",
        );
    }
    if validation_count > 0
        && validation_oversized_payload_guard_recovery_passed_count < validation_count
    {
        push_reason(
            &mut blocking_reasons,
            &mut blocking_reason_key_counts,
            &mut blocking_reason_family_counts,
            "release_candidate_hardening_oversized_payload_guard_recovery_surface_failed",
            "oversized_payload_guard_recovery_surface_failed",
            "degradation",
        );
    }
    if validation_count > 0
        && validation_policy_disabled_fallback_round_trip_passed_count < validation_count
    {
        push_reason(
            &mut blocking_reasons,
            &mut blocking_reason_key_counts,
            &mut blocking_reason_family_counts,
            "release_candidate_hardening_policy_disabled_fallback_round_trip_surface_failed",
            "policy_disabled_fallback_round_trip_surface_failed",
            "transport_integrity",
        );
    }
    if policy_disabled_fallback_surface_passed != Some(true) {
        push_reason(
            &mut blocking_reasons,
            &mut blocking_reason_key_counts,
            &mut blocking_reason_family_counts,
            "release_candidate_hardening_policy_disabled_fallback_surface_failed",
            "policy_disabled_fallback_surface_failed",
            "degradation",
        );
    }
    if policy_disabled_fallback_round_trip_stable != Some(true) {
        push_reason(
            &mut blocking_reasons,
            &mut blocking_reason_key_counts,
            &mut blocking_reason_family_counts,
            "release_candidate_hardening_policy_disabled_fallback_round_trip_surface_failed",
            "policy_disabled_fallback_round_trip_surface_failed",
            "transport_integrity",
        );
    }
    if transport_fallback_integrity_surface_passed != Some(true) {
        push_reason(
            &mut blocking_reasons,
            &mut blocking_reason_key_counts,
            &mut blocking_reason_family_counts,
            "release_candidate_hardening_transport_fallback_integrity_surface_failed",
            "transport_fallback_integrity_surface_failed",
            "degradation",
        );
    }

    let missing_required_inputs = required_inputs
        .iter()
        .filter(|label| !present_required_inputs.contains(*label))
        .cloned()
        .collect::<Vec<_>>();
    let required_input_count = required_inputs.len();
    let required_input_present_count = present_required_inputs.len();
    let required_input_passed_count = passed_required_inputs.len();
    let required_input_missing_count = missing_required_inputs.len();
    let required_input_failed_count =
        required_input_count.saturating_sub(required_input_passed_count);
    let required_input_unready_count =
        required_input_failed_count.saturating_sub(required_input_missing_count);
    let all_required_inputs_present = required_input_present_count == required_input_count;
    let all_required_inputs_passed =
        all_required_inputs_present && required_input_passed_count == required_input_count;

    degradation_hold_subjects.sort();
    degradation_hold_subjects.dedup();
    failed_validation_surface_keys.sort();
    failed_validation_surface_keys.dedup();
    interop_profile_catalog_host_labels.sort();
    let degradation_hold_count = degradation_hold_subjects.len();
    let blocking_reason_count = blocking_reasons.len();
    let blocking_reason_key_count = blocking_reason_key_counts.len();
    let blocking_reason_family_count = blocking_reason_family_counts.len();
    let interop_required_no_silent_fallback_profile_slugs =
        interop_required_no_silent_fallback_profile_set
            .into_iter()
            .collect::<Vec<_>>();
    let interop_failed_profile_slugs = interop_failed_profile_set.into_iter().collect::<Vec<_>>();
    let interop_failed_profile_count = interop_failed_profile_slugs.len();
    let expected_catalog_host_labels =
        vec!["linux".to_owned(), "macos".to_owned(), "windows".to_owned()];
    interop_profile_contract_passed = interop_profile_contract_passed
        && interop_required_no_silent_fallback_profile_slugs
            .iter()
            .cloned()
            .collect::<BTreeSet<_>>()
            == expected_required_profile_set
        && interop_failed_profile_count == interop_failed_profile_slugs.len();
    interop_profile_catalog_contract_passed = interop_profile_catalog_contract_passed
        && interop_profile_catalog_schema_version == 1
        && interop_profile_catalog_host_labels == expected_catalog_host_labels
        && interop_profile_catalog_source_lane
            == UDP_INTEROP_PROFILE_CATALOG_SOURCE_LANE_COMPATIBLE_HOST;
    let summary_contract_invalid_count = blocking_reason_family_counts
        .get("summary_contract")
        .copied()
        .unwrap_or(0);
    let (gate_state_reason, gate_state_reason_family) = summarize_rollout_gate_state(
        required_input_missing_count,
        summary_contract_invalid_count,
        required_input_unready_count,
        degradation_hold_count,
        blocking_reason_count,
    );
    let verdict = if all_required_inputs_passed
        && blocking_reason_count == 0
        && degradation_hold_count == 0
        && queue_hold_input_count == 0
        && queue_hold_host_count == 0
        && interop_profile_contract_passed
        && interop_profile_catalog_contract_passed
        && policy_disabled_fallback_surface_passed == Some(true)
        && policy_disabled_fallback_round_trip_stable == Some(true)
        && transport_fallback_integrity_surface_passed == Some(true)
    {
        "ready"
    } else {
        "hold"
    };
    let evidence_state = if all_required_inputs_present && all_consumed_inputs_contract_valid {
        "complete"
    } else {
        "incomplete"
    };
    let gate_state = if verdict == "ready" {
        "passed"
    } else {
        "blocked"
    };
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

    UdpReleaseCandidateHardeningSummary {
        summary_version: UDP_RELEASE_CANDIDATE_HARDENING_SUMMARY_VERSION,
        comparison_schema: UDP_ROLLOUT_OPERATOR_VERDICT_SCHEMA,
        comparison_schema_version: UDP_ROLLOUT_OPERATOR_VERDICT_SCHEMA_VERSION,
        verdict_family: UDP_ROLLOUT_OPERATOR_VERDICT_FAMILY,
        decision_scope: UDP_ROLLOUT_DECISION_SCOPE_RELEASE_CANDIDATE_HARDENING,
        decision_label: "release_candidate_hardening",
        profile: "release_candidate_hardening",
        verdict,
        evidence_state,
        gate_state,
        gate_state_reason,
        gate_state_reason_family,
        active_fuzz_required: true,
        required_inputs,
        considered_inputs,
        missing_required_inputs,
        missing_required_input_count: required_input_missing_count,
        required_input_count,
        required_input_missing_count,
        required_input_failed_count,
        required_input_unready_count,
        required_input_present_count,
        required_input_passed_count,
        all_required_inputs_present,
        all_required_inputs_passed,
        blocking_reason_count,
        blocking_reason_key_count,
        blocking_reason_family_count,
        blocking_reason_key_counts,
        blocking_reason_family_counts,
        advisory_reason_count: 0,
        release_candidate_consolidation_present,
        release_candidate_consolidation_passed,
        validation_count,
        validation_passed_count,
        validation_failed_count,
        validation_labels,
        validation_command_count_total,
        validation_command_failed_total,
        validation_surface_count_total,
        validation_surface_failed_total,
        validation_mtu_ceiling_passed_count,
        validation_fallback_flow_guard_rejection_passed_count,
        validation_oversized_payload_guard_recovery_passed_count,
        validation_policy_disabled_fallback_round_trip_passed_count,
        degradation_hold_count,
        degradation_hold_subjects,
        queue_guard_headroom_band_counts,
        queue_guard_headroom_missing_count,
        queue_guard_tight_hold_count,
        queue_pressure_hold_count,
        queue_hold_input_count,
        queue_hold_host_count,
        queue_guard_limiting_path_counts,
        interop_profile_contract_passed,
        interop_profile_catalog_contract_passed,
        interop_profile_catalog_schema_version,
        interop_profile_catalog_host_labels,
        interop_profile_catalog_source_lane,
        interop_required_no_silent_fallback_profile_slugs,
        interop_failed_profile_slugs,
        interop_failed_profile_count,
        explicit_fallback_profile_count,
        policy_disabled_fallback_surface_passed,
        policy_disabled_fallback_round_trip_stable,
        transport_fallback_integrity_surface_passed,
        failed_validation_surface_keys,
        blocking_reasons,
        blocking_reason_keys,
        blocking_reason_families,
        advisory_reasons,
    }
}

fn release_candidate_consolidation_summary_contract_valid(
    summary: &ReleaseCandidateConsolidationSummaryInput,
) -> bool {
    let expected_inputs = vec![
        "release_stability_signoff".to_owned(),
        "linux_interop_catalog".to_owned(),
        "macos_interop_catalog".to_owned(),
        "windows_interop_catalog".to_owned(),
    ];
    let expected_required_profile_set = udp_wan_lab_required_no_silent_fallback_profile_slugs()
        .into_iter()
        .map(str::to_owned)
        .collect::<BTreeSet<_>>();
    let actual_required_profile_set = summary
        .interop_required_no_silent_fallback_profile_slugs
        .iter()
        .cloned()
        .collect::<BTreeSet<_>>();
    let summary_contract_invalid_count = summary
        .blocking_reason_family_counts
        .get("summary_contract")
        .copied()
        .unwrap_or(0);
    let (expected_reason, expected_family) = summarize_rollout_gate_state(
        summary.required_input_missing_count,
        summary_contract_invalid_count,
        summary.required_input_unready_count,
        summary.degradation_hold_count,
        summary.blocking_reason_count,
    );

    summary.summary_version == Some(UDP_RELEASE_CANDIDATE_CONSOLIDATION_SUMMARY_VERSION)
        && summary.comparison_schema == UDP_ROLLOUT_OPERATOR_VERDICT_SCHEMA
        && summary.comparison_schema_version == UDP_ROLLOUT_OPERATOR_VERDICT_SCHEMA_VERSION
        && summary.verdict_family == UDP_ROLLOUT_OPERATOR_VERDICT_FAMILY
        && summary.decision_scope == UDP_ROLLOUT_DECISION_SCOPE_RELEASE_CANDIDATE_CONSOLIDATION
        && summary.decision_label == "release_candidate_consolidation"
        && summary.profile == "release_candidate_consolidation"
        && summary.active_fuzz_required
        && summary.required_inputs == expected_inputs
        && summary.considered_inputs == expected_inputs
        && rollout_input_identity_consistent(
            &summary.required_inputs,
            &summary.considered_inputs,
            &summary.missing_required_inputs,
            summary.required_input_count,
        )
        && summary.missing_required_input_count == summary.missing_required_inputs.len()
        && summary.required_input_missing_count == summary.missing_required_inputs.len()
        && summary.required_input_present_count <= summary.required_input_count
        && summary.required_input_passed_count <= summary.required_input_present_count
        && summary.required_input_failed_count
            == summary
                .required_input_count
                .saturating_sub(summary.required_input_passed_count)
        && summary.required_input_unready_count
            == summary
                .required_input_failed_count
                .saturating_sub(summary.required_input_missing_count)
        && summary.all_required_inputs_present
            == (summary.required_input_present_count == summary.required_input_count)
        && summary.all_required_inputs_passed
            == (summary.required_input_present_count == summary.required_input_count
                && summary.required_input_passed_count == summary.required_input_count)
        && summary.degradation_hold_count == summary.degradation_hold_subjects.len()
        && summary.blocking_reason_count == summary.blocking_reasons.len()
        && summary.blocking_reason_key_count == summary.blocking_reason_key_counts.len()
        && summary.blocking_reason_family_count == summary.blocking_reason_family_counts.len()
        && summary.blocking_reason_count
            == summary.blocking_reason_key_counts.values().sum::<usize>()
        && summary.blocking_reason_count
            == summary
                .blocking_reason_family_counts
                .values()
                .sum::<usize>()
        && blocking_reason_accounting_consistent(
            &summary.blocking_reason_keys,
            &summary.blocking_reason_key_counts,
            &summary.blocking_reason_families,
            &summary.blocking_reason_family_counts,
        )
        && summary.queue_hold_host_count <= 3
        && summary.queue_hold_host_count <= summary.queue_hold_input_count
        && actual_required_profile_set == expected_required_profile_set
        && summary.interop_failed_profile_count == summary.interop_failed_profile_slugs.len()
        && summary.interop_profile_catalog_schema_version == 1
        && summary.interop_profile_catalog_host_labels
            == vec!["linux".to_owned(), "macos".to_owned(), "windows".to_owned()]
        && summary.interop_profile_catalog_source_lane
            == UDP_INTEROP_PROFILE_CATALOG_SOURCE_LANE_COMPATIBLE_HOST
        && summary.gate_state_reason == expected_reason
        && summary.gate_state_reason_family == expected_family
        && summary.gate_state
            == if summary.verdict == "ready" {
                "passed"
            } else {
                "blocked"
            }
}

fn validation_summary_contract_valid(summary: &RolloutValidationSummaryInput) -> bool {
    summary.summary_version == Some(UDP_ROLLOUT_VALIDATION_SUMMARY_VERSION)
        && !summary.profile.trim().is_empty()
        && summary.command_count == summary.passed_command_count + summary.failed_command_count
        && summary.surface_count_total
            == summary.surface_count_passed + summary.surface_count_failed
        && (!summary.policy_disabled_fallback_round_trip_stable
            || (summary.policy_disabled_fallback_surface_passed == Some(true)
                && summary.transport_fallback_integrity_surface_passed))
        && (summary.queue_guard_headroom_band.as_deref() != Some("tight")
            || summary.queue_pressure_surface_passed)
        && !(summary.all_passed
            && (summary.failed_command_count != 0 || summary.surface_count_failed != 0))
        && (!summary.transport_fallback_integrity_surface_passed
            || (summary.fallback_flow_guard_rejection_stable
                && summary.udp_blocked_fallback_surface_passed
                && summary.policy_disabled_fallback_round_trip_stable
                && summary.policy_disabled_fallback_surface_passed == Some(true)))
}

fn validation_has_degradation_hold(summary: &RolloutValidationSummaryInput) -> bool {
    !summary.degradation_surface_passed
        || summary.rollout_surface_passed != Some(true)
        || !summary.queue_pressure_surface_passed
        || !summary.reordering_no_silent_fallback_passed
        || !summary.prolonged_impairment_no_silent_fallback
        || !summary.prolonged_repeated_impairment_stable
        || !summary.longer_impairment_recovery_stable
        || !summary.shutdown_sequence_stable
        || !summary.post_close_rejection_stable
        || !summary.associated_stream_guard_recovery_stable
        || !summary.oversized_payload_guard_recovery_stable
        || !summary.reordered_after_close_rejection_stable
        || !summary.mtu_ceiling_delivery_stable
        || !summary.fallback_flow_guard_rejection_stable
        || !summary.udp_blocked_fallback_surface_passed
        || !summary.clean_shutdown_stable
        || summary.policy_disabled_fallback_surface_passed != Some(true)
        || !summary.policy_disabled_fallback_round_trip_stable
        || !summary.transport_fallback_integrity_surface_passed
        || summary.queue_guard_headroom_band.is_none()
        || summary.queue_guard_headroom_band.as_deref() == Some("tight")
}

fn validation_summary_passed(summary: &RolloutValidationSummaryInput) -> bool {
    summary.all_passed
        && summary.cli_surface_consistency_passed
        && summary.startup_contract_validation_passed
        && summary.negotiated_limit_validation_passed
        && summary.selected_datagram_lifecycle_passed
        && summary.mtu_ceiling_delivery_stable
        && summary.fallback_flow_guard_rejection_stable
        && summary.udp_blocked_fallback_surface_passed
        && summary.repeated_queue_pressure_sticky
        && summary.queue_pressure_surface_passed
        && summary.reordering_no_silent_fallback_passed
        && summary.prolonged_impairment_no_silent_fallback
        && summary.prolonged_repeated_impairment_stable
        && summary.longer_impairment_recovery_stable
        && summary.shutdown_sequence_stable
        && summary.post_close_rejection_stable
        && summary.associated_stream_guard_recovery_stable
        && summary.oversized_payload_guard_recovery_stable
        && summary.reordered_after_close_rejection_stable
        && summary.clean_shutdown_stable
        && summary.sticky_selection_surface_passed
        && summary.degradation_surface_passed
        && summary.policy_disabled_fallback_surface_passed == Some(true)
        && summary.policy_disabled_fallback_round_trip_stable
        && summary.transport_fallback_integrity_surface_passed
        && summary.rollout_surface_passed == Some(true)
        && summary.command_count > 0
        && summary.failed_command_count == 0
        && summary.surface_count_total > 0
        && summary.surface_count_failed == 0
        && summary.queue_guard_headroom_band.is_some()
        && summary.queue_guard_headroom_band.as_deref() != Some("tight")
}

fn rollout_input_identity_consistent(
    required_inputs: &[String],
    considered_inputs: &[String],
    missing_required_inputs: &[String],
    required_input_count: usize,
) -> bool {
    let required_set = required_inputs.iter().collect::<BTreeSet<_>>();
    let considered_set = considered_inputs.iter().collect::<BTreeSet<_>>();
    let missing_set = missing_required_inputs.iter().collect::<BTreeSet<_>>();
    required_set.len() == required_inputs.len()
        && considered_set.len() == considered_inputs.len()
        && missing_set.len() == missing_required_inputs.len()
        && required_inputs.len() == required_input_count
        && required_set.is_subset(&considered_set)
        && missing_set.is_subset(&required_set)
        && required_inputs.iter().all(|label| !label.trim().is_empty())
        && considered_inputs
            .iter()
            .all(|label| !label.trim().is_empty())
        && missing_required_inputs
            .iter()
            .all(|label| !label.trim().is_empty())
}

fn load_input<T>(input_label: &str, path: &Path) -> LoadedSummaryInput<T>
where
    T: for<'de> Deserialize<'de>,
{
    if !path.exists() {
        return LoadedSummaryInput {
            input_label: input_label.to_owned(),
            present: false,
            parse_error: None,
            summary: None,
        };
    }

    match fs::read(path)
        .map_err(|error| error.to_string())
        .and_then(|bytes| serde_json::from_slice::<T>(&bytes).map_err(|error| error.to_string()))
    {
        Ok(summary) => LoadedSummaryInput {
            input_label: input_label.to_owned(),
            present: true,
            parse_error: None,
            summary: Some(summary),
        },
        Err(error) => LoadedSummaryInput {
            input_label: input_label.to_owned(),
            present: true,
            parse_error: Some(error),
            summary: None,
        },
    }
}

fn print_text_summary(summary: &UdpReleaseCandidateHardeningSummary, summary_path: &Path) {
    println!("Verta UDP release candidate hardening summary:");
    println!("- verdict: {}", summary.verdict);
    println!("- comparison_schema: {}", summary.comparison_schema);
    println!(
        "- comparison_schema_version: {}",
        summary.comparison_schema_version
    );
    println!("- decision_scope: {}", summary.decision_scope);
    println!("- decision_label: {}", summary.decision_label);
    println!("- evidence_state: {}", summary.evidence_state);
    println!("- gate_state: {}", summary.gate_state);
    println!("- gate_state_reason: {}", summary.gate_state_reason);
    println!(
        "- gate_state_reason_family: {}",
        summary.gate_state_reason_family
    );
    println!(
        "- required_input_counts: total={} present={} passed={}",
        summary.required_input_count,
        summary.required_input_present_count,
        summary.required_input_passed_count
    );
    println!(
        "- release_candidate_consolidation: present={} passed={}",
        summary.release_candidate_consolidation_present,
        summary.release_candidate_consolidation_passed
    );
    println!(
        "- validation_counts: total={} passed={} failed={}",
        summary.validation_count, summary.validation_passed_count, summary.validation_failed_count
    );
    println!(
        "- validation_mtu_ceiling_passed_count: {}",
        summary.validation_mtu_ceiling_passed_count
    );
    println!(
        "- validation_fallback_flow_guard_rejection_passed_count: {}",
        summary.validation_fallback_flow_guard_rejection_passed_count
    );
    println!(
        "- validation_oversized_payload_guard_recovery_passed_count: {}",
        summary.validation_oversized_payload_guard_recovery_passed_count
    );
    println!(
        "- validation_policy_disabled_fallback_round_trip_passed_count: {}",
        summary.validation_policy_disabled_fallback_round_trip_passed_count
    );
    println!(
        "- queue_guard_headroom_missing_count: {}",
        summary.queue_guard_headroom_missing_count
    );
    println!(
        "- queue_guard_tight_hold_count: {}",
        summary.queue_guard_tight_hold_count
    );
    println!(
        "- queue_pressure_hold_count: {}",
        summary.queue_pressure_hold_count
    );
    println!(
        "- queue_hold_input_count: {}",
        summary.queue_hold_input_count
    );
    println!("- queue_hold_host_count: {}", summary.queue_hold_host_count);
    println!(
        "- interop_profile_catalog_host_labels: {}",
        summary.interop_profile_catalog_host_labels.join(", ")
    );
    println!(
        "- interop_profile_catalog_source_lane: {}",
        summary.interop_profile_catalog_source_lane
    );
    println!(
        "- interop_failed_profile_count: {}",
        summary.interop_failed_profile_count
    );
    println!(
        "- policy_disabled_fallback_surface_passed: {}",
        summary
            .policy_disabled_fallback_surface_passed
            .map(|value| value.to_string())
            .unwrap_or_else(|| "missing".to_owned())
    );
    println!(
        "- policy_disabled_fallback_round_trip_stable: {}",
        summary
            .policy_disabled_fallback_round_trip_stable
            .map(|value| value.to_string())
            .unwrap_or_else(|| "missing".to_owned())
    );
    println!(
        "- transport_fallback_integrity_surface_passed: {}",
        summary
            .transport_fallback_integrity_surface_passed
            .map(|value| value.to_string())
            .unwrap_or_else(|| "missing".to_owned())
    );
    println!(
        "- blocking_reason_keys: {}",
        if summary.blocking_reason_keys.is_empty() {
            "none".to_owned()
        } else {
            summary.blocking_reason_keys.join(", ")
        }
    );
    println!(
        "- blocking_reasons: {}",
        if summary.blocking_reasons.is_empty() {
            "none".to_owned()
        } else {
            summary.blocking_reasons.join(", ")
        }
    );
    println!("- summary_path: {}", summary_path.display());
}

fn parse_args<I>(args: I) -> Result<ReleaseCandidateHardeningArgs, String>
where
    I: IntoIterator<Item = String>,
{
    let mut parsed = ReleaseCandidateHardeningArgs::default();
    let mut iter = args.into_iter();
    while let Some(arg) = iter.next() {
        match arg.as_str() {
            "--format" => {
                let value = iter
                    .next()
                    .ok_or_else(|| "--format requires a value".to_owned())?;
                parsed.format = Some(parse_output_format(&value)?);
            }
            "--summary-path" => {
                parsed.summary_path =
                    Some(PathBuf::from(iter.next().ok_or_else(|| {
                        "--summary-path requires a value".to_owned()
                    })?));
            }
            "--release-candidate-consolidation" => {
                parsed.release_candidate_consolidation =
                    Some(PathBuf::from(iter.next().ok_or_else(|| {
                        "--release-candidate-consolidation requires a value".to_owned()
                    })?));
            }
            "--linux-validation" => {
                parsed.linux_validation =
                    Some(PathBuf::from(iter.next().ok_or_else(|| {
                        "--linux-validation requires a value".to_owned()
                    })?));
            }
            "--macos-validation" => {
                parsed.macos_validation =
                    Some(PathBuf::from(iter.next().ok_or_else(|| {
                        "--macos-validation requires a value".to_owned()
                    })?));
            }
            "--windows-validation" => {
                parsed.windows_validation =
                    Some(PathBuf::from(iter.next().ok_or_else(|| {
                        "--windows-validation requires a value".to_owned()
                    })?));
            }
            "--help" | "-h" => return Err(usage()),
            other => return Err(format!("unknown argument: {other}\n\n{}", usage())),
        }
    }
    Ok(parsed)
}

fn parse_output_format(value: &str) -> Result<OutputFormat, String> {
    match value {
        "text" => Ok(OutputFormat::Text),
        "json" => Ok(OutputFormat::Json),
        other => Err(format!("unsupported output format: {other}")),
    }
}

fn usage() -> String {
    "usage: cargo run -p ns-testkit --example udp_release_candidate_hardening -- [--format text|json] [--summary-path PATH] [--release-candidate-consolidation PATH] [--linux-validation PATH] [--macos-validation PATH] [--windows-validation PATH]".to_owned()
}

fn default_release_candidate_consolidation_input() -> PathBuf {
    prefer_verta_input_path("udp-release-candidate-consolidation-summary.json")
}

fn default_linux_validation_input() -> PathBuf {
    prefer_verta_input_path("udp-rollout-validation-summary-linux.json")
}

fn default_macos_validation_input() -> PathBuf {
    prefer_verta_input_path("udp-rollout-validation-summary-macos.json")
}

fn default_windows_validation_input() -> PathBuf {
    prefer_verta_input_path("udp-rollout-validation-summary-windows.json")
}

fn default_summary_path() -> PathBuf {
    verta_output_path("udp-release-candidate-hardening-summary.json")
}

fn increment_count(map: &mut BTreeMap<String, usize>, key: &str) {
    *map.entry(key.to_owned()).or_insert(0) += 1;
}

fn merge_counts(target: &mut BTreeMap<String, usize>, source: &BTreeMap<String, usize>) {
    for (key, value) in source {
        *target.entry(key.clone()).or_insert(0) += value;
    }
}

fn merge_optional_bool(current: Option<bool>, next: Option<bool>) -> Option<bool> {
    match (current, next) {
        (Some(false), _) | (_, Some(false)) => Some(false),
        (Some(true), Some(true)) => Some(true),
        _ => None,
    }
}

fn push_reason(
    blocking_reasons: &mut Vec<String>,
    blocking_reason_key_counts: &mut BTreeMap<String, usize>,
    blocking_reason_family_counts: &mut BTreeMap<String, usize>,
    reason: &str,
    key: &str,
    family: &str,
) {
    blocking_reasons.push(reason.to_owned());
    increment_count(blocking_reason_key_counts, key);
    increment_count(blocking_reason_family_counts, family);
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::collections::BTreeSet;

    fn ready_release_candidate_consolidation() -> LoadedReleaseCandidateConsolidationInput {
        LoadedSummaryInput {
            input_label: "release_candidate_consolidation".to_owned(),
            present: true,
            parse_error: None,
            summary: Some(ReleaseCandidateConsolidationSummaryInput {
                summary_version: Some(UDP_RELEASE_CANDIDATE_CONSOLIDATION_SUMMARY_VERSION),
                comparison_schema: UDP_ROLLOUT_OPERATOR_VERDICT_SCHEMA.to_owned(),
                comparison_schema_version: UDP_ROLLOUT_OPERATOR_VERDICT_SCHEMA_VERSION,
                verdict_family: UDP_ROLLOUT_OPERATOR_VERDICT_FAMILY.to_owned(),
                decision_scope: UDP_ROLLOUT_DECISION_SCOPE_RELEASE_CANDIDATE_CONSOLIDATION
                    .to_owned(),
                decision_label: "release_candidate_consolidation".to_owned(),
                profile: "release_candidate_consolidation".to_owned(),
                verdict: "ready".to_owned(),
                evidence_state: "complete".to_owned(),
                gate_state: "passed".to_owned(),
                gate_state_reason: "all_required_inputs_passed".to_owned(),
                gate_state_reason_family: "ready".to_owned(),
                active_fuzz_required: true,
                required_inputs: vec![
                    "release_stability_signoff".to_owned(),
                    "linux_interop_catalog".to_owned(),
                    "macos_interop_catalog".to_owned(),
                    "windows_interop_catalog".to_owned(),
                ],
                considered_inputs: vec![
                    "release_stability_signoff".to_owned(),
                    "linux_interop_catalog".to_owned(),
                    "macos_interop_catalog".to_owned(),
                    "windows_interop_catalog".to_owned(),
                ],
                missing_required_inputs: Vec::new(),
                missing_required_input_count: 0,
                required_input_count: 4,
                required_input_missing_count: 0,
                required_input_failed_count: 0,
                required_input_unready_count: 0,
                required_input_present_count: 4,
                required_input_passed_count: 4,
                all_required_inputs_present: true,
                all_required_inputs_passed: true,
                blocking_reason_count: 0,
                blocking_reason_key_count: 0,
                blocking_reason_family_count: 0,
                blocking_reason_key_counts: BTreeMap::new(),
                blocking_reason_family_counts: BTreeMap::new(),
                degradation_hold_count: 0,
                degradation_hold_subjects: Vec::new(),
                queue_guard_headroom_band_counts: BTreeMap::new(),
                queue_guard_headroom_missing_count: 0,
                queue_guard_tight_hold_count: 0,
                queue_pressure_hold_count: 0,
                queue_hold_input_count: 0,
                queue_hold_host_count: 0,
                queue_guard_limiting_path_counts: BTreeMap::new(),
                interop_profile_contract_passed: true,
                interop_profile_catalog_contract_passed: true,
                interop_profile_catalog_schema_version: 1,
                interop_profile_catalog_host_labels: vec![
                    "linux".to_owned(),
                    "macos".to_owned(),
                    "windows".to_owned(),
                ],
                interop_profile_catalog_source_lane:
                    UDP_INTEROP_PROFILE_CATALOG_SOURCE_LANE_COMPATIBLE_HOST.to_owned(),
                interop_required_no_silent_fallback_profile_slugs:
                    udp_wan_lab_required_no_silent_fallback_profile_slugs()
                        .into_iter()
                        .map(str::to_owned)
                        .collect(),
                interop_failed_profile_slugs: Vec::new(),
                interop_failed_profile_count: 0,
                explicit_fallback_profile_count: 3,
                policy_disabled_fallback_surface_passed: Some(true),
                transport_fallback_integrity_surface_passed: Some(true),
                blocking_reasons: Vec::new(),
                blocking_reason_keys: Vec::new(),
                blocking_reason_families: Vec::new(),
            }),
        }
    }

    fn ready_validation(label: &str) -> LoadedValidationInput {
        LoadedSummaryInput {
            input_label: label.to_owned(),
            present: true,
            parse_error: None,
            summary: Some(RolloutValidationSummaryInput {
                summary_version: Some(UDP_ROLLOUT_VALIDATION_SUMMARY_VERSION),
                profile: "readiness".to_owned(),
                all_passed: true,
                cli_surface_consistency_passed: true,
                startup_contract_validation_passed: true,
                negotiated_limit_validation_passed: true,
                selected_datagram_lifecycle_passed: true,
                mtu_ceiling_delivery_stable: true,
                fallback_flow_guard_rejection_stable: true,
                udp_blocked_fallback_surface_passed: true,
                repeated_queue_pressure_sticky: true,
                queue_pressure_surface_passed: true,
                reordering_no_silent_fallback_passed: true,
                prolonged_impairment_no_silent_fallback: true,
                prolonged_repeated_impairment_stable: true,
                longer_impairment_recovery_stable: true,
                shutdown_sequence_stable: true,
                post_close_rejection_stable: true,
                associated_stream_guard_recovery_stable: true,
                oversized_payload_guard_recovery_stable: true,
                reordered_after_close_rejection_stable: true,
                clean_shutdown_stable: true,
                policy_disabled_fallback_surface_passed: Some(true),
                policy_disabled_fallback_round_trip_stable: true,
                transport_fallback_integrity_surface_passed: true,
                rollout_surface_passed: Some(true),
                surface_count_total: 9,
                surface_count_passed: 9,
                surface_count_failed: 0,
                failed_surface_keys: Vec::new(),
                command_count: 4,
                passed_command_count: 4,
                failed_command_count: 0,
                queue_guard_headroom_band: Some("healthy".to_owned()),
                queue_guard_headroom_missing_count: 0,
                queue_guard_limiting_path: Some("queue_recovery_send".to_owned()),
                sticky_selection_surface_passed: true,
                degradation_surface_passed: true,
            }),
        }
    }

    #[test]
    fn release_candidate_hardening_is_ready_with_consolidation_and_validations() {
        let summary = build_release_candidate_hardening_summary(
            ready_release_candidate_consolidation(),
            vec![
                ready_validation("linux_validation"),
                ready_validation("macos_validation"),
                ready_validation("windows_validation"),
            ],
        );

        assert_eq!(summary.verdict, "ready");
        assert_eq!(summary.gate_state, "passed");
        assert_eq!(
            summary.comparison_schema_version,
            UDP_ROLLOUT_OPERATOR_VERDICT_SCHEMA_VERSION
        );
        assert_eq!(
            summary.decision_scope,
            UDP_ROLLOUT_DECISION_SCOPE_RELEASE_CANDIDATE_HARDENING
        );
        assert_eq!(
            summary.summary_version,
            UDP_RELEASE_CANDIDATE_HARDENING_SUMMARY_VERSION
        );
        assert_eq!(summary.required_input_count, 4);
        assert_eq!(summary.required_input_missing_count, 0);
        assert_eq!(summary.validation_count, 3);
        assert_eq!(summary.validation_passed_count, 3);
        assert_eq!(summary.validation_mtu_ceiling_passed_count, 3);
        assert_eq!(
            summary.validation_fallback_flow_guard_rejection_passed_count,
            3
        );
        assert_eq!(
            summary.validation_oversized_payload_guard_recovery_passed_count,
            3
        );
        assert_eq!(summary.queue_hold_input_count, 0);
        assert_eq!(summary.queue_hold_host_count, 0);
        assert_eq!(summary.interop_failed_profile_count, 0);
        assert_eq!(
            summary
                .interop_required_no_silent_fallback_profile_slugs
                .iter()
                .cloned()
                .collect::<BTreeSet<_>>(),
            udp_wan_lab_required_no_silent_fallback_profile_slugs()
                .into_iter()
                .map(str::to_owned)
                .collect::<BTreeSet<_>>()
        );
    }

    #[test]
    fn release_candidate_hardening_holds_without_linux_validation() {
        let summary = build_release_candidate_hardening_summary(
            ready_release_candidate_consolidation(),
            vec![
                LoadedSummaryInput {
                    input_label: "linux_validation".to_owned(),
                    present: false,
                    parse_error: None,
                    summary: None,
                },
                ready_validation("macos_validation"),
                ready_validation("windows_validation"),
            ],
        );

        assert_eq!(summary.verdict, "hold");
        assert_eq!(summary.required_input_missing_count, 1);
        assert!(
            summary
                .missing_required_inputs
                .iter()
                .any(|value| value == "linux_validation")
        );
    }

    #[test]
    fn release_candidate_hardening_fails_closed_when_consolidation_contract_drifts() {
        let mut consolidation = ready_release_candidate_consolidation();
        consolidation
            .summary
            .as_mut()
            .expect("ready consolidation should exist")
            .interop_profile_catalog_host_labels = vec!["linux".to_owned(), "macos".to_owned()];

        let summary = build_release_candidate_hardening_summary(
            consolidation,
            vec![
                ready_validation("linux_validation"),
                ready_validation("macos_validation"),
                ready_validation("windows_validation"),
            ],
        );

        assert_eq!(summary.verdict, "hold");
        assert_eq!(summary.gate_state_reason, "summary_contract_invalid");
        assert!(
            summary
                .blocking_reasons
                .iter()
                .any(|reason| reason == "release_candidate_consolidation_summary_contract_invalid")
        );
    }

    #[test]
    fn release_candidate_hardening_projects_fallback_flow_guard_failures() {
        let mut linux = ready_validation("linux_validation");
        let summary = linux
            .summary
            .as_mut()
            .expect("ready validation summary should exist");
        summary.all_passed = false;
        summary.fallback_flow_guard_rejection_stable = false;
        summary.transport_fallback_integrity_surface_passed = false;
        summary.degradation_surface_passed = false;
        summary.rollout_surface_passed = Some(false);
        summary.surface_count_failed = 1;
        summary.surface_count_passed = 8;
        summary.failed_command_count = 1;
        summary.passed_command_count = 3;
        summary.failed_surface_keys = vec!["fallback_flow_guard_rejection_stable".to_owned()];

        let hardening = build_release_candidate_hardening_summary(
            ready_release_candidate_consolidation(),
            vec![
                linux,
                ready_validation("macos_validation"),
                ready_validation("windows_validation"),
            ],
        );

        assert_eq!(hardening.verdict, "hold");
        assert_eq!(
            hardening.validation_fallback_flow_guard_rejection_passed_count,
            2
        );
        assert!(
            hardening
                .blocking_reason_keys
                .iter()
                .any(|key| key == "fallback_flow_guard_rejection_surface_failed")
        );
    }

    #[test]
    fn release_candidate_hardening_projects_policy_disabled_fallback_round_trip_failures() {
        let mut linux = ready_validation("linux_validation");
        let summary = linux
            .summary
            .as_mut()
            .expect("ready validation summary should exist");
        summary.all_passed = false;
        summary.policy_disabled_fallback_round_trip_stable = false;
        summary.transport_fallback_integrity_surface_passed = false;
        summary.rollout_surface_passed = Some(false);
        summary.surface_count_failed = 1;
        summary.surface_count_passed = 8;
        summary.failed_command_count = 1;
        summary.passed_command_count = 3;
        summary.failed_surface_keys = vec!["policy_disabled_fallback_round_trip_stable".to_owned()];

        let hardening = build_release_candidate_hardening_summary(
            ready_release_candidate_consolidation(),
            vec![
                linux,
                ready_validation("macos_validation"),
                ready_validation("windows_validation"),
            ],
        );

        assert_eq!(hardening.verdict, "hold");
        assert_eq!(
            hardening.validation_policy_disabled_fallback_round_trip_passed_count,
            2
        );
        assert_eq!(
            hardening.policy_disabled_fallback_round_trip_stable,
            Some(false)
        );
        assert!(
            hardening
                .blocking_reason_keys
                .iter()
                .any(|key| key == "policy_disabled_fallback_round_trip_surface_failed")
        );
    }
}
