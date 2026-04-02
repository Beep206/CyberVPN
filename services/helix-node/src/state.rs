use std::sync::{
    atomic::{AtomicBool, Ordering},
    Arc,
};

use chrono::{DateTime, Utc};
use serde::Serialize;

use crate::{
    config::NodeConfig, control_plane::client::ControlPlaneClient, metrics::Metrics,
    runtime::RuntimeCoordinator,
};

#[derive(Debug, Clone, Serialize, serde::Deserialize)]
pub struct NodeRuntimeSnapshot {
    pub instance_id: String,
    pub node_id: String,
    pub daemon_version: String,
    pub assignment_id: Option<String>,
    pub runtime_fingerprint: Option<String>,
    pub rollout_id: Option<String>,
    pub transport_profile_id: Option<String>,
    pub profile_family: Option<String>,
    pub profile_version: Option<i32>,
    pub policy_version: Option<i32>,
    pub active_bundle_version: Option<String>,
    pub pending_bundle_version: Option<String>,
    pub last_known_good_bundle: Option<String>,
    pub desired_state: String,
    pub apply_state: String,
    pub ready: bool,
    pub runtime_healthy: bool,
    pub rollback_total: u64,
    pub apply_fail_total: u64,
    pub capabilities: Vec<String>,
    pub last_error: Option<String>,
    pub updated_at: DateTime<Utc>,
}

impl NodeRuntimeSnapshot {
    pub fn bootstrap(node_id: String, instance_id: String, daemon_version: String) -> Self {
        Self {
            instance_id,
            node_id,
            daemon_version,
            assignment_id: None,
            runtime_fingerprint: None,
            rollout_id: None,
            transport_profile_id: None,
            profile_family: None,
            profile_version: None,
            policy_version: None,
            active_bundle_version: None,
            pending_bundle_version: None,
            last_known_good_bundle: None,
            desired_state: "active".to_string(),
            apply_state: "idle".to_string(),
            ready: false,
            runtime_healthy: false,
            rollback_total: 0,
            apply_fail_total: 0,
            capabilities: Vec::new(),
            last_error: None,
            updated_at: Utc::now(),
        }
    }
}

#[derive(Clone)]
pub struct AppState {
    pub config: Arc<NodeConfig>,
    pub metrics: Arc<Metrics>,
    pub control_plane_client: Arc<ControlPlaneClient>,
    pub runtime: Arc<RuntimeCoordinator>,
    readiness: Arc<AtomicBool>,
}

impl AppState {
    pub fn new(
        config: NodeConfig,
        metrics: Metrics,
        control_plane_client: ControlPlaneClient,
        runtime: RuntimeCoordinator,
    ) -> Self {
        Self {
            config: Arc::new(config),
            metrics: Arc::new(metrics),
            control_plane_client: Arc::new(control_plane_client),
            runtime: Arc::new(runtime),
            readiness: Arc::new(AtomicBool::new(false)),
        }
    }

    pub fn is_ready(&self) -> bool {
        self.readiness.load(Ordering::Relaxed)
    }

    pub fn set_ready(&self, ready: bool) {
        self.readiness.store(ready, Ordering::Relaxed);
        self.metrics.set_ready(ready);
    }
}
