use axum::{body::Body, http::Request, routing::get, Router};
use sentry_tower::NewSentryLayer;
use tower::ServiceBuilder;
use tower_http::trace::TraceLayer;

use crate::{
    http::routes::{healthz, metrics, readyz, sentry_contract},
    state::AppState,
};

pub mod routes;

pub fn build_router(state: AppState) -> Router {
    Router::new()
        .route("/healthz", get(healthz))
        .route("/readyz", get(readyz))
        .route("/metrics", get(metrics))
        .route("/observability/sentry-contract", get(sentry_contract))
        .layer(
            ServiceBuilder::new()
                .layer(NewSentryLayer::<Request<Body>>::new_from_top())
                .layer(TraceLayer::new_for_http()),
        )
        .with_state(state)
}
