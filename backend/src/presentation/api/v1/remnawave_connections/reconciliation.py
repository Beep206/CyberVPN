"""Admin reconciliation for ambiguous Remnawave connection-drop receipts."""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from enum import StrEnum
from uuid import UUID, uuid5

from fastapi import Request
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.database.models.admin_user_model import AdminUserModel
from src.infrastructure.database.models.audit_log_model import AuditLog
from src.infrastructure.database.models.remnawave_upgrade_model import RemnawaveConnectionDropReceiptModel
from src.presentation.api.v1.admin.audit import build_admin_audit_details, write_required_admin_audit_entry

from .drop_receipts import (
    RemnawaveConnectionDropReceiptRecord,
    RemnawaveConnectionDropReceiptUnavailableError,
    RemnawaveConnectionDropState,
    connection_drop_receipt_record,
)

RECEIPT_ID_PATTERN = r"^[A-Za-z0-9_-]{43}$"
RECONCILIATION_REFERENCE_PATTERN = r"^(?:CASE|INC|REQ|TKT|RW)-[A-Z0-9][A-Z0-9_-]{5,58}$"
_RECEIPT_ID_RE = re.compile(RECEIPT_ID_PATTERN)
_RECONCILIATION_REFERENCE_RE = re.compile(RECONCILIATION_REFERENCE_PATTERN)
_RECONCILIATION_AUDIT_NAMESPACE = UUID("26aa4fd9-cfd5-4b70-8943-c3f95b9b3e84")
_RECONCILIATION_AUDIT_ACTION = "remnawave.connections.drop.reconciled"
_RECONCILIATION_AUDIT_ENTITY = "remnawave_connection_drop_receipt"


class RemnawaveConnectionDropReconciliationReason(StrEnum):
    PROVIDER_CONFIRMED_APPLIED = "provider_confirmed_applied"
    PROVIDER_CONFIRMED_NOT_APPLIED = "provider_confirmed_not_applied"
    POSTCONDITION_CONFIRMED_APPLIED = "postcondition_confirmed_applied"
    POSTCONDITION_CONFIRMED_NOT_APPLIED = "postcondition_confirmed_not_applied"


_ALLOWED_REASONS: dict[RemnawaveConnectionDropState, frozenset[RemnawaveConnectionDropReconciliationReason]] = {
    RemnawaveConnectionDropState.ACCEPTED: frozenset(
        {
            RemnawaveConnectionDropReconciliationReason.PROVIDER_CONFIRMED_APPLIED,
            RemnawaveConnectionDropReconciliationReason.POSTCONDITION_CONFIRMED_APPLIED,
        }
    ),
    RemnawaveConnectionDropState.REJECTED: frozenset(
        {
            RemnawaveConnectionDropReconciliationReason.PROVIDER_CONFIRMED_NOT_APPLIED,
            RemnawaveConnectionDropReconciliationReason.POSTCONDITION_CONFIRMED_NOT_APPLIED,
        }
    ),
}


class RemnawaveConnectionDropReconciliationNotFoundError(RuntimeError):
    """The opaque receipt identifier does not resolve to a persisted receipt."""


class RemnawaveConnectionDropReconciliationConflictError(RuntimeError):
    """A terminal receipt is immutable or a decision conflicts with it."""


class RemnawaveConnectionDropReconciliationUnavailableError(RuntimeError):
    """The receipt and its required audit event could not be committed atomically."""


@dataclass(frozen=True, slots=True)
class RemnawaveConnectionDropUnresolvedPage:
    items: tuple[RemnawaveConnectionDropReceiptRecord, ...]
    next_cursor: str | None


