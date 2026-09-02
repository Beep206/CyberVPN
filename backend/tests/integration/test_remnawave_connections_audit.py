import secrets
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.requests import Request

from src.infrastructure.database.models.admin_user_model import AdminUserModel
from src.infrastructure.database.models.audit_log_model import AuditLog
from src.infrastructure.remnawave.connections_gateway import RemnawaveConnectionDropCommand
from src.presentation.api.v1.remnawave_connections.audit import (
    RemnawaveConnectionDropAuditContext,
    persist_privileged_connection_drop_audit,
)
from src.presentation.api.v1.remnawave_connections.drop_receipts import (
    RemnawaveConnectionDropReceiptRecord,
    RemnawaveConnectionDropState,
)
from src.presentation.api.v1.remnawave_connections.job_registry import RemnawaveConnectionJobAudience


def _request() -> Request:
    return Request(
        {
            "type": "http",
            "method": "POST",
            "scheme": "https",
            "path": "/api/v1/admin/remnawave/connections/drop",
            "headers": [(b"user-agent", b"pytest-integration")],
            "client": ("203.0.113.10", 443),
            "server": ("admin.cyber-vpn.net", 443),
        }
    )


@pytest.mark.integration
async def test_connection_drop_audit_persists_once_across_replay(db: AsyncSession) -> None:
    actor = AdminUserModel(
        id=uuid4(),
        login=f"connections-audit-{secrets.token_hex(8)}",
        role="admin",
        is_active=True,
    )
    db.add(actor)
    await db.commit()
    receipt_id = secrets.token_urlsafe(32)
    now = datetime.now(UTC)
    receipt = RemnawaveConnectionDropReceiptRecord(
        database_id=uuid4(),
        receipt_id=receipt_id,
        hmac_key_id="c" * 64,
        audience=RemnawaveConnectionJobAudience.ADMIN,
        actor_id=actor.id,
        scope_hmac="a" * 64,
        payload_hmac="b" * 64,
        state=RemnawaveConnectionDropState.ACCEPTED,
        created_at=now,
        updated_at=now,
        expires_at=now + timedelta(days=1),
    )
    command = RemnawaveConnectionDropCommand.model_validate(
        {
            "dropBy": {"by": "userIds", "userIds": [42, 77]},
            "targetNodes": {"target": "allNodes"},
        }
    )
    context = RemnawaveConnectionDropAuditContext(db=db, request=_request(), actor=actor)

    try:
        await persist_privileged_connection_drop_audit(
            context=context,
            audience=RemnawaveConnectionJobAudience.ADMIN,
            command=command,
            payload_hmac=receipt.payload_hmac,
            receipt=receipt,
        )
        await persist_privileged_connection_drop_audit(
            context=context,
            audience=RemnawaveConnectionJobAudience.ADMIN,
            command=command,
            payload_hmac=receipt.payload_hmac,
            receipt=receipt,
        )

        rows = (
            (
                await db.execute(
                    select(AuditLog).where(
                        AuditLog.entity_type == "remnawave_connection_drop",
                        AuditLog.entity_id == receipt_id,
                    )
                )
            )
            .scalars()
            .all()
        )
        count = await db.scalar(select(func.count()).select_from(AuditLog).where(AuditLog.entity_id == receipt_id))

        assert count == 1
        assert len(rows) == 1
        assert rows[0].admin_id == actor.id
        assert rows[0].action == "remnawave.connections.drop.accepted"
        assert rows[0].new_value is not None
        assert rows[0].new_value["audience"] == "admin"
        assert rows[0].new_value["scope"] == "global"
        assert rows[0].new_value["user_ids"] == [42, 77]
        assert rows[0].new_value["payload_hmac"] == receipt.payload_hmac
        assert rows[0].new_value["receipt_id"] == receipt_id
    finally:
        await db.execute(delete(AuditLog).where(AuditLog.entity_id == receipt_id))
        await db.execute(delete(AdminUserModel).where(AdminUserModel.id == actor.id))
        await db.commit()
