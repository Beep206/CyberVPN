use ns_testkit::{repo_root, summarize_rollout_gate_state};
use serde::{Deserialize, Serialize};
use std::collections::{BTreeMap, BTreeSet};
use std::env;
use std::fs;
use std::path::{Path, PathBuf};

const PHASE_L_OPERATOR_READINESS_SUMMARY_VERSION: u8 = 1;

const REQUIRED_INCIDENT_IDS: &[&str] = &[
    "upstream_outage",
    "bridge_auth_drift",
    "secret_rotation",
    "replay_cache_webhook",
    "profile_disable",
    "rollback",
];

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
enum OutputFormat {
    Text,
    Json,
}

#[derive(Debug, Default)]
struct PhaseLArgs {
    format: Option<OutputFormat>,
    summary_path: Option<PathBuf>,
    runbook_matrix: Option<PathBuf>,
    profile_disable_drill: Option<PathBuf>,
    rollback_drill: Option<PathBuf>,
}

#[derive(Debug, Deserialize)]
struct RecoveryMatrixInput {
    #[serde(default)]
    summary_version: Option<u8>,
    phase: String,
    #[serde(default)]
    shared_documents: Vec<String>,
    #[serde(default)]
    incidents: Vec<RecoveryIncidentInput>,
}

#[derive(Debug, Deserialize)]
struct RecoveryIncidentInput {
    incident_id: String,
    title: String,
    runbook_path: String,
    #[serde(default)]
    safe_state_actions: Vec<String>,
    #[serde(default)]
    operator_visible_signals: Vec<String>,
    #[serde(default)]
    escalation_triggers: Vec<String>,
    #[serde(default)]
    recoverable_artifacts: Vec<String>,
    #[serde(default)]
    nonrecoverable_artifacts: Vec<String>,
    requires_rotation: bool,
    requires_re_registration: bool,
    #[serde(default)]
    primary_commands: Vec<String>,
}

#[derive(Debug, Deserialize)]
struct ProfileDisableDrillInput {
    #[serde(default)]
    summary_version: Option<u8>,
    verdict: String,
    evidence_state: String,
    gate_state: String,
    gate_state_reason: String,
    supported_upstream_environment_present: bool,
    supported_upstream_expected_lifecycle: String,
    lifecycle_transition_observed: bool,
    lifecycle_expected_state_passed: bool,
    lifecycle_bridge_manifest_bootstrap_denied: bool,
    lifecycle_bridge_manifest_refresh_denied: bool,
    lifecycle_bridge_token_exchange_denied: bool,
    lifecycle_denial_code_passed: bool,
    webhook_positive_delivery_passed: bool,
    webhook_duplicate_rejection_passed: bool,
    webhook_reconcile_hint_passed: bool,
    supported_upstream_lifecycle_passed: bool,
}

#[derive(Debug, Deserialize)]
struct RollbackDrillInput {
    #[serde(default)]
    summary_version: Option<u8>,
    verdict: String,
    evidence_state: String,
    gate_state: String,
    gate_state_reason: String,
    source_lane: String,
    artifact_root_present: Option<bool>,
    profile_count: usize,
    #[serde(default)]
    profile_slugs: Vec<String>,
    #[serde(default)]
    failed_profile_slugs: Vec<String>,
    degradation_path_visibility_passed: bool,
    transport_fallback_integrity_surface_passed: bool,
}

#[derive(Debug)]
struct LoadedInput<T> {
    present: bool,
    parse_error: Option<String>,
    summary: Option<T>,
}

type LoadedRecoveryMatrixInput = LoadedInput<RecoveryMatrixInput>;
type LoadedProfileDisableDrillInput = LoadedInput<ProfileDisableDrillInput>;
type LoadedRollbackDrillInput = LoadedInput<RollbackDrillInput>;

