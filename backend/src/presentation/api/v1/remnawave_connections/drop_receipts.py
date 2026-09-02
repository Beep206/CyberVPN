"""PostgreSQL-backed idempotency receipts for non-reconcilable drops."""

from __future__ import annotations

import hashlib
import hmac
import json
import re
import secrets
import uuid
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from enum import StrEnum
from typing import Any, Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator
from sqlalchemy import delete, func, or_, select, text
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from src.config.settings import settings
from src.infrastructure.database.models.remnawave_upgrade_model import RemnawaveConnectionDropReceiptModel

from .job_registry import RemnawaveConnectionJobAudience

_IDEMPOTENCY_KEY_RE = re.compile(r"^[A-Za-z0-9._:-]{16,128}$")
_HMAC_RE = re.compile(r"^[a-f0-9]{64}$")
_RECEIPT_ID_RE = re.compile(r"^[A-Za-z0-9_-]{43}$")
_KEY_HMAC_CONTEXT = b"cybervpn/remnawave-connections-drop-key/v1\0"
_SCOPE_HMAC_CONTEXT = b"cybervpn/remnawave-connections-drop-scope/v1\0"
_PAYLOAD_HMAC_CONTEXT = b"cybervpn/remnawave-connections-drop-payload/v1\0"
_HMAC_KEY_ID_CONTEXT = b"cybervpn/remnawave-connections-drop-hmac-key-id/v1\0"
_REGISTRY_CAPACITY_LOCK_ID = 7_056_235_614_317_964_303


class RemnawaveConnectionDropState(StrEnum):
    OUTCOME_UNKNOWN = "outcome_unknown"
    ACCEPTED = "accepted"
    REJECTED = "rejected"


class RemnawaveConnectionDropReceiptRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    database_id: UUID
    receipt_id: str = Field(min_length=43, max_length=43, pattern=_RECEIPT_ID_RE.pattern)
    hmac_key_id: str = Field(min_length=64, max_length=64, pattern=_HMAC_RE.pattern)
    audience: RemnawaveConnectionJobAudience
    actor_id: UUID
    workspace_id: UUID | None = None
    scope_hmac: str = Field(min_length=64, max_length=64, pattern=_HMAC_RE.pattern)
    payload_hmac: str = Field(min_length=64, max_length=64, pattern=_HMAC_RE.pattern)
    state: RemnawaveConnectionDropState
    created_at: datetime
    updated_at: datetime
    expires_at: datetime | None
    reconciled_at: datetime | None = None
    reconciled_by_admin_id: UUID | None = None
    reconciliation_reason: str | None = Field(default=None, max_length=48)
    reconciliation_reference: str | None = Field(default=None, max_length=64)

    @model_validator(mode="after")
    def validate_lifecycle(self) -> Self:
        for timestamp in (self.created_at, self.updated_at, self.expires_at, self.reconciled_at):
            if timestamp is not None and (timestamp.tzinfo is None or timestamp.utcoffset() is None):
                raise ValueError("Connection drop receipt timestamps must include timezone")
        reconciliation_values = (
            self.reconciled_at,
            self.reconciled_by_admin_id,
            self.reconciliation_reason,
            self.reconciliation_reference,
        )
        has_reconciliation = all(value is not None for value in reconciliation_values)
        if any(value is not None for value in reconciliation_values) and not has_reconciliation:
            raise ValueError("Connection drop receipt reconciliation metadata must be complete")
        if self.state is RemnawaveConnectionDropState.OUTCOME_UNKNOWN:
            if self.expires_at is not None or has_reconciliation:
                raise ValueError("Ambiguous connection drop receipts must not expire automatically")
        elif self.expires_at is None:
            raise ValueError("Terminal connection drop receipts require an expiry")
        elif has_reconciliation:
            reconciled_at = self.reconciled_at
            if reconciled_at is None or reconciled_at != self.updated_at or self.expires_at <= reconciled_at:
                raise ValueError("Reconciled connection drop receipt lifecycle is inconsistent")
        return self


@dataclass(frozen=True, slots=True)
class RemnawaveConnectionDropReservation:
    record: RemnawaveConnectionDropReceiptRecord
    is_new: bool


