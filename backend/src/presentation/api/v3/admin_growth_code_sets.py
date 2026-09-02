from __future__ import annotations

import hashlib
from collections.abc import Mapping
from decimal import Decimal
from typing import Any, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.use_cases.auth.permissions import Permission
from src.application.use_cases.payments.checkout import CheckoutCodeBasketInput, CheckoutUseCase
from src.infrastructure.database.models.admin_user_model import AdminUserModel
from src.infrastructure.database.models.growth_code_model import GrowthCodeReservationModel
from src.infrastructure.database.models.growth_code_set_model import (
    CheckoutCodeApplicationModel,
    CheckoutCodeSetModel,
    GrowthCodeReservationGroupModel,
    OrderCodeApplicationModel,
)
from src.infrastructure.database.models.growth_risk_fx_model import FxDiscountConversionModel
from src.presentation.dependencies.database import get_db
from src.presentation.dependencies.roles import require_permission
from src.shared.logging.sanitization import REDACTED

router = APIRouter(prefix="/admin/growth", tags=["admin-growth-code-sets-v3"])

_SENSITIVE_KEY_PARTS = (
    "raw_code",
    "rawcode",
    "code_input",
    "codeinput",
    "grant_token",
    "token",
    "secret",
    "password",
    "authorization",
    "cookie",
    "init_data",
    "initdata",
)


class AdminGrowthCodeSetApplicationResponse(BaseModel):
    id: UUID
    position_entered: int
    canonical_order: int
    growth_code_id: UUID | None
    legacy_code_type: str | None
    legacy_code_id: UUID | None
    masked_code: str
    roles: dict[str, Any]
    resolution_status: str
    reject_reason: str | None
    conflict_code: str | None
    policy_version_id: UUID | None
    rule_definition_id: UUID | None
    risk_decision_id: UUID | None
    fx_conversion_id: UUID | None
    reservation_id: UUID | None
    discount_snapshot: dict[str, Any]
    benefits_snapshot: dict[str, Any]
    private_access_snapshot: dict[str, Any]
    evaluation_trace: dict[str, Any]


class AdminGrowthReservationResponse(BaseModel):
    id: UUID
    growth_code_id: UUID
    reservation_group_id: UUID | None
    quote_session_id: UUID | None
    checkout_session_id: UUID | None
    user_id: UUID | None
    risk_subject_id: UUID | None
    risk_decision_id: UUID | None
    device_key_hash: str | None
    velocity_bucket: str | None
    status: str
    reserved_at: str
    expires_at: str
    committed_at: str | None
    consumed_at: str | None
    consumed_order_id: UUID | None
    consumed_payment_id: UUID | None
    released_at: str | None
    release_reason: str | None
    capacity_context: dict[str, Any]


class AdminGrowthReservationGroupResponse(BaseModel):
    id: UUID
    code_set_id: UUID
    status: str
    user_id: UUID | None
    quote_session_id: UUID | None
    checkout_session_id: UUID | None
    order_id: UUID | None
    payment_id: UUID | None
    reserved_at: str
    expires_at: str
    committed_at: str | None
    consumed_at: str | None
    released_at: str | None
    release_reason: str | None
    idempotency_key_hash: str


class AdminGrowthOrderApplicationResponse(BaseModel):
    id: UUID
    order_id: UUID
    code_set_id: UUID
    growth_code_id: UUID
    policy_version_id: UUID | None
    application_role: str
    application_status: str
    discount_amount: str
    currency_code: str
    source_amount: str | None
    source_currency_code: str | None
    fx_conversion_id: UUID | None
    reservation_id: UUID | None
    risk_decision_id: UUID | None
    application_snapshot: dict[str, Any]


class AdminGrowthFxConversionResponse(BaseModel):
    id: UUID
    growth_code_id: UUID
    policy_version_id: UUID
    source_amount: str
    source_currency: str
    target_currency: str
    conversion_mode: str
    fx_rate_snapshot_id: UUID | None
    configured_rate_version: str | None
    raw_converted_amount: str
    rounded_amount: str
    applied_amount: str
    target_minor_units: int
    rounding_mode: str


