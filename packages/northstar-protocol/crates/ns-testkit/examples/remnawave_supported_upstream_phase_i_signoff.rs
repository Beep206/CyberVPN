use ns_testkit::{repo_root, summarize_rollout_gate_state};
use serde::{Deserialize, Serialize};
use std::collections::BTreeMap;
use std::env;
use std::fs;
use std::io::ErrorKind;
use std::path::{Path, PathBuf};
#[cfg(test)]
use time::OffsetDateTime;

const PHASE_I_SIGNOFF_SCHEMA: &str = "supported_upstream_phase_i_operator_signoff";
const PHASE_I_SIGNOFF_SCHEMA_VERSION: u8 = 1;
const PHASE_I_SIGNOFF_VERDICT_FAMILY: &str = "supported_upstream_phase_i_signoff";
const PHASE_I_SIGNOFF_DECISION_SCOPE: &str = "supported_upstream_phase_i";
const PHASE_I_SIGNOFF_DECISION_LABEL: &str = "remnawave_supported_upstream_phase_i_signoff";
const PHASE_I_SIGNOFF_PROFILE: &str = "supported_upstream_phase_i_signoff";
const PHASE_I_SIGNOFF_SUMMARY_VERSION: u8 = 1;

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
enum OutputFormat {
    Text,
    Json,
}

#[derive(Debug, Default)]
struct PhaseISignoffArgs {
    format: Option<OutputFormat>,
    summary_path: Option<PathBuf>,
    deployment_label: Option<String>,
    upstream_summary_path: Option<PathBuf>,
    lifecycle_summary_path: Option<PathBuf>,
    deployment_reality_summary_path: Option<PathBuf>,
}

#[derive(Debug)]
struct ResolvedConfig {
    format: OutputFormat,
    summary_path: PathBuf,
    deployment_label: Option<String>,
    upstream_summary_path: PathBuf,
    lifecycle_summary_path: PathBuf,
    deployment_reality_summary_path: PathBuf,
}

#[derive(Debug, Default)]
struct SummaryState {
    missing_required_inputs: Vec<String>,
    blocking_reasons: Vec<String>,
    blocking_reason_key_counts: BTreeMap<String, usize>,
    blocking_reason_family_counts: BTreeMap<String, usize>,
    summary_contract_invalid_count: usize,
    required_input_unready_count: usize,
    degradation_hold_count: usize,
    successful_stage_count: usize,
    supported_upstream_environment_present: bool,
    supported_deployment_label_present: bool,
    prior_supported_upstream_summary_loaded: Option<bool>,
    prior_lifecycle_summary_loaded: Option<bool>,
    prior_deployment_reality_summary_loaded: Option<bool>,
    prior_supported_upstream_summary_passed: Option<bool>,
    prior_lifecycle_summary_passed: Option<bool>,
    prior_deployment_reality_summary_passed: Option<bool>,
    supported_upstream_base_url: Option<String>,
    supported_upstream_base_url_consistent: Option<bool>,
    supported_upstream_expected_account_id: Option<String>,
    supported_upstream_expected_account_id_consistent: Option<bool>,
    supported_upstream_version: Option<String>,
    supported_upstream_version_consistent: Option<bool>,
    control_plane_issuance_only_confirmed: Option<bool>,
    phase_i_operator_signoff_passed: Option<bool>,
    phase_i_honest_closure_recommended: Option<bool>,
    missing_environment_detected: bool,
    unsupported_upstream_version_detected: bool,
    upstream_auth_failure_detected: bool,
    upstream_timeout_detected: bool,
    response_shape_drift_detected: bool,
    webhook_signature_failure_detected: bool,
    lifecycle_drift_detected: bool,
    reconcile_lag_detected: bool,
    stale_snapshot_state_detected: bool,
    replay_sensitive_inconsistency_detected: bool,
    remote_store_auth_mismatch_detected: bool,
    remote_backend_unavailable_detected: bool,
    health_check_drift_detected: bool,
    startup_ordering_failure_detected: bool,
    partial_failover_detected: bool,
    missing_prior_lane_evidence_detected: bool,
    incompatible_contract_detected: bool,
}

#[derive(Debug, Serialize)]
struct SupportedUpstreamPhaseISignoffSummary {
    summary_version: u8,
    verification_schema: &'static str,
    verification_schema_version: u8,
    verdict_family: &'static str,
    decision_scope: &'static str,
    decision_label: &'static str,
    profile: &'static str,
    verdict: &'static str,
    evidence_state: &'static str,
    gate_state: &'static str,
    gate_state_reason: &'static str,
    gate_state_reason_family: &'static str,
    phase_i_state: &'static str,
    supported_deployment_label: Option<String>,
    supported_upstream_environment_present: bool,
    supported_upstream_base_url: Option<String>,
    supported_upstream_expected_account_id: Option<String>,
    supported_upstream_version: Option<String>,
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
    prior_supported_upstream_summary_path: String,
    prior_lifecycle_summary_path: String,
    prior_deployment_reality_summary_path: String,
    prior_supported_upstream_summary_loaded: Option<bool>,
    prior_lifecycle_summary_loaded: Option<bool>,
    prior_deployment_reality_summary_loaded: Option<bool>,
    prior_supported_upstream_summary_passed: Option<bool>,
    prior_lifecycle_summary_passed: Option<bool>,
    prior_deployment_reality_summary_passed: Option<bool>,
    supported_upstream_base_url_consistent: Option<bool>,
    supported_upstream_expected_account_id_consistent: Option<bool>,
    supported_upstream_version_consistent: Option<bool>,
    control_plane_issuance_only_confirmed: Option<bool>,
    phase_i_operator_signoff_passed: Option<bool>,
    phase_i_honest_closure_recommended: Option<bool>,
    missing_environment_detected: bool,
    unsupported_upstream_version_detected: bool,
    upstream_auth_failure_detected: bool,
    upstream_timeout_detected: bool,
    response_shape_drift_detected: bool,
    webhook_signature_failure_detected: bool,
    lifecycle_drift_detected: bool,
    reconcile_lag_detected: bool,
    stale_snapshot_state_detected: bool,
    replay_sensitive_inconsistency_detected: bool,
    remote_store_auth_mismatch_detected: bool,
    remote_backend_unavailable_detected: bool,
    health_check_drift_detected: bool,
    startup_ordering_failure_detected: bool,
    partial_failover_detected: bool,
    missing_prior_lane_evidence_detected: bool,
    incompatible_contract_detected: bool,
    blocking_reasons: Vec<String>,
    blocking_reason_keys: Vec<String>,
    blocking_reason_families: Vec<String>,
}

