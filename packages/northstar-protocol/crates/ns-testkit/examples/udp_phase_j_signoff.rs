use ns_testkit::{repo_root, summarize_rollout_gate_state};
use serde::{Deserialize, Serialize};
use std::collections::{BTreeMap, BTreeSet};
use std::env;
use std::fs;
use std::path::{Path, PathBuf};

const UDP_PHASE_J_SIGNOFF_SUMMARY_VERSION: u8 = 1;

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
enum OutputFormat {
    Text,
    Json,
}

#[derive(Debug, Default)]
struct PhaseJArgs {
    format: Option<OutputFormat>,
    summary_path: Option<PathBuf>,
    wan_staging: Option<PathBuf>,
    net_chaos: Option<PathBuf>,
}

#[derive(Debug, Deserialize)]
struct WanStagingSummaryInput {
    #[serde(default)]
    summary_version: Option<u8>,
    verdict: String,
    evidence_state: String,
    gate_state: String,
    gate_state_reason: String,
    source_lane: String,
    deployment_label: Option<String>,
    host_label: Option<String>,
    broader_than_same_revision_passed: Option<bool>,
    artifact_retention_passed: Option<bool>,
    degradation_path_visibility_passed: bool,
    transport_fallback_integrity_surface_passed: bool,
}

#[derive(Debug, Deserialize)]
struct NetChaosSummaryInput {
    #[serde(default)]
    summary_version: Option<u8>,
    verdict: String,
    evidence_state: String,
    gate_state: String,
    gate_state_reason: String,
    source_lane: String,
    deployment_label: Option<String>,
    host_label: Option<String>,
    artifact_root_present: Option<bool>,
    degradation_path_visibility_passed: bool,
    transport_fallback_integrity_surface_passed: bool,
    #[serde(default)]
    failed_profile_slugs: Vec<String>,
}

#[derive(Debug)]
struct LoadedInput<T> {
    present: bool,
    parse_error: Option<String>,
    summary: Option<T>,
}

type LoadedWanStagingInput = LoadedInput<WanStagingSummaryInput>;
type LoadedNetChaosInput = LoadedInput<NetChaosSummaryInput>;

#[derive(Debug, Serialize)]
struct UdpPhaseJSignoffSummary {
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
    wan_staging_present: bool,
    wan_staging_passed: bool,
    net_chaos_present: bool,
    net_chaos_passed: bool,
    deployment_labels: Vec<String>,
    host_labels: Vec<String>,
    broader_wan_evidence_passed: bool,
    artifact_retention_passed: bool,
    degradation_path_visibility_passed: bool,
    transport_fallback_integrity_surface_passed: bool,
    net_chaos_failed_profile_slugs: Vec<String>,
    phase_j_state: &'static str,
    blocking_reasons: Vec<String>,
    blocking_reason_keys: Vec<String>,
    blocking_reason_families: Vec<String>,
}

