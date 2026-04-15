use ns_testkit::{
    UDP_ROLLOUT_DECISION_SCOPE_DEPLOYMENT_SIGNOFF, UDP_ROLLOUT_DECISION_SCOPE_RELEASE_PREP,
    UDP_ROLLOUT_OPERATOR_VERDICT_FAMILY, UDP_ROLLOUT_OPERATOR_VERDICT_SCHEMA,
    UDP_ROLLOUT_OPERATOR_VERDICT_SCHEMA_VERSION, prefer_verta_input_path,
    rollout_queue_hold_present, summarize_rollout_gate_state,
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
struct ReleasePrepArgs {
    format: Option<OutputFormat>,
    summary_path: Option<PathBuf>,
    deployment_signoff: Option<PathBuf>,
    validations: Vec<PathBuf>,
}

const UDP_DEPLOYMENT_SIGNOFF_SUMMARY_VERSION: u8 = 7;
const UDP_ROLLOUT_VALIDATION_SUMMARY_VERSION: u8 = 19;
const UDP_RELEASE_PREP_SUMMARY_VERSION: u8 = 6;

#[derive(Debug, Deserialize)]
struct DeploymentSignoffSummaryInput {
    #[serde(default)]
    summary_version: Option<u8>,
    comparison_schema: String,
    comparison_schema_version: u8,
    verdict_family: String,
    decision_scope: String,
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
    interop_profile_contract_passed: bool,
    #[serde(default)]
    blocking_reasons: Vec<String>,
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
    repeated_queue_pressure_sticky: bool,
    #[serde(default)]
    queue_pressure_surface_passed: bool,
    #[serde(default)]
    reordering_no_silent_fallback_passed: bool,
    prolonged_impairment_no_silent_fallback: bool,
    prolonged_repeated_impairment_stable: bool,
    longer_impairment_recovery_stable: bool,
    shutdown_sequence_stable: bool,
    post_close_rejection_stable: bool,
    clean_shutdown_stable: bool,
    sticky_selection_surface_passed: bool,
    degradation_surface_passed: bool,
    #[serde(default)]
    policy_disabled_fallback_surface_passed: Option<bool>,
    #[serde(default)]
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
    queue_guard_limiting_path: Option<String>,
}

#[derive(Debug)]
struct LoadedDeploymentSignoffInput {
    present: bool,
    parse_error: Option<String>,
    summary: Option<DeploymentSignoffSummaryInput>,
}

#[derive(Debug)]
struct LoadedValidationInput {
    input_label: String,
    present: bool,
    parse_error: Option<String>,
    summary: Option<RolloutValidationSummaryInput>,
}

#[derive(Debug, Serialize)]
struct UdpReleasePrepSummary {
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
    deployment_signoff_present: bool,
    deployment_signoff_passed: bool,
    validation_count: usize,
    validation_passed_count: usize,
    validation_failed_count: usize,
    validation_labels: Vec<String>,
    validation_command_count_total: usize,
    validation_command_failed_total: usize,
    validation_surface_count_total: usize,
    validation_surface_failed_total: usize,
    degradation_hold_count: usize,
    degradation_hold_subjects: Vec<String>,
    queue_guard_headroom_band_counts: BTreeMap<String, usize>,
    queue_guard_headroom_missing_count: usize,
    queue_guard_tight_hold_count: usize,
    queue_pressure_hold_count: usize,
    queue_guard_limiting_path_counts: BTreeMap<String, usize>,
    interop_required_no_silent_fallback_profile_slugs: Vec<String>,
    interop_profile_contract_passed: bool,
    failed_validation_surface_keys: Vec<String>,
    blocking_reasons: Vec<String>,
    blocking_reason_keys: Vec<String>,
    blocking_reason_families: Vec<String>,
    advisory_reasons: Vec<String>,
}

fn main() -> Result<(), Box<dyn std::error::Error>> {
    let args = parse_args(env::args().skip(1))?;
    let deployment_signoff_path = args
        .deployment_signoff
        .unwrap_or_else(default_deployment_signoff_input);
    let validation_paths = if args.validations.is_empty() {
        vec![
            default_linux_validation_input(),
            default_macos_validation_input(),
            default_windows_validation_input(),
        ]
    } else {
        args.validations
    };
    let summary = build_release_prep_summary(
        load_deployment_signoff_input(&deployment_signoff_path),
        validation_paths
            .iter()
            .map(|path| load_validation_input(path))
            .collect(),
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
        return Err("udp release prep is not ready".into());
    }

    Ok(())
}

fn build_release_prep_summary(
    deployment_signoff: LoadedDeploymentSignoffInput,
    validations: Vec<LoadedValidationInput>,
) -> UdpReleasePrepSummary {
    let required_inputs = vec![
        "deployment_signoff".to_owned(),
        "linux_validation".to_owned(),
        "macos_validation".to_owned(),
        "windows_validation".to_owned(),
    ];
    let mut considered_inputs = vec!["deployment_signoff".to_owned()];
    let mut blocking_reasons = Vec::new();
    let mut blocking_reason_key_counts = BTreeMap::new();
    let mut blocking_reason_family_counts = BTreeMap::new();
    let advisory_reasons = Vec::new();
    let mut queue_guard_headroom_band_counts = BTreeMap::new();
    let mut queue_guard_limiting_path_counts = BTreeMap::new();
    let mut failed_validation_surface_keys = Vec::new();
    let mut degradation_hold_subjects = Vec::new();
    let mut validation_labels = Vec::new();
    let mut validation_passed_count = 0usize;
    let mut validation_command_count_total = 0usize;
    let mut validation_command_failed_total = 0usize;
    let mut validation_surface_count_total = 0usize;
    let mut validation_surface_failed_total = 0usize;
    let mut queue_guard_headroom_missing_count = 0usize;
    let mut queue_guard_tight_hold_count = 0usize;
    let mut queue_pressure_hold_count = 0usize;
    let mut all_consumed_inputs_contract_valid = true;
    let deployment_signoff_present = deployment_signoff.present;
    let mut present_required_inputs = BTreeSet::new();
    let mut passed_required_inputs = BTreeSet::new();
    let mut interop_profile_contract_passed = false;
    let expected_required_no_silent_fallback_profile_set =
        udp_wan_lab_required_no_silent_fallback_profile_slugs()
            .into_iter()
            .map(str::to_owned)
            .collect::<BTreeSet<_>>();
    let mut interop_required_no_silent_fallback_profile_set = BTreeSet::new();

    let deployment_signoff_passed = match deployment_signoff.summary.as_ref() {
        Some(summary)
            if deployment_signoff.present
                && deployment_signoff.parse_error.is_none()
                && deployment_signoff_summary_contract_valid(summary)
                && summary.verdict == "ready"
                && summary.evidence_state == "complete"
                && summary.gate_state == "passed"
                && summary.active_fuzz_required
                && summary.all_required_inputs_present
                && summary.all_required_inputs_passed
                && summary.blocking_reason_count == 0
                && summary.degradation_hold_count == 0
                && summary.queue_guard_tight_hold_count == 0 =>
        {
            present_required_inputs.insert("deployment_signoff".to_owned());
            passed_required_inputs.insert("deployment_signoff".to_owned());
            merge_counts(
                &mut queue_guard_headroom_band_counts,
                &summary.queue_guard_headroom_band_counts,
            );
            queue_guard_headroom_missing_count += summary.queue_guard_headroom_missing_count;
            merge_counts(
                &mut queue_guard_limiting_path_counts,
                &summary.queue_guard_limiting_path_counts,
            );
            queue_pressure_hold_count += summary.queue_pressure_hold_count;
            interop_required_no_silent_fallback_profile_set.extend(
                summary
                    .interop_required_no_silent_fallback_profile_slugs
                    .iter()
                    .cloned(),
            );
            interop_profile_contract_passed = summary.interop_profile_contract_passed;
            true
        }
        Some(summary) => {
            present_required_inputs.insert("deployment_signoff".to_owned());
            queue_guard_headroom_missing_count += summary.queue_guard_headroom_missing_count;
            merge_counts(
                &mut queue_guard_limiting_path_counts,
                &summary.queue_guard_limiting_path_counts,
            );
            queue_pressure_hold_count += summary.queue_pressure_hold_count;
            interop_required_no_silent_fallback_profile_set.extend(
                summary
                    .interop_required_no_silent_fallback_profile_slugs
                    .iter()
                    .cloned(),
            );
            interop_profile_contract_passed = summary.interop_profile_contract_passed;
            false
        }
        None => false,
    };

    if !deployment_signoff.present {
        push_reason(
            &mut blocking_reasons,
            &mut blocking_reason_key_counts,
            &mut blocking_reason_family_counts,
            "missing_deployment_signoff_summary",
            "missing_required_input",
            "summary_presence",
        );
    } else if let Some(error) = deployment_signoff.parse_error.as_ref() {
        all_consumed_inputs_contract_valid = false;
        push_reason(
            &mut blocking_reasons,
            &mut blocking_reason_key_counts,
            &mut blocking_reason_family_counts,
            &format!("deployment_signoff_parse_error:{error}"),
            "input_parse_error",
            "summary_contract",
        );
    } else if let Some(summary) = deployment_signoff.summary.as_ref() {
        if !deployment_signoff_summary_contract_valid(summary) {
            all_consumed_inputs_contract_valid = false;
            push_reason(
                &mut blocking_reasons,
                &mut blocking_reason_key_counts,
                &mut blocking_reason_family_counts,
                "deployment_signoff_summary_contract_invalid",
                "input_contract_invalid",
                "summary_contract",
            );
        } else if !deployment_signoff_passed {
            push_reason(
                &mut blocking_reasons,
                &mut blocking_reason_key_counts,
                &mut blocking_reason_family_counts,
                "deployment_signoff_not_ready",
                "deployment_signoff_not_ready",
                "gating",
            );
        }
    }

    for validation in validations {
        let Some(required_input) = classify_validation_requirement(&validation.input_label) else {
            continue;
        };
        considered_inputs.push(required_input.to_owned());
        validation_labels.push(validation.input_label.clone());

        if !validation.present {
            push_reason(
                &mut blocking_reasons,
                &mut blocking_reason_key_counts,
                &mut blocking_reason_family_counts,
                &format!("missing_{}_summary", required_input),
                "missing_required_input",
                "summary_presence",
            );
            continue;
        }

        present_required_inputs.insert(required_input.to_owned());
        if let Some(error) = validation.parse_error.as_ref() {
            all_consumed_inputs_contract_valid = false;
            push_reason(
                &mut blocking_reasons,
                &mut blocking_reason_key_counts,
                &mut blocking_reason_family_counts,
                &format!("{}:parse_error:{error}", validation.input_label),
                "input_parse_error",
                "summary_contract",
            );
            continue;
        }

        let Some(summary) = validation.summary.as_ref() else {
            continue;
        };
        if !validation_summary_contract_valid(summary) {
            all_consumed_inputs_contract_valid = false;
            push_reason(
                &mut blocking_reasons,
                &mut blocking_reason_key_counts,
                &mut blocking_reason_family_counts,
                &format!(
                    "{}:validation_summary_contract_invalid",
                    validation.input_label
                ),
                "input_contract_invalid",
                "summary_contract",
            );
            continue;
        }

        validation_command_count_total += summary.command_count;
        validation_command_failed_total += summary.failed_command_count;
        validation_surface_count_total += summary.surface_count_total;
        validation_surface_failed_total += summary.surface_count_failed;
        if let Some(band) = summary.queue_guard_headroom_band.as_ref() {
            *queue_guard_headroom_band_counts
                .entry(band.clone())
                .or_insert(0) += 1;
        } else {
            queue_guard_headroom_missing_count += 1;
        }
        if let Some(path) = summary.queue_guard_limiting_path.as_ref() {
            *queue_guard_limiting_path_counts
                .entry(path.clone())
                .or_insert(0) += 1;
        }
        queue_guard_tight_hold_count +=
            usize::from(summary.queue_guard_headroom_band.as_deref() == Some("tight"));
        queue_pressure_hold_count += usize::from(!summary.queue_pressure_surface_passed);

        if validation_summary_passed(summary) {
            validation_passed_count += 1;
            passed_required_inputs.insert(required_input.to_owned());
        } else {
            push_reason(
                &mut blocking_reasons,
                &mut blocking_reason_key_counts,
                &mut blocking_reason_family_counts,
                &format!("{}:validation_not_ready", validation.input_label),
                "validation_not_ready",
                "gating",
            );
        }

        if validation_has_degradation_hold(summary) {
            degradation_hold_subjects.push(validation.input_label.clone());
            push_reason(
                &mut blocking_reasons,
                &mut blocking_reason_key_counts,
                &mut blocking_reason_family_counts,
                &format!("{}:degradation_hold", validation.input_label),
                "degradation_hold",
                "degradation",
            );
        }
        failed_validation_surface_keys.extend(
            summary
                .failed_surface_keys
                .iter()
                .map(|key| format!("{}:{key}", validation.input_label)),
        );
    }

    let validation_count = validation_labels.len();
    let validation_failed_count = validation_count.saturating_sub(validation_passed_count);
    let missing_required_inputs = required_inputs
        .iter()
        .filter(|input| !present_required_inputs.contains(*input))
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
    let queue_hold_present = rollout_queue_hold_present(
        queue_guard_headroom_missing_count,
        queue_guard_tight_hold_count,
        queue_pressure_hold_count,
    );
    if !interop_profile_contract_passed {
        push_reason(
            &mut blocking_reasons,
            &mut blocking_reason_key_counts,
            &mut blocking_reason_family_counts,
            "deployment_signoff_interop_profile_contract_invalid",
            "interop_profile_contract_invalid",
            "schema",
        );
    }
    if interop_required_no_silent_fallback_profile_set
        != expected_required_no_silent_fallback_profile_set
    {
        push_reason(
            &mut blocking_reasons,
            &mut blocking_reason_key_counts,
            &mut blocking_reason_family_counts,
            "deployment_signoff_interop_required_no_silent_fallback_profile_set_mismatch",
            "interop_required_no_silent_fallback_profile_set_mismatch",
            "summary_contract",
        );
        interop_profile_contract_passed = false;
    }
    if queue_pressure_hold_count > 0 {
        push_reason(
            &mut blocking_reasons,
            &mut blocking_reason_key_counts,
            &mut blocking_reason_family_counts,
            "release_prep_queue_pressure_surface_failed",
            "queue_pressure_surface_failed",
            "capacity",
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
    let blocking_reason_count = blocking_reasons.len();
    let blocking_reason_key_count = blocking_reason_key_counts.len();
    let blocking_reason_family_count = blocking_reason_family_counts.len();

    let verdict = if all_required_inputs_passed
        && blocking_reason_count == 0
        && degradation_hold_count == 0
        && !queue_hold_present
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
    let evidence_state = if all_required_inputs_present && all_consumed_inputs_contract_valid {
        "complete"
    } else {
        "incomplete"
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
    let interop_required_no_silent_fallback_profile_slugs =
        interop_required_no_silent_fallback_profile_set
            .into_iter()
            .collect::<Vec<_>>();
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

    UdpReleasePrepSummary {
        summary_version: UDP_RELEASE_PREP_SUMMARY_VERSION,
        comparison_schema: UDP_ROLLOUT_OPERATOR_VERDICT_SCHEMA,
        comparison_schema_version: UDP_ROLLOUT_OPERATOR_VERDICT_SCHEMA_VERSION,
        verdict_family: UDP_ROLLOUT_OPERATOR_VERDICT_FAMILY,
        decision_scope: UDP_ROLLOUT_DECISION_SCOPE_RELEASE_PREP,
        decision_label: "release_prep",
        profile: "release_prep",
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
        deployment_signoff_present,
        deployment_signoff_passed,
        validation_count,
        validation_passed_count,
        validation_failed_count,
        validation_labels,
        validation_command_count_total,
        validation_command_failed_total,
        validation_surface_count_total,
        validation_surface_failed_total,
        degradation_hold_count,
        degradation_hold_subjects,
        queue_guard_headroom_band_counts,
        queue_guard_headroom_missing_count,
        queue_guard_tight_hold_count,
        queue_pressure_hold_count,
        queue_guard_limiting_path_counts,
        interop_required_no_silent_fallback_profile_slugs,
        interop_profile_contract_passed,
        failed_validation_surface_keys,
        blocking_reasons,
        blocking_reason_keys,
        blocking_reason_families,
        advisory_reasons,
    }
}

fn deployment_signoff_summary_contract_valid(summary: &DeploymentSignoffSummaryInput) -> bool {
    let expected_required_inputs = vec![
        "release_workflow".to_owned(),
        "compatible_host_validation".to_owned(),
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
    summary.summary_version == Some(UDP_DEPLOYMENT_SIGNOFF_SUMMARY_VERSION)
        && summary.comparison_schema == UDP_ROLLOUT_OPERATOR_VERDICT_SCHEMA
        && summary.comparison_schema_version == UDP_ROLLOUT_OPERATOR_VERDICT_SCHEMA_VERSION
        && summary.verdict_family == UDP_ROLLOUT_OPERATOR_VERDICT_FAMILY
        && summary.decision_scope == UDP_ROLLOUT_DECISION_SCOPE_DEPLOYMENT_SIGNOFF
        && summary.required_inputs == expected_required_inputs
        && summary.considered_inputs == expected_required_inputs
        && rollout_input_identity_consistent(
            &summary.required_inputs,
            &summary.considered_inputs,
            &summary.missing_required_inputs,
            summary.required_input_count,
        )
        && summary.required_input_missing_count == summary.missing_required_inputs.len()
        && summary.required_input_count >= summary.required_input_present_count
        && summary.required_input_present_count >= summary.required_input_passed_count
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
        && summary.missing_required_input_count == summary.missing_required_inputs.len()
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
        && summary.queue_pressure_hold_count <= summary.required_input_count
        && summary
            .interop_required_no_silent_fallback_profile_slugs
            .iter()
            .all(|slug| !slug.trim().is_empty())
        && summary
            .interop_required_no_silent_fallback_profile_slugs
            .len()
            == actual_required_profile_set.len()
        && actual_required_profile_set == expected_required_profile_set
        && summary.interop_profile_contract_passed
            == (actual_required_profile_set == expected_required_profile_set)
        && summary.queue_guard_tight_hold_count
            == summary
                .queue_guard_headroom_band_counts
                .get("tight")
                .copied()
                .unwrap_or(0)
        && (summary.queue_pressure_hold_count == 0
            || summary
                .blocking_reason_family_counts
                .contains_key("capacity"))
        && !(summary.queue_guard_headroom_missing_count > 0
            && summary
                .queue_guard_headroom_band_counts
                .values()
                .sum::<usize>()
                > 0)
        && summary.gate_state_reason == expected_reason
        && summary.gate_state_reason_family == expected_family
        && summary.gate_state
            == if summary.verdict == "ready" {
                "passed"
            } else {
                "blocked"
            }
        && !(summary.verdict == "ready"
            && (summary.queue_guard_tight_hold_count != 0
                || summary.queue_pressure_hold_count != 0))
        && !(summary.verdict == "ready"
            && (summary.blocking_reason_count != 0
                || summary.degradation_hold_count != 0
                || !summary.missing_required_inputs.is_empty()
                || summary.queue_guard_headroom_missing_count != 0
                || !summary.interop_profile_contract_passed))
}

fn validation_summary_contract_valid(summary: &RolloutValidationSummaryInput) -> bool {
    summary.summary_version == Some(UDP_ROLLOUT_VALIDATION_SUMMARY_VERSION)
        && !summary.profile.is_empty()
        && summary.command_count == summary.passed_command_count + summary.failed_command_count
        && summary.surface_count_total
            == summary.surface_count_passed + summary.surface_count_failed
        && (summary.queue_guard_headroom_band.as_deref() != Some("tight")
            || summary.queue_pressure_surface_passed)
        && !(summary.all_passed
            && (summary.failed_command_count != 0 || summary.surface_count_failed != 0))
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
        || !summary.clean_shutdown_stable
        || summary.policy_disabled_fallback_surface_passed != Some(true)
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
        && summary.repeated_queue_pressure_sticky
        && summary.queue_pressure_surface_passed
        && summary.reordering_no_silent_fallback_passed
        && summary.prolonged_impairment_no_silent_fallback
        && summary.prolonged_repeated_impairment_stable
        && summary.longer_impairment_recovery_stable
        && summary.shutdown_sequence_stable
        && summary.post_close_rejection_stable
        && summary.clean_shutdown_stable
        && summary.sticky_selection_surface_passed
        && summary.degradation_surface_passed
        && summary.policy_disabled_fallback_surface_passed == Some(true)
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

fn classify_validation_requirement(input_label: &str) -> Option<&'static str> {
    let normalized = input_label.to_ascii_lowercase();
    if normalized.contains("linux") {
        Some("linux_validation")
    } else if normalized.contains("macos") {
        Some("macos_validation")
    } else if normalized.contains("windows") {
        Some("windows_validation")
    } else {
        None
    }
}

fn load_deployment_signoff_input(path: &Path) -> LoadedDeploymentSignoffInput {
    if !path.exists() {
        return LoadedDeploymentSignoffInput {
            present: false,
            parse_error: None,
            summary: None,
        };
    }
    match fs::read(path)
        .map_err(|error| error.to_string())
        .and_then(|bytes| {
            serde_json::from_slice::<DeploymentSignoffSummaryInput>(&bytes)
                .map_err(|error| error.to_string())
        }) {
        Ok(summary) => LoadedDeploymentSignoffInput {
            present: true,
            parse_error: None,
            summary: Some(summary),
        },
        Err(error) => LoadedDeploymentSignoffInput {
            present: true,
            parse_error: Some(error),
            summary: None,
        },
    }
}

fn load_validation_input(path: &Path) -> LoadedValidationInput {
    let input_label = path
        .file_stem()
        .map(|value| value.to_string_lossy().into_owned())
        .unwrap_or_else(|| "rollout-validation".to_owned());
    if !path.exists() {
        return LoadedValidationInput {
            input_label,
            present: false,
            parse_error: None,
            summary: None,
        };
    }
    match fs::read(path)
        .map_err(|error| error.to_string())
        .and_then(|bytes| {
            serde_json::from_slice::<RolloutValidationSummaryInput>(&bytes)
                .map_err(|error| error.to_string())
        }) {
        Ok(summary) => LoadedValidationInput {
            input_label,
            present: true,
            parse_error: None,
            summary: Some(summary),
        },
        Err(error) => LoadedValidationInput {
            input_label,
            present: true,
            parse_error: Some(error),
            summary: None,
        },
    }
}

fn print_text_summary(summary: &UdpReleasePrepSummary, summary_path: &Path) {
    println!("Verta UDP release prep summary:");
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
        "- all_required_inputs: present={} passed={}",
        summary.all_required_inputs_present, summary.all_required_inputs_passed
    );
    println!(
        "- deployment_signoff: present={} passed={}",
        summary.deployment_signoff_present, summary.deployment_signoff_passed
    );
    println!(
        "- validation_counts: total={} passed={} failed={}",
        summary.validation_count, summary.validation_passed_count, summary.validation_failed_count
    );
    println!(
        "- validation_command_counts: total={} failed={}",
        summary.validation_command_count_total, summary.validation_command_failed_total
    );
    println!(
        "- validation_surface_counts: total={} failed={}",
        summary.validation_surface_count_total, summary.validation_surface_failed_total
    );
    println!(
        "- missing_required_input_count: {}",
        summary.missing_required_input_count
    );
    println!(
        "- degradation_hold_count: {}",
        summary.degradation_hold_count
    );
    if summary.missing_required_inputs.is_empty() {
        println!("- missing_required_inputs: none");
    } else {
        println!(
            "- missing_required_inputs: {}",
            summary.missing_required_inputs.join(", ")
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
    if summary.validation_labels.is_empty() {
        println!("- validation_labels: none");
    } else {
        println!(
            "- validation_labels: {}",
            summary.validation_labels.join(", ")
        );
    }
    println!(
        "- queue_guard_headroom_missing_count: {}",
        summary.queue_guard_headroom_missing_count
    );
    println!(
        "- queue_pressure_hold_count: {}",
        summary.queue_pressure_hold_count
    );
    println!(
        "- interop_profile_contract_passed: {}",
        summary.interop_profile_contract_passed
    );
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
    if summary.queue_guard_headroom_band_counts.is_empty() {
        println!("- queue_guard_headroom_band_counts: none");
    } else {
        println!(
            "- queue_guard_headroom_band_counts: {}",
            render_counts(&summary.queue_guard_headroom_band_counts)
        );
    }
    println!("- blocking_reason_count: {}", summary.blocking_reason_count);
    if summary.blocking_reason_key_counts.is_empty() {
        println!("- blocking_reason_key_counts: none");
    } else {
        println!(
            "- blocking_reason_key_counts: {}",
            render_counts(&summary.blocking_reason_key_counts)
        );
    }
    if summary.blocking_reason_family_counts.is_empty() {
        println!("- blocking_reason_family_counts: none");
    } else {
        println!(
            "- blocking_reason_family_counts: {}",
            render_counts(&summary.blocking_reason_family_counts)
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
    if summary.failed_validation_surface_keys.is_empty() {
        println!("- failed_validation_surface_keys: none");
    } else {
        println!(
            "- failed_validation_surface_keys: {}",
            summary.failed_validation_surface_keys.join(", ")
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
    if summary.blocking_reason_families.is_empty() {
        println!("- blocking_reason_families: none");
    } else {
        println!(
            "- blocking_reason_families: {}",
            summary.blocking_reason_families.join(", ")
        );
    }
    println!(
        "- blocking_reason_key_count: {}",
        summary.blocking_reason_key_count
    );
    println!(
        "- blocking_reason_family_count: {}",
        summary.blocking_reason_family_count
    );
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

fn parse_args<I>(mut args: I) -> Result<ReleasePrepArgs, String>
where
    I: Iterator<Item = String>,
{
    let mut parsed = ReleasePrepArgs::default();
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
            "--deployment-signoff" => {
                parsed.deployment_signoff =
                    Some(PathBuf::from(args.next().ok_or_else(|| {
                        "--deployment-signoff requires a value".to_owned()
                    })?));
            }
            "--validation" => {
                parsed.validations.push(PathBuf::from(
                    args.next()
                        .ok_or_else(|| "--validation requires a value".to_owned())?,
                ));
            }
            "--help" | "-h" => return Err(help_text()),
            _ => return Err(help_text()),
        }
    }
    Ok(parsed)
}

fn help_text() -> String {
    "Usage: cargo run -p ns-testkit --example udp_release_prep -- [--format text|json] [--summary-path <path>] [--deployment-signoff <path>] [--validation <path> ...]".to_owned()
}

fn default_deployment_signoff_input() -> PathBuf {
    prefer_verta_input_path("udp-deployment-signoff-summary.json")
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
    verta_output_path("udp-release-prep-summary.json")
}

fn push_reason(
    reasons: &mut Vec<String>,
    key_counts: &mut BTreeMap<String, usize>,
    family_counts: &mut BTreeMap<String, usize>,
    code: &str,
    reason_key: impl Into<String>,
    family: &'static str,
) {
    reasons.push(code.to_owned());
    *key_counts.entry(reason_key.into()).or_insert(0) += 1;
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
    use ns_testkit::{
        UDP_ROLLOUT_OPERATOR_VERDICT_SCHEMA_VERSION,
        udp_wan_lab_required_no_silent_fallback_profile_slugs,
    };
    use std::collections::BTreeSet;

    fn ready_deployment_signoff() -> LoadedDeploymentSignoffInput {
        LoadedDeploymentSignoffInput {
            present: true,
            parse_error: None,
            summary: Some(DeploymentSignoffSummaryInput {
                summary_version: Some(UDP_DEPLOYMENT_SIGNOFF_SUMMARY_VERSION),
                comparison_schema: "udp_rollout_operator_verdict".to_owned(),
                comparison_schema_version: UDP_ROLLOUT_OPERATOR_VERDICT_SCHEMA_VERSION,
                verdict_family: "udp_rollout_operator_decision".to_owned(),
                decision_scope: "deployment_signoff".to_owned(),
                verdict: "ready".to_owned(),
                evidence_state: "complete".to_owned(),
                gate_state: "passed".to_owned(),
                gate_state_reason: "all_required_inputs_passed".to_owned(),
                gate_state_reason_family: "ready".to_owned(),
                active_fuzz_required: true,
                required_inputs: vec![
                    "release_workflow".to_owned(),
                    "compatible_host_validation".to_owned(),
                ],
                considered_inputs: vec![
                    "release_workflow".to_owned(),
                    "compatible_host_validation".to_owned(),
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
                degradation_hold_count: 0,
                degradation_hold_subjects: Vec::new(),
                queue_guard_headroom_band_counts: BTreeMap::from([("healthy".to_owned(), 1)]),
                queue_guard_headroom_missing_count: 0,
                queue_guard_limiting_path_counts: BTreeMap::from([(
                    "queue_recovery_send".to_owned(),
                    1,
                )]),
                queue_guard_tight_hold_count: 0,
                queue_pressure_hold_count: 0,
                interop_required_no_silent_fallback_profile_slugs:
                    udp_wan_lab_required_no_silent_fallback_profile_slugs()
                        .into_iter()
                        .map(str::to_owned)
                        .collect(),
                interop_profile_contract_passed: true,
                blocking_reasons: Vec::new(),
            }),
        }
    }

    fn ready_validation(label: &str) -> LoadedValidationInput {
        LoadedValidationInput {
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
                repeated_queue_pressure_sticky: true,
                queue_pressure_surface_passed: true,
                reordering_no_silent_fallback_passed: true,
                prolonged_impairment_no_silent_fallback: true,
                prolonged_repeated_impairment_stable: true,
                longer_impairment_recovery_stable: true,
                shutdown_sequence_stable: true,
                post_close_rejection_stable: true,
                clean_shutdown_stable: true,
                sticky_selection_surface_passed: true,
                degradation_surface_passed: true,
                policy_disabled_fallback_surface_passed: Some(true),
                transport_fallback_integrity_surface_passed: true,
                rollout_surface_passed: Some(true),
                surface_count_total: 5,
                surface_count_passed: 5,
                surface_count_failed: 0,
                failed_surface_keys: Vec::new(),
                command_count: 3,
                passed_command_count: 3,
                failed_command_count: 0,
                queue_guard_headroom_band: Some("healthy".to_owned()),
                queue_guard_limiting_path: Some("queue_recovery_send".to_owned()),
            }),
        }
    }

    #[test]
    fn release_prep_emits_ready_operator_schema() {
        let summary = build_release_prep_summary(
            ready_deployment_signoff(),
            vec![
                ready_validation("udp-rollout-validation-summary-linux"),
                ready_validation("udp-rollout-validation-summary-macos"),
                ready_validation("udp-rollout-validation-summary-windows"),
            ],
        );

        assert_eq!(summary.verdict, "ready");
        assert_eq!(summary.gate_state, "passed");
        assert_eq!(summary.comparison_schema, "udp_rollout_operator_verdict");
        assert_eq!(
            summary.comparison_schema_version,
            UDP_ROLLOUT_OPERATOR_VERDICT_SCHEMA_VERSION
        );
        assert_eq!(summary.decision_scope, "release_prep");
        assert_eq!(summary.summary_version, UDP_RELEASE_PREP_SUMMARY_VERSION);
        assert_eq!(summary.required_input_count, 4);
        assert_eq!(summary.required_input_missing_count, 0);
        assert_eq!(summary.required_input_failed_count, 0);
        assert_eq!(summary.required_input_unready_count, 0);
        assert_eq!(summary.gate_state_reason, "all_required_inputs_passed");
        assert_eq!(summary.gate_state_reason_family, "ready");
        assert_eq!(summary.blocking_reason_count, 0);
        assert_eq!(summary.degradation_hold_count, 0);
        assert_eq!(summary.queue_guard_headroom_missing_count, 0);
        assert_eq!(summary.queue_guard_tight_hold_count, 0);
        assert_eq!(summary.queue_pressure_hold_count, 0);
        assert!(summary.interop_profile_contract_passed);
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
        assert_eq!(
            summary
                .queue_guard_headroom_band_counts
                .get("healthy")
                .copied(),
            Some(4)
        );
    }

    #[test]
    fn release_prep_holds_without_linux_validation() {
        let summary = build_release_prep_summary(
            ready_deployment_signoff(),
            vec![
                ready_validation("udp-rollout-validation-summary-macos"),
                ready_validation("udp-rollout-validation-summary-windows"),
            ],
        );

        assert_eq!(summary.verdict, "hold");
        assert_eq!(summary.gate_state, "blocked");
        assert_eq!(summary.required_input_missing_count, 1);
        assert_eq!(summary.required_input_failed_count, 1);
        assert!(
            summary
                .missing_required_inputs
                .iter()
                .any(|value| value == "linux_validation")
        );
    }

    #[test]
    fn release_prep_holds_when_deployment_signoff_reports_queue_pressure() {
        let mut deployment_signoff = ready_deployment_signoff();
        deployment_signoff
            .summary
            .as_mut()
            .expect("deployment signoff summary should exist")
            .queue_pressure_hold_count = 1;

        let summary = build_release_prep_summary(
            deployment_signoff,
            vec![
                ready_validation("udp-rollout-validation-summary-linux"),
                ready_validation("udp-rollout-validation-summary-macos"),
                ready_validation("udp-rollout-validation-summary-windows"),
            ],
        );

        assert_eq!(summary.verdict, "hold");
        assert!(summary.queue_pressure_hold_count > 0);
        assert!(
            summary
                .blocking_reason_keys
                .iter()
                .any(|value| value == "queue_pressure_surface_failed")
        );
    }
}
