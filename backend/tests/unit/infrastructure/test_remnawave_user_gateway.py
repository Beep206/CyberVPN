from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import ANY, AsyncMock
from uuid import UUID, uuid4

import httpx
import pytest

from src.config.settings import settings
from src.domain.enums import UserStatus
from src.domain.value_objects.remnawave_user_ref import RemnawaveUserRef
from src.infrastructure.remnawave.client import RemnawaveTransportError
from src.infrastructure.remnawave.user_gateway import (
    RemnawaveDefaultSquadResolutionError,
    RemnawaveIdentityBindingError,
    RemnawaveInventoryPaginationError,
    RemnawaveLegacyRollbackUserGateway,
    RemnawaveMutationAcceptedPending,
    RemnawavePasswordOnlyCredentialRotationSafetyDisabled,
    RemnawaveUserGateway,
)


class _ValidatedModel:
    def __init__(self, payload: dict):
        self._payload = payload

    def model_dump(self, *, by_alias: bool, mode: str) -> dict:
        assert by_alias is True
        assert mode == "json"
        return self._payload


def _echo_created_response(*_args, json: dict, **_kwargs) -> _ValidatedModel:
    response = dict(json)
    if isinstance(response.get("telegramId"), list):
        response["telegramId"] = response["telegramId"][0]
    return _ValidatedModel(
        {
            **response,
            "id": 42,
            "uuid": str(uuid4()),
            "status": "active",
        }
    )


def _mapped_user(data: dict):
    raw_uuid = data.get("uuid")
    raw_status = data.get("status", UserStatus.ACTIVE)
    raw_expire_at = data.get("expireAt")
    return SimpleNamespace(
        remnawave_id=data.get("id", 42),
        uuid=UUID(str(raw_uuid)) if raw_uuid else None,
        telegram_id=data.get("telegramId"),
        username=data.get("username", "demo-user"),
        status=raw_status if isinstance(raw_status, UserStatus) else UserStatus(str(raw_status)),
        email=data.get("email"),
        sub_revoked_at=data.get("subRevokedAt"),
        expire_at=(
            datetime.fromisoformat(str(raw_expire_at).replace("Z", "+00:00")) if raw_expire_at is not None else None
        ),
        traffic_limit_bytes=data.get("trafficLimitBytes"),
        hwid_device_limit=data.get("hwidDeviceLimit"),
        auto_renew=data.get("autoRenew"),
        traffic_limit_strategy=data.get("trafficLimitStrategy"),
        active_internal_squad_uuids=(
            tuple(
                str(item.get("uuid")) if isinstance(item, dict) else str(item) for item in data["activeInternalSquads"]
            )
            if "activeInternalSquads" in data
            else None
        ),
        external_squad_uuid=data.get("externalSquadUuid"),
        external_squad_uuid_observed="externalSquadUuid" in data,
    )


@pytest.mark.unit
async def test_create_assigns_default_squad_by_name(monkeypatch):
    client = AsyncMock()
    client.get_collection_validated.return_value = [
        SimpleNamespace(uuid=str(uuid4()), name="Other-Squad"),
        SimpleNamespace(uuid=str(uuid4()), name="Default-Squad"),
    ]
    client.post_validated.side_effect = _echo_created_response

    monkeypatch.setattr(
        "src.infrastructure.remnawave.user_gateway.map_remnawave_user",
        _mapped_user,
    )
    monkeypatch.setattr(settings, "remnawave_default_internal_squad_uuid", "")
    monkeypatch.setattr(settings, "remnawave_default_internal_squad_name", "Default-Squad")

    gateway = RemnawaveUserGateway(client)

    await gateway.create(username="demo-user", email="demo@example.com")

    client.get_collection_validated.assert_awaited_once()
    _, kwargs = client.post_validated.await_args
    assert kwargs["json"]["activeInternalSquads"] == [client.get_collection_validated.return_value[1].uuid]


@pytest.mark.unit
async def test_create_uses_configured_default_squad_uuid_without_lookup(monkeypatch):
    client = AsyncMock()
    client.post_validated.side_effect = _echo_created_response

    monkeypatch.setattr(
        "src.infrastructure.remnawave.user_gateway.map_remnawave_user",
        _mapped_user,
    )
    monkeypatch.setattr(settings, "remnawave_default_internal_squad_uuid", str(uuid4()))

    gateway = RemnawaveUserGateway(client)

    await gateway.create(username="demo-user", email="demo@example.com")

    client.get_collection_validated.assert_not_called()
    _, kwargs = client.post_validated.await_args
    assert kwargs["json"]["activeInternalSquads"] == [settings.remnawave_default_internal_squad_uuid]


