use ns_testkit::{
    UDP_ROLLOUT_DECISION_SCOPE_MATRIX, UDP_ROLLOUT_DECISION_SCOPE_RELEASE_WORKFLOW,
    UDP_ROLLOUT_OPERATOR_VERDICT_FAMILY, UDP_ROLLOUT_OPERATOR_VERDICT_SCHEMA,
    UDP_ROLLOUT_OPERATOR_VERDICT_SCHEMA_VERSION, repo_root, rollout_queue_hold_present,
    summarize_rollout_gate_state, udp_wan_lab_required_no_silent_fallback_profile_slugs,
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
struct WorkflowArgs {
    format: Option<OutputFormat>,
    inputs: Vec<PathBuf>,
    summary_path: Option<PathBuf>,
}

const UDP_ROLLOUT_MATRIX_SUMMARY_VERSION: u8 = 11;
const UDP_RELEASE_WORKFLOW_SUMMARY_VERSION: u8 = 8;

#[derive(Debug, Deserialize)]
struct MatrixSummaryInput {
    #[serde(default)]
    summary_version: Option<u8>,
    comparison_schema: String,
    comparison_schema_version: u8,
    verdict_family: String,
    decision_scope: String,
    decision_label: String,
    profile: String,
    verdict: String,
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
    advisory_reason_count: usize,
    host_count: usize,
    host_passed_count: usize,
    host_failed_count: usize,
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
    #[serde(default)]
    blocking_reason_keys: Vec<String>,
    #[serde(default)]
    blocking_reason_families: Vec<String>,
    #[serde(default)]
    advisory_reasons: Vec<String>,
}

#[derive(Debug)]
struct LoadedWorkflowInput {
    input_label: String,
    path: String,
    present: bool,
    parse_error: Option<String>,
    summary: Option<MatrixSummaryInput>,
}

#[derive(Debug, Serialize)]
struct WorkflowMatrixResult {
    input_label: String,
    summary_path: String,
    present: bool,
    summary_version: Option<u8>,
    comparison_schema_version: Option<u8>,
    profile: Option<String>,
    decision_label: Option<String>,
    verdict: &'static str,
    evidence_state: &'static str,
    gate_state: &'static str,
    passed: bool,
    required_inputs: Vec<String>,
    considered_inputs: Vec<String>,
    required_input_count: usize,
    required_input_missing_count: usize,
    required_input_failed_count: usize,
    required_input_present_count: usize,
    required_input_passed_count: usize,
    all_required_inputs_present: bool,
    all_required_inputs_passed: bool,
    missing_required_inputs: Vec<String>,
    blocking_reason_count: usize,
    blocking_reason_key_count: usize,
    blocking_reason_family_count: usize,
    advisory_reason_count: usize,
    blocking_reason_key_counts: BTreeMap<String, usize>,
    blocking_reason_family_counts: BTreeMap<String, usize>,
    host_count: usize,
    host_passed_count: usize,
    host_failed_count: usize,
    hosts_with_degradation_hold: Vec<String>,
    queue_guard_headroom_band_counts: BTreeMap<String, usize>,
    queue_guard_headroom_missing_count: usize,
    queue_guard_limiting_path_counts: BTreeMap<String, usize>,
    queue_guard_tight_hold_count: usize,
    queue_pressure_hold_count: usize,
    interop_required_no_silent_fallback_profile_slugs: Vec<String>,
    interop_profile_contract_passed: bool,
    blocking_reasons: Vec<String>,
    advisory_reasons: Vec<String>,
}

#[derive(Debug, Serialize)]
struct UdpReleaseWorkflowSummary {
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
    matrix_verdict_counts: BTreeMap<String, usize>,
    matrix_gate_state_counts: BTreeMap<String, usize>,
    matrix_profiles: Vec<String>,
    matrix_labels: Vec<String>,
    matrix_host_count_total: usize,
    matrix_host_passed_total: usize,
    matrix_host_failed_total: usize,
    degradation_hold_count: usize,
    degradation_hold_subjects: Vec<String>,
    queue_guard_headroom_band_counts: BTreeMap<String, usize>,
    queue_guard_headroom_missing_count: usize,
    queue_guard_limiting_path_counts: BTreeMap<String, usize>,
    queue_guard_tight_hold_count: usize,
    queue_pressure_hold_count: usize,
    interop_required_no_silent_fallback_profile_slugs: Vec<String>,
    interop_profile_contract_passed: bool,
    affected_matrix_count_by_reason_family: BTreeMap<String, usize>,
    blocking_reasons: Vec<String>,
    blocking_reason_keys: Vec<String>,
    blocking_reason_families: Vec<String>,
    advisory_reasons: Vec<String>,
    matrices: Vec<WorkflowMatrixResult>,
}

fn main() -> Result<(), Box<dyn std::error::Error>> {
    let args = parse_args(env::args().skip(1))?;
    let loaded_inputs = args
        .inputs
        .iter()
        .map(|path| load_input(path))
        .collect::<Vec<_>>();
    let summary = build_release_workflow_summary(loaded_inputs);

    let summary_path = args.summary_path.unwrap_or_else(default_summary_path);
    if let Some(parent) = summary_path.parent() {
        fs::create_dir_all(parent)?;
    }
    fs::write(&summary_path, serde_json::to_vec_pretty(&summary)?)?;

    match args.format.unwrap_or(OutputFormat::Text) {
        OutputFormat::Text => {
            println!("Northstar UDP release workflow summary:");
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
            if summary.matrix_verdict_counts.is_empty() {
                println!("- matrix_verdict_counts: none");
            } else {
                println!(
                    "- matrix_verdict_counts: {}",
                    render_counts(&summary.matrix_verdict_counts)
                );
            }
            if summary.matrix_gate_state_counts.is_empty() {
                println!("- matrix_gate_state_counts: none");
            } else {
                println!(
                    "- matrix_gate_state_counts: {}",
                    render_counts(&summary.matrix_gate_state_counts)
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
            if summary.affected_matrix_count_by_reason_family.is_empty() {
                println!("- affected_matrix_count_by_reason_family: none");
            } else {
                println!(
                    "- affected_matrix_count_by_reason_family: {}",
                    render_counts(&summary.affected_matrix_count_by_reason_family)
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
            println!("machine_readable_summary={}", summary_path.display());
        }
        OutputFormat::Json => {
            println!("{}", serde_json::to_string_pretty(&summary)?);
        }
    }

    if summary.verdict != "ready" {
        return Err("udp release workflow is not ready".into());
    }

    Ok(())
}

fn build_release_workflow_summary(inputs: Vec<LoadedWorkflowInput>) -> UdpReleaseWorkflowSummary {
    let required_inputs = vec!["readiness".to_owned(), "staged_rollout".to_owned()];
    let considered_inputs = inputs
        .iter()
        .map(|input| input.input_label.clone())
        .collect::<Vec<_>>();
    let expected_required_no_silent_fallback_profile_set =
        udp_wan_lab_required_no_silent_fallback_profile_slugs()
            .into_iter()
            .map(str::to_owned)
            .collect::<BTreeSet<_>>();
    let mut seen_profiles = BTreeMap::new();
    let mut missing_required_inputs = Vec::new();
    let mut blocking_reasons = Vec::new();
    let mut advisory_reasons = Vec::new();
    let mut blocking_reason_key_counts = BTreeMap::new();
    let mut blocking_reason_family_counts = BTreeMap::new();
    let mut matrix_verdict_counts = BTreeMap::new();
    let mut matrix_gate_state_counts = BTreeMap::new();
    let mut matrix_profiles = Vec::new();
    let mut matrix_labels = Vec::new();
    let mut queue_guard_headroom_band_counts = BTreeMap::new();
    let mut queue_guard_headroom_missing_count = 0usize;
    let mut queue_guard_limiting_path_counts = BTreeMap::new();
    let mut queue_guard_tight_hold_count = 0usize;
    let mut queue_pressure_hold_count = 0usize;
    let mut interop_required_no_silent_fallback_profile_set = BTreeSet::new();
    let mut affected_matrix_count_by_reason_family = BTreeMap::new();
    let mut degradation_hold_subjects = Vec::new();
    let mut matrices = Vec::new();
    let mut all_consumed_matrix_inputs_contract_valid = true;

    for input in inputs {
        let mut local_reasons = Vec::new();
        let matrix_result = if !input.present {
            push_reason(
                &mut blocking_reasons,
                &mut local_reasons,
                "summary_presence_missing",
                format!(
                    "missing_matrix_summary_{}",
                    sanitize_label(&input.input_label)
                ),
                "summary_presence",
            );
            WorkflowMatrixResult {
                input_label: input.input_label.clone(),
                summary_path: input.path,
                present: false,
                summary_version: None,
                comparison_schema_version: None,
                profile: None,
                decision_label: None,
                verdict: "hold",
                evidence_state: "incomplete",
                gate_state: "blocked",
                passed: false,
                required_inputs: Vec::new(),
                considered_inputs: Vec::new(),
                required_input_count: 0,
                required_input_missing_count: 0,
                required_input_failed_count: 0,
                required_input_present_count: 0,
                required_input_passed_count: 0,
                all_required_inputs_present: false,
                all_required_inputs_passed: false,
                missing_required_inputs: Vec::new(),
                blocking_reason_count: 1,
                blocking_reason_key_count: counts_from_reason_details(&local_reasons, true).len(),
                blocking_reason_family_count: counts_from_reason_details(&local_reasons, false)
                    .len(),
                advisory_reason_count: 0,
                blocking_reason_key_counts: counts_from_reason_details(&local_reasons, true),
                blocking_reason_family_counts: counts_from_reason_details(&local_reasons, false),
                host_count: 0,
                host_passed_count: 0,
                host_failed_count: 0,
                hosts_with_degradation_hold: Vec::new(),
                queue_guard_headroom_band_counts: BTreeMap::new(),
                queue_guard_headroom_missing_count: 0,
                queue_guard_limiting_path_counts: BTreeMap::new(),
                queue_guard_tight_hold_count: 0,
                queue_pressure_hold_count: 0,
                interop_required_no_silent_fallback_profile_slugs: Vec::new(),
                interop_profile_contract_passed: false,
                blocking_reasons: codes_from_reason_details(&local_reasons),
                advisory_reasons: Vec::new(),
            }
        } else if let Some(parse_error) = &input.parse_error {
            push_reason(
                &mut blocking_reasons,
                &mut local_reasons,
                "summary_parse_failed",
                format!(
                    "invalid_matrix_summary_{}",
                    sanitize_label(&input.input_label)
                ),
                "summary_parse",
            );
            advisory_reasons.push(format!(
                "{}:parse_error={}",
                input.input_label,
                parse_error.replace(char::is_whitespace, " ")
            ));
            WorkflowMatrixResult {
                input_label: input.input_label.clone(),
                summary_path: input.path,
                present: true,
                summary_version: None,
                comparison_schema_version: None,
                profile: None,
                decision_label: None,
                verdict: "hold",
                evidence_state: "incomplete",
                gate_state: "blocked",
                passed: false,
                required_inputs: Vec::new(),
                considered_inputs: Vec::new(),
                required_input_count: 0,
                required_input_missing_count: 0,
                required_input_failed_count: 0,
                required_input_present_count: 0,
                required_input_passed_count: 0,
                all_required_inputs_present: false,
                all_required_inputs_passed: false,
                missing_required_inputs: Vec::new(),
                blocking_reason_count: 1,
                blocking_reason_key_count: counts_from_reason_details(&local_reasons, true).len(),
                blocking_reason_family_count: counts_from_reason_details(&local_reasons, false)
                    .len(),
                advisory_reason_count: 1,
                blocking_reason_key_counts: counts_from_reason_details(&local_reasons, true),
                blocking_reason_family_counts: counts_from_reason_details(&local_reasons, false),
                host_count: 0,
                host_passed_count: 0,
                host_failed_count: 0,
                hosts_with_degradation_hold: Vec::new(),
                queue_guard_headroom_band_counts: BTreeMap::new(),
                queue_guard_headroom_missing_count: 0,
                queue_guard_limiting_path_counts: BTreeMap::new(),
                queue_guard_tight_hold_count: 0,
                queue_pressure_hold_count: 0,
                interop_required_no_silent_fallback_profile_slugs: Vec::new(),
                interop_profile_contract_passed: false,
                blocking_reasons: codes_from_reason_details(&local_reasons),
                advisory_reasons: vec![format!("parse_error={parse_error}")],
            }
        } else {
            let summary = input
                .summary
                .as_ref()
                .expect("workflow input should have parse_error or summary");
            let profile = summary.profile.clone();
            let actual_required_no_silent_fallback_profile_set = summary
                .interop_required_no_silent_fallback_profile_slugs
                .iter()
                .cloned()
                .collect::<BTreeSet<_>>();
            let mut summary_contract_valid = true;
            *seen_profiles.entry(profile.clone()).or_insert(0usize) += 1;

            if summary.summary_version != Some(UDP_ROLLOUT_MATRIX_SUMMARY_VERSION) {
                summary_contract_valid = false;
                push_reason(
                    &mut blocking_reasons,
                    &mut local_reasons,
                    "summary_version_unsupported",
                    format!("{}_summary_version_unsupported", sanitize_label(&profile)),
                    "summary_version",
                );
            }
            if summary.comparison_schema != UDP_ROLLOUT_OPERATOR_VERDICT_SCHEMA {
                summary_contract_valid = false;
                push_reason(
                    &mut blocking_reasons,
                    &mut local_reasons,
                    "comparison_schema_unsupported",
                    format!("{}_comparison_schema_unsupported", sanitize_label(&profile)),
                    "schema",
                );
            }
            if summary.comparison_schema_version != UDP_ROLLOUT_OPERATOR_VERDICT_SCHEMA_VERSION {
                summary_contract_valid = false;
                push_reason(
                    &mut blocking_reasons,
                    &mut local_reasons,
                    "comparison_schema_version_unsupported",
                    format!(
                        "{}_comparison_schema_version_unsupported",
                        sanitize_label(&profile)
                    ),
                    "schema",
                );
            }
            if summary.verdict_family != UDP_ROLLOUT_OPERATOR_VERDICT_FAMILY {
                summary_contract_valid = false;
                push_reason(
                    &mut blocking_reasons,
                    &mut local_reasons,
                    "verdict_family_unsupported",
                    format!("{}_verdict_family_unsupported", sanitize_label(&profile)),
                    "schema",
                );
            }
            if summary.decision_scope != UDP_ROLLOUT_DECISION_SCOPE_MATRIX {
                summary_contract_valid = false;
                push_reason(
                    &mut blocking_reasons,
                    &mut local_reasons,
                    "decision_scope_mismatch",
                    format!("{}_decision_scope_mismatch", sanitize_label(&profile)),
                    "shape",
                );
            }
            if summary
                .interop_required_no_silent_fallback_profile_slugs
                .iter()
                .any(|slug| slug.trim().is_empty())
                || actual_required_no_silent_fallback_profile_set.len()
                    != summary
                        .interop_required_no_silent_fallback_profile_slugs
                        .len()
            {
                summary_contract_valid = false;
                push_reason(
                    &mut blocking_reasons,
                    &mut local_reasons,
                    "interop_required_no_silent_fallback_profile_set_mismatch",
                    format!(
                        "{}_interop_required_no_silent_fallback_profile_set_mismatch",
                        sanitize_label(&profile)
                    ),
                    "summary_contract",
                );
            }
            if actual_required_no_silent_fallback_profile_set
                != expected_required_no_silent_fallback_profile_set
            {
                summary_contract_valid = false;
                push_reason(
                    &mut blocking_reasons,
                    &mut local_reasons,
                    "interop_required_no_silent_fallback_profile_set_mismatch",
                    format!(
                        "{}_interop_required_no_silent_fallback_profile_set_mismatch",
                        sanitize_label(&profile)
                    ),
                    "summary_contract",
                );
            }
            if !rollout_input_identity_consistent(
                &summary.required_inputs,
                &summary.considered_inputs,
                &summary.missing_required_inputs,
                summary.required_input_count,
            ) {
                summary_contract_valid = false;
                push_reason(
                    &mut blocking_reasons,
                    &mut local_reasons,
                    "input_identity_inconsistent",
                    format!("{}_input_identity_inconsistent", sanitize_label(&profile)),
                    "required_inputs",
                );
            }
            if !blocking_reason_accounting_consistent(
                summary.blocking_reason_count,
                &summary.blocking_reasons,
                &summary.blocking_reason_keys,
                &summary.blocking_reason_families,
                &summary.blocking_reason_key_counts,
                &summary.blocking_reason_family_counts,
            ) {
                summary_contract_valid = false;
                push_reason(
                    &mut blocking_reasons,
                    &mut local_reasons,
                    "blocking_reason_accounting_inconsistent",
                    format!(
                        "{}_blocking_reason_accounting_inconsistent",
                        sanitize_label(&profile)
                    ),
                    "shape",
                );
            }
            if summary.missing_required_input_count != summary.missing_required_inputs.len() {
                summary_contract_valid = false;
                push_reason(
                    &mut blocking_reasons,
                    &mut local_reasons,
                    "missing_required_input_count_inconsistent",
                    format!(
                        "{}_missing_required_input_count_inconsistent",
                        sanitize_label(&profile)
                    ),
                    "required_inputs",
                );
            }
            if summary.required_input_missing_count != summary.missing_required_inputs.len() {
                summary_contract_valid = false;
                push_reason(
                    &mut blocking_reasons,
                    &mut local_reasons,
                    "required_input_missing_count_inconsistent",
                    format!(
                        "{}_required_input_missing_count_inconsistent",
                        sanitize_label(&profile)
                    ),
                    "required_inputs",
                );
            }
            if summary.required_input_present_count > summary.required_input_count {
                summary_contract_valid = false;
                push_reason(
                    &mut blocking_reasons,
                    &mut local_reasons,
                    "required_input_present_count_inconsistent",
                    format!(
                        "{}_required_input_present_count_inconsistent",
                        sanitize_label(&profile)
                    ),
                    "required_inputs",
                );
            }
            if summary.required_input_passed_count > summary.required_input_present_count {
                summary_contract_valid = false;
                push_reason(
                    &mut blocking_reasons,
                    &mut local_reasons,
                    "required_input_passed_count_inconsistent",
                    format!(
                        "{}_required_input_passed_count_inconsistent",
                        sanitize_label(&profile)
                    ),
                    "required_inputs",
                );
            }
            if summary.required_input_failed_count
                != summary
                    .required_input_count
                    .saturating_sub(summary.required_input_passed_count)
            {
                summary_contract_valid = false;
                push_reason(
                    &mut blocking_reasons,
                    &mut local_reasons,
                    "required_input_failed_count_inconsistent",
                    format!(
                        "{}_required_input_failed_count_inconsistent",
                        sanitize_label(&profile)
                    ),
                    "required_inputs",
                );
            }
            if summary.required_input_unready_count
                != summary
                    .required_input_failed_count
                    .saturating_sub(summary.required_input_missing_count)
            {
                summary_contract_valid = false;
                push_reason(
                    &mut blocking_reasons,
                    &mut local_reasons,
                    "required_input_unready_count_inconsistent",
                    format!(
                        "{}_required_input_unready_count_inconsistent",
                        sanitize_label(&profile)
                    ),
                    "required_inputs",
                );
            }
            if summary.all_required_inputs_present
                != (summary.required_input_present_count == summary.required_input_count)
            {
                summary_contract_valid = false;
                push_reason(
                    &mut blocking_reasons,
                    &mut local_reasons,
                    "all_required_inputs_present_inconsistent",
                    format!(
                        "{}_all_required_inputs_present_inconsistent",
                        sanitize_label(&profile)
                    ),
                    "required_inputs",
                );
            }
            let (expected_gate_state_reason, expected_gate_state_reason_family) =
                summarize_rollout_gate_state(
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
            if summary.gate_state_reason != expected_gate_state_reason
                || summary.gate_state_reason_family != expected_gate_state_reason_family
            {
                summary_contract_valid = false;
                push_reason(
                    &mut blocking_reasons,
                    &mut local_reasons,
                    "gate_state_reason_inconsistent",
                    format!(
                        "{}_gate_state_reason_inconsistent",
                        sanitize_label(&profile)
                    ),
                    "shape",
                );
            }
            if summary.all_required_inputs_passed
                != (summary.required_input_present_count == summary.required_input_count
                    && summary.required_input_passed_count == summary.required_input_count)
            {
                summary_contract_valid = false;
                push_reason(
                    &mut blocking_reasons,
                    &mut local_reasons,
                    "all_required_inputs_passed_inconsistent",
                    format!(
                        "{}_all_required_inputs_passed_inconsistent",
                        sanitize_label(&profile)
                    ),
                    "required_inputs",
                );
            }
            if summary.degradation_hold_count != summary.degradation_hold_subjects.len() {
                summary_contract_valid = false;
                push_reason(
                    &mut blocking_reasons,
                    &mut local_reasons,
                    "degradation_hold_count_inconsistent",
                    format!(
                        "{}_degradation_hold_count_inconsistent",
                        sanitize_label(&profile)
                    ),
                    "degradation",
                );
            }
            if summary.queue_pressure_hold_count > summary.host_count {
                summary_contract_valid = false;
                push_reason(
                    &mut blocking_reasons,
                    &mut local_reasons,
                    "queue_pressure_hold_count_inconsistent",
                    format!(
                        "{}_queue_pressure_hold_count_inconsistent",
                        sanitize_label(&profile)
                    ),
                    "summary_contract",
                );
            }
            if summary.queue_pressure_hold_count > 0
                && !summary
                    .blocking_reason_family_counts
                    .contains_key("capacity")
            {
                summary_contract_valid = false;
                push_reason(
                    &mut blocking_reasons,
                    &mut local_reasons,
                    "queue_pressure_hold_count_inconsistent",
                    format!(
                        "{}_queue_pressure_hold_count_inconsistent",
                        sanitize_label(&profile)
                    ),
                    "summary_contract",
                );
            }
            if summary.blocking_reason_key_count != summary.blocking_reason_key_counts.len() {
                summary_contract_valid = false;
                push_reason(
                    &mut blocking_reasons,
                    &mut local_reasons,
                    "blocking_reason_key_count_inconsistent",
                    format!(
                        "{}_blocking_reason_key_count_inconsistent",
                        sanitize_label(&profile)
                    ),
                    "shape",
                );
            }
            if summary.blocking_reason_family_count != summary.blocking_reason_family_counts.len() {
                summary_contract_valid = false;
                push_reason(
                    &mut blocking_reasons,
                    &mut local_reasons,
                    "blocking_reason_family_count_inconsistent",
                    format!(
                        "{}_blocking_reason_family_count_inconsistent",
                        sanitize_label(&profile)
                    ),
                    "shape",
                );
            }
            if summary.verdict == "ready"
                && (summary.blocking_reason_count != 0
                    || !summary.missing_required_inputs.is_empty()
                    || summary.degradation_hold_count != 0
                    || summary.queue_pressure_hold_count != 0)
            {
                summary_contract_valid = false;
                push_reason(
                    &mut blocking_reasons,
                    &mut local_reasons,
                    "ready_verdict_blocking_semantics_inconsistent",
                    format!(
                        "{}_ready_verdict_blocking_semantics_inconsistent",
                        sanitize_label(&profile)
                    ),
                    "gating",
                );
            }
            if !summary.missing_required_inputs.is_empty()
                && !summary
                    .blocking_reason_family_counts
                    .keys()
                    .any(|family| family == "summary_presence" || family == "required_inputs")
            {
                summary_contract_valid = false;
                push_reason(
                    &mut blocking_reasons,
                    &mut local_reasons,
                    "missing_required_inputs_family_inconsistent",
                    format!(
                        "{}_missing_required_inputs_family_inconsistent",
                        sanitize_label(&profile)
                    ),
                    "required_inputs",
                );
            }
            if summary.degradation_hold_count > 0
                && !summary
                    .blocking_reason_family_counts
                    .contains_key("degradation")
            {
                summary_contract_valid = false;
                push_reason(
                    &mut blocking_reasons,
                    &mut local_reasons,
                    "degradation_hold_family_inconsistent",
                    format!(
                        "{}_degradation_hold_family_inconsistent",
                        sanitize_label(&profile)
                    ),
                    "degradation",
                );
            }
            if summary_contract_valid
                && summary.profile == "staged_rollout"
                && !summary.active_fuzz_required
            {
                push_reason(
                    &mut blocking_reasons,
                    &mut local_reasons,
                    "staged_rollout_active_fuzz_requirement_missing",
                    format!(
                        "{}_staged_rollout_active_fuzz_requirement_missing",
                        sanitize_label(&profile)
                    ),
                    "required_inputs",
                );
            }
            if summary_contract_valid
                && (summary.verdict != "ready"
                    || summary.gate_state != "passed"
                    || !summary.all_required_inputs_present
                    || !summary.all_required_inputs_passed)
            {
                push_reason(
                    &mut blocking_reasons,
                    &mut local_reasons,
                    "matrix_verdict_not_ready",
                    format!("{}_matrix_verdict_not_ready", sanitize_label(&profile)),
                    "gating",
                );
            }
            if summary_contract_valid && summary.queue_pressure_hold_count > 0 {
                push_reason(
                    &mut blocking_reasons,
                    &mut local_reasons,
                    "queue_pressure_surface_failed",
                    format!("{}_queue_pressure_surface_failed", sanitize_label(&profile)),
                    "capacity",
                );
            }
            if summary_contract_valid && !summary.hosts_with_degradation_hold.is_empty() {
                push_reason(
                    &mut blocking_reasons,
                    &mut local_reasons,
                    "matrix_degradation_hold_present",
                    format!(
                        "{}_matrix_degradation_hold_present",
                        sanitize_label(&profile)
                    ),
                    "degradation",
                );
            }
            if summary.degradation_hold_count > 0
                && !summary
                    .blocking_reason_family_counts
                    .contains_key("degradation")
            {
                summary_contract_valid = false;
                push_reason(
                    &mut blocking_reasons,
                    &mut local_reasons,
                    "degradation_hold_family_inconsistent",
                    format!(
                        "{}_degradation_hold_family_inconsistent",
                        sanitize_label(&profile)
                    ),
                    "degradation",
                );
            }

            let mut families = BTreeSet::new();
            if summary_contract_valid {
                matrix_profiles.push(profile.clone());
                matrix_labels.push(summary.decision_label.clone());
                *matrix_verdict_counts
                    .entry(summary.verdict.clone())
                    .or_insert(0) += 1;
                *matrix_gate_state_counts
                    .entry(summary.gate_state.clone())
                    .or_insert(0) += 1;
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
                merge_counts(
                    &mut blocking_reason_key_counts,
                    &summary.blocking_reason_key_counts,
                );
                merge_counts(
                    &mut blocking_reason_family_counts,
                    &summary.blocking_reason_family_counts,
                );
                blocking_reasons.extend(
                    summary
                        .blocking_reasons
                        .iter()
                        .map(|reason| format!("{}:{reason}", summary.profile)),
                );
                advisory_reasons.extend(
                    summary
                        .advisory_reasons
                        .iter()
                        .map(|reason| format!("{}:{reason}", summary.profile)),
                );
                degradation_hold_subjects.extend(summary.degradation_hold_subjects.iter().cloned());
                for family in summary.blocking_reason_family_counts.keys() {
                    families.insert(family.clone());
                }
            } else {
                all_consumed_matrix_inputs_contract_valid = false;
            }
            for detail in &local_reasons {
                families.insert(detail.family.to_owned());
            }
            for family in families {
                *affected_matrix_count_by_reason_family
                    .entry(family)
                    .or_insert(0) += 1;
            }

            merge_counts(
                &mut blocking_reason_key_counts,
                &counts_from_reason_details(&local_reasons, true),
            );
            merge_counts(
                &mut blocking_reason_family_counts,
                &counts_from_reason_details(&local_reasons, false),
            );

            WorkflowMatrixResult {
                input_label: input.input_label.clone(),
                summary_path: input.path,
                present: true,
                summary_version: summary.summary_version,
                comparison_schema_version: Some(summary.comparison_schema_version),
                profile: Some(summary.profile.clone()),
                decision_label: Some(summary.decision_label.clone()),
                verdict: if local_reasons.is_empty() && summary.verdict == "ready" {
                    "ready"
                } else {
                    "hold"
                },
                evidence_state: if summary.all_required_inputs_present {
                    "complete"
                } else {
                    "incomplete"
                },
                gate_state: if local_reasons.is_empty() && summary.gate_state == "passed" {
                    "passed"
                } else {
                    "blocked"
                },
                passed: local_reasons.is_empty()
                    && summary_contract_valid
                    && summary.verdict == "ready"
                    && summary.gate_state == "passed"
                    && summary.all_required_inputs_present
                    && summary.all_required_inputs_passed,
                required_inputs: summary.required_inputs.clone(),
                considered_inputs: summary.considered_inputs.clone(),
                required_input_count: summary.required_input_count,
                required_input_missing_count: summary.required_input_missing_count,
                required_input_failed_count: summary.required_input_failed_count,
                required_input_present_count: summary.required_input_present_count,
                required_input_passed_count: summary.required_input_passed_count,
                all_required_inputs_present: summary.all_required_inputs_present,
                all_required_inputs_passed: summary.all_required_inputs_passed,
                missing_required_inputs: summary.missing_required_inputs.clone(),
                blocking_reason_count: if summary_contract_valid {
                    summary.blocking_reason_count + local_reasons.len()
                } else {
                    local_reasons.len()
                },
                blocking_reason_key_count: if summary_contract_valid {
                    summary.blocking_reason_key_count
                } else {
                    counts_from_reason_details(&local_reasons, true).len()
                },
                blocking_reason_family_count: if summary_contract_valid {
                    summary.blocking_reason_family_count
                } else {
                    counts_from_reason_details(&local_reasons, false).len()
                },
                advisory_reason_count: if summary_contract_valid {
                    summary.advisory_reason_count + summary.advisory_reasons.len()
                } else {
                    0
                },
                blocking_reason_key_counts: {
                    let mut counts = if summary_contract_valid {
                        summary.blocking_reason_key_counts.clone()
                    } else {
                        BTreeMap::new()
                    };
                    merge_counts(
                        &mut counts,
                        &counts_from_reason_details(&local_reasons, true),
                    );
                    counts
                },
                blocking_reason_family_counts: {
                    let mut counts = if summary_contract_valid {
                        summary.blocking_reason_family_counts.clone()
                    } else {
                        BTreeMap::new()
                    };
                    merge_counts(
                        &mut counts,
                        &counts_from_reason_details(&local_reasons, false),
                    );
                    counts
                },
                host_count: summary.host_count,
                host_passed_count: summary.host_passed_count,
                host_failed_count: summary.host_failed_count,
                hosts_with_degradation_hold: if summary_contract_valid {
                    summary.hosts_with_degradation_hold.clone()
                } else {
                    Vec::new()
                },
                queue_guard_headroom_band_counts: if summary_contract_valid {
                    summary.queue_guard_headroom_band_counts.clone()
                } else {
                    BTreeMap::new()
                },
                queue_guard_headroom_missing_count: if summary_contract_valid {
                    summary.queue_guard_headroom_missing_count
                } else {
                    0
                },
                queue_guard_limiting_path_counts: if summary_contract_valid {
                    summary.queue_guard_limiting_path_counts.clone()
                } else {
                    BTreeMap::new()
                },
                queue_guard_tight_hold_count: if summary_contract_valid {
                    summary.queue_guard_tight_hold_count
                } else {
                    0
                },
                queue_pressure_hold_count: if summary_contract_valid {
                    summary.queue_pressure_hold_count
                } else {
                    0
                },
                interop_required_no_silent_fallback_profile_slugs: if summary_contract_valid {
                    summary
                        .interop_required_no_silent_fallback_profile_slugs
                        .clone()
                } else {
                    Vec::new()
                },
                interop_profile_contract_passed: if summary_contract_valid {
                    summary.interop_profile_contract_passed
                } else {
                    false
                },
                blocking_reasons: {
                    let mut reasons = if summary_contract_valid {
                        summary.blocking_reasons.clone()
                    } else {
                        Vec::new()
                    };
                    reasons.extend(codes_from_reason_details(&local_reasons));
                    reasons
                },
                advisory_reasons: if summary_contract_valid {
                    summary.advisory_reasons.clone()
                } else {
                    Vec::new()
                },
            }
        };

        matrices.push(matrix_result);
    }

    degradation_hold_subjects.sort();
    degradation_hold_subjects.dedup();
    for required in &required_inputs {
        match seen_profiles.get(required) {
            Some(1) => {}
            Some(_) => {
                all_consumed_matrix_inputs_contract_valid = false;
                let mut local_reasons = Vec::new();
                push_reason(
                    &mut blocking_reasons,
                    &mut local_reasons,
                    "duplicate_matrix_profile",
                    format!("duplicate_matrix_profile_{}", sanitize_label(required)),
                    "shape",
                );
                merge_counts(
                    &mut blocking_reason_key_counts,
                    &counts_from_reason_details(&local_reasons, true),
                );
                merge_counts(
                    &mut blocking_reason_family_counts,
                    &counts_from_reason_details(&local_reasons, false),
                );
            }
            None => missing_required_inputs.push(required.clone()),
        }
    }

    for missing in &missing_required_inputs {
        let mut local_reasons = Vec::new();
        push_reason(
            &mut blocking_reasons,
            &mut local_reasons,
            "summary_presence_missing",
            format!("missing_required_matrix_{}", sanitize_label(missing)),
            "summary_presence",
        );
        merge_counts(
            &mut blocking_reason_key_counts,
            &counts_from_reason_details(&local_reasons, true),
        );
        merge_counts(
            &mut blocking_reason_family_counts,
            &counts_from_reason_details(&local_reasons, false),
        );
    }

    let required_input_count = required_inputs.len();
    let missing_required_input_count = missing_required_inputs.len();
    let required_input_missing_count = missing_required_input_count;
    let required_input_present_count = required_inputs
        .iter()
        .filter(|profile| seen_profiles.contains_key(*profile))
        .count();
    let required_input_passed_count = required_inputs
        .iter()
        .filter(|profile| {
            matrices
                .iter()
                .any(|matrix| matrix.passed && matrix.profile.as_deref() == Some(profile.as_str()))
        })
        .count();
    let required_input_failed_count =
        required_input_count.saturating_sub(required_input_passed_count);
    let required_input_unready_count =
        required_input_failed_count.saturating_sub(required_input_missing_count);
    let all_required_inputs_present = required_input_present_count == required_input_count;
    let all_required_inputs_passed =
        all_required_inputs_present && required_input_passed_count == required_input_count;

    matrix_profiles.sort();
    matrix_profiles.dedup();
    matrix_labels.sort();
    matrix_labels.dedup();

    let matrix_host_count_total = matrices.iter().map(|matrix| matrix.host_count).sum();
    let matrix_host_passed_total = matrices.iter().map(|matrix| matrix.host_passed_count).sum();
    let matrix_host_failed_total = matrices.iter().map(|matrix| matrix.host_failed_count).sum();
    let degradation_hold_count = degradation_hold_subjects.len();
    let interop_profile_contract_passed = all_required_inputs_present
        && matrices
            .iter()
            .all(|matrix| matrix.interop_profile_contract_passed)
        && interop_required_no_silent_fallback_profile_set
            == expected_required_no_silent_fallback_profile_set;
    if queue_pressure_hold_count > 0 {
        let mut local_reasons = Vec::new();
        push_reason(
            &mut blocking_reasons,
            &mut local_reasons,
            "queue_pressure_surface_failed",
            "release_workflow_queue_pressure_surface_failed".to_owned(),
            "capacity",
        );
        merge_counts(
            &mut blocking_reason_key_counts,
            &counts_from_reason_details(&local_reasons, true),
        );
        merge_counts(
            &mut blocking_reason_family_counts,
            &counts_from_reason_details(&local_reasons, false),
        );
    }
    if interop_required_no_silent_fallback_profile_set
        != expected_required_no_silent_fallback_profile_set
    {
        let mut local_reasons = Vec::new();
        push_reason(
            &mut blocking_reasons,
            &mut local_reasons,
            "interop_required_no_silent_fallback_profile_set_mismatch",
            "release_workflow_interop_required_no_silent_fallback_profile_set_mismatch".to_owned(),
            "summary_contract",
        );
        merge_counts(
            &mut blocking_reason_key_counts,
            &counts_from_reason_details(&local_reasons, true),
        );
        merge_counts(
            &mut blocking_reason_family_counts,
            &counts_from_reason_details(&local_reasons, false),
        );
    }
    if queue_guard_tight_hold_count > 0 {
        let mut local_reasons = Vec::new();
        push_reason(
            &mut blocking_reasons,
            &mut local_reasons,
            "queue_guard_headroom_tight",
            "queue_guard_headroom_tight".to_owned(),
            "capacity",
        );
        merge_counts(
            &mut blocking_reason_key_counts,
            &counts_from_reason_details(&local_reasons, true),
        );
        merge_counts(
            &mut blocking_reason_family_counts,
            &counts_from_reason_details(&local_reasons, false),
        );
    }
    let blocking_reason_count = blocking_reasons.len();
    let blocking_reason_key_count = blocking_reason_key_counts.len();
    let blocking_reason_family_count = blocking_reason_family_counts.len();
    let advisory_reason_count = advisory_reasons.len();
    let evidence_state = if all_required_inputs_present && all_consumed_matrix_inputs_contract_valid
    {
        "complete"
    } else {
        "incomplete"
    };
    let queue_hold_present = rollout_queue_hold_present(
        queue_guard_headroom_missing_count,
        queue_guard_tight_hold_count,
        queue_pressure_hold_count,
    );
    let gate_state =
        if blocking_reason_count == 0 && all_required_inputs_passed && !queue_hold_present {
            "passed"
        } else {
            "blocked"
        };
    let verdict = if all_required_inputs_passed && blocking_reason_count == 0 && !queue_hold_present
    {
        "ready"
    } else {
        "hold"
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

    UdpReleaseWorkflowSummary {
        summary_version: UDP_RELEASE_WORKFLOW_SUMMARY_VERSION,
        comparison_schema: UDP_ROLLOUT_OPERATOR_VERDICT_SCHEMA,
        comparison_schema_version: UDP_ROLLOUT_OPERATOR_VERDICT_SCHEMA_VERSION,
        verdict_family: UDP_ROLLOUT_OPERATOR_VERDICT_FAMILY,
        decision_scope: UDP_ROLLOUT_DECISION_SCOPE_RELEASE_WORKFLOW,
        decision_label: "release_workflow",
        profile: "release_workflow",
        verdict,
        evidence_state,
        gate_state,
        gate_state_reason,
        gate_state_reason_family,
        active_fuzz_required: true,
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
        all_required_inputs_present,
        all_required_inputs_passed,
        blocking_reason_count,
        blocking_reason_key_count,
        blocking_reason_family_count,
        blocking_reason_key_counts,
        blocking_reason_family_counts,
        advisory_reason_count,
        matrix_verdict_counts,
        matrix_gate_state_counts,
        matrix_profiles,
        matrix_labels,
        matrix_host_count_total,
        matrix_host_passed_total,
        matrix_host_failed_total,
        degradation_hold_count,
        degradation_hold_subjects,
        queue_guard_headroom_band_counts,
        queue_guard_headroom_missing_count,
        queue_guard_limiting_path_counts,
        queue_guard_tight_hold_count,
        queue_pressure_hold_count,
        interop_required_no_silent_fallback_profile_slugs,
        interop_profile_contract_passed,
        affected_matrix_count_by_reason_family,
        blocking_reasons,
        blocking_reason_keys,
        blocking_reason_families,
        advisory_reasons,
        matrices,
    }
}

fn load_input(path: &Path) -> LoadedWorkflowInput {
    let input_label = path
        .file_stem()
        .map(|value| value.to_string_lossy().into_owned())
        .unwrap_or_else(|| "workflow-input".to_owned());
    let display_path = path.display().to_string();
    if !path.exists() {
        return LoadedWorkflowInput {
            input_label,
            path: display_path,
            present: false,
            parse_error: None,
            summary: None,
        };
    }

    match fs::read(path)
        .map_err(|error| error.to_string())
        .and_then(|bytes| {
            serde_json::from_slice::<MatrixSummaryInput>(&bytes).map_err(|error| error.to_string())
        }) {
        Ok(summary) => LoadedWorkflowInput {
            input_label,
            path: display_path,
            present: true,
            parse_error: None,
            summary: Some(summary),
        },
        Err(error) => LoadedWorkflowInput {
            input_label,
            path: display_path,
            present: true,
            parse_error: Some(error),
            summary: None,
        },
    }
}

fn render_counts(counts: &BTreeMap<String, usize>) -> String {
    counts
        .iter()
        .map(|(key, count)| format!("{key}={count}"))
        .collect::<Vec<_>>()
        .join(", ")
}

fn merge_counts(destination: &mut BTreeMap<String, usize>, source: &BTreeMap<String, usize>) {
    for (key, count) in source {
        *destination.entry(key.clone()).or_insert(0) += count;
    }
}

fn blocking_reason_accounting_consistent(
    blocking_reason_count: usize,
    blocking_reasons: &[String],
    blocking_reason_keys: &[String],
    blocking_reason_families: &[String],
    blocking_reason_key_counts: &BTreeMap<String, usize>,
    blocking_reason_family_counts: &BTreeMap<String, usize>,
) -> bool {
    let key_total = blocking_reason_key_counts.values().sum::<usize>();
    let family_total = blocking_reason_family_counts.values().sum::<usize>();
    let mut expected_keys = blocking_reason_key_counts
        .keys()
        .cloned()
        .collect::<Vec<_>>();
    expected_keys.sort();
    let mut expected_families = blocking_reason_family_counts
        .keys()
        .cloned()
        .collect::<Vec<_>>();
    expected_families.sort();
    blocking_reason_count == blocking_reasons.len()
        && blocking_reason_keys == expected_keys
        && blocking_reason_families == expected_families
        && blocking_reason_count == key_total
        && blocking_reason_count == family_total
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

fn sanitize_label(value: &str) -> String {
    value
        .chars()
        .map(|character| {
            if character.is_ascii_alphanumeric() {
                character.to_ascii_lowercase()
            } else {
                '_'
            }
        })
        .collect()
}

#[derive(Debug)]
struct ReasonDetail {
    code: String,
    reason_key: &'static str,
    family: &'static str,
}

fn push_reason(
    reasons: &mut Vec<String>,
    details: &mut Vec<ReasonDetail>,
    reason_key: &'static str,
    code: String,
    family: &'static str,
) {
    reasons.push(code.clone());
    details.push(ReasonDetail {
        code,
        reason_key,
        family,
    });
}

fn counts_from_reason_details(details: &[ReasonDetail], by_key: bool) -> BTreeMap<String, usize> {
    let mut counts = BTreeMap::new();
    for detail in details {
        let key = if by_key {
            detail.reason_key.to_owned()
        } else {
            detail.family.to_owned()
        };
        *counts.entry(key).or_insert(0) += 1;
    }
    counts
}

fn codes_from_reason_details(details: &[ReasonDetail]) -> Vec<String> {
    details.iter().map(|detail| detail.code.clone()).collect()
}

fn parse_args(
    arguments: impl IntoIterator<Item = String>,
) -> Result<WorkflowArgs, Box<dyn std::error::Error>> {
    let mut parsed = WorkflowArgs::default();
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
            "--input" => {
                let value = iter.next().ok_or("--input requires a summary path")?;
                parsed.inputs.push(PathBuf::from(value));
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

    if parsed.inputs.is_empty() {
        return Err("at least one --input summary path is required".into());
    }

    Ok(parsed)
}

fn print_usage() {
    eprintln!(
        "Usage: cargo run -p ns-testkit --example udp_release_workflow -- [--format text|json] [--summary-path <path>] --input <matrix-summary-path> [--input <matrix-summary-path> ...]"
    );
}

fn default_summary_path() -> PathBuf {
    repo_root()
        .join("target")
        .join("northstar")
        .join("udp-release-workflow-summary.json")
}

#[cfg(test)]
mod tests {
    use super::{
        LoadedWorkflowInput, MatrixSummaryInput, UDP_RELEASE_WORKFLOW_SUMMARY_VERSION,
        UDP_ROLLOUT_MATRIX_SUMMARY_VERSION, build_release_workflow_summary,
    };
    use ns_testkit::{
        UDP_ROLLOUT_OPERATOR_VERDICT_SCHEMA_VERSION,
        udp_wan_lab_required_no_silent_fallback_profile_slugs,
    };
    use std::collections::{BTreeMap, BTreeSet};

    fn loaded(path: &str, profile: &str, verdict: &str) -> LoadedWorkflowInput {
        let required_inputs = vec![profile.to_owned()];
        let considered_inputs = vec![profile.to_owned()];
        let queue_guard_headroom_band_counts = BTreeMap::from([("healthy".to_owned(), 1usize)]);
        LoadedWorkflowInput {
            input_label: profile.to_owned(),
            path: path.to_owned(),
            present: true,
            parse_error: None,
            summary: Some(MatrixSummaryInput {
                summary_version: Some(UDP_ROLLOUT_MATRIX_SUMMARY_VERSION),
                comparison_schema: "udp_rollout_operator_verdict".to_owned(),
                comparison_schema_version: UDP_ROLLOUT_OPERATOR_VERDICT_SCHEMA_VERSION,
                verdict_family: "udp_rollout_operator_decision".to_owned(),
                decision_scope: "matrix".to_owned(),
                decision_label: format!("{profile}_matrix"),
                profile: profile.to_owned(),
                verdict: verdict.to_owned(),
                gate_state: if verdict == "ready" {
                    "passed".to_owned()
                } else {
                    "blocked".to_owned()
                },
                gate_state_reason: if verdict == "ready" {
                    "all_required_inputs_passed".to_owned()
                } else {
                    "required_inputs_unready".to_owned()
                },
                gate_state_reason_family: if verdict == "ready" {
                    "ready".to_owned()
                } else {
                    "gating".to_owned()
                },
                active_fuzz_required: profile == "staged_rollout",
                required_inputs,
                considered_inputs,
                missing_required_inputs: Vec::new(),
                missing_required_input_count: 0,
                required_input_count: 1,
                required_input_missing_count: 0,
                required_input_failed_count: if verdict == "ready" { 0 } else { 1 },
                required_input_unready_count: if verdict == "ready" { 0 } else { 1 },
                required_input_present_count: 1,
                required_input_passed_count: if verdict == "ready" { 1 } else { 0 },
                all_required_inputs_present: true,
                all_required_inputs_passed: verdict == "ready",
                blocking_reason_count: if verdict == "ready" { 0 } else { 1 },
                blocking_reason_key_count: if verdict == "ready" { 0 } else { 1 },
                blocking_reason_family_count: if verdict == "ready" { 0 } else { 1 },
                blocking_reason_key_counts: if verdict == "ready" {
                    BTreeMap::new()
                } else {
                    BTreeMap::from([("host_verdict_not_ready".to_owned(), 1)])
                },
                blocking_reason_family_counts: if verdict == "ready" {
                    BTreeMap::new()
                } else {
                    BTreeMap::from([("gating".to_owned(), 1)])
                },
                advisory_reason_count: 0,
                host_count: 1,
                host_passed_count: if verdict == "ready" { 1 } else { 0 },
                host_failed_count: if verdict == "ready" { 0 } else { 1 },
                hosts_with_degradation_hold: Vec::new(),
                degradation_hold_count: 0,
                degradation_hold_subjects: Vec::new(),
                queue_guard_headroom_band_counts,
                queue_guard_headroom_missing_count: 0,
                queue_guard_limiting_path_counts: BTreeMap::from([("recovery".to_owned(), 1)]),
                queue_guard_tight_hold_count: 0,
                queue_pressure_hold_count: 0,
                interop_required_no_silent_fallback_profile_slugs:
                    udp_wan_lab_required_no_silent_fallback_profile_slugs()
                        .into_iter()
                        .map(str::to_owned)
                        .collect(),
                interop_profile_contract_passed: true,
                blocking_reasons: if verdict == "ready" {
                    Vec::new()
                } else {
                    vec!["linux:host_verdict_not_ready".to_owned()]
                },
                blocking_reason_keys: if verdict == "ready" {
                    Vec::new()
                } else {
                    vec!["host_verdict_not_ready".to_owned()]
                },
                blocking_reason_families: if verdict == "ready" {
                    Vec::new()
                } else {
                    vec!["gating".to_owned()]
                },
                advisory_reasons: Vec::new(),
            }),
        }
    }

    #[test]
    fn release_workflow_requires_readiness_and_staged_inputs() {
        let summary = build_release_workflow_summary(vec![
            loaded("readiness.json", "readiness", "ready"),
            loaded("staged.json", "staged_rollout", "ready"),
        ]);

        assert_eq!(
            summary.summary_version,
            UDP_RELEASE_WORKFLOW_SUMMARY_VERSION
        );
        assert_eq!(
            summary.comparison_schema_version,
            UDP_ROLLOUT_OPERATOR_VERDICT_SCHEMA_VERSION
        );
        assert_eq!(summary.decision_scope, "release_workflow");
        assert_eq!(summary.verdict, "ready");
        assert_eq!(summary.gate_state_reason, "all_required_inputs_passed");
        assert_eq!(summary.gate_state_reason_family, "ready");
        assert_eq!(summary.required_input_count, 2);
        assert_eq!(summary.required_input_missing_count, 0);
        assert_eq!(summary.required_input_failed_count, 0);
        assert_eq!(summary.required_input_unready_count, 0);
        assert_eq!(summary.required_input_present_count, 2);
        assert_eq!(summary.required_input_passed_count, 2);
        assert!(summary.missing_required_inputs.is_empty());
        assert_eq!(summary.missing_required_input_count, 0);
        assert_eq!(summary.blocking_reason_key_count, 0);
        assert_eq!(summary.blocking_reason_family_count, 0);
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
            Some(2)
        );
        assert!(summary.degradation_hold_subjects.is_empty());
    }

    #[test]
    fn release_workflow_fails_closed_without_staged_matrix() {
        let summary =
            build_release_workflow_summary(vec![loaded("readiness.json", "readiness", "ready")]);

        assert_eq!(summary.verdict, "hold");
        assert_eq!(summary.required_input_missing_count, 1);
        assert_eq!(summary.required_input_failed_count, 1);
        assert!(
            summary
                .missing_required_inputs
                .iter()
                .any(|input| input == "staged_rollout")
        );
    }

    #[test]
    fn release_workflow_holds_when_matrix_reports_queue_pressure() {
        let mut staged = loaded("staged.json", "staged_rollout", "ready");
        let staged_summary = staged
            .summary
            .as_mut()
            .expect("staged summary should exist");
        staged_summary.verdict = "hold".to_owned();
        staged_summary.gate_state = "blocked".to_owned();
        staged_summary.gate_state_reason = "required_inputs_unready".to_owned();
        staged_summary.gate_state_reason_family = "gating".to_owned();
        staged_summary.required_input_failed_count = 1;
        staged_summary.required_input_unready_count = 1;
        staged_summary.required_input_passed_count = 0;
        staged_summary.all_required_inputs_passed = false;
        staged_summary.blocking_reason_count = 1;
        staged_summary.blocking_reason_key_count = 1;
        staged_summary.blocking_reason_family_count = 1;
        staged_summary.blocking_reason_key_counts =
            BTreeMap::from([("queue_pressure_surface_failed".to_owned(), 1)]);
        staged_summary.blocking_reason_family_counts = BTreeMap::from([("capacity".to_owned(), 1)]);
        staged_summary.queue_pressure_hold_count = 1;
        staged_summary.blocking_reasons =
            vec!["staged_rollout:queue_pressure_surface_failed".to_owned()];
        staged_summary.blocking_reason_keys = vec!["queue_pressure_surface_failed".to_owned()];
        staged_summary.blocking_reason_families = vec!["capacity".to_owned()];

        let summary = build_release_workflow_summary(vec![
            loaded("readiness.json", "readiness", "ready"),
            staged,
        ]);

        assert_eq!(summary.verdict, "hold");
        assert!(summary.queue_pressure_hold_count > 0);
        assert!(
            summary
                .blocking_reason_keys
                .iter()
                .any(|key| key == "queue_pressure_surface_failed")
        );
    }

    #[test]
    fn release_workflow_fails_closed_when_required_no_silent_fallback_profile_set_drifts() {
        let mut staged = loaded("staged.json", "staged_rollout", "ready");
        staged
            .summary
            .as_mut()
            .expect("staged summary should exist")
            .interop_required_no_silent_fallback_profile_slugs = vec!["loss-burst".to_owned()];

        let summary = build_release_workflow_summary(vec![
            loaded("readiness.json", "readiness", "ready"),
            staged,
        ]);

        assert_eq!(summary.verdict, "hold");
        assert!(!summary.interop_profile_contract_passed);
        assert!(
            summary
                .blocking_reason_keys
                .iter()
                .any(|key| key == "interop_required_no_silent_fallback_profile_set_mismatch")
        );
    }
}
