"""Telegram bot integration routes."""

from typing import Dict, Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.use_cases.auth.permissions import Permission
from src.infrastructure.database.repositories.admin_user_repo import AdminUserRepository
from src.infrastructure.remnawave.client import RemnawaveClient
from src.presentation.api.v1.telegram.schemas import (
    TelegramUserResponse,
    CreateSubscriptionRequest,
    ConfigResponse,
    NotifyRequest,
)
from src.presentation.dependencies.database import get_db
from src.presentation.dependencies.remnawave import get_remnawave_client
from src.presentation.dependencies.roles import require_permission

router = APIRouter(prefix="/telegram", tags=["telegram"])


@router.get("/user/{telegram_id}", response_model=TelegramUserResponse)
async def get_telegram_user(
    telegram_id: int,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(require_permission(Permission.USER_READ)),
) -> TelegramUserResponse:
    """Get Telegram user information."""
    try:
        user_repo = AdminUserRepository(db)
        user = await user_repo.get_by_telegram_id(telegram_id=telegram_id)

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
    except HTTPException:
        raise
@router.post("/user/{telegram_id}/subscription", status_code=status.HTTP_201_CREATED)
async def create_subscription(
    telegram_id: int,
    request: CreateSubscriptionRequest,
    db: AsyncSession = Depends(get_db),
    remnawave_client: RemnawaveClient = Depends(get_remnawave_client),
    _: None = Depends(require_permission(Permission.SUBSCRIPTION_CREATE)),
) -> Dict[str, Any]:
    """Create a subscription for a Telegram user."""
    try:
        user_repo = AdminUserRepository(db)
        user = await user_repo.get_by_telegram_id(telegram_id=telegram_id)

        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User with telegram_id {telegram_id} not found",
            )

        # Create subscription via Remnawave API
        subscription_data = {
            "user_uuid": str(user.uuid),
            "plan_name": request.plan_name,
            "duration_days": request.duration_days,
        }

        result = await remnawave_client.post(
            endpoint="/api/subscriptions",
            data=subscription_data,
        )

        return {
            "status": "success",
            "subscription_id": result.get("id"),
            "expires_at": result.get("expires_at"),
        }
    except HTTPException:
        raise
@router.get("/user/{telegram_id}/config", response_model=ConfigResponse)
async def get_user_config(
    telegram_id: int,
    db: AsyncSession = Depends(get_db),
    remnawave_client: RemnawaveClient = Depends(get_remnawave_client),
    _: None = Depends(require_permission(Permission.USER_READ)),
) -> ConfigResponse:
    """Get VPN configuration for a Telegram user."""
    try:
        user_repo = AdminUserRepository(db)
        user = await user_repo.get_by_telegram_id(telegram_id=telegram_id)

        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User with telegram_id {telegram_id} not found",
            )

        # Get VPN config via Remnawave API
        result = await remnawave_client.get(
            endpoint=f"/api/users/{user.uuid}/config",
        )

        return ConfigResponse(
            config_string=result.get("config_string"),
            client_type=result.get("client_type", "vless"),
        )
    except HTTPException:
        raise