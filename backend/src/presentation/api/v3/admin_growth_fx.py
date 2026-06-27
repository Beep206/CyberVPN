from __future__ import annotations

from collections.abc import Mapping
from datetime import UTC, datetime, timedelta
from decimal import Decimal, InvalidOperation
from typing import Any, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.use_cases.auth.permissions import Permission
from src.application.use_cases.growth_code_sets.fx import (
    FxConversionError,
    FxRateSnapshot,
    conversion_mode_from_payload,
    convert_fixed_discount,
    minor_units_for_currency,
)
from src.infrastructure.database.models.admin_user_model import AdminUserModel
from src.infrastructure.database.models.growth_risk_fx_model import FxRateSnapshotModel
from src.presentation.api.v1.admin.audit import write_required_admin_audit_entry
from src.presentation.dependencies.database import get_db
from src.presentation.dependencies.roles import require_permission

router = APIRouter(prefix="/admin/growth/fx", tags=["admin-growth-fx-v3"])


class AdminGrowthFxRateResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    base_currency: str
    quote_currency: str
    rate: str
    inverse_rate: str | None
    source_type: str
    provider_key: str
    provider_rate_id: str | None
    observed_at: datetime
    fetched_at: datetime
    valid_until: datetime
    status: str
    metadata: dict[str, Any]
    created_at: datetime


class AdminGrowthFxRateListResponse(BaseModel):
    items: list[AdminGrowthFxRateResponse]
    total: int
    limit: int
    offset: int


class AdminGrowthFxStatusResponse(BaseModel):
    generated_at: datetime
    active_rate_count: int
    stale_rate_count: int
    disabled_rate_count: int
    latest_observed_at: datetime | None
    latest_valid_until: datetime | None
    providers: list[dict[str, Any]]


class AdminGrowthFxConfiguredRateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    base_currency: str = Field(..., min_length=3, max_length=12)
    quote_currency: str = Field(..., min_length=3, max_length=12)
    rate: str = Field(..., min_length=1, max_length=80)
    configured_rate_version: str = Field(..., min_length=1, max_length=80)
    valid_for_seconds: int = Field(default=3600, ge=60, le=2_592_000)
    provider_rate_id: str | None = Field(default=None, max_length=160)
    change_reason: str = Field(..., min_length=3, max_length=2000)

    @field_validator("base_currency", "quote_currency")
    @classmethod
    def _currency(cls, value: str) -> str:
        stripped = value.strip().upper()
        if not stripped:
            raise ValueError("currency must not be blank")
        return stripped


class AdminGrowthFxXtrTableRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    fiat_currency: str = Field(..., min_length=3, max_length=12)
    xtr_per_unit: str = Field(..., min_length=1, max_length=80)
    table_version: str = Field(..., min_length=1, max_length=80)
    valid_for_seconds: int = Field(default=86_400, ge=60, le=2_592_000)
    change_reason: str = Field(..., min_length=3, max_length=2000)

    @field_validator("fiat_currency")
    @classmethod
    def _fiat_currency(cls, value: str) -> str:
        stripped = value.strip().upper()
        if stripped == "XTR" or not stripped:
            raise ValueError("fiat_currency must be a non-XTR currency")
        return stripped


class AdminGrowthFxProviderActionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    change_reason: str = Field(..., min_length=3, max_length=2000)


class AdminGrowthFxSimulateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source_amount: str = Field(..., min_length=1, max_length=80)
    source_currency: str = Field(..., min_length=3, max_length=12)
    target_currency: str = Field(..., min_length=3, max_length=12)
    eligible_discount_base: str = Field(..., min_length=1, max_length=80)
    conversion_mode: Literal["market", "configured", "pricebook", "managed_xtr"] = "market"
    provider_key: str | None = Field(default=None, max_length=80)

    @field_validator("source_currency", "target_currency")
    @classmethod
    def _simulate_currency(cls, value: str) -> str:
        stripped = value.strip().upper()
        if not stripped:
            raise ValueError("currency must not be blank")
        return stripped


class AdminGrowthFxSimulationResponse(BaseModel):
    source_amount: str
    source_currency: str
    target_currency: str
    raw_converted_amount: str
    rounded_amount: str
    applied_amount: str
    target_minor_units: int
    rounding_mode: str
    conversion_mode: str
    rate_snapshot: dict[str, Any]
    no_rerate: bool


