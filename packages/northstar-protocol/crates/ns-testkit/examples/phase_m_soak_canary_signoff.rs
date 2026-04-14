use ns_testkit::{
    repo_root, summarize_rollout_gate_state, UDP_ROLLOUT_OPERATOR_VERDICT_FAMILY,
};
use serde::{Deserialize, Serialize};
use std::collections::BTreeMap;
use std::env;
use std::fs;
use std::path::{Path, PathBuf};
use std::time::{SystemTime, UNIX_EPOCH};

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
enum OutputFormat {
    Text,
    Json,
}

#[derive(Debug, Default)]
struct PhaseMArgs {
    format: Option<OutputFormat>,
    summary_path: Option<PathBuf>,
    stage_root: Option<PathBuf>,
    canary_plan: Option<PathBuf>,
    regression_ledger: Option<PathBuf>,
    phase_i_summary: Option<PathBuf>,
    wan_staging_summary: Option<PathBuf>,
}

#[derive(Debug, Deserialize)]
struct CanaryPlan {
    summary_version: u8,
    phase: String,
    environment_label: String,
    environment_kind: String,
    minimum_duration_seconds: u64,
    stage_pause_seconds: u64,
    rollback_command_refs: Vec<String>,
    baseline_refs: Vec<String>,
    rollback_trigger_conditions: Vec<String>,
    stages: Vec<CanaryStagePlan>,
}

#[derive(Debug, Deserialize)]
struct CanaryStagePlan {
    stage_id: String,
    rollout_fraction_hint: String,
    rollback_required: bool,
    required_artifacts: Vec<String>,
}

#[derive(Debug, Deserialize)]
struct RegressionLedger {
    summary_version: u8,
    phase: String,
    baseline_refs: Vec<String>,
    severity_rules: Vec<SeverityRule>,
    #[serde(default)]
    open_regressions: Vec<RegressionItem>,
    #[serde(default)]
    accepted_tail: Vec<RegressionItem>,
    catastrophic_regression_blockers: Vec<String>,
}

#[derive(Debug, Deserialize)]
struct SeverityRule {
    severity: String,
    max_open: usize,
}

#[derive(Debug, Deserialize)]
struct RegressionItem {
    severity: String,
}

#[derive(Debug, Deserialize)]
struct PhaseISummaryInput {
    verdict: String,
    phase_i_state: String,
}

#[derive(Debug, Deserialize)]
struct WanStagingSummaryInput {
    verdict: String,
    source_lane: String,
    all_profiles_passed: bool,
    transport_fallback_integrity_surface_passed: bool,
    degradation_path_visibility_passed: bool,
    artifact_retention_passed: Option<bool>,
}

#[derive(Debug, Deserialize)]
struct LifecycleSummaryInput {
    verdict: String,
    supported_upstream_expected_lifecycle: String,
    lifecycle_expected_state_passed: Option<bool>,
    lifecycle_bridge_manifest_bootstrap_denied: Option<bool>,
    lifecycle_bridge_manifest_refresh_denied: Option<bool>,
    lifecycle_bridge_token_exchange_denied: Option<bool>,
    webhook_positive_delivery_passed: Option<bool>,
    webhook_duplicate_rejection_passed: Option<bool>,
    webhook_reconcile_hint_passed: Option<bool>,
    supported_upstream_lifecycle_passed: Option<bool>,
}

