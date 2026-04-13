use chrono::Utc;
use tracing::warn;

use crate::{
    config::AdapterConfig,
    error::AppError,
    node_registry::{
        model::{
            DesktopRuntimeCore, DesktopRuntimeEventAck, DesktopRuntimeEventKind,
            DesktopRuntimeEventRequest, NodeHeartbeatRequest, NodeRegistryRecord, NodeUpsertInput,
            PublishRolloutBatchRequest, RolloutBatchRecord, RolloutCanaryEvidenceResponse,
            RolloutCanarySnapshotSummary, RolloutCanaryThresholdSummary, RolloutDesiredState,
            RolloutStateResponse,
        },
        repository::NodeRegistryRepository,
    },
    remnawave::client::{NodeInventoryItem, RemnawaveClient},
};

#[derive(Debug, Clone)]
pub struct NodeRegistryService {
    repository: NodeRegistryRepository,
    remnawave_client: RemnawaveClient,
}

impl NodeRegistryService {
    pub fn new(repository: NodeRegistryRepository, remnawave_client: RemnawaveClient) -> Self {
        Self {
            repository,
            remnawave_client,
        }
    }

    pub async fn sync_from_remnawave(&self) -> Result<(), AppError> {
        let nodes = self.remnawave_client.list_nodes().await?;
        let upserts = nodes
            .iter()
            .map(Self::inventory_to_upsert)
            .collect::<Vec<_>>();

        self.repository.upsert_nodes(&upserts).await
    }

    pub async fn list_nodes(
        &self,
        sync_from_source: bool,
    ) -> Result<Vec<NodeRegistryRecord>, AppError> {
        if sync_from_source {
            if let Err(error) = self.sync_from_remnawave().await {
                warn!(
                    error = %error,
                    "failed to sync Helix node inventory from Remnawave; returning cached registry view"
                );
            }
        }

        self.repository.list_nodes().await
    }

    pub async fn publish_rollout(
        &self,
        request: PublishRolloutBatchRequest,
    ) -> Result<RolloutBatchRecord, AppError> {
        validate_publish_request(&request)?;
        self.repository.publish_rollout(&request).await
    }

    pub async fn pause_rollout(&self, rollout_id: &str) -> Result<RolloutBatchRecord, AppError> {
        validate_rollout_id(rollout_id)?;
        self.repository
            .set_rollout_state(rollout_id, RolloutDesiredState::Paused)
            .await
    }

    pub async fn rollout_state(&self, rollout_id: &str) -> Result<RolloutStateResponse, AppError> {
        validate_rollout_id(rollout_id)?;
        self.repository.fetch_rollout_state(rollout_id).await
    }

    pub async fn rollout_canary_evidence(
        &self,
        rollout_id: &str,
        config: &AdapterConfig,
    ) -> Result<RolloutCanaryEvidenceResponse, AppError> {
        validate_rollout_id(rollout_id)?;
        let rollout = self.repository.fetch_rollout_state(rollout_id).await?;
        Ok(build_rollout_canary_evidence(&rollout, config))
    }

    pub async fn record_heartbeat(&self, heartbeat: NodeHeartbeatRequest) -> Result<(), AppError> {
        validate_rollout_id(&heartbeat.rollout_id)?;

        if heartbeat.schema_version != "1.0" {
            return Err(AppError::BadRequest(format!(
                "unsupported heartbeat schema_version: {}",
                heartbeat.schema_version
            )));
        }

        if heartbeat.node_id.trim().is_empty() {
            return Err(AppError::BadRequest(
                "heartbeat node_id must not be empty".to_string(),
            ));
        }

        if heartbeat
            .transport_profile
            .transport_profile_id
            .trim()
            .is_empty()
        {
            return Err(AppError::BadRequest(
                "heartbeat transport_profile_id must not be empty".to_string(),
            ));
        }

        if !matches!(
            heartbeat.daemon.status.as_str(),
            "ready" | "degraded" | "rollback" | "starting"
        ) {
            return Err(AppError::BadRequest(format!(
                "unsupported daemon status: {}",
                heartbeat.daemon.status
            )));
        }

        if !matches!(
            heartbeat.health.apply_state.as_str(),
            "idle" | "applying" | "failed" | "rolled-back"
        ) {
            return Err(AppError::BadRequest(format!(
                "unsupported apply_state: {}",
                heartbeat.health.apply_state
            )));
        }

        self.repository.record_heartbeat(&heartbeat).await
    }

