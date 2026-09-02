from __future__ import annotations

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from sqlalchemy.exc import OperationalError
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.requests import Request

from src.infrastructure.database.models.admin_user_model import AdminUserModel
from src.infrastructure.database.models.audit_log_model import AuditLog
from src.infrastructure.database.models.remnawave_upgrade_model import RemnawaveConnectionDropReceiptModel
from src.presentation.api.v1.admin.audit import build_admin_audit_details
from src.presentation.api.v1.remnawave_connections import reconciliation
from src.presentation.api.v1.remnawave_connections.drop_receipts import (
    RemnawaveConnectionDropReceiptRegistry,
    RemnawaveConnectionDropState,
)
from src.presentation.api.v1.remnawave_connections.job_registry import RemnawaveConnectionJobAudience
from src.presentation.api.v1.remnawave_connections.reconciliation import (
    RemnawaveConnectionDropReconciliationConflictError,
    RemnawaveConnectionDropReconciliationReason,
    RemnawaveConnectionDropReconciliationService,
    RemnawaveConnectionDropReconciliationUnavailableError,
)

_NOW = datetime(2026, 8, 31, 12, 0, tzinfo=UTC)
_RECEIPT_ID = "r" * 43
_HMAC_SECRET = b"connections-drop-domain-secret-00000001"


def _db() -> MagicMock:
    db = MagicMock(spec=AsyncSession)
    db.execute = AsyncMock()
    db.flush = AsyncMock()
    db.commit = AsyncMock()
    db.rollback = AsyncMock()
    return db


def _scalar_result(value: object) -> MagicMock:
    result = MagicMock()
    result.scalar_one_or_none.return_value = value
    return result


def _request() -> Request:
    return Request(
        {
            "type": "http",
            "method": "POST",
            "scheme": "https",
            "path": f"/api/v1/admin/remnawave/connections/drop-receipts/{_RECEIPT_ID}/reconcile",
            "headers": [(b"user-agent", b"pytest")],
            "client": ("203.0.113.10", 443),
            "server": ("admin.cyber-vpn.net", 443),
        }
    )


def _admin() -> AdminUserModel:
    return AdminUserModel(id=uuid4(), login=f"receipt-admin-{uuid4()}", role="admin", is_active=True)


def _model(
    *,
    state: RemnawaveConnectionDropState = RemnawaveConnectionDropState.OUTCOME_UNKNOWN,
    actor_id=None,
    reconciled_by_admin_id=None,
    reason: RemnawaveConnectionDropReconciliationReason | None = None,
    reference: str | None = None,
) -> RemnawaveConnectionDropReceiptModel:
    reconciled_at = _NOW if reason is not None else None
    return RemnawaveConnectionDropReceiptModel(
        id=uuid4(),
        key_hmac="a" * 64,
        hmac_key_id=RemnawaveConnectionDropReceiptRegistry.hmac_key_id(_HMAC_SECRET),
        receipt_id=_RECEIPT_ID,
        audience=RemnawaveConnectionJobAudience.ADMIN.value,
        actor_id=actor_id or uuid4(),
        workspace_id=None,
        scope_hmac="b" * 64,
        payload_hmac="c" * 64,
        state=state.value,
        created_at=_NOW - timedelta(hours=1),
        updated_at=reconciled_at or (_NOW - timedelta(hours=1)),
        expires_at=_NOW + timedelta(days=1) if state is not RemnawaveConnectionDropState.OUTCOME_UNKNOWN else None,
        reconciled_at=reconciled_at,
        reconciled_by_admin_id=reconciled_by_admin_id,
        reconciliation_reason=reason.value if reason is not None else None,
        reconciliation_reference=reference,
    )


