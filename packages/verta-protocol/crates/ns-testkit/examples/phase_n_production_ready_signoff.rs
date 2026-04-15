use ns_testkit::{UDP_ROLLOUT_OPERATOR_VERDICT_FAMILY, repo_root, summarize_rollout_gate_state};
use serde::{Deserialize, Serialize};
use std::collections::BTreeMap;
use std::env;
use std::fs;
use std::path::{Path, PathBuf};

const RELEASE_SCOPE_CANONICAL: &str = "verta_v0_1";

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
enum OutputFormat {
    Text,
    Json,
}

#[derive(Debug, Default)]
struct PhaseNArgs {
    format: Option<OutputFormat>,
    summary_path: Option<PathBuf>,
    project_root: Option<PathBuf>,
    phase_i_summary: Option<PathBuf>,
    phase_j_summary: Option<PathBuf>,
    phase_l_summary: Option<PathBuf>,
    phase_m_summary: Option<PathBuf>,
    release_checklist: Option<PathBuf>,
    support_matrix: Option<PathBuf>,
    known_limitations: Option<PathBuf>,
    git_head: Option<String>,
    git_branch: Option<String>,
    git_clean: Option<bool>,
}

#[derive(Debug, Deserialize)]
struct PhaseISummaryInput {
    verdict: String,
    phase_i_state: String,
    supported_deployment_label: String,
    supported_upstream_version: String,
}

#[derive(Debug, Deserialize)]
struct PhaseJSummaryInput {
    verdict: String,
    phase_j_state: String,
    broader_wan_evidence_passed: bool,
    artifact_retention_passed: bool,
    transport_fallback_integrity_surface_passed: bool,
}

#[derive(Debug, Deserialize)]
struct PhaseLSummaryInput {
    verdict: String,
    phase_l_state: String,
    profile_disable_drill_passed: bool,
    rollback_drill_passed: bool,
    recovery_boundaries_documented: bool,
    observability_mapping_documented: bool,
}

#[derive(Debug, Deserialize)]
struct PhaseMSummaryInput {
    verdict: String,
    phase_m_state: String,
    agreed_environment_label: Option<String>,
    observed_duration_seconds: u64,
    rollback_proven: bool,
    p0_open_count: usize,
    p1_open_count: usize,
}

#[derive(Debug, Deserialize)]
struct ProductionReadyChecklist {
    summary_version: u8,
    phase: String,
    release_scope: String,
    release_label: String,
    required_items: Vec<ChecklistItem>,
}

#[derive(Debug, Deserialize)]
struct ChecklistItem {
    item_id: String,
    status: String,
    required: bool,
    evidence_refs: Vec<String>,
}

#[derive(Debug, Deserialize)]
struct SupportedEnvironmentMatrix {
    summary_version: u8,
    phase: String,
    release_scope: String,
    environments: Vec<SupportedEnvironment>,
}

#[derive(Debug, Deserialize)]
struct SupportedEnvironment {
    environment_id: String,
    deployment_label: String,
    environment_kind: String,
    support_status: String,
    upstream_support: Vec<String>,
    configuration_refs: Vec<String>,
    evidence_refs: Vec<String>,
}

#[derive(Debug, Deserialize)]
struct KnownLimitations {
    summary_version: u8,
    phase: String,
    release_scope: String,
    limitations: Vec<KnownLimitation>,
}

#[derive(Debug, Deserialize)]
struct KnownLimitation {
    limitation_id: String,
    category: String,
    summary: String,
    blocking: bool,
    accepted: bool,
    out_of_scope: bool,
    refs: Vec<String>,
}

#[derive(Debug, Serialize)]
struct PhaseNProductionReadySummary {
    summary_version: u8,
    verdict_family: &'static str,
    decision_scope: &'static str,
    decision_label: &'static str,
    profile: &'static str,
    verdict: &'static str,
    evidence_state: &'static str,
    gate_state: &'static str,
    gate_state_reason: &'static str,
    gate_state_reason_family: &'static str,
    phase_n_state: &'static str,
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
    phase_i_present: bool,
    phase_i_passed: bool,
    phase_j_present: bool,
    phase_j_passed: bool,
    phase_l_present: bool,
    phase_l_passed: bool,
    phase_m_present: bool,
    phase_m_passed: bool,
    release_checklist_present: bool,
    release_checklist_passed: bool,
    support_matrix_present: bool,
    support_matrix_passed: bool,
    known_limitations_present: bool,
    known_limitations_passed: bool,
    phase_chain_ready: bool,
    supported_environments_documented: bool,
    known_limitations_explicit: bool,
    release_artifacts_attributable: bool,
    git_head_present: bool,
    git_branch_present: bool,
    git_clean: bool,
    git_head: Option<String>,
    git_branch: Option<String>,
    release_label: Option<String>,
    supported_upstream_version: Option<String>,
    verified_environment_count: usize,
    documented_environment_count: usize,
    verified_environment_labels: Vec<String>,
    supported_environment_kinds: Vec<String>,
    checklist_item_ids: Vec<String>,
    known_limitation_ids: Vec<String>,
    accepted_limitation_count: usize,
    blocking_limitation_count: usize,
    out_of_scope_limitation_count: usize,
    blocking_reasons: Vec<String>,
    blocking_reason_keys: Vec<String>,
    blocking_reason_families: Vec<String>,
}

#[derive(Debug, Default)]
struct EvaluationState {
    required_inputs: Vec<String>,
    missing_required_inputs: Vec<String>,
    present_required_inputs: Vec<String>,
    passed_required_inputs: Vec<String>,
    blocking_reasons: Vec<String>,
    blocking_reason_keys: Vec<String>,
    blocking_reason_families: Vec<String>,
    blocking_reason_key_counts: BTreeMap<String, usize>,
    blocking_reason_family_counts: BTreeMap<String, usize>,
    summary_contract_invalid_count: usize,
    required_input_unready_count: usize,
}

impl EvaluationState {
    fn require(&mut self, label: impl Into<String>) {
        self.required_inputs.push(label.into());
    }

    fn mark_present(&mut self, label: &str) {
        self.present_required_inputs.push(label.to_owned());
    }

    fn mark_passed(&mut self, label: &str) {
        self.passed_required_inputs.push(label.to_owned());
    }

    fn mark_missing(&mut self, label: &str) {
        self.missing_required_inputs.push(label.to_owned());
    }

