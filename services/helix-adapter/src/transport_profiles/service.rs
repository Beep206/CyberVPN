use crate::{
    error::AppError,
    manifests::model::SupportedTransportProfile,
    node_registry::model::RolloutChannel,
    transport_profiles::{
        model::{
            is_new_session_policy_issuable, validate_profile_request, TransportProfileRecord,
            UpsertTransportProfileRequest,
        },
        repository::TransportProfileRepository,
    },
};

#[derive(Debug, Clone)]
pub struct TransportProfileService {
    repository: TransportProfileRepository,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum ProfileSelectionTarget {
    DesktopNewSession,
    NodeAssignment,
}

impl TransportProfileService {
    pub fn new(repository: TransportProfileRepository) -> Self {
        Self { repository }
    }

    pub async fn list_profiles(&self) -> Result<Vec<TransportProfileRecord>, AppError> {
        self.repository.list_profiles().await
    }

    pub async fn upsert_profile(
        &self,
        request: UpsertTransportProfileRequest,
    ) -> Result<TransportProfileRecord, AppError> {
        validate_profile_request(&request)?;
        self.repository.upsert_profile(&request).await
    }

    pub async fn revoke_profile(
        &self,
        transport_profile_id: &str,
    ) -> Result<TransportProfileRecord, AppError> {
        if transport_profile_id.trim().is_empty() {
            return Err(AppError::BadRequest(
                "transport_profile_id must not be empty".to_string(),
            ));
        }

        self.repository.revoke_profile(transport_profile_id).await
    }

    pub async fn resolve_compatible_profile(
        &self,
        rollout_id: &str,
        channel: RolloutChannel,
        supported_protocol_versions: Option<&[i32]>,
        supported_transport_profiles: Option<&[SupportedTransportProfile]>,
    ) -> Result<TransportProfileRecord, AppError> {
        self.resolve_compatible_profile_for_target(
            rollout_id,
            channel,
            supported_protocol_versions,
            supported_transport_profiles,
            ProfileSelectionTarget::NodeAssignment,
            None,
        )
        .await
    }

    pub async fn resolve_compatible_profile_for_new_sessions(
        &self,
        rollout_id: &str,
        channel: RolloutChannel,
        supported_protocol_versions: Option<&[i32]>,
        supported_transport_profiles: Option<&[SupportedTransportProfile]>,
    ) -> Result<TransportProfileRecord, AppError> {
        self.resolve_compatible_profile_for_target(
            rollout_id,
            channel,
            supported_protocol_versions,
            supported_transport_profiles,
            ProfileSelectionTarget::DesktopNewSession,
            None,
        )
        .await
    }

