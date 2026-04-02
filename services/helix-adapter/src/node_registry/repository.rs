use std::str::FromStr;

use sqlx::PgPool;
use uuid::Uuid;

use crate::{
    error::AppError,
    node_registry::model::{
        DesktopRuntimeEventRequest, NodeHeartbeatRequest, NodeRegistryRecord, NodeUpsertInput,
        PublishRolloutBatchRequest, RolloutBatchRecord, RolloutChannel, RolloutDesiredState,
        RolloutHealthCounts, RolloutPolicyActuationRecord, RolloutStateResponse,
    },
    transport_profiles::{
        repository::{
            profile_policy_summary_from_totals, RuntimeEvidenceTotals, TransportProfileRepository,
        },
        service::{
            is_new_session_issuable, prioritize_candidates, prioritize_candidates_for_target,
            ProfileSelectionTarget,
        },
    },
};

const BLOCKED_PROFILE_SUPPRESSION_BASE_MINUTES: i64 = 45;
const BLOCKED_PROFILE_SUPPRESSION_STEP_MINUTES: i64 = 15;
const BLOCKED_PROFILE_SUPPRESSION_MAX_MINUTES: i64 = 240;

#[derive(Debug, Clone, sqlx::FromRow)]
struct RolloutDesktopEvidenceCounts {
    ready_total: f64,
    fallback_total: f64,
    continuity_total: f64,
    continuity_success_total: f64,
    cross_route_success_total: f64,
    benchmark_total: f64,
    throughput_evidence_total: f64,
    average_benchmark_throughput_kbps: Option<f64>,
    average_relative_throughput_ratio: Option<f64>,
    average_relative_open_to_first_byte_gap_ratio: Option<f64>,
}

#[derive(Debug, Clone)]
pub struct NodeRegistryRepository {
    pool: PgPool,
}

impl NodeRegistryRepository {
    pub fn new(pool: PgPool) -> Self {
        Self { pool }
    }

    pub async fn upsert_nodes(&self, nodes: &[NodeUpsertInput]) -> Result<(), AppError> {
        for node in nodes {
            sqlx::query(
                r#"
                INSERT INTO helix.nodes (
                    service_node_id,
                    remnawave_node_id,
                    node_name,
                    hostname,
                    transport_enabled,
                    rollout_channel,
                    node_group,
                    adapter_node_label,
                    last_synced_at,
                    created_at,
                    updated_at
                )
                VALUES ($1, $2, $3, $4, FALSE, 'lab', 'regional', $5, $6, NOW(), NOW())
                ON CONFLICT (remnawave_node_id) DO UPDATE
                SET
                    node_name = EXCLUDED.node_name,
                    hostname = EXCLUDED.hostname,
                    last_synced_at = EXCLUDED.last_synced_at,
                    updated_at = NOW()
                "#,
            )
            .bind(Uuid::new_v4())
            .bind(&node.remnawave_node_id)
            .bind(&node.node_name)
            .bind(&node.hostname)
            .bind(&node.adapter_node_label)
            .bind(node.last_synced_at)
            .execute(&self.pool)
            .await?;
        }

        Ok(())
    }

    pub async fn list_nodes(&self) -> Result<Vec<NodeRegistryRecord>, AppError> {
        let nodes = sqlx::query_as::<_, NodeRegistryRecord>(
            r#"
            SELECT
                service_node_id,
                remnawave_node_id,
                node_name,
                hostname,
                transport_port,
                transport_enabled,
                rollout_channel,
                node_group,
                adapter_node_label,
                last_heartbeat_at,
                daemon_version,
                active_rollout_id,
                last_synced_at,
                created_at,
                updated_at
            FROM helix.nodes
            ORDER BY transport_enabled DESC, remnawave_node_id ASC
            "#,
        )
        .fetch_all(&self.pool)
        .await?;

        Ok(nodes)
    }

    pub async fn list_transport_enabled_nodes_for_channel(
        &self,
        channel: &str,
    ) -> Result<Vec<NodeRegistryRecord>, AppError> {
        let nodes = sqlx::query_as::<_, NodeRegistryRecord>(
            r#"
            SELECT
                service_node_id,
                remnawave_node_id,
                node_name,
                hostname,
                transport_port,
                transport_enabled,
                rollout_channel,
                node_group,
                adapter_node_label,
                last_heartbeat_at,
                daemon_version,
                active_rollout_id,
                last_synced_at,
                created_at,
                updated_at
            FROM helix.nodes
            WHERE transport_enabled = TRUE
              AND rollout_channel = $1
            ORDER BY COALESCE(last_heartbeat_at, TIMESTAMPTZ '1970-01-01 00:00:00+00') DESC,
                     remnawave_node_id ASC
            "#,
        )
        .bind(channel)
        .fetch_all(&self.pool)
        .await?;

        Ok(nodes)
    }

    pub async fn find_node_by_remnawave_id(
        &self,
        node_id: &str,
    ) -> Result<NodeRegistryRecord, AppError> {
        let node = sqlx::query_as::<_, NodeRegistryRecord>(
            r#"
            SELECT
                service_node_id,
                remnawave_node_id,
                node_name,
                hostname,
                transport_port,
                transport_enabled,
                rollout_channel,
                node_group,
                adapter_node_label,
                last_heartbeat_at,
                daemon_version,
                active_rollout_id,
                last_synced_at,
                created_at,
                updated_at
            FROM helix.nodes
            WHERE remnawave_node_id = $1
            "#,
        )
        .bind(node_id)
        .fetch_optional(&self.pool)
        .await?
        .ok_or_else(|| AppError::NotFound(format!("node not found: {node_id}")))?;

        Ok(node)
    }