    fn add_blocking(&mut self, code: impl Into<String>, family: &'static str) {
        let code = code.into();
        self.blocking_reason_key_counts
            .entry(code.clone())
            .and_modify(|count| *count += 1)
            .or_insert(1);
        self.blocking_reason_family_counts
            .entry(family.to_owned())
            .and_modify(|count| *count += 1)
            .or_insert(1);
        self.blocking_reason_keys.push(code.clone());
        self.blocking_reason_families.push(family.to_owned());
        self.blocking_reasons.push(code);
    }

    fn add_contract_invalid(&mut self, code: impl Into<String>) {
        self.summary_contract_invalid_count += 1;
        self.add_blocking(code, "summary_contract");
    }

    fn add_unready(&mut self, code: impl Into<String>) {
        self.required_input_unready_count += 1;
        self.add_blocking(code, "gating");
    }
}

fn main() -> Result<(), Box<dyn std::error::Error>> {
    let args = parse_args(env::args().skip(1))?;
    let summary = build_summary(&args)?;
    let summary_path = args
        .summary_path
        .clone()
        .unwrap_or_else(default_summary_path);
    if let Some(parent) = summary_path.parent() {
        fs::create_dir_all(parent)?;
    }
    fs::write(&summary_path, serde_json::to_vec_pretty(&summary)?)?;

    match args.format.unwrap_or(OutputFormat::Text) {
        OutputFormat::Text => print_text_summary(&summary, &summary_path),
        OutputFormat::Json => println!("{}", serde_json::to_string_pretty(&summary)?),
    }

    if summary.verdict != "ready" {
        return Err("phase n production-ready signoff is not ready".into());
    }

    Ok(())
}

fn release_scope_supported(value: &str) -> bool {
    value == RELEASE_SCOPE_CANONICAL
}