#[derive(Debug, Deserialize)]
struct RollbackSummaryInput {
    verdict: String,
    artifact_root_present: Option<bool>,
    profile_slugs: Vec<String>,
    failed_profile_slugs: Vec<String>,
    degradation_path_visibility_passed: bool,
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

#[derive(Debug, Serialize)]
struct PhaseMStageSummary {
    stage_id: String,
    rollout_fraction_hint: String,
    stage_dir: String,
    lifecycle_summary_path: String,
    rollback_summary_path: String,
    phase_l_summary_path: String,
    lifecycle_ready: bool,
    rollback_ready: bool,
    phase_l_ready: bool,
    rollback_required: bool,
    rollback_proven: bool,
    stage_passed: bool,
}

#[derive(Debug, Serialize)]
struct PhaseMSoakCanarySummary {
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
    phase_m_state: &'static str,
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
    canary_plan_present: bool,
    canary_plan_passed: bool,
    regression_ledger_present: bool,
    regression_ledger_passed: bool,
    phase_i_baseline_present: bool,
    phase_i_baseline_passed: bool,
    wan_staging_baseline_present: bool,
    wan_staging_baseline_passed: bool,
    agreed_environment_label: Option<String>,
    agreed_environment_kind: Option<String>,
    minimum_duration_seconds: u64,
    observed_duration_seconds: u64,
    meets_minimum_duration: bool,
    stage_count: usize,
    stage_passed_count: usize,
    stage_failed_count: usize,
    stage_ids: Vec<String>,
    rollback_proven: bool,
    p0_open_count: usize,
    p1_open_count: usize,
    accepted_tail_count: usize,
    catastrophic_regression_detected: bool,
    stages: Vec<PhaseMStageSummary>,
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
        return Err("phase m soak/canary signoff is not ready".into());
    }

    Ok(())
}

