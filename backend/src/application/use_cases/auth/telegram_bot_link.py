"""Telegram bot deep-link authentication use case.

Validates a one-time token from a Telegram bot /login command,
looks up the user by telegram_id, and issues JWT tokens.
"""

import logging
from datetime import UTC, datetime

import redis.asyncio as redis

from src.application.services.auth_service import AuthService
from src.infrastructure.cache.bot_link_tokens import consume_bot_link_token
from src.infrastructure.database.models.admin_user_model import AdminUserModel
from src.infrastructure.database.repositories.admin_user_repo import AdminUserRepository

logger = logging.getLogger(__name__)


class TelegramBotLinkResult:
    """Result of Telegram bot link authentication."""

    def __init__(
        self,
        access_token: str,
        refresh_token: str,
        token_type: str,
        expires_in: int,
        user: AdminUserModel,
    ) -> None:
        self.access_token = access_token
        self.refresh_token = refresh_token
        self.token_type = token_type
        self.expires_in = expires_in
        self.user = user


class TelegramBotLinkUseCase:
    """Authenticates users via one-time Telegram bot login link token."""

    def __init__(
        self,
        user_repo: AdminUserRepository,
        auth_service: AuthService,
        redis_client: redis.Redis,
    ) -> None:
        self._user_repo = user_repo
        self._auth_service = auth_service
        self._redis = redis_client

    async def execute(self, token: str) -> TelegramBotLinkResult:
        """Consume one-time token, find user, issue JWT.

        Args:
            token: One-time login token from bot /login command.

        Returns:
            TelegramBotLinkResult with JWT tokens and user.

        Raises:
            ValueError: If token is invalid/expired or user not found.
        """
        # Step 1: Atomically consume the token
        telegram_id = await consume_bot_link_token(self._redis, token)
        if telegram_id is None:
            raise ValueError("Invalid or expired login token")

        # Step 2: Look up user by telegram_id
        user = await self._user_repo.get_by_telegram_id(telegram_id)
        if not user:
            logger.warning(
                "Bot link token valid but user not found",
                extra={"telegram_id": telegram_id},
            )
            raise ValueError("User not found for this Telegram account")

        if not user.is_active:
            raise ValueError("Account is deactivated")

        logger.info(
            "Telegram bot link login successful",
            extra={"user_id": str(user.id), "telegram_id": telegram_id},
        )

        # Step 3: Issue JWT tokens
        access_token, _, access_exp = self._auth_service.create_access_token(
            subject=str(user.id),
            role=user.role if isinstance(user.role, str) else user.role.value,
        )
        refresh_token, _, _ = self._auth_service.create_refresh_token(
            subject=str(user.id),
        )
        expires_in = int((access_exp - datetime.now(UTC)).total_seconds())

        return TelegramBotLinkResult(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            expires_in=expires_in,
            user=user,
        )
