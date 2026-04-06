pub mod bundle_store;
pub mod health;
pub mod process_supervisor;
pub mod rollback;

use std::{path::PathBuf, sync::Arc, time::Duration};

use chrono::Utc;
use sha2::{Digest, Sha256};
use tokio::sync::RwLock;

use crate::{
    control_plane::client::{
        NodeAssignmentDocument, NodeHeartbeatBundle, NodeHeartbeatCounters, NodeHeartbeatDaemon,
        NodeHeartbeatDocument, NodeHeartbeatHealth, NodeHeartbeatTransportProfile,
    },
    error::AppError,
    metrics::Metrics,
    runtime::{
        bundle_store::BundleStore, health::await_runtime_health,
        process_supervisor::ProcessSupervisor, rollback::rollback_to_last_known_good,
    },
    state::NodeRuntimeSnapshot,
};

#[derive(Clone)]
pub struct RuntimeCoordinator {
    bundle_store: BundleStore,
    supervisor: ProcessSupervisor,
    snapshot: Arc<RwLock<NodeRuntimeSnapshot>>,
    node_id: String,
    instance_id: String,
    daemon_version: String,
}

impl RuntimeCoordinator {
    pub async fn new(
        state_dir: PathBuf,
        node_id: String,
        instance_id: String,
        daemon_version: String,
        allow_private_targets: bool,
    ) -> Result<Self, AppError> {
        let bundle_store = BundleStore::new(state_dir).await?;
        let snapshot = NodeRuntimeSnapshot::bootstrap(
            node_id.clone(),
            instance_id.clone(),
            daemon_version.clone(),
        );

        Ok(Self {
            bundle_store,
            supervisor: ProcessSupervisor::new(allow_private_targets),
            snapshot: Arc::new(RwLock::new(snapshot)),
            node_id,
            instance_id,
            daemon_version,
        })
    }

    pub async fn restore_state(&self) -> Result<NodeRuntimeSnapshot, AppError> {
        let restored = self
            .bundle_store
            .load_snapshot()
            .await?
            .unwrap_or_else(|| self.bootstrap_snapshot());
        *self.snapshot.write().await = restored.clone();
        self.bundle_store.save_snapshot(&restored).await?;
        Ok(restored)
    }

    pub async fn snapshot(&self) -> NodeRuntimeSnapshot {
        self.snapshot.read().await.clone()
    }

    pub async fn record_runtime_error(&self, message: String) -> Result<(), AppError> {
        let mut snapshot = self.snapshot.write().await;
        snapshot.apply_state = "failed".to_string();
        snapshot.ready = false;
        snapshot.runtime_healthy = false;
        snapshot.last_error = Some(message);
        snapshot.updated_at = Utc::now();
        self.bundle_store.save_snapshot(&snapshot).await?;
        Ok(())
    }

