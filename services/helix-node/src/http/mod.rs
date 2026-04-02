use axum::{routing::get, Router};

use crate::{
    http::routes::{healthz, metrics, readyz},
    state::AppState,
};

pub mod routes;

pub fn build_router(state: AppState) -> Router {
    Router::new()
        .route("/healthz", get(healthz))
        .route("/readyz", get(readyz))
        .route("/metrics", get(metrics))
        .with_state(state)
}
