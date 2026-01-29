from __future__ import annotations

from typing import TYPE_CHECKING

import structlog
from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from middleware.admin import admin_required
from states.admin import AdminPlanState

if TYPE_CHECKING:
    from aiogram_i18n import I18nContext

    from clients.api_client import APIClient

logger = structlog.get_logger(__name__)

router = Router(name="admin_plans")
router.message.middleware(admin_required)
router.callback_query.middleware(admin_required)


@router.callback_query(F.data == "admin:plans")
async def plans_menu_handler(
    callback: CallbackQuery,
    i18n: I18nContext,
    api_client: APIClient,
) -> None:
    """Show subscription plans management menu."""
    try:
        # Get all plans
        plans = await api_client.get_all_plans()

        # Build plans list
        from aiogram.types import InlineKeyboardButton
        from aiogram.utils.keyboard import InlineKeyboardBuilder

        builder = InlineKeyboardBuilder()

        for plan in plans:
            plan_id = plan.get("id")
            plan_name = plan.get("name")
            price = plan.get("price")
            is_active = plan.get("is_active", True)

            status_emoji = "✅" if is_active else "❌"

            builder.row(
                InlineKeyboardButton(
                    text=f"{status_emoji} {plan_name} - ${price}",
                    callback_data=f"admin:plan:view:{plan_id}",
                )
            )

        builder.row(
            InlineKeyboardButton(
                text="➕ " + i18n.get("admin-plans-create"),
                callback_data="admin:plan:create",
            )
        )
        builder.row(
            InlineKeyboardButton(
                text="🔙 " + i18n.get("button-back"),
                callback_data="admin:menu",
            )
        )

        await callback.message.edit_text(
            text=i18n.get("admin-plans-title"),
            reply_markup=builder.as_markup(),
        )

        logger.info("admin_plans_viewed", admin_id=callback.from_user.id)

    except Exception as e:
        logger.error("admin_plans_error", admin_id=callback.from_user.id, error=str(e))
        await callback.answer(i18n.get("error-generic"), show_alert=True)

    await callback.answer()


@router.callback_query(F.data.startswith("admin:plan:view:"))
async def plan_view_handler(
    callback: CallbackQuery,
    i18n: I18nContext,
    api_client: APIClient,
) -> None:
    """View plan details."""
    plan_id = callback.data.split(":")[3]

    try:
        # Get plan details
        plan = await api_client.get_plan(plan_id)

        plan_text = i18n.get(
            "admin-plan-details",
            name=plan.get("name", "N/A"),
            price=plan.get("price", 0),
            bandwidth=plan.get("bandwidth_limit", "Unlimited"),
            devices=plan.get("max_devices", "Unlimited"),
            description=plan.get("description", "N/A"),
            is_active=i18n.get("yes") if plan.get("is_active") else i18n.get("no"),
        )

        # Create action buttons
        from aiogram.types import InlineKeyboardButton
        from aiogram.utils.keyboard import InlineKeyboardBuilder

        builder = InlineKeyboardBuilder()

        toggle_text = i18n.get("admin-plan-disable") if plan.get("is_active") else i18n.get("admin-plan-enable")

        builder.row(
            InlineKeyboardButton(
                text=toggle_text,
                callback_data=f"admin:plan:toggle:{plan_id}",
            )
        )
        builder.row(
            InlineKeyboardButton(
                text=i18n.get("admin-plan-edit"),
                callback_data=f"admin:plan:edit:{plan_id}",
            )
        )
        builder.row(
            InlineKeyboardButton(
                text="🔙 " + i18n.get("button-back"),
                callback_data="admin:plans",
            )
        )

        await callback.message.edit_text(
            text=plan_text,
            reply_markup=builder.as_markup(),
        )

        logger.info("admin_plan_viewed", admin_id=callback.from_user.id, plan_id=plan_id)

    except Exception as e:
        logger.error("admin_plan_view_error", admin_id=callback.from_user.id, plan_id=plan_id, error=str(e))
        await callback.answer(i18n.get("error-generic"), show_alert=True)

    await callback.answer()