    pub async fn publish_rollout(
        &self,
        request: &PublishRolloutBatchRequest,
    ) -> Result<RolloutBatchRecord, AppError> {
        let target_nodes = i32::try_from(request.target_node_ids.len()).map_err(|_| {
            AppError::BadRequest("target_node_ids length exceeds supported range".to_string())
        })?;

        let rollout = sqlx::query_as::<_, RolloutBatchRecord>(
            r#"
            INSERT INTO helix.rollout_batches (
                rollout_id,
                channel,
                desired_state,
                batch_id,
                manifest_version,
                target_nodes,
                completed_nodes,
                failed_nodes,
                desktop_connect_success_rate,
                desktop_fallback_rate,
                pause_on_rollback_spike,
                revoke_on_manifest_error,
                published_at,
                created_at,
                updated_at
            )
            VALUES ($1, $2, 'running', $3, $4, $5, 0, 0, 0, 0, $6, $7, NOW(), NOW(), NOW())
            ON CONFLICT (rollout_id) DO UPDATE
            SET
                channel = EXCLUDED.channel,
                desired_state = 'running',
                batch_id = EXCLUDED.batch_id,
                manifest_version = EXCLUDED.manifest_version,
                target_nodes = EXCLUDED.target_nodes,
                pause_on_rollback_spike = EXCLUDED.pause_on_rollback_spike,
                revoke_on_manifest_error = EXCLUDED.revoke_on_manifest_error,
                published_at = NOW(),
                updated_at = NOW()
            RETURNING
                rollout_id,
                channel,
                desired_state,
                batch_id,
                manifest_version,
                target_nodes,
                completed_nodes,
                failed_nodes,
                desktop_connect_success_rate,
                desktop_fallback_rate,
                pause_on_rollback_spike,
                revoke_on_manifest_error,
                published_at,
                created_at,
                updated_at
            "#,
        )
        .bind(&request.rollout_id)
        .bind(request.channel.as_str())
        .bind(&request.batch_id)
        .bind(&request.manifest_version)
        .bind(target_nodes)
        .bind(request.pause_on_rollback_spike)
        .bind(request.revoke_on_manifest_error)
        .fetch_one(&self.pool)
        .await?;

        sqlx::query(
            r#"
            UPDATE helix.nodes
            SET
                transport_enabled = TRUE,
                rollout_channel = $1,
                active_rollout_id = $2,
                updated_at = NOW()
            WHERE remnawave_node_id = ANY($3)
            "#,
        )
        .bind(request.channel.as_str())
        .bind(&request.rollout_id)
        .bind(&request.target_node_ids)
        .execute(&self.pool)
        .await?;

        Ok(rollout)
    }

    pub async fn set_rollout_state(
        &self,
        rollout_id: &str,
        state: RolloutDesiredState,
    ) -> Result<RolloutBatchRecord, AppError> {
        let rollout = sqlx::query_as::<_, RolloutBatchRecord>(
            r#"
            UPDATE helix.rollout_batches
            SET desired_state = $2, updated_at = NOW()
            WHERE rollout_id = $1
            RETURNING
                rollout_id,
                channel,
                desired_state,
                batch_id,
                manifest_version,
                target_nodes,
                completed_nodes,
                failed_nodes,
                desktop_connect_success_rate,
                desktop_fallback_rate,
                pause_on_rollback_spike,
                revoke_on_manifest_error,
                published_at,
                created_at,
                updated_at
            "#,
        )
        .bind(rollout_id)
        .bind(state.as_str())
        .fetch_optional(&self.pool)
        .await?
        .ok_or_else(|| AppError::NotFound(format!("rollout not found: {rollout_id}")))?;

        Ok(rollout)
    }

    pub async fn find_active_rollout_by_channel(
        &self,
        channel: &str,
    ) -> Result<RolloutBatchRecord, AppError> {
        let rollout = sqlx::query_as::<_, RolloutBatchRecord>(
            r#"
            SELECT
                rollout_id,
                channel,
                desired_state,
                batch_id,
                manifest_version,
                target_nodes,
                completed_nodes,
                failed_nodes,
                desktop_connect_success_rate,
                desktop_fallback_rate,
                pause_on_rollback_spike,
                revoke_on_manifest_error,
                published_at,
                created_at,
                updated_at
            FROM helix.rollout_batches
            WHERE channel = $1
              AND desired_state = 'running'
            ORDER BY published_at DESC
            LIMIT 1
            "#,
        )
        .bind(channel)
        .fetch_optional(&self.pool)
        .await?
        .ok_or_else(|| {
            AppError::NotFound(format!(
                "no active rollout configured for channel: {channel}"
            ))
        })?;

        Ok(rollout)
    }

