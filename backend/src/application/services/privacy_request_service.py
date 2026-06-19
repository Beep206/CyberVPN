"""Durable privacy request workflow service."""

from __future__ import annotations

import hashlib
import re
import secrets
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

import redis.asyncio as redis
from sqlalchemy import String, cast, func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.application.events.outbox import EventOutboxService, OutboxActorContext
from src.application.services.customer_shadow_service import ensure_customer_web_mobile_shadow
from src.application.services.support_ticket_service import SupportTicketService
from src.application.use_cases.auth.delete_account import DeleteAccountUseCase
from src.application.use_cases.auth_realms import RealmResolution
from src.application.use_cases.mobile_auth.delete_account import MobileDeleteAccountUseCase
from src.domain.entities.privacy_request import (
    ACTIVE_PRIVACY_REQUEST_STATUSES,
    CUSTOMER_CANCELABLE_PRIVACY_REQUEST_STATUSES,
    InvalidPrivacyRequestTransitionError,
    PrivacyRequestActorType,
    PrivacyRequestNotFoundError,
    PrivacyRequestStatus,
    PrivacyRequestType,
    assert_privacy_transition,
)
from src.domain.entities.support_ticket import SupportTicketStatus
from src.domain.exceptions import UserNotFoundError
from src.infrastructure.database.models.admin_user_model import AdminUserModel
from src.infrastructure.database.models.mobile_user_model import MobileUserModel
from src.infrastructure.database.models.privacy_request_model import PrivacyRequestEventModel, PrivacyRequestModel
from src.infrastructure.database.models.support_ticket_model import SupportTicketModel
from src.infrastructure.database.repositories.admin_user_repo import AdminUserRepository
from src.infrastructure.database.repositories.mobile_user_repo import MobileUserRepository
from src.infrastructure.database.repositories.support_ticket_repo import SQLAlchemySupportTicketRepository
from src.infrastructure.remnawave.user_gateway import RemnawaveUserGateway
from src.presentation.api.shared import (
    Stage1PrivacyRequestInput,
    Stage1SupportChannel,
    build_stage1_privacy_request,
)

PUBLIC_ID_ALPHABET = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"
PRIVACY_CREATE_RATE_LIMIT_PER_DAY = 3
NOTES_MAX_CHARS = 700
DECISION_REASON_MAX_CHARS = 500

SECRET_REDACTION_PATTERNS = (
    (re.compile(r"\b(?:https?|vless|vmess|trojan|ss|shadowsocks|wireguard)://\S+", re.I), "[redacted-url]"),
    (re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.I), "[redacted-email]"),
    (re.compile(r"\b\d{6,}:[A-Za-z0-9_-]{20,}\b"), "[redacted-telegram-token]"),
    (re.compile(r"\beyJ[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\b"), "[redacted-jwt]"),
    (re.compile(r"(?<![A-Za-z0-9])[A-Za-z0-9_+=/-]{48,}(?![A-Za-z0-9])"), "[redacted-secret]"),
)


class PrivacyRequestConflictError(Exception):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


class PrivacyRequestRateLimitedError(Exception):
    def __init__(self, retry_after_seconds: int) -> None:
        super().__init__("Privacy request rate limit exceeded")
        self.retry_after_seconds = retry_after_seconds


@dataclass(frozen=True, slots=True)
class PrivacyRequestCreateResult:
    request: PrivacyRequestModel
    support_ticket: SupportTicketModel
    existing: bool


@dataclass(frozen=True, slots=True)
class PrivacyRequestListResult:
    requests: tuple[PrivacyRequestModel, ...]
    next_cursor: str | None


@dataclass(frozen=True, slots=True)
class PrivacyRequestDetail:
    request: PrivacyRequestModel
    support_ticket: SupportTicketModel | None
    customer_account: MobileUserModel | None
    events: tuple[PrivacyRequestEventModel, ...]


def redact_privacy_notes(value: str | None) -> str | None:
    if value is None:
        return None
    redacted = value.strip()
    for pattern, replacement in SECRET_REDACTION_PATTERNS:
        redacted = pattern.sub(replacement, redacted)
    return redacted[:NOTES_MAX_CHARS] if redacted else None


def _utc_now() -> datetime:
    return datetime.now(UTC)


def _normalize_status(value: PrivacyRequestStatus | str | None) -> PrivacyRequestStatus | None:
    if value is None:
        return None
    return value if isinstance(value, PrivacyRequestStatus) else PrivacyRequestStatus(str(value))


