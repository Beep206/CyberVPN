import hashlib
import json
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from fastapi import HTTPException
from pydantic import SecretStr
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.requests import Request

from src.config.settings import settings
from src.infrastructure.database.models.admin_user_model import AdminUserModel
from src.infrastructure.database.models.audit_log_model import AuditLog
from src.infrastructure.remnawave.connections_gateway import RemnawaveConnectionDropCommand
from src.presentation.api.v1.admin.audit import STAGE1_REQUIRED_ADMIN_AUDIT_ACTIONS
from src.presentation.api.v1.remnawave_connections import routes
from src.presentation.api.v1.remnawave_connections.audit import (
    RemnawaveConnectionDropAuditContext,
    RemnawaveConnectionDropAuditUnavailableError,
    build_privileged_connection_drop_audit_details,
    persist_privileged_connection_drop_audit,
)
from src.presentation.api.v1.remnawave_connections.drop_receipts import (
    RemnawaveConnectionDropReceiptRecord,
    RemnawaveConnectionDropReceiptRegistry,
    RemnawaveConnectionDropReceiptUnavailableError,
    RemnawaveConnectionDropReservation,
    RemnawaveConnectionDropState,
)
from src.presentation.api.v1.remnawave_connections.job_registry import RemnawaveConnectionJobAudience

_RECEIPT_ID = "r" * 43
_IDEMPOTENCY_KEY = "audit-drop-key-0001"
_PAYLOAD_HMAC = "a" * 64


def _request() -> Request:
    return Request(
        {
            "type": "http",
            "method": "POST",
            "scheme": "https",
            "path": "/api/v1/admin/remnawave/connections/drop",
            "headers": [(b"user-agent", b"pytest-audit")],
            "client": ("203.0.113.10", 443),
            "server": ("admin.cyber-vpn.net", 443),
        }
    )


def _actor() -> AdminUserModel:
    return AdminUserModel(id=uuid4(), login="connections-auditor", role="admin")


def _receipt(
    *,
    actor: AdminUserModel,
    audience: RemnawaveConnectionJobAudience,
    state: RemnawaveConnectionDropState,
) -> RemnawaveConnectionDropReceiptRecord:
    now = datetime.now(UTC)
    return RemnawaveConnectionDropReceiptRecord(
        database_id=uuid4(),
        receipt_id=_RECEIPT_ID,
        hmac_key_id="c" * 64,
        audience=audience,
        actor_id=actor.id,
        scope_hmac="b" * 64,
        payload_hmac=_PAYLOAD_HMAC,
        state=state,
        created_at=now,
        updated_at=now,
        expires_at=None if state is RemnawaveConnectionDropState.OUTCOME_UNKNOWN else now + timedelta(days=1),
    )


def _ip_drop_command(*, node_uuid) -> RemnawaveConnectionDropCommand:
    return RemnawaveConnectionDropCommand.model_validate(
        {
            "dropBy": {"by": "ipAddresses", "ipAddresses": ["203.0.113.77", "2001:db8::77"]},
            "targetNodes": {"target": "specificNodes", "nodeUuids": [str(node_uuid)]},
        }
    )


@pytest.mark.unit
async def test_privileged_drop_audit_is_committed_append_only_and_redacts_target_ips(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        settings,
        "remnawave_stream_ip_hmac_secret",
        SecretStr("connections-audit-ip-domain-secret-0001"),
    )
    actor = _actor()
    workspace_id = uuid4()
    node_uuid = uuid4()
    db = AsyncMock(spec=AsyncSession)
    db.get.return_value = None
    receipt = _receipt(
        actor=actor,
        audience=RemnawaveConnectionJobAudience.PARTNER,
        state=RemnawaveConnectionDropState.ACCEPTED,
    )

    await persist_privileged_connection_drop_audit(
        context=RemnawaveConnectionDropAuditContext(
            db=db,
            request=_request(),
            actor=actor,
            workspace_id=workspace_id,
        ),
        audience=RemnawaveConnectionJobAudience.PARTNER,
        command=_ip_drop_command(node_uuid=node_uuid),
        payload_hmac=_PAYLOAD_HMAC,
        receipt=receipt,
    )

    db.commit.assert_awaited_once_with()
    db.flush.assert_awaited_once_with()
    audit_entry = db.add.call_args.args[0]
    assert isinstance(audit_entry, AuditLog)
    assert audit_entry.admin_id == actor.id
    assert audit_entry.action == "remnawave.connections.drop.accepted"
    assert audit_entry.entity_type == "remnawave_connection_drop"
    assert audit_entry.entity_id == _RECEIPT_ID
    assert audit_entry.new_value is not None
    assert audit_entry.new_value["audience"] == "partner"
    assert audit_entry.new_value["scope"] == "workspace"
    assert audit_entry.new_value["workspace_id"] == str(workspace_id)
    assert audit_entry.new_value["node_uuids"] == [str(node_uuid)]
    assert audit_entry.new_value["payload_hmac"] == _PAYLOAD_HMAC
    assert audit_entry.new_value["receipt_id"] == _RECEIPT_ID
    assert audit_entry.new_value["outcome"] == "accepted"
    assert audit_entry.new_value["drop_by"] == "ip_hmacs"
    ip_hmacs = audit_entry.new_value["ip_hmacs"]
    assert isinstance(ip_hmacs, list)
    assert len(ip_hmacs) == 2
    assert all(isinstance(value, str) and len(value) == 64 for value in ip_hmacs)
    serialized = str(audit_entry.new_value)
    assert "203.0.113.77" not in serialized
    assert "2001:db8::77" not in serialized
    assert _IDEMPOTENCY_KEY not in serialized


