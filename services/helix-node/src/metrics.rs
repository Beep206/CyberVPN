use std::sync::Arc;

use prometheus::{Encoder, IntCounter, IntGauge, Registry, TextEncoder};

use crate::error::AppError;

#[derive(Clone)]
pub struct Metrics {
    registry: Arc<Registry>,
    ready: IntGauge,
    runtime_healthy: IntGauge,
    assignment_apply_total: IntCounter,
    rollback_total: IntCounter,
}

impl Metrics {
    pub fn new(prefix: &str) -> Result<Self, AppError> {
        let registry = Registry::new();
        let ready = IntGauge::new(format!("{prefix}_ready").as_str(), "daemon readiness")
            .map_err(|error| AppError::Metrics(error.to_string()))?;
        let runtime_healthy = IntGauge::new(
            format!("{prefix}_runtime_healthy").as_str(),
            "runtime health state",
        )
        .map_err(|error| AppError::Metrics(error.to_string()))?;
        let assignment_apply_total = IntCounter::new(
            format!("{prefix}_assignment_apply_total").as_str(),
            "assignments applied successfully",
        )
        .map_err(|error| AppError::Metrics(error.to_string()))?;
        let rollback_total = IntCounter::new(
            format!("{prefix}_rollback_total").as_str(),
            "runtime rollbacks triggered",
        )
        .map_err(|error| AppError::Metrics(error.to_string()))?;

        registry
            .register(Box::new(ready.clone()))
            .map_err(|error| AppError::Metrics(error.to_string()))?;
        registry
            .register(Box::new(runtime_healthy.clone()))
            .map_err(|error| AppError::Metrics(error.to_string()))?;
        registry
            .register(Box::new(assignment_apply_total.clone()))
            .map_err(|error| AppError::Metrics(error.to_string()))?;
        registry
            .register(Box::new(rollback_total.clone()))
            .map_err(|error| AppError::Metrics(error.to_string()))?;

        Ok(Self {
            registry: Arc::new(registry),
            ready,
            runtime_healthy,
            assignment_apply_total,
            rollback_total,
        })
    }

    pub fn set_ready(&self, ready: bool) {
        self.ready.set(i64::from(ready));
    }

    pub fn set_runtime_healthy(&self, healthy: bool) {
        self.runtime_healthy.set(i64::from(healthy));
    }

    pub fn increment_assignment_apply(&self) {
        self.assignment_apply_total.inc();
    }

    pub fn increment_rollback(&self) {
        self.rollback_total.inc();
    }

    pub fn render(&self) -> Result<String, AppError> {
        let metric_families = self.registry.gather();
        let encoder = TextEncoder::new();
        let mut buffer = Vec::new();
        encoder
            .encode(&metric_families, &mut buffer)
            .map_err(|error| AppError::Metrics(error.to_string()))?;
        String::from_utf8(buffer).map_err(|error| AppError::Metrics(error.to_string()))
    }
}
