"""Telegram Web Widget authentication use case.

Validates Telegram OAuth payload (hash and auth_date), auto-registers
or auto-logs-in the user, and issues JWT tokens.
"""

import base64
import json
import logging
import secrets
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from src.application.services.auth_service import AuthService
from src.application.services.telegram_auth import (
    InvalidTelegramAuthError,
    TelegramAuthExpiredError,
    TelegramAuthService,
)
from src.application.use_cases.auth.oauth_login import OAuthLoginUseCase
from src.application.use_cases.auth.verify_otp import RemnawaveGateway
from src.infrastructure.database.models.admin_user_model import AdminUserModel
from src.infrastructure.database.repositories.admin_user_repo import AdminUserRepository

logger = logging.getLogger(__name__)
BEARER_SCHEME = "bearer"


class TelegramWebLoginResult:
    """Result of Telegram Web authentication."""

    def __init__(
        self,
        access_token: str,
        refresh_token: str,
        token_type: str,
        expires_in: int,
        user: AdminUserModel,
        is_new_user: bool,
    ) -> None:
        self.access_token = access_token
        self.refresh_token = refresh_token
        self.token_type = token_type
        self.expires_in = expires_in
        self.user = user
        self.is_new_user = is_new_user


class TelegramWebAuthUseCase:
    """Authenticates users via Telegram Web OAuth/Widget payload."""

    def __init__(
        self,
        user_repo: AdminUserRepository,
        auth_service: AuthService,
        session: AsyncSession,
        telegram_service: TelegramAuthService,
        remnawave_gateway: RemnawaveGateway | None = None,
    ) -> None:
        self._user_repo = user_repo
        self._auth_service = auth_service
        self._session = session
        self._telegram_service = telegram_service
        self._remnawave_gateway = remnawave_gateway

    async def execute(self, payload: dict) -> TelegramWebLoginResult:
        """Validate Telegram hash, extract user, auto-login or auto-register.

        Args:
            payload: Dict containing id, first_name, auth_date, hash, etc.

        Returns:
            TelegramWebLoginResult with JWT tokens and user

        Raises:
            ValueError: If signature is invalid or expired
        """
        try:
            # The existing TelegramAuthService validates a base64 encoded JSON
            auth_data_json = json.dumps(payload)
            auth_data_b64 = base64.b64encode(auth_data_json.encode()).decode("utf-8")
            user_info = self._telegram_service.validate_auth_data(auth_data_b64)
        except (InvalidTelegramAuthError, TelegramAuthExpiredError) as e:
            raise ValueError(str(e)) from e

        telegram_id = user_info.telegram_id
        username = user_info.username
        first_name = user_info.first_name

        user = await self._user_repo.get_by_telegram_id(telegram_id)
        is_new_user = False

        if not user:
            # Auto-register with Telegram-first onboarding
            login = OAuthLoginUseCase._generate_telegram_login(
                username=username,
                first_name=first_name,
                telegram_id=str(telegram_id),
            )

            # Ensure unique login
            existing = await self._user_repo.get_by_login(login)
            if existing:
                login = f"{login}_{secrets.token_hex(3)}"

            password_hash = await self._auth_service.hash_password(secrets.token_urlsafe(32))
            user = AdminUserModel(
                login=login,
                telegram_id=telegram_id,
                password_hash=password_hash,
                role="viewer",
                is_active=True,
                is_email_verified=True,
            )
            user = await self._user_repo.create(user)
            is_new_user = True

            logger.info(
                "Created new user from Telegram Web Login",
                extra={"user_id": str(user.id), "login": login},
            )

            if self._remnawave_gateway:
                try:
                    await self._remnawave_gateway.create_user(
                        username=login,
                        email="",
                        telegram_id=telegram_id,
                    )
                except Exception as e:
                    logger.exception(
                        "Failed to create Remnawave user for Web Telegram registration: %s",
                        e,
                        extra={"user_id": str(user.id)},
                    )
        else:
            logger.info(
                "Telegram Web login for existing user",
                extra={"user_id": str(user.id)},
            )

        await self._session.commit()

        # Issue JWT tokens
        access_token, _, access_exp = self._auth_service.create_access_token(
            subject=str(user.id),
            role=user.role if isinstance(user.role, str) else user.role.value,
        )
        refresh_token, _, _ = self._auth_service.create_refresh_token(
            subject=str(user.id),
        )
        expires_in = int((access_exp - datetime.now(UTC)).total_seconds())

        return TelegramWebLoginResult(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type=BEARER_SCHEME,
            expires_in=expires_in,
            user=user,
            is_new_user=is_new_user,
        )
