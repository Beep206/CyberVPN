from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from src.config.settings import settings
from src.infrastructure.database.models.partner_model import PartnerAccountModel
from src.presentation.api.v1.remnawave_status import routes
from src.presentation.dependencies.partner_workspace import PartnerWorkspaceAccess


@pytest.mark.unit
def test_admin_connections_capability_requires_exact_343_panel() -> None:
    assert routes._build_admin_capabilities(panel_version="3.4.3", node_ssh_available=False).connections is True
    assert routes._build_admin_capabilities(panel_version="3.4.1", node_ssh_available=True).connections is False
    assert routes._build_admin_capabilities(panel_version=None, node_ssh_available=True).connections is False


@pytest.mark.unit
async def test_partner_live_connections_capability_is_independent_of_stream_export(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    workspace_id = uuid4()
    monkeypatch.setattr(settings, "remnawave_stream_ingestion_enabled", False)
    monkeypatch.setattr(
        routes,
        "load_readable_partner_remnawave_grants",
        AsyncMock(return_value=[SimpleNamespace(resource_type="node", resource_uuid=uuid4())]),
    )

    response = await routes.get_partner_vpn_service_status(
        workspace_id=workspace_id,
        access=PartnerWorkspaceAccess(
            workspace=PartnerAccountModel(id=workspace_id),
            membership=None,
            role=None,
            permission_keys=frozenset(),
            is_internal_admin_override=False,
        ),
        db=AsyncMock(),
        client=AsyncMock(get=AsyncMock(return_value={"version": "3.4.3"})),
    )

    assert response.capabilities.connections is True
    assert response.capabilities.usage is False
    assert response.capabilities.devices is False
    assert response.degraded is False


@pytest.mark.unit
async def test_customer_live_connections_capability_requires_exact_active_mapping(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    customer_id = uuid4()
    db = AsyncMock()
    customer = SimpleNamespace(
        id=customer_id,
        remnawave_user_id=42,
        remnawave_uuid=None,
        is_active=True,
        status="active",
    )
    db.get.return_value = customer
    exact_resolver = AsyncMock(return_value=SimpleNamespace(id=42))
    monkeypatch.setattr(routes, "resolve_exact_mapped_mobile_user_ref", exact_resolver)
    monkeypatch.setattr(settings, "remnawave_stream_ingestion_enabled", False)

    response = await routes.get_customer_vpn_service_status(
        customer_account_id=customer_id,
        db=db,
        client=AsyncMock(get=AsyncMock(return_value={"version": "3.4.3"})),
    )

    exact_resolver.assert_awaited_once_with(db, customer)
    assert response.connections_available is True
    assert response.usage_available is True
    assert response.degraded is False
