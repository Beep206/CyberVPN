"""Telegram bot deep-link authentication use case.

Validates a one-time token from a Telegram bot /login command,
looks up the user by telegram_id, and issues JWT tokens.
"""

import logging
from datetime import UTC, datetime
from uuid import UUID

import redis.asyncio as redis
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.services.auth_service import AuthService
from src.application.services.auth_session_issuer import AuthSessionIssuer, AuthSessionIssueRequest
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
        requires_2fa: bool = False,
        tfa_token: str | None = None,
    ) -> None:
        self.access_token = access_token
        self.refresh_token = refresh_token
        self.token_type = token_type
        self.expires_in = expires_in
        self.user = user
        self.requires_2fa = requires_2fa
        self.tfa_token = tfa_token


class TelegramBotLinkUseCase:
    """Authenticates users via one-time Telegram bot login link token."""

    def __init__(
        self,
        user_repo: AdminUserRepository,
        auth_service: AuthService,
        redis_client: redis.Redis,
        session: AsyncSession | None = None,
    ) -> None:
        self._user_repo = user_repo
        self._auth_service = auth_service
        self._redis = redis_client
        self._session_issuer = AuthSessionIssuer(auth_service=auth_service, session=session) if session else None

    async def execute(
        self,
        token: str,
        *,
        client_fingerprint: str | None = None,
        client_device_key: str | None = None,
        client_ip: str | None = None,
        client_ip_source: str | None = None,
        proxy_peer: str | None = None,
        user_agent: str | None = None,
        auth_realm_id: UUID | None = None,
        auth_realm_key: str | None = None,
        audience: str | None = None,
        principal_type: str = "admin",
        scope_family: str = "admin",
    ) -> TelegramBotLinkResult:
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

        if user.totp_enabled:
            tfa_token, _, _ = self._auth_service.create_access_token(
                subject=str(user.id),
                role="2fa_pending",
                extra={"type": "2fa_pending"},
                audience=audience,
                principal_type=principal_type,
                realm_id=str(auth_realm_id) if auth_realm_id else None,
                realm_key=auth_realm_key,
                scope_family=scope_family,
            )
            return TelegramBotLinkResult(
                access_token="",
                refresh_token="",
                token_type="bearer",
                expires_in=0,
                user=user,
                requires_2fa=True,
                tfa_token=tfa_token,
            )

        if self._session_issuer is None:
            access_token, _, access_exp = self._auth_service.create_access_token(
                subject=str(user.id),
                role=user.role if isinstance(user.role, str) else user.role.value,
                audience=audience,
                principal_type=principal_type,
                realm_id=str(auth_realm_id) if auth_realm_id else None,
                realm_key=auth_realm_key,
                scope_family=scope_family,
            )
            refresh_token, _, _ = self._auth_service.create_refresh_token(
                subject=str(user.id),
                fingerprint=client_fingerprint,
                audience=audience,
                principal_type=principal_type,
                realm_id=str(auth_realm_id) if auth_realm_id else None,
                realm_key=auth_realm_key,
                scope_family=scope_family,
            )
            return TelegramBotLinkResult(
                access_token=access_token,
                refresh_token=refresh_token,
                token_type="bearer",
                expires_in=int((access_exp - datetime.now(UTC)).total_seconds()),
                user=user,
            )

        issued_session = await self._session_issuer.issue_auth_session(
            AuthSessionIssueRequest(
                user_id=user.id,
                role=user.role if isinstance(user.role, str) else user.role.value,
                device_key=client_device_key,
                refresh_fingerprint=client_fingerprint,
                ip_address=client_ip,
                ip_source=client_ip_source,
                proxy_peer=proxy_peer,
                user_agent=user_agent,
                auth_realm_id=auth_realm_id,
                auth_realm_key=auth_realm_key,
                audience=audience,
                principal_class=principal_type,
                principal_subject=str(user.id),
                scope_family=scope_family,
                access_extra={"auth_method": "telegram_bot_link"},
                platform="web",
            )
        )

        return TelegramBotLinkResult(
            access_token=issued_session.access_token,
            refresh_token=issued_session.refresh_token,
            token_type=issued_session.token_type,
            expires_in=issued_session.expires_in,
            user=user,
        )
