from datetime import UTC, datetime
from unittest.mock import ANY, AsyncMock
from uuid import uuid4

import pytest

from src.infrastructure.remnawave.server_gateway import RemnawaveServerGateway


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
        "name": "fra-01",
        "address": "10.0.0.1",
        "port": 443,
        "isConnected": True,
        "isDisabled": False,
        "isConnecting": False,
        "createdAt": now,
        "updatedAt": now,
        "countryCode": "DE",
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


@pytest.mark.unit
async def test_create_uses_post_validated():
    client = AsyncMock()
    client.post_validated.return_value = _ValidatedModel(_server_payload(name="ams-01"))

    gateway = RemnawaveServerGateway(client)

    server = await gateway.create(name="ams-01", address="10.0.0.2", port=8443)

    client.post_validated.assert_awaited_once()
    _, kwargs = client.post_validated.await_args
    assert kwargs["json"]["name"] == "ams-01"
    assert server.name == "ams-01"


@pytest.mark.unit
async def test_update_uses_put_validated():
    client = AsyncMock()
    server_uuid = uuid4()
    client.put_validated.return_value = _ValidatedModel(_server_payload(uuid=str(server_uuid), port=9443))

    gateway = RemnawaveServerGateway(client)

    server = await gateway.update(server_uuid, port=9443)

    client.put_validated.assert_awaited_once()
    assert server.port == 9443


@pytest.mark.unit
async def test_delete_uses_validated_delete():
    client = AsyncMock()
    server_uuid = uuid4()
    gateway = RemnawaveServerGateway(client)

    await gateway.delete(server_uuid)

    client.delete_validated.assert_awaited_once_with(f"/api/nodes/{server_uuid}", ANY)
