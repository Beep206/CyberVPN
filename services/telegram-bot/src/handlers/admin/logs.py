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

router = Router(name="admin_logs")
router.callback_query.middleware(admin_required)


@router.callback_query(F.data == "admin:logs")
async def logs_handler(
    callback: CallbackQuery,
    i18n: I18nContext,
    api_client: APIClient,
) -> None:
    """Show recent logs."""
    try:
        logs = await api_client.get_recent_logs(limit=20)

        if not logs:
            await callback.answer(i18n.get("admin-logs-no-logs"), show_alert=True)
            return

        logs_text = i18n.get("admin-logs-title") + "\n\n"

        for log in logs:
            timestamp = log.get("timestamp", "N/A")[:19]  # Trim to datetime
            level = log.get("level", "INFO")
            message = log.get("message", "N/A")
            user_id = log.get("user_id", "N/A")

            level_emoji = {
                "INFO": "ℹ️",
                "WARNING": "⚠️",
                "ERROR": "❌",
                "CRITICAL": "🔴",
            }.get(level, "📝")

            logs_text += f"{level_emoji} [{timestamp}] {level}\n"
            logs_text += f"   User: {user_id} | {message[:50]}...\n\n"

        from aiogram.types import InlineKeyboardButton
        from aiogram.utils.keyboard import InlineKeyboardBuilder

        builder = InlineKeyboardBuilder()
        builder.row(
            InlineKeyboardButton(
                text="🔄 " + i18n.get("admin-logs-refresh"),
                callback_data="admin:logs",
            )
        )
        builder.row(
            InlineKeyboardButton(
                text="📥 " + i18n.get("admin-logs-export"),
                callback_data="admin:logs:export",
            )
        )
        builder.row(
            InlineKeyboardButton(
                text="🔙 " + i18n.get("button-back"),
                callback_data="admin:menu",
            )
        )

        await callback.message.edit_text(
            text=logs_text,
            reply_markup=builder.as_markup(),
        )

        logger.info("admin_logs_viewed", admin_id=callback.from_user.id)

    except Exception as e:
        logger.error("admin_logs_error", admin_id=callback.from_user.id, error=str(e))
        await callback.answer(i18n.get("error-generic"), show_alert=True)

    await callback.answer()


@router.callback_query(F.data == "admin:logs:export")
async def logs_export_handler(
    callback: CallbackQuery,
    i18n: I18nContext,
    api_client: APIClient,
) -> None:
    """Export logs to file."""
    try:
        await callback.answer(i18n.get("admin-logs-export-started"), show_alert=True)

        # Get logs export from API
        logs_data = await api_client.export_logs()

        # Send as text file
        from aiogram.types import BufferedInputFile

        logs_file = BufferedInputFile(logs_data.encode("utf-8"), filename="bot_logs.txt")

        await callback.message.answer_document(
            document=logs_file,
            caption=i18n.get("admin-logs-export-completed"),
        )

        logger.info("admin_logs_exported", admin_id=callback.from_user.id)

    except Exception as e:
        logger.error("admin_logs_export_error", admin_id=callback.from_user.id, error=str(e))
        await callback.answer(i18n.get("error-export-failed"), show_alert=True)

    await callback.answer()