    pub async fn find_rollout_by_id(
        &self,
        rollout_id: &str,
    ) -> Result<RolloutBatchRecord, AppError> {
        let rollout = sqlx::query_as::<_, RolloutBatchRecord>(
            r#"
            SELECT
                rollout_id,
                channel,
                desired_state,
                batch_id,
                manifest_version,
                target_nodes,
                completed_nodes,
                failed_nodes,
                desktop_connect_success_rate,
                desktop_fallback_rate,
                pause_on_rollback_spike,
                revoke_on_manifest_error,
                published_at,
                created_at,
                updated_at
            FROM helix.rollout_batches
            WHERE rollout_id = $1
            "#,
        )
        .bind(rollout_id)
        .fetch_optional(&self.pool)
        .await?
        .ok_or_else(|| AppError::NotFound(format!("rollout not found: {rollout_id}")))?;

        Ok(rollout)
    }

    pub async fn fetch_active_rollout_actuation(
        &self,
        rollout_id: &str,
    ) -> Result<Option<RolloutPolicyActuationRecord>, AppError> {
        let actuation = sqlx::query_as::<_, RolloutPolicyActuationRecord>(
            r#"
            SELECT
                rollout_id,
                channel,
                reaction,
                target_transport_profile_id,
                trigger_reason,
                applied,
                created_at,
                updated_at,
                cleared_at
            FROM helix.rollout_policy_actuations
            WHERE rollout_id = $1
              AND applied = TRUE
              AND cleared_at IS NULL
            "#,
        )
        .bind(rollout_id)
        .fetch_optional(&self.pool)
        .await?;

        Ok(actuation)
    }

