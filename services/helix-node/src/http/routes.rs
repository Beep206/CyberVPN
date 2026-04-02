use axum::{extract::State, http::StatusCode, response::IntoResponse, Json};
use serde::Serialize;

use crate::state::AppState;

#[derive(Debug, Serialize)]
pub struct HealthResponse {
    status: &'static str,
    ready: bool,
    runtime_healthy: bool,
    active_bundle_version: Option<String>,
    apply_state: String,
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