@pytest.mark.unit
async def test_create_accepts_exact_numeric_only_3_4_identity_without_fabricating_uuid(monkeypatch):
    client = AsyncMock()

    def numeric_only_response(*_args, json: dict, **_kwargs) -> _ValidatedModel:
        return _ValidatedModel({**json, "id": 42, "status": "active"})

    client.post_validated.side_effect = numeric_only_response
    monkeypatch.setattr(settings, "remnawave_default_internal_squad_uuid", str(uuid4()))
    monkeypatch.setattr("src.infrastructure.remnawave.user_gateway.map_remnawave_user", _mapped_user)

    created = await RemnawaveUserGateway(client).create(
        username="numeric-only",
        email="numeric-only@example.com",
    )

    assert created.remnawave_id == 42
    assert created.uuid is None
    client.post_validated.assert_awaited_once()


@pytest.mark.unit
@pytest.mark.parametrize("invalid_numeric_id", [None, 0, -1, True, "42"])
async def test_create_rejects_missing_or_inexact_numeric_identity(monkeypatch, invalid_numeric_id):
    client = AsyncMock()
    client.post_validated.return_value = _ValidatedModel(
        {
            "id": invalid_numeric_id,
            "username": "numeric-only",
            "status": "active",
        }
    )
    monkeypatch.setattr(settings, "remnawave_default_internal_squad_uuid", str(uuid4()))
    monkeypatch.setattr("src.infrastructure.remnawave.user_gateway.map_remnawave_user", _mapped_user)

    with pytest.raises(RemnawaveIdentityBindingError, match="incomplete 3.x identity"):
        await RemnawaveUserGateway(client).create(username="numeric-only")


@pytest.mark.unit
@pytest.mark.parametrize("inventory_case", ["wrong_single", "missing", "ambiguous", "error"])
async def test_create_fails_before_post_without_one_exact_default_squad(monkeypatch, inventory_case: str):
    client = AsyncMock()
    configured_name = "CYBERVPN_PREMIUM_SMART_RU_NODES"
    if inventory_case == "wrong_single":
        client.get_collection_validated.return_value = [
            SimpleNamespace(uuid=str(uuid4()), name="RESTRICTED-OTHER-SQUAD")
        ]
    elif inventory_case == "missing":
        client.get_collection_validated.return_value = []
    elif inventory_case == "ambiguous":
        client.get_collection_validated.return_value = [
            SimpleNamespace(uuid=str(uuid4()), name=configured_name),
            SimpleNamespace(uuid=str(uuid4()), name=configured_name),
        ]
    else:
        client.get_collection_validated.side_effect = TimeoutError("inventory unavailable")
    monkeypatch.setattr(settings, "remnawave_default_internal_squad_uuid", "")
    monkeypatch.setattr(settings, "remnawave_default_internal_squad_name", configured_name)

    with pytest.raises(RemnawaveDefaultSquadResolutionError):
        await RemnawaveUserGateway(client).create(username="demo-user", email="demo@example.com")

    client.post_validated.assert_not_awaited()