@router.get("/status", response_model=AdminGrowthFxStatusResponse)
async def get_growth_fx_status(
    _current_user: AdminUserModel = Depends(require_permission(Permission.GROWTH_FX_VIEW)),
    db: AsyncSession = Depends(get_db),
) -> AdminGrowthFxStatusResponse:
    now = datetime.now(UTC)
    active_rate_count = int(
        await db.scalar(
            select(func.count()).where(
                FxRateSnapshotModel.status == "active",
                FxRateSnapshotModel.valid_until >= now,
            )
        )
        or 0
    )
    stale_rate_count = int(
        await db.scalar(
            select(func.count()).where(
                FxRateSnapshotModel.status == "active",
                FxRateSnapshotModel.valid_until < now,
            )
        )
        or 0
    )
    disabled_rate_count = int(
        await db.scalar(select(func.count()).where(FxRateSnapshotModel.status == "disabled")) or 0
    )
    latest_observed_at = await db.scalar(select(func.max(FxRateSnapshotModel.observed_at)))
    latest_valid_until = await db.scalar(select(func.max(FxRateSnapshotModel.valid_until)))
    provider_rows = await db.execute(
        select(
            FxRateSnapshotModel.provider_key,
            FxRateSnapshotModel.source_type,
            FxRateSnapshotModel.status,
            func.count(),
            func.max(FxRateSnapshotModel.observed_at),
        )
        .group_by(FxRateSnapshotModel.provider_key, FxRateSnapshotModel.source_type, FxRateSnapshotModel.status)
        .order_by(FxRateSnapshotModel.provider_key.asc(), FxRateSnapshotModel.source_type.asc())
    )
    return AdminGrowthFxStatusResponse(
        generated_at=now,
        active_rate_count=active_rate_count,
        stale_rate_count=stale_rate_count,
        disabled_rate_count=disabled_rate_count,
        latest_observed_at=latest_observed_at,
        latest_valid_until=latest_valid_until,
        providers=[
            {
                "provider_key": row[0],
                "source_type": row[1],
                "status": row[2],
                "rate_count": int(row[3]),
                "latest_observed_at": row[4].isoformat() if row[4] else None,
            }
            for row in provider_rows.all()
        ],
    )


