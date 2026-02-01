from __future__ import annotations

from typing import TYPE_CHECKING

import structlog
from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery

from src.keyboards.subscription import duration_keyboard, payment_methods_keyboard, plans_keyboard
from src.states.subscription import SubscriptionState

if TYPE_CHECKING:
    from aiogram_i18n import I18nContext

    from src.config import BotSettings
    from src.services.api_client import CyberVPNAPIClient

logger = structlog.get_logger(__name__)

router = Router(name="subscription")


def _extract_plan_durations(plan: dict) -> list[dict]:
    durations = plan.get("durations") or plan.get("duration_options") or plan.get("periods") or []
    if isinstance(durations, list):
        return [d for d in durations if isinstance(d, dict)]
    return []


def _select_price(prices: dict) -> tuple[float | None, str | None]:
    if not prices:
        return None, None
    if "RUB" in prices:
        return float(prices["RUB"]), "RUB"
    if "USD" in prices:
        return float(prices["USD"]), "USD"
    currency = next(iter(prices))
    return float(prices[currency]), str(currency)


@router.callback_query(F.data == "subscription:buy")
async def buy_subscription_handler(
    callback: CallbackQuery,
    i18n: I18nContext,
    api_client: CyberVPNAPIClient,
    state: FSMContext,
) -> None:
    """Start subscription purchase flow - show plan selection."""
    try:
        # Get available plans
        plans = await api_client.get_plans()

        if not plans:
            await callback.answer(i18n.get("error-no-plans"), show_alert=True)
            return

        await callback.message.edit_text(
            text=i18n.get("subscription-select-plan"),
            reply_markup=plans_keyboard(i18n, plans),
        )

        await state.set_state(SubscriptionState.selecting_plan)
        logger.info("subscription_flow_started", user_id=callback.from_user.id)

    except Exception as e:
        logger.error("buy_subscription_error", user_id=callback.from_user.id, error=str(e))
        await callback.answer(i18n.get("error-generic"), show_alert=True)

    await callback.answer()


@router.callback_query(SubscriptionState.selecting_plan, F.data.startswith("plan:"))
async def plan_selected_handler(
    callback: CallbackQuery,
    i18n: I18nContext,
    api_client: CyberVPNAPIClient,
    state: FSMContext,
) -> None:
    """Handle plan selection - show duration selection."""
    if callback.data is None:
        await state.clear()
        return

    plan_id = callback.data.split(":")[-1]

    # Store selected plan
    await state.update_data(plan_id=plan_id)

    plan = None
    durations = []
    try:
        plan = await api_client.get_plan(plan_id)
        if isinstance(plan, dict):
            durations = _extract_plan_durations(plan)
    except Exception:
        plan = None
        durations = []

    await state.update_data(plan=plan, durations=durations)

    await callback.message.edit_text(
        text=i18n.get("subscription-select-duration"),
        reply_markup=duration_keyboard(i18n, plan=plan, durations=durations),
    )

    await state.set_state(SubscriptionState.selecting_duration)
    logger.info("plan_selected", user_id=callback.from_user.id, plan_id=plan_id)

    await callback.answer()


@router.callback_query(SubscriptionState.selecting_duration, F.data.startswith("duration:"))
async def duration_selected_handler(
    callback: CallbackQuery,
    i18n: I18nContext,
    api_client: CyberVPNAPIClient,
    state: FSMContext,
    settings: BotSettings,
) -> None:
    """Handle duration selection - show payment methods."""
    if callback.data is None:
        await state.clear()
        return

    duration_days = int(callback.data.split(":")[-1])

    # Get stored plan
    data = await state.get_data()
    plan_id = data.get("plan_id")
    plan = data.get("plan") or {}
    durations = data.get("durations") or []

    if not plan_id:
        await callback.answer(i18n.get("error-generic"), show_alert=True)
        await state.clear()
        return

    # Calculate total price
    try:
        selected_duration = None
        for duration in durations:
            if int(duration.get("duration_days") or duration.get("days") or 0) == duration_days:
                selected_duration = duration
                break

        amount = None
        currency = None
        if selected_duration and isinstance(selected_duration, dict):
            prices = selected_duration.get("prices") or {}
            if isinstance(prices, dict):
                amount, currency = _select_price(prices)

        if amount is None:
            plan_data = plan if isinstance(plan, dict) else await api_client.get_plan(plan_id)
            base_price = plan_data.get("price", 0) if isinstance(plan_data, dict) else 0
            amount = float(base_price)
            currency = "USD"

        # Store duration and price
        await state.update_data(
            duration_days=duration_days,
            amount=amount,
            currency=currency,
        )

        await callback.message.edit_text(
            text=i18n.get(
                "subscription-select-payment",
                plan=(plan.get("name", "N/A") if isinstance(plan, dict) else "N/A"),
                duration=duration_days,
                price=f"{amount} {currency}" if currency else amount,
            ),
            reply_markup=payment_methods_keyboard(i18n, settings),
        )

        await state.set_state(SubscriptionState.selecting_payment)
        logger.info(
            "duration_selected",
            user_id=callback.from_user.id,
            plan_id=plan_id,
            duration=duration_days,
            price=amount,
        )

    except Exception as e:
        logger.error("duration_selection_error", user_id=callback.from_user.id, error=str(e))
        await callback.answer(i18n.get("error-generic"), show_alert=True)
        await state.clear()

    await callback.answer()


@router.callback_query(F.data == "subscription:back")
async def subscription_back_handler(
    callback: CallbackQuery,
    i18n: I18nContext,
    api_client: CyberVPNAPIClient,
    state: FSMContext,
) -> None:
    """Navigate back within subscription flow."""
    current_state = await state.get_state()

    try:
        if current_state == SubscriptionState.selecting_payment.state:
            data = await state.get_data()
            plan = data.get("plan")
            durations = data.get("durations")

            await callback.message.edit_text(
                text=i18n.get("subscription-select-duration"),
                reply_markup=duration_keyboard(i18n, plan=plan, durations=durations),
            )
            await state.set_state(SubscriptionState.selecting_duration)
            await callback.answer()
            return

        if current_state == SubscriptionState.selecting_duration.state:
            plans = await api_client.get_plans()
            await callback.message.edit_text(
                text=i18n.get("subscription-select-plan"),
                reply_markup=plans_keyboard(i18n, plans),
            )
            await state.set_state(SubscriptionState.selecting_plan)
            await callback.answer()
            return

    except Exception as e:
        logger.error("subscription_back_error", user_id=callback.from_user.id, error=str(e))
        await callback.answer(i18n.get("error-generic"), show_alert=True)
        return

    await state.clear()
    from src.keyboards.menu import main_menu_keyboard

    await callback.message.edit_text(
        text=i18n.get("menu-main-title"),
        reply_markup=main_menu_keyboard(i18n),
    )
    await callback.answer()


@router.callback_query(F.data == "subscription:cancel")
async def cancel_subscription_handler(
    callback: CallbackQuery,
    i18n: I18nContext,
    state: FSMContext,
) -> None:
    """Cancel subscription purchase flow."""
    await state.clear()

    from src.keyboards.menu import main_menu_keyboard

    await callback.message.edit_text(
        text=i18n.get("subscription-cancelled"),
        reply_markup=main_menu_keyboard(i18n),
    )

    logger.info("subscription_flow_cancelled", user_id=callback.from_user.id)
    await callback.answer()
