"""Subscription-related keyboards for CyberVPN Telegram Bot.

Provides plan selection, duration picker, and payment method chooser
keyboards with dynamic content from backend API responses.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

if TYPE_CHECKING:
    from collections.abc import Callable

    from src.config import BotSettings
    from src.models.subscription import PlanDuration, SubscriptionPlan


def plans_keyboard(
    i18n: Callable[..., str],
    plans: list[SubscriptionPlan] | list[dict[str, Any]],
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
        if isinstance(plan, dict):
            plan_id = plan.get("id")
            plan_name = plan.get("name", "")
            plan_tag = plan.get("tag") or plan.get("code") or ""
        else:
            plan_id = plan.id
            plan_name = plan.name
            plan_tag = plan.tag

        label = plan_name or plan_tag or "Plan"
        button_text = f"{plan_tag} — {plan_name}" if plan_tag and plan_name else label
        builder.button(
            text=button_text,
            callback_data=f"plan:select:{plan_id}",
        )

    # Navigation
    builder.button(
        text=i18n("btn-back"),
        callback_data="nav:menu",
    )

    # Layout: 1 plan per row for clarity
    builder.adjust(1)

    return builder.as_markup()


def duration_keyboard(
    i18n: Callable[..., str],
    plan: SubscriptionPlan | dict[str, Any] | None = None,
    durations: list[PlanDuration] | list[dict[str, Any]] | None = None,
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

    if plan is None or durations is None:
        for duration_days in (30, 90, 180, 365):
            builder.button(
                text=i18n("duration-item", duration_days=duration_days, price=""),
                callback_data=f"duration:{duration_days}",
            )

        builder.button(
            text=i18n("btn-back"),
            callback_data="nav:menu",
        )

        builder.adjust(1)
        return builder.as_markup()

    if isinstance(plan, dict):
        plan_id = plan.get("id")
    else:
        plan_id = plan.id

    for duration in durations:
        # Get first available price (prefer USD, fallback to first currency)
        if isinstance(duration, dict):
            duration_days = int(duration.get("duration_days") or duration.get("days") or 0)
            prices = duration.get("prices") or {}
        else:
            duration_days = duration.duration_days
            prices = duration.prices

        price_display = ""
        if isinstance(prices, dict) and "USD" in prices:
            price_display = f"${prices['USD']:.2f}"
        elif isinstance(prices, dict) and prices:
            currency = next(iter(prices))
            price_display = f"{prices[currency]:.2f} {currency}"

        button_text = i18n(
            "duration-item",
            duration_days=duration_days,
            price=price_display,
        )
        builder.button(
            text=button_text,
            callback_data=f"duration:select:{plan_id}:{duration_days}",
        )

    # Navigation
    builder.button(
        text=i18n("btn-back"),
        callback_data="subscription:back",
    )

    # Layout: 1 duration per row
    builder.adjust(1)

    return builder.as_markup()


def payment_methods_keyboard(
    i18n: Callable[..., str],
    settings: BotSettings,
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
            text=i18n("btn-pay-cryptobot"),
            callback_data="pay:cryptobot",
            style="primary",
        )

    # YooKassa (cards, wallets)
    if settings.yookassa.enabled:
        builder.button(
            text=i18n("btn-pay-yookassa"),
            callback_data="pay:yookassa",
            style="primary",
        )

    # Telegram Stars
    if settings.telegram_stars.enabled:
        builder.button(
            text=i18n("btn-pay-stars"),
            callback_data="pay:telegram_stars",
            style="primary",
        )

    # Navigation
    builder.button(
        text=i18n("btn-back"),
        callback_data="subscription:back",
        style="primary",
    )

    builder.adjust(1)
    return builder.as_markup()


def subscription_keyboard(
    i18n: Callable[..., str],
    *,
    has_active: bool,
) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()

    if has_active:
        builder.button(text=i18n("btn-get-config"), callback_data="config:menu", style="primary")
        builder.button(text=i18n("btn-extend"), callback_data="subscription:buy", style="primary")
        builder.button(text=i18n("btn-subscription"), callback_data="account:subscriptions", style="primary")
    else:
        builder.button(text=i18n("btn-trial"), callback_data="trial:activate", style="success")
        builder.button(text=i18n("btn-buy"), callback_data="subscription:buy", style="primary")
        builder.button(text=i18n("btn-enter-promo"), callback_data="promocode:enter", style="primary")

    builder.button(text=i18n("btn-back"), callback_data="nav:menu", style="primary")
    builder.adjust(1)

    return builder.as_markup()
