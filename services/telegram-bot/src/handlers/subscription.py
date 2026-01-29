from __future__ import annotations

from typing import TYPE_CHECKING

import structlog
from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery

from keyboards.payment import payment_methods_keyboard
from keyboards.subscription import duration_keyboard, plans_keyboard
from states.subscription import SubscriptionState

if TYPE_CHECKING:
    from aiogram_i18n import I18nContext

    from clients.api_client import APIClient
    from config.settings import Settings

logger = structlog.get_logger(__name__)

router = Router(name="subscription")


@router.callback_query(F.data == "subscription:buy")
async def buy_subscription_handler(
    callback: CallbackQuery,
    i18n: I18nContext,
    api_client: APIClient,
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
    state: FSMContext,
) -> None:
    """Handle plan selection - show duration selection."""
    plan_id = callback.data.split(":")[1]

    # Store selected plan
    await state.update_data(plan_id=plan_id)

    await callback.message.edit_text(
        text=i18n.get("subscription-select-duration"),
        reply_markup=duration_keyboard(i18n),
    )

    await state.set_state(SubscriptionState.selecting_duration)
    logger.info("plan_selected", user_id=callback.from_user.id, plan_id=plan_id)

    await callback.answer()


@router.callback_query(SubscriptionState.selecting_duration, F.data.startswith("duration:"))
async def duration_selected_handler(
    callback: CallbackQuery,
    i18n: I18nContext,
    api_client: APIClient,
    state: FSMContext,
    settings: Settings,
) -> None:
    """Handle duration selection - show payment methods."""
    duration_months = int(callback.data.split(":")[1])

    # Get stored plan
    data = await state.get_data()
    plan_id = data.get("plan_id")

    if not plan_id:
        await callback.answer(i18n.get("error-generic"), show_alert=True)
        await state.clear()
        return

    # Calculate total price
    try:
        plan = await api_client.get_plan(plan_id)
        base_price = plan.get("price", 0)
        total_price = base_price * duration_months

        # Apply discounts for longer durations
        if duration_months == 3:
            total_price *= 0.95  # 5% discount
        elif duration_months == 6:
            total_price *= 0.90  # 10% discount
        elif duration_months == 12:
            total_price *= 0.85  # 15% discount

        # Store duration and price
        await state.update_data(
            duration_months=duration_months,
            total_price=total_price,
        )

        await callback.message.edit_text(
            text=i18n.get(
                "subscription-select-payment",
                plan=plan.get("name", "N/A"),
                duration=duration_months,
                price=total_price,
            ),
            reply_markup=payment_methods_keyboard(i18n, settings),
        )

        await state.set_state(SubscriptionState.selecting_payment)
        logger.info(
            "duration_selected",
            user_id=callback.from_user.id,
            plan_id=plan_id,
            duration=duration_months,
            price=total_price,
        )

    except Exception as e:
        logger.error("duration_selection_error", user_id=callback.from_user.id, error=str(e))
        await callback.answer(i18n.get("error-generic"), show_alert=True)
        await state.clear()

    await callback.answer()


@router.callback_query(F.data == "subscription:cancel")
async def cancel_subscription_handler(
    callback: CallbackQuery,
    i18n: I18nContext,
    state: FSMContext,
) -> None:
    """Cancel subscription purchase flow."""
    await state.clear()

    from keyboards.main import main_menu_keyboard

    await callback.message.edit_text(
        text=i18n.get("subscription-cancelled"),
        reply_markup=main_menu_keyboard(i18n),
    )

    logger.info("subscription_flow_cancelled", user_id=callback.from_user.id)
    await callback.answer()
