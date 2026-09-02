from unittest.mock import AsyncMock
from uuid import UUID

import pytest
from fastapi import HTTPException
from httpx import HTTPStatusError, Request, Response

from src.application.use_cases.subscriptions.generate_config import (
    GenerateConfigLegacyRollbackUseCase,
    GenerateConfigUseCase,
)
from src.config.settings import settings
from src.domain.value_objects.remnawave_user_ref import RemnawaveUserRef
from src.infrastructure.remnawave.contracts import RemnawaveSubscriptionDetailsResponse


@pytest.mark.unit
@pytest.mark.asyncio
async def test_generate_config_prefers_subscription_url_over_direct_links() -> None:
    client = AsyncMock()
    client.get_validated = AsyncMock(
        return_value=RemnawaveSubscriptionDetailsResponse(
            is_found=True,
            user={
                "shortUuid": "user-1",
                "username": "user-1",
                "userStatus": "ACTIVE",
                "isActive": True,
            },
            links=[
                "vless://11111111-1111-1111-1111-111111111111@example.com:443?security=tls",
                "vless://22222222-2222-2222-2222-222222222222@example.com:443?security=tls",
            ],
            subscription_url="https://sub.example.com/user-1",
        )
    )

    result = await GenerateConfigUseCase(client).execute(1)

    assert result["config"] == "https://sub.example.com/user-1"
    assert result["config_string"] == result["config"]
    assert result["client_type"] == "subscription"
    assert result["subscription_url"] == "https://sub.example.com/user-1"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_generate_config_falls_back_to_subscription_url_for_placeholder_links() -> None:
    client = AsyncMock()
    client.get_validated = AsyncMock(
        return_value=RemnawaveSubscriptionDetailsResponse(
            is_found=True,
            user={
                "shortUuid": "user-2",
                "username": "user-2",
                "userStatus": "ACTIVE",
                "isActive": True,
            },
            links=[
                (
                    "vless://00000000-0000-0000-0000-000000000000@0.0.0.0:1"
                    "?encryption=none&type=tcp&security=none#→ No hosts found"
                ),
            ],
            subscription_url="https://sub.example.com/user-2",
        )
    )

    result = await GenerateConfigUseCase(client).execute(2)

    assert result["config"] == "https://sub.example.com/user-2"
    assert result["client_type"] == "subscription"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_generate_config_preserves_links_and_ss_conf_links() -> None:
    client = AsyncMock()
    client.get_validated = AsyncMock(
        return_value=RemnawaveSubscriptionDetailsResponse(
            is_found=True,
            user={
                "shortUuid": "user-3",
                "username": "user-3",
                "userStatus": "ACTIVE",
                "isActive": True,
            },
            links=["vmess://config-1"],
            ss_conf_links={"Node A": "ss://config-a"},
            subscription_url="https://sub.example.com/user-3",
        )
    )

    result = await GenerateConfigUseCase(client).execute(3)

    assert result["is_found"] is True
    assert result["links"] == ["vmess://config-1"]
    assert result["ss_conf_links"] == {"Node A": "ss://config-a"}


@pytest.mark.unit
@pytest.mark.asyncio
async def test_generate_config_allows_remnawave_2_8_xhttp_links_when_enabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "remnawave_feature_xhttp_enabled", True)
    monkeypatch.setattr(settings, "remnawave_feature_xhttp_rollout_mode", "canary")
    monkeypatch.setattr(settings, "remnawave_feature_xhttp_allowed_user_segments", "internal,beta")
    monkeypatch.setattr(settings, "remnawave_feature_xhttp_force_disabled", False)
    monkeypatch.setattr(settings, "remnawave_feature_xhttp_mihomo_enabled", True)
    xhttp_link = "vless://xhttp-user@example.com:443?type=xhttp&security=reality#xhttp"
    client = AsyncMock()
    client.get_validated = AsyncMock(
        return_value=RemnawaveSubscriptionDetailsResponse(
            is_found=True,
            user={
                "shortUuid": "xhttp-user",
                "username": "xhttp-user",
                "userStatus": "ACTIVE",
                "isActive": True,
            },
            links=[],
            xhttpLinks=[xhttp_link],
            subscription_url=None,
        )
    )

    result = await GenerateConfigUseCase(client).execute(4, user_segments=["beta"])

    assert result["config"] == xhttp_link
    assert result["client_type"] == "vless"
    assert result["links"] == [xhttp_link]
    assert result["xhttp_enabled"] is True
    assert result["xhttp_links"] == [xhttp_link]


@pytest.mark.unit
@pytest.mark.asyncio
async def test_generate_config_allows_premium_smart_ru_plan_rollout_xhttp_links(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "remnawave_feature_xhttp_enabled", True)
    monkeypatch.setattr(settings, "remnawave_feature_xhttp_rollout_mode", "premium_smart_ru")
    monkeypatch.setattr(settings, "remnawave_feature_xhttp_allowed_plan_codes", "premium_smart_ru")
    monkeypatch.setattr(settings, "remnawave_feature_xhttp_force_disabled", False)
    stable_link = "vless://stable-user@example.com:443?type=tcp&security=reality#stable"
    xhttp_link = "vless://xhttp-user@example.com:8443?type=xhttp&security=reality#xhttp"
    client = AsyncMock()
    client.get_validated = AsyncMock(
        return_value=RemnawaveSubscriptionDetailsResponse(
            is_found=True,
            user={
                "shortUuid": "xhttp-user",
                "username": "xhttp-user",
                "userStatus": "ACTIVE",
                "isActive": True,
            },
            links=[stable_link],
            xhttpLinks=[xhttp_link],
            subscription_url=None,
        )
    )

    result = await GenerateConfigUseCase(client).execute(5, plan_code="premium_smart_ru")

    assert result["config"] == stable_link
    assert result["links"] == [stable_link, xhttp_link]
    assert result["xhttp_enabled"] is True
    assert result["xhttp_links"] == [xhttp_link]


