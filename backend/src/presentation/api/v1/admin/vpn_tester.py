"""Admin API for CyberVPN VPN Tester."""

from __future__ import annotations

import hmac
import time
from datetime import datetime
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.use_cases.auth.permissions import Permission, has_permission
from src.application.vpn_testing import VpnTesterService
from src.application.vpn_testing.task2_route_evidence import (
    TASK2_XRAY_WEBHOOK_SECRET_HEADER,
    Task2RouteEvidenceRejected,
    Task2RouteEvidenceResult,
    Task2RouteEvidenceStore,
    Task2RouteEvidenceUnavailable,
    Task2XrayRoutingWebhook,
)
from src.config.settings import settings
from src.domain.enums import AdminRole
from src.infrastructure.cache.redis_client import get_redis
from src.infrastructure.database.models.admin_user_model import AdminUserModel
from src.infrastructure.database.models.vpn_tester_model import (
    VpnBalancerRecommendationModel,
    VpnTestEvidenceArtifactModel,
    VpnTestResultModel,
    VpnTestRunModel,
    VpnTestScheduleModel,
)
from src.infrastructure.database.repositories.vpn_tester_repo import VpnTesterRepository
from src.infrastructure.remnawave.client import RemnawaveClient
from src.presentation.dependencies import get_remnawave_client
from src.presentation.dependencies.database import get_db
from src.presentation.dependencies.roles import require_role

TASK2_ROUTE_EVIDENCE_INGRESS_HEADER = "X-CyberVPN-Task2-Evidence-Ingress"
TASK2_ROUTE_EVIDENCE_INGRESS_MARKER = "spb-source-verified-v1"

router = APIRouter(prefix="/admin/vpn-tester", tags=["admin", "vpn-tester"])


class VpnTesterResultResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID
    check_key: str
    check_name: str
    category: str
    status: str
    severity: str
    target: str
    safe_summary: str
    details: dict[str, Any]
    duration_ms: int
    created_at: datetime


class VpnTesterEvidenceResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID
    artifact_key: str
    artifact_type: str
    sha256: str
    preview: dict[str, Any]
    storage_uri: str | None
    expires_at: datetime | None
    created_at: datetime


class VpnTesterRunResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID
    suite_key: str
    suite_version: str
    mode: str
    trigger: str
    status: str
    requested_by_admin_id: UUID | None
    agent_id: str | None
    runtime_mode: str | None
    route_registry_version: str | None
    blocking: bool
    summary: dict[str, Any]
    pass_count: int
    fail_count: int
    degraded_count: int
    started_at: datetime | None
    finished_at: datetime | None
    created_at: datetime
    updated_at: datetime
    results: list[VpnTesterResultResponse] = Field(default_factory=list)
    evidence_artifacts: list[VpnTesterEvidenceResponse] = Field(default_factory=list)


class VpnTesterScheduleResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID
    schedule_key: str
    suite_key: str
    mode: str
    cron: str
    enabled: bool
    settings: dict[str, Any]
    next_run_at: datetime | None
    last_run_id: UUID | None
    last_status: str | None
    last_skipped_reason: str | None
    last_checked_at: datetime | None
    last_triggered_at: datetime | None
    schedule_source: str
    updated_at: datetime


class VpnTesterOverviewResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    enabled: bool
    runtime_enabled: bool
    scheduled_enabled: bool
    balancer_recommendations_enabled: bool
    counts: dict[str, int]
    latest_runs: list[VpnTesterRunResponse]
    schedules: list[VpnTesterScheduleResponse]
    generated_at: datetime


class CreateVpnTesterRunRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    suite_key: str = Field(default="premium_smart_ru_v1", min_length=3, max_length=80)
    mode: str = Field(default="contract", pattern="^(contract|runtime|all_tariffs|balancer_preview)$")
    context: dict[str, Any] = Field(default_factory=dict)


class UpdateVpnTesterScheduleRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    enabled: bool
    settings: dict[str, Any] | None = None


class InternalScheduledRunRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    suite_key: str = Field(default="default_subscription_smoke_v1", min_length=3, max_length=80)
    mode: str = Field(default="contract", pattern="^(contract|runtime|all_tariffs|balancer_preview)$")
    trigger: str = Field(default="scheduled", min_length=3, max_length=40)
    execute_immediately: bool = True
    context: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def reject_persisted_generated_artifact(self) -> InternalScheduledRunRequest:
        if (
            not self.execute_immediately
            and VpnTesterService.transient_generated_mihomo_artifact(self.context) is not None
        ):
            raise ValueError("generated_vpn_artifacts_require_immediate_execution")
        return self


class InternalScheduleGateRunRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    trigger: str = Field(default="scheduled", min_length=3, max_length=40)
    execute_immediately: bool = True
    idempotency_window: str = Field(default="minute", pattern="^(none|disabled|off|minute|hour|hourly|day|daily)$")


class InternalWorkerResultResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    skipped: bool = False
    reason: str | None = None
    run: VpnTesterRunResponse | None = None
    schedule: VpnTesterScheduleResponse | None = None
    cleanup: dict[str, Any] | None = None


class Task2RouteEvidenceCollectorResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    run_id: str
    route_key: str
    selected_outbound: str
    verdict: str
    digest: str


class VpnTesterTariffMatrixResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    rows: list[dict[str, Any]]
    total: int
    generated_at: datetime


class VpnTesterRouteMatrixResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    registry_key: str
    rows: list[dict[str, Any]]
    total: int
    generated_at: datetime


class VpnTesterReleaseGateOverrideResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID
    latest_run_id: UUID | None
    overridden_by_admin_id: UUID | None
    previous_status: str
    previous_blocking: bool
    reason: str
    expires_at: datetime
    created_at: datetime


class VpnTesterReleaseGateResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: str
    blocking: bool
    latest_run_id: UUID | None
    reason: str
    override_allowed_roles: list[str]
    active_override: VpnTesterReleaseGateOverrideResponse | None = None
    generated_at: datetime


class CreateReleaseGateOverrideRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    reason: str = Field(..., min_length=20, max_length=1000)
    ttl_minutes: int = Field(default=60, ge=1, le=4320)


class DismissBalancerRecommendationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    reason: str | None = Field(default=None, max_length=500)


class VpnBalancerRecommendationResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID
    recommendation_key: str
    recommendation_hash: str
    run_id: UUID | None
    status: str
    scope: str
    safe_summary: str
    candidate_changes: dict[str, Any]
    confidence: float
    acknowledged_by_admin_id: UUID | None
    acknowledged_at: datetime | None
    dismissed_by_admin_id: UUID | None
    dismissed_at: datetime | None
    dismissed_reason: str | None
    applied_manually_by_admin_id: UUID | None
    applied_manually_at: datetime | None
    expires_at: datetime | None
    created_at: datetime
    updated_at: datetime


def _serialize_result(result: VpnTestResultModel) -> VpnTesterResultResponse:
    return VpnTesterResultResponse(
        id=result.id,
        check_key=result.check_key,
        check_name=result.check_name,
        category=result.category,
        status=result.status,
        severity=result.severity,
        target=result.target,
        safe_summary=result.safe_summary,
        details=dict(result.details or {}),
        duration_ms=result.duration_ms,
        created_at=result.created_at,
    )


def _serialize_evidence(artifact: VpnTestEvidenceArtifactModel) -> VpnTesterEvidenceResponse:
    return VpnTesterEvidenceResponse(
        id=artifact.id,
        artifact_key=artifact.artifact_key,
        artifact_type=artifact.artifact_type,
        sha256=artifact.sha256,
        preview=dict(artifact.preview or {}),
        storage_uri=artifact.storage_uri,
        expires_at=artifact.expires_at,
        created_at=artifact.created_at,
    )


def _serialize_run(run: VpnTestRunModel, *, include_children: bool = True) -> VpnTesterRunResponse:
    return VpnTesterRunResponse(
        id=run.id,
        suite_key=run.suite_key,
        suite_version=run.suite_version,
        mode=run.mode,
        trigger=run.trigger,
        status=run.status,
        requested_by_admin_id=run.requested_by_admin_id,
        agent_id=run.agent_id,
        runtime_mode=run.runtime_mode,
        route_registry_version=run.route_registry_version,
        blocking=run.blocking,
        summary=dict(run.summary or {}),
        pass_count=run.pass_count,
        fail_count=run.fail_count,
        degraded_count=run.degraded_count,
        started_at=run.started_at,
        finished_at=run.finished_at,
        created_at=run.created_at,
        updated_at=run.updated_at,
        results=[_serialize_result(item) for item in run.results] if include_children else [],
        evidence_artifacts=[_serialize_evidence(item) for item in run.evidence_artifacts] if include_children else [],
    )


