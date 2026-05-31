"""Admin commercial pricebook lifecycle endpoints."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.use_cases.offers.admin_pricebook_lifecycle import (
    COMMERCIAL_CONTEXT_OPTIONS_CONFIG_KEY,
    COMMERCIAL_CONTEXT_OPTIONS_UPDATED_ACTION,
    PRICEBOOK_AUDIT_RESOURCE_TYPE,
    AdminCommercialContextOptionsUseCase,
    AdminPricebookLifecycleUseCase,
    PricebookLifecycleResult,
    pricebook_lifecycle_status,
)
from src.domain.enums import AdminRole
from src.infrastructure.database.models.admin_user_model import AdminUserModel
from src.infrastructure.database.models.pricebook_model import PricebookModel
from src.infrastructure.database.repositories.audit_log_repo import AuditLogRepository
from src.infrastructure.database.repositories.system_config_repo import SystemConfigRepository
from src.infrastructure.monitoring.metrics import route_operations_total
from src.presentation.api.v1.admin.audit import write_required_admin_audit_entry
from src.presentation.api.v1.admin.schemas import AuditLogResponse
from src.presentation.api.v1.pricebooks.schemas import PricebookResponse
from src.presentation.dependencies.database import get_db
from src.presentation.dependencies.roles import require_role

from .pricebooks_schemas import (
    AdminPricebookHistoryResponse,
    AdminPricebookLifecycleResponse,
    AdminPricebookValidationIssueResponse,
    AdminPricebookValidationResponse,
    AdminPricebookVersionResponse,
    CommercialContextCountryOptionResponse,
    CommercialContextCurrencyOptionResponse,
    CommercialContextOptionsResponse,
    PublishAdminPricebookRequest,
    RollbackAdminPricebookRequest,
    ScheduleAdminPricebookRequest,
    UpdateAdminPricebookRequest,
    UpdateCommercialContextOptionsRequest,
)

router = APIRouter(prefix="/admin", tags=["admin", "commercial-pricebooks"])


@router.get("/pricebooks", response_model=list[AdminPricebookVersionResponse])
async def list_admin_commercial_pricebooks(
    include_inactive: bool = Query(True),
    storefront_id: UUID | None = Query(None),
    storefront_key: str | None = Query(None, min_length=1, max_length=80),
    currency_code: str | None = Query(None, min_length=3, max_length=3),
    region_code: str | None = Query(None, min_length=2, max_length=16),
    db: AsyncSession = Depends(get_db),
    _: AdminUserModel = Depends(require_role(AdminRole.ADMIN)),
) -> list[AdminPricebookVersionResponse]:
    use_case = AdminPricebookLifecycleUseCase(db)
    pricebooks = await use_case.list_pricebooks(
        include_inactive=include_inactive,
        storefront_id=storefront_id,
        storefront_key=storefront_key,
        currency_code=currency_code,
        region_code=region_code,
    )
    route_operations_total.labels(route="admin_pricebooks", action="list", status="success").inc()
    return [_serialize_version(pricebook) for pricebook in pricebooks]


@router.patch("/pricebooks/{pricebook_id}", response_model=AdminPricebookLifecycleResponse)
async def update_admin_commercial_pricebook(
    pricebook_id: UUID,
    payload: UpdateAdminPricebookRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: AdminUserModel = Depends(require_role(AdminRole.ADMIN)),
) -> AdminPricebookLifecycleResponse:
    use_case = AdminPricebookLifecycleUseCase(db)
    data = payload.model_dump(exclude_unset=True)
    change_reason = data.pop("change_reason", None)
    try:
        result = await use_case.update_pricebook(pricebook_id, data)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    await _write_pricebook_audit(
        result=result,
        request=request,
        db=db,
        actor=current_user,
        change_reason=change_reason,
    )
    route_operations_total.labels(route="admin_pricebooks", action="update", status="success").inc()
    return _serialize_lifecycle(result)


@router.post("/pricebooks/{pricebook_id}/publish", response_model=AdminPricebookLifecycleResponse)
async def publish_admin_commercial_pricebook(
    pricebook_id: UUID,
    payload: PublishAdminPricebookRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: AdminUserModel = Depends(require_role(AdminRole.ADMIN)),
) -> AdminPricebookLifecycleResponse:
    use_case = AdminPricebookLifecycleUseCase(db)
    try:
        result = await use_case.publish_pricebook(pricebook_id, effective_from=payload.effective_from)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    await _write_pricebook_audit(
        result=result,
        request=request,
        db=db,
        actor=current_user,
        change_reason=payload.change_reason,
    )
    route_operations_total.labels(route="admin_pricebooks", action="publish", status="success").inc()
    return _serialize_lifecycle(result)


@router.post("/pricebooks/{pricebook_id}/schedule", response_model=AdminPricebookLifecycleResponse)
async def schedule_admin_commercial_pricebook(
    pricebook_id: UUID,
    payload: ScheduleAdminPricebookRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: AdminUserModel = Depends(require_role(AdminRole.ADMIN)),
) -> AdminPricebookLifecycleResponse:
    use_case = AdminPricebookLifecycleUseCase(db)
    try:
        result = await use_case.schedule_pricebook(pricebook_id, scheduled_for=payload.scheduled_for)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    await _write_pricebook_audit(
        result=result,
        request=request,
        db=db,
        actor=current_user,
        change_reason=payload.change_reason,
    )
    route_operations_total.labels(route="admin_pricebooks", action="schedule", status="success").inc()
    return _serialize_lifecycle(result)


@router.post("/pricebooks/{pricebook_id}/rollback", response_model=AdminPricebookLifecycleResponse)
async def rollback_admin_commercial_pricebook(
    pricebook_id: UUID,
    payload: RollbackAdminPricebookRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: AdminUserModel = Depends(require_role(AdminRole.ADMIN)),
) -> AdminPricebookLifecycleResponse:
    use_case = AdminPricebookLifecycleUseCase(db)
    try:
        result = await use_case.rollback_pricebook(pricebook_id, target_pricebook_id=payload.target_pricebook_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    await _write_pricebook_audit(
        result=result,
        request=request,
        db=db,
        actor=current_user,
        change_reason=payload.change_reason,
    )
    route_operations_total.labels(route="admin_pricebooks", action="rollback", status="success").inc()
    return _serialize_lifecycle(result)


@router.get("/pricebooks/{pricebook_key}/history", response_model=AdminPricebookHistoryResponse)
async def get_admin_commercial_pricebook_history(
    pricebook_key: str,
    db: AsyncSession = Depends(get_db),
    _: AdminUserModel = Depends(require_role(AdminRole.ADMIN)),
) -> AdminPricebookHistoryResponse:
    use_case = AdminPricebookLifecycleUseCase(db)
    versions = await use_case.list_history(pricebook_key)
    route_operations_total.labels(route="admin_pricebooks", action="history", status="success").inc()
    return AdminPricebookHistoryResponse(
        pricebook_key=pricebook_key,
        versions=[_serialize_version(pricebook) for pricebook in versions],
    )


@router.get("/pricebooks/{pricebook_id}/audit", response_model=list[AuditLogResponse])
async def get_admin_commercial_pricebook_audit(
    pricebook_id: UUID,
    limit: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    _: AdminUserModel = Depends(require_role(AdminRole.ADMIN)),
) -> list[AuditLogResponse]:
    audit_repo = AuditLogRepository(db)
    entries = await audit_repo.get_by_entity(
        PRICEBOOK_AUDIT_RESOURCE_TYPE,
        str(pricebook_id),
        limit=limit,
    )
    route_operations_total.labels(route="admin_pricebooks", action="audit", status="success").inc()
    return entries


@router.post("/pricebooks/{pricebook_id}/validate", response_model=AdminPricebookValidationResponse)
async def validate_admin_commercial_pricebook(
    pricebook_id: UUID,
    db: AsyncSession = Depends(get_db),
    _: AdminUserModel = Depends(require_role(AdminRole.ADMIN)),
) -> AdminPricebookValidationResponse:
    use_case = AdminPricebookLifecycleUseCase(db)
    try:
        issues = await use_case.validate_pricebook(pricebook_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    route_operations_total.labels(route="admin_pricebooks", action="validate", status="success").inc()
    return AdminPricebookValidationResponse(
        pricebook_id=pricebook_id,
        valid=not any(issue.severity == "error" for issue in issues),
        checked_at=datetime.now(UTC),
        issues=[AdminPricebookValidationIssueResponse(**issue.__dict__) for issue in issues],
    )


@router.get("/commercial-context/options", response_model=CommercialContextOptionsResponse)
async def get_admin_commercial_context_options(
    db: AsyncSession = Depends(get_db),
    _: AdminUserModel = Depends(require_role(AdminRole.ADMIN)),
) -> CommercialContextOptionsResponse:
    use_case = AdminCommercialContextOptionsUseCase(db)
    model = await SystemConfigRepository(db).get_by_key(COMMERCIAL_CONTEXT_OPTIONS_CONFIG_KEY)
    options = await use_case.get_options()
    route_operations_total.labels(route="admin_commercial_context", action="get_options", status="success").inc()
    return _serialize_context_options(options, source="system_config" if model is not None else "default")


@router.put("/commercial-context/options", response_model=CommercialContextOptionsResponse)
async def update_admin_commercial_context_options(
    payload: UpdateCommercialContextOptionsRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: AdminUserModel = Depends(require_role(AdminRole.ADMIN)),
) -> CommercialContextOptionsResponse:
    use_case = AdminCommercialContextOptionsUseCase(db)
    data = payload.model_dump(exclude={"change_reason"})
    try:
        previous, updated = await use_case.update_options(data, updated_by=current_user.id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    await write_required_admin_audit_entry(
        db=db,
        action=COMMERCIAL_CONTEXT_OPTIONS_UPDATED_ACTION,
        resource_type="system_config",
        resource_id=COMMERCIAL_CONTEXT_OPTIONS_CONFIG_KEY,
        actor=current_user,
        request=request,
        old_value=previous,
        details={
            **updated,
            "change_reason_length": len(payload.change_reason or ""),
        },
    )
    route_operations_total.labels(route="admin_commercial_context", action="update_options", status="success").inc()
    return _serialize_context_options(updated, source="system_config")


async def _write_pricebook_audit(
    *,
    result: PricebookLifecycleResult,
    request: Request,
    db: AsyncSession,
    actor: AdminUserModel,
    change_reason: str | None,
) -> None:
    await write_required_admin_audit_entry(
        db=db,
        action=result.action,
        resource_type=PRICEBOOK_AUDIT_RESOURCE_TYPE,
        resource_id=result.pricebook.id,
        actor=actor,
        request=request,
        old_value=result.previous,
        details={
            **result.current,
            "change_reason_length": len(change_reason or ""),
        },
    )


def _serialize_lifecycle(result: PricebookLifecycleResult) -> AdminPricebookLifecycleResponse:
    return AdminPricebookLifecycleResponse(
        pricebook=PricebookResponse.model_validate(result.pricebook),
        lifecycle_status=pricebook_lifecycle_status(result.pricebook),
        audit_action=result.action,
    )


def _serialize_version(pricebook: PricebookModel) -> AdminPricebookVersionResponse:
    return AdminPricebookVersionResponse(
        **PricebookResponse.model_validate(pricebook).model_dump(),
        lifecycle_status=pricebook_lifecycle_status(pricebook),
    )


def _serialize_context_options(options: dict, *, source: str) -> CommercialContextOptionsResponse:
    return CommercialContextOptionsResponse(
        countries=[
            CommercialContextCountryOptionResponse(**country)
            for country in options.get("countries", [])
            if country.get("is_enabled", True)
        ],
        currencies=[
            CommercialContextCurrencyOptionResponse(**currency)
            for currency in options.get("currencies", [])
            if currency.get("is_enabled", True)
        ],
        source=source,
    )