@pytest.mark.unit
@pytest.mark.asyncio
async def test_generate_config_filters_premium_smart_ru_xhttp_without_plan_context(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "remnawave_feature_xhttp_enabled", True)
    monkeypatch.setattr(settings, "remnawave_feature_xhttp_rollout_mode", "premium_smart_ru")
    monkeypatch.setattr(settings, "remnawave_feature_xhttp_allowed_plan_codes", "premium_smart_ru")
    monkeypatch.setattr(settings, "remnawave_feature_xhttp_force_disabled", False)
    stable_link = "vless://stable-user@example.com:443?type=tcp&security=reality#stable"
    xhttp_link = "vless://xhttp-user@example.com:8443?type=xhttp&security=reality#xhttp"
    client = AsyncMock()
    client.get_validated = AsyncMock(
        return_value=RemnawaveSubscriptionDetailsResponse(
            is_found=True,
            user={
                "shortUuid": "xhttp-user",
                "username": "xhttp-user",
                "userStatus": "ACTIVE",
                "isActive": True,
            },
            links=[stable_link],
            xhttpLinks=[xhttp_link],
            subscription_url=None,
        )
    )

    result = await GenerateConfigUseCase(client).execute(6)

    assert result["config"] == stable_link
    assert result["links"] == [stable_link]
    assert result["xhttp_enabled"] is False
    assert result["xhttp_links"] == []


@pytest.mark.unit
@pytest.mark.asyncio
async def test_generate_config_force_disabled_filters_xhttp_links_and_uses_stable_fallback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "remnawave_feature_xhttp_enabled", True)
    monkeypatch.setattr(settings, "remnawave_feature_xhttp_rollout_mode", "canary")
    monkeypatch.setattr(settings, "remnawave_feature_xhttp_force_disabled", True)
    stable_link = "vless://stable-user@example.com:443?type=tcp&security=reality#stable"
    xhttp_link = "vless://stable-user@example.com:443?type=xhttp&security=reality#xhttp"
    client = AsyncMock()
    client.get_validated = AsyncMock(
        return_value=RemnawaveSubscriptionDetailsResponse(
            is_found=True,
            user={
                "shortUuid": "stable-user",
                "username": "stable-user",
                "userStatus": "ACTIVE",
                "isActive": True,
            },
            links=[stable_link],
            xhttpLinks=[xhttp_link],
            subscription_url=None,
        )
    )

    result = await GenerateConfigUseCase(client).execute(7)

    assert result["config"] == stable_link
    assert result["links"] == [stable_link]
    assert result["xhttp_enabled"] is False
    assert result["xhttp_links"] == []


@pytest.mark.unit
@pytest.mark.asyncio
async def test_generate_config_maps_upstream_404_to_http_404() -> None:
    client = AsyncMock()
    client.get_validated = AsyncMock(
        side_effect=HTTPStatusError(
            "not found",
            request=Request("GET", "http://localhost:3005/api/subscriptions/by-id/8"),
            response=Response(404),
        )
    )

    with pytest.raises(HTTPException) as exc_info:
        await GenerateConfigUseCase(client).execute(8)

    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == "Subscription config not found"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_generate_config_maps_expired_user_to_http_422() -> None:
    client = AsyncMock()
    client.get_validated = AsyncMock(
        return_value=RemnawaveSubscriptionDetailsResponse(
            is_found=True,
            user={
                "shortUuid": "expired-user",
                "username": "expired-user",
                "userStatus": "EXPIRED",
                "isActive": False,
            },
            links=[],
            subscription_url="https://sub.example.com/expired-user",
        )
    )

    with pytest.raises(HTTPException) as exc_info:
        await GenerateConfigUseCase(client).execute(9)

    assert exc_info.value.status_code == 422
    assert exc_info.value.detail == "Subscription expired"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_generate_config_uses_numeric_subscription_route_after_cutover() -> None:
    client = AsyncMock()
    client.get_validated.return_value = RemnawaveSubscriptionDetailsResponse(
        is_found=True,
        user={
            "shortUuid": "numeric-user",
            "username": "numeric-user",
            "userStatus": "ACTIVE",
            "isActive": True,
        },
        links=["vless://numeric@example.test:443"],
    )

    await GenerateConfigUseCase(client).execute(RemnawaveUserRef(id=42))

    client.get_validated.assert_awaited_once_with(
        "/subscriptions/by-id/42",
        RemnawaveSubscriptionDetailsResponse,
    )


@pytest.mark.unit
@pytest.mark.asyncio
async def test_generate_config_rejects_legacy_only_identity_on_normal_path() -> None:
    client = AsyncMock()

    with pytest.raises(ValueError, match="numeric user id"):
        await GenerateConfigUseCase(client).execute(RemnawaveUserRef(legacy_uuid=UUID(int=1)))

    client.get_validated.assert_not_awaited()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_generate_config_legacy_uuid_isolated_to_explicit_rollback_adapter() -> None:
    legacy_uuid = UUID(int=1)
    client = AsyncMock()
    client.get_validated.return_value = RemnawaveSubscriptionDetailsResponse(
        is_found=True,
        user={
            "shortUuid": "rollback-user",
            "username": "rollback-user",
            "userStatus": "ACTIVE",
            "isActive": True,
        },
        links=["vless://rollback@example.test:443"],
    )

    await GenerateConfigLegacyRollbackUseCase(client).execute(legacy_uuid)

    client.get_validated.assert_awaited_once_with(
        f"/subscriptions/by-uuid/{legacy_uuid}",
        RemnawaveSubscriptionDetailsResponse,
    )
