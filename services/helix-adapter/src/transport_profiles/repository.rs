use std::collections::HashMap;

use chrono::{DateTime, Utc};

use sqlx::PgPool;

use crate::{
    error::AppError,
    node_registry::model::RolloutChannel,
    transport_profiles::model::{
        is_new_session_policy_issuable, new_session_policy_posture, TransportProfilePolicySummary,
        TransportProfileRecord, UpsertTransportProfileRequest,
    },
};

#[derive(Debug, Clone, sqlx::FromRow)]
struct RuntimeEvidenceRow {
    transport_profile_id: String,
    ready_total: f64,
    fallback_total: f64,
    continuity_total: f64,
    continuity_success_total: f64,
    cross_route_success_total: f64,
}

#[derive(Debug, Clone, sqlx::FromRow)]
struct ActiveChannelRolloutRow {
    channel: String,
    rollout_id: String,
}

#[derive(Debug, Clone, sqlx::FromRow)]
struct ActiveSuppressionWindowRow {
    transport_profile_id: String,
    suppressed_until: DateTime<Utc>,
    suppression_reason: String,
    observation_count: i32,
}

#[derive(Debug, Clone, Copy)]
pub struct RuntimeEvidenceTotals {
    pub ready_total: f64,
    pub fallback_total: f64,
    pub continuity_total: f64,
    pub continuity_success_total: f64,
    pub cross_route_success_total: f64,
}

#[derive(Debug, Clone)]
pub struct TransportProfileRepository {
    pool: PgPool,
}

impl TransportProfileRepository {
    pub fn new(pool: PgPool) -> Self {
        Self { pool }
    }

    pub async fn list_profiles(&self) -> Result<Vec<TransportProfileRecord>, AppError> {
        let profiles = sqlx::query_as::<_, TransportProfileRecord>(
            r#"
            SELECT
                transport_profile_id,
                channel,
                profile_family,
                profile_version,
                policy_version,
                protocol_version,
                session_mode,
                status,
                fallback_core,
                required_capabilities,
                compatibility_min_profile_version,
                compatibility_max_profile_version,
                startup_timeout_seconds,
                runtime_unhealthy_threshold,
                created_at,
                updated_at
            FROM helix.transport_profiles
            ORDER BY channel ASC, profile_family ASC, profile_version DESC, policy_version DESC
            "#,
        )
        .fetch_all(&self.pool)
        .await?;

        self.attach_active_rollout_policy(profiles).await
    }

    pub async fn list_candidate_profiles(
        &self,
        channel: RolloutChannel,
    ) -> Result<Vec<TransportProfileRecord>, AppError> {
        let profiles = sqlx::query_as::<_, TransportProfileRecord>(
            r#"
            SELECT
                transport_profile_id,
                channel,
                profile_family,
                profile_version,
                policy_version,
                protocol_version,
                session_mode,
                status,
                fallback_core,
                required_capabilities,
                compatibility_min_profile_version,
                compatibility_max_profile_version,
                startup_timeout_seconds,
                runtime_unhealthy_threshold,
                created_at,
                updated_at
            FROM helix.transport_profiles
            WHERE channel = $1
              AND status IN ('active', 'deprecated')
            ORDER BY
                CASE status WHEN 'active' THEN 0 ELSE 1 END,
                profile_version DESC,
                policy_version DESC
            "#,
        )
        .bind(channel.as_str())
        .fetch_all(&self.pool)
        .await?;

        Ok(profiles)
    }

