from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from fastapi import HTTPException
from pydantic import SecretStr

from src.config.settings import settings
from src.domain.enums import AdminRole
from src.presentation.api.v1.remnawave_connections import routes
from src.presentation.api.v1.remnawave_connections.schemas import RemnawaveConnectionsCapabilitiesResponse


@pytest.mark.unit
def test_connections_capabilities_default_destructive_actions_off() -> None:
    capabilities = RemnawaveConnectionsCapabilitiesResponse()

    assert capabilities.read_connections is True
    assert capabilities.drop_connections is False
    assert capabilities.drop_requires_idempotency_key is True
    assert capabilities.drop_outcome_may_be_unknown is True


@pytest.mark.unit
def test_admin_drop_capability_requires_admin_role_and_runtime_secret(monkeypatch) -> None:
    monkeypatch.setattr(settings, "remnawave_connection_drop_hmac_secret", SecretStr("x" * 32))

    assert routes._admin_drop_available(SimpleNamespace(role=AdminRole.ADMIN.value)) is True
    assert routes._admin_drop_available(SimpleNamespace(role=AdminRole.OPERATOR.value)) is False

    monkeypatch.setattr(settings, "remnawave_connection_drop_hmac_secret", SecretStr(""))
    assert routes._admin_drop_available(SimpleNamespace(role=AdminRole.ADMIN.value)) is False


@pytest.mark.unit
async def test_partner_drop_capability_requires_role_node_and_exact_service_identity(
    monkeypatch,
) -> None:
    workspace_id = uuid4()
    node_uuid = uuid4()
    identity_uuid = uuid4()
    access = SimpleNamespace(
        workspace=SimpleNamespace(id=workspace_id, status="active"),
        permission_keys=frozenset({"remnawave_read", "remnawave_execute"}),
        is_internal_admin_override=False,
    )
    current_user = SimpleNamespace(totp_enabled=True)
    monkeypatch.setattr(settings, "remnawave_connection_drop_hmac_secret", SecretStr("x" * 32))
    monkeypatch.setattr(routes, "enforce_partner_workspace_permission", AsyncMock())
    monkeypatch.setattr(
        routes,
        "load_readable_partner_remnawave_grants",
        AsyncMock(
            return_value=[
                SimpleNamespace(
                    resource_type="node",
                    resource_uuid=node_uuid,
                    permission_keys=["remnawave_read", "remnawave_execute"],
                ),
                SimpleNamespace(
                    resource_type="service_identity",
                    resource_uuid=identity_uuid,
                    permission_keys=["remnawave_read", "remnawave_execute"],
                ),
            ]
        ),
    )
    exact_identity = AsyncMock(return_value=42)
    monkeypatch.setattr(routes, "_partner_service_identity_numeric_user_id", exact_identity)

    assert (
        await routes._partner_drop_available(
            node_uuid=node_uuid,
            access=access,
            current_user=current_user,
            db=AsyncMock(),
        )
        is True
    )
    exact_identity.assert_awaited_once()

    access.permission_keys = frozenset({"remnawave_read"})
    assert (
        await routes._partner_drop_available(
            node_uuid=node_uuid,
            access=access,
            current_user=current_user,
            db=AsyncMock(),
        )
        is False
    )


