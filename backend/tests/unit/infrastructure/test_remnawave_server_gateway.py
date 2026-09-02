from datetime import UTC, datetime
from unittest.mock import ANY, AsyncMock
from uuid import UUID, uuid4

import pytest

from src.infrastructure.remnawave.client import (
    RemnawaveHTTPStatusError,
    RemnawaveProtocolError,
    RemnawaveTransportError,
)
from src.infrastructure.remnawave.contracts import RemnawaveNodeResponse
from src.infrastructure.remnawave.mappers.server_mapper import map_remnawave_server
from src.infrastructure.remnawave.server_gateway import (
    RemnawaveNodeCreateSafetyDisabled,
    RemnawaveNodeMutationAcceptedPending,
    RemnawaveServerGateway,
)


class _ValidatedModel:
    def __init__(self, payload: dict):
        self._payload = payload

    def model_dump(self, *, by_alias: bool, mode: str) -> dict:
        assert by_alias is True
        assert mode == "json"
        return self._payload


def _server_payload(**overrides) -> dict:
    now = datetime(2026, 4, 12, 12, 0, tzinfo=UTC).isoformat()
    payload = {
        "uuid": str(uuid4()),
        "id": 73,
        "name": "fra-01",
        "address": "10.0.0.1",
        "port": 443,
        "isConnected": True,
        "isDisabled": False,
        "isConnecting": False,
        "createdAt": now,
        "updatedAt": now,
        "countryCode": "DE",
        "ips": [{"ip": "203.0.113.8", "status": "INBOUND"}],
        "integrationUuids": [str(uuid4())],
    }
    payload.update(overrides)
    return payload


@pytest.mark.unit
async def test_get_all_uses_validated_collection():
    client = AsyncMock()
    client.get_collection_validated.return_value = [
        _ValidatedModel(
            _server_payload(
                xrayVersion="1.8.10",
                nodeVersion="2.7.4",
                activePluginUuid=str(uuid4()),
            )
        )
    ]

    gateway = RemnawaveServerGateway(client)

    servers = await gateway.get_all()

    client.get_collection_validated.assert_awaited_once_with("/api/nodes", "nodes", ANY)
    assert len(servers) == 1
    assert servers[0].name == "fra-01"
    assert servers[0].xray_version == "1.8.10"
    assert servers[0].node_version == "2.7.4"
    assert servers[0].id == 73
    assert servers[0].ips[0].ip == "203.0.113.8"
    assert len(servers[0].integration_uuids) == 1


@pytest.mark.unit
def test_target_3_4_node_identity_ips_integrations_and_nullable_port_are_preserved():
    payload = _server_payload(port=None)

    validated = RemnawaveNodeResponse.model_validate(payload)
    mapped = map_remnawave_server(validated.model_dump(by_alias=True, mode="json"))

    assert mapped.id == 73
    assert mapped.port is None
    assert mapped.ips[0].ip == "203.0.113.8"
    assert mapped.ips[0].status == "INBOUND"
    assert mapped.integration_uuids == (UUID(payload["integrationUuids"][0]),)


@pytest.mark.unit
async def test_create_is_safety_disabled_before_provider_io():
    client = AsyncMock()
    gateway = RemnawaveServerGateway(client)

    with pytest.raises(RemnawaveNodeCreateSafetyDisabled):
        await gateway.create(name="ams-01", address="10.0.0.2", port=8443)

    client.post_validated.assert_not_awaited()


@pytest.mark.unit
async def test_get_by_uuid_returns_none_only_for_exact_404():
    client = AsyncMock()
    client.get_validated.side_effect = RemnawaveHTTPStatusError(status_code=404)
    gateway = RemnawaveServerGateway(client)

    assert await gateway.get_by_uuid(uuid4()) is None


@pytest.mark.unit
async def test_get_by_uuid_propagates_protocol_failure():
    client = AsyncMock()
    client.get_validated.side_effect = RemnawaveProtocolError()
    gateway = RemnawaveServerGateway(client)

    with pytest.raises(RemnawaveProtocolError):
        await gateway.get_by_uuid(uuid4())


@pytest.mark.unit
async def test_update_uses_target_3_4_patch_collection_contract():
    client = AsyncMock()
    server_uuid = uuid4()
    client.patch_validated.return_value = _ValidatedModel(_server_payload(uuid=str(server_uuid), port=9443))

    gateway = RemnawaveServerGateway(client)

    server = await gateway.update(server_uuid, port=9443)

    client.patch_validated.assert_awaited_once_with(
        "/api/nodes",
        ANY,
        json={"uuid": str(server_uuid), "port": 9443},
    )
    assert server.port == 9443


@pytest.mark.unit
async def test_empty_update_ack_reconciles_once_by_immutable_uuid():
    client = AsyncMock()
    server_uuid = uuid4()
    client.patch_validated.return_value = None
    client.get_validated.return_value = _ValidatedModel(_server_payload(uuid=str(server_uuid), port=9443))
    gateway = RemnawaveServerGateway(client)

    server = await gateway.update(server_uuid, port=9443)

    assert server is not None
    assert server.uuid == server_uuid
    assert server.port == 9443
    client.patch_validated.assert_awaited_once()
    client.get_validated.assert_awaited_once_with(f"/api/nodes/{server_uuid}", ANY)


@pytest.mark.unit
async def test_update_transport_ambiguity_accepts_only_exact_readback():
    client = AsyncMock()
    server_uuid = uuid4()
    client.patch_validated.side_effect = RemnawaveTransportError()
    client.get_validated.return_value = _ValidatedModel(_server_payload(uuid=str(server_uuid), port=9444))
    gateway = RemnawaveServerGateway(client)

    with pytest.raises(RemnawaveNodeMutationAcceptedPending):
        await gateway.update(server_uuid, port=9443)

    client.patch_validated.assert_awaited_once_with(
        "/api/nodes",
        ANY,
        json={"uuid": str(server_uuid), "port": 9443},
    )
    client.get_validated.assert_awaited_once()


@pytest.mark.unit
async def test_update_empty_ack_propagates_readback_unavailability():
    client = AsyncMock()
    server_uuid = uuid4()
    client.patch_validated.return_value = None
    client.get_validated.side_effect = RemnawaveProtocolError()
    gateway = RemnawaveServerGateway(client)

    with pytest.raises(RemnawaveProtocolError):
        await gateway.update(server_uuid, port=9443)


@pytest.mark.unit
async def test_delete_uses_validated_delete():
    client = AsyncMock()
    server_uuid = uuid4()
    client.get_validated.side_effect = RemnawaveHTTPStatusError(status_code=404)
    gateway = RemnawaveServerGateway(client)

    await gateway.delete(server_uuid)

    client.delete_validated.assert_awaited_once_with(f"/api/nodes/{server_uuid}", ANY)
    client.get_validated.assert_awaited_once_with(f"/api/nodes/{server_uuid}", ANY)


@pytest.mark.unit
async def test_delete_transport_ambiguity_requires_authoritative_absence():
    client = AsyncMock()
    server_uuid = uuid4()
    client.delete_validated.side_effect = RemnawaveTransportError()
    client.get_validated.return_value = _ValidatedModel(_server_payload(uuid=str(server_uuid)))
    gateway = RemnawaveServerGateway(client)

    with pytest.raises(RemnawaveNodeMutationAcceptedPending):
        await gateway.delete(server_uuid)

    client.delete_validated.assert_awaited_once()
    client.get_validated.assert_awaited_once()