#[derive(Debug, Deserialize)]
struct PriorSummaryInput {
    gate_state: String,
    gate_state_reason: String,
    #[serde(default)]
    all_required_inputs_passed: bool,
    #[serde(default)]
    blocking_reason_keys: Vec<String>,
    #[serde(default)]
    supported_upstream_environment_present: bool,
    #[serde(default)]
    supported_upstream_base_url: Option<String>,
    #[serde(default)]
    supported_upstream_expected_account_id: Option<String>,
    #[serde(default)]
    upstream_source_version: Option<String>,
    #[serde(default)]
    supported_upstream_compatibility_passed: Option<bool>,
    #[serde(default)]
    supported_upstream_lifecycle_passed: Option<bool>,
    #[serde(default)]
    supported_upstream_deployment_reality_passed: Option<bool>,
    #[serde(default)]
    control_plane_issuance_only: Option<bool>,
}

#[derive(Clone, Copy)]
enum PriorSummaryKind {
    Upstream,
    Lifecycle,
    DeploymentReality,
}

impl PriorSummaryKind {
    fn input_label(self) -> &'static str {
        match self {
            Self::Upstream => "supported_upstream_summary_input",
            Self::Lifecycle => "supported_upstream_lifecycle_summary_input",
            Self::DeploymentReality => "supported_upstream_deployment_reality_summary_input",
        }
    }

    fn required_flag(self) -> &'static str {
        match self {
            Self::Upstream => "supported_upstream_compatibility_passed",
            Self::Lifecycle => "supported_upstream_lifecycle_passed",
            Self::DeploymentReality => "supported_upstream_deployment_reality_passed",
        }
    }
}

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    let args = parse_args(env::args().skip(1))?;
    let config = resolve_config(args);
    let summary = build_phase_i_signoff_summary(&config);

    if let Some(parent) = config.summary_path.parent() {
        fs::create_dir_all(parent)?;
    }
    fs::write(&config.summary_path, serde_json::to_vec_pretty(&summary)?)?;

    match config.format {
        OutputFormat::Text => print_text_summary(&summary, &config.summary_path),
        OutputFormat::Json => println!("{}", serde_json::to_string_pretty(&summary)?),
    }

    Ok(())
}

