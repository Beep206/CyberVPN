from __future__ import annotations

from typing import TYPE_CHECKING

import structlog
from aiogram import F, Router
from aiogram.types import CallbackQuery

from middleware.admin import admin_required

if TYPE_CHECKING:
    from aiogram_i18n import I18nContext

    from clients.api_client import APIClient

logger = structlog.get_logger(__name__)

router = Router(name="admin_remnawave")
router.callback_query.middleware(admin_required)


@router.callback_query(F.data == "admin:remnawave:stats")
async def remnawave_stats_handler(
    callback: CallbackQuery,
    i18n: I18nContext,
    api_client: APIClient,
) -> None:
    """Show Remnawave statistics."""
    try:
        stats = await api_client.get_remnawave_stats()

        total_users = stats.get("total_users", 0)
        active_subs = stats.get("active_subscriptions", 0)
        total_traffic = stats.get("total_traffic_gb", 0)
        servers_count = stats.get("servers_count", 0)

        stats_text = i18n.get(
            "admin-remnawave-stats",
            users=total_users,
            active_subs=active_subs,
            traffic=total_traffic,
            servers=servers_count,
        )

        from aiogram.types import InlineKeyboardButton
        from aiogram.utils.keyboard import InlineKeyboardBuilder

        builder = InlineKeyboardBuilder()
        builder.row(
            InlineKeyboardButton(
                text="🔄 " + i18n.get("admin-remnawave-refresh"),
                callback_data="admin:remnawave:stats",
            )
        )
        builder.row(
            InlineKeyboardButton(
                text="🔙 " + i18n.get("button-back"),
                callback_data="admin:menu",
            )
        )

        await callback.message.edit_text(
            text=stats_text,
            reply_markup=builder.as_markup(),
        )

        logger.info("admin_remnawave_stats_viewed", admin_id=callback.from_user.id)

    except Exception as e:
        logger.error("admin_remnawave_stats_error", admin_id=callback.from_user.id, error=str(e))
        await callback.answer(i18n.get("error-generic"), show_alert=True)

    await callback.answer()