#[derive(Debug, Serialize)]
struct PhaseLOperatorReadinessSummary {
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
    runbook_matrix_present: bool,
    runbook_matrix_passed: bool,
    shared_documents_present: bool,
    runbook_paths_present: bool,
    required_incident_ids_covered: bool,
    observability_mapping_documented: bool,
    recovery_boundaries_documented: bool,
    support_boundaries_documented: bool,
    profile_disable_drill_present: bool,
    profile_disable_drill_passed: bool,
    rollback_drill_present: bool,
    rollback_drill_passed: bool,
    rollback_degradation_path_visibility_passed: bool,
    rollback_transport_fallback_integrity_surface_passed: bool,
    profile_disable_expected_lifecycle: Option<String>,
    runbook_file_count: usize,
    shared_document_paths: Vec<String>,
    runbook_paths: Vec<String>,
    covered_incident_ids: Vec<String>,
    documented_rotation_required_incident_ids: Vec<String>,
    documented_re_registration_required_incident_ids: Vec<String>,
    missing_runbook_paths: Vec<String>,
    rollback_profile_slugs: Vec<String>,
    rollback_failed_profile_slugs: Vec<String>,
    phase_l_state: &'static str,
    blocking_reasons: Vec<String>,
    blocking_reason_keys: Vec<String>,
    blocking_reason_families: Vec<String>,
}

fn main() -> Result<(), Box<dyn std::error::Error>> {
    let args = parse_args(env::args().skip(1))?;
    let repo_root = repo_root();
    let summary = build_summary(
        &repo_root,
        load_input::<RecoveryMatrixInput>(
            args.runbook_matrix
                .unwrap_or_else(default_runbook_matrix_input)
                .as_path(),
        ),
        load_input::<ProfileDisableDrillInput>(
            args.profile_disable_drill
                .unwrap_or_else(default_profile_disable_drill_input)
                .as_path(),
        ),
        load_input::<RollbackDrillInput>(
            args.rollback_drill
                .unwrap_or_else(default_rollback_drill_input)
                .as_path(),
        ),
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
        return Err("phase l operator readiness signoff is not ready".into());
    }

    Ok(())
}