fn build_phase_i_signoff_summary(config: &ResolvedConfig) -> SupportedUpstreamPhaseISignoffSummary {
    let required_inputs = vec![
        "supported_deployment_label".to_owned(),
        "supported_upstream_summary_input".to_owned(),
        "supported_upstream_lifecycle_summary_input".to_owned(),
        "supported_upstream_deployment_reality_summary_input".to_owned(),
    ];
    let mut considered_inputs = required_inputs.clone();
    let mut state = SummaryState::default();

    if config
        .deployment_label
        .as_ref()
        .is_some_and(|label| !label.trim().is_empty())
    {
        state.supported_deployment_label_present = true;
    } else {
        state
            .missing_required_inputs
            .push("supported_deployment_label".to_owned());
    }

    let upstream = load_prior_summary_input(
        &config.upstream_summary_path,
        PriorSummaryKind::Upstream,
        &mut state,
    );
    let lifecycle = load_prior_summary_input(
        &config.lifecycle_summary_path,
        PriorSummaryKind::Lifecycle,
        &mut state,
    );
    let deployment = load_prior_summary_input(
        &config.deployment_reality_summary_path,
        PriorSummaryKind::DeploymentReality,
        &mut state,
    );

    considered_inputs.extend([
        "supported_upstream_summary_input".to_owned(),
        "supported_upstream_lifecycle_summary_input".to_owned(),
        "supported_upstream_deployment_reality_summary_input".to_owned(),
    ]);

    if let (Some(upstream), Some(lifecycle), Some(deployment)) =
        (upstream.as_ref(), lifecycle.as_ref(), deployment.as_ref())
    {
        state.supported_upstream_environment_present = upstream
            .supported_upstream_environment_present
            && lifecycle.supported_upstream_environment_present
            && deployment.supported_upstream_environment_present;
        if !state.supported_upstream_environment_present {
            state.missing_environment_detected = true;
            record_blocking_reason(
                &mut state,
                "missing_environment",
                "gating",
                "one or more prior supported-upstream lanes reported missing environment",
            );
        } else {
            evaluate_base_url_consistency(&mut state, upstream, lifecycle, deployment);
            evaluate_expected_account_id_consistency(&mut state, lifecycle, deployment);
            evaluate_version_consistency(&mut state, upstream, lifecycle, deployment);
        }
        evaluate_control_plane_scope(&mut state, deployment);
    }

    let signoff_passed = state.supported_deployment_label_present
        && state.prior_supported_upstream_summary_passed == Some(true)
        && state.prior_lifecycle_summary_passed == Some(true)
        && state.prior_deployment_reality_summary_passed == Some(true)
        && state.supported_upstream_environment_present
        && state.supported_upstream_base_url_consistent == Some(true)
        && state.supported_upstream_expected_account_id_consistent == Some(true)
        && state.supported_upstream_version_consistent == Some(true)
        && state.control_plane_issuance_only_confirmed == Some(true)
        && state.summary_contract_invalid_count == 0
        && state.required_input_unready_count == 0
        && state.degradation_hold_count == 0
        && state.missing_required_inputs.is_empty();
    state.phase_i_operator_signoff_passed = Some(signoff_passed);
    state.phase_i_honest_closure_recommended = Some(signoff_passed);

    let missing_required_input_count = state.missing_required_inputs.len();
    let blocking_reason_count = state.blocking_reasons.len();
    let (gate_state_reason, gate_state_reason_family) = summarize_rollout_gate_state(
        missing_required_input_count,
        state.summary_contract_invalid_count,
        state.required_input_unready_count,
        state.degradation_hold_count,
        blocking_reason_count,
    );
    let gate_state = if gate_state_reason_family == "ready" {
        "passed"
    } else {
        "blocked"
    };
    let verdict = if gate_state == "passed" {
        "ready"
    } else {
        "hold"
    };
    let evidence_state = if missing_required_input_count > 0 {
        "incomplete"
    } else if verdict == "ready" || state.successful_stage_count > 0 {
        "complete"
    } else {
        "partial"
    };
    let required_input_count = required_inputs.len();
    let required_input_present_count =
        required_input_count.saturating_sub(missing_required_input_count);
    let required_input_failed_count =
        usize::from(required_input_present_count > 0 && gate_state != "passed");
    let required_input_passed_count =
        required_input_present_count.saturating_sub(required_input_failed_count);
    let blocking_reason_keys = state
        .blocking_reason_key_counts
        .keys()
        .cloned()
        .collect::<Vec<_>>();
    let blocking_reason_families = state
        .blocking_reason_family_counts
        .keys()
        .cloned()
        .collect::<Vec<_>>();
    let phase_i_state = derive_phase_i_state(&state, verdict);

    SupportedUpstreamPhaseISignoffSummary {
        summary_version: PHASE_I_SIGNOFF_SUMMARY_VERSION,
        verification_schema: PHASE_I_SIGNOFF_SCHEMA,
        verification_schema_version: PHASE_I_SIGNOFF_SCHEMA_VERSION,
        verdict_family: PHASE_I_SIGNOFF_VERDICT_FAMILY,
        decision_scope: PHASE_I_SIGNOFF_DECISION_SCOPE,
        decision_label: PHASE_I_SIGNOFF_DECISION_LABEL,
        profile: PHASE_I_SIGNOFF_PROFILE,
        verdict,
        evidence_state,
        gate_state,
        gate_state_reason,
        gate_state_reason_family,
        phase_i_state,
        supported_deployment_label: config.deployment_label.clone(),
        supported_upstream_environment_present: state.supported_upstream_environment_present,
        supported_upstream_base_url: state.supported_upstream_base_url.clone(),
        supported_upstream_expected_account_id: state
            .supported_upstream_expected_account_id
            .clone(),
        supported_upstream_version: state.supported_upstream_version.clone(),
        required_inputs,
        considered_inputs,
        missing_required_inputs: state.missing_required_inputs,
        missing_required_input_count,
        required_input_count,
        required_input_missing_count: missing_required_input_count,
        required_input_failed_count,
        required_input_unready_count: state.required_input_unready_count,
        required_input_present_count,
        required_input_passed_count,
        all_required_inputs_present: missing_required_input_count == 0,
        all_required_inputs_passed: gate_state == "passed",
        blocking_reason_count,
        blocking_reason_key_count: blocking_reason_keys.len(),
        blocking_reason_family_count: blocking_reason_families.len(),
        blocking_reason_key_counts: state.blocking_reason_key_counts,
        blocking_reason_family_counts: state.blocking_reason_family_counts,
        prior_supported_upstream_summary_path: config.upstream_summary_path.display().to_string(),
        prior_lifecycle_summary_path: config.lifecycle_summary_path.display().to_string(),
        prior_deployment_reality_summary_path: config
            .deployment_reality_summary_path
            .display()
            .to_string(),
        prior_supported_upstream_summary_loaded: state.prior_supported_upstream_summary_loaded,
        prior_lifecycle_summary_loaded: state.prior_lifecycle_summary_loaded,
        prior_deployment_reality_summary_loaded: state.prior_deployment_reality_summary_loaded,
        prior_supported_upstream_summary_passed: state.prior_supported_upstream_summary_passed,
        prior_lifecycle_summary_passed: state.prior_lifecycle_summary_passed,
        prior_deployment_reality_summary_passed: state.prior_deployment_reality_summary_passed,
        supported_upstream_base_url_consistent: state.supported_upstream_base_url_consistent,
        supported_upstream_expected_account_id_consistent: state
            .supported_upstream_expected_account_id_consistent,
        supported_upstream_version_consistent: state.supported_upstream_version_consistent,
        control_plane_issuance_only_confirmed: state.control_plane_issuance_only_confirmed,
        phase_i_operator_signoff_passed: state.phase_i_operator_signoff_passed,
        phase_i_honest_closure_recommended: state.phase_i_honest_closure_recommended,
        missing_environment_detected: state.missing_environment_detected,
        unsupported_upstream_version_detected: state.unsupported_upstream_version_detected,
        upstream_auth_failure_detected: state.upstream_auth_failure_detected,
        upstream_timeout_detected: state.upstream_timeout_detected,
        response_shape_drift_detected: state.response_shape_drift_detected,
        webhook_signature_failure_detected: state.webhook_signature_failure_detected,
        lifecycle_drift_detected: state.lifecycle_drift_detected,
        reconcile_lag_detected: state.reconcile_lag_detected,
        stale_snapshot_state_detected: state.stale_snapshot_state_detected,
        replay_sensitive_inconsistency_detected: state.replay_sensitive_inconsistency_detected,
        remote_store_auth_mismatch_detected: state.remote_store_auth_mismatch_detected,
        remote_backend_unavailable_detected: state.remote_backend_unavailable_detected,
        health_check_drift_detected: state.health_check_drift_detected,
        startup_ordering_failure_detected: state.startup_ordering_failure_detected,
        partial_failover_detected: state.partial_failover_detected,
        missing_prior_lane_evidence_detected: state.missing_prior_lane_evidence_detected,
        incompatible_contract_detected: state.incompatible_contract_detected,
        blocking_reasons: state.blocking_reasons,
        blocking_reason_keys,
        blocking_reason_families,
    }
}