class AdminGrowthCodeSetInspectItemResponse(BaseModel):
    id: UUID
    code_set_hash: str
    user_id: UUID | None
    anonymous_session_id_hash: str | None
    auth_realm_id: UUID
    storefront_id: UUID | None
    sale_channel: str
    action_context: str
    status: str
    acceptance_mode: str
    aggregate_result: dict[str, Any]
    risk_snapshot: dict[str, Any]
    private_access_grant_id: UUID | None
    quote_session_id: UUID | None
    checkout_session_id: UUID | None
    order_id: UUID | None
    payment_id: UUID | None
    applications: list[AdminGrowthCodeSetApplicationResponse]
    reservation_groups: list[AdminGrowthReservationGroupResponse]
    reservations: list[AdminGrowthReservationResponse]
    order_applications: list[AdminGrowthOrderApplicationResponse]
    fx_conversions: list[AdminGrowthFxConversionResponse]


class AdminGrowthCodeSetInspectResponse(BaseModel):
    items: list[AdminGrowthCodeSetInspectItemResponse]
    total: int
    limit: int
    offset: int


class AdminGrowthCodeSetSimulationRequest(BaseModel):
    codes: list[str] = Field(default_factory=list, min_length=1, max_length=5)
    user_id: UUID
    plan_id: UUID
    currency: str = Field(default="USD", min_length=3, max_length=12)
    sale_channel: str = Field(default="web", min_length=1, max_length=40)
    storefront_id: UUID | None = None
    private_catalog_grant_id: UUID | None = None
    dry_run: Literal[True] = True


class AdminGrowthCodeSetSimulationResponse(BaseModel):
    accepted: bool
    dry_run: bool
    code_set_hash: str | None
    acceptance_mode: str
    applications: list[AdminGrowthCodeSetApplicationResponse]
    base_price: str
    discount_amount: str
    wallet_amount: str
    gateway_amount: str
    is_zero_gateway: bool
    settlement_mode: str
    trace: dict[str, Any]


class AdminGrowthCodeApplicationDetailResponse(BaseModel):
    application: AdminGrowthCodeSetApplicationResponse
    code_set: AdminGrowthCodeSetInspectItemResponse | None


class AdminGrowthOrderCodeApplicationsResponse(BaseModel):
    items: list[AdminGrowthOrderApplicationResponse]
    total: int


@router.post("/code-sets/simulate", response_model=AdminGrowthCodeSetSimulationResponse)
async def simulate_growth_code_set(
    payload: AdminGrowthCodeSetSimulationRequest,
    _current_user: AdminUserModel = Depends(require_permission(Permission.GROWTH_CODE_SETS_INSPECT)),
    db: AsyncSession = Depends(get_db),
) -> AdminGrowthCodeSetSimulationResponse:
    simulation_tx = await db.begin_nested()
    try:
        result = await CheckoutUseCase(db).execute(
            user_id=payload.user_id,
            plan_id=payload.plan_id,
            currency=payload.currency,
            code_basket=[CheckoutCodeBasketInput(code=code) for code in payload.codes],
            sale_channel=payload.sale_channel,
            storefront_id=payload.storefront_id,
            private_catalog_grant_id=payload.private_catalog_grant_id,
        )
        applications = [
            _simulation_application_response_from_payload(application) for application in result.code_set_applications
        ]
        return AdminGrowthCodeSetSimulationResponse(
            accepted=all(application.resolution_status == "accepted" for application in applications),
            dry_run=True,
            code_set_hash=result.code_set_hash,
            acceptance_mode=result.code_set_acceptance_mode or "all_or_nothing",
            applications=applications,
            base_price=_decimal(result.base_price),
            discount_amount=_decimal(result.discount_amount),
            wallet_amount=_decimal(result.wallet_amount),
            gateway_amount=_decimal(result.gateway_amount),
            is_zero_gateway=result.is_zero_gateway,
            settlement_mode="internal_zero" if result.is_zero_gateway else "external_gateway",
            trace={
                "application_count": len(applications),
                "private_catalog_grant_id": str(result.private_catalog_grant_id)
                if result.private_catalog_grant_id
                else None,
                "reservation_created": False,
                "payment_created": False,
                "risk_decision_persisted": False,
            },
        )
    except ValueError as exc:
        raise _admin_growth_error(
            status.HTTP_409_CONFLICT,
            "CODE_SET_SIMULATION_REJECTED",
            "admin.growth.codeSets.errors.simulationRejected",
            {"reason": str(exc)},
        ) from exc
    finally:
        if simulation_tx.is_active:
            await simulation_tx.rollback()


