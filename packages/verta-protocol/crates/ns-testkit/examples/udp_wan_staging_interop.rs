use ns_testkit::{
    UDP_INTEROP_PROFILE_CATALOG_SOURCE_LANE_WAN_STAGING, UdpWanLabCommandKind, repo_root,
    summarize_rollout_gate_state, udp_wan_lab_profile_by_slug, udp_wan_lab_profiles,
};
use serde::Serialize;
use std::collections::BTreeMap;
use std::env;
use std::fs;
use std::path::{Path, PathBuf};
use std::process::Command;
use std::time::Instant;

const UDP_WAN_STAGING_VERIFICATION_SCHEMA: &str = "udp_wan_staging_operator_verdict";
const UDP_WAN_STAGING_VERIFICATION_SCHEMA_VERSION: u8 = 1;
const UDP_WAN_STAGING_VERDICT_FAMILY: &str = "udp_wan_staging_interop";
const UDP_WAN_STAGING_DECISION_SCOPE: &str = "udp_wan_staging";
const UDP_WAN_STAGING_DECISION_LABEL: &str = "udp_wan_staging_interop";
const UDP_WAN_STAGING_PROFILE: &str = "wan_staging_interop";
const UDP_WAN_STAGING_SUMMARY_VERSION: u8 = 1;

const ROLE_PAIR_CANDIDATE_CLIENT_BASELINE_GATEWAY: &str =
    "candidate_client_against_baseline_gateway";
const ROLE_PAIR_BASELINE_CLIENT_CANDIDATE_GATEWAY: &str =
    "baseline_client_against_candidate_gateway";
const ROLE_PAIR_CANDIDATE_CLIENT_CANDIDATE_GATEWAY: &str =
    "candidate_client_against_candidate_gateway";

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
enum OutputFormat {
    Text,
    Json,
}

#[derive(Debug, Default)]
struct WanInteropArgs {
    profiles: Vec<String>,
    run_all: bool,
    format: Option<OutputFormat>,
    summary_path: Option<PathBuf>,
    deployment_label: Option<String>,
    host_label: Option<String>,
    candidate_revision: Option<String>,
    peer_revision: Option<String>,
    role_pair: Option<String>,
    artifact_root: Option<PathBuf>,
    qlog_path: Option<PathBuf>,
    packet_capture_path: Option<PathBuf>,
}

#[derive(Debug)]
struct ResolvedConfig {
    selected_profiles: Vec<&'static ns_testkit::UdpWanLabProfile>,
    format: OutputFormat,
    summary_path: PathBuf,
    deployment_label: Option<String>,
    host_label: Option<String>,
    candidate_revision: Option<String>,
    peer_revision: Option<String>,
    role_pair: Option<String>,
    artifact_root: Option<PathBuf>,
    qlog_path: Option<PathBuf>,
    packet_capture_path: Option<PathBuf>,
}

#[derive(Debug, Clone, Serialize)]
struct UdpWanStagingProfileResult {
    slug: String,
    spec_suite_ids: Vec<String>,
    command_kind: String,
    command_selector: String,
    requires_no_silent_fallback: bool,
    status: &'static str,
    exit_code: Option<i32>,
    duration_ms: u128,
    command: Vec<String>,
    error_detail: Option<String>,
}

#[derive(Debug, Serialize)]
struct UdpWanStagingInteropSummary {
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
    degradation_hold_count: usize,
    deployment_label: Option<String>,
    host_label: Option<String>,
    candidate_revision: Option<String>,
    peer_revision: Option<String>,
    broader_than_same_revision_passed: Option<bool>,
    role_pair: Option<String>,
    role_pair_valid: Option<bool>,
    evidence_lane: &'static str,
    source_lane: &'static str,
    artifact_root: Option<String>,
    artifact_root_present: Option<bool>,
    qlog_path: Option<String>,
    qlog_artifact_present: Option<bool>,
    packet_capture_path: Option<String>,
    packet_capture_artifact_present: Option<bool>,
    artifact_retention_passed: Option<bool>,
    all_profiles_passed: bool,
    profile_count: usize,
    profile_slugs: Vec<String>,
    failed_profile_slugs: Vec<String>,
    required_no_silent_fallback_profile_count: usize,
    required_no_silent_fallback_passed_count: usize,
    required_no_silent_fallback_profile_slugs: Vec<String>,
    explicit_fallback_profile_count: usize,
    udp_blocked_fallback_surface_passed: bool,
    datagram_only_unavailable_rejection_surface_passed: bool,
    policy_disabled_fallback_surface_passed: bool,
    queue_pressure_surface_passed: bool,
    transport_fallback_integrity_surface_passed: bool,
    degradation_path_visibility_passed: bool,
    results: Vec<UdpWanStagingProfileResult>,
    blocking_reasons: Vec<String>,
    blocking_reason_keys: Vec<String>,
    blocking_reason_families: Vec<String>,
}

