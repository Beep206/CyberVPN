from __future__ import annotations

from typing import TYPE_CHECKING

import structlog
from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from src.states.admin import AdminReferralSettingsState

if TYPE_CHECKING:
    from aiogram_i18n import I18nContext

    from src.services.api_client import CyberVPNAPIClient

logger = structlog.get_logger(__name__)

router = Router(name="admin_referral_settings")


@router.callback_query(F.data == "admin:referral:settings")
async def referral_settings_handler(
    callback: CallbackQuery,
    i18n: I18nContext,
    api_client: CyberVPNAPIClient,
) -> None:
    """Show referral program settings."""
    try:
        # Get current referral settings
        settings = await api_client.get_referral_settings()

        settings_text = i18n.get(
            "admin-referral-settings-info",
            bonus_percent=settings.get("bonus_percent", 0),
            min_withdrawal=settings.get("min_withdrawal", 0),
            is_enabled=i18n.get("yes") if settings.get("is_enabled") else i18n.get("no"),
        )

        # Create action buttons
        from aiogram.types import InlineKeyboardButton
        from aiogram.utils.keyboard import InlineKeyboardBuilder

        builder = InlineKeyboardBuilder()

        toggle_text = (
            i18n.get("admin-referral-disable") if settings.get("is_enabled") else i18n.get("admin-referral-enable")
        )

        builder.row(
            InlineKeyboardButton(
                text=toggle_text,
                callback_data="admin:referral:toggle",
                style="primary",
            )
        )
        builder.row(
            InlineKeyboardButton(
                text=i18n.get("admin-referral-edit-bonus"),
                callback_data="admin:referral:edit:bonus",
                style="primary",
            )
        )
        builder.row(
            InlineKeyboardButton(
                text=i18n.get("admin-referral-edit-withdrawal"),
                callback_data="admin:referral:edit:withdrawal",
                style="primary",
            )
        )
        builder.row(
            InlineKeyboardButton(
                text="🔙 " + i18n.get("button-back"),
                callback_data="admin:settings",
                style="primary",
            )
        )

        await callback.message.edit_text(
            text=settings_text,
            reply_markup=builder.as_markup(),
        )

        logger.info("admin_referral_settings_viewed", admin_id=callback.from_user.id)

    except Exception as e:
        logger.error("admin_referral_settings_error", admin_id=callback.from_user.id, error=str(e))
        await callback.answer(i18n.get("error-generic"), show_alert=True)

    await callback.answer()


@router.callback_query(F.data == "admin:referral:toggle")
async def referral_toggle_handler(
    callback: CallbackQuery,
    i18n: I18nContext,
    api_client: CyberVPNAPIClient,
) -> None:
    """Toggle referral program."""
    try:
        # Toggle referral program
        result = await api_client.toggle_referral_program()
        is_enabled = result.get("is_enabled", False)

        if is_enabled:
            await callback.answer(i18n.get("admin-referral-enabled"), show_alert=True)
        else:
            await callback.answer(i18n.get("admin-referral-disabled"), show_alert=True)

        # Refresh settings view
        await referral_settings_handler(callback, i18n, api_client)

        logger.info("admin_referral_toggled", admin_id=callback.from_user.id, is_enabled=is_enabled)

    except Exception as e:
        logger.error("admin_referral_toggle_error", admin_id=callback.from_user.id, error=str(e))
        await callback.answer(i18n.get("error-generic"), show_alert=True)


@router.callback_query(F.data == "admin:referral:edit:bonus")
async def referral_edit_bonus_prompt_handler(
    callback: CallbackQuery,
    i18n: I18nContext,
    state: FSMContext,
) -> None:
    """Prompt to edit referral bonus percent."""
    await callback.message.edit_text(
        text=i18n.get("admin-referral-edit-bonus-prompt"),
    )

    await state.set_state(AdminReferralSettingsState.editing_bonus)
    logger.info("admin_referral_edit_bonus_started", admin_id=callback.from_user.id)

    await callback.answer()


@router.message(AdminReferralSettingsState.editing_bonus, F.text)
async def referral_edit_bonus_handler(
    message: Message,
    i18n: I18nContext,
    api_client: CyberVPNAPIClient,
    state: FSMContext,
) -> None:
    """Update referral bonus percent."""
    try:
        bonus_percent = int(message.text.strip())

        if bonus_percent < 0 or bonus_percent > 100:
            await message.answer(i18n.get("admin-referral-bonus-invalid-range"))
            return

        # Update setting via API
        await api_client.update_referral_settings({"bonus_percent": bonus_percent})

        await message.answer(i18n.get("admin-referral-bonus-updated", bonus=bonus_percent))

        await state.clear()
        logger.info("admin_referral_bonus_updated", admin_id=message.from_user.id, new_bonus=bonus_percent)

    except ValueError:
        await message.answer(i18n.get("admin-referral-bonus-invalid-number"))
    except Exception as e:
        logger.error("admin_referral_bonus_update_error", admin_id=message.from_user.id, error=str(e))
        await message.answer(i18n.get("error-generic"))
        await state.clear()


@router.callback_query(F.data == "admin:referral:edit:withdrawal")
async def referral_edit_withdrawal_prompt_handler(
    callback: CallbackQuery,
    i18n: I18nContext,
    state: FSMContext,
) -> None:
    """Prompt to edit minimum withdrawal amount."""
    await callback.message.edit_text(
        text=i18n.get("admin-referral-edit-withdrawal-prompt"),
    )

    await state.set_state(AdminReferralSettingsState.editing_withdrawal)
    logger.info("admin_referral_edit_withdrawal_started", admin_id=callback.from_user.id)

    await callback.answer()


@router.message(AdminReferralSettingsState.editing_withdrawal, F.text)
async def referral_edit_withdrawal_handler(
    message: Message,
    i18n: I18nContext,
    api_client: CyberVPNAPIClient,
    state: FSMContext,
) -> None:
    """Update minimum withdrawal amount."""
    try:
        min_withdrawal = float(message.text.strip())

        if min_withdrawal < 0:
            await message.answer(i18n.get("admin-referral-withdrawal-invalid"))
            return

        # Update setting via API
        await api_client.update_referral_settings({"min_withdrawal": min_withdrawal})

        await message.answer(i18n.get("admin-referral-withdrawal-updated", amount=min_withdrawal))

        await state.clear()
        logger.info("admin_referral_withdrawal_updated", admin_id=message.from_user.id, new_min=min_withdrawal)

    except ValueError:
        await message.answer(i18n.get("admin-referral-withdrawal-invalid-number"))
    except Exception as e:
        logger.error("admin_referral_withdrawal_update_error", admin_id=message.from_user.id, error=str(e))
        await message.answer(i18n.get("error-generic"))
        await state.clear()
