use ns_testkit::{
    UDP_ROLLOUT_DECISION_SCOPE_HOST, UDP_ROLLOUT_DECISION_SCOPE_MATRIX,
    UDP_ROLLOUT_DECISION_SCOPE_RELEASE_BURN_IN,
    UDP_ROLLOUT_DECISION_SCOPE_RELEASE_CANDIDATE_SIGNOFF, UDP_ROLLOUT_OPERATOR_VERDICT_FAMILY,
    UDP_ROLLOUT_OPERATOR_VERDICT_SCHEMA, UDP_ROLLOUT_OPERATOR_VERDICT_SCHEMA_VERSION,
    prefer_verta_input_path, summarize_rollout_gate_state,
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
struct ReleaseBurnInArgs {
    format: Option<OutputFormat>,
    summary_path: Option<PathBuf>,
    release_candidate_signoff: Option<PathBuf>,
    linux_readiness: Option<PathBuf>,
    macos_readiness: Option<PathBuf>,
    windows_readiness: Option<PathBuf>,
    staged_matrix: Option<PathBuf>,
}

const UDP_RELEASE_CANDIDATE_SIGNOFF_SUMMARY_VERSION: u8 = 5;
const UDP_ROLLOUT_COMPARISON_SUMMARY_VERSION: u8 = 14;
const UDP_ROLLOUT_MATRIX_SUMMARY_VERSION: u8 = 11;
const UDP_RELEASE_BURN_IN_SUMMARY_VERSION: u8 = 2;

#[derive(Debug, Deserialize)]
struct ReleaseCandidateSignoffSummaryInput {
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
    queue_guard_limiting_path_counts: BTreeMap<String, usize>,
    #[serde(default)]
    queue_guard_tight_hold_count: usize,
    #[serde(default)]
    queue_pressure_hold_count: usize,
    #[serde(default)]
    interop_required_no_silent_fallback_profile_slugs: Vec<String>,
    #[serde(default)]
    policy_disabled_fallback_surface_passed: Option<bool>,
    #[serde(default)]
    transport_fallback_integrity_surface_passed: Option<bool>,
    #[serde(default)]
    interop_profile_contract_passed: bool,
    #[serde(default)]
    blocking_reasons: Vec<String>,
}

#[derive(Debug, Deserialize)]
struct ReadinessSummaryInput {
    #[serde(default)]
    summary_version: Option<u8>,
    comparison_schema: String,
    comparison_schema_version: u8,
    verdict_family: String,
    decision_scope: String,
    decision_label: String,
    profile: String,
    host_label: String,
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
    queue_guard_headroom_band: Option<String>,
    #[serde(default)]
    queue_guard_headroom_missing_count: usize,
    #[serde(default)]
    queue_guard_limiting_path: Option<String>,
    #[serde(default)]
    queue_guard_tight_hold_count: usize,
    #[serde(default)]
    queue_pressure_hold_count: usize,
    #[serde(default)]
    interop_required_no_silent_fallback_profile_slugs: Vec<String>,
    #[serde(default)]
    policy_disabled_fallback_surface_passed: Option<bool>,
    #[serde(default)]
    transport_fallback_integrity_surface_passed: Option<bool>,
    #[serde(default)]
    interop_profile_contract_passed: Option<bool>,
    #[serde(default)]
    blocking_reasons: Vec<String>,
}

#[derive(Debug, Deserialize)]
struct StagedRolloutMatrixSummaryInput {
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
    host_labels: Vec<String>,
    #[serde(default)]
    hosts_with_degradation_hold: Vec<String>,
    #[serde(default)]
    degradation_hold_count: usize,
    #[serde(default)]
    degradation_hold_subjects: Vec<String>,
    #[serde(default)]
    queue_guard_headroom_band_counts: BTreeMap<String, usize>,
    #[serde(default)]
    queue_guard_headroom_missing_count: usize,
    #[serde(default)]
    queue_guard_limiting_path_counts: BTreeMap<String, usize>,
    #[serde(default)]
    queue_guard_tight_hold_count: usize,
    #[serde(default)]
    queue_pressure_hold_count: usize,
    #[serde(default)]
    interop_required_no_silent_fallback_profile_slugs: Vec<String>,
    #[serde(default)]
    interop_profile_contract_passed: bool,
    #[serde(default)]
    blocking_reasons: Vec<String>,
}

#[derive(Debug)]
struct LoadedInput<T> {
    present: bool,
    parse_error: Option<String>,
    summary: Option<T>,
}

type LoadedReleaseCandidateSignoffInput = LoadedInput<ReleaseCandidateSignoffSummaryInput>;
type LoadedReadinessInput = LoadedInput<ReadinessSummaryInput>;
type LoadedStagedRolloutMatrixInput = LoadedInput<StagedRolloutMatrixSummaryInput>;

#[derive(Debug, Serialize)]
struct UdpReleaseBurnInSummary {
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
    release_candidate_signoff_present: bool,
    release_candidate_signoff_passed: bool,
    readiness_count: usize,
    readiness_passed_count: usize,
    readiness_failed_count: usize,
    readiness_labels: Vec<String>,
    readiness_host_labels: Vec<String>,
    staged_rollout_matrix_present: bool,
    staged_rollout_matrix_passed: bool,
    degradation_hold_count: usize,
    degradation_hold_subjects: Vec<String>,
    queue_guard_headroom_band_counts: BTreeMap<String, usize>,
    queue_guard_headroom_missing_count: usize,
    queue_guard_tight_hold_count: usize,
    queue_pressure_hold_count: usize,
    queue_guard_limiting_path_counts: BTreeMap<String, usize>,
    interop_profile_contract_passed: bool,
    interop_required_no_silent_fallback_profile_slugs: Vec<String>,
    transport_fallback_integrity_surface_passed: Option<bool>,
    blocking_reasons: Vec<String>,
    blocking_reason_keys: Vec<String>,
    blocking_reason_families: Vec<String>,
    advisory_reasons: Vec<String>,
}

fn main() -> Result<(), Box<dyn std::error::Error>> {
    let args = parse_args(env::args().skip(1))?;
    let release_candidate_signoff_path = args
        .release_candidate_signoff
        .unwrap_or_else(default_release_candidate_signoff_input);
    let linux_readiness_path = args
        .linux_readiness
        .unwrap_or_else(default_linux_readiness_input);
    let macos_readiness_path = args
        .macos_readiness
        .unwrap_or_else(default_macos_readiness_input);
    let windows_readiness_path = args
        .windows_readiness
        .unwrap_or_else(default_windows_readiness_input);
    let staged_matrix_path = args
        .staged_matrix
        .unwrap_or_else(default_staged_matrix_input);
    let summary = build_release_burn_in_summary(
        load_input::<ReleaseCandidateSignoffSummaryInput>(&release_candidate_signoff_path),
        load_input::<ReadinessSummaryInput>(&linux_readiness_path),
        load_input::<ReadinessSummaryInput>(&macos_readiness_path),
        load_input::<ReadinessSummaryInput>(&windows_readiness_path),
        load_input::<StagedRolloutMatrixSummaryInput>(&staged_matrix_path),
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
        return Err("udp release burn-in is not ready".into());
    }

    Ok(())
}

fn build_release_burn_in_summary(
    release_candidate_signoff: LoadedReleaseCandidateSignoffInput,
    linux_readiness: LoadedReadinessInput,
    macos_readiness: LoadedReadinessInput,
    windows_readiness: LoadedReadinessInput,
    staged_rollout_matrix: LoadedStagedRolloutMatrixInput,
) -> UdpReleaseBurnInSummary {
    let required_inputs = vec![
        "release_candidate_signoff".to_owned(),
        "linux_readiness".to_owned(),
        "macos_readiness".to_owned(),
        "windows_readiness".to_owned(),
        "staged_rollout_matrix".to_owned(),
    ];
    let considered_inputs = required_inputs.clone();
    let readiness_labels = vec![
        "linux_readiness".to_owned(),
        "macos_readiness".to_owned(),
        "windows_readiness".to_owned(),
    ];

    let mut present_required_inputs = BTreeSet::new();
    let mut passed_required_inputs = BTreeSet::new();
    let mut blocking_reasons = Vec::new();
    let mut blocking_reason_key_counts = BTreeMap::new();
    let mut blocking_reason_family_counts = BTreeMap::new();
    let advisory_reasons = Vec::new();
    let mut degradation_hold_subjects = Vec::new();
    let mut queue_guard_headroom_band_counts = BTreeMap::new();
    let mut queue_guard_limiting_path_counts = BTreeMap::new();
    let mut queue_guard_headroom_missing_count = 0usize;
    let mut queue_guard_tight_hold_count = 0usize;
    let mut queue_pressure_hold_count = 0usize;
    let mut all_consumed_inputs_contract_valid = true;
    let mut readiness_host_labels = Vec::new();
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
    let mut interop_required_no_silent_fallback_profile_set = BTreeSet::new();

    let release_candidate_signoff_present = release_candidate_signoff.present;
    if release_candidate_signoff_present {
        present_required_inputs.insert("release_candidate_signoff".to_owned());
    }
    let release_candidate_signoff_passed = match release_candidate_signoff.summary.as_ref() {
        Some(summary)
            if release_candidate_signoff.present
                && release_candidate_signoff.parse_error.is_none()
                && release_candidate_signoff_summary_contract_valid(summary)
                && summary.verdict == "ready"
                && summary.evidence_state == "complete"
                && summary.gate_state == "passed"
                && summary.active_fuzz_required
                && summary.all_required_inputs_present
                && summary.all_required_inputs_passed
                && summary.blocking_reason_count == 0
                && summary.degradation_hold_count == 0
                && summary.queue_guard_headroom_missing_count == 0
                && summary.queue_guard_tight_hold_count == 0
                && summary.queue_pressure_hold_count == 0
                && summary.policy_disabled_fallback_surface_passed == Some(true)
                && summary.transport_fallback_integrity_surface_passed == Some(true)
                && summary.interop_profile_contract_passed =>
        {
            merge_counts(
                &mut queue_guard_headroom_band_counts,
                &summary.queue_guard_headroom_band_counts,
            );
            queue_guard_headroom_missing_count += summary.queue_guard_headroom_missing_count;
            merge_counts(
                &mut queue_guard_limiting_path_counts,
                &summary.queue_guard_limiting_path_counts,
            );
            queue_guard_tight_hold_count += summary.queue_guard_tight_hold_count;
            queue_pressure_hold_count += summary.queue_pressure_hold_count;
            interop_required_no_silent_fallback_profile_set.extend(
                summary
                    .interop_required_no_silent_fallback_profile_slugs
                    .iter()
                    .cloned(),
            );
            passed_required_inputs.insert("release_candidate_signoff".to_owned());
            true
        }
        Some(summary) => {
            merge_counts(
                &mut queue_guard_headroom_band_counts,
                &summary.queue_guard_headroom_band_counts,
            );
            queue_guard_headroom_missing_count += summary.queue_guard_headroom_missing_count;
            merge_counts(
                &mut queue_guard_limiting_path_counts,
                &summary.queue_guard_limiting_path_counts,
            );
            queue_guard_tight_hold_count += summary.queue_guard_tight_hold_count;
            queue_pressure_hold_count += summary.queue_pressure_hold_count;
            interop_required_no_silent_fallback_profile_set.extend(
                summary
                    .interop_required_no_silent_fallback_profile_slugs
                    .iter()
                    .cloned(),
            );
            false
        }
        None => false,
    };

    if !release_candidate_signoff.present {
        push_reason(
            &mut blocking_reasons,
            &mut blocking_reason_key_counts,
            &mut blocking_reason_family_counts,
            "missing_release_candidate_signoff_summary",
            "missing_required_input",
            "summary_presence",
        );
    } else if let Some(error) = release_candidate_signoff.parse_error.as_ref() {
        all_consumed_inputs_contract_valid = false;
        push_reason(
            &mut blocking_reasons,
            &mut blocking_reason_key_counts,
            &mut blocking_reason_family_counts,
            &format!("release_candidate_signoff_parse_error:{error}"),
            "input_parse_error",
            "summary_contract",
        );
    } else if let Some(summary) = release_candidate_signoff.summary.as_ref() {
        if !release_candidate_signoff_summary_contract_valid(summary) {
            all_consumed_inputs_contract_valid = false;
            push_reason(
                &mut blocking_reasons,
                &mut blocking_reason_key_counts,
                &mut blocking_reason_family_counts,
                "release_candidate_signoff_summary_contract_invalid",
                "input_contract_invalid",
                "summary_contract",
            );
        } else if !release_candidate_signoff_passed {
            if summary.degradation_hold_count > 0 {
                degradation_hold_subjects.push("release_candidate_signoff".to_owned());
                degradation_hold_subjects.extend(summary.degradation_hold_subjects.iter().cloned());
            }
            push_reason(
                &mut blocking_reasons,
                &mut blocking_reason_key_counts,
                &mut blocking_reason_family_counts,
                "release_candidate_signoff_not_ready",
                "input_not_ready",
                if summary.degradation_hold_count > 0 {
                    "degradation"
                } else {
                    "gating"
                },
            );
        }
    }

    let mut process_readiness = |label: &str, input: &LoadedReadinessInput| -> bool {
        if input.present {
            present_required_inputs.insert(label.to_owned());
        }
        let passed = match input.summary.as_ref() {
            Some(summary)
                if input.present
                    && input.parse_error.is_none()
                    && readiness_summary_contract_valid(summary)
                    && summary.verdict == "ready"
                    && summary.evidence_state == "complete"
                    && summary.gate_state == "passed"
                    && !summary.active_fuzz_required
                    && summary.all_required_inputs_present
                    && summary.all_required_inputs_passed
                    && summary.blocking_reason_count == 0
                    && summary.degradation_hold_count == 0
                    && summary.queue_guard_headroom_missing_count == 0
                    && summary.queue_guard_tight_hold_count == 0
                    && summary.queue_pressure_hold_count == 0
                    && summary.policy_disabled_fallback_surface_passed == Some(true)
                    && summary.transport_fallback_integrity_surface_passed == Some(true)
                    && summary.interop_profile_contract_passed == Some(true) =>
            {
                readiness_host_labels.push(summary.host_label.clone());
                if let Some(band) = summary.queue_guard_headroom_band.as_ref() {
                    *queue_guard_headroom_band_counts
                        .entry(band.clone())
                        .or_insert(0) += 1;
                }
                queue_guard_headroom_missing_count += summary.queue_guard_headroom_missing_count;
                if let Some(path) = summary.queue_guard_limiting_path.as_ref() {
                    *queue_guard_limiting_path_counts
                        .entry(path.clone())
                        .or_insert(0) += 1;
                }
                queue_guard_tight_hold_count += summary.queue_guard_tight_hold_count;
                queue_pressure_hold_count += summary.queue_pressure_hold_count;
                interop_required_no_silent_fallback_profile_set.extend(
                    summary
                        .interop_required_no_silent_fallback_profile_slugs
                        .iter()
                        .cloned(),
                );
                passed_required_inputs.insert(label.to_owned());
                true
            }
            Some(summary) => {
                readiness_host_labels.push(summary.host_label.clone());
                if let Some(band) = summary.queue_guard_headroom_band.as_ref() {
                    *queue_guard_headroom_band_counts
                        .entry(band.clone())
                        .or_insert(0) += 1;
                }
                queue_guard_headroom_missing_count += summary.queue_guard_headroom_missing_count;
                if let Some(path) = summary.queue_guard_limiting_path.as_ref() {
                    *queue_guard_limiting_path_counts
                        .entry(path.clone())
                        .or_insert(0) += 1;
                }
                queue_guard_tight_hold_count += summary.queue_guard_tight_hold_count;
                queue_pressure_hold_count += summary.queue_pressure_hold_count;
                interop_required_no_silent_fallback_profile_set.extend(
                    summary
                        .interop_required_no_silent_fallback_profile_slugs
                        .iter()
                        .cloned(),
                );
                false
            }
            None => false,
        };

        if !input.present {
            push_reason(
                &mut blocking_reasons,
                &mut blocking_reason_key_counts,
                &mut blocking_reason_family_counts,
                &format!("missing_{label}_summary"),
                "missing_required_input",
                "summary_presence",
            );
        } else if let Some(error) = input.parse_error.as_ref() {
            all_consumed_inputs_contract_valid = false;
            push_reason(
                &mut blocking_reasons,
                &mut blocking_reason_key_counts,
                &mut blocking_reason_family_counts,
                &format!("{label}_parse_error:{error}"),
                "input_parse_error",
                "summary_contract",
            );
        } else if let Some(summary) = input.summary.as_ref() {
            if !readiness_summary_contract_valid(summary) {
                all_consumed_inputs_contract_valid = false;
                push_reason(
                    &mut blocking_reasons,
                    &mut blocking_reason_key_counts,
                    &mut blocking_reason_family_counts,
                    &format!("{label}_summary_contract_invalid"),
                    "input_contract_invalid",
                    "summary_contract",
                );
            } else if !passed {
                if summary.degradation_hold_count > 0 {
                    degradation_hold_subjects.push(label.to_owned());
                    degradation_hold_subjects
                        .extend(summary.degradation_hold_subjects.iter().cloned());
                }
                push_reason(
                    &mut blocking_reasons,
                    &mut blocking_reason_key_counts,
                    &mut blocking_reason_family_counts,
                    &format!("{label}_not_ready"),
                    "input_not_ready",
                    if summary.degradation_hold_count > 0 {
                        "degradation"
                    } else {
                        "gating"
                    },
                );
            }
        }

        passed
    };

    let linux_readiness_passed = process_readiness("linux_readiness", &linux_readiness);
    let macos_readiness_passed = process_readiness("macos_readiness", &macos_readiness);
    let windows_readiness_passed = process_readiness("windows_readiness", &windows_readiness);

    let staged_rollout_matrix_present = staged_rollout_matrix.present;
    if staged_rollout_matrix_present {
        present_required_inputs.insert("staged_rollout_matrix".to_owned());
    }
    let staged_rollout_matrix_passed = match staged_rollout_matrix.summary.as_ref() {
        Some(summary)
            if staged_rollout_matrix.present
                && staged_rollout_matrix.parse_error.is_none()
                && staged_rollout_matrix_summary_contract_valid(summary)
                && summary.verdict == "ready"
                && summary.evidence_state == "complete"
                && summary.gate_state == "passed"
                && summary.active_fuzz_required
                && summary.all_required_inputs_present
                && summary.all_required_inputs_passed
                && summary.blocking_reason_count == 0
                && summary.degradation_hold_count == 0
                && summary.queue_guard_headroom_missing_count == 0
                && summary.queue_guard_tight_hold_count == 0
                && summary.queue_pressure_hold_count == 0
                && summary.interop_profile_contract_passed =>
        {
            merge_counts(
                &mut queue_guard_headroom_band_counts,
                &summary.queue_guard_headroom_band_counts,
            );
            queue_guard_headroom_missing_count += summary.queue_guard_headroom_missing_count;
            merge_counts(
                &mut queue_guard_limiting_path_counts,
                &summary.queue_guard_limiting_path_counts,
            );
            queue_guard_tight_hold_count += summary.queue_guard_tight_hold_count;
            queue_pressure_hold_count += summary.queue_pressure_hold_count;
            interop_required_no_silent_fallback_profile_set.extend(
                summary
                    .interop_required_no_silent_fallback_profile_slugs
                    .iter()
                    .cloned(),
            );
            passed_required_inputs.insert("staged_rollout_matrix".to_owned());
            true
        }
        Some(summary) => {
            merge_counts(
                &mut queue_guard_headroom_band_counts,
                &summary.queue_guard_headroom_band_counts,
            );
            queue_guard_headroom_missing_count += summary.queue_guard_headroom_missing_count;
            merge_counts(
                &mut queue_guard_limiting_path_counts,
                &summary.queue_guard_limiting_path_counts,
            );
            queue_guard_tight_hold_count += summary.queue_guard_tight_hold_count;
            queue_pressure_hold_count += summary.queue_pressure_hold_count;
            interop_required_no_silent_fallback_profile_set.extend(
                summary
                    .interop_required_no_silent_fallback_profile_slugs
                    .iter()
                    .cloned(),
            );
            false
        }
        None => false,
    };

    if !staged_rollout_matrix.present {
        push_reason(
            &mut blocking_reasons,
            &mut blocking_reason_key_counts,
            &mut blocking_reason_family_counts,
            "missing_staged_rollout_matrix_summary",
            "missing_required_input",
            "summary_presence",
        );
    } else if let Some(error) = staged_rollout_matrix.parse_error.as_ref() {
        all_consumed_inputs_contract_valid = false;
        push_reason(
            &mut blocking_reasons,
            &mut blocking_reason_key_counts,
            &mut blocking_reason_family_counts,
            &format!("staged_rollout_matrix_parse_error:{error}"),
            "input_parse_error",
            "summary_contract",
        );
    } else if let Some(summary) = staged_rollout_matrix.summary.as_ref() {
        if !staged_rollout_matrix_summary_contract_valid(summary) {
            all_consumed_inputs_contract_valid = false;
            push_reason(
                &mut blocking_reasons,
                &mut blocking_reason_key_counts,
                &mut blocking_reason_family_counts,
                "staged_rollout_matrix_summary_contract_invalid",
                "input_contract_invalid",
                "summary_contract",
            );
        } else if !staged_rollout_matrix_passed {
            if summary.degradation_hold_count > 0 {
                degradation_hold_subjects.push("staged_rollout_matrix".to_owned());
                degradation_hold_subjects.extend(summary.degradation_hold_subjects.iter().cloned());
            }
            push_reason(
                &mut blocking_reasons,
                &mut blocking_reason_key_counts,
                &mut blocking_reason_family_counts,
                "staged_rollout_matrix_not_ready",
                "input_not_ready",
                if summary.degradation_hold_count > 0 {
                    "degradation"
                } else {
                    "gating"
                },
            );
        }
    }

    degradation_hold_subjects.sort();
    degradation_hold_subjects.dedup();
    readiness_host_labels.sort();
    readiness_host_labels.dedup();

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
    let degradation_hold_count = degradation_hold_subjects.len();
    let readiness_passed_count = usize::from(linux_readiness_passed)
        + usize::from(macos_readiness_passed)
        + usize::from(windows_readiness_passed);
    let readiness_failed_count = readiness_labels
        .len()
        .saturating_sub(readiness_passed_count);

    let interop_profile_contract_passed =
        release_candidate_signoff
            .summary
            .as_ref()
            .is_some_and(|summary| {
                release_candidate_signoff_summary_contract_valid(summary)
                    && summary.interop_profile_contract_passed
            })
            && linux_readiness.summary.as_ref().is_some_and(|summary| {
                readiness_summary_contract_valid(summary)
                    && summary.interop_profile_contract_passed == Some(true)
            })
            && macos_readiness.summary.as_ref().is_some_and(|summary| {
                readiness_summary_contract_valid(summary)
                    && summary.interop_profile_contract_passed == Some(true)
            })
            && windows_readiness.summary.as_ref().is_some_and(|summary| {
                readiness_summary_contract_valid(summary)
                    && summary.interop_profile_contract_passed == Some(true)
            })
            && staged_rollout_matrix
                .summary
                .as_ref()
                .is_some_and(|summary| {
                    staged_rollout_matrix_summary_contract_valid(summary)
                        && summary.interop_profile_contract_passed
                });
    if !interop_profile_contract_passed {
        push_reason(
            &mut blocking_reasons,
            &mut blocking_reason_key_counts,
            &mut blocking_reason_family_counts,
            "release_burn_in_interop_profile_contract_invalid",
            "interop_profile_contract_invalid",
            "summary_contract",
        );
    }
    if interop_required_no_silent_fallback_profile_set
        != expected_required_no_silent_fallback_profile_set
    {
        push_reason(
            &mut blocking_reasons,
            &mut blocking_reason_key_counts,
            &mut blocking_reason_family_counts,
            "release_burn_in_interop_required_no_silent_fallback_profile_set_mismatch",
            "interop_required_no_silent_fallback_profile_set_mismatch",
            "summary_contract",
        );
    }
    if queue_guard_headroom_missing_count > 0 {
        push_reason(
            &mut blocking_reasons,
            &mut blocking_reason_key_counts,
            &mut blocking_reason_family_counts,
            "queue_guard_headroom_missing",
            "queue_guard_headroom_missing",
            "capacity",
        );
    }
    if queue_pressure_hold_count > 0 {
        push_reason(
            &mut blocking_reasons,
            &mut blocking_reason_key_counts,
            &mut blocking_reason_family_counts,
            "release_burn_in_queue_pressure_surface_failed",
            "queue_pressure_surface_failed",
            "capacity",
        );
    }
    if queue_guard_tight_hold_count > 0 {
        push_reason(
            &mut blocking_reasons,
            &mut blocking_reason_key_counts,
            &mut blocking_reason_family_counts,
            "queue_guard_headroom_tight",
            "queue_guard_headroom_tight",
            "capacity",
        );
    }

    let transport_fallback_integrity_surface_passed = match (
        release_candidate_signoff
            .summary
            .as_ref()
            .and_then(|summary| summary.transport_fallback_integrity_surface_passed),
        linux_readiness
            .summary
            .as_ref()
            .and_then(|summary| summary.transport_fallback_integrity_surface_passed),
        macos_readiness
            .summary
            .as_ref()
            .and_then(|summary| summary.transport_fallback_integrity_surface_passed),
        windows_readiness
            .summary
            .as_ref()
            .and_then(|summary| summary.transport_fallback_integrity_surface_passed),
    ) {
        (Some(release_candidate), Some(linux), Some(macos), Some(windows))
            if release_candidate && linux && macos && windows =>
        {
            Some(true)
        }
        _ => None,
    };

    let blocking_reason_count = blocking_reasons.len();
    let blocking_reason_key_count = blocking_reason_key_counts.len();
    let blocking_reason_family_count = blocking_reason_family_counts.len();
    let evidence_state = if all_required_inputs_present && all_consumed_inputs_contract_valid {
        "complete"
    } else {
        "incomplete"
    };
    let verdict = if all_required_inputs_passed
        && blocking_reason_count == 0
        && degradation_hold_count == 0
        && queue_guard_tight_hold_count == 0
    {
        "ready"
    } else {
        "hold"
    };
    let gate_state = if verdict == "ready" {
        "passed"
    } else {
        "blocked"
    };
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
    let interop_required_no_silent_fallback_profile_slugs =
        interop_required_no_silent_fallback_profile_set
            .into_iter()
            .collect::<Vec<_>>();

    UdpReleaseBurnInSummary {
        summary_version: UDP_RELEASE_BURN_IN_SUMMARY_VERSION,
        comparison_schema: UDP_ROLLOUT_OPERATOR_VERDICT_SCHEMA,
        comparison_schema_version: UDP_ROLLOUT_OPERATOR_VERDICT_SCHEMA_VERSION,
        verdict_family: UDP_ROLLOUT_OPERATOR_VERDICT_FAMILY,
        decision_scope: UDP_ROLLOUT_DECISION_SCOPE_RELEASE_BURN_IN,
        decision_label: "release_burn_in",
        profile: "release_burn_in",
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
        release_candidate_signoff_present,
        release_candidate_signoff_passed,
        readiness_count: readiness_labels.len(),
        readiness_passed_count,
        readiness_failed_count,
        readiness_labels,
        readiness_host_labels,
        staged_rollout_matrix_present,
        staged_rollout_matrix_passed,
        degradation_hold_count,
        degradation_hold_subjects,
        queue_guard_headroom_band_counts,
        queue_guard_headroom_missing_count,
        queue_guard_tight_hold_count,
        queue_pressure_hold_count,
        queue_guard_limiting_path_counts,
        interop_profile_contract_passed,
        interop_required_no_silent_fallback_profile_slugs,
        transport_fallback_integrity_surface_passed,
        blocking_reasons,
        blocking_reason_keys,
        blocking_reason_families,
        advisory_reasons,
    }
}

fn release_candidate_signoff_summary_contract_valid(
    summary: &ReleaseCandidateSignoffSummaryInput,
) -> bool {
    let expected_inputs = vec![
        "release_prep".to_owned(),
        "windows_readiness".to_owned(),
        "windows_interop".to_owned(),
        "macos_interop".to_owned(),
    ];
    let expected_required_no_silent_fallback_profile_set =
        udp_wan_lab_required_no_silent_fallback_profile_slugs()
            .into_iter()
            .map(str::to_owned)
            .collect::<BTreeSet<_>>();
    let actual_required_no_silent_fallback_profile_set = summary
        .interop_required_no_silent_fallback_profile_slugs
        .iter()
        .cloned()
        .collect::<BTreeSet<_>>();
    let (expected_reason, expected_family) = summarize_rollout_gate_state(
        summary.required_input_missing_count,
        summary
            .blocking_reason_family_counts
            .get("summary_contract")
            .copied()
            .unwrap_or(0),
        summary.required_input_unready_count,
        summary.degradation_hold_count,
        summary.blocking_reason_count,
    );
    summary.summary_version == Some(UDP_RELEASE_CANDIDATE_SIGNOFF_SUMMARY_VERSION)
        && summary.comparison_schema == UDP_ROLLOUT_OPERATOR_VERDICT_SCHEMA
        && summary.comparison_schema_version == UDP_ROLLOUT_OPERATOR_VERDICT_SCHEMA_VERSION
        && summary.verdict_family == UDP_ROLLOUT_OPERATOR_VERDICT_FAMILY
        && summary.decision_scope == UDP_ROLLOUT_DECISION_SCOPE_RELEASE_CANDIDATE_SIGNOFF
        && summary.decision_label == "release_candidate_signoff"
        && summary.profile == "release_candidate_signoff"
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
        && summary.queue_guard_tight_hold_count
            == summary
                .queue_guard_headroom_band_counts
                .get("tight")
                .copied()
                .unwrap_or(0)
        && summary.queue_pressure_hold_count <= 2
        && summary
            .interop_required_no_silent_fallback_profile_slugs
            .len()
            == expected_required_no_silent_fallback_profile_set.len()
        && actual_required_no_silent_fallback_profile_set
            == expected_required_no_silent_fallback_profile_set
        && summary.gate_state_reason == expected_reason
        && summary.gate_state_reason_family == expected_family
        && summary.gate_state
            == if summary.verdict == "ready" {
                "passed"
            } else {
                "blocked"
            }
        && !(summary.verdict == "ready"
            && (summary.blocking_reason_count != 0
                || summary.degradation_hold_count != 0
                || !summary.missing_required_inputs.is_empty()
                || summary.queue_guard_tight_hold_count != 0
                || summary.queue_pressure_hold_count != 0
                || summary.queue_guard_headroom_missing_count != 0
                || summary.policy_disabled_fallback_surface_passed != Some(true)
                || summary.transport_fallback_integrity_surface_passed != Some(true)
                || !summary.interop_profile_contract_passed))
}

fn readiness_summary_contract_valid(summary: &ReadinessSummaryInput) -> bool {
    let expected_required_inputs = vec![
        "smoke".to_owned(),
        "perf".to_owned(),
        "interop".to_owned(),
        "rollout_validation".to_owned(),
    ];
    let expected_considered_inputs = vec![
        "smoke".to_owned(),
        "perf".to_owned(),
        "interop".to_owned(),
        "rollout_validation".to_owned(),
        "active_fuzz".to_owned(),
    ];
    let expected_required_no_silent_fallback_profile_set =
        udp_wan_lab_required_no_silent_fallback_profile_slugs()
            .into_iter()
            .map(str::to_owned)
            .collect::<BTreeSet<_>>();
    let actual_required_no_silent_fallback_profile_set = summary
        .interop_required_no_silent_fallback_profile_slugs
        .iter()
        .cloned()
        .collect::<BTreeSet<_>>();
    let (expected_reason, expected_family) = summarize_rollout_gate_state(
        summary.required_input_missing_count,
        summary
            .blocking_reason_family_counts
            .get("summary_contract")
            .copied()
            .unwrap_or(0),
        summary.required_input_unready_count,
        summary.degradation_hold_count,
        summary.blocking_reason_count,
    );
    summary.summary_version == Some(UDP_ROLLOUT_COMPARISON_SUMMARY_VERSION)
        && summary.comparison_schema == UDP_ROLLOUT_OPERATOR_VERDICT_SCHEMA
        && summary.comparison_schema_version == UDP_ROLLOUT_OPERATOR_VERDICT_SCHEMA_VERSION
        && summary.verdict_family == UDP_ROLLOUT_OPERATOR_VERDICT_FAMILY
        && summary.decision_scope == UDP_ROLLOUT_DECISION_SCOPE_HOST
        && summary.profile == "readiness"
        && !summary.decision_label.trim().is_empty()
        && !summary.host_label.trim().is_empty()
        && !summary.active_fuzz_required
        && summary.required_inputs == expected_required_inputs
        && summary.considered_inputs == expected_considered_inputs
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
        && summary.queue_pressure_hold_count <= 1
        && summary
            .interop_required_no_silent_fallback_profile_slugs
            .len()
            == expected_required_no_silent_fallback_profile_set.len()
        && actual_required_no_silent_fallback_profile_set
            == expected_required_no_silent_fallback_profile_set
        && summary.gate_state_reason == expected_reason
        && summary.gate_state_reason_family == expected_family
        && summary.gate_state
            == if summary.verdict == "ready" {
                "passed"
            } else {
                "blocked"
            }
        && !(summary.verdict == "ready"
            && (summary.blocking_reason_count != 0
                || summary.degradation_hold_count != 0
                || !summary.missing_required_inputs.is_empty()
                || summary.queue_guard_tight_hold_count != 0
                || summary.queue_pressure_hold_count != 0
                || summary.queue_guard_headroom_missing_count != 0
                || summary.policy_disabled_fallback_surface_passed != Some(true)
                || summary.transport_fallback_integrity_surface_passed != Some(true)
                || summary.interop_profile_contract_passed != Some(true)))
}

fn staged_rollout_matrix_summary_contract_valid(summary: &StagedRolloutMatrixSummaryInput) -> bool {
    let expected_required_no_silent_fallback_profile_set =
        udp_wan_lab_required_no_silent_fallback_profile_slugs()
            .into_iter()
            .map(str::to_owned)
            .collect::<BTreeSet<_>>();
    let actual_required_no_silent_fallback_profile_set = summary
        .interop_required_no_silent_fallback_profile_slugs
        .iter()
        .cloned()
        .collect::<BTreeSet<_>>();
    let (expected_reason, expected_family) = summarize_rollout_gate_state(
        summary.required_input_missing_count,
        summary
            .blocking_reason_family_counts
            .get("summary_contract")
            .copied()
            .unwrap_or(0),
        summary.required_input_unready_count,
        summary.degradation_hold_count,
        summary.blocking_reason_count,
    );
    let required_set = summary.required_inputs.iter().collect::<BTreeSet<_>>();
    let considered_set = summary.considered_inputs.iter().collect::<BTreeSet<_>>();
    summary.summary_version == Some(UDP_ROLLOUT_MATRIX_SUMMARY_VERSION)
        && summary.comparison_schema == UDP_ROLLOUT_OPERATOR_VERDICT_SCHEMA
        && summary.comparison_schema_version == UDP_ROLLOUT_OPERATOR_VERDICT_SCHEMA_VERSION
        && summary.verdict_family == UDP_ROLLOUT_OPERATOR_VERDICT_FAMILY
        && summary.decision_scope == UDP_ROLLOUT_DECISION_SCOPE_MATRIX
        && summary.profile == "staged_rollout"
        && !summary.decision_label.trim().is_empty()
        && summary.active_fuzz_required
        && summary.required_inputs == summary.considered_inputs
        && rollout_input_identity_consistent(
            &summary.required_inputs,
            &summary.considered_inputs,
            &summary.missing_required_inputs,
            summary.required_input_count,
        )
        && !summary.required_inputs.is_empty()
        && !summary.host_labels.is_empty()
        && required_set == considered_set
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
        && summary.queue_guard_tight_hold_count
            == summary
                .queue_guard_headroom_band_counts
                .get("tight")
                .copied()
                .unwrap_or(0)
        && summary.queue_pressure_hold_count <= summary.host_labels.len()
        && summary
            .interop_required_no_silent_fallback_profile_slugs
            .len()
            == expected_required_no_silent_fallback_profile_set.len()
        && actual_required_no_silent_fallback_profile_set
            == expected_required_no_silent_fallback_profile_set
        && summary
            .hosts_with_degradation_hold
            .iter()
            .all(|host| summary.host_labels.contains(host))
        && summary.gate_state_reason == expected_reason
        && summary.gate_state_reason_family == expected_family
        && summary.gate_state
            == if summary.verdict == "ready" {
                "passed"
            } else {
                "blocked"
            }
        && !(summary.verdict == "ready"
            && (summary.blocking_reason_count != 0
                || summary.degradation_hold_count != 0
                || !summary.missing_required_inputs.is_empty()
                || summary.queue_guard_tight_hold_count != 0
                || summary.queue_pressure_hold_count != 0
                || summary.queue_guard_headroom_missing_count != 0
                || !summary.interop_profile_contract_passed))
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

fn load_input<T>(path: &Path) -> LoadedInput<T>
where
    T: for<'de> Deserialize<'de>,
{
    if !path.exists() {
        return LoadedInput {
            present: false,
            parse_error: None,
            summary: None,
        };
    }
    match fs::read(path)
        .map_err(|error| error.to_string())
        .and_then(|bytes| serde_json::from_slice::<T>(&bytes).map_err(|error| error.to_string()))
    {
        Ok(summary) => LoadedInput {
            present: true,
            parse_error: None,
            summary: Some(summary),
        },
        Err(error) => LoadedInput {
            present: true,
            parse_error: Some(error),
            summary: None,
        },
    }
}

fn print_text_summary(summary: &UdpReleaseBurnInSummary, summary_path: &Path) {
    println!("Verta UDP release burn-in summary:");
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
        "- required_input_missing_count: {}",
        summary.required_input_missing_count
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
        "- release_candidate_signoff: present={} passed={}",
        summary.release_candidate_signoff_present, summary.release_candidate_signoff_passed
    );
    println!(
        "- readiness_counts: total={} passed={} failed={}",
        summary.readiness_count, summary.readiness_passed_count, summary.readiness_failed_count
    );
    println!(
        "- staged_rollout_matrix: present={} passed={}",
        summary.staged_rollout_matrix_present, summary.staged_rollout_matrix_passed
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
        "- interop_profile_contract_passed: {}",
        summary.interop_profile_contract_passed
    );
    println!(
        "- transport_fallback_integrity_surface_passed: {}",
        summary
            .transport_fallback_integrity_surface_passed
            .map(|value| value.to_string())
            .unwrap_or_else(|| "missing".to_owned())
    );
    if summary.missing_required_inputs.is_empty() {
        println!("- missing_required_inputs: none");
    } else {
        println!(
            "- missing_required_inputs: {}",
            summary.missing_required_inputs.join(", ")
        );
    }
    if summary.readiness_host_labels.is_empty() {
        println!("- readiness_host_labels: none");
    } else {
        println!(
            "- readiness_host_labels: {}",
            summary.readiness_host_labels.join(", ")
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
    if summary.degradation_hold_subjects.is_empty() {
        println!("- degradation_hold_subjects: none");
    } else {
        println!(
            "- degradation_hold_subjects: {}",
            summary.degradation_hold_subjects.join(", ")
        );
    }
    if summary.queue_guard_headroom_band_counts.is_empty() {
        println!("- queue_guard_headroom_band_counts: none");
    } else {
        println!(
            "- queue_guard_headroom_band_counts: {}",
            render_counts(&summary.queue_guard_headroom_band_counts)
        );
    }
    if summary.queue_guard_limiting_path_counts.is_empty() {
        println!("- queue_guard_limiting_path_counts: none");
    } else {
        println!(
            "- queue_guard_limiting_path_counts: {}",
            render_counts(&summary.queue_guard_limiting_path_counts)
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
    println!("machine_readable_summary={}", summary_path.display());
}

fn parse_args<I>(mut args: I) -> Result<ReleaseBurnInArgs, String>
where
    I: Iterator<Item = String>,
{
    let mut parsed = ReleaseBurnInArgs::default();
    while let Some(arg) = args.next() {
        match arg.as_str() {
            "--format" => {
                let value = args
                    .next()
                    .ok_or_else(|| "--format requires a value".to_owned())?;
                parsed.format = Some(match value.as_str() {
                    "text" => OutputFormat::Text,
                    "json" => OutputFormat::Json,
                    _ => return Err(help_text()),
                });
            }
            "--summary-path" => {
                parsed.summary_path =
                    Some(PathBuf::from(args.next().ok_or_else(|| {
                        "--summary-path requires a value".to_owned()
                    })?));
            }
            "--release-candidate-signoff" => {
                parsed.release_candidate_signoff =
                    Some(PathBuf::from(args.next().ok_or_else(|| {
                        "--release-candidate-signoff requires a value".to_owned()
                    })?));
            }
            "--linux-readiness" => {
                parsed.linux_readiness =
                    Some(PathBuf::from(args.next().ok_or_else(|| {
                        "--linux-readiness requires a value".to_owned()
                    })?));
            }
            "--macos-readiness" => {
                parsed.macos_readiness =
                    Some(PathBuf::from(args.next().ok_or_else(|| {
                        "--macos-readiness requires a value".to_owned()
                    })?));
            }
            "--windows-readiness" => {
                parsed.windows_readiness =
                    Some(PathBuf::from(args.next().ok_or_else(|| {
                        "--windows-readiness requires a value".to_owned()
                    })?));
            }
            "--staged-matrix" => {
                parsed.staged_matrix =
                    Some(PathBuf::from(args.next().ok_or_else(|| {
                        "--staged-matrix requires a value".to_owned()
                    })?));
            }
            "--help" | "-h" => return Err(help_text()),
            _ => return Err(help_text()),
        }
    }
    Ok(parsed)
}

fn help_text() -> String {
    "Usage: cargo run -p ns-testkit --example udp_release_burn_in -- [--format text|json] [--summary-path <path>] [--release-candidate-signoff <path>] [--linux-readiness <path>] [--macos-readiness <path>] [--windows-readiness <path>] [--staged-matrix <path>]".to_owned()
}

fn default_release_candidate_signoff_input() -> PathBuf {
    prefer_verta_input_path("udp-release-candidate-signoff-summary.json")
}

fn default_linux_readiness_input() -> PathBuf {
    prefer_verta_input_path("udp-rollout-comparison-summary-linux.json")
}

fn default_macos_readiness_input() -> PathBuf {
    prefer_verta_input_path("udp-rollout-comparison-summary-macos.json")
}

fn default_windows_readiness_input() -> PathBuf {
    prefer_verta_input_path("udp-rollout-comparison-summary-windows.json")
}

fn default_staged_matrix_input() -> PathBuf {
    prefer_verta_input_path("udp-rollout-matrix-summary-staged.json")
}

fn default_summary_path() -> PathBuf {
    verta_output_path("udp-release-burn-in-summary.json")
}

fn push_reason(
    reasons: &mut Vec<String>,
    key_counts: &mut BTreeMap<String, usize>,
    family_counts: &mut BTreeMap<String, usize>,
    code: &str,
    reason_key: &str,
    family: &'static str,
) {
    reasons.push(code.to_owned());
    *key_counts.entry(reason_key.to_owned()).or_insert(0) += 1;
    *family_counts.entry(family.to_owned()).or_insert(0) += 1;
}

fn merge_counts(target: &mut BTreeMap<String, usize>, source: &BTreeMap<String, usize>) {
    for (key, value) in source {
        *target.entry(key.clone()).or_insert(0) += value;
    }
}

fn render_counts(counts: &BTreeMap<String, usize>) -> String {
    counts
        .iter()
        .map(|(key, value)| format!("{key}={value}"))
        .collect::<Vec<_>>()
        .join(", ")
}

#[cfg(test)]
mod tests {
    use super::*;

    fn required_profile_slugs() -> Vec<String> {
        let mut values = udp_wan_lab_required_no_silent_fallback_profile_slugs()
            .into_iter()
            .map(str::to_owned)
            .collect::<Vec<_>>();
        values.sort();
        values
    }

    fn ready_release_candidate_signoff() -> LoadedReleaseCandidateSignoffInput {
        LoadedInput {
            present: true,
            parse_error: None,
            summary: Some(ReleaseCandidateSignoffSummaryInput {
                summary_version: Some(UDP_RELEASE_CANDIDATE_SIGNOFF_SUMMARY_VERSION),
                comparison_schema: "udp_rollout_operator_verdict".to_owned(),
                comparison_schema_version: UDP_ROLLOUT_OPERATOR_VERDICT_SCHEMA_VERSION,
                verdict_family: "udp_rollout_operator_decision".to_owned(),
                decision_scope: "release_candidate_signoff".to_owned(),
                decision_label: "release_candidate_signoff".to_owned(),
                profile: "release_candidate_signoff".to_owned(),
                verdict: "ready".to_owned(),
                evidence_state: "complete".to_owned(),
                gate_state: "passed".to_owned(),
                gate_state_reason: "all_required_inputs_passed".to_owned(),
                gate_state_reason_family: "ready".to_owned(),
                active_fuzz_required: true,
                required_inputs: vec![
                    "release_prep".to_owned(),
                    "windows_readiness".to_owned(),
                    "windows_interop".to_owned(),
                    "macos_interop".to_owned(),
                ],
                considered_inputs: vec![
                    "release_prep".to_owned(),
                    "windows_readiness".to_owned(),
                    "windows_interop".to_owned(),
                    "macos_interop".to_owned(),
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
                queue_guard_headroom_band_counts: BTreeMap::from([("healthy".to_owned(), 1usize)]),
                queue_guard_headroom_missing_count: 0,
                queue_guard_limiting_path_counts: BTreeMap::from([(
                    "queue_recovery_send".to_owned(),
                    2usize,
                )]),
                queue_guard_tight_hold_count: 0,
                queue_pressure_hold_count: 0,
                interop_required_no_silent_fallback_profile_slugs: required_profile_slugs(),
                policy_disabled_fallback_surface_passed: Some(true),
                transport_fallback_integrity_surface_passed: Some(true),
                interop_profile_contract_passed: true,
                blocking_reasons: Vec::new(),
            }),
        }
    }

    fn ready_readiness(host_label: &str) -> LoadedReadinessInput {
        LoadedInput {
            present: true,
            parse_error: None,
            summary: Some(ReadinessSummaryInput {
                summary_version: Some(UDP_ROLLOUT_COMPARISON_SUMMARY_VERSION),
                comparison_schema: "udp_rollout_operator_verdict".to_owned(),
                comparison_schema_version: UDP_ROLLOUT_OPERATOR_VERDICT_SCHEMA_VERSION,
                verdict_family: "udp_rollout_operator_decision".to_owned(),
                decision_scope: "host".to_owned(),
                decision_label: format!("{host_label}_readiness"),
                profile: "readiness".to_owned(),
                host_label: host_label.to_owned(),
                verdict: "ready".to_owned(),
                evidence_state: "complete".to_owned(),
                gate_state: "passed".to_owned(),
                gate_state_reason: "all_required_inputs_passed".to_owned(),
                gate_state_reason_family: "ready".to_owned(),
                active_fuzz_required: false,
                required_inputs: vec![
                    "smoke".to_owned(),
                    "perf".to_owned(),
                    "interop".to_owned(),
                    "rollout_validation".to_owned(),
                ],
                considered_inputs: vec![
                    "smoke".to_owned(),
                    "perf".to_owned(),
                    "interop".to_owned(),
                    "rollout_validation".to_owned(),
                    "active_fuzz".to_owned(),
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
                queue_guard_headroom_band: Some("healthy".to_owned()),
                queue_guard_headroom_missing_count: 0,
                queue_guard_limiting_path: Some("queue_recovery_send".to_owned()),
                queue_guard_tight_hold_count: 0,
                queue_pressure_hold_count: 0,
                interop_required_no_silent_fallback_profile_slugs: required_profile_slugs(),
                policy_disabled_fallback_surface_passed: Some(true),
                transport_fallback_integrity_surface_passed: Some(true),
                interop_profile_contract_passed: Some(true),
                blocking_reasons: Vec::new(),
            }),
        }
    }

    fn ready_staged_matrix() -> LoadedStagedRolloutMatrixInput {
        LoadedInput {
            present: true,
            parse_error: None,
            summary: Some(StagedRolloutMatrixSummaryInput {
                summary_version: Some(UDP_ROLLOUT_MATRIX_SUMMARY_VERSION),
                comparison_schema: "udp_rollout_operator_verdict".to_owned(),
                comparison_schema_version: UDP_ROLLOUT_OPERATOR_VERDICT_SCHEMA_VERSION,
                verdict_family: "udp_rollout_operator_decision".to_owned(),
                decision_scope: "matrix".to_owned(),
                decision_label: "staged_rollout_matrix".to_owned(),
                profile: "staged_rollout".to_owned(),
                verdict: "ready".to_owned(),
                evidence_state: "complete".to_owned(),
                gate_state: "passed".to_owned(),
                gate_state_reason: "all_required_inputs_passed".to_owned(),
                gate_state_reason_family: "ready".to_owned(),
                active_fuzz_required: true,
                required_inputs: vec![
                    "ubuntu-latest-staged".to_owned(),
                    "macos-latest-staged".to_owned(),
                ],
                considered_inputs: vec![
                    "ubuntu-latest-staged".to_owned(),
                    "macos-latest-staged".to_owned(),
                ],
                missing_required_inputs: Vec::new(),
                missing_required_input_count: 0,
                required_input_count: 2,
                required_input_missing_count: 0,
                required_input_failed_count: 0,
                required_input_unready_count: 0,
                required_input_present_count: 2,
                required_input_passed_count: 2,
                all_required_inputs_present: true,
                all_required_inputs_passed: true,
                blocking_reason_count: 0,
                blocking_reason_key_count: 0,
                blocking_reason_family_count: 0,
                blocking_reason_key_counts: BTreeMap::new(),
                blocking_reason_family_counts: BTreeMap::new(),
                host_labels: vec![
                    "ubuntu-latest-staged".to_owned(),
                    "macos-latest-staged".to_owned(),
                ],
                hosts_with_degradation_hold: Vec::new(),
                degradation_hold_count: 0,
                degradation_hold_subjects: Vec::new(),
                queue_guard_headroom_band_counts: BTreeMap::from([("healthy".to_owned(), 2usize)]),
                queue_guard_headroom_missing_count: 0,
                queue_guard_limiting_path_counts: BTreeMap::from([(
                    "queue_recovery_send".to_owned(),
                    2usize,
                )]),
                queue_guard_tight_hold_count: 0,
                queue_pressure_hold_count: 0,
                interop_required_no_silent_fallback_profile_slugs: required_profile_slugs(),
                interop_profile_contract_passed: true,
                blocking_reasons: Vec::new(),
            }),
        }
    }

    #[test]
    fn release_burn_in_emits_ready_operator_schema() {
        let summary = build_release_burn_in_summary(
            ready_release_candidate_signoff(),
            ready_readiness("ubuntu-latest-readiness"),
            ready_readiness("macos-latest-readiness"),
            ready_readiness("windows-latest-readiness"),
            ready_staged_matrix(),
        );

        assert_eq!(summary.summary_version, UDP_RELEASE_BURN_IN_SUMMARY_VERSION);
        assert_eq!(
            summary.comparison_schema_version,
            UDP_ROLLOUT_OPERATOR_VERDICT_SCHEMA_VERSION
        );
        assert_eq!(summary.decision_scope, "release_burn_in");
        assert_eq!(summary.verdict, "ready");
        assert_eq!(summary.gate_state, "passed");
        assert_eq!(summary.gate_state_reason, "all_required_inputs_passed");
        assert_eq!(summary.required_input_count, 5);
        assert_eq!(summary.required_input_passed_count, 5);
        assert_eq!(summary.readiness_count, 3);
        assert_eq!(summary.readiness_passed_count, 3);
        assert_eq!(summary.readiness_failed_count, 0);
        assert!(summary.release_candidate_signoff_passed);
        assert!(summary.staged_rollout_matrix_passed);
        assert_eq!(summary.queue_guard_headroom_missing_count, 0);
        assert_eq!(summary.queue_guard_tight_hold_count, 0);
        assert_eq!(summary.queue_pressure_hold_count, 0);
        assert!(summary.interop_profile_contract_passed);
        assert_eq!(
            summary.interop_required_no_silent_fallback_profile_slugs,
            required_profile_slugs()
        );
        assert_eq!(
            summary.transport_fallback_integrity_surface_passed,
            Some(true)
        );
        assert_eq!(
            summary
                .queue_guard_limiting_path_counts
                .get("queue_recovery_send")
                .copied(),
            Some(7)
        );
    }

    #[test]
    fn release_burn_in_fails_closed_without_staged_matrix() {
        let summary = build_release_burn_in_summary(
            ready_release_candidate_signoff(),
            ready_readiness("ubuntu-latest-readiness"),
            ready_readiness("macos-latest-readiness"),
            ready_readiness("windows-latest-readiness"),
            LoadedInput::<StagedRolloutMatrixSummaryInput> {
                present: false,
                parse_error: None,
                summary: None,
            },
        );

        assert_eq!(summary.verdict, "hold");
        assert_eq!(summary.gate_state, "blocked");
        assert_eq!(summary.required_input_missing_count, 1);
        assert_eq!(summary.required_input_unready_count, 0);
        assert!(
            summary
                .missing_required_inputs
                .iter()
                .any(|value| value == "staged_rollout_matrix")
        );
    }
}