fn evaluate_base_url_consistency(
    state: &mut SummaryState,
    upstream: &PriorSummaryInput,
    lifecycle: &PriorSummaryInput,
    deployment: &PriorSummaryInput,
) {
    let values = [
        (
            "supported_upstream_summary_input",
            upstream.supported_upstream_base_url.clone(),
        ),
        (
            "supported_upstream_lifecycle_summary_input",
            lifecycle.supported_upstream_base_url.clone(),
        ),
        (
            "supported_upstream_deployment_reality_summary_input",
            deployment.supported_upstream_base_url.clone(),
        ),
    ];
    if values.iter().any(|(_, value)| value.is_none()) {
        state.supported_upstream_base_url_consistent = Some(false);
        state.incompatible_contract_detected = true;
        state.summary_contract_invalid_count += 1;
        record_blocking_reason(
            state,
            "incompatible_contract",
            "bridge_contract",
            "one or more prior summaries omitted supported_upstream_base_url",
        );
        return;
    }

    let first = values[0].1.clone().unwrap_or_default();
    let consistent = values
        .iter()
        .all(|(_, value)| value.as_ref() == Some(&first));
    state.supported_upstream_base_url = Some(first);
    state.supported_upstream_base_url_consistent = Some(consistent);
    if !consistent {
        state.incompatible_contract_detected = true;
        state.summary_contract_invalid_count += 1;
        record_blocking_reason(
            state,
            "incompatible_contract",
            "bridge_contract",
            "supported_upstream_base_url drifted across prior summaries",
        );
    }
}

fn evaluate_expected_account_id_consistency(
    state: &mut SummaryState,
    lifecycle: &PriorSummaryInput,
    deployment: &PriorSummaryInput,
) {
    match (
        lifecycle.supported_upstream_expected_account_id.clone(),
        deployment.supported_upstream_expected_account_id.clone(),
    ) {
        (Some(lifecycle_id), Some(deployment_id)) => {
            let consistent = lifecycle_id == deployment_id;
            state.supported_upstream_expected_account_id = Some(lifecycle_id);
            state.supported_upstream_expected_account_id_consistent = Some(consistent);
            if !consistent {
                state.incompatible_contract_detected = true;
                state.summary_contract_invalid_count += 1;
                record_blocking_reason(
                    state,
                    "incompatible_contract",
                    "bridge_contract",
                    "supported_upstream_expected_account_id drifted across lifecycle and deployment summaries",
                );
            }
        }
        _ => {
            state.supported_upstream_expected_account_id_consistent = Some(false);
            state.incompatible_contract_detected = true;
            state.summary_contract_invalid_count += 1;
            record_blocking_reason(
                state,
                "incompatible_contract",
                "bridge_contract",
                "lifecycle or deployment summary omitted supported_upstream_expected_account_id",
            );
        }
    }
}

fn evaluate_version_consistency(
    state: &mut SummaryState,
    upstream: &PriorSummaryInput,
    lifecycle: &PriorSummaryInput,
    deployment: &PriorSummaryInput,
) {
    let values = [
        (
            "supported_upstream_summary_input",
            upstream.upstream_source_version.clone(),
        ),
        (
            "supported_upstream_lifecycle_summary_input",
            lifecycle.upstream_source_version.clone(),
        ),
        (
            "supported_upstream_deployment_reality_summary_input",
            deployment.upstream_source_version.clone(),
        ),
    ];
    if values.iter().any(|(_, value)| value.is_none()) {
        state.supported_upstream_version_consistent = Some(false);
        state.incompatible_contract_detected = true;
        state.summary_contract_invalid_count += 1;
        record_blocking_reason(
            state,
            "incompatible_contract",
            "bridge_contract",
            "one or more prior summaries omitted upstream_source_version",
        );
        return;
    }

    let first = values[0].1.clone().unwrap_or_default();
    let consistent = values
        .iter()
        .all(|(_, value)| value.as_ref() == Some(&first));
    state.supported_upstream_version = Some(first);
    state.supported_upstream_version_consistent = Some(consistent);
    if !consistent {
        state.incompatible_contract_detected = true;
        state.summary_contract_invalid_count += 1;
        record_blocking_reason(
            state,
            "incompatible_contract",
            "bridge_contract",
            "upstream_source_version drifted across prior summaries",
        );
    }
}

