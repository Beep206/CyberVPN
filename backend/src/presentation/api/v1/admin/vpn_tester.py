"""Admin API for CyberVPN VPN Tester."""

from __future__ import annotations

import hmac
from datetime import datetime
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.use_cases.auth.permissions import Permission, has_permission
from src.application.vpn_testing import VpnTesterService
from src.config.settings import settings
from src.domain.enums import AdminRole
from src.infrastructure.database.models.admin_user_model import AdminUserModel
from src.infrastructure.database.models.vpn_tester_model import (
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
    trigger: str = Field(default="scheduled", min_length=3, max_length=60)
    execute_immediately: bool = True


class InternalWorkerResultResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    skipped: bool = False
    reason: str | None = None
    run: VpnTesterRunResponse | None = None
    cleanup: dict[str, Any] | None = None


class VpnTesterTariffMatrixResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    rows: list[dict[str, Any]]
    total: int
    generated_at: datetime


class VpnTesterReleaseGateResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: str
    blocking: bool
    latest_run_id: UUID | None
    reason: str
    override_allowed_roles: list[str]
    generated_at: datetime


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
        updated_at=schedule.updated_at,
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


async def get_vpn_tester_service(
    db: AsyncSession = Depends(get_db),
    remnawave_client: RemnawaveClient = Depends(get_remnawave_client),
) -> VpnTesterService:
    return VpnTesterService(VpnTesterRepository(db), remnawave_client)


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
    admin: AdminUserModel = Depends(require_any_permission(Permission.SERVER_UPDATE, Permission.MONITORING_READ)),
    service: VpnTesterService = Depends(get_vpn_tester_service),
) -> VpnTesterRunResponse:
    _require_enabled()
    _require_mode_enabled(payload.mode)
    context = {
        "admin_surface": "vpn_tester",
        "client_host": request.client.host if request.client else None,
        "requested_context": payload.context,
    }
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
    _admin: AdminUserModel = Depends(require_any_permission(Permission.SERVER_UPDATE, Permission.MONITORING_READ)),
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
    _admin: AdminUserModel = Depends(require_all_permissions(Permission.SERVER_UPDATE, Permission.MANAGE_PLANS)),
    service: VpnTesterService = Depends(get_vpn_tester_service),
) -> VpnTesterTariffMatrixResponse:
    matrix = await service.tariff_matrix()
    return VpnTesterTariffMatrixResponse(**matrix)


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
    _admin: AdminUserModel = Depends(require_role(AdminRole.SUPER_ADMIN)),
    service: VpnTesterService = Depends(get_vpn_tester_service),
) -> VpnTesterReleaseGateResponse:
    gate = await service.release_gate()
    gate["status"] = "override_recorded"
    gate["blocking"] = False
    gate["reason"] = "manual_super_admin_override"
    return VpnTesterReleaseGateResponse(**gate)


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
    return InternalWorkerResultResponse(run=_serialize_run(executed))


@router.post("/internal/queued/execute-next", response_model=InternalWorkerResultResponse, include_in_schema=False)
async def internal_execute_next_vpn_tester_run(
    x_backend_internal_secret: str | None = Header(default=None, alias="X-Backend-Internal-Secret"),
    service: VpnTesterService = Depends(get_vpn_tester_service),
) -> InternalWorkerResultResponse:
    _require_backend_internal_secret(x_backend_internal_secret)
    executed = await service.execute_next_queued_run()
    if executed is None:
        return InternalWorkerResultResponse(skipped=True, reason="no_queued_runs")
    return InternalWorkerResultResponse(run=_serialize_run(executed))


@router.post("/internal/scheduled/run", response_model=InternalWorkerResultResponse, include_in_schema=False)
async def internal_create_scheduled_vpn_tester_run(
    payload: InternalScheduledRunRequest,
    x_backend_internal_secret: str | None = Header(default=None, alias="X-Backend-Internal-Secret"),
    service: VpnTesterService = Depends(get_vpn_tester_service),
) -> InternalWorkerResultResponse:
    _require_backend_internal_secret(x_backend_internal_secret)
    if not settings.vpn_tester_scheduled_enabled:
        return InternalWorkerResultResponse(skipped=True, reason="scheduled_disabled")
    run = await service.create_scheduled_run(suite_key=payload.suite_key, mode=payload.mode, trigger=payload.trigger)
    if payload.execute_immediately:
        run = await service.execute_run(run)
    return InternalWorkerResultResponse(run=_serialize_run(run))


@router.post("/internal/cleanup", response_model=InternalWorkerResultResponse, include_in_schema=False)
async def internal_cleanup_vpn_tester(
    x_backend_internal_secret: str | None = Header(default=None, alias="X-Backend-Internal-Secret"),
    service: VpnTesterService = Depends(get_vpn_tester_service),
) -> InternalWorkerResultResponse:
    _require_backend_internal_secret(x_backend_internal_secret)
    return InternalWorkerResultResponse(cleanup=await service.cleanup_expired_evidence())