    pub async fn sync_assignment(
        &self,
        assignment: &NodeAssignmentDocument,
        metrics: &Metrics,
        health_gate_timeout_seconds: u64,
    ) -> Result<NodeRuntimeSnapshot, AppError> {
        let current = self.snapshot().await;
        let bundle_version = assignment.runtime_profile.bundle_version.clone();
        let runtime_fingerprint = assignment_runtime_fingerprint(assignment);
        let current_supervisor_bundle = self.supervisor.current_bundle().await;

        if assignment_matches_active_runtime(&current, assignment, &runtime_fingerprint)
            && current_supervisor_bundle.as_deref() == Some(bundle_version.as_str())
        {
            let steady_state = NodeRuntimeSnapshot {
                assignment_id: Some(assignment.assignment_id.clone()),
                runtime_fingerprint: Some(runtime_fingerprint.clone()),
                rollout_id: Some(assignment.rollout_id.clone()),
                transport_profile_id: Some(assignment.transport_profile.transport_profile_id.clone()),
                profile_family: Some(assignment.transport_profile.profile_family.clone()),
                profile_version: Some(assignment.transport_profile.profile_version),
                policy_version: Some(assignment.transport_profile.policy_version),
                active_bundle_version: Some(bundle_version),
                pending_bundle_version: None,
                desired_state: assignment.desired_state.clone(),
                apply_state: "idle".to_string(),
                ready: true,
                runtime_healthy: true,
                last_error: None,
                updated_at: Utc::now(),
                ..current
            };

            *self.snapshot.write().await = steady_state.clone();
            self.bundle_store.save_snapshot(&steady_state).await?;
            metrics.set_runtime_healthy(true);
            return Ok(steady_state);
        }

        self.bundle_store.stage_assignment(assignment).await?;

        let mut applying = current.clone();
        applying.assignment_id = Some(assignment.assignment_id.clone());
        applying.runtime_fingerprint = Some(runtime_fingerprint.clone());
        applying.rollout_id = Some(assignment.rollout_id.clone());
        applying.transport_profile_id =
            Some(assignment.transport_profile.transport_profile_id.clone());
        applying.profile_family = Some(assignment.transport_profile.profile_family.clone());
        applying.profile_version = Some(assignment.transport_profile.profile_version);
        applying.policy_version = Some(assignment.transport_profile.policy_version);
        applying.pending_bundle_version = Some(bundle_version.clone());
        applying.desired_state = assignment.desired_state.clone();
        applying.apply_state = "applying".to_string();
        applying.ready = false;
        applying.runtime_healthy = false;
        applying.last_error = None;
        applying.capabilities = default_capabilities(&assignment.transport_profile.profile_family);
        applying.updated_at = Utc::now();

        *self.snapshot.write().await = applying.clone();
        self.bundle_store.save_snapshot(&applying).await?;
        metrics.set_runtime_healthy(false);

        if assignment.desired_state != "active" {
            let mut paused = applying.clone();
            paused.pending_bundle_version = None;
            paused.apply_state = "idle".to_string();
            paused.last_known_good_bundle = current.last_known_good_bundle.clone();
            paused.updated_at = Utc::now();
            *self.snapshot.write().await = paused.clone();
            self.bundle_store.save_snapshot(&paused).await?;
            return Ok(paused);
        }

        if !daemon_version_satisfies(
            &self.daemon_version,
            &assignment.runtime_profile.min_daemon_version,
        )? {
            return self
                .handle_apply_failure(
                    &current,
                    assignment,
                    metrics,
                    format!(
                        "daemon version {} does not satisfy required minimum {}",
                        self.daemon_version, assignment.runtime_profile.min_daemon_version
                    ),
                )
                .await;
        }

        if let Err(error) = self.supervisor.apply(assignment).await {
            return self
                .handle_apply_failure(&current, assignment, metrics, error.to_string())
                .await;
        }

        if let Err(error) = await_runtime_health(
            &self.supervisor,
            assignment,
            Duration::from_secs(health_gate_timeout_seconds),
        )
        .await
        {
            return self
                .handle_apply_failure(&current, assignment, metrics, error.to_string())
                .await;
        }

        let successful = NodeRuntimeSnapshot {
            assignment_id: Some(assignment.assignment_id.clone()),
            runtime_fingerprint: Some(runtime_fingerprint.clone()),
            rollout_id: Some(assignment.rollout_id.clone()),
            transport_profile_id: Some(assignment.transport_profile.transport_profile_id.clone()),
            profile_family: Some(assignment.transport_profile.profile_family.clone()),
            profile_version: Some(assignment.transport_profile.profile_version),
            policy_version: Some(assignment.transport_profile.policy_version),
            active_bundle_version: Some(bundle_version.clone()),
            pending_bundle_version: None,
            last_known_good_bundle: Some(bundle_version),
            desired_state: assignment.desired_state.clone(),
            apply_state: "idle".to_string(),
            ready: true,
            runtime_healthy: true,
            last_error: None,
            capabilities: default_capabilities(&assignment.transport_profile.profile_family),
            updated_at: Utc::now(),
            ..current
        };

        *self.snapshot.write().await = successful.clone();
        self.bundle_store.save_snapshot(&successful).await?;
        metrics.increment_assignment_apply();
        metrics.set_runtime_healthy(true);

        Ok(successful)
    }

    pub fn supervisor(&self) -> ProcessSupervisor {
        self.supervisor.clone()
    }