    pub async fn record_desktop_runtime_event(
        &self,
        event: DesktopRuntimeEventRequest,
    ) -> Result<DesktopRuntimeEventAck, AppError> {
        validate_rollout_id(&event.rollout_id)?;

        if event.schema_version != "1.0" {
            return Err(AppError::BadRequest(format!(
                "unsupported desktop runtime event schema_version: {}",
                event.schema_version
            )));
        }

        if event.user_id.trim().is_empty() {
            return Err(AppError::BadRequest(
                "desktop runtime event user_id must not be empty".to_string(),
            ));
        }

        if event.desktop_client_id.trim().is_empty() {
            return Err(AppError::BadRequest(
                "desktop runtime event desktop_client_id must not be empty".to_string(),
            ));
        }

        if event.transport_profile_id.trim().is_empty() {
            return Err(AppError::BadRequest(
                "desktop runtime event transport_profile_id must not be empty".to_string(),
            ));
        }

        if matches!(event.event_kind, DesktopRuntimeEventKind::Ready)
            && !matches!(event.active_core, DesktopRuntimeCore::Helix)
        {
            return Err(AppError::BadRequest(
                "desktop ready event must report active_core=helix".to_string(),
            ));
        }

        if matches!(event.event_kind, DesktopRuntimeEventKind::Disconnect)
            && !matches!(event.active_core, DesktopRuntimeCore::Helix)
        {
            return Err(AppError::BadRequest(
                "desktop disconnect event must report active_core=helix".to_string(),
            ));
        }

        if matches!(event.event_kind, DesktopRuntimeEventKind::Benchmark) {
            if !matches!(event.active_core, DesktopRuntimeCore::Helix) {
                return Err(AppError::BadRequest(
                    "desktop benchmark event must report active_core=helix".to_string(),
                ));
            }

            if event.payload.benchmark.is_none() {
                return Err(AppError::BadRequest(
                    "desktop benchmark event must include payload.benchmark".to_string(),
                ));
            }
        }

        if matches!(event.event_kind, DesktopRuntimeEventKind::Fallback) {
            let fallback_core = event.fallback_core.ok_or_else(|| {
                AppError::BadRequest(
                    "desktop fallback event must include fallback_core".to_string(),
                )
            })?;

            if !fallback_core.is_stable() || fallback_core != event.active_core {
                return Err(AppError::BadRequest(
                    "desktop fallback event must report the stable fallback core as active_core"
                        .to_string(),
                ));
            }
        }

        if let Some(latency_ms) = event.latency_ms {
            if latency_ms < 0 {
                return Err(AppError::BadRequest(
                    "desktop runtime event latency_ms must be >= 0".to_string(),
                ));
            }
        }

        if let Some(route_count) = event.route_count {
            if route_count < 0 {
                return Err(AppError::BadRequest(
                    "desktop runtime event route_count must be >= 0".to_string(),
                ));
            }
        }

        self.repository.record_desktop_runtime_event(&event).await?;

        Ok(DesktopRuntimeEventAck {
            status: "accepted",
            rollout_id: event.rollout_id,
            event_kind: event.event_kind.as_str().to_string(),
        })
    }

    pub fn inventory_to_upsert(node: &NodeInventoryItem) -> NodeUpsertInput {
        let base_label = node
            .hostname
            .as_deref()
            .unwrap_or(node.name.as_str())
            .to_ascii_lowercase()
            .replace(|character: char| !character.is_ascii_alphanumeric(), "-");

        let adapter_node_label = base_label
            .trim_matches('-')
            .split('-')
            .filter(|segment| !segment.is_empty())
            .collect::<Vec<_>>()
            .join("-");

        NodeUpsertInput {
            remnawave_node_id: node.id.clone(),
            node_name: node.name.clone(),
            hostname: node.hostname.clone(),
            adapter_node_label: if adapter_node_label.is_empty() {
                format!("node-{}", node.id.to_ascii_lowercase())
            } else {
                adapter_node_label
            },
            last_synced_at: Utc::now(),
        }
    }
}