    pub async fn attach_policy_for_rollout(
        &self,
        rollout_id: &str,
        mut profiles: Vec<TransportProfileRecord>,
    ) -> Result<Vec<TransportProfileRecord>, AppError> {
        if profiles.is_empty() {
            return Ok(profiles);
        }

        let profile_ids = profiles
            .iter()
            .map(|profile| profile.transport_profile_id.clone())
            .collect::<Vec<_>>();
        let evidence = self
            .fetch_runtime_evidence_by_profile(rollout_id, &profile_ids)
            .await?;
        let suppressions = self
            .fetch_active_suppression_windows(rollout_id, &profile_ids)
            .await?;

        for profile in &mut profiles {
            let mut policy = profile_policy_summary(evidence.get(&profile.transport_profile_id));
            if let Some(suppression) = suppressions.get(&profile.transport_profile_id) {
                apply_active_suppression_window(&mut policy, suppression);
            }
            profile.policy = Some(policy);
        }

        Ok(profiles)
    }

    pub async fn upsert_profile(
        &self,
        request: &UpsertTransportProfileRequest,
    ) -> Result<TransportProfileRecord, AppError> {
        let profile = sqlx::query_as::<_, TransportProfileRecord>(
            r#"
            INSERT INTO helix.transport_profiles (
                transport_profile_id,
                channel,
                profile_family,
                profile_version,
                policy_version,
                protocol_version,
                session_mode,
                status,
                fallback_core,
                required_capabilities,
                compatibility_min_profile_version,
                compatibility_max_profile_version,
                startup_timeout_seconds,
                runtime_unhealthy_threshold,
                created_at,
                updated_at
            )
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, NOW(), NOW())
            ON CONFLICT (transport_profile_id) DO UPDATE
            SET
                channel = EXCLUDED.channel,
                profile_family = EXCLUDED.profile_family,
                profile_version = EXCLUDED.profile_version,
                policy_version = EXCLUDED.policy_version,
                protocol_version = EXCLUDED.protocol_version,
                session_mode = EXCLUDED.session_mode,
                status = EXCLUDED.status,
                fallback_core = EXCLUDED.fallback_core,
                required_capabilities = EXCLUDED.required_capabilities,
                compatibility_min_profile_version = EXCLUDED.compatibility_min_profile_version,
                compatibility_max_profile_version = EXCLUDED.compatibility_max_profile_version,
                startup_timeout_seconds = EXCLUDED.startup_timeout_seconds,
                runtime_unhealthy_threshold = EXCLUDED.runtime_unhealthy_threshold,
                updated_at = NOW()
            RETURNING
                transport_profile_id,
                channel,
                profile_family,
                profile_version,
                policy_version,
                protocol_version,
                session_mode,
                status,
                fallback_core,
                required_capabilities,
                compatibility_min_profile_version,
                compatibility_max_profile_version,
                startup_timeout_seconds,
                runtime_unhealthy_threshold,
                created_at,
                updated_at
            "#,
        )
        .bind(&request.transport_profile_id)
        .bind(request.channel.as_str())
        .bind(&request.profile_family)
        .bind(request.profile_version)
        .bind(request.policy_version)
        .bind(request.protocol_version)
        .bind(&request.session_mode)
        .bind(request.status.as_str())
        .bind(&request.fallback_core)
        .bind(&request.required_capabilities)
        .bind(request.compatibility_min_profile_version)
        .bind(request.compatibility_max_profile_version)
        .bind(request.startup_timeout_seconds)
        .bind(request.runtime_unhealthy_threshold)
        .fetch_one(&self.pool)
        .await?;

