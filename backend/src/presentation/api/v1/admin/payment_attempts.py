"""Stage 1 admin-safe payment attempt views."""

from __future__ import annotations

from datetime import UTC, datetime
from hashlib import sha256
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import Select, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.use_cases.auth.permissions import Permission, has_permission
from src.config.settings import settings
from src.domain.enums import AdminRole, PaymentAttemptStatus
from src.infrastructure.database.models.admin_user_model import AdminUserModel
from src.infrastructure.database.models.order_model import OrderModel
from src.infrastructure.database.models.payment_attempt_model import PaymentAttemptModel
from src.infrastructure.monitoring.metrics import route_operations_total
from src.presentation.api.shared.stage1_contract import (
    PAYMENT_ATTEMPT_STATUS_TO_STAGE1_STATE,
    Stage1PaymentState,
)
from src.presentation.dependencies.auth import get_current_active_user
from src.presentation.dependencies.database import get_db
from src.presentation.dependencies.roles import require_permission

router = APIRouter(prefix="/admin", tags=["admin", "payment-attempts"])

AdminPaymentAttemptVisibility = Literal["support", "finance"]
AdminPaymentAttemptReviewState = Literal["ok", "manual_review", "alert_15m", "p1_escalation", "p0_blocker"]

STAGE1_PAYMENT_ATTEMPT_SUPPORT_ROLES = frozenset(
    {
        AdminRole.SUPPORT,
        AdminRole.FINANCE,
        AdminRole.ADMIN,
        AdminRole.SUPER_ADMIN,
        AdminRole.OWNER_SUPER_ADMIN,
    }
)
STAGE1_PAYMENT_ATTEMPT_ACTIVE_STATUSES = {
    PaymentAttemptStatus.PENDING.value,
    PaymentAttemptStatus.PROCESSING.value,
}
STAGE1_PAYMENT_ATTEMPT_REVIEW_AFTER_MINUTES = 15
STAGE1_PAYMENT_ATTEMPT_P1_AFTER_MINUTES = 60
STAGE1_PAYMENT_ATTEMPT_P0_AFTER_MINUTES = 24 * 60


class AdminPaymentAttemptResponse(BaseModel):
    """Admin-safe payment attempt row.

    Provider snapshots, request snapshots, idempotency keys, checkout URLs and
    raw external references are intentionally excluded.
    """

    model_config = ConfigDict(use_enum_values=True)

    id: UUID
    order_id: UUID
    user_id: UUID
    visibility: AdminPaymentAttemptVisibility
    payment_id: UUID | None = None
    payment_record_present: bool
    attempt_number: int
    provider: str
    sale_channel: str
    status: str
    stage1_payment_state: Stage1PaymentState
    displayed_amount: float
    currency_code: str
    wallet_amount: float | None = None
    gateway_amount: float | None = None
    provider_status: str | None = None
    external_reference_fingerprint: str | None = None
    idempotency_key_present: bool
    invoice_present: bool
    invoice_expires_at: str | None = None
    order_status: str
    settlement_status: str
    age_minutes: int
    review_state: AdminPaymentAttemptReviewState
    review_reason: str | None = None
    manual_review_required: bool
    support_escalation: bool
    launch_blocker: bool
    terminal_at: datetime | None = None
    created_at: datetime
    updated_at: datetime
    redacted_fields: list[str] = Field(default_factory=list)


class AdminPaymentAttemptListResponse(BaseModel):
    items: list[AdminPaymentAttemptResponse]
    limit: int
    offset: int


def _resolve_admin_role(user: AdminUserModel) -> AdminRole:
    try:
        return AdminRole(user.role)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid admin role") from exc


async def _require_stage1_payment_attempt_support_viewer(
    user: AdminUserModel = Depends(get_current_active_user),
) -> AdminUserModel:
    role = _resolve_admin_role(user)
    if settings.admin_2fa_required and not user.totp_enabled:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin 2FA required")
    if role not in STAGE1_PAYMENT_ATTEMPT_SUPPORT_ROLES:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Requires support, finance or admin payment-attempt view role",
        )
    return user


def _visibility_for(user: AdminUserModel) -> AdminPaymentAttemptVisibility:
    role = _resolve_admin_role(user)
    return "finance" if has_permission(role, Permission.PAYMENT_READ) else "support"