def _serialize_schedule(schedule: VpnTestScheduleModel) -> VpnTesterScheduleResponse:
    return VpnTesterScheduleResponse(
        id=schedule.id,
        schedule_key=schedule.schedule_key,
        suite_key=schedule.suite_key,
        mode=schedule.mode,
        cron=schedule.cron,
        enabled=schedule.enabled,
        settings=dict(schedule.settings or {}),
        next_run_at=schedule.next_run_at,
        last_run_id=schedule.last_run_id,
        last_status=schedule.last_status,
        last_skipped_reason=schedule.last_skipped_reason,
        last_checked_at=schedule.last_checked_at,
        last_triggered_at=schedule.last_triggered_at,
        schedule_source=schedule.schedule_source,
        updated_at=schedule.updated_at,
    )


def _serialize_balancer_recommendation(
    recommendation: VpnBalancerRecommendationModel,
) -> VpnBalancerRecommendationResponse:
    return VpnBalancerRecommendationResponse(
        id=recommendation.id,
        recommendation_key=recommendation.recommendation_key,
        recommendation_hash=recommendation.recommendation_hash,
        run_id=recommendation.run_id,
        status=recommendation.status,
        scope=recommendation.scope,
        safe_summary=recommendation.safe_summary,
        candidate_changes=dict(recommendation.candidate_changes or {}),
        confidence=recommendation.confidence,
        acknowledged_by_admin_id=recommendation.acknowledged_by_admin_id,
        acknowledged_at=recommendation.acknowledged_at,
        dismissed_by_admin_id=recommendation.dismissed_by_admin_id,
        dismissed_at=recommendation.dismissed_at,
        dismissed_reason=recommendation.dismissed_reason,
        applied_manually_by_admin_id=recommendation.applied_manually_by_admin_id,
        applied_manually_at=recommendation.applied_manually_at,
        expires_at=recommendation.expires_at,
        created_at=recommendation.created_at,
        updated_at=recommendation.updated_at,
    )


def _admin_role(user: AdminUserModel) -> AdminRole:
    try:
        return AdminRole(user.role)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid admin role") from exc


def require_any_permission(*permissions: Permission):
    async def checker(user: AdminUserModel = Depends(require_role(AdminRole.VIEWER))) -> AdminUserModel:
        role = _admin_role(user)
        if any(has_permission(role, permission) for permission in permissions):
            return user
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")

    return checker


def require_all_permissions(*permissions: Permission):
    async def checker(user: AdminUserModel = Depends(require_role(AdminRole.VIEWER))) -> AdminUserModel:
        role = _admin_role(user)
        if all(has_permission(role, permission) for permission in permissions):
            return user
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")

    return checker


def _can_manage_plans(user: AdminUserModel) -> bool:
    return has_permission(_admin_role(user), Permission.MANAGE_PLANS)


def _sanitize_tariff_matrix(matrix: dict[str, Any], *, include_sensitive: bool) -> dict[str, Any]:
    if include_sensitive:
        return matrix
    sanitized_rows = []
    for row in matrix.get("rows") or []:
        if not isinstance(row, dict):
            continue
        safe = dict(row)
        safe.pop("duration_days", None)
        safe.pop("traffic_limit_bytes", None)
        safe.pop("traffic_policy_keys", None)
        safe.pop("remnawave_assignment", None)
        safe["sensitive_fields_hidden"] = True
        sanitized_rows.append(safe)
    return {**matrix, "rows": sanitized_rows}


async def get_vpn_tester_service(
    db: AsyncSession = Depends(get_db),
    remnawave_client: RemnawaveClient = Depends(get_remnawave_client),
    redis_client: Redis = Depends(get_redis),
) -> VpnTesterService:
    return VpnTesterService(VpnTesterRepository(db), remnawave_client, redis_client)