    pub async fn build_heartbeat(
        &self,
        latency_ms: i32,
    ) -> Result<Option<NodeHeartbeatDocument>, AppError> {
        let snapshot = self.snapshot().await;

        let Some(rollout_id) = snapshot.rollout_id.clone() else {
            return Ok(None);
        };
        let Some(transport_profile_id) = snapshot.transport_profile_id.clone() else {
            return Ok(None);
        };
        let Some(profile_family) = snapshot.profile_family.clone() else {
            return Ok(None);
        };
        let Some(profile_version) = snapshot.profile_version else {
            return Ok(None);
        };
        let Some(policy_version) = snapshot.policy_version else {
            return Ok(None);
        };

        let active_version = snapshot
            .active_bundle_version
            .clone()
            .or_else(|| snapshot.pending_bundle_version.clone())
            .or_else(|| snapshot.last_known_good_bundle.clone())
            .unwrap_or_else(|| "bundle-bootstrap".to_string());
        let last_known_good_version = snapshot
            .last_known_good_bundle
            .clone()
            .unwrap_or_else(|| "bundle-bootstrap".to_string());
        let daemon_status = daemon_status_for(&snapshot).to_string();

        Ok(Some(NodeHeartbeatDocument {
            schema_version: "1.0".to_string(),
            heartbeat_id: uuid::Uuid::new_v4().to_string(),
            node_id: snapshot.node_id,
            rollout_id,
            observed_at: Utc::now(),
            transport_profile: NodeHeartbeatTransportProfile {
                transport_profile_id,
                profile_family: profile_family.clone(),
                profile_version,
                policy_version,
            },
            daemon: NodeHeartbeatDaemon {
                version: snapshot.daemon_version,
                instance_id: snapshot.instance_id,
                status: daemon_status,
            },
            bundle: NodeHeartbeatBundle {
                active_version,
                pending_version: snapshot.pending_bundle_version,
                last_known_good_version,
            },
            health: NodeHeartbeatHealth {
                ready: snapshot.ready,
                runtime_healthy: snapshot.runtime_healthy,
                apply_state: snapshot.apply_state,
                latency_ms,
                reason: snapshot.last_error,
            },
            counters: NodeHeartbeatCounters {
                rollback_total: i32::try_from(snapshot.rollback_total).map_err(|_| {
                    AppError::System("rollback_total exceeds supported heartbeat range".to_string())
                })?,
                apply_fail_total: i32::try_from(snapshot.apply_fail_total).map_err(|_| {
                    AppError::System(
                        "apply_fail_total exceeds supported heartbeat range".to_string(),
                    )
                })?,
            },
            capabilities: if snapshot.capabilities.is_empty() {
                default_capabilities(&profile_family)
            } else {
                snapshot.capabilities
            },
        }))
    }

    fn bootstrap_snapshot(&self) -> NodeRuntimeSnapshot {
        NodeRuntimeSnapshot::bootstrap(
            self.node_id.clone(),
            self.instance_id.clone(),
            self.daemon_version.clone(),
        )
    }

    async fn handle_apply_failure(
        &self,
        current: &NodeRuntimeSnapshot,
        assignment: &NodeAssignmentDocument,
        metrics: &Metrics,
        error_message: String,
    ) -> Result<NodeRuntimeSnapshot, AppError> {
        let rollback_target = current
            .last_known_good_bundle
            .clone()
            .unwrap_or_else(|| assignment.recovery.last_known_good_bundle.clone());
        let runtime_fingerprint = assignment_runtime_fingerprint(assignment);

        let failed_snapshot = NodeRuntimeSnapshot {
            assignment_id: Some(assignment.assignment_id.clone()),
            runtime_fingerprint: Some(runtime_fingerprint),
            rollout_id: Some(assignment.rollout_id.clone()),
            transport_profile_id: Some(assignment.transport_profile.transport_profile_id.clone()),
            profile_family: Some(assignment.transport_profile.profile_family.clone()),
            profile_version: Some(assignment.transport_profile.profile_version),
            policy_version: Some(assignment.transport_profile.policy_version),
            pending_bundle_version: Some(assignment.runtime_profile.bundle_version.clone()),
            desired_state: assignment.desired_state.clone(),
            apply_state: "failed".to_string(),
            ready: false,
            runtime_healthy: false,
            rollback_total: current.rollback_total + 1,
            apply_fail_total: current.apply_fail_total + 1,
            capabilities: default_capabilities(&assignment.transport_profile.profile_family),
            last_error: Some(error_message),
            updated_at: Utc::now(),
            ..current.clone()
        };

        let rolled_back = rollback_to_last_known_good(
            &self.bundle_store,
            &self.supervisor,
            &failed_snapshot,
            &rollback_target,
        )
        .await?;

        *self.snapshot.write().await = rolled_back.clone();
        metrics.increment_rollback();
        metrics.set_runtime_healthy(rolled_back.runtime_healthy);
        Ok(rolled_back)
    }
}