#[derive(Debug)]
struct EvaluationState {
    missing_required_inputs: Vec<String>,
    blocking_reasons: Vec<String>,
    blocking_reason_keys: Vec<String>,
    blocking_reason_families: Vec<String>,
    blocking_reason_key_counts: BTreeMap<String, usize>,
    blocking_reason_family_counts: BTreeMap<String, usize>,
    degradation_hold_count: usize,
    broader_than_same_revision_passed: Option<bool>,
    role_pair_valid: Option<bool>,
    artifact_root_present: Option<bool>,
    qlog_artifact_present: Option<bool>,
    packet_capture_artifact_present: Option<bool>,
    artifact_retention_passed: Option<bool>,
}

fn main() -> Result<(), Box<dyn std::error::Error>> {
    let mut args = parse_args(env::args().skip(1))?;
    if !args.run_all && args.profiles.is_empty() {
        args.run_all = true;
    }
    let config = resolve_config(args)?;

    let results = if collect_missing_required_inputs(&config).is_empty() {
        config
            .selected_profiles
            .iter()
            .map(|profile| run_profile(profile))
            .collect::<Vec<_>>()
    } else {
        Vec::new()
    };
    let summary = build_summary(&config, results);

    if let Some(parent) = config.summary_path.parent() {
        fs::create_dir_all(parent)?;
    }
    fs::write(&config.summary_path, serde_json::to_vec_pretty(&summary)?)?;

    match config.format {
        OutputFormat::Text => print_text_summary(&summary, &config.summary_path),
        OutputFormat::Json => println!("{}", serde_json::to_string_pretty(&summary)?),
    }

    if summary.verdict != "ready" {
        return Err("udp wan staging interop is not ready".into());
    }

    Ok(())
}