    pub async fn resolve_compatible_profile_for_target(
        &self,
        rollout_id: &str,
        channel: RolloutChannel,
        supported_protocol_versions: Option<&[i32]>,
        supported_transport_profiles: Option<&[SupportedTransportProfile]>,
        target: ProfileSelectionTarget,
        preferred_transport_profile_id: Option<&str>,
    ) -> Result<TransportProfileRecord, AppError> {
        let candidates = self.repository.list_candidate_profiles(channel).await?;
        let candidates = self
            .repository
            .attach_policy_for_rollout(rollout_id, candidates)
            .await?;

        let compatible = candidates
            .into_iter()
            .filter(|candidate| {
                profile_matches(
                    candidate,
                    supported_protocol_versions,
                    supported_transport_profiles,
                )
            })
            .collect::<Vec<_>>();

        if let Some(preferred_transport_profile_id) = preferred_transport_profile_id {
            if let Some(preferred) = compatible
                .iter()
                .find(|candidate| candidate.transport_profile_id == preferred_transport_profile_id)
                .cloned()
            {
                let preferred_issuable = match target {
                    ProfileSelectionTarget::DesktopNewSession => {
                        is_new_session_issuable(&preferred)
                    }
                    ProfileSelectionTarget::NodeAssignment => is_selection_eligible(&preferred),
                };

                if preferred_issuable {
                    return Ok(preferred);
                }
            }
        }

        let profile = prioritize_candidates_for_target(compatible, target)
            .into_iter()
            .next()
            .ok_or_else(|| {
                AppError::NotFound(format!(
                    "no compatible transport profile available for channel: {channel}"
                ))
            })?;

        Ok(profile)
    }
}

pub fn prioritize_candidates(
    candidates: Vec<TransportProfileRecord>,
) -> Vec<TransportProfileRecord> {
    prioritize_candidates_for_target(candidates, ProfileSelectionTarget::NodeAssignment)
}

pub fn prioritize_candidates_for_target(
    candidates: Vec<TransportProfileRecord>,
    target: ProfileSelectionTarget,
) -> Vec<TransportProfileRecord> {
    let eligible = match target {
        ProfileSelectionTarget::DesktopNewSession => candidates
            .iter()
            .filter(|candidate| is_new_session_issuable(candidate))
            .cloned()
            .collect::<Vec<_>>(),
        ProfileSelectionTarget::NodeAssignment => candidates
            .iter()
            .filter(|candidate| is_selection_eligible(candidate))
            .cloned()
            .collect::<Vec<_>>(),
    };
    let eligible = if target == ProfileSelectionTarget::NodeAssignment && eligible.is_empty() {
        candidates
    } else {
        eligible
    };

    let mut preferred = match target {
        ProfileSelectionTarget::DesktopNewSession => {
            let healthy_or_watch = eligible
                .iter()
                .filter(|candidate| !is_degraded(candidate))
                .cloned()
                .collect::<Vec<_>>();
            if healthy_or_watch.is_empty() {
                eligible
            } else {
                healthy_or_watch
            }
        }
        ProfileSelectionTarget::NodeAssignment => {
            let healthy = eligible
                .iter()
                .filter(|candidate| !is_degraded(candidate))
                .cloned()
                .collect::<Vec<_>>();
            if healthy.is_empty() {
                eligible
            } else {
                healthy
            }
        }
    };

    preferred.sort_by(|left, right| {
        profile_selection_score(right)
            .cmp(&profile_selection_score(left))
            .then_with(|| status_rank(right).cmp(&status_rank(left)))
            .then_with(|| right.profile_version.cmp(&left.profile_version))
            .then_with(|| right.policy_version.cmp(&left.policy_version))
    });

    preferred
}

fn profile_selection_score(candidate: &TransportProfileRecord) -> i32 {
    let version_bias = candidate.profile_version * 25 + candidate.policy_version * 7;
    let status_bias = status_rank(candidate) * 75;
    let advisory_bias = advisory_rank(candidate) * 90;
    let policy_score = candidate
        .policy
        .as_ref()
        .map(|policy| policy.policy_score)
        .unwrap_or(0);

    version_bias + status_bias + advisory_bias + policy_score
}

fn status_rank(candidate: &TransportProfileRecord) -> i32 {
    match candidate.status.as_str() {
        "active" => 2,
        "deprecated" => 1,
        _ => 0,
    }
}

fn advisory_rank(candidate: &TransportProfileRecord) -> i32 {
    match candidate
        .policy
        .as_ref()
        .map(|policy| policy.advisory_state.as_str())
    {
        Some("healthy") => 3,
        Some("watch") => 2,
        Some("degraded") => 1,
        Some("avoid-new-sessions") => -2,
        _ => 0,
    }
}

fn is_selection_eligible(candidate: &TransportProfileRecord) -> bool {
    candidate
        .policy
        .as_ref()
        .map(|policy| policy.selection_eligible)
        .unwrap_or(true)
}

pub fn is_new_session_issuable(candidate: &TransportProfileRecord) -> bool {
    let Some(policy) = candidate.policy.as_ref() else {
        return true;
    };
    is_new_session_policy_issuable(policy)
}

fn is_degraded(candidate: &TransportProfileRecord) -> bool {
    candidate
        .policy
        .as_ref()
        .is_some_and(|policy| policy.degraded)
}

fn profile_matches(
    candidate: &TransportProfileRecord,
    supported_protocol_versions: Option<&[i32]>,
    supported_transport_profiles: Option<&[SupportedTransportProfile]>,
) -> bool {
    if let Some(protocol_versions) = supported_protocol_versions {
        if !protocol_versions.contains(&candidate.protocol_version) {
            return false;
        }
    }

    if let Some(supported_profiles) = supported_transport_profiles {
        return supported_profiles.iter().any(|supported| {
            supported.profile_family == candidate.profile_family
                && candidate.profile_version >= supported.min_transport_profile_version
                && candidate.profile_version <= supported.max_transport_profile_version
                && supported
                    .supported_policy_versions
                    .contains(&candidate.policy_version)
        });
    }

    true
}

#[cfg(test)]
mod tests {
    use chrono::Utc;

    use super::{advisory_rank, prioritize_candidates_for_target, ProfileSelectionTarget};
    use crate::transport_profiles::model::{TransportProfilePolicySummary, TransportProfileRecord};