@router.callback_query(F.data.startswith("admin:plan:toggle:"))
async def plan_toggle_handler(
    callback: CallbackQuery,
    i18n: I18nContext,
    api_client: APIClient,
) -> None:
    """Toggle plan active status."""
    plan_id = callback.data.split(":")[3]

    try:
        # Toggle plan status
        result = await api_client.toggle_plan_status(plan_id)
        is_active = result.get("is_active", False)

        if is_active:
            await callback.answer(i18n.get("admin-plan-enabled"), show_alert=True)
        else:
            await callback.answer(i18n.get("admin-plan-disabled"), show_alert=True)

        # Refresh plan view
        await plan_view_handler(callback, i18n, api_client)

        logger.info("admin_plan_toggled", admin_id=callback.from_user.id, plan_id=plan_id, is_active=is_active)

    except Exception as e:
        logger.error("admin_plan_toggle_error", admin_id=callback.from_user.id, plan_id=plan_id, error=str(e))
        await callback.answer(i18n.get("error-generic"), show_alert=True)


@router.callback_query(F.data == "admin:plan:create")
async def plan_create_prompt_handler(
    callback: CallbackQuery,
    i18n: I18nContext,
    state: FSMContext,
) -> None:
    """Prompt for new plan creation."""
    await callback.message.edit_text(
        text=i18n.get("admin-plan-create-name-prompt"),
    )

    await state.set_state(AdminPlanState.creating_name)
    logger.info("admin_plan_creation_started", admin_id=callback.from_user.id)

    await callback.answer()


@router.message(AdminPlanState.creating_name, F.text)
async def plan_create_name_handler(
    message: Message,
    i18n: I18nContext,
    state: FSMContext,
) -> None:
    """Handle plan name input."""
    plan_name = message.text.strip()

    await state.update_data(plan_name=plan_name)
    await state.set_state(AdminPlanState.creating_price)

    await message.answer(
        text=i18n.get("admin-plan-create-price-prompt"),
    )


@router.message(AdminPlanState.creating_price, F.text)
async def plan_create_price_handler(
    message: Message,
    i18n: I18nContext,
    state: FSMContext,
) -> None:
    """Handle plan price input."""
    try:
        price = float(message.text.strip())

        if price < 0:
            await message.answer(i18n.get("admin-plan-create-price-invalid"))
            return

        await state.update_data(plan_price=price)
        await state.set_state(AdminPlanState.creating_description)

        await message.answer(
            text=i18n.get("admin-plan-create-description-prompt"),
        )

    except ValueError:
        await message.answer(i18n.get("admin-plan-create-price-invalid-number"))


@router.message(AdminPlanState.creating_description, F.text)
async def plan_create_description_handler(
    message: Message,
    i18n: I18nContext,
    api_client: APIClient,
    state: FSMContext,
) -> None:
    """Handle plan description input and create plan."""
    plan_description = message.text.strip()

    try:
        # Get stored data
        data = await state.get_data()
        plan_name = data.get("plan_name")
        plan_price = data.get("plan_price")

        if not plan_name or plan_price is None:
            await message.answer(i18n.get("error-generic"))
            await state.clear()
            return

        # Create plan via API
        plan_data = {
            "name": plan_name,
            "price": plan_price,
            "description": plan_description,
            "is_active": True,
        }

        plan = await api_client.create_plan(plan_data)
        plan_id = plan.get("id")

        await message.answer(
            i18n.get(
                "admin-plan-created",
                name=plan_name,
                price=plan_price,
                plan_id=plan_id,
            )
        )

        await state.clear()
        logger.info(
            "admin_plan_created",
            admin_id=message.from_user.id,
            plan_id=plan_id,
            plan_name=plan_name,
        )

    except Exception as e:
        logger.error("admin_plan_creation_error", admin_id=message.from_user.id, error=str(e))
        await message.answer(i18n.get("error-generic"))
        await state.clear()


@router.callback_query(F.data.startswith("admin:plan:edit:"))
async def plan_edit_handler(
    callback: CallbackQuery,
    i18n: I18nContext,
) -> None:
    """Handle plan edit (placeholder for future implementation)."""
    await callback.answer(
        i18n.get("admin-feature-coming-soon"),
        show_alert=True,
    )

    logger.info("admin_plan_edit_requested", admin_id=callback.from_user.id)
