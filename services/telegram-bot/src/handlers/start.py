from __future__ import annotations

from typing import TYPE_CHECKING

import structlog
from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import Message

from keyboards.main import main_menu_keyboard

if TYPE_CHECKING:
    from aiogram_i18n import I18nContext

    from clients.api_client import APIClient
    from config.settings import Settings

logger = structlog.get_logger(__name__)

router = Router(name="start")


@router.message(CommandStart())
async def start_handler(
    message: Message,
    i18n: I18nContext,
    settings: Settings,
    api_client: APIClient,
) -> None:
    """Handle /start command with deep link support."""
    user_id = message.from_user.id
    username = message.from_user.username or ""
    first_name = message.from_user.first_name or ""
    last_name = message.from_user.last_name or ""
    language_code = message.from_user.language_code or "en"

    # Parse deep links
    referrer_id = None
    promo_code = None

    if message.text and " " in message.text:
        deep_link = message.text.split(" ", 1)[1]

        if deep_link.startswith("ref_"):
            try:
                referrer_id = int(deep_link[4:])
                logger.info("referral_link_detected", user_id=user_id, referrer_id=referrer_id)
            except ValueError:
                logger.warning("invalid_referral_link", deep_link=deep_link)

        elif deep_link.startswith("promo_"):
            promo_code = deep_link[6:]
            logger.info("promo_link_detected", user_id=user_id, promo_code=promo_code)

    # Register user via API
    try:
        user_data = {
            "telegram_id": user_id,
            "username": username,
            "first_name": first_name,
            "last_name": last_name,
            "language_code": language_code,
        }

        if referrer_id:
            user_data["referrer_id"] = referrer_id

        user = await api_client.register_user(user_data)
        logger.info("user_registered", user_id=user_id, user=user)

        # Auto-activate promo code if provided
        if promo_code:
            try:
                await api_client.activate_promo_code(user_id, promo_code)
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
        "welcome-message",
        name=first_name or username or str(user_id),
    )

    if referrer_id:
        welcome_text += "\n\n" + i18n.get("welcome-referral-bonus")

    await message.answer(
        text=welcome_text,
        reply_markup=main_menu_keyboard(i18n),
    )

    logger.info("start_command_completed", user_id=user_id)