@router.get("/code-sets/inspect", response_model=AdminGrowthCodeSetInspectResponse)
async def inspect_growth_code_sets(
    code_set_id: UUID | None = None,
    code_set_hash: str | None = Query(default=None, min_length=8, max_length=128),
    quote_session_id: UUID | None = None,
    checkout_session_id: UUID | None = None,
    order_id: UUID | None = None,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    _current_user: AdminUserModel = Depends(require_permission(Permission.GROWTH_CODE_SETS_INSPECT)),
    db: AsyncSession = Depends(get_db),
) -> AdminGrowthCodeSetInspectResponse:
    if not any((code_set_id, code_set_hash, quote_session_id, checkout_session_id, order_id)):
        raise _admin_growth_error(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            "CODE_SET_INSPECT_FILTER_REQUIRED",
            "admin.growth.codeSets.errors.filterRequired",
        )

    statement = select(CheckoutCodeSetModel)
    if code_set_id is not None:
        statement = statement.where(CheckoutCodeSetModel.id == code_set_id)
    if code_set_hash is not None:
        statement = statement.where(CheckoutCodeSetModel.code_set_hash == code_set_hash)
    if quote_session_id is not None:
        statement = statement.where(CheckoutCodeSetModel.quote_session_id == quote_session_id)
    if checkout_session_id is not None:
        statement = statement.where(CheckoutCodeSetModel.checkout_session_id == checkout_session_id)
    if order_id is not None:
        statement = statement.where(CheckoutCodeSetModel.order_id == order_id)

    total = await _count_for(statement, db)
    result = await db.execute(statement.order_by(CheckoutCodeSetModel.created_at.desc()).limit(limit).offset(offset))
    code_sets = list(result.scalars().all())
    related_rows = await _related_rows(db, code_sets)
    items = [_inspect_item(code_set, related) for code_set, related in zip(code_sets, related_rows, strict=True)]
    return AdminGrowthCodeSetInspectResponse(items=items, total=total, limit=limit, offset=offset)


@router.get("/code-sets/{code_set_id}", response_model=AdminGrowthCodeSetInspectItemResponse)
async def get_growth_code_set_support_view(
    code_set_id: UUID,
    _current_user: AdminUserModel = Depends(require_permission(Permission.GROWTH_CODE_SETS_INSPECT)),
    db: AsyncSession = Depends(get_db),
) -> AdminGrowthCodeSetInspectItemResponse:
    response = await inspect_growth_code_sets(
        code_set_id=code_set_id,
        code_set_hash=None,
        quote_session_id=None,
        checkout_session_id=None,
        order_id=None,
        limit=1,
        offset=0,
        _current_user=_current_user,
        db=db,
    )
    if not response.items:
        raise _admin_growth_error(
            status.HTTP_404_NOT_FOUND,
            "CODE_SET_NOT_FOUND",
            "admin.growth.codeSets.errors.notFound",
            {"code_set_id": str(code_set_id)},
        )
    return response.items[0]


@router.get("/code-applications/{application_id}", response_model=AdminGrowthCodeApplicationDetailResponse)
async def get_growth_code_application_support_view(
    application_id: UUID,
    _current_user: AdminUserModel = Depends(require_permission(Permission.GROWTH_CODE_SETS_INSPECT)),
    db: AsyncSession = Depends(get_db),
) -> AdminGrowthCodeApplicationDetailResponse:
    application = await db.get(CheckoutCodeApplicationModel, application_id)
    if application is None:
        raise _admin_growth_error(
            status.HTTP_404_NOT_FOUND,
            "CODE_APPLICATION_NOT_FOUND",
            "admin.growth.codeSets.errors.applicationNotFound",
            {"application_id": str(application_id)},
        )
    code_set_response = await get_growth_code_set_support_view(application.code_set_id, _current_user, db)
    return AdminGrowthCodeApplicationDetailResponse(
        application=_application_response(application),
        code_set=code_set_response,
    )


@router.get("/orders/{order_id}/code-applications", response_model=AdminGrowthOrderCodeApplicationsResponse)
async def list_order_growth_code_applications(
    order_id: UUID,
    _current_user: AdminUserModel = Depends(require_permission(Permission.GROWTH_CODE_SETS_INSPECT)),
    db: AsyncSession = Depends(get_db),
) -> AdminGrowthOrderCodeApplicationsResponse:
    result = await db.execute(
        select(OrderCodeApplicationModel)
        .where(OrderCodeApplicationModel.order_id == order_id)
        .order_by(OrderCodeApplicationModel.created_at.desc())
    )
    items = [_order_application_response(item) for item in result.scalars().all()]
    return AdminGrowthOrderCodeApplicationsResponse(items=items, total=len(items))


