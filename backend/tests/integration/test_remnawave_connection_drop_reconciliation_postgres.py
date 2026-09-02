from __future__ import annotations

import asyncio
import secrets
from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
import pytest_asyncio
from sqlalchemy import func, select
from sqlalchemy.exc import OperationalError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from starlette.requests import Request

from src.infrastructure.database.models.admin_user_model import AdminUserModel
from src.infrastructure.database.models.audit_log_model import AuditLog
from src.infrastructure.database.models.remnawave_upgrade_model import RemnawaveConnectionDropReceiptModel
from src.presentation.api.v1.remnawave_connections import reconciliation
from src.presentation.api.v1.remnawave_connections.drop_receipts import (
    RemnawaveConnectionDropReceiptRegistry,
    RemnawaveConnectionDropReceiptUnavailableError,
    RemnawaveConnectionDropState,
)
from src.presentation.api.v1.remnawave_connections.job_registry import RemnawaveConnectionJobAudience
from src.presentation.api.v1.remnawave_connections.reconciliation import (
    RemnawaveConnectionDropReconciliationConflictError,
    RemnawaveConnectionDropReconciliationReason,
    RemnawaveConnectionDropReconciliationService,
)
from tests.integration.test_partner_commission_contracts_migration_postgres import (
    _asyncpg_url_for_database,
    _create_database,
    _database_url,
    _drop_database,
    _run_alembic,
)
from tests.integration.test_remnawave_connection_drop_migration_postgres import (
    CURRENT_REVISION,
    _IsolatedPostgresDatabase,
)

pytestmark = [pytest.mark.integration]

_HMAC_SECRET = b"connection-drop-reconciliation-secret-001"
_ROTATED_HMAC_SECRET = b"connection-drop-reconciliation-secret-002"
_PAYLOAD = {
    "dropBy": {"by": "userIds", "userIds": [42]},
    "targetNodes": {"target": "allNodes"},
}


@pytest_asyncio.fixture
async def isolated_postgres_database() -> AsyncIterator[_IsolatedPostgresDatabase]:
    database_name = f"cvpn_drop_reconcile_{secrets.token_hex(6)}"
    await _create_database(database_name)
    try:
        yield _IsolatedPostgresDatabase(
            name=database_name,
            sqlalchemy_url=_database_url(database_name),
            asyncpg_url=_asyncpg_url_for_database(database_name),
        )
    finally:
        await _drop_database(database_name)


def _request(receipt_id: str, *, client_ip: str) -> Request:
    return Request(
        {
            "type": "http",
            "method": "POST",
            "scheme": "https",
            "path": f"/api/v1/admin/remnawave/connections/drop-receipts/{receipt_id}/reconcile",
            "headers": [(b"user-agent", b"pytest-postgres")],
            "client": (client_ip, 443),
            "server": ("admin.cyber-vpn.net", 443),
        }
    )


async def _create_admin_and_unknown(
    sessions: async_sessionmaker[AsyncSession],
    *,
    client_key: str,
) -> tuple[AdminUserModel, str]:
    actor = AdminUserModel(
        id=uuid4(),
        login=f"receipt-reconcile-{secrets.token_hex(8)}",
        role="admin",
        is_active=True,
        totp_enabled=True,
    )
    async with sessions() as db:
        db.add(actor)
        await db.commit()
        reservation = await RemnawaveConnectionDropReceiptRegistry(
            db,
            hmac_secret=_HMAC_SECRET,
        ).reserve(
            audience=RemnawaveConnectionJobAudience.ADMIN,
            actor_id=actor.id,
            workspace_id=None,
            scope="admin:global",
            client_idempotency_key=client_key,
            payload=_PAYLOAD,
        )
    return actor, reservation.record.receipt_id