fn evaluate_control_plane_scope(state: &mut SummaryState, deployment: &PriorSummaryInput) {
    let confirmed = deployment.control_plane_issuance_only == Some(true);
    state.control_plane_issuance_only_confirmed = Some(confirmed);
    if !confirmed {
        state.incompatible_contract_detected = true;
        state.summary_contract_invalid_count += 1;
        record_blocking_reason(
            state,
            "incompatible_contract",
            "bridge_contract",
            "deployment-reality summary no longer declares control_plane_issuance_only = true",
        );
    }
}

fn derive_phase_i_state(state: &SummaryState, verdict: &str) -> &'static str {
    if !state.supported_deployment_label_present || !state.missing_required_inputs.is_empty() {
        if state.missing_prior_lane_evidence_detected {
            "missing_prior_lane_evidence"
        } else {
            "missing_required_inputs"
        }
    } else if !state.supported_upstream_environment_present {
        "missing_environment"
    } else if state.summary_contract_invalid_count > 0 {
        "contract_invalid"
    } else if state.required_input_unready_count > 0 {
        "required_input_unready"
    } else if state.degradation_hold_count > 0 {
        "degraded"
    } else if verdict == "ready" {
        "honestly_complete"
    } else {
        "blocked"
    }
}

fn load_prior_summary_input(
    path: &Path,
    kind: PriorSummaryKind,
    state: &mut SummaryState,
) -> Option<PriorSummaryInput> {
    let contents = match fs::read_to_string(path) {
        Ok(contents) => contents,
        Err(error) => {
            if error.kind() == ErrorKind::NotFound {
                state
                    .missing_required_inputs
                    .push(kind.input_label().to_owned());
                state.missing_prior_lane_evidence_detected = true;
            } else {
                state.summary_contract_invalid_count += 1;
                record_blocking_reason(
                    state,
                    "summary_contract_invalid",
                    "summary_contract",
                    format!("failed to read {}: {error}", kind.input_label()),
                );
            }
            return None;
        }
    };

    let summary: PriorSummaryInput = match serde_json::from_str(&contents) {
        Ok(summary) => summary,
        Err(error) => {
            state.summary_contract_invalid_count += 1;
            record_blocking_reason(
                state,
                "summary_contract_invalid",
                "summary_contract",
                format!("failed to parse {}: {error}", kind.input_label()),
            );
            return None;
        }
    };

    match kind {
        PriorSummaryKind::Upstream => state.prior_supported_upstream_summary_loaded = Some(true),
        PriorSummaryKind::Lifecycle => state.prior_lifecycle_summary_loaded = Some(true),
        PriorSummaryKind::DeploymentReality => {
            state.prior_deployment_reality_summary_loaded = Some(true)
        }
    }

    for key in &summary.blocking_reason_keys {
        project_prior_reason_key(state, key);
    }

    let specific_passed = match kind.required_flag() {
        "supported_upstream_compatibility_passed" => {
            summary.supported_upstream_compatibility_passed == Some(true)
        }
        "supported_upstream_lifecycle_passed" => {
            summary.supported_upstream_lifecycle_passed == Some(true)
        }
        "supported_upstream_deployment_reality_passed" => {
            summary.supported_upstream_deployment_reality_passed == Some(true)
        }
        _ => false,
    };
    let input_passed =
        summary.gate_state == "passed" && summary.all_required_inputs_passed && specific_passed;

    match kind {
        PriorSummaryKind::Upstream => {
            state.prior_supported_upstream_summary_passed = Some(input_passed)
        }
        PriorSummaryKind::Lifecycle => state.prior_lifecycle_summary_passed = Some(input_passed),
        PriorSummaryKind::DeploymentReality => {
            state.prior_deployment_reality_summary_passed = Some(input_passed)
        }
    }

    if input_passed {
        state.successful_stage_count += 1;
    } else {
        state.required_input_unready_count += 1;
        record_blocking_reason(
            state,
            "required_inputs_unready",
            "gating",
            format!(
                "{} gate_state={} reason={}",
                kind.input_label(),
                summary.gate_state,
                summary.gate_state_reason
            ),
        );
    }

    Some(summary)
}

fn project_prior_reason_key(state: &mut SummaryState, key: &str) {
    match key {
        "unsupported_upstream_version" => state.unsupported_upstream_version_detected = true,
        "upstream_auth_failure" => state.upstream_auth_failure_detected = true,
        "upstream_timeout" => state.upstream_timeout_detected = true,
        "response_shape_drift" => state.response_shape_drift_detected = true,
        "webhook_signature_failure" => state.webhook_signature_failure_detected = true,
        "lifecycle_drift" => state.lifecycle_drift_detected = true,
        "reconcile_lag_exceeded" => state.reconcile_lag_detected = true,
        "stale_snapshot_state" => state.stale_snapshot_state_detected = true,
        "replay_sensitive_inconsistency" => state.replay_sensitive_inconsistency_detected = true,
        "remote_store_auth_mismatch" => state.remote_store_auth_mismatch_detected = true,
        "remote_backend_unavailable" => state.remote_backend_unavailable_detected = true,
        "health_check_drift" => state.health_check_drift_detected = true,
        "startup_ordering_failure" => state.startup_ordering_failure_detected = true,
        "partial_failover" => state.partial_failover_detected = true,
        "incompatible_contract" => state.incompatible_contract_detected = true,
        _ => {}
    }
}