class RemnawaveConnectionDropReceiptConflictError(RuntimeError):
    """An idempotency key was reused with a different effective payload."""


class RemnawaveConnectionDropReceiptUnavailableError(RuntimeError):
    """A receipt cannot be durably reserved or updated."""


class RemnawaveConnectionDropReceiptCapacityError(RemnawaveConnectionDropReceiptUnavailableError):
    """The bounded registry cannot safely accept another ambiguous mutation."""


class RemnawaveConnectionDropReceiptRegistry:
    """Commit an ambiguous receipt before the single allowed provider call.

    Unknown outcomes are durable fail-safe tombstones until an explicit
    reconciliation moves them to a terminal state. Accepted/rejected rows have
    a bounded TTL and can be deleted only after it elapses. A database-wide
    advisory transaction lock makes cleanup, key-stability checks, capacity
    admission, and reservation one serializable decision across API workers.
    """

    ttl_seconds = 86_400
    max_active_receipts = 250_000
    max_active_per_actor = 1_000
    max_pending_per_actor = 32
    cleanup_batch_size = 100

    def __init__(
        self,
        db: AsyncSession,
        *,
        hmac_secret: bytes,
        terminal_ttl_seconds: int = ttl_seconds,
        max_active_receipts: int = max_active_receipts,
        max_active_per_actor: int = max_active_per_actor,
        max_pending_per_actor: int = max_pending_per_actor,
        cleanup_batch_size: int = cleanup_batch_size,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        if len(hmac_secret) < 32:
            raise RemnawaveConnectionDropReceiptUnavailableError("Connection drop idempotency HMAC is not configured")
        if terminal_ttl_seconds <= 0:
            raise ValueError("terminal_ttl_seconds must be positive")
        if max_active_receipts <= 0:
            raise ValueError("max_active_receipts must be positive")
        if max_active_per_actor <= 0:
            raise ValueError("max_active_per_actor must be positive")
        if max_pending_per_actor <= 0:
            raise ValueError("max_pending_per_actor must be positive")
        if cleanup_batch_size <= 0:
            raise ValueError("cleanup_batch_size must be positive")
        self._db = db
        self._hmac_secret = hmac_secret
        self._hmac_key_id = self.hmac_key_id(hmac_secret)
        self._terminal_ttl_seconds = terminal_ttl_seconds
        self._max_active_receipts = max_active_receipts
        self._max_active_per_actor = max_active_per_actor
        self._max_pending_per_actor = max_pending_per_actor
        self._cleanup_batch_size = cleanup_batch_size
        self._clock = clock or (lambda: datetime.now(UTC))

    async def reserve(
        self,
        *,
        audience: RemnawaveConnectionJobAudience,
        actor_id: UUID,
        workspace_id: UUID | None,
        scope: str,
        client_idempotency_key: str,
        payload: Mapping[str, Any],
    ) -> RemnawaveConnectionDropReservation:
        if _IDEMPOTENCY_KEY_RE.fullmatch(client_idempotency_key) is None:
            raise ValueError("Invalid connection drop idempotency key")
        if (audience is RemnawaveConnectionJobAudience.PARTNER) != (workspace_id is not None):
            raise ValueError("Connection drop workspace scope does not match audience")

        scope_hmac = self._hmac(_SCOPE_HMAC_CONTEXT, scope.encode("utf-8"))
        payload_hmac = self.payload_hmac(self._hmac_secret, payload)
        key_material = self._canonical_json(
            {
                "actorId": str(actor_id),
                "audience": audience.value,
                "clientKey": client_idempotency_key,
                "scope": scope,
                "workspaceId": str(workspace_id) if workspace_id is not None else None,
            }
        )
        key_hmac = self._hmac(_KEY_HMAC_CONTEXT, key_material)
        now = self._now()
        await self._acquire_registry_lock()
        await self._purge_expired_terminal(now)

        existing = await self._load_by_key_hmac(key_hmac)
        if existing is not None:
            try:
                record = self._validated_existing(
                    existing,
                    audience=audience,
                    actor_id=actor_id,
                    workspace_id=workspace_id,
                    scope_hmac=scope_hmac,
                    payload_hmac=payload_hmac,
                )
            except (
                RemnawaveConnectionDropReceiptConflictError,
                RemnawaveConnectionDropReceiptUnavailableError,
            ):
                await self._rollback()
                raise
            if self._is_expired_terminal(record, now):
                await self._delete_expired_terminal(record, now)
            else:
                await self._commit_or_unavailable("Connection drop receipt replay could not be finalized")
                return RemnawaveConnectionDropReservation(record=record, is_new=False)

        await self._validate_stable_hmac_key(now)
        await self._validate_capacity(
            audience=audience,
            actor_id=actor_id,
            now=now,
        )
        candidate = RemnawaveConnectionDropReceiptModel(
            id=uuid.uuid4(),
            key_hmac=key_hmac,
            hmac_key_id=self._hmac_key_id,
            receipt_id=secrets.token_urlsafe(32),
            audience=audience.value,
            actor_id=actor_id,
            workspace_id=workspace_id,
            scope_hmac=scope_hmac,
            payload_hmac=payload_hmac,
            # A crash after this commit can only replay an ambiguous receipt;
            # it can never make another provider send look safe.
            state=RemnawaveConnectionDropState.OUTCOME_UNKNOWN.value,
            created_at=now,
            updated_at=now,
            expires_at=None,
        )
        self._db.add(candidate)
        try:
            await self._db.commit()
        except IntegrityError:
            await self._rollback()
        except SQLAlchemyError as exc:
            await self._rollback()
            raise RemnawaveConnectionDropReceiptUnavailableError(
                "Connection drop receipt could not be durably reserved"
            ) from exc
        else:
            return RemnawaveConnectionDropReservation(record=self._record(candidate), is_new=True)

        existing = await self._load_by_key_hmac(key_hmac)
        if existing is None:
            # A receipt-id collision or inconsistent unique index is not safe
            # to reinterpret as a fresh command.
            raise RemnawaveConnectionDropReceiptUnavailableError(
                "Connection drop receipt conflict could not be reconciled"
            )
        try:
            record = self._validated_existing(
                existing,
                audience=audience,
                actor_id=actor_id,
                workspace_id=workspace_id,
                scope_hmac=scope_hmac,
                payload_hmac=payload_hmac,
            )
        except (
            RemnawaveConnectionDropReceiptConflictError,
            RemnawaveConnectionDropReceiptUnavailableError,
        ):
            await self._rollback()
            raise
        if self._is_expired_terminal(record, self._now()):
            raise RemnawaveConnectionDropReceiptUnavailableError("Connection drop receipt raced with terminal expiry")
        await self._commit_or_unavailable("Connection drop receipt conflict could not be finalized")
        return RemnawaveConnectionDropReservation(record=record, is_new=False)

    async def update_state(
        self,
        reservation: RemnawaveConnectionDropReservation,
        state: RemnawaveConnectionDropState,
    ) -> RemnawaveConnectionDropReceiptRecord:
        if state is RemnawaveConnectionDropState.OUTCOME_UNKNOWN:
            raise ValueError("Connection drop receipt cannot transition back to outcome_unknown")
        try:
            result = await self._db.execute(
                select(RemnawaveConnectionDropReceiptModel)
                .where(RemnawaveConnectionDropReceiptModel.id == reservation.record.database_id)
                .with_for_update()
            )
            model = result.scalar_one_or_none()
            if model is None:
                raise RemnawaveConnectionDropReceiptUnavailableError(
                    "Connection drop receipt disappeared before outcome update"
                )
            existing = self._record(model)
            self._validate_same_receipt(existing, reservation.record)
            if existing.state is RemnawaveConnectionDropState.OUTCOME_UNKNOWN:
                model.state = state.value
                now = self._now()
                model.updated_at = now
                model.expires_at = now + timedelta(seconds=self._terminal_ttl_seconds)
            await self._db.commit()
        except RemnawaveConnectionDropReceiptUnavailableError:
            await self._rollback()
            raise
        except SQLAlchemyError as exc:
            await self._rollback()
            raise RemnawaveConnectionDropReceiptUnavailableError(
                "Connection drop receipt outcome could not be persisted"
            ) from exc
        return self._record(model)

    async def _acquire_registry_lock(self) -> None:
        try:
            await self._db.execute(
                text("SELECT pg_advisory_xact_lock(:lock_id)"),
                {"lock_id": _REGISTRY_CAPACITY_LOCK_ID},
            )
        except SQLAlchemyError as exc:
            await self._rollback()
            raise RemnawaveConnectionDropReceiptUnavailableError(
                "Connection drop receipt capacity lock is unavailable"
            ) from exc

    async def _purge_expired_terminal(self, now: datetime) -> None:
        expired_ids = (
            select(RemnawaveConnectionDropReceiptModel.id)
            .where(
                RemnawaveConnectionDropReceiptModel.state.in_(
                    (
                        RemnawaveConnectionDropState.ACCEPTED.value,
                        RemnawaveConnectionDropState.REJECTED.value,
                    )
                ),
                RemnawaveConnectionDropReceiptModel.expires_at <= now,
            )
            .order_by(
                RemnawaveConnectionDropReceiptModel.expires_at,
                RemnawaveConnectionDropReceiptModel.id,
            )
            .limit(self._cleanup_batch_size)
        )
        try:
            await self._db.execute(
                delete(RemnawaveConnectionDropReceiptModel).where(
                    RemnawaveConnectionDropReceiptModel.id.in_(expired_ids)
                )
            )
        except SQLAlchemyError as exc:
            await self._rollback()
            raise RemnawaveConnectionDropReceiptUnavailableError(
                "Expired connection drop receipts could not be purged"
            ) from exc

    async def _delete_expired_terminal(
        self,
        record: RemnawaveConnectionDropReceiptRecord,
        now: datetime,
    ) -> None:
        try:
            result = await self._db.execute(
                delete(RemnawaveConnectionDropReceiptModel)
                .where(
                    RemnawaveConnectionDropReceiptModel.id == record.database_id,
                    RemnawaveConnectionDropReceiptModel.receipt_id == record.receipt_id,
                    RemnawaveConnectionDropReceiptModel.hmac_key_id == self._hmac_key_id,
                    RemnawaveConnectionDropReceiptModel.state.in_(
                        (
                            RemnawaveConnectionDropState.ACCEPTED.value,
                            RemnawaveConnectionDropState.REJECTED.value,
                        )
                    ),
                    RemnawaveConnectionDropReceiptModel.expires_at <= now,
                )
                .returning(RemnawaveConnectionDropReceiptModel.id)
            )
        except SQLAlchemyError as exc:
            await self._rollback()
            raise RemnawaveConnectionDropReceiptUnavailableError(
                "Expired connection drop receipt could not be released"
            ) from exc
        if result.scalar_one_or_none() != record.database_id:
            await self._rollback()
            raise RemnawaveConnectionDropReceiptUnavailableError(
                "Expired connection drop receipt changed during release"
            )

    async def _validate_stable_hmac_key(self, now: datetime) -> None:
        active = or_(
            RemnawaveConnectionDropReceiptModel.state == RemnawaveConnectionDropState.OUTCOME_UNKNOWN.value,
            RemnawaveConnectionDropReceiptModel.expires_at > now,
        )
        try:
            result = await self._db.execute(
                select(RemnawaveConnectionDropReceiptModel.id)
                .where(
                    RemnawaveConnectionDropReceiptModel.hmac_key_id != self._hmac_key_id,
                    active,
                )
                .limit(1)
            )
        except SQLAlchemyError as exc:
            await self._rollback()
            raise RemnawaveConnectionDropReceiptUnavailableError(
                "Connection drop HMAC key stability could not be verified"
            ) from exc
        if result.scalar_one_or_none() is not None:
            await self._rollback()
            raise RemnawaveConnectionDropReceiptUnavailableError(
                "Connection drop HMAC key changed while active receipts exist"
            )

    async def _validate_capacity(
        self,
        *,
        audience: RemnawaveConnectionJobAudience,
        actor_id: UUID,
        now: datetime,
    ) -> None:
        active = or_(
            RemnawaveConnectionDropReceiptModel.state == RemnawaveConnectionDropState.OUTCOME_UNKNOWN.value,
            RemnawaveConnectionDropReceiptModel.expires_at > now,
        )
        pending_for_actor = (
            (RemnawaveConnectionDropReceiptModel.state == RemnawaveConnectionDropState.OUTCOME_UNKNOWN.value)
            & (RemnawaveConnectionDropReceiptModel.audience == audience.value)
            & (RemnawaveConnectionDropReceiptModel.actor_id == actor_id)
        )
        active_for_actor = (
            active
            & (RemnawaveConnectionDropReceiptModel.audience == audience.value)
            & (RemnawaveConnectionDropReceiptModel.actor_id == actor_id)
        )
        try:
            result = await self._db.execute(
                select(
                    func.count(RemnawaveConnectionDropReceiptModel.id).filter(active),
                    func.count(RemnawaveConnectionDropReceiptModel.id).filter(active_for_actor),
                    func.count(RemnawaveConnectionDropReceiptModel.id).filter(pending_for_actor),
                )
            )
            active_count, actor_active_count, pending_count = result.one()
        except SQLAlchemyError as exc:
            await self._rollback()
            raise RemnawaveConnectionDropReceiptUnavailableError(
                "Connection drop receipt capacity could not be verified"
            ) from exc
        if int(active_count) >= self._max_active_receipts:
            await self._rollback()
            raise RemnawaveConnectionDropReceiptCapacityError(
                "Connection drop receipt registry reached its active capacity"
            )
        if int(actor_active_count) >= self._max_active_per_actor:
            await self._rollback()
            raise RemnawaveConnectionDropReceiptCapacityError(
                "Connection drop actor reached its active receipt capacity"
            )
        if int(pending_count) >= self._max_pending_per_actor:
            await self._rollback()
            raise RemnawaveConnectionDropReceiptCapacityError(
                "Connection drop actor requires reconciliation before another mutation"
            )

    def _validated_existing(
        self,
        model: RemnawaveConnectionDropReceiptModel,
        *,
        audience: RemnawaveConnectionJobAudience,
        actor_id: UUID,
        workspace_id: UUID | None,
        scope_hmac: str,
        payload_hmac: str,
    ) -> RemnawaveConnectionDropReceiptRecord:
        record = self._record(model)
        if record.hmac_key_id != self._hmac_key_id:
            raise RemnawaveConnectionDropReceiptUnavailableError(
                "Connection drop HMAC key changed while a receipt remains active"
            )
        if (
            record.audience is not audience
            or record.actor_id != actor_id
            or record.workspace_id != workspace_id
            or record.scope_hmac != scope_hmac
        ):
            raise RemnawaveConnectionDropReceiptUnavailableError("Connection drop receipt identity mismatch")
        if record.payload_hmac != payload_hmac:
            raise RemnawaveConnectionDropReceiptConflictError(
                "Connection drop idempotency key was reused with a different payload"
            )
        return record

    @staticmethod
    def _is_expired_terminal(
        record: RemnawaveConnectionDropReceiptRecord,
        now: datetime,
    ) -> bool:
        return (
            record.state is not RemnawaveConnectionDropState.OUTCOME_UNKNOWN
            and record.expires_at is not None
            and record.expires_at <= now
        )

    async def _commit_or_unavailable(self, message: str) -> None:
        try:
            await self._db.commit()
        except SQLAlchemyError as exc:
            await self._rollback()
            raise RemnawaveConnectionDropReceiptUnavailableError(message) from exc

    async def _load_by_key_hmac(self, key_hmac: str) -> RemnawaveConnectionDropReceiptModel | None:
        try:
            result = await self._db.execute(
                select(RemnawaveConnectionDropReceiptModel).where(
                    RemnawaveConnectionDropReceiptModel.key_hmac == key_hmac
                )
            )
            return result.scalar_one_or_none()
        except SQLAlchemyError as exc:
            await self._rollback()
            raise RemnawaveConnectionDropReceiptUnavailableError(
                "Connection drop receipt state could not be read"
            ) from exc

    async def _rollback(self) -> None:
        try:
            await self._db.rollback()
        except SQLAlchemyError as exc:
            raise RemnawaveConnectionDropReceiptUnavailableError(
                "Connection drop receipt transaction could not be rolled back"
            ) from exc

    @staticmethod
    def _record(model: RemnawaveConnectionDropReceiptModel) -> RemnawaveConnectionDropReceiptRecord:
        return connection_drop_receipt_record(model)

    @staticmethod
    def _validate_same_receipt(
        current: RemnawaveConnectionDropReceiptRecord,
        expected: RemnawaveConnectionDropReceiptRecord,
    ) -> None:
        if (
            current.database_id != expected.database_id
            or current.receipt_id != expected.receipt_id
            or current.hmac_key_id != expected.hmac_key_id
            or current.audience is not expected.audience
            or current.actor_id != expected.actor_id
            or current.workspace_id != expected.workspace_id
            or current.scope_hmac != expected.scope_hmac
            or current.payload_hmac != expected.payload_hmac
        ):
            raise RemnawaveConnectionDropReceiptUnavailableError("Connection drop receipt identity mismatch")

    @classmethod
    def payload_hmac(cls, hmac_secret: bytes, payload: Mapping[str, Any]) -> str:
        if len(hmac_secret) < 32:
            raise RemnawaveConnectionDropReceiptUnavailableError("Connection drop idempotency HMAC is not configured")
        return hmac.new(
            hmac_secret,
            _PAYLOAD_HMAC_CONTEXT + cls._canonical_json(payload),
            hashlib.sha256,
        ).hexdigest()

    @staticmethod
    def hmac_key_id(hmac_secret: bytes) -> str:
        if len(hmac_secret) < 32:
            raise RemnawaveConnectionDropReceiptUnavailableError("Connection drop idempotency HMAC is not configured")
        return hmac.new(hmac_secret, _HMAC_KEY_ID_CONTEXT, hashlib.sha256).hexdigest()

    def _now(self) -> datetime:
        now = self._clock()
        if now.tzinfo is None:
            raise RemnawaveConnectionDropReceiptUnavailableError("Connection drop receipt clock must include timezone")
        return now.astimezone(UTC)

    def _hmac(self, context: bytes, value: bytes) -> str:
        return hmac.new(self._hmac_secret, context + value, hashlib.sha256).hexdigest()

    @staticmethod
    def _canonical_json(value: Mapping[str, Any]) -> bytes:
        return json.dumps(
            value,
            ensure_ascii=True,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")


def configured_connection_drop_hmac_secret() -> bytes:
    secret = settings.remnawave_connection_drop_hmac_secret.get_secret_value().strip()
    if len(secret) < 32:
        raise RemnawaveConnectionDropReceiptUnavailableError("Connection drop idempotency HMAC is not configured")
    return secret.encode("utf-8")


def connection_drop_receipt_record(
    model: RemnawaveConnectionDropReceiptModel,
) -> RemnawaveConnectionDropReceiptRecord:
    """Validate a persisted receipt without exposing its secret lookup material."""

    try:
        return RemnawaveConnectionDropReceiptRecord(
            database_id=model.id,
            receipt_id=model.receipt_id,
            hmac_key_id=model.hmac_key_id,
            audience=RemnawaveConnectionJobAudience(model.audience),
            actor_id=model.actor_id,
            workspace_id=model.workspace_id,
            scope_hmac=model.scope_hmac,
            payload_hmac=model.payload_hmac,
            state=RemnawaveConnectionDropState(model.state),
            created_at=model.created_at,
            updated_at=model.updated_at,
            expires_at=model.expires_at,
            reconciled_at=model.reconciled_at,
            reconciled_by_admin_id=model.reconciled_by_admin_id,
            reconciliation_reason=model.reconciliation_reason,
            reconciliation_reference=model.reconciliation_reference,
        )
    except (TypeError, ValueError) as exc:
        raise RemnawaveConnectionDropReceiptUnavailableError("Connection drop receipt is invalid") from exc