def _require_enabled() -> None:
    if settings.vpn_tester_enabled:
        return
    raise HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail="VPN Tester is disabled by VPN_TESTER_ENABLED",
    )


def _require_mode_enabled(mode: str) -> None:
    if mode != "runtime" or settings.vpn_tester_runtime_enabled:
        return
    raise HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail="VPN Tester runtime checks are disabled by VPN_TESTER_RUNTIME_ENABLED",
    )


def _require_backend_internal_secret(secret: str | None) -> None:
    configured = settings.backend_internal_secret.get_secret_value().strip()
    if configured and secret and hmac.compare_digest(configured, secret.strip()):
        return
    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated.")


def _require_task2_route_evidence_enabled() -> None:
    if settings.vpn_tester_task2_route_evidence_enabled:
        return
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="task2_route_evidence_disabled")


def _require_task2_xray_webhook_secret(secret: str | None) -> None:
    configured = settings.vpn_tester_task2_xray_webhook_secret.get_secret_value().strip()
    if not configured:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="task2_route_evidence_unavailable")
    candidate = (secret or "").strip()
    if hmac.compare_digest(configured, candidate):
        return
    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated.")


def _require_task2_route_evidence_ingress(marker: str | None) -> None:
    if marker is not None and hmac.compare_digest(marker.strip(), TASK2_ROUTE_EVIDENCE_INGRESS_MARKER):
        return
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="task2_route_evidence_not_found")


def _task2_route_evidence_store(redis_client: Redis) -> Task2RouteEvidenceStore:
    return Task2RouteEvidenceStore(
        redis_client,
        expectation_ttl_seconds=settings.vpn_tester_task2_route_evidence_expectation_ttl_seconds,
        result_ttl_seconds=settings.vpn_tester_task2_route_evidence_result_ttl_seconds,
        webhook_secret=settings.vpn_tester_task2_xray_webhook_secret.get_secret_value().strip(),
    )


def _header_count(request: Request, header_name: str) -> int:
    target = header_name.lower().encode("ascii")
    return sum(1 for name, _value in request.scope.get("headers", []) if name.lower() == target)


def _reject_task2_webhook_transport(request: Request) -> None:
    if request.url.query:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="query_string_not_allowed")
    if _header_count(request, TASK2_XRAY_WEBHOOK_SECRET_HEADER) > 1:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="duplicate_webhook_secret_header")
    if _header_count(request, "Authorization") > 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="authorization_header_not_allowed")
    if _header_count(request, "Cookie") > 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="cookie_header_not_allowed")

    content_type = request.headers.get("content-type", "")
    media_type = content_type.split(";", 1)[0].strip().lower()
    if media_type != "application/json":
        raise HTTPException(status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, detail="json_required")


def _reject_task2_body_if_too_large(request: Request, body: bytes | None = None) -> None:
    max_body_bytes = settings.vpn_tester_task2_xray_webhook_max_body_bytes
    content_length = request.headers.get("content-length")
    if content_length is not None:
        try:
            if int(content_length) > max_body_bytes:
                raise HTTPException(status_code=status.HTTP_413_CONTENT_TOO_LARGE, detail="body_too_large")
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="invalid_content_length") from exc
    if body is not None and len(body) > max_body_bytes:
        raise HTTPException(status_code=status.HTTP_413_CONTENT_TOO_LARGE, detail="body_too_large")


async def _read_task2_bounded_body(request: Request) -> bytes:
    max_body_bytes = settings.vpn_tester_task2_xray_webhook_max_body_bytes
    body = bytearray()
    async for chunk in request.stream():
        if len(body) + len(chunk) > max_body_bytes:
            raise HTTPException(status_code=status.HTTP_413_CONTENT_TOO_LARGE, detail="body_too_large")
        body.extend(chunk)
    return bytes(body)


def _map_task2_route_evidence_rejection(exc: Task2RouteEvidenceRejected) -> HTTPException:
    if exc.reason == "expectation_not_found":
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="task2_route_evidence_not_found")
    return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="task2_route_evidence_rejected")


def _serialize_task2_route_evidence_result(
    result: Task2RouteEvidenceResult,
) -> Task2RouteEvidenceCollectorResponse:
    return Task2RouteEvidenceCollectorResponse(
        run_id=result.run_id,
        route_key=result.route_key,
        selected_outbound=result.selected_outbound,
        verdict=result.verdict,
        digest=result.digest,
    )