        Ok(profile)
    }

    pub async fn revoke_profile(
        &self,
        transport_profile_id: &str,
    ) -> Result<TransportProfileRecord, AppError> {
        let profile = sqlx::query_as::<_, TransportProfileRecord>(
            r#"
            UPDATE helix.transport_profiles
            SET status = 'revoked', updated_at = NOW()
            WHERE transport_profile_id = $1
            RETURNING
                transport_profile_id,
                channel,
                profile_family,
                profile_version,
                policy_version,
                protocol_version,
                session_mode,
                status,
                fallback_core,
                required_capabilities,
                compatibility_min_profile_version,
                compatibility_max_profile_version,
                startup_timeout_seconds,
                runtime_unhealthy_threshold,
                created_at,
                updated_at
            "#,
        )
        .bind(transport_profile_id)
        .fetch_optional(&self.pool)
        .await?
        .ok_or_else(|| {
            AppError::NotFound(format!(
                "transport profile not found: {transport_profile_id}"
            ))
        })?;

        Ok(profile)
    }

    async fn attach_active_rollout_policy(
        &self,
        mut profiles: Vec<TransportProfileRecord>,
    ) -> Result<Vec<TransportProfileRecord>, AppError> {
        if profiles.is_empty() {
            return Ok(profiles);
        }

        let active_rollouts = sqlx::query_as::<_, ActiveChannelRolloutRow>(
            r#"
            SELECT DISTINCT ON (channel)
                channel,
                rollout_id
            FROM helix.rollout_batches
            WHERE desired_state = 'running'
            ORDER BY channel, published_at DESC
            "#,
        )
        .fetch_all(&self.pool)
        .await?;

        let channel_rollouts = active_rollouts
            .into_iter()
            .map(|row| (row.channel, row.rollout_id))
            .collect::<HashMap<_, _>>();

        let mut by_channel = HashMap::<String, Vec<usize>>::new();
        for (index, profile) in profiles.iter().enumerate() {
            by_channel
                .entry(profile.channel.clone())
                .or_default()
                .push(index);
        }

        for (channel, indexes) in by_channel {
            let Some(rollout_id) = channel_rollouts.get(&channel) else {
                continue;
            };
            let profile_ids = indexes
                .iter()
                .map(|index| profiles[*index].transport_profile_id.clone())
                .collect::<Vec<_>>();
            let evidence = self
                .fetch_runtime_evidence_by_profile(rollout_id, &profile_ids)
                .await?;
            let suppressions = self
                .fetch_active_suppression_windows(rollout_id, &profile_ids)
                .await?;

            for index in indexes {
                let profile = &mut profiles[index];
                let mut policy =
                    profile_policy_summary(evidence.get(&profile.transport_profile_id));
                if let Some(suppression) = suppressions.get(&profile.transport_profile_id) {
                    apply_active_suppression_window(&mut policy, suppression);
                }
                profile.policy = Some(policy);
            }
        }

        Ok(profiles)
    }

    async fn fetch_runtime_evidence_by_profile(
        &self,
        rollout_id: &str,
        profile_ids: &[String],
    ) -> Result<HashMap<String, RuntimeEvidenceRow>, AppError> {
        if profile_ids.is_empty() {
            return Ok(HashMap::new());
        }

        let rows = sqlx::query_as::<_, RuntimeEvidenceRow>(
            r#"
            SELECT
                transport_profile_id,
                COUNT(*) FILTER (WHERE event_kind = 'ready')::DOUBLE PRECISION AS ready_total,
                COUNT(*) FILTER (WHERE event_kind = 'fallback')::DOUBLE PRECISION AS fallback_total,
                COUNT(*) FILTER (
                    WHERE COALESCE((payload -> 'continuity' ->> 'continuity_grace_entries')::INT, 0) > 0
                       OR COALESCE((payload -> 'continuity' ->> 'successful_continuity_recovers')::INT, 0) > 0
                       OR COALESCE((payload -> 'continuity' ->> 'failed_continuity_recovers')::INT, 0) > 0
                       OR COALESCE((payload -> 'continuity' ->> 'successful_cross_route_recovers')::INT, 0) > 0
                       OR jsonb_typeof(payload -> 'recovery' -> 'same_route_recovered') = 'boolean'
                       OR (payload -> 'recovery' ->> 'ready_recovery_latency_ms') IS NOT NULL
                       OR (payload -> 'recovery' ->> 'proxy_ready_latency_ms') IS NOT NULL
                )::DOUBLE PRECISION AS continuity_total,
                COUNT(*) FILTER (
                    WHERE COALESCE((payload -> 'continuity' ->> 'successful_continuity_recovers')::INT, 0) > 0
                       OR COALESCE((payload -> 'continuity' ->> 'successful_cross_route_recovers')::INT, 0) > 0
                       OR (
                            event_kind = 'ready'
                            AND jsonb_typeof(payload -> 'recovery' -> 'same_route_recovered') = 'boolean'
                          )
                       OR COALESCE((payload -> 'recovery' ->> 'successful_cross_route_recovers')::INT, 0) > 0
                )::DOUBLE PRECISION AS continuity_success_total,
                COUNT(*) FILTER (
                    WHERE COALESCE((payload -> 'continuity' ->> 'successful_cross_route_recovers')::INT, 0) > 0
                       OR COALESCE((payload -> 'recovery' ->> 'successful_cross_route_recovers')::INT, 0) > 0
                       OR (
                            event_kind = 'ready'
                            AND jsonb_typeof(payload -> 'recovery' -> 'same_route_recovered') = 'boolean'
                            AND COALESCE((payload -> 'recovery' ->> 'same_route_recovered')::BOOLEAN, TRUE) = FALSE
                          )
                )::DOUBLE PRECISION AS cross_route_success_total
            FROM helix.desktop_runtime_events
            WHERE rollout_id = $1
              AND transport_profile_id = ANY($2)
            GROUP BY transport_profile_id
            "#,
        )
        .bind(rollout_id)
        .bind(profile_ids)
        .fetch_all(&self.pool)
        .await?;

        Ok(rows
            .into_iter()
            .map(|row| (row.transport_profile_id.clone(), row))
            .collect())
    }

    async fn fetch_active_suppression_windows(
        &self,
        rollout_id: &str,
        profile_ids: &[String],
    ) -> Result<HashMap<String, ActiveSuppressionWindowRow>, AppError> {
        if profile_ids.is_empty() {
            return Ok(HashMap::new());
        }

        let rows = sqlx::query_as::<_, ActiveSuppressionWindowRow>(
            r#"
            SELECT
                transport_profile_id,
                suppressed_until,
                suppression_reason,
                observation_count
            FROM helix.profile_suppression_windows
            WHERE rollout_id = $1
              AND transport_profile_id = ANY($2)
              AND suppressed_until > NOW()
            "#,
        )
        .bind(rollout_id)
        .bind(profile_ids)
        .fetch_all(&self.pool)
        .await?;

        Ok(rows
            .into_iter()
            .map(|row| (row.transport_profile_id.clone(), row))
            .collect())
    }
}

