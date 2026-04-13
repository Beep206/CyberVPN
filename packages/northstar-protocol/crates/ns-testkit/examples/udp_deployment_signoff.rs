use ns_testkit::{
    UDP_ROLLOUT_DECISION_SCOPE_DEPLOYMENT_SIGNOFF, UDP_ROLLOUT_DECISION_SCOPE_RELEASE_WORKFLOW,
    UDP_ROLLOUT_OPERATOR_VERDICT_FAMILY, UDP_ROLLOUT_OPERATOR_VERDICT_SCHEMA,
    UDP_ROLLOUT_OPERATOR_VERDICT_SCHEMA_VERSION, repo_root, rollout_queue_hold_present,
    summarize_rollout_gate_state, udp_wan_lab_required_no_silent_fallback_profile_slugs,
};
use serde::{Deserialize, Serialize};
use std::collections::BTreeMap;
use std::env;
use std::fs;
use std::path::{Path, PathBuf};

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
enum OutputFormat {
    Text,
    Json,
}

#[derive(Debug, Default)]
struct SignoffArgs {
    format: Option<OutputFormat>,
    summary_path: Option<PathBuf>,
    release_workflow: Option<PathBuf>,
    validations: Vec<PathBuf>,
}

const UDP_RELEASE_WORKFLOW_SUMMARY_VERSION: u8 = 8;
const UDP_ROLLOUT_VALIDATION_SUMMARY_VERSION: u8 = 19;
const UDP_DEPLOYMENT_SIGNOFF_SUMMARY_VERSION: u8 = 7;

#[derive(Debug, Deserialize)]
struct ReleaseWorkflowSummaryInput {
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
struct LoadedReleaseWorkflowInput {
    present: bool,
    parse_error: Option<String>,
    summary: Option<ReleaseWorkflowSummaryInput>,
}

#[derive(Debug)]
struct LoadedValidationInput {
    input_label: String,
    present: bool,
    parse_error: Option<String>,
    summary: Option<RolloutValidationSummaryInput>,
}

#[derive(Debug, Serialize)]
struct UdpDeploymentSignoffSummary {
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
    release_workflow_present: bool,
    release_workflow_passed: bool,
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
    let release_path = args
        .release_workflow
        .unwrap_or_else(default_release_workflow_input);
    let validation_paths = if args.validations.is_empty() {
        vec![default_windows_validation_input()]
    } else {
        args.validations
    };
    let summary = build_deployment_signoff_summary(
        load_release_workflow_input(&release_path),
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
        return Err("udp deployment signoff is not ready".into());
    }

