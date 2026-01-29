from __future__ import annotations

from typing import TYPE_CHECKING

import structlog
from aiogram import F, Router
from aiogram.types import CallbackQuery

from keyboards.referral import referral_keyboard

if TYPE_CHECKING:
    from aiogram_i18n import I18nContext

    from clients.api_client import APIClient
    from config.settings import Settings

logger = structlog.get_logger(__name__)

router = Router(name="referral")


@router.callback_query(F.data == "referral:stats")
async def referral_stats_handler(
    callback: CallbackQuery,
    i18n: I18nContext,
    api_client: APIClient,
) -> None:
    """Show referral statistics."""
    user_id = callback.from_user.id

    try:
        stats = await api_client.get_referral_stats(user_id)

        total_referrals = stats.get("total_referrals", 0)
        total_bonus = stats.get("total_bonus", 0)
        available_balance = stats.get("available_balance", 0)
        pending_balance = stats.get("pending_balance", 0)

        stats_text = i18n.get(
            "referral-stats-details",
            total=total_referrals,
            bonus=total_bonus,
            available=available_balance,
            pending=pending_balance,
        )

        await callback.message.edit_text(
            text=stats_text,
            reply_markup=referral_keyboard(i18n, stats),
        )

        logger.info("referral_stats_viewed", user_id=user_id)

    except Exception as e:
        logger.error("referral_stats_error", user_id=user_id, error=str(e))
        await callback.answer(i18n.get("error-generic"), show_alert=True)

    await callback.answer()


@router.callback_query(F.data == "referral:share")
async def share_referral_link_handler(
    callback: CallbackQuery,
    i18n: I18nContext,
    settings: Settings,
) -> None:
    """Share referral link."""
    user_id = callback.from_user.id
    bot_username = settings.bot_username
    referral_link = f"https://t.me/{bot_username}?start=ref_{user_id}"

    share_text = i18n.get("referral-share-message", link=referral_link)

    from aiogram.types import InlineKeyboardButton
    from aiogram.utils.keyboard import InlineKeyboardBuilder

    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(
            text=i18n.get("referral-share-button"),
            url=f"https://t.me/share/url?url={referral_link}",
        )
    )
    builder.row(
        InlineKeyboardButton(
            text=i18n.get("button-back"),
            callback_data="menu:invite",
        )
    )

    await callback.message.edit_text(
        text=share_text,
        reply_markup=builder.as_markup(),
    )

    logger.info("referral_link_shared", user_id=user_id)
    await callback.answer()


@router.callback_query(F.data == "referral:withdraw")
async def withdraw_bonus_handler(
    callback: CallbackQuery,
    i18n: I18nContext,
    api_client: APIClient,
) -> None:
    """Withdraw referral bonus."""
    user_id = callback.from_user.id

    try:
        # Get current balance
        stats = await api_client.get_referral_stats(user_id)
        available_balance = stats.get("available_balance", 0)
        min_withdrawal = stats.get("min_withdrawal", 100)

        if available_balance < min_withdrawal:
            await callback.answer(
                i18n.get("referral-withdraw-insufficient", min=min_withdrawal),
                show_alert=True,
            )
            return

        # Create withdrawal request
        withdrawal = await api_client.create_withdrawal(user_id, available_balance)

        await callback.message.edit_text(
            text=i18n.get(
                "referral-withdraw-success",
                amount=available_balance,
                status=withdrawal.get("status", "pending"),
            ),
        )

        logger.info(
            "referral_withdrawal_created",
            user_id=user_id,
            amount=available_balance,
            withdrawal_id=withdrawal.get("id"),
        )

    except Exception as e:
        logger.error("referral_withdrawal_error", user_id=user_id, error=str(e))
        await callback.answer(i18n.get("error-withdrawal-failed"), show_alert=True)

    await callback.answer()
