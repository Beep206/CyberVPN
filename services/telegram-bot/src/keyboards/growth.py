"""Growth and rewards keyboards for the Telegram Bot."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from aiogram.utils.keyboard import InlineKeyboardBuilder

from src.keyboards.miniapp import miniapp_button

if TYPE_CHECKING:
    from collections.abc import Callable

    from aiogram.types import InlineKeyboardMarkup

    from src.config import BotSettings


def growth_capabilities(capabilities: dict[str, Any] | None) -> dict[str, bool]:
    """Extract supported growth flags from the public capabilities response."""
    growth = capabilities.get("growth") if isinstance(capabilities, dict) else None
    if not isinstance(growth, dict):
        # Preserve only existing bot-safe legacy actions when capability fetch
        # is unavailable; newer gift/notification flows stay in Mini App.
        return {
            "invites": True,
            "referral": True,
            "promo_codes": True,
            "gift_codes": False,
            "checkout_code_discounts": False,
            "growth_hub": False,
        }

    return {
        "invites": bool(growth.get("invites", False)),
        "referral": bool(growth.get("referral", False)),
        "promo_codes": bool(growth.get("promo_codes", False)),
        "gift_codes": bool(growth.get("gift_codes", False)),
        "checkout_code_discounts": bool(growth.get("checkout_code_discounts", False)),
        "growth_hub": bool(growth.get("growth_hub", False)),
    }


def has_growth_actions(capabilities: dict[str, Any] | None) -> bool:
    """Return whether at least one bot-safe growth action should be visible."""
    flags = growth_capabilities(capabilities)
    return any(
        flags[name]
        for name in (
            "invites",
            "referral",
            "promo_codes",
            "gift_codes",
            "checkout_code_discounts",
            "growth_hub",
        )
    )


def can_enter_code(capabilities: dict[str, Any] | None) -> bool:
    """Return whether bot-safe code entry should be offered."""
    flags = growth_capabilities(capabilities)
    return any(flags[name] for name in ("promo_codes", "checkout_code_discounts"))


def growth_menu_keyboard(
    i18n: Callable[..., str],
    *,
    settings: BotSettings | None = None,
    capabilities: dict[str, Any] | None = None,
) -> InlineKeyboardMarkup:
    """Build the Rewards/Growth menu while hiding disabled runtime features."""
    builder = InlineKeyboardBuilder()
    flags = growth_capabilities(capabilities)

    if flags["referral"]:
        builder.button(text=i18n("btn-growth-referral"), callback_data="growth:referral", style="primary")
    if flags["gift_codes"]:
        builder.row(
            miniapp_button(
                i18n,
                settings,
                text_key="btn-growth-gifts",
                path="/rewards/gifts",
                fallback_callback="miniapp:unavailable",
            )
        )
    if flags["invites"]:
        builder.button(text=i18n("btn-growth-invites"), callback_data="growth:invites", style="primary")
    if can_enter_code(capabilities):
        builder.button(text=i18n("btn-enter-code"), callback_data="growth:code", style="primary")
    if flags["growth_hub"]:
        builder.row(
            miniapp_button(
                i18n,
                settings,
                text_key="btn-growth-notifications",
                path="/rewards/notifications",
                fallback_callback="miniapp:unavailable",
            )
        )

    builder.row(
        miniapp_button(
            i18n,
            settings,
            text_key="btn-miniapp-open",
            path="/rewards",
            fallback_callback="miniapp:unavailable",
        )
    )
    builder.button(text=i18n("btn-back"), callback_data="nav:menu", style="primary")
    builder.adjust(1)
    return builder.as_markup()