@pytest.mark.unit
async def test_admin_reconciliation_transitions_unknown_and_starts_server_ttl_with_atomic_audit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    db = _db()
    model = _model()
    db.execute.return_value = _scalar_result(model)
    audit_write = AsyncMock()
    monkeypatch.setattr(reconciliation, "write_required_admin_audit_entry", audit_write)
    actor = _admin()
    service = RemnawaveConnectionDropReconciliationService(
        db,
        terminal_ttl_seconds=3_600,
        clock=lambda: _NOW,
    )

    record = await service.reconcile(
        receipt_id=_RECEIPT_ID,
        outcome=RemnawaveConnectionDropState.ACCEPTED,
        reason=RemnawaveConnectionDropReconciliationReason.PROVIDER_CONFIRMED_APPLIED,
        reference="CASE-ABC123",
        actor=actor,
        request=_request(),
    )

    assert record.state is RemnawaveConnectionDropState.ACCEPTED
    assert record.reconciled_at == record.updated_at == _NOW
    assert record.expires_at == _NOW + timedelta(hours=1)
    assert record.reconciled_by_admin_id == actor.id
    assert record.reconciliation_reason == "provider_confirmed_applied"
    assert record.reconciliation_reference == "CASE-ABC123"
    db.flush.assert_awaited_once_with()
    db.commit.assert_awaited_once_with()
    audit_write.assert_awaited_once()
    audit_call = audit_write.await_args.kwargs
    assert audit_call["action"] == "remnawave.connections.drop.reconciled"
    assert audit_call["resource_id"] == _RECEIPT_ID
    assert set(audit_call["details"]) == {
        "receipt_id",
        "outcome",
        "reason",
        "reference",
        "reconciled_at",
        "expires_at",
    }
    serialized_audit = repr(audit_call["details"])
    assert "key_hmac" not in serialized_audit
    assert "scope_hmac" not in serialized_audit
    assert "payload_hmac" not in serialized_audit
    assert "203.0.113.10" not in serialized_audit


@pytest.mark.unit
async def test_same_reconciliation_replay_is_idempotent_and_does_not_append_a_second_audit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    actor = _admin()
    reason = RemnawaveConnectionDropReconciliationReason.POSTCONDITION_CONFIRMED_NOT_APPLIED
    model = _model(
        state=RemnawaveConnectionDropState.REJECTED,
        reconciled_by_admin_id=actor.id,
        reason=reason,
        reference="INC-ABC123",
    )
    db = _db()
    service = RemnawaveConnectionDropReconciliationService(db, terminal_ttl_seconds=86_400)
    record = reconciliation.connection_drop_receipt_record(model)
    audit = AuditLog(
        id=service._audit_id(_RECEIPT_ID),  # noqa: SLF001 - deterministic audit invariant
        admin_id=actor.id,
        action="remnawave.connections.drop.reconciled",
        entity_type="remnawave_connection_drop_receipt",
        entity_id=_RECEIPT_ID,
        old_value={"state": "outcome_unknown"},
        new_value=build_admin_audit_details(service._audit_details(record)),  # noqa: SLF001
    )
    db.execute.side_effect = [_scalar_result(model), _scalar_result(audit)]
    audit_write = AsyncMock()
    monkeypatch.setattr(reconciliation, "write_required_admin_audit_entry", audit_write)

    replay = await service.reconcile(
        receipt_id=_RECEIPT_ID,
        outcome=RemnawaveConnectionDropState.REJECTED,
        reason=reason,
        reference="INC-ABC123",
        actor=_admin(),
        request=_request(),
    )

    assert replay.reconciled_by_admin_id == actor.id
    audit_write.assert_not_awaited()
    db.commit.assert_awaited_once_with()


