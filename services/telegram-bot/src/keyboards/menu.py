"""Menu keyboards for CyberVPN Telegram Bot.

Provides main menu and profile action keyboards with subscription
status integration.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from aiogram.utils.keyboard import InlineKeyboardBuilder, InlineKeyboardMarkup

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
        builder.button(
            text=i18n("menu-get-config"),
            callback_data="menu:connect",
        )
        builder.button(
            text=i18n("menu-renew-subscription"),
            callback_data="sub:renew",
        )
        builder.button(
            text=i18n("menu-my-subscription"),
            callback_data="sub:status",
        )
    else:
        builder.button(
            text=i18n("menu-buy-subscription"),
            callback_data="sub:plans",
        )
        # Show trial button if user has no subscription status
        if user.status in {"none", "NONE", UserStatus.NONE}:
            builder.button(
                text=i18n("menu-free-trial"),
                callback_data="sub:trial",
            )

    # Profile and account
    builder.button(
        text=i18n("menu-my-profile"),
        callback_data="account:profile",
    )
    builder.button(
        text=i18n("menu-referral-program"),
        callback_data="referral:main",
    )

    # Settings
    builder.button(
        text=i18n("menu-language"),
        callback_data="account:language",
    )

    # Support
    builder.button(
        text=i18n("menu-support"),
        callback_data="account:support",
    )

    # Admin panel for privileged users
    if user.is_admin:
        builder.button(
            text=i18n("menu-admin-panel"),
            callback_data="admin:main",
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

    builder.button(
        text=i18n("profile-view-subscription"),
        callback_data="profile:subscription",
    )
    builder.button(
        text=i18n("profile-change-language"),
        callback_data="profile:language",
    )
    builder.button(
        text=i18n("profile-referral-stats"),
        callback_data="profile:referral",
    )
    builder.button(
        text=i18n("profile-contact-support"),
        callback_data="profile:support",
    )
    builder.button(
        text=i18n("button-back"),
        callback_data="nav:back",
    )

    # Layout: 2 buttons per row, except back button
    builder.adjust(2, 2, 1)

    return builder.as_markup()
