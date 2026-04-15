use ns_testkit::{
    UDP_INTEROP_PROFILE_CATALOG_SOURCE_LANE_COMPATIBLE_HOST, UDP_ROLLOUT_DECISION_SCOPE_HOST,
    UDP_ROLLOUT_DECISION_SCOPE_RELEASE_GATE, UDP_ROLLOUT_DECISION_SCOPE_RELEASE_READINESS_BURNDOWN,
    UDP_ROLLOUT_OPERATOR_VERDICT_FAMILY, UDP_ROLLOUT_OPERATOR_VERDICT_SCHEMA,
    UDP_ROLLOUT_OPERATOR_VERDICT_SCHEMA_VERSION, blocking_reason_accounting_consistent,
    prefer_verta_input_path, rollout_queue_hold_host_count, rollout_queue_hold_input_count,
    rollout_queue_hold_present, summarize_rollout_gate_state,
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
struct ReleaseReadinessBurndownArgs {
    format: Option<OutputFormat>,
    summary_path: Option<PathBuf>,
    release_gate: Option<PathBuf>,
    linux_readiness: Option<PathBuf>,
    macos_readiness: Option<PathBuf>,
    windows_readiness: Option<PathBuf>,
}

const UDP_RELEASE_GATE_SUMMARY_VERSION: u8 = 3;
const UDP_ROLLOUT_COMPARISON_SUMMARY_VERSION: u8 = 14;
const UDP_RELEASE_READINESS_BURNDOWN_SUMMARY_VERSION: u8 = 3;

#[derive(Debug, Deserialize)]
struct ReleaseGateSummaryInput {
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
    release_soak_present: bool,
    release_soak_passed: bool,
    interop_profile_contract_passed: bool,
    interop_profile_catalog_contract_passed: bool,
    interop_profile_catalog_schema_version: u8,
    #[serde(default)]
    interop_profile_catalog_host_labels: Vec<String>,
    #[serde(default)]
    interop_profile_catalog_source_lane: String,
    #[serde(default)]
    interop_required_no_silent_fallback_profile_slugs: Vec<String>,
    #[serde(default)]
    interop_failed_profile_slugs: Vec<String>,
    explicit_fallback_profile_count: usize,
    #[serde(default)]
    policy_disabled_fallback_surface_passed: Option<bool>,
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
    policy_disabled_fallback_surface_passed: Option<bool>,
    #[serde(default)]
    transport_fallback_integrity_surface_passed: Option<bool>,
    #[serde(default)]
    interop_profile_contract_passed: Option<bool>,
    #[serde(default)]
    blocking_reasons: Vec<String>,
}

#[derive(Debug)]
struct LoadedInput<T> {
    label: String,
    present: bool,
    parse_error: Option<String>,
    summary: Option<T>,
}

type LoadedReleaseGateInput = LoadedInput<ReleaseGateSummaryInput>;
type LoadedReadinessInput = LoadedInput<ReadinessSummaryInput>;

#[derive(Debug, Serialize)]
struct UdpReleaseReadinessBurndownSummary {
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
    release_gate_present: bool,
    release_gate_passed: bool,
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
    explicit_fallback_profile_count: usize,
    interop_profile_contract_passed: bool,
    interop_profile_catalog_contract_passed: bool,
    interop_profile_catalog_schema_version: u8,
    interop_profile_catalog_host_labels: Vec<String>,
    interop_profile_catalog_source_lane: String,
    policy_disabled_fallback_surface_passed: Option<bool>,
    transport_fallback_integrity_surface_passed: Option<bool>,
    blocking_reasons: Vec<String>,
    blocking_reason_keys: Vec<String>,
    blocking_reason_families: Vec<String>,
}

fn main() -> Result<(), Box<dyn std::error::Error>> {
    let args = parse_args(env::args().skip(1))?;
    let summary = build_release_readiness_burndown_summary(
        load_input::<ReleaseGateSummaryInput>(
            "release_gate",
            &args.release_gate.unwrap_or_else(default_release_gate_input),
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
        return Err("udp release readiness burndown is not ready".into());
    }

    Ok(())
}

fn build_release_readiness_burndown_summary(
    release_gate: LoadedReleaseGateInput,
    readiness_inputs: Vec<LoadedReadinessInput>,
) -> UdpReleaseReadinessBurndownSummary {
    let required_inputs = vec![
        "release_gate".to_owned(),
        "linux_readiness".to_owned(),
        "macos_readiness".to_owned(),
        "windows_readiness".to_owned(),
    ];
    let considered_inputs = required_inputs.clone();
    let expected_required_profile_set = udp_wan_lab_required_no_silent_fallback_profile_slugs()
        .into_iter()
        .map(str::to_owned)
        .collect::<BTreeSet<_>>();

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
    let mut policy_disabled_fallback_surface_passed = Some(true);
    let mut transport_fallback_integrity_surface_passed = Some(true);
    let mut interop_profile_catalog_schema_version = 0u8;
    let mut interop_profile_catalog_host_labels = Vec::new();
    let mut interop_profile_catalog_source_lane = String::new();

    let release_gate_present = release_gate.present;
    if release_gate_present {
        present_required_inputs.insert("release_gate".to_owned());
    }
    let release_gate_passed = if let Some(summary) = release_gate.summary.as_ref() {
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
        if summary.policy_disabled_fallback_surface_passed == Some(false) {
            policy_disabled_fallback_surface_passed = Some(false);
        } else if summary.policy_disabled_fallback_surface_passed.is_none() {
            policy_disabled_fallback_surface_passed = None;
        }
        if summary.transport_fallback_integrity_surface_passed == Some(false) {
            transport_fallback_integrity_surface_passed = Some(false);
        } else if summary
            .transport_fallback_integrity_surface_passed
            .is_none()
        {
            transport_fallback_integrity_surface_passed = None;
        }
        if release_gate_summary_contract_valid(summary)
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
            && summary.policy_disabled_fallback_surface_passed == Some(true)
            && summary.transport_fallback_integrity_surface_passed == Some(true)
            && summary.interop_profile_contract_passed
            && summary.interop_profile_catalog_contract_passed
        {
            passed_required_inputs.insert("release_gate".to_owned());
            true
        } else {
            false
        }
    } else {
        false
    };

    if !release_gate.present {
        push_reason(
            &mut blocking_reasons,
            &mut blocking_reason_key_counts,
            &mut blocking_reason_family_counts,
            "missing_release_gate_summary",
            "missing_required_input",
            "summary_presence",
        );
    } else if let Some(error) = release_gate.parse_error.as_ref() {
        all_consumed_inputs_contract_valid = false;
        policy_disabled_fallback_surface_passed = None;
        transport_fallback_integrity_surface_passed = None;
        push_reason(
            &mut blocking_reasons,
            &mut blocking_reason_key_counts,
            &mut blocking_reason_family_counts,
            &format!("release_gate_parse_error:{error}"),
            "input_parse_error",
            "summary_contract",
        );
    } else if let Some(summary) = release_gate.summary.as_ref() {
        if !release_gate_summary_contract_valid(summary) {
            all_consumed_inputs_contract_valid = false;
            push_reason(
                &mut blocking_reasons,
                &mut blocking_reason_key_counts,
                &mut blocking_reason_family_counts,
                "release_gate_summary_contract_invalid",
                "input_contract_invalid",
                "summary_contract",
            );
        } else if !release_gate_passed {
            if summary.degradation_hold_count > 0 {
                degradation_hold_subjects.push("release_gate".to_owned());
                degradation_hold_subjects.extend(summary.degradation_hold_subjects.iter().cloned());
            }
            push_reason(
                &mut blocking_reasons,
                &mut blocking_reason_key_counts,
                &mut blocking_reason_family_counts,
                "release_gate_not_ready",
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
            if summary.policy_disabled_fallback_surface_passed == Some(false) {
                policy_disabled_fallback_surface_passed = Some(false);
            } else if summary.policy_disabled_fallback_surface_passed.is_none() {
                policy_disabled_fallback_surface_passed = None;
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
                && summary.policy_disabled_fallback_surface_passed == Some(true)
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
            policy_disabled_fallback_surface_passed = None;
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
            policy_disabled_fallback_surface_passed = None;
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
    let expected_catalog_host_labels =
        vec!["linux".to_owned(), "macos".to_owned(), "windows".to_owned()];
    if interop_profile_catalog_host_labels != expected_catalog_host_labels {
        push_reason(
            &mut blocking_reasons,
            &mut blocking_reason_key_counts,
            &mut blocking_reason_family_counts,
            "release_readiness_burndown_interop_catalog_host_coverage_incomplete",
            "interop_catalog_host_coverage_incomplete",
            "summary_presence",
        );
    }
    let interop_required_no_silent_fallback_profile_slugs =
        interop_required_profile_set.into_iter().collect::<Vec<_>>();
    let interop_failed_profile_slugs = interop_failed_profile_set.into_iter().collect::<Vec<_>>();
    let interop_profile_catalog_contract_passed =
        release_gate.summary.as_ref().is_some_and(|summary| {
            release_gate_summary_contract_valid(summary)
                && summary.interop_profile_catalog_contract_passed
        }) && interop_profile_catalog_schema_version == 1
            && interop_profile_catalog_host_labels == expected_catalog_host_labels
            && interop_profile_catalog_source_lane
                == UDP_INTEROP_PROFILE_CATALOG_SOURCE_LANE_COMPATIBLE_HOST;
    if !interop_profile_catalog_contract_passed {
        push_reason(
            &mut blocking_reasons,
            &mut blocking_reason_key_counts,
            &mut blocking_reason_family_counts,
            "release_readiness_burndown_interop_profile_catalog_contract_invalid",
            "interop_profile_catalog_contract_invalid",
            "summary_contract",
        );
    }
    let interop_profile_contract_passed = release_gate.summary.as_ref().is_some_and(|summary| {
        release_gate_summary_contract_valid(summary) && summary.interop_profile_contract_passed
    }) && interop_profile_catalog_contract_passed
        && interop_required_no_silent_fallback_profile_slugs
            == expected_required_profile_set
                .iter()
                .cloned()
                .collect::<Vec<_>>();
    if !interop_profile_contract_passed {
        push_reason(
            &mut blocking_reasons,
            &mut blocking_reason_key_counts,
            &mut blocking_reason_family_counts,
            "release_readiness_burndown_interop_profile_contract_invalid",
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
            "release_readiness_burndown_interop_required_no_silent_fallback_profile_set_mismatch",
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
            "release_readiness_burndown_queue_pressure_surface_failed",
            "queue_pressure_surface_failed",
            "capacity",
        );
    }
    if policy_disabled_fallback_surface_passed == Some(false) {
        push_reason(
            &mut blocking_reasons,
            &mut blocking_reason_key_counts,
            &mut blocking_reason_family_counts,
            "release_readiness_burndown_policy_disabled_fallback_surface_failed",
            "policy_disabled_fallback_surface_failed",
            "transport_integrity",
        );
    }
    if transport_fallback_integrity_surface_passed == Some(false) {
        push_reason(
            &mut blocking_reasons,
            &mut blocking_reason_key_counts,
            &mut blocking_reason_family_counts,
            "release_readiness_burndown_transport_fallback_integrity_surface_failed",
            "transport_fallback_integrity_surface_failed",
            "transport_integrity",
        );
    }
    let queue_hold_input_count = rollout_queue_hold_input_count(queue_hold_inputs.iter().copied());
    let queue_hold_host_count = rollout_queue_hold_host_count(queue_hold_hosts.iter().copied());
    let blocking_reason_count = blocking_reasons.len();
    let blocking_reason_key_count = blocking_reason_key_counts.len();
    let blocking_reason_family_count = blocking_reason_family_counts.len();
    let evidence_state = if all_required_inputs_present && all_consumed_inputs_contract_valid {
        "complete"
    } else {
        "incomplete"
    };
    let verdict = if all_required_inputs_passed
        && blocking_reason_count == 0
        && degradation_hold_count == 0
        && !rollout_queue_hold_present(
            queue_guard_headroom_missing_count,
            queue_guard_tight_hold_count,
            queue_pressure_hold_count,
        )
        && policy_disabled_fallback_surface_passed == Some(true)
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

    UdpReleaseReadinessBurndownSummary {
        summary_version: UDP_RELEASE_READINESS_BURNDOWN_SUMMARY_VERSION,
        comparison_schema: UDP_ROLLOUT_OPERATOR_VERDICT_SCHEMA,
        comparison_schema_version: UDP_ROLLOUT_OPERATOR_VERDICT_SCHEMA_VERSION,
        verdict_family: UDP_ROLLOUT_OPERATOR_VERDICT_FAMILY,
        decision_scope: UDP_ROLLOUT_DECISION_SCOPE_RELEASE_READINESS_BURNDOWN,
        decision_label: "release_readiness_burndown",
        profile: "release_readiness_burndown",
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
        release_gate_present,
        release_gate_passed,
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
        explicit_fallback_profile_count,
        interop_profile_contract_passed,
        interop_profile_catalog_contract_passed,
        interop_profile_catalog_schema_version,
        interop_profile_catalog_host_labels,
        interop_profile_catalog_source_lane,
        policy_disabled_fallback_surface_passed,
        transport_fallback_integrity_surface_passed,
        blocking_reasons,
        blocking_reason_keys,
        blocking_reason_families,
    }
}

fn release_gate_summary_contract_valid(summary: &ReleaseGateSummaryInput) -> bool {
    let expected_inputs = vec![
        "release_soak".to_owned(),
        "linux_interop_catalog".to_owned(),
        "macos_interop_catalog".to_owned(),
        "windows_interop_catalog".to_owned(),
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
    summary.summary_version == Some(UDP_RELEASE_GATE_SUMMARY_VERSION)
        && summary.comparison_schema == UDP_ROLLOUT_OPERATOR_VERDICT_SCHEMA
        && summary.comparison_schema_version == UDP_ROLLOUT_OPERATOR_VERDICT_SCHEMA_VERSION
        && summary.verdict_family == UDP_ROLLOUT_OPERATOR_VERDICT_FAMILY
        && summary.decision_scope == UDP_ROLLOUT_DECISION_SCOPE_RELEASE_GATE
        && summary.decision_label == "release_gate"
        && summary.profile == "release_gate"
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
        && summary.queue_hold_input_count
            == usize::from(rollout_queue_hold_present(
                summary.queue_guard_headroom_missing_count,
                summary.queue_guard_tight_hold_count,
                summary.queue_pressure_hold_count,
            ))
        && summary.release_soak_present
        && (summary.release_soak_passed || summary.verdict != "ready")
        && summary.interop_profile_catalog_schema_version == 1
        && summary.interop_profile_catalog_host_labels
            == vec!["linux".to_owned(), "macos".to_owned(), "windows".to_owned()]
        && summary.interop_profile_catalog_source_lane
            == UDP_INTEROP_PROFILE_CATALOG_SOURCE_LANE_COMPATIBLE_HOST
        && actual_required_profile_set == expected_required_profile_set
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
        && actual_required_profile_set == expected_required_profile_set
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

fn print_text_summary(summary: &UdpReleaseReadinessBurndownSummary, summary_path: &Path) {
    println!("Verta UDP release-readiness burn-down summary:");
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
        "- release_gate: present={} passed={}",
        summary.release_gate_present, summary.release_gate_passed
    );
    println!(
        "- readiness_counts: total={} passed={} failed={}",
        summary.readiness_count, summary.readiness_passed_count, summary.readiness_failed_count
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
        "- interop_profile_contract_passed: {}",
        summary.interop_profile_contract_passed
    );
    println!(
        "- interop_profile_catalog_contract_passed: {}",
        summary.interop_profile_catalog_contract_passed
    );
    println!(
        "- policy_disabled_fallback_surface_passed: {}",
        summary
            .policy_disabled_fallback_surface_passed
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
    println!(
        "- readiness_labels: {}",
        summary.readiness_labels.join(", ")
    );
    println!(
        "- readiness_host_labels: {}",
        summary.readiness_host_labels.join(", ")
    );
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

fn parse_args<I>(args: I) -> Result<ReleaseReadinessBurndownArgs, Box<dyn std::error::Error>>
where
    I: IntoIterator<Item = String>,
{
    let mut parsed = ReleaseReadinessBurndownArgs::default();
    let mut iter = args.into_iter();
    while let Some(argument) = iter.next() {
        match argument.as_str() {
            "--summary-path" => {
                parsed.summary_path = Some(PathBuf::from(
                    iter.next()
                        .ok_or("--summary-path requires a path argument")?,
                ));
            }
            "--release-gate" => {
                parsed.release_gate = Some(PathBuf::from(
                    iter.next()
                        .ok_or("--release-gate requires a path argument")?,
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
            "--format" => match iter.next().as_deref() {
                Some("text") => parsed.format = Some(OutputFormat::Text),
                Some("json") => parsed.format = Some(OutputFormat::Json),
                Some(other) => return Err(format!("unsupported format: {other}").into()),
                None => return Err("--format requires text or json".into()),
            },
            "--help" | "-h" => {
                print_usage();
                std::process::exit(0);
            }
            other => return Err(format!("unrecognized argument: {other}").into()),
        }
    }
    Ok(parsed)
}

fn print_usage() {
    eprintln!(
        "Usage: cargo run -p ns-testkit --example udp_release_readiness_burndown -- [--summary-path <path>] [--release-gate <path>] [--linux-readiness <path>] [--macos-readiness <path>] [--windows-readiness <path>] [--format text|json]"
    );
}

fn default_release_gate_input() -> PathBuf {
    prefer_verta_input_path("udp-release-gate-summary.json")
}

fn default_linux_readiness_input() -> PathBuf {
    prefer_verta_input_path("udp-rollout-comparison-summary-linux.json")
}

fn default_macos_readiness_input() -> PathBuf {
    prefer_verta_input_path("udp-rollout-comparison-summary-macos.json")
}

fn default_windows_readiness_input() -> PathBuf {
    prefer_verta_input_path("udp-rollout-comparison-summary-windows.json")
}

fn default_summary_path() -> PathBuf {
    verta_output_path("udp-release-readiness-burndown-summary.json")
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

    fn ready_release_gate() -> LoadedReleaseGateInput {
        LoadedInput {
            label: "release_gate".to_owned(),
            present: true,
            parse_error: None,
            summary: Some(ReleaseGateSummaryInput {
                summary_version: Some(UDP_RELEASE_GATE_SUMMARY_VERSION),
                comparison_schema: UDP_ROLLOUT_OPERATOR_VERDICT_SCHEMA.to_owned(),
                comparison_schema_version: UDP_ROLLOUT_OPERATOR_VERDICT_SCHEMA_VERSION,
                verdict_family: UDP_ROLLOUT_OPERATOR_VERDICT_FAMILY.to_owned(),
                decision_scope: UDP_ROLLOUT_DECISION_SCOPE_RELEASE_GATE.to_owned(),
                decision_label: "release_gate".to_owned(),
                profile: "release_gate".to_owned(),
                verdict: "ready".to_owned(),
                evidence_state: "complete".to_owned(),
                gate_state: "passed".to_owned(),
                gate_state_reason: "all_required_inputs_passed".to_owned(),
                gate_state_reason_family: "ready".to_owned(),
                active_fuzz_required: true,
                required_inputs: vec![
                    "release_soak".to_owned(),
                    "linux_interop_catalog".to_owned(),
                    "macos_interop_catalog".to_owned(),
                    "windows_interop_catalog".to_owned(),
                ],
                considered_inputs: vec![
                    "release_soak".to_owned(),
                    "linux_interop_catalog".to_owned(),
                    "macos_interop_catalog".to_owned(),
                    "windows_interop_catalog".to_owned(),
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
                queue_hold_input_count: 0,
                release_soak_present: true,
                release_soak_passed: true,
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
                interop_required_no_silent_fallback_profile_slugs: required_profile_slugs(),
                interop_failed_profile_slugs: Vec::new(),
                explicit_fallback_profile_count: 3,
                policy_disabled_fallback_surface_passed: Some(true),
                transport_fallback_integrity_surface_passed: Some(true),
                blocking_reasons: Vec::new(),
                blocking_reason_keys: Vec::new(),
                blocking_reason_families: Vec::new(),
            }),
        }
    }

    fn ready_readiness(label: &str, host_label: &str) -> LoadedReadinessInput {
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
                policy_disabled_fallback_surface_passed: Some(true),
                transport_fallback_integrity_surface_passed: Some(true),
                interop_profile_contract_passed: Some(true),
                blocking_reasons: Vec::new(),
            }),
        }
    }

    #[test]
    fn release_readiness_burndown_is_ready_with_release_gate_and_host_readiness() {
        let summary = build_release_readiness_burndown_summary(
            ready_release_gate(),
            vec![
                ready_readiness("linux_readiness", "ubuntu-latest-rollout"),
                ready_readiness("macos_readiness", "macos-latest-rollout"),
                ready_readiness("windows_readiness", "windows-latest-rollout"),
            ],
        );
        assert_eq!(summary.verdict, "ready");
        assert_eq!(summary.gate_state, "passed");
        assert_eq!(summary.required_input_passed_count, 4);
        assert!(summary.interop_profile_contract_passed);
        assert!(summary.interop_profile_catalog_contract_passed);
        assert_eq!(summary.queue_hold_host_count, 0);
    }

    #[test]
    fn release_readiness_burndown_fails_closed_when_release_gate_missing() {
        let summary = build_release_readiness_burndown_summary(
            LoadedInput {
                label: "release_gate".to_owned(),
                present: false,
                parse_error: None,
                summary: None,
            },
            vec![
                ready_readiness("linux_readiness", "ubuntu-latest-rollout"),
                ready_readiness("macos_readiness", "macos-latest-rollout"),
                ready_readiness("windows_readiness", "windows-latest-rollout"),
            ],
        );
        assert_eq!(summary.verdict, "hold");
        assert!(
            summary
                .blocking_reasons
                .iter()
                .any(|reason| reason == "missing_release_gate_summary")
        );
    }

    #[test]
    fn release_readiness_burndown_counts_hosts_with_queue_holds() {
        let mut linux = ready_readiness("linux_readiness", "ubuntu-latest-rollout");
        linux
            .summary
            .as_mut()
            .expect("linux readiness should be present")
            .queue_pressure_hold_count = 1;
        let mut windows = ready_readiness("windows_readiness", "windows-latest-rollout");
        windows
            .summary
            .as_mut()
            .expect("windows readiness should be present")
            .queue_guard_tight_hold_count = 2;

        let summary = build_release_readiness_burndown_summary(
            ready_release_gate(),
            vec![
                linux,
                ready_readiness("macos_readiness", "macos-latest-rollout"),
                windows,
            ],
        );

        assert_eq!(summary.queue_hold_input_count, 2);
        assert_eq!(summary.queue_hold_host_count, 2);
        assert_eq!(summary.verdict, "hold");
    }
}