@router.get("/overview", response_model=VpnTesterOverviewResponse)
async def get_vpn_tester_overview(
    _admin: AdminUserModel = Depends(require_any_permission(Permission.SERVER_READ, Permission.MONITORING_READ)),
    service: VpnTesterService = Depends(get_vpn_tester_service),
) -> VpnTesterOverviewResponse:
    overview = await service.overview()
    return VpnTesterOverviewResponse(
        enabled=bool(overview["enabled"]),
        runtime_enabled=bool(overview["runtime_enabled"]),
        scheduled_enabled=bool(overview["scheduled_enabled"]),
        balancer_recommendations_enabled=bool(overview["balancer_recommendations_enabled"]),
        counts=dict(overview["counts"]),
        latest_runs=[_serialize_run(run, include_children=False) for run in overview["latest_runs"]],
        schedules=[_serialize_schedule(schedule) for schedule in overview["schedules"]],
        generated_at=overview["generated_at"],
    )


@router.get("/runs", response_model=list[VpnTesterRunResponse])
async def list_vpn_tester_runs(
    limit: int = 25,
    status_filter: str | None = None,
    _admin: AdminUserModel = Depends(require_any_permission(Permission.SERVER_READ, Permission.MONITORING_READ)),
    service: VpnTesterService = Depends(get_vpn_tester_service),
) -> list[VpnTesterRunResponse]:
    runs = await service.list_runs(limit=limit, status=status_filter)
    return [_serialize_run(run, include_children=False) for run in runs]


@router.post("/runs", response_model=VpnTesterRunResponse, status_code=status.HTTP_202_ACCEPTED)
async def create_vpn_tester_run(
    payload: CreateVpnTesterRunRequest,
    request: Request,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    admin: AdminUserModel = Depends(require_any_permission(Permission.SERVER_UPDATE, Permission.MANAGE_PLANS)),
    service: VpnTesterService = Depends(get_vpn_tester_service),
) -> VpnTesterRunResponse:
    _require_enabled()
    context = {
        "admin_surface": "vpn_tester",
        "client_host": request.client.host if request.client else None,
        "requested_context": payload.context,
    }
    if service.transient_generated_mihomo_artifact(context) is not None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Generated VPN artifacts are accepted only by the immediate internal runtime path.",
        )
    run = await service.create_manual_run(
        suite_key=payload.suite_key,
        mode=payload.mode,
        requested_by_admin_id=admin.id,
        idempotency_key=idempotency_key,
        request_context=context,
    )
    return _serialize_run(run, include_children=False)


@router.get("/runs/{run_id}", response_model=VpnTesterRunResponse)
async def get_vpn_tester_run(
    run_id: UUID,
    _admin: AdminUserModel = Depends(require_any_permission(Permission.SERVER_READ, Permission.MONITORING_READ)),
    service: VpnTesterService = Depends(get_vpn_tester_service),
) -> VpnTesterRunResponse:
    run = await service.get_run(run_id)
    if run is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Run not found")
    return _serialize_run(run)


@router.post("/runs/{run_id}/cancel", response_model=VpnTesterRunResponse)
async def cancel_vpn_tester_run(
    run_id: UUID,
    _admin: AdminUserModel = Depends(require_any_permission(Permission.SERVER_UPDATE, Permission.MANAGE_PLANS)),
    service: VpnTesterService = Depends(get_vpn_tester_service),
) -> VpnTesterRunResponse:
    run = await service.cancel_run(run_id)
    if run is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Run not found")
    return _serialize_run(run)


@router.get("/runs/{run_id}/evidence", response_model=list[VpnTesterEvidenceResponse])
async def list_vpn_tester_evidence(
    run_id: UUID,
    _admin: AdminUserModel = Depends(require_any_permission(Permission.SERVER_READ, Permission.MONITORING_READ)),
    service: VpnTesterService = Depends(get_vpn_tester_service),
) -> list[VpnTesterEvidenceResponse]:
    run = await service.get_run(run_id)
    if run is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Run not found")
    return [_serialize_evidence(item) for item in run.evidence_artifacts]


