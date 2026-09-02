"""Internal numeric identity and stream ingestion boundary for trusted workers."""

from __future__ import annotations

import hmac
import re
from datetime import datetime
from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Path, Request, Response, status
from httpx import HTTPStatusError, RequestError
from pydantic import BaseModel, ConfigDict, Field, IPvAnyAddress, ValidationError, field_validator
from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.services.remnawave_identity_access import (
    RemnawaveIdentityAccessConflict,
    resolve_exact_mapped_mobile_user_ref,
)
from src.application.services.remnawave_stream_checkpoints import (
    RemnawaveStreamCheckpointError,
    RemnawaveStreamCheckpointService,
    RemnawaveStreamObservationResult,
)
from src.application.services.remnawave_stream_gaps import (
    RemnawaveStreamGapError,
    RemnawaveStreamGapNotFoundError,
    RemnawaveStreamGapResult,
    RemnawaveStreamGapService,
    RemnawaveStreamGapTransitionError,
)
from src.application.services.remnawave_stream_ingestion import (
    ConnectionIp,
    ConnectionUser,
    RemnawaveStreamIdempotencyConflict,
    RemnawaveStreamIngestionError,
    RemnawaveStreamIngestionService,
    UsageRecord,
    payload_fingerprint,
)
from src.application.services.remnawave_stream_reconciliation import (
    RemnawaveStreamGapReconciliationService,
)
from src.application.services.remnawave_stream_retention import RemnawaveStreamRetentionService
from src.application.use_cases.payments.commit_checkout import CheckoutIdempotencyConflictError
from src.application.use_cases.payments.remnawave_auto_renew import (
    CreateRemnawaveAutoRenewInvoiceUseCase,
    RemnawaveAutoRenewConflictError,
    RemnawaveAutoRenewNotFoundError,
    RemnawaveAutoRenewResult,
    RemnawaveAutoRenewUpstreamUnavailableError,
)
from src.config.settings import settings
from src.infrastructure.database.models.mobile_user_model import MobileUserModel
from src.infrastructure.database.models.remnawave_upgrade_model import RemnawaveIdentityReconciliationModel
from src.infrastructure.payments.cryptobot.client import CryptoBotClient
from src.infrastructure.remnawave.client import RemnawaveClient
from src.infrastructure.remnawave.stream_reconciliation_gateway import (
    RemnawaveStreamAuthoritativeReadError,
    RemnawaveStreamRestReconciliationGateway,
)
from src.infrastructure.remnawave.user_gateway import RemnawaveUserGateway
from src.presentation.dependencies.database import get_db
from src.presentation.dependencies.remnawave import get_remnawave_client
from src.presentation.dependencies.services import get_crypto_client

router = APIRouter(prefix="/internal/remnawave", tags=["internal-remnawave"])

_RECONCILIATION_INCOMPLETE_DETAIL = "Remnawave numeric identity reconciliation is incomplete"


def _stream_gap_response(result: RemnawaveStreamGapResult) -> InternalRemnawaveStreamGapResponse:
    return InternalRemnawaveStreamGapResponse(
        gap_id=result.gap_id,
        stream_name=result.stream_name,
        loss_kind=result.loss_kind,
        missing_message_ids=list(result.missing_message_ids),
        missing_count=result.missing_count,
        from_message_id=result.from_message_id,
        to_message_id=result.to_message_id,
        reconciliation_status=result.reconciliation_status,
        detected_at=result.detected_at,
        reused=result.reused,
    )


def _stream_observation_response(
    result: RemnawaveStreamObservationResult,
) -> InternalRemnawaveStreamObservationResponse:
    return InternalRemnawaveStreamObservationResponse(
        stream_name=result.stream_name,
        last_committed_message_id=result.last_committed_message_id,
        stream_exists=result.stream_exists,
        group_exists=result.group_exists,
        loss_detected=result.loss_detected,
        loss_reason=result.loss_reason,
        gap=_stream_gap_response(result.gap) if result.gap is not None else None,
        observed_at=result.observed_at,
    )


