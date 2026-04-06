use std::time::Duration;

use crate::{
    control_plane::client::NodeAssignmentDocument, error::AppError,
    runtime::process_supervisor::ProcessSupervisor,
};

pub async fn await_runtime_health(
    supervisor: &ProcessSupervisor,
    assignment: &NodeAssignmentDocument,
    timeout: Duration,
) -> Result<(), AppError> {
    supervisor
        .ensure_healthy(&assignment.runtime_profile.bundle_version, timeout)
        .await
}
