from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from src.application.use_cases.subscriptions.generate_config import GenerateConfigUseCase
from src.config.settings import settings
from src.infrastructure.remnawave.contracts import RemnawaveSubscriptionDetailsResponse


@pytest.mark.asyncio
async def test_remnawave_2_8_subscription_exposes_xhttp_and_stable_fallback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "remnawave_feature_xhttp_enabled", True)
    monkeypatch.setattr(settings, "remnawave_feature_xhttp_rollout_mode", "canary")
    monkeypatch.setattr(settings, "remnawave_feature_xhttp_allowed_user_segments", "internal,beta")
    monkeypatch.setattr(settings, "remnawave_feature_xhttp_force_disabled", False)
    monkeypatch.setattr(settings, "remnawave_feature_xhttp_mihomo_enabled", True)
    stable_link = "vless://stable-user@example.com:443?type=tcp&security=reality#stable"
    xhttp_link = "vless://xhttp-user@example.com:8443?type=xhttp&security=reality#xhttp"
    client = AsyncMock()
    client.get_validated = AsyncMock(
        return_value=RemnawaveSubscriptionDetailsResponse(
            isFound=True,
            user={
                "shortUuid": "xhttp-user",
                "username": "xhttp-user",
                "userStatus": "ACTIVE",
                "isActive": True,
            },
            links=[stable_link],
            xhttpLinks=[xhttp_link],
            subscriptionUrl="https://sub.example.com/xhttp-user",
        )
    )

    result = await GenerateConfigUseCase(client).execute("xhttp-user", user_segments=["internal"])

    assert result["subscription_url"] == "https://sub.example.com/xhttp-user"
    assert result["xhttp_enabled"] is True
    assert result["xhttp_links"] == [xhttp_link]
    assert stable_link in result["links"]
    assert xhttp_link in result["links"]


@pytest.mark.asyncio
async def test_remnawave_2_8_subscription_filters_premium_rollout_without_plan(
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
            isFound=True,
            user={
                "shortUuid": "xhttp-user",
                "username": "xhttp-user",
                "userStatus": "ACTIVE",
                "isActive": True,
            },
            links=[stable_link],
            xhttpLinks=[xhttp_link],
            subscriptionUrl=None,
        )
    )

    result = await GenerateConfigUseCase(client).execute("xhttp-user")

    assert result["config"] == stable_link
    assert result["xhttp_enabled"] is False
    assert result["xhttp_links"] == []
    assert result["links"] == [stable_link]


@pytest.mark.asyncio
async def test_remnawave_2_8_subscription_force_disable_filters_xhttp(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "remnawave_feature_xhttp_enabled", True)
    monkeypatch.setattr(settings, "remnawave_feature_xhttp_rollout_mode", "canary")
    monkeypatch.setattr(settings, "remnawave_feature_xhttp_force_disabled", True)
    stable_link = "vless://stable-user@example.com:443?type=tcp&security=reality#stable"
    xhttp_link = "vless://xhttp-user@example.com:8443?type=xhttp&security=reality#xhttp"
    client = AsyncMock()
    client.get_validated = AsyncMock(
        return_value=RemnawaveSubscriptionDetailsResponse(
            isFound=True,
            user={
                "shortUuid": "xhttp-user",
                "username": "xhttp-user",
                "userStatus": "ACTIVE",
                "isActive": True,
            },
            links=[stable_link],
            xhttpLinks=[xhttp_link],
            subscriptionUrl=None,
        )
    )

    result = await GenerateConfigUseCase(client).execute("xhttp-user")

    assert result["config"] == stable_link
    assert result["xhttp_enabled"] is False
    assert result["xhttp_links"] == []
    assert result["links"] == [stable_link]