fn build_summary(args: &PhaseMArgs) -> Result<PhaseMSoakCanarySummary, Box<dyn std::error::Error>> {
    let stage_root = args.stage_root.clone().unwrap_or_else(default_stage_root);
    let canary_plan_path = args.canary_plan.clone().unwrap_or_else(default_canary_plan_path);
    let regression_ledger_path = args
        .regression_ledger
        .clone()
        .unwrap_or_else(default_regression_ledger_path);
    let phase_i_summary_path = args.phase_i_summary.clone().unwrap_or_else(default_phase_i_summary_path);
    let wan_staging_summary_path = args
        .wan_staging_summary
        .clone()
        .unwrap_or_else(default_wan_staging_summary_path);

    let mut state = EvaluationState::default();
    state.require("canary_plan");
    state.require("regression_ledger");
    state.require("phase_i_baseline");
    state.require("wan_staging_baseline");

    let mut agreed_environment_label = None;
    let mut agreed_environment_kind = None;
    let mut minimum_duration_seconds = 0;
    let mut stage_ids = Vec::new();
    let mut stages = Vec::new();
    let mut stage_passed_count = 0usize;
    let mut lifecycle_mtimes = Vec::new();
    let mut rollback_proven = true;

    let mut canary_plan_present = false;
    let mut canary_plan_passed = false;
    let canary_plan = if canary_plan_path.is_file() {
        state.mark_present("canary_plan");
        canary_plan_present = true;
        Some(load_json::<CanaryPlan>(&canary_plan_path)?)
    } else {
        state.mark_missing("canary_plan");
        state.add_blocking("canary_plan_missing", "summary_presence");
        None
    };

    if let Some(plan) = &canary_plan {
        if plan.summary_version != 1 || plan.phase != "phase_m_soak_canary" {
            state.add_contract_invalid("canary_plan_contract_invalid");
        } else if plan.minimum_duration_seconds == 0
            || plan.stage_pause_seconds == 0
            || plan.environment_label.is_empty()
            || plan.environment_kind.is_empty()
            || plan.rollback_command_refs.len() < 2
            || plan.rollback_trigger_conditions.is_empty()
            || plan.baseline_refs.is_empty()
        {
            state.add_contract_invalid("canary_plan_incomplete");
        } else {
            agreed_environment_label = Some(plan.environment_label.clone());
            agreed_environment_kind = Some(plan.environment_kind.clone());
            minimum_duration_seconds = plan.minimum_duration_seconds;
            stage_ids = plan.stages.iter().map(|stage| stage.stage_id.clone()).collect();
            let exact_stage_ids = vec![
                "canary_5".to_owned(),
                "canary_25".to_owned(),
                "canary_100".to_owned(),
            ];
            if stage_ids != exact_stage_ids {
                state.add_contract_invalid("canary_plan_stage_inventory_drift");
            } else {
                canary_plan_passed = true;
                state.mark_passed("canary_plan");
            }
        }
    }

    let mut regression_ledger_present = false;
    let mut regression_ledger_passed = false;
    let mut p0_open_count = 0usize;
    let mut p1_open_count = 0usize;
    let mut accepted_tail_count = 0usize;
    let regression_ledger = if regression_ledger_path.is_file() {
        state.mark_present("regression_ledger");
        regression_ledger_present = true;
        Some(load_json::<RegressionLedger>(&regression_ledger_path)?)
    } else {
        state.mark_missing("regression_ledger");
        state.add_blocking("regression_ledger_missing", "summary_presence");
        None
    };

    if let Some(ledger) = &regression_ledger {
        if ledger.summary_version != 1
            || ledger.phase != "phase_m_regression_burndown"
            || ledger.severity_rules.len() < 4
            || ledger.baseline_refs.is_empty()
            || ledger.catastrophic_regression_blockers.is_empty()
        {
            state.add_contract_invalid("regression_ledger_contract_invalid");
        } else {
            let mut rules = BTreeMap::new();
            for rule in &ledger.severity_rules {
                rules.insert(rule.severity.as_str(), rule.max_open);
            }
            if rules.get("p0") != Some(&0) || rules.get("p1") != Some(&0) {
                state.add_contract_invalid("regression_bug_bar_invalid");
            } else {
                p0_open_count = ledger
                    .open_regressions
                    .iter()
                    .filter(|item| item.severity == "p0")
                    .count();
                p1_open_count = ledger
                    .open_regressions
                    .iter()
                    .filter(|item| item.severity == "p1")
                    .count();
                accepted_tail_count = ledger.accepted_tail.len();
                if p0_open_count > 0 || p1_open_count > 0 {
                    state.add_unready("regression_p0_p1_open");
                } else {
                    regression_ledger_passed = true;
                    state.mark_passed("regression_ledger");
                }
            }
        }
    }

    let mut phase_i_baseline_present = false;
    let mut phase_i_baseline_passed = false;
    if phase_i_summary_path.is_file() {
        state.mark_present("phase_i_baseline");
        phase_i_baseline_present = true;
        let summary = load_json::<PhaseISummaryInput>(&phase_i_summary_path)?;
        if summary.verdict == "ready" && summary.phase_i_state == "honestly_complete" {
            phase_i_baseline_passed = true;
            state.mark_passed("phase_i_baseline");
        } else {
            state.add_unready("phase_i_baseline_not_ready");
        }
    } else {
        state.mark_missing("phase_i_baseline");
        state.add_blocking("phase_i_baseline_missing", "summary_presence");
    }

    let mut wan_staging_baseline_present = false;
    let mut wan_staging_baseline_passed = false;
    if wan_staging_summary_path.is_file() {
        state.mark_present("wan_staging_baseline");
        wan_staging_baseline_present = true;
        let summary = load_json::<WanStagingSummaryInput>(&wan_staging_summary_path)?;
        if summary.verdict == "ready"
            && summary.source_lane == "wan_staging_interop"
            && summary.all_profiles_passed
            && summary.transport_fallback_integrity_surface_passed
            && summary.degradation_path_visibility_passed
            && summary.artifact_retention_passed == Some(true)
        {
            wan_staging_baseline_passed = true;
            state.mark_passed("wan_staging_baseline");
        } else {
            state.add_unready("wan_staging_baseline_not_ready");
        }
    } else {
        state.mark_missing("wan_staging_baseline");
        state.add_blocking("wan_staging_baseline_missing", "summary_presence");
    }

    if let Some(plan) = &canary_plan {
        for stage in &plan.stages {
            let stage_label = format!("canary_stage:{}", stage.stage_id);
            state.require(stage_label.clone());
            let stage_dir = stage_root.join(&stage.stage_id);
            let lifecycle_path = stage_dir.join("lifecycle-summary.json");
            let rollback_path = stage_dir.join("rollback-summary.json");
            let phase_l_path = stage_dir.join("phase-l-summary.json");

            let documented_artifacts = stage.required_artifacts.as_slice()
                == ["lifecycle-summary.json", "rollback-summary.json", "phase-l-summary.json"];
            if !documented_artifacts {
                state.add_contract_invalid(format!("{}_artifact_contract_invalid", stage.stage_id));
            }

            let mut lifecycle_ready = false;
            let mut rollback_ready = false;
            let mut phase_l_ready = false;

            if !lifecycle_path.is_file() || !rollback_path.is_file() || !phase_l_path.is_file() {
                state.mark_missing(&stage_label);
                state.add_blocking(
                    format!("{}_artifacts_missing", stage.stage_id),
                    "summary_presence",
                );
                rollback_proven = false;
            } else {
                state.mark_present(&stage_label);

                let lifecycle = load_json::<LifecycleSummaryInput>(&lifecycle_path)?;
                lifecycle_ready = lifecycle.verdict == "ready"
                    && lifecycle.supported_upstream_expected_lifecycle == "disabled"
                    && lifecycle.lifecycle_expected_state_passed == Some(true)
                    && lifecycle.lifecycle_bridge_manifest_bootstrap_denied == Some(true)
                    && lifecycle.lifecycle_bridge_manifest_refresh_denied == Some(true)
                    && lifecycle.lifecycle_bridge_token_exchange_denied == Some(true)
                    && lifecycle.webhook_positive_delivery_passed == Some(true)
                    && lifecycle.webhook_duplicate_rejection_passed == Some(true)
                    && lifecycle.webhook_reconcile_hint_passed == Some(true)
                    && lifecycle.supported_upstream_lifecycle_passed == Some(true);

                let rollback = load_json::<RollbackSummaryInput>(&rollback_path)?;
                rollback_ready = rollback.verdict == "ready"
                    && rollback.artifact_root_present == Some(true)
                    && rollback.profile_slugs == vec!["udp-blocked".to_owned()]
                    && rollback.failed_profile_slugs.is_empty()
                    && rollback.degradation_path_visibility_passed
                    && rollback.transport_fallback_integrity_surface_passed;

                let phase_l = load_json::<PhaseLSummaryInput>(&phase_l_path)?;
                phase_l_ready = phase_l.verdict == "ready"
                    && phase_l.phase_l_state == "honestly_complete"
                    && phase_l.profile_disable_drill_passed
                    && phase_l.rollback_drill_passed
                    && phase_l.recovery_boundaries_documented
                    && phase_l.observability_mapping_documented;

                if lifecycle_ready && rollback_ready && phase_l_ready {
                    stage_passed_count += 1;
                    state.mark_passed(&stage_label);
                } else {
                    state.add_unready(format!("{}_not_ready", stage.stage_id));
                }

                if let Ok(modified) = fs::metadata(&phase_l_path).and_then(|meta| meta.modified()) {
                    lifecycle_mtimes.push(modified);
                }
                rollback_proven &= rollback_ready && stage.rollback_required;
            }

            stages.push(PhaseMStageSummary {
                stage_id: stage.stage_id.clone(),
                rollout_fraction_hint: stage.rollout_fraction_hint.clone(),
                stage_dir: stage_dir.display().to_string(),
                lifecycle_summary_path: lifecycle_path.display().to_string(),
                rollback_summary_path: rollback_path.display().to_string(),
                phase_l_summary_path: phase_l_path.display().to_string(),
                lifecycle_ready,
                rollback_ready,
                phase_l_ready,
                rollback_required: stage.rollback_required,
                rollback_proven: rollback_ready && stage.rollback_required,
                stage_passed: lifecycle_ready && rollback_ready && phase_l_ready,
            });
        }
    }

    let observed_duration_seconds = observed_duration_seconds(&lifecycle_mtimes);
    let meets_minimum_duration = minimum_duration_seconds > 0
        && observed_duration_seconds >= minimum_duration_seconds;
    if canary_plan_present && !meets_minimum_duration {
        state.add_unready("minimum_soak_duration_unmet");
    }

    let stage_count = stages.len();
    let stage_failed_count = stage_count.saturating_sub(stage_passed_count);
    if stage_count == 0 {
        rollback_proven = false;
    }

    let catastrophic_regression_detected = !phase_i_baseline_passed
        || !wan_staging_baseline_passed
        || stage_failed_count > 0
        || !rollback_proven
        || p0_open_count > 0
        || p1_open_count > 0;
    if catastrophic_regression_detected {
        state.add_unready("catastrophic_regression_detected");
    }

    let required_input_count = state.required_inputs.len();
    let required_input_missing_count = state.missing_required_inputs.len();
    let required_input_present_count = state.present_required_inputs.len();
    let required_input_passed_count = state.passed_required_inputs.len();
    let required_input_failed_count = required_input_present_count.saturating_sub(required_input_passed_count);
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
    let verdict = if gate_state == "pass" { "ready" } else { "hold" };
    let evidence_state = if required_input_missing_count == 0 { "complete" } else { "incomplete" };
    let phase_m_state = if verdict == "ready" {
        "honestly_complete"
    } else {
        "blocked"
    };

    Ok(PhaseMSoakCanarySummary {
        summary_version: 1,
        verdict_family: UDP_ROLLOUT_OPERATOR_VERDICT_FAMILY,
        decision_scope: "phase_m_soak_canary_signoff",
        decision_label: "phase_m_soak_canary_signoff",
        profile: "phase_m",
        verdict,
        evidence_state,
        gate_state,
        gate_state_reason,
        gate_state_reason_family,
        phase_m_state,
        required_inputs: state.required_inputs,
        considered_inputs: vec![
            "canary_plan".to_owned(),
            "regression_ledger".to_owned(),
            "phase_i_baseline".to_owned(),
            "wan_staging_baseline".to_owned(),
            "canary_stage:canary_5".to_owned(),
            "canary_stage:canary_25".to_owned(),
            "canary_stage:canary_100".to_owned(),
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
        canary_plan_present,
        canary_plan_passed,
        regression_ledger_present,
        regression_ledger_passed,
        phase_i_baseline_present,
        phase_i_baseline_passed,
        wan_staging_baseline_present,
        wan_staging_baseline_passed,
        agreed_environment_label,
        agreed_environment_kind,
        minimum_duration_seconds,
        observed_duration_seconds,
        meets_minimum_duration,
        stage_count,
        stage_passed_count,
        stage_failed_count,
        stage_ids,
        rollback_proven,
        p0_open_count,
        p1_open_count,
        accepted_tail_count,
        catastrophic_regression_detected,
        stages,
        blocking_reasons: state.blocking_reasons,
        blocking_reason_keys: state.blocking_reason_keys,
        blocking_reason_families: state.blocking_reason_families,
    })
}

fn load_json<T: for<'de> Deserialize<'de>>(path: &Path) -> Result<T, Box<dyn std::error::Error>> {
    Ok(serde_json::from_slice(&fs::read(path)?)?)
}

fn observed_duration_seconds(times: &[SystemTime]) -> u64 {
    if times.len() < 2 {
        return 0;
    }

    let oldest = times.iter().min().copied().unwrap_or(UNIX_EPOCH);
    let newest = times.iter().max().copied().unwrap_or(UNIX_EPOCH);
    newest
        .duration_since(oldest)
        .unwrap_or_default()
        .as_secs()
}

fn parse_args(arguments: impl IntoIterator<Item = String>) -> Result<PhaseMArgs, Box<dyn std::error::Error>> {
    let mut parsed = PhaseMArgs::default();
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
            "--summary-path" => parsed.summary_path = Some(PathBuf::from(next_arg(&mut iter, "--summary-path")?)),
            "--stage-root" => parsed.stage_root = Some(PathBuf::from(next_arg(&mut iter, "--stage-root")?)),
            "--canary-plan" => parsed.canary_plan = Some(PathBuf::from(next_arg(&mut iter, "--canary-plan")?)),
            "--regression-ledger" => {
                parsed.regression_ledger = Some(PathBuf::from(next_arg(&mut iter, "--regression-ledger")?))
            }
            "--phase-i" => parsed.phase_i_summary = Some(PathBuf::from(next_arg(&mut iter, "--phase-i")?)),
            "--wan-staging" => {
                parsed.wan_staging_summary = Some(PathBuf::from(next_arg(&mut iter, "--wan-staging")?))
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
        "Usage: cargo run -p ns-testkit --example phase_m_soak_canary_signoff -- [--format text|json] [--summary-path <path>] [--stage-root <path>] [--canary-plan <path>] [--regression-ledger <path>] [--phase-i <path>] [--wan-staging <path>]"
    );
}

fn default_summary_path() -> PathBuf {
    repo_root()
        .join("target")
        .join("northstar")
        .join("phase-m-soak-canary-signoff-summary.json")
}

fn default_stage_root() -> PathBuf {
    repo_root().join("target").join("northstar").join("phase-m-soak")
}

fn default_canary_plan_path() -> PathBuf {
    repo_root()
        .join("docs")
        .join("runbooks")
        .join("phase-m-canary-plan.json")
}

fn default_regression_ledger_path() -> PathBuf {
    repo_root()
        .join("docs")
        .join("development")
        .join("phase-m-regression-ledger.json")
}

fn default_phase_i_summary_path() -> PathBuf {
    repo_root()
        .join("target")
        .join("northstar")
        .join("remnawave-supported-upstream-phase-i-signoff-summary.json")
}

fn default_wan_staging_summary_path() -> PathBuf {
    repo_root()
        .join("target")
        .join("northstar")
        .join("udp-wan-staging-interop-summary.json")
}

fn print_text_summary(summary: &PhaseMSoakCanarySummary, summary_path: &Path) {
    println!("Northstar Phase M soak/canary signoff");
    println!("- verdict: {}", summary.verdict);
    println!("- phase_m_state: {}", summary.phase_m_state);
    println!("- gate_state: {}", summary.gate_state);
    println!("- gate_state_reason: {}", summary.gate_state_reason);
    println!(
        "- agreed_environment: label={} kind={}",
        summary
            .agreed_environment_label
            .as_deref()
            .unwrap_or("n/a"),
        summary
            .agreed_environment_kind
            .as_deref()
            .unwrap_or("n/a"),
    );
    println!(
        "- soak_duration: observed={}s minimum={}s meets_minimum={}",
        summary.observed_duration_seconds,
        summary.minimum_duration_seconds,
        summary.meets_minimum_duration
    );
    println!(
        "- baselines: phase_i={} wan_staging={}",
        summary.phase_i_baseline_passed, summary.wan_staging_baseline_passed
    );
    println!(
        "- regression_bar: p0_open={} p1_open={} accepted_tail={}",
        summary.p0_open_count, summary.p1_open_count, summary.accepted_tail_count
    );
    println!(
        "- stages: total={} passed={} failed={}",
        summary.stage_count, summary.stage_passed_count, summary.stage_failed_count
    );
    for stage in &summary.stages {
        println!(
            "- {} lifecycle={} rollback={} phase_l={} passed={}",
            stage.stage_id,
            stage.lifecycle_ready,
            stage.rollback_ready,
            stage.phase_l_ready,
            stage.stage_passed
        );
    }
    println!("- rollback_proven: {}", summary.rollback_proven);
    println!(
        "- catastrophic_regression_detected: {}",
        summary.catastrophic_regression_detected
    );
    if summary.blocking_reasons.is_empty() {
        println!("- blocking_reasons: none");
    } else {
        println!("- blocking_reasons: {}", summary.blocking_reasons.join(", "));
    }
    println!("machine_readable_summary={}", summary_path.display());
}

#[cfg(test)]
mod tests {
    use super::*;
    use serde_json::json;

    fn create_temp_dir(label: &str) -> PathBuf {
        let root = std::env::temp_dir()
            .join(format!("northstar-phase-m-{}-{}", label, std::process::id()))
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

    fn write_json(path: &Path, value: serde_json::Value) {
        if let Some(parent) = path.parent() {
            fs::create_dir_all(parent).unwrap();
        }
        fs::write(path, serde_json::to_vec_pretty(&value).unwrap()).unwrap();
    }

    fn ready_args(root: &Path) -> PhaseMArgs {
        let docs_root = root.join("docs");
        let target_root = root.join("target").join("northstar");
        let stage_root = target_root.join("phase-m-soak");

        write_json(
            &docs_root.join("runbooks").join("phase-m-canary-plan.json"),
            json!({
                "summary_version": 1,
                "phase": "phase_m_soak_canary",
                "environment_label": "remnawave-local-docker",
                "environment_kind": "local_supported_staging",
                "minimum_duration_seconds": 1,
                "stage_pause_seconds": 1,
                "rollback_command_refs": ["a", "b"],
                "baseline_refs": ["x"],
                "rollback_trigger_conditions": ["x"],
                "stages": [
                    {"stage_id":"canary_5","rollout_fraction_hint":"5%","rollback_required":true,"required_artifacts":["lifecycle-summary.json","rollback-summary.json","phase-l-summary.json"]},
                    {"stage_id":"canary_25","rollout_fraction_hint":"25%","rollback_required":true,"required_artifacts":["lifecycle-summary.json","rollback-summary.json","phase-l-summary.json"]},
                    {"stage_id":"canary_100","rollout_fraction_hint":"100%","rollback_required":true,"required_artifacts":["lifecycle-summary.json","rollback-summary.json","phase-l-summary.json"]}
                ]
            }),
        );
        write_json(
            &docs_root.join("development").join("phase-m-regression-ledger.json"),
            json!({
                "summary_version": 1,
                "phase": "phase_m_regression_burndown",
                "baseline_refs": ["x"],
                "severity_rules": [
                    {"severity":"p0","max_open":0,"description":"x"},
                    {"severity":"p1","max_open":0,"description":"x"},
                    {"severity":"p2","max_open":0,"description":"x"},
                    {"severity":"p3","max_open":999,"description":"x"}
                ],
                "open_regressions": [],
                "accepted_tail": [],
                "catastrophic_regression_blockers": ["x"]
            }),
        );
        write_json(
            &target_root.join("remnawave-supported-upstream-phase-i-signoff-summary.json"),
            json!({"verdict":"ready","phase_i_state":"honestly_complete"}),
        );
        write_json(
            &target_root.join("udp-wan-staging-interop-summary.json"),
            json!({
                "verdict":"ready",
                "source_lane":"wan_staging_interop",
                "all_profiles_passed":true,
                "transport_fallback_integrity_surface_passed":true,
                "degradation_path_visibility_passed":true,
                "artifact_retention_passed":true
            }),
        );

        for (index, stage) in ["canary_5", "canary_25", "canary_100"].iter().enumerate() {
            let dir = stage_root.join(stage);
            write_json(
                &dir.join("lifecycle-summary.json"),
                json!({
                    "verdict":"ready",
                    "supported_upstream_expected_lifecycle":"disabled",
                    "lifecycle_expected_state_passed":true,
                    "lifecycle_bridge_manifest_bootstrap_denied":true,
                    "lifecycle_bridge_manifest_refresh_denied":true,
                    "lifecycle_bridge_token_exchange_denied":true,
                    "webhook_positive_delivery_passed":true,
                    "webhook_duplicate_rejection_passed":true,
                    "webhook_reconcile_hint_passed":true,
                    "supported_upstream_lifecycle_passed":true
                }),
            );
            write_json(
                &dir.join("rollback-summary.json"),
                json!({
                    "verdict":"ready",
                    "artifact_root_present":true,
                    "profile_slugs":["udp-blocked"],
                    "failed_profile_slugs":[],
                    "degradation_path_visibility_passed":true,
                    "transport_fallback_integrity_surface_passed":true
                }),
            );
            write_json(
                &dir.join("phase-l-summary.json"),
                json!({
                    "verdict":"ready",
                    "phase_l_state":"honestly_complete",
                    "profile_disable_drill_passed":true,
                    "rollback_drill_passed":true,
                    "recovery_boundaries_documented":true,
                    "observability_mapping_documented":true
                }),
            );
            if index < 2 {
                std::thread::sleep(std::time::Duration::from_secs(1));
            }
        }

        PhaseMArgs {
            format: Some(OutputFormat::Json),
            summary_path: Some(target_root.join("phase-m-soak-canary-signoff-summary.json")),
            stage_root: Some(stage_root),
            canary_plan: Some(docs_root.join("runbooks").join("phase-m-canary-plan.json")),
            regression_ledger: Some(docs_root.join("development").join("phase-m-regression-ledger.json")),
            phase_i_summary: Some(target_root.join("remnawave-supported-upstream-phase-i-signoff-summary.json")),
            wan_staging_summary: Some(target_root.join("udp-wan-staging-interop-summary.json")),
        }
    }

    #[test]
    fn ready_summary_when_plan_baselines_and_stages_pass() {
        let root = create_temp_dir("ready");
        let args = ready_args(&root);
        let summary = build_summary(&args).unwrap();
        assert_eq!(summary.verdict, "ready");
        assert_eq!(summary.phase_m_state, "honestly_complete");
        assert!(summary.rollback_proven);
        assert_eq!(summary.stage_passed_count, 3);
    }

    #[test]
    fn blocks_when_stage_artifact_missing() {
        let root = create_temp_dir("missing-stage");
        let args = ready_args(&root);
        fs::remove_file(
            args.stage_root
                .as_ref()
                .unwrap()
                .join("canary_25")
                .join("rollback-summary.json"),
        )
        .unwrap();
        let summary = build_summary(&args).unwrap();
        assert_eq!(summary.verdict, "hold");
        assert_eq!(summary.stage_failed_count, 1);
        assert!(summary
            .missing_required_inputs
            .contains(&"canary_stage:canary_25".to_owned()));
    }

    #[test]
    fn blocks_when_p1_regression_is_open() {
        let root = create_temp_dir("open-p1");
        let args = ready_args(&root);
        write_json(
            args.regression_ledger.as_ref().unwrap(),
            json!({
                "summary_version": 1,
                "phase": "phase_m_regression_burndown",
                "baseline_refs": ["x"],
                "severity_rules": [
                    {"severity":"p0","max_open":0,"description":"x"},
                    {"severity":"p1","max_open":0,"description":"x"},
                    {"severity":"p2","max_open":0,"description":"x"},
                    {"severity":"p3","max_open":999,"description":"x"}
                ],
                "open_regressions": [{"severity":"p1","id":"REG-1","title":"blocking"}],
                "accepted_tail": [],
                "catastrophic_regression_blockers": ["x"]
            }),
        );
        let summary = build_summary(&args).unwrap();
        assert_eq!(summary.verdict, "hold");
        assert_eq!(summary.p1_open_count, 1);
        assert!(summary
            .blocking_reasons
            .contains(&"regression_p0_p1_open".to_owned()));
    }
}
