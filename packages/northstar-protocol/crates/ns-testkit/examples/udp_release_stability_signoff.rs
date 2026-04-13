use ns_testkit::{
    UDP_INTEROP_PROFILE_CATALOG_SOURCE_LANE_COMPATIBLE_HOST,
    UDP_ROLLOUT_DECISION_SCOPE_RELEASE_READINESS_BURNDOWN,
    UDP_ROLLOUT_DECISION_SCOPE_RELEASE_STABILITY_SIGNOFF, UDP_ROLLOUT_OPERATOR_VERDICT_FAMILY,
    UDP_ROLLOUT_OPERATOR_VERDICT_SCHEMA, UDP_ROLLOUT_OPERATOR_VERDICT_SCHEMA_VERSION,
    blocking_reason_accounting_consistent, repo_root, summarize_rollout_gate_state,
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
struct ReleaseStabilitySignoffArgs {
    format: Option<OutputFormat>,
    summary_path: Option<PathBuf>,
    release_readiness_burndown: Option<PathBuf>,
    linux_interop: Option<PathBuf>,
    macos_interop: Option<PathBuf>,
    windows_interop: Option<PathBuf>,
}

const UDP_RELEASE_READINESS_BURNDOWN_SUMMARY_VERSION: u8 = 3;
const UDP_INTEROP_LAB_SUMMARY_VERSION: u8 = 4;
const UDP_RELEASE_STABILITY_SIGNOFF_SUMMARY_VERSION: u8 = 2;

#[derive(Debug, Deserialize)]
struct ReleaseReadinessBurndownSummaryInput {
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
    required_inputs: Vec<String>,
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
    blocking_reason_keys: Vec<String>,
    #[serde(default)]
    blocking_reason_families: Vec<String>,
    release_gate_present: bool,
    release_gate_passed: bool,
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
    explicit_fallback_profile_count: usize,
    interop_profile_contract_passed: bool,
    interop_profile_catalog_contract_passed: bool,
    interop_profile_catalog_schema_version: u8,
    #[serde(default)]
    interop_profile_catalog_host_labels: Vec<String>,
    #[serde(default)]
    interop_profile_catalog_source_lane: String,
    #[serde(default)]
    policy_disabled_fallback_surface_passed: Option<bool>,
    #[serde(default)]
    transport_fallback_integrity_surface_passed: Option<bool>,
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
    required_no_silent_fallback_profile_count: usize,
    required_no_silent_fallback_passed_count: usize,
    #[serde(default)]
    required_no_silent_fallback_profile_slugs: Vec<String>,
    explicit_fallback_profile_count: usize,
    policy_disabled_fallback_surface_passed: bool,
}

#[derive(Debug)]
struct LoadedInput<T> {
    label: String,
    present: bool,
    parse_error: Option<String>,
    summary: Option<T>,
}

type LoadedBurndownInput = LoadedInput<ReleaseReadinessBurndownSummaryInput>;
type LoadedInteropInput = LoadedInput<InteropLabSummaryInput>;

#[derive(Debug, Serialize)]
struct UdpReleaseStabilitySignoffSummary {
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
    release_readiness_burndown_present: bool,
    release_readiness_burndown_passed: bool,
    interop_count: usize,
    interop_passed_count: usize,
    interop_failed_count: usize,
    degradation_hold_count: usize,
    degradation_hold_subjects: Vec<String>,
    queue_guard_headroom_missing_count: usize,
    queue_guard_tight_hold_count: usize,
    queue_pressure_hold_count: usize,
    queue_hold_input_count: usize,
    queue_hold_host_count: usize,
    interop_profile_contract_passed: bool,
    interop_profile_catalog_contract_passed: bool,
    interop_profile_catalog_schema_version: u8,
    interop_profile_catalog_host_labels: Vec<String>,
    interop_profile_catalog_source_lane: String,
    interop_required_no_silent_fallback_profile_slugs: Vec<String>,
    interop_failed_profile_slugs: Vec<String>,
    explicit_fallback_profile_count: usize,
    policy_disabled_fallback_surface_passed: Option<bool>,
    transport_fallback_integrity_surface_passed: Option<bool>,
    blocking_reasons: Vec<String>,
    blocking_reason_keys: Vec<String>,
    blocking_reason_families: Vec<String>,
}

fn main() -> Result<(), Box<dyn std::error::Error>> {
    let args = parse_args(env::args().skip(1))?;
    let summary = build_release_stability_signoff_summary(
        load_input::<ReleaseReadinessBurndownSummaryInput>(
            "release_readiness_burndown",
            &args
                .release_readiness_burndown
                .unwrap_or_else(default_release_readiness_burndown_input),
        ),
        vec![
            load_input::<InteropLabSummaryInput>(
                "linux_interop",
                &args
                    .linux_interop
                    .unwrap_or_else(default_linux_interop_input),
            ),
            load_input::<InteropLabSummaryInput>(
                "macos_interop",
                &args
                    .macos_interop
                    .unwrap_or_else(default_macos_interop_input),
            ),
            load_input::<InteropLabSummaryInput>(
                "windows_interop",
                &args
                    .windows_interop
                    .unwrap_or_else(default_windows_interop_input),
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
        return Err("udp release stability signoff is not ready".into());
    }

    Ok(())
}

fn build_release_stability_signoff_summary(
    burndown: LoadedBurndownInput,
    interop_inputs: Vec<LoadedInteropInput>,
) -> UdpReleaseStabilitySignoffSummary {
    let required_inputs = vec![
        "release_readiness_burndown".to_owned(),
        "linux_interop".to_owned(),
        "macos_interop".to_owned(),
        "windows_interop".to_owned(),
    ];
    let considered_inputs = required_inputs.clone();
    let expected_profile_set = udp_wan_lab_profile_slugs()
        .into_iter()
        .map(str::to_owned)
        .collect::<BTreeSet<_>>();
    let expected_required_profile_set = udp_wan_lab_required_no_silent_fallback_profile_slugs()
        .into_iter()
        .map(str::to_owned)
        .collect::<BTreeSet<_>>();
    let expected_catalog_host_labels =
        vec!["linux".to_owned(), "macos".to_owned(), "windows".to_owned()];

    let mut present_required_inputs = BTreeSet::new();
    let mut passed_required_inputs = BTreeSet::new();
    let mut blocking_reasons = Vec::new();
    let mut blocking_reason_key_counts = BTreeMap::new();
    let mut blocking_reason_family_counts = BTreeMap::new();
    let mut degradation_hold_subjects = Vec::new();
    let mut interop_passed_count = 0usize;
    let mut interop_profile_set = BTreeSet::new();
    let mut interop_required_profile_set = BTreeSet::new();
    let mut interop_failed_profile_set = BTreeSet::new();
    let mut all_consumed_inputs_contract_valid = true;
    let mut explicit_fallback_profile_count = 0usize;
    let mut policy_disabled_fallback_surface_passed = Some(true);
    let mut transport_fallback_integrity_surface_passed = Some(true);
    let mut queue_guard_headroom_missing_count = 0usize;
    let mut queue_guard_tight_hold_count = 0usize;
    let mut queue_pressure_hold_count = 0usize;
    let mut queue_hold_input_count = 0usize;
    let mut queue_hold_host_count = 0usize;
    let mut interop_profile_catalog_schema_version = 0u8;
    let mut interop_profile_catalog_host_labels = Vec::new();
    let mut interop_profile_catalog_source_lane = String::new();

    let release_readiness_burndown_present = burndown.present;
    if burndown.present {
        present_required_inputs.insert("release_readiness_burndown".to_owned());
    }
    let release_readiness_burndown_passed = if let Some(summary) = burndown.summary.as_ref() {
        queue_guard_headroom_missing_count = summary.queue_guard_headroom_missing_count;
        queue_guard_tight_hold_count = summary.queue_guard_tight_hold_count;
        queue_pressure_hold_count = summary.queue_pressure_hold_count;
        queue_hold_input_count = summary.queue_hold_input_count;
        queue_hold_host_count = summary.queue_hold_host_count;
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
        match summary.policy_disabled_fallback_surface_passed {
            Some(false) => policy_disabled_fallback_surface_passed = Some(false),
            None => policy_disabled_fallback_surface_passed = None,
            Some(true) => {}
        }
        match summary.transport_fallback_integrity_surface_passed {
            Some(false) => transport_fallback_integrity_surface_passed = Some(false),
            None => transport_fallback_integrity_surface_passed = None,
            Some(true) => {}
        }

        if release_readiness_burndown_summary_contract_valid(summary)
            && summary.verdict == "ready"
            && summary.evidence_state == "complete"
            && summary.gate_state == "passed"
            && summary.all_required_inputs_present
            && summary.all_required_inputs_passed
            && summary.blocking_reason_count == 0
            && summary.degradation_hold_count == 0
            && summary.queue_hold_input_count == 0
            && summary.queue_hold_host_count == 0
            && summary.policy_disabled_fallback_surface_passed == Some(true)
            && summary.transport_fallback_integrity_surface_passed == Some(true)
            && summary.interop_profile_contract_passed
            && summary.interop_profile_catalog_contract_passed
        {
            passed_required_inputs.insert("release_readiness_burndown".to_owned());
            true
        } else {
            false
        }
    } else {
        false
    };

    if !burndown.present {
        policy_disabled_fallback_surface_passed = None;
        transport_fallback_integrity_surface_passed = None;
        push_reason(
            &mut blocking_reasons,
            &mut blocking_reason_key_counts,
            &mut blocking_reason_family_counts,
            "missing_release_readiness_burndown_summary",
            "missing_required_input",
            "summary_presence",
        );
    } else if let Some(error) = burndown.parse_error.as_ref() {
        all_consumed_inputs_contract_valid = false;
        policy_disabled_fallback_surface_passed = None;
        transport_fallback_integrity_surface_passed = None;
        push_reason(
            &mut blocking_reasons,
            &mut blocking_reason_key_counts,
            &mut blocking_reason_family_counts,
            &format!("release_readiness_burndown_parse_error:{error}"),
            "input_parse_error",
            "summary_contract",
        );
    } else if let Some(summary) = burndown.summary.as_ref() {
        if !release_readiness_burndown_summary_contract_valid(summary) {
            all_consumed_inputs_contract_valid = false;
            policy_disabled_fallback_surface_passed = None;
            transport_fallback_integrity_surface_passed = None;
            push_reason(
                &mut blocking_reasons,
                &mut blocking_reason_key_counts,
                &mut blocking_reason_family_counts,
                "release_readiness_burndown_summary_contract_invalid",
                "input_contract_invalid",
                "summary_contract",
            );
        } else if !release_readiness_burndown_passed {
            if summary.degradation_hold_count > 0 {
                degradation_hold_subjects.push("release_readiness_burndown".to_owned());
                degradation_hold_subjects.extend(summary.degradation_hold_subjects.iter().cloned());
            }
            push_reason(
                &mut blocking_reasons,
                &mut blocking_reason_key_counts,
                &mut blocking_reason_family_counts,
                "release_readiness_burndown_not_ready",
                "input_not_ready",
                if summary.queue_hold_input_count > 0 {
                    "capacity"
                } else if summary.degradation_hold_count > 0 {
                    "degradation"
                } else {
                    "gating"
                },
            );
        }
    }

    for input in interop_inputs {
        if input.present {
            present_required_inputs.insert(input.label.clone());
        }

        let passed = match input.summary.as_ref() {
            Some(summary)
                if input.present
                    && input.parse_error.is_none()
                    && interop_summary_contract_valid(summary) =>
            {
                interop_profile_set.extend(summary.profile_slugs.iter().cloned());
                interop_required_profile_set.extend(
                    summary
                        .required_no_silent_fallback_profile_slugs
                        .iter()
                        .cloned(),
                );
                interop_failed_profile_set.extend(summary.failed_profile_slugs.iter().cloned());
                explicit_fallback_profile_count =
                    explicit_fallback_profile_count.max(summary.explicit_fallback_profile_count);
                if !summary.policy_disabled_fallback_surface_passed {
                    policy_disabled_fallback_surface_passed = Some(false);
                }
                if summary.all_passed
                    && summary.failed_profile_slugs.is_empty()
                    && summary.required_no_silent_fallback_passed_count
                        == summary.required_no_silent_fallback_profile_count
                    && summary.policy_disabled_fallback_surface_passed
                {
                    interop_passed_count += 1;
                    passed_required_inputs.insert(input.label.clone());
                    true
                } else {
                    false
                }
            }
            Some(summary) => {
                interop_profile_set.extend(summary.profile_slugs.iter().cloned());
                interop_required_profile_set.extend(
                    summary
                        .required_no_silent_fallback_profile_slugs
                        .iter()
                        .cloned(),
                );
                interop_failed_profile_set.extend(summary.failed_profile_slugs.iter().cloned());
                explicit_fallback_profile_count =
                    explicit_fallback_profile_count.max(summary.explicit_fallback_profile_count);
                if !summary.policy_disabled_fallback_surface_passed {
                    policy_disabled_fallback_surface_passed = Some(false);
                }
                false
            }
            None => false,
        };

        if !input.present {
            policy_disabled_fallback_surface_passed = None;
            push_reason(
                &mut blocking_reasons,
                &mut blocking_reason_key_counts,
                &mut blocking_reason_family_counts,
                &format!("missing_{}_summary", input.label),
                "missing_required_input",
                "summary_presence",
            );
        } else if let Some(error) = input.parse_error.as_ref() {
            all_consumed_inputs_contract_valid = false;
            policy_disabled_fallback_surface_passed = None;
            push_reason(
                &mut blocking_reasons,
                &mut blocking_reason_key_counts,
                &mut blocking_reason_family_counts,
                &format!("{}_parse_error:{error}", input.label),
                "input_parse_error",
                "summary_contract",
            );
        } else if let Some(summary) = input.summary.as_ref() {
            if !interop_summary_contract_valid(summary) {
                all_consumed_inputs_contract_valid = false;
                policy_disabled_fallback_surface_passed = None;
                push_reason(
                    &mut blocking_reasons,
                    &mut blocking_reason_key_counts,
                    &mut blocking_reason_family_counts,
                    &format!("{}_summary_contract_invalid", input.label),
                    "input_contract_invalid",
                    "summary_contract",
                );
            } else if !passed {
                let (reason_key, family) = if !summary.policy_disabled_fallback_surface_passed {
                    ("policy_disabled_fallback_surface_failed", "policy")
                } else if !summary.failed_profile_slugs.is_empty()
                    || summary.required_no_silent_fallback_passed_count
                        != summary.required_no_silent_fallback_profile_count
                {
                    ("interop_profile_failed", "compatibility")
                } else {
                    ("input_not_ready", "gating")
                };
                push_reason(
                    &mut blocking_reasons,
                    &mut blocking_reason_key_counts,
                    &mut blocking_reason_family_counts,
                    &format!("{}_not_ready", input.label),
                    reason_key,
                    family,
                );
            }
        }
    }

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
    let required_input_missing_count = missing_required_inputs.len();
    let required_input_present_count = present_required_inputs.len();
    let required_input_passed_count = passed_required_inputs.len();
    let required_input_failed_count =
        required_input_count.saturating_sub(required_input_passed_count);
    let required_input_unready_count =
        required_input_failed_count.saturating_sub(required_input_missing_count);
    let all_required_inputs_present = required_input_missing_count == 0;
    let all_required_inputs_passed = required_input_passed_count == required_input_count;

    if interop_profile_catalog_host_labels != expected_catalog_host_labels {
        push_reason(
            &mut blocking_reasons,
            &mut blocking_reason_key_counts,
            &mut blocking_reason_family_counts,
            "release_stability_signoff_interop_catalog_host_coverage_incomplete",
            "interop_catalog_host_coverage_incomplete",
            "compatibility",
        );
    }

    let interop_profile_catalog_contract_passed =
        burndown.summary.as_ref().is_some_and(|summary| {
            release_readiness_burndown_summary_contract_valid(summary)
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
            "release_stability_signoff_interop_profile_catalog_contract_invalid",
            "interop_profile_catalog_contract_invalid",
            "summary_contract",
        );
    }

    let mut interop_required_no_silent_fallback_profile_slugs =
        interop_required_profile_set.into_iter().collect::<Vec<_>>();
    interop_required_no_silent_fallback_profile_slugs.sort();
    let mut interop_failed_profile_slugs =
        interop_failed_profile_set.into_iter().collect::<Vec<_>>();
    interop_failed_profile_slugs.sort();
    let interop_profile_contract_passed = burndown.summary.as_ref().is_some_and(|summary| {
        release_readiness_burndown_summary_contract_valid(summary)
            && summary.interop_profile_contract_passed
    }) && interop_profile_catalog_contract_passed
        && interop_profile_set == expected_profile_set
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
            "release_stability_signoff_interop_profile_contract_invalid",
            "interop_profile_contract_invalid",
            "summary_contract",
        );
    }

    if queue_hold_input_count > 0 {
        push_reason(
            &mut blocking_reasons,
            &mut blocking_reason_key_counts,
            &mut blocking_reason_family_counts,
            "release_stability_signoff_queue_hold_inputs_present",
            "queue_hold_input_present",
            "capacity",
        );
    }
    if queue_hold_host_count > 0 {
        push_reason(
            &mut blocking_reasons,
            &mut blocking_reason_key_counts,
            &mut blocking_reason_family_counts,
            "release_stability_signoff_queue_hold_hosts_present",
            "queue_hold_host_present",
            "capacity",
        );
    }
    if policy_disabled_fallback_surface_passed != Some(true) {
        push_reason(
            &mut blocking_reasons,
            &mut blocking_reason_key_counts,
            &mut blocking_reason_family_counts,
            "release_stability_signoff_policy_disabled_fallback_surface_failed",
            "policy_disabled_fallback_surface_failed",
            "policy",
        );
    }
    if transport_fallback_integrity_surface_passed != Some(true) {
        push_reason(
            &mut blocking_reasons,
            &mut blocking_reason_key_counts,
            &mut blocking_reason_family_counts,
            "release_stability_signoff_transport_fallback_integrity_surface_failed",
            "transport_fallback_integrity_surface_failed",
            "transport_integrity",
        );
    }
    if !interop_failed_profile_slugs.is_empty() {
        push_reason(
            &mut blocking_reasons,
            &mut blocking_reason_key_counts,
            &mut blocking_reason_family_counts,
            "release_stability_signoff_interop_profiles_failed",
            "interop_profile_failed",
            "compatibility",
        );
    }

    let interop_count = 3usize;
    let interop_failed_count = interop_count.saturating_sub(interop_passed_count);
    let blocking_reason_count = blocking_reasons.len();
    let blocking_reason_key_count = blocking_reason_key_counts.len();
    let blocking_reason_family_count = blocking_reason_family_counts.len();
    let summary_contract_invalid_count = blocking_reason_family_counts
        .get("summary_contract")
        .copied()
        .unwrap_or(0);
    let evidence_state = if all_required_inputs_present && all_consumed_inputs_contract_valid {
        "complete"
    } else {
        "incomplete"
    };
    let verdict = if all_required_inputs_present
        && all_consumed_inputs_contract_valid
        && blocking_reason_count == 0
        && degradation_hold_count == 0
        && queue_hold_input_count == 0
        && queue_hold_host_count == 0
        && interop_failed_profile_slugs.is_empty()
        && release_readiness_burndown_passed
        && interop_passed_count == interop_count
        && policy_disabled_fallback_surface_passed == Some(true)
        && transport_fallback_integrity_surface_passed == Some(true)
        && interop_profile_contract_passed
        && interop_profile_catalog_contract_passed
    {
        "ready"
    } else {
        "hold"
    };
    let (gate_state_reason, gate_state_reason_family) = summarize_rollout_gate_state(
        required_input_missing_count,
        summary_contract_invalid_count,
        required_input_unready_count,
        degradation_hold_count,
        blocking_reason_count,
    );
    let gate_state = if verdict == "ready" {
        "passed"
    } else {
        "blocked"
    };

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

    UdpReleaseStabilitySignoffSummary {
        summary_version: UDP_RELEASE_STABILITY_SIGNOFF_SUMMARY_VERSION,
        comparison_schema: UDP_ROLLOUT_OPERATOR_VERDICT_SCHEMA,
        comparison_schema_version: UDP_ROLLOUT_OPERATOR_VERDICT_SCHEMA_VERSION,
        verdict_family: UDP_ROLLOUT_OPERATOR_VERDICT_FAMILY,
        decision_scope: UDP_ROLLOUT_DECISION_SCOPE_RELEASE_STABILITY_SIGNOFF,
        decision_label: "release_stability_signoff",
        profile: "release_stability_signoff",
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
        release_readiness_burndown_present,
        release_readiness_burndown_passed,
        interop_count,
        interop_passed_count,
        interop_failed_count,
        degradation_hold_count,
        degradation_hold_subjects,
        queue_guard_headroom_missing_count,
        queue_guard_tight_hold_count,
        queue_pressure_hold_count,
        queue_hold_input_count,
        queue_hold_host_count,
        interop_profile_contract_passed,
        interop_profile_catalog_contract_passed,
        interop_profile_catalog_schema_version,
        interop_profile_catalog_host_labels,
        interop_profile_catalog_source_lane,
        interop_required_no_silent_fallback_profile_slugs,
        interop_failed_profile_slugs,
        explicit_fallback_profile_count,
        policy_disabled_fallback_surface_passed,
        transport_fallback_integrity_surface_passed,
        blocking_reasons,
        blocking_reason_keys,
        blocking_reason_families,
    }
}

fn release_readiness_burndown_summary_contract_valid(
    summary: &ReleaseReadinessBurndownSummaryInput,
) -> bool {
    let expected_inputs = vec![
        "release_gate".to_owned(),
        "linux_readiness".to_owned(),
        "macos_readiness".to_owned(),
        "windows_readiness".to_owned(),
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

    summary.summary_version == Some(UDP_RELEASE_READINESS_BURNDOWN_SUMMARY_VERSION)
        && summary.comparison_schema == UDP_ROLLOUT_OPERATOR_VERDICT_SCHEMA
        && summary.comparison_schema_version == UDP_ROLLOUT_OPERATOR_VERDICT_SCHEMA_VERSION
        && summary.verdict_family == UDP_ROLLOUT_OPERATOR_VERDICT_FAMILY
        && summary.decision_scope == UDP_ROLLOUT_DECISION_SCOPE_RELEASE_READINESS_BURNDOWN
        && summary.decision_label == "release_readiness_burndown"
        && summary.profile == "release_readiness_burndown"
        && summary.active_fuzz_required
        && summary.required_inputs == expected_inputs
        && summary.considered_inputs == expected_inputs
        && rollout_input_identity_consistent(
            &summary.required_inputs,
            &summary.considered_inputs,
            &summary.missing_required_inputs,
            summary.required_input_count,
        )
        && summary.missing_required_input_count == summary.required_input_missing_count
        && summary.required_input_count == 4
        && summary.release_gate_present
        && (summary.release_gate_passed || summary.verdict != "ready")
        && summary.readiness_count == 3
        && summary.readiness_labels
            == vec![
                "linux_readiness".to_owned(),
                "macos_readiness".to_owned(),
                "windows_readiness".to_owned(),
            ]
        && summary.readiness_host_labels
            == vec!["linux".to_owned(), "macos".to_owned(), "windows".to_owned()]
        && summary.readiness_passed_count <= summary.readiness_count
        && summary.readiness_failed_count
            == summary
                .readiness_count
                .saturating_sub(summary.readiness_passed_count)
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
        && summary.queue_hold_host_count <= summary.readiness_count
        && summary.queue_hold_host_count <= summary.queue_hold_input_count
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

fn interop_summary_contract_valid(summary: &InteropLabSummaryInput) -> bool {
    let expected_profile_set = udp_wan_lab_profile_slugs()
        .into_iter()
        .map(str::to_owned)
        .collect::<BTreeSet<_>>();
    let expected_required_profile_set = udp_wan_lab_required_no_silent_fallback_profile_slugs()
        .into_iter()
        .map(str::to_owned)
        .collect::<BTreeSet<_>>();
    let actual_profile_set = summary
        .profile_slugs
        .iter()
        .cloned()
        .collect::<BTreeSet<_>>();
    let actual_required_profile_set = summary
        .required_no_silent_fallback_profile_slugs
        .iter()
        .cloned()
        .collect::<BTreeSet<_>>();

    summary.summary_version == Some(UDP_INTEROP_LAB_SUMMARY_VERSION)
        && summary.profile_count == expected_profile_set.len()
        && summary.profile_slugs.len() == expected_profile_set.len()
        && actual_profile_set == expected_profile_set
        && summary
            .failed_profile_slugs
            .iter()
            .all(|slug| expected_profile_set.contains(slug))
        && summary.required_no_silent_fallback_profile_count == expected_required_profile_set.len()
        && summary.required_no_silent_fallback_passed_count
            <= summary.required_no_silent_fallback_profile_count
        && actual_required_profile_set == expected_required_profile_set
        && summary.explicit_fallback_profile_count
            == expected_profile_set
                .len()
                .saturating_sub(expected_required_profile_set.len())
        && summary.all_passed == summary.failed_profile_slugs.is_empty()
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

fn print_text_summary(summary: &UdpReleaseStabilitySignoffSummary, summary_path: &Path) {
    println!("Northstar UDP release stability signoff summary:");
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
        "- release_readiness_burndown: present={} passed={}",
        summary.release_readiness_burndown_present, summary.release_readiness_burndown_passed
    );
    println!(
        "- interop_counts: total={} passed={} failed={}",
        summary.interop_count, summary.interop_passed_count, summary.interop_failed_count
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
        "- interop_profile_catalog_schema_version: {}",
        summary.interop_profile_catalog_schema_version
    );
    println!(
        "- interop_profile_catalog_host_labels: {}",
        if summary.interop_profile_catalog_host_labels.is_empty() {
            "none".to_owned()
        } else {
            summary.interop_profile_catalog_host_labels.join(", ")
        }
    );
    println!(
        "- interop_profile_catalog_source_lane: {}",
        summary.interop_profile_catalog_source_lane
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
    if summary.missing_required_inputs.is_empty() {
        println!("- missing_required_inputs: none");
    } else {
        println!(
            "- missing_required_inputs: {}",
            summary.missing_required_inputs.join(", ")
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
    if summary.interop_failed_profile_slugs.is_empty() {
        println!("- interop_failed_profile_slugs: none");
    } else {
        println!(
            "- interop_failed_profile_slugs: {}",
            summary.interop_failed_profile_slugs.join(", ")
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
    println!("- summary_path: {}", summary_path.display());
}

fn parse_args<I>(mut args: I) -> Result<ReleaseStabilitySignoffArgs, String>
where
    I: Iterator<Item = String>,
{
    let mut parsed = ReleaseStabilitySignoffArgs::default();
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
            "--release-readiness-burndown" => {
                parsed.release_readiness_burndown =
                    Some(PathBuf::from(args.next().ok_or_else(|| {
                        "--release-readiness-burndown requires a value".to_owned()
                    })?));
            }
            "--linux-interop" => {
                parsed.linux_interop =
                    Some(PathBuf::from(args.next().ok_or_else(|| {
                        "--linux-interop requires a value".to_owned()
                    })?));
            }
            "--macos-interop" => {
                parsed.macos_interop =
                    Some(PathBuf::from(args.next().ok_or_else(|| {
                        "--macos-interop requires a value".to_owned()
                    })?));
            }
            "--windows-interop" => {
                parsed.windows_interop =
                    Some(PathBuf::from(args.next().ok_or_else(|| {
                        "--windows-interop requires a value".to_owned()
                    })?));
            }
            "--help" | "-h" => return Err(help_text()),
            _ => return Err(help_text()),
        }
    }
    Ok(parsed)
}

fn help_text() -> String {
    "Usage: cargo run -p ns-testkit --example udp_release_stability_signoff -- [--format text|json] [--summary-path <path>] [--release-readiness-burndown <path>] [--linux-interop <path>] [--macos-interop <path>] [--windows-interop <path>]".to_owned()
}

fn default_release_readiness_burndown_input() -> PathBuf {
    repo_root()
        .join("target")
        .join("northstar")
        .join("udp-release-readiness-burndown-summary.json")
}

fn default_linux_interop_input() -> PathBuf {
    repo_root()
        .join("target")
        .join("northstar")
        .join("udp-interop-lab-summary-linux.json")
}

fn default_macos_interop_input() -> PathBuf {
    repo_root()
        .join("target")
        .join("northstar")
        .join("udp-interop-lab-summary-macos.json")
}

fn default_windows_interop_input() -> PathBuf {
    repo_root()
        .join("target")
        .join("northstar")
        .join("udp-interop-lab-summary-windows.json")
}

fn default_summary_path() -> PathBuf {
    repo_root()
        .join("target")
        .join("northstar")
        .join("udp-release-stability-signoff-summary.json")
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

    fn all_profile_slugs() -> Vec<String> {
        let mut values = udp_wan_lab_profile_slugs()
            .into_iter()
            .map(str::to_owned)
            .collect::<Vec<_>>();
        values.sort();
        values
    }

    fn required_profile_slugs() -> Vec<String> {
        let mut values = udp_wan_lab_required_no_silent_fallback_profile_slugs()
            .into_iter()
            .map(str::to_owned)
            .collect::<Vec<_>>();
        values.sort();
        values
    }

    fn ready_release_readiness_burndown() -> LoadedBurndownInput {
        let required_profiles = required_profile_slugs();
        LoadedInput {
            label: "release_readiness_burndown".to_owned(),
            present: true,
            parse_error: None,
            summary: Some(ReleaseReadinessBurndownSummaryInput {
                summary_version: Some(UDP_RELEASE_READINESS_BURNDOWN_SUMMARY_VERSION),
                comparison_schema: UDP_ROLLOUT_OPERATOR_VERDICT_SCHEMA.to_owned(),
                comparison_schema_version: UDP_ROLLOUT_OPERATOR_VERDICT_SCHEMA_VERSION,
                verdict_family: UDP_ROLLOUT_OPERATOR_VERDICT_FAMILY.to_owned(),
                decision_scope: UDP_ROLLOUT_DECISION_SCOPE_RELEASE_READINESS_BURNDOWN.to_owned(),
                decision_label: "release_readiness_burndown".to_owned(),
                profile: "release_readiness_burndown".to_owned(),
                verdict: "ready".to_owned(),
                evidence_state: "complete".to_owned(),
                gate_state: "passed".to_owned(),
                gate_state_reason: "all_required_inputs_passed".to_owned(),
                gate_state_reason_family: "ready".to_owned(),
                active_fuzz_required: true,
                required_inputs: vec![
                    "release_gate".to_owned(),
                    "linux_readiness".to_owned(),
                    "macos_readiness".to_owned(),
                    "windows_readiness".to_owned(),
                ],
                considered_inputs: vec![
                    "release_gate".to_owned(),
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
                blocking_reason_keys: Vec::new(),
                blocking_reason_families: Vec::new(),
                release_gate_present: true,
                release_gate_passed: true,
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
                interop_required_no_silent_fallback_profile_slugs: required_profiles,
                interop_failed_profile_slugs: Vec::new(),
                explicit_fallback_profile_count: all_profile_slugs().len()
                    - required_profile_slugs().len(),
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
                policy_disabled_fallback_surface_passed: Some(true),
                transport_fallback_integrity_surface_passed: Some(true),
                blocking_reasons: Vec::new(),
            }),
        }
    }

    fn ready_interop(label: &str) -> LoadedInteropInput {
        LoadedInput {
            label: label.to_owned(),
            present: true,
            parse_error: None,
            summary: Some(InteropLabSummaryInput {
                summary_version: Some(UDP_INTEROP_LAB_SUMMARY_VERSION),
                all_passed: true,
                profile_count: all_profile_slugs().len(),
                profile_slugs: all_profile_slugs(),
                failed_profile_slugs: Vec::new(),
                required_no_silent_fallback_profile_count: required_profile_slugs().len(),
                required_no_silent_fallback_passed_count: required_profile_slugs().len(),
                required_no_silent_fallback_profile_slugs: required_profile_slugs(),
                explicit_fallback_profile_count: all_profile_slugs().len()
                    - required_profile_slugs().len(),
                policy_disabled_fallback_surface_passed: true,
            }),
        }
    }

    #[test]
    fn release_stability_signoff_ready_when_all_inputs_pass() {
        let summary = build_release_stability_signoff_summary(
            ready_release_readiness_burndown(),
            vec![
                ready_interop("linux_interop"),
                ready_interop("macos_interop"),
                ready_interop("windows_interop"),
            ],
        );

        assert_eq!(
            summary.summary_version,
            UDP_RELEASE_STABILITY_SIGNOFF_SUMMARY_VERSION
        );
        assert_eq!(
            summary.comparison_schema_version,
            UDP_ROLLOUT_OPERATOR_VERDICT_SCHEMA_VERSION
        );
        assert_eq!(summary.verdict, "ready");
        assert_eq!(summary.gate_state, "passed");
        assert_eq!(summary.gate_state_reason, "all_required_inputs_passed");
        assert_eq!(summary.interop_passed_count, 3);
        assert_eq!(summary.queue_hold_host_count, 0);
        assert!(summary.interop_profile_contract_passed);
        assert!(summary.interop_profile_catalog_contract_passed);
        assert_eq!(
            summary.interop_profile_catalog_host_labels,
            vec!["linux".to_owned(), "macos".to_owned(), "windows".to_owned()]
        );
        assert!(summary.blocking_reasons.is_empty());
    }

    #[test]
    fn release_stability_signoff_holds_on_queue_hold_hosts() {
        let mut burndown = ready_release_readiness_burndown();
        let summary = burndown
            .summary
            .as_mut()
            .expect("ready release-readiness burndown summary should exist");
        summary.verdict = "hold".to_owned();
        summary.gate_state = "blocked".to_owned();
        summary.gate_state_reason = "required_inputs_unready".to_owned();
        summary.gate_state_reason_family = "gating".to_owned();
        summary.required_input_failed_count = 1;
        summary.required_input_unready_count = 1;
        summary.required_input_passed_count = 3;
        summary.all_required_inputs_passed = false;
        summary.queue_hold_input_count = 1;
        summary.queue_hold_host_count = 1;
        summary.blocking_reason_count = 1;
        summary.blocking_reason_key_count = 1;
        summary.blocking_reason_family_count = 1;
        summary.blocking_reason_key_counts =
            BTreeMap::from([("queue_hold_input_present".to_owned(), 1usize)]);
        summary.blocking_reason_family_counts = BTreeMap::from([("capacity".to_owned(), 1usize)]);
        summary.blocking_reason_keys = vec!["queue_hold_input_present".to_owned()];
        summary.blocking_reason_families = vec!["capacity".to_owned()];
        summary.blocking_reasons =
            vec!["release_readiness_burndown_queue_hold_inputs_present".to_owned()];

        let stability = build_release_stability_signoff_summary(
            burndown,
            vec![
                ready_interop("linux_interop"),
                ready_interop("macos_interop"),
                ready_interop("windows_interop"),
            ],
        );

        assert_eq!(stability.verdict, "hold");
        assert_eq!(stability.gate_state, "blocked");
        assert_eq!(stability.queue_hold_input_count, 1);
        assert_eq!(stability.queue_hold_host_count, 1);
        assert_eq!(
            stability
                .blocking_reason_key_counts
                .get("queue_hold_host_present"),
            Some(&1)
        );
        assert!(
            stability
                .blocking_reasons
                .contains(&"release_stability_signoff_queue_hold_hosts_present".to_owned())
        );
    }

    #[test]
    fn release_stability_signoff_requires_catalog_host_coverage() {
        let mut burndown = ready_release_readiness_burndown();
        burndown
            .summary
            .as_mut()
            .expect("ready release-readiness burndown summary should exist")
            .interop_profile_catalog_host_labels = vec!["linux".to_owned(), "macos".to_owned()];

        let summary = build_release_stability_signoff_summary(
            burndown,
            vec![
                ready_interop("linux_interop"),
                ready_interop("macos_interop"),
                ready_interop("windows_interop"),
            ],
        );

        assert_eq!(summary.verdict, "hold");
        assert!(!summary.interop_profile_catalog_contract_passed);
        assert!(summary.blocking_reasons.contains(
            &"release_stability_signoff_interop_catalog_host_coverage_incomplete".to_owned()
        ));
    }

    #[test]
    fn release_stability_signoff_holds_on_burndown_blocking_reason_accounting_drift() {
        let mut burndown = ready_release_readiness_burndown();
        burndown
            .summary
            .as_mut()
            .expect("ready release-readiness burndown summary should exist")
            .blocking_reason_keys = vec!["unexpected_key".to_owned()];

        let summary = build_release_stability_signoff_summary(
            burndown,
            vec![
                ready_interop("linux_interop"),
                ready_interop("macos_interop"),
                ready_interop("windows_interop"),
            ],
        );

        assert_eq!(summary.verdict, "hold");
        assert_eq!(summary.gate_state_reason, "summary_contract_invalid");
        assert_eq!(summary.gate_state_reason_family, "summary_contract");
        assert!(
            summary
                .blocking_reasons
                .contains(&"release_readiness_burndown_summary_contract_invalid".to_owned())
        );
    }
}
