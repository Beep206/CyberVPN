use std::{net::SocketAddr, sync::Arc, time::Duration};

use helix_runtime::{spawn_server, ServerConfig, ServerHandle};
use tokio::sync::Mutex;

use crate::{control_plane::client::NodeAssignmentDocument, error::AppError};

#[derive(Debug, Default)]
struct FailureModes {
    apply_bundle: Option<String>,
    unhealthy_bundle: Option<String>,
}

#[derive(Debug, Clone)]
pub struct ProcessSupervisor {
    current_bundle: Arc<Mutex<Option<String>>>,
    current_server: Arc<Mutex<Option<ServerHandle>>>,
    failure_modes: Arc<Mutex<FailureModes>>,
    allow_private_targets: bool,
}

impl ProcessSupervisor {
    pub fn new(allow_private_targets: bool) -> Self {
        Self {
            current_bundle: Arc::new(Mutex::new(None)),
            current_server: Arc::new(Mutex::new(None)),
            failure_modes: Arc::new(Mutex::new(FailureModes::default())),
            allow_private_targets,
        }
    }

    pub async fn apply(&self, assignment: &NodeAssignmentDocument) -> Result<(), AppError> {
        let bundle_version = assignment.runtime_profile.bundle_version.clone();
        let mut failure_modes = self.failure_modes.lock().await;

        if failure_modes.apply_bundle.as_deref() == Some(bundle_version.as_str()) {
            failure_modes.apply_bundle = None;
            return Err(AppError::System(format!(
                "simulated apply failure for bundle {}",
                bundle_version
            )));
        }
        drop(failure_modes);

        if assignment.runtime_profile.ports.is_empty() {
            return Err(AppError::System(
                "assignment runtime profile must include at least one port".to_string(),
            ));
        }

        self.stop_current_server().await;
        let bind_addrs = assignment
            .runtime_profile
            .ports
            .iter()
            .map(|port| SocketAddr::from(([0, 0, 0, 0], *port)))
            .collect::<Vec<_>>();

        let server = spawn_server(ServerConfig {
            bind_addrs,
            transport_profile_id: assignment.transport_profile.transport_profile_id.clone(),
            profile_family: assignment.transport_profile.profile_family.clone(),
            profile_version: assignment.transport_profile.profile_version,
            policy_version: assignment.transport_profile.policy_version,
            session_mode: session_mode_for_profile(&assignment.transport_profile.profile_family),
            token: assignment.credentials.token.clone(),
            heartbeat_timeout: Duration::from_secs(
                u64::try_from(
                    assignment
                        .runtime_profile
                        .health_check_interval_seconds
                        .max(5),
                )
                .unwrap_or(5),
            ),
            allow_private_targets: self.allow_private_targets,
        })
        .await?;

        *self.current_server.lock().await = Some(server);
        *self.current_bundle.lock().await = Some(bundle_version);
        Ok(())
    }

    pub async fn ensure_healthy(
        &self,
        bundle_version: &str,
        timeout: Duration,
    ) -> Result<(), AppError> {
        let mut failure_modes = self.failure_modes.lock().await;
        if failure_modes.unhealthy_bundle.as_deref() == Some(bundle_version) {
            failure_modes.unhealthy_bundle = None;
            tokio::time::sleep(timeout.min(Duration::from_millis(100))).await;
            return Err(AppError::System(format!(
                "simulated health gate failure for bundle {}",
                bundle_version
            )));
        }
        drop(failure_modes);

        let deadline = tokio::time::Instant::now() + timeout;
        loop {
            let healthy = {
                let bundle_matches = self.current_bundle().await.as_deref() == Some(bundle_version);
                let server = self.current_server.lock().await.clone();
                if let Some(server) = server {
                    let snapshot = server.snapshot().await;
                    bundle_matches && snapshot.ready && !snapshot.bound_addrs.is_empty()
                } else {
                    false
                }
            };

            if healthy {
                return Ok(());
            }

            if tokio::time::Instant::now() >= deadline {
                return Err(AppError::System(format!(
                    "runtime health gate timed out for bundle {}",
                    bundle_version
                )));
            }

            tokio::time::sleep(Duration::from_millis(25)).await;
        }
    }

    pub async fn rollback(
        &self,
        bundle_version: &str,
        assignment: Option<&NodeAssignmentDocument>,
    ) -> Result<(), AppError> {
        self.stop_current_server().await;

        if let Some(assignment) = assignment {
            let bind_addrs = assignment
                .runtime_profile
                .ports
                .iter()
                .map(|port| SocketAddr::from(([0, 0, 0, 0], *port)))
                .collect::<Vec<_>>();
            let server = spawn_server(ServerConfig {
                bind_addrs,
                transport_profile_id: assignment.transport_profile.transport_profile_id.clone(),
                profile_family: assignment.transport_profile.profile_family.clone(),
                profile_version: assignment.transport_profile.profile_version,
                policy_version: assignment.transport_profile.policy_version,
                session_mode: session_mode_for_profile(
                    &assignment.transport_profile.profile_family,
                ),
                token: assignment.credentials.token.clone(),
                heartbeat_timeout: Duration::from_secs(
                    u64::try_from(
                        assignment
                            .runtime_profile
                            .health_check_interval_seconds
                            .max(5),
                    )
                    .unwrap_or(5),
                ),
                allow_private_targets: self.allow_private_targets,
            })
            .await?;
            *self.current_server.lock().await = Some(server);
        }

        *self.current_bundle.lock().await = if assignment.is_some() {
            Some(bundle_version.to_string())
        } else {
            None
        };
        Ok(())
    }

    pub async fn current_bundle(&self) -> Option<String> {
        self.current_bundle.lock().await.clone()
    }

    pub async fn shutdown(&self) {
        self.stop_current_server().await;
        *self.current_bundle.lock().await = None;
    }

    async fn stop_current_server(&self) {
        if let Some(server) = self.current_server.lock().await.take() {
            server.shutdown().await;
        }
    }

    pub async fn force_apply_failure_for_tests(&self, bundle_version: impl Into<String>) {
        self.failure_modes.lock().await.apply_bundle = Some(bundle_version.into());
    }

    pub async fn force_unhealthy_bundle_for_tests(&self, bundle_version: impl Into<String>) {
        self.failure_modes.lock().await.unhealthy_bundle = Some(bundle_version.into());
    }
}

impl Default for ProcessSupervisor {
    fn default() -> Self {
        Self::new(false)
    }
}

fn session_mode_for_profile(profile_family: &str) -> String {
    if profile_family.contains("stateful") {
        "stateful".to_string()
    } else {
        "hybrid".to_string()
    }
}