def _utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _age_minutes(started_at: datetime, observed_at: datetime | None = None) -> int:
    observed = observed_at or datetime.now(UTC)
    return max(int((_utc(observed) - _utc(started_at)).total_seconds() // 60), 0)


def _safe_fingerprint(value: str | None) -> str | None:
    if not value:
        return None
    return sha256(value.encode("utf-8")).hexdigest()[:16]


def _safe_provider_status(provider_snapshot: dict | None) -> str | None:
    if not isinstance(provider_snapshot, dict):
        return None

    for key in ("status", "payment_status", "invoice_status", "state"):
        value = provider_snapshot.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()[:64]
    return None


def _safe_invoice_expires_at(provider_snapshot: dict | None) -> str | None:
    if not isinstance(provider_snapshot, dict):
        return None

    value = provider_snapshot.get("expires_at")
    if isinstance(value, str) and value.strip():
        return value.strip()[:64]
    return None


def _stage1_payment_state(status_value: str) -> Stage1PaymentState:
    try:
        return PAYMENT_ATTEMPT_STATUS_TO_STAGE1_STATE[PaymentAttemptStatus(status_value)]
    except ValueError:
        return Stage1PaymentState.RECONCILIATION_REQUIRED


def _review_for_attempt(
    attempt: PaymentAttemptModel,
    *,
    observed_at: datetime | None = None,
) -> tuple[AdminPaymentAttemptReviewState, str | None, int]:
    detected_at = attempt.terminal_at or attempt.updated_at or attempt.created_at
    age = _age_minutes(detected_at, observed_at=observed_at)
    known_statuses = {status_value.value for status_value in PaymentAttemptStatus}
    review_reason: str | None = None

    if attempt.status in STAGE1_PAYMENT_ATTEMPT_ACTIVE_STATUSES and age >= STAGE1_PAYMENT_ATTEMPT_REVIEW_AFTER_MINUTES:
        review_reason = "stale_active_attempt"
    elif attempt.status == PaymentAttemptStatus.SUCCEEDED.value and attempt.payment_id is None:
        review_reason = "paid_without_canonical_payment"
    elif attempt.status not in known_statuses:
        review_reason = "unknown_payment_attempt_status"

    if review_reason is None:
        return "ok", None, age
    if age >= STAGE1_PAYMENT_ATTEMPT_P0_AFTER_MINUTES:
        return "p0_blocker", review_reason, age
    if age >= STAGE1_PAYMENT_ATTEMPT_P1_AFTER_MINUTES:
        return "p1_escalation", review_reason, age
    if age >= STAGE1_PAYMENT_ATTEMPT_REVIEW_AFTER_MINUTES:
        return "alert_15m", review_reason, age
    return "manual_review", review_reason, age


def _serialize_admin_payment_attempt(
    attempt: PaymentAttemptModel,
    order: OrderModel,
    *,
    visibility: AdminPaymentAttemptVisibility,
    observed_at: datetime | None = None,
) -> AdminPaymentAttemptResponse:
    provider_snapshot = attempt.provider_snapshot or {}
    review_state, review_reason, age_minutes = _review_for_attempt(attempt, observed_at=observed_at)
    is_finance = visibility == "finance"

    return AdminPaymentAttemptResponse(
        id=attempt.id,
        order_id=attempt.order_id,
        user_id=order.user_id,
        visibility=visibility,
        payment_id=attempt.payment_id if is_finance else None,
        payment_record_present=attempt.payment_id is not None,
        attempt_number=attempt.attempt_number,
        provider=attempt.provider,
        sale_channel=attempt.sale_channel,
        status=attempt.status,
        stage1_payment_state=_stage1_payment_state(attempt.status),
        displayed_amount=float(attempt.displayed_amount),
        currency_code=attempt.currency_code,
        wallet_amount=float(attempt.wallet_amount) if is_finance else None,
        gateway_amount=float(attempt.gateway_amount) if is_finance else None,
        provider_status=_safe_provider_status(provider_snapshot),
        external_reference_fingerprint=_safe_fingerprint(attempt.external_reference),
        idempotency_key_present=bool(attempt.idempotency_key),
        invoice_present=bool(provider_snapshot.get("invoice_id") or provider_snapshot.get("payment_url")),
        invoice_expires_at=_safe_invoice_expires_at(provider_snapshot),
        order_status=order.order_status,
        settlement_status=order.settlement_status,
        age_minutes=age_minutes,
        review_state=review_state,
        review_reason=review_reason,
        manual_review_required=review_state != "ok",
        support_escalation=review_state in {"alert_15m", "p1_escalation", "p0_blocker"},
        launch_blocker=review_state == "p0_blocker",
        terminal_at=attempt.terminal_at,
        created_at=attempt.created_at,
        updated_at=attempt.updated_at,
        redacted_fields=[
            "external_reference",
            "idempotency_key",
            "provider_snapshot",
            "request_snapshot",
            "invoice.payment_url",
        ],
    )


def _admin_payment_attempts_query() -> Select[tuple[PaymentAttemptModel, OrderModel]]:
    return select(PaymentAttemptModel, OrderModel).join(OrderModel, PaymentAttemptModel.order_id == OrderModel.id)


async def _list_payment_attempt_rows(
    db: AsyncSession,
    *,
    user_id: UUID | None = None,
    order_id: UUID | None = None,
    status_filter: str | None = None,
    provider: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[tuple[PaymentAttemptModel, OrderModel]]:
    stmt = _admin_payment_attempts_query()
    if user_id is not None:
        stmt = stmt.where(OrderModel.user_id == user_id)
    if order_id is not None:
        stmt = stmt.where(PaymentAttemptModel.order_id == order_id)
    if status_filter:
        stmt = stmt.where(PaymentAttemptModel.status == status_filter)
    if provider:
        stmt = stmt.where(PaymentAttemptModel.provider == provider)
    stmt = stmt.order_by(PaymentAttemptModel.created_at.desc()).offset(offset).limit(limit)

    result = await db.execute(stmt)
    return [(attempt, order) for attempt, order in result.all()]


async def _get_payment_attempt_row(
    db: AsyncSession,
    *,
    payment_attempt_id: UUID,
) -> tuple[PaymentAttemptModel, OrderModel] | None:
    result = await db.execute(
        _admin_payment_attempts_query().where(PaymentAttemptModel.id == payment_attempt_id).limit(1)
    )
    row = result.first()
    if row is None:
        return None
    attempt, order = row
    return attempt, order


@router.get("/payment-attempts", response_model=AdminPaymentAttemptListResponse)
async def list_admin_payment_attempts(
    user_id: UUID | None = Query(None, description="Filter by customer account id"),
    order_id: UUID | None = Query(None, description="Filter by order id"),
    status_filter: str | None = Query(None, alias="status", max_length=20),
    provider: str | None = Query(None, max_length=30),
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    current_user: AdminUserModel = Depends(require_permission(Permission.PAYMENT_READ)),
) -> AdminPaymentAttemptListResponse:
    rows = await _list_payment_attempt_rows(
        db,
        user_id=user_id,
        order_id=order_id,
        status_filter=status_filter,
        provider=provider,
        offset=offset,
        limit=limit,
    )

    route_operations_total.labels(route="admin_payment_attempts", action="list", status="success").inc()
    return AdminPaymentAttemptListResponse(
        items=[
            _serialize_admin_payment_attempt(attempt, order, visibility=_visibility_for(current_user))
            for attempt, order in rows
        ],
        offset=offset,
        limit=limit,
    )


@router.get("/payment-attempts/{payment_attempt_id}", response_model=AdminPaymentAttemptResponse)
async def get_admin_payment_attempt(
    payment_attempt_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: AdminUserModel = Depends(require_permission(Permission.PAYMENT_READ)),
) -> AdminPaymentAttemptResponse:
    row = await _get_payment_attempt_row(db, payment_attempt_id=payment_attempt_id)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Payment attempt not found")

    route_operations_total.labels(route="admin_payment_attempts", action="detail", status="success").inc()
    attempt, order = row
    return _serialize_admin_payment_attempt(attempt, order, visibility=_visibility_for(current_user))


@router.get("/mobile-users/{user_id}/payment-attempts", response_model=AdminPaymentAttemptListResponse)
async def list_customer_payment_attempts_for_support(
    user_id: UUID,
    status_filter: str | None = Query(None, alias="status", max_length=20),
    provider: str | None = Query(None, max_length=30),
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: AdminUserModel = Depends(_require_stage1_payment_attempt_support_viewer),
) -> AdminPaymentAttemptListResponse:
    rows = await _list_payment_attempt_rows(
        db,
        user_id=user_id,
        status_filter=status_filter,
        provider=provider,
        offset=offset,
        limit=limit,
    )

    route_operations_total.labels(route="admin_payment_attempts", action="support_list", status="success").inc()
    return AdminPaymentAttemptListResponse(
        items=[
            _serialize_admin_payment_attempt(attempt, order, visibility=_visibility_for(current_user))
            for attempt, order in rows
        ],
        offset=offset,
        limit=limit,
    )
