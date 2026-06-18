from __future__ import annotations

from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.use_cases.auth.account_linking import AccountLinkingUseCase
from src.infrastructure.database.models.oauth_account_model import OAuthAccount
from src.infrastructure.database.repositories.admin_user_repo import AdminUserRepository


class TelegramAccountLinkConflictError(ValueError):
    """Raised when a Telegram identity cannot be linked to the requested user."""


class TelegramAccountLinkingUseCase:
    """Keep the Telegram OAuth identity and canonical admin_users.telegram_id in sync."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._account_linking = AccountLinkingUseCase(session)
        self._users = AdminUserRepository(session)

    async def link_account(
        self,
        *,
        user_id: UUID,
        telegram_id: str | int,
        username: str | None = None,
    ) -> OAuthAccount:
        try:
            normalized_telegram_id = int(telegram_id)
        except (TypeError, ValueError) as exc:
            raise TelegramAccountLinkConflictError("Invalid Telegram account identifier.") from exc

        user = await self._users.get_by_id(user_id)
        if user is None:
            raise TelegramAccountLinkConflictError("Authenticated user was not found.")

        existing_user = await self._users.get_by_telegram_id(normalized_telegram_id)
        if existing_user is not None and existing_user.id != user_id:
            raise TelegramAccountLinkConflictError("Telegram account is already linked to another user.")

        try:
            account = await self._account_linking.link_account(
                user_id=user_id,
                provider="telegram",
                provider_user_id=str(normalized_telegram_id),
                provider_username=username,
            )
            user.telegram_id = normalized_telegram_id
            await self._session.flush()
        except ValueError as exc:
            raise TelegramAccountLinkConflictError(str(exc)) from exc
        except IntegrityError as exc:
            raise TelegramAccountLinkConflictError("Telegram account is already linked to another user.") from exc

        return account

    async def unlink_account(self, *, user_id: UUID) -> None:
        user = await self._users.get_by_id(user_id)
        if user is None:
            raise TelegramAccountLinkConflictError("Authenticated user was not found.")

        await self._account_linking.unlink_account(user_id, "telegram")
        user.telegram_id = None
        await self._session.flush()