fn parse_args(
    arguments: impl IntoIterator<Item = String>,
) -> Result<WanInteropArgs, Box<dyn std::error::Error>> {
    let mut parsed = WanInteropArgs::default();
    let mut iter = arguments.into_iter();
    while let Some(argument) = iter.next() {
        match argument.as_str() {
            "--all" => parsed.run_all = true,
            "--profile" => {
                let value = iter.next().ok_or("--profile requires a slug argument")?;
                parsed.profiles.push(value);
            }
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
            "--deployment-label" => {
                parsed.deployment_label =
                    Some(iter.next().ok_or("--deployment-label requires a value")?);
            }
            "--host-label" => {
                parsed.host_label = Some(iter.next().ok_or("--host-label requires a value")?);
            }
            "--candidate-revision" => {
                parsed.candidate_revision =
                    Some(iter.next().ok_or("--candidate-revision requires a value")?);
            }
            "--peer-revision" => {
                parsed.peer_revision = Some(iter.next().ok_or("--peer-revision requires a value")?);
            }
            "--role-pair" => {
                parsed.role_pair = Some(iter.next().ok_or("--role-pair requires a value")?);
            }
            "--artifact-root" => {
                let value = iter
                    .next()
                    .ok_or("--artifact-root requires a filesystem path")?;
                parsed.artifact_root = Some(PathBuf::from(value));
            }
            "--qlog-path" => {
                let value = iter
                    .next()
                    .ok_or("--qlog-path requires a filesystem path")?;
                parsed.qlog_path = Some(PathBuf::from(value));
            }
            "--packet-capture-path" => {
                let value = iter
                    .next()
                    .ok_or("--packet-capture-path requires a filesystem path")?;
                parsed.packet_capture_path = Some(PathBuf::from(value));
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

fn resolve_config(args: WanInteropArgs) -> Result<ResolvedConfig, Box<dyn std::error::Error>> {
    let selected_profiles = select_profiles(&args)?;
    Ok(ResolvedConfig {
        selected_profiles,
        format: args.format.unwrap_or(OutputFormat::Text),
        summary_path: args.summary_path.unwrap_or_else(default_summary_path),
        deployment_label: args
            .deployment_label
            .or_else(|| read_env("VERTA_UDP_WAN_STAGING_DEPLOYMENT_LABEL")),
        host_label: args
            .host_label
            .or_else(|| read_env("VERTA_UDP_WAN_STAGING_HOST_LABEL")),
        candidate_revision: args
            .candidate_revision
            .or_else(|| read_env("VERTA_UDP_WAN_STAGING_CANDIDATE_REVISION")),
        peer_revision: args
            .peer_revision
            .or_else(|| read_env("VERTA_UDP_WAN_STAGING_PEER_REVISION")),
        role_pair: args
            .role_pair
            .or_else(|| read_env("VERTA_UDP_WAN_STAGING_ROLE_PAIR")),
        artifact_root: args
            .artifact_root
            .or_else(|| read_env("VERTA_UDP_WAN_STAGING_ARTIFACT_ROOT").map(PathBuf::from)),
        qlog_path: args
            .qlog_path
            .or_else(|| read_env("VERTA_UDP_WAN_STAGING_QLOG_PATH").map(PathBuf::from)),
        packet_capture_path: args
            .packet_capture_path
            .or_else(|| read_env("VERTA_UDP_WAN_STAGING_PACKET_CAPTURE_PATH").map(PathBuf::from)),
    })
}

fn build_summary(
    config: &ResolvedConfig,
    results: Vec<UdpWanStagingProfileResult>,
) -> UdpWanStagingInteropSummary {
    let required_inputs = required_inputs();
    let considered_inputs = considered_inputs();
    let mut state = EvaluationState {
        missing_required_inputs: collect_missing_required_inputs(config),
        blocking_reasons: Vec::new(),
        blocking_reason_keys: Vec::new(),
        blocking_reason_families: Vec::new(),
        blocking_reason_key_counts: BTreeMap::new(),
        blocking_reason_family_counts: BTreeMap::new(),
        degradation_hold_count: 0,
        broader_than_same_revision_passed: None,
        role_pair_valid: None,
        artifact_root_present: None,
        qlog_artifact_present: None,
        packet_capture_artifact_present: None,
        artifact_retention_passed: None,
    };

    let mut profile_slugs = results
        .iter()
        .map(|result| result.slug.clone())
        .collect::<Vec<_>>();
    profile_slugs.sort();
    let mut failed_profile_slugs = results
        .iter()
        .filter(|result| result.status != "passed")
        .map(|result| result.slug.clone())
        .collect::<Vec<_>>();
    failed_profile_slugs.sort();
    let explicit_fallback_profile_count = results
        .iter()
        .filter(|result| !result.requires_no_silent_fallback)
        .count();
    let mut required_no_silent_fallback_profile_slugs = results
        .iter()
        .filter(|result| result.requires_no_silent_fallback)
        .map(|result| result.slug.clone())
        .collect::<Vec<_>>();
    required_no_silent_fallback_profile_slugs.sort();
    let required_no_silent_fallback_profile_count = required_no_silent_fallback_profile_slugs.len();
    let required_no_silent_fallback_passed_count = results
        .iter()
        .filter(|result| result.requires_no_silent_fallback && result.status == "passed")
        .count();
    let udp_blocked_fallback_surface_passed = results
        .iter()
        .any(|result| result.slug == "udp-blocked-fallback" && result.status == "passed");
    let policy_disabled_fallback_surface_passed = results
        .iter()
        .any(|result| result.slug == "policy-disabled-fallback" && result.status == "passed");
    let datagram_only_unavailable_rejection_surface_passed = results.iter().any(|result| {
        result.slug == "datagram-only-unavailable-rejection" && result.status == "passed"
    });
    let queue_pressure_surface_passed = results
        .iter()
        .any(|result| result.slug == "queue-pressure-sticky" && result.status == "passed");
    let degradation_path_visibility_passed = udp_blocked_fallback_surface_passed
        && policy_disabled_fallback_surface_passed
        && datagram_only_unavailable_rejection_surface_passed;
    let transport_fallback_integrity_surface_passed = required_no_silent_fallback_profile_count > 0
        && required_no_silent_fallback_passed_count == required_no_silent_fallback_profile_count
        && degradation_path_visibility_passed;
    let all_profiles_passed = !results.is_empty() && failed_profile_slugs.is_empty();

    if state.missing_required_inputs.is_empty() {
        state.broader_than_same_revision_passed = config
            .candidate_revision
            .as_deref()
            .zip(config.peer_revision.as_deref())
            .map(|(candidate, peer)| candidate != peer);
        if state.broader_than_same_revision_passed == Some(false) {
            record_blocking_reason(
                &mut state,
                "wan_staging_same_revision_pair",
                "same_revision_pair",
                "cross_revision_permutation",
            );
        }

        state.role_pair_valid = config.role_pair.as_deref().map(is_valid_role_pair);
        if state.role_pair_valid == Some(false) {
            record_blocking_reason(
                &mut state,
                "wan_staging_role_pair_invalid",
                "role_pair_invalid",
                "role_permutation",
            );
        }

        state.artifact_root_present = config.artifact_root.as_ref().map(|path| path.is_dir());
        state.qlog_artifact_present = config.qlog_path.as_ref().map(|path| path.is_file());
        state.packet_capture_artifact_present = config
            .packet_capture_path
            .as_ref()
            .map(|path| path.is_file());
        state.artifact_retention_passed = Some(
            state.artifact_root_present == Some(true)
                && (state.qlog_artifact_present == Some(true)
                    || state.packet_capture_artifact_present == Some(true)),
        );
        if state.artifact_retention_passed == Some(false) {
            record_degradation_hold(
                &mut state,
                "wan_staging_artifact_retention_missing",
                "artifact_retention_missing",
                "artifact_retention",
            );
        }

        if !all_profiles_passed {
            record_blocking_reason(
                &mut state,
                "wan_staging_profiles_failed",
                "profiles_failed",
                "interop_execution",
            );
        }
        if !degradation_path_visibility_passed {
            record_blocking_reason(
                &mut state,
                "wan_staging_degradation_paths_incomplete",
                "degradation_paths_incomplete",
                "interop_execution",
            );
        }
        if !transport_fallback_integrity_surface_passed {
            record_blocking_reason(
                &mut state,
                "wan_staging_transport_fallback_integrity_failed",
                "transport_fallback_integrity_failed",
                "interop_execution",
            );
        }
    }

    let required_input_count = required_inputs.len();
    let required_input_missing_count = state.missing_required_inputs.len();
    let required_input_present_count =
        required_input_count.saturating_sub(required_input_missing_count);
    let required_input_passed_count = required_input_present_count;
    let required_input_failed_count = 0usize;
    let required_input_unready_count = 0usize;
    let all_required_inputs_present = required_input_missing_count == 0;
    let all_required_inputs_passed = all_required_inputs_present
        && required_input_failed_count == 0
        && required_input_unready_count == 0;
    let (gate_state_reason, gate_state_reason_family) = summarize_rollout_gate_state(
        required_input_missing_count,
        0,
        required_input_unready_count,
        state.degradation_hold_count,
        state.blocking_reasons.len(),
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
    } else if state.degradation_hold_count > 0 || !state.blocking_reasons.is_empty() {
        "degraded"
    } else {
        "complete"
    };

    UdpWanStagingInteropSummary {
        summary_version: UDP_WAN_STAGING_SUMMARY_VERSION,
        verification_schema: UDP_WAN_STAGING_VERIFICATION_SCHEMA,
        verification_schema_version: UDP_WAN_STAGING_VERIFICATION_SCHEMA_VERSION,
        verdict_family: UDP_WAN_STAGING_VERDICT_FAMILY,
        decision_scope: UDP_WAN_STAGING_DECISION_SCOPE,
        decision_label: UDP_WAN_STAGING_DECISION_LABEL,
        profile: UDP_WAN_STAGING_PROFILE,
        verdict,
        evidence_state,
        gate_state,
        gate_state_reason,
        gate_state_reason_family,
        required_inputs,
        considered_inputs,
        missing_required_inputs: state.missing_required_inputs,
        missing_required_input_count: required_input_missing_count,
        required_input_count,
        required_input_missing_count,
        required_input_failed_count,
        required_input_unready_count,
        required_input_present_count,
        required_input_passed_count,
        all_required_inputs_present,
        all_required_inputs_passed,
        blocking_reason_count: state.blocking_reasons.len(),
        blocking_reason_key_count: state.blocking_reason_key_counts.len(),
        blocking_reason_family_count: state.blocking_reason_family_counts.len(),
        blocking_reason_key_counts: state.blocking_reason_key_counts,
        blocking_reason_family_counts: state.blocking_reason_family_counts,
        degradation_hold_count: state.degradation_hold_count,
        deployment_label: config.deployment_label.clone(),
        host_label: config.host_label.clone(),
        candidate_revision: config.candidate_revision.clone(),
        peer_revision: config.peer_revision.clone(),
        broader_than_same_revision_passed: state.broader_than_same_revision_passed,
        role_pair: config.role_pair.clone(),
        role_pair_valid: state.role_pair_valid,
        evidence_lane: "wan_staging",
        source_lane: UDP_INTEROP_PROFILE_CATALOG_SOURCE_LANE_WAN_STAGING,
        artifact_root: config
            .artifact_root
            .as_ref()
            .map(|path| path.display().to_string()),
        artifact_root_present: state.artifact_root_present,
        qlog_path: config
            .qlog_path
            .as_ref()
            .map(|path| path.display().to_string()),
        qlog_artifact_present: state.qlog_artifact_present,
        packet_capture_path: config
            .packet_capture_path
            .as_ref()
            .map(|path| path.display().to_string()),
        packet_capture_artifact_present: state.packet_capture_artifact_present,
        artifact_retention_passed: state.artifact_retention_passed,
        all_profiles_passed,
        profile_count: results.len(),
        profile_slugs,
        failed_profile_slugs,
        required_no_silent_fallback_profile_count,
        required_no_silent_fallback_passed_count,
        required_no_silent_fallback_profile_slugs,
        explicit_fallback_profile_count,
        udp_blocked_fallback_surface_passed,
        datagram_only_unavailable_rejection_surface_passed,
        policy_disabled_fallback_surface_passed,
        queue_pressure_surface_passed,
        transport_fallback_integrity_surface_passed,
        degradation_path_visibility_passed,
        results,
        blocking_reasons: state.blocking_reasons,
        blocking_reason_keys: state.blocking_reason_keys,
        blocking_reason_families: state.blocking_reason_families,
    }
}

fn required_inputs() -> Vec<String> {
    vec![
        "deployment_label".to_owned(),
        "host_label".to_owned(),
        "candidate_revision".to_owned(),
        "peer_revision".to_owned(),
        "role_pair".to_owned(),
        "artifact_root".to_owned(),
    ]
}

fn considered_inputs() -> Vec<String> {
    let mut inputs = required_inputs();
    inputs.push("qlog_path".to_owned());
    inputs.push("packet_capture_path".to_owned());
    inputs
}

fn collect_missing_required_inputs(config: &ResolvedConfig) -> Vec<String> {
    let mut missing = Vec::new();
    if config
        .deployment_label
        .as_deref()
        .map(str::trim)
        .filter(|value| !value.is_empty())
        .is_none()
    {
        missing.push("deployment_label".to_owned());
    }
    if config
        .host_label
        .as_deref()
        .map(str::trim)
        .filter(|value| !value.is_empty())
        .is_none()
    {
        missing.push("host_label".to_owned());
    }
    if config
        .candidate_revision
        .as_deref()
        .map(str::trim)
        .filter(|value| !value.is_empty())
        .is_none()
    {
        missing.push("candidate_revision".to_owned());
    }
    if config
        .peer_revision
        .as_deref()
        .map(str::trim)
        .filter(|value| !value.is_empty())
        .is_none()
    {
        missing.push("peer_revision".to_owned());
    }
    if config
        .role_pair
        .as_deref()
        .map(str::trim)
        .filter(|value| !value.is_empty())
        .is_none()
    {
        missing.push("role_pair".to_owned());
    }
    if config.artifact_root.is_none() {
        missing.push("artifact_root".to_owned());
    }
    missing
}

fn select_profiles(
    args: &WanInteropArgs,
) -> Result<Vec<&'static ns_testkit::UdpWanLabProfile>, Box<dyn std::error::Error>> {
    if args.run_all {
        return Ok(udp_wan_lab_profiles().iter().collect());
    }

    args.profiles
        .iter()
        .map(|slug| {
            udp_wan_lab_profile_by_slug(slug)
                .ok_or_else(|| format!("unknown UDP WAN staging interop profile {slug}").into())
        })
        .collect()
}

fn run_profile(profile: &'static ns_testkit::UdpWanLabProfile) -> UdpWanStagingProfileResult {
    let repo_root = repo_root();
    let mut command = vec!["cargo".to_owned(), "test".to_owned()];
    command.extend(profile.cargo_args.iter().map(|value| (*value).to_owned()));

    let started_at = Instant::now();
    match Command::new(&command[0])
        .args(&command[1..])
        .current_dir(repo_root)
        .status()
    {
        Ok(status) => UdpWanStagingProfileResult {
            slug: profile.slug.to_owned(),
            spec_suite_ids: profile
                .spec_suite_ids
                .iter()
                .map(|value| (*value).to_owned())
                .collect(),
            command_kind: command_kind_label(profile.command_kind).to_owned(),
            command_selector: profile.command_selector.to_owned(),
            requires_no_silent_fallback: profile.requires_no_silent_fallback,
            status: if status.success() { "passed" } else { "failed" },
            exit_code: status.code(),
            duration_ms: started_at.elapsed().as_millis(),
            command,
            error_detail: None,
        },
        Err(error) => UdpWanStagingProfileResult {
            slug: profile.slug.to_owned(),
            spec_suite_ids: profile
                .spec_suite_ids
                .iter()
                .map(|value| (*value).to_owned())
                .collect(),
            command_kind: command_kind_label(profile.command_kind).to_owned(),
            command_selector: profile.command_selector.to_owned(),
            requires_no_silent_fallback: profile.requires_no_silent_fallback,
            status: "failed",
            exit_code: None,
            duration_ms: started_at.elapsed().as_millis(),
            command,
            error_detail: Some(error.to_string()),
        },
    }
}

fn print_text_summary(summary: &UdpWanStagingInteropSummary, summary_path: &Path) {
    println!("Verta UDP WAN staging interop summary:");
    println!("- verdict: {}", summary.verdict);
    println!("- evidence_state: {}", summary.evidence_state);
    println!("- gate_state_reason: {}", summary.gate_state_reason);
    println!(
        "- deployment_label: {}",
        summary.deployment_label.as_deref().unwrap_or("missing")
    );
    println!(
        "- host_label: {}",
        summary.host_label.as_deref().unwrap_or("missing")
    );
    println!(
        "- candidate_revision: {}",
        summary.candidate_revision.as_deref().unwrap_or("missing")
    );
    println!(
        "- peer_revision: {}",
        summary.peer_revision.as_deref().unwrap_or("missing")
    );
    println!(
        "- role_pair: {}",
        summary.role_pair.as_deref().unwrap_or("missing")
    );
    println!("- source_lane: {}", summary.source_lane);
    println!(
        "- artifact_retention_passed: {}",
        summary.artifact_retention_passed.unwrap_or(false)
    );
    println!(
        "- broader_than_same_revision_passed: {}",
        summary.broader_than_same_revision_passed.unwrap_or(false)
    );
    println!(
        "- role_pair_valid: {}",
        summary.role_pair_valid.unwrap_or(false)
    );
    println!(
        "- degradation_path_visibility_passed: {}",
        summary.degradation_path_visibility_passed
    );
    println!(
        "- transport_fallback_integrity_surface_passed: {}",
        summary.transport_fallback_integrity_surface_passed
    );
    if summary.missing_required_inputs.is_empty() {
        println!("- missing_required_inputs: none");
    } else {
        println!(
            "- missing_required_inputs: {}",
            summary.missing_required_inputs.join(", ")
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
    for result in &summary.results {
        println!(
            "- {slug} {status} via {command_kind}:{command_selector}",
            slug = result.slug,
            status = result.status,
            command_kind = result.command_kind,
            command_selector = result.command_selector,
        );
    }
    println!("machine_readable_summary={}", summary_path.display());
}

fn print_usage() {
    eprintln!(
        "Usage: cargo run -p ns-testkit --example udp_wan_staging_interop -- [--all | --profile <slug> ...] [--format text|json] [--summary-path <path>] [--deployment-label <label>] [--host-label <label>] [--candidate-revision <rev>] [--peer-revision <rev>] [--role-pair <pair>] [--artifact-root <path>] [--qlog-path <path>] [--packet-capture-path <path>]"
    );
}

fn default_summary_path() -> PathBuf {
    repo_root()
        .join("target")
        .join("verta")
        .join("udp-wan-staging-interop-summary.json")
}

fn command_kind_label(kind: UdpWanLabCommandKind) -> &'static str {
    match kind {
        UdpWanLabCommandKind::LiveUdp => "live_udp",
        UdpWanLabCommandKind::Lib => "lib",
    }
}

fn is_valid_role_pair(value: &str) -> bool {
    matches!(
        value,
        ROLE_PAIR_CANDIDATE_CLIENT_BASELINE_GATEWAY
            | ROLE_PAIR_BASELINE_CLIENT_CANDIDATE_GATEWAY
            | ROLE_PAIR_CANDIDATE_CLIENT_CANDIDATE_GATEWAY
    )
}

fn read_env(key: &str) -> Option<String> {
    env::var(key).ok().map(|value| value.trim().to_owned())
}

fn record_blocking_reason(state: &mut EvaluationState, reason: &str, key: &str, family: &str) {
    state.blocking_reasons.push(reason.to_owned());
    state.blocking_reason_keys.push(key.to_owned());
    state.blocking_reason_families.push(family.to_owned());
    *state
        .blocking_reason_key_counts
        .entry(key.to_owned())
        .or_insert(0) += 1;
    *state
        .blocking_reason_family_counts
        .entry(family.to_owned())
        .or_insert(0) += 1;
}

fn record_degradation_hold(state: &mut EvaluationState, reason: &str, key: &str, family: &str) {
    state.degradation_hold_count += 1;
    record_blocking_reason(state, reason, key, family);
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::time::{SystemTime, UNIX_EPOCH};

    fn sample_result(
        slug: &str,
        requires_no_silent_fallback: bool,
        status: &'static str,
    ) -> UdpWanStagingProfileResult {
        UdpWanStagingProfileResult {
            slug: slug.to_owned(),
            spec_suite_ids: Vec::new(),
            command_kind: "live_udp".to_owned(),
            command_selector: slug.to_owned(),
            requires_no_silent_fallback,
            status,
            exit_code: Some(if status == "passed" { 0 } else { 1 }),
            duration_ms: 1,
            command: vec!["cargo".to_owned(), "test".to_owned()],
            error_detail: None,
        }
    }

    fn passing_results() -> Vec<UdpWanStagingProfileResult> {
        vec![
            sample_result("loss-burst", true, "passed"),
            sample_result("queue-pressure-sticky", true, "passed"),
            sample_result("udp-blocked-fallback", false, "passed"),
            sample_result("policy-disabled-fallback", false, "passed"),
            sample_result("datagram-only-unavailable-rejection", false, "passed"),
        ]
    }

    fn unique_temp_path(label: &str) -> PathBuf {
        let nanos = SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .expect("system clock should be after epoch")
            .as_nanos();
        env::temp_dir().join(format!(
            "verta-udp-wan-staging-{label}-{}-{nanos}",
            std::process::id()
        ))
    }

    fn write_temp_file(path: &Path) {
        if let Some(parent) = path.parent() {
            fs::create_dir_all(parent).expect("temp parent should be creatable");
        }
        fs::write(path, b"artifact").expect("temp file should be writable");
    }

    fn sample_config() -> ResolvedConfig {
        let artifact_root = unique_temp_path("artifact-root");
        let qlog_path = artifact_root.join("session.qlog");
        let packet_capture_path = artifact_root.join("session.pcap");
        fs::create_dir_all(&artifact_root).expect("artifact root should be creatable");
        write_temp_file(&qlog_path);
        write_temp_file(&packet_capture_path);

        ResolvedConfig {
            selected_profiles: Vec::new(),
            format: OutputFormat::Json,
            summary_path: unique_temp_path("summary"),
            deployment_label: Some("staging-eu-1".to_owned()),
            host_label: Some("edge-eu-1".to_owned()),
            candidate_revision: Some("rc-2026-04-13".to_owned()),
            peer_revision: Some("main-2026-04-12".to_owned()),
            role_pair: Some(ROLE_PAIR_CANDIDATE_CLIENT_BASELINE_GATEWAY.to_owned()),
            artifact_root: Some(artifact_root),
            qlog_path: Some(qlog_path),
            packet_capture_path: Some(packet_capture_path),
        }
    }

    #[test]
    fn wan_staging_summary_fails_closed_when_required_inputs_are_missing() {
        let config = ResolvedConfig {
            selected_profiles: Vec::new(),
            format: OutputFormat::Json,
            summary_path: default_summary_path(),
            deployment_label: None,
            host_label: None,
            candidate_revision: None,
            peer_revision: None,
            role_pair: None,
            artifact_root: None,
            qlog_path: None,
            packet_capture_path: None,
        };

        let summary = build_summary(&config, Vec::new());

        assert_eq!(summary.verdict, "hold");
        assert_eq!(summary.evidence_lane, "wan_staging");
        assert_eq!(
            summary.source_lane,
            UDP_INTEROP_PROFILE_CATALOG_SOURCE_LANE_WAN_STAGING
        );
        assert_eq!(summary.gate_state_reason, "missing_required_inputs");
        assert!(
            summary
                .missing_required_inputs
                .iter()
                .any(|value| value == "deployment_label")
        );
        assert!(
            summary
                .missing_required_inputs
                .iter()
                .any(|value| value == "artifact_root")
        );
    }

    #[test]
    fn wan_staging_summary_blocks_same_revision_pairs() {
        let mut config = sample_config();
        config.peer_revision = config.candidate_revision.clone();

        let summary = build_summary(&config, passing_results());

        assert_eq!(summary.verdict, "hold");
        assert_eq!(summary.gate_state_reason, "blocking_reasons_present");
        assert_eq!(summary.broader_than_same_revision_passed, Some(false));
        assert!(
            summary
                .blocking_reasons
                .iter()
                .any(|value| value == "wan_staging_same_revision_pair")
        );
    }

    #[test]
    fn wan_staging_summary_marks_artifact_retention_as_degradation_hold() {
        let mut config = sample_config();
        config.qlog_path = None;
        config.packet_capture_path = None;

        let summary = build_summary(&config, passing_results());

        assert_eq!(summary.verdict, "hold");
        assert_eq!(summary.gate_state_reason, "degradation_hold");
        assert_eq!(summary.degradation_path_visibility_passed, true);
        assert_eq!(summary.artifact_retention_passed, Some(false));
    }

    #[test]
    fn wan_staging_summary_is_ready_with_cross_revision_and_artifacts() {
        let config = sample_config();

        let summary = build_summary(&config, passing_results());

        assert_eq!(summary.verdict, "ready");
        assert_eq!(summary.gate_state_reason, "all_required_inputs_passed");
        assert_eq!(summary.broader_than_same_revision_passed, Some(true));
        assert_eq!(summary.role_pair_valid, Some(true));
        assert_eq!(summary.artifact_retention_passed, Some(true));
        assert_eq!(summary.transport_fallback_integrity_surface_passed, true);
        assert_eq!(summary.degradation_path_visibility_passed, true);
    }
}
