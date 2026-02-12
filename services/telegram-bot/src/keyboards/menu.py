"""Menu keyboards for CyberVPN Telegram Bot.

Provides main menu and profile action keyboards with subscription
status integration.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

if TYPE_CHECKING:
    from collections.abc import Callable

    from src.models.user import UserDTO, UserStatus


def main_menu_kb(i18n: Callable[[str], str], user: UserDTO) -> InlineKeyboardMarkup:
    """Build full main menu keyboard based on user profile.

    Args:
        i18n: Fluent translator function for localization.
        user: User data transfer object with subscription status.

    Returns:
        InlineKeyboardMarkup with menu options tailored to user status.
    """
    builder = InlineKeyboardBuilder()

    # Determine subscription state
    has_active_subscription = user.status in {
        "active",
        "ACTIVE",
        UserStatus.ACTIVE if hasattr(UserStatus, "ACTIVE") else None,
    }

    # Connection/Subscription section
    if has_active_subscription:
        builder.button(text=i18n("btn-connect"), callback_data="menu:connect", style="primary")
        builder.button(text=i18n("btn-extend"), callback_data="subscription:buy", style="primary")
        builder.button(text=i18n("btn-subscription"), callback_data="account:subscriptions", style="primary")
    else:
        # Show trial button if user has no subscription status
        if user.status in {"none", "NONE", UserStatus.NONE}:
            builder.button(text=i18n("btn-trial"), callback_data="trial:activate", style="primary")
        builder.button(text=i18n("btn-buy"), callback_data="subscription:buy", style="primary")

    # Profile and account
    builder.button(text=i18n("btn-profile"), callback_data="account:profile", style="primary")
    builder.button(text=i18n("btn-invite"), callback_data="menu:invite", style="primary")

    # Settings
    builder.button(text=i18n("btn-language"), callback_data="account:language", style="primary")

    # Support
    builder.button(text=i18n("btn-support"), callback_data="menu:support", style="primary")

    # Admin panel for privileged users
    if user.is_admin:
        builder.button(
            text=i18n("btn-admin-panel"),
            callback_data="admin:menu",
            style="primary",
        )

    # Layout: 2 buttons per row for balance
    builder.adjust(2)

    return builder.as_markup()


def profile_kb(i18n: Callable[[str], str]) -> InlineKeyboardMarkup:
    """Build profile actions keyboard.

    Args:
        i18n: Fluent translator function for localization.

    Returns:
        InlineKeyboardMarkup with profile management options.
    """
    builder = InlineKeyboardBuilder()

    builder.button(text=i18n("btn-subscription"), callback_data="account:subscriptions", style="primary")
    builder.button(text=i18n("btn-language"), callback_data="account:language", style="primary")
    builder.button(text=i18n("btn-invite"), callback_data="menu:invite", style="primary")
    builder.button(text=i18n("btn-support"), callback_data="menu:support", style="primary")
    builder.button(text=i18n("btn-back"), callback_data="nav:menu", style="primary")

    # Layout: 2 buttons per row, except back button
    builder.adjust(2, 2, 1)

    return builder.as_markup()


def main_menu_keyboard(
    i18n: Callable[[str], str],
    user: UserDTO | dict | None = None,
) -> InlineKeyboardMarkup:
    if user is None:
        from src.keyboards.common import main_menu_keyboard as fallback

        return fallback(i18n)
    if isinstance(user, dict):
        user = UserDTO.model_validate(user)
    return main_menu_kb(i18n, user)