    pub async fn fetch_rollout_state(
        &self,
        rollout_id: &str,
    ) -> Result<RolloutStateResponse, AppError> {
        let rollout = sqlx::query_as::<_, RolloutBatchRecord>(
            r#"
            SELECT
                rollout_id,
                channel,
                desired_state,
                batch_id,
                manifest_version,
                target_nodes,
                completed_nodes,
                failed_nodes,
                desktop_connect_success_rate,
                desktop_fallback_rate,
                pause_on_rollback_spike,
                revoke_on_manifest_error,
                published_at,
                created_at,
                updated_at
            FROM helix.rollout_batches
            WHERE rollout_id = $1
            "#,
        )
        .bind(rollout_id)
        .fetch_optional(&self.pool)
        .await?
        .ok_or_else(|| AppError::NotFound(format!("rollout not found: {rollout_id}")))?;
        let active_actuation = self.fetch_active_rollout_actuation(rollout_id).await?;

        let health = sqlx::query_as::<_, RolloutHealthCounts>(
            r#"
            WITH latest AS (
                SELECT DISTINCT ON (node_id)
                    node_id,
                    observed_at,
                    ready,
                    runtime_healthy,
                    apply_state,
                    rollback_total
                FROM helix.node_heartbeat_snapshots
                WHERE rollout_id = $1
                ORDER BY node_id, observed_at DESC
            )
            SELECT
                COUNT(*) FILTER (
                    WHERE ready = TRUE
                      AND runtime_healthy = TRUE
                      AND apply_state = 'idle'
                )::BIGINT AS healthy,
                COUNT(*) FILTER (
                    WHERE observed_at < NOW() - INTERVAL '60 seconds'
                )::BIGINT AS stale,
                COUNT(*) FILTER (
                    WHERE apply_state = 'rolled-back'
                       OR rollback_total > 0
                )::BIGINT AS rolled_back
            FROM latest
            "#,
        )
        .bind(rollout_id)
        .fetch_one(&self.pool)
        .await
        .unwrap_or(RolloutHealthCounts {
            healthy: 0,
            stale: 0,
            rolled_back: 0,
        });

        let desktop = sqlx::query_as::<_, RolloutDesktopEvidenceCounts>(
            r#"
            SELECT
                COUNT(*) FILTER (WHERE event_kind = 'ready')::DOUBLE PRECISION AS ready_total,
                COUNT(*) FILTER (WHERE event_kind = 'fallback')::DOUBLE PRECISION AS fallback_total,
                COUNT(*) FILTER (
                    WHERE jsonb_typeof(payload -> 'continuity') = 'object'
                       OR jsonb_typeof(payload -> 'recovery') = 'object'
                )::DOUBLE PRECISION AS continuity_total,
                COUNT(*) FILTER (
                    WHERE COALESCE((payload -> 'continuity' ->> 'successful_continuity_recovers')::INT, 0) > 0
                       OR COALESCE((payload -> 'recovery' ->> 'same_route_recovered')::BOOLEAN, FALSE) = TRUE
                )::DOUBLE PRECISION AS continuity_success_total,
                COUNT(*) FILTER (
                    WHERE COALESCE((payload -> 'continuity' ->> 'successful_cross_route_recovers')::INT, 0) > 0
                       OR COALESCE((payload -> 'recovery' ->> 'successful_cross_route_recovers')::INT, 0) > 0
                )::DOUBLE PRECISION AS cross_route_success_total,
                COUNT(*) FILTER (
                    WHERE event_kind = 'benchmark'
                      AND jsonb_typeof(payload -> 'benchmark') = 'object'
                )::DOUBLE PRECISION AS benchmark_total,
                COUNT(*) FILTER (
                    WHERE event_kind = 'benchmark'
                      AND jsonb_typeof(payload -> 'benchmark') = 'object'
                      AND (payload -> 'benchmark' ->> 'relative_throughput_ratio_vs_baseline') IS NOT NULL
                )::DOUBLE PRECISION AS throughput_evidence_total,
                AVG((payload -> 'benchmark' ->> 'throughput_kbps')::DOUBLE PRECISION) FILTER (
                    WHERE event_kind = 'benchmark'
                      AND jsonb_typeof(payload -> 'benchmark') = 'object'
                      AND (payload -> 'benchmark' ->> 'throughput_kbps') IS NOT NULL
                ) AS average_benchmark_throughput_kbps,
                AVG((payload -> 'benchmark' ->> 'relative_throughput_ratio_vs_baseline')::DOUBLE PRECISION) FILTER (
                    WHERE event_kind = 'benchmark'
                      AND jsonb_typeof(payload -> 'benchmark') = 'object'
                      AND (payload -> 'benchmark' ->> 'relative_throughput_ratio_vs_baseline') IS NOT NULL
                ) AS average_relative_throughput_ratio,
                AVG((payload -> 'benchmark' ->> 'relative_open_to_first_byte_gap_ratio_vs_baseline')::DOUBLE PRECISION) FILTER (
                    WHERE event_kind = 'benchmark'
                      AND jsonb_typeof(payload -> 'benchmark') = 'object'
                      AND (payload -> 'benchmark' ->> 'relative_open_to_first_byte_gap_ratio_vs_baseline') IS NOT NULL
                ) AS average_relative_open_to_first_byte_gap_ratio
            FROM helix.desktop_runtime_events
            WHERE rollout_id = $1
            "#,
        )
        .bind(rollout_id)
        .fetch_one(&self.pool)
        .await
        .unwrap_or(RolloutDesktopEvidenceCounts {
            ready_total: 0.0,
            fallback_total: 0.0,
            continuity_total: 0.0,
            continuity_success_total: 0.0,
            cross_route_success_total: 0.0,
            benchmark_total: 0.0,
            throughput_evidence_total: 0.0,
            average_benchmark_throughput_kbps: None,
            average_relative_throughput_ratio: None,
            average_relative_open_to_first_byte_gap_ratio: None,
        });
        let rollout_channel = RolloutChannel::from_str(&rollout.channel)?;
        let transport_profiles = TransportProfileRepository::new(self.pool.clone());
        let policy_candidates = transport_profiles
            .list_candidate_profiles(rollout_channel)
            .await?;
        let policy_candidates = transport_profiles
            .attach_policy_for_rollout(rollout_id, policy_candidates)
            .await?;
        let observed_active_transport_profile_id = sqlx::query_scalar::<_, String>(
            r#"
            SELECT transport_profile_id
            FROM helix.desktop_runtime_events
            WHERE rollout_id = $1
              AND event_kind <> 'benchmark'
            ORDER BY observed_at DESC
            LIMIT 1
            "#,
        )
        .bind(rollout_id)
        .fetch_optional(&self.pool)
        .await?;
        let healthy_candidate_count = i32::try_from(
            policy_candidates
                .iter()
                .filter(|candidate| {
                    candidate
                        .policy
                        .as_ref()
                        .map(|policy| policy.selection_eligible && !policy.degraded)
                        .unwrap_or(true)
                })
                .count(),
        )
        .unwrap_or(i32::MAX);
        let eligible_candidate_count = i32::try_from(
            policy_candidates
                .iter()
                .filter(|candidate| {
                    candidate
                        .policy
                        .as_ref()
                        .map(|policy| policy.selection_eligible)
                        .unwrap_or(true)
                })
                .count(),
        )
        .unwrap_or(i32::MAX);
        let suppressed_candidate_count = i32::try_from(
            policy_candidates
                .iter()
                .filter(|candidate| {
                    candidate
                        .policy
                        .as_ref()
                        .is_some_and(|policy| policy.suppression_window_active)
                })
                .count(),
        )
        .unwrap_or(i32::MAX);
        let prioritized_candidates = prioritize_candidates(policy_candidates.clone());
        let new_session_candidates = prioritize_candidates_for_target(
            policy_candidates,
            ProfileSelectionTarget::DesktopNewSession,
        );
        let active_profile = observed_active_transport_profile_id
            .as_deref()
            .and_then(|transport_profile_id| {
                prioritized_candidates
                    .iter()
                    .find(|candidate| candidate.transport_profile_id == transport_profile_id)
                    .cloned()
            })
            .or_else(|| prioritized_candidates.first().cloned());
        let selected_profile_new_session_issuable =
            active_profile.as_ref().is_some_and(is_new_session_issuable);
        let active_profile_posture = active_profile
            .as_ref()
            .and_then(|profile| profile.policy.as_ref())
            .map(|policy| policy.new_session_posture.as_str());
        let recommended_transport_profile_id = new_session_candidates
            .iter()
            .find(|candidate| {
                active_profile
                    .as_ref()
                    .map(|selected| candidate.transport_profile_id != selected.transport_profile_id)
                    .unwrap_or(true)
            })
            .map(|candidate| candidate.transport_profile_id.clone());
        let active_profile_policy = active_profile
            .as_ref()
            .and_then(|profile| profile.policy.clone());
        let active_profile_suppressed = active_profile_policy
            .as_ref()
            .is_some_and(|policy| policy.suppression_window_active);
        let active_profile_advisory_state = active_profile_policy
            .as_ref()
            .map(|policy| policy.advisory_state.as_str());
        let (channel_posture, automatic_reaction) = match (
            active_profile.as_ref(),
            active_profile_suppressed,
            active_profile_posture,
            recommended_transport_profile_id.as_deref(),
        ) {
            (None, _, _, _) => ("critical".to_string(), "pause-channel".to_string()),
            (_, true, _, Some(_)) => ("critical".to_string(), "rotate-profile-now".to_string()),
            (_, true, _, None) => ("critical".to_string(), "pause-channel".to_string()),
            (_, false, Some("blocked"), Some(_)) => {
                ("blocked".to_string(), "rotate-new-sessions".to_string())
            }
            (_, false, Some("blocked"), None) => {
                ("blocked".to_string(), "pause-new-sessions".to_string())
            }
            (_, false, Some("guarded"), Some(_)) => {
                ("guarded".to_string(), "rotate-new-sessions".to_string())
            }
            (_, false, Some("guarded"), None) => ("guarded".to_string(), "none".to_string()),
            (_, false, Some("watch"), _) => ("watch".to_string(), "observe".to_string()),
            _ => ("healthy".to_string(), "none".to_string()),
        };
        let profile_rotation_recommended = matches!(
            automatic_reaction.as_str(),
            "rotate-new-sessions" | "rotate-profile-now"
        );
        let pause_recommended = matches!(
            automatic_reaction.as_str(),
            "pause-new-sessions" | "pause-channel"
        );
        let recommended_action = match (
            active_profile.as_ref(),
            active_profile_suppressed,
            active_profile_advisory_state,
            selected_profile_new_session_issuable,
            recommended_transport_profile_id.as_deref(),
        ) {
            (Some(selected), true, _, _, Some(alternative)) => Some(format!(
                "Rotate Helix rollout {} away from transport profile {} to {} now. The active profile is inside an adapter suppression cooloff window and should not receive new sessions until it recovers.",
                rollout_id, selected.transport_profile_id, alternative
            )),
            (Some(selected), true, _, _, None) => Some(format!(
                "Pause Helix rollout {} for new sessions. Transport profile {} is inside an adapter suppression cooloff window and no healthier compatible profile is available.",
                rollout_id, selected.transport_profile_id
            )),
            (Some(selected), false, Some("avoid-new-sessions"), _, Some(alternative)) => Some(format!(
                "Rotate new Helix sessions from transport profile {} to {}. The current preferred profile is marked avoid-new-sessions.",
                selected.transport_profile_id, alternative
            )),
            (Some(selected), false, Some("avoid-new-sessions"), _, None) => Some(format!(
                "Pause new Helix sessions for rollout {}. Transport profile {} is marked avoid-new-sessions and no healthier compatible profile is available.",
                rollout_id, selected.transport_profile_id
            )),
            (Some(selected), false, Some("degraded"), false, Some(alternative)) => Some(format!(
                "Rotate new Helix sessions from transport profile {} to {}. The current preferred profile no longer meets continuity guardrails for new sessions.",
                selected.transport_profile_id, alternative
            )),
            (Some(selected), false, Some("degraded"), false, None) => Some(format!(
                "Pause new Helix sessions for rollout {}. Transport profile {} is degraded and no longer meets the continuity guardrails required for new desktop sessions.",
                rollout_id, selected.transport_profile_id
            )),
            (Some(selected), false, Some("degraded"), true, Some(alternative)) => Some(format!(
                "Prefer transport profile {} for new Helix sessions. Current preferred profile {} is degraded.",
                alternative, selected.transport_profile_id
            )),
            (Some(selected), false, Some("degraded"), true, None) => Some(format!(
                "Keep rollout {} under watch. Transport profile {} is degraded and no healthier compatible profile is currently available.",
                rollout_id, selected.transport_profile_id
            )),
            (None, _, _, _, _) => Some(format!(
                "Pause Helix rollout {} for new sessions. No compatible transport profile is currently eligible for desktop issuance.",
                rollout_id
            )),
            _ => None,
        };

        Ok(RolloutStateResponse {
            schema_version: "1.0",
            rollout_id: rollout.rollout_id,
            channel: rollout.channel,
            desired_state: rollout.desired_state,
            published_at: rollout.published_at,
            current_batch: crate::node_registry::model::RolloutBatchSummary {
                batch_id: rollout.batch_id,
                manifest_version: rollout.manifest_version,
                target_nodes: rollout.target_nodes,
                completed_nodes: rollout.completed_nodes,
                failed_nodes: rollout.failed_nodes,
            },
            nodes: crate::node_registry::model::RolloutNodeSummary {
                healthy: health.healthy,
                stale: health.stale,
                rolled_back: health.rolled_back,
            },
            desktop: crate::node_registry::model::RolloutDesktopSummary {
                connect_success_rate: if desktop.ready_total + desktop.fallback_total == 0.0 {
                    rollout.desktop_connect_success_rate
                } else {
                    desktop.ready_total / (desktop.ready_total + desktop.fallback_total)
                },
                fallback_rate: if desktop.ready_total + desktop.fallback_total == 0.0 {
                    rollout.desktop_fallback_rate
                } else {
                    desktop.fallback_total / (desktop.ready_total + desktop.fallback_total)
                },
                continuity_observed_events: desktop.continuity_total.round() as i32,
                continuity_success_rate: if desktop.continuity_total == 0.0 {
                    0.0
                } else {
                    desktop.continuity_success_total / desktop.continuity_total
                },
                cross_route_recovery_rate: if desktop.continuity_total == 0.0 {
                    0.0
                } else {
                    desktop.cross_route_success_total / desktop.continuity_total
                },
                benchmark_observed_events: desktop.benchmark_total.round() as i32,
                throughput_evidence_observed_events: desktop
                    .throughput_evidence_total
                    .round() as i32,
                average_benchmark_throughput_kbps: desktop.average_benchmark_throughput_kbps,
                average_relative_throughput_ratio: desktop.average_relative_throughput_ratio,
                average_relative_open_to_first_byte_gap_ratio: desktop
                    .average_relative_open_to_first_byte_gap_ratio,
            },
            policy: crate::node_registry::model::RolloutPolicySummary {
                pause_on_rollback_spike: rollout.pause_on_rollback_spike,
                revoke_on_manifest_error: rollout.revoke_on_manifest_error,
                active_transport_profile_id: active_profile
                    .as_ref()
                    .map(|profile| profile.transport_profile_id.clone()),
                active_profile_policy,
                recommended_transport_profile_id,
                healthy_candidate_count,
                eligible_candidate_count,
                suppressed_candidate_count,
                active_profile_suppressed,
                channel_posture,
                automatic_reaction,
                applied_automatic_reaction: active_actuation
                    .as_ref()
                    .map(|actuation| actuation.reaction.clone()),
                applied_transport_profile_id: active_actuation
                    .as_ref()
                    .and_then(|actuation| actuation.target_transport_profile_id.clone()),
                automatic_reaction_trigger_reason: active_actuation
                    .as_ref()
                    .and_then(|actuation| actuation.trigger_reason.clone()),
                automatic_reaction_updated_at: active_actuation
                    .as_ref()
                    .map(|actuation| actuation.updated_at),
                pause_recommended,
                profile_rotation_recommended,
                recommended_action,
            },
        })
    }