def _normalize_request_type(value: PrivacyRequestType | str) -> PrivacyRequestType:
    return value if isinstance(value, PrivacyRequestType) else PrivacyRequestType(str(value))


def _public_id(prefix: str) -> str:
    suffix = "".join(secrets.choice(PUBLIC_ID_ALPHABET) for _ in range(18))
    return f"{prefix}-{suffix}"


def _hash_idempotency_key(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    if not normalized:
        return None
    try:
        uuid.UUID(normalized)
    except ValueError as exc:
        raise ValueError("Idempotency-Key must be a UUID") from exc
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def _request_active_status_values() -> tuple[str, ...]:
    return tuple(status.value for status in ACTIVE_PRIVACY_REQUEST_STATUSES)


def _safe_decision_reason(value: str | None, *, required: bool = False) -> str | None:
    redacted = redact_privacy_notes(value)
    if required and not redacted:
        raise ValueError("Decision reason is required")
    if redacted and len(redacted) > DECISION_REASON_MAX_CHARS:
        return redacted[:DECISION_REASON_MAX_CHARS]
    return redacted


class PrivacyRequestService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._support = SupportTicketService(SQLAlchemySupportTicketRepository(session))
        self._outbox = EventOutboxService(session)

    async def create_customer_request(
        self,
        *,
        current_user: AdminUserModel,
        current_realm: RealmResolution,
        request_type: PrivacyRequestType | str,
        reason_code: str | None,
        notes: str | None,
        locale: str | None,
        idempotency_key: str | None,
    ) -> PrivacyRequestCreateResult:
        request_kind = _normalize_request_type(request_type)
        key_hash = _hash_idempotency_key(idempotency_key)
        principal_type = "customer"
        principal_subject = current_user.id
        auth_realm_id = current_realm.auth_realm.id

        if key_hash:
            existing = await self._get_by_idempotency_hash(key_hash)
            if existing is not None:
                if (
                    existing.auth_realm_id != auth_realm_id
                    or existing.principal_subject != principal_subject
                    or existing.principal_type != principal_type
                ):
                    raise PrivacyRequestConflictError(
                        "IDEMPOTENCY_KEY_REUSED",
                        "Idempotency key already belongs to another request",
                    )
                await self._append_outbox_event(existing, "privacy_request.existing_returned")
                return PrivacyRequestCreateResult(
                    request=existing,
                    support_ticket=await self._get_support_ticket_required(existing.support_ticket_id),
                    existing=True,
                )

        active = await self._get_active_customer_request(
            auth_realm_id=auth_realm_id,
            principal_type=principal_type,
            principal_subject=principal_subject,
            request_type=request_kind,
        )
        if active is not None:
            await self._append_outbox_event(active, "privacy_request.existing_returned")
            return PrivacyRequestCreateResult(
                request=active,
                support_ticket=await self._get_support_ticket_required(active.support_ticket_id),
                existing=True,
            )

        await self._enforce_daily_create_rate_limit(
            auth_realm_id=auth_realm_id,
            principal_type=principal_type,
            principal_subject=principal_subject,
        )

        customer_account = await ensure_customer_web_mobile_shadow(
            db=self._session,
            user=current_user,
            current_realm=current_realm,
        )
        if current_realm.realm_type == "customer" and current_user.email and customer_account is None:
            raise PrivacyRequestConflictError(
                "CUSTOMER_SHADOW_CONFLICT",
                "Customer resource account could not be safely resolved",
            )

        notes_redacted = redact_privacy_notes(notes)
        reason_redacted = redact_privacy_notes(reason_code)
        privacy_request_id = uuid.uuid4()
        privacy_public_id = await self._new_unique_privacy_public_id()
        decision = build_stage1_privacy_request(
            Stage1PrivacyRequestInput(
                request_kind=request_kind.value,
                channel=Stage1SupportChannel.WEB_CONTACT_FORM,
                user_reference=privacy_public_id,
                contact=None,
                notes=notes_redacted,
            )
        )
        support_message = self._build_initial_support_message(
            public_id=privacy_public_id,
            request_type=request_kind,
            reason_code=reason_redacted,
            notes_redacted=notes_redacted,
        )
        support_ticket = await self._support.create_privacy_ticket(
            customer_account_id=customer_account.id if customer_account is not None else None,
            actor_id=principal_subject,
            request_public_id=privacy_public_id,
            request_type=request_kind.value,
            legacy_routing_reference=decision.ticket.reference,
            message=support_message,
            metadata={
                "privacy_request_id": str(privacy_request_id),
                "privacy_request_public_id": privacy_public_id,
                "request_type": request_kind.value,
            },
        )

        request = PrivacyRequestModel(
            id=privacy_request_id,
            public_id=privacy_public_id,
            auth_realm_id=auth_realm_id,
            principal_type=principal_type,
            principal_subject=principal_subject,
            customer_account_id=customer_account.id if customer_account is not None else None,
            support_ticket_id=support_ticket.id,
            request_type=request_kind.value,
            status=PrivacyRequestStatus.SUBMITTED.value,
            reason_code=reason_redacted,
            notes_redacted=notes_redacted,
            locale=locale,
            idempotency_key_hash=key_hash,
            policy_snapshot=self._policy_snapshot(decision),
            submitted_at=_utc_now(),
        )
        self._session.add(request)
        try:
            await self._session.flush()
        except IntegrityError:
            raise PrivacyRequestConflictError(
                "ACTIVE_PRIVACY_REQUEST_EXISTS",
                "An active privacy request already exists",
            ) from None

        await self._add_event(
            request,
            event_type="created",
            actor_type=PrivacyRequestActorType.CUSTOMER,
            actor_id=principal_subject,
            to_status=PrivacyRequestStatus.SUBMITTED,
            safe_summary="Customer submitted privacy request",
            metadata={"support_ticket_reference": support_ticket.public_id},
        )
        await self._append_outbox_event(request, "privacy_request.created")
        return PrivacyRequestCreateResult(
            request=await self._get_required_by_id(request.id),
            support_ticket=await self._get_support_ticket_required(support_ticket.id),
            existing=False,
        )

    async def list_customer_requests(
        self,
        *,
        auth_realm_id: UUID,
        principal_subject: UUID,
        request_type: PrivacyRequestType | str | None = None,
        status: PrivacyRequestStatus | str | None = None,
        cursor: str | None = None,
        limit: int = 50,
    ) -> PrivacyRequestListResult:
        offset = self._parse_cursor(cursor)
        bounded_limit = min(max(limit, 1), 100)
        stmt = (
            select(PrivacyRequestModel)
            .options(selectinload(PrivacyRequestModel.events))
            .where(
                PrivacyRequestModel.auth_realm_id == auth_realm_id,
                PrivacyRequestModel.principal_subject == principal_subject,
                PrivacyRequestModel.principal_type == "customer",
            )
        )
        if request_type is not None:
            stmt = stmt.where(PrivacyRequestModel.request_type == _normalize_request_type(request_type).value)
        normalized_status = _normalize_status(status)
        if normalized_status is not None:
            stmt = stmt.where(PrivacyRequestModel.status == normalized_status.value)
        stmt = stmt.order_by(PrivacyRequestModel.submitted_at.desc(), PrivacyRequestModel.id.desc())
        result = await self._session.execute(stmt.offset(offset).limit(bounded_limit + 1))
        rows = list(result.scalars().all())
        next_cursor = str(offset + bounded_limit) if len(rows) > bounded_limit else None
        return PrivacyRequestListResult(requests=tuple(rows[:bounded_limit]), next_cursor=next_cursor)

    async def get_customer_request(
        self,
        *,
        auth_realm_id: UUID,
        principal_subject: UUID,
        reference: str,
    ) -> PrivacyRequestDetail:
        request = await self._get_by_reference(reference)
        if (
            request is None
            or request.auth_realm_id != auth_realm_id
            or request.principal_subject != principal_subject
            or request.principal_type != "customer"
        ):
            raise PrivacyRequestNotFoundError("Privacy request not found")
        return await self._detail(request)

    async def cancel_customer_request(
        self,
        *,
        auth_realm_id: UUID,
        principal_subject: UUID,
        reference: str,
    ) -> PrivacyRequestDetail:
        request = await self._get_customer_request_for_update(
            auth_realm_id=auth_realm_id,
            principal_subject=principal_subject,
            reference=reference,
        )
        current = PrivacyRequestStatus(request.status)
        if current not in CUSTOMER_CANCELABLE_PRIVACY_REQUEST_STATUSES:
            raise InvalidPrivacyRequestTransitionError("Privacy request can no longer be canceled")
        await self._transition(
            request,
            to_status=PrivacyRequestStatus.CANCELED,
            actor_type=PrivacyRequestActorType.CUSTOMER,
            actor_id=principal_subject,
            safe_summary="Customer canceled privacy request",
            event_type="canceled",
        )
        request.canceled_at = _utc_now()
        request.canceled_by = principal_subject
        await self._sync_support_status(request, SupportTicketStatus.CLOSED)
        await self._append_outbox_event(request, "privacy_request.canceled")
        return await self._detail(request)

    async def list_admin_requests(
        self,
        *,
        status: PrivacyRequestStatus | str | None = None,
        request_type: PrivacyRequestType | str | None = None,
        assigned_admin_id: UUID | None = None,
        overdue: bool | None = None,
        submitted_from: datetime | None = None,
        submitted_to: datetime | None = None,
        query: str | None = None,
        cursor: str | None = None,
        limit: int = 50,
    ) -> PrivacyRequestListResult:
        offset = self._parse_cursor(cursor)
        bounded_limit = min(max(limit, 1), 100)
        stmt = select(PrivacyRequestModel).options(selectinload(PrivacyRequestModel.events))
        normalized_status = _normalize_status(status)
        if normalized_status is not None:
            stmt = stmt.where(PrivacyRequestModel.status == normalized_status.value)
        if request_type is not None:
            stmt = stmt.where(PrivacyRequestModel.request_type == _normalize_request_type(request_type).value)
        if assigned_admin_id is not None:
            stmt = stmt.where(PrivacyRequestModel.assigned_admin_id == assigned_admin_id)
        if submitted_from is not None:
            stmt = stmt.where(PrivacyRequestModel.submitted_at >= submitted_from)
        if submitted_to is not None:
            stmt = stmt.where(PrivacyRequestModel.submitted_at <= submitted_to)
        if overdue:
            stmt = stmt.where(
                PrivacyRequestModel.status.in_(_request_active_status_values()),
                PrivacyRequestModel.submitted_at <= _utc_now() - timedelta(days=30),
            )
        stmt = self._apply_admin_query(stmt, query)
        stmt = stmt.order_by(PrivacyRequestModel.submitted_at.desc(), PrivacyRequestModel.id.desc())
        result = await self._session.execute(stmt.offset(offset).limit(bounded_limit + 1))
        rows = list(result.scalars().unique().all())
        next_cursor = str(offset + bounded_limit) if len(rows) > bounded_limit else None
        return PrivacyRequestListResult(requests=tuple(rows[:bounded_limit]), next_cursor=next_cursor)

    async def count_admin_action_required(self) -> int:
        stmt = (
            select(func.count())
            .select_from(PrivacyRequestModel)
            .where(
                PrivacyRequestModel.status.in_(
                    (
                        PrivacyRequestStatus.SUBMITTED.value,
                        PrivacyRequestStatus.IDENTITY_VERIFICATION.value,
                        PrivacyRequestStatus.PENDING_DECISION.value,
                        PrivacyRequestStatus.FAILED.value,
                    )
                )
            )
        )
        result = await self._session.execute(stmt)
        return int(result.scalar_one() or 0)

    async def get_admin_request(self, *, reference: str) -> PrivacyRequestDetail:
        request = await self._get_by_reference(reference)
        if request is None:
            raise PrivacyRequestNotFoundError("Privacy request not found")
        return await self._detail(request)

    async def start_review(
        self,
        *,
        reference: str,
        admin_id: UUID,
        assign_to_self: bool,
    ) -> PrivacyRequestDetail:
        request = await self._get_admin_request_for_update(reference)
        await self._transition(
            request,
            to_status=PrivacyRequestStatus.IDENTITY_VERIFICATION,
            actor_type=PrivacyRequestActorType.ADMIN,
            actor_id=admin_id,
            safe_summary="Privacy review started",
            event_type="review_started",
        )
        now = _utc_now()
        request.review_started_at = now
        if assign_to_self:
            request.assigned_admin_id = admin_id
            await self._sync_support_assignment(request, admin_id)
        await self._append_outbox_event(request, "privacy_request.review_started")
        return await self._detail(request)

    async def request_identity_verification(
        self,
        *,
        reference: str,
        admin_id: UUID,
        message: str,
    ) -> PrivacyRequestDetail:
        request = await self._get_admin_request_for_update(reference)
        if PrivacyRequestStatus(request.status) != PrivacyRequestStatus.IDENTITY_VERIFICATION:
            raise InvalidPrivacyRequestTransitionError("Identity verification can only be requested during review")
        safe_message = _safe_decision_reason(message, required=True)
        ticket = await self._get_support_ticket_required(request.support_ticket_id)
        await self._support.add_admin_reply(ticket_ref=ticket.public_id, admin_id=admin_id, message=safe_message or "")
        await self._add_event(
            request,
            event_type="identity_verification_requested",
            actor_type=PrivacyRequestActorType.ADMIN,
            actor_id=admin_id,
            from_status=PrivacyRequestStatus.IDENTITY_VERIFICATION,
            to_status=PrivacyRequestStatus.IDENTITY_VERIFICATION,
            safe_summary="Identity verification requested via support ticket",
        )
        await self._append_outbox_event(request, "privacy_request.identity_verification_requested")
        return await self._detail(request)

    async def verify_identity(
        self,
        *,
        reference: str,
        admin_id: UUID,
        verification_method: str,
        safe_note: str | None,
    ) -> PrivacyRequestDetail:
        request = await self._get_admin_request_for_update(reference)
        await self._transition(
            request,
            to_status=PrivacyRequestStatus.PENDING_DECISION,
            actor_type=PrivacyRequestActorType.ADMIN,
            actor_id=admin_id,
            safe_summary="Customer identity verified",
            event_type="identity_verified",
            metadata={
                "verification_method": verification_method[:80],
                "safe_note": _safe_decision_reason(safe_note),
            },
        )
        request.identity_verified_at = _utc_now()
        request.identity_verified_by = admin_id
        await self._append_outbox_event(request, "privacy_request.identity_verified")
        return await self._detail(request)

    async def approve(
        self,
        *,
        reference: str,
        admin_id: UUID,
        decision_reason: str,
    ) -> PrivacyRequestDetail:
        request = await self._get_admin_request_for_update(reference)
        if request.identity_verified_at is None:
            raise InvalidPrivacyRequestTransitionError("Identity verification is required before approval")
        reason = _safe_decision_reason(decision_reason, required=True)
        await self._transition(
            request,
            to_status=PrivacyRequestStatus.APPROVED,
            actor_type=PrivacyRequestActorType.ADMIN,
            actor_id=admin_id,
            safe_summary="Privacy request approved",
            event_type="approved",
        )
        request.decision_at = _utc_now()
        request.decision_by = admin_id
        request.decision_reason = reason
        await self._append_outbox_event(request, "privacy_request.approved")
        return await self._detail(request)

    async def deny(
        self,
        *,
        reference: str,
        admin_id: UUID,
        decision_reason: str,
    ) -> PrivacyRequestDetail:
        request = await self._get_admin_request_for_update(reference)
        reason = _safe_decision_reason(decision_reason, required=True)
        await self._transition(
            request,
            to_status=PrivacyRequestStatus.DENIED,
            actor_type=PrivacyRequestActorType.ADMIN,
            actor_id=admin_id,
            safe_summary="Privacy request denied",
            event_type="denied",
        )
        request.decision_at = _utc_now()
        request.decision_by = admin_id
        request.decision_reason = reason
        await self._sync_support_status(request, SupportTicketStatus.RESOLVED)
        await self._append_outbox_event(request, "privacy_request.denied")
        return await self._detail(request)

    async def schedule(
        self,
        *,
        reference: str,
        admin_id: UUID,
        scheduled_for: datetime | None,
    ) -> PrivacyRequestDetail:
        request = await self._get_admin_request_for_update(reference)
        target = scheduled_for or _utc_now()
        await self._transition(
            request,
            to_status=PrivacyRequestStatus.SCHEDULED,
            actor_type=PrivacyRequestActorType.ADMIN,
            actor_id=admin_id,
            safe_summary="Privacy request scheduled for fulfillment",
            event_type="scheduled",
            metadata={"scheduled_for": target.isoformat()},
        )
        request.scheduled_for = target
        request.last_error_code = None
        request.last_error_redacted = None
        await self._append_outbox_event(request, "privacy_request.scheduled")
        return await self._detail(request)

    async def retry_failed(
        self,
        *,
        reference: str,
        admin_id: UUID,
        scheduled_for: datetime | None = None,
    ) -> PrivacyRequestDetail:
        return await self.schedule(reference=reference, admin_id=admin_id, scheduled_for=scheduled_for or _utc_now())

    async def execute_account_deletion(
        self,
        *,
        reference: str,
        admin_id: UUID,
        redis_client: redis.Redis,
        user_gateway: RemnawaveUserGateway,
    ) -> PrivacyRequestDetail:
        request = await self._get_admin_request_for_update(reference)
        if request.request_type != PrivacyRequestType.ACCOUNT_DELETION.value:
            raise InvalidPrivacyRequestTransitionError("Only account deletion requests can be executed")
        if PrivacyRequestStatus(request.status) != PrivacyRequestStatus.SCHEDULED:
            raise InvalidPrivacyRequestTransitionError("Privacy request must be scheduled before execution")
        if request.identity_verified_at is None or request.decision_at is None:
            raise InvalidPrivacyRequestTransitionError("Verified approval is required before execution")
        if request.scheduled_for:
            scheduled_for = request.scheduled_for
            if scheduled_for.tzinfo is None:
                scheduled_for = scheduled_for.replace(tzinfo=UTC)
            if scheduled_for.astimezone(UTC) > _utc_now():
                raise PrivacyRequestConflictError("PRIVACY_REQUEST_NOT_DUE", "Privacy request is not due yet")

        await self._add_event(
            request,
            event_type="fulfillment_started",
            actor_type=PrivacyRequestActorType.ADMIN,
            actor_id=admin_id,
            from_status=PrivacyRequestStatus.SCHEDULED,
            to_status=PrivacyRequestStatus.SCHEDULED,
            safe_summary="Account deletion fulfillment started",
        )
        await self._append_outbox_event(request, "privacy_request.fulfillment_started")

        try:
            mobile_repo = MobileUserRepository(self._session)
            mobile_user = await mobile_repo.get_by_id(request.principal_subject)
            mobile_result: dict[str, Any] = {"mobile_user_present": mobile_user is not None}
            if mobile_user is not None:
                result = await MobileDeleteAccountUseCase(
                    user_repo=mobile_repo,
                    user_gateway=user_gateway,
                    redis_client=redis_client,
                ).execute(request.principal_subject)
                mobile_result = {
                    "mobile_user_present": True,
                    "vpn_access_removed": result.vpn_access_removed,
                    "jwt_sessions_revoked": result.jwt_sessions_revoked,
                }

            try:
                await DeleteAccountUseCase(
                    user_repo=AdminUserRepository(self._session),
                    session=self._session,
                    redis_client=redis_client,
                ).execute(request.principal_subject)
            except UserNotFoundError:
                pass

            await self._transition(
                request,
                to_status=PrivacyRequestStatus.FULFILLED,
                actor_type=PrivacyRequestActorType.ADMIN,
                actor_id=admin_id,
                safe_summary="Account deletion fulfilled",
                event_type="fulfilled",
                metadata=mobile_result,
            )
            request.fulfilled_at = _utc_now()
            request.fulfilled_by = admin_id
            request.last_error_code = None
            request.last_error_redacted = None
            await self._sync_support_status(request, SupportTicketStatus.RESOLVED)
            await self._append_outbox_event(request, "privacy_request.fulfillment_succeeded")
        except Exception as exc:
            request.last_error_code = exc.__class__.__name__[:80]
            request.last_error_redacted = "Account deletion fulfillment failed; see service logs by request id"
            await self._transition(
                request,
                to_status=PrivacyRequestStatus.FAILED,
                actor_type=PrivacyRequestActorType.SYSTEM,
                actor_id=None,
                safe_summary="Account deletion fulfillment failed",
                event_type="fulfillment_failed",
                metadata={"error_code": request.last_error_code},
            )
            await self._sync_support_status(request, SupportTicketStatus.PENDING_SUPPORT)
            await self._append_outbox_event(request, "privacy_request.fulfillment_failed")
        return await self._detail(request)

    async def _get_by_idempotency_hash(self, key_hash: str) -> PrivacyRequestModel | None:
        result = await self._session.execute(
            select(PrivacyRequestModel)
            .options(selectinload(PrivacyRequestModel.events))
            .where(PrivacyRequestModel.idempotency_key_hash == key_hash)
        )
        return result.scalar_one_or_none()

    async def _get_active_customer_request(
        self,
        *,
        auth_realm_id: UUID,
        principal_type: str,
        principal_subject: UUID,
        request_type: PrivacyRequestType,
    ) -> PrivacyRequestModel | None:
        result = await self._session.execute(
            select(PrivacyRequestModel)
            .options(selectinload(PrivacyRequestModel.events))
            .where(
                PrivacyRequestModel.auth_realm_id == auth_realm_id,
                PrivacyRequestModel.principal_type == principal_type,
                PrivacyRequestModel.principal_subject == principal_subject,
                PrivacyRequestModel.request_type == request_type.value,
                PrivacyRequestModel.status.in_(_request_active_status_values()),
            )
            .order_by(PrivacyRequestModel.submitted_at.desc())
        )
        return result.scalars().first()

    async def _enforce_daily_create_rate_limit(
        self,
        *,
        auth_realm_id: UUID,
        principal_type: str,
        principal_subject: UUID,
    ) -> None:
        since = _utc_now() - timedelta(days=1)
        result = await self._session.execute(
            select(func.count())
            .select_from(PrivacyRequestModel)
            .where(
                PrivacyRequestModel.auth_realm_id == auth_realm_id,
                PrivacyRequestModel.principal_type == principal_type,
                PrivacyRequestModel.principal_subject == principal_subject,
                PrivacyRequestModel.submitted_at >= since,
            )
        )
        count = int(result.scalar_one() or 0)
        if count >= PRIVACY_CREATE_RATE_LIMIT_PER_DAY:
            raise PrivacyRequestRateLimitedError(retry_after_seconds=24 * 60 * 60)

    async def _new_unique_privacy_public_id(self) -> str:
        for _ in range(10):
            candidate = _public_id("PRV")
            result = await self._session.execute(
                select(PrivacyRequestModel.id).where(PrivacyRequestModel.public_id == candidate)
            )
            if result.scalar_one_or_none() is None:
                return candidate
        raise RuntimeError("Could not allocate privacy request public ID")

    def _build_initial_support_message(
        self,
        *,
        public_id: str,
        request_type: PrivacyRequestType,
        reason_code: str | None,
        notes_redacted: str | None,
    ) -> str:
        parts = [
            "Manual privacy review requested.",
            f"Privacy request: {public_id}",
            f"Request type: {request_type.value}",
        ]
        if reason_code:
            parts.append(f"Reason code: {reason_code}")
        if notes_redacted:
            parts.append(f"Notes: {notes_redacted}")
        return "\n".join(parts)

    def _policy_snapshot(self, decision) -> dict[str, Any]:
        return {
            "policy": "CyberVPN privacy request manual review v1",
            "legacy_ticket_reference": decision.ticket.reference,
            "target_queue": decision.ticket.target_queue,
            "priority": decision.ticket.priority.value,
            "support_state": decision.ticket.support_state.value,
            "ack_sla_minutes": decision.ticket.ack_sla_minutes,
            "customer_response_sla_minutes": decision.ticket.customer_response_sla_minutes,
            "manual_fulfillment_target_days": decision.manual_fulfillment_target_days,
            "required_actions": list(decision.escalation.rule.required_actions),
            "forbidden_actions": list(decision.escalation.rule.forbidden_actions),
            "audit_required": decision.escalation.rule.audit_required,
        }

    async def _get_required_by_id(self, request_id: UUID) -> PrivacyRequestModel:
        result = await self._session.execute(
            select(PrivacyRequestModel)
            .options(selectinload(PrivacyRequestModel.events))
            .where(PrivacyRequestModel.id == request_id)
        )
        request = result.scalar_one_or_none()
        if request is None:
            raise PrivacyRequestNotFoundError("Privacy request not found")
        return request

    async def _get_by_reference(self, reference: str) -> PrivacyRequestModel | None:
        normalized = reference.strip()
        stmt = select(PrivacyRequestModel).options(selectinload(PrivacyRequestModel.events))
        try:
            request_id = UUID(normalized)
        except ValueError:
            stmt = stmt.where(PrivacyRequestModel.public_id == normalized)
        else:
            stmt = stmt.where(or_(PrivacyRequestModel.id == request_id, PrivacyRequestModel.public_id == normalized))
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def _get_customer_request_for_update(
        self,
        *,
        auth_realm_id: UUID,
        principal_subject: UUID,
        reference: str,
    ) -> PrivacyRequestModel:
        request = await self._get_for_update(reference)
        if (
            request.auth_realm_id != auth_realm_id
            or request.principal_subject != principal_subject
            or request.principal_type != "customer"
        ):
            raise PrivacyRequestNotFoundError("Privacy request not found")
        return request

    async def _get_admin_request_for_update(self, reference: str) -> PrivacyRequestModel:
        return await self._get_for_update(reference)

    async def _get_for_update(self, reference: str) -> PrivacyRequestModel:
        normalized = reference.strip()
        stmt = select(PrivacyRequestModel).options(selectinload(PrivacyRequestModel.events)).with_for_update()
        try:
            request_id = UUID(normalized)
        except ValueError:
            stmt = stmt.where(PrivacyRequestModel.public_id == normalized)
        else:
            stmt = stmt.where(or_(PrivacyRequestModel.id == request_id, PrivacyRequestModel.public_id == normalized))
        result = await self._session.execute(stmt)
        request = result.scalar_one_or_none()
        if request is None:
            raise PrivacyRequestNotFoundError("Privacy request not found")
        return request

    async def _get_support_ticket_required(self, ticket_id: UUID) -> SupportTicketModel:
        ticket = await self._session.get(SupportTicketModel, ticket_id)
        if ticket is None:
            raise PrivacyRequestConflictError("SUPPORT_TICKET_MISSING", "Linked support ticket is missing")
        return ticket

    async def _detail(self, request: PrivacyRequestModel) -> PrivacyRequestDetail:
        request = await self._get_required_by_id(request.id)
        support_ticket = await self._session.get(SupportTicketModel, request.support_ticket_id)
        customer_account = None
        if request.customer_account_id is not None:
            customer_account = await self._session.get(MobileUserModel, request.customer_account_id)
        return PrivacyRequestDetail(
            request=request,
            support_ticket=support_ticket,
            customer_account=customer_account,
            events=tuple(request.events),
        )

    def _apply_admin_query(self, stmt, query: str | None):
        normalized = (query or "").strip()
        if not normalized:
            return stmt
        like = f"%{normalized}%"
        stmt = stmt.outerjoin(
            SupportTicketModel,
            SupportTicketModel.id == PrivacyRequestModel.support_ticket_id,
        ).outerjoin(
            MobileUserModel,
            MobileUserModel.id == PrivacyRequestModel.customer_account_id,
        )
        predicates = [
            PrivacyRequestModel.public_id.ilike(like),
            SupportTicketModel.public_id.ilike(like),
            cast(PrivacyRequestModel.principal_subject, String).ilike(like),
            cast(MobileUserModel.public_uid, String).ilike(like),
        ]
        return stmt.where(or_(*predicates))

    async def _transition(
        self,
        request: PrivacyRequestModel,
        *,
        to_status: PrivacyRequestStatus,
        actor_type: PrivacyRequestActorType,
        actor_id: UUID | None,
        safe_summary: str,
        event_type: str,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        from_status = PrivacyRequestStatus(request.status)
        assert_privacy_transition(from_status=from_status, to_status=to_status)
        now = _utc_now()
        request.status = to_status.value
        request.updated_at = now
        request.version += 1
        await self._add_event(
            request,
            event_type=event_type,
            actor_type=actor_type,
            actor_id=actor_id,
            from_status=from_status,
            to_status=to_status,
            safe_summary=safe_summary,
            metadata=metadata,
        )

    async def _add_event(
        self,
        request: PrivacyRequestModel,
        *,
        event_type: str,
        actor_type: PrivacyRequestActorType,
        actor_id: UUID | None,
        safe_summary: str,
        from_status: PrivacyRequestStatus | None = None,
        to_status: PrivacyRequestStatus | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        self._session.add(
            PrivacyRequestEventModel(
                privacy_request_id=request.id,
                event_type=event_type,
                actor_type=actor_type.value,
                actor_id=actor_id,
                from_status=from_status.value if from_status is not None else None,
                to_status=to_status.value if to_status is not None else None,
                safe_summary=safe_summary[:500],
                metadata_json=dict(metadata or {}),
                created_at=_utc_now(),
            )
        )
        await self._session.flush()

    async def _sync_support_status(self, request: PrivacyRequestModel, status: SupportTicketStatus) -> None:
        ticket = await self._session.get(SupportTicketModel, request.support_ticket_id)
        if ticket is None:
            return
        now = _utc_now()
        ticket.status = status.value
        ticket.updated_at = now
        if status == SupportTicketStatus.RESOLVED:
            ticket.resolved_at = now
        elif status == SupportTicketStatus.CLOSED:
            ticket.closed_at = now
        await self._session.flush()

    async def _sync_support_assignment(self, request: PrivacyRequestModel, admin_id: UUID) -> None:
        ticket = await self._session.get(SupportTicketModel, request.support_ticket_id)
        if ticket is None:
            return
        ticket.assigned_admin_id = admin_id
        ticket.updated_at = _utc_now()
        await self._session.flush()

    async def _append_outbox_event(self, request: PrivacyRequestModel, event_name: str) -> None:
        await self._outbox.append_event(
            event_name=event_name,
            aggregate_type="privacy_request",
            aggregate_id=str(request.id),
            partition_key=str(request.principal_subject),
            event_payload={
                "privacy_request_id": str(request.id),
                "privacy_request_reference": request.public_id,
                "request_type": request.request_type,
                "status": request.status,
            },
            actor_context=OutboxActorContext(
                principal_type=request.principal_type,
                principal_id=str(request.principal_subject),
                auth_realm_id=str(request.auth_realm_id),
            ),
            source_context={"source": "privacy_request_service"},
        )

    @staticmethod
    def _parse_cursor(cursor: str | None) -> int:
        if cursor is None:
            return 0
        try:
            value = int(cursor)
        except ValueError:
            return 0
        return max(value, 0)
