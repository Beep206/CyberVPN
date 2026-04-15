use ns_testkit::{
    UDP_ROLLOUT_DECISION_SCOPE_RELEASE_BURN_IN, UDP_ROLLOUT_DECISION_SCOPE_RELEASE_SOAK,
    UDP_ROLLOUT_OPERATOR_VERDICT_FAMILY, UDP_ROLLOUT_OPERATOR_VERDICT_SCHEMA,
    UDP_ROLLOUT_OPERATOR_VERDICT_SCHEMA_VERSION, prefer_verta_input_path,
    summarize_rollout_gate_state, udp_wan_lab_profile_slugs,
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
struct ReleaseSoakArgs {
    format: Option<OutputFormat>,
    summary_path: Option<PathBuf>,
    release_burn_in: Option<PathBuf>,
    linux_interop: Option<PathBuf>,
    macos_interop: Option<PathBuf>,
    windows_interop: Option<PathBuf>,
}

const UDP_RELEASE_BURN_IN_SUMMARY_VERSION: u8 = 2;
const UDP_INTEROP_LAB_SUMMARY_VERSION: u8 = 4;
const UDP_RELEASE_SOAK_SUMMARY_VERSION: u8 = 1;

#[derive(Debug, Deserialize)]
struct ReleaseBurnInSummaryInput {
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
    queue_guard_headroom_band_counts: BTreeMap<String, usize>,
    #[serde(default)]
    queue_guard_headroom_missing_count: usize,
    #[serde(default)]
    queue_guard_tight_hold_count: usize,
    #[serde(default)]
    queue_pressure_hold_count: usize,
    #[serde(default)]
    queue_guard_limiting_path_counts: BTreeMap<String, usize>,
    #[serde(default)]
    interop_profile_contract_passed: bool,
    #[serde(default)]
    interop_required_no_silent_fallback_profile_slugs: Vec<String>,
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
struct LoadedInput<T> {
    label: String,
    present: bool,
    parse_error: Option<String>,
    summary: Option<T>,
}

type LoadedReleaseBurnInInput = LoadedInput<ReleaseBurnInSummaryInput>;
type LoadedInteropInput = LoadedInput<InteropLabSummaryInput>;

#[derive(Debug, Serialize)]
struct UdpReleaseSoakSummary {
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
    release_burn_in_present: bool,
    release_burn_in_passed: bool,
    interop_count: usize,
    interop_passed_count: usize,
    interop_failed_count: usize,
    interop_labels: Vec<String>,
    degradation_hold_count: usize,
    degradation_hold_subjects: Vec<String>,
    queue_guard_headroom_band_counts: BTreeMap<String, usize>,
    queue_guard_headroom_missing_count: usize,
    queue_guard_tight_hold_count: usize,
    queue_pressure_hold_count: usize,
    queue_guard_limiting_path_counts: BTreeMap<String, usize>,
    interop_profile_contract_passed: bool,
    interop_required_no_silent_fallback_profile_slugs: Vec<String>,
    interop_failed_profile_slugs: Vec<String>,
    explicit_fallback_profile_count: usize,
    policy_disabled_fallback_surface_passed: Option<bool>,
    transport_fallback_integrity_surface_passed: Option<bool>,
    blocking_reasons: Vec<String>,
    blocking_reason_keys: Vec<String>,
    blocking_reason_families: Vec<String>,
    advisory_reasons: Vec<String>,
}

fn main() -> Result<(), Box<dyn std::error::Error>> {
    let args = parse_args(env::args().skip(1))?;
    let release_burn_in_path = args
        .release_burn_in
        .unwrap_or_else(default_release_burn_in_input);
    let linux_interop_path = args
        .linux_interop
        .unwrap_or_else(default_linux_interop_input);
    let macos_interop_path = args
        .macos_interop
        .unwrap_or_else(default_macos_interop_input);
    let windows_interop_path = args
        .windows_interop
        .unwrap_or_else(default_windows_interop_input);
    let summary = build_release_soak_summary(
        load_input::<ReleaseBurnInSummaryInput>("release_burn_in", &release_burn_in_path),
        vec![
            load_input::<InteropLabSummaryInput>("linux_interop", &linux_interop_path),
            load_input::<InteropLabSummaryInput>("macos_interop", &macos_interop_path),
            load_input::<InteropLabSummaryInput>("windows_interop", &windows_interop_path),
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
        return Err("udp release soak is not ready".into());
    }

    Ok(())
}

fn build_release_soak_summary(
    release_burn_in: LoadedReleaseBurnInInput,
    interop_inputs: Vec<LoadedInteropInput>,
) -> UdpReleaseSoakSummary {
    let required_inputs = vec![
        "release_burn_in".to_owned(),
        "linux_interop".to_owned(),
        "macos_interop".to_owned(),
        "windows_interop".to_owned(),
    ];
    let considered_inputs = required_inputs.clone();
    let expected_profile_set = udp_wan_lab_profile_slugs()
        .into_iter()
        .map(str::to_owned)
        .collect::<BTreeSet<_>>();
    let expected_required_no_silent_fallback_profile_set =
        udp_wan_lab_required_no_silent_fallback_profile_slugs()
            .into_iter()
            .map(str::to_owned)
            .collect::<BTreeSet<_>>();

    let mut present_required_inputs = BTreeSet::new();
    let mut passed_required_inputs = BTreeSet::new();
    let mut blocking_reasons = Vec::new();
    let mut blocking_reason_key_counts = BTreeMap::new();
    let mut blocking_reason_family_counts = BTreeMap::new();
    let advisory_reasons = Vec::new();
    let mut degradation_hold_subjects = Vec::new();
    let mut queue_guard_headroom_band_counts = BTreeMap::new();
    let mut queue_guard_limiting_path_counts = BTreeMap::new();
    let mut queue_guard_headroom_missing_count = 0usize;
    let mut queue_guard_tight_hold_count = 0usize;
    let mut queue_pressure_hold_count = 0usize;
    let mut interop_required_no_silent_fallback_profile_set = BTreeSet::new();
    let mut interop_failed_profile_set = BTreeSet::new();
    let mut interop_labels = Vec::new();
    let mut interop_passed_count = 0usize;
    let mut explicit_fallback_profile_count = 0usize;
    let mut all_consumed_inputs_contract_valid = true;

    let release_burn_in_present = release_burn_in.present;
    if release_burn_in_present {
        present_required_inputs.insert("release_burn_in".to_owned());
    }
    let release_burn_in_passed = match release_burn_in.summary.as_ref() {
        Some(summary)
            if release_burn_in.present
                && release_burn_in.parse_error.is_none()
                && release_burn_in_summary_contract_valid(summary)
                && summary.verdict == "ready"
                && summary.evidence_state == "complete"
                && summary.gate_state == "passed"
                && summary.active_fuzz_required
                && summary.all_required_inputs_present
                && summary.all_required_inputs_passed
                && summary.blocking_reason_count == 0
                && summary.degradation_hold_count == 0
                && summary.queue_guard_headroom_missing_count == 0
                && summary.queue_guard_tight_hold_count == 0
                && summary.queue_pressure_hold_count == 0
                && summary.transport_fallback_integrity_surface_passed == Some(true)
                && summary.interop_profile_contract_passed =>
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
            queue_pressure_hold_count += summary.queue_pressure_hold_count;
            interop_required_no_silent_fallback_profile_set.extend(
                summary
                    .interop_required_no_silent_fallback_profile_slugs
                    .iter()
                    .cloned(),
            );
            passed_required_inputs.insert("release_burn_in".to_owned());
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
            queue_pressure_hold_count += summary.queue_pressure_hold_count;
            interop_required_no_silent_fallback_profile_set.extend(
                summary
                    .interop_required_no_silent_fallback_profile_slugs
                    .iter()
                    .cloned(),
            );
            false
        }
        None => false,
    };

    if !release_burn_in.present {
        push_reason(
            &mut blocking_reasons,
            &mut blocking_reason_key_counts,
            &mut blocking_reason_family_counts,
            "missing_release_burn_in_summary",
            "missing_required_input",
            "summary_presence",
        );
    } else if let Some(error) = release_burn_in.parse_error.as_ref() {
        all_consumed_inputs_contract_valid = false;
        push_reason(
            &mut blocking_reasons,
            &mut blocking_reason_key_counts,
            &mut blocking_reason_family_counts,
            &format!("release_burn_in_parse_error:{error}"),
            "input_parse_error",
            "summary_contract",
        );
    } else if let Some(summary) = release_burn_in.summary.as_ref() {
        if !release_burn_in_summary_contract_valid(summary) {
            all_consumed_inputs_contract_valid = false;
            push_reason(
                &mut blocking_reasons,
                &mut blocking_reason_key_counts,
                &mut blocking_reason_family_counts,
                "release_burn_in_summary_contract_invalid",
                "input_contract_invalid",
                "summary_contract",
            );
        } else if !release_burn_in_passed {
            if summary.degradation_hold_count > 0 {
                degradation_hold_subjects.push("release_burn_in".to_owned());
                degradation_hold_subjects.extend(summary.degradation_hold_subjects.iter().cloned());
            }
            push_reason(
                &mut blocking_reasons,
                &mut blocking_reason_key_counts,
                &mut blocking_reason_family_counts,
                "release_burn_in_not_ready",
                "input_not_ready",
                if summary.degradation_hold_count > 0 {
                    "degradation"
                } else {
                    "gating"
                },
            );
        }
    }

    let mut policy_disabled_fallback_surface_failed = false;
    let mut transport_fallback_integrity_surface_failed = false;
    for input in interop_inputs {
        interop_labels.push(input.label.clone());
        if input.present {
            present_required_inputs.insert(input.label.clone());
        }
        let passed = match input.summary.as_ref() {
            Some(summary)
                if input.present
                    && input.parse_error.is_none()
                    && interop_summary_contract_valid(summary)
                    && summary.all_passed
                    && summary.failed_profile_slugs.is_empty()
                    && summary.required_no_silent_fallback_passed_count
                        == summary.required_no_silent_fallback_profile_count
                    && summary.policy_disabled_fallback_surface_passed
                    && summary.queue_pressure_surface_passed
                    && summary.transport_fallback_integrity_surface_passed =>
            {
                explicit_fallback_profile_count =
                    explicit_fallback_profile_count.max(summary.explicit_fallback_profile_count);
                interop_required_no_silent_fallback_profile_set.extend(
                    summary
                        .required_no_silent_fallback_profile_slugs
                        .iter()
                        .cloned(),
                );
                passed_required_inputs.insert(input.label.clone());
                interop_passed_count += 1;
                true
            }
            Some(summary) => {
                explicit_fallback_profile_count =
                    explicit_fallback_profile_count.max(summary.explicit_fallback_profile_count);
                interop_required_no_silent_fallback_profile_set.extend(
                    summary
                        .required_no_silent_fallback_profile_slugs
                        .iter()
                        .cloned(),
                );
                interop_failed_profile_set.extend(summary.failed_profile_slugs.iter().cloned());
                if !summary.queue_pressure_surface_passed {
                    queue_pressure_hold_count += 1;
                }
                if !summary.policy_disabled_fallback_surface_passed {
                    policy_disabled_fallback_surface_failed = true;
                }
                if !summary.transport_fallback_integrity_surface_passed {
                    transport_fallback_integrity_surface_failed = true;
                }
                false
            }
            None => false,
        };

        if !input.present {
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
                push_reason(
                    &mut blocking_reasons,
                    &mut blocking_reason_key_counts,
                    &mut blocking_reason_family_counts,
                    &format!("{}_summary_contract_invalid", input.label),
                    "input_contract_invalid",
                    "summary_contract",
                );
            } else if !passed {
                if !summary.policy_disabled_fallback_surface_passed {
                    push_reason(
                        &mut blocking_reasons,
                        &mut blocking_reason_key_counts,
                        &mut blocking_reason_family_counts,
                        &format!("{}_policy_disabled_fallback_surface_failed", input.label),
                        "policy_disabled_fallback_surface_failed",
                        "transport_integrity",
                    );
                }
                if !summary.transport_fallback_integrity_surface_passed {
                    push_reason(
                        &mut blocking_reasons,
                        &mut blocking_reason_key_counts,
                        &mut blocking_reason_family_counts,
                        &format!(
                            "{}_transport_fallback_integrity_surface_failed",
                            input.label
                        ),
                        "transport_fallback_integrity_surface_failed",
                        "transport_integrity",
                    );
                }
                if !summary.queue_pressure_surface_passed {
                    push_reason(
                        &mut blocking_reasons,
                        &mut blocking_reason_key_counts,
                        &mut blocking_reason_family_counts,
                        &format!("{}_queue_pressure_surface_failed", input.label),
                        "queue_pressure_surface_failed",
                        "capacity",
                    );
                }
                push_reason(
                    &mut blocking_reasons,
                    &mut blocking_reason_key_counts,
                    &mut blocking_reason_family_counts,
                    &format!("{}_not_ready", input.label),
                    "input_not_ready",
                    if !summary.queue_pressure_surface_passed {
                        "degradation"
                    } else {
                        "gating"
                    },
                );
            }
        }
    }

    interop_labels.sort();
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
    degradation_hold_subjects.sort();
    degradation_hold_subjects.dedup();
    let degradation_hold_count = degradation_hold_subjects.len();
    let interop_failed_count = interop_labels.len().saturating_sub(interop_passed_count);

    let interop_profile_contract_passed = release_burn_in.summary.as_ref().is_some_and(|summary| {
        release_burn_in_summary_contract_valid(summary) && summary.interop_profile_contract_passed
    }) && interop_required_no_silent_fallback_profile_set
        == expected_required_no_silent_fallback_profile_set
        && interop_failed_profile_set
            .iter()
            .all(|slug| expected_profile_set.contains(slug));
    if !interop_profile_contract_passed {
        push_reason(
            &mut blocking_reasons,
            &mut blocking_reason_key_counts,
            &mut blocking_reason_family_counts,
            "release_soak_interop_profile_contract_invalid",
            "interop_profile_contract_invalid",
            "summary_contract",
        );
    }
    if interop_required_no_silent_fallback_profile_set
        != expected_required_no_silent_fallback_profile_set
    {
        push_reason(
            &mut blocking_reasons,
            &mut blocking_reason_key_counts,
            &mut blocking_reason_family_counts,
            "release_soak_interop_required_no_silent_fallback_profile_set_mismatch",
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
            "release_soak_queue_pressure_surface_failed",
            "queue_pressure_surface_failed",
            "capacity",
        );
    }

    let policy_disabled_fallback_surface_passed =
        if interop_labels.len() == 3 && all_required_inputs_present {
            Some(!policy_disabled_fallback_surface_failed)
        } else {
            None
        };
    if policy_disabled_fallback_surface_passed == Some(false) {
        push_reason(
            &mut blocking_reasons,
            &mut blocking_reason_key_counts,
            &mut blocking_reason_family_counts,
            "release_soak_policy_disabled_fallback_surface_failed",
            "policy_disabled_fallback_surface_failed",
            "transport_integrity",
        );
    }

    let transport_fallback_integrity_surface_passed = match (
        release_burn_in
            .summary
            .as_ref()
            .and_then(|summary| summary.transport_fallback_integrity_surface_passed),
        if interop_labels.len() == 3 && all_required_inputs_present {
            Some(!transport_fallback_integrity_surface_failed)
        } else {
            None
        },
    ) {
        (Some(burn_in_surface), Some(interop_surface)) => Some(burn_in_surface && interop_surface),
        _ => None,
    };
    if transport_fallback_integrity_surface_passed == Some(false) {
        push_reason(
            &mut blocking_reasons,
            &mut blocking_reason_key_counts,
            &mut blocking_reason_family_counts,
            "release_soak_transport_fallback_integrity_surface_failed",
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
        && blocking_reason_count == 0
        && degradation_hold_count == 0
        && queue_guard_tight_hold_count == 0
        && queue_pressure_hold_count == 0
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
    let interop_required_no_silent_fallback_profile_slugs =
        interop_required_no_silent_fallback_profile_set
            .into_iter()
            .collect::<Vec<_>>();
    let interop_failed_profile_slugs = interop_failed_profile_set.into_iter().collect::<Vec<_>>();

    UdpReleaseSoakSummary {
        summary_version: UDP_RELEASE_SOAK_SUMMARY_VERSION,
        comparison_schema: UDP_ROLLOUT_OPERATOR_VERDICT_SCHEMA,
        comparison_schema_version: UDP_ROLLOUT_OPERATOR_VERDICT_SCHEMA_VERSION,
        verdict_family: UDP_ROLLOUT_OPERATOR_VERDICT_FAMILY,
        decision_scope: UDP_ROLLOUT_DECISION_SCOPE_RELEASE_SOAK,
        decision_label: "release_soak",
        profile: "release_soak",
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
        release_burn_in_present,
        release_burn_in_passed,
        interop_count: interop_labels.len(),
        interop_passed_count,
        interop_failed_count,
        interop_labels,
        degradation_hold_count,
        degradation_hold_subjects,
        queue_guard_headroom_band_counts,
        queue_guard_headroom_missing_count,
        queue_guard_tight_hold_count,
        queue_pressure_hold_count,
        queue_guard_limiting_path_counts,
        interop_profile_contract_passed,
        interop_required_no_silent_fallback_profile_slugs,
        interop_failed_profile_slugs,
        explicit_fallback_profile_count,
        policy_disabled_fallback_surface_passed,
        transport_fallback_integrity_surface_passed,
        blocking_reasons,
        blocking_reason_keys,
        blocking_reason_families,
        advisory_reasons,
    }
}

fn release_burn_in_summary_contract_valid(summary: &ReleaseBurnInSummaryInput) -> bool {
    let expected_inputs = vec![
        "release_candidate_signoff".to_owned(),
        "linux_readiness".to_owned(),
        "macos_readiness".to_owned(),
        "windows_readiness".to_owned(),
        "staged_rollout_matrix".to_owned(),
    ];
    let expected_required_no_silent_fallback_profile_set =
        udp_wan_lab_required_no_silent_fallback_profile_slugs()
            .into_iter()
            .map(str::to_owned)
            .collect::<BTreeSet<_>>();
    let actual_required_no_silent_fallback_profile_set = summary
        .interop_required_no_silent_fallback_profile_slugs
        .iter()
        .cloned()
        .collect::<BTreeSet<_>>();
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
    summary.summary_version == Some(UDP_RELEASE_BURN_IN_SUMMARY_VERSION)
        && summary.comparison_schema == UDP_ROLLOUT_OPERATOR_VERDICT_SCHEMA
        && summary.comparison_schema_version == UDP_ROLLOUT_OPERATOR_VERDICT_SCHEMA_VERSION
        && summary.verdict_family == UDP_ROLLOUT_OPERATOR_VERDICT_FAMILY
        && summary.decision_scope == UDP_ROLLOUT_DECISION_SCOPE_RELEASE_BURN_IN
        && summary.decision_label == "release_burn_in"
        && summary.profile == "release_burn_in"
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
        && summary.queue_guard_tight_hold_count
            == summary
                .queue_guard_headroom_band_counts
                .get("tight")
                .copied()
                .unwrap_or(0)
        && summary.queue_pressure_hold_count <= 4
        && summary
            .interop_required_no_silent_fallback_profile_slugs
            .len()
            == expected_required_no_silent_fallback_profile_set.len()
        && actual_required_no_silent_fallback_profile_set
            == expected_required_no_silent_fallback_profile_set
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
                || summary.queue_pressure_hold_count != 0
                || summary.queue_guard_headroom_missing_count != 0
                || summary.transport_fallback_integrity_surface_passed != Some(true)
                || !summary.interop_profile_contract_passed))
}

fn interop_summary_contract_valid(summary: &InteropLabSummaryInput) -> bool {
    let expected_profile_set = udp_wan_lab_profile_slugs()
        .into_iter()
        .map(str::to_owned)
        .collect::<BTreeSet<_>>();
    let actual_profile_set = summary
        .profile_slugs
        .iter()
        .cloned()
        .collect::<BTreeSet<_>>();
    let expected_required_no_silent_fallback_profile_set =
        udp_wan_lab_required_no_silent_fallback_profile_slugs()
            .into_iter()
            .map(str::to_owned)
            .collect::<BTreeSet<_>>();
    let actual_required_no_silent_fallback_profile_set = summary
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
        && summary.required_no_silent_fallback_profile_count
            == expected_required_no_silent_fallback_profile_set.len()
        && summary.required_no_silent_fallback_passed_count
            <= summary.required_no_silent_fallback_profile_count
        && summary.required_no_silent_fallback_profile_slugs.len()
            == expected_required_no_silent_fallback_profile_set.len()
        && actual_required_no_silent_fallback_profile_set
            == expected_required_no_silent_fallback_profile_set
        && summary.explicit_fallback_profile_count <= summary.profile_count
        && !(summary.all_passed
            && (!summary.failed_profile_slugs.is_empty()
                || summary.required_no_silent_fallback_passed_count
                    != summary.required_no_silent_fallback_profile_count
                || !summary.policy_disabled_fallback_surface_passed
                || !summary.queue_pressure_surface_passed
                || !summary.transport_fallback_integrity_surface_passed))
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

fn print_text_summary(summary: &UdpReleaseSoakSummary, summary_path: &Path) {
    println!("Verta UDP release soak summary:");
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
        "- release_burn_in: present={} passed={}",
        summary.release_burn_in_present, summary.release_burn_in_passed
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
        "- interop_profile_contract_passed: {}",
        summary.interop_profile_contract_passed
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
    if summary.interop_labels.is_empty() {
        println!("- interop_labels: none");
    } else {
        println!("- interop_labels: {}", summary.interop_labels.join(", "));
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
    if summary.interop_failed_profile_slugs.is_empty() {
        println!("- interop_failed_profile_slugs: none");
    } else {
        println!(
            "- interop_failed_profile_slugs: {}",
            summary.interop_failed_profile_slugs.join(", ")
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
    if summary.queue_guard_headroom_band_counts.is_empty() {
        println!("- queue_guard_headroom_band_counts: none");
    } else {
        println!(
            "- queue_guard_headroom_band_counts: {}",
            render_counts(&summary.queue_guard_headroom_band_counts)
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

fn parse_args<I>(mut args: I) -> Result<ReleaseSoakArgs, String>
where
    I: Iterator<Item = String>,
{
    let mut parsed = ReleaseSoakArgs::default();
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
            "--release-burn-in" => {
                parsed.release_burn_in =
                    Some(PathBuf::from(args.next().ok_or_else(|| {
                        "--release-burn-in requires a value".to_owned()
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
    "Usage: cargo run -p ns-testkit --example udp_release_soak -- [--format text|json] [--summary-path <path>] [--release-burn-in <path>] [--linux-interop <path>] [--macos-interop <path>] [--windows-interop <path>]".to_owned()
}

fn default_release_burn_in_input() -> PathBuf {
    prefer_verta_input_path("udp-release-burn-in-summary.json")
}

fn default_linux_interop_input() -> PathBuf {
    prefer_verta_input_path("udp-interop-lab-summary-linux.json")
}

fn default_macos_interop_input() -> PathBuf {
    prefer_verta_input_path("udp-interop-lab-summary-macos.json")
}

fn default_windows_interop_input() -> PathBuf {
    prefer_verta_input_path("udp-interop-lab-summary-windows.json")
}

fn default_summary_path() -> PathBuf {
    verta_output_path("udp-release-soak-summary.json")
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

    fn all_profile_slugs() -> Vec<String> {
        udp_wan_lab_profile_slugs()
            .into_iter()
            .map(str::to_owned)
            .collect()
    }

    fn required_profile_slugs() -> Vec<String> {
        let mut values = udp_wan_lab_required_no_silent_fallback_profile_slugs()
            .into_iter()
            .map(str::to_owned)
            .collect::<Vec<_>>();
        values.sort();
        values
    }

    fn ready_release_burn_in() -> LoadedReleaseBurnInInput {
        LoadedInput {
            label: "release_burn_in".to_owned(),
            present: true,
            parse_error: None,
            summary: Some(ReleaseBurnInSummaryInput {
                summary_version: Some(UDP_RELEASE_BURN_IN_SUMMARY_VERSION),
                comparison_schema: "udp_rollout_operator_verdict".to_owned(),
                comparison_schema_version: UDP_ROLLOUT_OPERATOR_VERDICT_SCHEMA_VERSION,
                verdict_family: "udp_rollout_operator_decision".to_owned(),
                decision_scope: "release_burn_in".to_owned(),
                decision_label: "release_burn_in".to_owned(),
                profile: "release_burn_in".to_owned(),
                verdict: "ready".to_owned(),
                evidence_state: "complete".to_owned(),
                gate_state: "passed".to_owned(),
                gate_state_reason: "all_required_inputs_passed".to_owned(),
                gate_state_reason_family: "ready".to_owned(),
                active_fuzz_required: true,
                required_inputs: vec![
                    "release_candidate_signoff".to_owned(),
                    "linux_readiness".to_owned(),
                    "macos_readiness".to_owned(),
                    "windows_readiness".to_owned(),
                    "staged_rollout_matrix".to_owned(),
                ],
                considered_inputs: vec![
                    "release_candidate_signoff".to_owned(),
                    "linux_readiness".to_owned(),
                    "macos_readiness".to_owned(),
                    "windows_readiness".to_owned(),
                    "staged_rollout_matrix".to_owned(),
                ],
                missing_required_inputs: Vec::new(),
                missing_required_input_count: 0,
                required_input_count: 5,
                required_input_missing_count: 0,
                required_input_failed_count: 0,
                required_input_unready_count: 0,
                required_input_present_count: 5,
                required_input_passed_count: 5,
                all_required_inputs_present: true,
                all_required_inputs_passed: true,
                blocking_reason_count: 0,
                blocking_reason_key_count: 0,
                blocking_reason_family_count: 0,
                blocking_reason_key_counts: BTreeMap::new(),
                blocking_reason_family_counts: BTreeMap::new(),
                degradation_hold_count: 0,
                degradation_hold_subjects: Vec::new(),
                queue_guard_headroom_band_counts: BTreeMap::from([("healthy".to_owned(), 4usize)]),
                queue_guard_headroom_missing_count: 0,
                queue_guard_tight_hold_count: 0,
                queue_pressure_hold_count: 0,
                queue_guard_limiting_path_counts: BTreeMap::from([(
                    "queue_recovery_send".to_owned(),
                    6usize,
                )]),
                interop_profile_contract_passed: true,
                interop_required_no_silent_fallback_profile_slugs: required_profile_slugs(),
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
                explicit_fallback_profile_count: 3,
                policy_disabled_fallback_surface_passed: true,
                queue_pressure_surface_passed: true,
                transport_fallback_integrity_surface_passed: true,
            }),
        }
    }

    #[test]
    fn release_soak_emits_ready_operator_schema() {
        let summary = build_release_soak_summary(
            ready_release_burn_in(),
            vec![
                ready_interop("linux_interop"),
                ready_interop("macos_interop"),
                ready_interop("windows_interop"),
            ],
        );

        assert_eq!(summary.summary_version, UDP_RELEASE_SOAK_SUMMARY_VERSION);
        assert_eq!(
            summary.comparison_schema_version,
            UDP_ROLLOUT_OPERATOR_VERDICT_SCHEMA_VERSION
        );
        assert_eq!(summary.decision_scope, "release_soak");
        assert_eq!(summary.verdict, "ready");
        assert_eq!(summary.gate_state, "passed");
        assert_eq!(summary.gate_state_reason, "all_required_inputs_passed");
        assert_eq!(summary.required_input_count, 4);
        assert_eq!(summary.required_input_passed_count, 4);
        assert_eq!(summary.interop_count, 3);
        assert_eq!(summary.interop_passed_count, 3);
        assert_eq!(summary.interop_failed_count, 0);
        assert!(summary.release_burn_in_passed);
        assert_eq!(summary.queue_guard_headroom_missing_count, 0);
        assert_eq!(summary.queue_guard_tight_hold_count, 0);
        assert_eq!(summary.queue_pressure_hold_count, 0);
        assert!(summary.interop_profile_contract_passed);
        assert_eq!(
            summary.interop_required_no_silent_fallback_profile_slugs,
            required_profile_slugs()
        );
        assert_eq!(summary.policy_disabled_fallback_surface_passed, Some(true));
        assert_eq!(
            summary.transport_fallback_integrity_surface_passed,
            Some(true)
        );
    }

    #[test]
    fn release_soak_fails_closed_without_windows_interop() {
        let summary = build_release_soak_summary(
            ready_release_burn_in(),
            vec![
                ready_interop("linux_interop"),
                ready_interop("macos_interop"),
                LoadedInput::<InteropLabSummaryInput> {
                    label: "windows_interop".to_owned(),
                    present: false,
                    parse_error: None,
                    summary: None,
                },
            ],
        );

        assert_eq!(summary.verdict, "hold");
        assert_eq!(summary.gate_state, "blocked");
        assert_eq!(summary.required_input_missing_count, 1);
        assert!(
            summary
                .missing_required_inputs
                .iter()
                .any(|value| value == "windows_interop")
        );
    }
}
