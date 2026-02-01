from __future__ import annotations

from typing import TYPE_CHECKING, Any

import structlog
from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import Message

from src.keyboards.menu import main_menu_keyboard

if TYPE_CHECKING:
    from aiogram_i18n import I18nContext

    from src.services.api_client import CyberVPNAPIClient

logger = structlog.get_logger(__name__)

router = Router(name="start")


@router.message(CommandStart())
async def start_handler(
    message: Message,
    i18n: I18nContext,
    api_client: CyberVPNAPIClient,
    user: dict[str, Any] | None = None,
    referrer_id: int | None = None,
    promo_code: str | None = None,
) -> None:
    """Handle /start command with deep link support."""
    if message.from_user is None:
        return

    is_new_user = user is None
    user_id = message.from_user.id
    username = message.from_user.username or ""
    first_name = message.from_user.first_name or ""
    last_name = message.from_user.last_name or ""
    language_code = message.from_user.language_code or "en"

    # Update user data on /start and ensure registration exists
    try:
        if user is None:
            user = await api_client.register_user(
                telegram_id=user_id,
                username=username or None,
                language=language_code,
                referrer_id=referrer_id,
            )
            logger.info("user_registered", user_id=user_id, user=user)
        else:
            await api_client.update_user(
                user_id,
                {
                    "username": username or None,
                    "language": language_code,
                },
            )

        # Auto-activate promo code if provided
        if promo_code:
            try:
                await api_client.activate_promocode(user_id, promo_code)
                await message.answer(i18n.get("promo-activated", code=promo_code))
                logger.info("promo_activated_on_start", user_id=user_id, promo_code=promo_code)
            except Exception as e:
                logger.warning("promo_activation_failed", user_id=user_id, promo_code=promo_code, error=str(e))

    except Exception as e:
        logger.error("user_registration_failed", user_id=user_id, error=str(e))
        await message.answer(i18n.get("error-registration-failed"))
        return

    # Send welcome message with main menu
    welcome_text = i18n.get(
        "welcome-message" if is_new_user else "welcome-back",
        name=first_name or username or str(user_id),
    )

    if referrer_id:
        welcome_text += "\n\n" + i18n.get("welcome-referral-bonus")

    await message.answer(
        text=welcome_text,
        reply_markup=main_menu_keyboard(i18n),
    )

    logger.info("start_command_completed", user_id=user_id)