class InternalRemnawaveUserResolutionResponse(BaseModel):
    customer_id: UUID
    remnawave_user_id: int = Field(ge=1)
    reconciliation_state: str


class InternalAutoRenewInvoiceRequest(BaseModel):
    expected_expire_at: datetime

    @field_validator("expected_expire_at")
    @classmethod
    def require_aware_timestamp(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            raise ValueError("timestamp must include timezone")
        return value


class InternalAutoRenewInvoiceResponse(BaseModel):
    payment_id: UUID
    reused: bool
    notification_status: Literal["queued", "already_queued"]


class InternalAutoRenewEligibilityRequest(BaseModel):
    user_ids: list[int] = Field(min_length=1, max_length=1000)

    @field_validator("user_ids")
    @classmethod
    def validate_user_ids(cls, values: list[int]) -> list[int]:
        if any(isinstance(value, bool) or value <= 0 for value in values):
            raise ValueError("user_ids must contain positive integers")
        if len(set(values)) != len(values):
            raise ValueError("user_ids must not contain duplicates")
        return values


class InternalAutoRenewEligibilityResponse(BaseModel):
    eligible_user_ids: list[int]


class InternalRemnawaveRetentionPurgeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    batch_limit: int = Field(default=1000, ge=1, le=5000)


class InternalRemnawaveRetentionPurgeResponse(BaseModel):
    deleted_by_table: dict[str, int]
    total_deleted: int = Field(ge=0)
    has_more: bool
    purged_at: datetime


class InternalRemnawaveDeadLetterRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    stream_name: Literal["user_usage", "subscription_requests", "node_connections"]
    message_id: str = Field(pattern=r"^[0-9]+-[0-9]+$", max_length=64)
    schema_version: str | None = Field(default=None, min_length=1, max_length=12)
    error_type: str = Field(pattern=r"^[A-Za-z0-9_.:-]+$", min_length=1, max_length=80)
    redacted_reason: str = Field(pattern=r"^[A-Za-z0-9_.:-]+$", min_length=1, max_length=120)
    payload_fingerprint: str = Field(pattern=r"^[a-f0-9]{64}$")
    attempts: int = Field(ge=1, le=10_000)


class InternalRemnawaveStreamGapRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    stream_name: Literal["user_usage", "subscription_requests", "node_connections"]
    missing_message_ids: list[str] = Field(min_length=1, max_length=1000)
    detected_at: datetime

    @field_validator("missing_message_ids")
    @classmethod
    def validate_missing_message_ids(cls, values: list[str]) -> list[str]:
        if any(not re.fullmatch(r"[0-9]+-[0-9]+", value) or len(value) > 64 for value in values):
            raise ValueError("missing_message_ids must contain Redis stream ids")
        if len(set(values)) != len(values):
            raise ValueError("missing_message_ids must not contain duplicates")
        return values

    @field_validator("detected_at")
    @classmethod
    def require_aware_detected_at(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            raise ValueError("timestamp must include timezone")
        return value


class InternalRemnawaveStreamGapTransitionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    reconciliation_status: Literal["running", "reconciled", "partial", "failed"]
    redacted_detail: str = Field(pattern=r"^[A-Za-z0-9_.:-]+$", min_length=1, max_length=120)
    authoritative_read_completed: bool = False


class InternalRemnawaveStreamGapResponse(BaseModel):
    gap_id: UUID
    stream_name: Literal["user_usage", "subscription_requests", "node_connections"]
    loss_kind: Literal["exact_ids", "unknown_range"]
    missing_message_ids: list[str]
    missing_count: int = Field(ge=0, le=1000)
    from_message_id: str | None
    to_message_id: str | None
    reconciliation_status: Literal["pending", "running", "reconciled", "partial", "failed"]
    detected_at: datetime
    reused: bool


class InternalRemnawaveStreamObservationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    observed_stream_identity: str = Field(pattern=r"^[A-Za-z0-9_.:-]+$", min_length=1, max_length=128)
    stream_exists: bool
    group_exists: bool
    first_message_id: str | None = Field(default=None, pattern=r"^[0-9]+-[0-9]+$", max_length=64)
    last_message_id: str | None = Field(default=None, pattern=r"^[0-9]+-[0-9]+$", max_length=64)
    group_last_delivered_id: str | None = Field(
        default=None,
        pattern=r"^[0-9]+-[0-9]+$",
        max_length=64,
    )
    group_pending_count: int = Field(default=0, ge=0, le=100_000)
    group_pending_min_id: str | None = Field(default=None, pattern=r"^[0-9]+-[0-9]+$", max_length=64)
    group_pending_max_id: str | None = Field(default=None, pattern=r"^[0-9]+-[0-9]+$", max_length=64)
    group_lag: int | None = Field(default=None, ge=0, le=10_000_000)
    observed_at: datetime

    @field_validator("observed_at")
    @classmethod
    def require_aware_observed_at(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            raise ValueError("timestamp must include timezone")
        return value


class InternalRemnawaveStreamObservationResponse(BaseModel):
    stream_name: Literal["user_usage", "subscription_requests", "node_connections"]
    last_committed_message_id: str | None
    stream_exists: bool
    group_exists: bool
    loss_detected: bool
    loss_reason: str | None
    gap: InternalRemnawaveStreamGapResponse | None
    observed_at: datetime


class UserUsageRecordRequest(BaseModel):
    user_id: int = Field(ge=1)
    total_bytes: int = Field(ge=0)


class UserUsageStreamEventRequest(BaseModel):
    event_type: Literal["user_usage"]
    schema_version: Literal["1"]
    node_id: int = Field(ge=1)
    observed_at: datetime
    records: list[UserUsageRecordRequest] = Field(max_length=10_000)

    @field_validator("observed_at")
    @classmethod
    def require_aware_timestamp(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            raise ValueError("timestamp must include timezone")
        return value


class SubscriptionRequestStreamEventRequest(BaseModel):
    event_type: Literal["subscription_requests"]
    schema_version: Literal["1"]
    user_id: int = Field(ge=1)
    requested_at: datetime
    request_ip: IPvAnyAddress | None = None
    user_agent: str | None = Field(default=None, max_length=1024)
    srr_rule_name: str | None = Field(default=None, max_length=160)
    srr_response_type: str = Field(min_length=1, max_length=80)

    @field_validator("requested_at")
    @classmethod
    def require_aware_timestamp(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            raise ValueError("timestamp must include timezone")
        return value


class NodeConnectionIpRequest(BaseModel):
    ip: IPvAnyAddress
    last_seen: datetime

    @field_validator("last_seen")
    @classmethod
    def require_aware_timestamp(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            raise ValueError("timestamp must include timezone")
        return value


class NodeConnectionUserRequest(BaseModel):
    user_id: int = Field(ge=1)
    ips: list[NodeConnectionIpRequest] = Field(max_length=1_000)


class NodeConnectionsStreamEventRequest(BaseModel):
    event_type: Literal["node_connections"]
    schema_version: Literal["1"]
    node_id: int = Field(ge=1)
    observed_at: datetime
    users: list[NodeConnectionUserRequest] = Field(max_length=10_000)

    @field_validator("observed_at")
    @classmethod
    def require_aware_timestamp(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            raise ValueError("timestamp must include timezone")
        return value


StreamEventRequest = Annotated[
    UserUsageStreamEventRequest | SubscriptionRequestStreamEventRequest | NodeConnectionsStreamEventRequest,
    Field(discriminator="event_type"),
]


def require_backend_internal_secret(request: Request) -> None:
    supplied = request.headers.getlist("X-Backend-Internal-Secret")
    configured = settings.backend_internal_secret.get_secret_value().strip()
    if len(supplied) != 1 or not configured or not hmac.compare_digest(supplied[0].strip(), configured):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated.")


async def _require_exact_mapped_mobile_identity(
    db: AsyncSession,
    *,
    customer: MobileUserModel,
    remnawave_user_id: int,
) -> None:
    if customer.remnawave_user_id != remnawave_user_id:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=_RECONCILIATION_INCOMPLETE_DETAIL,
        )
    try:
        user_ref = await resolve_exact_mapped_mobile_user_ref(db, customer)
    except RemnawaveIdentityAccessConflict as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=_RECONCILIATION_INCOMPLETE_DETAIL,
        ) from exc
    if user_ref is None or user_ref.require_numeric_id() != remnawave_user_id:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=_RECONCILIATION_INCOMPLETE_DETAIL,
        )


@router.get(
    "/users/by-customer/{customer_id}",
    response_model=InternalRemnawaveUserResolutionResponse,
    dependencies=[Depends(require_backend_internal_secret)],
)
async def resolve_numeric_user_for_worker(
    customer_id: Annotated[UUID, Path()],
    db: AsyncSession = Depends(get_db),
) -> InternalRemnawaveUserResolutionResponse:
    """Resolve worker payment/provisioning handoffs to the canonical 3.x id."""

    customer = await db.get(MobileUserModel, customer_id)
    if customer is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Customer not found")
    if customer.remnawave_user_id is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Remnawave numeric identity is not reconciled",
        )
    await _require_exact_mapped_mobile_identity(
        db,
        customer=customer,
        remnawave_user_id=customer.remnawave_user_id,
    )
    return InternalRemnawaveUserResolutionResponse(
        customer_id=customer.id,
        remnawave_user_id=customer.remnawave_user_id,
        reconciliation_state="mapped",
    )


@router.get(
    "/users/by-remnawave-id/{remnawave_user_id}",
    response_model=InternalRemnawaveUserResolutionResponse,
    dependencies=[Depends(require_backend_internal_secret)],
)
async def resolve_customer_for_numeric_user(
    remnawave_user_id: Annotated[int, Path(ge=1)],
    db: AsyncSession = Depends(get_db),
) -> InternalRemnawaveUserResolutionResponse:
    """Resolve a provider numeric id without accepting a legacy UUID fallback."""

    result = await db.execute(select(MobileUserModel).where(MobileUserModel.remnawave_user_id == remnawave_user_id))
    customer = result.scalar_one_or_none()
    if customer is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Customer not found")
    await _require_exact_mapped_mobile_identity(
        db,
        customer=customer,
        remnawave_user_id=remnawave_user_id,
    )
    return InternalRemnawaveUserResolutionResponse(
        customer_id=customer.id,
        remnawave_user_id=remnawave_user_id,
        reconciliation_state="mapped",
    )


@router.post(
    "/auto-renew/eligible",
    response_model=InternalAutoRenewEligibilityResponse,
    dependencies=[Depends(require_backend_internal_secret)],
)
async def list_auto_renew_eligible_users(
    payload: InternalAutoRenewEligibilityRequest,
    db: AsyncSession = Depends(get_db),
) -> InternalAutoRenewEligibilityResponse:
    """Filter a bounded Remnawave scan through CyberVPN-owned consent."""

    if not settings.payment_autorenewal_enabled:
        return InternalAutoRenewEligibilityResponse(eligible_user_ids=[])
    result = await db.execute(
        select(MobileUserModel.remnawave_user_id)
        .join(
            RemnawaveIdentityReconciliationModel,
            (RemnawaveIdentityReconciliationModel.subject_type == "mobile_user")
            & (RemnawaveIdentityReconciliationModel.subject_id == MobileUserModel.id),
        )
        .where(
            MobileUserModel.remnawave_user_id.in_(payload.user_ids),
            MobileUserModel.subscription_auto_renew_enabled.is_(True),
            MobileUserModel.is_active.is_(True),
            RemnawaveIdentityReconciliationModel.reconciliation_state == "mapped",
            RemnawaveIdentityReconciliationModel.numeric_user_id == MobileUserModel.remnawave_user_id,
            or_(
                and_(
                    MobileUserModel.remnawave_uuid.is_(None),
                    RemnawaveIdentityReconciliationModel.legacy_uuid.is_(None),
                ),
                and_(
                    MobileUserModel.remnawave_uuid.is_not(None),
                    RemnawaveIdentityReconciliationModel.legacy_uuid.is_not(None),
                    RemnawaveIdentityReconciliationModel.legacy_uuid == MobileUserModel.remnawave_uuid,
                ),
            ),
        )
        .order_by(MobileUserModel.remnawave_user_id)
    )
    return InternalAutoRenewEligibilityResponse(
        eligible_user_ids=[int(value) for value in result.scalars().all() if value is not None]
    )


@router.post(
    "/users/{remnawave_user_id}/auto-renew-invoice",
    response_model=InternalAutoRenewInvoiceResponse,
    dependencies=[Depends(require_backend_internal_secret)],
)
async def create_auto_renew_invoice(
    payload: InternalAutoRenewInvoiceRequest,
    remnawave_user_id: Annotated[int, Path(ge=1)],
    idempotency_key: Annotated[str, Header(alias="Idempotency-Key", min_length=20, max_length=160)],
    db: AsyncSession = Depends(get_db),
    remnawave_client: RemnawaveClient = Depends(get_remnawave_client),
    crypto_client: CryptoBotClient = Depends(get_crypto_client),
) -> InternalAutoRenewInvoiceResponse:
    """Create a tracked renewal invoice from CyberVPN billing authority."""

    try:
        result: RemnawaveAutoRenewResult = await CreateRemnawaveAutoRenewInvoiceUseCase(
            db,
            crypto_client=crypto_client,
            user_gateway=RemnawaveUserGateway(remnawave_client),
        ).execute(
            remnawave_user_id=remnawave_user_id,
            expected_expire_at=payload.expected_expire_at,
            idempotency_key=idempotency_key,
        )
    except RemnawaveAutoRenewNotFoundError as exc:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except (RemnawaveAutoRenewConflictError, CheckoutIdempotencyConflictError) as exc:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except RemnawaveAutoRenewUpstreamUnavailableError as exc:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
    except HTTPStatusError as exc:
        await db.rollback()
        upstream_status = exc.response.status_code
        mapped_status = (
            status.HTTP_503_SERVICE_UNAVAILABLE
            if upstream_status == status.HTTP_429_TOO_MANY_REQUESTS or upstream_status >= 500
            else status.HTTP_502_BAD_GATEWAY
        )
        raise HTTPException(status_code=mapped_status, detail="Renewal provider request failed") from exc
    except RequestError as exc:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Renewal provider response is ambiguous; reconciliation is required",
        ) from exc
    except ValueError as exc:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)) from exc
    return InternalAutoRenewInvoiceResponse(
        payment_id=UUID(result.payment_id),
        reused=result.reused,
        notification_status=result.notification_status,
    )


