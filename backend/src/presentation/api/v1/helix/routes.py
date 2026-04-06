from fastapi import APIRouter, Depends, HTTPException, status

from src.application.services.helix_service import (
    HelixAccessDeniedError,
    HelixDisabledError,
    HelixManifestUnavailableError,
    HelixService,
    ResolveManifestCommand,
    RuntimeEventCommand,
)
from src.domain.enums import AdminRole
from src.infrastructure.database.models.admin_user_model import AdminUserModel
from src.infrastructure.monitoring.metrics import route_operations_total
from src.infrastructure.helix.client import AdapterPublishRolloutRequest
from src.presentation.dependencies import get_current_active_user, require_role
from src.presentation.dependencies.helix import (
    get_helix_service,
)

from .schemas import (
    HelixCapabilityDefaultsResponse,
    HelixManifestVersionResponse,
    HelixNodeAssignmentPreviewResponse,
    HelixNodeListResponse,
    HelixPublishRolloutRequest,
    HelixRolloutCanaryEvidenceResponse,
    HelixResolveManifestRequest,
    HelixResolveManifestResponse,
    HelixRuntimeEventRequest,
    HelixRuntimeEventResponse,
    HelixRolloutBatchResponse,
    HelixRolloutStateResponse,
    HelixTransportProfilesResponse,
)

router = APIRouter(prefix="/helix", tags=["helix"])


def _raise_hidden_not_found() -> None:
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")


@router.get("/capabilities", response_model=HelixCapabilityDefaultsResponse)
async def get_capability_defaults(
    current_user: AdminUserModel = Depends(get_current_active_user),
    service: HelixService = Depends(get_helix_service),
) -> HelixCapabilityDefaultsResponse:
    try:
        response = await service.get_capability_defaults_for_user(current_user)
    except (
        HelixDisabledError,
        HelixAccessDeniedError,
        HelixManifestUnavailableError,
    ):
        _raise_hidden_not_found()
    route_operations_total.labels(
        route="helix", action="capabilities", status="success"
    ).inc()
    return response


@router.post("/manifest", response_model=HelixResolveManifestResponse)
async def resolve_manifest(
    request: HelixResolveManifestRequest,
    current_user: AdminUserModel = Depends(get_current_active_user),
    service: HelixService = Depends(get_helix_service),
) -> HelixResolveManifestResponse:
    try:
        response = await service.resolve_manifest_for_user(
            current_user,
            ResolveManifestCommand(
                desktop_client_id=request.desktop_client_id,
                trace_id=request.trace_id,
                channel=request.channel,
                supported_protocol_versions=request.supported_protocol_versions,
                supported_transport_profiles=request.supported_transport_profiles,
                preferred_fallback_core=request.preferred_fallback_core,
            ),
        )
    except (
        HelixDisabledError,
        HelixAccessDeniedError,
        HelixManifestUnavailableError,
    ):
        _raise_hidden_not_found()
    route_operations_total.labels(
        route="helix", action="resolve_manifest", status="success"
    ).inc()
    return response


@router.post("/events/runtime", response_model=HelixRuntimeEventResponse)
async def report_runtime_event(
    request: HelixRuntimeEventRequest,
    current_user: AdminUserModel = Depends(get_current_active_user),
    service: HelixService = Depends(get_helix_service),
) -> HelixRuntimeEventResponse:
    try:
        response = await service.report_runtime_event_for_user(
            current_user,
            RuntimeEventCommand(
                desktop_client_id=request.desktop_client_id,
                manifest_version_id=request.manifest_version_id,
                rollout_id=request.rollout_id,
                transport_profile_id=request.transport_profile_id,
                event_kind=request.event_kind,
                active_core=request.active_core,
                fallback_core=request.fallback_core,
                latency_ms=request.latency_ms,
                route_count=request.route_count,
                reason=request.reason,
                payload=request.payload,
            ),
        )
    except (HelixDisabledError, HelixAccessDeniedError):
        _raise_hidden_not_found()
    route_operations_total.labels(
        route="helix", action="runtime_event", status="success"
    ).inc()
    return response


@router.get("/admin/nodes", response_model=HelixNodeListResponse)
async def list_nodes(
    _current_user=Depends(require_role(AdminRole.OPERATOR)),
    service: HelixService = Depends(get_helix_service),
) -> HelixNodeListResponse:
    try:
        response = await service.list_nodes()
    except HelixDisabledError:
        _raise_hidden_not_found()
    route_operations_total.labels(
        route="helix", action="list_nodes", status="success"
    ).inc()
    return response


