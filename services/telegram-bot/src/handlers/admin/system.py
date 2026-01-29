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

router = Router(name="admin_system")
router.callback_query.middleware(admin_required)


@router.callback_query(F.data == "admin:system")
async def system_menu_handler(
    callback: CallbackQuery,
    i18n: I18nContext,
) -> None:
    """Show system monitoring menu."""
    from aiogram.types import InlineKeyboardButton
    from aiogram.utils.keyboard import InlineKeyboardBuilder

    builder = InlineKeyboardBuilder()

    builder.row(
        InlineKeyboardButton(
            text=i18n.get("admin-system-health"),
            callback_data="admin:system:health",
        )
    )
    builder.row(
        InlineKeyboardButton(
            text=i18n.get("admin-system-logs"),
            callback_data="admin:system:logs",
        )
    )
    builder.row(
        InlineKeyboardButton(
            text=i18n.get("admin-system-cache"),
            callback_data="admin:system:cache",
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="🔙 " + i18n.get("button-back"),
            callback_data="admin:menu",
        )
    )

    await callback.message.edit_text(
        text=i18n.get("admin-system-title"),
        reply_markup=builder.as_markup(),
    )

    logger.info("admin_system_menu_opened", admin_id=callback.from_user.id)
    await callback.answer()


@router.callback_query(F.data == "admin:system:health")
async def system_health_handler(
    callback: CallbackQuery,
    i18n: I18nContext,
    api_client: APIClient,
) -> None:
    """Show system health status."""
    try:
        # Get system health
        health = await api_client.get_system_health()

        # API status
        api_status = health.get("api", {})
        api_online = api_status.get("status") == "online"
        api_response_time = api_status.get("response_time_ms", 0)

        # Database status
        db_status = health.get("database", {})
        db_online = db_status.get("status") == "online"
        db_connections = db_status.get("active_connections", 0)

        # Redis status
        redis_status = health.get("redis", {})
        redis_online = redis_status.get("status") == "online"
        redis_memory = redis_status.get("memory_usage_mb", 0)

        # Bot status
        bot_status = health.get("bot", {})
        bot_uptime = bot_status.get("uptime_hours", 0)
        bot_memory = bot_status.get("memory_usage_mb", 0)

        health_text = i18n.get("admin-system-health-title") + "\n\n"

        # API
        api_emoji = "✅" if api_online else "❌"
        health_text += f"{api_emoji} API: {api_response_time}ms\n"

        # Database
        db_emoji = "✅" if db_online else "❌"
        health_text += f"{db_emoji} Database: {db_connections} connections\n"

        # Redis
        redis_emoji = "✅" if redis_online else "❌"
        health_text += f"{redis_emoji} Redis: {redis_memory:.1f} MB\n"

        # Bot
        health_text += f"🤖 Bot: {bot_uptime:.1f}h uptime, {bot_memory:.1f} MB\n"

        from aiogram.types import InlineKeyboardButton
        from aiogram.utils.keyboard import InlineKeyboardBuilder

        builder = InlineKeyboardBuilder()
        builder.row(
            InlineKeyboardButton(
                text="🔄 " + i18n.get("admin-system-refresh"),
                callback_data="admin:system:health",
            )
        )
        builder.row(
            InlineKeyboardButton(
                text="🔙 " + i18n.get("button-back"),
                callback_data="admin:system",
            )
        )

        await callback.message.edit_text(
            text=health_text,
            reply_markup=builder.as_markup(),
        )

        logger.info("admin_system_health_viewed", admin_id=callback.from_user.id)

    except Exception as e:
        logger.error("admin_system_health_error", admin_id=callback.from_user.id, error=str(e))
        await callback.answer(i18n.get("error-generic"), show_alert=True)

    await callback.answer()