@pytest.mark.unit
@pytest.mark.parametrize(
    ("outcome", "reason", "reference"),
    [
        (
            RemnawaveConnectionDropState.ACCEPTED,
            RemnawaveConnectionDropReconciliationReason.PROVIDER_CONFIRMED_APPLIED,
            "CASE-DIFFERENT",
        ),
        (
            RemnawaveConnectionDropState.REJECTED,
            RemnawaveConnectionDropReconciliationReason.PROVIDER_CONFIRMED_NOT_APPLIED,
            "CASE-ABC123",
        ),
    ],
)
async def test_terminal_reconciliation_is_immutable_and_conflicts_are_409_domain_errors(
    outcome: RemnawaveConnectionDropState,
    reason: RemnawaveConnectionDropReconciliationReason,
    reference: str,
) -> None:
    actor = _admin()
    model = _model(
        state=RemnawaveConnectionDropState.ACCEPTED,
        reconciled_by_admin_id=actor.id,
        reason=RemnawaveConnectionDropReconciliationReason.PROVIDER_CONFIRMED_APPLIED,
        reference="CASE-ABC123",
    )
    db = _db()
    db.execute.return_value = _scalar_result(model)
    service = RemnawaveConnectionDropReconciliationService(db, terminal_ttl_seconds=86_400)

    with pytest.raises(RemnawaveConnectionDropReconciliationConflictError, match="immutable"):
        await service.reconcile(
            receipt_id=_RECEIPT_ID,
            outcome=outcome,
            reason=reason,
            reference=reference,
            actor=actor,
            request=_request(),
        )

    db.rollback.assert_awaited_once_with()
    db.commit.assert_not_awaited()


@pytest.mark.unit
async def test_audit_failure_rolls_back_transition_and_retry_can_repair(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    actor = _admin()
    db = _db()
    first_model = _model()
    db.execute.return_value = _scalar_result(first_model)
    audit_error = OperationalError("insert audit", {}, RuntimeError("audit unavailable"))
    monkeypatch.setattr(reconciliation, "write_required_admin_audit_entry", AsyncMock(side_effect=audit_error))
    service = RemnawaveConnectionDropReconciliationService(db, terminal_ttl_seconds=86_400, clock=lambda: _NOW)

    with pytest.raises(RemnawaveConnectionDropReconciliationUnavailableError):
        await service.reconcile(
            receipt_id=_RECEIPT_ID,
            outcome=RemnawaveConnectionDropState.ACCEPTED,
            reason=RemnawaveConnectionDropReconciliationReason.PROVIDER_CONFIRMED_APPLIED,
            reference="TKT-ABC123",
            actor=actor,
            request=_request(),
        )

    db.rollback.assert_awaited_once_with()
    db.commit.assert_not_awaited()

    retry_db = _db()
    retry_db.execute.return_value = _scalar_result(_model())
    successful_audit = AsyncMock()
    monkeypatch.setattr(reconciliation, "write_required_admin_audit_entry", successful_audit)
    retry = await RemnawaveConnectionDropReconciliationService(
        retry_db,
        terminal_ttl_seconds=86_400,
        clock=lambda: _NOW,
    ).reconcile(
        receipt_id=_RECEIPT_ID,
        outcome=RemnawaveConnectionDropState.ACCEPTED,
        reason=RemnawaveConnectionDropReconciliationReason.PROVIDER_CONFIRMED_APPLIED,
        reference="TKT-ABC123",
        actor=actor,
        request=_request(),
    )
    assert retry.state is RemnawaveConnectionDropState.ACCEPTED
    successful_audit.assert_awaited_once()
    retry_db.commit.assert_awaited_once_with()


@pytest.mark.unit
@pytest.mark.parametrize(
    ("receipt_id", "reference"),
    [("short", "CASE-ABC123"), (_RECEIPT_ID, "free text from provider")],
)
async def test_reconciliation_rejects_non_opaque_identifiers_before_database_access(
    receipt_id: str,
    reference: str,
) -> None:
    db = _db()
    service = RemnawaveConnectionDropReconciliationService(db, terminal_ttl_seconds=86_400)

    with pytest.raises(ValueError):
        await service.reconcile(
            receipt_id=receipt_id,
            outcome=RemnawaveConnectionDropState.ACCEPTED,
            reason=RemnawaveConnectionDropReconciliationReason.PROVIDER_CONFIRMED_APPLIED,
            reference=reference,
            actor=_admin(),
            request=_request(),
        )

    db.execute.assert_not_awaited()