@router.get("/schedules", response_model=list[VpnTesterScheduleResponse])
async def list_vpn_tester_schedules(
    _admin: AdminUserModel = Depends(require_any_permission(Permission.SERVER_READ, Permission.MONITORING_READ)),
    service: VpnTesterService = Depends(get_vpn_tester_service),
) -> list[VpnTesterScheduleResponse]:
    schedules = await service.list_schedules()
    return [_serialize_schedule(schedule) for schedule in schedules]


@router.put("/schedules/{schedule_key}", response_model=VpnTesterScheduleResponse)
async def update_vpn_tester_schedule(
    schedule_key: str,
    payload: UpdateVpnTesterScheduleRequest,
    _admin: AdminUserModel = Depends(require_all_permissions(Permission.SERVER_UPDATE, Permission.MANAGE_PLANS)),
    service: VpnTesterService = Depends(get_vpn_tester_service),
) -> VpnTesterScheduleResponse:
    schedule = await service.update_schedule(schedule_key, enabled=payload.enabled, schedule_settings=payload.settings)
    if schedule is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Schedule not found")
    return _serialize_schedule(schedule)


@router.get("/tariffs", response_model=VpnTesterTariffMatrixResponse)
async def get_vpn_tester_tariff_matrix(
    admin: AdminUserModel = Depends(
        require_any_permission(Permission.SERVER_READ, Permission.MONITORING_READ, Permission.MANAGE_PLANS)
    ),
    service: VpnTesterService = Depends(get_vpn_tester_service),
) -> VpnTesterTariffMatrixResponse:
    matrix = await service.tariff_matrix()
    return VpnTesterTariffMatrixResponse(**_sanitize_tariff_matrix(matrix, include_sensitive=_can_manage_plans(admin)))


@router.get("/route-matrix", response_model=VpnTesterRouteMatrixResponse)
async def get_vpn_tester_route_matrix(
    _admin: AdminUserModel = Depends(require_any_permission(Permission.SERVER_READ, Permission.MONITORING_READ)),
    service: VpnTesterService = Depends(get_vpn_tester_service),
) -> VpnTesterRouteMatrixResponse:
    return VpnTesterRouteMatrixResponse(**await service.route_matrix())


@router.get("/balancer/preview", response_model=dict[str, Any])
async def get_vpn_tester_balancer_preview(
    _admin: AdminUserModel = Depends(require_any_permission(Permission.SERVER_READ, Permission.MONITORING_READ)),
    service: VpnTesterService = Depends(get_vpn_tester_service),
) -> dict[str, Any]:
    matrix = await service.tariff_matrix()
    return {
        "enabled": bool(settings.vpn_tester_balancer_recommendations_enabled),
        "mutates_live_state": False,
        "summary": "Recommendations only; live routing is not changed by this endpoint.",
        "tariff_rows": matrix["rows"],
        "generated_at": matrix["generated_at"],
    }


@router.get("/release-gate", response_model=VpnTesterReleaseGateResponse)
async def get_vpn_tester_release_gate(
    _admin: AdminUserModel = Depends(require_any_permission(Permission.SERVER_READ, Permission.MONITORING_READ)),
    service: VpnTesterService = Depends(get_vpn_tester_service),
) -> VpnTesterReleaseGateResponse:
    return VpnTesterReleaseGateResponse(**await service.release_gate())


@router.post("/release-gate/override", response_model=VpnTesterReleaseGateResponse)
async def override_vpn_tester_release_gate(
    payload: CreateReleaseGateOverrideRequest,
    request: Request,
    admin: AdminUserModel = Depends(require_role(AdminRole.SUPER_ADMIN)),
    service: VpnTesterService = Depends(get_vpn_tester_service),
) -> VpnTesterReleaseGateResponse:
    try:
        gate = await service.create_release_gate_override(
            admin_id=admin.id,
            admin_role=_admin_role(admin),
            reason=payload.reason,
            ttl_minutes=payload.ttl_minutes,
            request_context={
                "admin_surface": "vpn_tester",
                "client_host": request.client.host if request.client else None,
            },
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)) from exc
    return VpnTesterReleaseGateResponse(**gate)