@router.post(
    "/stream-checkpoints/{stream_name}/observe",
    response_model=InternalRemnawaveStreamObservationResponse,
    dependencies=[Depends(require_backend_internal_secret)],
)
async def observe_remnawave_stream_startup(
    stream_name: Annotated[
        Literal["user_usage", "subscription_requests", "node_connections"],
        Path(),
    ],
    payload: InternalRemnawaveStreamObservationRequest,
    db: AsyncSession = Depends(get_db),
) -> InternalRemnawaveStreamObservationResponse:
    """Compare live Valkey identity/range/group state with the durable checkpoint."""

    try:
        result = await RemnawaveStreamCheckpointService(db).observe_startup(
            stream_name=stream_name,
            observed_stream_identity=payload.observed_stream_identity,
            stream_exists=payload.stream_exists,
            group_exists=payload.group_exists,
            first_message_id=payload.first_message_id,
            last_message_id=payload.last_message_id,
            group_last_delivered_id=payload.group_last_delivered_id,
            group_pending_count=payload.group_pending_count,
            group_pending_min_id=payload.group_pending_min_id,
            group_pending_max_id=payload.group_pending_max_id,
            observed_at=payload.observed_at,
            group_lag=payload.group_lag,
        )
        await db.commit()
    except (RemnawaveStreamCheckpointError, RemnawaveStreamGapError) as exc:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)) from exc
    return _stream_observation_response(result)


