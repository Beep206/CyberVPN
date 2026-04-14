use ns_testkit::{
    UDP_ROLLOUT_DECISION_SCOPE_HOST, UDP_ROLLOUT_DECISION_SCOPE_MATRIX,
    UDP_ROLLOUT_OPERATOR_VERDICT_FAMILY, UDP_ROLLOUT_OPERATOR_VERDICT_SCHEMA,
    UDP_ROLLOUT_OPERATOR_VERDICT_SCHEMA_VERSION, repo_root, summarize_rollout_gate_state,
    udp_wan_lab_required_no_silent_fallback_profile_slugs,
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
struct MatrixArgs {
    format: Option<OutputFormat>,
    inputs: Vec<PathBuf>,
    summary_path: Option<PathBuf>,
}

const UDP_ROLLOUT_COMPARISON_SUMMARY_VERSION: u8 = 14;
const UDP_ROLLOUT_MATRIX_SUMMARY_VERSION: u8 = 11;

#[derive(Debug, Deserialize)]
struct ComparisonSummaryInput {
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
    gate_state: String,
    gate_state_reason: String,
    gate_state_reason_family: String,
    active_fuzz_required: bool,
    required_inputs: Vec<String>,
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
    interop_profile_contract_passed: Option<bool>,
    #[serde(default)]
    degradation_surface_passed: Option<bool>,
    #[serde(default)]
    degradation_hold_count: usize,
    #[serde(default)]
    degradation_hold_subjects: Vec<String>,
    #[serde(default)]
    surface_count_total: Option<usize>,
    #[serde(default)]
    surface_count_passed: Option<usize>,
    #[serde(default)]
    surface_count_failed: Option<usize>,
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
struct LoadedMatrixInput {
    input_label: String,
    path: String,
    present: bool,
    parse_error: Option<String>,
    summary: Option<ComparisonSummaryInput>,
}

#[derive(Debug, Serialize)]
struct HostMatrixResult {
    input_label: String,
    host_label: String,
    summary_path: String,
    present: bool,
    summary_version: Option<u8>,
    comparison_schema_version: Option<u8>,
    profile: Option<String>,
    decision_label: Option<String>,
    verdict: &'static str,
    evidence_state: &'static str,
    gate_state: &'static str,
    gate_state_reason: &'static str,
    gate_state_reason_family: &'static str,
    passed: bool,
    required_input_count: usize,
    required_input_missing_count: usize,
    required_input_failed_count: usize,
    required_input_unready_count: usize,
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
    queue_guard_headroom_band: Option<String>,
    queue_guard_headroom_missing_count: usize,
    queue_guard_limiting_path: Option<String>,
    queue_guard_tight_hold_count: usize,
    queue_pressure_hold_count: usize,
    interop_required_no_silent_fallback_profile_slugs: Vec<String>,
    interop_profile_contract_passed: Option<bool>,
    degradation_surface_passed: Option<bool>,
    surface_count_total: Option<usize>,
    surface_count_passed: Option<usize>,
    surface_count_failed: Option<usize>,
    blocking_reasons: Vec<String>,
    advisory_reasons: Vec<String>,
}

#[derive(Debug, Serialize)]
struct UdpRolloutMatrixSummary {
    summary_version: u8,
    comparison_schema: &'static str,
    comparison_schema_version: u8,
    verdict_family: &'static str,
    decision_scope: &'static str,
    decision_label: String,
    profile: String,
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
    host_count: usize,
    host_passed_count: usize,
    host_failed_count: usize,
    host_labels: Vec<String>,
    hosts_with_degradation_hold: Vec<String>,
    degradation_hold_count: usize,
    degradation_hold_subjects: Vec<String>,
    queue_guard_headroom_band_counts: BTreeMap<String, usize>,
    queue_guard_headroom_missing_count: usize,
    queue_guard_limiting_path_counts: BTreeMap<String, usize>,
    queue_guard_tight_hold_count: usize,
    queue_pressure_hold_count: usize,
    interop_required_no_silent_fallback_profile_slugs: Vec<String>,
    interop_profile_contract_passed: bool,
    limiting_paths_observed: Vec<String>,
    affected_host_count_by_reason_family: BTreeMap<String, usize>,
    blocking_reasons: Vec<String>,
    blocking_reason_keys: Vec<String>,
    blocking_reason_families: Vec<String>,
    advisory_reasons: Vec<String>,
    hosts: Vec<HostMatrixResult>,
}

fn main() -> Result<(), Box<dyn std::error::Error>> {
    let args = parse_args(env::args().skip(1))?;
    let loaded_inputs = args
        .inputs
        .iter()
        .map(|path| load_input(path))
        .collect::<Vec<_>>();
    let summary = build_matrix_summary(loaded_inputs);

    let summary_path = args.summary_path.unwrap_or_else(default_summary_path);
    if let Some(parent) = summary_path.parent() {
        fs::create_dir_all(parent)?;
    }
    fs::write(&summary_path, serde_json::to_vec_pretty(&summary)?)?;

    match args.format.unwrap_or(OutputFormat::Text) {
        OutputFormat::Text => {
            println!("Northstar UDP rollout matrix summary:");
            println!("- profile: {}", summary.profile);
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
            println!("- active_fuzz_required: {}", summary.active_fuzz_required);
            println!(
                "- host_counts: total={} passed={} failed={}",
                summary.host_count, summary.host_passed_count, summary.host_failed_count
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
            if summary.hosts_with_degradation_hold.is_empty() {
                println!("- hosts_with_degradation_hold: none");
            } else {
                println!(
                    "- hosts_with_degradation_hold: {}",
                    summary.hosts_with_degradation_hold.join(", ")
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
            println!(
                "- queue_guard_headroom_missing_count: {}",
                summary.queue_guard_headroom_missing_count
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
            println!(
                "- interop_profile_contract_passed: {}",
                summary.interop_profile_contract_passed
            );
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
            if summary.affected_host_count_by_reason_family.is_empty() {
                println!("- affected_host_count_by_reason_family: none");
            } else {
                println!(
                    "- affected_host_count_by_reason_family: {}",
                    render_counts(&summary.affected_host_count_by_reason_family)
                );
            }
            if summary.limiting_paths_observed.is_empty() {
                println!("- limiting_paths_observed: none");
            } else {
                println!(
                    "- limiting_paths_observed: {}",
                    summary.limiting_paths_observed.join(", ")
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
            if summary.blocking_reason_key_counts.is_empty() {
                println!("- blocking_reason_key_counts: none");
            } else {
                println!(
                    "- blocking_reason_key_counts: {}",
                    render_counts(&summary.blocking_reason_key_counts)
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
            if summary.blocking_reason_family_counts.is_empty() {
                println!("- blocking_reason_family_counts: none");
            } else {
                println!(
                    "- blocking_reason_family_counts: {}",
                    render_counts(&summary.blocking_reason_family_counts)
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
            println!("machine_readable_summary={}", summary_path.display());
        }
        OutputFormat::Json => {
            println!("{}", serde_json::to_string_pretty(&summary)?);
        }
    }

    if summary.verdict != "ready" {
        return Err("udp rollout matrix is not ready".into());
    }

    Ok(())
}

fn build_matrix_summary(inputs: Vec<LoadedMatrixInput>) -> UdpRolloutMatrixSummary {
    let expected_required_no_silent_fallback_profile_set =
        udp_wan_lab_required_no_silent_fallback_profile_slugs()
            .into_iter()
            .map(str::to_owned)
            .collect::<BTreeSet<_>>();
    let profile = inputs
        .iter()
        .filter_map(|input| {
            input
                .summary
                .as_ref()
                .map(|summary| summary.profile.clone())
        })
        .next()
        .unwrap_or_else(|| "readiness".to_owned());
    let active_fuzz_required = profile == "staged_rollout";
    let decision_label = format!("{profile}_matrix");

    let mut host_labels = Vec::new();
    let mut hosts = Vec::with_capacity(inputs.len());
    let mut missing_required_inputs = Vec::new();
    let mut blocking_reasons = Vec::new();
    let mut advisory_reasons = Vec::new();
    let mut blocking_reason_key_counts = BTreeMap::new();
    let mut blocking_reason_family_counts = BTreeMap::new();
    let mut queue_guard_headroom_band_counts = BTreeMap::new();
    let mut queue_guard_headroom_missing_count = 0usize;
    let mut queue_guard_limiting_path_counts = BTreeMap::new();
    let mut queue_guard_tight_hold_count = 0usize;
    let mut queue_pressure_hold_count = 0usize;
    let mut interop_required_no_silent_fallback_profile_set = BTreeSet::new();
    let mut affected_host_count_by_reason_family = BTreeMap::new();
    let mut hosts_with_degradation_hold = Vec::new();
    let mut all_consumed_host_inputs_contract_valid = true;

    for input in inputs {
        if !input.present {
            missing_required_inputs.push(input.input_label.clone());
        }

        let mut local_reason_details = Vec::new();
        let mut local_advisory_reasons = Vec::new();
        let host_result = if !input.present {
            let host_label = input.input_label.clone();
            push_reason(
                &mut blocking_reasons,
                &mut local_reason_details,
                "summary_presence_missing",
                format!("missing_input_summary_{}", sanitize_label(&host_label)),
                "summary_presence",
            );
            HostMatrixResult {
                input_label: input.input_label.clone(),
                host_label,
                summary_path: input.path,
                present: false,
                summary_version: None,
                comparison_schema_version: None,
                profile: None,
                decision_label: None,
                verdict: "hold",
                evidence_state: "incomplete",
                gate_state: "blocked",
                gate_state_reason: "missing_required_inputs",
                gate_state_reason_family: "summary_presence",
                passed: false,
                required_input_count: 0,
                required_input_missing_count: 0,
                required_input_failed_count: 0,
                required_input_unready_count: 0,
                required_input_present_count: 0,
                required_input_passed_count: 0,
                all_required_inputs_present: false,
                all_required_inputs_passed: false,
                missing_required_inputs: Vec::new(),
                blocking_reason_count: local_reason_details.len(),
                blocking_reason_key_count: counts_from_reason_details(&local_reason_details, true)
                    .len(),
                blocking_reason_family_count: counts_from_reason_details(
                    &local_reason_details,
                    false,
                )
                .len(),
                advisory_reason_count: 0,
                blocking_reason_key_counts: counts_from_reason_details(&local_reason_details, true),
                blocking_reason_family_counts: counts_from_reason_details(
                    &local_reason_details,
                    false,
                ),
                queue_guard_headroom_band: None,
                queue_guard_headroom_missing_count: 0,
                queue_guard_limiting_path: None,
                queue_guard_tight_hold_count: 0,
                queue_pressure_hold_count: 0,
                interop_required_no_silent_fallback_profile_slugs: Vec::new(),
                interop_profile_contract_passed: None,
                degradation_surface_passed: None,
                surface_count_total: None,
                surface_count_passed: None,
                surface_count_failed: None,
                blocking_reasons: codes_from_reason_details(&local_reason_details),
                advisory_reasons: Vec::new(),
            }
        } else if let Some(parse_error) = &input.parse_error {
            let host_label = input.input_label.clone();
            all_consumed_host_inputs_contract_valid = false;
            push_reason(
                &mut blocking_reasons,
                &mut local_reason_details,
                "summary_parse_failed",
                format!("invalid_input_summary_{}", sanitize_label(&host_label)),
                "summary_parse",
            );
            local_advisory_reasons.push(format!(
                "{}:parse_error={}",
                host_label,
                parse_error.replace(char::is_whitespace, " ")
            ));
            HostMatrixResult {
                input_label: input.input_label.clone(),
                host_label,
                summary_path: input.path,
                present: true,
                summary_version: None,
                comparison_schema_version: None,
                profile: None,
                decision_label: None,
                verdict: "hold",
                evidence_state: "incomplete",
                gate_state: "blocked",
                gate_state_reason: "blocking_reasons_present",
                gate_state_reason_family: "gating",
                passed: false,
                required_input_count: 0,
                required_input_missing_count: 0,
                required_input_failed_count: 0,
                required_input_unready_count: 0,
                required_input_present_count: 0,
                required_input_passed_count: 0,
                all_required_inputs_present: false,
                all_required_inputs_passed: false,
                missing_required_inputs: Vec::new(),
                blocking_reason_count: local_reason_details.len(),
                blocking_reason_key_count: counts_from_reason_details(&local_reason_details, true)
                    .len(),
                blocking_reason_family_count: counts_from_reason_details(
                    &local_reason_details,
                    false,
                )
                .len(),
                advisory_reason_count: local_advisory_reasons.len(),
                blocking_reason_key_counts: counts_from_reason_details(&local_reason_details, true),
                blocking_reason_family_counts: counts_from_reason_details(
                    &local_reason_details,
                    false,
                ),
                queue_guard_headroom_band: None,
                queue_guard_headroom_missing_count: 0,
                queue_guard_limiting_path: None,
                queue_guard_tight_hold_count: 0,
                queue_pressure_hold_count: 0,
                interop_required_no_silent_fallback_profile_slugs: Vec::new(),
                interop_profile_contract_passed: None,
                degradation_surface_passed: None,
                surface_count_total: None,
                surface_count_passed: None,
                surface_count_failed: None,
                blocking_reasons: codes_from_reason_details(&local_reason_details),
                advisory_reasons: local_advisory_reasons,
            }
        } else {
            let summary = input
                .summary
                .as_ref()
                .expect("present matrix input should have either parse_error or summary");
            let host_label = summary.host_label.clone();
            host_labels.push(host_label.clone());
            let mut summary_contract_valid = true;

            if summary.summary_version != Some(UDP_ROLLOUT_COMPARISON_SUMMARY_VERSION) {
                summary_contract_valid = false;
                push_reason(
                    &mut blocking_reasons,
                    &mut local_reason_details,
                    "summary_version_unsupported",
                    format!(
                        "{}_summary_version_unsupported",
                        sanitize_label(&host_label)
                    ),
                    "summary_version",
                );
            }
            if summary.comparison_schema != UDP_ROLLOUT_OPERATOR_VERDICT_SCHEMA {
                summary_contract_valid = false;
                push_reason(
                    &mut blocking_reasons,
                    &mut local_reason_details,
                    "comparison_schema_unsupported",
                    format!(
                        "{}_comparison_schema_unsupported",
                        sanitize_label(&host_label)
                    ),
                    "schema",
                );
            }
            if summary.comparison_schema_version != UDP_ROLLOUT_OPERATOR_VERDICT_SCHEMA_VERSION {
                summary_contract_valid = false;
                push_reason(
                    &mut blocking_reasons,
                    &mut local_reason_details,
                    "comparison_schema_version_unsupported",
                    format!(
                        "{}_comparison_schema_version_unsupported",
                        sanitize_label(&host_label)
                    ),
                    "schema",
                );
            }
            if summary.verdict_family != UDP_ROLLOUT_OPERATOR_VERDICT_FAMILY {
                summary_contract_valid = false;
                push_reason(
                    &mut blocking_reasons,
                    &mut local_reason_details,
                    "verdict_family_unsupported",
                    format!("{}_verdict_family_unsupported", sanitize_label(&host_label)),
                    "schema",
                );
            }
            if summary.decision_scope != UDP_ROLLOUT_DECISION_SCOPE_HOST {
                summary_contract_valid = false;
                push_reason(
                    &mut blocking_reasons,
                    &mut local_reason_details,
                    "decision_scope_mismatch",
                    format!("{}_decision_scope_mismatch", sanitize_label(&host_label)),
                    "shape",
                );
            }
            if summary.profile != profile {
                summary_contract_valid = false;
                push_reason(
                    &mut blocking_reasons,
                    &mut local_reason_details,
                    "profile_mismatch",
                    format!("{}_profile_mismatch", sanitize_label(&host_label)),
                    "shape",
                );
            }
            if !input_presence_consistent(summary) {
                summary_contract_valid = false;
                push_reason(
                    &mut blocking_reasons,
                    &mut local_reason_details,
                    "required_input_presence_inconsistent",
                    format!(
                        "{}_required_input_presence_inconsistent",
                        sanitize_label(&host_label)
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
                    &mut local_reason_details,
                    "gate_state_reason_inconsistent",
                    format!(
                        "{}_gate_state_reason_inconsistent",
                        sanitize_label(&profile)
                    ),
                    "shape",
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
                    &mut local_reason_details,
                    "blocking_reason_accounting_inconsistent",
                    format!(
                        "{}_blocking_reason_accounting_inconsistent",
                        sanitize_label(&host_label)
                    ),
                    "shape",
                );
            }
            if summary.missing_required_input_count != summary.missing_required_inputs.len() {
                summary_contract_valid = false;
                push_reason(
                    &mut blocking_reasons,
                    &mut local_reason_details,
                    "missing_required_input_count_inconsistent",
                    format!(
                        "{}_missing_required_input_count_inconsistent",
                        sanitize_label(&host_label)
                    ),
                    "required_inputs",
                );
            }
            if summary.required_input_missing_count != summary.missing_required_inputs.len() {
                summary_contract_valid = false;
                push_reason(
                    &mut blocking_reasons,
                    &mut local_reason_details,
                    "required_input_missing_count_inconsistent",
                    format!(
                        "{}_required_input_missing_count_inconsistent",
                        sanitize_label(&host_label)
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
                    &mut local_reason_details,
                    "required_input_failed_count_inconsistent",
                    format!(
                        "{}_required_input_failed_count_inconsistent",
                        sanitize_label(&host_label)
                    ),
                    "required_inputs",
                );
            }
            let host_required_no_silent_fallback_profile_set = summary
                .interop_required_no_silent_fallback_profile_slugs
                .iter()
                .cloned()
                .collect::<BTreeSet<_>>();
            if host_required_no_silent_fallback_profile_set
                != expected_required_no_silent_fallback_profile_set
            {
                summary_contract_valid = false;
                push_reason(
                    &mut blocking_reasons,
                    &mut local_reason_details,
                    "interop_required_no_silent_fallback_profile_set_mismatch",
                    format!(
                        "{}_interop_required_no_silent_fallback_profile_set_mismatch",
                        sanitize_label(&host_label)
                    ),
                    "summary_contract",
                );
            }
            if summary.blocking_reason_key_count != summary.blocking_reason_key_counts.len() {
                summary_contract_valid = false;
                push_reason(
                    &mut blocking_reasons,
                    &mut local_reason_details,
                    "blocking_reason_key_count_inconsistent",
                    format!(
                        "{}_blocking_reason_key_count_inconsistent",
                        sanitize_label(&host_label)
                    ),
                    "shape",
                );
            }
            if summary.blocking_reason_family_count != summary.blocking_reason_family_counts.len() {
                summary_contract_valid = false;
                push_reason(
                    &mut blocking_reasons,
                    &mut local_reason_details,
                    "blocking_reason_family_count_inconsistent",
                    format!(
                        "{}_blocking_reason_family_count_inconsistent",
                        sanitize_label(&host_label)
                    ),
                    "shape",
                );
            }
            if summary.degradation_hold_count != summary.degradation_hold_subjects.len() {
                summary_contract_valid = false;
                push_reason(
                    &mut blocking_reasons,
                    &mut local_reason_details,
                    "degradation_hold_count_inconsistent",
                    format!(
                        "{}_degradation_hold_count_inconsistent",
                        sanitize_label(&host_label)
                    ),
                    "degradation",
                );
            }
            if summary.verdict == "ready"
                && (summary.blocking_reason_count != 0
                    || !summary.missing_required_inputs.is_empty()
                    || summary.degradation_hold_count != 0)
            {
                summary_contract_valid = false;
                push_reason(
                    &mut blocking_reasons,
                    &mut local_reason_details,
                    "ready_verdict_blocking_semantics_inconsistent",
                    format!(
                        "{}_ready_verdict_blocking_semantics_inconsistent",
                        sanitize_label(&host_label)
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
                    &mut local_reason_details,
                    "missing_required_inputs_family_inconsistent",
                    format!(
                        "{}_missing_required_inputs_family_inconsistent",
                        sanitize_label(&host_label)
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
                    &mut local_reason_details,
                    "degradation_hold_family_inconsistent",
                    format!(
                        "{}_degradation_hold_family_inconsistent",
                        sanitize_label(&host_label)
                    ),
                    "degradation",
                );
            }
            if summary_contract_valid && active_fuzz_required && !summary.active_fuzz_required {
                push_reason(
                    &mut blocking_reasons,
                    &mut local_reason_details,
                    "staged_rollout_active_fuzz_requirement_missing",
                    format!(
                        "{}_staged_rollout_active_fuzz_requirement_missing",
                        sanitize_label(&host_label)
                    ),
                    "required_inputs",
                );
            }
            if summary_contract_valid
                && active_fuzz_required
                && !summary
                    .required_inputs
                    .iter()
                    .any(|input| input == "active_fuzz")
            {
                push_reason(
                    &mut blocking_reasons,
                    &mut local_reason_details,
                    "staged_rollout_active_fuzz_input_missing",
                    format!(
                        "{}_staged_rollout_active_fuzz_input_missing",
                        sanitize_label(&host_label)
                    ),
                    "required_inputs",
                );
            }
            if summary_contract_valid && summary.degradation_surface_passed != Some(true) {
                hosts_with_degradation_hold.push(host_label.clone());
                push_reason(
                    &mut blocking_reasons,
                    &mut local_reason_details,
                    "degradation_surface_failed",
                    format!("{}_degradation_surface_failed", sanitize_label(&host_label)),
                    "degradation",
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
                    &mut local_reason_details,
                    "host_verdict_not_ready",
                    format!("{}_host_verdict_not_ready", sanitize_label(&host_label)),
                    "gating",
                );
            }

            let mut host_reason_families = BTreeSet::new();
            if summary_contract_valid {
                if let Some(band) = &summary.queue_guard_headroom_band {
                    *queue_guard_headroom_band_counts
                        .entry(band.clone())
                        .or_insert(0) += 1;
                }
                queue_guard_headroom_missing_count += summary.queue_guard_headroom_missing_count;
                if let Some(path) = &summary.queue_guard_limiting_path {
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
                advisory_reasons.extend(
                    summary
                        .advisory_reasons
                        .iter()
                        .map(|reason| format!("{host_label}:{reason}")),
                );
                for family in summary.blocking_reason_family_counts.keys() {
                    host_reason_families.insert(family.clone());
                }
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
                        .map(|reason| format!("{host_label}:{reason}")),
                );
            } else {
                all_consumed_host_inputs_contract_valid = false;
            }
            for detail in &local_reason_details {
                host_reason_families.insert(detail.family.to_owned());
            }
            for family in host_reason_families {
                *affected_host_count_by_reason_family
                    .entry(family)
                    .or_insert(0) += 1;
            }

            merge_counts(
                &mut blocking_reason_key_counts,
                &counts_from_reason_details(&local_reason_details, true),
            );
            merge_counts(
                &mut blocking_reason_family_counts,
                &counts_from_reason_details(&local_reason_details, false),
            );

            blocking_reasons.extend(
                local_reason_details
                    .iter()
                    .map(|detail| detail.code.clone()),
            );

            let passed = summary_contract_valid
                && local_reason_details.is_empty()
                && summary.verdict == "ready"
                && summary.gate_state == "passed"
                && summary.all_required_inputs_present
                && summary.all_required_inputs_passed;
            let required_input_unready_count = summary
                .required_input_failed_count
                .saturating_sub(summary.required_input_missing_count);
            let summary_contract_invalid_count = if summary_contract_valid {
                summary
                    .blocking_reason_family_counts
                    .get("summary_contract")
                    .copied()
                    .unwrap_or(0)
            } else {
                local_reason_details
                    .iter()
                    .filter(|detail| detail.family == "shape")
                    .count()
            };
            let (gate_state_reason, gate_state_reason_family) = summarize_rollout_gate_state(
                summary.required_input_missing_count,
                summary_contract_invalid_count,
                required_input_unready_count,
                summary.degradation_hold_count,
                if summary_contract_valid {
                    summary.blocking_reason_count + local_reason_details.len()
                } else {
                    local_reason_details.len()
                },
            );

            HostMatrixResult {
                input_label: input.input_label.clone(),
                host_label,
                summary_path: input.path,
                present: true,
                summary_version: summary.summary_version,
                comparison_schema_version: Some(summary.comparison_schema_version),
                profile: Some(summary.profile.clone()),
                decision_label: Some(summary.decision_label.clone()),
                verdict: if passed { "ready" } else { "hold" },
                evidence_state: if summary.all_required_inputs_present {
                    "complete"
                } else {
                    "incomplete"
                },
                gate_state: if passed { "passed" } else { "blocked" },
                gate_state_reason,
                gate_state_reason_family,
                passed,
                required_input_count: summary.required_input_count,
                required_input_missing_count: summary.required_input_missing_count,
                required_input_failed_count: summary.required_input_failed_count,
                required_input_unready_count,
                required_input_present_count: summary.required_input_present_count,
                required_input_passed_count: summary.required_input_passed_count,
                all_required_inputs_present: summary.all_required_inputs_present,
                all_required_inputs_passed: summary.all_required_inputs_passed,
                missing_required_inputs: summary.missing_required_inputs.clone(),
                blocking_reason_count: if summary_contract_valid {
                    summary.blocking_reason_count + local_reason_details.len()
                } else {
                    local_reason_details.len()
                },
                blocking_reason_key_count: if summary_contract_valid {
                    summary.blocking_reason_key_count
                } else {
                    counts_from_reason_details(&local_reason_details, true).len()
                },
                blocking_reason_family_count: if summary_contract_valid {
                    summary.blocking_reason_family_count
                } else {
                    counts_from_reason_details(&local_reason_details, false).len()
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
                        &counts_from_reason_details(&local_reason_details, true),
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
                        &counts_from_reason_details(&local_reason_details, false),
                    );
                    counts
                },
                queue_guard_headroom_band: if summary_contract_valid {
                    summary.queue_guard_headroom_band.clone()
                } else {
                    None
                },
                queue_guard_headroom_missing_count: if summary_contract_valid {
                    summary.queue_guard_headroom_missing_count
                } else {
                    0
                },
                queue_guard_limiting_path: if summary_contract_valid {
                    summary.queue_guard_limiting_path.clone()
                } else {
                    None
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
                    None
                },
                degradation_surface_passed: if summary_contract_valid {
                    summary.degradation_surface_passed
                } else {
                    None
                },
                surface_count_total: if summary_contract_valid {
                    summary.surface_count_total
                } else {
                    None
                },
                surface_count_passed: if summary_contract_valid {
                    summary.surface_count_passed
                } else {
                    None
                },
                surface_count_failed: if summary_contract_valid {
                    summary.surface_count_failed
                } else {
                    None
                },
                blocking_reasons: {
                    let mut reasons = if summary_contract_valid {
                        summary.blocking_reasons.clone()
                    } else {
                        Vec::new()
                    };
                    reasons.extend(codes_from_reason_details(&local_reason_details));
                    reasons
                },
                advisory_reasons: if summary_contract_valid {
                    summary.advisory_reasons.clone()
                } else {
                    Vec::new()
                },
            }
        };

        if host_result.present {
            advisory_reasons.extend(host_result.advisory_reasons.iter().cloned());
        }
        hosts.push(host_result);
    }

    let required_inputs = hosts
        .iter()
        .map(|host| host.input_label.clone())
        .collect::<Vec<_>>();
    let considered_inputs = required_inputs.clone();
    let required_input_count = required_inputs.len();
    let missing_required_input_count = missing_required_inputs.len();
    let required_input_missing_count = missing_required_input_count;
    let required_input_present_count = hosts.iter().filter(|host| host.present).count();
    let required_input_passed_count = hosts.iter().filter(|host| host.passed).count();
    let required_input_failed_count =
        required_input_count.saturating_sub(required_input_passed_count);
    let required_input_unready_count =
        required_input_failed_count.saturating_sub(required_input_missing_count);
    let all_required_inputs_present = required_input_present_count == required_input_count;
    let all_required_inputs_passed =
        all_required_inputs_present && required_input_passed_count == required_input_count;
    let host_count = hosts.len();
    let host_passed_count = hosts.iter().filter(|host| host.passed).count();
    let host_failed_count = host_count.saturating_sub(host_passed_count);
    let interop_profile_contract_passed = hosts
        .iter()
        .all(|host| host.interop_profile_contract_passed == Some(true));
    if !interop_required_no_silent_fallback_profile_set.is_empty()
        && interop_required_no_silent_fallback_profile_set
            != expected_required_no_silent_fallback_profile_set
    {
        blocking_reasons
            .push("matrix_interop_required_no_silent_fallback_profile_set_mismatch".to_owned());
        *blocking_reason_key_counts
            .entry("interop_required_no_silent_fallback_profile_set_mismatch".to_owned())
            .or_insert(0) += 1;
        *blocking_reason_family_counts
            .entry("summary_contract".to_owned())
            .or_insert(0) += 1;
    }
    if queue_pressure_hold_count > 0 {
        blocking_reasons.push("matrix_queue_pressure_surface_failed".to_owned());
        *blocking_reason_key_counts
            .entry("queue_pressure_surface_failed".to_owned())
            .or_insert(0) += 1;
        *blocking_reason_family_counts
            .entry("capacity".to_owned())
            .or_insert(0) += 1;
    }
    let blocking_reason_count = blocking_reasons.len();
    let advisory_reason_count = advisory_reasons.len();
    let evidence_state = if all_required_inputs_present && all_consumed_host_inputs_contract_valid {
        "complete"
    } else {
        "incomplete"
    };
    let gate_state = if blocking_reason_count == 0 && all_required_inputs_passed {
        "passed"
    } else {
        "blocked"
    };
    let verdict = if all_required_inputs_passed && blocking_reason_count == 0 {
        "ready"
    } else {
        "hold"
    };

    let mut limiting_paths_observed = queue_guard_limiting_path_counts
        .keys()
        .cloned()
        .collect::<Vec<_>>();
    limiting_paths_observed.sort();
    host_labels.sort();
    host_labels.dedup();
    hosts_with_degradation_hold.sort();
    hosts_with_degradation_hold.dedup();
    let degradation_hold_count = hosts_with_degradation_hold.len();
    let degradation_hold_subjects = hosts_with_degradation_hold.clone();
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
            .iter()
            .cloned()
            .collect::<Vec<_>>();
    let blocking_reason_key_count = blocking_reason_key_counts.len();
    let blocking_reason_family_count = blocking_reason_family_counts.len();
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

    UdpRolloutMatrixSummary {
        summary_version: UDP_ROLLOUT_MATRIX_SUMMARY_VERSION,
        comparison_schema: UDP_ROLLOUT_OPERATOR_VERDICT_SCHEMA,
        comparison_schema_version: UDP_ROLLOUT_OPERATOR_VERDICT_SCHEMA_VERSION,
        verdict_family: UDP_ROLLOUT_OPERATOR_VERDICT_FAMILY,
        decision_scope: UDP_ROLLOUT_DECISION_SCOPE_MATRIX,
        decision_label,
        profile,
        verdict,
        evidence_state,
        gate_state,
        gate_state_reason,
        gate_state_reason_family,
        active_fuzz_required,
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
        host_count,
        host_passed_count,
        host_failed_count,
        host_labels,
        hosts_with_degradation_hold,
        degradation_hold_count,
        degradation_hold_subjects,
        queue_guard_headroom_band_counts,
        queue_guard_headroom_missing_count,
        queue_guard_limiting_path_counts,
        queue_guard_tight_hold_count,
        queue_pressure_hold_count,
        interop_required_no_silent_fallback_profile_slugs,
        interop_profile_contract_passed,
        limiting_paths_observed,
        affected_host_count_by_reason_family,
        blocking_reasons,
        blocking_reason_keys,
        blocking_reason_families,
        advisory_reasons,
        hosts,
    }
}

fn load_input(path: &Path) -> LoadedMatrixInput {
    let input_label = path
        .file_stem()
        .map(|value| value.to_string_lossy().into_owned())
        .unwrap_or_else(|| "matrix-input".to_owned());
    let display_path = path.display().to_string();
    if !path.exists() {
        return LoadedMatrixInput {
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
            serde_json::from_slice::<ComparisonSummaryInput>(&bytes)
                .map_err(|error| error.to_string())
        }) {
        Ok(summary) => LoadedMatrixInput {
            input_label,
            path: display_path,
            present: true,
            parse_error: None,
            summary: Some(summary),
        },
        Err(error) => LoadedMatrixInput {
            input_label,
            path: display_path,
            present: true,
            parse_error: Some(error),
            summary: None,
        },
    }
}

fn input_presence_consistent(summary: &ComparisonSummaryInput) -> bool {
    summary.required_input_present_count <= summary.required_input_count
        && summary.required_input_passed_count <= summary.required_input_present_count
        && summary.required_input_missing_count == summary.missing_required_inputs.len()
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
        && summary.missing_required_inputs.len() == summary.required_input_missing_count
        && summary.gate_state
            == if summary.verdict == "ready" {
                "passed"
            } else {
                "blocked"
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

fn merge_counts(destination: &mut BTreeMap<String, usize>, source: &BTreeMap<String, usize>) {
    for (key, count) in source {
        *destination.entry(key.clone()).or_insert(0) += count;
    }
}

fn render_counts(counts: &BTreeMap<String, usize>) -> String {
    counts
        .iter()
        .map(|(key, count)| format!("{key}={count}"))
        .collect::<Vec<_>>()
        .join(", ")
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
) -> Result<MatrixArgs, Box<dyn std::error::Error>> {
    let mut parsed = MatrixArgs::default();
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
        "Usage: cargo run -p ns-testkit --example udp_rollout_matrix -- [--format text|json] [--summary-path <path>] --input <comparison-summary-path> [--input <comparison-summary-path> ...]"
    );
}

fn default_summary_path() -> PathBuf {
    repo_root()
        .join("target")
        .join("northstar")
        .join("udp-rollout-matrix-summary.json")
}

#[cfg(test)]
mod tests {
    use super::{
        ComparisonSummaryInput, LoadedMatrixInput, UDP_ROLLOUT_COMPARISON_SUMMARY_VERSION,
        UDP_ROLLOUT_OPERATOR_VERDICT_SCHEMA_VERSION, build_matrix_summary,
    };
    use ns_testkit::udp_wan_lab_required_no_silent_fallback_profile_slugs;

    fn loaded(path: &str, summary: ComparisonSummaryInput) -> LoadedMatrixInput {
        LoadedMatrixInput {
            input_label: summary.host_label.clone(),
            path: path.to_owned(),
            present: true,
            parse_error: None,
            summary: Some(summary),
        }
    }

    fn ready_summary(host_label: &str, profile: &str) -> ComparisonSummaryInput {
        ComparisonSummaryInput {
            summary_version: Some(UDP_ROLLOUT_COMPARISON_SUMMARY_VERSION),
            comparison_schema: "udp_rollout_operator_verdict".to_owned(),
            comparison_schema_version: UDP_ROLLOUT_OPERATOR_VERDICT_SCHEMA_VERSION,
            verdict_family: "udp_rollout_operator_decision".to_owned(),
            decision_scope: "host".to_owned(),
            decision_label: host_label.to_owned(),
            profile: profile.to_owned(),
            host_label: host_label.to_owned(),
            verdict: "ready".to_owned(),
            gate_state: "passed".to_owned(),
            gate_state_reason: "all_required_inputs_passed".to_owned(),
            gate_state_reason_family: "ready".to_owned(),
            active_fuzz_required: profile == "staged_rollout",
            required_inputs: if profile == "staged_rollout" {
                vec![
                    "smoke".to_owned(),
                    "perf".to_owned(),
                    "interop".to_owned(),
                    "rollout_validation".to_owned(),
                    "active_fuzz".to_owned(),
                ]
            } else {
                vec![
                    "smoke".to_owned(),
                    "perf".to_owned(),
                    "interop".to_owned(),
                    "rollout_validation".to_owned(),
                ]
            },
            missing_required_inputs: Vec::new(),
            missing_required_input_count: 0,
            required_input_count: if profile == "staged_rollout" { 5 } else { 4 },
            required_input_missing_count: 0,
            required_input_failed_count: 0,
            required_input_unready_count: 0,
            required_input_present_count: if profile == "staged_rollout" { 5 } else { 4 },
            required_input_passed_count: if profile == "staged_rollout" { 5 } else { 4 },
            all_required_inputs_present: true,
            all_required_inputs_passed: true,
            blocking_reason_count: 0,
            blocking_reason_key_count: 0,
            blocking_reason_family_count: 0,
            blocking_reason_key_counts: Default::default(),
            blocking_reason_family_counts: Default::default(),
            advisory_reason_count: 0,
            queue_guard_headroom_band: Some("healthy".to_owned()),
            queue_guard_headroom_missing_count: 0,
            queue_guard_limiting_path: Some("recovery".to_owned()),
            queue_guard_tight_hold_count: 0,
            queue_pressure_hold_count: 0,
            interop_required_no_silent_fallback_profile_slugs:
                udp_wan_lab_required_no_silent_fallback_profile_slugs()
                    .into_iter()
                    .map(str::to_owned)
                    .collect(),
            degradation_surface_passed: Some(true),
            degradation_hold_count: 0,
            degradation_hold_subjects: Vec::new(),
            surface_count_total: Some(15),
            surface_count_passed: Some(15),
            surface_count_failed: Some(0),
            blocking_reasons: Vec::new(),
            blocking_reason_keys: Vec::new(),
            blocking_reason_families: Vec::new(),
            advisory_reasons: Vec::new(),
            interop_profile_contract_passed: Some(true),
        }
    }

    #[test]
    fn readiness_matrix_emits_ready_operator_verdict_schema() {
        let summary = build_matrix_summary(vec![
            loaded(
                "linux.json",
                ready_summary("ubuntu-latest-rollout", "readiness"),
            ),
            loaded(
                "macos.json",
                ready_summary("macos-latest-rollout", "readiness"),
            ),
        ]);

        assert_eq!(summary.summary_version, 11);
        assert_eq!(summary.comparison_schema, "udp_rollout_operator_verdict");
        assert_eq!(
            summary.comparison_schema_version,
            UDP_ROLLOUT_OPERATOR_VERDICT_SCHEMA_VERSION
        );
        assert_eq!(summary.decision_scope, "matrix");
        assert_eq!(summary.profile, "readiness");
        assert_eq!(summary.verdict, "ready");
        assert_eq!(summary.gate_state, "passed");
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
        assert_eq!(summary.host_count, 2);
        assert_eq!(summary.host_passed_count, 2);
        assert!(summary.hosts_with_degradation_hold.is_empty());
        assert_eq!(summary.degradation_hold_count, 0);
        assert_eq!(summary.queue_guard_tight_hold_count, 0);
        assert_eq!(summary.queue_pressure_hold_count, 0);
        assert!(summary.degradation_hold_subjects.is_empty());
        assert_eq!(
            summary
                .interop_required_no_silent_fallback_profile_slugs
                .len(),
            udp_wan_lab_required_no_silent_fallback_profile_slugs().len()
        );
        assert_eq!(
            summary
                .queue_guard_limiting_path_counts
                .get("recovery")
                .copied(),
            Some(2)
        );
    }

    #[test]
    fn staged_matrix_fails_closed_without_active_fuzz_requirement() {
        let mut staged = ready_summary("ubuntu-latest-staged", "staged_rollout");
        staged.active_fuzz_required = false;

        let summary = build_matrix_summary(vec![loaded("linux-staged.json", staged)]);

        assert_eq!(summary.profile, "staged_rollout");
        assert_eq!(summary.verdict, "hold");
        assert_eq!(summary.gate_state, "blocked");
        assert!(
            summary
                .blocking_reasons
                .iter()
                .any(|reason| reason.contains("active_fuzz_requirement_missing"))
        );
        assert_eq!(
            summary
                .blocking_reason_key_counts
                .get("staged_rollout_active_fuzz_requirement_missing")
                .copied(),
            Some(1)
        );
    }

    #[test]
    fn matrix_holds_on_unsupported_host_summary_version() {
        let mut readiness = ready_summary("windows-latest-rollout", "readiness");
        readiness.summary_version = Some(10);

        let summary = build_matrix_summary(vec![loaded("windows.json", readiness)]);

        assert_eq!(summary.verdict, "hold");
        assert_eq!(summary.evidence_state, "incomplete");
        assert!(
            summary
                .blocking_reasons
                .iter()
                .any(|reason| reason.contains("summary_version_unsupported"))
        );
        assert_eq!(
            summary
                .blocking_reason_key_counts
                .get("summary_version_unsupported")
                .copied(),
            Some(1)
        );
    }
}
