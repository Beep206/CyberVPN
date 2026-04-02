use axum::{
    extract::{Path, State},
    http::{HeaderMap, StatusCode},
    routing::{get, post},
    Json, Router,
};
use serde::Serialize;

use crate::{
    app_state::AppState,
    assignments::model::NodeAssignmentDocument,
    error::AppError,
    manifests::model::{ClientCapabilityDefaults, ResolveManifestRequest, ResolveManifestResponse},
    node_registry::model::{
        DesktopRuntimeEventAck, DesktopRuntimeEventRequest, NodeHeartbeatRequest,
        RolloutCanaryEvidenceResponse, RolloutStateResponse,
    },
};

#[derive(Debug, Serialize)]
struct InternalPingResponse {
    status: &'static str,
    endpoint: &'static str,
}

pub fn router() -> Router<AppState> {
    Router::new()
        .route("/ping", get(ping))
        .route("/manifests/resolve", post(resolve_manifest))
        .route("/rollouts/{rollout_id}/status", get(rollout_status))
        .route(
            "/rollouts/{rollout_id}/canary-evidence",
            get(rollout_canary_evidence),
        )
        .route("/nodes/{node_id}/assignment", get(node_assignment))
        .route("/nodes/{node_id}/heartbeat", post(node_heartbeat))
        .route("/desktop/runtime-events", post(desktop_runtime_event))
        .route(
            "/client-capabilities/defaults",
            get(client_capability_defaults),
        )
}

async fn ping(
    State(state): State<AppState>,
    headers: HeaderMap,
) -> Result<Json<InternalPingResponse>, AppError> {
    authorize(&headers, &state)?;
    state.metrics.increment_internal_requests();

    Ok(Json(InternalPingResponse {
        status: "ok",
        endpoint: "internal",
    }))
}

async fn resolve_manifest(
    State(state): State<AppState>,
    headers: HeaderMap,
    Json(request): Json<ResolveManifestRequest>,
) -> Result<Json<ResolveManifestResponse>, AppError> {
    authorize(&headers, &state)?;
    state.metrics.increment_internal_requests();

    let response = state
        .manifest_store
        .resolve_manifest(
            request,
            state.default_rollout_channel()?,
            state.config.manifest_ttl_seconds,
        )
        .await?;
    state.metrics.increment_manifest_issued();

    Ok(Json(response))
}

async fn rollout_status(
    State(state): State<AppState>,
    headers: HeaderMap,
    Path(rollout_id): Path<String>,
) -> Result<Json<RolloutStateResponse>, AppError> {
    authorize(&headers, &state)?;
    state.metrics.increment_internal_requests();
    Ok(Json(
        state
            .node_registry_service
            .rollout_state(&rollout_id)
            .await?,
    ))
}

async fn rollout_canary_evidence(
    State(state): State<AppState>,
    headers: HeaderMap,
    Path(rollout_id): Path<String>,
) -> Result<Json<RolloutCanaryEvidenceResponse>, AppError> {
    authorize(&headers, &state)?;
    state.metrics.increment_internal_requests();
    Ok(Json(
        state
            .node_registry_service
            .rollout_canary_evidence(&rollout_id, &state.config)
            .await?,
    ))
}

async fn client_capability_defaults(
    State(state): State<AppState>,
    headers: HeaderMap,
) -> Result<Json<ClientCapabilityDefaults>, AppError> {
    authorize(&headers, &state)?;
    state.metrics.increment_internal_requests();
    Ok(Json(state.manifest_store.client_capability_defaults(
        state.default_rollout_channel()?,
    )))
}

async fn node_assignment(
    State(state): State<AppState>,
    headers: HeaderMap,
    Path(node_id): Path<String>,
) -> Result<Json<NodeAssignmentDocument>, AppError> {
    authorize(&headers, &state)?;
    state.metrics.increment_internal_requests();
    Ok(Json(
        state
            .assignment_store
            .resolve_node_assignment(&node_id)
            .await?,
    ))
}

async fn node_heartbeat(
    State(state): State<AppState>,
    headers: HeaderMap,
    Path(node_id): Path<String>,
    Json(heartbeat): Json<NodeHeartbeatRequest>,
) -> Result<StatusCode, AppError> {
    authorize(&headers, &state)?;
    state.metrics.increment_internal_requests();

    if node_id != heartbeat.node_id {
        return Err(AppError::BadRequest(format!(
            "heartbeat node_id mismatch: path={node_id} body={}",
            heartbeat.node_id
        )));
    }

    state
        .node_registry_service
        .record_heartbeat(heartbeat)
        .await?;
    state.metrics.increment_node_heartbeat_ingested();

    Ok(StatusCode::ACCEPTED)
}

async fn desktop_runtime_event(
    State(state): State<AppState>,
    headers: HeaderMap,
    Json(event): Json<DesktopRuntimeEventRequest>,
) -> Result<Json<DesktopRuntimeEventAck>, AppError> {
    authorize(&headers, &state)?;
    state.metrics.increment_internal_requests();

    let ack = state
        .node_registry_service
        .record_desktop_runtime_event(event)
        .await?;
    state.metrics.increment_desktop_runtime_event_ingested();

    Ok(Json(ack))
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