    Ok(())
}

fn build_deployment_signoff_summary(
    release_workflow: LoadedReleaseWorkflowInput,
    validations: Vec<LoadedValidationInput>,
) -> UdpDeploymentSignoffSummary {
    let required_inputs = vec![
        "release_workflow".to_owned(),
        "compatible_host_validation".to_owned(),
    ];
    let mut considered_inputs = vec!["release_workflow".to_owned()];
    let mut missing_required_inputs = Vec::new();
    let mut blocking_reasons = Vec::new();
    let mut blocking_reason_key_counts = BTreeMap::new();
    let mut blocking_reason_family_counts = BTreeMap::new();
    let advisory_reasons = Vec::new();
    let mut queue_guard_headroom_band_counts = BTreeMap::new();
    let mut queue_guard_limiting_path_counts = BTreeMap::new();
    let mut failed_validation_surface_keys = Vec::new();
    let mut degradation_hold_subjects = Vec::new();
    let mut validation_labels = Vec::new();
    let mut validation_present_count = 0usize;
    let mut validation_passed_count = 0usize;
    let mut validation_command_count_total = 0usize;
    let mut validation_command_failed_total = 0usize;
    let mut validation_surface_count_total = 0usize;
    let mut validation_surface_failed_total = 0usize;
    let mut queue_guard_headroom_missing_count = 0usize;
    let mut queue_guard_tight_hold_count = 0usize;
    let mut queue_pressure_hold_count = 0usize;
    let release_workflow_present = release_workflow.present;
    let mut all_consumed_inputs_contract_valid = true;
    let mut interop_profile_contract_passed = false;
    let expected_required_no_silent_fallback_profile_set =
        udp_wan_lab_required_no_silent_fallback_profile_slugs()
            .into_iter()
            .map(str::to_owned)
            .collect::<std::collections::BTreeSet<_>>();
    let mut interop_required_no_silent_fallback_profile_set = std::collections::BTreeSet::new();

    let release_workflow_passed = match release_workflow.summary.as_ref() {
        Some(summary)
            if release_workflow.present
                && release_workflow.parse_error.is_none()
                && release_summary_contract_valid(summary)
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
        _ => false,
    };

    if !release_workflow.present {
        missing_required_inputs.push("release_workflow".to_owned());
        push_reason(
            &mut blocking_reasons,
            &mut blocking_reason_key_counts,
            &mut blocking_reason_family_counts,
            "summary_presence_missing",
            "missing_release_workflow_summary",
            "summary_presence",
        );
    } else if release_workflow.parse_error.is_some() {
        all_consumed_inputs_contract_valid = false;
        push_reason(
            &mut blocking_reasons,
            &mut blocking_reason_key_counts,
            &mut blocking_reason_family_counts,
            "summary_parse_failed",
            "invalid_release_workflow_summary",
            "summary_parse",
        );
    } else if let Some(summary) = release_workflow.summary.as_ref() {
        if !release_summary_contract_valid(summary) {
            all_consumed_inputs_contract_valid = false;
            push_reason(
                &mut blocking_reasons,
                &mut blocking_reason_key_counts,
                &mut blocking_reason_family_counts,
                "summary_contract_invalid",
                "release_workflow_summary_contract_invalid",
                "schema",
            );
        } else if !release_workflow_passed {
            push_reason(
                &mut blocking_reasons,
                &mut blocking_reason_key_counts,
                &mut blocking_reason_family_counts,
                "release_workflow_not_ready",
                "release_workflow_not_ready",
                if summary.degradation_hold_count > 0 {
                    "degradation"
                } else {
                    "gating"
                },
            );
            degradation_hold_subjects.extend(summary.degradation_hold_subjects.iter().cloned());
            queue_guard_headroom_missing_count += summary.queue_guard_headroom_missing_count;
            queue_pressure_hold_count += summary.queue_pressure_hold_count;
            interop_required_no_silent_fallback_profile_set.extend(
                summary
                    .interop_required_no_silent_fallback_profile_slugs
                    .iter()
                    .cloned(),
            );
            interop_profile_contract_passed = summary.interop_profile_contract_passed;
        }
    }

    if validations.is_empty() {
        missing_required_inputs.push("compatible_host_validation".to_owned());
    }

    for input in validations {
        considered_inputs.push(input.input_label.clone());
        validation_labels.push(input.input_label.clone());

        if !input.present {
            push_reason(
                &mut blocking_reasons,
                &mut blocking_reason_key_counts,
                &mut blocking_reason_family_counts,
                "summary_presence_missing",
                format!("missing_{}_summary", sanitize_label(&input.input_label)),
                "summary_presence",
            );
            continue;
        }

        validation_present_count += 1;

        if input.parse_error.is_some() {
            all_consumed_inputs_contract_valid = false;
            push_reason(
                &mut blocking_reasons,
                &mut blocking_reason_key_counts,
                &mut blocking_reason_family_counts,
                "summary_parse_failed",
                format!("invalid_{}_summary", sanitize_label(&input.input_label)),
                "summary_parse",
            );
            continue;
        }

        let Some(summary) = input.summary.as_ref() else {
            continue;
        };

        if !validation_summary_contract_valid(summary) {
            all_consumed_inputs_contract_valid = false;
            push_reason(
                &mut blocking_reasons,
                &mut blocking_reason_key_counts,
                &mut blocking_reason_family_counts,
                "summary_contract_invalid",
                format!(
                    "{}_summary_contract_invalid",
                    sanitize_label(&input.input_label)
                ),
                "shape",
            );
            continue;
        }

        validation_command_count_total += summary.command_count;
        validation_command_failed_total += summary.failed_command_count;
        validation_surface_count_total += summary.surface_count_total;
        validation_surface_failed_total += summary.surface_count_failed;
        failed_validation_surface_keys.extend(summary.failed_surface_keys.iter().cloned());
        if let Some(band) = summary.queue_guard_headroom_band.as_ref() {
            *queue_guard_headroom_band_counts
                .entry(band.clone())
                .or_insert(0) += 1;
        } else {
            queue_guard_headroom_missing_count += 1;
        }
        if let Some(path) = &summary.queue_guard_limiting_path {
            *queue_guard_limiting_path_counts
                .entry(path.clone())
                .or_insert(0) += 1;
        }
        queue_guard_tight_hold_count +=
            usize::from(summary.queue_guard_headroom_band.as_deref() == Some("tight"));
        queue_pressure_hold_count += usize::from(!summary.queue_pressure_surface_passed);

        let validation_passed = validation_summary_passed(summary);
        if validation_passed {
            validation_passed_count += 1;
        } else {
            push_reason(
                &mut blocking_reasons,
                &mut blocking_reason_key_counts,
                &mut blocking_reason_family_counts,
                "compatible_host_validation_not_ready",
                format!(
                    "{}_validation_not_ready",
                    sanitize_label(&input.input_label)
                ),
                if validation_has_degradation_hold(summary) {
                    "degradation"
                } else {
                    "gating"
                },
            );
        }

        if validation_has_degradation_hold(summary) {
            degradation_hold_subjects.push(input.input_label.clone());
        }
    }

    if validation_present_count == 0 {
        if !missing_required_inputs
            .iter()
            .any(|value| value == "compatible_host_validation")
        {
            missing_required_inputs.push("compatible_host_validation".to_owned());
        }
        push_reason(
            &mut blocking_reasons,
            &mut blocking_reason_key_counts,
            &mut blocking_reason_family_counts,
            "summary_presence_missing",
            "missing_compatible_host_validation_summary",
            "summary_presence",
        );
    }

    if !interop_profile_contract_passed {
        push_reason(
            &mut blocking_reasons,
            &mut blocking_reason_key_counts,
            &mut blocking_reason_family_counts,
            "release_workflow_interop_profile_contract_invalid",
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
            "release_workflow_interop_required_no_silent_fallback_profile_set_mismatch",
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
            "deployment_signoff_queue_pressure_surface_failed",
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

    validation_labels.sort();
    validation_labels.dedup();
    degradation_hold_subjects.sort();
    degradation_hold_subjects.dedup();
    failed_validation_surface_keys.sort();
    failed_validation_surface_keys.dedup();
    let required_input_count = required_inputs.len();
    let required_input_missing_count = missing_required_inputs.len();
    let required_input_present_count =
        usize::from(release_workflow_present) + usize::from(validation_present_count > 0);
    let required_input_passed_count = usize::from(release_workflow_passed)
        + usize::from(
            validation_present_count > 0 && validation_passed_count == validation_present_count,
        );
    let required_input_failed_count =
        required_input_count.saturating_sub(required_input_passed_count);
    let required_input_unready_count =
        required_input_failed_count.saturating_sub(required_input_missing_count);
    let all_required_inputs_present = required_input_present_count == required_input_count;
    let all_required_inputs_passed = all_required_inputs_present
        && required_input_passed_count == required_input_count
        && validation_present_count > 0;
    let queue_hold_present = rollout_queue_hold_present(
        queue_guard_headroom_missing_count,
        queue_guard_tight_hold_count,
        queue_pressure_hold_count,
    );
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
    let evidence_state = if all_required_inputs_present && all_consumed_inputs_contract_valid {
        "complete"
    } else {
        "incomplete"
    };
    let verdict =
        if all_required_inputs_passed && blocking_reasons.is_empty() && !queue_hold_present {
            "ready"
        } else {
            "hold"
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
    let blocking_reason_key_count = blocking_reason_key_counts.len();
    let mut blocking_reason_families = blocking_reason_family_counts
        .keys()
        .cloned()
        .collect::<Vec<_>>();
    blocking_reason_families.sort();
    let blocking_reason_family_count = blocking_reason_family_counts.len();
    let degradation_hold_count = degradation_hold_subjects.len();
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
        blocking_reasons.len(),
    );

    UdpDeploymentSignoffSummary {
        summary_version: UDP_DEPLOYMENT_SIGNOFF_SUMMARY_VERSION,
        comparison_schema: UDP_ROLLOUT_OPERATOR_VERDICT_SCHEMA,
        comparison_schema_version: UDP_ROLLOUT_OPERATOR_VERDICT_SCHEMA_VERSION,
        verdict_family: UDP_ROLLOUT_OPERATOR_VERDICT_FAMILY,
        decision_scope: UDP_ROLLOUT_DECISION_SCOPE_DEPLOYMENT_SIGNOFF,
        decision_label: "deployment_signoff",
        profile: "deployment_signoff",
        verdict,
        evidence_state,
        gate_state,
        gate_state_reason,
        gate_state_reason_family,
        active_fuzz_required: true,
        required_inputs,
        considered_inputs,
        missing_required_inputs: missing_required_inputs.clone(),
        missing_required_input_count: missing_required_inputs.len(),
        required_input_count,
        required_input_missing_count,
        required_input_failed_count,
        required_input_unready_count,
        required_input_present_count,
        required_input_passed_count,
        all_required_inputs_present,
        all_required_inputs_passed,
        blocking_reason_count: blocking_reasons.len(),
        blocking_reason_key_count,
        blocking_reason_family_count,
        blocking_reason_key_counts,
        blocking_reason_family_counts,
        advisory_reason_count: advisory_reasons.len(),
        release_workflow_present,
        release_workflow_passed,
        validation_count: validation_labels.len(),
        validation_passed_count,
        validation_failed_count: validation_labels
            .len()
            .saturating_sub(validation_passed_count),
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

fn release_summary_contract_valid(summary: &ReleaseWorkflowSummaryInput) -> bool {
    let expected_required_inputs = vec!["readiness".to_owned(), "staged_rollout".to_owned()];
    let expected_required_profile_set = udp_wan_lab_required_no_silent_fallback_profile_slugs()
        .into_iter()
        .map(str::to_owned)
        .collect::<std::collections::BTreeSet<_>>();
    let actual_required_profile_set = summary
        .interop_required_no_silent_fallback_profile_slugs
        .iter()
        .cloned()
        .collect::<std::collections::BTreeSet<_>>();
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
    summary.summary_version == Some(UDP_RELEASE_WORKFLOW_SUMMARY_VERSION)
        && summary.comparison_schema == UDP_ROLLOUT_OPERATOR_VERDICT_SCHEMA
        && summary.comparison_schema_version == UDP_ROLLOUT_OPERATOR_VERDICT_SCHEMA_VERSION
        && summary.verdict_family == UDP_ROLLOUT_OPERATOR_VERDICT_FAMILY
        && summary.decision_scope == UDP_ROLLOUT_DECISION_SCOPE_RELEASE_WORKFLOW
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
    let required_set = required_inputs
        .iter()
        .collect::<std::collections::BTreeSet<_>>();
    let considered_set = considered_inputs
        .iter()
        .collect::<std::collections::BTreeSet<_>>();
    let missing_set = missing_required_inputs
        .iter()
        .collect::<std::collections::BTreeSet<_>>();
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

fn load_release_workflow_input(path: &Path) -> LoadedReleaseWorkflowInput {
    if !path.exists() {
        return LoadedReleaseWorkflowInput {
            present: false,
            parse_error: None,
            summary: None,
        };
    }
    match fs::read(path)
        .map_err(|error| error.to_string())
        .and_then(|bytes| {
            serde_json::from_slice::<ReleaseWorkflowSummaryInput>(&bytes)
                .map_err(|error| error.to_string())
        }) {
        Ok(summary) => LoadedReleaseWorkflowInput {
            present: true,
            parse_error: None,
            summary: Some(summary),
        },
        Err(error) => LoadedReleaseWorkflowInput {
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

fn print_text_summary(summary: &UdpDeploymentSignoffSummary, summary_path: &Path) {
    println!("Northstar UDP deployment signoff summary:");
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

fn parse_args<I>(mut args: I) -> Result<SignoffArgs, String>
where
    I: Iterator<Item = String>,
{
    let mut parsed = SignoffArgs::default();
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
            "--release-workflow" => {
                parsed.release_workflow =
                    Some(PathBuf::from(args.next().ok_or_else(|| {
                        "--release-workflow requires a value".to_owned()
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
    "Usage: cargo run -p ns-testkit --example udp_deployment_signoff -- [--format text|json] [--summary-path <path>] [--release-workflow <path>] [--validation <path> ...]".to_owned()
}

fn default_release_workflow_input() -> PathBuf {
    repo_root()
        .join("target")
        .join("northstar")
        .join("udp-release-workflow-summary.json")
}

fn default_windows_validation_input() -> PathBuf {
    repo_root()
        .join("target")
        .join("northstar")
        .join("udp-rollout-validation-summary-windows.json")
}

fn default_summary_path() -> PathBuf {
    repo_root()
        .join("target")
        .join("northstar")
        .join("udp-deployment-signoff-summary.json")
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

fn sanitize_label(value: &str) -> String {
    value
        .chars()
        .map(|ch| {
            if ch.is_ascii_alphanumeric() {
                ch.to_ascii_lowercase()
            } else {
                '_'
            }
        })
        .collect()
}

#[cfg(test)]
mod tests {
    use super::*;
    use ns_testkit::{
        UDP_ROLLOUT_OPERATOR_VERDICT_SCHEMA_VERSION,
        udp_wan_lab_required_no_silent_fallback_profile_slugs,
    };
    use std::collections::BTreeSet;

    fn ready_release() -> LoadedReleaseWorkflowInput {
        LoadedReleaseWorkflowInput {
            present: true,
            parse_error: None,
            summary: Some(ReleaseWorkflowSummaryInput {
                summary_version: Some(UDP_RELEASE_WORKFLOW_SUMMARY_VERSION),
                comparison_schema: "udp_rollout_operator_verdict".to_owned(),
                comparison_schema_version: UDP_ROLLOUT_OPERATOR_VERDICT_SCHEMA_VERSION,
                verdict_family: "udp_rollout_operator_decision".to_owned(),
                decision_scope: "release_workflow".to_owned(),
                verdict: "ready".to_owned(),
                evidence_state: "complete".to_owned(),
                gate_state: "passed".to_owned(),
                gate_state_reason: "all_required_inputs_passed".to_owned(),
                gate_state_reason_family: "ready".to_owned(),
                active_fuzz_required: true,
                required_inputs: vec!["readiness".to_owned(), "staged_rollout".to_owned()],
                considered_inputs: vec!["readiness".to_owned(), "staged_rollout".to_owned()],
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
                queue_guard_headroom_band_counts: BTreeMap::from([("healthy".to_owned(), 2usize)]),
                queue_guard_headroom_missing_count: 0,
                queue_guard_limiting_path_counts: BTreeMap::new(),
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
    fn deployment_signoff_emits_ready_operator_schema() {
        let summary = build_deployment_signoff_summary(
            ready_release(),
            vec![ready_validation("udp-rollout-validation-summary-windows")],
        );

        assert_eq!(summary.verdict, "ready");
        assert_eq!(summary.gate_state, "passed");
        assert_eq!(summary.comparison_schema, "udp_rollout_operator_verdict");
        assert_eq!(
            summary.comparison_schema_version,
            UDP_ROLLOUT_OPERATOR_VERDICT_SCHEMA_VERSION
        );
        assert_eq!(summary.decision_scope, "deployment_signoff");
        assert_eq!(
            summary.summary_version,
            UDP_DEPLOYMENT_SIGNOFF_SUMMARY_VERSION
        );
        assert_eq!(summary.missing_required_input_count, 0);
        assert_eq!(summary.required_input_missing_count, 0);
        assert_eq!(summary.required_input_failed_count, 0);
        assert_eq!(summary.required_input_unready_count, 0);
        assert_eq!(summary.gate_state_reason, "all_required_inputs_passed");
        assert_eq!(summary.gate_state_reason_family, "ready");
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
        assert_eq!(summary.blocking_reason_count, 0);
        assert_eq!(summary.blocking_reason_key_count, 0);
        assert_eq!(summary.blocking_reason_family_count, 0);
    }

    #[test]
    fn deployment_signoff_holds_without_compatible_host_validation() {
        let summary = build_deployment_signoff_summary(ready_release(), Vec::new());

        assert_eq!(summary.verdict, "hold");
        assert_eq!(summary.gate_state, "blocked");
        assert_eq!(summary.required_input_missing_count, 1);
        assert_eq!(summary.required_input_failed_count, 1);
        assert!(
            summary
                .missing_required_inputs
                .iter()
                .any(|value| value == "compatible_host_validation")
        );
        assert!(
            summary
                .blocking_reason_families
                .iter()
                .any(|value| value == "summary_presence")
        );
    }

    #[test]
    fn deployment_signoff_holds_when_release_workflow_reports_queue_pressure() {
        let mut release = ready_release();
        let release_summary = release
            .summary
            .as_mut()
            .expect("release summary should exist");
        release_summary.verdict = "hold".to_owned();
        release_summary.gate_state = "blocked".to_owned();
        release_summary.gate_state_reason = "required_inputs_unready".to_owned();
        release_summary.gate_state_reason_family = "gating".to_owned();
        release_summary.required_input_failed_count = 1;
        release_summary.required_input_unready_count = 1;
        release_summary.required_input_passed_count = 1;
        release_summary.all_required_inputs_passed = false;
        release_summary.blocking_reason_count = 1;
        release_summary.blocking_reason_key_count = 1;
        release_summary.blocking_reason_family_count = 1;
        release_summary
            .blocking_reason_key_counts
            .insert("queue_pressure_surface_failed".to_owned(), 1);
        release_summary
            .blocking_reason_family_counts
            .insert("capacity".to_owned(), 1);
        release_summary.queue_pressure_hold_count = 1;
        release_summary.blocking_reasons =
            vec!["release_workflow_queue_pressure_surface_failed".to_owned()];

        let summary = build_deployment_signoff_summary(
            release,
            vec![ready_validation("udp-rollout-validation-summary-windows")],
        );

        assert_eq!(summary.verdict, "hold");
        assert!(summary.queue_pressure_hold_count > 0);
        assert_eq!(summary.gate_state_reason, "required_inputs_unready");
        assert!(
            summary
                .blocking_reason_keys
                .iter()
                .any(|value| value == "queue_pressure_surface_failed")
        );
    }
}