fn build_summary(
    args: &PhaseNArgs,
) -> Result<PhaseNProductionReadySummary, Box<dyn std::error::Error>> {
    let project_root = args
        .project_root
        .clone()
        .unwrap_or_else(default_project_root);
    let phase_i_summary_path = args
        .phase_i_summary
        .clone()
        .unwrap_or_else(default_phase_i_summary_path);
    let phase_j_summary_path = args
        .phase_j_summary
        .clone()
        .unwrap_or_else(default_phase_j_summary_path);
    let phase_l_summary_path = args
        .phase_l_summary
        .clone()
        .unwrap_or_else(default_phase_l_summary_path);
    let phase_m_summary_path = args
        .phase_m_summary
        .clone()
        .unwrap_or_else(default_phase_m_summary_path);
    let release_checklist_path = args
        .release_checklist
        .clone()
        .unwrap_or_else(default_release_checklist_path);
    let support_matrix_path = args
        .support_matrix
        .clone()
        .unwrap_or_else(default_support_matrix_path);
    let known_limitations_path = args
        .known_limitations
        .clone()
        .unwrap_or_else(default_known_limitations_path);

    let mut state = EvaluationState::default();
    for label in [
        "phase_i_summary",
        "phase_j_summary",
        "phase_l_summary",
        "phase_m_summary",
        "release_checklist",
        "support_matrix",
        "known_limitations",
        "git_head",
        "git_branch",
        "git_clean",
    ] {
        state.require(label);
    }

    let mut phase_i_present = false;
    let mut phase_i_passed = false;
    let mut supported_deployment_label = None;
    let mut supported_upstream_version = None;
    if phase_i_summary_path.is_file() {
        state.mark_present("phase_i_summary");
        phase_i_present = true;
        let summary = load_json::<PhaseISummaryInput>(&phase_i_summary_path)?;
        if summary.verdict == "ready"
            && summary.phase_i_state == "honestly_complete"
            && !summary.supported_deployment_label.is_empty()
            && !summary.supported_upstream_version.is_empty()
        {
            supported_deployment_label = Some(summary.supported_deployment_label);
            supported_upstream_version = Some(summary.supported_upstream_version);
            phase_i_passed = true;
            state.mark_passed("phase_i_summary");
        } else {
            state.add_unready("phase_i_summary_not_ready");
        }
    } else {
        state.mark_missing("phase_i_summary");
        state.add_blocking("phase_i_summary_missing", "summary_presence");
    }

    let mut phase_j_present = false;
    let mut phase_j_passed = false;
    if phase_j_summary_path.is_file() {
        state.mark_present("phase_j_summary");
        phase_j_present = true;
        let summary = load_json::<PhaseJSummaryInput>(&phase_j_summary_path)?;
        if summary.verdict == "ready"
            && summary.phase_j_state == "honestly_complete"
            && summary.broader_wan_evidence_passed
            && summary.artifact_retention_passed
            && summary.transport_fallback_integrity_surface_passed
        {
            phase_j_passed = true;
            state.mark_passed("phase_j_summary");
        } else {
            state.add_unready("phase_j_summary_not_ready");
        }
    } else {
        state.mark_missing("phase_j_summary");
        state.add_blocking("phase_j_summary_missing", "summary_presence");
    }

    let mut phase_l_present = false;
    let mut phase_l_passed = false;
    if phase_l_summary_path.is_file() {
        state.mark_present("phase_l_summary");
        phase_l_present = true;
        let summary = load_json::<PhaseLSummaryInput>(&phase_l_summary_path)?;
        if summary.verdict == "ready"
            && summary.phase_l_state == "honestly_complete"
            && summary.profile_disable_drill_passed
            && summary.rollback_drill_passed
            && summary.recovery_boundaries_documented
            && summary.observability_mapping_documented
        {
            phase_l_passed = true;
            state.mark_passed("phase_l_summary");
        } else {
            state.add_unready("phase_l_summary_not_ready");
        }
    } else {
        state.mark_missing("phase_l_summary");
        state.add_blocking("phase_l_summary_missing", "summary_presence");
    }

    let mut phase_m_present = false;
    let mut phase_m_passed = false;
    let mut phase_m_environment_label = None;
    if phase_m_summary_path.is_file() {
        state.mark_present("phase_m_summary");
        phase_m_present = true;
        let summary = load_json::<PhaseMSummaryInput>(&phase_m_summary_path)?;
        if summary.verdict == "ready"
            && summary.phase_m_state == "honestly_complete"
            && summary.observed_duration_seconds > 0
            && summary.rollback_proven
            && summary.p0_open_count == 0
            && summary.p1_open_count == 0
        {
            phase_m_environment_label = summary.agreed_environment_label;
            phase_m_passed = true;
            state.mark_passed("phase_m_summary");
        } else {
            state.add_unready("phase_m_summary_not_ready");
        }
    } else {
        state.mark_missing("phase_m_summary");
        state.add_blocking("phase_m_summary_missing", "summary_presence");
    }

    let expected_checklist_ids = vec![
        "phase_i_honest_closure".to_owned(),
        "phase_j_wan_and_chaos".to_owned(),
        "phase_k_sustained_verification".to_owned(),
        "phase_l_operator_readiness".to_owned(),
        "phase_m_soak_canary".to_owned(),
        "supported_environment_matrix".to_owned(),
        "known_limitations_documented".to_owned(),
        "artifact_attribution_documented".to_owned(),
        "local_env_files_ignored".to_owned(),
    ];
    let mut release_checklist_present = false;
    let mut release_checklist_passed = false;
    let mut release_label = None;
    let mut checklist_item_ids = Vec::new();
    if release_checklist_path.is_file() {
        state.mark_present("release_checklist");
        release_checklist_present = true;
        let checklist = load_json::<ProductionReadyChecklist>(&release_checklist_path)?;
        if checklist.summary_version != 1
            || checklist.phase != "phase_n_production_ready_closure"
            || !release_scope_supported(&checklist.release_scope)
            || checklist.release_label.is_empty()
        {
            state.add_contract_invalid("release_checklist_contract_invalid");
        } else {
            release_label = Some(checklist.release_label.clone());
            checklist_item_ids = checklist
                .required_items
                .iter()
                .map(|item| item.item_id.clone())
                .collect();
            if checklist_item_ids != expected_checklist_ids {
                state.add_contract_invalid("release_checklist_inventory_drift");
            } else {
                let mut all_items_passed = true;
                for item in &checklist.required_items {
                    if !item.required
                        || item.status != "done"
                        || item.evidence_refs.is_empty()
                        || item
                            .evidence_refs
                            .iter()
                            .any(|reference| !project_root.join(reference).exists())
                    {
                        all_items_passed = false;
                        break;
                    }
                }
                if all_items_passed {
                    release_checklist_passed = true;
                    state.mark_passed("release_checklist");
                } else {
                    state.add_unready("release_checklist_not_complete");
                }
            }
        }
    } else {
        state.mark_missing("release_checklist");
        state.add_blocking("release_checklist_missing", "summary_presence");
    }

    let expected_environment_ids = vec![
        "local_supported_staging".to_owned(),
        "operator_managed_staging".to_owned(),
        "operator_managed_production".to_owned(),
    ];
    let mut support_matrix_present = false;
    let mut support_matrix_passed = false;
    let mut verified_environment_count = 0usize;
    let mut documented_environment_count = 0usize;
    let mut verified_environment_labels = Vec::new();
    let mut supported_environment_kinds = Vec::new();
    if support_matrix_path.is_file() {
        state.mark_present("support_matrix");
        support_matrix_present = true;
        let matrix = load_json::<SupportedEnvironmentMatrix>(&support_matrix_path)?;
        if matrix.summary_version != 1
            || matrix.phase != "phase_n_production_ready_closure"
            || !release_scope_supported(&matrix.release_scope)
        {
            state.add_contract_invalid("support_matrix_contract_invalid");
        } else {
            let environment_ids = matrix
                .environments
                .iter()
                .map(|environment| environment.environment_id.clone())
                .collect::<Vec<_>>();
            supported_environment_kinds = matrix
                .environments
                .iter()
                .map(|environment| environment.environment_kind.clone())
                .collect::<Vec<_>>();
            if environment_ids != expected_environment_ids {
                state.add_contract_invalid("support_matrix_inventory_drift");
            } else {
                let mut all_envs_valid = true;
                for environment in &matrix.environments {
                    if environment.configuration_refs.is_empty()
                        || environment.evidence_refs.is_empty()
                        || environment.upstream_support.is_empty()
                        || environment
                            .configuration_refs
                            .iter()
                            .any(|reference| !project_root.join(reference).exists())
                        || environment
                            .evidence_refs
                            .iter()
                            .any(|reference| !project_root.join(reference).exists())
                    {
                        all_envs_valid = false;
                        break;
                    }

                    if environment.support_status == "verified" {
                        verified_environment_count += 1;
                        verified_environment_labels.push(environment.deployment_label.clone());
                    }
                    if environment.support_status == "verified"
                        || environment.support_status == "documented"
                    {
                        documented_environment_count += 1;
                    }
                }

                let local_env_matches_phase_i = matrix.environments[0].deployment_label
                    == supported_deployment_label.clone().unwrap_or_default();
                let local_env_matches_phase_m = matrix.environments[0].deployment_label
                    == phase_m_environment_label.clone().unwrap_or_default();
                let production_env_documented = matrix.environments[2].environment_kind
                    == "operator_managed_production"
                    && matrix.environments[2].support_status == "documented";

                if all_envs_valid
                    && verified_environment_count >= 1
                    && documented_environment_count == 3
                    && local_env_matches_phase_i
                    && local_env_matches_phase_m
                    && production_env_documented
                {
                    support_matrix_passed = true;
                    state.mark_passed("support_matrix");
                } else {
                    state.add_unready("support_matrix_not_ready");
                }
            }
        }
    } else {
        state.mark_missing("support_matrix");
        state.add_blocking("support_matrix_missing", "summary_presence");
    }

    let expected_limitation_ids = vec![
        "single_carrier_h3_only".to_owned(),
        "zero_rtt_disabled".to_owned(),
        "client_inbound_placeholder".to_owned(),
        "multi_host_release_evidence_ci_driven".to_owned(),
    ];
    let mut known_limitations_present = false;
    let mut known_limitations_passed = false;
    let mut known_limitation_ids = Vec::new();
    let mut accepted_limitation_count = 0usize;
    let mut blocking_limitation_count = 0usize;
    let mut out_of_scope_limitation_count = 0usize;
    if known_limitations_path.is_file() {
        state.mark_present("known_limitations");
        known_limitations_present = true;
        let limitations = load_json::<KnownLimitations>(&known_limitations_path)?;
        if limitations.summary_version != 1
            || limitations.phase != "phase_n_production_ready_closure"
            || !release_scope_supported(&limitations.release_scope)
        {
            state.add_contract_invalid("known_limitations_contract_invalid");
        } else {
            known_limitation_ids = limitations
                .limitations
                .iter()
                .map(|limitation| limitation.limitation_id.clone())
                .collect::<Vec<_>>();
            if known_limitation_ids != expected_limitation_ids {
                state.add_contract_invalid("known_limitations_inventory_drift");
            } else {
                let mut all_limitations_valid = true;
                for limitation in &limitations.limitations {
                    if limitation.category.is_empty()
                        || limitation.summary.is_empty()
                        || limitation.refs.is_empty()
                        || limitation
                            .refs
                            .iter()
                            .any(|reference| !project_root.join(reference).exists())
                    {
                        all_limitations_valid = false;
                        break;
                    }
                    if limitation.accepted {
                        accepted_limitation_count += 1;
                    }
                    if limitation.blocking {
                        blocking_limitation_count += 1;
                    }
                    if limitation.out_of_scope {
                        out_of_scope_limitation_count += 1;
                    }
                }
                if all_limitations_valid
                    && accepted_limitation_count == expected_limitation_ids.len()
                    && blocking_limitation_count == 0
                    && out_of_scope_limitation_count >= 2
                {
                    known_limitations_passed = true;
                    state.mark_passed("known_limitations");
                } else if all_limitations_valid {
                    state.add_unready("known_limitations_blocking_present");
                } else {
                    state.add_contract_invalid("known_limitations_refs_invalid");
                }
            }
        }
    } else {
        state.mark_missing("known_limitations");
        state.add_blocking("known_limitations_missing", "summary_presence");
    }

    let git_head = args.git_head.clone().filter(|value| !value.is_empty());
    let git_branch = args.git_branch.clone().filter(|value| !value.is_empty());
    let git_clean = args.git_clean.unwrap_or(false);
    let git_head_present = git_head.as_deref().is_some_and(is_valid_git_head);
    let git_branch_present = git_branch
        .as_deref()
        .is_some_and(|branch| !branch.is_empty() && branch != "HEAD");
    if git_head_present {
        state.mark_present("git_head");
        state.mark_passed("git_head");
    } else {
        state.mark_missing("git_head");
        state.add_blocking("git_head_missing", "summary_presence");
    }
    if git_branch_present {
        state.mark_present("git_branch");
        state.mark_passed("git_branch");
    } else {
        state.mark_missing("git_branch");
        state.add_blocking("git_branch_missing", "summary_presence");
    }
    if args.git_clean.is_some() {
        state.mark_present("git_clean");
        if git_clean {
            state.mark_passed("git_clean");
        } else {
            state.add_unready("git_worktree_dirty");
        }
    } else {
        state.mark_missing("git_clean");
        state.add_blocking("git_clean_missing", "summary_presence");
    }

    let phase_chain_ready = phase_i_passed && phase_j_passed && phase_l_passed && phase_m_passed;
    let supported_environments_documented = support_matrix_passed;
    let known_limitations_explicit = known_limitations_passed;
    let release_artifacts_attributable =
        git_head_present && git_branch_present && git_clean && release_checklist_passed;

    if !phase_chain_ready {
        state.add_unready("prior_phase_chain_not_ready");
    }
    if !supported_environments_documented {
        state.add_unready("supported_environments_not_documented");
    }
    if !known_limitations_explicit {
        state.add_unready("known_limitations_not_explicit");
    }
    if !release_artifacts_attributable {
        state.add_unready("release_artifacts_not_attributable");
    }

    let required_input_count = state.required_inputs.len();
    let required_input_missing_count = state.missing_required_inputs.len();
    let required_input_present_count = state.present_required_inputs.len();
    let required_input_passed_count = state.passed_required_inputs.len();
    let required_input_failed_count =
        required_input_present_count.saturating_sub(required_input_passed_count);
    let blocking_reason_count = state.blocking_reasons.len();
    let blocking_reason_key_count = state.blocking_reason_key_counts.len();
    let blocking_reason_family_count = state.blocking_reason_family_counts.len();
    let (gate_state_reason, gate_state_reason_family) = summarize_rollout_gate_state(
        required_input_missing_count,
        state.summary_contract_invalid_count,
        state.required_input_unready_count,
        0,
        blocking_reason_count,
    );
    let gate_state = if gate_state_reason_family == "ready" {
        "pass"
    } else {
        "blocked"
    };
    let verdict = if gate_state == "pass" {
        "ready"
    } else {
        "hold"
    };
    let evidence_state = if required_input_missing_count == 0 {
        "complete"
    } else {
        "incomplete"
    };
    let phase_n_state = if verdict == "ready" {
        "honestly_complete"
    } else {
        "blocked"
    };

    Ok(PhaseNProductionReadySummary {
        summary_version: 1,
        verdict_family: UDP_ROLLOUT_OPERATOR_VERDICT_FAMILY,
        decision_scope: "phase_n_production_ready_signoff",
        decision_label: "phase_n_production_ready_signoff",
        profile: "phase_n",
        verdict,
        evidence_state,
        gate_state,
        gate_state_reason,
        gate_state_reason_family,
        phase_n_state,
        required_inputs: state.required_inputs,
        considered_inputs: vec![
            "phase_i_summary".to_owned(),
            "phase_j_summary".to_owned(),
            "phase_l_summary".to_owned(),
            "phase_m_summary".to_owned(),
            "release_checklist".to_owned(),
            "support_matrix".to_owned(),
            "known_limitations".to_owned(),
            "git_head".to_owned(),
            "git_branch".to_owned(),
            "git_clean".to_owned(),
        ],
        missing_required_inputs: state.missing_required_inputs,
        missing_required_input_count: required_input_missing_count,
        required_input_count,
        required_input_missing_count,
        required_input_failed_count,
        required_input_unready_count: state.required_input_unready_count,
        required_input_present_count,
        required_input_passed_count,
        all_required_inputs_present: required_input_missing_count == 0,
        all_required_inputs_passed: required_input_count == required_input_passed_count,
        blocking_reason_count,
        blocking_reason_key_count,
        blocking_reason_family_count,
        blocking_reason_key_counts: state.blocking_reason_key_counts,
        blocking_reason_family_counts: state.blocking_reason_family_counts,
        phase_i_present,
        phase_i_passed,
        phase_j_present,
        phase_j_passed,
        phase_l_present,
        phase_l_passed,
        phase_m_present,
        phase_m_passed,
        release_checklist_present,
        release_checklist_passed,
        support_matrix_present,
        support_matrix_passed,
        known_limitations_present,
        known_limitations_passed,
        phase_chain_ready,
        supported_environments_documented,
        known_limitations_explicit,
        release_artifacts_attributable,
        git_head_present,
        git_branch_present,
        git_clean,
        git_head,
        git_branch,
        release_label,
        supported_upstream_version,
        verified_environment_count,
        documented_environment_count,
        verified_environment_labels,
        supported_environment_kinds,
        checklist_item_ids,
        known_limitation_ids,
        accepted_limitation_count,
        blocking_limitation_count,
        out_of_scope_limitation_count,
        blocking_reasons: state.blocking_reasons,
        blocking_reason_keys: state.blocking_reason_keys,
        blocking_reason_families: state.blocking_reason_families,
    })
}

