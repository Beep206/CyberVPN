"""Authenticated Telegram OIDC account unlinking for mobile users."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from src.application.dto.mobile_auth import TelegramLinkResponseDTO
from src.domain.exceptions import UserNotFoundError
from src.infrastructure.database.repositories.mobile_user_repo import MobileUserRepository


@dataclass
class MobileTelegramOIDCUnlinkUseCase:
    """Remove Telegram identity linkage from the current mobile user."""

    user_repo: MobileUserRepository

    async def execute(self, *, user_id: UUID) -> TelegramLinkResponseDTO:
        user = await self.user_repo.get_by_id(user_id)
        if not user:
            raise UserNotFoundError(str(user_id))

        user.telegram_subject = None
        user.telegram_id = None
        user.telegram_username = None
        await self.user_repo.update(user)

        return TelegramLinkResponseDTO(
            linked=False,
            provider="telegram",
            telegram_username=None,
        )