fn main() -> Result<(), Box<dyn std::error::Error>> {
    let args = parse_args(env::args().skip(1))?;
    let summary = build_summary(
        load_input::<WanStagingSummaryInput>(
            args.wan_staging
                .unwrap_or_else(default_wan_staging_input)
                .as_path(),
        ),
        load_input::<NetChaosSummaryInput>(
            args.net_chaos
                .unwrap_or_else(default_net_chaos_input)
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
        return Err("phase j signoff is not ready".into());
    }

    Ok(())
}

fn parse_args(
    arguments: impl IntoIterator<Item = String>,
) -> Result<PhaseJArgs, Box<dyn std::error::Error>> {
    let mut parsed = PhaseJArgs::default();
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
            "--wan-staging" => {
                let value = iter
                    .next()
                    .ok_or("--wan-staging requires a filesystem path")?;
                parsed.wan_staging = Some(PathBuf::from(value));
            }
            "--net-chaos" => {
                let value = iter
                    .next()
                    .ok_or("--net-chaos requires a filesystem path")?;
                parsed.net_chaos = Some(PathBuf::from(value));
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
    wan_staging: LoadedWanStagingInput,
    net_chaos: LoadedNetChaosInput,
) -> UdpPhaseJSignoffSummary {
    let required_inputs = vec!["wan_staging".to_owned(), "net_chaos".to_owned()];
    let considered_inputs = required_inputs.clone();
    let mut missing_required_inputs = Vec::new();
    let mut blocking_reasons = Vec::new();
    let mut blocking_reason_keys = Vec::new();
    let mut blocking_reason_families = Vec::new();
    let mut blocking_reason_key_counts = BTreeMap::new();
    let mut blocking_reason_family_counts = BTreeMap::new();

    let wan_staging_present = wan_staging.present && wan_staging.parse_error.is_none();
    let net_chaos_present = net_chaos.present && net_chaos.parse_error.is_none();
    if !wan_staging_present {
        missing_required_inputs.push("wan_staging".to_owned());
    }
    if !net_chaos_present {
        missing_required_inputs.push("net_chaos".to_owned());
    }

    let wan_staging_passed = wan_staging
        .summary
        .as_ref()
        .map(|summary| {
            summary.summary_version == Some(1)
                && summary.verdict == "ready"
                && summary.evidence_state == "complete"
                && summary.gate_state == "pass"
                && summary.gate_state_reason == "all_required_inputs_passed"
                && summary.source_lane == "wan_staging_interop"
                && summary.broader_than_same_revision_passed == Some(true)
                && summary.artifact_retention_passed == Some(true)
                && summary.degradation_path_visibility_passed
                && summary.transport_fallback_integrity_surface_passed
        })
        .unwrap_or(false);
    if wan_staging_present && !wan_staging_passed {
        record_blocking_reason(
            &mut blocking_reasons,
            &mut blocking_reason_keys,
            &mut blocking_reason_families,
            &mut blocking_reason_key_counts,
            &mut blocking_reason_family_counts,
            "phase_j_wan_staging_not_ready",
            "wan_staging_not_ready",
            "phase_j_inputs",
        );
    }

    let net_chaos_passed = net_chaos
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
                && summary.degradation_path_visibility_passed
                && summary.transport_fallback_integrity_surface_passed
                && summary.failed_profile_slugs.is_empty()
        })
        .unwrap_or(false);
    if net_chaos_present && !net_chaos_passed {
        record_blocking_reason(
            &mut blocking_reasons,
            &mut blocking_reason_keys,
            &mut blocking_reason_families,
            &mut blocking_reason_key_counts,
            &mut blocking_reason_family_counts,
            "phase_j_net_chaos_not_ready",
            "net_chaos_not_ready",
            "phase_j_inputs",
        );
    }

    let deployment_labels = {
        let mut labels = BTreeSet::new();
        if let Some(value) = wan_staging
            .summary
            .as_ref()
            .and_then(|summary| summary.deployment_label.clone())
        {
            labels.insert(value);
        }
        if let Some(value) = net_chaos
            .summary
            .as_ref()
            .and_then(|summary| summary.deployment_label.clone())
        {
            labels.insert(value);
        }
        labels.into_iter().collect::<Vec<_>>()
    };
    let host_labels = {
        let mut labels = BTreeSet::new();
        if let Some(value) = wan_staging
            .summary
            .as_ref()
            .and_then(|summary| summary.host_label.clone())
        {
            labels.insert(value);
        }
        if let Some(value) = net_chaos
            .summary
            .as_ref()
            .and_then(|summary| summary.host_label.clone())
        {
            labels.insert(value);
        }
        labels.into_iter().collect::<Vec<_>>()
    };
    let broader_wan_evidence_passed = wan_staging_passed && net_chaos_passed;
    let artifact_retention_passed = wan_staging
        .summary
        .as_ref()
        .and_then(|summary| summary.artifact_retention_passed)
        .unwrap_or(false)
        && net_chaos
            .summary
            .as_ref()
            .and_then(|summary| summary.artifact_root_present)
            .unwrap_or(false);
    let degradation_path_visibility_passed = wan_staging
        .summary
        .as_ref()
        .map(|summary| summary.degradation_path_visibility_passed)
        .unwrap_or(false)
        && net_chaos
            .summary
            .as_ref()
            .map(|summary| summary.degradation_path_visibility_passed)
            .unwrap_or(false);
    let transport_fallback_integrity_surface_passed = wan_staging
        .summary
        .as_ref()
        .map(|summary| summary.transport_fallback_integrity_surface_passed)
        .unwrap_or(false)
        && net_chaos
            .summary
            .as_ref()
            .map(|summary| summary.transport_fallback_integrity_surface_passed)
            .unwrap_or(false);
    let net_chaos_failed_profile_slugs = net_chaos
        .summary
        .as_ref()
        .map(|summary| summary.failed_profile_slugs.clone())
        .unwrap_or_default();

    let required_input_count = required_inputs.len();
    let required_input_missing_count = missing_required_inputs.len();
    let required_input_present_count =
        required_input_count.saturating_sub(required_input_missing_count);
    let required_input_passed_count = [wan_staging_passed, net_chaos_passed]
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
    let phase_j_state = if verdict == "ready" {
        "honestly_complete"
    } else if required_input_missing_count > 0 {
        "missing_inputs"
    } else {
        "blocked"
    };

    UdpPhaseJSignoffSummary {
        summary_version: UDP_PHASE_J_SIGNOFF_SUMMARY_VERSION,
        verdict_family: "udp_phase_j_signoff",
        decision_scope: "phase_j",
        decision_label: "udp_phase_j_signoff",
        profile: "phase_j_signoff",
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
        wan_staging_present,
        wan_staging_passed,
        net_chaos_present,
        net_chaos_passed,
        deployment_labels,
        host_labels,
        broader_wan_evidence_passed,
        artifact_retention_passed,
        degradation_path_visibility_passed,
        transport_fallback_integrity_surface_passed,
        net_chaos_failed_profile_slugs,
        phase_j_state,
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

fn default_summary_path() -> PathBuf {
    repo_root()
        .join("target")
        .join("northstar")
        .join("udp-phase-j-signoff-summary.json")
}

fn default_wan_staging_input() -> PathBuf {
    repo_root()
        .join("target")
        .join("northstar")
        .join("udp-wan-staging-interop-summary.json")
}

fn default_net_chaos_input() -> PathBuf {
    repo_root()
        .join("target")
        .join("northstar")
        .join("udp-net-chaos-campaign-summary.json")
}

fn print_text_summary(summary: &UdpPhaseJSignoffSummary, summary_path: &Path) {
    println!("Northstar Phase J signoff summary:");
    println!("- verdict: {}", summary.verdict);
    println!("- phase_j_state: {}", summary.phase_j_state);
    println!("- gate_state_reason: {}", summary.gate_state_reason);
    println!("- wan_staging_passed: {}", summary.wan_staging_passed);
    println!("- net_chaos_passed: {}", summary.net_chaos_passed);
    println!(
        "- broader_wan_evidence_passed: {}",
        summary.broader_wan_evidence_passed
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
        "Usage: cargo run -p ns-testkit --example udp_phase_j_signoff -- [--format text|json] [--summary-path <path>] [--wan-staging <path>] [--net-chaos <path>]"
    );
}

#[cfg(test)]
mod tests {
    use super::*;

    fn loaded_wan(summary: WanStagingSummaryInput) -> LoadedWanStagingInput {
        LoadedInput {
            present: true,
            parse_error: None,
            summary: Some(summary),
        }
    }

    fn loaded_net(summary: NetChaosSummaryInput) -> LoadedNetChaosInput {
        LoadedInput {
            present: true,
            parse_error: None,
            summary: Some(summary),
        }
    }

    fn ready_wan() -> WanStagingSummaryInput {
        WanStagingSummaryInput {
            summary_version: Some(1),
            verdict: "ready".to_owned(),
            evidence_state: "complete".to_owned(),
            gate_state: "pass".to_owned(),
            gate_state_reason: "all_required_inputs_passed".to_owned(),
            source_lane: "wan_staging_interop".to_owned(),
            deployment_label: Some("local-netchaos".to_owned()),
            host_label: Some("lab-linux".to_owned()),
            broader_than_same_revision_passed: Some(true),
            artifact_retention_passed: Some(true),
            degradation_path_visibility_passed: true,
            transport_fallback_integrity_surface_passed: true,
        }
    }

    fn ready_net() -> NetChaosSummaryInput {
        NetChaosSummaryInput {
            summary_version: Some(1),
            verdict: "ready".to_owned(),
            evidence_state: "complete".to_owned(),
            gate_state: "pass".to_owned(),
            gate_state_reason: "all_required_inputs_passed".to_owned(),
            source_lane: "net_chaos_campaign".to_owned(),
            deployment_label: Some("local-netchaos".to_owned()),
            host_label: Some("lab-linux".to_owned()),
            artifact_root_present: Some(true),
            degradation_path_visibility_passed: true,
            transport_fallback_integrity_surface_passed: true,
            failed_profile_slugs: Vec::new(),
        }
    }

    #[test]
    fn phase_j_signoff_is_ready_when_wan_and_net_chaos_are_ready() {
        let summary = build_summary(loaded_wan(ready_wan()), loaded_net(ready_net()));

        assert_eq!(summary.verdict, "ready");
        assert_eq!(summary.phase_j_state, "honestly_complete");
        assert!(summary.broader_wan_evidence_passed);
    }

    #[test]
    fn phase_j_signoff_blocks_when_net_chaos_is_not_ready() {
        let mut net = ready_net();
        net.verdict = "hold".to_owned();
        net.gate_state = "hold".to_owned();
        net.gate_state_reason = "blocking_reasons_present".to_owned();
        net.failed_profile_slugs = vec!["udp-flaky".to_owned()];
        net.transport_fallback_integrity_surface_passed = false;

        let summary = build_summary(loaded_wan(ready_wan()), loaded_net(net));

        assert_eq!(summary.verdict, "hold");
        assert_eq!(summary.phase_j_state, "blocked");
        assert!(
            summary
                .blocking_reasons
                .iter()
                .any(|value| value == "phase_j_net_chaos_not_ready")
        );
        assert_eq!(
            summary.net_chaos_failed_profile_slugs,
            vec!["udp-flaky".to_owned()]
        );
    }
}
