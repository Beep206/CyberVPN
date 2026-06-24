"""Customer and admin privacy request routes."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import NoReturn
from uuid import UUID

import redis.asyncio as redis
from fastapi import APIRouter, Depends, Header, HTTPException, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.services.privacy_request_service import (
    PrivacyRequestConflictError,
    PrivacyRequestDetail,
    PrivacyRequestRateLimitedError,
    PrivacyRequestService,
)
from src.application.use_cases.auth.permissions import Permission
from src.domain.entities.privacy_request import (
    CUSTOMER_CANCELABLE_PRIVACY_REQUEST_STATUSES,
    InvalidPrivacyRequestTransitionError,
    PrivacyRequestNotFoundError,
    PrivacyRequestStatus,
    PrivacyRequestType,
)
from src.infrastructure.cache.redis_client import get_redis
from src.infrastructure.remnawave.client import RemnawaveClient
from src.infrastructure.remnawave.user_gateway import RemnawaveUserGateway
from src.presentation.dependencies.auth import get_current_active_web_user
from src.presentation.dependencies.auth_realms import get_request_web_auth_realm
from src.presentation.dependencies.database import get_db
from src.presentation.dependencies.remnawave import get_remnawave_client
from src.presentation.dependencies.roles import require_permission

from .schemas import (
    AdminPrivacyRequestDetailResponse,
    AdminPrivacyRequestListResponse,
    AdminPrivacyRequestSummaryResponse,
    CustomerPrivacyRequestDetailResponse,
    DecisionRequest,
    ExecuteRequest,
    PrivacyRequestAcceptedResponse,
    PrivacyRequestCreateRequest,
    PrivacyRequestEventResponse,
    PrivacyRequestListResponse,
    PrivacyRequestStatusLiteral,
    PrivacyRequestSummaryResponse,
    PrivacyRequestTypeLiteral,
    RequestIdentityVerificationRequest,
    ScheduleRequest,
    StartReviewRequest,
    VerifyIdentityRequest,
)

customer_router = APIRouter(prefix="/auth/me/privacy-requests", tags=["privacy-requests"])
admin_router = APIRouter(prefix="/admin/privacy-requests", tags=["admin", "privacy-requests"])


def _service(db: AsyncSession) -> PrivacyRequestService:
    return PrivacyRequestService(db)


def _message_for_request(request_type: str) -> str:
    if request_type == PrivacyRequestType.ACCOUNT_DELETION.value:
        return "Account deletion request accepted for manual privacy review."
    return "Data export request accepted for manual privacy review."


def _manual_target_days(detail: PrivacyRequestDetail) -> int:
    value = detail.request.policy_snapshot.get("manual_fulfillment_target_days")
    return int(value) if isinstance(value, int) else 30


def _ticket_reference(detail: PrivacyRequestDetail) -> str | None:
    return detail.support_ticket.public_id if detail.support_ticket is not None else None


def _is_overdue(submitted_at: datetime, status_value: str) -> bool:
    if status_value in {"fulfilled", "denied", "canceled"}:
        return False
    normalized = submitted_at if submitted_at.tzinfo is not None else submitted_at.replace(tzinfo=UTC)
    return normalized.astimezone(UTC) <= datetime.now(UTC) - timedelta(days=30)


def _customer_allowed_actions(status_value: str) -> list[str]:
    status_enum = PrivacyRequestStatus(status_value)
    if status_enum in CUSTOMER_CANCELABLE_PRIVACY_REQUEST_STATUSES:
        return ["cancel"]
    return []


def _admin_allowed_actions(status_value: str) -> list[str]:
    status_enum = PrivacyRequestStatus(status_value)
    if status_enum == PrivacyRequestStatus.SUBMITTED:
        return ["start_review"]
    if status_enum == PrivacyRequestStatus.IDENTITY_VERIFICATION:
        return ["request_identity_verification", "verify_identity", "deny"]
    if status_enum == PrivacyRequestStatus.PENDING_DECISION:
        return ["approve", "deny"]
    if status_enum == PrivacyRequestStatus.APPROVED:
        return ["schedule"]
    if status_enum == PrivacyRequestStatus.SCHEDULED:
        return ["execute"]
    if status_enum == PrivacyRequestStatus.FAILED:
        return ["retry", "deny"]
    return []


def _event_response(event) -> PrivacyRequestEventResponse:
    return PrivacyRequestEventResponse(
        event_type=event.event_type,
        actor_type=event.actor_type,
        from_status=event.from_status,
        to_status=event.to_status,
        safe_summary=event.safe_summary,
        metadata=dict(event.metadata_json or {}),
        created_at=event.created_at,
    )


def _summary_response(detail: PrivacyRequestDetail) -> PrivacyRequestSummaryResponse:
    request = detail.request
    return PrivacyRequestSummaryResponse(
        privacy_request_reference=request.public_id,
        ticket_reference=_ticket_reference(detail),
        request_type=request.request_type,
        status=request.status,
        submitted_at=request.submitted_at,
        updated_at=request.updated_at,
        scheduled_for=request.scheduled_for,
        fulfilled_at=request.fulfilled_at,
        canceled_at=request.canceled_at,
        manual_fulfillment_target_days=_manual_target_days(detail),
        allowed_actions=_customer_allowed_actions(request.status),
    )


def _customer_detail_response(detail: PrivacyRequestDetail) -> CustomerPrivacyRequestDetailResponse:
    request = detail.request
    return CustomerPrivacyRequestDetailResponse(
        **_summary_response(detail).model_dump(),
        reason_code=request.reason_code,
        notes_redacted=request.notes_redacted,
        events=[_event_response(event) for event in detail.events],
    )


def _safe_customer_reference(detail: PrivacyRequestDetail) -> str:
    if detail.customer_account is not None:
        return f"UID:{detail.customer_account.public_uid}"
    return f"principal:{str(detail.request.principal_subject)[:8]}"


def _admin_summary_response(detail: PrivacyRequestDetail) -> AdminPrivacyRequestSummaryResponse:
    request = detail.request
    base_summary = _summary_response(detail).model_dump()
    base_summary["allowed_actions"] = _admin_allowed_actions(request.status)
    return AdminPrivacyRequestSummaryResponse(
        **base_summary,
        safe_customer_reference=_safe_customer_reference(detail),
        assigned_admin_id=str(request.assigned_admin_id) if request.assigned_admin_id is not None else None,
        overdue=_is_overdue(request.submitted_at, request.status),
    )


def _admin_detail_response(detail: PrivacyRequestDetail) -> AdminPrivacyRequestDetailResponse:
    request = detail.request
    return AdminPrivacyRequestDetailResponse(
        **_admin_summary_response(detail).model_dump(),
        reason_code=request.reason_code,
        notes_redacted=request.notes_redacted,
        policy_snapshot=dict(request.policy_snapshot or {}),
        customer_account_public_uid=detail.customer_account.public_uid if detail.customer_account is not None else None,
        principal_subject=str(request.principal_subject),
        support_ticket_reference=_ticket_reference(detail),
        decision_reason=request.decision_reason,
        last_error_code=request.last_error_code,
        last_error_redacted=request.last_error_redacted,
        review_started_at=request.review_started_at,
        identity_verified_at=request.identity_verified_at,
        decision_at=request.decision_at,
        version=request.version,
        events=[_event_response(event) for event in detail.events],
    )


async def _detail_for_summary(service: PrivacyRequestService, reference: str) -> PrivacyRequestDetail:
    return await service.get_admin_request(reference=reference)


def _raise_http(exc: Exception) -> NoReturn:
    if isinstance(exc, PrivacyRequestNotFoundError):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Privacy request not found") from exc
    if isinstance(exc, InvalidPrivacyRequestTransitionError):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    if isinstance(exc, PrivacyRequestConflictError):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": exc.code, "message": str(exc)},
        ) from exc
    if isinstance(exc, PrivacyRequestRateLimitedError):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={"code": "PRIVACY_REQUEST_RATE_LIMITED", "message": str(exc)},
            headers={"Retry-After": str(exc.retry_after_seconds)},
        ) from exc
    if isinstance(exc, ValueError):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    raise exc


def _combine_legacy_notes(payload: PrivacyRequestCreateRequest) -> tuple[str | None, str | None]:
    reason_code = payload.reason_code or payload.reason
    notes = payload.notes
    if payload.feedback:
        notes = "\n".join(part for part in (notes, payload.feedback) if part)
    return reason_code, notes


@customer_router.post("", response_model=PrivacyRequestAcceptedResponse, status_code=status.HTTP_202_ACCEPTED)
@customer_router.post(
    "/",
    response_model=PrivacyRequestAcceptedResponse,
    status_code=status.HTTP_202_ACCEPTED,
    include_in_schema=False,
)
async def create_privacy_request(
    payload: PrivacyRequestCreateRequest,
    response: Response,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    current_user=Depends(get_current_active_web_user),
    current_realm=Depends(get_request_web_auth_realm),
    db: AsyncSession = Depends(get_db),
) -> PrivacyRequestAcceptedResponse:
    try:
        reason_code, notes = _combine_legacy_notes(payload)
        result = await _service(db).create_customer_request(
            current_user=current_user,
            current_realm=current_realm,
            request_type=payload.request_type,
            reason_code=reason_code,
            notes=notes,
            locale=payload.locale,
            idempotency_key=idempotency_key,
        )
    except Exception as exc:
        _raise_http(exc)
    if result.existing:
        response.status_code = status.HTTP_200_OK
    detail = await _service(db).get_admin_request(reference=result.request.public_id)
    return PrivacyRequestAcceptedResponse(
        privacy_request_reference=result.request.public_id,
        ticket_reference=result.support_ticket.public_id,
        request_type=result.request.request_type,
        status=result.request.status,
        message=_message_for_request(result.request.request_type),
        submitted_at=result.request.submitted_at,
        manual_fulfillment_target_days=_manual_target_days(detail),
        existing=result.existing,
    )


@customer_router.get("", response_model=PrivacyRequestListResponse)
async def list_customer_privacy_requests(
    request_type: PrivacyRequestTypeLiteral | None = None,
    request_status: PrivacyRequestStatusLiteral | None = Query(default=None, alias="status"),
    cursor: str | None = None,
    limit: int = Query(50, ge=1, le=100),
    current_user=Depends(get_current_active_web_user),
    current_realm=Depends(get_request_web_auth_realm),
    db: AsyncSession = Depends(get_db),
) -> PrivacyRequestListResponse:
    try:
        service = _service(db)
        result = await service.list_customer_requests(
            auth_realm_id=current_realm.auth_realm.id,
            principal_subject=current_user.id,
            request_type=request_type,
            status=request_status,
            cursor=cursor,
            limit=limit,
        )
        responses = [
            _summary_response(
                await service.get_customer_request(
                    auth_realm_id=current_realm.auth_realm.id,
                    principal_subject=current_user.id,
                    reference=request.public_id,
                )
            )
            for request in result.requests
        ]
        return PrivacyRequestListResponse(requests=responses, next_cursor=result.next_cursor)
    except Exception as exc:
        _raise_http(exc)


@customer_router.get("/{reference}", response_model=CustomerPrivacyRequestDetailResponse)
async def get_customer_privacy_request(
    reference: str,
    current_user=Depends(get_current_active_web_user),
    current_realm=Depends(get_request_web_auth_realm),
    db: AsyncSession = Depends(get_db),
) -> CustomerPrivacyRequestDetailResponse:
    try:
        detail = await _service(db).get_customer_request(
            auth_realm_id=current_realm.auth_realm.id,
            principal_subject=current_user.id,
            reference=reference,
        )
        return _customer_detail_response(detail)
    except Exception as exc:
        _raise_http(exc)


@customer_router.post("/{reference}/cancel", response_model=CustomerPrivacyRequestDetailResponse)
async def cancel_customer_privacy_request(
    reference: str,
    current_user=Depends(get_current_active_web_user),
    current_realm=Depends(get_request_web_auth_realm),
    db: AsyncSession = Depends(get_db),
) -> CustomerPrivacyRequestDetailResponse:
    try:
        detail = await _service(db).cancel_customer_request(
            auth_realm_id=current_realm.auth_realm.id,
            principal_subject=current_user.id,
            reference=reference,
        )
        return _customer_detail_response(detail)
    except Exception as exc:
        _raise_http(exc)


@admin_router.get("", response_model=AdminPrivacyRequestListResponse)
async def list_admin_privacy_requests(
    request_status: PrivacyRequestStatusLiteral | None = Query(default=None, alias="status"),
    request_type: PrivacyRequestTypeLiteral | None = None,
    assigned_admin_id: UUID | None = None,
    overdue: bool | None = None,
    submitted_from: datetime | None = None,
    submitted_to: datetime | None = None,
    query: str | None = Query(default=None, max_length=120),
    cursor: str | None = None,
    limit: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    _admin=Depends(require_permission(Permission.PRIVACY_REQUEST_READ)),
) -> AdminPrivacyRequestListResponse:
    try:
        service = _service(db)
        result = await service.list_admin_requests(
            status=request_status,
            request_type=request_type,
            assigned_admin_id=assigned_admin_id,
            overdue=overdue,
            submitted_from=submitted_from,
            submitted_to=submitted_to,
            query=query,
            cursor=cursor,
            limit=limit,
        )
        responses = [
            _admin_summary_response(await _detail_for_summary(service, request.public_id))
            for request in result.requests
        ]
        return AdminPrivacyRequestListResponse(requests=responses, next_cursor=result.next_cursor)
    except Exception as exc:
        _raise_http(exc)


@admin_router.get("/queue-count", response_model=dict[str, int])
async def count_admin_privacy_requests(
    db: AsyncSession = Depends(get_db),
    _admin=Depends(require_permission(Permission.PRIVACY_REQUEST_READ)),
) -> dict[str, int]:
    return {"count": await _service(db).count_admin_action_required()}


@admin_router.get("/{reference}", response_model=AdminPrivacyRequestDetailResponse)
async def get_admin_privacy_request(
    reference: str,
    db: AsyncSession = Depends(get_db),
    _admin=Depends(require_permission(Permission.PRIVACY_REQUEST_READ)),
) -> AdminPrivacyRequestDetailResponse:
    try:
        detail = await _service(db).get_admin_request(reference=reference)
        return _admin_detail_response(detail)
    except Exception as exc:
        _raise_http(exc)


@admin_router.post("/{reference}/start-review", response_model=AdminPrivacyRequestDetailResponse)
async def start_privacy_review(
    reference: str,
    payload: StartReviewRequest,
    db: AsyncSession = Depends(get_db),
    admin=Depends(require_permission(Permission.PRIVACY_REQUEST_REVIEW)),
) -> AdminPrivacyRequestDetailResponse:
    try:
        return _admin_detail_response(
            await _service(db).start_review(
                reference=reference,
                admin_id=admin.id,
                assign_to_self=payload.assign_to_self,
            )
        )
    except Exception as exc:
        _raise_http(exc)


@admin_router.post("/{reference}/request-identity-verification", response_model=AdminPrivacyRequestDetailResponse)
async def request_privacy_identity_verification(
    reference: str,
    payload: RequestIdentityVerificationRequest,
    db: AsyncSession = Depends(get_db),
    admin=Depends(require_permission(Permission.PRIVACY_REQUEST_REVIEW)),
) -> AdminPrivacyRequestDetailResponse:
    try:
        return _admin_detail_response(
            await _service(db).request_identity_verification(
                reference=reference,
                admin_id=admin.id,
                message=payload.message,
            )
        )
    except Exception as exc:
        _raise_http(exc)


@admin_router.post("/{reference}/verify-identity", response_model=AdminPrivacyRequestDetailResponse)
async def verify_privacy_identity(
    reference: str,
    payload: VerifyIdentityRequest,
    db: AsyncSession = Depends(get_db),
    admin=Depends(require_permission(Permission.PRIVACY_REQUEST_REVIEW)),
) -> AdminPrivacyRequestDetailResponse:
    try:
        return _admin_detail_response(
            await _service(db).verify_identity(
                reference=reference,
                admin_id=admin.id,
                verification_method=payload.verification_method,
                safe_note=payload.safe_note,
            )
        )
    except Exception as exc:
        _raise_http(exc)


@admin_router.post("/{reference}/approve", response_model=AdminPrivacyRequestDetailResponse)
async def approve_privacy_request(
    reference: str,
    payload: DecisionRequest,
    db: AsyncSession = Depends(get_db),
    admin=Depends(require_permission(Permission.PRIVACY_REQUEST_REVIEW)),
) -> AdminPrivacyRequestDetailResponse:
    try:
        return _admin_detail_response(
            await _service(db).approve(
                reference=reference,
                admin_id=admin.id,
                decision_reason=payload.decision_reason,
            )
        )
    except Exception as exc:
        _raise_http(exc)


@admin_router.post("/{reference}/deny", response_model=AdminPrivacyRequestDetailResponse)
async def deny_privacy_request(
    reference: str,
    payload: DecisionRequest,
    db: AsyncSession = Depends(get_db),
    admin=Depends(require_permission(Permission.PRIVACY_REQUEST_REVIEW)),
) -> AdminPrivacyRequestDetailResponse:
    try:
        return _admin_detail_response(
            await _service(db).deny(
                reference=reference,
                admin_id=admin.id,
                decision_reason=payload.decision_reason,
            )
        )
    except Exception as exc:
        _raise_http(exc)


@admin_router.post("/{reference}/schedule", response_model=AdminPrivacyRequestDetailResponse)
async def schedule_privacy_request(
    reference: str,
    payload: ScheduleRequest,
    db: AsyncSession = Depends(get_db),
    admin=Depends(require_permission(Permission.PRIVACY_REQUEST_REVIEW)),
) -> AdminPrivacyRequestDetailResponse:
    try:
        return _admin_detail_response(
            await _service(db).schedule(
                reference=reference,
                admin_id=admin.id,
                scheduled_for=payload.scheduled_for,
            )
        )
    except Exception as exc:
        _raise_http(exc)


@admin_router.post("/{reference}/execute", response_model=AdminPrivacyRequestDetailResponse)
async def execute_privacy_request(
    reference: str,
    payload: ExecuteRequest,
    db: AsyncSession = Depends(get_db),
    admin=Depends(require_permission(Permission.PRIVACY_REQUEST_FULFILL)),
    redis_client: redis.Redis = Depends(get_redis),
    remnawave_client: RemnawaveClient = Depends(get_remnawave_client),
) -> AdminPrivacyRequestDetailResponse:
    if payload.confirm_text != "DELETE":
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Type DELETE to execute")
    try:
        return _admin_detail_response(
            await _service(db).execute_account_deletion(
                reference=reference,
                admin_id=admin.id,
                redis_client=redis_client,
                user_gateway=RemnawaveUserGateway(remnawave_client),
            )
        )
    except Exception as exc:
        _raise_http(exc)


@admin_router.post("/{reference}/retry", response_model=AdminPrivacyRequestDetailResponse)
async def retry_privacy_request(
    reference: str,
    payload: ScheduleRequest,
    db: AsyncSession = Depends(get_db),
    admin=Depends(require_permission(Permission.PRIVACY_REQUEST_REVIEW)),
) -> AdminPrivacyRequestDetailResponse:
    try:
        return _admin_detail_response(
            await _service(db).retry_failed(
                reference=reference,
                admin_id=admin.id,
                scheduled_for=payload.scheduled_for,
            )
        )
    except Exception as exc:
        _raise_http(exc)