async def _related_rows(
    db: AsyncSession,
    code_sets: list[CheckoutCodeSetModel],
) -> list[dict[str, list[Any]]]:
    if not code_sets:
        return []
    code_set_ids = [item.id for item in code_sets]
    applications = (
        (
            await db.execute(
                select(CheckoutCodeApplicationModel)
                .where(CheckoutCodeApplicationModel.code_set_id.in_(code_set_ids))
                .order_by(CheckoutCodeApplicationModel.canonical_order.asc())
            )
        )
        .scalars()
        .all()
    )
    reservation_groups = (
        (
            await db.execute(
                select(GrowthCodeReservationGroupModel)
                .where(GrowthCodeReservationGroupModel.code_set_id.in_(code_set_ids))
                .order_by(GrowthCodeReservationGroupModel.reserved_at.desc())
            )
        )
        .scalars()
        .all()
    )
    reservation_ids = [item.reservation_id for item in applications if item.reservation_id is not None]
    reservations = (
        (
            await db.execute(
                select(GrowthCodeReservationModel)
                .where(GrowthCodeReservationModel.id.in_(reservation_ids))
                .order_by(GrowthCodeReservationModel.reserved_at.desc())
            )
        )
        .scalars()
        .all()
        if reservation_ids
        else []
    )
    order_applications = (
        (
            await db.execute(
                select(OrderCodeApplicationModel)
                .where(OrderCodeApplicationModel.code_set_id.in_(code_set_ids))
                .order_by(OrderCodeApplicationModel.created_at.desc())
            )
        )
        .scalars()
        .all()
    )
    fx_conversion_ids = [item.fx_conversion_id for item in applications if item.fx_conversion_id is not None]
    fx_conversions = (
        (
            await db.execute(
                select(FxDiscountConversionModel)
                .where(FxDiscountConversionModel.id.in_(fx_conversion_ids))
                .order_by(FxDiscountConversionModel.created_at.desc())
            )
        )
        .scalars()
        .all()
        if fx_conversion_ids
        else []
    )
    related: list[dict[str, list[Any]]] = []
    for code_set in code_sets:
        application_ids = {application.id for application in applications if application.code_set_id == code_set.id}
        related.append(
            {
                "applications": [item for item in applications if item.code_set_id == code_set.id],
                "reservation_groups": [item for item in reservation_groups if item.code_set_id == code_set.id],
                "reservations": [
                    item
                    for item in reservations
                    if any(
                        application.reservation_id == item.id
                        for application in applications
                        if application.code_set_id == code_set.id
                    )
                ],
                "order_applications": [item for item in order_applications if item.code_set_id == code_set.id],
                "fx_conversions": [item for item in fx_conversions if item.code_application_id in application_ids],
            }
        )
    return related


def _inspect_item(
    code_set: CheckoutCodeSetModel,
    related: Mapping[str, list[Any]],
) -> AdminGrowthCodeSetInspectItemResponse:
    return AdminGrowthCodeSetInspectItemResponse(
        id=code_set.id,
        code_set_hash=code_set.code_set_hash,
        user_id=code_set.user_id,
        anonymous_session_id_hash=_hash_optional(code_set.anonymous_session_id),
        auth_realm_id=code_set.auth_realm_id,
        storefront_id=code_set.storefront_id,
        sale_channel=code_set.sale_channel,
        action_context=code_set.action_context,
        status=code_set.status,
        acceptance_mode=code_set.acceptance_mode,
        aggregate_result=_safe_json(code_set.aggregate_result),
        risk_snapshot=_safe_json(code_set.risk_snapshot),
        private_access_grant_id=code_set.private_access_grant_id,
        quote_session_id=code_set.quote_session_id,
        checkout_session_id=code_set.checkout_session_id,
        order_id=code_set.order_id,
        payment_id=code_set.payment_id,
        applications=[_application_response(item) for item in related["applications"]],
        reservation_groups=[_reservation_group_response(item) for item in related["reservation_groups"]],
        reservations=[_reservation_response(item) for item in related["reservations"]],
        order_applications=[_order_application_response(item) for item in related["order_applications"]],
        fx_conversions=[_fx_conversion_response(item) for item in related["fx_conversions"]],
    )


