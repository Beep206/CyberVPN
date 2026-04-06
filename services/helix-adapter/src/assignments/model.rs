use chrono::{DateTime, Utc};
use serde::Serialize;
use uuid::Uuid;

use crate::manifests::model::ManifestSignature;

#[derive(Debug, Clone, Serialize)]
pub struct NodeAssignmentCompatibilityWindow {
    pub min_transport_profile_version: i32,
    pub max_transport_profile_version: i32,
}

#[derive(Debug, Clone, Serialize)]
pub struct NodeAssignmentTransportProfile {
    pub transport_profile_id: String,
    pub profile_family: String,
    pub profile_version: i32,
    pub policy_version: i32,
    pub compatibility_window: NodeAssignmentCompatibilityWindow,
}

#[derive(Debug, Clone, Serialize)]
pub struct NodeAssignmentRuntimeProfile {
    pub bundle_version: String,
    pub min_daemon_version: String,
    pub ports: Vec<u16>,
    pub health_check_interval_seconds: i32,
}

#[derive(Debug, Clone, Serialize)]
pub struct NodeAssignmentCredentials {
    pub key_id: String,
    pub token: String,
}

#[derive(Debug, Clone, Serialize)]
pub struct NodeAssignmentRecovery {
    pub last_known_good_bundle: String,
    pub rollback_timeout_seconds: i32,
}

#[derive(Debug, Clone, Serialize)]
pub struct NodeAssignmentIntegrity {
    pub assignment_hash: String,
    pub signature: ManifestSignature,
}

#[derive(Debug, Clone, Serialize)]
pub struct UnsignedNodeAssignmentDocument {
    pub schema_version: &'static str,
    pub assignment_id: Uuid,
    pub rollout_id: String,
    pub node_id: String,
    pub channel: String,
    pub issued_at: DateTime<Utc>,
    pub expires_at: DateTime<Utc>,
    pub desired_state: String,
    pub transport_profile: NodeAssignmentTransportProfile,
    pub runtime_profile: NodeAssignmentRuntimeProfile,
    pub credentials: NodeAssignmentCredentials,
    pub recovery: NodeAssignmentRecovery,
}

#[derive(Debug, Clone, Serialize)]
pub struct NodeAssignmentDocument {
    pub schema_version: &'static str,
    pub assignment_id: Uuid,
    pub rollout_id: String,
    pub node_id: String,
    pub channel: String,
    pub issued_at: DateTime<Utc>,
    pub expires_at: DateTime<Utc>,
    pub desired_state: String,
    pub transport_profile: NodeAssignmentTransportProfile,
    pub runtime_profile: NodeAssignmentRuntimeProfile,
    pub credentials: NodeAssignmentCredentials,
    pub recovery: NodeAssignmentRecovery,
    pub integrity: NodeAssignmentIntegrity,
}