@pytest.mark.unit
async def test_partner_drop_capability_rejects_non_executable_or_unmapped_grants(monkeypatch) -> None:
    workspace_id = uuid4()
    node_uuid = uuid4()
    identity_uuid = uuid4()
    access = SimpleNamespace(
        workspace=SimpleNamespace(id=workspace_id, status="active"),
        permission_keys=frozenset({"remnawave_read", "remnawave_execute"}),
        is_internal_admin_override=False,
    )
    current_user = SimpleNamespace(totp_enabled=True)
    monkeypatch.setattr(settings, "remnawave_connection_drop_hmac_secret", SecretStr("x" * 32))
    monkeypatch.setattr(routes, "enforce_partner_workspace_permission", AsyncMock())
    grants = AsyncMock(
        return_value=[
            SimpleNamespace(
                resource_type="node",
                resource_uuid=node_uuid,
                permission_keys=["remnawave_read"],
            ),
            SimpleNamespace(
                resource_type="service_identity",
                resource_uuid=identity_uuid,
                permission_keys=["remnawave_read", "remnawave_execute"],
            ),
        ]
    )
    monkeypatch.setattr(routes, "load_readable_partner_remnawave_grants", grants)
    exact_identity = AsyncMock(return_value=42)
    monkeypatch.setattr(routes, "_partner_service_identity_numeric_user_id", exact_identity)

    assert (
        await routes._partner_drop_available(
            node_uuid=node_uuid,
            access=access,
            current_user=current_user,
            db=AsyncMock(),
        )
        is False
    )
    exact_identity.assert_not_awaited()

    grants.return_value[0].permission_keys.append("remnawave_execute")
    exact_identity.side_effect = HTTPException(status_code=404, detail="Remnawave resource not found")
    assert (
        await routes._partner_drop_available(
            node_uuid=node_uuid,
            access=access,
            current_user=current_user,
            db=AsyncMock(),
        )
        is False
    )


@pytest.mark.unit
@pytest.mark.parametrize("workspace_status", ["suspended", "rejected", "terminated"])
async def test_partner_drop_capability_rejects_frozen_workspace(
    monkeypatch,
    workspace_status: str,
) -> None:
    access = SimpleNamespace(
        workspace=SimpleNamespace(id=uuid4(), status=workspace_status),
        permission_keys=frozenset({"remnawave_read", "remnawave_execute"}),
        is_internal_admin_override=False,
    )
    grants = AsyncMock()
    monkeypatch.setattr(settings, "remnawave_connection_drop_hmac_secret", SecretStr("x" * 32))
    monkeypatch.setattr(routes, "load_readable_partner_remnawave_grants", grants)

    assert (
        await routes._partner_drop_available(
            node_uuid=uuid4(),
            access=access,
            current_user=SimpleNamespace(totp_enabled=True),
            db=AsyncMock(),
        )
        is False
    )
    grants.assert_not_awaited()


@pytest.mark.unit
async def test_partner_drop_capability_rejects_workspace_mfa_requirement(monkeypatch) -> None:
    access = SimpleNamespace(
        workspace=SimpleNamespace(id=uuid4(), status="active"),
        permission_keys=frozenset({"remnawave_read", "remnawave_execute"}),
        is_internal_admin_override=False,
    )
    db = AsyncMock()
    db.execute.return_value = SimpleNamespace(
        scalar_one_or_none=lambda: SimpleNamespace(require_mfa_for_workspace=True)
    )
    grants = AsyncMock()
    monkeypatch.setattr(settings, "remnawave_connection_drop_hmac_secret", SecretStr("x" * 32))
    monkeypatch.setattr(routes, "load_readable_partner_remnawave_grants", grants)

    assert (
        await routes._partner_drop_available(
            node_uuid=uuid4(),
            access=access,
            current_user=SimpleNamespace(totp_enabled=False),
            db=db,
        )
        is False
    )
    grants.assert_not_awaited()


@pytest.mark.unit
def test_customer_drop_capability_tracks_receipt_runtime_configuration(monkeypatch) -> None:
    monkeypatch.setattr(settings, "remnawave_connection_drop_hmac_secret", SecretStr(""))
    unavailable = routes._connections_capabilities(drop_connections=routes._drop_receipt_runtime_available())

    monkeypatch.setattr(settings, "remnawave_connection_drop_hmac_secret", SecretStr("x" * 32))
    available = routes._connections_capabilities(drop_connections=routes._drop_receipt_runtime_available())

    assert unavailable.drop_connections is False
    assert available.drop_connections is True
