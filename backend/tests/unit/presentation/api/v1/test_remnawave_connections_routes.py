from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID, uuid4

import httpx
import pytest
from fastapi import FastAPI, HTTPException
from pydantic import ValidationError
from starlette.requests import Request

from src.application.services.remnawave_identity_access import RemnawaveIdentityAccessConflict
from src.infrastructure.database.models.admin_user_model import AdminUserModel
from src.infrastructure.database.models.partner_model import PartnerAccountModel
from src.infrastructure.remnawave.connections_gateway import (
    RemnawaveConnectionDropCommand,
    RemnawaveConnectionJob,
    RemnawaveDropByUserIds,
    RemnawaveDropOnAllNodes,
    RemnawaveNodeConnectionsJobResult,
    RemnawaveUserConnectionsJobResult,
)
from src.presentation.api.v1.remnawave_connections import job_registry, routes
from src.presentation.api.v1.remnawave_connections.drop_receipts import (
    RemnawaveConnectionDropReceiptConflictError,
    RemnawaveConnectionDropReceiptRecord,
    RemnawaveConnectionDropReceiptUnavailableError,
    RemnawaveConnectionDropReservation,
    RemnawaveConnectionDropState,
)
from src.presentation.api.v1.remnawave_connections.job_registry import (
    RemnawaveConnectionJobAudience,
    RemnawaveConnectionJobKind,
    RemnawaveConnectionJobRecord,
    RemnawaveConnectionJobRegistry,
    RemnawaveConnectionJobRegistryUnavailableError,
)
from src.presentation.api.v1.remnawave_connections.schemas import (
    AdminRemnawaveConnectionDropRequest,
    PartnerRemnawaveConnectionDropRequest,
)
from src.presentation.dependencies.auth import get_current_active_web_user, get_current_mobile_user_id
from src.presentation.dependencies.database import get_db
from src.presentation.dependencies.partner_workspace import PartnerWorkspaceAccess

_REQUEST_ID = "a" * 43
_IDEMPOTENCY_KEY = "drop-test-key-0001"


def _partner_access(workspace_id: UUID) -> PartnerWorkspaceAccess:
    return PartnerWorkspaceAccess(
        workspace=PartnerAccountModel(id=workspace_id),
        membership=None,
        role=None,
        permission_keys=frozenset(),
        is_internal_admin_override=False,
    )


def _admin_user(user_id: UUID) -> AdminUserModel:
    return AdminUserModel(id=user_id, login=f"test-{user_id}", role="admin")


def _request() -> Request:
    return Request(
        {
            "type": "http",
            "method": "POST",
            "scheme": "https",
            "path": "/api/v1/admin/remnawave/connections/drop",
            "headers": [(b"user-agent", b"pytest")],
            "client": ("203.0.113.10", 443),
            "server": ("admin.cyber-vpn.net", 443),
        }
    )


def _drop_record(
    *,
    audience: RemnawaveConnectionJobAudience,
    actor_id: UUID,
    state: RemnawaveConnectionDropState = RemnawaveConnectionDropState.OUTCOME_UNKNOWN,
) -> RemnawaveConnectionDropReceiptRecord:
    now = datetime.now(UTC)
    return RemnawaveConnectionDropReceiptRecord(
        database_id=uuid4(),
        receipt_id="r" * 43,
        hmac_key_id="c" * 64,
        audience=audience,
        actor_id=actor_id,
        scope_hmac="a" * 64,
        payload_hmac="b" * 64,
        state=state,
        created_at=now,
        updated_at=now,
        expires_at=None if state is RemnawaveConnectionDropState.OUTCOME_UNKNOWN else now + timedelta(days=1),
    )


def _drop_reservation(
    *,
    audience: RemnawaveConnectionJobAudience,
    actor_id: UUID,
    is_new: bool = True,
    state: RemnawaveConnectionDropState = RemnawaveConnectionDropState.OUTCOME_UNKNOWN,
) -> RemnawaveConnectionDropReservation:
    return RemnawaveConnectionDropReservation(
        record=_drop_record(audience=audience, actor_id=actor_id, state=state),
        is_new=is_new,
    )


@pytest.mark.unit
def test_unknown_drop_receipt_public_contract_has_no_false_expiry() -> None:
    record = _drop_record(
        audience=RemnawaveConnectionJobAudience.CUSTOMER,
        actor_id=uuid4(),
        state=RemnawaveConnectionDropState.OUTCOME_UNKNOWN,
    )

    response = routes._drop_receipt_response(record)

    assert response.state == "outcome_unknown"
    assert response.requires_reconciliation is True
    assert response.expires_at is None
    assert response.expires_in_seconds is None
    assert response.retry_allowed is False


