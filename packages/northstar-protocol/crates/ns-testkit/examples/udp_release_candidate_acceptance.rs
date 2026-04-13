use ns_testkit::{
    UDP_INTEROP_PROFILE_CATALOG_SOURCE_LANE_COMPATIBLE_HOST, UDP_ROLLOUT_DECISION_SCOPE_HOST,
    UDP_ROLLOUT_DECISION_SCOPE_RELEASE_CANDIDATE_ACCEPTANCE,
    UDP_ROLLOUT_DECISION_SCOPE_RELEASE_CANDIDATE_READINESS, UDP_ROLLOUT_OPERATOR_VERDICT_FAMILY,
    UDP_ROLLOUT_OPERATOR_VERDICT_SCHEMA, UDP_ROLLOUT_OPERATOR_VERDICT_SCHEMA_VERSION,
    blocking_reason_accounting_consistent, repo_root, rollout_queue_hold_host_count,
    rollout_queue_hold_input_count, rollout_queue_hold_present, summarize_rollout_gate_state,
    udp_wan_lab_profile_slugs, udp_wan_lab_required_no_silent_fallback_profile_slugs,
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
struct ReleaseCandidateAcceptanceArgs {
    format: Option<OutputFormat>,
    summary_path: Option<PathBuf>,
    release_candidate_readiness: Option<PathBuf>,
    linux_readiness: Option<PathBuf>,
    macos_readiness: Option<PathBuf>,
    windows_readiness: Option<PathBuf>,
}

const UDP_RELEASE_CANDIDATE_READINESS_SUMMARY_VERSION: u8 = 1;
const UDP_ROLLOUT_COMPARISON_SUMMARY_VERSION: u8 = 14;
const UDP_RELEASE_CANDIDATE_ACCEPTANCE_SUMMARY_VERSION: u8 = 1;

#[derive(Debug, Deserialize)]
struct ReleaseCandidateReadinessSummaryInput {
    #[serde(default)]
    summary_version: Option<u8>,
    comparison_schema: String,
    comparison_schema_version: u8,
    verdict_family: String,
    decision_scope: String,
    decision_label: String,
    profile: String,
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
    release_candidate_stabilization_present: bool,
    release_candidate_stabilization_passed: bool,
    readiness_count: usize,
    readiness_passed_count: usize,
    readiness_failed_count: usize,
    #[serde(default)]
    readiness_labels: Vec<String>,
    #[serde(default)]
    readiness_host_labels: Vec<String>,
    #[serde(default)]
    degradation_hold_count: usize,
    #[serde(default)]
    degradation_hold_subjects: Vec<String>,
    #[serde(default)]
    queue_guard_headroom_missing_count: usize,
    #[serde(default)]
    queue_guard_tight_hold_count: usize,
    #[serde(default)]
    queue_pressure_hold_count: usize,
    #[serde(default)]
    queue_hold_input_count: usize,
    #[serde(default)]
    queue_hold_host_count: usize,
    #[serde(default)]
    interop_required_no_silent_fallback_profile_slugs: Vec<String>,
    #[serde(default)]
    interop_failed_profile_slugs: Vec<String>,
    #[serde(default)]
    interop_failed_profile_count: usize,
    #[serde(default)]
    explicit_fallback_profile_count: usize,
    interop_profile_contract_passed: bool,
    interop_profile_catalog_contract_passed: bool,
    interop_profile_catalog_schema_version: u8,
    #[serde(default)]
    interop_profile_catalog_host_labels: Vec<String>,
    #[serde(default)]
    interop_profile_catalog_source_lane: String,
    #[serde(default)]
    udp_blocked_fallback_surface_passed: Option<bool>,
    #[serde(default)]
    policy_disabled_fallback_surface_passed: Option<bool>,
    #[serde(default)]
    policy_disabled_fallback_round_trip_stable: Option<bool>,
    #[serde(default)]
    transport_fallback_integrity_surface_passed: Option<bool>,
    #[serde(default)]
    blocking_reasons: Vec<String>,
    #[serde(default)]
    blocking_reason_keys: Vec<String>,
    #[serde(default)]
    blocking_reason_families: Vec<String>,
}

#[derive(Debug, Deserialize)]
struct ReadinessSummaryInput {
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
    queue_guard_headroom_missing_count: usize,
    #[serde(default)]
    queue_guard_tight_hold_count: usize,
    #[serde(default)]
    queue_pressure_hold_count: usize,
    #[serde(default)]
    interop_required_no_silent_fallback_profile_slugs: Vec<String>,
    #[serde(default)]
    udp_blocked_fallback_surface_passed: Option<bool>,
    #[serde(default)]
    policy_disabled_fallback_surface_passed: Option<bool>,
    #[serde(default)]
    policy_disabled_fallback_round_trip_stable: Option<bool>,
    #[serde(default)]
    transport_fallback_integrity_surface_passed: Option<bool>,
    #[serde(default)]
    interop_profile_contract_passed: Option<bool>,
    #[serde(default)]
    blocking_reasons: Vec<String>,
    #[serde(default)]
    blocking_reason_keys: Vec<String>,
    #[serde(default)]
    blocking_reason_families: Vec<String>,
}

#[derive(Debug)]
struct LoadedInput<T> {
    label: String,
    present: bool,
    parse_error: Option<String>,
    summary: Option<T>,
}

type LoadedReleaseCandidateReadinessInput = LoadedInput<ReleaseCandidateReadinessSummaryInput>;
type LoadedReadinessInput = LoadedInput<ReadinessSummaryInput>;

#[derive(Debug, Serialize)]
struct UdpReleaseCandidateAcceptanceSummary {
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
    release_candidate_readiness_present: bool,
    release_candidate_readiness_passed: bool,
    readiness_count: usize,
    readiness_passed_count: usize,
    readiness_failed_count: usize,
    readiness_labels: Vec<String>,
    readiness_host_labels: Vec<String>,
    degradation_hold_count: usize,
    degradation_hold_subjects: Vec<String>,
    queue_guard_headroom_missing_count: usize,
    queue_guard_tight_hold_count: usize,
    queue_pressure_hold_count: usize,
    queue_hold_input_count: usize,
    queue_hold_host_count: usize,
    interop_required_no_silent_fallback_profile_slugs: Vec<String>,
    interop_failed_profile_slugs: Vec<String>,
    interop_failed_profile_count: usize,
    explicit_fallback_profile_count: usize,
    interop_profile_contract_passed: bool,
    interop_profile_catalog_contract_passed: bool,
    interop_profile_catalog_schema_version: u8,
    interop_profile_catalog_host_labels: Vec<String>,
    interop_profile_catalog_source_lane: String,
    udp_blocked_fallback_surface_passed: Option<bool>,
    policy_disabled_fallback_surface_passed: Option<bool>,
    policy_disabled_fallback_round_trip_stable: Option<bool>,
    transport_fallback_integrity_surface_passed: Option<bool>,
    blocking_reasons: Vec<String>,
    blocking_reason_keys: Vec<String>,
    blocking_reason_families: Vec<String>,
}

fn main() -> Result<(), Box<dyn std::error::Error>> {
    let args = parse_args(env::args().skip(1))?;
    let summary = build_release_candidate_acceptance_summary(
        load_input::<ReleaseCandidateReadinessSummaryInput>(
            "release_candidate_readiness",
            &args
                .release_candidate_readiness
                .unwrap_or_else(default_release_candidate_readiness_input),
        ),
        vec![
            load_input::<ReadinessSummaryInput>(
                "linux_readiness",
                &args
                    .linux_readiness
                    .unwrap_or_else(default_linux_readiness_input),
            ),
            load_input::<ReadinessSummaryInput>(
                "macos_readiness",
                &args
                    .macos_readiness
                    .unwrap_or_else(default_macos_readiness_input),
            ),
            load_input::<ReadinessSummaryInput>(
                "windows_readiness",
                &args
                    .windows_readiness
                    .unwrap_or_else(default_windows_readiness_input),
            ),
        ],
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
        return Err("udp release candidate acceptance is not ready".into());
    }

    Ok(())
}

fn build_release_candidate_acceptance_summary(
    release_candidate_readiness: LoadedReleaseCandidateReadinessInput,
    readiness_inputs: Vec<LoadedReadinessInput>,
) -> UdpReleaseCandidateAcceptanceSummary {
    let required_inputs = vec![
        "release_candidate_readiness".to_owned(),
        "linux_readiness".to_owned(),
        "macos_readiness".to_owned(),
        "windows_readiness".to_owned(),
    ];
    let considered_inputs = required_inputs.clone();
    let expected_required_profile_set = udp_wan_lab_required_no_silent_fallback_profile_slugs()
        .into_iter()
        .map(str::to_owned)
        .collect::<BTreeSet<_>>();
    let expected_catalog_host_labels =
        vec!["linux".to_owned(), "macos".to_owned(), "windows".to_owned()];
    let expected_readiness_labels = vec![
        "linux_readiness".to_owned(),
        "macos_readiness".to_owned(),
        "windows_readiness".to_owned(),
    ];

    let mut present_required_inputs = BTreeSet::new();
    let mut passed_required_inputs = BTreeSet::new();
    let mut blocking_reasons = Vec::new();
    let mut blocking_reason_key_counts = BTreeMap::new();
    let mut blocking_reason_family_counts = BTreeMap::new();
    let mut degradation_hold_subjects = Vec::new();
    let mut queue_guard_headroom_missing_count = 0usize;
    let mut queue_guard_tight_hold_count = 0usize;
    let mut queue_pressure_hold_count = 0usize;
    let mut queue_hold_inputs = Vec::new();
    let mut queue_hold_hosts = Vec::new();
    let mut interop_required_profile_set = BTreeSet::new();
    let mut interop_failed_profile_set = BTreeSet::new();
    let mut readiness_labels = Vec::new();
    let mut readiness_host_labels = Vec::new();
    let mut readiness_passed_count = 0usize;
    let mut all_consumed_inputs_contract_valid = true;
    let mut explicit_fallback_profile_count = 0usize;
    let mut interop_profile_catalog_schema_version = 0u8;
    let mut interop_profile_catalog_host_labels = Vec::new();
    let mut interop_profile_catalog_source_lane = String::new();
    let mut udp_blocked_fallback_surface_passed = Some(true);
    let mut policy_disabled_fallback_surface_passed = Some(true);
    let mut policy_disabled_fallback_round_trip_stable = Some(true);
    let mut transport_fallback_integrity_surface_passed = Some(true);

    let release_candidate_readiness_present = release_candidate_readiness.present;
    if release_candidate_readiness_present {
        present_required_inputs.insert("release_candidate_readiness".to_owned());
    }
    let release_candidate_readiness_passed = if let Some(summary) =
        release_candidate_readiness.summary.as_ref()
    {
        queue_guard_headroom_missing_count += summary.queue_guard_headroom_missing_count;
        queue_guard_tight_hold_count += summary.queue_guard_tight_hold_count;
        queue_pressure_hold_count += summary.queue_pressure_hold_count;
        queue_hold_inputs.push((
            summary.queue_guard_headroom_missing_count,
            summary.queue_guard_tight_hold_count,
            summary.queue_pressure_hold_count,
        ));
        interop_required_profile_set.extend(
            summary
                .interop_required_no_silent_fallback_profile_slugs
                .iter()
                .cloned(),
        );
        interop_failed_profile_set.extend(summary.interop_failed_profile_slugs.iter().cloned());
        explicit_fallback_profile_count =
            explicit_fallback_profile_count.max(summary.explicit_fallback_profile_count);
        interop_profile_catalog_schema_version = summary.interop_profile_catalog_schema_version;
        interop_profile_catalog_host_labels = summary.interop_profile_catalog_host_labels.clone();
        interop_profile_catalog_source_lane = summary.interop_profile_catalog_source_lane.clone();
        udp_blocked_fallback_surface_passed = summary.udp_blocked_fallback_surface_passed;
        policy_disabled_fallback_surface_passed = summary.policy_disabled_fallback_surface_passed;
        policy_disabled_fallback_round_trip_stable =
            summary.policy_disabled_fallback_round_trip_stable;
        transport_fallback_integrity_surface_passed =
            summary.transport_fallback_integrity_surface_passed;
        if summary.degradation_hold_count > 0 {
            degradation_hold_subjects.push("release_candidate_readiness".to_owned());
            degradation_hold_subjects.extend(summary.degradation_hold_subjects.iter().cloned());
        }

        if release_candidate_readiness_summary_contract_valid(summary)
            && summary.verdict == "ready"
            && summary.evidence_state == "complete"
            && summary.gate_state == "passed"
            && summary.active_fuzz_required
            && summary.all_required_inputs_present
            && summary.all_required_inputs_passed
            && summary.blocking_reason_count == 0
            && summary.degradation_hold_count == 0
            && summary.queue_hold_input_count == 0
            && summary.queue_hold_host_count == 0
            && !rollout_queue_hold_present(
                summary.queue_guard_headroom_missing_count,
                summary.queue_guard_tight_hold_count,
                summary.queue_pressure_hold_count,
            )
            && summary.readiness_count == 3
            && summary.readiness_passed_count == 3
            && summary.readiness_failed_count == 0
            && summary.readiness_labels == expected_readiness_labels
            && summary.readiness_host_labels == expected_catalog_host_labels
            && summary.udp_blocked_fallback_surface_passed == Some(true)
            && summary.policy_disabled_fallback_surface_passed == Some(true)
            && summary.policy_disabled_fallback_round_trip_stable == Some(true)
            && summary.transport_fallback_integrity_surface_passed == Some(true)
            && summary.interop_profile_contract_passed
            && summary.interop_profile_catalog_contract_passed
            && summary.interop_profile_catalog_schema_version == 1
            && summary.interop_profile_catalog_host_labels == expected_catalog_host_labels
            && summary.interop_profile_catalog_source_lane
                == UDP_INTEROP_PROFILE_CATALOG_SOURCE_LANE_COMPATIBLE_HOST
            && summary.interop_failed_profile_count == 0
        {
            passed_required_inputs.insert("release_candidate_readiness".to_owned());
            true
        } else {
            false
        }
    } else {
        false
    };

    if !release_candidate_readiness.present {
        udp_blocked_fallback_surface_passed = None;
        policy_disabled_fallback_surface_passed = None;
        policy_disabled_fallback_round_trip_stable = None;
        transport_fallback_integrity_surface_passed = None;
        push_reason(
            &mut blocking_reasons,
            &mut blocking_reason_key_counts,
            &mut blocking_reason_family_counts,
            "missing_release_candidate_readiness_summary",
            "missing_required_input",
            "summary_presence",
        );
    } else if let Some(error) = release_candidate_readiness.parse_error.as_ref() {
        all_consumed_inputs_contract_valid = false;
        udp_blocked_fallback_surface_passed = None;
        policy_disabled_fallback_surface_passed = None;
        policy_disabled_fallback_round_trip_stable = None;
        transport_fallback_integrity_surface_passed = None;
        push_reason(
            &mut blocking_reasons,
            &mut blocking_reason_key_counts,
            &mut blocking_reason_family_counts,
            &format!("release_candidate_readiness_parse_error:{error}"),
            "input_parse_error",
            "summary_contract",
        );
    } else if let Some(summary) = release_candidate_readiness.summary.as_ref() {
        if summary.interop_profile_catalog_source_lane
            != UDP_INTEROP_PROFILE_CATALOG_SOURCE_LANE_COMPATIBLE_HOST
        {
            all_consumed_inputs_contract_valid = false;
            push_reason(
                &mut blocking_reasons,
                &mut blocking_reason_key_counts,
                &mut blocking_reason_family_counts,
                "release_candidate_acceptance_interop_catalog_source_lane_invalid",
                "interop_catalog_source_lane_invalid",
                "summary_contract",
            );
        } else if summary.interop_failed_profile_count != summary.interop_failed_profile_slugs.len()
        {
            all_consumed_inputs_contract_valid = false;
            push_reason(
                &mut blocking_reasons,
                &mut blocking_reason_key_counts,
                &mut blocking_reason_family_counts,
                "release_candidate_acceptance_interop_failed_profile_count_inconsistent",
                "interop_failed_profile_count_inconsistent",
                "summary_contract",
            );
        } else if summary.interop_profile_contract_passed
            && (summary.interop_failed_profile_count != 0
                || !summary.interop_failed_profile_slugs.is_empty())
        {
            all_consumed_inputs_contract_valid = false;
            push_reason(
                &mut blocking_reasons,
                &mut blocking_reason_key_counts,
                &mut blocking_reason_family_counts,
                "release_candidate_acceptance_interop_profile_passed_contract_inconsistent",
                "interop_profile_passed_contract_inconsistent",
                "summary_contract",
            );
        } else if summary.policy_disabled_fallback_round_trip_stable == Some(true)
            && (summary.policy_disabled_fallback_surface_passed != Some(true)
                || summary.udp_blocked_fallback_surface_passed != Some(true)
                || summary.transport_fallback_integrity_surface_passed != Some(true))
        {
            all_consumed_inputs_contract_valid = false;
            push_reason(
                &mut blocking_reasons,
                &mut blocking_reason_key_counts,
                &mut blocking_reason_family_counts,
                "release_candidate_acceptance_policy_disabled_fallback_round_trip_contract_inconsistent",
                "policy_disabled_fallback_round_trip_contract_inconsistent",
                "summary_contract",
            );
        } else if summary.interop_profile_catalog_host_labels != expected_catalog_host_labels {
            all_consumed_inputs_contract_valid = false;
            push_reason(
                &mut blocking_reasons,
                &mut blocking_reason_key_counts,
                &mut blocking_reason_family_counts,
                "release_candidate_acceptance_interop_catalog_host_label_set_invalid",
                "interop_catalog_host_label_set_invalid",
                "summary_contract",
            );
        } else if !release_candidate_readiness_summary_contract_valid(summary) {
            all_consumed_inputs_contract_valid = false;
            push_reason(
                &mut blocking_reasons,
                &mut blocking_reason_key_counts,
                &mut blocking_reason_family_counts,
                "release_candidate_readiness_summary_contract_invalid",
                "input_contract_invalid",
                "summary_contract",
            );
        } else if !release_candidate_readiness_passed {
            push_reason(
                &mut blocking_reasons,
                &mut blocking_reason_key_counts,
                &mut blocking_reason_family_counts,
                "release_candidate_readiness_not_ready",
                "input_not_ready",
                if rollout_queue_hold_present(
                    summary.queue_guard_headroom_missing_count,
                    summary.queue_guard_tight_hold_count,
                    summary.queue_pressure_hold_count,
                ) || summary.queue_hold_input_count > 0
                    || summary.queue_hold_host_count > 0
                {
                    "capacity"
                } else if summary.degradation_hold_count > 0 {
                    "degradation"
                } else {
                    "gating"
                },
            );
        }
    }

    for input in readiness_inputs {
        readiness_labels.push(input.label.clone());
        if input.present {
            present_required_inputs.insert(input.label.clone());
        }
        let passed = if let Some(summary) = input.summary.as_ref() {
            queue_guard_headroom_missing_count += summary.queue_guard_headroom_missing_count;
            queue_guard_tight_hold_count += summary.queue_guard_tight_hold_count;
            queue_pressure_hold_count += summary.queue_pressure_hold_count;
            queue_hold_inputs.push((
                summary.queue_guard_headroom_missing_count,
                summary.queue_guard_tight_hold_count,
                summary.queue_pressure_hold_count,
            ));
            queue_hold_hosts.push((
                summary.queue_guard_headroom_missing_count,
                summary.queue_guard_tight_hold_count,
                summary.queue_pressure_hold_count,
            ));
            interop_required_profile_set.extend(
                summary
                    .interop_required_no_silent_fallback_profile_slugs
                    .iter()
                    .cloned(),
            );
            readiness_host_labels.push(summary.host_label.clone());
            if summary.udp_blocked_fallback_surface_passed == Some(false) {
                udp_blocked_fallback_surface_passed = Some(false);
            } else if summary.udp_blocked_fallback_surface_passed.is_none() {
                udp_blocked_fallback_surface_passed = None;
            }
            if summary.policy_disabled_fallback_surface_passed == Some(false) {
                policy_disabled_fallback_surface_passed = Some(false);
            } else if summary.policy_disabled_fallback_surface_passed.is_none() {
                policy_disabled_fallback_surface_passed = None;
            }
            if summary.policy_disabled_fallback_round_trip_stable == Some(false) {
                policy_disabled_fallback_round_trip_stable = Some(false);
            } else if summary.policy_disabled_fallback_round_trip_stable.is_none() {
                policy_disabled_fallback_round_trip_stable = None;
            }
            if summary.transport_fallback_integrity_surface_passed == Some(false) {
                transport_fallback_integrity_surface_passed = Some(false);
            } else if summary
                .transport_fallback_integrity_surface_passed
                .is_none()
            {
                transport_fallback_integrity_surface_passed = None;
            }
            if readiness_summary_contract_valid(summary)
                && summary.verdict == "ready"
                && summary.evidence_state == "complete"
                && summary.gate_state == "passed"
                && summary.all_required_inputs_present
                && summary.all_required_inputs_passed
                && summary.blocking_reason_count == 0
                && summary.degradation_hold_count == 0
                && !rollout_queue_hold_present(
                    summary.queue_guard_headroom_missing_count,
                    summary.queue_guard_tight_hold_count,
                    summary.queue_pressure_hold_count,
                )
                && summary.udp_blocked_fallback_surface_passed == Some(true)
                && summary.policy_disabled_fallback_surface_passed == Some(true)
                && summary.policy_disabled_fallback_round_trip_stable == Some(true)
                && summary.transport_fallback_integrity_surface_passed == Some(true)
                && summary.interop_profile_contract_passed == Some(true)
            {
                passed_required_inputs.insert(input.label.clone());
                readiness_passed_count += 1;
                true
            } else {
                false
            }
        } else {
            false
        };

        if !input.present {
            udp_blocked_fallback_surface_passed = None;
            policy_disabled_fallback_surface_passed = None;
            policy_disabled_fallback_round_trip_stable = None;
            transport_fallback_integrity_surface_passed = None;
            push_reason(
                &mut blocking_reasons,
                &mut blocking_reason_key_counts,
                &mut blocking_reason_family_counts,
                &format!("missing_{}", input.label),
                "missing_required_input",
                "summary_presence",
            );
        } else if let Some(error) = input.parse_error.as_ref() {
            all_consumed_inputs_contract_valid = false;
            udp_blocked_fallback_surface_passed = None;
            policy_disabled_fallback_surface_passed = None;
            policy_disabled_fallback_round_trip_stable = None;
            transport_fallback_integrity_surface_passed = None;
            push_reason(
                &mut blocking_reasons,
                &mut blocking_reason_key_counts,
                &mut blocking_reason_family_counts,
                &format!("{}_parse_error:{error}", input.label),
                "input_parse_error",
                "summary_contract",
            );
        } else if let Some(summary) = input.summary.as_ref() {
            if !readiness_summary_contract_valid(summary) {
                all_consumed_inputs_contract_valid = false;
                push_reason(
                    &mut blocking_reasons,
                    &mut blocking_reason_key_counts,
                    &mut blocking_reason_family_counts,
                    &format!("{}_summary_contract_invalid", input.label),
                    "input_contract_invalid",
                    "summary_contract",
                );
            } else if !passed {
                if summary.degradation_hold_count > 0 {
                    degradation_hold_subjects.push(input.label.clone());
                    degradation_hold_subjects
                        .extend(summary.degradation_hold_subjects.iter().cloned());
                }
                push_reason(
                    &mut blocking_reasons,
                    &mut blocking_reason_key_counts,
                    &mut blocking_reason_family_counts,
                    &format!("{}_not_ready", input.label),
                    "input_not_ready",
                    if rollout_queue_hold_present(
                        summary.queue_guard_headroom_missing_count,
                        summary.queue_guard_tight_hold_count,
                        summary.queue_pressure_hold_count,
                    ) {
                        "capacity"
                    } else if summary.degradation_hold_count > 0 {
                        "degradation"
                    } else {
                        "gating"
                    },
                );
            }
        }
    }

    readiness_labels.sort();
    readiness_host_labels.sort();
    readiness_host_labels.dedup();
    interop_profile_catalog_host_labels.sort();
    degradation_hold_subjects.sort();
    degradation_hold_subjects.dedup();
    let degradation_hold_count = degradation_hold_subjects.len();
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
    let interop_required_no_silent_fallback_profile_slugs =
        interop_required_profile_set.into_iter().collect::<Vec<_>>();
    let interop_failed_profile_slugs = interop_failed_profile_set.into_iter().collect::<Vec<_>>();
    let interop_failed_profile_count = interop_failed_profile_slugs.len();

    if readiness_host_labels != expected_catalog_host_labels {
        all_consumed_inputs_contract_valid = false;
        push_reason(
            &mut blocking_reasons,
            &mut blocking_reason_key_counts,
            &mut blocking_reason_family_counts,
            "release_candidate_acceptance_readiness_host_label_set_invalid",
            "readiness_host_label_set_invalid",
            "summary_contract",
        );
    }

    let interop_profile_catalog_contract_passed = release_candidate_readiness
        .summary
        .as_ref()
        .is_some_and(|summary| {
            release_candidate_readiness_summary_contract_valid(summary)
                && summary.interop_profile_catalog_contract_passed
        })
        && interop_profile_catalog_schema_version == 1
        && interop_profile_catalog_host_labels == expected_catalog_host_labels
        && interop_profile_catalog_source_lane
            == UDP_INTEROP_PROFILE_CATALOG_SOURCE_LANE_COMPATIBLE_HOST;
    if !interop_profile_catalog_contract_passed {
        push_reason(
            &mut blocking_reasons,
            &mut blocking_reason_key_counts,
            &mut blocking_reason_family_counts,
            "release_candidate_acceptance_interop_profile_catalog_contract_invalid",
            "interop_profile_catalog_contract_invalid",
            "summary_contract",
        );
    }

    let interop_profile_contract_passed =
        release_candidate_readiness
            .summary
            .as_ref()
            .is_some_and(|summary| {
                release_candidate_readiness_summary_contract_valid(summary)
                    && summary.interop_profile_contract_passed
            })
            && interop_profile_catalog_contract_passed
            && interop_required_no_silent_fallback_profile_slugs
                == expected_required_profile_set
                    .iter()
                    .cloned()
                    .collect::<Vec<_>>()
            && interop_failed_profile_count == 0;
    if !interop_profile_contract_passed {
        push_reason(
            &mut blocking_reasons,
            &mut blocking_reason_key_counts,
            &mut blocking_reason_family_counts,
            "release_candidate_acceptance_interop_profile_contract_invalid",
            "interop_profile_contract_invalid",
            "summary_contract",
        );
    }
    if interop_required_no_silent_fallback_profile_slugs
        != expected_required_profile_set
            .iter()
            .cloned()
            .collect::<Vec<_>>()
    {
        push_reason(
            &mut blocking_reasons,
            &mut blocking_reason_key_counts,
            &mut blocking_reason_family_counts,
            "release_candidate_acceptance_interop_required_no_silent_fallback_profile_set_mismatch",
            "interop_required_no_silent_fallback_profile_set_mismatch",
            "summary_contract",
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
    if queue_pressure_hold_count > 0 {
        push_reason(
            &mut blocking_reasons,
            &mut blocking_reason_key_counts,
            &mut blocking_reason_family_counts,
            "release_candidate_acceptance_queue_pressure_surface_failed",
            "queue_pressure_surface_failed",
            "capacity",
        );
    }
    let queue_hold_input_count = rollout_queue_hold_input_count(queue_hold_inputs.iter().copied());
    let queue_hold_host_count = rollout_queue_hold_host_count(queue_hold_hosts.iter().copied());
    if queue_hold_input_count > 0 {
        push_reason(
            &mut blocking_reasons,
            &mut blocking_reason_key_counts,
            &mut blocking_reason_family_counts,
            "release_candidate_acceptance_queue_hold_inputs_present",
            "queue_hold_input_present",
            "capacity",
        );
    }
    if queue_hold_host_count > 0 {
        push_reason(
            &mut blocking_reasons,
            &mut blocking_reason_key_counts,
            &mut blocking_reason_family_counts,
            "release_candidate_acceptance_queue_hold_hosts_present",
            "queue_hold_host_present",
            "capacity",
        );
    }
    if udp_blocked_fallback_surface_passed == Some(false) {
        push_reason(
            &mut blocking_reasons,
            &mut blocking_reason_key_counts,
            &mut blocking_reason_family_counts,
            "release_candidate_acceptance_udp_blocked_fallback_surface_failed",
            "udp_blocked_fallback_surface_failed",
            "transport_integrity",
        );
    }
    if policy_disabled_fallback_surface_passed == Some(false) {
        push_reason(
            &mut blocking_reasons,
            &mut blocking_reason_key_counts,
            &mut blocking_reason_family_counts,
            "release_candidate_acceptance_policy_disabled_fallback_surface_failed",
            "policy_disabled_fallback_surface_failed",
            "transport_integrity",
        );
    }
    if policy_disabled_fallback_round_trip_stable == Some(false) {
        push_reason(
            &mut blocking_reasons,
            &mut blocking_reason_key_counts,
            &mut blocking_reason_family_counts,
            "release_candidate_acceptance_policy_disabled_fallback_round_trip_surface_failed",
            "policy_disabled_fallback_round_trip_surface_failed",
            "transport_integrity",
        );
    }
    if policy_disabled_fallback_round_trip_stable == Some(true)
        && (policy_disabled_fallback_surface_passed != Some(true)
            || udp_blocked_fallback_surface_passed != Some(true)
            || transport_fallback_integrity_surface_passed != Some(true))
    {
        all_consumed_inputs_contract_valid = false;
        push_reason(
            &mut blocking_reasons,
            &mut blocking_reason_key_counts,
            &mut blocking_reason_family_counts,
            "release_candidate_acceptance_policy_disabled_fallback_round_trip_contract_inconsistent",
            "policy_disabled_fallback_round_trip_contract_inconsistent",
            "summary_contract",
        );
    }
    if transport_fallback_integrity_surface_passed == Some(false) {
        push_reason(
            &mut blocking_reasons,
            &mut blocking_reason_key_counts,
            &mut blocking_reason_family_counts,
            "release_candidate_acceptance_transport_fallback_integrity_surface_failed",
            "transport_fallback_integrity_surface_failed",
            "transport_integrity",
        );
    }

    let blocking_reason_count = blocking_reasons.len();
    let blocking_reason_key_count = blocking_reason_key_counts.len();
    let blocking_reason_family_count = blocking_reason_family_counts.len();
    let evidence_state = if all_required_inputs_present && all_consumed_inputs_contract_valid {
        "complete"
    } else {
        "incomplete"
    };
    let verdict = if all_required_inputs_passed
        && all_consumed_inputs_contract_valid
        && blocking_reason_count == 0
        && degradation_hold_count == 0
        && !rollout_queue_hold_present(
            queue_guard_headroom_missing_count,
            queue_guard_tight_hold_count,
            queue_pressure_hold_count,
        )
        && queue_hold_input_count == 0
        && queue_hold_host_count == 0
        && udp_blocked_fallback_surface_passed == Some(true)
        && policy_disabled_fallback_surface_passed == Some(true)
        && policy_disabled_fallback_round_trip_stable == Some(true)
        && transport_fallback_integrity_surface_passed == Some(true)
        && interop_profile_contract_passed
        && interop_profile_catalog_contract_passed
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

    UdpReleaseCandidateAcceptanceSummary {
        summary_version: UDP_RELEASE_CANDIDATE_ACCEPTANCE_SUMMARY_VERSION,
        comparison_schema: UDP_ROLLOUT_OPERATOR_VERDICT_SCHEMA,
        comparison_schema_version: UDP_ROLLOUT_OPERATOR_VERDICT_SCHEMA_VERSION,
        verdict_family: UDP_ROLLOUT_OPERATOR_VERDICT_FAMILY,
        decision_scope: UDP_ROLLOUT_DECISION_SCOPE_RELEASE_CANDIDATE_ACCEPTANCE,
        decision_label: "release_candidate_acceptance",
        profile: "release_candidate_acceptance",
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
        release_candidate_readiness_present,
        release_candidate_readiness_passed,
        readiness_count: readiness_labels.len(),
        readiness_passed_count,
        readiness_failed_count: readiness_labels
            .len()
            .saturating_sub(readiness_passed_count),
        readiness_labels,
        readiness_host_labels,
        degradation_hold_count,
        degradation_hold_subjects,
        queue_guard_headroom_missing_count,
        queue_guard_tight_hold_count,
        queue_pressure_hold_count,
        queue_hold_input_count,
        queue_hold_host_count,
        interop_required_no_silent_fallback_profile_slugs,
        interop_failed_profile_slugs,
        interop_failed_profile_count,
        explicit_fallback_profile_count,
        interop_profile_contract_passed,
        interop_profile_catalog_contract_passed,
        interop_profile_catalog_schema_version,
        interop_profile_catalog_host_labels,
        interop_profile_catalog_source_lane,
        udp_blocked_fallback_surface_passed,
        policy_disabled_fallback_surface_passed,
        policy_disabled_fallback_round_trip_stable,
        transport_fallback_integrity_surface_passed,
        blocking_reasons,
        blocking_reason_keys,
        blocking_reason_families,
    }
}

fn release_candidate_readiness_summary_contract_valid(
    summary: &ReleaseCandidateReadinessSummaryInput,
) -> bool {
    let expected_inputs = vec![
        "release_candidate_stabilization".to_owned(),
        "linux_readiness".to_owned(),
        "macos_readiness".to_owned(),
        "windows_readiness".to_owned(),
    ];
    let expected_readiness_labels = vec![
        "linux_readiness".to_owned(),
        "macos_readiness".to_owned(),
        "windows_readiness".to_owned(),
    ];
    let expected_host_labels = vec!["linux".to_owned(), "macos".to_owned(), "windows".to_owned()];
    let expected_required_profile_set = udp_wan_lab_required_no_silent_fallback_profile_slugs()
        .into_iter()
        .map(str::to_owned)
        .collect::<BTreeSet<_>>();
    let actual_required_profile_set = summary
        .interop_required_no_silent_fallback_profile_slugs
        .iter()
        .cloned()
        .collect::<BTreeSet<_>>();
    let summary_contract_invalid_count = summary
        .blocking_reason_family_counts
        .get("summary_contract")
        .copied()
        .unwrap_or(0);
    let (expected_reason, expected_family) = summarize_rollout_gate_state(
        summary.required_input_missing_count,
        summary_contract_invalid_count,
        summary.required_input_unready_count,
        summary.degradation_hold_count,
        summary.blocking_reason_count,
    );

    summary.summary_version == Some(UDP_RELEASE_CANDIDATE_READINESS_SUMMARY_VERSION)
        && summary.comparison_schema == UDP_ROLLOUT_OPERATOR_VERDICT_SCHEMA
        && summary.comparison_schema_version == UDP_ROLLOUT_OPERATOR_VERDICT_SCHEMA_VERSION
        && summary.verdict_family == UDP_ROLLOUT_OPERATOR_VERDICT_FAMILY
        && summary.decision_scope == UDP_ROLLOUT_DECISION_SCOPE_RELEASE_CANDIDATE_READINESS
        && summary.decision_label == "release_candidate_readiness"
        && summary.profile == "release_candidate_readiness"
        && summary.active_fuzz_required
        && summary.required_inputs == expected_inputs
        && summary.considered_inputs == expected_inputs
        && rollout_input_identity_consistent(
            &summary.required_inputs,
            &summary.considered_inputs,
            &summary.missing_required_inputs,
            summary.required_input_count,
        )
        && summary.missing_required_input_count == summary.missing_required_inputs.len()
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
        && blocking_reason_accounting_consistent(
            &summary.blocking_reason_keys,
            &summary.blocking_reason_key_counts,
            &summary.blocking_reason_families,
            &summary.blocking_reason_family_counts,
        )
        && summary.degradation_hold_count == summary.degradation_hold_subjects.len()
        && summary.queue_hold_input_count
            == usize::from(rollout_queue_hold_present(
                summary.queue_guard_headroom_missing_count,
                summary.queue_guard_tight_hold_count,
                summary.queue_pressure_hold_count,
            ))
        && summary.queue_hold_host_count <= 3
        && summary.queue_hold_host_count <= summary.queue_hold_input_count
        && summary.release_candidate_stabilization_present
        && (summary.release_candidate_stabilization_passed || summary.verdict != "ready")
        && summary.readiness_count == 3
        && summary.readiness_passed_count <= summary.readiness_count
        && summary.readiness_failed_count
            == summary
                .readiness_count
                .saturating_sub(summary.readiness_passed_count)
        && summary.readiness_labels == expected_readiness_labels
        && summary.readiness_host_labels == expected_host_labels
        && summary.interop_profile_catalog_schema_version == 1
        && summary.interop_profile_catalog_host_labels == expected_host_labels
        && summary.interop_profile_catalog_source_lane
            == UDP_INTEROP_PROFILE_CATALOG_SOURCE_LANE_COMPATIBLE_HOST
        && actual_required_profile_set == expected_required_profile_set
        && summary.interop_failed_profile_count == summary.interop_failed_profile_slugs.len()
        && (!summary.interop_profile_contract_passed
            || (summary.interop_failed_profile_count == 0
                && summary.interop_failed_profile_slugs.is_empty()))
        && summary.explicit_fallback_profile_count
            == udp_wan_lab_profile_slugs()
                .len()
                .saturating_sub(expected_required_profile_set.len())
        && summary.udp_blocked_fallback_surface_passed.is_some()
        && (summary.transport_fallback_integrity_surface_passed != Some(true)
            || (summary.policy_disabled_fallback_round_trip_stable == Some(true)
                && summary.udp_blocked_fallback_surface_passed == Some(true)))
        && (summary.policy_disabled_fallback_round_trip_stable != Some(true)
            || (summary.policy_disabled_fallback_surface_passed == Some(true)
                && summary.udp_blocked_fallback_surface_passed == Some(true)
                && summary.transport_fallback_integrity_surface_passed == Some(true)))
        && summary.gate_state_reason == expected_reason
        && summary.gate_state_reason_family == expected_family
        && summary.gate_state
            == if summary.verdict == "ready" {
                "passed"
            } else {
                "blocked"
            }
}

fn readiness_summary_contract_valid(summary: &ReadinessSummaryInput) -> bool {
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
    let expected_required_profile_set = udp_wan_lab_required_no_silent_fallback_profile_slugs()
        .into_iter()
        .map(str::to_owned)
        .collect::<BTreeSet<_>>();
    let actual_required_profile_set = summary
        .interop_required_no_silent_fallback_profile_slugs
        .iter()
        .cloned()
        .collect::<BTreeSet<_>>();
    let summary_contract_invalid_count = summary
        .blocking_reason_family_counts
        .get("summary_contract")
        .copied()
        .unwrap_or(0);
    let (expected_reason, expected_family) = summarize_rollout_gate_state(
        summary.required_input_missing_count,
        summary_contract_invalid_count,
        summary.required_input_unready_count,
        summary.degradation_hold_count,
        summary.blocking_reason_count,
    );

    summary.summary_version == Some(UDP_ROLLOUT_COMPARISON_SUMMARY_VERSION)
        && summary.comparison_schema == UDP_ROLLOUT_OPERATOR_VERDICT_SCHEMA
        && summary.comparison_schema_version == UDP_ROLLOUT_OPERATOR_VERDICT_SCHEMA_VERSION
        && summary.verdict_family == UDP_ROLLOUT_OPERATOR_VERDICT_FAMILY
        && summary.decision_scope == UDP_ROLLOUT_DECISION_SCOPE_HOST
        && summary.profile == "readiness"
        && !summary.decision_label.trim().is_empty()
        && !summary.host_label.trim().is_empty()
        && !summary.active_fuzz_required
        && summary.required_inputs == expected_required_inputs
        && summary.considered_inputs == expected_considered_inputs
        && rollout_input_identity_consistent(
            &summary.required_inputs,
            &summary.considered_inputs,
            &summary.missing_required_inputs,
            summary.required_input_count,
        )
        && summary.missing_required_input_count == summary.missing_required_inputs.len()
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
        && blocking_reason_accounting_consistent(
            &summary.blocking_reason_keys,
            &summary.blocking_reason_key_counts,
            &summary.blocking_reason_families,
            &summary.blocking_reason_family_counts,
        )
        && actual_required_profile_set == expected_required_profile_set
        && summary.udp_blocked_fallback_surface_passed.is_some()
        && (summary.transport_fallback_integrity_surface_passed != Some(true)
            || (summary.policy_disabled_fallback_round_trip_stable == Some(true)
                && summary.udp_blocked_fallback_surface_passed == Some(true)))
        && (summary.policy_disabled_fallback_round_trip_stable != Some(true)
            || (summary.policy_disabled_fallback_surface_passed == Some(true)
                && summary.transport_fallback_integrity_surface_passed == Some(true)))
        && summary.gate_state_reason == expected_reason
        && summary.gate_state_reason_family == expected_family
        && summary.gate_state
            == if summary.verdict == "ready" {
                "passed"
            } else {
                "blocked"
            }
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

fn load_input<T>(label: &str, path: &Path) -> LoadedInput<T>
where
    T: for<'de> Deserialize<'de>,
{
    if !path.exists() {
        return LoadedInput {
            label: label.to_owned(),
            present: false,
            parse_error: None,
            summary: None,
        };
    }

    match fs::read(path)
        .map_err(|error| error.to_string())
        .and_then(|bytes| serde_json::from_slice::<T>(&bytes).map_err(|error| error.to_string()))
    {
        Ok(summary) => LoadedInput {
            label: label.to_owned(),
            present: true,
            parse_error: None,
            summary: Some(summary),
        },
        Err(error) => LoadedInput {
            label: label.to_owned(),
            present: true,
            parse_error: Some(error),
            summary: None,
        },
    }
}

fn print_text_summary(summary: &UdpReleaseCandidateAcceptanceSummary, summary_path: &Path) {
    println!("Northstar UDP release candidate acceptance summary:");
    println!("- verdict: {}", summary.verdict);
    println!("- comparison_schema: {}", summary.comparison_schema);
    println!(
        "- comparison_schema_version: {}",
        summary.comparison_schema_version
    );
    println!("- decision_scope: {}", summary.decision_scope);
    println!("- decision_label: {}", summary.decision_label);
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
        "- release_candidate_readiness: present={} passed={}",
        summary.release_candidate_readiness_present, summary.release_candidate_readiness_passed
    );
    println!(
        "- readiness_counts: total={} passed={} failed={}",
        summary.readiness_count, summary.readiness_passed_count, summary.readiness_failed_count
    );
    println!(
        "- readiness_host_labels: {}",
        summary.readiness_host_labels.join(", ")
    );
    println!(
        "- interop_profile_catalog_schema_version: {}",
        summary.interop_profile_catalog_schema_version
    );
    println!(
        "- interop_profile_catalog_host_labels: {}",
        summary.interop_profile_catalog_host_labels.join(", ")
    );
    println!(
        "- interop_profile_catalog_source_lane: {}",
        summary.interop_profile_catalog_source_lane
    );
    println!(
        "- interop_failed_profile_count: {}",
        summary.interop_failed_profile_count
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
        "- queue_hold_input_count: {}",
        summary.queue_hold_input_count
    );
    println!("- queue_hold_host_count: {}", summary.queue_hold_host_count);
    println!(
        "- udp_blocked_fallback_surface_passed: {}",
        summary
            .udp_blocked_fallback_surface_passed
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
        "- policy_disabled_fallback_round_trip_stable: {}",
        summary
            .policy_disabled_fallback_round_trip_stable
            .map(|value| value.to_string())
            .unwrap_or_else(|| "missing".to_owned())
    );
    println!(
        "- transport_fallback_integrity_surface_passed: {}",
        summary
            .transport_fallback_integrity_surface_passed
            .map(|value| value.to_string())
            .unwrap_or_else(|| "missing".to_owned())
    );
    if summary.blocking_reasons.is_empty() {
        println!("- blocking_reasons: none");
    } else {
        println!(
            "- blocking_reasons: {}",
            summary.blocking_reasons.join(", ")
        );
    }
    println!(
        "- blocking_reason_key_counts: {}",
        render_counts(&summary.blocking_reason_key_counts)
    );
    println!(
        "- blocking_reason_family_counts: {}",
        render_counts(&summary.blocking_reason_family_counts)
    );
    println!("- summary_path: {}", summary_path.display());
}

fn parse_args<I>(args: I) -> Result<ReleaseCandidateAcceptanceArgs, Box<dyn std::error::Error>>
where
    I: IntoIterator<Item = String>,
{
    let mut parsed = ReleaseCandidateAcceptanceArgs::default();
    let mut iter = args.into_iter();
    while let Some(argument) = iter.next() {
        match argument.as_str() {
            "--json" => parsed.format = Some(OutputFormat::Json),
            "--text" => parsed.format = Some(OutputFormat::Text),
            "--summary-path" => {
                parsed.summary_path = Some(PathBuf::from(
                    iter.next()
                        .ok_or("--summary-path requires a path argument")?,
                ));
            }
            "--release-candidate-readiness" => {
                parsed.release_candidate_readiness = Some(PathBuf::from(
                    iter.next()
                        .ok_or("--release-candidate-readiness requires a path argument")?,
                ));
            }
            "--linux-readiness" => {
                parsed.linux_readiness = Some(PathBuf::from(
                    iter.next()
                        .ok_or("--linux-readiness requires a path argument")?,
                ));
            }
            "--macos-readiness" => {
                parsed.macos_readiness = Some(PathBuf::from(
                    iter.next()
                        .ok_or("--macos-readiness requires a path argument")?,
                ));
            }
            "--windows-readiness" => {
                parsed.windows_readiness = Some(PathBuf::from(
                    iter.next()
                        .ok_or("--windows-readiness requires a path argument")?,
                ));
            }
            other => return Err(format!("unsupported argument: {other}").into()),
        }
    }
    Ok(parsed)
}

fn default_release_candidate_readiness_input() -> PathBuf {
    repo_root()
        .join("target")
        .join("northstar")
        .join("udp-release-candidate-readiness-summary.json")
}

fn default_linux_readiness_input() -> PathBuf {
    repo_root()
        .join("target")
        .join("northstar")
        .join("udp-rollout-comparison-summary-linux.json")
}

fn default_macos_readiness_input() -> PathBuf {
    repo_root()
        .join("target")
        .join("northstar")
        .join("udp-rollout-comparison-summary-macos.json")
}

fn default_windows_readiness_input() -> PathBuf {
    repo_root()
        .join("target")
        .join("northstar")
        .join("udp-rollout-comparison-summary-windows.json")
}

fn default_summary_path() -> PathBuf {
    repo_root()
        .join("target")
        .join("northstar")
        .join("udp-release-candidate-acceptance-summary.json")
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

fn render_counts(counts: &BTreeMap<String, usize>) -> String {
    if counts.is_empty() {
        "none".to_owned()
    } else {
        counts
            .iter()
            .map(|(key, value)| format!("{key}={value}"))
            .collect::<Vec<_>>()
            .join(", ")
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn required_profile_slugs() -> Vec<String> {
        let mut values = udp_wan_lab_required_no_silent_fallback_profile_slugs()
            .into_iter()
            .map(str::to_owned)
            .collect::<Vec<_>>();
        values.sort();
        values
    }

    fn explicit_fallback_profile_count() -> usize {
        udp_wan_lab_profile_slugs()
            .len()
            .saturating_sub(required_profile_slugs().len())
    }

    fn ready_release_candidate_readiness() -> LoadedReleaseCandidateReadinessInput {
        LoadedInput {
            label: "release_candidate_readiness".to_owned(),
            present: true,
            parse_error: None,
            summary: Some(ReleaseCandidateReadinessSummaryInput {
                summary_version: Some(UDP_RELEASE_CANDIDATE_READINESS_SUMMARY_VERSION),
                comparison_schema: UDP_ROLLOUT_OPERATOR_VERDICT_SCHEMA.to_owned(),
                comparison_schema_version: UDP_ROLLOUT_OPERATOR_VERDICT_SCHEMA_VERSION,
                verdict_family: UDP_ROLLOUT_OPERATOR_VERDICT_FAMILY.to_owned(),
                decision_scope: UDP_ROLLOUT_DECISION_SCOPE_RELEASE_CANDIDATE_READINESS.to_owned(),
                decision_label: "release_candidate_readiness".to_owned(),
                profile: "release_candidate_readiness".to_owned(),
                verdict: "ready".to_owned(),
                evidence_state: "complete".to_owned(),
                gate_state: "passed".to_owned(),
                gate_state_reason: "all_required_inputs_passed".to_owned(),
                gate_state_reason_family: "ready".to_owned(),
                active_fuzz_required: true,
                required_inputs: vec![
                    "release_candidate_stabilization".to_owned(),
                    "linux_readiness".to_owned(),
                    "macos_readiness".to_owned(),
                    "windows_readiness".to_owned(),
                ],
                considered_inputs: vec![
                    "release_candidate_stabilization".to_owned(),
                    "linux_readiness".to_owned(),
                    "macos_readiness".to_owned(),
                    "windows_readiness".to_owned(),
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
                release_candidate_stabilization_present: true,
                release_candidate_stabilization_passed: true,
                readiness_count: 3,
                readiness_passed_count: 3,
                readiness_failed_count: 0,
                readiness_labels: vec![
                    "linux_readiness".to_owned(),
                    "macos_readiness".to_owned(),
                    "windows_readiness".to_owned(),
                ],
                readiness_host_labels: vec![
                    "linux".to_owned(),
                    "macos".to_owned(),
                    "windows".to_owned(),
                ],
                degradation_hold_count: 0,
                degradation_hold_subjects: Vec::new(),
                queue_guard_headroom_missing_count: 0,
                queue_guard_tight_hold_count: 0,
                queue_pressure_hold_count: 0,
                queue_hold_input_count: 0,
                queue_hold_host_count: 0,
                interop_required_no_silent_fallback_profile_slugs: required_profile_slugs(),
                interop_failed_profile_slugs: Vec::new(),
                interop_failed_profile_count: 0,
                explicit_fallback_profile_count: explicit_fallback_profile_count(),
                interop_profile_contract_passed: true,
                interop_profile_catalog_contract_passed: true,
                interop_profile_catalog_schema_version: 1,
                interop_profile_catalog_host_labels: vec![
                    "linux".to_owned(),
                    "macos".to_owned(),
                    "windows".to_owned(),
                ],
                interop_profile_catalog_source_lane:
                    UDP_INTEROP_PROFILE_CATALOG_SOURCE_LANE_COMPATIBLE_HOST.to_owned(),
                udp_blocked_fallback_surface_passed: Some(true),
                policy_disabled_fallback_surface_passed: Some(true),
                policy_disabled_fallback_round_trip_stable: Some(true),
                transport_fallback_integrity_surface_passed: Some(true),
                blocking_reasons: Vec::new(),
                blocking_reason_keys: Vec::new(),
                blocking_reason_families: Vec::new(),
            }),
        }
    }

    fn ready_host_readiness(label: &str, host_label: &str) -> LoadedReadinessInput {
        LoadedInput {
            label: label.to_owned(),
            present: true,
            parse_error: None,
            summary: Some(ReadinessSummaryInput {
                summary_version: Some(UDP_ROLLOUT_COMPARISON_SUMMARY_VERSION),
                comparison_schema: UDP_ROLLOUT_OPERATOR_VERDICT_SCHEMA.to_owned(),
                comparison_schema_version: UDP_ROLLOUT_OPERATOR_VERDICT_SCHEMA_VERSION,
                verdict_family: UDP_ROLLOUT_OPERATOR_VERDICT_FAMILY.to_owned(),
                decision_scope: UDP_ROLLOUT_DECISION_SCOPE_HOST.to_owned(),
                decision_label: format!("{host_label}_readiness"),
                profile: "readiness".to_owned(),
                host_label: host_label.to_owned(),
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
                queue_guard_headroom_missing_count: 0,
                queue_guard_tight_hold_count: 0,
                queue_pressure_hold_count: 0,
                interop_required_no_silent_fallback_profile_slugs: required_profile_slugs(),
                udp_blocked_fallback_surface_passed: Some(true),
                policy_disabled_fallback_surface_passed: Some(true),
                policy_disabled_fallback_round_trip_stable: Some(true),
                transport_fallback_integrity_surface_passed: Some(true),
                interop_profile_contract_passed: Some(true),
                blocking_reasons: Vec::new(),
                blocking_reason_keys: Vec::new(),
                blocking_reason_families: Vec::new(),
            }),
        }
    }

    fn ready_readiness_inputs() -> Vec<LoadedReadinessInput> {
        vec![
            ready_host_readiness("linux_readiness", "linux"),
            ready_host_readiness("macos_readiness", "macos"),
            ready_host_readiness("windows_readiness", "windows"),
        ]
    }

    #[test]
    fn acceptance_summary_is_ready_for_valid_inputs() {
        let summary = build_release_candidate_acceptance_summary(
            ready_release_candidate_readiness(),
            ready_readiness_inputs(),
        );

        assert_eq!(summary.verdict, "ready");
        assert_eq!(summary.gate_state, "passed");
        assert_eq!(summary.gate_state_reason, "all_required_inputs_passed");
        assert_eq!(summary.readiness_count, 3);
        assert_eq!(summary.interop_failed_profile_count, 0);
        assert_eq!(summary.udp_blocked_fallback_surface_passed, Some(true));
        assert_eq!(
            summary.transport_fallback_integrity_surface_passed,
            Some(true)
        );
    }

    #[test]
    fn acceptance_summary_fails_closed_when_parent_is_missing() {
        let summary = build_release_candidate_acceptance_summary(
            LoadedInput {
                label: "release_candidate_readiness".to_owned(),
                present: false,
                parse_error: None,
                summary: None,
            },
            ready_readiness_inputs(),
        );

        assert_eq!(summary.verdict, "hold");
        assert_eq!(summary.gate_state_reason, "missing_required_inputs");
        assert_eq!(summary.udp_blocked_fallback_surface_passed, None);
        assert!(
            summary
                .blocking_reasons
                .contains(&"missing_release_candidate_readiness_summary".to_owned())
        );
    }

    #[test]
    fn acceptance_summary_rejects_source_lane_drift() {
        let mut readiness = ready_release_candidate_readiness();
        readiness
            .summary
            .as_mut()
            .expect("summary")
            .interop_profile_catalog_source_lane = "wrong_lane".to_owned();

        let summary =
            build_release_candidate_acceptance_summary(readiness, ready_readiness_inputs());

        assert_eq!(summary.verdict, "hold");
        assert_eq!(summary.gate_state_reason, "summary_contract_invalid");
        assert!(
            summary
                .blocking_reasons
                .iter()
                .any(|reason| { reason.contains("interop_catalog_source_lane_invalid") })
        );
    }

    #[test]
    fn acceptance_summary_rejects_policy_disabled_round_trip_contract_drift() {
        let mut readiness = ready_release_candidate_readiness();
        readiness
            .summary
            .as_mut()
            .expect("summary")
            .policy_disabled_fallback_surface_passed = Some(false);

        let summary =
            build_release_candidate_acceptance_summary(readiness, ready_readiness_inputs());

        assert_eq!(summary.verdict, "hold");
        assert_eq!(summary.gate_state_reason, "summary_contract_invalid");
        assert!(summary.blocking_reasons.iter().any(|reason| {
            reason.contains("policy_disabled_fallback_round_trip_contract_inconsistent")
        }));
    }

    #[test]
    fn acceptance_summary_rejects_readiness_host_label_drift() {
        let mut inputs = ready_readiness_inputs();
        inputs[2].summary.as_mut().expect("summary").host_label = "bsd".to_owned();

        let summary =
            build_release_candidate_acceptance_summary(ready_release_candidate_readiness(), inputs);

        assert_eq!(summary.verdict, "hold");
        assert_eq!(summary.gate_state_reason, "summary_contract_invalid");
        assert!(
            summary
                .blocking_reasons
                .iter()
                .any(|reason| { reason.contains("readiness_host_label_set_invalid") })
        );
    }

    #[test]
    fn acceptance_summary_treats_failed_blocked_fallback_as_unready() {
        let mut inputs = ready_readiness_inputs();
        let summary = inputs[0].summary.as_mut().expect("summary");
        summary.verdict = "hold".to_owned();
        summary.gate_state = "blocked".to_owned();
        summary.gate_state_reason = "required_inputs_unready".to_owned();
        summary.gate_state_reason_family = "gating".to_owned();
        summary.required_input_failed_count = 1;
        summary.required_input_unready_count = 1;
        summary.required_input_passed_count = 3;
        summary.all_required_inputs_passed = false;
        summary.blocking_reason_count = 1;
        summary.blocking_reason_key_count = 1;
        summary.blocking_reason_family_count = 1;
        summary
            .blocking_reason_key_counts
            .insert("udp_blocked_fallback_surface_failed".to_owned(), 1);
        summary
            .blocking_reason_family_counts
            .insert("transport_integrity".to_owned(), 1);
        summary.blocking_reasons =
            vec!["linux_readiness_udp_blocked_fallback_surface_failed".to_owned()];
        summary.blocking_reason_keys = vec!["udp_blocked_fallback_surface_failed".to_owned()];
        summary.blocking_reason_families = vec!["transport_integrity".to_owned()];
        summary.udp_blocked_fallback_surface_passed = Some(false);
        summary.policy_disabled_fallback_round_trip_stable = Some(false);
        summary.transport_fallback_integrity_surface_passed = Some(false);

        let summary =
            build_release_candidate_acceptance_summary(ready_release_candidate_readiness(), inputs);

        assert_eq!(summary.verdict, "hold");
        assert_eq!(summary.gate_state_reason, "required_inputs_unready");
        assert_eq!(summary.udp_blocked_fallback_surface_passed, Some(false));
        assert!(
            summary
                .blocking_reasons
                .iter()
                .any(|reason| { reason.contains("udp_blocked_fallback_surface_failed") })
        );
    }
}
