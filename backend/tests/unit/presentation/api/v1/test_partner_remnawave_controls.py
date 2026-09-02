from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID, uuid4

import httpx
import pytest
from fastapi import FastAPI, HTTPException, status
from sqlalchemy.dialects import postgresql

from src.domain.entities.partner_permission import PartnerPermission
from src.presentation.api.v1.partner_remnawave import routes
from src.presentation.api.v1.partner_remnawave.grant_queries import (
    MAX_ACTIVE_PARTNER_REMNAWAVE_GRANTS,
    load_readable_partner_remnawave_grants,
)
from src.presentation.dependencies.auth import get_current_active_web_user
from src.presentation.dependencies.database import get_db


def _access(
    workspace_id: UUID,
    *permissions: PartnerPermission,
) -> SimpleNamespace:
    return SimpleNamespace(
        workspace=SimpleNamespace(id=workspace_id, status="active"),
        permission_keys=frozenset(permission.value for permission in permissions),
        is_internal_admin_override=False,
    )


def _grant(
    workspace_id: UUID,
    resource_uuid: UUID,
    *,
    resource_type: str = "node",
    permission_keys: list[str] | None = None,
) -> SimpleNamespace:
    return SimpleNamespace(
        workspace_id=workspace_id,
        resource_type=resource_type,
        resource_uuid=resource_uuid,
        permission_keys=permission_keys or [PartnerPermission.REMNAWAVE_READ.value],
        revoked_at=None,
        audit_reason="internal reason must not be serialized",
        granted_by_admin_user_id=uuid4(),
    )


def _scalar_one_or_none(value: object) -> MagicMock:
    result = MagicMock()
    result.scalar_one_or_none.return_value = value
    result.scalars.return_value.all.return_value = [] if value is None else [value]
    return result


def test_service_identity_grant_serializes_without_provider_identity_details() -> None:
    workspace_id = uuid4()
    resource_uuid = uuid4()
    response = routes._serialize_resource(
        access=_access(
            workspace_id,
            PartnerPermission.REMNAWAVE_READ,
            PartnerPermission.REMNAWAVE_EXECUTE,
        ),
        grant=_grant(
            workspace_id,
            resource_uuid,
            resource_type="service_identity",
            permission_keys=["remnawave_read", "remnawave_execute"],
        ),
    )

    assert response.resource_type is routes.PartnerRemnawaveResourceType.SERVICE_IDENTITY
    assert response.resource_uuid == resource_uuid
    assert response.provider_details_available is False
    serialized = response.model_dump_json()
    assert "provider_numeric" not in serialized
    assert "provider_subject" not in serialized


def _app(
    *,
    own_workspace_id: UUID,
    db: AsyncMock,
    access: SimpleNamespace,
) -> FastAPI:
    app = FastAPI()
    app.include_router(routes.router, prefix="/api/v1")
    current_user = SimpleNamespace(id=uuid4(), totp_enabled=True)

    async def access_override(workspace_id: UUID):
        if workspace_id != own_workspace_id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Remnawave workspace not found")
        return access

    async def user_override():
        return current_user

    async def db_override():
        yield db

    app.dependency_overrides[routes.get_partner_remnawave_workspace_access] = access_override
    app.dependency_overrides[get_current_active_web_user] = user_override
    app.dependency_overrides[get_db] = db_override
    return app


@pytest.mark.unit
async def test_direct_resource_url_hides_foreign_workspace_and_missing_grant() -> None:
    own_workspace_id = uuid4()
    foreign_workspace_id = uuid4()
    resource_uuid = uuid4()
    db = AsyncMock()
    db.execute.return_value = _scalar_one_or_none(None)
    app = _app(
        own_workspace_id=own_workspace_id,
        db=db,
        access=_access(own_workspace_id, PartnerPermission.REMNAWAVE_READ),
    )

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="https://partner.cyber-vpn.net",
    ) as client:
        foreign = await client.get(
            f"/api/v1/partner-workspaces/{foreign_workspace_id}/remnawave/resources/node/{resource_uuid}"
        )
        missing = await client.get(
            f"/api/v1/partner-workspaces/{own_workspace_id}/remnawave/resources/node/{resource_uuid}"
        )

    assert foreign.status_code == 404
    assert missing.status_code == 404
    assert missing.json()["detail"] == "Remnawave resource not found"


@pytest.mark.unit
async def test_direct_resource_url_requires_read_in_exact_object_grant() -> None:
    workspace_id = uuid4()
    resource_uuid = uuid4()
    write_only_grant = _grant(
        workspace_id,
        resource_uuid,
        permission_keys=[PartnerPermission.REMNAWAVE_WRITE.value],
    )
    db = AsyncMock()
    db.execute.return_value = _scalar_one_or_none(write_only_grant)
    app = _app(
        own_workspace_id=workspace_id,
        db=db,
        access=_access(workspace_id, PartnerPermission.REMNAWAVE_READ),
    )

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="https://partner.cyber-vpn.net",
    ) as client:
        response = await client.get(
            f"/api/v1/partner-workspaces/{workspace_id}/remnawave/resources/node/{resource_uuid}"
        )

    assert response.status_code == 404


