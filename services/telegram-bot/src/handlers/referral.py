from __future__ import annotations

from typing import TYPE_CHECKING

import structlog
from aiogram import F, Router
from aiogram.types import CallbackQuery

from src.keyboards.referral import referral_keyboard

if TYPE_CHECKING:
    from aiogram_i18n import I18nContext

    from src.config import BotSettings
    from src.services.api_client import CyberVPNAPIClient

logger = structlog.get_logger(__name__)

router = Router(name="referral")


async def _render_referral_info(
    callback: CallbackQuery,
    i18n: I18nContext,
    api_client: CyberVPNAPIClient,
    settings: BotSettings,
) -> None:
    """Render referral info and stats."""
    user_id = callback.from_user.id

    try:
        stats = await api_client.get_referral_stats(user_id)

        total_referrals = stats.get("total_referrals", 0)
        total_bonus = stats.get("bonus_days", stats.get("total_bonus", 0))
        bot_username = settings.bot_username or "CyberVPNBot"
        referral_link = f"https://t.me/{bot_username}?start=ref_{user_id}"

        stats_text = i18n.get(
            "referral-info",
            count=total_referrals,
            bonus_days=total_bonus,
            link=referral_link,
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


@router.callback_query(F.data == "referral:link")
async def referral_link_handler(
    callback: CallbackQuery,
    i18n: I18nContext,
    api_client: CyberVPNAPIClient,
    settings: BotSettings,
) -> None:
    """Show referral link and stats."""
    await _render_referral_info(callback, i18n, api_client, settings)


@router.callback_query(F.data == "referral:stats")
async def referral_stats_handler(
    callback: CallbackQuery,
    i18n: I18nContext,
    api_client: CyberVPNAPIClient,
    settings: BotSettings,
) -> None:
    """Show referral statistics."""
    await _render_referral_info(callback, i18n, api_client, settings)


@router.callback_query(F.data == "referral:share")
async def share_referral_link_handler(
    callback: CallbackQuery,
    i18n: I18nContext,
    settings: BotSettings,
) -> None:
    """Share referral link."""
    user_id = callback.from_user.id
    bot_username = settings.bot_username or "CyberVPNBot"
    referral_link = f"https://t.me/{bot_username}?start=ref_{user_id}"

    share_text = i18n.get("referral-share", link=referral_link)

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
            text=i18n.get("btn-back"),
            callback_data="menu:invite",
            style="primary",
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
    api_client: CyberVPNAPIClient,
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
        withdrawal = await api_client.withdraw_referral_points(user_id, available_balance)

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
