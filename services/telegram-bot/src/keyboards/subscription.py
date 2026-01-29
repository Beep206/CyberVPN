"""Subscription-related keyboards for CyberVPN Telegram Bot.

Provides plan selection, duration picker, and payment method chooser
keyboards with dynamic content from backend API responses.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from aiogram.utils.keyboard import InlineKeyboardBuilder, InlineKeyboardMarkup

if TYPE_CHECKING:
    from collections.abc import Callable

    from src.config import Settings
    from src.models.subscription import PlanDuration, SubscriptionPlan


def plans_keyboard(
    i18n: Callable[[str], str],
    plans: list[SubscriptionPlan],
) -> InlineKeyboardMarkup:
    """Build subscription plan selection keyboard.

    Args:
        i18n: Fluent translator function for localization.
        plans: List of available subscription plans.

    Returns:
        InlineKeyboardMarkup with plan buttons and navigation.
    """
    builder = InlineKeyboardBuilder()

    for plan in plans:
        # Format button text with plan name and tag
        button_text = f"{plan.tag} — {plan.name}"
        builder.button(
            text=button_text,
            callback_data=f"plan:select:{plan.id}",
        )

    # Navigation
    builder.button(
        text=i18n("button-back"),
        callback_data="nav:back",
    )

    # Layout: 1 plan per row for clarity
    builder.adjust(1)

    return builder.as_markup()


def duration_keyboard(
    i18n: Callable[[str], str],
    plan: SubscriptionPlan,
    durations: list[PlanDuration],
) -> InlineKeyboardMarkup:
    """Build duration selection keyboard for a specific plan.

    Args:
        i18n: Fluent translator function for localization.
        plan: The selected subscription plan.
        durations: Available duration options with pricing.

    Returns:
        InlineKeyboardMarkup with duration buttons.
    """
    builder = InlineKeyboardBuilder()

    for duration in durations:
        # Format duration text
        if duration.duration_days == -1:
            duration_text = i18n("duration-unlimited")
        elif duration.duration_days == 1:
            duration_text = i18n("duration-1-day")
        elif duration.duration_days == 7:
            duration_text = i18n("duration-1-week")
        elif duration.duration_days == 30:
            duration_text = i18n("duration-1-month")
        elif duration.duration_days == 90:
            duration_text = i18n("duration-3-months")
        elif duration.duration_days == 180:
            duration_text = i18n("duration-6-months")
        elif duration.duration_days == 365:
            duration_text = i18n("duration-1-year")
        else:
            duration_text = i18n("duration-n-days").format(days=duration.duration_days)

        # Get first available price (prefer USD, fallback to first currency)
        price_display = ""
        if "USD" in duration.prices:
            price_display = f"${duration.prices['USD']:.2f}"
        elif duration.prices:
            currency = next(iter(duration.prices))
            price_display = f"{duration.prices[currency]:.2f} {currency}"

        button_text = f"{duration_text} — {price_display}"
        builder.button(
            text=button_text,
            callback_data=f"duration:select:{plan.id}:{duration.duration_days}",
        )

    # Navigation
    builder.button(
        text=i18n("button-back"),
        callback_data="nav:back",
    )

    # Layout: 1 duration per row
    builder.adjust(1)

    return builder.as_markup()


def payment_methods_keyboard(
    i18n: Callable[[str], str],
    settings: Settings,
) -> InlineKeyboardMarkup:
    """Build payment method selection keyboard.

    Args:
        i18n: Fluent translator function for localization.
        settings: Application settings with payment gateway configs.

    Returns:
        InlineKeyboardMarkup with available payment methods.
    """
    builder = InlineKeyboardBuilder()

    # CryptoBot (cryptocurrency)
    if settings.cryptobot.enabled:
        builder.button(
            text=i18n("payment-cryptobot"),
            callback_data="pay:cryptobot",
        )

    # YooKassa (cards, wallets)
    if settings.yookassa.enabled:
        builder.button(
            text=i18n("payment-yookassa"),
            callback_data="pay:yookassa",
        )

    # Telegram Stars
    if settings.telegram_stars.enabled:
        builder.button(
            text=i18n("payment-stars"),
            callback_data="pay:telegram_stars",
        )

    # Navigation
    builder.button(
        text=i18n("button-back"),
        callback_data="nav:back",
    )

    # Layout: 1 payment method per row
    builder.adjust(1)

    return builder.as_markup()