def _application_response(application: CheckoutCodeApplicationModel) -> AdminGrowthCodeSetApplicationResponse:
    return AdminGrowthCodeSetApplicationResponse(
        id=application.id,
        position_entered=application.position_entered,
        canonical_order=application.canonical_order,
        growth_code_id=application.growth_code_id,
        legacy_code_type=application.legacy_code_type,
        legacy_code_id=application.legacy_code_id,
        masked_code=application.masked_code,
        roles=_roles_json(application.roles),
        resolution_status=application.resolution_status,
        reject_reason=application.reject_reason,
        conflict_code=application.conflict_code,
        policy_version_id=application.policy_version_id,
        rule_definition_id=application.rule_definition_id,
        risk_decision_id=application.risk_decision_id,
        fx_conversion_id=application.fx_conversion_id,
        reservation_id=application.reservation_id,
        discount_snapshot=_safe_json(application.discount_snapshot),
        benefits_snapshot=_safe_json(application.benefits_snapshot),
        private_access_snapshot=_safe_json(application.private_access_snapshot),
        evaluation_trace=_safe_json(application.evaluation_trace),
    )


def _application_response_from_payload(application: Mapping[str, Any]) -> AdminGrowthCodeSetApplicationResponse:
    return AdminGrowthCodeSetApplicationResponse(
        id=_stable_payload_uuid(application),
        position_entered=int(application.get("position_entered") or 0),
        canonical_order=int(application.get("canonical_order") or application.get("position_entered") or 0),
        growth_code_id=_uuid_or_none(application.get("growth_code_id")),
        legacy_code_type=_string_or_none(application.get("legacy_code_type")),
        legacy_code_id=_uuid_or_none(application.get("legacy_code_id")),
        masked_code=str(application.get("masked_code") or "****"),
        roles=_roles_json(application.get("roles")),
        resolution_status=str(application.get("resolution_status") or application.get("status") or "unknown"),
        reject_reason=_string_or_none(application.get("reject_reason")),
        conflict_code=_string_or_none(application.get("conflict_code")),
        policy_version_id=_uuid_or_none(application.get("policy_version_id")),
        rule_definition_id=_uuid_or_none(application.get("rule_definition_id")),
        risk_decision_id=_uuid_or_none(application.get("risk_decision_id")),
        fx_conversion_id=_uuid_or_none(application.get("fx_conversion_id")),
        reservation_id=_uuid_or_none(application.get("reservation_id")),
        discount_snapshot=_safe_json(application.get("discount")),
        benefits_snapshot=_snapshot_from_payload(application.get("benefits")),
        private_access_snapshot=_safe_json(application.get("private_access")),
        evaluation_trace=_safe_json(application.get("evaluation_trace")),
    )


def _simulation_application_response_from_payload(
    application: Mapping[str, Any],
) -> AdminGrowthCodeSetApplicationResponse:
    response = _application_response_from_payload(application)
    return response.model_copy(
        update={
            "risk_decision_id": None,
            "fx_conversion_id": None,
            "reservation_id": None,
        }
    )


def _reservation_group_response(group: GrowthCodeReservationGroupModel) -> AdminGrowthReservationGroupResponse:
    return AdminGrowthReservationGroupResponse(
        id=group.id,
        code_set_id=group.code_set_id,
        status=group.status,
        user_id=group.user_id,
        quote_session_id=group.quote_session_id,
        checkout_session_id=group.checkout_session_id,
        order_id=group.order_id,
        payment_id=group.payment_id,
        reserved_at=group.reserved_at.isoformat(),
        expires_at=group.expires_at.isoformat(),
        committed_at=group.committed_at.isoformat() if group.committed_at else None,
        consumed_at=group.consumed_at.isoformat() if group.consumed_at else None,
        released_at=group.released_at.isoformat() if group.released_at else None,
        release_reason=group.release_reason,
        idempotency_key_hash=_hash_optional(group.idempotency_key) or "",
    )


def _reservation_response(reservation: GrowthCodeReservationModel) -> AdminGrowthReservationResponse:
    return AdminGrowthReservationResponse(
        id=reservation.id,
        growth_code_id=reservation.growth_code_id,
        reservation_group_id=reservation.reservation_group_id,
        quote_session_id=reservation.quote_session_id,
        checkout_session_id=reservation.checkout_session_id,
        user_id=reservation.user_id,
        risk_subject_id=reservation.risk_subject_id,
        risk_decision_id=reservation.risk_decision_id,
        device_key_hash=reservation.device_key_hash,
        velocity_bucket=reservation.velocity_bucket,
        status=reservation.status,
        reserved_at=reservation.reserved_at.isoformat(),
        expires_at=reservation.expires_at.isoformat(),
        committed_at=reservation.committed_at.isoformat() if reservation.committed_at else None,
        consumed_at=reservation.consumed_at.isoformat() if reservation.consumed_at else None,
        consumed_order_id=reservation.consumed_order_id,
        consumed_payment_id=reservation.consumed_payment_id,
        released_at=reservation.released_at.isoformat() if reservation.released_at else None,
        release_reason=reservation.release_reason,
        capacity_context=_safe_json(reservation.capacity_context),
    )