@router.get("/balancer/recommendations", response_model=list[VpnBalancerRecommendationResponse])
async def list_vpn_tester_balancer_recommendations(
    limit: int = 50,
    _admin: AdminUserModel = Depends(require_any_permission(Permission.SERVER_READ, Permission.MONITORING_READ)),
    service: VpnTesterService = Depends(get_vpn_tester_service),
) -> list[VpnBalancerRecommendationResponse]:
    recommendations = await service.list_balancer_recommendations(limit=limit)
    return [_serialize_balancer_recommendation(item) for item in recommendations]


@router.post("/balancer/recommendations/{recommendation_id}/ack", response_model=VpnBalancerRecommendationResponse)
async def acknowledge_vpn_tester_balancer_recommendation(
    recommendation_id: UUID,
    admin: AdminUserModel = Depends(require_any_permission(Permission.SERVER_UPDATE, Permission.MANAGE_PLANS)),
    service: VpnTesterService = Depends(get_vpn_tester_service),
) -> VpnBalancerRecommendationResponse:
    recommendation = await service.acknowledge_balancer_recommendation(recommendation_id, admin_id=admin.id)
    if recommendation is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Recommendation not found")
    return _serialize_balancer_recommendation(recommendation)


@router.post("/balancer/recommendations/{recommendation_id}/dismiss", response_model=VpnBalancerRecommendationResponse)
async def dismiss_vpn_tester_balancer_recommendation(
    recommendation_id: UUID,
    payload: DismissBalancerRecommendationRequest,
    admin: AdminUserModel = Depends(require_any_permission(Permission.SERVER_UPDATE, Permission.MANAGE_PLANS)),
    service: VpnTesterService = Depends(get_vpn_tester_service),
) -> VpnBalancerRecommendationResponse:
    recommendation = await service.dismiss_balancer_recommendation(
        recommendation_id,
        admin_id=admin.id,
        reason=payload.reason,
    )
    if recommendation is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Recommendation not found")
    return _serialize_balancer_recommendation(recommendation)


@router.post(
    "/internal/task2/route-evidence/xray-routing-webhook",
    response_model=Task2RouteEvidenceCollectorResponse,
    status_code=status.HTTP_202_ACCEPTED,
    include_in_schema=False,
)
async def internal_collect_task2_xray_route_evidence(
    request: Request,
    x_task2_xray_webhook_secret: str | None = Header(default=None, alias=TASK2_XRAY_WEBHOOK_SECRET_HEADER),
    x_task2_route_evidence_ingress: str | None = Header(default=None, alias=TASK2_ROUTE_EVIDENCE_INGRESS_HEADER),
    redis_client: Redis = Depends(get_redis),
) -> Task2RouteEvidenceCollectorResponse:
    _require_task2_route_evidence_enabled()
    _reject_task2_webhook_transport(request)
    if _header_count(request, TASK2_ROUTE_EVIDENCE_INGRESS_HEADER) > 1:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="duplicate_ingress_marker_header")
    _require_task2_route_evidence_ingress(x_task2_route_evidence_ingress)
    _require_task2_xray_webhook_secret(x_task2_xray_webhook_secret)
    _reject_task2_body_if_too_large(request)

    raw_body = await _read_task2_bounded_body(request)
    try:
        webhook = Task2XrayRoutingWebhook.model_validate_json(raw_body)
    except ValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="invalid_xray_routing_webhook",
        ) from exc

    store = _task2_route_evidence_store(redis_client)
    try:
        result = await store.record_xray_routing_webhook(
            webhook,
            synthetic_user=settings.vpn_tester_task2_synthetic_user,
            max_skew_seconds=settings.vpn_tester_task2_xray_webhook_max_skew_seconds,
            now_epoch_seconds=int(time.time()),
        )
    except Task2RouteEvidenceUnavailable as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="task2_route_evidence_unavailable",
        ) from exc
    except Task2RouteEvidenceRejected as exc:
        raise _map_task2_route_evidence_rejection(exc) from exc
    return _serialize_task2_route_evidence_result(result)


