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

router = Router(name="admin_stats")
router.callback_query.middleware(admin_required)


@router.callback_query(F.data == "admin:stats")
async def show_stats_handler(
    callback: CallbackQuery,
    i18n: I18nContext,
    api_client: APIClient,
) -> None:
    """Show bot statistics."""
    try:
        stats = await api_client.get_bot_stats()

        total_users = stats.get("total_users", 0)
        active_subscriptions = stats.get("active_subscriptions", 0)
        total_revenue = stats.get("total_revenue", 0)
        new_users_today = stats.get("new_users_today", 0)
        new_users_week = stats.get("new_users_week", 0)
        new_users_month = stats.get("new_users_month", 0)

        stats_text = i18n.get(
            "admin-stats-overview",
            total_users=total_users,
            active_subs=active_subscriptions,
            revenue=total_revenue,
            new_today=new_users_today,
            new_week=new_users_week,
            new_month=new_users_month,
        )

        from aiogram.types import InlineKeyboardButton
        from aiogram.utils.keyboard import InlineKeyboardBuilder

        builder = InlineKeyboardBuilder()
        builder.row(
            InlineKeyboardButton(
                text=i18n.get("admin-stats-detailed"),
                callback_data="admin:stats:detailed",
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

        logger.info("admin_stats_viewed", admin_id=callback.from_user.id)

    except Exception as e:
        logger.error("admin_stats_error", admin_id=callback.from_user.id, error=str(e))
        await callback.answer(i18n.get("error-generic"), show_alert=True)

    await callback.answer()


@router.callback_query(F.data == "admin:stats:detailed")
async def show_detailed_stats_handler(
    callback: CallbackQuery,
    i18n: I18nContext,
    api_client: APIClient,
) -> None:
    """Show detailed statistics."""
    try:
        stats = await api_client.get_detailed_stats()

        # Payment statistics
        payment_stats = stats.get("payments", {})
        total_payments = payment_stats.get("total", 0)
        successful_payments = payment_stats.get("successful", 0)
        failed_payments = payment_stats.get("failed", 0)

        # Referral statistics
        referral_stats = stats.get("referrals", {})
        total_referrals = referral_stats.get("total", 0)
        active_referrals = referral_stats.get("active", 0)

        # Plan statistics
        plan_stats = stats.get("plans", {})

        stats_text = i18n.get("admin-stats-detailed-title") + "\n\n"

        stats_text += f"💳 {i18n.get('admin-stats-payments')}:\n"
        stats_text += f"   {i18n.get('total')}: {total_payments}\n"
        stats_text += f"   ✅ {i18n.get('successful')}: {successful_payments}\n"
        stats_text += f"   ❌ {i18n.get('failed')}: {failed_payments}\n\n"

        stats_text += f"👥 {i18n.get('admin-stats-referrals')}:\n"
        stats_text += f"   {i18n.get('total')}: {total_referrals}\n"
        stats_text += f"   {i18n.get('active')}: {active_referrals}\n\n"

        stats_text += f"📊 {i18n.get('admin-stats-plans')}:\n"
        for plan_name, count in plan_stats.items():
            stats_text += f"   {plan_name}: {count}\n"

        from aiogram.types import InlineKeyboardButton
        from aiogram.utils.keyboard import InlineKeyboardBuilder

        builder = InlineKeyboardBuilder()
        builder.row(
            InlineKeyboardButton(
                text="🔙 " + i18n.get("button-back"),
                callback_data="admin:stats",
            )
        )

        await callback.message.edit_text(
            text=stats_text,
            reply_markup=builder.as_markup(),
        )

        logger.info("admin_detailed_stats_viewed", admin_id=callback.from_user.id)

    except Exception as e:
        logger.error("admin_detailed_stats_error", admin_id=callback.from_user.id, error=str(e))
        await callback.answer(i18n.get("error-generic"), show_alert=True)

    await callback.answer()
