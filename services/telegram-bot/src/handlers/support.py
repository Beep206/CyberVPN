"""CyberVPN Telegram Bot — Support handler.

Displays support contact information to users.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Callable

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message

router = Router(name="support")

if TYPE_CHECKING:
    from src.config import BotSettings


def _normalize_support_contact(raw_contact: str) -> str:
    """Format configured support username as Telegram handle."""
    return raw_contact if raw_contact.startswith("@") else f"@{raw_contact}"


def _render_support_message(
    i18n: Callable[..., str],
    settings: BotSettings,
) -> str:
    """Build localized support message shared by menu and command entrypoints."""
    return i18n("support-message", contact=_normalize_support_contact(settings.support_username))


@router.message(Command("support", "paysupport"))
async def support_command(
    message: Message,
    i18n: Callable[..., str],
    settings: BotSettings,
) -> None:
    """Provide payment-support contact via explicit Telegram commands."""
    await message.answer(_render_support_message(i18n, settings))


@router.callback_query(F.data == "menu:support")
async def support_menu(
    callback: CallbackQuery,
    i18n: Callable[..., str],
    settings: BotSettings,
) -> None:
    """Show support contact information.

    Args:
        callback: Callback query from support menu button.
        i18n: Translator function.
        settings: Bot settings with support username.
    """
    await callback.answer()
    await callback.message.edit_text(
        _render_support_message(i18n, settings),
    )