@router.post(
    "/stream-gaps",
    response_model=InternalRemnawaveStreamGapResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_backend_internal_secret)],
)
async def register_remnawave_stream_gap(
    payload: InternalRemnawaveStreamGapRequest,
    db: AsyncSession = Depends(get_db),
) -> InternalRemnawaveStreamGapResponse:
    """Commit exact XAUTOCLAIM deleted IDs before the worker continues."""

    try:
        result = await RemnawaveStreamGapService(db).register(
            stream_name=payload.stream_name,
            missing_message_ids=payload.missing_message_ids,
            detected_at=payload.detected_at,
        )
        await db.commit()
    except RemnawaveStreamGapError as exc:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)) from exc
    return _stream_gap_response(result)


@router.patch(
    "/stream-gaps/{gap_id}/reconciliation",
    response_model=InternalRemnawaveStreamGapResponse,
    dependencies=[Depends(require_backend_internal_secret)],
)
async def transition_remnawave_stream_gap(
    gap_id: Annotated[UUID, Path()],
    payload: InternalRemnawaveStreamGapTransitionRequest,
    db: AsyncSession = Depends(get_db),
) -> InternalRemnawaveStreamGapResponse:
    """Advance a gap only after the trusted worker performs a safe upstream read."""

    try:
        result = await RemnawaveStreamGapService(db).transition(
            gap_id=gap_id,
            reconciliation_status=payload.reconciliation_status,
            redacted_detail=payload.redacted_detail,
            authoritative_read_completed=payload.authoritative_read_completed,
        )
        await db.commit()
    except RemnawaveStreamGapNotFoundError as exc:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except RemnawaveStreamGapTransitionError as exc:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except RemnawaveStreamGapError as exc:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)) from exc
    return _stream_gap_response(result)


