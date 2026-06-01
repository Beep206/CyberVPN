from __future__ import annotations

from datetime import UTC, datetime
from html import escape
from typing import TYPE_CHECKING

import structlog
from aiogram import F, Router
from aiogram.filters import Command

from src.keyboards.menu import main_menu_keyboard, profile_kb
from src.keyboards.referral import invite_codes_keyboard
from src.keyboards.subscription import subscription_keyboard

if TYPE_CHECKING:
    from aiogram.types import CallbackQuery, InlineKeyboardMarkup, Message
    from aiogram_i18n import I18nContext

    from src.config import BotSettings
    from src.services.api_client import CyberVPNAPIClient

logger = structlog.get_logger(__name__)

router = Router(name="menu")


def _parse_datetime(value: object) -> datetime | None:
    if isinstance(value, datetime):
        return value
    if not isinstance(value, str) or not value:
        return None

    normalized = value.replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(normalized)
    except ValueError:
        return None


def _format_invite_date(value: object) -> str:
    parsed = _parse_datetime(value)
    if parsed is None:
        return "N/A"
    return parsed.astimezone(UTC).strftime("%Y-%m-%d")


def _is_invite_expired(invite: dict[str, object]) -> bool:
    expires_at = _parse_datetime(invite.get("expires_at"))
    if expires_at is None:
        return False
    return expires_at.astimezone(UTC) <= datetime.now(UTC)


def _invite_status_key(invite: dict[str, object]) -> str:
    if bool(invite.get("is_used")):
        return "my-invites-status-used"
    if _is_invite_expired(invite):
        return "my-invites-status-expired"
    return "my-invites-status-active"


def _render_invite_items(invites: list[dict[str, object]], i18n: I18nContext) -> str:
    if not invites:
        return i18n.get("my-invites-empty")

    items: list[str] = []
    for invite in invites[:10]:
        code = escape(str(invite.get("code") or "N/A"))
        free_days = int(invite.get("free_days") or 0)
        status = i18n.get(_invite_status_key(invite))
        expires = _format_invite_date(invite.get("expires_at"))
        created = _format_invite_date(invite.get("created_at"))
        items.append(
            i18n.get(
                "my-invites-item",
                code=code,
                days=free_days,
                status=status,
                expires=expires,
                created=created,
            )
        )

    return "\n\n".join(items)


async def _build_my_invites_response(
    *,
    user_id: int,
    i18n: I18nContext,
    api_client: CyberVPNAPIClient,
) -> tuple[str, InlineKeyboardMarkup]:
    invites = await api_client.get_invite_codes(user_id)
    active_count = sum(
        1
        for invite in invites
        if not bool(invite.get("is_used")) and not _is_invite_expired(invite)
    )
    text = i18n.get(
        "my-invites-info",
        count=len(invites),
        active_count=active_count,
        items=_render_invite_items(invites, i18n),
    )
    return text, invite_codes_keyboard(i18n)


async def _build_connect_menu_response(
    *,
    user_id: int,
    i18n: I18nContext,
    api_client: CyberVPNAPIClient,
) -> tuple[str, InlineKeyboardMarkup]:
    entitlements = await api_client.get_current_entitlements(user_id)
    status = str(entitlements.get("status") or "none")

    if status in {"active", "trial"}:
        service_state = await api_client.get_current_service_state(user_id)
        text = i18n.get(
            "subscription-active",
            plan=entitlements.get("display_name") or entitlements.get("plan_code") or "N/A",
            expires=entitlements.get("expires_at", "N/A"),
        )
        channel = service_state.get("access_delivery_channel") or {}
        purchase_context = service_state.get("purchase_context") or {}
        provider_name = service_state.get("provider_name") or "N/A"
        channel_type = channel.get("channel_type")
        source_type = purchase_context.get("source_type")
        details: list[str] = [f"Provider: {provider_name}"]
        if channel_type:
            details.append(f"Channel: {channel_type}")
        if source_type:
            details.append(f"Source: {source_type}")
        text = f"{text}\n\n" + "\n".join(details)
    else:
        text = i18n.get("subscription-none")

    return text, subscription_keyboard(i18n, has_active=status in {"active", "trial"})


@router.message(Command("menu"))
async def main_menu_command_handler(
    message: Message,
    i18n: I18nContext,
    api_client: CyberVPNAPIClient,
    settings: BotSettings | None = None,
) -> None:
    """Open the main menu from the Telegram command list."""
    if message.from_user is None:
        return

    user = None
    try:
        user = await api_client.get_user(message.from_user.id)
    except Exception as e:
        logger.warning("menu_command_user_fetch_failed", user_id=message.from_user.id, error=str(e))

    await message.answer(
        text=i18n.get("menu-main-title"),
        reply_markup=main_menu_keyboard(i18n, user, settings=settings),
    )


