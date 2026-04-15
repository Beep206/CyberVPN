use ns_testkit::{
    UDP_ROLLOUT_DECISION_SCOPE_HOST, UDP_ROLLOUT_DECISION_SCOPE_RELEASE_CANDIDATE_SIGNOFF,
    UDP_ROLLOUT_DECISION_SCOPE_RELEASE_PREP, UDP_ROLLOUT_OPERATOR_VERDICT_FAMILY,
    UDP_ROLLOUT_OPERATOR_VERDICT_SCHEMA, UDP_ROLLOUT_OPERATOR_VERDICT_SCHEMA_VERSION,
    prefer_verta_input_path, summarize_rollout_gate_state, udp_wan_lab_profile_slugs,
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
struct ReleaseCandidateSignoffArgs {
    format: Option<OutputFormat>,
    summary_path: Option<PathBuf>,
    release_prep: Option<PathBuf>,
    windows_readiness: Option<PathBuf>,
    windows_interop: Option<PathBuf>,
    macos_interop: Option<PathBuf>,
}

const UDP_RELEASE_PREP_SUMMARY_VERSION: u8 = 6;
const UDP_ROLLOUT_COMPARISON_SUMMARY_VERSION: u8 = 14;
const UDP_INTEROP_LAB_SUMMARY_VERSION: u8 = 4;
const UDP_RELEASE_CANDIDATE_SIGNOFF_SUMMARY_VERSION: u8 = 5;

#[derive(Debug, Deserialize)]
struct ReleasePrepSummaryInput {
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
    interop_profile_contract_passed: bool,
    #[serde(default)]
    blocking_reasons: Vec<String>,
}

#[derive(Debug, Deserialize)]
struct WindowsReadinessSummaryInput {
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
    queue_guard_limiting_path: Option<String>,
    #[serde(default)]
    interop_profile_count: Option<usize>,
    #[serde(default)]
    interop_profile_slugs: Vec<String>,
    #[serde(default)]
    interop_required_no_silent_fallback_profile_slugs: Vec<String>,
    #[serde(default)]
    interop_failed_profile_slugs: Vec<String>,
    #[serde(default)]
    explicit_fallback_profile_count: usize,
    #[serde(default)]
    policy_disabled_fallback_surface_passed: Option<bool>,
    #[serde(default)]
    transport_fallback_integrity_surface_passed: Option<bool>,
    #[serde(default)]
    interop_profile_contract_passed: Option<bool>,
    #[serde(default)]
    queue_guard_tight_hold_count: usize,
    #[serde(default)]
    queue_pressure_hold_count: usize,
    #[serde(default)]
    blocking_reasons: Vec<String>,
}

#[derive(Debug, Deserialize)]
struct InteropLabSummaryInput {
    #[serde(default)]
    summary_version: Option<u8>,
    all_passed: bool,
    profile_count: usize,
    #[serde(default)]
    profile_slugs: Vec<String>,
    #[serde(default)]
    failed_profile_slugs: Vec<String>,
    #[serde(default)]
    required_no_silent_fallback_profile_count: usize,
    #[serde(default)]
    required_no_silent_fallback_passed_count: usize,
    #[serde(default)]
    required_no_silent_fallback_profile_slugs: Vec<String>,
    #[serde(default)]
    explicit_fallback_profile_count: usize,
    policy_disabled_fallback_surface_passed: bool,
    #[serde(default)]
    queue_pressure_surface_passed: bool,
    #[serde(default)]
    transport_fallback_integrity_surface_passed: bool,
}

#[derive(Debug)]
struct LoadedReleasePrepInput {
    present: bool,
    parse_error: Option<String>,
    summary: Option<ReleasePrepSummaryInput>,
}

#[derive(Debug)]
struct LoadedWindowsReadinessInput {
    present: bool,
    parse_error: Option<String>,
    summary: Option<WindowsReadinessSummaryInput>,
}

#[derive(Debug)]
struct LoadedWindowsInteropInput {
    present: bool,
    parse_error: Option<String>,
    summary: Option<InteropLabSummaryInput>,
}

#[derive(Debug)]
struct LoadedMacosInteropInput {
    present: bool,
    parse_error: Option<String>,
    summary: Option<InteropLabSummaryInput>,
}

#[derive(Debug, Serialize)]
struct UdpReleaseCandidateSignoffSummary {
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
    release_prep_present: bool,
    release_prep_passed: bool,
    windows_readiness_present: bool,
    windows_readiness_passed: bool,
    windows_interop_present: bool,
    windows_interop_passed: bool,
    macos_interop_present: bool,
    macos_interop_passed: bool,
    windows_host_label: Option<String>,
    interop_profile_count: Option<usize>,
    interop_profile_slugs: Vec<String>,
    interop_required_no_silent_fallback_profile_slugs: Vec<String>,
    interop_failed_profile_slugs: Vec<String>,
    macos_interop_profile_count: Option<usize>,
    macos_interop_profile_slugs: Vec<String>,
    macos_interop_failed_profile_slugs: Vec<String>,
    explicit_fallback_profile_count: usize,
    policy_disabled_fallback_surface_passed: Option<bool>,
    transport_fallback_integrity_surface_passed: Option<bool>,
    degradation_hold_count: usize,
    degradation_hold_subjects: Vec<String>,
    queue_guard_headroom_band_counts: BTreeMap<String, usize>,
    queue_guard_headroom_missing_count: usize,
    queue_guard_tight_hold_count: usize,
    queue_pressure_hold_count: usize,
    queue_guard_limiting_path_counts: BTreeMap<String, usize>,
    interop_profile_contract_passed: bool,
    blocking_reasons: Vec<String>,
    blocking_reason_keys: Vec<String>,
    blocking_reason_families: Vec<String>,
    advisory_reasons: Vec<String>,
}

fn main() -> Result<(), Box<dyn std::error::Error>> {
    let args = parse_args(env::args().skip(1))?;
    let release_prep_path = args.release_prep.unwrap_or_else(default_release_prep_input);
    let windows_readiness_path = args
        .windows_readiness
        .unwrap_or_else(default_windows_readiness_input);
    let windows_interop_path = args
        .windows_interop
        .unwrap_or_else(default_windows_interop_input);
    let macos_interop_path = args
        .macos_interop
        .unwrap_or_else(default_macos_interop_input);
    let summary = build_release_candidate_signoff_summary(
        load_release_prep_input(&release_prep_path),
        load_windows_readiness_input(&windows_readiness_path),
        load_windows_interop_input(&windows_interop_path),
        load_macos_interop_input(&macos_interop_path),
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
        return Err("udp release candidate signoff is not ready".into());
    }

    Ok(())
}

fn build_release_candidate_signoff_summary(
    release_prep: LoadedReleasePrepInput,
    windows_readiness: LoadedWindowsReadinessInput,
    windows_interop: LoadedWindowsInteropInput,
    macos_interop: LoadedMacosInteropInput,
) -> UdpReleaseCandidateSignoffSummary {
    let required_inputs = vec![
        "release_prep".to_owned(),
        "windows_readiness".to_owned(),
        "windows_interop".to_owned(),
        "macos_interop".to_owned(),
    ];
    let considered_inputs = required_inputs.clone();
    let mut present_required_inputs = BTreeSet::new();
    let mut passed_required_inputs = BTreeSet::new();
    let mut blocking_reasons = Vec::new();
    let mut blocking_reason_key_counts = BTreeMap::new();
    let mut blocking_reason_family_counts = BTreeMap::new();
    let advisory_reasons = Vec::new();
    let mut queue_guard_headroom_band_counts = BTreeMap::new();
    let mut queue_guard_limiting_path_counts = BTreeMap::new();
    let mut degradation_hold_subjects = Vec::new();
    let mut all_consumed_inputs_contract_valid = true;
    let mut queue_guard_headroom_missing_count = 0usize;
    let mut queue_guard_tight_hold_count = 0usize;
    let expected_required_no_silent_fallback_profile_slugs =
        udp_wan_lab_required_no_silent_fallback_profile_slugs()
            .into_iter()
            .map(str::to_owned)
            .collect::<Vec<_>>();
    let expected_required_no_silent_fallback_profile_set =
        expected_required_no_silent_fallback_profile_slugs
            .iter()
            .cloned()
            .collect::<BTreeSet<_>>();

    let release_prep_present = release_prep.present;
    if release_prep_present {
        present_required_inputs.insert("release_prep".to_owned());
    }
    let release_prep_passed = match release_prep.summary.as_ref() {
        Some(summary)
            if release_prep.present
                && release_prep.parse_error.is_none()
                && release_prep_summary_contract_valid(summary)
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
            queue_guard_tight_hold_count += summary.queue_guard_tight_hold_count;
            passed_required_inputs.insert("release_prep".to_owned());
            true
        }
        Some(summary) => {
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
            false
        }
        None => false,
    };

    if !release_prep.present {
        push_reason(
            &mut blocking_reasons,
            &mut blocking_reason_key_counts,
            &mut blocking_reason_family_counts,
            "missing_release_prep_summary",
            "missing_required_input",
            "summary_presence",
        );
    } else if let Some(error) = release_prep.parse_error.as_ref() {
        all_consumed_inputs_contract_valid = false;
        push_reason(
            &mut blocking_reasons,
            &mut blocking_reason_key_counts,
            &mut blocking_reason_family_counts,
            &format!("release_prep_parse_error:{error}"),
            "input_parse_error",
            "summary_contract",
        );
    } else if let Some(summary) = release_prep.summary.as_ref() {
        if !release_prep_summary_contract_valid(summary) {
            all_consumed_inputs_contract_valid = false;
            push_reason(
                &mut blocking_reasons,
                &mut blocking_reason_key_counts,
                &mut blocking_reason_family_counts,
                "release_prep_summary_contract_invalid",
                "input_contract_invalid",
                "summary_contract",
            );
        } else if !release_prep_passed {
            if summary.degradation_hold_count > 0 {
                degradation_hold_subjects.extend(summary.degradation_hold_subjects.iter().cloned());
            }
            push_reason(
                &mut blocking_reasons,
                &mut blocking_reason_key_counts,
                &mut blocking_reason_family_counts,
                "release_prep_not_ready",
                "release_prep_not_ready",
                if summary.degradation_hold_count > 0 {
                    "degradation"
                } else {
                    "gating"
                },
            );
        }
    }

    let windows_readiness_present = windows_readiness.present;
    if windows_readiness_present {
        present_required_inputs.insert("windows_readiness".to_owned());
    }
    let windows_host_label = windows_readiness
        .summary
        .as_ref()
        .map(|summary| summary.host_label.clone());
    let windows_readiness_required_no_silent_fallback_profile_slugs = windows_readiness
        .summary
        .as_ref()
        .map(|summary| {
            summary
                .interop_required_no_silent_fallback_profile_slugs
                .clone()
        })
        .unwrap_or_default();
    let windows_readiness_required_no_silent_fallback_profile_set =
        windows_readiness_required_no_silent_fallback_profile_slugs
            .iter()
            .cloned()
            .collect::<BTreeSet<_>>();
    let windows_readiness_passed = match windows_readiness.summary.as_ref() {
        Some(summary)
            if windows_readiness.present
                && windows_readiness.parse_error.is_none()
                && windows_readiness_summary_contract_valid(summary)
                && summary.profile == "readiness"
                && summary.decision_scope == UDP_ROLLOUT_DECISION_SCOPE_HOST
                && summary.verdict == "ready"
                && summary.evidence_state == "complete"
                && summary.gate_state == "passed"
                && !summary.active_fuzz_required
                && summary.all_required_inputs_present
                && summary.all_required_inputs_passed
                && summary.blocking_reason_count == 0
                && summary.degradation_hold_count == 0
                && summary.queue_guard_tight_hold_count == 0
                && summary.queue_pressure_hold_count == 0
                && summary.policy_disabled_fallback_surface_passed == Some(true)
                && summary.transport_fallback_integrity_surface_passed == Some(true)
                && summary.interop_profile_contract_passed == Some(true) =>
        {
            merge_counts(
                &mut queue_guard_headroom_band_counts,
                &summary.queue_guard_headroom_band_counts,
            );
            queue_guard_headroom_missing_count += summary.queue_guard_headroom_missing_count;
            if let Some(path) = summary.queue_guard_limiting_path.as_ref() {
                *queue_guard_limiting_path_counts
                    .entry(path.clone())
                    .or_insert(0) += 1;
            }
            queue_guard_tight_hold_count += summary.queue_guard_tight_hold_count;
            passed_required_inputs.insert("windows_readiness".to_owned());
            true
        }
        Some(summary) => {
            merge_counts(
                &mut queue_guard_headroom_band_counts,
                &summary.queue_guard_headroom_band_counts,
            );
            queue_guard_headroom_missing_count += summary.queue_guard_headroom_missing_count;
            if let Some(path) = summary.queue_guard_limiting_path.as_ref() {
                *queue_guard_limiting_path_counts
                    .entry(path.clone())
                    .or_insert(0) += 1;
            }
            queue_guard_tight_hold_count += summary.queue_guard_tight_hold_count;
            false
        }
        None => false,
    };

    if !windows_readiness.present {
        push_reason(
            &mut blocking_reasons,
            &mut blocking_reason_key_counts,
            &mut blocking_reason_family_counts,
            "missing_windows_readiness_summary",
            "missing_required_input",
            "summary_presence",
        );
    } else if let Some(error) = windows_readiness.parse_error.as_ref() {
        all_consumed_inputs_contract_valid = false;
        push_reason(
            &mut blocking_reasons,
            &mut blocking_reason_key_counts,
            &mut blocking_reason_family_counts,
            &format!("windows_readiness_parse_error:{error}"),
            "input_parse_error",
            "summary_contract",
        );
    } else if let Some(summary) = windows_readiness.summary.as_ref() {
        if !windows_readiness_summary_contract_valid(summary) {
            all_consumed_inputs_contract_valid = false;
            push_reason(
                &mut blocking_reasons,
                &mut blocking_reason_key_counts,
                &mut blocking_reason_family_counts,
                "windows_readiness_summary_contract_invalid",
                "input_contract_invalid",
                "summary_contract",
            );
            if windows_readiness_required_no_silent_fallback_profile_set
                != expected_required_no_silent_fallback_profile_set
            {
                push_reason(
                    &mut blocking_reasons,
                    &mut blocking_reason_key_counts,
                    &mut blocking_reason_family_counts,
                    "windows_readiness_interop_required_no_silent_fallback_profile_set_mismatch",
                    "interop_required_no_silent_fallback_profile_set_mismatch",
                    "summary_contract",
                );
            }
        } else {
            if summary.degradation_hold_count > 0 {
                degradation_hold_subjects.push("windows_readiness".to_owned());
                degradation_hold_subjects.extend(summary.degradation_hold_subjects.iter().cloned());
            }
            if !windows_readiness_passed {
                push_reason(
                    &mut blocking_reasons,
                    &mut blocking_reason_key_counts,
                    &mut blocking_reason_family_counts,
                    "windows_readiness_not_ready",
                    "windows_readiness_not_ready",
                    if summary.degradation_hold_count > 0 {
                        "degradation"
                    } else {
                        "gating"
                    },
                );
            }
            if summary.policy_disabled_fallback_surface_passed == Some(false) {
                push_reason(
                    &mut blocking_reasons,
                    &mut blocking_reason_key_counts,
                    &mut blocking_reason_family_counts,
                    "windows_policy_disabled_fallback_surface_failed",
                    "policy_disabled_fallback_surface_failed",
                    "interop",
                );
            }
            if summary.transport_fallback_integrity_surface_passed == Some(false) {
                push_reason(
                    &mut blocking_reasons,
                    &mut blocking_reason_key_counts,
                    &mut blocking_reason_family_counts,
                    "windows_transport_fallback_integrity_surface_failed",
                    "transport_fallback_integrity_surface_failed",
                    "degradation",
                );
            }
            if summary.queue_pressure_hold_count > 0 {
                push_reason(
                    &mut blocking_reasons,
                    &mut blocking_reason_key_counts,
                    &mut blocking_reason_family_counts,
                    "windows_queue_pressure_surface_failed",
                    "queue_pressure_surface_failed",
                    "capacity",
                );
            }
        }
    }

    let windows_interop_present = windows_interop.present;
    if windows_interop_present {
        present_required_inputs.insert("windows_interop".to_owned());
    }
    let interop_profile_count = windows_interop
        .summary
        .as_ref()
        .map(|summary| summary.profile_count);
    let windows_interop_required_no_silent_fallback_profile_slugs = windows_interop
        .summary
        .as_ref()
        .map(|summary| summary.required_no_silent_fallback_profile_slugs.clone())
        .unwrap_or_default();
    let interop_profile_slugs = windows_interop
        .summary
        .as_ref()
        .map(|summary| summary.profile_slugs.clone())
        .unwrap_or_default();
    let interop_failed_profile_slugs = windows_interop
        .summary
        .as_ref()
        .map(|summary| summary.failed_profile_slugs.clone())
        .unwrap_or_default();
    let windows_interop_policy_disabled_fallback_surface_passed = windows_interop
        .summary
        .as_ref()
        .map(|summary| summary.policy_disabled_fallback_surface_passed);
    let windows_interop_transport_fallback_integrity_surface_passed = windows_interop
        .summary
        .as_ref()
        .map(|summary| summary.transport_fallback_integrity_surface_passed);
    let windows_interop_explicit_fallback_profile_count = windows_interop
        .summary
        .as_ref()
        .map(|summary| summary.explicit_fallback_profile_count)
        .unwrap_or(0);
    let windows_interop_passed = match windows_interop.summary.as_ref() {
        Some(summary)
            if windows_interop.present
                && windows_interop.parse_error.is_none()
                && interop_summary_contract_valid(summary)
                && summary.all_passed
                && summary.queue_pressure_surface_passed
                && summary.policy_disabled_fallback_surface_passed
                && summary.transport_fallback_integrity_surface_passed =>
        {
            passed_required_inputs.insert("windows_interop".to_owned());
            true
        }
        _ => false,
    };

    if !windows_interop.present {
        push_reason(
            &mut blocking_reasons,
            &mut blocking_reason_key_counts,
            &mut blocking_reason_family_counts,
            "missing_windows_interop_summary",
            "missing_required_input",
            "summary_presence",
        );
    } else if let Some(error) = windows_interop.parse_error.as_ref() {
        all_consumed_inputs_contract_valid = false;
        push_reason(
            &mut blocking_reasons,
            &mut blocking_reason_key_counts,
            &mut blocking_reason_family_counts,
            &format!("windows_interop_parse_error:{error}"),
            "input_parse_error",
            "summary_contract",
        );
    } else if let Some(summary) = windows_interop.summary.as_ref() {
        if !interop_summary_contract_valid(summary) {
            all_consumed_inputs_contract_valid = false;
            push_reason(
                &mut blocking_reasons,
                &mut blocking_reason_key_counts,
                &mut blocking_reason_family_counts,
                "windows_interop_summary_contract_invalid",
                "input_contract_invalid",
                "summary_contract",
            );
        } else {
            if !summary.queue_pressure_surface_passed
                || !summary.policy_disabled_fallback_surface_passed
                || !summary.transport_fallback_integrity_surface_passed
                || !summary.failed_profile_slugs.is_empty()
            {
                degradation_hold_subjects.push("windows_interop".to_owned());
                degradation_hold_subjects.extend(summary.failed_profile_slugs.iter().cloned());
            }
            if !windows_interop_passed {
                push_reason(
                    &mut blocking_reasons,
                    &mut blocking_reason_key_counts,
                    &mut blocking_reason_family_counts,
                    "windows_interop_not_ready",
                    "windows_interop_not_ready",
                    if summary.failed_profile_slugs.is_empty() {
                        "gating"
                    } else {
                        "interop"
                    },
                );
            }
            if !summary.queue_pressure_surface_passed {
                push_reason(
                    &mut blocking_reasons,
                    &mut blocking_reason_key_counts,
                    &mut blocking_reason_family_counts,
                    "windows_queue_pressure_surface_failed",
                    "queue_pressure_surface_failed",
                    "capacity",
                );
            }
            if !summary.policy_disabled_fallback_surface_passed {
                push_reason(
                    &mut blocking_reasons,
                    &mut blocking_reason_key_counts,
                    &mut blocking_reason_family_counts,
                    "windows_policy_disabled_fallback_surface_failed",
                    "policy_disabled_fallback_surface_failed",
                    "interop",
                );
            }
            if !summary.transport_fallback_integrity_surface_passed {
                push_reason(
                    &mut blocking_reasons,
                    &mut blocking_reason_key_counts,
                    &mut blocking_reason_family_counts,
                    "windows_transport_fallback_integrity_surface_failed",
                    "transport_fallback_integrity_surface_failed",
                    "degradation",
                );
            }
        }
    }

    let macos_interop_present = macos_interop.present;
    if macos_interop_present {
        present_required_inputs.insert("macos_interop".to_owned());
    }
    let macos_interop_profile_count = macos_interop
        .summary
        .as_ref()
        .map(|summary| summary.profile_count);
    let macos_interop_required_no_silent_fallback_profile_slugs = macos_interop
        .summary
        .as_ref()
        .map(|summary| summary.required_no_silent_fallback_profile_slugs.clone())
        .unwrap_or_default();
    let macos_interop_profile_slugs = macos_interop
        .summary
        .as_ref()
        .map(|summary| summary.profile_slugs.clone())
        .unwrap_or_default();
    let macos_interop_failed_profile_slugs = macos_interop
        .summary
        .as_ref()
        .map(|summary| summary.failed_profile_slugs.clone())
        .unwrap_or_default();
    let macos_interop_passed = match macos_interop.summary.as_ref() {
        Some(summary)
            if macos_interop.present
                && macos_interop.parse_error.is_none()
                && interop_summary_contract_valid(summary)
                && summary.all_passed
                && summary.queue_pressure_surface_passed
                && summary.policy_disabled_fallback_surface_passed
                && summary.transport_fallback_integrity_surface_passed =>
        {
            passed_required_inputs.insert("macos_interop".to_owned());
            true
        }
        _ => false,
    };

    if !macos_interop.present {
        push_reason(
            &mut blocking_reasons,
            &mut blocking_reason_key_counts,
            &mut blocking_reason_family_counts,
            "missing_macos_interop_summary",
            "missing_required_input",
            "summary_presence",
        );
    } else if let Some(error) = macos_interop.parse_error.as_ref() {
        all_consumed_inputs_contract_valid = false;
        push_reason(
            &mut blocking_reasons,
            &mut blocking_reason_key_counts,
            &mut blocking_reason_family_counts,
            &format!("macos_interop_parse_error:{error}"),
            "input_parse_error",
            "summary_contract",
        );
    } else if let Some(summary) = macos_interop.summary.as_ref() {
        if !interop_summary_contract_valid(summary) {
            all_consumed_inputs_contract_valid = false;
            push_reason(
                &mut blocking_reasons,
                &mut blocking_reason_key_counts,
                &mut blocking_reason_family_counts,
                "macos_interop_summary_contract_invalid",
                "input_contract_invalid",
                "summary_contract",
            );
        } else {
            if !summary.queue_pressure_surface_passed
                || !summary.failed_profile_slugs.is_empty()
                || !summary.policy_disabled_fallback_surface_passed
                || !summary.transport_fallback_integrity_surface_passed
            {
                degradation_hold_subjects.push("macos_interop".to_owned());
                degradation_hold_subjects.extend(summary.failed_profile_slugs.iter().cloned());
            }
            if !macos_interop_passed {
                push_reason(
                    &mut blocking_reasons,
                    &mut blocking_reason_key_counts,
                    &mut blocking_reason_family_counts,
                    "macos_interop_not_ready",
                    "macos_interop_not_ready",
                    if summary.failed_profile_slugs.is_empty() {
                        "gating"
                    } else {
                        "interop"
                    },
                );
            }
            if !summary.policy_disabled_fallback_surface_passed {
                push_reason(
                    &mut blocking_reasons,
                    &mut blocking_reason_key_counts,
                    &mut blocking_reason_family_counts,
                    "macos_policy_disabled_fallback_surface_failed",
                    "policy_disabled_fallback_surface_failed",
                    "interop",
                );
            }
            if !summary.queue_pressure_surface_passed {
                push_reason(
                    &mut blocking_reasons,
                    &mut blocking_reason_key_counts,
                    &mut blocking_reason_family_counts,
                    "macos_queue_pressure_surface_failed",
                    "queue_pressure_surface_failed",
                    "capacity",
                );
            }
            if !summary.transport_fallback_integrity_surface_passed {
                push_reason(
                    &mut blocking_reasons,
                    &mut blocking_reason_key_counts,
                    &mut blocking_reason_family_counts,
                    "macos_transport_fallback_integrity_surface_failed",
                    "transport_fallback_integrity_surface_failed",
                    "degradation",
                );
            }
        }
    }

    degradation_hold_subjects.sort();
    degradation_hold_subjects.dedup();
    let missing_required_inputs = required_inputs
        .iter()
        .filter(|label| !present_required_inputs.contains(*label))
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
    let queue_pressure_hold_count = windows_readiness
        .summary
        .as_ref()
        .map(|summary| summary.queue_pressure_hold_count)
        .unwrap_or(0)
        .max(usize::from(
            windows_interop
                .summary
                .as_ref()
                .map(|summary| !summary.queue_pressure_surface_passed)
                .unwrap_or(false),
        ))
        + usize::from(
            macos_interop
                .summary
                .as_ref()
                .map(|summary| !summary.queue_pressure_surface_passed)
                .unwrap_or(false),
        );
    let interop_required_no_silent_fallback_profile_slugs =
        if !windows_readiness_required_no_silent_fallback_profile_slugs.is_empty() {
            windows_readiness_required_no_silent_fallback_profile_slugs.clone()
        } else if !windows_interop_required_no_silent_fallback_profile_slugs.is_empty() {
            windows_interop_required_no_silent_fallback_profile_slugs.clone()
        } else {
            macos_interop_required_no_silent_fallback_profile_slugs.clone()
        };
    let interop_profile_contract_passed =
        release_prep.summary.as_ref().is_some_and(|summary| {
            release_prep_summary_contract_valid(summary) && summary.interop_profile_contract_passed
        }) && windows_readiness.summary.as_ref().is_some_and(|summary| {
            windows_readiness_summary_contract_valid(summary)
                && summary.interop_profile_contract_passed == Some(true)
        }) && windows_interop
            .summary
            .as_ref()
            .is_some_and(interop_summary_contract_valid)
            && macos_interop
                .summary
                .as_ref()
                .is_some_and(interop_summary_contract_valid);
    if !interop_profile_contract_passed {
        push_reason(
            &mut blocking_reasons,
            &mut blocking_reason_key_counts,
            &mut blocking_reason_family_counts,
            "release_candidate_interop_profile_contract_invalid",
            "interop_profile_contract_invalid",
            "summary_contract",
        );
    }
    if queue_pressure_hold_count > 0 {
        push_reason(
            &mut blocking_reasons,
            &mut blocking_reason_key_counts,
            &mut blocking_reason_family_counts,
            "release_candidate_queue_pressure_surface_failed",
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
    let policy_disabled_fallback_surface_passed = match (
        windows_readiness
            .summary
            .as_ref()
            .and_then(|summary| summary.policy_disabled_fallback_surface_passed),
        windows_interop_policy_disabled_fallback_surface_passed,
        macos_interop
            .summary
            .as_ref()
            .map(|summary| summary.policy_disabled_fallback_surface_passed),
    ) {
        (Some(windows_readiness), Some(windows_interop), Some(macos_interop)) => {
            Some(windows_readiness && windows_interop && macos_interop)
        }
        _ => None,
    };
    let transport_fallback_integrity_surface_passed = match (
        windows_readiness
            .summary
            .as_ref()
            .and_then(|summary| summary.transport_fallback_integrity_surface_passed),
        windows_interop_transport_fallback_integrity_surface_passed,
        macos_interop
            .summary
            .as_ref()
            .map(|summary| summary.transport_fallback_integrity_surface_passed),
    ) {
        (Some(windows_readiness), Some(windows_interop), Some(macos_interop)) => {
            Some(windows_readiness && windows_interop && macos_interop)
        }
        _ => None,
    };
    let explicit_fallback_profile_count = windows_interop_explicit_fallback_profile_count.max(
        macos_interop
            .summary
            .as_ref()
            .map(|summary| summary.explicit_fallback_profile_count)
            .unwrap_or(0),
    );
    let verdict = if all_required_inputs_passed
        && blocking_reason_count == 0
        && degradation_hold_count == 0
        && queue_guard_tight_hold_count == 0
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

    UdpReleaseCandidateSignoffSummary {
        summary_version: UDP_RELEASE_CANDIDATE_SIGNOFF_SUMMARY_VERSION,
        comparison_schema: UDP_ROLLOUT_OPERATOR_VERDICT_SCHEMA,
        comparison_schema_version: UDP_ROLLOUT_OPERATOR_VERDICT_SCHEMA_VERSION,
        verdict_family: UDP_ROLLOUT_OPERATOR_VERDICT_FAMILY,
        decision_scope: UDP_ROLLOUT_DECISION_SCOPE_RELEASE_CANDIDATE_SIGNOFF,
        decision_label: "release_candidate_signoff",
        profile: "release_candidate_signoff",
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
        release_prep_present,
        release_prep_passed,
        windows_readiness_present,
        windows_readiness_passed,
        windows_interop_present,
        windows_interop_passed,
        macos_interop_present,
        macos_interop_passed,
        windows_host_label,
        interop_profile_count,
        interop_profile_slugs,
        interop_failed_profile_slugs,
        macos_interop_profile_count,
        macos_interop_profile_slugs,
        macos_interop_failed_profile_slugs,
        explicit_fallback_profile_count,
        policy_disabled_fallback_surface_passed,
        transport_fallback_integrity_surface_passed,
        degradation_hold_count,
        degradation_hold_subjects,
        queue_guard_headroom_band_counts,
        queue_guard_headroom_missing_count,
        queue_guard_tight_hold_count,
        queue_pressure_hold_count,
        queue_guard_limiting_path_counts,
        interop_required_no_silent_fallback_profile_slugs,
        interop_profile_contract_passed,
        blocking_reasons,
        blocking_reason_keys,
        blocking_reason_families,
        advisory_reasons,
    }
}

fn release_prep_summary_contract_valid(summary: &ReleasePrepSummaryInput) -> bool {
    let expected_required_inputs = vec![
        "deployment_signoff".to_owned(),
        "linux_validation".to_owned(),
        "macos_validation".to_owned(),
        "windows_validation".to_owned(),
    ];
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
    summary.summary_version == Some(UDP_RELEASE_PREP_SUMMARY_VERSION)
        && summary.comparison_schema == UDP_ROLLOUT_OPERATOR_VERDICT_SCHEMA
        && summary.comparison_schema_version == UDP_ROLLOUT_OPERATOR_VERDICT_SCHEMA_VERSION
        && summary.verdict_family == UDP_ROLLOUT_OPERATOR_VERDICT_FAMILY
        && summary.decision_scope == UDP_ROLLOUT_DECISION_SCOPE_RELEASE_PREP
        && summary.required_inputs == expected_required_inputs
        && summary.considered_inputs == expected_required_inputs
        && rollout_input_identity_consistent(
            &summary.required_inputs,
            &summary.considered_inputs,
            &summary.missing_required_inputs,
            summary.required_input_count,
        )
        && summary.required_input_missing_count == summary.missing_required_inputs.len()
        && summary.required_input_present_count <= summary.required_input_count
        && summary.required_input_passed_count <= summary.required_input_present_count
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
        && summary.queue_guard_tight_hold_count
            == summary
                .queue_guard_headroom_band_counts
                .get("tight")
                .copied()
                .unwrap_or(0)
        && summary.gate_state_reason == expected_reason
        && summary.gate_state_reason_family == expected_family
        && summary.gate_state
            == if summary.verdict == "ready" {
                "passed"
            } else {
                "blocked"
            }
        && !(summary.verdict == "ready"
            && (summary.blocking_reason_count != 0
                || summary.degradation_hold_count != 0
                || !summary.missing_required_inputs.is_empty()
                || summary.queue_guard_tight_hold_count != 0
                || summary.queue_guard_headroom_missing_count != 0
                || !summary.interop_profile_contract_passed))
}

fn windows_readiness_summary_contract_valid(summary: &WindowsReadinessSummaryInput) -> bool {
    let expected_required_inputs = vec![
        "smoke".to_owned(),
        "perf".to_owned(),
        "interop".to_owned(),
        "rollout_validation".to_owned(),
    ];
    let expected_considered_inputs = vec![
        "smoke".to_owned(),
        "perf".to_owned(),
        "interop".to_owned(),
        "rollout_validation".to_owned(),
        "active_fuzz".to_owned(),
    ];
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
    let expected_profile_slugs = udp_wan_lab_profile_slugs()
        .into_iter()
        .map(str::to_owned)
        .collect::<BTreeSet<_>>();
    let expected_required_profile_slugs = udp_wan_lab_required_no_silent_fallback_profile_slugs()
        .into_iter()
        .map(str::to_owned)
        .collect::<BTreeSet<_>>();
    let actual_profile_slugs = summary
        .interop_profile_slugs
        .iter()
        .cloned()
        .collect::<BTreeSet<_>>();
    let actual_required_profile_slugs = summary
        .interop_required_no_silent_fallback_profile_slugs
        .iter()
        .cloned()
        .collect::<BTreeSet<_>>();
    let failed_profile_slugs = summary
        .interop_failed_profile_slugs
        .iter()
        .cloned()
        .collect::<BTreeSet<_>>();
    let interop_profile_count = summary
        .interop_profile_count
        .unwrap_or(summary.interop_profile_slugs.len());
    let expected_explicit_fallback_profile_count = expected_profile_slugs
        .len()
        .saturating_sub(expected_required_profile_slugs.len());
    summary.summary_version == Some(UDP_ROLLOUT_COMPARISON_SUMMARY_VERSION)
        && summary.comparison_schema == UDP_ROLLOUT_OPERATOR_VERDICT_SCHEMA
        && summary.comparison_schema_version == UDP_ROLLOUT_OPERATOR_VERDICT_SCHEMA_VERSION
        && summary.verdict_family == UDP_ROLLOUT_OPERATOR_VERDICT_FAMILY
        && summary.decision_scope == UDP_ROLLOUT_DECISION_SCOPE_HOST
        && summary.profile == "readiness"
        && !summary.decision_label.is_empty()
        && !summary.host_label.is_empty()
        && summary.required_inputs == expected_required_inputs
        && summary.considered_inputs == expected_considered_inputs
        && rollout_input_identity_consistent(
            &summary.required_inputs,
            &summary.considered_inputs,
            &summary.missing_required_inputs,
            summary.required_input_count,
        )
        && summary.required_input_missing_count == summary.missing_required_inputs.len()
        && summary.required_input_present_count <= summary.required_input_count
        && summary.required_input_passed_count <= summary.required_input_present_count
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
        && actual_profile_slugs == expected_profile_slugs
        && actual_required_profile_slugs == expected_required_profile_slugs
        && summary.interop_profile_slugs.len() == actual_profile_slugs.len()
        && summary
            .interop_required_no_silent_fallback_profile_slugs
            .len()
            == actual_required_profile_slugs.len()
        && interop_profile_count == expected_profile_slugs.len()
        && failed_profile_slugs.is_subset(&actual_profile_slugs)
        && summary.interop_failed_profile_slugs.len() == failed_profile_slugs.len()
        && summary.explicit_fallback_profile_count == expected_explicit_fallback_profile_count
        && summary.queue_pressure_hold_count <= 1
        && summary.queue_guard_tight_hold_count
            == summary
                .queue_guard_headroom_band_counts
                .get("tight")
                .copied()
                .unwrap_or(0)
        && summary.gate_state_reason == expected_reason
        && summary.gate_state_reason_family == expected_family
        && summary.gate_state
            == if summary.verdict == "ready" {
                "passed"
            } else {
                "blocked"
            }
        && !(summary.policy_disabled_fallback_surface_passed == Some(true)
            && (!actual_profile_slugs.contains("policy-disabled-fallback")
                || failed_profile_slugs.contains("policy-disabled-fallback")
                || summary.explicit_fallback_profile_count == 0))
        && !(summary.transport_fallback_integrity_surface_passed == Some(true)
            && (summary.policy_disabled_fallback_surface_passed != Some(true)
                || summary.explicit_fallback_profile_count == 0
                || summary.queue_guard_tight_hold_count != 0))
        && !(summary.queue_pressure_hold_count == 0
            && failed_profile_slugs.contains("queue-pressure-sticky"))
        && !(summary.verdict == "ready"
            && (summary.blocking_reason_count != 0
                || summary.degradation_hold_count != 0
                || !summary.missing_required_inputs.is_empty()
                || summary.queue_guard_tight_hold_count != 0
                || summary.queue_pressure_hold_count != 0
                || summary.queue_guard_headroom_missing_count != 0
                || summary.interop_profile_contract_passed != Some(true)))
}

fn interop_summary_contract_valid(summary: &InteropLabSummaryInput) -> bool {
    let expected_profile_slugs = udp_wan_lab_profile_slugs()
        .into_iter()
        .map(str::to_owned)
        .collect::<BTreeSet<_>>();
    let expected_required_profile_slugs = udp_wan_lab_required_no_silent_fallback_profile_slugs()
        .into_iter()
        .map(str::to_owned)
        .collect::<BTreeSet<_>>();
    let actual_profile_slugs = summary
        .profile_slugs
        .iter()
        .cloned()
        .collect::<BTreeSet<_>>();
    let failed_profile_slugs = summary
        .failed_profile_slugs
        .iter()
        .cloned()
        .collect::<BTreeSet<_>>();
    let actual_required_profile_slugs = summary
        .required_no_silent_fallback_profile_slugs
        .iter()
        .cloned()
        .collect::<BTreeSet<_>>();
    let failed_required_count = summary
        .failed_profile_slugs
        .iter()
        .filter(|slug| actual_required_profile_slugs.contains(*slug))
        .count();

    summary.summary_version == Some(UDP_INTEROP_LAB_SUMMARY_VERSION)
        && actual_profile_slugs == expected_profile_slugs
        && summary.profile_count == expected_profile_slugs.len()
        && summary.profile_slugs.len() == actual_profile_slugs.len()
        && failed_profile_slugs.is_subset(&actual_profile_slugs)
        && summary.failed_profile_slugs.len() == failed_profile_slugs.len()
        && actual_required_profile_slugs == expected_required_profile_slugs
        && summary.required_no_silent_fallback_profile_count
            == expected_required_profile_slugs.len()
        && summary.required_no_silent_fallback_profile_slugs.len()
            == actual_required_profile_slugs.len()
        && summary.explicit_fallback_profile_count
            == expected_profile_slugs
                .len()
                .saturating_sub(expected_required_profile_slugs.len())
        && summary.required_no_silent_fallback_passed_count
            == summary
                .required_no_silent_fallback_profile_count
                .saturating_sub(failed_required_count)
        && (summary.all_passed == summary.failed_profile_slugs.is_empty())
        && !(summary.queue_pressure_surface_passed
            && (!actual_profile_slugs.contains("queue-pressure-sticky")
                || failed_profile_slugs.contains("queue-pressure-sticky")))
        && !(summary.policy_disabled_fallback_surface_passed
            && (!actual_profile_slugs.contains("policy-disabled-fallback")
                || failed_profile_slugs.contains("policy-disabled-fallback")
                || summary.explicit_fallback_profile_count == 0))
        && !(summary.transport_fallback_integrity_surface_passed
            && (!summary.queue_pressure_surface_passed
                || !summary.policy_disabled_fallback_surface_passed
                || summary.required_no_silent_fallback_passed_count
                    != summary.required_no_silent_fallback_profile_count
                || failed_required_count != 0))
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

fn load_release_prep_input(path: &Path) -> LoadedReleasePrepInput {
    if !path.exists() {
        return LoadedReleasePrepInput {
            present: false,
            parse_error: None,
            summary: None,
        };
    }
    match fs::read(path)
        .map_err(|error| error.to_string())
        .and_then(|bytes| {
            serde_json::from_slice::<ReleasePrepSummaryInput>(&bytes)
                .map_err(|error| error.to_string())
        }) {
        Ok(summary) => LoadedReleasePrepInput {
            present: true,
            parse_error: None,
            summary: Some(summary),
        },
        Err(error) => LoadedReleasePrepInput {
            present: true,
            parse_error: Some(error),
            summary: None,
        },
    }
}

fn load_windows_readiness_input(path: &Path) -> LoadedWindowsReadinessInput {
    if !path.exists() {
        return LoadedWindowsReadinessInput {
            present: false,
            parse_error: None,
            summary: None,
        };
    }
    match fs::read(path)
        .map_err(|error| error.to_string())
        .and_then(|bytes| {
            serde_json::from_slice::<WindowsReadinessSummaryInput>(&bytes)
                .map_err(|error| error.to_string())
        }) {
        Ok(summary) => LoadedWindowsReadinessInput {
            present: true,
            parse_error: None,
            summary: Some(summary),
        },
        Err(error) => LoadedWindowsReadinessInput {
            present: true,
            parse_error: Some(error),
            summary: None,
        },
    }
}

fn load_windows_interop_input(path: &Path) -> LoadedWindowsInteropInput {
    if !path.exists() {
        return LoadedWindowsInteropInput {
            present: false,
            parse_error: None,
            summary: None,
        };
    }
    match fs::read(path)
        .map_err(|error| error.to_string())
        .and_then(|bytes| {
            serde_json::from_slice::<InteropLabSummaryInput>(&bytes)
                .map_err(|error| error.to_string())
        }) {
        Ok(summary) => LoadedWindowsInteropInput {
            present: true,
            parse_error: None,
            summary: Some(summary),
        },
        Err(error) => LoadedWindowsInteropInput {
            present: true,
            parse_error: Some(error),
            summary: None,
        },
    }
}

fn load_macos_interop_input(path: &Path) -> LoadedMacosInteropInput {
    if !path.exists() {
        return LoadedMacosInteropInput {
            present: false,
            parse_error: None,
            summary: None,
        };
    }
    match fs::read(path)
        .map_err(|error| error.to_string())
        .and_then(|bytes| {
            serde_json::from_slice::<InteropLabSummaryInput>(&bytes)
                .map_err(|error| error.to_string())
        }) {
        Ok(summary) => LoadedMacosInteropInput {
            present: true,
            parse_error: None,
            summary: Some(summary),
        },
        Err(error) => LoadedMacosInteropInput {
            present: true,
            parse_error: Some(error),
            summary: None,
        },
    }
}

fn print_text_summary(summary: &UdpReleaseCandidateSignoffSummary, summary_path: &Path) {
    println!("Verta UDP release candidate signoff summary:");
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
        "- release_prep: present={} passed={}",
        summary.release_prep_present, summary.release_prep_passed
    );
    println!(
        "- windows_readiness: present={} passed={} host={}",
        summary.windows_readiness_present,
        summary.windows_readiness_passed,
        summary.windows_host_label.as_deref().unwrap_or("missing")
    );
    println!(
        "- windows_interop: present={} passed={}",
        summary.windows_interop_present, summary.windows_interop_passed
    );
    println!(
        "- macos_interop: present={} passed={}",
        summary.macos_interop_present, summary.macos_interop_passed
    );
    println!(
        "- explicit_fallback_profile_count: {}",
        summary.explicit_fallback_profile_count
    );
    println!(
        "- transport_fallback_integrity_surface_passed: {}",
        summary
            .transport_fallback_integrity_surface_passed
            .map(|value| value.to_string())
            .unwrap_or_else(|| "missing".to_owned())
    );
    println!(
        "- policy_disabled_fallback_surface_passed: {}",
        summary
            .policy_disabled_fallback_surface_passed
            .map(|value| value.to_string())
            .unwrap_or_else(|| "missing".to_owned())
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
    if summary.interop_profile_slugs.is_empty() {
        println!("- windows_interop_profile_slugs: none");
    } else {
        println!(
            "- windows_interop_profile_slugs: {}",
            summary.interop_profile_slugs.join(", ")
        );
    }
    if summary.interop_failed_profile_slugs.is_empty() {
        println!("- windows_interop_failed_profile_slugs: none");
    } else {
        println!(
            "- windows_interop_failed_profile_slugs: {}",
            summary.interop_failed_profile_slugs.join(", ")
        );
    }
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
    if summary.macos_interop_profile_slugs.is_empty() {
        println!("- macos_interop_profile_slugs: none");
    } else {
        println!(
            "- macos_interop_profile_slugs: {}",
            summary.macos_interop_profile_slugs.join(", ")
        );
    }
    if summary.macos_interop_failed_profile_slugs.is_empty() {
        println!("- macos_interop_failed_profile_slugs: none");
    } else {
        println!(
            "- macos_interop_failed_profile_slugs: {}",
            summary.macos_interop_failed_profile_slugs.join(", ")
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

fn parse_args<I>(mut args: I) -> Result<ReleaseCandidateSignoffArgs, String>
where
    I: Iterator<Item = String>,
{
    let mut parsed = ReleaseCandidateSignoffArgs::default();
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
            "--release-prep" => {
                parsed.release_prep =
                    Some(PathBuf::from(args.next().ok_or_else(|| {
                        "--release-prep requires a value".to_owned()
                    })?));
            }
            "--windows-readiness" => {
                parsed.windows_readiness =
                    Some(PathBuf::from(args.next().ok_or_else(|| {
                        "--windows-readiness requires a value".to_owned()
                    })?));
            }
            "--windows-interop" => {
                parsed.windows_interop =
                    Some(PathBuf::from(args.next().ok_or_else(|| {
                        "--windows-interop requires a value".to_owned()
                    })?));
            }
            "--macos-interop" => {
                parsed.macos_interop =
                    Some(PathBuf::from(args.next().ok_or_else(|| {
                        "--macos-interop requires a value".to_owned()
                    })?));
            }
            "--help" | "-h" => return Err(help_text()),
            _ => return Err(help_text()),
        }
    }
    Ok(parsed)
}

fn help_text() -> String {
    "Usage: cargo run -p ns-testkit --example udp_release_candidate_signoff -- [--format text|json] [--summary-path <path>] [--release-prep <path>] [--windows-readiness <path>] [--windows-interop <path>] [--macos-interop <path>]".to_owned()
}

fn default_release_prep_input() -> PathBuf {
    prefer_verta_input_path("udp-release-prep-summary.json")
}

fn default_windows_readiness_input() -> PathBuf {
    prefer_verta_input_path("udp-rollout-comparison-summary-windows.json")
}

fn default_windows_interop_input() -> PathBuf {
    prefer_verta_input_path("udp-interop-lab-summary-windows.json")
}

fn default_macos_interop_input() -> PathBuf {
    prefer_verta_input_path("udp-interop-lab-summary-macos.json")
}

fn default_summary_path() -> PathBuf {
    verta_output_path("udp-release-candidate-signoff-summary.json")
}

fn push_reason(
    reasons: &mut Vec<String>,
    key_counts: &mut BTreeMap<String, usize>,
    family_counts: &mut BTreeMap<String, usize>,
    code: &str,
    reason_key: &str,
    family: &'static str,
) {
    reasons.push(code.to_owned());
    *key_counts.entry(reason_key.to_owned()).or_insert(0) += 1;
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
    use ns_testkit::UDP_ROLLOUT_OPERATOR_VERDICT_SCHEMA_VERSION;

    fn all_profile_slugs() -> Vec<String> {
        udp_wan_lab_profile_slugs()
            .into_iter()
            .map(str::to_owned)
            .collect()
    }

    fn required_profile_slugs() -> Vec<String> {
        udp_wan_lab_required_no_silent_fallback_profile_slugs()
            .into_iter()
            .map(str::to_owned)
            .collect()
    }

    fn ready_release_prep() -> LoadedReleasePrepInput {
        LoadedReleasePrepInput {
            present: true,
            parse_error: None,
            summary: Some(ReleasePrepSummaryInput {
                summary_version: Some(UDP_RELEASE_PREP_SUMMARY_VERSION),
                comparison_schema: "udp_rollout_operator_verdict".to_owned(),
                comparison_schema_version: UDP_ROLLOUT_OPERATOR_VERDICT_SCHEMA_VERSION,
                verdict_family: "udp_rollout_operator_decision".to_owned(),
                decision_scope: "release_prep".to_owned(),
                verdict: "ready".to_owned(),
                evidence_state: "complete".to_owned(),
                gate_state: "passed".to_owned(),
                gate_state_reason: "all_required_inputs_passed".to_owned(),
                gate_state_reason_family: "ready".to_owned(),
                active_fuzz_required: true,
                required_inputs: vec![
                    "deployment_signoff".to_owned(),
                    "linux_validation".to_owned(),
                    "macos_validation".to_owned(),
                    "windows_validation".to_owned(),
                ],
                considered_inputs: vec![
                    "deployment_signoff".to_owned(),
                    "linux_validation".to_owned(),
                    "macos_validation".to_owned(),
                    "windows_validation".to_owned(),
                ],
                missing_required_inputs: Vec::new(),
                missing_required_input_count: 0,
                required_input_count: 4,
                required_input_missing_count: 0,
                required_input_failed_count: 0,
                required_input_unready_count: 0,
                required_input_present_count: 4,
                required_input_passed_count: 4,
                all_required_inputs_present: true,
                all_required_inputs_passed: true,
                blocking_reason_count: 0,
                blocking_reason_key_count: 0,
                blocking_reason_family_count: 0,
                blocking_reason_key_counts: BTreeMap::new(),
                blocking_reason_family_counts: BTreeMap::new(),
                degradation_hold_count: 0,
                degradation_hold_subjects: Vec::new(),
                queue_guard_headroom_band_counts: BTreeMap::from([("healthy".to_owned(), 1usize)]),
                queue_guard_headroom_missing_count: 0,
                queue_guard_limiting_path_counts: BTreeMap::from([(
                    "queue_recovery_send".to_owned(),
                    3usize,
                )]),
                queue_guard_tight_hold_count: 0,
                interop_profile_contract_passed: true,
                blocking_reasons: Vec::new(),
            }),
        }
    }

    fn ready_windows_readiness() -> LoadedWindowsReadinessInput {
        LoadedWindowsReadinessInput {
            present: true,
            parse_error: None,
            summary: Some(WindowsReadinessSummaryInput {
                summary_version: Some(UDP_ROLLOUT_COMPARISON_SUMMARY_VERSION),
                comparison_schema: "udp_rollout_operator_verdict".to_owned(),
                comparison_schema_version: UDP_ROLLOUT_OPERATOR_VERDICT_SCHEMA_VERSION,
                verdict_family: "udp_rollout_operator_decision".to_owned(),
                decision_scope: "host".to_owned(),
                decision_label: "windows_rollout_readiness".to_owned(),
                profile: "readiness".to_owned(),
                host_label: "windows-latest-readiness".to_owned(),
                verdict: "ready".to_owned(),
                evidence_state: "complete".to_owned(),
                gate_state: "passed".to_owned(),
                gate_state_reason: "all_required_inputs_passed".to_owned(),
                gate_state_reason_family: "ready".to_owned(),
                active_fuzz_required: false,
                required_inputs: vec![
                    "smoke".to_owned(),
                    "perf".to_owned(),
                    "interop".to_owned(),
                    "rollout_validation".to_owned(),
                ],
                considered_inputs: vec![
                    "smoke".to_owned(),
                    "perf".to_owned(),
                    "interop".to_owned(),
                    "rollout_validation".to_owned(),
                    "active_fuzz".to_owned(),
                ],
                missing_required_inputs: Vec::new(),
                missing_required_input_count: 0,
                required_input_count: 4,
                required_input_missing_count: 0,
                required_input_failed_count: 0,
                required_input_unready_count: 0,
                required_input_present_count: 4,
                required_input_passed_count: 4,
                all_required_inputs_present: true,
                all_required_inputs_passed: true,
                blocking_reason_count: 0,
                blocking_reason_key_count: 0,
                blocking_reason_family_count: 0,
                blocking_reason_key_counts: BTreeMap::new(),
                blocking_reason_family_counts: BTreeMap::new(),
                degradation_hold_count: 0,
                degradation_hold_subjects: Vec::new(),
                queue_guard_headroom_band_counts: BTreeMap::from([("healthy".to_owned(), 1usize)]),
                queue_guard_headroom_missing_count: 0,
                queue_guard_limiting_path: Some("queue_recovery_send".to_owned()),
                interop_profile_count: Some(all_profile_slugs().len()),
                interop_profile_slugs: all_profile_slugs(),
                interop_required_no_silent_fallback_profile_slugs: required_profile_slugs(),
                interop_failed_profile_slugs: Vec::new(),
                explicit_fallback_profile_count: 3,
                policy_disabled_fallback_surface_passed: Some(true),
                transport_fallback_integrity_surface_passed: Some(true),
                interop_profile_contract_passed: Some(true),
                queue_guard_tight_hold_count: 0,
                queue_pressure_hold_count: 0,
                blocking_reasons: Vec::new(),
            }),
        }
    }

    fn ready_windows_interop() -> LoadedWindowsInteropInput {
        LoadedWindowsInteropInput {
            present: true,
            parse_error: None,
            summary: Some(InteropLabSummaryInput {
                summary_version: Some(4),
                all_passed: true,
                profile_count: all_profile_slugs().len(),
                profile_slugs: all_profile_slugs(),
                failed_profile_slugs: Vec::new(),
                required_no_silent_fallback_profile_count: required_profile_slugs().len(),
                required_no_silent_fallback_passed_count: required_profile_slugs().len(),
                required_no_silent_fallback_profile_slugs: required_profile_slugs(),
                explicit_fallback_profile_count: 3,
                policy_disabled_fallback_surface_passed: true,
                queue_pressure_surface_passed: true,
                transport_fallback_integrity_surface_passed: true,
            }),
        }
    }

    fn ready_macos_interop() -> LoadedMacosInteropInput {
        LoadedMacosInteropInput {
            present: true,
            parse_error: None,
            summary: Some(InteropLabSummaryInput {
                summary_version: Some(4),
                all_passed: true,
                profile_count: all_profile_slugs().len(),
                profile_slugs: all_profile_slugs(),
                failed_profile_slugs: Vec::new(),
                required_no_silent_fallback_profile_count: required_profile_slugs().len(),
                required_no_silent_fallback_passed_count: required_profile_slugs().len(),
                required_no_silent_fallback_profile_slugs: required_profile_slugs(),
                explicit_fallback_profile_count: 3,
                policy_disabled_fallback_surface_passed: true,
                queue_pressure_surface_passed: true,
                transport_fallback_integrity_surface_passed: true,
            }),
        }
    }

    #[test]
    fn release_candidate_signoff_emits_ready_operator_schema() {
        let summary = build_release_candidate_signoff_summary(
            ready_release_prep(),
            ready_windows_readiness(),
            ready_windows_interop(),
            ready_macos_interop(),
        );

        assert_eq!(
            summary.summary_version,
            UDP_RELEASE_CANDIDATE_SIGNOFF_SUMMARY_VERSION
        );
        assert_eq!(
            summary.comparison_schema_version,
            UDP_ROLLOUT_OPERATOR_VERDICT_SCHEMA_VERSION
        );
        assert_eq!(summary.verdict, "ready");
        assert_eq!(summary.gate_state, "passed");
        assert_eq!(summary.gate_state_reason, "all_required_inputs_passed");
        assert_eq!(summary.gate_state_reason_family, "ready");
        assert_eq!(summary.required_input_unready_count, 0);
        assert_eq!(summary.required_input_count, 4);
        assert_eq!(summary.required_input_passed_count, 4);
        assert_eq!(summary.explicit_fallback_profile_count, 3);
        assert_eq!(summary.queue_pressure_hold_count, 0);
        assert_eq!(summary.policy_disabled_fallback_surface_passed, Some(true));
        assert_eq!(
            summary.transport_fallback_integrity_surface_passed,
            Some(true)
        );
        assert!(summary.windows_interop_present);
        assert!(summary.windows_interop_passed);
        assert!(summary.macos_interop_present);
        assert!(summary.macos_interop_passed);
        assert_eq!(
            summary.macos_interop_profile_count,
            Some(all_profile_slugs().len())
        );
        assert_eq!(
            summary.interop_profile_count,
            Some(all_profile_slugs().len())
        );
        assert_eq!(
            summary.interop_required_no_silent_fallback_profile_slugs,
            required_profile_slugs()
        );
        assert_eq!(summary.queue_guard_tight_hold_count, 0);
        assert_eq!(summary.queue_guard_headroom_missing_count, 0);
        assert!(summary.interop_profile_contract_passed);
        assert_eq!(
            summary.windows_host_label.as_deref(),
            Some("windows-latest-readiness")
        );
        assert_eq!(
            summary
                .queue_guard_headroom_band_counts
                .get("healthy")
                .copied(),
            Some(2)
        );
        assert_eq!(
            summary
                .queue_guard_limiting_path_counts
                .get("queue_recovery_send")
                .copied(),
            Some(4)
        );
    }

    #[test]
    fn release_candidate_signoff_holds_when_windows_readiness_is_missing() {
        let summary = build_release_candidate_signoff_summary(
            ready_release_prep(),
            LoadedWindowsReadinessInput {
                present: false,
                parse_error: None,
                summary: None,
            },
            ready_windows_interop(),
            ready_macos_interop(),
        );

        assert_eq!(summary.verdict, "hold");
        assert_eq!(summary.gate_state, "blocked");
        assert_eq!(summary.gate_state_reason, "missing_required_inputs");
        assert_eq!(summary.gate_state_reason_family, "summary_presence");
        assert_eq!(summary.required_input_missing_count, 1);
        assert_eq!(summary.required_input_unready_count, 0);
        assert!(
            summary
                .missing_required_inputs
                .iter()
                .any(|value| value == "windows_readiness")
        );
    }

    #[test]
    fn release_candidate_signoff_holds_when_windows_interop_policy_surface_fails() {
        let mut windows_interop = ready_windows_interop();
        let summary = windows_interop
            .summary
            .as_mut()
            .expect("summary should exist");
        summary.all_passed = false;
        summary.failed_profile_slugs = vec!["policy-disabled-fallback".to_owned()];
        summary.policy_disabled_fallback_surface_passed = false;
        summary.transport_fallback_integrity_surface_passed = false;

        let summary = build_release_candidate_signoff_summary(
            ready_release_prep(),
            ready_windows_readiness(),
            windows_interop,
            ready_macos_interop(),
        );

        assert_eq!(summary.verdict, "hold");
        assert_eq!(summary.gate_state, "blocked");
        assert_eq!(summary.required_input_missing_count, 0);
        assert_eq!(summary.required_input_unready_count, 1);
        assert_eq!(summary.gate_state_reason, "required_inputs_unready");
        assert_eq!(summary.gate_state_reason_family, "gating");
        assert_eq!(summary.policy_disabled_fallback_surface_passed, Some(false));
        assert_eq!(
            summary.transport_fallback_integrity_surface_passed,
            Some(false)
        );
        assert!(
            summary
                .blocking_reasons
                .iter()
                .any(|reason| reason == "windows_policy_disabled_fallback_surface_failed")
        );
        assert!(
            summary
                .blocking_reasons
                .iter()
                .any(|reason| reason == "windows_transport_fallback_integrity_surface_failed")
        );
        assert!(
            summary
                .interop_failed_profile_slugs
                .iter()
                .any(|slug| slug == "policy-disabled-fallback")
        );
    }

    #[test]
    fn release_candidate_signoff_holds_when_macos_interop_is_missing() {
        let summary = build_release_candidate_signoff_summary(
            ready_release_prep(),
            ready_windows_readiness(),
            ready_windows_interop(),
            LoadedMacosInteropInput {
                present: false,
                parse_error: None,
                summary: None,
            },
        );

        assert_eq!(summary.verdict, "hold");
        assert_eq!(summary.gate_state, "blocked");
        assert_eq!(summary.required_input_missing_count, 1);
        assert!(
            summary
                .missing_required_inputs
                .iter()
                .any(|value| value == "macos_interop")
        );
    }
}
