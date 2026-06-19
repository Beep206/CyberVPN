"""Authenticated Telegram bot account linking for mobile users."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.database.models.mobile_user_model import MobileUserModel
from src.infrastructure.database.repositories.mobile_user_repo import MobileUserRepository


class MobileTelegramAccountLinkConflictError(ValueError):
    """Raised when a Telegram identity cannot be linked to the requested customer."""


class MobileTelegramAccountLinkingUseCase:
    """Link Telegram bot identities to mobile user accounts without touching OIDC subject data."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._users = MobileUserRepository(session)

    async def link_account(
        self,
        *,
        user_id: UUID,
        telegram_id: str | int,
        username: str | None = None,
    ) -> MobileUserModel:
        try:
            normalized_telegram_id = int(telegram_id)
        except (TypeError, ValueError) as exc:
            raise MobileTelegramAccountLinkConflictError("Invalid Telegram account identifier.") from exc

        user = await self._users.get_by_id(user_id)
        if user is None:
            raise MobileTelegramAccountLinkConflictError("Authenticated customer was not found.")

        existing_user = await self._users.get_by_telegram_id(normalized_telegram_id)
        if existing_user is not None and existing_user.id != user_id:
            raise MobileTelegramAccountLinkConflictError("Telegram account is already linked to another customer.")

        if user.telegram_id is not None and user.telegram_id != normalized_telegram_id:
            raise MobileTelegramAccountLinkConflictError(
                "Customer account already has a different Telegram identity linked."
            )

        try:
            user.telegram_id = normalized_telegram_id
            user.telegram_username = username
            await self._session.flush()
        except IntegrityError as exc:
            raise MobileTelegramAccountLinkConflictError(
                "Telegram account is already linked to another customer."
            ) from exc

        return user
