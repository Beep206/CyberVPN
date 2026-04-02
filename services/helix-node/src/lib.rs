pub mod config;
pub mod control_plane;
pub mod error;
pub mod http;
pub mod metrics;
pub mod runtime;
pub mod state;

use std::time::{Duration, Instant};

use tracing::{error, info, warn};

use crate::{
    config::NodeConfig, control_plane::client::ControlPlaneClient, error::AppError,
    metrics::Metrics, runtime::RuntimeCoordinator, state::AppState,
};

pub async fn build_state(config: NodeConfig) -> Result<AppState, AppError> {
    let metrics = Metrics::new(&config.metrics_prefix)?;
    let client = ControlPlaneClient::new(&config)?;
    let runtime = RuntimeCoordinator::new(
        config.state_dir.clone(),
        config.node_id.clone(),
        config.instance_id.clone(),
        config.daemon_version.clone(),
        config.allow_private_targets,
    )
    .await?;

    runtime.restore_state().await?;

    Ok(AppState::new(config, metrics, client, runtime))
}

pub fn build_app(state: AppState) -> axum::Router {
    http::build_router(state)
}

pub fn spawn_control_loop(state: AppState) {
    tokio::spawn(async move {
        loop {
            let poll_interval = Duration::from_secs(state.config.assignment_poll_interval_seconds);

            match state.control_plane_client.fetch_assignment().await {
                Ok(assignment) => {
                    let cycle_started_at = Instant::now();
                    match state
                        .runtime
                        .sync_assignment(
                            &assignment,
                            &state.metrics,
                            state.config.health_gate_timeout_seconds,
                        )
                        .await
                    {
                        Ok(snapshot) => {
                            state.set_ready(snapshot.ready);
                            info!(
                                node_id = %snapshot.node_id,
                                active_bundle = ?snapshot.active_bundle_version,
                                apply_state = %snapshot.apply_state,
                                "Helix node assignment synchronized"
                            );
                        }
                        Err(error) => {
                            error!(?error, "failed to synchronize Helix assignment");
                            if let Err(record_error) = state
                                .runtime
                                .record_runtime_error(format!("assignment sync failed: {error}"))
                                .await
                            {
                                error!(?record_error, "failed to persist assignment sync error");
                            }
                            state.metrics.set_runtime_healthy(false);
                            state.set_ready(false);
                        }
                    }

                    let latency_ms =
                        i32::try_from(cycle_started_at.elapsed().as_millis()).unwrap_or(i32::MAX);
                    match state.runtime.build_heartbeat(latency_ms).await {
                        Ok(Some(heartbeat)) => {
                            if let Err(error) =
                                state.control_plane_client.send_heartbeat(&heartbeat).await
                            {
                                warn!(?error, "failed to send node heartbeat");
                            }
                        }
                        Ok(None) => {}
                        Err(error) => {
                            warn!(?error, "failed to build node heartbeat");
                        }
                    }
                }
                Err(error) => {
                    warn!(?error, "control-plane assignment fetch failed");
                    if let Err(record_error) = state
                        .runtime
                        .record_runtime_error(format!("control-plane fetch failed: {error}"))
                        .await
                    {
                        error!(?record_error, "failed to persist control-plane error");
                    }
                    state.metrics.set_runtime_healthy(false);
                    state.set_ready(false);
                }
            }

            tokio::time::sleep(poll_interval).await;
        }
    });
}