@router.post("/internal/runs/{run_id}/execute", response_model=InternalWorkerResultResponse, include_in_schema=False)
async def internal_execute_vpn_tester_run(
    run_id: UUID,
    x_backend_internal_secret: str | None = Header(default=None, alias="X-Backend-Internal-Secret"),
    service: VpnTesterService = Depends(get_vpn_tester_service),
) -> InternalWorkerResultResponse:
    _require_backend_internal_secret(x_backend_internal_secret)
    run = await service.get_run(run_id)
    if run is None:
        return InternalWorkerResultResponse(skipped=True, reason="run_not_found")
    executed = await service.execute_run(run)
    refreshed = await service.get_run(executed.id)
    return InternalWorkerResultResponse(run=_serialize_run(refreshed or executed))


@router.post("/internal/queued/execute-next", response_model=InternalWorkerResultResponse, include_in_schema=False)
async def internal_execute_next_vpn_tester_run(
    x_backend_internal_secret: str | None = Header(default=None, alias="X-Backend-Internal-Secret"),
    service: VpnTesterService = Depends(get_vpn_tester_service),
) -> InternalWorkerResultResponse:
    _require_backend_internal_secret(x_backend_internal_secret)
    executed = await service.execute_next_queued_run()
    if executed is None:
        return InternalWorkerResultResponse(skipped=True, reason="no_queued_runs")
    refreshed = await service.get_run(executed.id)
    return InternalWorkerResultResponse(run=_serialize_run(refreshed or executed))


@router.post("/internal/scheduled/run", response_model=InternalWorkerResultResponse, include_in_schema=False)
async def internal_create_scheduled_vpn_tester_run(
    payload: InternalScheduledRunRequest,
    x_backend_internal_secret: str | None = Header(default=None, alias="X-Backend-Internal-Secret"),
    service: VpnTesterService = Depends(get_vpn_tester_service),
) -> InternalWorkerResultResponse:
    _require_backend_internal_secret(x_backend_internal_secret)
    if not settings.vpn_tester_enabled:
        return InternalWorkerResultResponse(skipped=True, reason="vpn_tester_disabled")
    generated_mihomo_artifact = service.transient_generated_mihomo_artifact(payload.context)
    if generated_mihomo_artifact is not None and not payload.execute_immediately:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Generated VPN artifacts cannot be queued or persisted.",
        )
    run = await service.create_scheduled_run(
        suite_key=payload.suite_key,
        mode=payload.mode,
        trigger=payload.trigger,
        request_context=payload.context,
    )
    if payload.execute_immediately:
        run = await service.execute_run(run, generated_mihomo_artifact=generated_mihomo_artifact)
    refreshed = await service.get_run(run.id)
    return InternalWorkerResultResponse(run=_serialize_run(refreshed or run))


@router.post(
    "/internal/schedules/{schedule_key}/run",
    response_model=InternalWorkerResultResponse,
    include_in_schema=True,
)
async def internal_run_vpn_tester_schedule(
    schedule_key: str,
    payload: InternalScheduleGateRunRequest,
    x_backend_internal_secret: str | None = Header(default=None, alias="X-Backend-Internal-Secret"),
    service: VpnTesterService = Depends(get_vpn_tester_service),
) -> InternalWorkerResultResponse:
    _require_backend_internal_secret(x_backend_internal_secret)
    result = await service.run_schedule(
        schedule_key=schedule_key,
        trigger=payload.trigger,
        execute_immediately=payload.execute_immediately,
        idempotency_window=payload.idempotency_window,
    )
    run = result.get("run")
    if isinstance(run, VpnTestRunModel):
        run = await service.get_run(run.id) or run
    schedule_model = result.get("schedule")
    return InternalWorkerResultResponse(
        skipped=bool(result.get("skipped")),
        reason=result.get("reason"),
        run=_serialize_run(run) if isinstance(run, VpnTestRunModel) else None,
        schedule=_serialize_schedule(schedule_model) if isinstance(schedule_model, VpnTestScheduleModel) else None,
    )


@router.post("/internal/cleanup", response_model=InternalWorkerResultResponse, include_in_schema=False)
async def internal_cleanup_vpn_tester(
    x_backend_internal_secret: str | None = Header(default=None, alias="X-Backend-Internal-Secret"),
    service: VpnTesterService = Depends(get_vpn_tester_service),
) -> InternalWorkerResultResponse:
    _require_backend_internal_secret(x_backend_internal_secret)
    return InternalWorkerResultResponse(cleanup=await service.cleanup_expired_evidence())
