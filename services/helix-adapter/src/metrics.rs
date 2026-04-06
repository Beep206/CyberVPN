use prometheus::{Encoder, IntCounter, IntGauge, Registry, TextEncoder};

use crate::error::AppError;

#[derive(Debug)]
pub struct Metrics {
    registry: Registry,
    health_requests_total: IntCounter,
    internal_requests_total: IntCounter,
    admin_requests_total: IntCounter,
    manifest_issued_total: IntCounter,
    rollout_published_total: IntCounter,
    node_heartbeat_ingested_total: IntCounter,
    desktop_runtime_event_ingested_total: IntCounter,
    readiness: IntGauge,
}

impl Metrics {
    pub fn new(prefix: &str) -> Result<Self, AppError> {
        let registry = Registry::new_custom(Some(prefix.to_string()), None)
            .map_err(|error| AppError::Internal(error.to_string()))?;

        let health_requests_total = IntCounter::new(
            "health_requests_total",
            "Total number of health and metrics endpoint requests",
        )
        .map_err(|error| AppError::Internal(error.to_string()))?;
        let internal_requests_total = IntCounter::new(
            "internal_requests_total",
            "Total number of internal API requests",
        )
        .map_err(|error| AppError::Internal(error.to_string()))?;
        let admin_requests_total =
            IntCounter::new("admin_requests_total", "Total number of admin API requests")
                .map_err(|error| AppError::Internal(error.to_string()))?;
        let manifest_issued_total = IntCounter::new(
            "manifest_issued_total",
            "Total number of manifests issued by the adapter",
        )
        .map_err(|error| AppError::Internal(error.to_string()))?;
        let rollout_published_total = IntCounter::new(
            "rollout_published_total",
            "Total number of rollout publish operations",
        )
        .map_err(|error| AppError::Internal(error.to_string()))?;
        let node_heartbeat_ingested_total = IntCounter::new(
            "node_heartbeat_ingested_total",
            "Total number of node heartbeat snapshots ingested by the adapter",
        )
        .map_err(|error| AppError::Internal(error.to_string()))?;
        let desktop_runtime_event_ingested_total = IntCounter::new(
            "desktop_runtime_event_ingested_total",
            "Total number of desktop runtime events ingested by the adapter",
        )
        .map_err(|error| AppError::Internal(error.to_string()))?;
        let readiness = IntGauge::new("adapter_ready", "Readiness status of the adapter")
            .map_err(|error| AppError::Internal(error.to_string()))?;

        registry
            .register(Box::new(health_requests_total.clone()))
            .map_err(|error| AppError::Internal(error.to_string()))?;
        registry
            .register(Box::new(internal_requests_total.clone()))
            .map_err(|error| AppError::Internal(error.to_string()))?;
        registry
            .register(Box::new(admin_requests_total.clone()))
            .map_err(|error| AppError::Internal(error.to_string()))?;
        registry
            .register(Box::new(manifest_issued_total.clone()))
            .map_err(|error| AppError::Internal(error.to_string()))?;
        registry
            .register(Box::new(rollout_published_total.clone()))
            .map_err(|error| AppError::Internal(error.to_string()))?;
        registry
            .register(Box::new(node_heartbeat_ingested_total.clone()))
            .map_err(|error| AppError::Internal(error.to_string()))?;
        registry
            .register(Box::new(desktop_runtime_event_ingested_total.clone()))
            .map_err(|error| AppError::Internal(error.to_string()))?;
        registry
            .register(Box::new(readiness.clone()))
            .map_err(|error| AppError::Internal(error.to_string()))?;

        readiness.set(1);

        Ok(Self {
            registry,
            health_requests_total,
            internal_requests_total,
            admin_requests_total,
            manifest_issued_total,
            rollout_published_total,
            node_heartbeat_ingested_total,
            desktop_runtime_event_ingested_total,
            readiness,
        })
    }

    pub fn increment_health_requests(&self) {
        self.health_requests_total.inc();
    }

    pub fn increment_internal_requests(&self) {
        self.internal_requests_total.inc();
    }

    pub fn increment_admin_requests(&self) {
        self.admin_requests_total.inc();
    }

    pub fn increment_manifest_issued(&self) {
        self.manifest_issued_total.inc();
    }

    pub fn increment_rollout_published(&self) {
        self.rollout_published_total.inc();
    }

    pub fn increment_node_heartbeat_ingested(&self) {
        self.node_heartbeat_ingested_total.inc();
    }

    pub fn increment_desktop_runtime_event_ingested(&self) {
        self.desktop_runtime_event_ingested_total.inc();
    }

    pub fn set_ready(&self, value: bool) {
        self.readiness.set(i64::from(value));
    }

    pub fn render(&self) -> Result<String, AppError> {
        let metric_families = self.registry.gather();
        let encoder = TextEncoder::new();
        let mut buffer = Vec::new();
        encoder
            .encode(&metric_families, &mut buffer)
            .map_err(|error| AppError::Internal(error.to_string()))?;

        String::from_utf8(buffer).map_err(|error| AppError::Internal(error.to_string()))
    }
}