    pub async fn touch_last_known_good_bundle(
        &self,
        node_id: &str,
        assignment_id: Uuid,
        bundle_version: &str,
    ) -> Result<(), AppError> {
        sqlx::query(
            r#"
            INSERT INTO helix.last_known_good_bundles (
                node_id,
                assignment_id,
                bundle_version,
                updated_at
            )
            VALUES ($1, $2, $3, NOW())
            ON CONFLICT (node_id) DO UPDATE
            SET
                assignment_id = EXCLUDED.assignment_id,
                bundle_version = EXCLUDED.bundle_version,
                updated_at = NOW()
            "#,
        )
        .bind(node_id)
        .bind(assignment_id)
        .bind(bundle_version)
        .execute(&self.pool)
        .await?;

        Ok(())
    }

    pub async fn get_last_known_good_bundle(
        &self,
        rollout_id: &str,
        node_id: &str,
    ) -> Result<Option<String>, AppError> {
        let bundle_version = sqlx::query_scalar::<_, String>(
            r#"
            SELECT lkg.bundle_version
            FROM helix.last_known_good_bundles lkg
            JOIN helix.nodes n
              ON n.remnawave_node_id = lkg.node_id
            WHERE lkg.node_id = $1
              AND (n.active_rollout_id = $2 OR $2 = '')
            ORDER BY lkg.updated_at DESC
            LIMIT 1
            "#,
        )
        .bind(node_id)
        .bind(rollout_id)
        .fetch_optional(&self.pool)
        .await?;

        Ok(bundle_version)
    }