@pytest.mark.unit
async def test_direct_resource_url_requires_role_read_even_with_exact_object_grant() -> None:
    workspace_id = uuid4()
    resource_uuid = uuid4()
    grant = _grant(
        workspace_id,
        resource_uuid,
        permission_keys=[PartnerPermission.REMNAWAVE_READ.value],
    )
    db = AsyncMock()
    db.execute.return_value = _scalar_one_or_none(grant)
    app = _app(
        own_workspace_id=workspace_id,
        db=db,
        access=_access(workspace_id),
    )

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="https://partner.cyber-vpn.net",
    ) as client:
        response = await client.get(
            f"/api/v1/partner-workspaces/{workspace_id}/remnawave/resources/node/{resource_uuid}"
        )

    assert response.status_code == 404
    assert response.json()["detail"] == "Remnawave resource not found"
    assert db.execute.await_count == 0


@pytest.mark.unit
async def test_granted_detail_returns_allowlisted_ledger_fields_and_truthful_operations() -> None:
    workspace_id = uuid4()
    resource_uuid = uuid4()
    grant = _grant(
        workspace_id,
        resource_uuid,
        permission_keys=[
            PartnerPermission.REMNAWAVE_READ.value,
            PartnerPermission.REMNAWAVE_WRITE.value,
            PartnerPermission.REMNAWAVE_EXECUTE.value,
        ],
    )
    db = AsyncMock()
    db.execute.return_value = _scalar_one_or_none(grant)
    app = _app(
        own_workspace_id=workspace_id,
        db=db,
        access=_access(
            workspace_id,
            PartnerPermission.REMNAWAVE_READ,
            PartnerPermission.REMNAWAVE_WRITE,
            PartnerPermission.REMNAWAVE_EXECUTE,
        ),
    )

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="https://partner.cyber-vpn.net",
    ) as client:
        response = await client.get(
            f"/api/v1/partner-workspaces/{workspace_id}/remnawave/resources/node/{resource_uuid}"
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload == {
        "workspace_id": str(workspace_id),
        "resource_type": "node",
        "resource_uuid": str(resource_uuid),
        "effective_permissions": ["remnawave_read", "remnawave_write", "remnawave_execute"],
        "available_operations": ["inspect_assignment"],
        "unavailable_operations": ["mutate_resource", "execute_resource"],
        "forbidden_operations": ["browser_ssh"],
        "provider_details_available": False,
        "safe_mutations": [],
    }
    serialized = response.text
    assert "audit_reason" not in serialized
    assert "granted_by" not in serialized
    assert "internal reason" not in serialized


@pytest.mark.unit
async def test_granted_detail_only_reports_role_and_object_permission_intersection() -> None:
    workspace_id = uuid4()
    resource_uuid = uuid4()
    grant = _grant(
        workspace_id,
        resource_uuid,
        permission_keys=[
            PartnerPermission.REMNAWAVE_READ.value,
            PartnerPermission.REMNAWAVE_WRITE.value,
            PartnerPermission.REMNAWAVE_EXECUTE.value,
        ],
    )
    db = AsyncMock()
    db.execute.return_value = _scalar_one_or_none(grant)
    app = _app(
        own_workspace_id=workspace_id,
        db=db,
        access=_access(workspace_id, PartnerPermission.REMNAWAVE_READ),
    )

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="https://partner.cyber-vpn.net",
    ) as client:
        response = await client.get(
            f"/api/v1/partner-workspaces/{workspace_id}/remnawave/resources/node/{resource_uuid}"
        )

    assert response.status_code == 200
    assert response.json()["effective_permissions"] == [PartnerPermission.REMNAWAVE_READ.value]


@pytest.mark.unit
async def test_partner_browser_ssh_direct_url_is_always_forbidden() -> None:
    workspace_id = uuid4()
    db = AsyncMock()
    app = _app(
        own_workspace_id=workspace_id,
        db=db,
        access=_access(
            workspace_id,
            PartnerPermission.REMNAWAVE_READ,
            PartnerPermission.REMNAWAVE_WRITE,
            PartnerPermission.REMNAWAVE_EXECUTE,
            PartnerPermission.REMNAWAVE_SSH,
        ),
    )

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="https://partner.cyber-vpn.net",
    ) as client:
        response = await client.post(f"/api/v1/partner-workspaces/{workspace_id}/remnawave/node-ssh/tickets")

    assert response.status_code == 403
    assert response.json()["detail"] == "Browser SSH is admin-only"


