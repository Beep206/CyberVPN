"""Telegram bot integration routes."""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status

from src.application.use_cases.auth.permissions import Permission
from src.infrastructure.remnawave.client import RemnawaveClient
from src.infrastructure.remnawave.user_gateway import RemnawaveUserGateway
from src.presentation.api.v1.telegram.schemas import (
    ConfigResponse,
    CreateSubscriptionRequest,
    TelegramUserResponse,
)
from src.presentation.dependencies.remnawave import get_remnawave_client
from src.presentation.dependencies.roles import require_permission

router = APIRouter(prefix="/telegram", tags=["telegram"])


@router.get("/user/{telegram_id}", response_model=TelegramUserResponse)
async def get_telegram_user(
    telegram_id: int,
    remnawave_client: RemnawaveClient = Depends(get_remnawave_client),
    _: None = Depends(require_permission(Permission.USER_READ)),
) -> TelegramUserResponse:
    """Get Telegram user information."""
    gateway = RemnawaveUserGateway(client=remnawave_client)
    user = await gateway.get_by_telegram_id(telegram_id=telegram_id)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with telegram_id {telegram_id} not found",
        )

    return TelegramUserResponse(
        uuid=user.uuid,
        username=user.username,
        status=user.status,
        data_usage=user.data_usage,
        data_limit=user.data_limit,
        expires_at=user.expires_at,
        subscription_url=user.subscription_url,
    )


@router.post("/user/{telegram_id}/subscription", status_code=status.HTTP_201_CREATED)
async def create_subscription(
    telegram_id: int,
    request: CreateSubscriptionRequest,
    remnawave_client: RemnawaveClient = Depends(get_remnawave_client),
    _: None = Depends(require_permission(Permission.SUBSCRIPTION_CREATE)),
) -> dict[str, Any]:
    """Create a subscription for a Telegram user."""
    gateway = RemnawaveUserGateway(client=remnawave_client)
    user = await gateway.get_by_telegram_id(telegram_id=telegram_id)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with telegram_id {telegram_id} not found",
        )

    subscription_data = {
        "user_uuid": str(user.uuid),
        "plan_name": request.plan_name,
        "duration_days": request.duration_days,
    }

    result = await remnawave_client.post(
        "/api/subscriptions",
        json=subscription_data,
    )

    return {
        "status": "success",
        "subscription_id": result.get("id"),
        "expires_at": result.get("expires_at"),
    }


@router.get("/user/{telegram_id}/config", response_model=ConfigResponse)
async def get_user_config(
    telegram_id: int,
    remnawave_client: RemnawaveClient = Depends(get_remnawave_client),
    _: None = Depends(require_permission(Permission.USER_READ)),
) -> ConfigResponse:
    """Get VPN configuration for a Telegram user."""
    gateway = RemnawaveUserGateway(client=remnawave_client)
    user = await gateway.get_by_telegram_id(telegram_id=telegram_id)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with telegram_id {telegram_id} not found",
        )

    result = await remnawave_client.get(
        f"/api/users/{user.uuid}/config",
    )

    return ConfigResponse(
        config_string=str(result.get("config_string", "")),
        client_type=result.get("client_type", "vless"),
    )