    pub async fn record_heartbeat(&self, heartbeat: &NodeHeartbeatRequest) -> Result<(), AppError> {
        sqlx::query(
            r#"
            INSERT INTO helix.node_heartbeat_snapshots (
                heartbeat_id,
                node_id,
                rollout_id,
                observed_at,
                daemon_version,
                instance_id,
                daemon_status,
                active_bundle_version,
                pending_bundle_version,
                last_known_good_version,
                ready,
                runtime_healthy,
                apply_state,
                latency_ms,
                reason,
                rollback_total,
                apply_fail_total,
                capabilities,
                payload
            )
            VALUES (
                $1, $2, $3, $4, $5, $6, $7,
                $8, $9, $10, $11, $12, $13, $14, $15, $16, $17, $18, $19
            )
            "#,
        )
        .bind(heartbeat.heartbeat_id)
        .bind(&heartbeat.node_id)
        .bind(&heartbeat.rollout_id)
        .bind(heartbeat.observed_at)
        .bind(&heartbeat.daemon.version)
        .bind(&heartbeat.daemon.instance_id)
        .bind(&heartbeat.daemon.status)
        .bind(&heartbeat.bundle.active_version)
        .bind(&heartbeat.bundle.pending_version)
        .bind(&heartbeat.bundle.last_known_good_version)
        .bind(heartbeat.health.ready)
        .bind(heartbeat.health.runtime_healthy)
        .bind(&heartbeat.health.apply_state)
        .bind(heartbeat.health.latency_ms)
        .bind(&heartbeat.health.reason)
        .bind(heartbeat.counters.rollback_total)
        .bind(heartbeat.counters.apply_fail_total)
        .bind(serde_json::to_value(&heartbeat.capabilities)?)
        .bind(serde_json::to_value(heartbeat)?)
        .execute(&self.pool)
        .await?;

        sqlx::query(
            r#"
            UPDATE helix.nodes
            SET
                last_heartbeat_at = $2,
                daemon_version = $3,
                active_rollout_id = $4,
                updated_at = NOW()
            WHERE remnawave_node_id = $1
            "#,
        )
        .bind(&heartbeat.node_id)
        .bind(heartbeat.observed_at)
        .bind(&heartbeat.daemon.version)
        .bind(&heartbeat.rollout_id)
        .execute(&self.pool)
        .await?;

        Ok(())
    }