fn daemon_version_satisfies(current: &str, minimum: &str) -> Result<bool, AppError> {
    Ok(parse_semver_like(current)? >= parse_semver_like(minimum)?)
}

fn parse_semver_like(value: &str) -> Result<(u32, u32, u32), AppError> {
    let trimmed = value.trim_start_matches('v');
    let mut parts = trimmed.split('.');
    let major = parts
        .next()
        .ok_or_else(|| AppError::System(format!("invalid version: {value}")))?
        .parse::<u32>()
        .map_err(|_| AppError::System(format!("invalid version: {value}")))?;
    let minor = parts
        .next()
        .ok_or_else(|| AppError::System(format!("invalid version: {value}")))?
        .parse::<u32>()
        .map_err(|_| AppError::System(format!("invalid version: {value}")))?;
    let patch = parts
        .next()
        .ok_or_else(|| AppError::System(format!("invalid version: {value}")))?
        .parse::<u32>()
        .map_err(|_| AppError::System(format!("invalid version: {value}")))?;

    Ok((major, minor, patch))
}

fn daemon_status_for(snapshot: &NodeRuntimeSnapshot) -> &'static str {
    match snapshot.apply_state.as_str() {
        "applying" => "starting",
        "rolled-back" => "rollback",
        _ if snapshot.ready && snapshot.runtime_healthy => "ready",
        _ => "degraded",
    }
}

fn default_capabilities(profile_family: &str) -> Vec<String> {
    vec![
        "protocol.v1".to_string(),
        "runtime.rollback".to_string(),
        "metrics.prometheus".to_string(),
        format!("profile.{profile_family}"),
    ]
}

fn assignment_matches_active_runtime(
    current: &NodeRuntimeSnapshot,
    assignment: &NodeAssignmentDocument,
    runtime_fingerprint: &str,
) -> bool {
    current.ready
        && current.runtime_healthy
        && current.runtime_fingerprint.as_deref() == Some(runtime_fingerprint)
        && current.desired_state == assignment.desired_state
        && current.rollout_id.as_deref() == Some(assignment.rollout_id.as_str())
        && current.transport_profile_id.as_deref()
            == Some(assignment.transport_profile.transport_profile_id.as_str())
        && current.profile_family.as_deref()
            == Some(assignment.transport_profile.profile_family.as_str())
        && current.profile_version == Some(assignment.transport_profile.profile_version)
        && current.policy_version == Some(assignment.transport_profile.policy_version)
        && current.active_bundle_version.as_deref()
            == Some(assignment.runtime_profile.bundle_version.as_str())
}

fn assignment_runtime_fingerprint(assignment: &NodeAssignmentDocument) -> String {
    let ports = assignment
        .runtime_profile
        .ports
        .iter()
        .map(u16::to_string)
        .collect::<Vec<_>>()
        .join(",");
    let material = format!(
        "desired_state={}|transport_profile_id={}|profile_family={}|profile_version={}|policy_version={}|bundle_version={}|min_daemon_version={}|ports={}|health_check_interval_seconds={}|credential_key_id={}|credential_token={}",
        assignment.desired_state,
        assignment.transport_profile.transport_profile_id,
        assignment.transport_profile.profile_family,
        assignment.transport_profile.profile_version,
        assignment.transport_profile.policy_version,
        assignment.runtime_profile.bundle_version,
        assignment.runtime_profile.min_daemon_version,
        ports,
        assignment.runtime_profile.health_check_interval_seconds,
        assignment.credentials.key_id,
        assignment.credentials.token,
    );
    let digest = Sha256::digest(material.as_bytes());
    format!("sha256:{digest:x}")
}
