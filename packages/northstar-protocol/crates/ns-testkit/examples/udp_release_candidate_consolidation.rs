use ns_testkit::{
    UDP_INTEROP_PROFILE_CATALOG_SOURCE_LANE_COMPATIBLE_HOST,
    UDP_ROLLOUT_DECISION_SCOPE_RELEASE_CANDIDATE_CONSOLIDATION,
    UDP_ROLLOUT_DECISION_SCOPE_RELEASE_STABILITY_SIGNOFF, UDP_ROLLOUT_OPERATOR_VERDICT_FAMILY,
    UDP_ROLLOUT_OPERATOR_VERDICT_SCHEMA, UDP_ROLLOUT_OPERATOR_VERDICT_SCHEMA_VERSION,
    UdpWanLabCommandKind, blocking_reason_accounting_consistent, repo_root,
    rollout_queue_hold_present, summarize_rollout_gate_state, udp_wan_lab_profile_by_slug,
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
struct ReleaseCandidateConsolidationArgs {
    format: Option<OutputFormat>,
    summary_path: Option<PathBuf>,
    release_stability_signoff: Option<PathBuf>,
    linux_interop_catalog: Option<PathBuf>,
    macos_interop_catalog: Option<PathBuf>,
    windows_interop_catalog: Option<PathBuf>,
}

const UDP_RELEASE_STABILITY_SIGNOFF_SUMMARY_VERSION: u8 = 2;
const UDP_RELEASE_CANDIDATE_CONSOLIDATION_SUMMARY_VERSION: u8 = 2;

#[derive(Debug, Deserialize)]
struct ReleaseStabilitySignoffSummaryInput {
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
    queue_hold_input_count: usize,
    #[serde(default)]
    queue_hold_host_count: usize,
    #[serde(default)]
    queue_guard_limiting_path_counts: BTreeMap<String, usize>,
    #[serde(default)]
    interop_profile_contract_passed: bool,
    #[serde(default)]
    interop_profile_catalog_contract_passed: bool,
    #[serde(default)]
    interop_profile_catalog_schema_version: u8,
    #[serde(default)]
    interop_profile_catalog_host_labels: Vec<String>,
    #[serde(default)]
    interop_profile_catalog_source_lane: String,
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
    blocking_reasons: Vec<String>,
    #[serde(default)]
    blocking_reason_keys: Vec<String>,
    #[serde(default)]
    blocking_reason_families: Vec<String>,
}

#[derive(Debug, Deserialize)]
struct InteropProfileCatalogEntry {
    slug: String,
    spec_suite_ids: Vec<String>,
    description: String,
    command_kind: String,
    command_selector: String,
    requires_no_silent_fallback: bool,
}

#[derive(Debug, Deserialize)]
struct InteropProfileCatalogInput {
    catalog_schema: String,
    catalog_schema_version: u8,
    host_label: String,
    source_lane: String,
    profiles: Vec<InteropProfileCatalogEntry>,
}

#[derive(Debug)]
struct LoadedInput<T> {
    label: String,
    present: bool,
    parse_error: Option<String>,
    summary: Option<T>,
}

type LoadedReleaseStabilityInput = LoadedInput<ReleaseStabilitySignoffSummaryInput>;
type LoadedCatalogInput = LoadedInput<InteropProfileCatalogInput>;

#[derive(Debug, Serialize)]
struct UdpReleaseCandidateConsolidationSummary {
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
    release_stability_signoff_present: bool,
    release_stability_signoff_passed: bool,
    interop_profile_catalog_count: usize,
    interop_profile_catalog_passed_count: usize,
    interop_profile_catalog_labels: Vec<String>,
    degradation_hold_count: usize,
    degradation_hold_subjects: Vec<String>,
    queue_guard_headroom_band_counts: BTreeMap<String, usize>,
    queue_guard_headroom_missing_count: usize,
    queue_guard_tight_hold_count: usize,
    queue_pressure_hold_count: usize,
    queue_hold_input_count: usize,
    queue_hold_host_count: usize,
    queue_guard_limiting_path_counts: BTreeMap<String, usize>,
    interop_profile_contract_passed: bool,
    interop_profile_catalog_contract_passed: bool,
    interop_profile_catalog_schema_version: u8,
    interop_profile_catalog_host_labels: Vec<String>,
    interop_profile_catalog_source_lane: String,
    interop_profile_slugs: Vec<String>,
    interop_required_no_silent_fallback_profile_slugs: Vec<String>,
    interop_failed_profile_slugs: Vec<String>,
    interop_failed_profile_count: usize,
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
    let release_stability_signoff_path = args
        .release_stability_signoff
        .unwrap_or_else(default_release_stability_signoff_input);
    let linux_catalog_path = args
        .linux_interop_catalog
        .unwrap_or_else(default_linux_interop_catalog_input);
    let macos_catalog_path = args
        .macos_interop_catalog
        .unwrap_or_else(default_macos_interop_catalog_input);
    let windows_catalog_path = args
        .windows_interop_catalog
        .unwrap_or_else(default_windows_interop_catalog_input);
    let summary = build_release_candidate_consolidation_summary(
        load_input::<ReleaseStabilitySignoffSummaryInput>(
            "release_stability_signoff",
            &release_stability_signoff_path,
        ),
        vec![
            load_input::<InteropProfileCatalogInput>("linux_interop_catalog", &linux_catalog_path),
            load_input::<InteropProfileCatalogInput>("macos_interop_catalog", &macos_catalog_path),
            load_input::<InteropProfileCatalogInput>(
                "windows_interop_catalog",
                &windows_catalog_path,
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
        return Err("udp release candidate consolidation is not ready".into());
    }

    Ok(())
}

fn build_release_candidate_consolidation_summary(
    release_stability_signoff: LoadedReleaseStabilityInput,
    catalog_inputs: Vec<LoadedCatalogInput>,
) -> UdpReleaseCandidateConsolidationSummary {
    let required_inputs = vec![
        "release_stability_signoff".to_owned(),
        "linux_interop_catalog".to_owned(),
        "macos_interop_catalog".to_owned(),
        "windows_interop_catalog".to_owned(),
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

    let mut present_required_inputs = BTreeSet::new();
    let mut passed_required_inputs = BTreeSet::new();
    let mut blocking_reasons = Vec::new();
    let mut blocking_reason_key_counts = BTreeMap::new();
    let mut blocking_reason_family_counts = BTreeMap::new();
    let mut degradation_hold_subjects = Vec::new();
    let mut queue_guard_headroom_band_counts = BTreeMap::new();
    let mut queue_guard_limiting_path_counts = BTreeMap::new();
    let mut queue_guard_headroom_missing_count = 0usize;
    let mut queue_guard_tight_hold_count = 0usize;
    let mut queue_pressure_hold_count = 0usize;
    let mut queue_hold_input_count = 0usize;
    let mut queue_hold_host_count = 0usize;
    let mut interop_profile_set = BTreeSet::new();
    let mut interop_required_profile_set = BTreeSet::new();
    let mut interop_failed_profile_set = BTreeSet::new();
    let mut explicit_fallback_profile_count = 0usize;
    let mut all_consumed_inputs_contract_valid = true;
    let mut interop_profile_catalog_labels = Vec::new();
    let mut interop_profile_catalog_host_labels = Vec::new();
    let mut interop_profile_catalog_source_lane = String::new();
    let mut interop_profile_catalog_passed_count = 0usize;
    let mut interop_profile_catalog_contract_passed = true;
    let mut policy_disabled_fallback_surface_passed = None;
    let mut transport_fallback_integrity_surface_passed = None;

    let release_stability_signoff_present = release_stability_signoff.present;
    if release_stability_signoff_present {
        present_required_inputs.insert("release_stability_signoff".to_owned());
    }
    let release_stability_signoff_passed = match release_stability_signoff.summary.as_ref() {
        Some(summary)
            if release_stability_signoff.present
                && release_stability_signoff.parse_error.is_none()
                && release_stability_signoff_summary_contract_valid(summary)
                && summary.verdict == "ready"
                && summary.evidence_state == "complete"
                && summary.gate_state == "passed"
                && summary.active_fuzz_required
                && summary.all_required_inputs_present
                && summary.all_required_inputs_passed
                && summary.blocking_reason_count == 0
                && summary.degradation_hold_count == 0
                && !rollout_queue_hold_present(
                    summary.queue_guard_headroom_missing_count,
                    summary.queue_guard_tight_hold_count,
                    summary.queue_pressure_hold_count,
                )
                && summary.queue_hold_input_count == 0
                && summary.queue_hold_host_count == 0
                && summary.policy_disabled_fallback_surface_passed == Some(true)
                && summary.transport_fallback_integrity_surface_passed == Some(true)
                && summary.interop_profile_contract_passed
                && summary.interop_profile_catalog_contract_passed =>
        {
            merge_counts(
                &mut queue_guard_headroom_band_counts,
                &summary.queue_guard_headroom_band_counts,
            );
            merge_counts(
                &mut queue_guard_limiting_path_counts,
                &summary.queue_guard_limiting_path_counts,
            );
            queue_guard_headroom_missing_count += summary.queue_guard_headroom_missing_count;
            queue_guard_tight_hold_count += summary.queue_guard_tight_hold_count;
            queue_pressure_hold_count += summary.queue_pressure_hold_count;
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
            interop_profile_catalog_contract_passed = interop_profile_catalog_contract_passed
                && summary.interop_profile_catalog_contract_passed;
            interop_profile_catalog_source_lane =
                summary.interop_profile_catalog_source_lane.clone();
            policy_disabled_fallback_surface_passed =
                summary.policy_disabled_fallback_surface_passed;
            transport_fallback_integrity_surface_passed =
                summary.transport_fallback_integrity_surface_passed;
            passed_required_inputs.insert("release_stability_signoff".to_owned());
            true
        }
        Some(summary) => {
            merge_counts(
                &mut queue_guard_headroom_band_counts,
                &summary.queue_guard_headroom_band_counts,
            );
            merge_counts(
                &mut queue_guard_limiting_path_counts,
                &summary.queue_guard_limiting_path_counts,
            );
            queue_guard_headroom_missing_count += summary.queue_guard_headroom_missing_count;
            queue_guard_tight_hold_count += summary.queue_guard_tight_hold_count;
            queue_pressure_hold_count += summary.queue_pressure_hold_count;
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
            interop_profile_catalog_contract_passed = interop_profile_catalog_contract_passed
                && summary.interop_profile_catalog_contract_passed;
            interop_profile_catalog_source_lane =
                summary.interop_profile_catalog_source_lane.clone();
            policy_disabled_fallback_surface_passed =
                summary.policy_disabled_fallback_surface_passed;
            transport_fallback_integrity_surface_passed =
                summary.transport_fallback_integrity_surface_passed;
            false
        }
        None => false,
    };

    if !release_stability_signoff.present {
        push_reason(
            &mut blocking_reasons,
            &mut blocking_reason_key_counts,
            &mut blocking_reason_family_counts,
            "missing_release_stability_signoff_summary",
            "missing_required_input",
            "summary_presence",
        );
    } else if let Some(error) = release_stability_signoff.parse_error.as_ref() {
        all_consumed_inputs_contract_valid = false;
        push_reason(
            &mut blocking_reasons,
            &mut blocking_reason_key_counts,
            &mut blocking_reason_family_counts,
            &format!("release_stability_signoff_parse_error:{error}"),
            "input_parse_error",
            "summary_contract",
        );
    } else if let Some(summary) = release_stability_signoff.summary.as_ref() {
        if !release_stability_signoff_summary_contract_valid(summary) {
            all_consumed_inputs_contract_valid = false;
            push_reason(
                &mut blocking_reasons,
                &mut blocking_reason_key_counts,
                &mut blocking_reason_family_counts,
                "release_stability_signoff_summary_contract_invalid",
                "input_contract_invalid",
                "summary_contract",
            );
        } else if !release_stability_signoff_passed {
            if summary.degradation_hold_count > 0 {
                degradation_hold_subjects.push("release_stability_signoff".to_owned());
                degradation_hold_subjects.extend(summary.degradation_hold_subjects.iter().cloned());
            }
            push_reason(
                &mut blocking_reasons,
                &mut blocking_reason_key_counts,
                &mut blocking_reason_family_counts,
                "release_stability_signoff_not_ready",
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

    for input in catalog_inputs {
        interop_profile_catalog_labels.push(input.label.clone());
        if input.present {
            present_required_inputs.insert(input.label.clone());
        }
        let expected_host_label = expected_catalog_host_label(&input.label);
        let passed = match input.summary.as_ref() {
            Some(summary)
                if input.present
                    && input.parse_error.is_none()
                    && interop_profile_catalog_contract_valid(summary, expected_host_label) =>
            {
                let catalog_profile_set = summary
                    .profiles
                    .iter()
                    .map(|entry| entry.slug.clone())
                    .collect::<BTreeSet<_>>();
                let catalog_required_profile_set = summary
                    .profiles
                    .iter()
                    .filter(|entry| entry.requires_no_silent_fallback)
                    .map(|entry| entry.slug.clone())
                    .collect::<BTreeSet<_>>();
                interop_profile_set.extend(catalog_profile_set);
                interop_required_profile_set.extend(catalog_required_profile_set);
                explicit_fallback_profile_count = explicit_fallback_profile_count.max(
                    summary
                        .profiles
                        .iter()
                        .filter(|entry| !entry.requires_no_silent_fallback)
                        .count(),
                );
                interop_profile_catalog_host_labels.push(summary.host_label.clone());
                interop_profile_catalog_passed_count += 1;
                passed_required_inputs.insert(input.label.clone());
                true
            }
            Some(summary) => {
                let catalog_profile_set = summary
                    .profiles
                    .iter()
                    .map(|entry| entry.slug.clone())
                    .collect::<BTreeSet<_>>();
                let catalog_required_profile_set = summary
                    .profiles
                    .iter()
                    .filter(|entry| entry.requires_no_silent_fallback)
                    .map(|entry| entry.slug.clone())
                    .collect::<BTreeSet<_>>();
                interop_profile_set.extend(catalog_profile_set);
                interop_required_profile_set.extend(catalog_required_profile_set);
                explicit_fallback_profile_count = explicit_fallback_profile_count.max(
                    summary
                        .profiles
                        .iter()
                        .filter(|entry| !entry.requires_no_silent_fallback)
                        .count(),
                );
                interop_profile_catalog_host_labels.push(summary.host_label.clone());
                false
            }
            None => false,
        };

        if !input.present {
            interop_profile_catalog_contract_passed = false;
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
            interop_profile_catalog_contract_passed = false;
            push_reason(
                &mut blocking_reasons,
                &mut blocking_reason_key_counts,
                &mut blocking_reason_family_counts,
                &format!("{}_parse_error:{error}", input.label),
                "input_parse_error",
                "summary_contract",
            );
        } else if let Some(summary) = input.summary.as_ref() {
            if summary.catalog_schema != "udp_interop_profile_catalog" {
                all_consumed_inputs_contract_valid = false;
                interop_profile_catalog_contract_passed = false;
                push_reason(
                    &mut blocking_reasons,
                    &mut blocking_reason_key_counts,
                    &mut blocking_reason_family_counts,
                    &format!("{}_schema_unsupported", input.label),
                    "interop_catalog_schema_unsupported",
                    "summary_contract",
                );
            } else if summary.catalog_schema_version != 1 {
                all_consumed_inputs_contract_valid = false;
                interop_profile_catalog_contract_passed = false;
                push_reason(
                    &mut blocking_reasons,
                    &mut blocking_reason_key_counts,
                    &mut blocking_reason_family_counts,
                    &format!("{}_schema_version_unsupported", input.label),
                    "interop_catalog_schema_unsupported",
                    "summary_contract",
                );
            } else if summary.host_label != expected_host_label {
                all_consumed_inputs_contract_valid = false;
                interop_profile_catalog_contract_passed = false;
                push_reason(
                    &mut blocking_reasons,
                    &mut blocking_reason_key_counts,
                    &mut blocking_reason_family_counts,
                    &format!("{}_host_label_mismatch", input.label),
                    "interop_catalog_host_label_mismatch",
                    "summary_contract",
                );
            } else if summary.source_lane != UDP_INTEROP_PROFILE_CATALOG_SOURCE_LANE_COMPATIBLE_HOST
            {
                all_consumed_inputs_contract_valid = false;
                interop_profile_catalog_contract_passed = false;
                push_reason(
                    &mut blocking_reasons,
                    &mut blocking_reason_key_counts,
                    &mut blocking_reason_family_counts,
                    "release_candidate_consolidation_interop_catalog_source_lane_invalid",
                    "interop_catalog_source_lane_invalid",
                    "summary_contract",
                );
            } else if !interop_profile_catalog_contract_valid(summary, expected_host_label) {
                all_consumed_inputs_contract_valid = false;
                interop_profile_catalog_contract_passed = false;
                push_reason(
                    &mut blocking_reasons,
                    &mut blocking_reason_key_counts,
                    &mut blocking_reason_family_counts,
                    &format!("{}_contract_invalid", input.label),
                    "input_contract_invalid",
                    "summary_contract",
                );
            } else if !passed {
                interop_profile_catalog_contract_passed = false;
                push_reason(
                    &mut blocking_reasons,
                    &mut blocking_reason_key_counts,
                    &mut blocking_reason_family_counts,
                    &format!("{}_not_ready", input.label),
                    "input_not_ready",
                    "gating",
                );
            }
        }
    }

    interop_profile_catalog_labels.sort();
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
    let interop_profile_catalog_count = interop_profile_catalog_labels.len();
    let expected_catalog_host_labels = ["linux", "macos", "windows"]
        .into_iter()
        .map(str::to_owned)
        .collect::<Vec<_>>();
    let queue_hold_input_count =
        queue_hold_input_count.max(usize::from(rollout_queue_hold_present(
            queue_guard_headroom_missing_count,
            queue_guard_tight_hold_count,
            queue_pressure_hold_count,
        )));

    interop_profile_catalog_contract_passed = interop_profile_catalog_contract_passed
        && interop_profile_catalog_count == 3
        && interop_profile_catalog_passed_count == interop_profile_catalog_count
        && interop_profile_catalog_host_labels == expected_catalog_host_labels
        && interop_profile_catalog_source_lane
            == UDP_INTEROP_PROFILE_CATALOG_SOURCE_LANE_COMPATIBLE_HOST
        && interop_profile_set == expected_profile_set
        && interop_required_profile_set == expected_required_profile_set;
    let unique_catalog_host_label_count = interop_profile_catalog_host_labels
        .iter()
        .collect::<BTreeSet<_>>()
        .len();
    if unique_catalog_host_label_count != interop_profile_catalog_host_labels.len() {
        push_reason(
            &mut blocking_reasons,
            &mut blocking_reason_key_counts,
            &mut blocking_reason_family_counts,
            "release_candidate_consolidation_interop_catalog_duplicate_host_label",
            "interop_catalog_duplicate_host_label",
            "summary_contract",
        );
    }
    if interop_profile_catalog_host_labels != expected_catalog_host_labels {
        push_reason(
            &mut blocking_reasons,
            &mut blocking_reason_key_counts,
            &mut blocking_reason_family_counts,
            "release_candidate_consolidation_interop_catalog_host_coverage_incomplete",
            "interop_catalog_host_coverage_incomplete",
            "summary_presence",
        );
    }
    if !interop_profile_catalog_contract_passed {
        push_reason(
            &mut blocking_reasons,
            &mut blocking_reason_key_counts,
            &mut blocking_reason_family_counts,
            "release_candidate_consolidation_interop_profile_catalog_contract_invalid",
            "interop_profile_catalog_contract_invalid",
            "summary_contract",
        );
    }

    let interop_profile_contract_passed =
        release_stability_signoff
            .summary
            .as_ref()
            .is_some_and(|summary| {
                release_stability_signoff_summary_contract_valid(summary)
                    && summary.interop_profile_contract_passed
            })
            && interop_profile_catalog_contract_passed
            && interop_profile_set == expected_profile_set
            && interop_required_profile_set == expected_required_profile_set;
    if !interop_profile_contract_passed {
        push_reason(
            &mut blocking_reasons,
            &mut blocking_reason_key_counts,
            &mut blocking_reason_family_counts,
            "release_candidate_consolidation_interop_profile_contract_invalid",
            "interop_profile_contract_invalid",
            "summary_contract",
        );
    }
    if interop_required_profile_set != expected_required_profile_set {
        push_reason(
            &mut blocking_reasons,
            &mut blocking_reason_key_counts,
            &mut blocking_reason_family_counts,
            "release_candidate_consolidation_interop_required_no_silent_fallback_profile_set_mismatch",
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
            "release_candidate_consolidation_queue_pressure_surface_failed",
            "queue_pressure_surface_failed",
            "capacity",
        );
    }
    if queue_hold_host_count > 0 {
        push_reason(
            &mut blocking_reasons,
            &mut blocking_reason_key_counts,
            &mut blocking_reason_family_counts,
            "release_candidate_consolidation_queue_hold_hosts_present",
            "queue_hold_host_present",
            "capacity",
        );
    }
    if policy_disabled_fallback_surface_passed == Some(false) {
        push_reason(
            &mut blocking_reasons,
            &mut blocking_reason_key_counts,
            &mut blocking_reason_family_counts,
            "release_candidate_consolidation_policy_disabled_fallback_surface_failed",
            "policy_disabled_fallback_surface_failed",
            "transport_integrity",
        );
    }
    if transport_fallback_integrity_surface_passed == Some(false) {
        push_reason(
            &mut blocking_reasons,
            &mut blocking_reason_key_counts,
            &mut blocking_reason_family_counts,
            "release_candidate_consolidation_transport_fallback_integrity_surface_failed",
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
        && !rollout_queue_hold_present(
            queue_guard_headroom_missing_count,
            queue_guard_tight_hold_count,
            queue_pressure_hold_count,
        )
        && queue_hold_input_count == 0
        && queue_hold_host_count == 0
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
    let interop_profile_slugs = interop_profile_set.into_iter().collect::<Vec<_>>();
    let interop_required_no_silent_fallback_profile_slugs =
        interop_required_profile_set.into_iter().collect::<Vec<_>>();
    let interop_failed_profile_slugs = interop_failed_profile_set.into_iter().collect::<Vec<_>>();
    let interop_failed_profile_count = interop_failed_profile_slugs.len();

    UdpReleaseCandidateConsolidationSummary {
        summary_version: UDP_RELEASE_CANDIDATE_CONSOLIDATION_SUMMARY_VERSION,
        comparison_schema: UDP_ROLLOUT_OPERATOR_VERDICT_SCHEMA,
        comparison_schema_version: UDP_ROLLOUT_OPERATOR_VERDICT_SCHEMA_VERSION,
        verdict_family: UDP_ROLLOUT_OPERATOR_VERDICT_FAMILY,
        decision_scope: UDP_ROLLOUT_DECISION_SCOPE_RELEASE_CANDIDATE_CONSOLIDATION,
        decision_label: "release_candidate_consolidation",
        profile: "release_candidate_consolidation",
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
        release_stability_signoff_present,
        release_stability_signoff_passed,
        interop_profile_catalog_count,
        interop_profile_catalog_passed_count,
        interop_profile_catalog_labels,
        degradation_hold_count,
        degradation_hold_subjects,
        queue_guard_headroom_band_counts,
        queue_guard_headroom_missing_count,
        queue_guard_tight_hold_count,
        queue_pressure_hold_count,
        queue_hold_input_count,
        queue_hold_host_count,
        queue_guard_limiting_path_counts,
        interop_profile_contract_passed,
        interop_profile_catalog_contract_passed,
        interop_profile_catalog_schema_version: release_stability_signoff
            .summary
            .as_ref()
            .map(|summary| summary.interop_profile_catalog_schema_version)
            .unwrap_or(1),
        interop_profile_catalog_host_labels,
        interop_profile_catalog_source_lane,
        interop_profile_slugs,
        interop_required_no_silent_fallback_profile_slugs,
        interop_failed_profile_slugs,
        interop_failed_profile_count,
        explicit_fallback_profile_count,
        policy_disabled_fallback_surface_passed,
        transport_fallback_integrity_surface_passed,
        blocking_reasons,
        blocking_reason_keys,
        blocking_reason_families,
        advisory_reasons: Vec::new(),
    }
}

fn release_stability_signoff_summary_contract_valid(
    summary: &ReleaseStabilitySignoffSummaryInput,
) -> bool {
    let expected_inputs = vec![
        "release_readiness_burndown".to_owned(),
        "linux_interop".to_owned(),
        "macos_interop".to_owned(),
        "windows_interop".to_owned(),
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

    summary.summary_version == Some(UDP_RELEASE_STABILITY_SIGNOFF_SUMMARY_VERSION)
        && summary.comparison_schema == UDP_ROLLOUT_OPERATOR_VERDICT_SCHEMA
        && summary.comparison_schema_version == UDP_ROLLOUT_OPERATOR_VERDICT_SCHEMA_VERSION
        && summary.verdict_family == UDP_ROLLOUT_OPERATOR_VERDICT_FAMILY
        && summary.decision_scope == UDP_ROLLOUT_DECISION_SCOPE_RELEASE_STABILITY_SIGNOFF
        && summary.decision_label == "release_stability_signoff"
        && summary.profile == "release_stability_signoff"
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
        && summary.queue_hold_host_count <= 3
        && summary.queue_hold_host_count <= summary.queue_hold_input_count
        && summary
            .interop_required_no_silent_fallback_profile_slugs
            .len()
            == expected_required_profile_set.len()
        && actual_required_profile_set == expected_required_profile_set
        && summary.interop_profile_catalog_schema_version == 1
        && summary.interop_profile_catalog_host_labels
            == vec!["linux".to_owned(), "macos".to_owned(), "windows".to_owned()]
        && summary.interop_profile_catalog_source_lane
            == UDP_INTEROP_PROFILE_CATALOG_SOURCE_LANE_COMPATIBLE_HOST
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
                || rollout_queue_hold_present(
                    summary.queue_guard_headroom_missing_count,
                    summary.queue_guard_tight_hold_count,
                    summary.queue_pressure_hold_count,
                )
                || summary.queue_hold_input_count != 0
                || summary.queue_hold_host_count != 0
                || summary.transport_fallback_integrity_surface_passed != Some(true)
                || summary.policy_disabled_fallback_surface_passed != Some(true)
                || !summary.interop_profile_contract_passed
                || !summary.interop_profile_catalog_contract_passed))
}

fn interop_profile_catalog_contract_valid(
    summary: &InteropProfileCatalogInput,
    expected_host_label: &str,
) -> bool {
    let expected_profile_set = udp_wan_lab_profile_slugs()
        .into_iter()
        .map(str::to_owned)
        .collect::<BTreeSet<_>>();
    let actual_profile_set = summary
        .profiles
        .iter()
        .map(|entry| entry.slug.clone())
        .collect::<BTreeSet<_>>();
    let expected_required_profile_set = udp_wan_lab_required_no_silent_fallback_profile_slugs()
        .into_iter()
        .map(str::to_owned)
        .collect::<BTreeSet<_>>();
    let actual_required_profile_set = summary
        .profiles
        .iter()
        .filter(|entry| entry.requires_no_silent_fallback)
        .map(|entry| entry.slug.clone())
        .collect::<BTreeSet<_>>();

    summary.catalog_schema == "udp_interop_profile_catalog"
        && summary.catalog_schema_version == 1
        && summary.host_label == expected_host_label
        && summary.source_lane == UDP_INTEROP_PROFILE_CATALOG_SOURCE_LANE_COMPATIBLE_HOST
        && summary.profiles.len() == expected_profile_set.len()
        && actual_profile_set.len() == summary.profiles.len()
        && actual_profile_set == expected_profile_set
        && actual_required_profile_set == expected_required_profile_set
        && summary.profiles.iter().all(|entry| {
            !entry.slug.trim().is_empty()
                && !entry.description.trim().is_empty()
                && !entry.command_kind.trim().is_empty()
                && !entry.command_selector.trim().is_empty()
                && entry
                    .spec_suite_ids
                    .iter()
                    .all(|value| !value.trim().is_empty())
                && udp_wan_lab_profile_by_slug(&entry.slug).is_some_and(|profile| {
                    let expected_spec_suite_ids = profile
                        .spec_suite_ids
                        .iter()
                        .map(|value| (*value).to_owned())
                        .collect::<Vec<_>>();
                    entry.spec_suite_ids == expected_spec_suite_ids
                        && entry.description == profile.description
                        && entry.command_kind == command_kind_label(profile.command_kind)
                        && entry.command_selector == profile.command_selector
                        && entry.requires_no_silent_fallback == profile.requires_no_silent_fallback
                })
        })
}

fn expected_catalog_host_label(label: &str) -> &'static str {
    match label {
        "linux_interop_catalog" => "linux",
        "macos_interop_catalog" => "macos",
        "windows_interop_catalog" => "windows",
        _ => "unknown",
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

fn print_text_summary(summary: &UdpReleaseCandidateConsolidationSummary, summary_path: &Path) {
    println!("Northstar UDP release candidate consolidation summary:");
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
        "- release_stability_signoff: present={} passed={}",
        summary.release_stability_signoff_present, summary.release_stability_signoff_passed
    );
    println!(
        "- interop_profile_catalog_counts: total={} passed={}",
        summary.interop_profile_catalog_count, summary.interop_profile_catalog_passed_count
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
        "- interop_profile_catalog_labels: {}",
        summary.interop_profile_catalog_labels.join(", ")
    );
    if summary.interop_profile_slugs.is_empty() {
        println!("- interop_profile_slugs: none");
    } else {
        println!(
            "- interop_profile_slugs: {}",
            summary.interop_profile_slugs.join(", ")
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
    println!(
        "- blocking_reason_key_counts: {}",
        render_counts(&summary.blocking_reason_key_counts)
    );
    println!(
        "- blocking_reason_family_counts: {}",
        render_counts(&summary.blocking_reason_family_counts)
    );
    println!(
        "- queue_guard_headroom_band_counts: {}",
        render_counts(&summary.queue_guard_headroom_band_counts)
    );
    println!(
        "- queue_guard_limiting_path_counts: {}",
        render_counts(&summary.queue_guard_limiting_path_counts)
    );
    println!("- summary_path: {}", summary_path.display());
}

fn parse_args<I>(args: I) -> Result<ReleaseCandidateConsolidationArgs, Box<dyn std::error::Error>>
where
    I: IntoIterator<Item = String>,
{
    let mut parsed = ReleaseCandidateConsolidationArgs::default();
    let mut iter = args.into_iter();
    while let Some(argument) = iter.next() {
        match argument.as_str() {
            "--summary-path" => {
                parsed.summary_path = Some(PathBuf::from(
                    iter.next()
                        .ok_or("--summary-path requires a path argument")?,
                ));
            }
            "--release-stability-signoff" => {
                parsed.release_stability_signoff = Some(PathBuf::from(
                    iter.next()
                        .ok_or("--release-stability-signoff requires a path argument")?,
                ));
            }
            "--linux-interop-catalog" => {
                parsed.linux_interop_catalog = Some(PathBuf::from(
                    iter.next()
                        .ok_or("--linux-interop-catalog requires a path argument")?,
                ));
            }
            "--macos-interop-catalog" => {
                parsed.macos_interop_catalog = Some(PathBuf::from(
                    iter.next()
                        .ok_or("--macos-interop-catalog requires a path argument")?,
                ));
            }
            "--windows-interop-catalog" => {
                parsed.windows_interop_catalog = Some(PathBuf::from(
                    iter.next()
                        .ok_or("--windows-interop-catalog requires a path argument")?,
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
        "Usage: cargo run -p ns-testkit --example udp_release_candidate_consolidation -- [--summary-path <path>] [--release-stability-signoff <path>] [--linux-interop-catalog <path>] [--macos-interop-catalog <path>] [--windows-interop-catalog <path>] [--format text|json]"
    );
}

fn default_release_stability_signoff_input() -> PathBuf {
    repo_root()
        .join("target")
        .join("northstar")
        .join("udp-release-stability-signoff-summary.json")
}

fn default_linux_interop_catalog_input() -> PathBuf {
    repo_root()
        .join("target")
        .join("northstar")
        .join("udp-interop-profile-catalog-linux.json")
}

fn default_macos_interop_catalog_input() -> PathBuf {
    repo_root()
        .join("target")
        .join("northstar")
        .join("udp-interop-profile-catalog-macos.json")
}

fn default_windows_interop_catalog_input() -> PathBuf {
    repo_root()
        .join("target")
        .join("northstar")
        .join("udp-interop-profile-catalog-windows.json")
}

fn default_summary_path() -> PathBuf {
    repo_root()
        .join("target")
        .join("northstar")
        .join("udp-release-candidate-consolidation-summary.json")
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

fn command_kind_label(kind: UdpWanLabCommandKind) -> &'static str {
    match kind {
        UdpWanLabCommandKind::LiveUdp => "live_udp",
        UdpWanLabCommandKind::Lib => "lib",
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

    fn ready_release_stability_signoff() -> LoadedReleaseStabilityInput {
        let explicit_fallback_profile_count =
            all_profile_slugs().len() - required_profile_slugs().len();
        LoadedInput {
            label: "release_stability_signoff".to_owned(),
            present: true,
            parse_error: None,
            summary: Some(ReleaseStabilitySignoffSummaryInput {
                summary_version: Some(UDP_RELEASE_STABILITY_SIGNOFF_SUMMARY_VERSION),
                comparison_schema: UDP_ROLLOUT_OPERATOR_VERDICT_SCHEMA.to_owned(),
                comparison_schema_version: UDP_ROLLOUT_OPERATOR_VERDICT_SCHEMA_VERSION,
                verdict_family: UDP_ROLLOUT_OPERATOR_VERDICT_FAMILY.to_owned(),
                decision_scope: UDP_ROLLOUT_DECISION_SCOPE_RELEASE_STABILITY_SIGNOFF.to_owned(),
                decision_label: "release_stability_signoff".to_owned(),
                profile: "release_stability_signoff".to_owned(),
                verdict: "ready".to_owned(),
                evidence_state: "complete".to_owned(),
                gate_state: "passed".to_owned(),
                gate_state_reason: "all_required_inputs_passed".to_owned(),
                gate_state_reason_family: "ready".to_owned(),
                active_fuzz_required: true,
                required_inputs: vec![
                    "release_readiness_burndown".to_owned(),
                    "linux_interop".to_owned(),
                    "macos_interop".to_owned(),
                    "windows_interop".to_owned(),
                ],
                considered_inputs: vec![
                    "release_readiness_burndown".to_owned(),
                    "linux_interop".to_owned(),
                    "macos_interop".to_owned(),
                    "windows_interop".to_owned(),
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
                queue_guard_headroom_band_counts: BTreeMap::new(),
                queue_guard_headroom_missing_count: 0,
                queue_guard_tight_hold_count: 0,
                queue_pressure_hold_count: 0,
                queue_hold_input_count: 0,
                queue_hold_host_count: 0,
                queue_guard_limiting_path_counts: BTreeMap::new(),
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
                explicit_fallback_profile_count,
                policy_disabled_fallback_surface_passed: Some(true),
                transport_fallback_integrity_surface_passed: Some(true),
                blocking_reasons: Vec::new(),
                blocking_reason_keys: Vec::new(),
                blocking_reason_families: Vec::new(),
            }),
        }
    }

    fn ready_catalog(label: &str) -> LoadedCatalogInput {
        let host_label = expected_catalog_host_label(label).to_owned();
        let profiles = all_profile_slugs()
            .into_iter()
            .map(|slug| {
                let profile = udp_wan_lab_profile_by_slug(&slug)
                    .expect("profile slug from helper should exist");
                InteropProfileCatalogEntry {
                    slug,
                    spec_suite_ids: profile
                        .spec_suite_ids
                        .iter()
                        .map(|value| (*value).to_owned())
                        .collect(),
                    description: profile.description.to_owned(),
                    command_kind: command_kind_label(profile.command_kind).to_owned(),
                    command_selector: profile.command_selector.to_owned(),
                    requires_no_silent_fallback: profile.requires_no_silent_fallback,
                }
            })
            .collect::<Vec<_>>();
        LoadedInput {
            label: label.to_owned(),
            present: true,
            parse_error: None,
            summary: Some(InteropProfileCatalogInput {
                catalog_schema: "udp_interop_profile_catalog".to_owned(),
                catalog_schema_version: 1,
                host_label,
                source_lane: UDP_INTEROP_PROFILE_CATALOG_SOURCE_LANE_COMPATIBLE_HOST.to_owned(),
                profiles,
            }),
        }
    }

    #[test]
    fn release_candidate_consolidation_summary_is_ready_with_release_stability_signoff_and_host_catalogs()
     {
        let summary = build_release_candidate_consolidation_summary(
            ready_release_stability_signoff(),
            vec![
                ready_catalog("linux_interop_catalog"),
                ready_catalog("macos_interop_catalog"),
                ready_catalog("windows_interop_catalog"),
            ],
        );

        assert_eq!(
            summary.summary_version,
            UDP_RELEASE_CANDIDATE_CONSOLIDATION_SUMMARY_VERSION
        );
        assert_eq!(
            summary.decision_scope,
            UDP_ROLLOUT_DECISION_SCOPE_RELEASE_CANDIDATE_CONSOLIDATION
        );
        assert_eq!(summary.verdict, "ready");
        assert_eq!(summary.gate_state, "passed");
        assert_eq!(summary.required_input_count, 4);
        assert_eq!(summary.required_input_passed_count, 4);
        assert_eq!(summary.interop_profile_catalog_count, 3);
        assert_eq!(summary.interop_profile_catalog_passed_count, 3);
        assert!(summary.interop_profile_contract_passed);
        assert!(summary.interop_profile_catalog_contract_passed);
        assert_eq!(
            summary.interop_profile_catalog_host_labels,
            vec!["linux".to_owned(), "macos".to_owned(), "windows".to_owned()]
        );
        assert_eq!(summary.interop_profile_slugs, all_profile_slugs());
        assert_eq!(
            summary.interop_required_no_silent_fallback_profile_slugs,
            required_profile_slugs()
        );
        assert_eq!(summary.queue_pressure_hold_count, 0);
        assert_eq!(summary.queue_hold_input_count, 0);
        assert_eq!(summary.blocking_reason_count, 0);
    }

    #[test]
    fn release_candidate_consolidation_holds_when_release_stability_signoff_reports_queue_pressure()
    {
        let mut release_stability_signoff = ready_release_stability_signoff();
        let summary = release_stability_signoff
            .summary
            .as_mut()
            .expect("ready release soak should be present");
        summary.verdict = "hold".to_owned();
        summary.gate_state = "blocked".to_owned();
        summary.gate_state_reason = "blocking_reasons_present".to_owned();
        summary.gate_state_reason_family = "gating".to_owned();
        summary.queue_pressure_hold_count = 1;
        summary.queue_hold_input_count = 1;
        summary.blocking_reason_count = 1;
        summary.blocking_reason_key_count = 1;
        summary.blocking_reason_family_count = 1;
        summary
            .blocking_reason_key_counts
            .insert("queue_pressure_surface_failed".to_owned(), 1);
        summary
            .blocking_reason_family_counts
            .insert("capacity".to_owned(), 1);
        summary.blocking_reason_keys = vec!["queue_pressure_surface_failed".to_owned()];
        summary.blocking_reason_families = vec!["capacity".to_owned()];
        summary.blocking_reasons =
            vec!["release_stability_signoff_queue_pressure_surface_failed".to_owned()];

        let summary = build_release_candidate_consolidation_summary(
            release_stability_signoff,
            vec![
                ready_catalog("linux_interop_catalog"),
                ready_catalog("macos_interop_catalog"),
                ready_catalog("windows_interop_catalog"),
            ],
        );

        assert_eq!(summary.verdict, "hold");
        assert_eq!(summary.queue_pressure_hold_count, 1);
        assert_eq!(summary.queue_hold_input_count, 1);
        assert!(summary.blocking_reasons.iter().any(
            |reason| reason == "release_candidate_consolidation_queue_pressure_surface_failed"
        ));
    }

    #[test]
    fn release_candidate_consolidation_fails_closed_when_catalog_contract_drifts() {
        let mut macos_catalog = ready_catalog("macos_interop_catalog");
        macos_catalog
            .summary
            .as_mut()
            .expect("ready catalog should be present")
            .profiles
            .pop();

        let summary = build_release_candidate_consolidation_summary(
            ready_release_stability_signoff(),
            vec![
                ready_catalog("linux_interop_catalog"),
                macos_catalog,
                ready_catalog("windows_interop_catalog"),
            ],
        );

        assert_eq!(summary.verdict, "hold");
        assert_eq!(summary.evidence_state, "incomplete");
        assert!(
            summary
                .blocking_reasons
                .iter()
                .any(|reason| reason == "macos_interop_catalog_contract_invalid")
        );
        assert!(!summary.interop_profile_catalog_contract_passed);
    }

    #[test]
    fn release_candidate_consolidation_holds_on_release_stability_blocking_reason_drift() {
        let mut release_stability_signoff = ready_release_stability_signoff();
        release_stability_signoff
            .summary
            .as_mut()
            .expect("ready release stability signoff should be present")
            .blocking_reason_keys = vec!["unexpected_key".to_owned()];

        let summary = build_release_candidate_consolidation_summary(
            release_stability_signoff,
            vec![
                ready_catalog("linux_interop_catalog"),
                ready_catalog("macos_interop_catalog"),
                ready_catalog("windows_interop_catalog"),
            ],
        );

        assert_eq!(summary.verdict, "hold");
        assert_eq!(summary.gate_state_reason, "summary_contract_invalid");
        assert_eq!(summary.gate_state_reason_family, "summary_contract");
        assert!(
            summary
                .blocking_reasons
                .iter()
                .any(|reason| reason == "release_stability_signoff_summary_contract_invalid")
        );
    }

    #[test]
    fn release_candidate_consolidation_fails_closed_when_catalog_host_labels_duplicate() {
        let mut windows_catalog = ready_catalog("windows_interop_catalog");
        windows_catalog
            .summary
            .as_mut()
            .expect("ready catalog should be present")
            .host_label = "macos".to_owned();

        let summary = build_release_candidate_consolidation_summary(
            ready_release_stability_signoff(),
            vec![
                ready_catalog("linux_interop_catalog"),
                ready_catalog("macos_interop_catalog"),
                windows_catalog,
            ],
        );

        assert_eq!(summary.verdict, "hold");
        assert!(summary.blocking_reasons.iter().any(|reason| reason
            == "release_candidate_consolidation_interop_catalog_duplicate_host_label"));
        assert!(!summary.interop_profile_catalog_contract_passed);
    }

    #[test]
    fn release_candidate_consolidation_fails_closed_when_catalog_source_lane_drifts() {
        let mut macos_catalog = ready_catalog("macos_interop_catalog");
        macos_catalog
            .summary
            .as_mut()
            .expect("ready catalog should be present")
            .source_lane = "rollout_matrix".to_owned();

        let summary = build_release_candidate_consolidation_summary(
            ready_release_stability_signoff(),
            vec![
                ready_catalog("linux_interop_catalog"),
                macos_catalog,
                ready_catalog("windows_interop_catalog"),
            ],
        );

        assert_eq!(summary.verdict, "hold");
        assert_eq!(summary.gate_state_reason, "summary_contract_invalid");
        assert!(summary.blocking_reasons.iter().any(|reason| reason
            == "release_candidate_consolidation_interop_catalog_source_lane_invalid"));
        assert!(!summary.interop_profile_catalog_contract_passed);
    }
}