@pytest.mark.unit
def test_admin_drop_audit_preserves_exact_numeric_targets_and_global_scope() -> None:
    actor = _actor()
    receipt = _receipt(
        actor=actor,
        audience=RemnawaveConnectionJobAudience.ADMIN,
        state=RemnawaveConnectionDropState.ACCEPTED,
    )

    details = build_privileged_connection_drop_audit_details(
        audience=RemnawaveConnectionJobAudience.ADMIN,
        workspace_id=None,
        command=RemnawaveConnectionDropCommand.model_validate(
            {
                "dropBy": {"by": "userIds", "userIds": [42, 77]},
                "targetNodes": {"target": "allNodes"},
            }
        ),
        payload_hmac=_PAYLOAD_HMAC,
        receipt=receipt,
    )

    assert details["audience"] == "admin"
    assert details["scope"] == "global"
    assert details["drop_by"] == "user_ids"
    assert details["user_ids"] == [42, 77]
    assert details["target_nodes"] == "all_nodes"


@pytest.mark.unit
async def test_missing_ip_hmac_secret_fails_before_receipt_or_provider_io(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "remnawave_stream_ip_hmac_secret", SecretStr(""))
    actor = _actor()
    gateway = AsyncMock()
    receipts = AsyncMock()

    with pytest.raises(HTTPException) as unavailable:
        await routes._execute_connection_drop(
            audience=RemnawaveConnectionJobAudience.ADMIN,
            actor_id=actor.id,
            scope="admin:global",
            client_idempotency_key=_IDEMPOTENCY_KEY,
            command=_ip_drop_command(node_uuid=uuid4()),
            gateway=gateway,
            receipts=receipts,
            audit_context=RemnawaveConnectionDropAuditContext(
                db=AsyncMock(spec=AsyncSession),
                request=_request(),
                actor=actor,
            ),
        )

    assert unavailable.value.status_code == 503
    receipts.reserve.assert_not_awaited()
    gateway.drop_once.assert_not_awaited()


@pytest.mark.unit
async def test_privileged_drop_audit_replay_reuses_deterministic_event_without_append() -> None:
    actor = _actor()
    receipt = _receipt(
        actor=actor,
        audience=RemnawaveConnectionJobAudience.ADMIN,
        state=RemnawaveConnectionDropState.OUTCOME_UNKNOWN,
    )
    db = AsyncMock(spec=AsyncSession)
    db.get.return_value = None
    context = RemnawaveConnectionDropAuditContext(db=db, request=_request(), actor=actor)
    command = RemnawaveConnectionDropCommand.model_validate(
        {
            "dropBy": {"by": "userIds", "userIds": [42]},
            "targetNodes": {"target": "allNodes"},
        }
    )

    await persist_privileged_connection_drop_audit(
        context=context,
        audience=RemnawaveConnectionJobAudience.ADMIN,
        command=command,
        payload_hmac=_PAYLOAD_HMAC,
        receipt=receipt,
    )
    existing = db.add.call_args.args[0]
    assert existing.action == "remnawave.connections.drop.outcome_unknown"
    db.add.reset_mock()
    db.flush.reset_mock()
    db.commit.reset_mock()
    db.get.return_value = existing

    await persist_privileged_connection_drop_audit(
        context=context,
        audience=RemnawaveConnectionJobAudience.ADMIN,
        command=command,
        payload_hmac=_PAYLOAD_HMAC,
        receipt=receipt,
    )

    db.add.assert_not_called()
    db.flush.assert_not_awaited()
    db.commit.assert_not_awaited()


@pytest.mark.unit
async def test_privileged_drop_audit_db_failure_rolls_back_with_sanitized_error() -> None:
    actor = _actor()
    db = AsyncMock(spec=AsyncSession)
    db.get.return_value = None
    db.commit.side_effect = SQLAlchemyError("database unavailable")

    with pytest.raises(RemnawaveConnectionDropAuditUnavailableError):
        await persist_privileged_connection_drop_audit(
            context=RemnawaveConnectionDropAuditContext(db=db, request=_request(), actor=actor),
            audience=RemnawaveConnectionJobAudience.ADMIN,
            command=RemnawaveConnectionDropCommand.model_validate(
                {
                    "dropBy": {"by": "userIds", "userIds": [42]},
                    "targetNodes": {"target": "allNodes"},
                }
            ),
            payload_hmac=_PAYLOAD_HMAC,
            receipt=_receipt(
                actor=actor,
                audience=RemnawaveConnectionJobAudience.ADMIN,
                state=RemnawaveConnectionDropState.REJECTED,
            ),
        )

    assert db.add.call_args.args[0].action == "remnawave.connections.drop.rejected"
    db.rollback.assert_awaited_once_with()


