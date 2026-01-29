from __future__ import annotations

from typing import TYPE_CHECKING

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

if TYPE_CHECKING:
    from aiogram_i18n import I18nContext


def promos_list_keyboard(
    i18n: I18nContext,
    promos: list[dict],
    page: int,
    total_pages: int,
) -> InlineKeyboardMarkup:
    """Create paginated promo codes list keyboard."""
    builder = InlineKeyboardBuilder()

    # Promo code buttons (2 per row)
    for promo in promos:
        code = promo.get("code", "Unknown")
        active = promo.get("is_active", False)
        status = "✅" if active else "❌"
        builder.button(
            text=f"{status} {code}",
            callback_data=f"admin:promo:{promo.get('id')}",
        )
    builder.adjust(2)

    # Pagination
    nav_buttons = []
    if page > 1:
        nav_buttons.append(
            InlineKeyboardButton(
                text="◀️ " + i18n.get("button-prev"),
                callback_data=f"admin:promos:page:{page - 1}",
            )
        )
    nav_buttons.append(
        InlineKeyboardButton(
            text=f"{page}/{total_pages}",
            callback_data="noop",
        )
    )
    if page < total_pages:
        nav_buttons.append(
            InlineKeyboardButton(
                text=i18n.get("button-next") + " ▶️",
                callback_data=f"admin:promos:page:{page + 1}",
            )
        )
    builder.row(*nav_buttons)

    # Create new promo
    builder.row(
        InlineKeyboardButton(
            text="➕ " + i18n.get("admin-promo-create-new"),
            callback_data="admin:promo:create",
        )
    )

    # Back button
    builder.row(
        InlineKeyboardButton(
            text="🔙 " + i18n.get("button-back"),
            callback_data="admin:menu",
        )
    )

    return builder.as_markup()


def promo_actions_keyboard(i18n: I18nContext, promo_id: str | int) -> InlineKeyboardMarkup:
    """Create actions keyboard for a single promo code."""
    builder = InlineKeyboardBuilder()

    builder.row(
        InlineKeyboardButton(
            text="✏️ " + i18n.get("admin-promo-edit"),
            callback_data=f"admin:promo:edit:{promo_id}",
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="🔄 " + i18n.get("admin-promo-toggle"),
            callback_data=f"admin:promo:toggle:{promo_id}",
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="📊 " + i18n.get("admin-promo-stats"),
            callback_data=f"admin:promo:stats:{promo_id}",
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="🗑 " + i18n.get("admin-promo-delete"),
            callback_data=f"admin:promo:delete:{promo_id}",
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="🔙 " + i18n.get("button-back"),
            callback_data="admin:promos",
        )
    )

    return builder.as_markup()


def create_promo_keyboard(i18n: I18nContext) -> InlineKeyboardMarkup:
    """Create promo code creation keyboard."""
    builder = InlineKeyboardBuilder()

    builder.row(
        InlineKeyboardButton(
            text="💰 " + i18n.get("admin-promo-discount-type"),
            callback_data="admin:promo:create:discount",
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="📅 " + i18n.get("admin-promo-duration-type"),
            callback_data="admin:promo:create:duration",
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="🔢 " + i18n.get("admin-promo-usage-limit"),
            callback_data="admin:promo:create:limit",
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="✅ " + i18n.get("admin-promo-create-confirm"),
            callback_data="admin:promo:create:confirm",
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="❌ " + i18n.get("button-cancel"),
            callback_data="admin:promos",
        )
    )

    return builder.as_markup()