@router.get(
    "/admin/rollouts/{rollout_id}", response_model=HelixRolloutStateResponse
)
async def get_rollout_status(
    rollout_id: str,
    _current_user=Depends(require_role(AdminRole.OPERATOR)),
    service: HelixService = Depends(get_helix_service),
) -> HelixRolloutStateResponse:
    try:
        response = await service.get_rollout_status(rollout_id)
    except HelixDisabledError:
        _raise_hidden_not_found()
    route_operations_total.labels(
        route="helix", action="get_rollout", status="success"
    ).inc()
    return response


@router.get(
    "/admin/rollouts/{rollout_id}/canary-evidence",
    response_model=HelixRolloutCanaryEvidenceResponse,
)
async def get_rollout_canary_evidence(
    rollout_id: str,
    _current_user=Depends(require_role(AdminRole.OPERATOR)),
    service: HelixService = Depends(get_helix_service),
) -> HelixRolloutCanaryEvidenceResponse:
    try:
        response = await service.get_rollout_canary_evidence(rollout_id)
    except HelixDisabledError:
        _raise_hidden_not_found()
    route_operations_total.labels(
        route="helix", action="get_rollout_canary_evidence", status="success"
    ).inc()
    return response


@router.get(
    "/admin/transport-profiles",
    response_model=HelixTransportProfilesResponse,
)
async def list_transport_profiles(
    _current_user=Depends(require_role(AdminRole.OPERATOR)),
    service: HelixService = Depends(get_helix_service),
) -> HelixTransportProfilesResponse:
    try:
        response = await service.list_transport_profiles()
    except HelixDisabledError:
        _raise_hidden_not_found()
    route_operations_total.labels(
        route="helix", action="list_profiles", status="success"
    ).inc()
    return response


@router.get(
    "/admin/nodes/{node_id}/assignment",
    response_model=HelixNodeAssignmentPreviewResponse,
)
async def preview_node_assignment(
    node_id: str,
    _current_user=Depends(require_role(AdminRole.OPERATOR)),
    service: HelixService = Depends(get_helix_service),
) -> HelixNodeAssignmentPreviewResponse:
    try:
        response = await service.preview_node_assignment(node_id)
    except HelixDisabledError:
        _raise_hidden_not_found()
    route_operations_total.labels(
        route="helix", action="node_assignment", status="success"
    ).inc()
    return response


@router.post("/admin/rollouts", response_model=HelixRolloutBatchResponse)
async def publish_rollout(
    request: HelixPublishRolloutRequest,
    _current_user=Depends(require_role(AdminRole.ADMIN)),
    service: HelixService = Depends(get_helix_service),
) -> HelixRolloutBatchResponse:
    try:
        response = await service.publish_rollout(
            AdapterPublishRolloutRequest.model_validate(request.model_dump())
        )
    except HelixDisabledError:
        _raise_hidden_not_found()
    route_operations_total.labels(
        route="helix", action="publish_rollout", status="success"
    ).inc()
    return response


@router.post(
    "/admin/rollouts/{rollout_id}/pause",
    response_model=HelixRolloutBatchResponse,
)
async def pause_rollout(
    rollout_id: str,
    _current_user=Depends(require_role(AdminRole.ADMIN)),
    service: HelixService = Depends(get_helix_service),
) -> HelixRolloutBatchResponse:
    try:
        response = await service.pause_rollout(rollout_id)
    except HelixDisabledError:
        _raise_hidden_not_found()
    route_operations_total.labels(
        route="helix", action="pause_rollout", status="success"
    ).inc()
    return response


@router.post(
    "/admin/manifests/{manifest_version_id}/revoke",
    response_model=HelixManifestVersionResponse,
)
async def revoke_manifest(
    manifest_version_id: str,
    _current_user=Depends(require_role(AdminRole.ADMIN)),
    service: HelixService = Depends(get_helix_service),
) -> HelixManifestVersionResponse:
    try:
        response = await service.revoke_manifest(manifest_version_id)
    except HelixDisabledError:
        _raise_hidden_not_found()
    route_operations_total.labels(
        route="helix", action="revoke_manifest", status="success"
    ).inc()
    return response
