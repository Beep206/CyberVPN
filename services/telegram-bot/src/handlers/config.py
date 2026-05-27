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
_CONFIG_SELECT_SUBSCRIPTION_FALLBACK = (
    "📦 <b>Choose subscription</b>\n\n"
    "You have multiple active subscriptions. Choose which VPN config to send."
)


def _select_subscription_url(config: dict[str, object]) -> str | None:
    """Return only an HTTP(S) subscription URL, never a raw proxy URI."""
    for key in (
        "subscription_url",
        "subscriptionUrl",
        "config_url",
        "configUrl",
        "url",
        "config_string",
        "configString",
        "config",
    ):
        value = config.get(key)
        if not isinstance(value, str):
            continue
        candidate = value.strip()
        if candidate.lower().startswith(("https://", "http://")):
            return candidate
    return None


def _subscription_key(subscription: dict[str, object] | None) -> str | None:
    if not subscription:
        return None
    raw = subscription.get("subscription_key") or subscription.get("subscriptionKey")
    return str(raw) if raw else None


def _config_select_subscription_text(i18n: I18nContext) -> str:
    try:
        text = i18n.get("config-select-subscription")
    except Exception:
        text = _CONFIG_SELECT_SUBSCRIPTION_FALLBACK
    if text == "config-select-subscription":
        return _CONFIG_SELECT_SUBSCRIPTION_FALLBACK
    return text


async def _selectable_subscriptions(
    *,
    api_client: CyberVPNAPIClient,
    telegram_id: int,
) -> list[dict[str, object]]:
    subscriptions = await api_client.get_user_subscriptions(telegram_id)
    return [
        subscription
        for subscription in subscriptions
        if isinstance(subscription, dict)
        and subscription.get("status") in {"active", "trial"}
        and _subscription_key(subscription)
    ]


async def _prompt_subscription_selection(
    *,
    callback: CallbackQuery,
    i18n: I18nContext,
    subscriptions: list[dict[str, object]],
    action: str,
) -> None:
    from src.keyboards.config import subscription_select_keyboard

    await callback.message.edit_text(
        text=_config_select_subscription_text(i18n),
        reply_markup=subscription_select_keyboard(subscriptions, action=action, i18n=i18n.get),
    )


async def _send_config_link(
    *,
    callback: CallbackQuery,
    i18n: I18nContext,
    api_client: CyberVPNAPIClient,
    subscription_key: str | None = None,
) -> bool:
    user_id = callback.from_user.id
    config = await api_client.get_user_config(user_id, subscription_key=subscription_key)
    config_url = _select_subscription_url(config)

    if not config_url:
        await callback.answer(i18n.get("error-config-not-ready"), show_alert=True)
        return False

    await callback.message.answer(
        text=i18n.get("config-link-message", url=config_url),
    )

    logger.info(
        "config_link_sent",
        user_id=user_id,
        subscription_key=subscription_key or config.get("subscription_key"),
    )
    return True


async def _send_config_qr(
    *,
    callback: CallbackQuery,
    i18n: I18nContext,
    api_client: CyberVPNAPIClient,
    subscription_key: str | None = None,
) -> bool:
    user_id = callback.from_user.id
    config = await api_client.get_user_config(user_id, subscription_key=subscription_key)
    config_url = _select_subscription_url(config)

    if not config_url:
        await callback.answer(i18n.get("error-config-not-ready"), show_alert=True)
        return False

    from src.services.qr_service import generate_subscription_qr

    qr_buffer = generate_subscription_qr(config_url)
    qr_file = BufferedInputFile(qr_buffer.getvalue(), filename="config_qr.png")

    await callback.message.answer_photo(
        photo=qr_file,
        caption=i18n.get("config-qr-caption"),
    )

    logger.info("config_qr_sent", user_id=user_id, subscription_key=subscription_key)
    return True


async def _maybe_prompt_subscription_or_send(
    *,
    callback: CallbackQuery,
    i18n: I18nContext,
    api_client: CyberVPNAPIClient,
    action: str,
) -> None:
    user_id = callback.from_user.id
    subscriptions = await _selectable_subscriptions(api_client=api_client, telegram_id=user_id)
    if len(subscriptions) > 1:
        await _prompt_subscription_selection(
            callback=callback,
            i18n=i18n,
            subscriptions=subscriptions,
            action=action,
        )
        return

    selected_key = _subscription_key(subscriptions[0]) if subscriptions else None
    if action == "link":
        await _send_config_link(
            callback=callback,
            i18n=i18n,
            api_client=api_client,
            subscription_key=selected_key,
        )
    else:
        await _send_config_qr(
            callback=callback,
            i18n=i18n,
            api_client=api_client,
            subscription_key=selected_key,
        )


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
        await _maybe_prompt_subscription_or_send(
            callback=callback,
            i18n=i18n,
            api_client=api_client,
            action="link",
        )

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
        await _maybe_prompt_subscription_or_send(
            callback=callback,
            i18n=i18n,
            api_client=api_client,
            action="qr",
        )

    except Exception as e:
        logger.error("config_qr_error", user_id=user_id, error=str(e))
        await callback.answer(i18n.get("error-generic"), show_alert=True)

    await callback.answer()


@router.callback_query(F.data.startswith("config:pick:"))
async def send_selected_config_handler(
    callback: CallbackQuery,
    i18n: I18nContext,
    api_client: CyberVPNAPIClient,
) -> None:
    """Send config for the selected subscription from a compact indexed callback."""
    user_id = callback.from_user.id
    parts = (callback.data or "").split(":")
    if len(parts) != 4 or parts[2] not in {"link", "qr"}:
        await callback.answer(i18n.get("error-generic"), show_alert=True)
        return

    action = parts[2]
    try:
        index = int(parts[3])
    except ValueError:
        await callback.answer(i18n.get("error-generic"), show_alert=True)
        return

    try:
        subscriptions = await _selectable_subscriptions(api_client=api_client, telegram_id=user_id)
        selected = subscriptions[index] if 0 <= index < len(subscriptions) else None
        selected_key = _subscription_key(selected)
        if not selected_key:
            await callback.answer(i18n.get("error-config-not-ready"), show_alert=True)
            return

        if action == "link":
            await _send_config_link(
                callback=callback,
                i18n=i18n,
                api_client=api_client,
                subscription_key=selected_key,
            )
        else:
            await _send_config_qr(
                callback=callback,
                i18n=i18n,
                api_client=api_client,
                subscription_key=selected_key,
            )
    except Exception as e:
        logger.error("config_selected_delivery_error", user_id=user_id, error=str(e), action=action)
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
