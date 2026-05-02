use axum::{
    extract::State,
    http::{HeaderMap, StatusCode},
    response::IntoResponse,
    Json,
};
use serde::Serialize;

use crate::{
    observability::{is_observability_authorized, sentry_contract as sentry_contract_snapshot},
    state::AppState,
};

#[derive(Debug, Serialize)]
pub struct HealthResponse {
    status: &'static str,
    service: &'static str,
    environment: String,
    node_id: String,
    ready: bool,
    runtime_healthy: bool,
    active_bundle_version: Option<String>,
    apply_state: String,
}

#[derive(Debug, Serialize)]
pub struct SentryContractResponse {
    runtime_surface: &'static str,
    service: &'static str,
    environment: String,
    release: String,
    dsn_configured: bool,
    node_id: String,
    daemon_version: String,
}

pub async fn healthz(State(state): State<AppState>) -> impl IntoResponse {
    let snapshot = state.runtime.snapshot().await;

    (
        StatusCode::OK,
        Json(HealthResponse {
            status: if snapshot.runtime_healthy {
                "ok"
            } else {
                "degraded"
            },
            service: "helix-node",
            environment: state.config.environment.clone(),
            node_id: snapshot.node_id,
            ready: snapshot.ready,
            runtime_healthy: snapshot.runtime_healthy,
            active_bundle_version: snapshot.active_bundle_version,
            apply_state: snapshot.apply_state,
        }),
    )
}

pub async fn readyz(State(state): State<AppState>) -> impl IntoResponse {
    if state.is_ready() {
        return StatusCode::OK;
    }

    StatusCode::SERVICE_UNAVAILABLE
}

pub async fn metrics(State(state): State<AppState>) -> impl IntoResponse {
    match state.metrics.render() {
        Ok(payload) => (
            StatusCode::OK,
            [("content-type", "text/plain; version=0.0.4")],
            payload,
        )
            .into_response(),
        Err(error) => (
            StatusCode::INTERNAL_SERVER_ERROR,
            [("content-type", "text/plain; charset=utf-8")],
            error.to_string(),
        )
            .into_response(),
    }
}

pub async fn sentry_contract(
    State(state): State<AppState>,
    headers: HeaderMap,
) -> Result<Json<SentryContractResponse>, StatusCode> {
    let provided_secret = headers
        .get("x-observability-secret")
        .and_then(|value| value.to_str().ok());

    if !is_observability_authorized(&state.config.observability_internal_secret, provided_secret) {
        return Err(StatusCode::FORBIDDEN);
    }

    let snapshot = sentry_contract_snapshot(&state.config);

    Ok(Json(SentryContractResponse {
        runtime_surface: snapshot.runtime_surface,
        service: snapshot.service,
        environment: snapshot.environment,
        release: snapshot.release,
        dsn_configured: snapshot.dsn_configured,
        node_id: snapshot.node_id,
        daemon_version: snapshot.daemon_version,
    }))
}
