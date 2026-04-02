use std::time::Duration;

use chrono::{DateTime, Utc};
use serde::{Deserialize, Serialize};

use crate::{config::NodeConfig, error::AppError};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Signature {
    pub alg: String,
    pub key_id: String,
    pub sig: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct NodeAssignmentCompatibilityWindow {
    pub min_transport_profile_version: i32,
    pub max_transport_profile_version: i32,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct NodeAssignmentTransportProfile {
    pub transport_profile_id: String,
    pub profile_family: String,
    pub profile_version: i32,
    pub policy_version: i32,
    pub compatibility_window: NodeAssignmentCompatibilityWindow,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct NodeAssignmentRuntimeProfile {
    pub bundle_version: String,
    pub min_daemon_version: String,
    pub ports: Vec<u16>,
    pub health_check_interval_seconds: i32,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct NodeAssignmentCredentials {
    pub key_id: String,
    pub token: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct NodeAssignmentRecovery {
    pub last_known_good_bundle: String,
    pub rollback_timeout_seconds: i32,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct NodeAssignmentIntegrity {
    pub assignment_hash: String,
    pub signature: Signature,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct NodeAssignmentDocument {
    pub schema_version: String,
    pub assignment_id: String,
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

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct NodeHeartbeatTransportProfile {
    pub transport_profile_id: String,
    pub profile_family: String,
    pub profile_version: i32,
    pub policy_version: i32,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct NodeHeartbeatDaemon {
    pub version: String,
    pub instance_id: String,
    pub status: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct NodeHeartbeatBundle {
    pub active_version: String,
    pub pending_version: Option<String>,
    pub last_known_good_version: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct NodeHeartbeatHealth {
    pub ready: bool,
    pub runtime_healthy: bool,
    pub apply_state: String,
    pub latency_ms: i32,
    pub reason: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct NodeHeartbeatCounters {
    pub rollback_total: i32,
    pub apply_fail_total: i32,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct NodeHeartbeatDocument {
    pub schema_version: String,
    pub heartbeat_id: String,
    pub node_id: String,
    pub rollout_id: String,
    pub observed_at: DateTime<Utc>,
    pub transport_profile: NodeHeartbeatTransportProfile,
    pub daemon: NodeHeartbeatDaemon,
    pub bundle: NodeHeartbeatBundle,
    pub health: NodeHeartbeatHealth,
    pub counters: NodeHeartbeatCounters,
    pub capabilities: Vec<String>,
}

#[derive(Debug, Clone)]
pub struct ControlPlaneClient {
    base_url: String,
    token: String,
    node_id: String,
    client: reqwest::Client,
}

impl ControlPlaneClient {
    pub fn new(config: &NodeConfig) -> Result<Self, AppError> {
        let client = reqwest::Client::builder()
            .timeout(Duration::from_secs(10))
            .user_agent(format!(
                "{}/{}",
                env!("CARGO_PKG_NAME"),
                env!("CARGO_PKG_VERSION")
            ))
            .build()?;

        Ok(Self {
            base_url: config.adapter_url.trim_end_matches('/').to_string(),
            token: config.adapter_token.clone(),
            node_id: config.node_id.clone(),
            client,
        })
    }

    pub async fn fetch_assignment(&self) -> Result<NodeAssignmentDocument, AppError> {
        let response = self
            .client
            .get(format!(
                "{}/internal/nodes/{}/assignment",
                self.base_url, self.node_id
            ))
            .header("x-internal-token", &self.token)
            .send()
            .await?;

        if !response.status().is_success() {
            return Err(AppError::System(format!(
                "adapter assignment fetch failed with status {}",
                response.status()
            )));
        }

        response.json().await.map_err(AppError::Reqwest)
    }

    pub async fn send_heartbeat(&self, heartbeat: &NodeHeartbeatDocument) -> Result<(), AppError> {
        let response = self
            .client
            .post(format!(
                "{}/internal/nodes/{}/heartbeat",
                self.base_url, self.node_id
            ))
            .header("x-internal-token", &self.token)
            .json(heartbeat)
            .send()
            .await?;

        if !response.status().is_success() {
            return Err(AppError::System(format!(
                "adapter heartbeat ingest failed with status {}",
                response.status()
            )));
        }

        Ok(())
    }
}
