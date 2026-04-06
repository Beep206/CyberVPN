use chrono::Utc;

use crate::{
    error::AppError,
    runtime::{bundle_store::BundleStore, process_supervisor::ProcessSupervisor},
    state::NodeRuntimeSnapshot,
};

pub async fn rollback_to_last_known_good(
    bundle_store: &BundleStore,
    supervisor: &ProcessSupervisor,
    snapshot: &NodeRuntimeSnapshot,
    rollback_target: &str,
) -> Result<NodeRuntimeSnapshot, AppError> {
    let rollback_assignment = if rollback_target == "bundle-bootstrap" {
        None
    } else {
        bundle_store.load_assignment(rollback_target).await?
    };

    if rollback_target != "bundle-bootstrap" && rollback_assignment.is_none() {
        return Err(AppError::System(format!(
            "rollback target bundle is unavailable locally: {}",
            rollback_target
        )));
    }

    supervisor
        .rollback(rollback_target, rollback_assignment.as_ref())
        .await?;

    let healthy_after_rollback = rollback_target != "bundle-bootstrap";
    let rolled_back = NodeRuntimeSnapshot {
        active_bundle_version: if healthy_after_rollback {
            Some(rollback_target.to_string())
        } else {
            None
        },
        pending_bundle_version: None,
        last_known_good_bundle: Some(rollback_target.to_string()),
        apply_state: "rolled-back".to_string(),
        ready: healthy_after_rollback,
        runtime_healthy: healthy_after_rollback,
        updated_at: Utc::now(),
        ..snapshot.clone()
    };

    bundle_store.save_snapshot(&rolled_back).await?;
    Ok(rolled_back)
}
