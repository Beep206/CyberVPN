"""Telegram Mini App authentication use case.

Validates initData from Telegram.WebApp.initData, extracts user,
auto-registers or auto-logs-in, and issues JWT tokens.
"""

import logging
import secrets
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from src.application.services.auth_service import AuthService
from src.application.use_cases.auth.oauth_login import OAuthLoginUseCase
from src.application.use_cases.auth.verify_otp import RemnawaveGateway
from src.infrastructure.database.models.admin_user_model import AdminUserModel
from src.infrastructure.database.repositories.admin_user_repo import AdminUserRepository
from src.infrastructure.oauth.telegram import TelegramOAuthProvider

logger = logging.getLogger(__name__)


class TelegramMiniAppResult:
    """Result of Telegram Mini App authentication."""

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


class TelegramMiniAppUseCase:
    """Authenticates users via Telegram Mini App initData."""

    def __init__(
        self,
        user_repo: AdminUserRepository,
        auth_service: AuthService,
        session: AsyncSession,
        telegram_provider: TelegramOAuthProvider,
        remnawave_gateway: RemnawaveGateway | None = None,
    ) -> None:
        self._user_repo = user_repo
        self._auth_service = auth_service
        self._session = session
        self._telegram = telegram_provider
        self._remnawave_gateway = remnawave_gateway

    async def execute(self, init_data: str) -> TelegramMiniAppResult:
        """Validate initData, extract Telegram user, auto-login or auto-register.

        Args:
            init_data: Raw URL-encoded initData from Telegram.WebApp.initData

        Returns:
            TelegramMiniAppResult with JWT tokens and user

        Raises:
            ValueError: If initData is invalid or expired
        """
        # Step 1: Validate HMAC signature and auth_date freshness
        user_info = self._telegram.validate_init_data(init_data)
        if not user_info:
            raise ValueError("Invalid or expired Telegram initData")

        telegram_id = user_info["id"]
        if not telegram_id:
            raise ValueError("Telegram user ID missing from initData")

        username = user_info.get("username")
        first_name = user_info.get("first_name")

        # Step 2: Look up user by telegram_id
        user = await self._user_repo.get_by_telegram_id(int(telegram_id))
        is_new_user = False

        if not user:
            # Step 3: Auto-register with Telegram-first onboarding
            login = OAuthLoginUseCase._generate_telegram_login(
                username=username,
                first_name=first_name,
                telegram_id=telegram_id,
            )

            # Ensure unique login
            existing = await self._user_repo.get_by_login(login)
            if existing:
                login = f"{login}_{secrets.token_hex(3)}"

            password_hash = await self._auth_service.hash_password(
                secrets.token_urlsafe(32)
            )
            user = AdminUserModel(
                login=login,
                telegram_id=int(telegram_id),
                password_hash=password_hash,
                role="viewer",
                is_active=True,
                is_email_verified=True,  # Telegram users are auto-verified
            )
            user = await self._user_repo.create(user)
            is_new_user = True

            logger.info(
                "Created new user from Telegram Mini App",
                extra={"user_id": str(user.id), "login": login},
            )

            # Create Remnawave VPN user (best-effort)
            if self._remnawave_gateway:
                try:
                    await self._remnawave_gateway.create_user(
                        username=login,
                        email="",
                        telegram_id=int(telegram_id),
                    )
                except Exception:
                    logger.exception(
                        "Failed to create Remnawave user for Mini App registration",
                        extra={"user_id": str(user.id)},
                    )
        else:
            logger.info(
                "Telegram Mini App login for existing user",
                extra={"user_id": str(user.id)},
            )

        await self._session.commit()

        # Step 4: Issue JWT tokens
        access_token, _, access_exp = self._auth_service.create_access_token(
            subject=str(user.id),
            role=user.role if isinstance(user.role, str) else user.role.value,
        )
        refresh_token, _, _ = self._auth_service.create_refresh_token(
            subject=str(user.id),
        )
        expires_in = int((access_exp - datetime.now(UTC)).total_seconds())

        return TelegramMiniAppResult(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            expires_in=expires_in,
            user=user,
            is_new_user=is_new_user,
        )
