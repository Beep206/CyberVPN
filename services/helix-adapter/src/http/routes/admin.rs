use axum::{
    extract::{Path, State},
    http::HeaderMap,
    routing::{get, post},
    Json, Router,
};
use serde::Serialize;
use uuid::Uuid;

use crate::{
    app_state::AppState,
    error::AppError,
    node_registry::model::{NodeRegistryRecord, PublishRolloutBatchRequest, RolloutBatchRecord},
    transport_profiles::model::{TransportProfileRecord, UpsertTransportProfileRequest},
};

#[derive(Debug, Serialize)]
struct AdminPingResponse {
    status: &'static str,
    endpoint: &'static str,
}

pub fn router() -> Router<AppState> {
    Router::new()
        .route("/ping", get(ping))
        .route("/nodes", get(list_nodes))
        .route("/rollouts", post(publish_rollout))
        .route("/rollouts/{rollout_id}/pause", post(pause_rollout))
        .route("/transport-profiles", get(list_transport_profiles))
        .route("/transport-profiles", post(upsert_transport_profile))
        .route(
            "/transport-profiles/{transport_profile_id}/revoke",
            post(revoke_transport_profile),
        )
        .route(
            "/manifests/{manifest_version_id}/revoke",
            post(revoke_manifest),
        )
}

async fn ping(
    State(state): State<AppState>,
    headers: HeaderMap,
) -> Result<Json<AdminPingResponse>, AppError> {
    authorize(&headers, &state)?;
    state.metrics.increment_admin_requests();

    Ok(Json(AdminPingResponse {
        status: "ok",
        endpoint: "admin",
    }))
}

async fn list_nodes(
    State(state): State<AppState>,
    headers: HeaderMap,
) -> Result<Json<Vec<NodeRegistryRecord>>, AppError> {
    authorize(&headers, &state)?;
    state.metrics.increment_admin_requests();
    Ok(Json(state.node_registry_service.list_nodes(true).await?))
}

async fn publish_rollout(
    State(state): State<AppState>,
    headers: HeaderMap,
    Json(request): Json<PublishRolloutBatchRequest>,
) -> Result<Json<RolloutBatchRecord>, AppError> {
    authorize(&headers, &state)?;
    state.metrics.increment_admin_requests();

    let rollout = state.node_registry_service.publish_rollout(request).await?;
    state.metrics.increment_rollout_published();

    Ok(Json(rollout))
}

async fn list_transport_profiles(
    State(state): State<AppState>,
    headers: HeaderMap,
) -> Result<Json<Vec<TransportProfileRecord>>, AppError> {
    authorize(&headers, &state)?;
    state.metrics.increment_admin_requests();
    Ok(Json(state.transport_profile_service.list_profiles().await?))
}

async fn upsert_transport_profile(
    State(state): State<AppState>,
    headers: HeaderMap,
    Json(request): Json<UpsertTransportProfileRequest>,
) -> Result<Json<TransportProfileRecord>, AppError> {
    authorize(&headers, &state)?;
    state.metrics.increment_admin_requests();
    Ok(Json(
        state
            .transport_profile_service
            .upsert_profile(request)
            .await?,
    ))
}

async fn pause_rollout(
    State(state): State<AppState>,
    headers: HeaderMap,
    Path(rollout_id): Path<String>,
) -> Result<Json<RolloutBatchRecord>, AppError> {
    authorize(&headers, &state)?;
    state.metrics.increment_admin_requests();
    Ok(Json(
        state
            .node_registry_service
            .pause_rollout(&rollout_id)
            .await?,
    ))
}

async fn revoke_transport_profile(
    State(state): State<AppState>,
    headers: HeaderMap,
    Path(transport_profile_id): Path<String>,
) -> Result<Json<TransportProfileRecord>, AppError> {
    authorize(&headers, &state)?;
    state.metrics.increment_admin_requests();
    Ok(Json(
        state
            .transport_profile_service
            .revoke_profile(&transport_profile_id)
            .await?,
    ))
}

async fn revoke_manifest(
    State(state): State<AppState>,
    headers: HeaderMap,
    Path(manifest_version_id): Path<Uuid>,
) -> Result<Json<crate::manifests::model::ManifestVersionRecord>, AppError> {
    authorize(&headers, &state)?;
    state.metrics.increment_admin_requests();
    Ok(Json(
        state
            .manifest_store
            .revoke_manifest(manifest_version_id)
            .await?,
    ))
}

fn authorize(headers: &HeaderMap, state: &AppState) -> Result<(), AppError> {
    let token = headers
        .get("x-internal-token")
        .and_then(|value| value.to_str().ok())
        .ok_or(AppError::Unauthorized)?;

    if token == state.config.internal_auth_token {
        return Ok(());
    }

    Err(AppError::Unauthorized)
}