fn record_blocking_reason(
    state: &mut SummaryState,
    key: &str,
    family: &str,
    detail: impl Into<String>,
) {
    *state
        .blocking_reason_key_counts
        .entry(key.to_owned())
        .or_insert(0) += 1;
    *state
        .blocking_reason_family_counts
        .entry(family.to_owned())
        .or_insert(0) += 1;
    state
        .blocking_reasons
        .push(format!("{key}: {}", detail.into()));
}

fn parse_args<I>(args: I) -> Result<PhaseISignoffArgs, Box<dyn std::error::Error>>
where
    I: IntoIterator<Item = String>,
{
    let mut parsed = PhaseISignoffArgs::default();
    let mut iter = args.into_iter();
    while let Some(argument) = iter.next() {
        match argument.as_str() {
            "--json" => parsed.format = Some(OutputFormat::Json),
            "--text" => parsed.format = Some(OutputFormat::Text),
            "--summary-path" => {
                parsed.summary_path = Some(PathBuf::from(next_value(&mut iter, "--summary-path")?));
            }
            "--deployment-label" => {
                parsed.deployment_label = Some(next_value(&mut iter, "--deployment-label")?)
            }
            "--upstream-summary-path" => {
                parsed.upstream_summary_path = Some(PathBuf::from(next_value(
                    &mut iter,
                    "--upstream-summary-path",
                )?));
            }
            "--lifecycle-summary-path" => {
                parsed.lifecycle_summary_path = Some(PathBuf::from(next_value(
                    &mut iter,
                    "--lifecycle-summary-path",
                )?));
            }
            "--deployment-reality-summary-path" => {
                parsed.deployment_reality_summary_path = Some(PathBuf::from(next_value(
                    &mut iter,
                    "--deployment-reality-summary-path",
                )?));
            }
            flag => return Err(format!("unrecognized argument: {flag}").into()),
        }
    }
    Ok(parsed)
}

fn next_value<I>(iter: &mut I, flag: &str) -> Result<String, Box<dyn std::error::Error>>
where
    I: Iterator<Item = String>,
{
    iter.next()
        .ok_or_else(|| format!("expected a value after {flag}").into())
}

fn resolve_config(args: PhaseISignoffArgs) -> ResolvedConfig {
    ResolvedConfig {
        format: args.format.unwrap_or(OutputFormat::Text),
        summary_path: args
            .summary_path
            .or_else(|| {
                env::var("NORTHSTAR_REMNAWAVE_SUPPORTED_UPSTREAM_PHASE_I_SIGNOFF_SUMMARY_PATH")
                    .ok()
                    .map(PathBuf::from)
            })
            .unwrap_or_else(default_summary_path),
        deployment_label: env_override(
            args.deployment_label,
            "NORTHSTAR_REMNAWAVE_SUPPORTED_UPSTREAM_DEPLOYMENT_LABEL",
        ),
        upstream_summary_path: args
            .upstream_summary_path
            .or_else(|| {
                env::var("NORTHSTAR_REMNAWAVE_SUPPORTED_UPSTREAM_SUMMARY_INPUT_PATH")
                    .ok()
                    .map(PathBuf::from)
            })
            .unwrap_or_else(default_supported_upstream_summary_path),
        lifecycle_summary_path: args
            .lifecycle_summary_path
            .or_else(|| {
                env::var("NORTHSTAR_REMNAWAVE_SUPPORTED_UPSTREAM_LIFECYCLE_SUMMARY_INPUT_PATH")
                    .ok()
                    .map(PathBuf::from)
            })
            .unwrap_or_else(default_lifecycle_summary_path),
        deployment_reality_summary_path: args
            .deployment_reality_summary_path
            .or_else(|| {
                env::var(
                    "NORTHSTAR_REMNAWAVE_SUPPORTED_UPSTREAM_DEPLOYMENT_REALITY_SUMMARY_INPUT_PATH",
                )
                .ok()
                .map(PathBuf::from)
            })
            .unwrap_or_else(default_deployment_reality_summary_path),
    }
}

fn env_override(current: Option<String>, key: &str) -> Option<String> {
    current.or_else(|| env::var(key).ok()).and_then(|value| {
        if value.trim().is_empty() {
            None
        } else {
            Some(value)
        }
    })
}

fn print_text_summary(summary: &SupportedUpstreamPhaseISignoffSummary, summary_path: &Path) {
    println!("Northstar Supported Upstream Phase I Operator Signoff");
    println!("- verdict: {}", summary.verdict);
    println!("- gate_state: {}", summary.gate_state);
    println!("- gate_state_reason: {}", summary.gate_state_reason);
    println!("- phase_i_state: {}", summary.phase_i_state);
    println!(
        "- phase_i_honest_closure_recommended: {:?}",
        summary.phase_i_honest_closure_recommended
    );
    println!(
        "- prior_supported_upstream_summary_passed: {:?}",
        summary.prior_supported_upstream_summary_passed
    );
    println!(
        "- prior_lifecycle_summary_passed: {:?}",
        summary.prior_lifecycle_summary_passed
    );
    println!(
        "- prior_deployment_reality_summary_passed: {:?}",
        summary.prior_deployment_reality_summary_passed
    );
    println!(
        "- control_plane_issuance_only_confirmed: {:?}",
        summary.control_plane_issuance_only_confirmed
    );
    println!(
        "- supported_upstream_environment_present: {}",
        summary.supported_upstream_environment_present
    );
    println!("- summary_path: {}", summary_path.display());
}

