from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import ANY, AsyncMock
from uuid import uuid4

import pytest

from src.config.settings import settings
from src.infrastructure.remnawave.user_gateway import RemnawaveUserGateway


class _ValidatedModel:
    def __init__(self, payload: dict):
        self._payload = payload

    def model_dump(self, *, by_alias: bool, mode: str) -> dict:
        assert by_alias is True
        assert mode == "json"
        return self._payload


@pytest.mark.unit
async def test_create_assigns_default_squad_by_name(monkeypatch):
    client = AsyncMock()
    client.get_collection_validated.return_value = [
        SimpleNamespace(uuid=str(uuid4()), name="Other-Squad"),
        SimpleNamespace(uuid=str(uuid4()), name="Default-Squad"),
    ]
    client.post_validated.return_value = _ValidatedModel({"uuid": str(uuid4()), "username": "demo-user"})

    monkeypatch.setattr(
        "src.infrastructure.remnawave.user_gateway.map_remnawave_user",
        lambda data: SimpleNamespace(uuid=data["uuid"], username=data["username"]),
    )
    monkeypatch.setattr(settings, "remnawave_default_internal_squad_uuid", "")
    monkeypatch.setattr(settings, "remnawave_default_internal_squad_name", "Default-Squad")

    gateway = RemnawaveUserGateway(client)

    await gateway.create(username="demo-user", email="demo@example.com")

    client.get_collection_validated.assert_awaited_once()
    _, kwargs = client.post_validated.await_args
    assert kwargs["json"]["activeInternalSquads"] == [
        client.get_collection_validated.return_value[1].uuid
    ]


@pytest.mark.unit
async def test_create_uses_configured_default_squad_uuid_without_lookup(monkeypatch):
    client = AsyncMock()
    client.post_validated.return_value = _ValidatedModel({"uuid": str(uuid4()), "username": "demo-user"})

    monkeypatch.setattr(
        "src.infrastructure.remnawave.user_gateway.map_remnawave_user",
        lambda data: SimpleNamespace(uuid=data["uuid"], username=data["username"]),
    )
    monkeypatch.setattr(settings, "remnawave_default_internal_squad_uuid", str(uuid4()))

    gateway = RemnawaveUserGateway(client)

    await gateway.create(username="demo-user", email="demo@example.com")

    client.get_collection_validated.assert_not_called()
    _, kwargs = client.post_validated.await_args
    assert kwargs["json"]["activeInternalSquads"] == [settings.remnawave_default_internal_squad_uuid]


@pytest.mark.unit
async def test_create_preserves_explicit_active_internal_squads(monkeypatch):
    client = AsyncMock()
    client.post_validated.return_value = _ValidatedModel({"uuid": str(uuid4()), "username": "demo-user"})
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

    client.get_collection_validated.assert_not_called()
    _, kwargs = client.post_validated.await_args
    assert kwargs["json"]["activeInternalSquads"] == [explicit_squad_uuid]


@pytest.mark.unit
async def test_create_normalizes_payload_and_sets_default_expire_at(monkeypatch):
    client = AsyncMock()
    client.get_collection_validated.return_value = [SimpleNamespace(uuid=str(uuid4()), name="Default-Squad")]
    client.post_validated.return_value = _ValidatedModel({"uuid": str(uuid4()), "username": "demo-user"})

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

    _, kwargs = client.post_validated.await_args
    assert kwargs["json"]["telegramId"] == 123
    assert kwargs["json"]["trafficLimitBytes"] == 2048
    assert kwargs["json"]["expireAt"] == "2026-04-08T12:00:00Z"
    assert "password" not in kwargs["json"]


@pytest.mark.unit
async def test_update_uses_patch_and_normalizes_payload(monkeypatch):
    client = AsyncMock()
    client.patch_validated.return_value = _ValidatedModel({"uuid": str(uuid4()), "username": "demo-user"})

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

    client.patch_validated.assert_awaited_once()
    _, kwargs = client.patch_validated.await_args
    assert kwargs["json"]["uuid"] == str(user_uuid)
    assert kwargs["json"]["telegramId"] == 777
    assert "activeInternalSquads" in kwargs["json"]
    assert "password" not in kwargs["json"]


@pytest.mark.unit
async def test_get_all_uses_validated_collection(monkeypatch):
    client = AsyncMock()
    now = datetime(2026, 4, 12, 12, 0, tzinfo=UTC).isoformat()
    client.get_collection_validated.return_value = [
        _ValidatedModel(
            {
                "uuid": str(uuid4()),
                "username": "demo-user",
                "status": "active",
                "shortUuid": "short",
                "createdAt": now,
                "updatedAt": now,
            }
        )
    ]

    monkeypatch.setattr(
        "src.infrastructure.remnawave.user_gateway.map_remnawave_user",
        lambda data: SimpleNamespace(uuid=data["uuid"], username=data["username"]),
    )

    gateway = RemnawaveUserGateway(client)

    users = await gateway.get_all(offset=5, limit=10)

    client.get_collection_validated.assert_awaited_once_with(
        "/api/users",
        "users",
        ANY,
        params={"start": 5, "size": 10},
    )
    assert [user.username for user in users] == ["demo-user"]


@pytest.mark.unit
async def test_delete_uses_validated_delete():
    client = AsyncMock()
    gateway = RemnawaveUserGateway(client)
    user_uuid = uuid4()

    await gateway.delete(user_uuid)

    client.delete_validated.assert_awaited_once_with(f"/api/users/{user_uuid}", ANY)