fn validate_publish_request(request: &PublishRolloutBatchRequest) -> Result<(), AppError> {
    validate_rollout_id(&request.rollout_id)?;

    if request.batch_id.trim().is_empty() {
        return Err(AppError::BadRequest(
            "batch_id must not be empty".to_string(),
        ));
    }

    if request.manifest_version.trim().is_empty() {
        return Err(AppError::BadRequest(
            "manifest_version must not be empty".to_string(),
        ));
    }

    if request.target_node_ids.is_empty() {
        return Err(AppError::BadRequest(
            "target_node_ids must not be empty".to_string(),
        ));
    }

    Ok(())
}

fn validate_rollout_id(rollout_id: &str) -> Result<(), AppError> {
    if rollout_id.starts_with("rollout-") && rollout_id.len() > "rollout-".len() {
        return Ok(());
    }

    Err(AppError::BadRequest(format!(
        "invalid rollout_id: {rollout_id}"
    )))
}

fn build_rollout_canary_evidence(
    rollout: &RolloutStateResponse,
    config: &AdapterConfig,
) -> RolloutCanaryEvidenceResponse {
    let (decision, reasons, evidence_gaps) = evaluate_canary_gate(rollout, config);
    let (follow_up_action, follow_up_severity, follow_up_tasks) =
        derive_canary_follow_up(rollout, decision, &reasons, &evidence_gaps);
    let active_profile_policy = rollout.policy.active_profile_policy.as_ref();

    RolloutCanaryEvidenceResponse {
        schema_version: "1.0",
        rollout_id: rollout.rollout_id.clone(),
        channel: rollout.channel.clone(),
        evaluated_at: Utc::now(),
        decision: decision.to_string(),
        reasons,
        evidence_gaps,
        recommended_follow_up_action: follow_up_action.map(str::to_string),
        recommended_follow_up_severity: follow_up_severity.map(str::to_string),
        recommended_follow_up_tasks: follow_up_tasks,
        thresholds: RolloutCanaryThresholdSummary {
            min_connect_success_rate: config.helix_canary_min_connect_success_rate,
            max_fallback_rate: config.helix_canary_max_fallback_rate,
            min_continuity_observations: config.helix_canary_min_continuity_observations,
            require_throughput_evidence: config.helix_canary_require_throughput_evidence,
            min_relative_throughput_ratio: config.helix_canary_min_relative_throughput_ratio,
            max_relative_open_to_first_byte_gap_ratio: config
                .helix_canary_max_relative_open_to_first_byte_gap_ratio,
            min_continuity_success_rate: config.helix_rollout_min_continuity_success_rate,
            min_cross_route_recovery_rate: config.helix_rollout_min_cross_route_recovery_rate,
        },
        snapshot: RolloutCanarySnapshotSummary {
            desired_state: rollout.desired_state.clone(),
            failed_nodes: rollout.current_batch.failed_nodes,
            rolled_back_nodes: rollout.nodes.rolled_back,
            connect_success_rate: rollout.desktop.connect_success_rate,
            fallback_rate: rollout.desktop.fallback_rate,
            continuity_observed_events: rollout.desktop.continuity_observed_events,
            continuity_success_rate: rollout.desktop.continuity_success_rate,
            cross_route_recovery_rate: rollout.desktop.cross_route_recovery_rate,
            benchmark_observed_events: rollout.desktop.benchmark_observed_events,
            throughput_evidence_observed_events: rollout
                .desktop
                .throughput_evidence_observed_events,
            average_benchmark_throughput_kbps: rollout.desktop.average_benchmark_throughput_kbps,
            average_relative_throughput_ratio: rollout.desktop.average_relative_throughput_ratio,
            average_relative_open_to_first_byte_gap_ratio: rollout
                .desktop
                .average_relative_open_to_first_byte_gap_ratio,
            channel_posture: rollout.policy.channel_posture.clone(),
            active_profile_advisory_state: active_profile_policy
                .map(|policy| policy.advisory_state.clone()),
            active_profile_new_session_posture: active_profile_policy
                .map(|policy| policy.new_session_posture.clone()),
            applied_automatic_reaction: rollout.policy.applied_automatic_reaction.clone(),
            applied_transport_profile_id: rollout.policy.applied_transport_profile_id.clone(),
        },
    }
}

