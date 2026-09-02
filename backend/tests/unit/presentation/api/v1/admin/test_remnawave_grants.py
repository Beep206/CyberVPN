import base64
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID, uuid4

import pytest
from fastapi import FastAPI, HTTPException
from pydantic import ValidationError

from src.infrastructure.database.models.remnawave_upgrade_model import PartnerRemnawaveResourceGrantModel
from src.presentation.api.v1.admin import remnawave_grants
from src.presentation.api.v1.admin.remnawave_grants import (
    RemnawaveResourceGrantCreateRequest,
    RemnawaveResourceGrantRevokeRequest,
)


def _scalar_result(value):
    result = MagicMock()
    result.scalar_one_or_none.return_value = value
    result.scalars.return_value.first.return_value = value
    return result


def _scalars_result(values):
    result = MagicMock()
    result.scalars.return_value.all.return_value = values
    return result


def _grant(*, index: int, granted_at: datetime, revoked: bool = False):
    return PartnerRemnawaveResourceGrantModel(
        id=UUID(int=index),
        workspace_id=UUID(int=10_000 + index),
        resource_type="node",
        resource_uuid=UUID(int=20_000 + index),
        permission_keys=["remnawave_read"],
        granted_by_admin_user_id=UUID(int=30_000 + index),
        granted_at=granted_at,
        revoked_by_admin_user_id=UUID(int=40_000 + index) if revoked else None,
        revoked_at=granted_at + timedelta(minutes=1) if revoked else None,
        audit_reason="approved scoped node visibility",
    )


def _request() -> SimpleNamespace:
    return SimpleNamespace(client=None, headers={})


def test_resource_grant_rejects_non_remnawave_permission() -> None:
    with pytest.raises(ValidationError):
        RemnawaveResourceGrantCreateRequest(
            workspace_id=uuid4(),
            resource_type="node",
            resource_uuid=uuid4(),
            permission_keys=["integrations_write"],
            reason="scoped operations access",
        )


@pytest.mark.parametrize(
    "request_type",
    [RemnawaveResourceGrantCreateRequest, RemnawaveResourceGrantRevokeRequest],
)
def test_resource_grant_rejects_whitespace_only_audit_reason(request_type) -> None:
    kwargs = {"reason": "      "}
    if request_type is RemnawaveResourceGrantCreateRequest:
        kwargs.update(
            workspace_id=uuid4(),
            resource_type="node",
            resource_uuid=uuid4(),
            permission_keys=["remnawave_read"],
        )
    with pytest.raises(ValidationError):
        request_type(**kwargs)


def test_resource_grant_normalizes_audit_reason_before_persistence() -> None:
    request = RemnawaveResourceGrantRevokeRequest(reason="  approved revocation  ")

    assert request.reason == "approved revocation"


def test_service_identity_is_an_explicit_grant_resource_type() -> None:
    request = RemnawaveResourceGrantCreateRequest(
        workspace_id=uuid4(),
        resource_type="service_identity",
        resource_uuid=uuid4(),
        permission_keys=["remnawave_execute"],
        reason="approved exact service identity operation",
    )

    assert request.resource_type == "service_identity"


def test_resource_grant_list_openapi_contract_is_bounded_and_cursor_based() -> None:
    app = FastAPI()
    app.include_router(remnawave_grants.router, prefix="/api/v1")

    operation = app.openapi()["paths"]["/api/v1/admin/remnawave-resource-grants"]["get"]
    parameters = {parameter["name"]: parameter for parameter in operation["parameters"]}

    assert parameters["limit"]["schema"] == {
        "default": 50,
        "maximum": 100,
        "minimum": 1,
        "title": "Limit",
        "type": "integer",
    }
    assert parameters["cursor"]["schema"]["anyOf"][0] == {
        "maxLength": 256,
        "minLength": 1,
        "type": "string",
    }
    response_ref = operation["responses"]["200"]["content"]["application/json"]["schema"]["$ref"]
    response_schema_name = response_ref.rsplit("/", 1)[-1]
    response_schema = app.openapi()["components"]["schemas"][response_schema_name]
    assert "next_cursor" in response_schema["properties"]


@pytest.mark.asyncio
async def test_resource_grant_list_fetches_one_extra_row_and_emits_keyset_cursor() -> None:
    granted_at = datetime(2026, 8, 30, 12, 0, tzinfo=UTC)
    rows = [
        _grant(index=3, granted_at=granted_at),
        _grant(index=2, granted_at=granted_at),
        _grant(index=1, granted_at=granted_at - timedelta(seconds=1)),
    ]
    db = MagicMock()
    db.execute = AsyncMock(return_value=_scalars_result(rows))

    response = await remnawave_grants.list_remnawave_resource_grants(
        workspace_id=None,
        include_revoked=False,
        limit=2,
        cursor=None,
        db=db,
        _=None,
    )

    assert [item.id for item in response.items] == [rows[0].id, rows[1].id]
    assert response.next_cursor is not None
    assert remnawave_grants._decode_grant_cursor(response.next_cursor) == (
        granted_at,
        rows[1].id,
    )
    statement = db.execute.await_args.args[0]
    assert statement._limit_clause.value == 3
    rendered_statement = str(statement)
    assert (
        "ORDER BY partner_remnawave_resource_grants.granted_at DESC, partner_remnawave_resource_grants.id DESC"
    ) in rendered_statement
    assert "partner_remnawave_resource_grants.revoked_at IS NULL" in rendered_statement


