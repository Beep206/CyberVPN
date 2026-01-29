from __future__ import annotations

from typing import TYPE_CHECKING

import structlog
from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from middleware.admin import admin_required
from states.admin import AdminAccessState

if TYPE_CHECKING:
    from aiogram_i18n import I18nContext

    from clients.api_client import APIClient

logger = structlog.get_logger(__name__)

router = Router(name="admin_access")
router.message.middleware(admin_required)
router.callback_query.middleware(admin_required)


@router.callback_query(F.data == "admin:access:settings")
async def access_settings_handler(
    callback: CallbackQuery,
    i18n: I18nContext,
    api_client: APIClient,
) -> None:
    """Show access control settings."""
    try:
        # Get current admin list
        admins = await api_client.get_admin_list()

        admin_text = i18n.get("admin-access-title") + "\n\n"

        for admin in admins:
            admin_id = admin.get("telegram_id")
            username = admin.get("username") or admin.get("first_name", "N/A")
            role = admin.get("role", "admin")

            admin_text += f"👤 {username} (ID: {admin_id}) - {role}\n"

        # Create action buttons
        from aiogram.types import InlineKeyboardButton
        from aiogram.utils.keyboard import InlineKeyboardBuilder

        builder = InlineKeyboardBuilder()

        builder.row(
            InlineKeyboardButton(
                text="➕ " + i18n.get("admin-access-add"),
                callback_data="admin:access:add",
            )
        )
        builder.row(
            InlineKeyboardButton(
                text="➖ " + i18n.get("admin-access-remove"),
                callback_data="admin:access:remove",
            )
        )
        builder.row(
            InlineKeyboardButton(
                text="🔙 " + i18n.get("button-back"),
                callback_data="admin:settings",
            )
        )

        await callback.message.edit_text(
            text=admin_text,
            reply_markup=builder.as_markup(),
        )

        logger.info("admin_access_settings_viewed", admin_id=callback.from_user.id)

    except Exception as e:
        logger.error("admin_access_settings_error", admin_id=callback.from_user.id, error=str(e))
        await callback.answer(i18n.get("error-generic"), show_alert=True)

    await callback.answer()


@router.callback_query(F.data == "admin:access:add")
async def access_add_prompt_handler(
    callback: CallbackQuery,
    i18n: I18nContext,
    state: FSMContext,
) -> None:
    """Prompt to add new admin."""
    await callback.message.edit_text(
        text=i18n.get("admin-access-add-prompt"),
    )

    await state.set_state(AdminAccessState.adding_admin)
    logger.info("admin_access_add_started", admin_id=callback.from_user.id)

    await callback.answer()


@router.message(AdminAccessState.adding_admin, F.text)
async def access_add_handler(
    message: Message,
    i18n: I18nContext,
    api_client: APIClient,
    state: FSMContext,
) -> None:
    """Add new admin."""
    try:
        new_admin_id = int(message.text.strip())

        # Add admin via API
        result = await api_client.add_admin(new_admin_id)

        await message.answer(
            i18n.get(
                "admin-access-added",
                admin_id=new_admin_id,
                username=result.get("username", "N/A"),
            )
        )

        await state.clear()
        logger.info("admin_access_added", admin_id=message.from_user.id, new_admin_id=new_admin_id)

    except ValueError:
        await message.answer(i18n.get("admin-access-invalid-id"))
    except Exception as e:
        logger.error("admin_access_add_error", admin_id=message.from_user.id, error=str(e))
        await message.answer(i18n.get("error-generic"))
        await state.clear()


@router.callback_query(F.data == "admin:access:remove")
async def access_remove_prompt_handler(
    callback: CallbackQuery,
    i18n: I18nContext,
    state: FSMContext,
) -> None:
    """Prompt to remove admin."""
    await callback.message.edit_text(
        text=i18n.get("admin-access-remove-prompt"),
    )

    await state.set_state(AdminAccessState.removing_admin)
    logger.info("admin_access_remove_started", admin_id=callback.from_user.id)

    await callback.answer()


@router.message(AdminAccessState.removing_admin, F.text)
async def access_remove_handler(
    message: Message,
    i18n: I18nContext,
    api_client: APIClient,
    state: FSMContext,
) -> None:
    """Remove admin."""
    try:
        remove_admin_id = int(message.text.strip())

        # Prevent self-removal
        if remove_admin_id == message.from_user.id:
            await message.answer(i18n.get("admin-access-cannot-remove-self"))
            await state.clear()
            return

        # Remove admin via API
        await api_client.remove_admin(remove_admin_id)

        await message.answer(
            i18n.get("admin-access-removed", admin_id=remove_admin_id)
        )

        await state.clear()
        logger.info("admin_access_removed", admin_id=message.from_user.id, removed_admin_id=remove_admin_id)

    except ValueError:
        await message.answer(i18n.get("admin-access-invalid-id"))
    except Exception as e:
        logger.error("admin_access_remove_error", admin_id=message.from_user.id, error=str(e))
        await message.answer(i18n.get("error-generic"))
        await state.clear()
