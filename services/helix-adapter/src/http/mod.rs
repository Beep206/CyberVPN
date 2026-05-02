pub mod routes;

use axum::{body::Body, http::Request, Router};
use sentry_tower::NewSentryLayer;
use tower::ServiceBuilder;
use tower_http::trace::TraceLayer;

use crate::app_state::AppState;

pub fn build_router(state: AppState) -> Router {
    Router::new()
        .merge(routes::health::router())
        .nest("/internal", routes::internal::router())
        .nest("/admin", routes::admin::router())
        .layer(
            ServiceBuilder::new()
                .layer(NewSentryLayer::<Request<Body>>::new_from_top())
                .layer(TraceLayer::new_for_http()),
        )
        .with_state(state)
}