class RemnawaveConnectionDropReconciliationService:
    """Resolve exact public receipt IDs without requiring idempotency HMAC material."""

    def __init__(
        self,
        db: AsyncSession,
        *,
        terminal_ttl_seconds: int,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        if terminal_ttl_seconds <= 0:
            raise ValueError("terminal_ttl_seconds must be positive")
        self._db = db
        self._terminal_ttl_seconds = terminal_ttl_seconds
        self._clock = clock or (lambda: datetime.now(UTC))

    async def list_unresolved(
        self,
        *,
        limit: int,
        cursor: str | None,
    ) -> RemnawaveConnectionDropUnresolvedPage:
        if limit < 1 or limit > 100:
            raise ValueError("Connection drop reconciliation page limit must be between 1 and 100")
        if cursor is not None:
            self._validate_receipt_id(cursor)
        statement = (
            select(RemnawaveConnectionDropReceiptModel)
            .where(RemnawaveConnectionDropReceiptModel.state == RemnawaveConnectionDropState.OUTCOME_UNKNOWN.value)
            .order_by(RemnawaveConnectionDropReceiptModel.receipt_id)
            .limit(limit + 1)
        )
        if cursor is not None:
            statement = statement.where(RemnawaveConnectionDropReceiptModel.receipt_id > cursor)
        try:
            result = await self._db.execute(statement)
            models = list(result.scalars().all())
            records = tuple(connection_drop_receipt_record(model) for model in models[:limit])
            next_cursor = records[-1].receipt_id if len(models) > limit and records else None
            await self._db.rollback()
        except RemnawaveConnectionDropReceiptUnavailableError as exc:
            await self._rollback_after_error()
            raise RemnawaveConnectionDropReconciliationUnavailableError(
                "Connection drop reconciliation receipts are invalid"
            ) from exc
        except SQLAlchemyError as exc:
            await self._rollback_after_error()
            raise RemnawaveConnectionDropReconciliationUnavailableError(
                "Connection drop reconciliation receipts could not be read"
            ) from exc
        return RemnawaveConnectionDropUnresolvedPage(items=records, next_cursor=next_cursor)

    async def get(self, receipt_id: str) -> RemnawaveConnectionDropReceiptRecord:
        self._validate_receipt_id(receipt_id)
        try:
            result = await self._db.execute(
                select(RemnawaveConnectionDropReceiptModel).where(
                    RemnawaveConnectionDropReceiptModel.receipt_id == receipt_id
                )
            )
            model = result.scalar_one_or_none()
            if model is None:
                await self._db.rollback()
                raise RemnawaveConnectionDropReconciliationNotFoundError("Connection drop receipt not found")
            record = connection_drop_receipt_record(model)
            await self._db.rollback()
            return record
        except RemnawaveConnectionDropReconciliationNotFoundError:
            raise
        except RemnawaveConnectionDropReceiptUnavailableError as exc:
            await self._rollback_after_error()
            raise RemnawaveConnectionDropReconciliationUnavailableError(
                "Connection drop reconciliation receipt is invalid"
            ) from exc
        except SQLAlchemyError as exc:
            await self._rollback_after_error()
            raise RemnawaveConnectionDropReconciliationUnavailableError(
                "Connection drop reconciliation receipt could not be read"
            ) from exc

    async def reconcile(
        self,
        *,
        receipt_id: str,
        outcome: RemnawaveConnectionDropState,
        reason: RemnawaveConnectionDropReconciliationReason,
        reference: str,
        actor: AdminUserModel,
        request: Request,
    ) -> RemnawaveConnectionDropReceiptRecord:
        self._validate_decision(
            receipt_id=receipt_id,
            outcome=outcome,
            reason=reason,
            reference=reference,
        )
        try:
            result = await self._db.execute(
                select(RemnawaveConnectionDropReceiptModel)
                .where(RemnawaveConnectionDropReceiptModel.receipt_id == receipt_id)
                .with_for_update()
            )
            model = result.scalar_one_or_none()
            if model is None:
                raise RemnawaveConnectionDropReconciliationNotFoundError("Connection drop receipt not found")
            current = connection_drop_receipt_record(model)
            if current.state is RemnawaveConnectionDropState.OUTCOME_UNKNOWN:
                now = self._now()
                model.state = outcome.value
                model.updated_at = now
                model.expires_at = now + timedelta(seconds=self._terminal_ttl_seconds)
                model.reconciled_at = now
                model.reconciled_by_admin_id = actor.id
                model.reconciliation_reason = reason.value
                model.reconciliation_reference = reference
                await self._db.flush()
                current = connection_drop_receipt_record(model)
                await write_required_admin_audit_entry(
                    db=self._db,
                    action=_RECONCILIATION_AUDIT_ACTION,
                    resource_type=_RECONCILIATION_AUDIT_ENTITY,
                    resource_id=receipt_id,
                    actor=actor,
                    request=request,
                    old_value={"state": RemnawaveConnectionDropState.OUTCOME_UNKNOWN.value},
                    details=self._audit_details(current),
                    audit_entry_id=self._audit_id(receipt_id),
                )
            else:
                self._validate_idempotent_replay(
                    current=current,
                    outcome=outcome,
                    reason=reason,
                    reference=reference,
                )
                await self._validate_existing_audit(current)
            await self._db.commit()
            return current
        except (
            RemnawaveConnectionDropReconciliationNotFoundError,
            RemnawaveConnectionDropReconciliationConflictError,
        ):
            await self._rollback_after_error()
            raise
        except (RemnawaveConnectionDropReceiptUnavailableError, SQLAlchemyError) as exc:
            await self._rollback_after_error()
            raise RemnawaveConnectionDropReconciliationUnavailableError(
                "Connection drop reconciliation could not be committed"
            ) from exc
        except Exception:
            # Audit is part of the state-transition transaction. Roll back even
            # unexpected audit adapter failures before propagating them.
            await self._rollback_after_error()
            raise

    async def _validate_existing_audit(self, record: RemnawaveConnectionDropReceiptRecord) -> None:
        result = await self._db.execute(select(AuditLog).where(AuditLog.id == self._audit_id(record.receipt_id)))
        audit = result.scalar_one_or_none()
        if audit is None or (
            audit.admin_id != record.reconciled_by_admin_id
            or audit.action != _RECONCILIATION_AUDIT_ACTION
            or audit.entity_type != _RECONCILIATION_AUDIT_ENTITY
            or audit.entity_id != record.receipt_id
            or audit.old_value != {"state": RemnawaveConnectionDropState.OUTCOME_UNKNOWN.value}
            or audit.new_value != build_admin_audit_details(self._audit_details(record))
        ):
            raise RemnawaveConnectionDropReconciliationUnavailableError(
                "Connection drop reconciliation audit is missing or inconsistent"
            )

    @staticmethod
    def _validate_idempotent_replay(
        *,
        current: RemnawaveConnectionDropReceiptRecord,
        outcome: RemnawaveConnectionDropState,
        reason: RemnawaveConnectionDropReconciliationReason,
        reference: str,
    ) -> None:
        if (
            current.state is not outcome
            or current.reconciliation_reason != reason.value
            or current.reconciliation_reference != reference
            or current.reconciled_at is None
            or current.reconciled_by_admin_id is None
        ):
            raise RemnawaveConnectionDropReconciliationConflictError(
                "Connection drop receipt already has an immutable terminal outcome"
            )

    @staticmethod
    def _audit_details(record: RemnawaveConnectionDropReceiptRecord) -> dict[str, str]:
        if record.reconciled_at is None or record.expires_at is None:
            raise RemnawaveConnectionDropReconciliationUnavailableError(
                "Connection drop reconciliation lifecycle is incomplete"
            )
        if record.reconciliation_reason is None or record.reconciliation_reference is None:
            raise RemnawaveConnectionDropReconciliationUnavailableError(
                "Connection drop reconciliation metadata is incomplete"
            )
        return {
            "receipt_id": record.receipt_id,
            "outcome": record.state.value,
            "reason": record.reconciliation_reason,
            "reference": record.reconciliation_reference,
            "reconciled_at": record.reconciled_at.astimezone(UTC).isoformat(),
            "expires_at": record.expires_at.astimezone(UTC).isoformat(),
        }

    @staticmethod
    def _audit_id(receipt_id: str) -> UUID:
        return uuid5(_RECONCILIATION_AUDIT_NAMESPACE, receipt_id)

    @staticmethod
    def _validate_receipt_id(receipt_id: str) -> None:
        if _RECEIPT_ID_RE.fullmatch(receipt_id) is None:
            raise ValueError("Invalid connection drop receipt ID")

    @staticmethod
    def _validate_decision(
        *,
        receipt_id: str,
        outcome: RemnawaveConnectionDropState,
        reason: RemnawaveConnectionDropReconciliationReason,
        reference: str,
    ) -> None:
        RemnawaveConnectionDropReconciliationService._validate_receipt_id(receipt_id)
        allowed = _ALLOWED_REASONS.get(outcome)
        if allowed is None or reason not in allowed:
            raise ValueError("Reconciliation reason does not match the terminal outcome")
        if _RECONCILIATION_REFERENCE_RE.fullmatch(reference) is None:
            raise ValueError("Invalid reconciliation reference")

    def _now(self) -> datetime:
        now = self._clock()
        if now.tzinfo is None or now.utcoffset() is None:
            raise RemnawaveConnectionDropReconciliationUnavailableError(
                "Connection drop reconciliation clock must include timezone"
            )
        return now.astimezone(UTC)

    async def _rollback_after_error(self) -> None:
        try:
            await self._db.rollback()
        except SQLAlchemyError as exc:
            raise RemnawaveConnectionDropReconciliationUnavailableError(
                "Connection drop reconciliation transaction could not be rolled back"
            ) from exc