@pytest.mark.unit
def test_terminal_drop_receipt_remaining_ttl_clamps_elapsed_clock_skew_to_zero() -> None:
    now = datetime.now(UTC)
    record = _drop_record(
        audience=RemnawaveConnectionJobAudience.ADMIN,
        actor_id=uuid4(),
        state=RemnawaveConnectionDropState.ACCEPTED,
    ).model_copy(update={"expires_at": now - timedelta(seconds=1)})

    response = routes._drop_receipt_response(record)

    assert response.state == "accepted"
    assert response.requires_reconciliation is False
    assert response.expires_at == record.expires_at
    assert response.expires_in_seconds == 0
    assert response.retry_allowed is False


def _user_job_result(*, user_id: int = 42) -> RemnawaveUserConnectionsJobResult:
    return RemnawaveUserConnectionsJobResult.model_validate(
        {
            "isCompleted": True,
            "isFailed": False,
            "progress": {"total": 2, "completed": 2, "percent": 100},
            "result": {
                "success": True,
                "userId": user_id,
                "nodes": [
                    {
                        "nodeUuid": str(uuid4()),
                        "nodeName": "private topology name",
                        "countryCode": "RU",
                        "ips": [{"ip": "203.0.113.8", "lastSeen": "2026-08-31T07:00:00Z"}],
                    }
                ],
            },
        }
    )


def _node_job_result(*, node_uuid) -> RemnawaveNodeConnectionsJobResult:
    return RemnawaveNodeConnectionsJobResult.model_validate(
        {
            "isCompleted": True,
            "isFailed": False,
            "result": {
                "success": True,
                "nodeUuid": str(node_uuid),
                "users": [
                    {
                        "userId": 42,
                        "ips": [{"ip": "203.0.113.8", "lastSeen": "2026-08-31T07:00:00Z"}],
                    },
                    {"userId": 43, "ips": []},
                ],
            },
        }
    )


@pytest.mark.unit
@pytest.mark.parametrize(
    "unsafe_body",
    [
        {"dropBy": {"by": "userIds", "userIds": [42]}},
        {"dropBy": {"by": "ipAddresses", "ipAddresses": ["203.0.113.77"]}},
        {"serviceIdentityUuid": str(uuid4()), "ipAddresses": ["203.0.113.77"]},
    ],
)
def test_partner_drop_contract_rejects_numeric_and_ip_targets(unsafe_body: dict[str, object]) -> None:
    with pytest.raises(ValidationError):
        PartnerRemnawaveConnectionDropRequest.model_validate(unsafe_body)


@pytest.mark.unit
async def test_connection_job_registry_issues_opaque_ttl_binding(monkeypatch: pytest.MonkeyPatch) -> None:
    redis_client = AsyncMock()
    redis_client.set.return_value = True
    monkeypatch.setattr(job_registry.secrets, "token_urlsafe", lambda _size: _REQUEST_ID)
    registry = RemnawaveConnectionJobRegistry(redis_client)
    actor_id = uuid4()
    record = RemnawaveConnectionJobRecord(
        audience=RemnawaveConnectionJobAudience.CUSTOMER,
        kind=RemnawaveConnectionJobKind.USER,
        actor_id=actor_id,
        user_id=42,
        upstream_job_id="provider-job-1",
    )

    request_id = await registry.issue(record)

    assert request_id == _REQUEST_ID
    call = redis_client.set.await_args
    assert call.args[0] == f"remnawave:connections:job:v1:{_REQUEST_ID}"
    assert "203.0.113" not in call.args[1]
    assert call.kwargs == {"ex": 300, "nx": True}

    redis_client.get.return_value = call.args[1]
    loaded = await registry.load(request_id)
    assert loaded == record


@pytest.mark.unit
async def test_connection_job_registry_corruption_fails_closed_and_is_removed() -> None:
    redis_client = AsyncMock()
    redis_client.get.return_value = b'{"audience":"customer"}'
    registry = RemnawaveConnectionJobRegistry(redis_client)

    with pytest.raises(RemnawaveConnectionJobRegistryUnavailableError):
        await registry.load(_REQUEST_ID)

    redis_client.delete.assert_awaited_once_with(f"remnawave:connections:job:v1:{_REQUEST_ID}")


