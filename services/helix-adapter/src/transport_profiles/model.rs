use chrono::{DateTime, Utc};
use serde::{Deserialize, Serialize};
use sqlx::FromRow;

use crate::{error::AppError, node_registry::model::RolloutChannel};

#[derive(Debug, Clone, Copy, Serialize, Deserialize, PartialEq, Eq)]
#[serde(rename_all = "lowercase")]
pub enum TransportProfileStatus {
    Active,
    Deprecated,
    Revoked,
}

impl TransportProfileStatus {
    pub fn as_str(self) -> &'static str {
        match self {
            Self::Active => "active",
            Self::Deprecated => "deprecated",
            Self::Revoked => "revoked",
        }
    }
}

#[derive(Debug, Clone, Serialize, Deserialize, FromRow)]
pub struct TransportProfileRecord {
    pub transport_profile_id: String,
    pub channel: String,
    pub profile_family: String,
    pub profile_version: i32,
    pub policy_version: i32,
    pub protocol_version: i32,
    pub session_mode: String,
    pub status: String,
    pub fallback_core: String,
    pub required_capabilities: Vec<String>,
    pub compatibility_min_profile_version: i32,
    pub compatibility_max_profile_version: i32,
    pub startup_timeout_seconds: i32,
    pub runtime_unhealthy_threshold: i32,
    pub created_at: DateTime<Utc>,
    pub updated_at: DateTime<Utc>,
    #[sqlx(skip)]
    #[serde(skip_serializing_if = "Option::is_none")]
    pub policy: Option<TransportProfilePolicySummary>,
}

#[derive(Debug, Clone, Default, Serialize, Deserialize)]
pub struct TransportProfilePolicySummary {
    pub observed_events: i32,
    pub connect_success_rate: f64,
    pub fallback_rate: f64,
    pub continuity_success_rate: f64,
    pub cross_route_recovery_rate: f64,
    pub policy_score: i32,
    pub degraded: bool,
    pub advisory_state: String,
    pub recommended_action: Option<String>,
    pub selection_eligible: bool,
    pub new_session_issuable: bool,
    pub new_session_posture: String,
    pub suppression_window_active: bool,
    pub suppression_reason: Option<String>,
    pub suppression_observation_count: i32,
    pub suppressed_until: Option<DateTime<Utc>>,
}

pub fn is_new_session_policy_issuable(policy: &TransportProfilePolicySummary) -> bool {
    if !policy.selection_eligible {
        return false;
    }

    match policy.advisory_state.as_str() {
        "avoid-new-sessions" => false,
        "degraded" => {
            policy.continuity_success_rate >= 0.60
                && policy.fallback_rate <= 0.30
                && (policy.observed_events < 6 || policy.cross_route_recovery_rate >= 0.35)
        }
        _ => true,
    }
}

pub fn new_session_policy_posture(policy: &TransportProfilePolicySummary) -> &'static str {
    if !policy.new_session_issuable {
        return "blocked";
    }

    match policy.advisory_state.as_str() {
        "degraded" => "guarded",
        "watch" => "watch",
        _ => "preferred",
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct UpsertTransportProfileRequest {
    pub transport_profile_id: String,
    pub channel: RolloutChannel,
    pub profile_family: String,
    pub profile_version: i32,
    pub policy_version: i32,
    pub protocol_version: i32,
    pub session_mode: String,
    pub status: TransportProfileStatus,
    pub fallback_core: String,
    pub required_capabilities: Vec<String>,
    pub compatibility_min_profile_version: i32,
    pub compatibility_max_profile_version: i32,
    pub startup_timeout_seconds: i32,
    pub runtime_unhealthy_threshold: i32,
}

pub fn validate_profile_request(request: &UpsertTransportProfileRequest) -> Result<(), AppError> {
    if !request.transport_profile_id.starts_with("ptp-") {
        return Err(AppError::BadRequest(
            "transport_profile_id must start with `ptp-`".to_string(),
        ));
    }

    if request.profile_family.trim().is_empty() {
        return Err(AppError::BadRequest(
            "profile_family must not be empty".to_string(),
        ));
    }

    if request.profile_version < 1 || request.policy_version < 1 || request.protocol_version < 1 {
        return Err(AppError::BadRequest(
            "profile_version, policy_version, and protocol_version must be >= 1".to_string(),
        ));
    }

    if !matches!(request.session_mode.as_str(), "stateful" | "hybrid") {
        return Err(AppError::BadRequest(
            "session_mode must be `stateful` or `hybrid`".to_string(),
        ));
    }

    if !matches!(request.fallback_core.as_str(), "sing-box" | "xray") {
        return Err(AppError::BadRequest(
            "fallback_core must be `sing-box` or `xray`".to_string(),
        ));
    }

    if request.required_capabilities.is_empty() {
        return Err(AppError::BadRequest(
            "required_capabilities must not be empty".to_string(),
        ));
    }

    if request.compatibility_min_profile_version > request.compatibility_max_profile_version {
        return Err(AppError::BadRequest(
            "compatibility_min_profile_version must be <= compatibility_max_profile_version"
                .to_string(),
        ));
    }

    if request.startup_timeout_seconds < 5 || request.startup_timeout_seconds > 120 {
        return Err(AppError::BadRequest(
            "startup_timeout_seconds must be between 5 and 120".to_string(),
        ));
    }

    if request.runtime_unhealthy_threshold < 1 || request.runtime_unhealthy_threshold > 10 {
        return Err(AppError::BadRequest(
            "runtime_unhealthy_threshold must be between 1 and 10".to_string(),
        ));
    }

    Ok(())
}
