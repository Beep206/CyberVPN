use axum::{extract::State, http::StatusCode, routing::get, Json, Router};
use serde::Serialize;

use crate::{app_state::AppState, error::AppError};

#[derive(Debug, Serialize)]
struct HealthResponse {
    status: &'static str,
    service: &'static str,
}

pub fn router() -> Router<AppState> {
    Router::new()
        .route("/healthz", get(healthz))
        .route("/readyz", get(readyz))
        .route("/metrics", get(metrics))
}

async fn healthz(State(state): State<AppState>) -> Json<HealthResponse> {
    state.metrics.increment_health_requests();
    Json(HealthResponse {
        status: "ok",
        service: "helix-adapter",
    })
}

async fn readyz(State(state): State<AppState>) -> (StatusCode, Json<HealthResponse>) {
    state.metrics.increment_health_requests();
    let ready = state.is_ready();

    (
        if ready {
            StatusCode::OK
        } else {
            StatusCode::SERVICE_UNAVAILABLE
        },
        Json(HealthResponse {
            status: if ready { "ready" } else { "not-ready" },
            service: "helix-adapter",
        }),
    )
}

async fn metrics(State(state): State<AppState>) -> Result<String, AppError> {
    state.metrics.increment_health_requests();
    state.metrics.render()
}