@router.post(
    "/stream-gaps/{gap_id}/reconcile",
    response_model=InternalRemnawaveStreamGapResponse,
    dependencies=[Depends(require_backend_internal_secret)],
)
async def reconcile_remnawave_stream_gap(
    gap_id: Annotated[UUID, Path()],
    db: AsyncSession = Depends(get_db),
    remnawave_client: RemnawaveClient = Depends(get_remnawave_client),
) -> InternalRemnawaveStreamGapResponse:
    """Refresh recoverable current truth; never fabricate lost historical events."""

    try:
        result = await RemnawaveStreamGapReconciliationService(
            db,
            reader=RemnawaveStreamRestReconciliationGateway(remnawave_client),
        ).execute(gap_id)
    except RemnawaveStreamGapNotFoundError as exc:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except RemnawaveStreamGapTransitionError as exc:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except (
        HTTPStatusError,
        RequestError,
        RemnawaveStreamAuthoritativeReadError,
        RemnawaveStreamIngestionError,
        ValidationError,
        ValueError,
    ) as exc:
        # The durable state remains running. The worker retries this trigger;
        # it must not XACK until a terminal partial response is committed.
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authoritative Remnawave stream reconciliation is unavailable",
        ) from exc
    return _stream_gap_response(result)


@router.post(
    "/retention/purge",
    response_model=InternalRemnawaveRetentionPurgeResponse,
    dependencies=[Depends(require_backend_internal_secret)],
)
async def purge_expired_remnawave_stream_rows(
    payload: InternalRemnawaveRetentionPurgeRequest,
    db: AsyncSession = Depends(get_db),
) -> InternalRemnawaveRetentionPurgeResponse:
    """Delete one deterministic bounded batch and commit before reporting success."""

    try:
        result = await RemnawaveStreamRetentionService(db).purge_expired(batch_limit=payload.batch_limit)
        await db.commit()
    except ValueError as exc:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)) from exc
    return InternalRemnawaveRetentionPurgeResponse(
        deleted_by_table=result.deleted_by_table,
        total_deleted=result.total_deleted,
        has_more=result.has_more,
        purged_at=result.purged_at,
    )