    pub async fn record_desktop_runtime_event(
        &self,
        event: &DesktopRuntimeEventRequest,
    ) -> Result<(), AppError> {
        sqlx::query(
            r#"
            INSERT INTO helix.desktop_runtime_events (
                event_id,
                user_id,
                desktop_client_id,
                manifest_version_id,
                rollout_id,
                transport_profile_id,
                event_kind,
                active_core,
                fallback_core,
                latency_ms,
                route_count,
                reason,
                observed_at,
                payload
            )
            VALUES (
                $1, $2, $3, $4, $5, $6, $7,
                $8, $9, $10, $11, $12, $13, $14
            )
            "#,
        )
        .bind(event.event_id)
        .bind(&event.user_id)
        .bind(&event.desktop_client_id)
        .bind(event.manifest_version_id)
        .bind(&event.rollout_id)
        .bind(&event.transport_profile_id)
        .bind(event.event_kind.as_str())
        .bind(event.active_core.as_str())
        .bind(event.fallback_core.map(|core| core.as_str()))
        .bind(event.latency_ms)
        .bind(event.route_count)
        .bind(&event.reason)
        .bind(event.observed_at)
        .bind(serde_json::to_value(&event.payload)?)
        .execute(&self.pool)
        .await?;

        sqlx::query(
            r#"
            WITH stats AS (
                SELECT
                    COUNT(*) FILTER (WHERE event_kind = 'ready')::DOUBLE PRECISION AS ready_total,
                    COUNT(*) FILTER (WHERE event_kind = 'fallback')::DOUBLE PRECISION AS fallback_total
                FROM helix.desktop_runtime_events
                WHERE rollout_id = $1
            )
            UPDATE helix.rollout_batches
            SET
                desktop_connect_success_rate = CASE
                    WHEN stats.ready_total + stats.fallback_total = 0 THEN 0
                    ELSE stats.ready_total / (stats.ready_total + stats.fallback_total)
                END,
                desktop_fallback_rate = CASE
                    WHEN stats.ready_total + stats.fallback_total = 0 THEN 0
                    ELSE stats.fallback_total / (stats.ready_total + stats.fallback_total)
                END,
                updated_at = NOW()
            FROM stats
            WHERE rollout_batches.rollout_id = $1
            "#,
        )
        .bind(&event.rollout_id)
        .execute(&self.pool)
        .await?;

        self.refresh_profile_suppression_window(&event.rollout_id, &event.transport_profile_id)
            .await?;
        self.apply_automatic_rollout_actuation(&event.rollout_id)
            .await?;

        Ok(())
    }

    async fn apply_automatic_rollout_actuation(&self, rollout_id: &str) -> Result<(), AppError> {
        let rollout_state = self.fetch_rollout_state(rollout_id).await?;
        let existing_actuation = self.fetch_active_rollout_actuation(rollout_id).await?;

        match rollout_state.policy.automatic_reaction.as_str() {
            "rotate-profile-now" => {
                if let Some(target_transport_profile_id) = rollout_state
                    .policy
                    .recommended_transport_profile_id
                    .clone()
                {
                    sqlx::query(
                        r#"
                        INSERT INTO helix.rollout_policy_actuations (
                            rollout_id,
                            channel,
                            reaction,
                            target_transport_profile_id,
                            trigger_reason,
                            applied,
                            created_at,
                            updated_at,
                            cleared_at
                        )
                        VALUES ($1, $2, $3, $4, $5, TRUE, NOW(), NOW(), NULL)
                        ON CONFLICT (rollout_id) DO UPDATE
                        SET
                            channel = EXCLUDED.channel,
                            reaction = EXCLUDED.reaction,
                            target_transport_profile_id = EXCLUDED.target_transport_profile_id,
                            trigger_reason = EXCLUDED.trigger_reason,
                            applied = TRUE,
                            updated_at = NOW(),
                            cleared_at = NULL
                        "#,
                    )
                    .bind(rollout_id)
                    .bind(&rollout_state.channel)
                    .bind("rotate-profile-now")
                    .bind(target_transport_profile_id)
                    .bind(rollout_state.policy.recommended_action.clone())
                    .execute(&self.pool)
                    .await?;
                }
            }
            "pause-channel" => {
                sqlx::query(
                    r#"
                    INSERT INTO helix.rollout_policy_actuations (
                        rollout_id,
                        channel,
                        reaction,
                        target_transport_profile_id,
                        trigger_reason,
                        applied,
                        created_at,
                        updated_at,
                        cleared_at
                    )
                    VALUES ($1, $2, $3, NULL, $4, TRUE, NOW(), NOW(), NULL)
                    ON CONFLICT (rollout_id) DO UPDATE
                    SET
                        channel = EXCLUDED.channel,
                        reaction = EXCLUDED.reaction,
                        target_transport_profile_id = NULL,
                        trigger_reason = EXCLUDED.trigger_reason,
                        applied = TRUE,
                        updated_at = NOW(),
                        cleared_at = NULL
                    "#,
                )
                .bind(rollout_id)
                .bind(&rollout_state.channel)
                .bind("pause-channel")
                .bind(rollout_state.policy.recommended_action.clone())
                .execute(&self.pool)
                .await?;

                if rollout_state.desired_state != "paused" {
                    let _ = self
                        .set_rollout_state(rollout_id, RolloutDesiredState::Paused)
                        .await?;
                }
            }
            _ => {
                if existing_actuation
                    .as_ref()
                    .is_some_and(|actuation| actuation.reaction == "rotate-profile-now")
                {
                    sqlx::query(
                        r#"
                        UPDATE helix.rollout_policy_actuations
                        SET
                            applied = FALSE,
                            updated_at = NOW(),
                            cleared_at = NOW()
                        WHERE rollout_id = $1
                          AND reaction = 'rotate-profile-now'
                          AND applied = TRUE
                          AND cleared_at IS NULL
                        "#,
                    )
                    .bind(rollout_id)
                    .execute(&self.pool)
                    .await?;
                }
            }
        }

        Ok(())
    }

