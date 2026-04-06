use std::sync::{
    atomic::{AtomicBool, Ordering},
    Arc,
};

use crate::{
    assignments::store::NodeAssignmentStore,
    config::AdapterConfig,
    manifests::store::ManifestStore,
    metrics::Metrics,
    node_registry::{model::RolloutChannel, service::NodeRegistryService},
    transport_profiles::service::TransportProfileService,
};

#[derive(Clone)]
pub struct AppState {
    pub config: Arc<AdapterConfig>,
    pub metrics: Arc<Metrics>,
    pub node_registry_service: NodeRegistryService,
    pub transport_profile_service: TransportProfileService,
    pub manifest_store: ManifestStore,
    pub assignment_store: NodeAssignmentStore,
    readiness: Arc<AtomicBool>,
}

impl AppState {
    pub fn new(
        config: AdapterConfig,
        metrics: Metrics,
        node_registry_service: NodeRegistryService,
        transport_profile_service: TransportProfileService,
        manifest_store: ManifestStore,
        assignment_store: NodeAssignmentStore,
    ) -> Self {
        Self {
            config: Arc::new(config),
            metrics: Arc::new(metrics),
            node_registry_service,
            transport_profile_service,
            manifest_store,
            assignment_store,
            readiness: Arc::new(AtomicBool::new(true)),
        }
    }

    pub fn is_ready(&self) -> bool {
        self.readiness.load(Ordering::Relaxed)
    }

    pub fn set_ready(&self, value: bool) {
        self.readiness.store(value, Ordering::Relaxed);
        self.metrics.set_ready(value);
    }

    pub fn default_rollout_channel(&self) -> Result<RolloutChannel, crate::error::AppError> {
        self.config.default_rollout_channel.parse()
    }
}