fn default_summary_path() -> PathBuf {
    repo_root()
        .join("target")
        .join("northstar")
        .join("remnawave-supported-upstream-phase-i-signoff-summary.json")
}

fn default_supported_upstream_summary_path() -> PathBuf {
    repo_root()
        .join("target")
        .join("northstar")
        .join("remnawave-supported-upstream-summary.json")
}

fn default_lifecycle_summary_path() -> PathBuf {
    repo_root()
        .join("target")
        .join("northstar")
        .join("remnawave-supported-upstream-lifecycle-summary.json")
}

fn default_deployment_reality_summary_path() -> PathBuf {
    repo_root()
        .join("target")
        .join("northstar")
        .join("remnawave-supported-upstream-deployment-reality-summary.json")
}

#[cfg(test)]
fn unique_test_path(prefix: &str, suffix: &str) -> PathBuf {
    repo_root().join("target").join("northstar").join(format!(
        "{prefix}-{}-{}.{}",
        std::process::id(),
        OffsetDateTime::now_utc().unix_timestamp_nanos(),
        suffix
    ))
}

#[cfg(test)]
mod tests {
    use super::*;
    use serde_json::json;

    fn write_summary(path: &Path, value: serde_json::Value) {
        if let Some(parent) = path.parent() {
            fs::create_dir_all(parent).expect("create test summary dir");
        }
        fs::write(
            path,
            serde_json::to_vec_pretty(&value).expect("serialize summary"),
        )
        .expect("write test summary");
    }

    fn ready_summary(kind: PriorSummaryKind) -> serde_json::Value {
        let mut value = json!({
            "gate_state": "passed",
            "gate_state_reason": "ready",
            "all_required_inputs_passed": true,
            "blocking_reason_keys": [],
            "supported_upstream_environment_present": true,
            "supported_upstream_base_url": "https://supported.example",
            "upstream_source_version": "2.7.4"
        });

        match kind {
            PriorSummaryKind::Upstream => {
                value["supported_upstream_compatibility_passed"] = json!(true);
            }
            PriorSummaryKind::Lifecycle => {
                value["supported_upstream_lifecycle_passed"] = json!(true);
                value["supported_upstream_expected_account_id"] = json!("acct-1");
            }
            PriorSummaryKind::DeploymentReality => {
                value["supported_upstream_deployment_reality_passed"] = json!(true);
                value["supported_upstream_expected_account_id"] = json!("acct-1");
                value["control_plane_issuance_only"] = json!(true);
            }
        }

        value
    }

    #[test]
    fn phase_i_signoff_is_ready_for_consistent_supported_deployment_inputs() {
        let upstream_path = unique_test_path("phase-i-upstream", "json");
        let lifecycle_path = unique_test_path("phase-i-lifecycle", "json");
        let deployment_path = unique_test_path("phase-i-deployment", "json");
        write_summary(&upstream_path, ready_summary(PriorSummaryKind::Upstream));
        write_summary(&lifecycle_path, ready_summary(PriorSummaryKind::Lifecycle));
        write_summary(
            &deployment_path,
            ready_summary(PriorSummaryKind::DeploymentReality),
        );

        let summary = build_phase_i_signoff_summary(&ResolvedConfig {
            format: OutputFormat::Json,
            summary_path: unique_test_path("phase-i-signoff", "json"),
            deployment_label: Some("supported-panel-eu-1".to_owned()),
            upstream_summary_path: upstream_path,
            lifecycle_summary_path: lifecycle_path,
            deployment_reality_summary_path: deployment_path,
        });

        assert_eq!(summary.gate_state, "passed", "{summary:#?}");
        assert_eq!(summary.verdict, "ready");
        assert_eq!(summary.phase_i_state, "honestly_complete");
        assert_eq!(summary.phase_i_operator_signoff_passed, Some(true));
        assert_eq!(summary.phase_i_honest_closure_recommended, Some(true));
        assert_eq!(summary.control_plane_issuance_only_confirmed, Some(true));
        assert_eq!(summary.supported_upstream_base_url_consistent, Some(true));
        assert_eq!(
            summary.supported_upstream_expected_account_id_consistent,
            Some(true)
        );
        assert_eq!(summary.supported_upstream_version_consistent, Some(true));
    }

