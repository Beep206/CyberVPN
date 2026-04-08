from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException
from httpx import HTTPStatusError, Request, Response

from src.application.use_cases.subscriptions.generate_config import GenerateConfigUseCase
from src.presentation.schemas.remnawave_responses import RemnawaveSubscriptionDetailsResponse


@pytest.mark.unit
@pytest.mark.asyncio
async def test_generate_config_prefers_first_real_link() -> None:
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

    result = await GenerateConfigUseCase(client).execute("user-1")

    assert result["config"] == "vless://11111111-1111-1111-1111-111111111111@example.com:443?security=tls"
    assert result["config_string"] == result["config"]
    assert result["client_type"] == "vless"
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

    result = await GenerateConfigUseCase(client).execute("user-2")

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

    result = await GenerateConfigUseCase(client).execute("user-3")

    assert result["is_found"] is True
    assert result["links"] == ["vmess://config-1"]
    assert result["ss_conf_links"] == {"Node A": "ss://config-a"}


@pytest.mark.unit
@pytest.mark.asyncio
async def test_generate_config_maps_upstream_404_to_http_404() -> None:
    client = AsyncMock()
    client.get_validated = AsyncMock(
        side_effect=HTTPStatusError(
            "not found",
            request=Request("GET", "http://localhost:3005/api/subscriptions/by-uuid/missing"),
            response=Response(404),
        )
    )

    with pytest.raises(HTTPException) as exc_info:
        await GenerateConfigUseCase(client).execute("missing")

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
        await GenerateConfigUseCase(client).execute("expired-user")

    assert exc_info.value.status_code == 422
    assert exc_info.value.detail == "Subscription expired"
