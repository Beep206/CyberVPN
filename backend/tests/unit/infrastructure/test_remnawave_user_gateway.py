from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from src.config.settings import settings
from src.infrastructure.remnawave.user_gateway import RemnawaveUserGateway


@pytest.mark.unit
async def test_create_assigns_default_squad_by_name(monkeypatch):
    client = AsyncMock()
    client.get.return_value = {
        "total": 2,
        "internalSquads": [
            {"uuid": str(uuid4()), "name": "Other-Squad"},
            {"uuid": str(uuid4()), "name": "Default-Squad"},
        ],
    }
    client.post.return_value = {"uuid": str(uuid4()), "username": "demo-user"}

    monkeypatch.setattr(
        "src.infrastructure.remnawave.user_gateway.map_remnawave_user",
        lambda data: SimpleNamespace(uuid=data["uuid"], username=data["username"]),
    )
    monkeypatch.setattr(settings, "remnawave_default_internal_squad_uuid", "")
    monkeypatch.setattr(settings, "remnawave_default_internal_squad_name", "Default-Squad")

    gateway = RemnawaveUserGateway(client)

    await gateway.create(username="demo-user", email="demo@example.com")

    client.get.assert_awaited_once_with("/internal-squads")
    _, kwargs = client.post.await_args
    assert kwargs["json"]["activeInternalSquads"] == [
        client.get.return_value["internalSquads"][1]["uuid"]
    ]


@pytest.mark.unit
async def test_create_uses_configured_default_squad_uuid_without_lookup(monkeypatch):
    client = AsyncMock()
    client.post.return_value = {"uuid": str(uuid4()), "username": "demo-user"}

    monkeypatch.setattr(
        "src.infrastructure.remnawave.user_gateway.map_remnawave_user",
        lambda data: SimpleNamespace(uuid=data["uuid"], username=data["username"]),
    )
    monkeypatch.setattr(settings, "remnawave_default_internal_squad_uuid", str(uuid4()))

    gateway = RemnawaveUserGateway(client)

    await gateway.create(username="demo-user", email="demo@example.com")

    client.get.assert_not_called()
    _, kwargs = client.post.await_args
    assert kwargs["json"]["activeInternalSquads"] == [settings.remnawave_default_internal_squad_uuid]


@pytest.mark.unit
async def test_create_preserves_explicit_active_internal_squads(monkeypatch):
    client = AsyncMock()
    client.post.return_value = {"uuid": str(uuid4()), "username": "demo-user"}
    explicit_squad_uuid = str(uuid4())

    monkeypatch.setattr(
        "src.infrastructure.remnawave.user_gateway.map_remnawave_user",
        lambda data: SimpleNamespace(uuid=data["uuid"], username=data["username"]),
    )
    monkeypatch.setattr(settings, "remnawave_default_internal_squad_uuid", "")
    monkeypatch.setattr(settings, "remnawave_default_internal_squad_name", "Default-Squad")

    gateway = RemnawaveUserGateway(client)

    await gateway.create(
        username="demo-user",
        email="demo@example.com",
        activeInternalSquads=[explicit_squad_uuid],
    )

    client.get.assert_not_called()
    _, kwargs = client.post.await_args
    assert kwargs["json"]["activeInternalSquads"] == [explicit_squad_uuid]


@pytest.mark.unit
async def test_create_normalizes_payload_and_sets_default_expire_at(monkeypatch):
    client = AsyncMock()
    client.get.return_value = {"total": 1, "internalSquads": [{"uuid": str(uuid4()), "name": "Default-Squad"}]}
    client.post.return_value = {"uuid": str(uuid4()), "username": "demo-user"}

    monkeypatch.setattr(
        "src.infrastructure.remnawave.user_gateway.map_remnawave_user",
        lambda data: SimpleNamespace(uuid=data["uuid"], username=data["username"]),
    )
    monkeypatch.setattr(settings, "remnawave_default_internal_squad_uuid", "")
    monkeypatch.setattr(settings, "remnawave_default_internal_squad_name", "Default-Squad")
    monkeypatch.setattr(settings, "remnawave_default_user_expire_days", 7)

    gateway = RemnawaveUserGateway(client)

    await gateway.create(
        username="demo-user",
        email="demo@example.com",
        telegram_id=123,
        expire_at=datetime(2026, 4, 8, 12, 0, tzinfo=UTC),
        data_limit=2048,
        password="ignored-local-password",
    )

    _, kwargs = client.post.await_args
    assert kwargs["json"]["telegramId"] == 123
    assert kwargs["json"]["trafficLimitBytes"] == 2048
    assert kwargs["json"]["expireAt"] == "2026-04-08T12:00:00Z"
    assert "password" not in kwargs["json"]


@pytest.mark.unit
async def test_update_uses_patch_and_normalizes_payload(monkeypatch):
    client = AsyncMock()
    client.patch.return_value = {"uuid": str(uuid4()), "username": "demo-user"}

    monkeypatch.setattr(
        "src.infrastructure.remnawave.user_gateway.map_remnawave_user",
        lambda data: SimpleNamespace(uuid=data["uuid"], username=data["username"]),
    )

    gateway = RemnawaveUserGateway(client)
    user_uuid = uuid4()

    await gateway.update(
        user_uuid,
        email="updated@example.com",
        telegram_id=777,
        active_internal_squads=[str(uuid4())],
        password="ignored-local-password",
    )

    client.patch.assert_awaited_once()
    _, kwargs = client.patch.await_args
    assert kwargs["json"]["uuid"] == str(user_uuid)
    assert kwargs["json"]["telegramId"] == 777
    assert "activeInternalSquads" in kwargs["json"]
    assert "password" not in kwargs["json"]
