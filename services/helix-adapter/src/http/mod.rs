pub mod routes;

use axum::Router;
use tower_http::trace::TraceLayer;

use crate::app_state::AppState;

pub fn build_router(state: AppState) -> Router {
    Router::new()
        .merge(routes::health::router())
        .nest("/internal", routes::internal::router())
        .nest("/admin", routes::admin::router())
        .layer(TraceLayer::new_for_http())
        .with_state(state)
}