@router.callback_query(F.data == "admin:system:logs")
async def system_logs_handler(
    callback: CallbackQuery,
    i18n: I18nContext,
    api_client: APIClient,
) -> None:
    """Show recent system logs."""
    try:
        # Get recent logs
        logs = await api_client.get_recent_logs(limit=10)

        if not logs:
            await callback.answer(i18n.get("admin-system-no-logs"), show_alert=True)
            return

        logs_text = i18n.get("admin-system-logs-title") + "\n\n"

        for log in logs:
            timestamp = log.get("timestamp", "")[:19]  # Trim to datetime
            level = log.get("level", "INFO")
            message = log.get("message", "")[:50]  # Truncate

            level_emoji = {
                "ERROR": "❌",
                "WARNING": "⚠️",
                "INFO": "ℹ️",
                "DEBUG": "🐛",
            }.get(level, "📝")

            logs_text += f"{level_emoji} {timestamp}\n{message}\n\n"

        from aiogram.types import InlineKeyboardButton
        from aiogram.utils.keyboard import InlineKeyboardBuilder

        builder = InlineKeyboardBuilder()
        builder.row(
            InlineKeyboardButton(
                text="🔄 " + i18n.get("admin-system-refresh"),
                callback_data="admin:system:logs",
            )
        )
        builder.row(
            InlineKeyboardButton(
                text="🔙 " + i18n.get("button-back"),
                callback_data="admin:system",
            )
        )

        await callback.message.edit_text(
            text=logs_text,
            reply_markup=builder.as_markup(),
        )

        logger.info("admin_system_logs_viewed", admin_id=callback.from_user.id)

    except Exception as e:
        logger.error("admin_system_logs_error", admin_id=callback.from_user.id, error=str(e))
        await callback.answer(i18n.get("error-generic"), show_alert=True)

    await callback.answer()


@router.callback_query(F.data == "admin:system:cache")
async def system_cache_handler(
    callback: CallbackQuery,
    i18n: I18nContext,
    api_client: APIClient,
) -> None:
    """Show cache statistics and controls."""
    try:
        # Get cache stats
        cache_stats = await api_client.get_cache_stats()

        total_keys = cache_stats.get("total_keys", 0)
        memory_usage = cache_stats.get("memory_usage_mb", 0)
        hit_rate = cache_stats.get("hit_rate_percent", 0)

        cache_text = i18n.get("admin-system-cache-title") + "\n\n"
        cache_text += f"🔑 {i18n.get('admin-system-cache-keys')}: {total_keys}\n"
        cache_text += f"💾 {i18n.get('admin-system-cache-memory')}: {memory_usage:.1f} MB\n"
        cache_text += f"📊 {i18n.get('admin-system-cache-hit-rate')}: {hit_rate:.1f}%\n"

        from aiogram.types import InlineKeyboardButton
        from aiogram.utils.keyboard import InlineKeyboardBuilder

        builder = InlineKeyboardBuilder()
        builder.row(
            InlineKeyboardButton(
                text="🗑️ " + i18n.get("admin-system-cache-clear"),
                callback_data="admin:system:cache:clear",
            )
        )
        builder.row(
            InlineKeyboardButton(
                text="🔄 " + i18n.get("admin-system-refresh"),
                callback_data="admin:system:cache",
            )
        )
        builder.row(
            InlineKeyboardButton(
                text="🔙 " + i18n.get("button-back"),
                callback_data="admin:system",
            )
        )

        await callback.message.edit_text(
            text=cache_text,
            reply_markup=builder.as_markup(),
        )

        logger.info("admin_system_cache_viewed", admin_id=callback.from_user.id)

    except Exception as e:
        logger.error("admin_system_cache_error", admin_id=callback.from_user.id, error=str(e))
        await callback.answer(i18n.get("error-generic"), show_alert=True)

    await callback.answer()


@router.callback_query(F.data == "admin:system:cache:clear")
async def system_cache_clear_handler(
    callback: CallbackQuery,
    i18n: I18nContext,
    api_client: APIClient,
) -> None:
    """Clear system cache."""
    try:
        # Clear cache via API
        result = await api_client.clear_cache()
        cleared_keys = result.get("cleared_keys", 0)

        await callback.answer(
            i18n.get("admin-system-cache-cleared", count=cleared_keys),
            show_alert=True,
        )

        # Refresh cache view
        await system_cache_handler(callback, i18n, api_client)

        logger.info("admin_system_cache_cleared", admin_id=callback.from_user.id, cleared_keys=cleared_keys)

    except Exception as e:
        logger.error("admin_system_cache_clear_error", admin_id=callback.from_user.id, error=str(e))
        await callback.answer(i18n.get("error-generic"), show_alert=True)