    #[allow(clippy::too_many_arguments)]
    fn candidate(
        transport_profile_id: &str,
        profile_version: i32,
        policy_version: i32,
        advisory_state: &str,
        selection_eligible: bool,
        degraded: bool,
        fallback_rate: f64,
        continuity_success_rate: f64,
        cross_route_recovery_rate: f64,
    ) -> TransportProfileRecord {
        TransportProfileRecord {
            transport_profile_id: transport_profile_id.to_string(),
            channel: "lab".to_string(),
            profile_family: "edge-hybrid".to_string(),
            profile_version,
            policy_version,
            protocol_version: 1,
            session_mode: "hybrid".to_string(),
            status: "active".to_string(),
            fallback_core: "sing-box".to_string(),
            required_capabilities: vec!["protocol.v1".to_string()],
            compatibility_min_profile_version: 1,
            compatibility_max_profile_version: 4,
            startup_timeout_seconds: 20,
            runtime_unhealthy_threshold: 3,
            created_at: Utc::now(),
            updated_at: Utc::now(),
            policy: Some(TransportProfilePolicySummary {
                connect_success_rate: 1.0 - fallback_rate,
                fallback_rate,
                continuity_success_rate,
                cross_route_recovery_rate,
                policy_score: 600,
                degraded,
                advisory_state: advisory_state.to_string(),
                recommended_action: None,
                selection_eligible,
                observed_events: 8,
                new_session_issuable: selection_eligible
                    && (!degraded
                        || (continuity_success_rate >= 0.60
                            && fallback_rate <= 0.30
                            && cross_route_recovery_rate >= 0.35)),
                new_session_posture: match advisory_state {
                    "degraded" => "guarded".to_string(),
                    "watch" => "watch".to_string(),
                    "avoid-new-sessions" => "blocked".to_string(),
                    _ => "preferred".to_string(),
                },
                suppression_window_active: false,
                suppression_reason: None,
                suppression_observation_count: 0,
                suppressed_until: None,
            }),
        }
    }

    #[test]
    fn desktop_new_sessions_prefer_watch_over_degraded_even_when_degraded_is_newer() {
        let watch = candidate(
            "ptp-lab-edge-v2",
            2,
            4,
            "watch",
            true,
            false,
            0.10,
            0.79,
            0.52,
        );
        let degraded_newer = candidate(
            "ptp-lab-edge-v3",
            3,
            5,
            "degraded",
            true,
            true,
            0.26,
            0.66,
            0.40,
        );

        let prioritized = prioritize_candidates_for_target(
            vec![degraded_newer, watch.clone()],
            ProfileSelectionTarget::DesktopNewSession,
        );

        assert_eq!(
            prioritized[0].transport_profile_id,
            watch.transport_profile_id
        );
    }

    #[test]
    fn desktop_new_sessions_drop_degraded_profile_when_continuity_is_too_poor() {
        let degraded_only = candidate(
            "ptp-lab-edge-v3",
            3,
            5,
            "degraded",
            true,
            true,
            0.28,
            0.48,
            0.20,
        );

        let prioritized = prioritize_candidates_for_target(
            vec![degraded_only],
            ProfileSelectionTarget::DesktopNewSession,
        );

        assert!(prioritized.is_empty());
    }

    #[test]
    fn desktop_new_sessions_can_still_issue_degraded_profile_when_it_is_only_option_and_continuity_is_stable(
    ) {
        let degraded_only = candidate(
            "ptp-lab-edge-v3",
            3,
            5,
            "degraded",
            true,
            true,
            0.24,
            0.68,
            0.38,
        );

        let prioritized = prioritize_candidates_for_target(
            vec![degraded_only.clone()],
            ProfileSelectionTarget::DesktopNewSession,
        );

        assert_eq!(prioritized.len(), 1);
        assert_eq!(
            prioritized[0].transport_profile_id,
            degraded_only.transport_profile_id
        );
    }

    #[test]
    fn advisory_rank_orders_states_from_healthy_to_avoid_new_sessions() {
        let healthy = candidate(
            "ptp-lab-edge-v1",
            1,
            4,
            "healthy",
            true,
            false,
            0.08,
            0.84,
            0.55,
        );
        let degraded = candidate(
            "ptp-lab-edge-v2",
            2,
            5,
            "degraded",
            true,
            true,
            0.22,
            0.65,
            0.40,
        );
        let avoid = candidate(
            "ptp-lab-edge-v3",
            3,
            6,
            "avoid-new-sessions",
            false,
            true,
            0.42,
            0.32,
            0.12,
        );

        assert!(advisory_rank(&healthy) > advisory_rank(&degraded));
        assert!(advisory_rank(&degraded) > advisory_rank(&avoid));
    }
}
