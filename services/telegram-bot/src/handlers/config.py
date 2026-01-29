from __future__ import annotations

from typing import TYPE_CHECKING

import structlog
from aiogram import F, Router
from aiogram.types import BufferedInputFile, CallbackQuery

if TYPE_CHECKING:
    from aiogram_i18n import I18nContext

    from clients.api_client import APIClient

logger = structlog.get_logger(__name__)

router = Router(name="config")


@router.callback_query(F.data == "config:link")
async def send_config_link_handler(
    callback: CallbackQuery,
    i18n: I18nContext,
    api_client: APIClient,
) -> None:
    """Send subscription config link."""
    user_id = callback.from_user.id

    try:
        # Get active subscription
        subscriptions = await api_client.get_user_subscriptions(user_id)
        active_subs = [sub for sub in subscriptions if sub.get("status") == "active"]

        if not active_subs:
            await callback.answer(i18n.get("error-no-active-subscription"), show_alert=True)
            return

        subscription = active_subs[0]
        config_url = subscription.get("config_url")

        if not config_url:
            await callback.answer(i18n.get("error-config-not-ready"), show_alert=True)
            return

        await callback.message.answer(
            text=i18n.get("config-link-message", url=config_url),
        )

        logger.info("config_link_sent", user_id=user_id, subscription_id=subscription.get("id"))

    except Exception as e:
        logger.error("config_link_error", user_id=user_id, error=str(e))
        await callback.answer(i18n.get("error-generic"), show_alert=True)

    await callback.answer()


@router.callback_query(F.data == "config:qr")
async def send_config_qr_handler(
    callback: CallbackQuery,
    i18n: I18nContext,
    api_client: APIClient,
) -> None:
    """Send subscription config QR code."""
    user_id = callback.from_user.id

    try:
        # Get active subscription
        subscriptions = await api_client.get_user_subscriptions(user_id)
        active_subs = [sub for sub in subscriptions if sub.get("status") == "active"]

        if not active_subs:
            await callback.answer(i18n.get("error-no-active-subscription"), show_alert=True)
            return

        subscription = active_subs[0]
        subscription_id = subscription.get("id")

        # Get QR code from API
        qr_data = await api_client.get_subscription_qr(subscription_id)

        if not qr_data:
            await callback.answer(i18n.get("error-qr-generation-failed"), show_alert=True)
            return

        # Send QR code as photo
        qr_file = BufferedInputFile(qr_data, filename="config_qr.png")

        await callback.message.answer_photo(
            photo=qr_file,
            caption=i18n.get("config-qr-caption"),
        )

        logger.info("config_qr_sent", user_id=user_id, subscription_id=subscription_id)

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