fn evaluate_canary_gate(
    rollout: &RolloutStateResponse,
    config: &AdapterConfig,
) -> (&'static str, Vec<String>, Vec<String>) {
    let mut reasons = Vec::new();
    let mut evidence_gaps = Vec::new();
    let policy = &rollout.policy;
    let desktop = &rollout.desktop;
    let active_profile_policy = policy.active_profile_policy.as_ref();

    if rollout.desired_state != "running" {
        reasons.push(format!("rollout desired state={}", rollout.desired_state));
    }

    if matches!(
        policy.applied_automatic_reaction.as_deref(),
        Some("pause-channel" | "rotate-profile-now")
    ) {
        reasons.push(format!(
            "applied actuation={}",
            policy
                .applied_automatic_reaction
                .as_deref()
                .unwrap_or("none")
        ));
    }

    if rollout.current_batch.failed_nodes > 0 {
        reasons.push(format!(
            "failed nodes={}",
            rollout.current_batch.failed_nodes
        ));
    }

    if rollout.nodes.rolled_back > 0 {
        reasons.push(format!("rolled back nodes={}", rollout.nodes.rolled_back));
    }

    if desktop.connect_success_rate < config.helix_canary_min_connect_success_rate {
        reasons.push(format!(
            "connect success rate={:.2}%",
            desktop.connect_success_rate * 100.0
        ));
    }

    if desktop.fallback_rate > config.helix_canary_max_fallback_rate {
        reasons.push(format!(
            "fallback rate={:.2}%",
            desktop.fallback_rate * 100.0
        ));
    }

    if desktop.continuity_observed_events > 0
        && desktop.continuity_success_rate < config.helix_rollout_min_continuity_success_rate
    {
        reasons.push(format!(
            "continuity success rate={:.2}%",
            desktop.continuity_success_rate * 100.0
        ));
    }

    if desktop.continuity_observed_events > 0
        && desktop.cross_route_recovery_rate < config.helix_rollout_min_cross_route_recovery_rate
    {
        reasons.push(format!(
            "cross-route recovery rate={:.2}%",
            desktop.cross_route_recovery_rate * 100.0
        ));
    }

    if let Some(active_profile_policy) = active_profile_policy {
        if matches!(
            active_profile_policy.new_session_posture.as_str(),
            "guarded" | "blocked"
        ) {
            reasons.push(format!(
                "new-session posture={}",
                active_profile_policy.new_session_posture
            ));
        }
    }

    if let Some(relative_throughput_ratio) = desktop.average_relative_throughput_ratio {
        if relative_throughput_ratio < config.helix_canary_min_relative_throughput_ratio {
            reasons.push(format!(
                "relative throughput ratio={relative_throughput_ratio:.2}"
            ));
        }
    }

    if let Some(relative_gap_ratio) = desktop.average_relative_open_to_first_byte_gap_ratio {
        if relative_gap_ratio > config.helix_canary_max_relative_open_to_first_byte_gap_ratio {
            reasons.push(format!(
                "relative open->first-byte gap ratio={relative_gap_ratio:.2}"
            ));
        }
    }

    if !reasons.is_empty() {
        return ("no-go", reasons, evidence_gaps);
    }

    if desktop.continuity_observed_events < config.helix_canary_min_continuity_observations {
        evidence_gaps.push(format!(
            "continuity observations={}",
            desktop.continuity_observed_events
        ));
    }

    if config.helix_canary_require_throughput_evidence
        && desktop.throughput_evidence_observed_events == 0
    {
        evidence_gaps.push(format!(
            "throughput evidence observations={}",
            desktop.throughput_evidence_observed_events
        ));
    }

    if desktop.benchmark_observed_events > 0
        && desktop
            .average_relative_open_to_first_byte_gap_ratio
            .is_none()
    {
        evidence_gaps.push("gap ratio evidence unavailable in rollout status".to_string());
    }

    if matches!(policy.channel_posture.as_str(), "watch" | "degraded") {
        reasons.push(format!("channel posture={}", policy.channel_posture));
    }

    if let Some(active_profile_policy) = active_profile_policy {
        if active_profile_policy.advisory_state == "watch" {
            reasons.push("active profile advisory=watch".to_string());
        }
    }

    if !reasons.is_empty() || !evidence_gaps.is_empty() {
        let combined = reasons
            .iter()
            .cloned()
            .chain(evidence_gaps.iter().cloned())
            .collect::<Vec<_>>();
        return ("watch", combined, evidence_gaps);
    }

    ("go", reasons, evidence_gaps)
}