    #[test]
    fn phase_i_signoff_holds_when_environment_is_missing() {
        let upstream_path = unique_test_path("phase-i-upstream-missing-env", "json");
        let lifecycle_path = unique_test_path("phase-i-lifecycle-missing-env", "json");
        let deployment_path = unique_test_path("phase-i-deployment-missing-env", "json");
        write_summary(
            &upstream_path,
            json!({
                "gate_state": "blocked",
                "gate_state_reason": "missing_required_inputs",
                "all_required_inputs_passed": false,
                "blocking_reason_keys": [],
                "supported_upstream_environment_present": false,
                "supported_upstream_base_url": "https://supported.example",
                "upstream_source_version": "2.7.4",
                "supported_upstream_compatibility_passed": null
            }),
        );
        write_summary(
            &lifecycle_path,
            json!({
                "gate_state": "blocked",
                "gate_state_reason": "missing_required_inputs",
                "all_required_inputs_passed": false,
                "blocking_reason_keys": [],
                "supported_upstream_environment_present": false,
                "supported_upstream_base_url": "https://supported.example",
                "supported_upstream_expected_account_id": "acct-1",
                "upstream_source_version": "2.7.4",
                "supported_upstream_lifecycle_passed": null
            }),
        );
        write_summary(
            &deployment_path,
            json!({
                "gate_state": "blocked",
                "gate_state_reason": "missing_required_inputs",
                "all_required_inputs_passed": false,
                "blocking_reason_keys": [],
                "supported_upstream_environment_present": false,
                "supported_upstream_base_url": "https://supported.example",
                "supported_upstream_expected_account_id": "acct-1",
                "upstream_source_version": "2.7.4",
                "supported_upstream_deployment_reality_passed": null,
                "control_plane_issuance_only": true
            }),
        );

        let summary = build_phase_i_signoff_summary(&ResolvedConfig {
            format: OutputFormat::Json,
            summary_path: unique_test_path("phase-i-signoff-missing-env", "json"),
            deployment_label: Some("supported-panel-eu-1".to_owned()),
            upstream_summary_path: upstream_path,
            lifecycle_summary_path: lifecycle_path,
            deployment_reality_summary_path: deployment_path,
        });

        assert_eq!(summary.gate_state, "blocked");
        assert_eq!(summary.verdict, "hold");
        assert_eq!(summary.phase_i_state, "missing_environment");
        assert_eq!(summary.phase_i_operator_signoff_passed, Some(false));
        assert_eq!(summary.phase_i_honest_closure_recommended, Some(false));
        assert_eq!(summary.missing_environment_detected, true);
        assert_eq!(summary.required_input_unready_count, 3);
    }

    #[test]
    fn phase_i_signoff_holds_when_deployment_label_is_missing() {
        let upstream_path = unique_test_path("phase-i-upstream-missing-label", "json");
        let lifecycle_path = unique_test_path("phase-i-lifecycle-missing-label", "json");
        let deployment_path = unique_test_path("phase-i-deployment-missing-label", "json");
        write_summary(&upstream_path, ready_summary(PriorSummaryKind::Upstream));
        write_summary(&lifecycle_path, ready_summary(PriorSummaryKind::Lifecycle));
        write_summary(
            &deployment_path,
            ready_summary(PriorSummaryKind::DeploymentReality),
        );

        let summary = build_phase_i_signoff_summary(&ResolvedConfig {
            format: OutputFormat::Json,
            summary_path: unique_test_path("phase-i-signoff-missing-label", "json"),
            deployment_label: None,
            upstream_summary_path: upstream_path,
            lifecycle_summary_path: lifecycle_path,
            deployment_reality_summary_path: deployment_path,
        });

        assert_eq!(summary.gate_state, "blocked");
        assert_eq!(summary.phase_i_state, "missing_required_inputs");
        assert_eq!(
            summary
                .missing_required_inputs
                .contains(&"supported_deployment_label".to_owned()),
            true
        );
    }

    #[test]
    fn phase_i_signoff_holds_when_prior_summary_is_missing() {
        let upstream_path = unique_test_path("phase-i-upstream-missing-prior", "json");
        let lifecycle_path = unique_test_path("phase-i-lifecycle-missing-prior", "json");
        let deployment_path = unique_test_path("phase-i-deployment-missing-prior", "json");
        write_summary(&upstream_path, ready_summary(PriorSummaryKind::Upstream));
        write_summary(&lifecycle_path, ready_summary(PriorSummaryKind::Lifecycle));

        let summary = build_phase_i_signoff_summary(&ResolvedConfig {
            format: OutputFormat::Json,
            summary_path: unique_test_path("phase-i-signoff-missing-prior", "json"),
            deployment_label: Some("supported-panel-eu-1".to_owned()),
            upstream_summary_path: upstream_path,
            lifecycle_summary_path: lifecycle_path,
            deployment_reality_summary_path: deployment_path,
        });

        assert_eq!(summary.gate_state, "blocked");
        assert_eq!(summary.phase_i_state, "missing_prior_lane_evidence");
        assert_eq!(summary.missing_prior_lane_evidence_detected, true);
    }

    #[test]
    fn phase_i_signoff_holds_when_control_plane_scope_drifts() {
        let upstream_path = unique_test_path("phase-i-upstream-scope-drift", "json");
        let lifecycle_path = unique_test_path("phase-i-lifecycle-scope-drift", "json");
        let deployment_path = unique_test_path("phase-i-deployment-scope-drift", "json");
        write_summary(&upstream_path, ready_summary(PriorSummaryKind::Upstream));
        write_summary(&lifecycle_path, ready_summary(PriorSummaryKind::Lifecycle));
        let mut deployment_summary = ready_summary(PriorSummaryKind::DeploymentReality);
        deployment_summary["control_plane_issuance_only"] = json!(false);
        write_summary(&deployment_path, deployment_summary);

        let summary = build_phase_i_signoff_summary(&ResolvedConfig {
            format: OutputFormat::Json,
            summary_path: unique_test_path("phase-i-signoff-scope-drift", "json"),
            deployment_label: Some("supported-panel-eu-1".to_owned()),
            upstream_summary_path: upstream_path,
            lifecycle_summary_path: lifecycle_path,
            deployment_reality_summary_path: deployment_path,
        });

        assert_eq!(summary.gate_state, "blocked");
        assert_eq!(summary.phase_i_state, "contract_invalid");
        assert_eq!(summary.control_plane_issuance_only_confirmed, Some(false));
        assert_eq!(summary.incompatible_contract_detected, true);
    }
}