fn profile_policy_summary(evidence: Option<&RuntimeEvidenceRow>) -> TransportProfilePolicySummary {
    let totals = evidence.map_or(
        RuntimeEvidenceTotals {
            ready_total: 0.0,
            fallback_total: 0.0,
            continuity_total: 0.0,
            continuity_success_total: 0.0,
            cross_route_success_total: 0.0,
        },
        |row| RuntimeEvidenceTotals {
            ready_total: row.ready_total,
            fallback_total: row.fallback_total,
            continuity_total: row.continuity_total,
            continuity_success_total: row.continuity_success_total,
            cross_route_success_total: row.cross_route_success_total,
        },
    );

    profile_policy_summary_from_totals(totals)
}

pub fn profile_policy_summary_from_totals(
    totals: RuntimeEvidenceTotals,
) -> TransportProfilePolicySummary {
    let observed_events = (totals.ready_total + totals.fallback_total) as i32;
    let continuity_total = totals.continuity_total;
    let connect_success_rate = {
        let total = totals.ready_total + totals.fallback_total;
        if total == 0.0 {
            0.78
        } else {
            totals.ready_total / total
        }
    };
    let fallback_rate = {
        let total = totals.ready_total + totals.fallback_total;
        if total == 0.0 {
            0.08
        } else {
            totals.fallback_total / total
        }
    };
    let continuity_success_rate = if totals.continuity_total == 0.0 {
        0.72
    } else {
        totals.continuity_success_total / totals.continuity_total
    };
    let cross_route_recovery_rate = if totals.continuity_total == 0.0 {
        0.50
    } else {
        totals.cross_route_success_total / totals.continuity_total
    };
    let degraded = observed_events >= 4
        && (connect_success_rate < 0.75
            || fallback_rate > 0.20
            || (continuity_total >= 2.0 && continuity_success_rate < 0.70));
    let severely_degraded = observed_events >= 4
        && (connect_success_rate < 0.55
            || fallback_rate > 0.35
            || (continuity_total >= 2.0 && continuity_success_rate < 0.45));
    let mut policy_score = 0;
    policy_score += (connect_success_rate * 400.0).round() as i32;
    policy_score += ((1.0 - fallback_rate) * 250.0).round() as i32;
    policy_score += (continuity_success_rate * 250.0).round() as i32;
    policy_score += (cross_route_recovery_rate * 150.0).round() as i32;
    policy_score += observed_events.min(20) * 5;
    if degraded {
        policy_score -= 220;
    }
    if severely_degraded {
        policy_score -= 180;
    }

    let (advisory_state, recommended_action, selection_eligible) = if severely_degraded {
        (
            "avoid-new-sessions".to_string(),
            Some(
                "Pause new Helix manifest selection for this profile until continuity and fallback rates recover."
                    .to_string(),
            ),
            false,
        )
    } else if degraded {
        (
            "degraded".to_string(),
            Some(
                "Keep profile available only when healthier compatible options are unavailable and investigate rollout quality."
                    .to_string(),
            ),
            true,
        )
    } else if observed_events >= 2 && (fallback_rate > 0.12 || continuity_success_rate < 0.80) {
        (
            "watch".to_string(),
            Some(
                "Continue observing this profile; quality is acceptable but trending away from the preferred Helix target."
                    .to_string(),
            ),
            true,
        )
    } else {
        ("healthy".to_string(), None, true)
    };

    let mut policy = TransportProfilePolicySummary {
        observed_events,
        connect_success_rate,
        fallback_rate,
        continuity_success_rate,
        cross_route_recovery_rate,
        policy_score,
        degraded,
        advisory_state,
        recommended_action,
        selection_eligible,
        new_session_issuable: true,
        new_session_posture: "preferred".to_string(),
        suppression_window_active: false,
        suppression_reason: None,
        suppression_observation_count: 0,
        suppressed_until: None,
    };
    policy.new_session_issuable = is_new_session_policy_issuable(&policy);
    policy.new_session_posture = new_session_policy_posture(&policy).to_string();
    policy
}

fn apply_active_suppression_window(
    policy: &mut TransportProfilePolicySummary,
    suppression: &ActiveSuppressionWindowRow,
) {
    let suppression_penalty = 180 + suppression.observation_count.min(6) * 20;
    policy.suppression_window_active = true;
    policy.suppression_reason = Some(suppression.suppression_reason.clone());
    policy.suppression_observation_count = suppression.observation_count;
    policy.suppressed_until = Some(suppression.suppressed_until);
    policy.new_session_issuable = false;
    policy.new_session_posture = "blocked".to_string();
    policy.policy_score -= suppression_penalty;
    let suppression_reason = format!(
        "Adapter cooloff window remains active until {} UTC ({}, observations={})",
        suppression.suppressed_until.format("%Y-%m-%d %H:%M:%S"),
        suppression.suppression_reason,
        suppression.observation_count
    );
    policy.recommended_action = match policy.recommended_action.take() {
        Some(existing) => Some(format!("{existing} {suppression_reason}.")),
        None => Some(format!(
            "Keep this Helix profile out of new desktop sessions. {suppression_reason}."
        )),
    };
}