fn parse_args(
    arguments: impl IntoIterator<Item = String>,
) -> Result<PhaseLArgs, Box<dyn std::error::Error>> {
    let mut parsed = PhaseLArgs::default();
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
            "--runbook-matrix" => {
                let value = iter
                    .next()
                    .ok_or("--runbook-matrix requires a filesystem path")?;
                parsed.runbook_matrix = Some(PathBuf::from(value));
            }
            "--profile-disable-drill" => {
                let value = iter
                    .next()
                    .ok_or("--profile-disable-drill requires a filesystem path")?;
                parsed.profile_disable_drill = Some(PathBuf::from(value));
            }
            "--rollback-drill" => {
                let value = iter
                    .next()
                    .ok_or("--rollback-drill requires a filesystem path")?;
                parsed.rollback_drill = Some(PathBuf::from(value));
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

fn build_summary(
    repo_root: &Path,
    runbook_matrix: LoadedRecoveryMatrixInput,
    profile_disable_drill: LoadedProfileDisableDrillInput,
    rollback_drill: LoadedRollbackDrillInput,
) -> PhaseLOperatorReadinessSummary {
    let required_inputs = vec![
        "runbook_matrix".to_owned(),
        "profile_disable_drill".to_owned(),
        "rollback_drill".to_owned(),
    ];
    let considered_inputs = required_inputs.clone();
    let mut missing_required_inputs = Vec::new();
    let mut blocking_reasons = Vec::new();
    let mut blocking_reason_keys = Vec::new();
    let mut blocking_reason_families = Vec::new();
    let mut blocking_reason_key_counts = BTreeMap::new();
    let mut blocking_reason_family_counts = BTreeMap::new();

    let runbook_matrix_present = runbook_matrix.present && runbook_matrix.parse_error.is_none();
    let profile_disable_drill_present =
        profile_disable_drill.present && profile_disable_drill.parse_error.is_none();
    let rollback_drill_present = rollback_drill.present && rollback_drill.parse_error.is_none();

    if !runbook_matrix_present {
        missing_required_inputs.push("runbook_matrix".to_owned());
    }
    if !profile_disable_drill_present {
        missing_required_inputs.push("profile_disable_drill".to_owned());
    }
    if !rollback_drill_present {
        missing_required_inputs.push("rollback_drill".to_owned());
    }

    let mut shared_document_paths = Vec::new();
    let mut runbook_paths = Vec::new();
    let mut covered_incident_ids = Vec::new();
    let mut documented_rotation_required_incident_ids = Vec::new();
    let mut documented_re_registration_required_incident_ids = Vec::new();
    let mut missing_runbook_paths = Vec::new();

    let runbook_matrix_passed = runbook_matrix
        .summary
        .as_ref()
        .map(|summary| {
            let required_incident_ids = REQUIRED_INCIDENT_IDS
                .iter()
                .map(|value| (*value).to_owned())
                .collect::<BTreeSet<_>>();
            let covered_incident_id_set = summary
                .incidents
                .iter()
                .map(|incident| incident.incident_id.clone())
                .collect::<BTreeSet<_>>();
            let required_incident_ids_covered =
                required_incident_ids.is_subset(&covered_incident_id_set);

            shared_document_paths = summary.shared_documents.clone();
            shared_document_paths.sort();

            runbook_paths = summary
                .incidents
                .iter()
                .map(|incident| incident.runbook_path.clone())
                .collect::<BTreeSet<_>>()
                .into_iter()
                .collect::<Vec<_>>();
            runbook_paths.sort();

            covered_incident_ids = covered_incident_id_set.into_iter().collect::<Vec<_>>();

            documented_rotation_required_incident_ids = summary
                .incidents
                .iter()
                .filter(|incident| incident.requires_rotation)
                .map(|incident| incident.incident_id.clone())
                .collect::<Vec<_>>();
            documented_rotation_required_incident_ids.sort();

            documented_re_registration_required_incident_ids = summary
                .incidents
                .iter()
                .filter(|incident| incident.requires_re_registration)
                .map(|incident| incident.incident_id.clone())
                .collect::<Vec<_>>();
            documented_re_registration_required_incident_ids.sort();

            let shared_documents_present = summary.shared_documents.iter().all(|path| {
                let resolved = resolve_repo_relative_path(repo_root, path);
                let present = resolved.is_file();
                if !present {
                    missing_runbook_paths.push(path.clone());
                }
                present
            });
            let runbook_paths_present = summary.incidents.iter().all(|incident| {
                let resolved = resolve_repo_relative_path(repo_root, &incident.runbook_path);
                let present = resolved.is_file();
                if !present {
                    missing_runbook_paths.push(incident.runbook_path.clone());
                }
                present
            });
            let observability_mapping_documented = summary.incidents.iter().all(|incident| {
                !incident.title.trim().is_empty()
                    && !incident.safe_state_actions.is_empty()
                    && !incident.operator_visible_signals.is_empty()
                    && !incident.escalation_triggers.is_empty()
                    && !incident.primary_commands.is_empty()
            });
            let recovery_boundaries_documented = summary.incidents.iter().all(|incident| {
                !incident.recoverable_artifacts.is_empty()
                    && !incident.nonrecoverable_artifacts.is_empty()
            }) && !documented_rotation_required_incident_ids.is_empty()
                && !documented_re_registration_required_incident_ids.is_empty();
            let support_boundaries_documented = summary
                .shared_documents
                .iter()
                .any(|path| path == "docs/runbooks/RECOVERY_BOUNDARIES.md");

            summary.summary_version == Some(1)
                && summary.phase == "phase_l_operator_readiness"
                && required_incident_ids_covered
                && shared_documents_present
                && runbook_paths_present
                && observability_mapping_documented
                && recovery_boundaries_documented
                && support_boundaries_documented
        })
        .unwrap_or(false);

    let required_incident_ids_covered = REQUIRED_INCIDENT_IDS
        .iter()
        .all(|required_id| covered_incident_ids.iter().any(|value| value == required_id));
    let shared_documents_present = !shared_document_paths.is_empty()
        && shared_document_paths.iter().all(|path| {
            resolve_repo_relative_path(repo_root, path).is_file()
        });
    let runbook_paths_present =
        !runbook_paths.is_empty() && runbook_paths.iter().all(|path| {
            resolve_repo_relative_path(repo_root, path).is_file()
        });
    let observability_mapping_documented = runbook_matrix
        .summary
        .as_ref()
        .map(|summary| {
            summary.incidents.iter().all(|incident| {
                !incident.title.trim().is_empty()
                    && !incident.safe_state_actions.is_empty()
                    && !incident.operator_visible_signals.is_empty()
                    && !incident.escalation_triggers.is_empty()
                    && !incident.primary_commands.is_empty()
            })
        })
        .unwrap_or(false);
    let recovery_boundaries_documented = runbook_matrix
        .summary
        .as_ref()
        .map(|summary| {
            summary.incidents.iter().all(|incident| {
                !incident.recoverable_artifacts.is_empty()
                    && !incident.nonrecoverable_artifacts.is_empty()
            }) && !documented_rotation_required_incident_ids.is_empty()
                && !documented_re_registration_required_incident_ids.is_empty()
        })
        .unwrap_or(false);
    let support_boundaries_documented = shared_document_paths
        .iter()
        .any(|path| path == "docs/runbooks/RECOVERY_BOUNDARIES.md");

    missing_runbook_paths.sort();
    missing_runbook_paths.dedup();

    if runbook_matrix_present && !runbook_matrix_passed {
        record_blocking_reason(
            &mut blocking_reasons,
            &mut blocking_reason_keys,
            &mut blocking_reason_families,
            &mut blocking_reason_key_counts,
            &mut blocking_reason_family_counts,
            "phase_l_runbook_matrix_not_ready",
            "runbook_matrix_not_ready",
            "phase_l_inputs",
        );
    }

    let profile_disable_drill_passed = profile_disable_drill
        .summary
        .as_ref()
        .map(|summary| {
            summary.summary_version == Some(1)
                && summary.verdict == "ready"
                && summary.evidence_state == "verified"
                && summary.gate_state == "passed"
                && summary.gate_state_reason == "all_required_inputs_passed"
                && summary.supported_upstream_environment_present
                && summary.supported_upstream_lifecycle_passed
                && summary.lifecycle_transition_observed
                && summary.lifecycle_expected_state_passed
                && summary.lifecycle_bridge_manifest_bootstrap_denied
                && summary.lifecycle_bridge_manifest_refresh_denied
                && summary.lifecycle_bridge_token_exchange_denied
                && summary.lifecycle_denial_code_passed
                && summary.webhook_positive_delivery_passed
                && summary.webhook_duplicate_rejection_passed
                && summary.webhook_reconcile_hint_passed
        })
        .unwrap_or(false);
    if profile_disable_drill_present && !profile_disable_drill_passed {
        record_blocking_reason(
            &mut blocking_reasons,
            &mut blocking_reason_keys,
            &mut blocking_reason_families,
            &mut blocking_reason_key_counts,
            &mut blocking_reason_family_counts,
            "phase_l_profile_disable_drill_not_ready",
            "profile_disable_drill_not_ready",
            "phase_l_inputs",
        );
    }

    let rollback_drill_passed = rollback_drill
        .summary
        .as_ref()
        .map(|summary| {
            summary.summary_version == Some(1)
                && summary.verdict == "ready"
                && summary.evidence_state == "complete"
                && summary.gate_state == "pass"
                && summary.gate_state_reason == "all_required_inputs_passed"
                && summary.source_lane == "net_chaos_campaign"
                && summary.artifact_root_present == Some(true)
                && summary.profile_count == 1
                && summary.profile_slugs == vec!["udp-blocked".to_owned()]
                && summary.failed_profile_slugs.is_empty()
                && summary.degradation_path_visibility_passed
                && summary.transport_fallback_integrity_surface_passed
        })
        .unwrap_or(false);
    if rollback_drill_present && !rollback_drill_passed {
        record_blocking_reason(
            &mut blocking_reasons,
            &mut blocking_reason_keys,
            &mut blocking_reason_families,
            &mut blocking_reason_key_counts,
            &mut blocking_reason_family_counts,
            "phase_l_rollback_drill_not_ready",
            "rollback_drill_not_ready",
            "phase_l_inputs",
        );
    }

    let required_input_count = required_inputs.len();
    let required_input_missing_count = missing_required_inputs.len();
    let required_input_present_count =
        required_input_count.saturating_sub(required_input_missing_count);
    let required_input_passed_count = [
        runbook_matrix_passed,
        profile_disable_drill_passed,
        rollback_drill_passed,
    ]
    .into_iter()
    .filter(|passed| *passed)
    .count();
    let required_input_failed_count =
        required_input_present_count.saturating_sub(required_input_passed_count);
    let required_input_unready_count = 0usize;
    let all_required_inputs_present = required_input_missing_count == 0;
    let all_required_inputs_passed =
        all_required_inputs_present && required_input_failed_count == 0;
    let (gate_state_reason, gate_state_reason_family) = summarize_rollout_gate_state(
        required_input_missing_count,
        0,
        required_input_unready_count,
        0,
        blocking_reasons.len(),
    );
    let gate_state = if gate_state_reason == "all_required_inputs_passed" {
        "pass"
    } else {
        "hold"
    };
    let verdict = if gate_state == "pass" {
        "ready"
    } else {
        "hold"
    };
    let evidence_state = if required_input_missing_count > 0 {
        "missing_required_inputs"
    } else if blocking_reasons.is_empty() {
        "complete"
    } else {
        "degraded"
    };
    let phase_l_state = if verdict == "ready" {
        "honestly_complete"
    } else if required_input_missing_count > 0 {
        "missing_inputs"
    } else {
        "blocked"
    };

    let rollback_profile_slugs = rollback_drill
        .summary
        .as_ref()
        .map(|summary| summary.profile_slugs.clone())
        .unwrap_or_default();
    let rollback_failed_profile_slugs = rollback_drill
        .summary
        .as_ref()
        .map(|summary| summary.failed_profile_slugs.clone())
        .unwrap_or_default();
    let rollback_degradation_path_visibility_passed = rollback_drill
        .summary
        .as_ref()
        .map(|summary| summary.degradation_path_visibility_passed)
        .unwrap_or(false);
    let rollback_transport_fallback_integrity_surface_passed = rollback_drill
        .summary
        .as_ref()
        .map(|summary| summary.transport_fallback_integrity_surface_passed)
        .unwrap_or(false);
    let profile_disable_expected_lifecycle = profile_disable_drill
        .summary
        .as_ref()
        .map(|summary| summary.supported_upstream_expected_lifecycle.clone());

    let runbook_file_count = shared_document_paths
        .iter()
        .chain(runbook_paths.iter())
        .collect::<BTreeSet<_>>()
        .len();

    PhaseLOperatorReadinessSummary {
        summary_version: PHASE_L_OPERATOR_READINESS_SUMMARY_VERSION,
        verdict_family: "phase_l_operator_readiness_signoff",
        decision_scope: "phase_l",
        decision_label: "phase_l_operator_readiness_signoff",
        profile: "phase_l_operator_readiness",
        verdict,
        evidence_state,
        gate_state,
        gate_state_reason,
        gate_state_reason_family,
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
        blocking_reason_count: blocking_reasons.len(),
        blocking_reason_key_count: blocking_reason_key_counts.len(),
        blocking_reason_family_count: blocking_reason_family_counts.len(),
        blocking_reason_key_counts,
        blocking_reason_family_counts,
        runbook_matrix_present,
        runbook_matrix_passed,
        shared_documents_present,
        runbook_paths_present,
        required_incident_ids_covered,
        observability_mapping_documented,
        recovery_boundaries_documented,
        support_boundaries_documented,
        profile_disable_drill_present,
        profile_disable_drill_passed,
        rollback_drill_present,
        rollback_drill_passed,
        rollback_degradation_path_visibility_passed,
        rollback_transport_fallback_integrity_surface_passed,
        profile_disable_expected_lifecycle,
        runbook_file_count,
        shared_document_paths,
        runbook_paths,
        covered_incident_ids,
        documented_rotation_required_incident_ids,
        documented_re_registration_required_incident_ids,
        missing_runbook_paths,
        rollback_profile_slugs,
        rollback_failed_profile_slugs,
        phase_l_state,
        blocking_reasons,
        blocking_reason_keys,
        blocking_reason_families,
    }
}

fn load_input<T>(path: &Path) -> LoadedInput<T>
where
    T: for<'de> Deserialize<'de>,
{
    match fs::read(path) {
        Ok(bytes) => match serde_json::from_slice::<T>(&bytes) {
            Ok(summary) => LoadedInput {
                present: true,
                parse_error: None,
                summary: Some(summary),
            },
            Err(error) => LoadedInput {
                present: true,
                parse_error: Some(error.to_string()),
                summary: None,
            },
        },
        Err(_) => LoadedInput {
            present: false,
            parse_error: None,
            summary: None,
        },
    }
}

fn record_blocking_reason(
    blocking_reasons: &mut Vec<String>,
    blocking_reason_keys: &mut Vec<String>,
    blocking_reason_families: &mut Vec<String>,
    blocking_reason_key_counts: &mut BTreeMap<String, usize>,
    blocking_reason_family_counts: &mut BTreeMap<String, usize>,
    reason: &str,
    key: &str,
    family: &str,
) {
    blocking_reasons.push(reason.to_owned());
    blocking_reason_keys.push(key.to_owned());
    blocking_reason_families.push(family.to_owned());
    *blocking_reason_key_counts
        .entry(key.to_owned())
        .or_insert(0) += 1;
    *blocking_reason_family_counts
        .entry(family.to_owned())
        .or_insert(0) += 1;
}

fn resolve_repo_relative_path(repo_root: &Path, path: &str) -> PathBuf {
    let candidate = PathBuf::from(path);
    if candidate.is_absolute() {
        candidate
    } else {
        repo_root.join(candidate)
    }
}

fn default_summary_path() -> PathBuf {
    repo_root()
        .join("target")
        .join("northstar")
        .join("phase-l-operator-readiness-signoff-summary.json")
}

fn default_runbook_matrix_input() -> PathBuf {
    repo_root()
        .join("docs")
        .join("runbooks")
        .join("operator-recovery-matrix.json")
}

fn default_profile_disable_drill_input() -> PathBuf {
    repo_root()
        .join("target")
        .join("northstar")
        .join("remnawave-supported-upstream-lifecycle-summary.json")
}

fn default_rollback_drill_input() -> PathBuf {
    repo_root()
        .join("target")
        .join("northstar")
        .join("operator-rollout-rollback-drill-summary.json")
}

fn print_text_summary(summary: &PhaseLOperatorReadinessSummary, summary_path: &Path) {
    println!("Northstar Phase L operator readiness signoff summary:");
    println!("- verdict: {}", summary.verdict);
    println!("- phase_l_state: {}", summary.phase_l_state);
    println!("- gate_state_reason: {}", summary.gate_state_reason);
    println!("- runbook_matrix_passed: {}", summary.runbook_matrix_passed);
    println!(
        "- profile_disable_drill_passed: {}",
        summary.profile_disable_drill_passed
    );
    println!("- rollback_drill_passed: {}", summary.rollback_drill_passed);
    println!(
        "- recovery_boundaries_documented: {}",
        summary.recovery_boundaries_documented
    );
    println!(
        "- observability_mapping_documented: {}",
        summary.observability_mapping_documented
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

fn print_usage() {
    eprintln!(
        "Usage: cargo run -p ns-testkit --example phase_l_operator_readiness_signoff -- [--format text|json] [--summary-path <path>] [--runbook-matrix <path>] [--profile-disable-drill <path>] [--rollback-drill <path>]"
    );
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::time::{SystemTime, UNIX_EPOCH};

    fn loaded_matrix(summary: RecoveryMatrixInput) -> LoadedRecoveryMatrixInput {
        LoadedInput {
            present: true,
            parse_error: None,
            summary: Some(summary),
        }
    }

    fn loaded_profile(summary: ProfileDisableDrillInput) -> LoadedProfileDisableDrillInput {
        LoadedInput {
            present: true,
            parse_error: None,
            summary: Some(summary),
        }
    }

    fn loaded_rollback(summary: RollbackDrillInput) -> LoadedRollbackDrillInput {
        LoadedInput {
            present: true,
            parse_error: None,
            summary: Some(summary),
        }
    }

    fn ready_matrix() -> RecoveryMatrixInput {
        RecoveryMatrixInput {
            summary_version: Some(1),
            phase: "phase_l_operator_readiness".to_owned(),
            shared_documents: vec![
                "docs/runbooks/INDEX.md".to_owned(),
                "docs/runbooks/RECOVERY_BOUNDARIES.md".to_owned(),
            ],
            incidents: vec![
                incident("upstream_outage", "docs/runbooks/REMNAWAVE_UPSTREAM_OUTAGE.md", false, false),
                incident(
                    "bridge_auth_drift",
                    "docs/runbooks/BRIDGE_AUTH_DRIFT_AND_SECRET_ROTATION.md",
                    true,
                    false,
                ),
                incident(
                    "secret_rotation",
                    "docs/runbooks/BRIDGE_AUTH_DRIFT_AND_SECRET_ROTATION.md",
                    true,
                    false,
                ),
                incident(
                    "replay_cache_webhook",
                    "docs/runbooks/REPLAY_CACHE_AND_WEBHOOK_RECOVERY.md",
                    false,
                    false,
                ),
                incident(
                    "profile_disable",
                    "docs/runbooks/PROFILE_DISABLE_AND_ROLLBACK.md",
                    false,
                    true,
                ),
                incident(
                    "rollback",
                    "docs/runbooks/PROFILE_DISABLE_AND_ROLLBACK.md",
                    false,
                    false,
                ),
            ],
        }
    }

    fn incident(
        incident_id: &str,
        runbook_path: &str,
        requires_rotation: bool,
        requires_re_registration: bool,
    ) -> RecoveryIncidentInput {
        RecoveryIncidentInput {
            incident_id: incident_id.to_owned(),
            title: format!("Title for {incident_id}"),
            runbook_path: runbook_path.to_owned(),
            safe_state_actions: vec!["hold release".to_owned()],
            operator_visible_signals: vec!["signal".to_owned()],
            escalation_triggers: vec!["trigger".to_owned()],
            recoverable_artifacts: vec!["artifact".to_owned()],
            nonrecoverable_artifacts: vec!["nonrecoverable".to_owned()],
            requires_rotation,
            requires_re_registration,
            primary_commands: vec!["bash scripts/example.sh".to_owned()],
        }
    }

    fn ready_profile_disable() -> ProfileDisableDrillInput {
        ProfileDisableDrillInput {
            summary_version: Some(1),
            verdict: "ready".to_owned(),
            evidence_state: "verified".to_owned(),
            gate_state: "passed".to_owned(),
            gate_state_reason: "all_required_inputs_passed".to_owned(),
            supported_upstream_environment_present: true,
            supported_upstream_expected_lifecycle: "disabled".to_owned(),
            lifecycle_transition_observed: true,
            lifecycle_expected_state_passed: true,
            lifecycle_bridge_manifest_bootstrap_denied: true,
            lifecycle_bridge_manifest_refresh_denied: true,
            lifecycle_bridge_token_exchange_denied: true,
            lifecycle_denial_code_passed: true,
            webhook_positive_delivery_passed: true,
            webhook_duplicate_rejection_passed: true,
            webhook_reconcile_hint_passed: true,
            supported_upstream_lifecycle_passed: true,
        }
    }

    fn ready_rollback() -> RollbackDrillInput {
        RollbackDrillInput {
            summary_version: Some(1),
            verdict: "ready".to_owned(),
            evidence_state: "complete".to_owned(),
            gate_state: "pass".to_owned(),
            gate_state_reason: "all_required_inputs_passed".to_owned(),
            source_lane: "net_chaos_campaign".to_owned(),
            artifact_root_present: Some(true),
            profile_count: 1,
            profile_slugs: vec!["udp-blocked".to_owned()],
            failed_profile_slugs: Vec::new(),
            degradation_path_visibility_passed: true,
            transport_fallback_integrity_surface_passed: true,
        }
    }

    fn temp_repo_root() -> PathBuf {
        let unique = SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .expect("system time should be after unix epoch")
            .as_nanos();
        let root = std::env::temp_dir().join(format!("northstar-phase-l-{unique}"));
        fs::create_dir_all(root.join("docs").join("runbooks"))
            .expect("runbook directory should be creatable");
        for path in [
            "docs/runbooks/INDEX.md",
            "docs/runbooks/RECOVERY_BOUNDARIES.md",
            "docs/runbooks/REMNAWAVE_UPSTREAM_OUTAGE.md",
            "docs/runbooks/BRIDGE_AUTH_DRIFT_AND_SECRET_ROTATION.md",
            "docs/runbooks/REPLAY_CACHE_AND_WEBHOOK_RECOVERY.md",
            "docs/runbooks/PROFILE_DISABLE_AND_ROLLBACK.md",
        ] {
            fs::write(root.join(path), "# placeholder\n").expect("fixture runbook should write");
        }
        root
    }

    #[test]
    fn phase_l_signoff_is_ready_when_inputs_and_runbooks_pass() {
        let root = temp_repo_root();
        let summary = build_summary(
            &root,
            loaded_matrix(ready_matrix()),
            loaded_profile(ready_profile_disable()),
            loaded_rollback(ready_rollback()),
        );

        assert_eq!(summary.verdict, "ready");
        assert_eq!(summary.phase_l_state, "honestly_complete");
        assert!(summary.runbook_matrix_passed);
        assert!(summary.rollback_drill_passed);
    }

    #[test]
    fn phase_l_signoff_blocks_when_rollback_drill_is_not_ready() {
        let root = temp_repo_root();
        let mut rollback = ready_rollback();
        rollback.verdict = "hold".to_owned();
        rollback.gate_state = "hold".to_owned();
        rollback.gate_state_reason = "blocking_reasons_present".to_owned();
        rollback.failed_profile_slugs = vec!["udp-blocked".to_owned()];
        rollback.transport_fallback_integrity_surface_passed = false;

        let summary = build_summary(
            &root,
            loaded_matrix(ready_matrix()),
            loaded_profile(ready_profile_disable()),
            loaded_rollback(rollback),
        );

        assert_eq!(summary.verdict, "hold");
        assert_eq!(summary.phase_l_state, "blocked");
        assert!(
            summary
                .blocking_reasons
                .iter()
                .any(|value| value == "phase_l_rollback_drill_not_ready")
        );
    }

    #[test]
    fn phase_l_signoff_blocks_when_required_runbook_path_is_missing() {
        let root = temp_repo_root();
        fs::remove_file(root.join("docs/runbooks/PROFILE_DISABLE_AND_ROLLBACK.md"))
            .expect("fixture runbook should be removable");

        let summary = build_summary(
            &root,
            loaded_matrix(ready_matrix()),
            loaded_profile(ready_profile_disable()),
            loaded_rollback(ready_rollback()),
        );

        assert_eq!(summary.verdict, "hold");
        assert!(!summary.runbook_matrix_passed);
        assert!(
            summary
                .missing_runbook_paths
                .iter()
                .any(|value| value == "docs/runbooks/PROFILE_DISABLE_AND_ROLLBACK.md")
        );
    }
}