@router.post(
    "/dead-letters",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_backend_internal_secret)],
)
async def upsert_remnawave_dead_letter(
    payload: InternalRemnawaveDeadLetterRequest,
    db: AsyncSession = Depends(get_db),
) -> Response:
    """Durably upsert redacted DLQ metadata before a worker may ACK."""

    try:
        await RemnawaveStreamIngestionService(db).upsert_dead_letter(
            stream_name=payload.stream_name,
            message_id=payload.message_id,
            schema_version=payload.schema_version,
            error_type=payload.error_type,
            redacted_reason=payload.redacted_reason,
            source_fingerprint=payload.payload_fingerprint,
            attempts=payload.attempts,
        )
        await db.commit()
    except RemnawaveStreamIngestionError as exc:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)) from exc
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/streams/events",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_backend_internal_secret)],
)
async def persist_stream_event(
    payload: StreamEventRequest,
    idempotency_key: Annotated[str, Header(alias="Idempotency-Key", min_length=20, max_length=160)],
    db: AsyncSession = Depends(get_db),
) -> Response:
    """Commit a validated event before the worker is allowed to XACK it."""

    if not settings.remnawave_stream_ingestion_enabled:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Stream ingestion is disabled")
    service = RemnawaveStreamIngestionService(db)
    digest = payload_fingerprint(payload.model_dump_json())
    try:
        if isinstance(payload, UserUsageStreamEventRequest):
            await service.persist_user_usage(
                idempotency_key=idempotency_key,
                payload_sha256=digest,
                schema_version=payload.schema_version,
                node_id=payload.node_id,
                observed_at=payload.observed_at,
                records=tuple(
                    UsageRecord(user_id=item.user_id, total_bytes=item.total_bytes) for item in payload.records
                ),
            )
        elif isinstance(payload, SubscriptionRequestStreamEventRequest):
            await service.persist_subscription_request(
                idempotency_key=idempotency_key,
                payload_sha256=digest,
                schema_version=payload.schema_version,
                user_id=payload.user_id,
                requested_at=payload.requested_at,
                request_ip=str(payload.request_ip) if payload.request_ip is not None else None,
                user_agent=payload.user_agent,
                srr_rule_name=payload.srr_rule_name,
                srr_response_type=payload.srr_response_type,
            )
        else:
            await service.persist_node_connections(
                idempotency_key=idempotency_key,
                payload_sha256=digest,
                schema_version=payload.schema_version,
                node_id=payload.node_id,
                observed_at=payload.observed_at,
                users=tuple(
                    ConnectionUser(
                        user_id=user.user_id,
                        ips=tuple(ConnectionIp(ip=str(item.ip), last_seen=item.last_seen) for item in user.ips),
                    )
                    for user in payload.users
                ),
            )
        # Explicit commit is part of the worker protocol: a 204 is the durable
        # boundary after which XACK is safe.
        await db.commit()
    except RemnawaveStreamIngestionError as exc:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)) from exc
    except RemnawaveStreamIdempotencyConflict as exc:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    return Response(status_code=status.HTTP_204_NO_CONTENT)