@router.callback_query(F.data == "menu:main")
async def main_menu_handler(
    callback: CallbackQuery,
    i18n: I18nContext,
    api_client: CyberVPNAPIClient,
    settings: BotSettings | None = None,
) -> None:
    """Handle main menu callback."""
    user = None
    try:
        user = await api_client.get_user(callback.from_user.id)
    except Exception as e:
        logger.warning("menu_user_fetch_failed", user_id=callback.from_user.id, error=str(e))

    await callback.message.edit_text(
        text=i18n.get("menu-main-title"),
        reply_markup=main_menu_keyboard(i18n, user, settings=settings),
    )
    await callback.answer()


@router.callback_query(F.data.in_({"menu:connect", "menu:vpn", "menu:subscription"}))
async def connect_menu_handler(
    callback: CallbackQuery,
    i18n: I18nContext,
    api_client: CyberVPNAPIClient,
) -> None:
    """Handle connect/subscription menu callback."""
    user_id = callback.from_user.id

    try:
        text, reply_markup = await _build_connect_menu_response(
            user_id=user_id,
            i18n=i18n,
            api_client=api_client,
        )

        await callback.message.edit_text(
            text=text,
            reply_markup=reply_markup,
        )
    except Exception as e:
        logger.error("connect_menu_error", user_id=user_id, error=str(e))
        await callback.answer(i18n.get("error-generic"), show_alert=True)
        return

    await callback.answer()


@router.message(Command("connect"))
async def connect_command_handler(
    message: Message,
    i18n: I18nContext,
    api_client: CyberVPNAPIClient,
) -> None:
    """Open the VPN access/config surface from the Telegram command list."""
    if message.from_user is None:
        return

    user_id = message.from_user.id
    try:
        text, reply_markup = await _build_connect_menu_response(
            user_id=user_id,
            i18n=i18n,
            api_client=api_client,
        )
    except Exception as e:
        logger.error("connect_command_error", user_id=user_id, error=str(e))
        await message.answer(i18n.get("error-generic"))
        return

    await message.answer(text=text, reply_markup=reply_markup)


@router.callback_query(F.data.in_({"menu:invite", "growth:invites"}))
async def invite_menu_handler(
    callback: CallbackQuery,
    i18n: I18nContext,
    api_client: CyberVPNAPIClient,
) -> None:
    """Handle invite-code menu callback."""
    user_id = callback.from_user.id

    try:
        text, reply_markup = await _build_my_invites_response(
            user_id=user_id,
            i18n=i18n,
            api_client=api_client,
        )

        await callback.message.edit_text(
            text=text,
            reply_markup=reply_markup,
        )
    except Exception as e:
        logger.error("invite_menu_error", user_id=user_id, error=str(e))
        await callback.answer(i18n.get("error-generic"), show_alert=True)
        return

    await callback.answer()


@router.callback_query(F.data == "referral:invites")
async def invite_codes_refresh_handler(
    callback: CallbackQuery,
    i18n: I18nContext,
    api_client: CyberVPNAPIClient,
) -> None:
    """Refresh the invite-code list from the bot UI."""
    await invite_menu_handler(callback, i18n, api_client)


@router.message(Command("invites"))
async def invite_codes_command_handler(
    message: Message,
    i18n: I18nContext,
    api_client: CyberVPNAPIClient,
) -> None:
    """Open manually issued invite codes from the Telegram command list."""
    if message.from_user is None:
        return

    user_id = message.from_user.id
    try:
        text, reply_markup = await _build_my_invites_response(
            user_id=user_id,
            i18n=i18n,
            api_client=api_client,
        )
    except Exception as e:
        logger.error("invite_codes_command_error", user_id=user_id, error=str(e))
        await message.answer(i18n.get("error-generic"))
        return

    await message.answer(text=text, reply_markup=reply_markup)


@router.callback_query(F.data == "menu:profile")
async def profile_menu_handler(
    callback: CallbackQuery,
    i18n: I18nContext,
    api_client: CyberVPNAPIClient,
) -> None:
    """Handle profile menu callback."""
    user_id = callback.from_user.id

    try:
        # Get user profile
        user = await api_client.get_user(user_id)
        username = user.get("username")
        username_display = f"@{username}" if username else "N/A"
        telegram_id = user.get("telegram_id", user_id)

        text = i18n.get(
            "profile-info",
            telegram_id=telegram_id,
            username=username_display,
            language=user.get("language_code", "en").upper(),
            registered=user.get("created_at", "N/A"),
        )

        await callback.message.edit_text(
            text=text,
            reply_markup=profile_kb(i18n),
        )
    except Exception as e:
        logger.error("profile_menu_error", user_id=user_id, error=str(e))
        await callback.answer(i18n.get("error-generic"), show_alert=True)
        return

    await callback.answer()


@router.callback_query(F.data == "menu:support")
async def support_menu_handler(
    callback: CallbackQuery,
    i18n: I18nContext,
    settings: BotSettings,
) -> None:
    """Handle support menu callback."""
    support_username = settings.support_username
    contact = support_username if support_username.startswith("@") else f"@{support_username}"
    support_text = i18n.get("support-message", contact=contact)

    await callback.message.edit_text(
        text=support_text,
    )
    await callback.answer()