@pytest.mark.unit
async def test_connection_request_binding_hides_cross_customer_idor_as_not_found() -> None:
    owning_customer_id = uuid4()
    attacking_customer_id = uuid4()
    registry = AsyncMock()
    registry.load.return_value = RemnawaveConnectionJobRecord(
        audience=RemnawaveConnectionJobAudience.CUSTOMER,
        kind=RemnawaveConnectionJobKind.USER,
        actor_id=owning_customer_id,
        user_id=42,
        upstream_job_id="provider-job-1",
    )

    with pytest.raises(HTTPException) as denied:
        await routes._load_scoped_job(
            registry=registry,
            request_id=_REQUEST_ID,
            audience=RemnawaveConnectionJobAudience.CUSTOMER,
            kind=RemnawaveConnectionJobKind.USER,
            actor_id=attacking_customer_id,
            user_id=42,
        )

    assert denied.value.status_code == 404
    assert denied.value.detail == "Connection request not found"


@pytest.mark.unit
async def test_customer_request_uses_only_authenticated_canonical_numeric_identity(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    customer_id = uuid4()
    db = AsyncMock()
    customer = SimpleNamespace(
        id=customer_id,
        remnawave_user_id=42,
        remnawave_uuid=str(uuid4()),
        is_active=True,
        status="active",
    )
    db.get.return_value = customer
    exact_mapping = AsyncMock(return_value=SimpleNamespace(require_numeric_id=lambda: 42))
    monkeypatch.setattr(routes, "resolve_exact_mapped_mobile_user_ref", exact_mapping)
    gateway = AsyncMock()
    gateway.request_by_user.return_value = RemnawaveConnectionJob(jobId="provider-job-1")
    registry = AsyncMock()
    registry.issue.return_value = _REQUEST_ID

    response = await routes.request_customer_connections(
        customer_account_id=customer_id,
        db=db,
        gateway=gateway,
        registry=registry,
    )

    gateway.request_by_user.assert_awaited_once_with(42)
    record = registry.issue.await_args.args[0]
    assert record.actor_id == customer_id
    assert record.user_id == 42
    assert record.audience is RemnawaveConnectionJobAudience.CUSTOMER
    assert response.request_id == _REQUEST_ID


@pytest.mark.unit
async def test_customer_result_is_own_status_without_topology_or_ip_payload(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    customer_id = uuid4()
    db = AsyncMock()
    db.get.return_value = SimpleNamespace(
        id=customer_id,
        remnawave_user_id=42,
        remnawave_uuid=str(uuid4()),
        is_active=True,
        status="active",
    )
    monkeypatch.setattr(
        routes,
        "resolve_exact_mapped_mobile_user_ref",
        AsyncMock(return_value=SimpleNamespace(require_numeric_id=lambda: 42)),
    )
    registry = AsyncMock()
    registry.load.return_value = RemnawaveConnectionJobRecord(
        audience=RemnawaveConnectionJobAudience.CUSTOMER,
        kind=RemnawaveConnectionJobKind.USER,
        actor_id=customer_id,
        user_id=42,
        upstream_job_id="provider-job-1",
    )
    gateway = AsyncMock()
    gateway.get_by_user_result.return_value = _user_job_result()

    response = await routes.get_customer_connections(
        request_id=_REQUEST_ID,
        customer_account_id=customer_id,
        db=db,
        gateway=gateway,
        registry=registry,
    )

    assert response.connected is True
    assert response.connected_node_count == 1
    assert response.active_ip_count == 1
    serialized = response.model_dump_json()
    assert "private topology name" not in serialized
    assert "203.0.113.8" not in serialized
    assert "node_uuid" not in serialized
    assert "country_code" not in serialized


@pytest.mark.unit
async def test_partner_node_result_requires_exact_grant_and_returns_only_aggregate(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    workspace_id = uuid4()
    node_uuid = uuid4()
    partner_id = uuid4()
    access = _partner_access(workspace_id)
    grant_check = AsyncMock()
    monkeypatch.setattr(routes, "enforce_partner_remnawave_resource_grant", grant_check)
    registry = AsyncMock()
    registry.load.return_value = RemnawaveConnectionJobRecord(
        audience=RemnawaveConnectionJobAudience.PARTNER,
        kind=RemnawaveConnectionJobKind.NODE,
        actor_id=partner_id,
        workspace_id=workspace_id,
        node_uuid=node_uuid,
        upstream_job_id="provider-job-1",
    )
    gateway = AsyncMock()
    gateway.get_by_node_result.return_value = _node_job_result(node_uuid=node_uuid)

    response = await routes.get_partner_node_connections(
        workspace_id=workspace_id,
        node_uuid=node_uuid,
        request_id=_REQUEST_ID,
        access=access,
        current_user=_admin_user(partner_id),
        db=AsyncMock(),
        gateway=gateway,
        registry=registry,
    )

    grant_call = grant_check.await_args
    assert grant_call is not None
    assert grant_call.kwargs["resource_uuid"] == node_uuid
    assert grant_call.kwargs["permission"].value == "remnawave_read"
    assert response.connected_user_count == 1
    assert response.active_ip_count == 1
    serialized = response.model_dump_json()
    assert "203.0.113.8" not in serialized
    assert '"user_id"' not in serialized


@pytest.mark.unit
async def test_partner_missing_or_revoked_exact_grant_never_reaches_provider(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    workspace_id = uuid4()
    grant_check = AsyncMock(side_effect=HTTPException(status_code=404, detail="Remnawave resource not found"))
    monkeypatch.setattr(routes, "enforce_partner_remnawave_resource_grant", grant_check)
    gateway = AsyncMock()
    registry = AsyncMock()

    with pytest.raises(HTTPException) as denied:
        await routes.request_partner_node_connections(
            workspace_id=workspace_id,
            node_uuid=uuid4(),
            access=_partner_access(workspace_id),
            current_user=_admin_user(uuid4()),
            db=AsyncMock(),
            gateway=gateway,
            registry=registry,
        )

    assert denied.value.status_code == 404
    gateway.request_by_node.assert_not_awaited()
    registry.issue.assert_not_awaited()


@pytest.mark.unit
async def test_partner_resolved_workspace_mismatch_is_404_before_grant_or_provider(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    path_workspace_id = uuid4()
    grant_check = AsyncMock()
    monkeypatch.setattr(routes, "enforce_partner_remnawave_resource_grant", grant_check)
    gateway = AsyncMock()
    registry = AsyncMock()

    with pytest.raises(HTTPException) as denied:
        await routes.request_partner_node_connections(
            workspace_id=path_workspace_id,
            node_uuid=uuid4(),
            access=_partner_access(uuid4()),
            current_user=_admin_user(uuid4()),
            db=AsyncMock(),
            gateway=gateway,
            registry=registry,
        )

    assert denied.value.status_code == 404
    grant_check.assert_not_awaited()
    gateway.request_by_node.assert_not_awaited()


@pytest.mark.unit
async def test_partner_drop_requires_execute_before_receipt_or_provider_io(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    workspace_id = uuid4()
    node_uuid = uuid4()
    current_user = SimpleNamespace(id=uuid4())
    permission_check = AsyncMock(
        side_effect=HTTPException(status_code=403, detail="Missing partner workspace permission: remnawave_execute")
    )
    grant_check = AsyncMock()
    monkeypatch.setattr(routes, "enforce_partner_workspace_permission", permission_check)
    monkeypatch.setattr(routes, "enforce_partner_remnawave_resource_grant", grant_check)
    gateway = AsyncMock()
    receipts = AsyncMock()
    body = PartnerRemnawaveConnectionDropRequest.model_validate({"serviceIdentityUuid": str(uuid4())})

    with pytest.raises(HTTPException) as denied:
        await routes.drop_partner_node_connections(
            workspace_id=workspace_id,
            node_uuid=node_uuid,
            body=body,
            request=_request(),
            idempotency_key=_IDEMPOTENCY_KEY,
            access=_partner_access(workspace_id),
            current_user=_admin_user(current_user.id),
            db=AsyncMock(),
            gateway=gateway,
            receipts=receipts,
        )

    assert denied.value.status_code == 403
    grant_check.assert_not_awaited()
    receipts.reserve.assert_not_awaited()
    gateway.drop_once.assert_not_awaited()


@pytest.mark.unit
async def test_partner_drop_missing_or_foreign_exact_node_grant_is_404_before_io(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    workspace_id = uuid4()
    permission_check = AsyncMock()
    grant_check = AsyncMock(side_effect=HTTPException(status_code=404, detail="Remnawave resource not found"))
    monkeypatch.setattr(routes, "enforce_partner_workspace_permission", permission_check)
    monkeypatch.setattr(routes, "enforce_partner_remnawave_resource_grant", grant_check)
    gateway = AsyncMock()
    receipts = AsyncMock()

    with pytest.raises(HTTPException) as denied:
        await routes.drop_partner_node_connections(
            workspace_id=workspace_id,
            node_uuid=uuid4(),
            body=PartnerRemnawaveConnectionDropRequest.model_validate({"serviceIdentityUuid": str(uuid4())}),
            request=_request(),
            idempotency_key=_IDEMPOTENCY_KEY,
            access=_partner_access(workspace_id),
            current_user=_admin_user(uuid4()),
            db=AsyncMock(),
            gateway=gateway,
            receipts=receipts,
        )

    assert denied.value.status_code == 404
    receipts.reserve.assert_not_awaited()
    gateway.drop_once.assert_not_awaited()


@pytest.mark.unit
async def test_partner_drop_foreign_service_identity_grant_is_404_before_receipt_or_provider(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    workspace_id = uuid4()
    node_uuid = uuid4()
    identity_uuid = uuid4()
    permission_check = AsyncMock()
    grant_check = AsyncMock(
        side_effect=[
            SimpleNamespace(resource_type="node", resource_uuid=node_uuid),
            HTTPException(status_code=404, detail="Remnawave resource not found"),
        ]
    )
    monkeypatch.setattr(routes, "enforce_partner_workspace_permission", permission_check)
    monkeypatch.setattr(routes, "enforce_partner_remnawave_resource_grant", grant_check)
    monkeypatch.setattr(
        routes,
        "resolve_exact_mapped_remnawave_ref",
        AsyncMock(return_value=SimpleNamespace(require_numeric_id=lambda: 42)),
    )
    identity = SimpleNamespace(
        id=identity_uuid,
        provider_numeric_subject_id=42,
        provider_subject_ref=str(uuid4()),
    )
    db = AsyncMock()
    result = MagicMock()
    result.scalar_one_or_none.return_value = identity
    db.execute.return_value = result
    gateway = AsyncMock()
    receipts = AsyncMock()

    with pytest.raises(HTTPException) as denied:
        await routes.drop_partner_node_connections(
            workspace_id=workspace_id,
            node_uuid=node_uuid,
            body=PartnerRemnawaveConnectionDropRequest.model_validate({"serviceIdentityUuid": str(identity_uuid)}),
            request=_request(),
            idempotency_key=_IDEMPOTENCY_KEY,
            access=_partner_access(workspace_id),
            current_user=_admin_user(uuid4()),
            db=db,
            gateway=gateway,
            receipts=receipts,
        )

    assert denied.value.status_code == 404
    assert [call.kwargs["resource_type"] for call in grant_check.await_args_list] == [
        "node",
        "service_identity",
    ]
    receipts.reserve.assert_not_awaited()
    gateway.drop_once.assert_not_awaited()


@pytest.mark.unit
@pytest.mark.parametrize(
    "mapping_result",
    [
        None,
        RemnawaveIdentityAccessConflict("pending mapping"),
        RemnawaveIdentityAccessConflict("conflicting mapping"),
    ],
)
async def test_customer_missing_pending_or_conflicting_ledger_never_reaches_provider(
    monkeypatch: pytest.MonkeyPatch,
    mapping_result: object,
) -> None:
    customer_id = uuid4()
    db = AsyncMock()
    db.get.return_value = SimpleNamespace(
        id=customer_id,
        remnawave_user_id=42,
        remnawave_uuid=str(uuid4()),
        is_active=True,
        status="active",
    )
    resolver = AsyncMock()
    if isinstance(mapping_result, Exception):
        resolver.side_effect = mapping_result
    else:
        resolver.return_value = mapping_result
    monkeypatch.setattr(routes, "resolve_exact_mapped_mobile_user_ref", resolver)
    gateway = AsyncMock()
    registry = AsyncMock()

    with pytest.raises(HTTPException) as denied:
        await routes.request_customer_connections(
            customer_account_id=customer_id,
            db=db,
            gateway=gateway,
            registry=registry,
        )

    assert denied.value.status_code == 409
    gateway.request_by_user.assert_not_awaited()
    registry.issue.assert_not_awaited()


@pytest.mark.unit
async def test_admin_drop_sends_exact_shape_once_and_returns_accepted_receipt(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    actor_id = uuid4()
    body = AdminRemnawaveConnectionDropRequest.model_validate(
        {
            "dropBy": {"by": "userIds", "userIds": [42]},
            "targetNodes": {"target": "allNodes"},
        }
    )
    receipts = AsyncMock()
    reservation = _drop_reservation(audience=RemnawaveConnectionJobAudience.ADMIN, actor_id=actor_id)
    receipts.reserve.return_value = reservation
    receipts.update_state.return_value = reservation.record.model_copy(
        update={
            "state": RemnawaveConnectionDropState.ACCEPTED,
            "expires_at": reservation.record.created_at + timedelta(days=1),
        }
    )
    gateway = AsyncMock()
    audit_writer = AsyncMock()
    monkeypatch.setattr(routes, "persist_privileged_connection_drop_audit", audit_writer)

    response = await routes.drop_admin_connections(
        body=body,
        request=_request(),
        idempotency_key=_IDEMPOTENCY_KEY,
        current_user=_admin_user(actor_id),
        db=AsyncMock(),
        gateway=gateway,
        receipts=receipts,
    )

    gateway.drop_once.assert_awaited_once()
    command = gateway.drop_once.await_args.args[0]
    assert isinstance(command, RemnawaveConnectionDropCommand)
    assert command.canonical_payload() == {
        "dropBy": {"by": "userIds", "userIds": [42]},
        "targetNodes": {"target": "allNodes"},
    }
    assert response.state == "accepted"
    assert response.retry_allowed is False
    audit_call = audit_writer.await_args
    assert audit_call is not None
    assert audit_call.kwargs["audience"] is RemnawaveConnectionJobAudience.ADMIN
    assert audit_call.kwargs["context"].actor.id == actor_id


@pytest.mark.unit
async def test_customer_drop_is_server_scoped_to_canonical_user_and_all_nodes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    customer_id = uuid4()
    db = AsyncMock()
    db.get.return_value = SimpleNamespace(
        id=customer_id,
        remnawave_user_id=42,
        remnawave_uuid=str(uuid4()),
        is_active=True,
        status="active",
    )
    monkeypatch.setattr(
        routes,
        "resolve_exact_mapped_mobile_user_ref",
        AsyncMock(return_value=SimpleNamespace(require_numeric_id=lambda: 42)),
    )
    receipts = AsyncMock()
    reservation = _drop_reservation(audience=RemnawaveConnectionJobAudience.CUSTOMER, actor_id=customer_id)
    receipts.reserve.return_value = reservation
    receipts.update_state.return_value = reservation.record.model_copy(
        update={
            "state": RemnawaveConnectionDropState.ACCEPTED,
            "expires_at": reservation.record.created_at + timedelta(days=1),
        }
    )
    gateway = AsyncMock()
    audit_writer = AsyncMock()
    monkeypatch.setattr(routes, "persist_privileged_connection_drop_audit", audit_writer)

    response = await routes.drop_customer_connections(
        idempotency_key=_IDEMPOTENCY_KEY,
        customer_account_id=customer_id,
        db=db,
        gateway=gateway,
        receipts=receipts,
    )

    command = gateway.drop_once.await_args.args[0]
    assert command.canonical_payload() == {
        "dropBy": {"by": "userIds", "userIds": [42]},
        "targetNodes": {"target": "allNodes"},
    }
    assert response.state == "accepted"
    audit_writer.assert_not_awaited()


@pytest.mark.unit
async def test_partner_drop_is_server_scoped_to_exact_granted_node(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    workspace_id = uuid4()
    node_uuid = uuid4()
    actor_id = uuid4()
    permission_check = AsyncMock()
    grant_check = AsyncMock()
    monkeypatch.setattr(routes, "enforce_partner_workspace_permission", permission_check)
    monkeypatch.setattr(routes, "enforce_partner_remnawave_resource_grant", grant_check)
    identity_uuid = uuid4()
    identity_resolver = AsyncMock(return_value=42)
    monkeypatch.setattr(routes, "_partner_service_identity_numeric_user_id", identity_resolver)
    audit_writer = AsyncMock()
    monkeypatch.setattr(routes, "persist_privileged_connection_drop_audit", audit_writer)
    receipts = AsyncMock()
    reservation = _drop_reservation(audience=RemnawaveConnectionJobAudience.PARTNER, actor_id=actor_id)
    receipts.reserve.return_value = reservation
    receipts.update_state.return_value = reservation.record.model_copy(
        update={
            "state": RemnawaveConnectionDropState.ACCEPTED,
            "expires_at": reservation.record.created_at + timedelta(days=1),
        }
    )
    gateway = AsyncMock()

    response = await routes.drop_partner_node_connections(
        workspace_id=workspace_id,
        node_uuid=node_uuid,
        body=PartnerRemnawaveConnectionDropRequest.model_validate({"serviceIdentityUuid": str(identity_uuid)}),
        request=_request(),
        idempotency_key=_IDEMPOTENCY_KEY,
        access=_partner_access(workspace_id),
        current_user=_admin_user(actor_id),
        db=AsyncMock(),
        gateway=gateway,
        receipts=receipts,
    )

    permission_call = permission_check.await_args
    grant_call = grant_check.await_args
    assert permission_call is not None
    assert grant_call is not None
    assert permission_call.kwargs["permission"].value == "remnawave_execute"
    assert grant_call.kwargs["resource_uuid"] == node_uuid
    assert grant_call.kwargs["permission"].value == "remnawave_execute"
    assert identity_resolver.await_args.kwargs["service_identity_uuid"] == identity_uuid
    command = gateway.drop_once.await_args.args[0]
    assert command.canonical_payload() == {
        "dropBy": {"by": "userIds", "userIds": [42]},
        "targetNodes": {"target": "specificNodes", "nodeUuids": [str(node_uuid)]},
    }
    assert response.state == "accepted"
    audit_call = audit_writer.await_args
    assert audit_call is not None
    assert audit_call.kwargs["audience"] is RemnawaveConnectionJobAudience.PARTNER
    assert audit_call.kwargs["context"].workspace_id == workspace_id


@pytest.mark.unit
@pytest.mark.parametrize(
    "provider_failure",
    [routes.RemnawaveTransportError(), routes.RemnawaveHTTPStatusError(status_code=503)],
)
async def test_drop_replay_or_ambiguous_outcome_never_sends_twice(provider_failure: Exception) -> None:
    actor_id = uuid4()
    command = RemnawaveConnectionDropCommand(
        dropBy=RemnawaveDropByUserIds(userIds=[42]),
        targetNodes=RemnawaveDropOnAllNodes(),
    )
    receipts = AsyncMock()
    receipts.reserve.side_effect = [
        _drop_reservation(audience=RemnawaveConnectionJobAudience.ADMIN, actor_id=actor_id),
        _drop_reservation(
            audience=RemnawaveConnectionJobAudience.ADMIN,
            actor_id=actor_id,
            is_new=False,
        ),
    ]
    gateway = AsyncMock()
    gateway.drop_once.side_effect = provider_failure

    first = await routes._execute_connection_drop(
        audience=RemnawaveConnectionJobAudience.ADMIN,
        actor_id=actor_id,
        scope="admin:global",
        client_idempotency_key=_IDEMPOTENCY_KEY,
        command=command,
        gateway=gateway,
        receipts=receipts,
    )
    second = await routes._execute_connection_drop(
        audience=RemnawaveConnectionJobAudience.ADMIN,
        actor_id=actor_id,
        scope="admin:global",
        client_idempotency_key=_IDEMPOTENCY_KEY,
        command=command,
        gateway=gateway,
        receipts=receipts,
    )

    assert first.state == second.state == "outcome_unknown"
    assert first.retry_allowed is second.retry_allowed is False
    assert gateway.drop_once.await_count == 1


@pytest.mark.unit
async def test_drop_known_upstream_rejection_is_recorded_and_not_retried() -> None:
    actor_id = uuid4()
    reservation = _drop_reservation(audience=RemnawaveConnectionJobAudience.ADMIN, actor_id=actor_id)
    rejected = reservation.record.model_copy(
        update={
            "state": RemnawaveConnectionDropState.REJECTED,
            "expires_at": reservation.record.created_at + timedelta(days=1),
        }
    )
    receipts = AsyncMock()
    receipts.reserve.side_effect = [
        reservation,
        RemnawaveConnectionDropReservation(
            record=rejected,
            is_new=False,
        ),
    ]
    receipts.update_state.return_value = rejected
    gateway = AsyncMock()
    gateway.drop_once.side_effect = routes.RemnawaveHTTPStatusError(status_code=400)
    command = RemnawaveConnectionDropCommand(
        dropBy=RemnawaveDropByUserIds(userIds=[42]),
        targetNodes=RemnawaveDropOnAllNodes(),
    )

    for _attempt in range(2):
        with pytest.raises(HTTPException) as rejected_response:
            await routes._execute_connection_drop(
                audience=RemnawaveConnectionJobAudience.ADMIN,
                actor_id=actor_id,
                scope="admin:global",
                client_idempotency_key=_IDEMPOTENCY_KEY,
                command=command,
                gateway=gateway,
                receipts=receipts,
            )
        assert rejected_response.value.status_code == 502

    receipts.update_state.assert_awaited_once_with(reservation, RemnawaveConnectionDropState.REJECTED)
    assert gateway.drop_once.await_count == 1


@pytest.mark.unit
@pytest.mark.parametrize(
    ("receipt_error", "expected_status"),
    [
        (RemnawaveConnectionDropReceiptConflictError("different payload"), 409),
        (RemnawaveConnectionDropReceiptUnavailableError("redis unavailable"), 503),
    ],
)
async def test_drop_receipt_failure_happens_before_provider_io(receipt_error: Exception, expected_status: int) -> None:
    actor_id = uuid4()
    receipts = AsyncMock()
    receipts.reserve.side_effect = receipt_error
    gateway = AsyncMock()

    with pytest.raises(HTTPException) as denied:
        await routes._execute_connection_drop(
            audience=RemnawaveConnectionJobAudience.ADMIN,
            actor_id=actor_id,
            scope="admin:global",
            client_idempotency_key=_IDEMPOTENCY_KEY,
            command=RemnawaveConnectionDropCommand(
                dropBy=RemnawaveDropByUserIds(userIds=[42]),
                targetNodes=RemnawaveDropOnAllNodes(),
            ),
            gateway=gateway,
            receipts=receipts,
        )

    assert denied.value.status_code == expected_status
    gateway.drop_once.assert_not_awaited()


@pytest.mark.unit
def test_connections_openapi_exposes_all_audiences_and_truthful_drop_status() -> None:
    app = FastAPI()
    app.include_router(routes.router, prefix="/api/v1")
    paths = app.openapi()["paths"]

    assert "/api/v1/admin/remnawave/connections/users/{user_id}/requests" in paths
    assert "/api/v1/admin/remnawave/connections/nodes/{node_uuid}/requests" in paths
    assert "/api/v1/partner-workspaces/{workspace_id}/remnawave/connections/nodes/{node_uuid}/requests" in paths
    assert "/api/v1/customer/remnawave/connections/requests" in paths
    drop_operation = paths["/api/v1/admin/remnawave/connections/drop"]["post"]
    assert "202" in drop_operation["responses"]
    assert "503" in drop_operation["responses"]
    idempotency_header = next(
        parameter for parameter in drop_operation["parameters"] if parameter["name"] == "Idempotency-Key"
    )
    assert idempotency_header["in"] == "header"
    assert idempotency_header["required"] is True
    partner_drop = paths["/api/v1/partner-workspaces/{workspace_id}/remnawave/connections/nodes/{node_uuid}/drop"][
        "post"
    ]
    request_ref = partner_drop["requestBody"]["content"]["application/json"]["schema"]["$ref"]
    request_schema = app.openapi()["components"]["schemas"][request_ref.rsplit("/", 1)[-1]]
    assert request_schema["required"] == ["serviceIdentityUuid"]
    assert set(request_schema["properties"]) == {"serviceIdentityUuid"}
    assert request_schema["additionalProperties"] is False


@pytest.mark.unit
@pytest.mark.parametrize("denied_status", [403, 404])
async def test_partner_api_hides_cross_tenant_or_missing_permission_before_provider(
    denied_status: int,
) -> None:
    workspace_id = uuid4()
    gateway = AsyncMock()
    registry = AsyncMock()
    app = FastAPI()
    app.include_router(routes.router, prefix="/api/v1")

    async def deny_workspace_access():
        raise HTTPException(status_code=denied_status, detail="Remnawave workspace unavailable")

    async def current_user():
        return SimpleNamespace(id=uuid4())

    async def db():
        return AsyncMock()

    app.dependency_overrides[routes.get_partner_remnawave_workspace_access] = deny_workspace_access
    app.dependency_overrides[get_current_active_web_user] = current_user
    app.dependency_overrides[get_db] = db
    app.dependency_overrides[routes.get_remnawave_connections_gateway] = lambda: gateway
    app.dependency_overrides[routes.get_remnawave_connection_job_registry] = lambda: registry

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="https://partner.cyber-vpn.net",
    ) as client:
        response = await client.post(
            f"/api/v1/partner-workspaces/{workspace_id}/remnawave/connections/nodes/{uuid4()}/requests"
        )

    assert response.status_code == denied_status
    gateway.request_by_node.assert_not_awaited()
    registry.issue.assert_not_awaited()


@pytest.mark.unit
async def test_customer_api_cross_actor_request_id_is_404_without_provider_lookup(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    owning_customer_id = uuid4()
    attacking_customer_id = uuid4()
    db_session = AsyncMock()
    db_session.get.return_value = SimpleNamespace(
        id=attacking_customer_id,
        remnawave_user_id=99,
        remnawave_uuid=str(uuid4()),
        is_active=True,
        status="active",
    )
    monkeypatch.setattr(
        routes,
        "resolve_exact_mapped_mobile_user_ref",
        AsyncMock(return_value=SimpleNamespace(require_numeric_id=lambda: 99)),
    )
    registry = AsyncMock()
    registry.load.return_value = RemnawaveConnectionJobRecord(
        audience=RemnawaveConnectionJobAudience.CUSTOMER,
        kind=RemnawaveConnectionJobKind.USER,
        actor_id=owning_customer_id,
        user_id=42,
        upstream_job_id="provider-job-1",
    )
    gateway = AsyncMock()
    app = FastAPI()
    app.include_router(routes.router, prefix="/api/v1")

    async def current_customer():
        return attacking_customer_id

    async def db():
        return db_session

    app.dependency_overrides[get_current_mobile_user_id] = current_customer
    app.dependency_overrides[get_db] = db
    app.dependency_overrides[routes.get_remnawave_connections_gateway] = lambda: gateway
    app.dependency_overrides[routes.get_remnawave_connection_job_registry] = lambda: registry

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="https://app.cyber-vpn.net",
    ) as client:
        response = await client.get(f"/api/v1/customer/remnawave/connections/requests/{_REQUEST_ID}")

    assert response.status_code == 404
    assert response.json()["detail"] == "Connection request not found"
    gateway.get_by_user_result.assert_not_awaited()