def _order_application_response(application: OrderCodeApplicationModel) -> AdminGrowthOrderApplicationResponse:
    return AdminGrowthOrderApplicationResponse(
        id=application.id,
        order_id=application.order_id,
        code_set_id=application.code_set_id,
        growth_code_id=application.growth_code_id,
        policy_version_id=application.policy_version_id,
        application_role=application.application_role,
        application_status=application.application_status,
        discount_amount=_decimal(application.discount_amount),
        currency_code=application.currency_code,
        source_amount=_decimal(application.source_amount) if application.source_amount is not None else None,
        source_currency_code=application.source_currency_code,
        fx_conversion_id=application.fx_conversion_id,
        reservation_id=application.reservation_id,
        risk_decision_id=application.risk_decision_id,
        application_snapshot=_safe_json(application.application_snapshot),
    )


def _fx_conversion_response(conversion: FxDiscountConversionModel) -> AdminGrowthFxConversionResponse:
    return AdminGrowthFxConversionResponse(
        id=conversion.id,
        growth_code_id=conversion.growth_code_id,
        policy_version_id=conversion.policy_version_id,
        source_amount=_decimal(conversion.source_amount),
        source_currency=conversion.source_currency,
        target_currency=conversion.target_currency,
        conversion_mode=conversion.conversion_mode,
        fx_rate_snapshot_id=conversion.fx_rate_snapshot_id,
        configured_rate_version=conversion.configured_rate_version,
        raw_converted_amount=_decimal(conversion.raw_converted_amount),
        rounded_amount=_decimal(conversion.rounded_amount),
        applied_amount=_decimal(conversion.applied_amount),
        target_minor_units=conversion.target_minor_units,
        rounding_mode=conversion.rounding_mode,
    )


def _safe_json(value: object) -> dict[str, Any]:
    if not isinstance(value, dict):
        return {}
    return _scrub(value)


def _snapshot_from_payload(value: object) -> dict[str, Any]:
    if isinstance(value, dict):
        return _scrub(value)
    if isinstance(value, list):
        return {"items": _scrub(value)}
    return {}


def _roles_json(value: object) -> dict[str, Any]:
    if isinstance(value, dict):
        return _scrub(value)
    if isinstance(value, list | tuple | set):
        return {"items": [str(item) for item in value]}
    return {}


def _uuid_or_none(value: object) -> UUID | None:
    if value in (None, ""):
        return None
    if isinstance(value, UUID):
        return value
    try:
        return UUID(str(value))
    except (TypeError, ValueError):
        return None


def _string_or_none(value: object) -> str | None:
    if value in (None, ""):
        return None
    return str(value)


def _stable_payload_uuid(application: Mapping[str, Any]) -> UUID:
    existing = _uuid_or_none(application.get("id"))
    if existing is not None:
        return existing
    digest = hashlib.sha256(
        "|".join(
            [
                str(application.get("position_entered") or 0),
                str(application.get("canonical_order") or 0),
                str((application.get("code_ref") or {}).get("code_hash") or application.get("masked_code") or ""),
            ]
        ).encode("utf-8")
    ).hexdigest()
    return UUID(digest[:32])


def _scrub(value: object) -> Any:
    if isinstance(value, dict):
        scrubbed: dict[str, Any] = {}
        for key, item in value.items():
            key_text = str(key)
            normalized = key_text.lower().replace("-", "_")
            if any(part in normalized for part in _SENSITIVE_KEY_PARTS):
                scrubbed[key_text] = REDACTED
            else:
                scrubbed[key_text] = _scrub(item)
        return scrubbed
    if isinstance(value, list):
        return [_scrub(item) for item in value]
    if isinstance(value, tuple):
        return [_scrub(item) for item in value]
    if isinstance(value, Decimal):
        return _decimal(value)
    return value


def _hash_optional(value: str | None) -> str | None:
    if value is None or value == "":
        return None
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _decimal(value: Decimal) -> str:
    return format(value, "f")


async def _count_for(statement: Select[tuple[Any]], db: AsyncSession) -> int:
    count_statement = select(func.count()).select_from(statement.order_by(None).limit(None).offset(None).subquery())
    return int(await db.scalar(count_statement) or 0)


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
