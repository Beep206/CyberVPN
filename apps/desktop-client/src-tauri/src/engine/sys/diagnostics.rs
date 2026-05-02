use crate::engine::error::AppError;
use crate::engine::helix::config::TransportBenchmarkSample;
use crate::engine::sys::net_monitor::{StealthHealthSnapshot, StealthNetworkMemory, StealthPolicy};
use crate::ipc::models::ProxyNode;
use serde::{Deserialize, Serialize};
use std::collections::HashSet;
use std::time::{Duration, SystemTime, UNIX_EPOCH};
use tauri::{AppHandle, Emitter};
use tokio::net::{TcpStream, UdpSocket};
use tokio::time::timeout;

#[derive(Debug, Clone, Serialize, Deserialize, Default)]
#[serde(rename_all = "camelCase")]
pub struct StealthRollbackSnapshot {
    pub previous_node_id: String,
    pub previous_stealth_mode_enabled: bool,
    pub network_name: Option<String>,
    pub previous_network_policy: Option<StealthPolicy>,
    pub created_at: Option<u64>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct StealthProbeFinding {
    pub id: String,
    pub label: String,
    pub status: String,
    pub summary: String,
    pub detail: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct StealthPreviewChange {
    pub scope: String,
    pub field: String,
    pub from: String,
    pub to: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct StealthStrategy {
    pub id: String,
    pub tier: String,
    pub rank: u8,
    pub title: String,
    pub summary: String,
    pub reason: String,
    pub tradeoff: String,
    pub readiness: String,
    pub action_label: String,
    pub target_node_id: String,
    pub target_node_name: String,
    pub target_protocol: String,
    pub enable_stealth_mode: bool,
    pub preview_changes: Vec<StealthPreviewChange>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct CensorshipReport {
    pub node_id: String,
    pub node_name: String,
    pub network_name: String,
    pub assessed_at: Option<u64>,
    pub status: String,
    pub confidence: u8,
    pub summary: String,
    pub findings: Vec<StealthProbeFinding>,
    pub recommended_strategy_id: Option<String>,
    pub strategies: Vec<StealthStrategy>,
    pub auto_pilot: Option<StealthAutoPilotState>,
    pub network_memory: Option<StealthNetworkMemory>,
    pub network_policy: Option<StealthPolicy>,
    pub rollback_available: bool,
}

#[derive(Debug, Clone, Serialize, Deserialize, Default)]
#[serde(rename_all = "camelCase")]
pub struct StealthAutoPilotState {
    pub mode: String,
    pub action: String,
    pub trusted_pattern: bool,
    pub strategy_id: Option<String>,
    pub strategy_title: Option<String>,
    pub target_node_id: Option<String>,
    pub target_node_name: Option<String>,
    pub message: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct StealthActionResult {
    pub strategy_id: String,
    pub target_node_id: String,
    pub message: String,
    pub rollback_available: bool,
    pub health: Option<StealthHealthAssessment>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct StealthHealthProbe {
    pub id: String,
    pub label: String,
    pub status: String,
    pub summary: String,
    pub detail: String,
    pub first_byte_latency_ms: Option<i32>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct StealthHealthAssessment {
    pub checked_at: Option<u64>,
    pub status: String,
    pub summary: String,
    pub success_count: u32,
    pub sample_count: u32,
    pub median_first_byte_latency_ms: Option<i32>,
    pub probes: Vec<StealthHealthProbe>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct StealthCompareProbe {
    pub id: String,
    pub label: String,
    pub category: String,
    pub status: String,
    pub summary: String,
    pub detail: String,
    pub first_byte_latency_ms: Option<i32>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct StealthStrategyComparison {
    pub strategy: StealthStrategy,
    pub latency_ms: Option<i32>,
    pub dns_success_count: u32,
    pub dns_sample_count: u32,
    pub handshake_success_count: u32,
    pub handshake_sample_count: u32,
    pub stability: String,
    pub summary: String,
    pub probes: Vec<StealthCompareProbe>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct StealthCompareReport {
    pub node_id: String,
    pub node_name: String,
    pub assessed_at: Option<u64>,
    pub restored_connection: bool,
    pub restore_message: Option<String>,
    pub entries: Vec<StealthStrategyComparison>,
}

#[derive(Debug, Clone)]
struct HttpsProbeOutcome {
    healthy: bool,
    likely_sni_interference: bool,
    likely_certificate_interception: bool,
    summary: String,
    detail: String,
}

pub fn current_timestamp_ms() -> Option<u64> {
    SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .ok()
        .and_then(|duration| u64::try_from(duration.as_millis()).ok())
}

fn median_i32(values: &[i32]) -> Option<i32> {
    if values.is_empty() {
        return None;
    }

    let mut sorted = values.to_vec();
    sorted.sort_unstable();
    let middle = sorted.len() / 2;

    if sorted.len() % 2 == 1 {
        sorted.get(middle).copied()
    } else {
        let left = i64::from(*sorted.get(middle.saturating_sub(1))?);
        let right = i64::from(*sorted.get(middle)?);
        i32::try_from((left + right) / 2).ok()
    }
}

pub fn health_snapshot_from_assessment(
    assessment: &StealthHealthAssessment,
) -> StealthHealthSnapshot {
    StealthHealthSnapshot {
        checked_at: assessment.checked_at,
        status: Some(assessment.status.clone()),
        summary: Some(assessment.summary.clone()),
        success_count: Some(assessment.success_count),
        sample_count: Some(assessment.sample_count),
        median_first_byte_latency_ms: assessment.median_first_byte_latency_ms,
    }
}

fn failed_finding(id: &str, label: &str, summary: &str, detail: &str) -> StealthProbeFinding {
    StealthProbeFinding {
        id: id.to_string(),
        label: label.to_string(),
        status: "fail".to_string(),
        summary: summary.to_string(),
        detail: detail.to_string(),
    }
}

fn node_supports_camouflage(node: &ProxyNode) -> bool {
    node.protocol == "vless" || node.tls.as_deref() == Some("reality")
}

fn node_latency_bonus(node: &ProxyNode) -> i32 {
    match node.ping {
        Some(ping) if ping > 0 => 900 - i32::try_from(ping.min(900)).unwrap_or(900),
        _ => 0,
    }
}

fn node_affinity_bonus(candidate: &ProxyNode, selected: &ProxyNode) -> i32 {
    let mut score = 0;

    if candidate.group_id == selected.group_id && candidate.group_id.is_some() {
        score += 120;
    }
    if candidate.subscription_id == selected.subscription_id && candidate.subscription_id.is_some()
    {
        score += 80;
    }
    if candidate.protocol == selected.protocol {
        score += 25;
    }
    if candidate.port == selected.port {
        score += 15;
    }

    score
}

fn balanced_score(candidate: &ProxyNode, selected: &ProxyNode) -> i32 {
    if !node_supports_camouflage(candidate) {
        return i32::MIN / 4;
    }

    let mut score = node_affinity_bonus(candidate, selected) + node_latency_bonus(candidate);
    if candidate.id == selected.id {
        score += 280;
    }
    if candidate.port == 443 {
        score += 40;
    }
    if candidate.tls.as_deref() == Some("reality") {
        score += 50;
    }
    score
}

fn resistant_score(candidate: &ProxyNode, selected: &ProxyNode) -> i32 {
    if !node_supports_camouflage(candidate) {
        return i32::MIN / 4;
    }

    let mut score = node_affinity_bonus(candidate, selected) + (node_latency_bonus(candidate) / 2);
    if candidate.id == selected.id {
        score += 120;
    }
    if candidate.tls.as_deref() == Some("reality") {
        score += 260;
    } else if candidate.protocol == "vless" {
        score += 120;
    }
    if candidate.port == 443 {
        score += 80;
    }
    if candidate.tls_fragment == Some(true) || candidate.tls_record_fragment == Some(true) {
        score += 20;
    }
    score
}

fn maximum_score(candidate: &ProxyNode, selected: &ProxyNode) -> i32 {
    if !node_supports_camouflage(candidate) {
        return i32::MIN / 4;
    }

    let mut score =
        node_affinity_bonus(candidate, selected) / 2 + (node_latency_bonus(candidate) / 4);
    if candidate.tls.as_deref() == Some("reality") {
        score += 420;
    } else if candidate.protocol == "vless" {
        score += 220;
    }
    if candidate.port == 443 {
        score += 120;
    }
    if candidate.fingerprint.is_some() {
        score += 25;
    }
    if candidate.sni.is_some() {
        score += 15;
    }
    score
}

fn best_candidate(profiles: &[ProxyNode], scorer: impl Fn(&ProxyNode) -> i32) -> Option<ProxyNode> {
    profiles
        .iter()
        .cloned()
        .max_by_key(|candidate| scorer(candidate))
}

fn build_strategy_id(tier: &str, target_node_id: &str, enable_stealth_mode: bool) -> String {
    let posture = if enable_stealth_mode {
        "camouflage"
    } else {
        "standard"
    };
    format!("{tier}:{target_node_id}:{posture}")
}

pub fn parse_strategy_id(strategy_id: &str) -> Option<(String, String, bool)> {
    let mut parts = strategy_id.splitn(3, ':');
    let tier = parts.next()?.to_string();
    let target_node_id = parts.next()?.to_string();
    let posture = parts.next()?;
    let enable_stealth_mode = match posture {
        "camouflage" => true,
        "standard" => false,
        _ => return None,
    };

    Some((tier, target_node_id, enable_stealth_mode))
}

pub fn normalize_auto_pilot_mode(mode: &str) -> &'static str {
    match mode.trim() {
        "ask-before-apply" => "ask-before-apply",
        "auto-apply-trusted" => "auto-apply-trusted",
        "auto-apply-with-rollback" => "auto-apply-with-rollback",
        _ => "recommend-only",
    }
}

fn is_actionable_status(status: &str) -> bool {
    matches!(status, "degraded" | "filtered" | "intercepted")
}

fn resolve_strategy<'a>(
    report: &'a CensorshipReport,
    strategy_id: Option<&str>,
) -> Option<&'a StealthStrategy> {
    let strategy_id = strategy_id?;
    report
        .strategies
        .iter()
        .find(|strategy| strategy.id == strategy_id)
}

fn resolve_policy_strategy<'a>(
    report: &'a CensorshipReport,
    network_policy: &StealthPolicy,
) -> Option<&'a StealthStrategy> {
    resolve_strategy(report, network_policy.strategy_id.as_deref()).or_else(|| {
        report.strategies.iter().find(|strategy| {
            network_policy.target_node_id.as_deref() == Some(strategy.target_node_id.as_str())
                && network_policy.enable_stealth_mode == Some(strategy.enable_stealth_mode)
        })
    })
}

fn is_trusted_pattern(
    network_policy: &StealthPolicy,
    network_memory: Option<&StealthNetworkMemory>,
) -> bool {
    let Some(strategy_id) = network_policy.strategy_id.as_deref() else {
        return false;
    };

    let Some(memory) = network_memory else {
        return false;
    };

    memory.last_known_good_strategy_id.as_deref() == Some(strategy_id)
        || memory.last_applied_recommendation_id.as_deref() == Some(strategy_id)
}

fn policy_matches_live_connection(
    current_node_id: Option<&str>,
    current_stealth_mode_enabled: bool,
    network_policy: &StealthPolicy,
) -> bool {
    network_policy.target_node_id.as_deref() == current_node_id
        && network_policy.enable_stealth_mode == Some(current_stealth_mode_enabled)
}

fn auto_pilot_state(
    mode: &str,
    action: &str,
    trusted_pattern: bool,
    strategy: Option<&StealthStrategy>,
    message: Option<String>,
) -> StealthAutoPilotState {
    StealthAutoPilotState {
        mode: normalize_auto_pilot_mode(mode).to_string(),
        action: action.to_string(),
        trusted_pattern,
        strategy_id: strategy.map(|value| value.id.clone()),
        strategy_title: strategy.map(|value| value.title.clone()),
        target_node_id: strategy.map(|value| value.target_node_id.clone()),
        target_node_name: strategy.map(|value| value.target_node_name.clone()),
        message,
    }
}

pub fn evaluate_auto_pilot(
    mode: &str,
    report: &CensorshipReport,
    network_policy: Option<&StealthPolicy>,
    network_memory: Option<&StealthNetworkMemory>,
    current_node_id: Option<&str>,
    current_stealth_mode_enabled: bool,
) -> StealthAutoPilotState {
    let mode = normalize_auto_pilot_mode(mode);
    let recommended_strategy = resolve_strategy(report, report.recommended_strategy_id.as_deref())
        .or_else(|| {
            report
                .strategies
                .iter()
                .find(|strategy| strategy.readiness == "ready")
        });

    if !is_actionable_status(&report.status) {
        return auto_pilot_state(mode, "idle", false, recommended_strategy, None);
    }

    let Some(network_policy) = network_policy else {
        return auto_pilot_state(mode, "recommend", false, recommended_strategy, None);
    };

    let trusted_pattern = is_trusted_pattern(network_policy, network_memory);
    let policy_strategy = resolve_policy_strategy(report, network_policy)
        .filter(|strategy| strategy.readiness == "ready");

    if policy_matches_live_connection(
        current_node_id,
        current_stealth_mode_enabled,
        network_policy,
    ) {
        return auto_pilot_state(mode, "idle", trusted_pattern, policy_strategy, None);
    }

    match mode {
        "recommend-only" => auto_pilot_state(
            mode,
            "recommend",
            trusted_pattern,
            recommended_strategy,
            None,
        ),
        "ask-before-apply" => {
            if let Some(strategy) = policy_strategy {
                auto_pilot_state(mode, "confirm", trusted_pattern, Some(strategy), None)
            } else {
                auto_pilot_state(
                    mode,
                    "recommend",
                    trusted_pattern,
                    recommended_strategy,
                    None,
                )
            }
        }
        "auto-apply-trusted" | "auto-apply-with-rollback" => {
            if trusted_pattern {
                if let Some(strategy) = policy_strategy {
                    auto_pilot_state(mode, "auto-apply", true, Some(strategy), None)
                } else {
                    auto_pilot_state(mode, "recommend", true, recommended_strategy, None)
                }
            } else if let Some(strategy) = policy_strategy {
                auto_pilot_state(mode, "confirm", false, Some(strategy), None)
            } else {
                auto_pilot_state(mode, "recommend", false, recommended_strategy, None)
            }
        }
        _ => auto_pilot_state(
            "recommend-only",
            "recommend",
            trusted_pattern,
            recommended_strategy,
            None,
        ),
    }
}

fn build_preview_changes(
    current_node: &ProxyNode,
    target_node: &ProxyNode,
    current_stealth_mode_enabled: bool,
    target_stealth_mode_enabled: bool,
) -> Vec<StealthPreviewChange> {
    let mut changes = Vec::new();

    if current_node.id != target_node.id {
        changes.push(StealthPreviewChange {
            scope: "connection".to_string(),
            field: "Target node".to_string(),
            from: format!("{} · {}", current_node.name, current_node.server),
            to: format!("{} · {}", target_node.name, target_node.server),
        });
        changes.push(StealthPreviewChange {
            scope: "connection".to_string(),
            field: "Protocol".to_string(),
            from: current_node.protocol.to_uppercase(),
            to: target_node.protocol.to_uppercase(),
        });
    }

    if current_stealth_mode_enabled != target_stealth_mode_enabled {
        changes.push(StealthPreviewChange {
            scope: "transport".to_string(),
            field: "Stealth posture".to_string(),
            from: if current_stealth_mode_enabled {
                "Camouflage enabled".to_string()
            } else {
                "Standard transport".to_string()
            },
            to: if target_stealth_mode_enabled {
                "Camouflage enabled".to_string()
            } else {
                "Standard transport".to_string()
            },
        });
    }

    if target_stealth_mode_enabled
        && node_supports_camouflage(target_node)
        && (!current_stealth_mode_enabled || current_node.id != target_node.id)
    {
        changes.push(StealthPreviewChange {
            scope: "transport".to_string(),
            field: "Overlay".to_string(),
            from: if current_stealth_mode_enabled {
                "Current camouflage route".to_string()
            } else {
                "No camouflage overlay".to_string()
            },
            to: "XHTTP camouflage with adaptive padding and multiplex shaping".to_string(),
        });
    }

    changes
}

fn build_strategy(
    tier: &str,
    current_node: &ProxyNode,
    target_node: &ProxyNode,
    current_stealth_mode_enabled: bool,
    target_stealth_mode_enabled: bool,
    title: impl Into<String>,
    summary: impl Into<String>,
    reason: impl Into<String>,
    tradeoff: impl Into<String>,
) -> StealthStrategy {
    let preview_changes = build_preview_changes(
        current_node,
        target_node,
        current_stealth_mode_enabled,
        target_stealth_mode_enabled,
    );
    let readiness = if preview_changes.is_empty() {
        "noop"
    } else {
        "ready"
    };
    let action_label = match readiness {
        "ready" => "Apply strategy",
        _ => "Already matched",
    };

    StealthStrategy {
        id: build_strategy_id(tier, &target_node.id, target_stealth_mode_enabled),
        tier: tier.to_string(),
        rank: 0,
        title: title.into(),
        summary: summary.into(),
        reason: reason.into(),
        tradeoff: tradeoff.into(),
        readiness: readiness.to_string(),
        action_label: action_label.to_string(),
        target_node_id: target_node.id.clone(),
        target_node_name: target_node.name.clone(),
        target_protocol: target_node.protocol.clone(),
        enable_stealth_mode: target_stealth_mode_enabled,
        preview_changes,
    }
}

fn build_manual_strategy(
    tier: &str,
    current_node: &ProxyNode,
    current_stealth_mode_enabled: bool,
    title: impl Into<String>,
    summary: impl Into<String>,
    reason: impl Into<String>,
    tradeoff: impl Into<String>,
    action_label: impl Into<String>,
) -> StealthStrategy {
    StealthStrategy {
        id: build_strategy_id(tier, &current_node.id, current_stealth_mode_enabled),
        tier: tier.to_string(),
        rank: 0,
        title: title.into(),
        summary: summary.into(),
        reason: reason.into(),
        tradeoff: tradeoff.into(),
        readiness: "manual".to_string(),
        action_label: action_label.into(),
        target_node_id: current_node.id.clone(),
        target_node_name: current_node.name.clone(),
        target_protocol: current_node.protocol.clone(),
        enable_stealth_mode: current_stealth_mode_enabled,
        preview_changes: Vec::new(),
    }
}

fn build_fast_strategy(
    selected_node: &ProxyNode,
    current_stealth_mode_enabled: bool,
) -> StealthStrategy {
    build_strategy(
        "fast",
        selected_node,
        selected_node,
        current_stealth_mode_enabled,
        false,
        "Fast",
        format!(
            "Stay on '{}' with the standard transport path and the lowest possible overhead.",
            selected_node.name
        ),
        "Keeps the currently selected node and removes extra camouflage layers whenever they are active.",
        "Best throughput and lowest overhead, but also the weakest posture if the network is filtering aggressively.",
    )
}

fn build_balanced_strategy(
    selected_node: &ProxyNode,
    profiles: &[ProxyNode],
    current_stealth_mode_enabled: bool,
) -> StealthStrategy {
    if node_supports_camouflage(selected_node) {
        return build_strategy(
            "balanced",
            selected_node,
            selected_node,
            current_stealth_mode_enabled,
            true,
            "Balanced",
            format!(
                "Keep '{}' and add the built-in camouflage overlay for a moderate resistance bump.",
                selected_node.name
            ),
            "Prefers the selected node when it already supports the built-in camouflage path.",
            "Moderate overhead and usually the safest first step before switching to a different node.",
        );
    }

    if let Some(candidate) =
        best_candidate(profiles, |profile| balanced_score(profile, selected_node))
    {
        if node_supports_camouflage(&candidate) {
            return build_strategy(
                "balanced",
                selected_node,
                &candidate,
                current_stealth_mode_enabled,
                true,
                "Balanced",
                format!(
                    "Switch to '{}' and reconnect with camouflage enabled.",
                    candidate.name
                ),
                "Chooses the closest compatible sibling node by affinity and latency before escalating harder.",
                "Moderate overhead with a likely node switch if the current one cannot use camouflage.",
            );
        }
    }

    build_manual_strategy(
        "balanced",
        selected_node,
        current_stealth_mode_enabled,
        "Balanced",
        "No camouflage-capable node is available for an automatic balanced fallback.",
        "The current catalog does not expose a safe, automatically applicable balanced option.",
        "Requires a compatible VLESS or REALITY-capable node before the client can apply camouflage.",
        "Pick a compatible node",
    )
}

fn build_resistant_strategy(
    selected_node: &ProxyNode,
    profiles: &[ProxyNode],
    current_stealth_mode_enabled: bool,
) -> StealthStrategy {
    if let Some(candidate) =
        best_candidate(profiles, |profile| resistant_score(profile, selected_node))
    {
        if node_supports_camouflage(&candidate) {
            return build_strategy(
                "resistant",
                selected_node,
                &candidate,
                current_stealth_mode_enabled,
                true,
                "Resistant",
                format!(
                    "Bias toward '{}' for a stronger anti-filtering posture.",
                    candidate.name
                ),
                "Leans toward REALITY-capable or otherwise stronger camouflage-ready nodes, still preferring nearby affinity when possible.",
                "More resilient than Balanced, but usually slower and more likely to move you away from the selected route.",
            );
        }
    }

    build_manual_strategy(
        "resistant",
        selected_node,
        current_stealth_mode_enabled,
        "Resistant",
        "No stronger camouflage-capable fallback is available automatically for this catalog.",
        "The current profile set does not expose a stronger stealth-capable node than the one already selected.",
        "Requires a compatible REALITY or VLESS node to provide a meaningfully more resistant path.",
        "Review nodes manually",
    )
}

fn build_maximum_strategy(
    selected_node: &ProxyNode,
    profiles: &[ProxyNode],
    current_stealth_mode_enabled: bool,
) -> StealthStrategy {
    if let Some(candidate) =
        best_candidate(profiles, |profile| maximum_score(profile, selected_node))
    {
        if node_supports_camouflage(&candidate) {
            return build_strategy(
                "maximum",
                selected_node,
                &candidate,
                current_stealth_mode_enabled,
                true,
                "Maximum Evasion",
                format!(
                    "Use '{}' as the strongest available automatic camouflage route.",
                    candidate.name
                ),
                "Optimizes for the strongest available camouflage-capable node, regardless of how far it drifts from the originally selected route.",
                "Highest evasion bias in the current catalog and the biggest chance of a latency or geography tradeoff.",
            );
        }
    }

    build_manual_strategy(
        "maximum",
        selected_node,
        current_stealth_mode_enabled,
        "Maximum Evasion",
        "The catalog does not currently contain a stronger automatic maximum-evasion route.",
        "No compatible node scored high enough to produce a distinct maximum strategy automatically.",
        "Needs a stronger REALITY or compatible VLESS route in the catalog before maximum mode can be applied.",
        "Review nodes manually",
    )
}

fn build_last_known_good_strategy(
    selected_node: &ProxyNode,
    profiles: &[ProxyNode],
    network_memory: Option<&StealthNetworkMemory>,
    current_stealth_mode_enabled: bool,
) -> Option<StealthStrategy> {
    let memory = network_memory?;
    let target_node_id = memory.last_known_good_node_id.as_ref()?;
    let target_node = profiles
        .iter()
        .find(|profile| &profile.id == target_node_id)?;
    let target_stealth_mode_enabled = memory.last_known_good_stealth_mode_enabled.unwrap_or(true);
    let title = memory
        .last_known_good_strategy_title
        .clone()
        .unwrap_or_else(|| "Last known good".to_string());

    Some(build_strategy(
        "last-known-good",
        selected_node,
        target_node,
        current_stealth_mode_enabled,
        target_stealth_mode_enabled,
        title,
        format!(
            "Reuse '{}' because it was the last remembered working stealth route on this network.",
            target_node.name
        ),
        "This network already has a memorized route that the client previously applied successfully.",
        "Usually the fastest recovery option on a familiar network, but it may be stale if the network changed since the last successful run.",
    ))
}

fn recommended_order(status: &str, has_last_known_good: bool) -> Vec<&'static str> {
    match status {
        "clear" => {
            if has_last_known_good {
                vec![
                    "fast",
                    "balanced",
                    "last-known-good",
                    "resistant",
                    "maximum",
                ]
            } else {
                vec!["fast", "balanced", "resistant", "maximum"]
            }
        }
        "degraded" => {
            if has_last_known_good {
                vec![
                    "balanced",
                    "last-known-good",
                    "fast",
                    "resistant",
                    "maximum",
                ]
            } else {
                vec!["balanced", "fast", "resistant", "maximum"]
            }
        }
        "filtered" => {
            if has_last_known_good {
                vec![
                    "last-known-good",
                    "resistant",
                    "maximum",
                    "balanced",
                    "fast",
                ]
            } else {
                vec!["resistant", "maximum", "balanced", "fast"]
            }
        }
        "intercepted" => {
            if has_last_known_good {
                vec![
                    "last-known-good",
                    "maximum",
                    "resistant",
                    "balanced",
                    "fast",
                ]
            } else {
                vec!["maximum", "resistant", "balanced", "fast"]
            }
        }
        _ => vec!["balanced", "fast", "resistant", "maximum"],
    }
}

fn build_strategy_ladder(
    selected_node: &ProxyNode,
    profiles: &[ProxyNode],
    status: &str,
    current_stealth_mode_enabled: bool,
    network_memory: Option<&StealthNetworkMemory>,
) -> (Vec<StealthStrategy>, Option<String>) {
    let mut pool = vec![
        build_fast_strategy(selected_node, current_stealth_mode_enabled),
        build_balanced_strategy(selected_node, profiles, current_stealth_mode_enabled),
        build_resistant_strategy(selected_node, profiles, current_stealth_mode_enabled),
        build_maximum_strategy(selected_node, profiles, current_stealth_mode_enabled),
    ];

    if let Some(strategy) = build_last_known_good_strategy(
        selected_node,
        profiles,
        network_memory,
        current_stealth_mode_enabled,
    ) {
        pool.push(strategy);
    }

    let order = recommended_order(
        status,
        pool.iter()
            .any(|strategy| strategy.tier == "last-known-good"),
    );
    let mut ranked = Vec::new();
    let mut seen_actions = HashSet::new();

    for tier in order {
        for strategy in pool.iter().filter(|strategy| strategy.tier == tier) {
            let action_key = format!(
                "{}:{}",
                strategy.target_node_id, strategy.enable_stealth_mode
            );

            if seen_actions.insert(action_key) {
                let mut ranked_strategy = strategy.clone();
                ranked_strategy.rank = u8::try_from(ranked.len() + 1).unwrap_or(u8::MAX);
                ranked.push(ranked_strategy);
                break;
            }
        }
    }

    let recommended_strategy_id = ranked.first().map(|strategy| strategy.id.clone());
    (ranked, recommended_strategy_id)
}

async fn tcp_reachability_probe(
    server: String,
    port: u16,
    app_handle: AppHandle,
) -> StealthProbeFinding {
    let _ = app_handle.emit(
        "stealth-probe-log",
        format!("Probing node TCP reachability for {server}:{port}... [START]"),
    );

    match timeout(
        Duration::from_secs(5),
        TcpStream::connect((server.as_str(), port)),
    )
    .await
    {
        Ok(Ok(_)) => {
            let _ = app_handle.emit(
                "stealth-probe-log",
                "Probing node TCP reachability... [OK]".to_string(),
            );
            StealthProbeFinding {
                id: "node-tcp".to_string(),
                label: "Node reachability".to_string(),
                status: "pass".to_string(),
                summary: "The selected node accepted a direct TCP connection.".to_string(),
                detail: format!("A TCP handshake to {server}:{port} completed within 5 seconds."),
            }
        }
        Ok(Err(error)) => {
            let _ = app_handle.emit(
                "stealth-probe-log",
                format!("Probing node TCP reachability... [FAIL: {error}]"),
            );
            failed_finding(
                "node-tcp",
                "Node reachability",
                "The selected node was not reachable over direct TCP.",
                &format!("TCP connect to {server}:{port} failed: {error}"),
            )
        }
        Err(_) => {
            let _ = app_handle.emit(
                "stealth-probe-log",
                "Probing node TCP reachability... [TIMEOUT]".to_string(),
            );
            failed_finding(
                "node-tcp",
                "Node reachability",
                "The selected node did not respond to TCP reachability checks.",
                &format!("TCP connect to {server}:{port} exceeded the 5 second timeout."),
            )
        }
    }
}

async fn https_probe(app_handle: AppHandle) -> HttpsProbeOutcome {
    let _ = app_handle.emit(
        "stealth-probe-log",
        "Running HTTPS/SNI baseline probe against https://www.google.com/generate_204... [START]",
    );

    let client = match reqwest::Client::builder()
        .timeout(Duration::from_secs(5))
        .redirect(reqwest::redirect::Policy::none())
        .build()
    {
        Ok(client) => client,
        Err(error) => {
            let detail = format!("HTTP client init failed: {error}");
            let _ = app_handle.emit(
                "stealth-probe-log",
                format!("Running HTTPS/SNI baseline probe... [CLIENT INIT FAILED: {error}]"),
            );
            return HttpsProbeOutcome {
                healthy: false,
                likely_sni_interference: false,
                likely_certificate_interception: false,
                summary: "HTTPS baseline probe could not be initialized.".to_string(),
                detail,
            };
        }
    };

    match client
        .get("https://www.google.com/generate_204")
        .send()
        .await
    {
        Ok(response) => {
            let _ = app_handle.emit(
                "stealth-probe-log",
                format!(
                    "Running HTTPS/SNI baseline probe... [OK: {}]",
                    response.status()
                ),
            );
            HttpsProbeOutcome {
                healthy: true,
                likely_sni_interference: false,
                likely_certificate_interception: false,
                summary: "HTTPS baseline traffic completed successfully.".to_string(),
                detail: format!(
                    "Received status {} from the HTTPS baseline probe without transport errors.",
                    response.status()
                ),
            }
        }
        Err(error) => {
            let message = error.to_string();
            let lowered = message.to_lowercase();
            let likely_certificate_interception = lowered.contains("certificate")
                || lowered.contains("cert")
                || lowered.contains("issuer");
            let likely_sni_interference = lowered.contains("reset")
                || lowered.contains("timeout")
                || lowered.contains("closed")
                || lowered.contains("handshake");
            let _ = app_handle.emit(
                "stealth-probe-log",
                format!("Running HTTPS/SNI baseline probe... [FAIL: {message}]"),
            );
            HttpsProbeOutcome {
                healthy: false,
                likely_sni_interference,
                likely_certificate_interception,
                summary: if likely_certificate_interception {
                    "HTTPS baseline failed with a certificate anomaly.".to_string()
                } else if likely_sni_interference {
                    "HTTPS baseline failed with a reset, timeout, or handshake interruption."
                        .to_string()
                } else {
                    "HTTPS baseline failed for an inconclusive reason.".to_string()
                },
                detail: message,
            }
        }
    }
}

fn build_dns_query(host: &str, query_id: u16) -> Vec<u8> {
    let mut query = Vec::with_capacity(64);
    query.extend_from_slice(&query_id.to_be_bytes());
    query.extend_from_slice(&0x0100u16.to_be_bytes());
    query.extend_from_slice(&1u16.to_be_bytes());
    query.extend_from_slice(&0u16.to_be_bytes());
    query.extend_from_slice(&0u16.to_be_bytes());
    query.extend_from_slice(&0u16.to_be_bytes());

    for label in host.split('.') {
        query.push(label.len() as u8);
        query.extend_from_slice(label.as_bytes());
    }
    query.push(0);
    query.extend_from_slice(&1u16.to_be_bytes());
    query.extend_from_slice(&1u16.to_be_bytes());
    query
}

async fn udp_dns_probe(app_handle: AppHandle) -> StealthProbeFinding {
    let _ = app_handle.emit(
        "stealth-probe-log",
        "Running UDP DNS probe against 1.1.1.1:53... [START]",
    );

    let socket = match UdpSocket::bind("0.0.0.0:0").await {
        Ok(socket) => socket,
        Err(error) => {
            let _ = app_handle.emit(
                "stealth-probe-log",
                format!("Running UDP DNS probe... [BIND FAILED: {error}]"),
            );
            return StealthProbeFinding {
                id: "udp-dns".to_string(),
                label: "UDP / DNS viability".to_string(),
                status: "inconclusive".to_string(),
                summary: "The local system could not open a UDP socket for diagnostics."
                    .to_string(),
                detail: error.to_string(),
            };
        }
    };

    if let Err(error) = socket.connect("1.1.1.1:53").await {
        let _ = app_handle.emit(
            "stealth-probe-log",
            format!("Running UDP DNS probe... [CONNECT FAILED: {error}]"),
        );
        return failed_finding(
            "udp-dns",
            "UDP / DNS viability",
            "The network did not allow a baseline UDP DNS probe to initialize.",
            &error.to_string(),
        );
    }

    let query_id = 0xCAFEu16;
    let query = build_dns_query("cloudflare.com", query_id);
    if let Err(error) = socket.send(&query).await {
        let _ = app_handle.emit(
            "stealth-probe-log",
            format!("Running UDP DNS probe... [SEND FAILED: {error}]"),
        );
        return failed_finding(
            "udp-dns",
            "UDP / DNS viability",
            "The baseline UDP DNS query could not be sent.",
            &error.to_string(),
        );
    }

    let mut buffer = [0u8; 1024];
    match timeout(Duration::from_secs(4), socket.recv(&mut buffer)).await {
        Ok(Ok(size)) if size >= 12 && buffer[0..2] == query_id.to_be_bytes() => {
            let _ = app_handle.emit(
                "stealth-probe-log",
                "Running UDP DNS probe... [OK]".to_string(),
            );
            StealthProbeFinding {
                id: "udp-dns".to_string(),
                label: "UDP / DNS viability".to_string(),
                status: "pass".to_string(),
                summary: "A baseline UDP DNS query completed successfully.".to_string(),
                detail:
                    "A response arrived from 1.1.1.1:53, which suggests UDP is currently usable."
                        .to_string(),
            }
        }
        Ok(Ok(size)) => {
            let _ = app_handle.emit(
                "stealth-probe-log",
                format!("Running UDP DNS probe... [WARN: {size} bytes]"),
            );
            StealthProbeFinding {
                id: "udp-dns".to_string(),
                label: "UDP / DNS viability".to_string(),
                status: "warn".to_string(),
                summary: "UDP returned data, but the response was not a clean DNS answer."
                    .to_string(),
                detail: format!(
                    "Received {size} bytes, but the payload did not match the diagnostic DNS query ID."
                ),
            }
        }
        Ok(Err(error)) => {
            let _ = app_handle.emit(
                "stealth-probe-log",
                format!("Running UDP DNS probe... [FAIL: {error}]"),
            );
            failed_finding(
                "udp-dns",
                "UDP / DNS viability",
                "UDP baseline traffic failed before a DNS response was received.",
                &error.to_string(),
            )
        }
        Err(_) => {
            let _ = app_handle.emit(
                "stealth-probe-log",
                "Running UDP DNS probe... [TIMEOUT]".to_string(),
            );
            failed_finding(
                "udp-dns",
                "UDP / DNS viability",
                "No UDP DNS response arrived within the diagnostic timeout.",
                "The query to 1.1.1.1:53 timed out after 4 seconds.",
            )
        }
    }
}

fn build_sni_finding(outcome: &HttpsProbeOutcome) -> StealthProbeFinding {
    if outcome.healthy {
        return StealthProbeFinding {
            id: "https-sni".to_string(),
            label: "HTTPS / SNI baseline".to_string(),
            status: "pass".to_string(),
            summary: "HTTPS baseline traffic completed without visible SNI interference."
                .to_string(),
            detail: outcome.detail.clone(),
        };
    }

    if outcome.likely_sni_interference {
        return failed_finding(
            "https-sni",
            "HTTPS / SNI baseline",
            "Baseline HTTPS traffic showed reset, timeout, or handshake interruption patterns.",
            &outcome.detail,
        );
    }

    StealthProbeFinding {
        id: "https-sni".to_string(),
        label: "HTTPS / SNI baseline".to_string(),
        status: "inconclusive".to_string(),
        summary: "HTTPS baseline traffic failed, but the error pattern was inconclusive."
            .to_string(),
        detail: outcome.detail.clone(),
    }
}

fn build_tls_finding(outcome: &HttpsProbeOutcome) -> StealthProbeFinding {
    if outcome.healthy {
        return StealthProbeFinding {
            id: "tls-integrity".to_string(),
            label: "TLS certificate integrity".to_string(),
            status: "pass".to_string(),
            summary: "No certificate anomaly was observed during the HTTPS baseline probe."
                .to_string(),
            detail: outcome.detail.clone(),
        };
    }

    if outcome.likely_certificate_interception {
        return failed_finding(
            "tls-integrity",
            "TLS certificate integrity",
            "The HTTPS baseline probe failed with a certificate anomaly.",
            &outcome.detail,
        );
    }

    StealthProbeFinding {
        id: "tls-integrity".to_string(),
        label: "TLS certificate integrity".to_string(),
        status: "warn".to_string(),
        summary: "TLS baseline failed, but no explicit certificate anomaly was observed."
            .to_string(),
        detail: outcome.detail.clone(),
    }
}

fn health_probe_from_sample(
    id: &str,
    label: &str,
    sample: TransportBenchmarkSample,
) -> StealthHealthProbe {
    StealthHealthProbe {
        id: id.to_string(),
        label: label.to_string(),
        status: if sample.success { "pass" } else { "fail" }.to_string(),
        summary: if sample.success {
            "Traffic crossed the live proxy path successfully.".to_string()
        } else {
            "Traffic did not make it through the live proxy path.".to_string()
        },
        detail: sample.error.unwrap_or_else(|| {
            format!(
                "First byte arrived in {} ms.",
                sample.first_byte_latency_ms.unwrap_or_default()
            )
        }),
        first_byte_latency_ms: sample.first_byte_latency_ms,
    }
}

fn failed_health_probe(id: &str, label: &str, error: &AppError) -> StealthHealthProbe {
    StealthHealthProbe {
        id: id.to_string(),
        label: label.to_string(),
        status: "fail".to_string(),
        summary: "Traffic did not make it through the live proxy path.".to_string(),
        detail: error.to_string(),
        first_byte_latency_ms: None,
    }
}

fn compare_probe_from_sample(
    id: &str,
    label: &str,
    category: &str,
    sample: TransportBenchmarkSample,
) -> StealthCompareProbe {
    StealthCompareProbe {
        id: id.to_string(),
        label: label.to_string(),
        category: category.to_string(),
        status: if sample.success { "pass" } else { "fail" }.to_string(),
        summary: if sample.success {
            "Traffic crossed the temporary compare route successfully.".to_string()
        } else {
            "Traffic did not make it through the temporary compare route.".to_string()
        },
        detail: sample.error.unwrap_or_else(|| {
            format!(
                "First byte arrived in {} ms.",
                sample.first_byte_latency_ms.unwrap_or_default()
            )
        }),
        first_byte_latency_ms: sample.first_byte_latency_ms,
    }
}

fn failed_compare_probe(
    id: &str,
    label: &str,
    category: &str,
    error: &AppError,
) -> StealthCompareProbe {
    StealthCompareProbe {
        id: id.to_string(),
        label: label.to_string(),
        category: category.to_string(),
        status: "fail".to_string(),
        summary: "Traffic did not make it through the temporary compare route.".to_string(),
        detail: error.to_string(),
        first_byte_latency_ms: None,
    }
}

fn summarize_strategy_comparison(
    strategy: &StealthStrategy,
    probes: Vec<StealthCompareProbe>,
) -> StealthStrategyComparison {
    let dns_probes = probes
        .iter()
        .filter(|probe| probe.category == "dns")
        .collect::<Vec<_>>();
    let handshake_probes = probes
        .iter()
        .filter(|probe| probe.category == "handshake")
        .collect::<Vec<_>>();
    let dns_success_count = u32::try_from(
        dns_probes
            .iter()
            .filter(|probe| probe.status == "pass")
            .count(),
    )
    .unwrap_or(u32::MAX);
    let dns_sample_count = u32::try_from(dns_probes.len()).unwrap_or(u32::MAX);
    let handshake_success_count = u32::try_from(
        handshake_probes
            .iter()
            .filter(|probe| probe.status == "pass")
            .count(),
    )
    .unwrap_or(u32::MAX);
    let handshake_sample_count = u32::try_from(handshake_probes.len()).unwrap_or(u32::MAX);
    let first_byte_latencies = probes
        .iter()
        .filter_map(|probe| probe.first_byte_latency_ms)
        .collect::<Vec<_>>();
    let latency_ms = median_i32(&first_byte_latencies);
    let total_success_count = dns_success_count + handshake_success_count;
    let total_sample_count = dns_sample_count + handshake_sample_count;

    let (stability, summary) = if total_success_count == 0 {
        (
            "failed".to_string(),
            format!(
                "'{}' did not pass any live compare probes on the current network.",
                strategy.title
            ),
        )
    } else if total_success_count < total_sample_count {
        let stability = if total_success_count >= total_sample_count.saturating_sub(1) {
            "degraded"
        } else {
            "unstable"
        };
        (
            stability.to_string(),
            format!(
                "'{}' passed {} of {} live compare probes. DNS {} / {}, handshake {} / {}.",
                strategy.title,
                total_success_count,
                total_sample_count,
                dns_success_count,
                dns_sample_count,
                handshake_success_count,
                handshake_sample_count
            ),
        )
    } else if latency_ms.is_some_and(|latency| latency > 1500) {
        (
            "degraded".to_string(),
            format!(
                "'{}' passed every probe, but median first-byte latency is heavily degraded.",
                strategy.title
            ),
        )
    } else {
        (
            "working".to_string(),
            format!(
                "'{}' passed DNS and handshake compare probes cleanly on the current network.",
                strategy.title
            ),
        )
    };

    StealthStrategyComparison {
        strategy: strategy.clone(),
        latency_ms,
        dns_success_count,
        dns_sample_count,
        handshake_success_count,
        handshake_sample_count,
        stability,
        summary,
        probes,
    }
}

pub fn failed_strategy_comparison(
    strategy: &StealthStrategy,
    summary: impl Into<String>,
    detail: impl Into<String>,
) -> StealthStrategyComparison {
    let summary = summary.into();
    let detail = detail.into();

    StealthStrategyComparison {
        strategy: strategy.clone(),
        latency_ms: None,
        dns_success_count: 0,
        dns_sample_count: 0,
        handshake_success_count: 0,
        handshake_sample_count: 0,
        stability: "failed".to_string(),
        summary: summary.clone(),
        probes: vec![StealthCompareProbe {
            id: "compare-runner".to_string(),
            label: "Compare runner".to_string(),
            category: "runner".to_string(),
            status: "fail".to_string(),
            summary,
            detail,
            first_byte_latency_ms: None,
        }],
    }
}

fn summarize_health_probes(probes: Vec<StealthHealthProbe>) -> StealthHealthAssessment {
    let success_count = u32::try_from(probes.iter().filter(|probe| probe.status == "pass").count())
        .unwrap_or(u32::MAX);
    let sample_count = u32::try_from(probes.len()).unwrap_or(u32::MAX);
    let first_byte_latencies = probes
        .iter()
        .filter_map(|probe| probe.first_byte_latency_ms)
        .collect::<Vec<_>>();
    let median_first_byte_latency_ms = median_i32(&first_byte_latencies);

    let (status, summary) = if success_count == 0 {
        (
            "failed".to_string(),
            "The live stealth route did not pass any post-apply traffic checks.".to_string(),
        )
    } else if success_count < sample_count {
        (
            "unstable".to_string(),
            "The live stealth route passed only part of the post-apply traffic checks and looks inconsistent.".to_string(),
        )
    } else if median_first_byte_latency_ms.is_some_and(|latency| latency > 1500) {
        (
            "degraded".to_string(),
            "The live stealth route is passing traffic, but first-byte latency is heavily degraded.".to_string(),
        )
    } else {
        (
            "working".to_string(),
            "The live stealth route passed the post-apply traffic checks and looks healthy."
                .to_string(),
        )
    };

    StealthHealthAssessment {
        checked_at: current_timestamp_ms(),
        status,
        summary,
        success_count,
        sample_count,
        median_first_byte_latency_ms,
        probes,
    }
}

pub async fn run_stealth_health_check(
    proxy_url: &str,
    app_handle: AppHandle,
) -> StealthHealthAssessment {
    let targets = [
        ("route-example", "Example", "example.com", 80, "/"),
        ("route-neverssl", "NeverSSL", "neverssl.com", 80, "/"),
        (
            "route-firefox-portal",
            "Firefox Portal",
            "detectportal.firefox.com",
            80,
            "/success.txt",
        ),
    ];
    let mut probes = Vec::new();

    for (id, label, host, port, path) in targets {
        let _ = app_handle.emit(
            "stealth-probe-log",
            format!("Running live health probe for {host}:{port}{path}... [START]"),
        );
        match crate::engine::helix::benchmark::wait_for_proxy_first_byte_ready(
            proxy_url,
            host,
            port,
            path,
            Duration::from_secs(6),
            Duration::from_secs(4),
        )
        .await
        {
            Ok(sample) => {
                let _ = app_handle.emit(
                    "stealth-probe-log",
                    format!(
                        "Running live health probe for {host}:{port}{path}... [OK: {} ms]",
                        sample.first_byte_latency_ms.unwrap_or_default()
                    ),
                );
                probes.push(health_probe_from_sample(id, label, sample));
            }
            Err(error) => {
                let _ = app_handle.emit(
                    "stealth-probe-log",
                    format!("Running live health probe for {host}:{port}{path}... [FAIL: {error}]"),
                );
                probes.push(failed_health_probe(id, label, &error));
            }
        }
    }

    summarize_health_probes(probes)
}

pub async fn run_stealth_strategy_compare(
    proxy_url: &str,
    strategy: &StealthStrategy,
    app_handle: AppHandle,
) -> StealthStrategyComparison {
    let targets = [
        ("dns-example", "Example", "dns", "example.com", 80, "/"),
        ("dns-neverssl", "NeverSSL", "dns", "neverssl.com", 80, "/"),
        (
            "handshake-google",
            "Google Generate 204",
            "handshake",
            "www.google.com",
            443,
            "/generate_204",
        ),
        (
            "handshake-cloudflare",
            "Cloudflare Trace",
            "handshake",
            "cloudflare.com",
            443,
            "/cdn-cgi/trace",
        ),
    ];
    let mut probes = Vec::new();

    for (id, label, category, host, port, path) in targets {
        let _ = app_handle.emit(
            "stealth-probe-log",
            format!(
                "Running compare probe for '{}' via {host}:{port}{path}... [START]",
                strategy.title
            ),
        );
        match crate::engine::helix::benchmark::wait_for_proxy_first_byte_ready(
            proxy_url,
            host,
            port,
            path,
            Duration::from_secs(6),
            Duration::from_secs(4),
        )
        .await
        {
            Ok(sample) => {
                let _ = app_handle.emit(
                    "stealth-probe-log",
                    format!(
                        "Running compare probe for '{}' via {host}:{port}{path}... [OK: {} ms]",
                        strategy.title,
                        sample.first_byte_latency_ms.unwrap_or_default()
                    ),
                );
                probes.push(compare_probe_from_sample(id, label, category, sample));
            }
            Err(error) => {
                let _ = app_handle.emit(
                    "stealth-probe-log",
                    format!(
                        "Running compare probe for '{}' via {host}:{port}{path}... [FAIL: {error}]",
                        strategy.title
                    ),
                );
                probes.push(failed_compare_probe(id, label, category, &error));
            }
        }
    }

    summarize_strategy_comparison(strategy, probes)
}

fn derive_status_summary(findings: &[StealthProbeFinding]) -> (String, u8, String) {
    let tcp_failed = findings
        .iter()
        .find(|finding| finding.id == "node-tcp")
        .is_some_and(|finding| finding.status == "fail");
    let sni_failed = findings
        .iter()
        .find(|finding| finding.id == "https-sni")
        .is_some_and(|finding| finding.status == "fail");
    let udp_failed = findings
        .iter()
        .find(|finding| finding.id == "udp-dns")
        .is_some_and(|finding| finding.status == "fail");
    let tls_failed = findings
        .iter()
        .find(|finding| finding.id == "tls-integrity")
        .is_some_and(|finding| finding.status == "fail");

    if tls_failed {
        return (
            "intercepted".to_string(),
            82,
            "The network shows certificate-level HTTPS anomalies consistent with active interception or aggressive HTTPS tampering."
                .to_string(),
        );
    }

    if tcp_failed && sni_failed {
        return (
            "filtered".to_string(),
            78,
            "The selected node is not reachable over TCP and HTTPS baseline traffic is also being interrupted."
                .to_string(),
        );
    }

    if sni_failed {
        return (
            "filtered".to_string(),
            68,
            "HTTPS baseline traffic shows reset, timeout, or handshake interruption patterns that often align with DPI filtering."
                .to_string(),
        );
    }

    if udp_failed && !tcp_failed {
        return (
            "degraded".to_string(),
            62,
            "TCP reachability looks healthy, but baseline UDP/DNS traffic appears degraded or blocked."
                .to_string(),
        );
    }

    if tcp_failed {
        return (
            "degraded".to_string(),
            60,
            "The selected node is not reachable from the current network, but the wider censorship pattern is not yet strong enough to classify as full filtering."
                .to_string(),
        );
    }

    (
        "clear".to_string(),
        55,
        "No strong censorship indicators were observed for the selected node and the baseline network probes."
            .to_string(),
    )
}

pub async fn run_stealth_diagnostics(
    node: ProxyNode,
    profiles: Vec<ProxyNode>,
    network_name: String,
    current_stealth_mode_enabled: bool,
    network_memory: Option<StealthNetworkMemory>,
    app_handle: AppHandle,
) -> Result<CensorshipReport, AppError> {
    let _ = app_handle.emit(
        "stealth-probe-log",
        format!(
            "Starting honest diagnostics for node '{}' on network '{}'.",
            node.name, network_name
        ),
    );

    let tcp_handle = {
        let app = app_handle.clone();
        let server = node.server.clone();
        let port = node.port;
        tokio::spawn(async move { tcp_reachability_probe(server, port, app).await })
    };

    let https_handle = {
        let app = app_handle.clone();
        tokio::spawn(async move { https_probe(app).await })
    };

    let udp_handle = {
        let app = app_handle.clone();
        tokio::spawn(async move { udp_dns_probe(app).await })
    };

    let tcp_finding = tcp_handle.await.unwrap_or_else(|error| {
        failed_finding(
            "node-tcp",
            "Node reachability",
            "The TCP probe task failed unexpectedly.",
            &error.to_string(),
        )
    });
    let https_outcome = https_handle
        .await
        .unwrap_or_else(|error| HttpsProbeOutcome {
            healthy: false,
            likely_sni_interference: false,
            likely_certificate_interception: false,
            summary: "The HTTPS baseline probe task failed unexpectedly.".to_string(),
            detail: error.to_string(),
        });
    let udp_finding = udp_handle.await.unwrap_or_else(|error| {
        failed_finding(
            "udp-dns",
            "UDP / DNS viability",
            "The UDP DNS probe task failed unexpectedly.",
            &error.to_string(),
        )
    });

    let sni_finding = build_sni_finding(&https_outcome);
    let tls_finding = build_tls_finding(&https_outcome);
    let findings = vec![tcp_finding, sni_finding, udp_finding, tls_finding];
    let (status, confidence, summary) = derive_status_summary(&findings);
    let (strategies, recommended_strategy_id) = build_strategy_ladder(
        &node,
        &profiles,
        status.as_str(),
        current_stealth_mode_enabled,
        network_memory.as_ref(),
    );

    let _ = app_handle.emit(
        "stealth-probe-log",
        format!(
            "Diagnostic complete. Assessment: {status} ({confidence}% confidence). Recommended strategy: {}.",
            recommended_strategy_id.as_deref().unwrap_or("none")
        ),
    );
    let _ = app_handle.emit(
        "stealth-probe-log",
        format!("HTTPS summary: {}", https_outcome.summary),
    );

    Ok(CensorshipReport {
        node_id: node.id,
        node_name: node.name,
        network_name,
        assessed_at: current_timestamp_ms(),
        status,
        confidence,
        summary,
        findings,
        recommended_strategy_id,
        strategies,
        auto_pilot: None,
        network_memory,
        network_policy: None,
        rollback_available: false,
    })
}

#[cfg(test)]
mod tests {
    use super::*;

    fn sample_vless_node() -> ProxyNode {
        ProxyNode {
            id: "node-1".to_string(),
            name: "Frankfurt".to_string(),
            server: "1.1.1.1".to_string(),
            port: 443,
            protocol: "vless".to_string(),
            group_id: Some("group-a".to_string()),
            subscription_id: Some("sub-a".to_string()),
            ping: Some(48),
            ..Default::default()
        }
    }

    fn sample_reality_node() -> ProxyNode {
        ProxyNode {
            id: "node-2".to_string(),
            name: "Amsterdam REALITY".to_string(),
            server: "1.0.0.1".to_string(),
            port: 443,
            protocol: "vless".to_string(),
            tls: Some("reality".to_string()),
            group_id: Some("group-a".to_string()),
            subscription_id: Some("sub-a".to_string()),
            ping: Some(72),
            ..Default::default()
        }
    }

    fn sample_wireguard_node() -> ProxyNode {
        ProxyNode {
            id: "node-3".to_string(),
            name: "WireGuard".to_string(),
            server: "1.1.1.2".to_string(),
            port: 51820,
            protocol: "wireguard".to_string(),
            ping: Some(32),
            ..Default::default()
        }
    }

    fn sample_report(
        status: &str,
        strategies: Vec<StealthStrategy>,
        recommended_strategy_id: Option<String>,
    ) -> CensorshipReport {
        CensorshipReport {
            node_id: "node-3".to_string(),
            node_name: "WireGuard".to_string(),
            network_name: "Cafe Wi-Fi".to_string(),
            assessed_at: Some(123),
            status: status.to_string(),
            confidence: 82,
            summary: "Synthetic report".to_string(),
            findings: Vec::new(),
            recommended_strategy_id,
            strategies,
            auto_pilot: None,
            network_memory: None,
            network_policy: None,
            rollback_available: false,
        }
    }

    #[test]
    fn parse_strategy_id_returns_expected_parts() {
        let parsed = parse_strategy_id("balanced:node-7:camouflage").expect("strategy");
        assert_eq!(parsed.0, "balanced");
        assert_eq!(parsed.1, "node-7");
        assert!(parsed.2);
    }

    #[test]
    fn balanced_strategy_prefers_selected_node_when_it_supports_camouflage() {
        let selected = sample_vless_node();
        let strategy = build_balanced_strategy(&selected, &[selected.clone()], false);
        assert_eq!(strategy.target_node_id, selected.id);
        assert_eq!(strategy.readiness, "ready");
        assert!(strategy.enable_stealth_mode);
    }

    #[test]
    fn maximum_strategy_prefers_reality_candidate() {
        let selected = sample_wireguard_node();
        let candidate = build_maximum_strategy(
            &selected,
            &[selected.clone(), sample_vless_node(), sample_reality_node()],
            false,
        );

        assert_eq!(candidate.target_node_id, "node-2");
        assert_eq!(candidate.tier, "maximum");
        assert!(candidate.enable_stealth_mode);
    }

    #[test]
    fn filtered_network_prefers_last_known_good_first() {
        let selected = sample_wireguard_node();
        let network_memory = StealthNetworkMemory {
            last_known_good_node_id: Some("node-2".to_string()),
            last_known_good_node_name: Some("Amsterdam REALITY".to_string()),
            last_known_good_strategy_id: Some("last-known-good:node-2:camouflage".to_string()),
            last_known_good_strategy_title: Some("Last known good".to_string()),
            last_known_good_stealth_mode_enabled: Some(true),
            ..Default::default()
        };

        let (strategies, recommended) = build_strategy_ladder(
            &selected,
            &[selected.clone(), sample_vless_node(), sample_reality_node()],
            "filtered",
            false,
            Some(&network_memory),
        );

        assert_eq!(
            recommended.as_deref(),
            Some("last-known-good:node-2:camouflage")
        );
        assert_eq!(
            strategies.first().map(|strategy| strategy.tier.as_str()),
            Some("last-known-good")
        );
    }

    #[test]
    fn recommend_only_mode_never_auto_applies() {
        let selected = sample_wireguard_node();
        let (strategies, recommended) = build_strategy_ladder(
            &selected,
            &[selected.clone(), sample_vless_node(), sample_reality_node()],
            "filtered",
            false,
            None,
        );
        let report = sample_report("filtered", strategies, recommended);

        let auto_pilot =
            evaluate_auto_pilot("recommend-only", &report, None, None, Some("node-3"), false);

        assert_eq!(auto_pilot.mode, "recommend-only");
        assert_eq!(auto_pilot.action, "recommend");
    }

    #[test]
    fn ask_before_apply_prefers_saved_policy() {
        let selected = sample_wireguard_node();
        let (strategies, recommended) = build_strategy_ladder(
            &selected,
            &[selected.clone(), sample_vless_node(), sample_reality_node()],
            "filtered",
            false,
            None,
        );
        let report = sample_report("filtered", strategies, recommended);
        let saved_strategy_id = report
            .strategies
            .iter()
            .find(|strategy| strategy.target_node_id == "node-2" && strategy.readiness == "ready")
            .map(|strategy| strategy.id.clone())
            .expect("saved strategy");
        let policy = StealthPolicy {
            strategy_id: Some(saved_strategy_id.clone()),
            target_node_id: Some("node-2".to_string()),
            target_node_name: Some("Amsterdam REALITY".to_string()),
            enable_stealth_mode: Some(true),
            ..Default::default()
        };

        let auto_pilot = evaluate_auto_pilot(
            "ask-before-apply",
            &report,
            Some(&policy),
            None,
            Some("node-3"),
            false,
        );

        assert_eq!(auto_pilot.action, "confirm");
        assert_eq!(
            auto_pilot.strategy_id.as_deref(),
            Some(saved_strategy_id.as_str())
        );
    }

    #[test]
    fn auto_apply_trusted_requires_confirmed_memory() {
        let selected = sample_wireguard_node();
        let (strategies, recommended) = build_strategy_ladder(
            &selected,
            &[selected.clone(), sample_vless_node(), sample_reality_node()],
            "filtered",
            false,
            None,
        );
        let report = sample_report("filtered", strategies, recommended);
        let policy = StealthPolicy {
            strategy_id: Some("maximum:node-2:camouflage".to_string()),
            target_node_id: Some("node-2".to_string()),
            target_node_name: Some("Amsterdam REALITY".to_string()),
            enable_stealth_mode: Some(true),
            ..Default::default()
        };
        let memory = StealthNetworkMemory {
            last_known_good_strategy_id: Some("maximum:node-2:camouflage".to_string()),
            last_applied_recommendation_id: Some("maximum:node-2:camouflage".to_string()),
            ..Default::default()
        };

        let auto_pilot = evaluate_auto_pilot(
            "auto-apply-trusted",
            &report,
            Some(&policy),
            Some(&memory),
            Some("node-3"),
            false,
        );

        assert_eq!(auto_pilot.action, "auto-apply");
        assert!(auto_pilot.trusted_pattern);
    }

    #[test]
    fn auto_apply_trusted_does_not_fire_for_untrusted_policy() {
        let selected = sample_wireguard_node();
        let (strategies, recommended) = build_strategy_ladder(
            &selected,
            &[selected.clone(), sample_vless_node(), sample_reality_node()],
            "filtered",
            false,
            None,
        );
        let report = sample_report("filtered", strategies, recommended);
        let policy = StealthPolicy {
            strategy_id: Some("maximum:node-2:camouflage".to_string()),
            target_node_id: Some("node-2".to_string()),
            target_node_name: Some("Amsterdam REALITY".to_string()),
            enable_stealth_mode: Some(true),
            ..Default::default()
        };

        let auto_pilot = evaluate_auto_pilot(
            "auto-apply-trusted",
            &report,
            Some(&policy),
            None,
            Some("node-3"),
            false,
        );

        assert_eq!(auto_pilot.action, "confirm");
        assert!(!auto_pilot.trusted_pattern);
    }

    #[test]
    fn health_summary_marks_working_when_all_probes_pass() {
        let assessment = summarize_health_probes(vec![
            StealthHealthProbe {
                id: "a".to_string(),
                label: "A".to_string(),
                status: "pass".to_string(),
                summary: "ok".to_string(),
                detail: "ok".to_string(),
                first_byte_latency_ms: Some(220),
            },
            StealthHealthProbe {
                id: "b".to_string(),
                label: "B".to_string(),
                status: "pass".to_string(),
                summary: "ok".to_string(),
                detail: "ok".to_string(),
                first_byte_latency_ms: Some(260),
            },
        ]);

        assert_eq!(assessment.status, "working");
        assert_eq!(assessment.success_count, 2);
    }

    #[test]
    fn health_summary_marks_unstable_when_only_some_probes_pass() {
        let assessment = summarize_health_probes(vec![
            StealthHealthProbe {
                id: "a".to_string(),
                label: "A".to_string(),
                status: "pass".to_string(),
                summary: "ok".to_string(),
                detail: "ok".to_string(),
                first_byte_latency_ms: Some(320),
            },
            StealthHealthProbe {
                id: "b".to_string(),
                label: "B".to_string(),
                status: "fail".to_string(),
                summary: "fail".to_string(),
                detail: "fail".to_string(),
                first_byte_latency_ms: None,
            },
        ]);

        assert_eq!(assessment.status, "unstable");
        assert_eq!(assessment.success_count, 1);
    }

    #[test]
    fn health_summary_marks_failed_when_no_probe_passes() {
        let assessment = summarize_health_probes(vec![StealthHealthProbe {
            id: "a".to_string(),
            label: "A".to_string(),
            status: "fail".to_string(),
            summary: "fail".to_string(),
            detail: "fail".to_string(),
            first_byte_latency_ms: None,
        }]);

        assert_eq!(assessment.status, "failed");
        assert_eq!(assessment.success_count, 0);
    }

    fn sample_compare_strategy() -> StealthStrategy {
        build_strategy(
            "balanced",
            &sample_vless_node(),
            &sample_reality_node(),
            false,
            true,
            "Balanced",
            "Summary",
            "Reason",
            "Tradeoff",
        )
    }

    #[test]
    fn strategy_compare_marks_working_when_dns_and_handshake_pass() {
        let strategy = sample_compare_strategy();
        let assessment = summarize_strategy_comparison(
            &strategy,
            vec![
                StealthCompareProbe {
                    id: "dns-example".to_string(),
                    label: "Example".to_string(),
                    category: "dns".to_string(),
                    status: "pass".to_string(),
                    summary: "ok".to_string(),
                    detail: "ok".to_string(),
                    first_byte_latency_ms: Some(120),
                },
                StealthCompareProbe {
                    id: "dns-neverssl".to_string(),
                    label: "NeverSSL".to_string(),
                    category: "dns".to_string(),
                    status: "pass".to_string(),
                    summary: "ok".to_string(),
                    detail: "ok".to_string(),
                    first_byte_latency_ms: Some(140),
                },
                StealthCompareProbe {
                    id: "handshake-google".to_string(),
                    label: "Google".to_string(),
                    category: "handshake".to_string(),
                    status: "pass".to_string(),
                    summary: "ok".to_string(),
                    detail: "ok".to_string(),
                    first_byte_latency_ms: Some(180),
                },
                StealthCompareProbe {
                    id: "handshake-cloudflare".to_string(),
                    label: "Cloudflare".to_string(),
                    category: "handshake".to_string(),
                    status: "pass".to_string(),
                    summary: "ok".to_string(),
                    detail: "ok".to_string(),
                    first_byte_latency_ms: Some(160),
                },
            ],
        );

        assert_eq!(assessment.stability, "working");
        assert_eq!(assessment.dns_success_count, 2);
        assert_eq!(assessment.handshake_success_count, 2);
        assert_eq!(assessment.latency_ms, Some(150));
    }

    #[test]
    fn strategy_compare_marks_unstable_when_only_half_of_probes_pass() {
        let strategy = sample_compare_strategy();
        let assessment = summarize_strategy_comparison(
            &strategy,
            vec![
                StealthCompareProbe {
                    id: "dns-example".to_string(),
                    label: "Example".to_string(),
                    category: "dns".to_string(),
                    status: "pass".to_string(),
                    summary: "ok".to_string(),
                    detail: "ok".to_string(),
                    first_byte_latency_ms: Some(320),
                },
                StealthCompareProbe {
                    id: "dns-neverssl".to_string(),
                    label: "NeverSSL".to_string(),
                    category: "dns".to_string(),
                    status: "fail".to_string(),
                    summary: "fail".to_string(),
                    detail: "timeout".to_string(),
                    first_byte_latency_ms: None,
                },
                StealthCompareProbe {
                    id: "handshake-google".to_string(),
                    label: "Google".to_string(),
                    category: "handshake".to_string(),
                    status: "pass".to_string(),
                    summary: "ok".to_string(),
                    detail: "ok".to_string(),
                    first_byte_latency_ms: Some(400),
                },
                StealthCompareProbe {
                    id: "handshake-cloudflare".to_string(),
                    label: "Cloudflare".to_string(),
                    category: "handshake".to_string(),
                    status: "fail".to_string(),
                    summary: "fail".to_string(),
                    detail: "reset".to_string(),
                    first_byte_latency_ms: None,
                },
            ],
        );

        assert_eq!(assessment.stability, "unstable");
        assert_eq!(assessment.dns_success_count, 1);
        assert_eq!(assessment.handshake_success_count, 1);
    }
}