fn derive_canary_follow_up(
    rollout: &RolloutStateResponse,
    decision: &str,
    reasons: &[String],
    evidence_gaps: &[String],
) -> (Option<&'static str>, Option<&'static str>, Vec<String>) {
    let applied_reaction = rollout.policy.applied_automatic_reaction.as_deref();

    if matches!(applied_reaction, Some("pause-channel")) {
        return (
            Some("hold-channel-paused"),
            Some("critical"),
            vec![
                "Keep new Helix sessions paused on this rollout channel.".to_string(),
                "Validate node convergence and replacement profile readiness.".to_string(),
                "Re-run canary evidence before any manual resume decision.".to_string(),
            ],
        );
    }

    if matches!(applied_reaction, Some("rotate-profile-now"))
        || rollout.policy.profile_rotation_recommended
    {
        let target_profile = rollout
            .policy
            .applied_transport_profile_id
            .clone()
            .or_else(|| rollout.policy.recommended_transport_profile_id.clone())
            .unwrap_or_else(|| "healthier profile candidate".to_string());
        return (
            Some("approve-profile-rotation"),
            Some(if decision == "no-go" {
                "critical"
            } else {
                "warning"
            }),
            vec![
                format!("Confirm desktop and node assignments converge on {target_profile}."),
                "Watch continuity, fallback, and throughput evidence during the next window."
                    .to_string(),
                "Revoke or demote the degraded profile after recovery stabilizes.".to_string(),
            ],
        );
    }

    if decision == "no-go" {
        let reason_summary = if reasons.is_empty() {
            "formal canary no-go without explicit reason".to_string()
        } else {
            reasons.join("; ")
        };

        return (
            Some("review-canary-blockers"),
            Some("critical"),
            vec![
                "Treat the rollout as blocked for expansion until the no-go reason is resolved."
                    .to_string(),
                format!(
                    "Validate whether manual pause or profile rotation is required: {reason_summary}."
                ),
                "Re-run canary evidence after corrective action.".to_string(),
            ],
        );
    }

    if !evidence_gaps.is_empty() {
        return (
            Some("collect-more-evidence"),
            Some("warning"),
            vec![
                "Run Helix recovery drill and target-matrix benchmarks on the affected desktop cohort."
                    .to_string(),
                "Capture support bundles until continuity and throughput evidence reach the canary thresholds."
                    .to_string(),
                "Keep the rollout on watch until evidence gaps are cleared.".to_string(),
            ],
        );
    }

    if decision == "watch" {
        return (
            Some("review-watch-signals"),
            Some("warning"),
            vec![
                "Inspect the watch-level reasons against the current profile posture.".to_string(),
                "Keep the rollout in canary while continuity and fallback trends stabilize."
                    .to_string(),
                "Promote only after the next evidence snapshot returns go.".to_string(),
            ],
        );
    }

    (None, None, Vec::new())
}

#[cfg(test)]
mod tests {
    use serde_json::json;

    use super::NodeRegistryService;
    use crate::remnawave::client::NodeInventoryItem;

    #[test]
    fn inventory_to_upsert_maps_current_remnawave_inventory_shape() {
        let inventory_item: NodeInventoryItem = serde_json::from_value(json!({
            "uuid": "550e8400-e29b-41d4-a716-446655440123",
            "name": "PT Edge FRA 01",
            "address": "fra-01.example.com",
            "isDisabled": false,
            "activePluginUuid": "550e8400-e29b-41d4-a716-446655440124",
            "versions": {
                "node": "2.7.4",
                "xray": "1.8.10"
            }
        }))
        .expect("current Remnawave inventory payload");

        let upsert = NodeRegistryService::inventory_to_upsert(&inventory_item);

        assert_eq!(upsert.remnawave_node_id, inventory_item.id);
        assert_eq!(upsert.node_name, inventory_item.name);
        assert_eq!(upsert.hostname.as_deref(), Some("fra-01.example.com"));
        assert_eq!(upsert.adapter_node_label, "fra-01-example-com");
        assert_eq!(inventory_item.effective_enabled(), Some(true));
        assert_eq!(inventory_item.effective_node_version(), Some("2.7.4"));
        assert_eq!(inventory_item.effective_xray_version(), Some("1.8.10"));
        assert_eq!(
            inventory_item.active_plugin_uuid.as_deref(),
            Some("550e8400-e29b-41d4-a716-446655440124")
        );
    }
}
