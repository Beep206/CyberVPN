"""Subscription-related keyboards for CyberVPN Telegram Bot."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from aiogram.utils.keyboard import InlineKeyboardBuilder

if TYPE_CHECKING:
    from collections.abc import Callable

    from aiogram.types import InlineKeyboardMarkup

    from src.config import BotSettings


def _price_label(*, price_rub: Any = None, price_usd: Any = None, prices: dict[str, Any] | None = None) -> str:
    if isinstance(prices, dict):
        if "RUB" in prices:
            return f"{float(prices['RUB']):.0f} RUB"
        if "USD" in prices:
            return f"${float(prices['USD']):.2f}"
        if prices:
            currency = next(iter(prices))
            return f"{float(prices[currency]):.2f} {currency}"

    if price_rub is not None:
        return f"{float(price_rub):.0f} RUB"
    if price_usd is not None:
        return f"${float(price_usd):.2f}"
    return ""


def plans_keyboard(
    i18n: Callable[..., str],
    plans: list[dict[str, Any]],
) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()

    for plan in plans:
        plan_code = str(plan.get("plan_code") or plan.get("id") or "")
        plan_name = str(plan.get("display_name") or plan.get("name") or plan_code.title())
        durations = plan.get("durations") or []
        starting_price = ""
        if durations:
            first = durations[0]
            starting_price = _price_label(
                price_rub=first.get("price_rub"),
                price_usd=first.get("price_usd"),
                prices=first.get("prices"),
            )
        elif plan:
            starting_price = _price_label(
                price_rub=plan.get("price_rub"),
                price_usd=plan.get("price_usd"),
                prices=plan.get("prices"),
            )

        devices = plan.get("devices_included") or plan.get("device_limit")
        details = f" · {devices} dev" if devices else ""
        price_suffix = f" · {starting_price}" if starting_price else ""
        builder.button(
            text=f"{plan_name}{details}{price_suffix}",
            callback_data=f"plan:select:{plan_code}",
        )

    builder.button(text=i18n("btn-back"), callback_data="nav:menu")
    builder.adjust(1)
    return builder.as_markup()


def duration_keyboard(
    i18n: Callable[..., str],
    plan: dict[str, Any] | None = None,
    durations: list[dict[str, Any]] | None = None,
) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()

    plan_code = str((plan or {}).get("plan_code") or "")
    for duration in durations or []:
        duration_days = int(duration.get("duration_days") or duration.get("days") or 0)
        price_display = _price_label(
            price_rub=duration.get("price_rub"),
            price_usd=duration.get("price_usd"),
            prices=duration.get("prices"),
        )
        builder.button(
            text=i18n("duration-item", duration_days=duration_days, price=price_display),
            callback_data=f"duration:select:{plan_code}:{duration_days}",
        )

    builder.button(text=i18n("btn-back"), callback_data="subscription:back")
    builder.adjust(1)
    return builder.as_markup()


def addons_keyboard(
    i18n: Callable[..., str],
    *,
    extra_device_qty: int = 0,
    extra_device_limit: int = 0,
) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()

    if extra_device_limit > 0:
        if extra_device_qty > 0:
            builder.button(text="- 1 device", callback_data="addon:dec:extra_device")
        if extra_device_qty < extra_device_limit:
            builder.button(text="+ 1 device", callback_data="addon:inc:extra_device")

    builder.button(text=i18n("btn-next"), callback_data="addon:continue")
    builder.button(text=i18n("btn-back"), callback_data="subscription:back")
    builder.adjust(2, 1, 1)
    return builder.as_markup()


def payment_methods_keyboard(
    i18n: Callable[..., str],
    settings: BotSettings,
) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()

    if settings.cryptobot.enabled:
        builder.button(
            text=i18n("btn-pay-cryptobot"),
            callback_data="pay:cryptobot",
        )

    builder.button(text=i18n("btn-back"), callback_data="subscription:back")
    builder.adjust(1)
    return builder.as_markup()


def subscription_keyboard(
    i18n: Callable[..., str],
    *,
    has_active: bool,
) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()

    if has_active:
        builder.button(text=i18n("btn-get-config"), callback_data="config:menu")
        builder.button(text=i18n("btn-extend"), callback_data="subscription:buy")
        builder.button(text=i18n("btn-subscription"), callback_data="account:subscriptions")
    else:
        builder.button(text=i18n("btn-trial"), callback_data="trial:activate")
        builder.button(text=i18n("btn-buy"), callback_data="subscription:buy")
        builder.button(text=i18n("btn-enter-promo"), callback_data="promocode:enter")

    builder.button(text=i18n("btn-back"), callback_data="nav:menu")
    builder.adjust(1)
    return builder.as_markup()