    async fn refresh_profile_suppression_window(
        &self,
        rollout_id: &str,
        transport_profile_id: &str,
    ) -> Result<(), AppError> {
        #[derive(sqlx::FromRow)]
        struct ProfileEvidenceRow {
            ready_total: f64,
            fallback_total: f64,
            continuity_total: f64,
            continuity_success_total: f64,
            cross_route_success_total: f64,
        }

        let evidence = sqlx::query_as::<_, ProfileEvidenceRow>(
            r#"
            SELECT
                COUNT(*) FILTER (WHERE event_kind = 'ready')::DOUBLE PRECISION AS ready_total,
                COUNT(*) FILTER (WHERE event_kind = 'fallback')::DOUBLE PRECISION AS fallback_total,
                COUNT(*) FILTER (
                    WHERE jsonb_typeof(payload -> 'continuity') = 'object'
                       OR jsonb_typeof(payload -> 'recovery') = 'object'
                )::DOUBLE PRECISION AS continuity_total,
                COUNT(*) FILTER (
                    WHERE COALESCE((payload -> 'continuity' ->> 'successful_continuity_recovers')::INT, 0) > 0
                       OR COALESCE((payload -> 'recovery' ->> 'same_route_recovered')::BOOLEAN, FALSE) = TRUE
                )::DOUBLE PRECISION AS continuity_success_total,
                COUNT(*) FILTER (
                    WHERE COALESCE((payload -> 'continuity' ->> 'successful_cross_route_recovers')::INT, 0) > 0
                       OR COALESCE((payload -> 'recovery' ->> 'successful_cross_route_recovers')::INT, 0) > 0
                )::DOUBLE PRECISION AS cross_route_success_total
            FROM helix.desktop_runtime_events
            WHERE rollout_id = $1
              AND transport_profile_id = $2
            "#,
        )
        .bind(rollout_id)
        .bind(transport_profile_id)
        .fetch_one(&self.pool)
        .await?;

        let policy = profile_policy_summary_from_totals(RuntimeEvidenceTotals {
            ready_total: evidence.ready_total,
            fallback_total: evidence.fallback_total,
            continuity_total: evidence.continuity_total,
            continuity_success_total: evidence.continuity_success_total,
            cross_route_success_total: evidence.cross_route_success_total,
        });

        if policy.new_session_posture == "blocked" {
            let existing_observation_count = sqlx::query_scalar::<_, i32>(
                r#"
                SELECT observation_count
                FROM helix.profile_suppression_windows
                WHERE rollout_id = $1
                  AND transport_profile_id = $2
                "#,
            )
            .bind(rollout_id)
            .bind(transport_profile_id)
            .fetch_optional(&self.pool)
            .await?
            .unwrap_or(0);
            let next_observation_count = existing_observation_count + 1;
            let suppression_minutes = (BLOCKED_PROFILE_SUPPRESSION_BASE_MINUTES
                + i64::from(next_observation_count.saturating_sub(1))
                    * BLOCKED_PROFILE_SUPPRESSION_STEP_MINUTES)
                .min(BLOCKED_PROFILE_SUPPRESSION_MAX_MINUTES);

            sqlx::query(
                r#"
                INSERT INTO helix.profile_suppression_windows (
                    rollout_id,
                    transport_profile_id,
                    suppressed_until,
                    suppression_reason,
                    first_observed_at,
                    last_observed_at,
                    observation_count
                )
                VALUES ($1, $2, NOW() + ($3 * INTERVAL '1 minute'), $4, NOW(), NOW(), 1)
                ON CONFLICT (rollout_id, transport_profile_id) DO UPDATE
                SET
                    suppressed_until = GREATEST(
                        helix.profile_suppression_windows.suppressed_until,
                        NOW() + ($3 * INTERVAL '1 minute')
                    ),
                    suppression_reason = EXCLUDED.suppression_reason,
                    last_observed_at = NOW(),
                    observation_count = helix.profile_suppression_windows.observation_count + 1
                "#,
            )
            .bind(rollout_id)
            .bind(transport_profile_id)
            .bind(suppression_minutes)
            .bind("blocked-new-session-posture")
            .execute(&self.pool)
            .await?;
        } else {
            sqlx::query(
                r#"
                DELETE FROM helix.profile_suppression_windows
                WHERE rollout_id = $1
                  AND transport_profile_id = $2
                  AND suppressed_until <= NOW()
                "#,
            )
            .bind(rollout_id)
            .bind(transport_profile_id)
            .execute(&self.pool)
            .await?;
        }

        Ok(())
    }
}
