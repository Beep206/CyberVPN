"""Authenticated Telegram OIDC account linking for mobile users."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from src.application.dto.mobile_auth import (
    TelegramLinkResponseDTO,
    TelegramOIDCLinkRequestDTO,
)
from src.application.services.telegram_oidc_auth import TelegramOIDCAuthService
from src.domain.exceptions import UserNotFoundError, ValidationError
from src.infrastructure.database.repositories.mobile_user_repo import MobileUserRepository


@dataclass
class MobileTelegramOIDCLinkUseCase:
    """Link a validated Telegram OIDC identity to the current mobile user."""

    user_repo: MobileUserRepository
    telegram_oidc_service: TelegramOIDCAuthService

    async def execute(
        self,
        *,
        user_id: UUID,
        request: TelegramOIDCLinkRequestDTO,
    ) -> TelegramLinkResponseDTO:
        user = await self.user_repo.get_by_id(user_id)
        if not user:
            raise UserNotFoundError(str(user_id))

        telegram_user = await self.telegram_oidc_service.validate_id_token(request.id_token)

        existing_subject = await self.user_repo.get_by_telegram_subject(telegram_user.subject)
        if existing_subject is not None and existing_subject.id != user.id:
            raise ValidationError(
                "Telegram identity is already linked to another account",
                {"reason": "subject_conflict"},
            )

        if telegram_user.telegram_id is not None:
            existing_telegram_id = await self.user_repo.get_by_telegram_id(telegram_user.telegram_id)
            if existing_telegram_id is not None and existing_telegram_id.id != user.id:
                raise ValidationError(
                    "Telegram identity is already linked to another account",
                    {"reason": "telegram_id_conflict"},
                )

        user.telegram_subject = telegram_user.subject
        user.telegram_id = telegram_user.telegram_id
        user.telegram_username = telegram_user.preferred_username
        await self.user_repo.update(user)

        return TelegramLinkResponseDTO(
            linked=True,
            provider="telegram",
            telegram_username=user.telegram_username,
        )
