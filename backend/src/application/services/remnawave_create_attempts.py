"""Durable guards for Remnawave create mutations without upstream idempotency."""

from __future__ import annotations

import hashlib
import hmac
import json
import re
from dataclasses import dataclass
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.services.remnawave_identity_access import _acquire_remnawave_identity_registry_lock
from src.config.settings import settings
from src.domain.value_objects.remnawave_user_ref import RemnawaveUserRef
from src.infrastructure.database.models.mobile_user_model import MobileUserModel
from src.infrastructure.database.models.partner_model import ApiIdempotencyRecordModel

_SAFE_SCOPE_RE = re.compile(r"^[a-z0-9][a-z0-9_.:-]{2,79}$")
_SAFE_REFERENCE_KEY_RE = re.compile(r"^[a-z][a-z0-9_]{1,47}$")
_PENDING_STATES = frozenset({"pending", "reconciliation_required"})
_TERMINAL_STATES = frozenset({"completed", "rejected"})
_FORBIDDEN_REFERENCE_KEY_PARTS = frozenset(
    {
        "credential",
        "password",
        "private",
        "secret",
        "token",
    }
)


class RemnawaveCreateAttemptConflict(RuntimeError):
    """A create attempt cannot be replayed without authoritative reconciliation."""


@dataclass(frozen=True)
class RemnawaveCreateAttemptDecision:
    record: ApiIdempotencyRecordModel
    should_mutate: bool


@dataclass(frozen=True)
class RemnawaveGiftProvisioningAttemptDecision:
    gift_record: ApiIdempotencyRecordModel
    customer_record: ApiIdempotencyRecordModel
    should_mutate: bool


def remnawave_create_request_hash(payload: dict[str, Any]) -> str:
    """Hash a caller-provided redacted payload for replay-conflict detection."""

    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    return hashlib.sha256(b"cybervpn/remnawave-create/v1\0" + encoded).hexdigest()


def remnawave_create_sensitive_request_hash(payload: dict[str, Any]) -> str:
    """Bind sensitive create fields without persisting an enumerable digest.

    The JWT secret is used only as key material for this purpose-separated
    HMAC. Raw email/password values remain transient and never enter the
    idempotency record, logs, or response payload.
    """

    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    secret = settings.jwt_secret.get_secret_value().encode("utf-8")
    return hmac.new(
        secret,
        b"cybervpn/remnawave-create-request/v1\0" + encoded,
        hashlib.sha256,
    ).hexdigest()


def remnawave_customer_create_key(customer_account_id: object) -> str:
    """Return the shared account-create key used by every customer entrypoint."""

    return remnawave_create_request_hash({"customer_account_id": str(customer_account_id)})


async def _assert_customer_allows_new_provider_mutation(
    session: AsyncSession,
    customer_account_id: UUID,
) -> None:
    get_bind = getattr(session, "get_bind", None)
    if not callable(get_bind):
        return
    bind = get_bind()
    if getattr(getattr(bind, "dialect", None), "name", "") != "postgresql":
        return
    # The caller already holds the shared identity-registry advisory lock;
    # account retirement takes the exclusive form of that same transaction
    # lock before changing terminal state. A row-level FOR UPDATE is therefore
    # redundant and can self-deadlock when a separate saga-marker transaction
    # checks a customer whose outer transaction holds an FK KEY SHARE lock.
    customer_status = (
        await session.execute(select(MobileUserModel.status).where(MobileUserModel.id == customer_account_id))
    ).scalar_one_or_none()
    if customer_status is None or customer_status in {"deleting", "deleted"}:
        raise RemnawaveCreateAttemptConflict("Customer account no longer accepts Remnawave mutations")


