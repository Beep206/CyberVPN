use chrono::{Duration, Utc};
use sqlx::PgPool;
use uuid::Uuid;

use crate::{
    assignments::model::{
        NodeAssignmentCompatibilityWindow, NodeAssignmentCredentials, NodeAssignmentDocument,
        NodeAssignmentIntegrity, NodeAssignmentRecovery, NodeAssignmentRuntimeProfile,
        NodeAssignmentTransportProfile, UnsignedNodeAssignmentDocument,
    },
    error::AppError,
    manifests::signer::ManifestSigner,
    node_registry::{model::RolloutChannel, repository::NodeRegistryRepository},
    session_credentials::derive_rollout_session_token,
    transport_profiles::{model::TransportProfileRecord, service::TransportProfileService},
};

const NODE_ASSIGNMENT_TTL_SECONDS: i64 = 10_800;
const MIN_DAEMON_VERSION: &str = "v0.1.0";

#[derive(Debug, Clone)]
pub struct NodeAssignmentStore {
    _pool: PgPool,
    node_repository: NodeRegistryRepository,
    transport_profile_service: TransportProfileService,
    signer: ManifestSigner,
}

impl NodeAssignmentStore {
    pub fn new(
        pool: PgPool,
        node_repository: NodeRegistryRepository,
        transport_profile_service: TransportProfileService,
        signer: ManifestSigner,
    ) -> Self {
        Self {
            _pool: pool,
            node_repository,
            transport_profile_service,
            signer,
        }
    }

    pub async fn resolve_node_assignment(
        &self,
        node_id: &str,
    ) -> Result<NodeAssignmentDocument, AppError> {
        if node_id.trim().is_empty() {
            return Err(AppError::BadRequest(
                "node_id must not be empty".to_string(),
            ));
        }

        let node = self
            .node_repository
            .find_node_by_remnawave_id(node_id)
            .await?;
        if !node.transport_enabled {
            return Err(AppError::NotFound(format!(
                "node is not transport-enabled: {node_id}"
            )));
        }

        let channel: RolloutChannel = node.rollout_channel.parse()?;
        let rollout = if let Some(active_rollout_id) = node.active_rollout_id.as_deref() {
            self.node_repository
                .find_rollout_by_id(active_rollout_id)
                .await?
        } else {
            self.node_repository
                .find_active_rollout_by_channel(channel.as_str())
                .await?
        };
        let active_actuation = self
            .node_repository
            .fetch_active_rollout_actuation(&rollout.rollout_id)
            .await?;

        let profile = self
            .transport_profile_service
            .resolve_compatible_profile_for_target(
                &rollout.rollout_id,
                channel,
                None,
                None,
                crate::transport_profiles::service::ProfileSelectionTarget::NodeAssignment,
                active_actuation
                    .as_ref()
                    .and_then(|actuation| {
                        (actuation.reaction == "rotate-profile-now")
                            .then_some(actuation.target_transport_profile_id.as_deref())
                    })
                    .flatten(),
            )
            .await?;

        let issued_at = Utc::now();
        let unsigned_assignment = UnsignedNodeAssignmentDocument {
            schema_version: "1.1",
            assignment_id: Uuid::new_v4(),
            rollout_id: rollout.rollout_id.clone(),
            node_id: node.remnawave_node_id,
            channel: rollout.channel.clone(),
            issued_at,
            expires_at: issued_at + Duration::seconds(NODE_ASSIGNMENT_TTL_SECONDS),
            desired_state: desired_state(&rollout.desired_state).to_string(),
            transport_profile: NodeAssignmentTransportProfile {
                transport_profile_id: profile.transport_profile_id.clone(),
                profile_family: profile.profile_family.clone(),
                profile_version: profile.profile_version,
                policy_version: profile.policy_version,
                compatibility_window: NodeAssignmentCompatibilityWindow {
                    min_transport_profile_version: profile.compatibility_min_profile_version,
                    max_transport_profile_version: profile.compatibility_max_profile_version,
                },
            },
            runtime_profile: NodeAssignmentRuntimeProfile {
                bundle_version: format!(
                    "{}-{}",
                    rollout.manifest_version, profile.transport_profile_id
                ),
                min_daemon_version: MIN_DAEMON_VERSION.to_string(),
                ports: runtime_ports(node.transport_port, &profile, channel),
                health_check_interval_seconds: health_check_interval(&profile),
            },
            credentials: NodeAssignmentCredentials {
                key_id: self.signer.key_id().to_string(),
                token: derive_rollout_session_token(
                    &rollout.rollout_id,
                    &profile.transport_profile_id,
                    self.signer.key_id(),
                ),
            },
            recovery: NodeAssignmentRecovery {
                last_known_good_bundle: self
                    .node_repository
                    .get_last_known_good_bundle(&rollout.rollout_id, node_id)
                    .await?
                    .unwrap_or_else(|| "bundle-bootstrap".to_string()),
                rollback_timeout_seconds: rollback_timeout(&profile),
            },
        };

        let payload = serde_json::to_vec(&unsigned_assignment)?;
        let (assignment_hash, signature) = self.signer.sign_bytes(&payload)?;
        let assignment = NodeAssignmentDocument {
            schema_version: unsigned_assignment.schema_version,
            assignment_id: unsigned_assignment.assignment_id,
            rollout_id: unsigned_assignment.rollout_id,
            node_id: unsigned_assignment.node_id,
            channel: unsigned_assignment.channel,
            issued_at: unsigned_assignment.issued_at,
            expires_at: unsigned_assignment.expires_at,
            desired_state: unsigned_assignment.desired_state,
            transport_profile: unsigned_assignment.transport_profile,
            runtime_profile: unsigned_assignment.runtime_profile,
            credentials: unsigned_assignment.credentials,
            recovery: unsigned_assignment.recovery,
            integrity: NodeAssignmentIntegrity {
                assignment_hash,
                signature,
            },
        };

        self.signer.verify_bytes(
            &payload,
            &assignment.integrity.assignment_hash,
            &assignment.integrity.signature,
        )?;

        Ok(assignment)
    }
}

fn desired_state(state: &str) -> &'static str {
    match state {
        "paused" => "paused",
        "revoked" => "revoked",
        _ => "active",
    }
}

fn runtime_ports(
    transport_port: Option<i32>,
    profile: &TransportProfileRecord,
    channel: RolloutChannel,
) -> Vec<u16> {
    let mut ports = vec![443];
    if profile.profile_family == "edge-hybrid" {
        ports.push(8443);
    }
    if channel == RolloutChannel::Lab {
        ports.push(
            transport_port
                .and_then(|port| u16::try_from(port).ok())
                .unwrap_or(9443),
        );
    }
    ports
}

fn health_check_interval(profile: &TransportProfileRecord) -> i32 {
    (profile.startup_timeout_seconds / 2).clamp(15, 60)
}

fn rollback_timeout(profile: &TransportProfileRecord) -> i32 {
    (profile.startup_timeout_seconds * 3).clamp(30, 600)
}