@pytest.mark.unit
async def test_create_preserves_explicit_active_internal_squads(monkeypatch):
    client = AsyncMock()
    client.post_validated.side_effect = _echo_created_response
    explicit_squad_uuid = str(uuid4())

    monkeypatch.setattr(
        "src.infrastructure.remnawave.user_gateway.map_remnawave_user",
        _mapped_user,
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
    client.post_validated.side_effect = _echo_created_response

    monkeypatch.setattr(
        "src.infrastructure.remnawave.user_gateway.map_remnawave_user",
        _mapped_user,
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
        auto_renew=True,
        autoRenew=False,
        password="ignored-local-password",
    )

    _, kwargs = client.post_validated.await_args
    assert kwargs["json"]["telegramId"] == [123]
    assert kwargs["json"]["trafficLimitBytes"] == 2048
    assert kwargs["json"]["expireAt"] == "2026-04-08T12:00:00Z"
    assert "password" not in kwargs["json"]
    assert "auto_renew" not in kwargs["json"]
    assert "autoRenew" not in kwargs["json"]


@pytest.mark.unit
async def test_create_omits_null_traffic_limit_for_unlimited_users(monkeypatch):
    client = AsyncMock()
    client.get_collection_validated.return_value = [SimpleNamespace(uuid=str(uuid4()), name="Default-Squad")]
    client.post_validated.side_effect = _echo_created_response

    monkeypatch.setattr(
        "src.infrastructure.remnawave.user_gateway.map_remnawave_user",
        _mapped_user,
    )
    monkeypatch.setattr(settings, "remnawave_default_internal_squad_uuid", "")
    monkeypatch.setattr(settings, "remnawave_default_internal_squad_name", "Default-Squad")

    gateway = RemnawaveUserGateway(client)

    await gateway.create(username="demo-user", email="demo@example.com", traffic_limit_bytes=None)

    _, kwargs = client.post_validated.await_args
    assert "trafficLimitBytes" not in kwargs["json"]


@pytest.mark.unit
async def test_create_replaces_telegram_placeholder_email_for_remnawave(monkeypatch):
    client = AsyncMock()
    client.get_collection_validated.return_value = [SimpleNamespace(uuid=str(uuid4()), name="Default-Squad")]
    client.post_validated.side_effect = _echo_created_response

    monkeypatch.setattr(
        "src.infrastructure.remnawave.user_gateway.map_remnawave_user",
        _mapped_user,
    )
    monkeypatch.setattr(settings, "remnawave_default_internal_squad_uuid", "")
    monkeypatch.setattr(settings, "remnawave_default_internal_squad_name", "Default-Squad")

    gateway = RemnawaveUserGateway(client)

    await gateway.create(username="cvpn_t_demo", email="tg123456@telegram.local")

    _, kwargs = client.post_validated.await_args
    assert kwargs["json"]["email"] == "cvpn_t_demo@cyber-vpn.net"


@pytest.mark.unit
async def test_create_replaces_empty_email_for_remnawave(monkeypatch):
    client = AsyncMock()
    client.get_collection_validated.return_value = [SimpleNamespace(uuid=str(uuid4()), name="Default-Squad")]
    client.post_validated.side_effect = _echo_created_response

    monkeypatch.setattr(
        "src.infrastructure.remnawave.user_gateway.map_remnawave_user",
        _mapped_user,
    )
    monkeypatch.setattr(settings, "remnawave_default_internal_squad_uuid", "")
    monkeypatch.setattr(settings, "remnawave_default_internal_squad_name", "Default-Squad")

    gateway = RemnawaveUserGateway(client)

    await gateway.create(username="Sasha_Beep", email="", telegram_id=157383237)

    _, kwargs = client.post_validated.await_args
    assert kwargs["json"]["email"] == "sasha_beep@cyber-vpn.net"
    assert kwargs["json"]["telegramId"] == [157383237]


@pytest.mark.unit
@pytest.mark.parametrize(
    ("create_kwargs", "response_overrides"),
    [
        ({"email": "wanted@example.com"}, {"email": "wrong@example.com"}),
        (
            {"email": "wanted@example.com", "traffic_limit_bytes": 999},
            {"trafficLimitBytes": 1},
        ),
        (
            {"email": "wanted@example.com", "expire_at": datetime(2027, 1, 1, tzinfo=UTC)},
            {"expireAt": "2026-01-01T00:00:00Z"},
        ),
        (
            {"email": "wanted@example.com", "telegram_id": 777},
            {"telegramId": 778},
        ),
        (
            {"email": "wanted@example.com", "hwid_device_limit": 5},
            {"hwidDeviceLimit": 1},
        ),
    ],
)
async def test_create_rejects_stale_observable_fields_in_direct_response(
    monkeypatch,
    create_kwargs: dict,
    response_overrides: dict,
):
    client = AsyncMock()

    def stale_response(*_args, json: dict, **_kwargs) -> _ValidatedModel:
        return _ValidatedModel(
            {
                **json,
                "id": 42,
                "uuid": str(uuid4()),
                "status": "active",
                **response_overrides,
            }
        )

    client.post_validated.side_effect = stale_response
    monkeypatch.setattr(settings, "remnawave_default_internal_squad_uuid", str(uuid4()))
    monkeypatch.setattr("src.infrastructure.remnawave.user_gateway.map_remnawave_user", _mapped_user)

    with pytest.raises(RemnawaveMutationAcceptedPending) as exc_info:
        await RemnawaveUserGateway(client).create(username="demo-user", **create_kwargs)

    assert exc_info.value.operation == "create"
    assert exc_info.value.numeric_user_id == 42
    client.post_validated.assert_awaited_once()


@pytest.mark.unit
async def test_get_by_telegram_id_treats_empty_upstream_list_as_missing_user(monkeypatch):
    client = AsyncMock()
    client.get.return_value = []

    gateway = RemnawaveUserGateway(client)

    user = await gateway.get_by_telegram_id(123456789)

    assert user is None
    client.get.assert_awaited_once_with("/api/users/by-telegram-id/123456789")


@pytest.mark.unit
async def test_update_rejects_legacy_uuid_in_normal_3x_gateway(monkeypatch):
    client = AsyncMock()
    client.patch_validated.return_value = _ValidatedModel({"uuid": str(uuid4()), "username": "demo-user"})

    monkeypatch.setattr(
        "src.infrastructure.remnawave.user_gateway.map_remnawave_user",
        _mapped_user,
    )

    gateway = RemnawaveUserGateway(client)
    user_uuid = uuid4()

    with pytest.raises(ValueError, match="numeric user id"):
        await gateway.update(
            user_uuid,
            email="updated@example.com",
            telegram_id=777,
            active_internal_squads=[str(uuid4())],
            password="ignored-local-password",
        )

    client.patch_validated.assert_not_awaited()


@pytest.mark.unit
async def test_update_prefers_numeric_remnawave_user_id(monkeypatch):
    client = AsyncMock()
    legacy_uuid = uuid4()
    response = _ValidatedModel({"id": 42, "uuid": str(legacy_uuid), "username": "demo-user", "status": "disabled"})
    client.get_validated.return_value = response
    client.patch_validated.return_value = response
    monkeypatch.setattr(
        "src.infrastructure.remnawave.user_gateway.map_remnawave_user",
        _mapped_user,
    )

    gateway = RemnawaveUserGateway(client)
    await gateway.update(RemnawaveUserRef(id=42, legacy_uuid=legacy_uuid), status="disabled")

    _, kwargs = client.patch_validated.await_args
    assert kwargs["json"]["id"] == 42
    assert "uuid" not in kwargs["json"]
    assert kwargs["json"]["status"] == "DISABLED"


@pytest.mark.unit
@pytest.mark.parametrize(
    ("update_kwargs", "response_overrides"),
    [
        ({"email": "wanted@example.com"}, {"email": "wrong@example.com"}),
        ({"traffic_limit_bytes": 999}, {"trafficLimitBytes": 1}),
        ({"telegram_id": 777}, {"telegramId": 778}),
        ({"hwid_device_limit": 5}, {"hwidDeviceLimit": 1}),
        (
            {"expire_at": datetime(2027, 1, 1, tzinfo=UTC)},
            {"expireAt": "2026-01-01T00:00:00Z"},
        ),
    ],
)
async def test_update_rejects_stale_observable_fields_in_direct_response(
    monkeypatch,
    update_kwargs: dict,
    response_overrides: dict,
):
    client = AsyncMock()
    legacy_uuid = uuid4()
    response = _ValidatedModel(
        {
            "id": 42,
            "uuid": str(legacy_uuid),
            "username": "demo-user",
            "status": "active",
            **response_overrides,
        }
    )
    client.get_validated.return_value = response
    client.patch_validated.return_value = response
    monkeypatch.setattr("src.infrastructure.remnawave.user_gateway.map_remnawave_user", _mapped_user)

    with pytest.raises(RemnawaveMutationAcceptedPending) as exc_info:
        await RemnawaveUserGateway(client).update(
            RemnawaveUserRef(id=42, legacy_uuid=legacy_uuid),
            **update_kwargs,
        )

    assert exc_info.value.operation == "update"
    assert exc_info.value.numeric_user_id == 42
    client.patch_validated.assert_awaited_once()


@pytest.mark.unit
async def test_update_rejects_direct_response_that_omits_requested_relationship_assignment(monkeypatch):
    client = AsyncMock()
    legacy_uuid = uuid4()
    response = _ValidatedModel(
        {
            "id": 42,
            "uuid": str(legacy_uuid),
            "username": "demo-user",
            "status": "active",
            "email": "wanted@example.com",
            "expireAt": "2027-01-01T00:00:00Z",
            "trafficLimitBytes": 999,
        }
    )
    client.get_validated.return_value = response
    client.patch_validated.return_value = response
    monkeypatch.setattr("src.infrastructure.remnawave.user_gateway.map_remnawave_user", _mapped_user)

    with pytest.raises(RemnawaveMutationAcceptedPending):
        await RemnawaveUserGateway(client).update(
            RemnawaveUserRef(id=42, legacy_uuid=legacy_uuid),
            email="wanted@example.com",
            expire_at=datetime(2027, 1, 1, tzinfo=UTC),
            traffic_limit_bytes=999,
            trafficLimitStrategy="NO_RESET",
        )


@pytest.mark.unit
async def test_update_accepts_exact_relationship_assignment_with_expanded_squads(monkeypatch):
    client = AsyncMock()
    legacy_uuid = uuid4()
    squad_a = str(uuid4())
    squad_b = str(uuid4())
    response = _ValidatedModel(
        {
            "id": 42,
            "uuid": str(legacy_uuid),
            "username": "demo-user",
            "status": "active",
            "trafficLimitStrategy": "NO_RESET",
            "activeInternalSquads": [{"uuid": squad_b}, {"uuid": squad_a}],
            "externalSquadUuid": None,
        }
    )
    client.get_validated.return_value = response
    client.patch_validated.return_value = response
    monkeypatch.setattr("src.infrastructure.remnawave.user_gateway.map_remnawave_user", _mapped_user)

    result = await RemnawaveUserGateway(client).update(
        RemnawaveUserRef(id=42, legacy_uuid=legacy_uuid),
        trafficLimitStrategy="NO_RESET",
        activeInternalSquads=[squad_a, squad_b],
        externalSquadUuid=None,
    )

    assert set(result.active_internal_squad_uuids) == {squad_a, squad_b}


@pytest.mark.unit
@pytest.mark.parametrize(
    ("requested", "response"),
    [
        ({"trafficLimitStrategy": "NO_RESET"}, {"trafficLimitStrategy": "MONTH"}),
        ({"activeInternalSquads": ["wanted"]}, {"activeInternalSquads": [{"uuid": "stale"}]}),
        ({"externalSquadUuid": "wanted"}, {"externalSquadUuid": "stale"}),
        ({"externalSquadUuid": None}, {}),
    ],
)
async def test_update_rejects_stale_or_missing_relationship_postcondition(monkeypatch, requested, response):
    client = AsyncMock()
    legacy_uuid = uuid4()
    payload = {
        "id": 42,
        "uuid": str(legacy_uuid),
        "username": "demo-user",
        "status": "active",
        **response,
    }
    validated = _ValidatedModel(payload)
    client.get_validated.return_value = validated
    client.patch_validated.return_value = validated
    monkeypatch.setattr("src.infrastructure.remnawave.user_gateway.map_remnawave_user", _mapped_user)

    with pytest.raises(RemnawaveMutationAcceptedPending):
        await RemnawaveUserGateway(client).update(
            RemnawaveUserRef(id=42, legacy_uuid=legacy_uuid),
            **requested,
        )


@pytest.mark.unit
async def test_update_caller_cannot_override_canonical_numeric_identity(monkeypatch):
    client = AsyncMock()
    legacy_uuid = uuid4()
    response = _ValidatedModel({"id": 42, "uuid": str(legacy_uuid), "username": "demo-user", "status": "disabled"})
    client.get_validated.return_value = response
    client.patch_validated.return_value = response
    monkeypatch.setattr(
        "src.infrastructure.remnawave.user_gateway.map_remnawave_user",
        _mapped_user,
    )

    gateway = RemnawaveUserGateway(client)
    await gateway.update(
        RemnawaveUserRef(id=42, legacy_uuid=legacy_uuid),
        id=99,
        uuid=str(uuid4()),
        status="disabled",
    )

    _, kwargs = client.patch_validated.await_args
    assert kwargs["json"]["id"] == 42
    assert "uuid" not in kwargs["json"]


@pytest.mark.unit
async def test_get_by_ref_uses_numeric_route_when_mapping_is_reconciled(monkeypatch):
    client = AsyncMock()
    legacy_uuid = uuid4()
    client.get_validated.return_value = _ValidatedModel({"id": 42, "uuid": str(legacy_uuid), "username": "demo-user"})
    monkeypatch.setattr(
        "src.infrastructure.remnawave.user_gateway.map_remnawave_user",
        _mapped_user,
    )

    gateway = RemnawaveUserGateway(client)
    await gateway.get_by_ref(RemnawaveUserRef(id=42, legacy_uuid=legacy_uuid))

    client.get_validated.assert_awaited_once_with("/api/users/42", ANY)


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
        _mapped_user,
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
async def test_get_all_cursor_rejects_non_advancing_cursor(monkeypatch):
    client = AsyncMock()
    client.get_all_users_cursor_page.return_value = SimpleNamespace(
        items=[{"id": 42, "username": "demo-user"}],
        next_cursor="cursor-a",
        has_next_page=True,
    )
    monkeypatch.setattr("src.infrastructure.remnawave.user_gateway.map_remnawave_user", _mapped_user)

    with pytest.raises(RemnawaveInventoryPaginationError, match="did not advance"):
        await RemnawaveUserGateway(client).get_all_cursor(cursor="cursor-a", limit=100)

    client.get_all_users_cursor_page.assert_awaited_once_with(cursor="cursor-a", limit=100)


@pytest.mark.unit
async def test_get_all_cursor_rejects_repeated_cursor_cycle(monkeypatch):
    client = AsyncMock()
    client.get_all_users_cursor_page.side_effect = [
        SimpleNamespace(items=[{"id": 42}], next_cursor="cursor-a", has_next_page=True),
        SimpleNamespace(items=[{"id": 43}], next_cursor="cursor-b", has_next_page=True),
        SimpleNamespace(items=[{"id": 44}], next_cursor="cursor-a", has_next_page=True),
    ]
    monkeypatch.setattr("src.infrastructure.remnawave.user_gateway.map_remnawave_user", _mapped_user)

    with pytest.raises(RemnawaveInventoryPaginationError, match="did not advance"):
        await RemnawaveUserGateway(client).get_all_cursor(limit=100)

    assert client.get_all_users_cursor_page.await_count == 3


@pytest.mark.unit
async def test_get_all_cursor_rejects_continuation_without_unique_progress(monkeypatch):
    client = AsyncMock()
    client.get_all_users_cursor_page.side_effect = [
        SimpleNamespace(items=[{"id": 42}], next_cursor="cursor-a", has_next_page=True),
        SimpleNamespace(items=[{"id": 42}], next_cursor="cursor-b", has_next_page=True),
    ]
    monkeypatch.setattr("src.infrastructure.remnawave.user_gateway.map_remnawave_user", _mapped_user)

    with pytest.raises(RemnawaveInventoryPaginationError, match="no unique progress"):
        await RemnawaveUserGateway(client).get_all_cursor(limit=100)

    assert client.get_all_users_cursor_page.await_count == 2


@pytest.mark.unit
async def test_delete_rejects_legacy_uuid_in_normal_3x_gateway():
    client = AsyncMock()
    gateway = RemnawaveUserGateway(client)
    user_uuid = uuid4()

    with pytest.raises(ValueError, match="numeric user id"):
        await gateway.delete(user_uuid)

    client.delete_validated.assert_not_awaited()


@pytest.mark.unit
async def test_delete_uses_numeric_id_from_dual_reference(monkeypatch):
    client = AsyncMock()
    legacy_uuid = uuid4()
    request = httpx.Request("GET", "https://remnawave.test/api/users/73")
    client.get_validated.side_effect = [
        _ValidatedModel({"id": 73, "uuid": str(legacy_uuid), "username": "demo-user"}),
        httpx.HTTPStatusError(
            "missing",
            request=request,
            response=httpx.Response(404, request=request),
        ),
    ]
    monkeypatch.setattr("src.infrastructure.remnawave.user_gateway.map_remnawave_user", _mapped_user)
    gateway = RemnawaveUserGateway(client)

    await gateway.delete(RemnawaveUserRef(id=73, legacy_uuid=legacy_uuid))

    client.delete_validated.assert_awaited_once_with("/api/users/73", ANY)


@pytest.mark.unit
async def test_delete_accepted_but_still_present_is_pending(monkeypatch):
    client = AsyncMock()
    legacy_uuid = uuid4()
    client.get_validated.return_value = _ValidatedModel(
        {"id": 73, "uuid": str(legacy_uuid), "username": "still-active"}
    )
    client.delete_validated.return_value = None
    monkeypatch.setattr("src.infrastructure.remnawave.user_gateway.map_remnawave_user", _mapped_user)

    with pytest.raises(RemnawaveMutationAcceptedPending) as exc_info:
        await RemnawaveUserGateway(client).delete(RemnawaveUserRef(id=73, legacy_uuid=legacy_uuid))

    assert exc_info.value.operation == "delete"
    assert exc_info.value.numeric_user_id == 73
    client.delete_validated.assert_awaited_once()
    assert client.get_validated.await_count == 2


@pytest.mark.unit
async def test_explicit_rollback_adapter_is_the_only_uuid_mutation_path():
    client = AsyncMock()
    legacy_uuid = uuid4()

    await RemnawaveLegacyRollbackUserGateway(client).delete_by_uuid(legacy_uuid)

    client.delete_validated.assert_awaited_once_with(f"/api/users/{legacy_uuid}", ANY)


@pytest.mark.unit
async def test_confirm_absent_by_numeric_id_distinguishes_404_from_existing_user(monkeypatch):
    client = AsyncMock()
    request = httpx.Request("GET", "https://remnawave.test/api/users/73")
    client.get_validated.side_effect = httpx.HTTPStatusError(
        "missing",
        request=request,
        response=httpx.Response(404, request=request),
    )
    gateway = RemnawaveUserGateway(client)
    monkeypatch.setattr("src.infrastructure.remnawave.user_gateway.map_remnawave_user", _mapped_user)

    assert await gateway.confirm_absent_by_id(73) is True

    client.get_validated.side_effect = None
    client.get_validated.return_value = _ValidatedModel({"id": 73, "username": "still-active"})
    assert await gateway.confirm_absent_by_id(73) is False


@pytest.mark.unit
async def test_get_by_id_rejects_wrong_upstream_numeric_identity(monkeypatch):
    client = AsyncMock()
    client.get_validated.return_value = _ValidatedModel({"id": 74, "uuid": str(uuid4())})
    monkeypatch.setattr("src.infrastructure.remnawave.user_gateway.map_remnawave_user", _mapped_user)

    with pytest.raises(RemnawaveIdentityBindingError, match="numeric response"):
        await RemnawaveUserGateway(client).get_by_id(73)


@pytest.mark.unit
async def test_get_by_ref_rejects_wrong_upstream_legacy_binding(monkeypatch):
    client = AsyncMock()
    client.get_validated.return_value = _ValidatedModel({"id": 73, "uuid": str(uuid4())})
    monkeypatch.setattr("src.infrastructure.remnawave.user_gateway.map_remnawave_user", _mapped_user)

    with pytest.raises(RemnawaveIdentityBindingError, match="rollback reference"):
        await RemnawaveUserGateway(client).get_by_ref(RemnawaveUserRef(id=73, legacy_uuid=uuid4()))


@pytest.mark.unit
async def test_get_by_ref_accepts_omitted_upstream_uuid_with_exact_numeric_binding(monkeypatch):
    client = AsyncMock()
    client.get_validated.return_value = _ValidatedModel({"id": 73, "username": "numeric-only"})
    monkeypatch.setattr("src.infrastructure.remnawave.user_gateway.map_remnawave_user", _mapped_user)

    user = await RemnawaveUserGateway(client).get_by_ref(RemnawaveUserRef(id=73, legacy_uuid=uuid4()))

    assert user is not None
    assert user.remnawave_id == 73
    assert user.uuid is None


@pytest.mark.unit
async def test_update_binding_mismatch_fails_before_provider_mutation(monkeypatch):
    client = AsyncMock()
    client.get_validated.return_value = _ValidatedModel({"id": 73, "uuid": str(uuid4())})
    monkeypatch.setattr("src.infrastructure.remnawave.user_gateway.map_remnawave_user", _mapped_user)

    with pytest.raises(RemnawaveIdentityBindingError, match="rollback reference"):
        await RemnawaveUserGateway(client).update(
            RemnawaveUserRef(id=73, legacy_uuid=uuid4()),
            status="disabled",
        )

    client.patch_validated.assert_not_awaited()


@pytest.mark.unit
async def test_empty_create_ack_is_typed_pending_without_metadata_lookup_or_retry(monkeypatch):
    client = AsyncMock()
    client.post_validated.return_value = None
    monkeypatch.setattr(settings, "remnawave_default_internal_squad_uuid", str(uuid4()))

    with pytest.raises(RemnawaveMutationAcceptedPending) as exc_info:
        await RemnawaveUserGateway(client).create(username="cvpn_new", email="new@example.test")

    assert exc_info.value.operation == "create"
    assert exc_info.value.numeric_user_id is None
    client.post_validated.assert_awaited_once()
    client.get.assert_not_awaited()
    client.get_validated.assert_not_awaited()


@pytest.mark.unit
async def test_create_transport_ambiguity_is_pending_without_lookup_or_repost(monkeypatch):
    client = AsyncMock()
    client.post_validated.side_effect = RemnawaveTransportError()
    monkeypatch.setattr(settings, "remnawave_default_internal_squad_uuid", str(uuid4()))

    with pytest.raises(RemnawaveMutationAcceptedPending) as exc_info:
        await RemnawaveUserGateway(client).create(username="cvpn_new", email="new@example.test")

    assert exc_info.value.operation == "create"
    client.post_validated.assert_awaited_once()
    client.get_validated.assert_not_awaited()


@pytest.mark.unit
async def test_update_transport_ambiguity_reconciles_once_without_patch_replay(monkeypatch):
    client = AsyncMock()
    legacy_uuid = uuid4()
    response = _ValidatedModel({"id": 73, "uuid": str(legacy_uuid), "username": "demo-user", "status": "disabled"})
    client.get_validated.return_value = response
    client.patch_validated.side_effect = RemnawaveTransportError()
    monkeypatch.setattr("src.infrastructure.remnawave.user_gateway.map_remnawave_user", _mapped_user)

    result = await RemnawaveUserGateway(client).update(
        RemnawaveUserRef(id=73, legacy_uuid=legacy_uuid),
        status="disabled",
    )

    assert result.status is UserStatus.DISABLED
    assert client.get_validated.await_count == 2
    client.patch_validated.assert_awaited_once()


@pytest.mark.unit
async def test_revoke_transport_ambiguity_never_reposts_and_requires_provable_state(monkeypatch):
    client = AsyncMock()
    legacy_uuid = uuid4()
    preflight = _ValidatedModel({"id": 73, "uuid": str(legacy_uuid), "username": "demo-user", "status": "active"})
    reconciled = _ValidatedModel(
        {
            "id": 73,
            "uuid": str(legacy_uuid),
            "username": "demo-user",
            "status": "active",
            "subRevokedAt": "2026-08-30T12:00:00Z",
        }
    )
    client.get_validated.side_effect = [preflight, reconciled]
    client.post_validated.side_effect = RemnawaveTransportError()
    monkeypatch.setattr("src.infrastructure.remnawave.user_gateway.map_remnawave_user", _mapped_user)

    gateway = RemnawaveUserGateway(client)
    result = await gateway.revoke_subscription(
        RemnawaveUserRef(id=73, legacy_uuid=legacy_uuid),
        revoke_only_passwords=False,
    )
    assert result.sub_revoked_at is not None
    assert client.get_validated.await_count == 2

    client.post_validated.assert_awaited_once()


@pytest.mark.unit
async def test_password_only_rotation_is_safety_disabled_before_provider_io():
    client = AsyncMock()

    with pytest.raises(RemnawavePasswordOnlyCredentialRotationSafetyDisabled, match="durable receipts"):
        await RemnawaveUserGateway(client).revoke_subscription(
            RemnawaveUserRef(id=73, legacy_uuid=uuid4()),
            revoke_only_passwords=True,
        )

    client.get_validated.assert_not_awaited()
    client.post_validated.assert_not_awaited()


@pytest.mark.unit
async def test_delete_transport_ambiguity_confirms_absence_without_replay(monkeypatch):
    client = AsyncMock()
    legacy_uuid = uuid4()
    request = httpx.Request("GET", "https://remnawave.test/api/users/73")
    client.get_validated.side_effect = [
        _ValidatedModel({"id": 73, "uuid": str(legacy_uuid), "username": "demo-user"}),
        httpx.HTTPStatusError(
            "missing",
            request=request,
            response=httpx.Response(404, request=request),
        ),
    ]
    client.delete_validated.side_effect = RemnawaveTransportError()
    monkeypatch.setattr("src.infrastructure.remnawave.user_gateway.map_remnawave_user", _mapped_user)

    await RemnawaveUserGateway(client).delete(RemnawaveUserRef(id=73, legacy_uuid=legacy_uuid))

    client.delete_validated.assert_awaited_once()
    assert client.get_validated.await_count == 2


@pytest.mark.unit
async def test_empty_update_ack_reconciles_once_by_exact_known_numeric_target(monkeypatch):
    client = AsyncMock()
    legacy_uuid = uuid4()
    response = _ValidatedModel({"id": 73, "uuid": str(legacy_uuid), "username": "demo-user", "status": "disabled"})
    client.get_validated.return_value = response
    client.patch_validated.return_value = None
    monkeypatch.setattr("src.infrastructure.remnawave.user_gateway.map_remnawave_user", _mapped_user)

    result = await RemnawaveUserGateway(client).update(
        RemnawaveUserRef(id=73, legacy_uuid=legacy_uuid),
        status="disabled",
    )

    assert result.remnawave_id == 73
    assert client.get_validated.await_count == 2
    client.patch_validated.assert_awaited_once()


@pytest.mark.unit
async def test_empty_disable_ack_still_active_is_pending(monkeypatch):
    client = AsyncMock()
    legacy_uuid = uuid4()
    client.get_validated.return_value = _ValidatedModel(
        {"id": 73, "uuid": str(legacy_uuid), "username": "demo-user", "status": "active"}
    )
    client.patch_validated.return_value = None
    monkeypatch.setattr("src.infrastructure.remnawave.user_gateway.map_remnawave_user", _mapped_user)

    with pytest.raises(RemnawaveMutationAcceptedPending) as exc_info:
        await RemnawaveUserGateway(client).update(
            RemnawaveUserRef(id=73, legacy_uuid=legacy_uuid),
            status=UserStatus.DISABLED,
        )

    assert exc_info.value.operation == "update"
    assert client.get_validated.await_count == 2
    client.patch_validated.assert_awaited_once()


@pytest.mark.unit
async def test_empty_revoke_ack_without_revoked_timestamp_is_pending(monkeypatch):
    client = AsyncMock()
    legacy_uuid = uuid4()
    client.get_validated.return_value = _ValidatedModel(
        {"id": 73, "uuid": str(legacy_uuid), "username": "demo-user", "subRevokedAt": None}
    )
    client.post_validated.return_value = None
    monkeypatch.setattr("src.infrastructure.remnawave.user_gateway.map_remnawave_user", _mapped_user)

    with pytest.raises(RemnawaveMutationAcceptedPending) as exc_info:
        await RemnawaveUserGateway(client).revoke_subscription(RemnawaveUserRef(id=73, legacy_uuid=legacy_uuid))

    assert exc_info.value.operation == "revoke"
    assert client.get_validated.await_count == 2
    client.post_validated.assert_awaited_once()
