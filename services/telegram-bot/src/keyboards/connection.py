"""Telegram connection flow keyboards."""

from __future__ import annotations

from typing import TYPE_CHECKING

from aiogram.types import InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

if TYPE_CHECKING:
    from collections.abc import Callable

    from aiogram.types import InlineKeyboardMarkup

    from src.config import BotSettings
    from src.models.connection import ConnectionPlatform

_INSTRUCTION_PLATFORMS: tuple[ConnectionPlatform, ...] = ("ios", "android", "windows", "macos", "linux")


def connection_keyboard(
    i18n: Callable[..., str],
    *,
    session_id: str,
) -> InlineKeyboardMarkup:
    """Build the private-chat connection action keyboard."""
    builder = InlineKeyboardBuilder()
    builder.button(
        text=i18n("bot-onboarding-connection-open-link-button"),
        callback_data=f"connection:open_link:{session_id}",
    )
    builder.button(
        text=i18n("bot-onboarding-connection-show-qr-button"),
        callback_data=f"connection:show_qr:{session_id}",
    )
    for platform in _INSTRUCTION_PLATFORMS:
        builder.button(
            text=i18n(f"bot-onboarding-connection-platform-{platform}"),
            callback_data=f"connection:instructions:{platform}:{session_id}",
        )
    builder.button(
        text=i18n("bot-onboarding-connection-mark-connected-button"),
        callback_data=f"connection:mark_connected:unknown:{session_id}",
    )
    builder.button(
        text=i18n("bot-onboarding-connection-dashboard-button"),
        callback_data=f"connection:dashboard:{session_id}",
    )
    builder.adjust(2, 2, 3, 1, 1)
    return builder.as_markup()


def connection_instruction_keyboard(
    i18n: Callable[..., str],
    *,
    session_id: str,
    platform: ConnectionPlatform,
) -> InlineKeyboardMarkup:
    """Build platform instruction follow-up actions."""
    builder = InlineKeyboardBuilder()
    builder.button(
        text=i18n("bot-onboarding-connection-open-link-button"),
        callback_data=f"connection:open_link:{session_id}",
    )
    builder.button(
        text=i18n("bot-onboarding-connection-show-qr-button"),
        callback_data=f"connection:show_qr:{session_id}",
    )
    builder.button(
        text=i18n("bot-onboarding-connection-mark-connected-button"),
        callback_data=f"connection:mark_connected:{platform}:{session_id}",
    )
    builder.button(text=i18n("btn-back"), callback_data=f"connection:back:{session_id}")
    builder.adjust(2, 1, 1)
    return builder.as_markup()


def connection_private_chat_keyboard(
    i18n: Callable[..., str],
    settings: BotSettings | None,
) -> InlineKeyboardMarkup | None:
    """Build a safe deep-link prompt for non-private chats."""
    if settings is None:
        return None

    username = settings.bot_username or settings.staging_bot_username or settings.production_bot_username
    if username:
        username = username.removeprefix("@")
        return InlineKeyboardBuilder(
            [
                [
                    InlineKeyboardButton(
                        text=i18n("bot-onboarding-connection-open-private-chat-button"),
                        url=f"https://t.me/{username}?start=connect",
                    )
                ]
            ]
        ).as_markup()

    if settings.miniapp_url is not None:
        return InlineKeyboardBuilder(
            [
                [
                    InlineKeyboardButton(
                        text=i18n("bot-onboarding-connection-open-private-chat-button"),
                        url=str(settings.miniapp_url),
                    )
                ]
            ]
        ).as_markup()

    return None


def connection_help_keyboard(i18n: Callable[..., str]) -> InlineKeyboardMarkup:
    """Build command-style help actions."""
    builder = InlineKeyboardBuilder()
    builder.button(text=i18n("bot-onboarding-connection-connect-button"), callback_data="menu:connect")
    builder.button(text=i18n("bot-onboarding-connection-instructions-button"), callback_data="connection:instructions")
    builder.button(text=i18n("btn-support"), callback_data="menu:support")
    builder.adjust(1)
    return builder.as_markup()