@pytest.mark.asyncio
async def test_resource_grant_list_cursor_is_stable_and_revoked_inclusion_is_preserved() -> None:
    granted_at = datetime(2026, 8, 30, 12, 0, tzinfo=UTC)
    cursor = remnawave_grants._encode_grant_cursor(
        granted_at=granted_at,
        grant_id=UUID(int=50),
    )
    workspace_id = UUID(int=60)
    db = MagicMock()
    db.execute = AsyncMock(return_value=_scalars_result([]))

    response = await remnawave_grants.list_remnawave_resource_grants(
        workspace_id=workspace_id,
        include_revoked=True,
        limit=100,
        cursor=cursor,
        db=db,
        _=None,
    )

    assert response.items == []
    assert response.next_cursor is None
    statement = db.execute.await_args.args[0]
    assert statement._limit_clause.value == 101
    rendered_statement = str(statement)
    assert "partner_remnawave_resource_grants.workspace_id =" in rendered_statement
    assert "partner_remnawave_resource_grants.revoked_at IS NULL" not in rendered_statement
    assert "partner_remnawave_resource_grants.granted_at <" in rendered_statement
    assert "partner_remnawave_resource_grants.granted_at =" in rendered_statement
    assert "partner_remnawave_resource_grants.id <" in rendered_statement


@pytest.mark.asyncio
@pytest.mark.parametrize("limit", [0, 101])
async def test_resource_grant_list_rejects_out_of_range_limit(limit: int) -> None:
    db = MagicMock()
    db.execute = AsyncMock()

    with pytest.raises(HTTPException) as exc_info:
        await remnawave_grants.list_remnawave_resource_grants(
            workspace_id=None,
            include_revoked=False,
            limit=limit,
            cursor=None,
            db=db,
            _=None,
        )

    assert exc_info.value.status_code == 422
    db.execute.assert_not_awaited()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "cursor",
    [
        "not-base64!",
        base64.urlsafe_b64encode(b"{}").decode("ascii").rstrip("="),
        "a" * 257,
    ],
)
async def test_resource_grant_list_rejects_invalid_cursor(cursor: str) -> None:
    db = MagicMock()
    db.execute = AsyncMock()

    with pytest.raises(HTTPException) as exc_info:
        await remnawave_grants.list_remnawave_resource_grants(
            workspace_id=None,
            include_revoked=False,
            limit=50,
            cursor=cursor,
            db=db,
            _=None,
        )

    assert exc_info.value.status_code == 422
    assert exc_info.value.detail == "Invalid Remnawave resource grant cursor"
    db.execute.assert_not_awaited()


@pytest.mark.asyncio
async def test_resource_grant_issue_is_explicit_and_audited(monkeypatch) -> None:
    db = MagicMock()
    db.execute = AsyncMock(return_value=_scalar_result(None))
    db.flush = AsyncMock()
    db.commit = AsyncMock()
    db.refresh = AsyncMock()
    db.add.side_effect = lambda grant: setattr(grant, "id", grant.id or uuid4())
    audit = AsyncMock()
    monkeypatch.setattr(remnawave_grants, "write_required_admin_audit_entry", audit)
    actor = SimpleNamespace(id=uuid4())
    body = RemnawaveResourceGrantCreateRequest(
        workspace_id=uuid4(),
        resource_type="node",
        resource_uuid=uuid4(),
        permission_keys=["remnawave_read", "remnawave_execute", "remnawave_read"],
        reason="approved scoped node operations",
    )

    response = await remnawave_grants.create_remnawave_resource_grant(
        body=body,
        request=_request(),
        current_user=actor,
        db=db,
        _=None,
    )

    assert response.workspace_id == body.workspace_id
    assert response.permission_keys == ["remnawave_read", "remnawave_execute"]
    assert response.granted_by_admin_user_id == actor.id
    audit.assert_awaited_once()
    assert audit.await_args.kwargs["action"] == "partner_remnawave_resource_grant.issued"
    db.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_resource_grant_cannot_be_silently_overwritten() -> None:
    existing = SimpleNamespace(revoked_at=None)
    db = MagicMock()
    db.execute = AsyncMock(return_value=_scalar_result(existing))

    with pytest.raises(HTTPException) as exc_info:
        await remnawave_grants.create_remnawave_resource_grant(
            body=RemnawaveResourceGrantCreateRequest(
                workspace_id=uuid4(),
                resource_type="host",
                resource_uuid=uuid4(),
                permission_keys=["remnawave_read"],
                reason="approved scoped host visibility",
            ),
            request=_request(),
            current_user=SimpleNamespace(id=uuid4()),
            db=db,
            _=None,
        )

    assert exc_info.value.status_code == 409


@pytest.mark.asyncio
async def test_resource_grant_revoke_is_immediate_and_audited(monkeypatch) -> None:
    grant = PartnerRemnawaveResourceGrantModel(
        id=uuid4(),
        workspace_id=uuid4(),
        resource_type="shared_list",
        resource_uuid=uuid4(),
        permission_keys=["remnawave_read"],
        granted_by_admin_user_id=uuid4(),
        granted_at=datetime.now(UTC),
        audit_reason="initial approved access",
    )
    db = MagicMock()
    db.get = AsyncMock(return_value=grant)
    db.flush = AsyncMock()
    db.commit = AsyncMock()
    db.refresh = AsyncMock()
    audit = AsyncMock()
    monkeypatch.setattr(remnawave_grants, "write_required_admin_audit_entry", audit)
    actor = SimpleNamespace(id=uuid4())

    response = await remnawave_grants.revoke_remnawave_resource_grant(
        grant_id=grant.id,
        body=RemnawaveResourceGrantRevokeRequest(reason="workspace assignment withdrawn"),
        request=_request(),
        current_user=actor,
        db=db,
        _=None,
    )

    assert response.revoked_by_admin_user_id == actor.id
    assert response.revoked_at is not None
    audit.assert_awaited_once()
    assert audit.await_args.kwargs["action"] == "partner_remnawave_resource_grant.revoked"
    db.commit.assert_awaited_once()