fn load_json<T: for<'de> Deserialize<'de>>(path: &Path) -> Result<T, Box<dyn std::error::Error>> {
    Ok(serde_json::from_slice(&fs::read(path)?)?)
}

fn is_valid_git_head(value: &str) -> bool {
    value.len() == 40 && value.chars().all(|character| character.is_ascii_hexdigit())
}

fn parse_args(
    arguments: impl IntoIterator<Item = String>,
) -> Result<PhaseNArgs, Box<dyn std::error::Error>> {
    let mut parsed = PhaseNArgs::default();
    let mut iter = arguments.into_iter();
    while let Some(argument) = iter.next() {
        match argument.as_str() {
            "--format" => {
                let value = next_arg(&mut iter, "--format")?;
                parsed.format = Some(match value.as_str() {
                    "text" => OutputFormat::Text,
                    "json" => OutputFormat::Json,
                    other => return Err(format!("unsupported --format value {other}").into()),
                });
            }
            "--summary-path" => {
                parsed.summary_path = Some(PathBuf::from(next_arg(&mut iter, "--summary-path")?))
            }
            "--project-root" => {
                parsed.project_root = Some(PathBuf::from(next_arg(&mut iter, "--project-root")?))
            }
            "--phase-i" => {
                parsed.phase_i_summary = Some(PathBuf::from(next_arg(&mut iter, "--phase-i")?))
            }
            "--phase-j" => {
                parsed.phase_j_summary = Some(PathBuf::from(next_arg(&mut iter, "--phase-j")?))
            }
            "--phase-l" => {
                parsed.phase_l_summary = Some(PathBuf::from(next_arg(&mut iter, "--phase-l")?))
            }
            "--phase-m" => {
                parsed.phase_m_summary = Some(PathBuf::from(next_arg(&mut iter, "--phase-m")?))
            }
            "--release-checklist" => {
                parsed.release_checklist =
                    Some(PathBuf::from(next_arg(&mut iter, "--release-checklist")?))
            }
            "--support-matrix" => {
                parsed.support_matrix =
                    Some(PathBuf::from(next_arg(&mut iter, "--support-matrix")?))
            }
            "--known-limitations" => {
                parsed.known_limitations =
                    Some(PathBuf::from(next_arg(&mut iter, "--known-limitations")?))
            }
            "--git-head" => parsed.git_head = Some(next_arg(&mut iter, "--git-head")?),
            "--git-branch" => parsed.git_branch = Some(next_arg(&mut iter, "--git-branch")?),
            "--git-clean" => {
                parsed.git_clean = Some(match next_arg(&mut iter, "--git-clean")?.as_str() {
                    "true" => true,
                    "false" => false,
                    other => return Err(format!("unsupported --git-clean value {other}").into()),
                })
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

fn next_arg(
    iter: &mut impl Iterator<Item = String>,
    flag: &str,
) -> Result<String, Box<dyn std::error::Error>> {
    iter.next()
        .ok_or_else(|| format!("{flag} requires a value").into())
}

fn print_usage() {
    eprintln!(
        "Usage: cargo run -p ns-testkit --example phase_n_production_ready_signoff -- [--format text|json] [--summary-path <path>] [--project-root <path>] [--phase-i <path>] [--phase-j <path>] [--phase-l <path>] [--phase-m <path>] [--release-checklist <path>] [--support-matrix <path>] [--known-limitations <path>] [--git-head <sha>] [--git-branch <name>] [--git-clean true|false]"
    );
}

fn default_summary_path() -> PathBuf {
    repo_root()
        .join("target")
        .join("verta")
        .join("phase-n-production-ready-signoff-summary.json")
}

fn default_project_root() -> PathBuf {
    let mut root = repo_root();
    root.pop();
    root.pop();
    root
}

fn default_phase_i_summary_path() -> PathBuf {
    prefer_target_verta_then_verta("remnawave-supported-upstream-phase-i-signoff-summary.json")
}

fn default_phase_j_summary_path() -> PathBuf {
    prefer_target_verta_then_verta("udp-phase-j-signoff-summary.json")
}

fn default_phase_l_summary_path() -> PathBuf {
    prefer_target_verta_then_verta("phase-l-operator-readiness-signoff-summary.json")
}

fn default_phase_m_summary_path() -> PathBuf {
    prefer_target_verta_then_verta("phase-m-soak-canary-signoff-summary.json")
}

fn prefer_target_verta_then_verta(file_name: &str) -> PathBuf {
    let canonical = repo_root().join("target").join("verta").join(file_name);
    if canonical.exists() {
        return canonical;
    }

    let legacy = repo_root().join("target").join("verta").join(file_name);
    if legacy.exists() {
        return legacy;
    }

    canonical
}

fn default_release_checklist_path() -> PathBuf {
    repo_root()
        .join("docs")
        .join("release")
        .join("production-ready-checklist.json")
}

fn default_support_matrix_path() -> PathBuf {
    repo_root()
        .join("docs")
        .join("release")
        .join("supported-environment-matrix.json")
}

fn default_known_limitations_path() -> PathBuf {
    repo_root()
        .join("docs")
        .join("release")
        .join("known-limitations.json")
}

fn print_text_summary(summary: &PhaseNProductionReadySummary, summary_path: &Path) {
    println!("Verta Phase N production-ready signoff");
    println!("- verdict: {}", summary.verdict);
    println!("- phase_n_state: {}", summary.phase_n_state);
    println!("- gate_state: {}", summary.gate_state);
    println!("- gate_state_reason: {}", summary.gate_state_reason);
    println!(
        "- phase_chain_ready: phase_i={} phase_j={} phase_l={} phase_m={}",
        summary.phase_i_passed,
        summary.phase_j_passed,
        summary.phase_l_passed,
        summary.phase_m_passed
    );
    println!(
        "- release_docs: checklist={} support_matrix={} known_limitations={}",
        summary.release_checklist_passed,
        summary.support_matrix_passed,
        summary.known_limitations_passed
    );
    println!(
        "- git: branch={} head={} clean={} attributable={}",
        summary.git_branch.as_deref().unwrap_or("n/a"),
        summary.git_head.as_deref().unwrap_or("n/a"),
        summary.git_clean,
        summary.release_artifacts_attributable
    );
    println!(
        "- supported_environments: verified={} documented={} labels={}",
        summary.verified_environment_count,
        summary.documented_environment_count,
        if summary.verified_environment_labels.is_empty() {
            "none".to_owned()
        } else {
            summary.verified_environment_labels.join(",")
        }
    );
    println!(
        "- known_limitations: accepted={} blocking={} out_of_scope={}",
        summary.accepted_limitation_count,
        summary.blocking_limitation_count,
        summary.out_of_scope_limitation_count
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

#[cfg(test)]
mod tests {
    use super::*;
    use serde_json::json;
    use std::time::{SystemTime, UNIX_EPOCH};

    fn create_temp_dir(label: &str) -> PathBuf {
        let root = std::env::temp_dir()
            .join(format!("verta-phase-n-{}-{}", label, std::process::id()))
            .join(
                SystemTime::now()
                    .duration_since(UNIX_EPOCH)
                    .unwrap_or_default()
                    .as_nanos()
                    .to_string(),
            );
        fs::create_dir_all(&root).unwrap();
        root
    }

    fn write_text(path: &Path, value: &str) {
        if let Some(parent) = path.parent() {
            fs::create_dir_all(parent).unwrap();
        }
        fs::write(path, value).unwrap();
    }

    fn write_json(path: &Path, value: serde_json::Value) {
        if let Some(parent) = path.parent() {
            fs::create_dir_all(parent).unwrap();
        }
        fs::write(path, serde_json::to_vec_pretty(&value).unwrap()).unwrap();
    }

    fn ready_args(root: &Path) -> PhaseNArgs {
        write_json(
            &root.join("packages/verta-protocol/target/verta/remnawave-supported-upstream-phase-i-signoff-summary.json"),
            json!({
                "verdict":"ready",
                "phase_i_state":"honestly_complete",
                "supported_deployment_label":"remnawave-local-docker",
                "supported_upstream_version":"2.7.4"
            }),
        );
        write_json(
            &root.join("packages/verta-protocol/target/verta/udp-phase-j-signoff-summary.json"),
            json!({
                "verdict":"ready",
                "phase_j_state":"honestly_complete",
                "broader_wan_evidence_passed":true,
                "artifact_retention_passed":true,
                "transport_fallback_integrity_surface_passed":true
            }),
        );
        write_json(
            &root.join("packages/verta-protocol/target/verta/phase-l-operator-readiness-signoff-summary.json"),
            json!({
                "verdict":"ready",
                "phase_l_state":"honestly_complete",
                "profile_disable_drill_passed":true,
                "rollback_drill_passed":true,
                "recovery_boundaries_documented":true,
                "observability_mapping_documented":true
            }),
        );
        write_json(
            &root.join(
                "packages/verta-protocol/target/verta/phase-m-soak-canary-signoff-summary.json",
            ),
            json!({
                "verdict":"ready",
                "phase_m_state":"honestly_complete",
                "agreed_environment_label":"remnawave-local-docker",
                "observed_duration_seconds":52,
                "rollback_proven":true,
                "p0_open_count":0,
                "p1_open_count":0
            }),
        );

        for path in [
            ".github/workflows/verta-udp-bounded-verification.yml",
            ".github/workflows/verta-udp-scheduled-verification.yml",
            ".github/workflows/verta-udp-release-evidence.yml",
            "packages/verta-protocol/docs/development/SUSTAINED_VERIFICATION_GATES.md",
            "packages/verta-protocol/docs/runbooks/INDEX.md",
            "packages/verta-protocol/docs/transport/FIRST_CARRIER_NOTES.md",
            "packages/verta-protocol/docs/spec/verta_blueprint_v0.md",
            "packages/verta-protocol/docs/implementation/IMPLEMENTATION_STATUS.md",
            "infra/docker-compose.yml",
            "infra/caddy/Caddyfile",
            "infra/ansible/inventories/staging/group_vars/control_plane_staging/main.yml",
            "infra/ansible/inventories/production/group_vars/control_plane_production/main.yml",
            ".gitignore",
            "infra/.env.example",
            "packages/verta-protocol/docs/release/SUPPORTED_ENVIRONMENT_MATRIX.md",
            "packages/verta-protocol/docs/release/KNOWN_LIMITATIONS.md",
            "packages/verta-protocol/docs/release/ARTIFACT_ATTRIBUTION.md",
        ] {
            write_text(&root.join(path), "ok");
        }

        write_json(
            &root.join("packages/verta-protocol/docs/release/production-ready-checklist.json"),
            json!({
                "summary_version":1,
                "phase":"phase_n_production_ready_closure",
                "release_scope":"verta_v0_1",
                "release_label":"verta-v0.1-production-ready",
                "required_items":[
                    {"item_id":"phase_i_honest_closure","status":"done","required":true,"evidence_refs":["packages/verta-protocol/target/verta/remnawave-supported-upstream-phase-i-signoff-summary.json"]},
                    {"item_id":"phase_j_wan_and_chaos","status":"done","required":true,"evidence_refs":["packages/verta-protocol/target/verta/udp-phase-j-signoff-summary.json"]},
                    {"item_id":"phase_k_sustained_verification","status":"done","required":true,"evidence_refs":[".github/workflows/verta-udp-bounded-verification.yml",".github/workflows/verta-udp-scheduled-verification.yml",".github/workflows/verta-udp-release-evidence.yml","packages/verta-protocol/docs/development/SUSTAINED_VERIFICATION_GATES.md"]},
                    {"item_id":"phase_l_operator_readiness","status":"done","required":true,"evidence_refs":["packages/verta-protocol/target/verta/phase-l-operator-readiness-signoff-summary.json"]},
                    {"item_id":"phase_m_soak_canary","status":"done","required":true,"evidence_refs":["packages/verta-protocol/target/verta/phase-m-soak-canary-signoff-summary.json"]},
                    {"item_id":"supported_environment_matrix","status":"done","required":true,"evidence_refs":["packages/verta-protocol/docs/release/SUPPORTED_ENVIRONMENT_MATRIX.md","packages/verta-protocol/docs/release/supported-environment-matrix.json"]},
                    {"item_id":"known_limitations_documented","status":"done","required":true,"evidence_refs":["packages/verta-protocol/docs/release/KNOWN_LIMITATIONS.md","packages/verta-protocol/docs/release/known-limitations.json"]},
                    {"item_id":"artifact_attribution_documented","status":"done","required":true,"evidence_refs":["packages/verta-protocol/docs/release/ARTIFACT_ATTRIBUTION.md"]},
                    {"item_id":"local_env_files_ignored","status":"done","required":true,"evidence_refs":[".gitignore","infra/.env.example"]}
                ]
            }),
        );
        write_json(
            &root.join("packages/verta-protocol/docs/release/supported-environment-matrix.json"),
            json!({
                "summary_version":1,
                "phase":"phase_n_production_ready_closure",
                "release_scope":"verta_v0_1",
                "environments":[
                    {"environment_id":"local_supported_staging","deployment_label":"remnawave-local-docker","environment_kind":"local_supported_staging","support_status":"verified","upstream_support":["remnawave_2.7.x"],"configuration_refs":["infra/docker-compose.yml","infra/caddy/Caddyfile"],"evidence_refs":["packages/verta-protocol/target/verta/remnawave-supported-upstream-phase-i-signoff-summary.json","packages/verta-protocol/target/verta/phase-m-soak-canary-signoff-summary.json"]},
                    {"environment_id":"operator_managed_staging","deployment_label":"control-plane-staging","environment_kind":"operator_managed_staging","support_status":"documented","upstream_support":["remnawave_2.7.x"],"configuration_refs":["infra/ansible/inventories/staging/group_vars/control_plane_staging/main.yml"],"evidence_refs":["packages/verta-protocol/docs/development/SUSTAINED_VERIFICATION_GATES.md","packages/verta-protocol/docs/runbooks/INDEX.md"]},
                    {"environment_id":"operator_managed_production","deployment_label":"control-plane-production","environment_kind":"operator_managed_production","support_status":"documented","upstream_support":["remnawave_2.7.x"],"configuration_refs":["infra/ansible/inventories/production/group_vars/control_plane_production/main.yml"],"evidence_refs":["packages/verta-protocol/docs/development/SUSTAINED_VERIFICATION_GATES.md","packages/verta-protocol/docs/runbooks/INDEX.md"]}
                ]
            }),
        );
        write_json(
            &root.join("packages/verta-protocol/docs/release/known-limitations.json"),
            json!({
                "summary_version":1,
                "phase":"phase_n_production_ready_closure",
                "release_scope":"verta_v0_1",
                "limitations":[
                    {"limitation_id":"single_carrier_h3_only","category":"carrier","summary":"x","blocking":false,"accepted":true,"out_of_scope":true,"refs":["packages/verta-protocol/docs/transport/FIRST_CARRIER_NOTES.md"]},
                    {"limitation_id":"zero_rtt_disabled","category":"security_policy","summary":"x","blocking":false,"accepted":true,"out_of_scope":true,"refs":["packages/verta-protocol/docs/spec/verta_blueprint_v0.md"]},
                    {"limitation_id":"client_inbound_placeholder","category":"scope","summary":"x","blocking":false,"accepted":true,"out_of_scope":true,"refs":["packages/verta-protocol/docs/implementation/IMPLEMENTATION_STATUS.md"]},
                    {"limitation_id":"multi_host_release_evidence_ci_driven","category":"verification","summary":"x","blocking":false,"accepted":true,"out_of_scope":false,"refs":[".github/workflows/verta-udp-release-evidence.yml","packages/verta-protocol/docs/development/SUSTAINED_VERIFICATION_GATES.md"]}
                ]
            }),
        );

        PhaseNArgs {
            format: Some(OutputFormat::Json),
            summary_path: Some(root.join("packages/verta-protocol/target/verta/phase-n-production-ready-signoff-summary.json")),
            project_root: Some(root.to_path_buf()),
            phase_i_summary: Some(root.join("packages/verta-protocol/target/verta/remnawave-supported-upstream-phase-i-signoff-summary.json")),
            phase_j_summary: Some(root.join("packages/verta-protocol/target/verta/udp-phase-j-signoff-summary.json")),
            phase_l_summary: Some(root.join("packages/verta-protocol/target/verta/phase-l-operator-readiness-signoff-summary.json")),
            phase_m_summary: Some(root.join("packages/verta-protocol/target/verta/phase-m-soak-canary-signoff-summary.json")),
            release_checklist: Some(root.join("packages/verta-protocol/docs/release/production-ready-checklist.json")),
            support_matrix: Some(root.join("packages/verta-protocol/docs/release/supported-environment-matrix.json")),
            known_limitations: Some(root.join("packages/verta-protocol/docs/release/known-limitations.json")),
            git_head: Some("0123456789abcdef0123456789abcdef01234567".to_owned()),
            git_branch: Some("main".to_owned()),
            git_clean: Some(true),
        }
    }

    #[test]
    fn ready_summary_when_phase_chain_docs_and_git_are_ready() {
        let root = create_temp_dir("ready");
        let args = ready_args(&root);
        let summary = build_summary(&args).unwrap();
        assert_eq!(summary.verdict, "ready");
        assert_eq!(summary.phase_n_state, "honestly_complete");
        assert!(summary.release_artifacts_attributable);
    }

    #[test]
    fn blocks_when_git_worktree_is_dirty() {
        let root = create_temp_dir("dirty");
        let mut args = ready_args(&root);
        args.git_clean = Some(false);
        let summary = build_summary(&args).unwrap();
        assert_eq!(summary.verdict, "hold");
        assert!(
            summary
                .blocking_reasons
                .contains(&"git_worktree_dirty".to_owned())
        );
    }

    #[test]
    fn blocks_when_known_limitation_is_blocking() {
        let root = create_temp_dir("blocking-limitation");
        let args = ready_args(&root);
        write_json(
            args.known_limitations.as_ref().unwrap(),
            json!({
                "summary_version":1,
                "phase":"phase_n_production_ready_closure",
                "release_scope":"verta_v0_1",
                "limitations":[
                    {"limitation_id":"single_carrier_h3_only","category":"carrier","summary":"x","blocking":true,"accepted":true,"out_of_scope":true,"refs":["packages/verta-protocol/docs/transport/FIRST_CARRIER_NOTES.md"]},
                    {"limitation_id":"zero_rtt_disabled","category":"security_policy","summary":"x","blocking":false,"accepted":true,"out_of_scope":true,"refs":["packages/verta-protocol/docs/spec/verta_blueprint_v0.md"]},
                    {"limitation_id":"client_inbound_placeholder","category":"scope","summary":"x","blocking":false,"accepted":true,"out_of_scope":true,"refs":["packages/verta-protocol/docs/implementation/IMPLEMENTATION_STATUS.md"]},
                    {"limitation_id":"multi_host_release_evidence_ci_driven","category":"verification","summary":"x","blocking":false,"accepted":true,"out_of_scope":false,"refs":[".github/workflows/verta-udp-release-evidence.yml","packages/verta-protocol/docs/development/SUSTAINED_VERIFICATION_GATES.md"]}
                ]
            }),
        );
        let summary = build_summary(&args).unwrap();
        assert_eq!(summary.verdict, "hold");
        assert_eq!(summary.blocking_limitation_count, 1);
        assert!(
            summary
                .blocking_reasons
                .contains(&"known_limitations_blocking_present".to_owned())
        );
    }

    #[test]
    fn legacy_release_scope_remains_accepted() {
        let root = create_temp_dir("legacy-release-scope");
        let args = ready_args(&root);

        write_json(
            args.release_checklist.as_ref().unwrap(),
            json!({
                "summary_version":1,
                "phase":"phase_n_production_ready_closure",
                "release_scope":"verta_v0_1",
                "release_label":"verta-v0.1-production-ready",
                "required_items":[
                    {"item_id":"phase_i_honest_closure","status":"done","required":true,"evidence_refs":["packages/verta-protocol/target/verta/remnawave-supported-upstream-phase-i-signoff-summary.json"]},
                    {"item_id":"phase_j_wan_and_chaos","status":"done","required":true,"evidence_refs":["packages/verta-protocol/target/verta/udp-phase-j-signoff-summary.json"]},
                    {"item_id":"phase_k_sustained_verification","status":"done","required":true,"evidence_refs":[".github/workflows/verta-udp-bounded-verification.yml",".github/workflows/verta-udp-scheduled-verification.yml",".github/workflows/verta-udp-release-evidence.yml","packages/verta-protocol/docs/development/SUSTAINED_VERIFICATION_GATES.md"]},
                    {"item_id":"phase_l_operator_readiness","status":"done","required":true,"evidence_refs":["packages/verta-protocol/target/verta/phase-l-operator-readiness-signoff-summary.json"]},
                    {"item_id":"phase_m_soak_canary","status":"done","required":true,"evidence_refs":["packages/verta-protocol/target/verta/phase-m-soak-canary-signoff-summary.json"]},
                    {"item_id":"supported_environment_matrix","status":"done","required":true,"evidence_refs":["packages/verta-protocol/docs/release/SUPPORTED_ENVIRONMENT_MATRIX.md","packages/verta-protocol/docs/release/supported-environment-matrix.json"]},
                    {"item_id":"known_limitations_documented","status":"done","required":true,"evidence_refs":["packages/verta-protocol/docs/release/KNOWN_LIMITATIONS.md","packages/verta-protocol/docs/release/known-limitations.json"]},
                    {"item_id":"artifact_attribution_documented","status":"done","required":true,"evidence_refs":["packages/verta-protocol/docs/release/ARTIFACT_ATTRIBUTION.md"]},
                    {"item_id":"local_env_files_ignored","status":"done","required":true,"evidence_refs":[".gitignore","infra/.env.example"]}
                ]
            }),
        );
        write_json(
            args.support_matrix.as_ref().unwrap(),
            json!({
                "summary_version":1,
                "phase":"phase_n_production_ready_closure",
                "release_scope":"verta_v0_1",
                "environments":[
                    {"environment_id":"local_supported_staging","deployment_label":"remnawave-local-docker","environment_kind":"local_supported_staging","support_status":"verified","upstream_support":["remnawave_2.7.x"],"configuration_refs":["infra/docker-compose.yml","infra/caddy/Caddyfile"],"evidence_refs":["packages/verta-protocol/target/verta/remnawave-supported-upstream-phase-i-signoff-summary.json","packages/verta-protocol/target/verta/phase-m-soak-canary-signoff-summary.json"]},
                    {"environment_id":"operator_managed_staging","deployment_label":"control-plane-staging","environment_kind":"operator_managed_staging","support_status":"documented","upstream_support":["remnawave_2.7.x"],"configuration_refs":["infra/ansible/inventories/staging/group_vars/control_plane_staging/main.yml"],"evidence_refs":["packages/verta-protocol/docs/development/SUSTAINED_VERIFICATION_GATES.md","packages/verta-protocol/docs/runbooks/INDEX.md"]},
                    {"environment_id":"operator_managed_production","deployment_label":"control-plane-production","environment_kind":"operator_managed_production","support_status":"documented","upstream_support":["remnawave_2.7.x"],"configuration_refs":["infra/ansible/inventories/production/group_vars/control_plane_production/main.yml"],"evidence_refs":["packages/verta-protocol/docs/development/SUSTAINED_VERIFICATION_GATES.md","packages/verta-protocol/docs/runbooks/INDEX.md"]}
                ]
            }),
        );
        write_json(
            args.known_limitations.as_ref().unwrap(),
            json!({
                "summary_version":1,
                "phase":"phase_n_production_ready_closure",
                "release_scope":"verta_v0_1",
                "limitations":[
                    {"limitation_id":"single_carrier_h3_only","category":"carrier","summary":"x","blocking":false,"accepted":true,"out_of_scope":true,"refs":["packages/verta-protocol/docs/transport/FIRST_CARRIER_NOTES.md"]},
                    {"limitation_id":"zero_rtt_disabled","category":"security_policy","summary":"x","blocking":false,"accepted":true,"out_of_scope":true,"refs":["packages/verta-protocol/docs/spec/verta_blueprint_v0.md"]},
                    {"limitation_id":"client_inbound_placeholder","category":"scope","summary":"x","blocking":false,"accepted":true,"out_of_scope":true,"refs":["packages/verta-protocol/docs/implementation/IMPLEMENTATION_STATUS.md"]},
                    {"limitation_id":"multi_host_release_evidence_ci_driven","category":"verification","summary":"x","blocking":false,"accepted":true,"out_of_scope":false,"refs":[".github/workflows/verta-udp-release-evidence.yml","packages/verta-protocol/docs/development/SUSTAINED_VERIFICATION_GATES.md"]}
                ]
            }),
        );

        let summary = build_summary(&args).unwrap();
        assert_eq!(summary.verdict, "ready");
    }
}
