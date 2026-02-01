from __future__ import annotations

from typing import TYPE_CHECKING

import structlog
from aiogram import F, Router
from aiogram.types import BufferedInputFile, CallbackQuery

if TYPE_CHECKING:
    from aiogram_i18n import I18nContext

    from src.services.api_client import CyberVPNAPIClient

logger = structlog.get_logger(__name__)

router = Router(name="config")


@router.callback_query(F.data == "config:menu")
async def config_menu_handler(
    callback: CallbackQuery,
    i18n: I18nContext,
) -> None:
    """Show configuration delivery options."""
    from src.keyboards.config import config_delivery_keyboard

    await callback.message.edit_text(
        text=i18n.get("config-delivery-prompt"),
        reply_markup=config_delivery_keyboard(i18n),
    )
    await callback.answer()


@router.callback_query(F.data == "config:link")
async def send_config_link_handler(
    callback: CallbackQuery,
    i18n: I18nContext,
    api_client: CyberVPNAPIClient,
) -> None:
    """Send subscription config link."""
    user_id = callback.from_user.id

    try:
        config = await api_client.get_user_config(user_id)
        config_url = config.get("config_url") or config.get("url") or config.get("subscription_url")

        if not config_url:
            await callback.answer(i18n.get("error-config-not-ready"), show_alert=True)
            return

        await callback.message.answer(
            text=i18n.get("config-link-message", url=config_url),
        )

        subscription_id = config.get("subscription_id") if isinstance(config, dict) else None
        logger.info("config_link_sent", user_id=user_id, subscription_id=subscription_id)

    except Exception as e:
        logger.error("config_link_error", user_id=user_id, error=str(e))
        await callback.answer(i18n.get("error-generic"), show_alert=True)

    await callback.answer()


@router.callback_query(F.data == "config:qr")
async def send_config_qr_handler(
    callback: CallbackQuery,
    i18n: I18nContext,
    api_client: CyberVPNAPIClient,
) -> None:
    """Send subscription config QR code."""
    user_id = callback.from_user.id

    try:
        config = await api_client.get_user_config(user_id)
        config_url = config.get("config_url") or config.get("url") or config.get("subscription_url")

        if not config_url:
            await callback.answer(i18n.get("error-config-not-ready"), show_alert=True)
            return

        from src.services.qr_service import generate_subscription_qr

        qr_buffer = generate_subscription_qr(config_url)
        qr_file = BufferedInputFile(qr_buffer.getvalue(), filename="config_qr.png")

        await callback.message.answer_photo(
            photo=qr_file,
            caption=i18n.get("config-qr-caption"),
        )

        logger.info("config_qr_sent", user_id=user_id)

    except Exception as e:
        logger.error("config_qr_error", user_id=user_id, error=str(e))
        await callback.answer(i18n.get("error-generic"), show_alert=True)

    await callback.answer()


@router.callback_query(F.data == "config:instructions")
async def send_config_instructions_handler(
    callback: CallbackQuery,
    i18n: I18nContext,
) -> None:
    """Send configuration instructions."""
    instructions = i18n.get("config-instructions")

    await callback.message.answer(
        text=instructions,
    )

    logger.info("config_instructions_sent", user_id=callback.from_user.id)
    await callback.answer()
