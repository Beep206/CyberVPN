from __future__ import annotations

from typing import TYPE_CHECKING

import structlog
from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from src.states.admin import AdminPromoState

if TYPE_CHECKING:
    from aiogram_i18n import I18nContext

    from src.services.api_client import CyberVPNAPIClient

logger = structlog.get_logger(__name__)

router = Router(name="admin_promos")


@router.callback_query(F.data == "admin:promos")
async def promos_menu_handler(
    callback: CallbackQuery,
    i18n: I18nContext,
    api_client: CyberVPNAPIClient,
) -> None:
    """Show promocodes management menu."""
    try:
        # Get all promocodes
        promos = await api_client.get_all_promocodes()

        # Build promos list
        from aiogram.types import InlineKeyboardButton
        from aiogram.utils.keyboard import InlineKeyboardBuilder

        builder = InlineKeyboardBuilder()

        for promo in promos[:15]:  # Limit to 15 for display
            promo_id = promo.get("id")
            code = promo.get("code")
            discount = promo.get("discount_value")
            is_active = promo.get("is_active", True)

            status_emoji = "✅" if is_active else "❌"

            builder.row(
                InlineKeyboardButton(
                    text=f"{status_emoji} {code} - {discount}%",
                    callback_data=f"admin:promo:view:{promo_id}",
                )
            )

        builder.row(
            InlineKeyboardButton(
                text="➕ " + i18n.get("admin-promos-create"),
                callback_data="admin:promo:create",
            )
        )
        builder.row(
            InlineKeyboardButton(
                text="🔙 " + i18n.get("button-back"),
                callback_data="admin:menu",
            )
        )

        await callback.message.edit_text(
            text=i18n.get("admin-promos-title"),
            reply_markup=builder.as_markup(),
        )

        logger.info("admin_promos_viewed", admin_id=callback.from_user.id)

    except Exception as e:
        logger.error("admin_promos_error", admin_id=callback.from_user.id, error=str(e))
        await callback.answer(i18n.get("error-generic"), show_alert=True)

    await callback.answer()


@router.callback_query(F.data.startswith("admin:promo:view:"))
async def promo_view_handler(
    callback: CallbackQuery,
    i18n: I18nContext,
    api_client: CyberVPNAPIClient,
) -> None:
    """View promocode details."""
    promo_id = callback.data.split(":")[3]

    try:
        # Get promo details
        promo = await api_client.get_promocode(promo_id)

        promo_text = i18n.get(
            "admin-promo-details",
            code=promo.get("code", "N/A"),
            discount_type=promo.get("discount_type", "percentage"),
            discount_value=promo.get("discount_value", 0),
            usage_limit=promo.get("usage_limit") or i18n.get("unlimited"),
            usage_count=promo.get("usage_count", 0),
            expires_at=promo.get("expires_at") or i18n.get("never"),
            is_active=i18n.get("yes") if promo.get("is_active") else i18n.get("no"),
        )

        # Create action buttons
        from aiogram.types import InlineKeyboardButton
        from aiogram.utils.keyboard import InlineKeyboardBuilder

        builder = InlineKeyboardBuilder()

        toggle_text = i18n.get("admin-promo-disable") if promo.get("is_active") else i18n.get("admin-promo-enable")

        builder.row(
            InlineKeyboardButton(
                text=toggle_text,
                callback_data=f"admin:promo:toggle:{promo_id}",
            )
        )
        builder.row(
            InlineKeyboardButton(
                text="🔙 " + i18n.get("button-back"),
                callback_data="admin:promos",
            )
        )

        await callback.message.edit_text(
            text=promo_text,
            reply_markup=builder.as_markup(),
        )

        logger.info("admin_promo_viewed", admin_id=callback.from_user.id, promo_id=promo_id)

    except Exception as e:
        logger.error("admin_promo_view_error", admin_id=callback.from_user.id, promo_id=promo_id, error=str(e))
        await callback.answer(i18n.get("error-generic"), show_alert=True)

    await callback.answer()