class RemnawaveMutationAttemptService:
    """Persist a stop-before-retry marker around one provider mutation.

    Remnawave 3.x does not expose an idempotency key for these mutations.  The
    initial pending marker is therefore committed before the provider call.
    A crash, empty accepted response, or transport ambiguity leaves that
    marker latched until an operator reconciles it; no request path may issue
    the mutation again merely because the provider response was unavailable.
    """

    def __init__(self, session: AsyncSession, *, resource_type: str) -> None:
        self._session = session
        normalized_resource_type = resource_type.strip().lower()
        if not _SAFE_SCOPE_RE.fullmatch(normalized_resource_type):
            raise ValueError("Remnawave mutation resource type is invalid")
        self._resource_type = normalized_resource_type

    async def begin(
        self,
        *,
        scope: str,
        idempotency_key: str,
        request_hash: str,
        customer_account_id: UUID | None = None,
    ) -> RemnawaveCreateAttemptDecision:
        normalized_scope = scope.strip().lower()
        normalized_key = idempotency_key.strip()
        if not _SAFE_SCOPE_RE.fullmatch(normalized_scope):
            raise ValueError("Remnawave mutation scope is invalid")
        if not normalized_key or len(normalized_key) > 160:
            raise ValueError("Remnawave mutation idempotency key is invalid")
        if not re.fullmatch(r"[a-f0-9]{64}", request_hash):
            raise ValueError("Remnawave mutation request hash is invalid")

        if customer_account_id is not None:
            await _acquire_remnawave_identity_registry_lock(self._session, shared=True)
        existing = await self._get(normalized_scope, normalized_key)
        if existing is not None:
            return self._decision_for_existing(existing, request_hash=request_hash)
        if customer_account_id is not None:
            await _assert_customer_allows_new_provider_mutation(self._session, customer_account_id)

        record = ApiIdempotencyRecordModel(
            scope=normalized_scope,
            idempotency_key=normalized_key,
            resource_type=self._resource_type,
            resource_id=customer_account_id,
            request_hash=request_hash,
            response_payload={},
            status="pending",
            expires_at=None,
        )
        self._session.add(record)
        try:
            # This is an intentional saga boundary: the stop marker must
            # survive a process crash during the following provider request.
            await self._session.commit()
        except IntegrityError:
            await self._session.rollback()
            winner = await self._get(normalized_scope, normalized_key)
            if winner is None:
                raise
            return self._decision_for_existing(winner, request_hash=request_hash)
        return RemnawaveCreateAttemptDecision(record=record, should_mutate=True)

    async def mark_reconciliation_required(self, record: ApiIdempotencyRecordModel) -> None:
        await self.stage_reconciliation_required(record)
        await self._session.commit()

    async def stage_reconciliation_required(self, record: ApiIdempotencyRecordModel) -> None:
        """Stage an ambiguous outcome for an audit-atomic caller commit."""

        current = await self._lock_current_for_transition(record)
        if current.status in _TERMINAL_STATES:
            return
        if current.status not in _PENDING_STATES:
            raise RemnawaveCreateAttemptConflict("Remnawave mutation attempt is in an unsupported state")
        current.status = "reconciliation_required"
        current.response_payload = {}
        await self._session.flush()

    async def mark_completed(
        self,
        record: ApiIdempotencyRecordModel,
        *,
        user_ref: RemnawaveUserRef,
    ) -> None:
        numeric_id = user_ref.require_numeric_id()
        response_payload: dict[str, int | str] = {"numeric_user_id": numeric_id}
        if user_ref.legacy_uuid is not None:
            response_payload["legacy_uuid"] = str(user_ref.legacy_uuid)
        await self.mark_completed_reference(record, reference=response_payload)

    async def mark_completed_reference(
        self,
        record: ApiIdempotencyRecordModel,
        *,
        reference: dict[str, str | int | bool],
    ) -> None:
        """Persist a bounded non-sensitive provider reference for replay.

        Generic operator mutations may settle to a UUID, numeric id, name, or
        exact state without sharing the user-create response shape.  Raw
        configs, snippets, credentials, tokens, and provider payloads must
        never be stored in this broadly reused idempotency table.
        """

        if not 1 <= len(reference) <= 8:
            raise ValueError("Remnawave completion reference must contain 1..8 fields")
        normalized: dict[str, str | int | bool] = {}
        for raw_key, value in reference.items():
            key = raw_key.strip().lower()
            if not _SAFE_REFERENCE_KEY_RE.fullmatch(key) or any(part in key for part in _FORBIDDEN_REFERENCE_KEY_PARTS):
                raise ValueError("Remnawave completion reference key is unsafe")
            if isinstance(value, str):
                normalized_string = value.strip()
                if not normalized_string or len(normalized_string) > 255:
                    raise ValueError("Remnawave completion reference value is invalid")
                normalized[key] = normalized_string
            elif isinstance(value, bool):
                normalized[key] = value
            elif isinstance(value, int) and -(2**53 - 1) <= value <= 2**53 - 1:
                normalized[key] = value
            else:
                raise ValueError("Remnawave completion reference value is invalid")
        encoded = json.dumps(normalized, sort_keys=True, separators=(",", ":")).encode("utf-8")
        if len(encoded) > 2_048:
            raise ValueError("Remnawave completion reference is too large")
        current = await self._lock_current_for_transition(record)
        if current.status == "completed":
            if current.response_payload != normalized:
                raise RemnawaveCreateAttemptConflict("Completed Remnawave mutation has a different provider reference")
            return
        if current.status == "rejected":
            raise RemnawaveCreateAttemptConflict("Rejected Remnawave mutation cannot be completed")
        if current.status not in _PENDING_STATES:
            raise RemnawaveCreateAttemptConflict("Remnawave mutation attempt is in an unsupported state")
        current.status = "completed"
        current.response_payload = normalized
        await self._session.flush()

    async def mark_rejected(
        self,
        record: ApiIdempotencyRecordModel,
        *,
        error_code: str,
    ) -> None:
        """Close a definitively rejected provider request without raw errors."""

        await self.stage_rejected(record, error_code=error_code)
        await self._session.commit()

    async def stage_rejected(
        self,
        record: ApiIdempotencyRecordModel,
        *,
        error_code: str,
    ) -> None:
        """Stage a definitive rejection for an audit-atomic caller commit."""

        normalized_error = error_code.strip().lower()
        if not _SAFE_SCOPE_RE.fullmatch(normalized_error):
            raise ValueError("Remnawave rejection code is invalid")
        current = await self._lock_current_for_transition(record)
        rejected_payload = {"error_code": normalized_error}
        if current.status == "rejected":
            if current.response_payload != rejected_payload:
                raise RemnawaveCreateAttemptConflict("Rejected Remnawave mutation has a different provider error")
            return
        if current.status == "completed":
            raise RemnawaveCreateAttemptConflict("Completed Remnawave mutation cannot be rejected")
        if current.status not in _PENDING_STATES:
            raise RemnawaveCreateAttemptConflict("Remnawave mutation attempt is in an unsupported state")
        current.status = "rejected"
        current.response_payload = rejected_payload
        await self._session.flush()

    async def _lock_current_for_transition(
        self,
        record: ApiIdempotencyRecordModel,
    ) -> ApiIdempotencyRecordModel:
        """Refresh and lock the durable marker before a monotonic transition.

        A replay can load ``pending`` while the mutation winner is still in
        provider I/O.  Without this refresh it could later overwrite the
        winner's committed terminal state from its stale identity-map value.
        Holding the exact marker row through the caller-owned audit commit
        makes every transition observe the latest committed state.
        """

        result = await self._session.execute(
            select(ApiIdempotencyRecordModel)
            .where(ApiIdempotencyRecordModel.id == record.id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        current = result.scalars().one_or_none()
        if current is None:
            raise RemnawaveCreateAttemptConflict("Remnawave mutation attempt no longer exists")
        return current

    @staticmethod
    def completed_reference(record: ApiIdempotencyRecordModel) -> dict[str, str | int | bool] | None:
        if record.status != "completed" or not isinstance(record.response_payload, dict):
            return None
        reference: dict[str, str | int | bool] = {}
        for key, value in record.response_payload.items():
            if not isinstance(key, str) or not isinstance(value, (str, int, bool)):
                return None
            reference[key] = value
        return reference

    @staticmethod
    def completed_ref(record: ApiIdempotencyRecordModel) -> RemnawaveUserRef | None:
        if record.status != "completed":
            return None
        payload = dict(record.response_payload or {})
        try:
            legacy_uuid_raw = payload.get("legacy_uuid")
            return RemnawaveUserRef(
                id=payload.get("numeric_user_id"),
                legacy_uuid=UUID(str(legacy_uuid_raw)) if legacy_uuid_raw not in {None, ""} else None,
            )
        except (TypeError, ValueError):
            return None

    async def _get(self, scope: str, idempotency_key: str) -> ApiIdempotencyRecordModel | None:
        result = await self._session.execute(
            select(ApiIdempotencyRecordModel).where(
                ApiIdempotencyRecordModel.scope == scope,
                ApiIdempotencyRecordModel.idempotency_key == idempotency_key,
            )
        )
        return result.scalars().one_or_none()

    @staticmethod
    def _decision_for_existing(
        record: ApiIdempotencyRecordModel,
        *,
        request_hash: str,
    ) -> RemnawaveCreateAttemptDecision:
        if record.request_hash != request_hash:
            raise RemnawaveCreateAttemptConflict(
                "Remnawave mutation idempotency key was already used for another request"
            )
        if record.status in _PENDING_STATES or record.status == "completed":
            return RemnawaveCreateAttemptDecision(record=record, should_mutate=False)
        raise RemnawaveCreateAttemptConflict("Remnawave mutation attempt is in an unsupported state")


class RemnawaveCreateAttemptService(RemnawaveMutationAttemptService):
    """Compatibility wrapper for the shared Remnawave user-create latch."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, resource_type="remnawave_user_create")


class RemnawaveGiftProvisioningAttemptService:
    """Atomically reserve a one-use gift and its customer provider mutation.

    The gift record blocks a second customer after a crash or ambiguous
    provider response. The customer record preserves the cross-entrypoint
    create/update guard. Both records are committed in one transaction so a
    conflict can never leave only one of the two tombstones behind.
    """

    _GIFT_SCOPE = "remnawave-gift:provision"

    def __init__(self, session: AsyncSession, *, customer_resource_type: str) -> None:
        self._session = session
        normalized_resource_type = customer_resource_type.strip().lower()
        if not _SAFE_SCOPE_RE.fullmatch(normalized_resource_type):
            raise ValueError("Remnawave customer mutation resource type is invalid")
        self._customer_resource_type = normalized_resource_type

    async def begin(
        self,
        *,
        gift_code_id: UUID,
        customer_account_id: UUID,
        customer_scope: str,
        customer_idempotency_key: str,
        request_hash: str,
    ) -> RemnawaveGiftProvisioningAttemptDecision:
        normalized_customer_scope = customer_scope.strip().lower()
        normalized_customer_key = customer_idempotency_key.strip()
        if not _SAFE_SCOPE_RE.fullmatch(normalized_customer_scope):
            raise ValueError("Remnawave customer mutation scope is invalid")
        if not normalized_customer_key or len(normalized_customer_key) > 160:
            raise ValueError("Remnawave customer mutation idempotency key is invalid")
        if not re.fullmatch(r"[a-f0-9]{64}", request_hash):
            raise ValueError("Remnawave gift provisioning request hash is invalid")

        await _acquire_remnawave_identity_registry_lock(self._session, shared=True)
        gift_key = remnawave_create_request_hash({"gift_code_id": str(gift_code_id)})
        gift_record = await self._get(self._GIFT_SCOPE, gift_key)
        customer_record = await self._get(normalized_customer_scope, normalized_customer_key)
        if gift_record is not None or customer_record is not None:
            return self._decision_for_existing_pair(
                gift_record=gift_record,
                customer_record=customer_record,
                request_hash=request_hash,
            )
        await _assert_customer_allows_new_provider_mutation(self._session, customer_account_id)

        gift_record = ApiIdempotencyRecordModel(
            scope=self._GIFT_SCOPE,
            idempotency_key=gift_key,
            resource_type="remnawave_gift_redemption",
            resource_id=gift_code_id,
            request_hash=request_hash,
            response_payload={},
            status="pending",
            expires_at=None,
        )
        customer_record = ApiIdempotencyRecordModel(
            scope=normalized_customer_scope,
            idempotency_key=normalized_customer_key,
            resource_type=self._customer_resource_type,
            resource_id=customer_account_id,
            request_hash=request_hash,
            response_payload={},
            status="pending",
            expires_at=None,
        )
        self._session.add_all([gift_record, customer_record])
        try:
            await self._session.commit()
        except IntegrityError:
            await self._session.rollback()
            return self._decision_for_existing_pair(
                gift_record=await self._get(self._GIFT_SCOPE, gift_key),
                customer_record=await self._get(normalized_customer_scope, normalized_customer_key),
                request_hash=request_hash,
            )
        return RemnawaveGiftProvisioningAttemptDecision(
            gift_record=gift_record,
            customer_record=customer_record,
            should_mutate=True,
        )

    async def mark_reconciliation_required(
        self,
        decision: RemnawaveGiftProvisioningAttemptDecision,
    ) -> None:
        for record in (decision.gift_record, decision.customer_record):
            record.status = "reconciliation_required"
            record.response_payload = {}
        await self._session.commit()

    async def mark_completed(
        self,
        decision: RemnawaveGiftProvisioningAttemptDecision,
        *,
        user_ref: RemnawaveUserRef,
    ) -> None:
        numeric_id = user_ref.require_numeric_id()
        response_payload: dict[str, int | str] = {"numeric_user_id": numeric_id}
        if user_ref.legacy_uuid is not None:
            response_payload["legacy_uuid"] = str(user_ref.legacy_uuid)
        for record in (decision.gift_record, decision.customer_record):
            record.status = "completed"
            record.response_payload = dict(response_payload)
        await self._session.flush()

    async def _get(self, scope: str, idempotency_key: str) -> ApiIdempotencyRecordModel | None:
        result = await self._session.execute(
            select(ApiIdempotencyRecordModel).where(
                ApiIdempotencyRecordModel.scope == scope,
                ApiIdempotencyRecordModel.idempotency_key == idempotency_key,
            )
        )
        return result.scalars().one_or_none()

    @staticmethod
    def _decision_for_existing_pair(
        *,
        gift_record: ApiIdempotencyRecordModel | None,
        customer_record: ApiIdempotencyRecordModel | None,
        request_hash: str,
    ) -> RemnawaveGiftProvisioningAttemptDecision:
        if gift_record is None or customer_record is None:
            raise RemnawaveCreateAttemptConflict(
                "Remnawave gift provisioning reservation is incomplete and requires reconciliation"
            )
        gift_decision = RemnawaveMutationAttemptService._decision_for_existing(
            gift_record,
            request_hash=request_hash,
        )
        customer_decision = RemnawaveMutationAttemptService._decision_for_existing(
            customer_record,
            request_hash=request_hash,
        )
        if gift_decision.should_mutate or customer_decision.should_mutate:
            raise RemnawaveCreateAttemptConflict("Remnawave gift provisioning reservation has inconsistent state")
        return RemnawaveGiftProvisioningAttemptDecision(
            gift_record=gift_record,
            customer_record=customer_record,
            should_mutate=False,
        )