@pytest.mark.unit
async def test_resource_inventory_is_bounded_and_never_advertises_unsupported_controls() -> None:
    workspace_id = uuid4()
    grants = [
        _grant(workspace_id, uuid4(), resource_type="host"),
        _grant(workspace_id, uuid4(), resource_type="node"),
        _grant(workspace_id, uuid4(), resource_type="squad"),
    ]
    count_result = MagicMock()
    count_result.scalar_one.return_value = 3
    list_result = MagicMock()
    list_result.scalars.return_value.all.return_value = grants
    db = AsyncMock()
    db.execute.side_effect = [count_result, list_result]
    access = _access(workspace_id, PartnerPermission.REMNAWAVE_READ)

    response = await routes.list_partner_remnawave_resources(
        workspace_id=workspace_id,
        limit=2,
        offset=0,
        access=access,
        db=db,
    )

    assert response.total == 3
    assert response.next_offset == 2
    assert [item.resource_type for item in response.items] == ["host", "node"]
    assert response.capabilities.inspect_assignment is True
    assert response.capabilities.mutate_resource is False
    assert response.capabilities.execute_resource is False
    assert response.capabilities.browser_ssh is False
    assert response.capabilities.mutation_unavailable_reason == "no_current_write_granted_safe_mutation"
    assert response.capabilities.safe_mutations == []


@pytest.mark.unit
async def test_active_workspace_membership_without_remnawave_read_is_forbidden(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    workspace_id = uuid4()
    access = _access(workspace_id)
    resolver = AsyncMock(return_value=access)
    monkeypatch.setattr(routes, "resolve_partner_workspace_access", resolver)

    with pytest.raises(HTTPException) as denied:
        await routes.get_partner_remnawave_workspace_access(
            workspace_id=workspace_id,
            current_realm=SimpleNamespace(realm_type="partner"),
            current_user=SimpleNamespace(id=uuid4(), totp_enabled=True),
            db=AsyncMock(),
        )

    assert denied.value.status_code == 403
    assert denied.value.detail == "Missing partner workspace permission: remnawave_read"


@pytest.mark.unit
async def test_active_workspace_membership_with_remnawave_read_is_allowed(monkeypatch: pytest.MonkeyPatch) -> None:
    workspace_id = uuid4()
    access = _access(workspace_id, PartnerPermission.REMNAWAVE_READ)
    resolver = AsyncMock(return_value=access)
    monkeypatch.setattr(routes, "resolve_partner_workspace_access", resolver)

    result = await routes.get_partner_remnawave_workspace_access(
        workspace_id=workspace_id,
        current_realm=SimpleNamespace(realm_type="partner"),
        current_user=SimpleNamespace(id=uuid4(), totp_enabled=True),
        db=AsyncMock(),
    )

    assert result is access


@pytest.mark.unit
async def test_foreign_membership_failure_is_hidden_as_not_found(monkeypatch: pytest.MonkeyPatch) -> None:
    resolver = AsyncMock(side_effect=HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="workspace denied"))
    monkeypatch.setattr(routes, "resolve_partner_workspace_access", resolver)

    with pytest.raises(HTTPException) as hidden:
        await routes.get_partner_remnawave_workspace_access(
            workspace_id=uuid4(),
            current_realm=SimpleNamespace(realm_type="partner"),
            current_user=SimpleNamespace(id=uuid4(), totp_enabled=True),
            db=AsyncMock(),
        )

    assert hidden.value.status_code == 404
    assert hidden.value.detail == "Remnawave workspace not found"


@pytest.mark.unit
async def test_grant_query_is_bounded_and_never_uses_generic_json_contains() -> None:
    workspace_id = uuid4()
    count_result = MagicMock()
    count_result.scalar_one.return_value = 1
    list_result = MagicMock()
    list_result.scalars.return_value.all.return_value = [
        _grant(workspace_id, uuid4()),
    ]
    db = AsyncMock()
    db.execute.side_effect = [count_result, list_result]

    result = await load_readable_partner_remnawave_grants(db=db, workspace_id=workspace_id)

    assert len(result) == 1
    statements = [call.args[0] for call in db.execute.await_args_list]
    compiled = [str(statement.compile(dialect=postgresql.dialect())) for statement in statements]
    assert all(" LIKE " not in sql for sql in compiled)
    assert all("permission_keys LIKE" not in sql for sql in compiled)
    assert "LIMIT" in compiled[1]
    list_params = statements[1].compile(dialect=postgresql.dialect()).params
    assert MAX_ACTIVE_PARTNER_REMNAWAVE_GRANTS + 1 in list_params.values()


@pytest.mark.unit
async def test_grant_query_fails_closed_before_loading_an_oversized_workspace() -> None:
    count_result = MagicMock()
    count_result.scalar_one.return_value = MAX_ACTIVE_PARTNER_REMNAWAVE_GRANTS + 1
    db = AsyncMock()
    db.execute.return_value = count_result

    with pytest.raises(HTTPException) as rejected:
        await load_readable_partner_remnawave_grants(db=db, workspace_id=uuid4())

    assert rejected.value.status_code == 503
    assert rejected.value.detail == "Remnawave resource inventory exceeds safe limit"
    assert db.execute.await_count == 1