@router.callback_query(F.data.startswith("admin:promo:toggle:"))
async def promo_toggle_handler(
    callback: CallbackQuery,
    i18n: I18nContext,
    api_client: CyberVPNAPIClient,
) -> None:
    """Toggle promocode active status."""
    promo_id = callback.data.split(":")[3]

    try:
        # Toggle promo status
        result = await api_client.toggle_promocode_status(promo_id)
        is_active = result.get("is_active", False)

        if is_active:
            await callback.answer(i18n.get("admin-promo-enabled"), show_alert=True)
        else:
            await callback.answer(i18n.get("admin-promo-disabled"), show_alert=True)

        # Refresh promo view
        await promo_view_handler(callback, i18n, api_client)

        logger.info("admin_promo_toggled", admin_id=callback.from_user.id, promo_id=promo_id, is_active=is_active)

    except Exception as e:
        logger.error("admin_promo_toggle_error", admin_id=callback.from_user.id, promo_id=promo_id, error=str(e))
        await callback.answer(i18n.get("error-generic"), show_alert=True)


@router.callback_query(F.data == "admin:promo:create")
async def promo_create_prompt_handler(
    callback: CallbackQuery,
    i18n: I18nContext,
    state: FSMContext,
) -> None:
    """Prompt for new promocode creation."""
    await callback.message.edit_text(
        text=i18n.get("admin-promo-create-code-prompt"),
    )

    await state.set_state(AdminPromoState.creating_code)
    logger.info("admin_promo_creation_started", admin_id=callback.from_user.id)

    await callback.answer()


@router.message(AdminPromoState.creating_code, F.text)
async def promo_create_code_handler(
    message: Message,
    i18n: I18nContext,
    state: FSMContext,
) -> None:
    """Handle promo code input."""
    promo_code = message.text.strip().upper()

    if len(promo_code) < 3 or len(promo_code) > 20:
        await message.answer(i18n.get("admin-promo-create-code-invalid-length"))
        return

    await state.update_data(promo_code=promo_code)
    await state.set_state(AdminPromoState.creating_discount)

    await message.answer(
        text=i18n.get("admin-promo-create-discount-prompt"),
    )


@router.message(AdminPromoState.creating_discount, F.text)
async def promo_create_discount_handler(
    message: Message,
    i18n: I18nContext,
    state: FSMContext,
) -> None:
    """Handle promo discount value input."""
    try:
        discount_value = int(message.text.strip())

        if discount_value <= 0 or discount_value > 100:
            await message.answer(i18n.get("admin-promo-create-discount-invalid-range"))
            return

        await state.update_data(discount_value=discount_value)
        await state.set_state(AdminPromoState.creating_limit)

        await message.answer(
            text=i18n.get("admin-promo-create-limit-prompt"),
        )

    except ValueError:
        await message.answer(i18n.get("admin-promo-create-discount-invalid-number"))


@router.message(AdminPromoState.creating_limit, F.text)
async def promo_create_limit_handler(
    message: Message,
    i18n: I18nContext,
    api_client: CyberVPNAPIClient,
    state: FSMContext,
) -> None:
    """Handle promo usage limit input and create promocode."""
    try:
        usage_limit_text = message.text.strip().lower()

        # Allow "unlimited" or a number
        if usage_limit_text in ["unlimited", "0", "none", "-"]:
            usage_limit = None
        else:
            usage_limit = int(usage_limit_text)

            if usage_limit < 0:
                await message.answer(i18n.get("admin-promo-create-limit-invalid"))
                return

        # Get stored data
        data = await state.get_data()
        promo_code = data.get("promo_code")
        discount_value = data.get("discount_value")

        if not promo_code or not discount_value:
            await message.answer(i18n.get("error-generic"))
            await state.clear()
            return

        # Create promocode via API
        promo_data = {
            "code": promo_code,
            "discount_type": "percentage",
            "discount_value": discount_value,
            "usage_limit": usage_limit,
            "is_active": True,
        }

        promo = await api_client.create_promocode(promo_data)
        promo_id = promo.get("id")

        await message.answer(
            i18n.get(
                "admin-promo-created",
                code=promo_code,
                discount=discount_value,
                limit=usage_limit or i18n.get("unlimited"),
                promo_id=promo_id,
            )
        )

        await state.clear()
        logger.info(
            "admin_promo_created",
            admin_id=message.from_user.id,
            promo_id=promo_id,
            promo_code=promo_code,
        )

    except ValueError:
        await message.answer(i18n.get("admin-promo-create-limit-invalid-number"))
    except Exception as e:
        logger.error("admin_promo_creation_error", admin_id=message.from_user.id, error=str(e))
        await message.answer(i18n.get("error-generic"))
        await state.clear()