@router.get("/rates", response_model=AdminGrowthFxRateListResponse)
async def list_growth_fx_rates(
    base_currency: str | None = Query(default=None, min_length=3, max_length=12),
    quote_currency: str | None = Query(default=None, min_length=3, max_length=12),
    provider_key: str | None = Query(default=None, min_length=1, max_length=80),
    source_type: str | None = Query(default=None, min_length=1, max_length=30),
    status_filter: str | None = Query(default=None, alias="status", min_length=1, max_length=20),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    _current_user: AdminUserModel = Depends(require_permission(Permission.GROWTH_FX_VIEW)),
    db: AsyncSession = Depends(get_db),
) -> AdminGrowthFxRateListResponse:
    statement = select(FxRateSnapshotModel)
    if base_currency is not None:
        statement = statement.where(FxRateSnapshotModel.base_currency == base_currency.upper())
    if quote_currency is not None:
        statement = statement.where(FxRateSnapshotModel.quote_currency == quote_currency.upper())
    if provider_key is not None:
        statement = statement.where(FxRateSnapshotModel.provider_key == provider_key)
    if source_type is not None:
        statement = statement.where(FxRateSnapshotModel.source_type == source_type)
    if status_filter is not None:
        statement = statement.where(FxRateSnapshotModel.status == status_filter)
    total = await _count_for(statement, db)
    result = await db.execute(statement.order_by(FxRateSnapshotModel.observed_at.desc()).limit(limit).offset(offset))
    return AdminGrowthFxRateListResponse(
        items=[_rate_response(item) for item in result.scalars().all()],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.post("/configured-rates", response_model=AdminGrowthFxRateResponse, status_code=status.HTTP_201_CREATED)
async def create_configured_growth_fx_rate(
    payload: AdminGrowthFxConfiguredRateRequest,
    request: Request,
    current_user: AdminUserModel = Depends(require_permission(Permission.GROWTH_FX_OVERRIDE)),
    db: AsyncSession = Depends(get_db),
) -> AdminGrowthFxRateResponse:
    rate = _parse_positive_decimal(payload.rate, "FX_RATE_INVALID")
    now = datetime.now(UTC)
    model = FxRateSnapshotModel(
        base_currency=payload.base_currency,
        quote_currency=payload.quote_currency,
        rate=rate,
        inverse_rate=(Decimal("1") / rate),
        source_type="configured",
        provider_key="admin_configured",
        provider_rate_id=payload.provider_rate_id,
        observed_at=now,
        fetched_at=now,
        valid_until=now + timedelta(seconds=payload.valid_for_seconds),
        status="pending_approval",
        metadata_={
            "configured_rate_version": payload.configured_rate_version,
            "created_by_admin_user_id": str(current_user.id),
            "change_reason": payload.change_reason,
        },
    )
    db.add(model)
    await db.flush()
    await write_required_admin_audit_entry(
        db=db,
        action="growth_fx.configured_rate.created",
        resource_type="fx_rate_snapshot",
        resource_id=model.id,
        actor=current_user,
        request=request,
        details={
            "base_currency": model.base_currency,
            "quote_currency": model.quote_currency,
            "source_type": model.source_type,
            "provider_key": model.provider_key,
            "configured_rate_version": payload.configured_rate_version,
            "change_reason": payload.change_reason,
        },
    )
    return _rate_response(model)


@router.post("/xtr-tables", response_model=AdminGrowthFxRateResponse, status_code=status.HTTP_201_CREATED)
async def create_growth_fx_xtr_table(
    payload: AdminGrowthFxXtrTableRequest,
    request: Request,
    current_user: AdminUserModel = Depends(require_permission(Permission.GROWTH_FX_OVERRIDE)),
    db: AsyncSession = Depends(get_db),
) -> AdminGrowthFxRateResponse:
    rate = _parse_positive_decimal(payload.xtr_per_unit, "FX_XTR_TABLE_INVALID")
    now = datetime.now(UTC)
    model = FxRateSnapshotModel(
        base_currency=payload.fiat_currency,
        quote_currency="XTR",
        rate=rate,
        inverse_rate=(Decimal("1") / rate),
        source_type="managed_xtr",
        provider_key="admin_xtr_table",
        provider_rate_id=payload.table_version,
        observed_at=now,
        fetched_at=now,
        valid_until=now + timedelta(seconds=payload.valid_for_seconds),
        status="pending_approval",
        metadata_={
            "managed_xtr": True,
            "configured_rate_version": payload.table_version,
            "created_by_admin_user_id": str(current_user.id),
            "change_reason": payload.change_reason,
        },
    )
    db.add(model)
    await db.flush()
    await write_required_admin_audit_entry(
        db=db,
        action="growth_fx.xtr_table.created",
        resource_type="fx_rate_snapshot",
        resource_id=model.id,
        actor=current_user,
        request=request,
        details={
            "base_currency": model.base_currency,
            "quote_currency": model.quote_currency,
            "source_type": model.source_type,
            "provider_key": model.provider_key,
            "table_version": payload.table_version,
            "change_reason": payload.change_reason,
        },
    )
    return _rate_response(model)


@router.post("/simulate", response_model=AdminGrowthFxSimulationResponse)
async def simulate_growth_fx_conversion(
    payload: AdminGrowthFxSimulateRequest,
    _current_user: AdminUserModel = Depends(require_permission(Permission.GROWTH_FX_VIEW)),
    db: AsyncSession = Depends(get_db),
) -> AdminGrowthFxSimulationResponse:
    rate_statement = select(FxRateSnapshotModel).where(
        FxRateSnapshotModel.base_currency == payload.source_currency,
        FxRateSnapshotModel.quote_currency == payload.target_currency,
        FxRateSnapshotModel.status == "active",
    )
    if payload.provider_key is not None:
        rate_statement = rate_statement.where(FxRateSnapshotModel.provider_key == payload.provider_key)
    if payload.conversion_mode == "managed_xtr":
        rate_statement = rate_statement.where(FxRateSnapshotModel.source_type == "managed_xtr")
    elif payload.conversion_mode == "configured":
        rate_statement = rate_statement.where(FxRateSnapshotModel.source_type == "configured")
    elif payload.conversion_mode == "pricebook":
        rate_statement = rate_statement.where(FxRateSnapshotModel.source_type == "pricebook")
    result = await db.execute(rate_statement.order_by(FxRateSnapshotModel.observed_at.desc()).limit(20))
    rates = [_rate_snapshot(item) for item in result.scalars().all()]
    source_amount = _parse_positive_decimal(payload.source_amount, "FX_AMOUNT_INVALID")
    try:
        conversion = convert_fixed_discount(
            source_amount=source_amount,
            source_currency=payload.source_currency,
            quote_currency=payload.target_currency,
            discountable_amount=_parse_positive_decimal(payload.eligible_discount_base, "FX_AMOUNT_INVALID"),
            rate_snapshots=rates,
        )
    except FxConversionError as exc:
        raise _admin_growth_error(
            status.HTTP_409_CONFLICT,
            exc.code,
            f"admin.growth.fx.errors.{exc.code.lower()}",
            {
                "source_currency": payload.source_currency,
                "target_currency": payload.target_currency,
                "conversion_mode": payload.conversion_mode,
            },
        ) from exc
    conversion_payload = conversion.to_payload()
    rate_snapshot = conversion_payload.get("rate_snapshot")
    rate_snapshot_payload = rate_snapshot if isinstance(rate_snapshot, dict) else {}
    raw_converted_amount = (
        source_amount * Decimal(str(rate_snapshot_payload["rate"]))
        if rate_snapshot_payload
        else conversion.target_amount
    )
    return AdminGrowthFxSimulationResponse(
        source_amount=format(conversion.source_amount, "f"),
        source_currency=conversion.source_currency,
        target_currency=conversion.target_currency,
        raw_converted_amount=format(raw_converted_amount, "f"),
        rounded_amount=format(conversion.target_amount, "f"),
        applied_amount=format(conversion.applied_amount, "f"),
        target_minor_units=minor_units_for_currency(conversion.target_currency),
        rounding_mode=str(rate_snapshot_payload.get("rounding_mode") or "ROUND_HALF_UP"),
        conversion_mode=conversion_mode_from_payload(rate_snapshot_payload or None),
        rate_snapshot=rate_snapshot_payload,
        no_rerate=True,
    )


@router.post("/rates/{rate_id}/approve", response_model=AdminGrowthFxRateResponse)
async def approve_growth_fx_rate(
    rate_id: UUID,
    payload: AdminGrowthFxProviderActionRequest,
    request: Request,
    current_user: AdminUserModel = Depends(require_permission(Permission.GROWTH_FX_APPROVE)),
    db: AsyncSession = Depends(get_db),
) -> AdminGrowthFxRateResponse:
    model = await db.get(FxRateSnapshotModel, rate_id)
    if model is None:
        raise _admin_growth_error(
            status.HTTP_404_NOT_FOUND,
            "FX_RATE_NOT_FOUND",
            "admin.growth.fx.errors.rateNotFound",
            {"rate_id": str(rate_id)},
        )
    metadata = dict(model.metadata_ or {})
    if model.source_type not in {"configured", "managed_xtr"}:
        raise _admin_growth_error(
            status.HTTP_409_CONFLICT,
            "FX_RATE_APPROVAL_UNSUPPORTED",
            "admin.growth.fx.errors.approvalUnsupported",
            {"rate_id": str(rate_id), "source_type": model.source_type},
        )
    if metadata.get("created_by_admin_user_id") == str(current_user.id):
        raise _admin_growth_error(
            status.HTTP_409_CONFLICT,
            "FX_RATE_SELF_APPROVAL_FORBIDDEN",
            "admin.growth.fx.errors.selfApprovalForbidden",
            {"rate_id": str(rate_id)},
        )
    if model.status != "pending_approval":
        raise _admin_growth_error(
            status.HTTP_409_CONFLICT,
            "FX_RATE_APPROVAL_STATE_CONFLICT",
            "admin.growth.fx.errors.approvalStateConflict",
            {"rate_id": str(rate_id), "status": model.status},
        )

    old_status = model.status
    model.status = "active"
    metadata.update(
        {
            "approved_by_admin_user_id": str(current_user.id),
            "approved_at": datetime.now(UTC).isoformat(),
            "approval_reason": payload.change_reason,
        }
    )
    model.metadata_ = metadata
    await db.flush()
    await write_required_admin_audit_entry(
        db=db,
        action="growth_fx.rate.approved",
        resource_type="fx_rate_snapshot",
        resource_id=model.id,
        actor=current_user,
        request=request,
        old_value={"status": old_status},
        details={
            "base_currency": model.base_currency,
            "quote_currency": model.quote_currency,
            "source_type": model.source_type,
            "provider_key": model.provider_key,
            "change_reason": payload.change_reason,
        },
    )
    return _rate_response(model)


@router.post("/providers/{provider_key}/disable", response_model=AdminGrowthFxStatusResponse)
async def disable_growth_fx_provider(
    provider_key: str,
    payload: AdminGrowthFxProviderActionRequest,
    request: Request,
    current_user: AdminUserModel = Depends(require_permission(Permission.GROWTH_FX_MANAGE)),
    db: AsyncSession = Depends(get_db),
) -> AdminGrowthFxStatusResponse:
    updated_count = await _set_provider_status(db, provider_key=provider_key, next_status="disabled")
    await write_required_admin_audit_entry(
        db=db,
        action="growth_fx.provider.disabled",
        resource_type="fx_provider",
        resource_id=provider_key,
        actor=current_user,
        request=request,
        details={
            "provider_key": provider_key,
            "updated_rate_count": updated_count,
            "change_reason": payload.change_reason,
        },
    )
    return await get_growth_fx_status(current_user, db)


@router.post("/providers/{provider_key}/enable", response_model=AdminGrowthFxStatusResponse)
async def enable_growth_fx_provider(
    provider_key: str,
    payload: AdminGrowthFxProviderActionRequest,
    request: Request,
    current_user: AdminUserModel = Depends(require_permission(Permission.GROWTH_FX_MANAGE)),
    db: AsyncSession = Depends(get_db),
) -> AdminGrowthFxStatusResponse:
    updated_count = await _set_provider_status(db, provider_key=provider_key, next_status="active")
    await write_required_admin_audit_entry(
        db=db,
        action="growth_fx.provider.enabled",
        resource_type="fx_provider",
        resource_id=provider_key,
        actor=current_user,
        request=request,
        details={
            "provider_key": provider_key,
            "updated_rate_count": updated_count,
            "change_reason": payload.change_reason,
        },
    )
    return await get_growth_fx_status(current_user, db)


async def _set_provider_status(db: AsyncSession, *, provider_key: str, next_status: str) -> int:
    result = await db.execute(select(FxRateSnapshotModel).where(FxRateSnapshotModel.provider_key == provider_key))
    models = result.scalars().all()
    updated_count = 0
    for model in models:
        if next_status == "active" and model.status == "pending_approval":
            continue
        if model.status == next_status:
            continue
        model.status = next_status
        updated_count += 1
    await db.flush()
    return updated_count


def _rate_response(model: FxRateSnapshotModel) -> AdminGrowthFxRateResponse:
    return AdminGrowthFxRateResponse(
        id=model.id,
        base_currency=model.base_currency,
        quote_currency=model.quote_currency,
        rate=format(model.rate, "f"),
        inverse_rate=format(model.inverse_rate, "f") if model.inverse_rate is not None else None,
        source_type=model.source_type,
        provider_key=model.provider_key,
        provider_rate_id=model.provider_rate_id,
        observed_at=model.observed_at,
        fetched_at=model.fetched_at,
        valid_until=model.valid_until,
        status=model.status,
        metadata=dict(model.metadata_ or {}),
        created_at=model.created_at,
    )


def _rate_snapshot(model: FxRateSnapshotModel) -> FxRateSnapshot:
    metadata = dict(model.metadata_ or {})
    return FxRateSnapshot(
        rate_id=model.id,
        provider=model.provider_key,
        provider_priority=int(metadata.get("provider_priority") or 100),
        source_currency=model.base_currency,
        target_currency=model.quote_currency,
        rate=Decimal(model.rate),
        fetched_at=model.fetched_at,
        expires_at=model.valid_until,
        rounding_mode=str(metadata.get("rounding_mode") or "ROUND_HALF_UP"),
        managed_xtr=bool(metadata.get("managed_xtr") or model.source_type == "managed_xtr"),
        source_type=model.source_type,
        configured_rate_version=(
            str(metadata.get("configured_rate_version"))
            if metadata.get("configured_rate_version") not in (None, "")
            else None
        ),
    )


async def _count_for(statement: Select[tuple[Any]], db: AsyncSession) -> int:
    count_statement = select(func.count()).select_from(statement.order_by(None).limit(None).offset(None).subquery())
    return int(await db.scalar(count_statement) or 0)


def _parse_positive_decimal(value: str, code: str) -> Decimal:
    try:
        parsed = Decimal(value)
    except (InvalidOperation, ValueError) as exc:
        raise _admin_growth_error(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            code,
            "admin.growth.fx.errors.amountInvalid",
            {"value": value},
        ) from exc
    if parsed <= 0:
        raise _admin_growth_error(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            code,
            "admin.growth.fx.errors.amountInvalid",
            {"value": value},
        )
    return parsed


def _admin_growth_error(
    status_code: int,
    code: str,
    message_key: str,
    debug_context: Mapping[str, Any] | None = None,
) -> HTTPException:
    return HTTPException(
        status_code=status_code,
        detail={
            "code": code,
            "message_key": message_key,
            "retryable": False,
            "debug_context": dict(debug_context or {}),
        },
    )