@pytest.mark.unit
async def test_audit_failure_after_drop_replays_receipt_without_second_provider_call(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    actor = _actor()
    unknown = _receipt(
        actor=actor,
        audience=RemnawaveConnectionJobAudience.ADMIN,
        state=RemnawaveConnectionDropState.OUTCOME_UNKNOWN,
    )
    accepted = unknown.model_copy(
        update={
            "state": RemnawaveConnectionDropState.ACCEPTED,
            "expires_at": unknown.created_at + timedelta(days=1),
        }
    )
    receipts = AsyncMock()
    receipts.reserve.side_effect = [
        RemnawaveConnectionDropReservation(record=unknown, is_new=True),
        RemnawaveConnectionDropReservation(record=accepted, is_new=False),
    ]
    receipts.update_state.return_value = accepted
    gateway = AsyncMock()
    audit_writer = AsyncMock(side_effect=[RemnawaveConnectionDropAuditUnavailableError("audit down"), None])
    monkeypatch.setattr(routes, "persist_privileged_connection_drop_audit", audit_writer)
    command = RemnawaveConnectionDropCommand.model_validate(
        {
            "dropBy": {"by": "userIds", "userIds": [42]},
            "targetNodes": {"target": "allNodes"},
        }
    )
    audit_context = RemnawaveConnectionDropAuditContext(
        db=AsyncMock(spec=AsyncSession),
        request=_request(),
        actor=actor,
    )

    with pytest.raises(HTTPException) as audit_failure:
        await routes._execute_connection_drop(
            audience=RemnawaveConnectionJobAudience.ADMIN,
            actor_id=actor.id,
            scope="admin:global",
            client_idempotency_key=_IDEMPOTENCY_KEY,
            command=command,
            gateway=gateway,
            receipts=receipts,
            audit_context=audit_context,
        )
    replay = await routes._execute_connection_drop(
        audience=RemnawaveConnectionJobAudience.ADMIN,
        actor_id=actor.id,
        scope="admin:global",
        client_idempotency_key=_IDEMPOTENCY_KEY,
        command=command,
        gateway=gateway,
        receipts=receipts,
        audit_context=audit_context,
    )

    assert audit_failure.value.status_code == 503
    assert replay.state == "accepted"
    assert gateway.drop_once.await_count == 1
    assert audit_writer.await_count == 2


@pytest.mark.unit
async def test_provider_4xx_state_write_failure_audits_only_durable_unknown(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    actor = _actor()
    unknown = _receipt(
        actor=actor,
        audience=RemnawaveConnectionJobAudience.ADMIN,
        state=RemnawaveConnectionDropState.OUTCOME_UNKNOWN,
    )
    receipts = AsyncMock()
    receipts.reserve.return_value = RemnawaveConnectionDropReservation(record=unknown, is_new=True)
    receipts.update_state.side_effect = RemnawaveConnectionDropReceiptUnavailableError("db unavailable")
    gateway = AsyncMock()
    gateway.drop_once.side_effect = routes.RemnawaveHTTPStatusError(status_code=400)
    audit_writer = AsyncMock()
    monkeypatch.setattr(routes, "persist_privileged_connection_drop_audit", audit_writer)

    response = await routes._execute_connection_drop(
        audience=RemnawaveConnectionJobAudience.ADMIN,
        actor_id=actor.id,
        scope="admin:global",
        client_idempotency_key=_IDEMPOTENCY_KEY,
        command=RemnawaveConnectionDropCommand.model_validate(
            {
                "dropBy": {"by": "userIds", "userIds": [42]},
                "targetNodes": {"target": "allNodes"},
            }
        ),
        gateway=gateway,
        receipts=receipts,
        audit_context=RemnawaveConnectionDropAuditContext(
            db=AsyncMock(spec=AsyncSession),
            request=_request(),
            actor=actor,
        ),
    )

    assert response.state == "outcome_unknown"
    assert audit_writer.await_args.kwargs["receipt"].state is RemnawaveConnectionDropState.OUTCOME_UNKNOWN


@pytest.mark.unit
def test_connection_drop_outcome_actions_are_required_admin_audits() -> None:
    assert {
        "remnawave.connections.drop.accepted",
        "remnawave.connections.drop.outcome_unknown",
        "remnawave.connections.drop.rejected",
    } <= STAGE1_REQUIRED_ADMIN_AUDIT_ACTIONS


@pytest.mark.unit
def test_ip_payload_identity_is_keyed_and_not_offline_dictionary_sha256() -> None:
    command = _ip_drop_command(node_uuid=uuid4())
    canonical = json.dumps(
        command.canonical_payload(),
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    payload_hmac = RemnawaveConnectionDropReceiptRegistry.payload_hmac(
        b"connections-drop-domain-secret-00000001",
        command.canonical_payload(),
    )

    assert payload_hmac != hashlib.sha256(canonical).hexdigest()
    assert "203.0.113.77" not in payload_hmac
    assert "2001:db8::77" not in payload_hmac
