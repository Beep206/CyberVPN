use axum::{
    extract::State,
    http::{HeaderMap, StatusCode},
    routing::get,
    Json, Router,
};
use serde::Serialize;

use crate::{
    app_state::AppState,
    error::AppError,
    observability::{is_observability_authorized, sentry_contract, RUNTIME_SURFACE, SERVICE_NAME},
};

#[derive(Debug, Serialize)]
struct HealthResponse {
    status: &'static str,
    service: &'static str,
    environment: String,
}

#[derive(Debug, Serialize)]
struct SentryContractResponse {
    runtime_surface: &'static str,
    service: &'static str,
    environment: String,
    release: String,
    dsn_configured: bool,
}

pub fn router() -> Router<AppState> {
    Router::new()
        .route("/healthz", get(healthz))
        .route("/readyz", get(readyz))
        .route("/metrics", get(metrics))
        .route(
            "/observability/sentry-contract",
            get(sentry_runtime_contract),
        )
}

async fn healthz(State(state): State<AppState>) -> Json<HealthResponse> {
    state.metrics.increment_health_requests();
    Json(HealthResponse {
        status: "ok",
        service: SERVICE_NAME,
        environment: state.config.environment.clone(),
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
            service: SERVICE_NAME,
            environment: state.config.environment.clone(),
        }),
    )
}

async fn metrics(State(state): State<AppState>) -> Result<String, AppError> {
    state.metrics.increment_health_requests();
    state.metrics.render()
}

async fn sentry_runtime_contract(
    State(state): State<AppState>,
    headers: HeaderMap,
) -> Result<Json<SentryContractResponse>, StatusCode> {
    state.metrics.increment_health_requests();

    let provided_secret = headers
        .get("x-observability-secret")
        .and_then(|value| value.to_str().ok());

    if !is_observability_authorized(&state.config.observability_internal_secret, provided_secret) {
        return Err(StatusCode::FORBIDDEN);
    }

    let snapshot = sentry_contract(&state.config);

    Ok(Json(SentryContractResponse {
        runtime_surface: RUNTIME_SURFACE,
        service: snapshot.service,
        environment: snapshot.environment,
        release: snapshot.release,
        dsn_configured: snapshot.dsn_configured,
    }))
}