@pytest.mark.asyncio
async def test_concurrent_reconciliation_is_one_audit_idempotent_or_one_winner_conflict(
    isolated_postgres_database: _IsolatedPostgresDatabase,
) -> None:
    database = isolated_postgres_database
    await asyncio.to_thread(_run_alembic, database.sqlalchemy_url, "upgrade", CURRENT_REVISION)
    engine = create_async_engine(database.sqlalchemy_url, pool_pre_ping=True)
    sessions = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    try:
        actor, same_receipt_id = await _create_admin_and_unknown(
            sessions,
            client_key="reconcile-same-key-0001",  # gitleaks:allow -- deterministic idempotency fixture
        )

        async def same_decision(client_ip: str):
            async with sessions() as db:
                return await RemnawaveConnectionDropReconciliationService(
                    db,
                    terminal_ttl_seconds=86_400,
                ).reconcile(
                    receipt_id=same_receipt_id,
                    outcome=RemnawaveConnectionDropState.ACCEPTED,
                    reason=RemnawaveConnectionDropReconciliationReason.PROVIDER_CONFIRMED_APPLIED,
                    reference="CASE-SAME01",
                    actor=actor,
                    request=_request(same_receipt_id, client_ip=client_ip),
                )

        same_results = await asyncio.gather(same_decision("203.0.113.10"), same_decision("203.0.113.11"))
        assert {result.state for result in same_results} == {RemnawaveConnectionDropState.ACCEPTED}
        assert {result.reconciled_at for result in same_results} == {same_results[0].reconciled_at}
        assert {result.reconciled_by_admin_id for result in same_results} == {actor.id}

        async with sessions() as db:
            assert (
                await db.scalar(
                    select(func.count())
                    .select_from(AuditLog)
                    .where(
                        AuditLog.action == "remnawave.connections.drop.reconciled",
                        AuditLog.entity_id == same_receipt_id,
                    )
                )
                == 1
            )

        _, conflicting_receipt_id = await _create_admin_and_unknown(
            sessions,
            client_key="reconcile-conflict-key-0001",
        )

        async def conflicting_decision(
            outcome: RemnawaveConnectionDropState,
            reason: RemnawaveConnectionDropReconciliationReason,
            reference: str,
        ):
            async with sessions() as db:
                return await RemnawaveConnectionDropReconciliationService(
                    db,
                    terminal_ttl_seconds=86_400,
                ).reconcile(
                    receipt_id=conflicting_receipt_id,
                    outcome=outcome,
                    reason=reason,
                    reference=reference,
                    actor=actor,
                    request=_request(conflicting_receipt_id, client_ip="203.0.113.12"),
                )

        conflict_results = await asyncio.gather(
            conflicting_decision(
                RemnawaveConnectionDropState.ACCEPTED,
                RemnawaveConnectionDropReconciliationReason.PROVIDER_CONFIRMED_APPLIED,
                "CASE-WINNER1",
            ),
            conflicting_decision(
                RemnawaveConnectionDropState.REJECTED,
                RemnawaveConnectionDropReconciliationReason.PROVIDER_CONFIRMED_NOT_APPLIED,
                "CASE-WINNER2",
            ),
            return_exceptions=True,
        )
        winners = [item for item in conflict_results if not isinstance(item, BaseException)]
        conflicts = [
            item for item in conflict_results if isinstance(item, RemnawaveConnectionDropReconciliationConflictError)
        ]
        assert len(winners) == 1
        assert len(conflicts) == 1
        async with sessions() as db:
            assert (
                await db.scalar(
                    select(func.count())
                    .select_from(AuditLog)
                    .where(
                        AuditLog.action == "remnawave.connections.drop.reconciled",
                        AuditLog.entity_id == conflicting_receipt_id,
                    )
                )
                == 1
            )
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_audit_failure_rolls_back_unknown_and_retry_repairs_atomically(
    isolated_postgres_database: _IsolatedPostgresDatabase,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    database = isolated_postgres_database
    await asyncio.to_thread(_run_alembic, database.sqlalchemy_url, "upgrade", CURRENT_REVISION)
    engine = create_async_engine(database.sqlalchemy_url, pool_pre_ping=True)
    sessions = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    original_audit_writer = reconciliation.write_required_admin_audit_entry
    try:
        actor, receipt_id = await _create_admin_and_unknown(
            sessions,
            client_key="reconcile-audit-repair-key-0001",
        )
        monkeypatch.setattr(
            reconciliation,
            "write_required_admin_audit_entry",
            AsyncMock(side_effect=OperationalError("audit insert", {}, RuntimeError("audit unavailable"))),
        )
        async with sessions() as db:
            with pytest.raises(reconciliation.RemnawaveConnectionDropReconciliationUnavailableError):
                await RemnawaveConnectionDropReconciliationService(
                    db,
                    terminal_ttl_seconds=86_400,
                ).reconcile(
                    receipt_id=receipt_id,
                    outcome=RemnawaveConnectionDropState.ACCEPTED,
                    reason=RemnawaveConnectionDropReconciliationReason.PROVIDER_CONFIRMED_APPLIED,
                    reference="TKT-REPAIR1",
                    actor=actor,
                    request=_request(receipt_id, client_ip="203.0.113.20"),
                )

        async with sessions() as db:
            persisted = await db.scalar(
                select(RemnawaveConnectionDropReceiptModel).where(
                    RemnawaveConnectionDropReceiptModel.receipt_id == receipt_id
                )
            )
            assert persisted is not None
            assert persisted.state == RemnawaveConnectionDropState.OUTCOME_UNKNOWN.value
            assert persisted.expires_at is None
            assert persisted.reconciled_at is None
            audit_count = await db.scalar(
                select(func.count()).select_from(AuditLog).where(AuditLog.entity_id == receipt_id)
            )
            assert audit_count == 0

        monkeypatch.setattr(reconciliation, "write_required_admin_audit_entry", original_audit_writer)
        async with sessions() as db:
            repaired = await RemnawaveConnectionDropReconciliationService(
                db,
                terminal_ttl_seconds=86_400,
            ).reconcile(
                receipt_id=receipt_id,
                outcome=RemnawaveConnectionDropState.ACCEPTED,
                reason=RemnawaveConnectionDropReconciliationReason.PROVIDER_CONFIRMED_APPLIED,
                reference="TKT-REPAIR1",
                actor=actor,
                request=_request(receipt_id, client_ip="203.0.113.20"),
            )
        assert repaired.state is RemnawaveConnectionDropState.ACCEPTED
        async with sessions() as db:
            audit_count = await db.scalar(
                select(func.count()).select_from(AuditLog).where(AuditLog.entity_id == receipt_id)
            )
            assert audit_count == 1
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_reconciliation_ttl_controls_rotation_release_without_deleting_unknown(
    isolated_postgres_database: _IsolatedPostgresDatabase,
) -> None:
    database = isolated_postgres_database
    await asyncio.to_thread(_run_alembic, database.sqlalchemy_url, "upgrade", CURRENT_REVISION)
    engine = create_async_engine(database.sqlalchemy_url, pool_pre_ping=True)
    sessions = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    started_at = datetime.now(UTC)
    try:
        actor, receipt_id = await _create_admin_and_unknown(
            sessions,
            client_key="reconcile-rotation-source-0001",
        )
        async with sessions() as db:
            reconciled = await RemnawaveConnectionDropReconciliationService(
                db,
                terminal_ttl_seconds=60,
                clock=lambda: started_at,
            ).reconcile(
                receipt_id=receipt_id,
                outcome=RemnawaveConnectionDropState.REJECTED,
                reason=RemnawaveConnectionDropReconciliationReason.PROVIDER_CONFIRMED_NOT_APPLIED,
                reference="REQ-ROTATE1",
                actor=actor,
                request=_request(receipt_id, client_ip="203.0.113.30"),
            )
        assert reconciled.expires_at == started_at + timedelta(seconds=60)

        async with sessions() as db:
            with pytest.raises(RemnawaveConnectionDropReceiptUnavailableError, match="HMAC key changed"):
                await RemnawaveConnectionDropReceiptRegistry(
                    db,
                    hmac_secret=_ROTATED_HMAC_SECRET,
                    clock=lambda: started_at + timedelta(seconds=59),
                ).reserve(
                    audience=RemnawaveConnectionJobAudience.ADMIN,
                    actor_id=uuid4(),
                    workspace_id=None,
                    scope="admin:global",
                    client_idempotency_key="rotation-blocked-key-0001",
                    payload=_PAYLOAD,
                )

        async with sessions() as db:
            replacement = await RemnawaveConnectionDropReceiptRegistry(
                db,
                hmac_secret=_ROTATED_HMAC_SECRET,
                clock=lambda: started_at + timedelta(seconds=61),
            ).reserve(
                audience=RemnawaveConnectionJobAudience.ADMIN,
                actor_id=uuid4(),
                workspace_id=None,
                scope="admin:global",
                client_idempotency_key="rotation-released-key-0001",
                payload=_PAYLOAD,
            )
        assert replacement.is_new is True
        assert replacement.record.state is RemnawaveConnectionDropState.OUTCOME_UNKNOWN
        assert replacement.record.expires_at is None
        async with sessions() as db:
            assert (
                await db.scalar(
                    select(func.count())
                    .select_from(RemnawaveConnectionDropReceiptModel)
                    .where(RemnawaveConnectionDropReceiptModel.receipt_id == receipt_id)
                )
                == 0
            )
            assert (
                await db.scalar(
                    select(func.count())
                    .select_from(RemnawaveConnectionDropReceiptModel)
                    .where(
                        RemnawaveConnectionDropReceiptModel.state == RemnawaveConnectionDropState.OUTCOME_UNKNOWN.value
                    )
                )
                == 1
            )
    finally:
        await engine.dispose()
