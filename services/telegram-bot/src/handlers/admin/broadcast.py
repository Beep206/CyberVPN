from __future__ import annotations

from typing import TYPE_CHECKING

import structlog
from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from middleware.admin import admin_required
from states.admin import AdminBroadcastState

if TYPE_CHECKING:
    from aiogram_i18n import I18nContext

    from clients.api_client import APIClient

logger = structlog.get_logger(__name__)

router = Router(name="admin_broadcast")
router.message.middleware(admin_required)
router.callback_query.middleware(admin_required)


@router.callback_query(F.data == "admin:broadcast")
async def broadcast_menu_handler(
    callback: CallbackQuery,
    i18n: I18nContext,
    state: FSMContext,
) -> None:
    """Start broadcast flow."""
    await callback.message.edit_text(
        text=i18n.get("admin-broadcast-compose-prompt"),
    )

    await state.set_state(AdminBroadcastState.composing_message)
    logger.info("admin_broadcast_started", admin_id=callback.from_user.id)

    await callback.answer()


@router.message(AdminBroadcastState.composing_message, F.text | F.photo | F.video)
async def broadcast_message_composed_handler(
    message: Message,
    i18n: I18nContext,
    state: FSMContext,
) -> None:
    """Handle composed broadcast message."""
    # Store message data
    message_data = {
        "text": message.text or message.caption,
        "message_id": message.message_id,
        "chat_id": message.chat.id,
    }

    if message.photo:
        message_data["photo_file_id"] = message.photo[-1].file_id
    elif message.video:
        message_data["video_file_id"] = message.video.file_id

    await state.update_data(broadcast_message=message_data)

    # Show audience selection
    from aiogram.types import InlineKeyboardButton
    from aiogram.utils.keyboard import InlineKeyboardBuilder

    builder = InlineKeyboardBuilder()

    builder.row(
        InlineKeyboardButton(
            text=i18n.get("admin-broadcast-audience-all"),
            callback_data="admin:broadcast:audience:all",
        )
    )
    builder.row(
        InlineKeyboardButton(
            text=i18n.get("admin-broadcast-audience-active"),
            callback_data="admin:broadcast:audience:active",
        )
    )
    builder.row(
        InlineKeyboardButton(
            text=i18n.get("admin-broadcast-audience-inactive"),
            callback_data="admin:broadcast:audience:inactive",
        )
    )
    builder.row(
        InlineKeyboardButton(
            text=i18n.get("admin-broadcast-audience-trial"),
            callback_data="admin:broadcast:audience:trial",
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="❌ " + i18n.get("button-cancel"),
            callback_data="admin:broadcast:cancel",
        )
    )

    await message.answer(
        text=i18n.get("admin-broadcast-select-audience"),
        reply_markup=builder.as_markup(),
    )

    await state.set_state(AdminBroadcastState.selecting_audience)
    logger.info("admin_broadcast_message_composed", admin_id=message.from_user.id)


@router.callback_query(AdminBroadcastState.selecting_audience, F.data.startswith("admin:broadcast:audience:"))
async def broadcast_audience_selected_handler(
    callback: CallbackQuery,
    i18n: I18nContext,
    api_client: APIClient,
    state: FSMContext,
) -> None:
    """Handle audience selection."""
    audience_type = callback.data.split(":")[3]

    # Store audience type
    await state.update_data(audience_type=audience_type)

    try:
        # Get estimated audience count
        count = await api_client.get_broadcast_audience_count(audience_type)

        # Show confirmation
        from aiogram.types import InlineKeyboardButton
        from aiogram.utils.keyboard import InlineKeyboardBuilder

        builder = InlineKeyboardBuilder()

        builder.row(
            InlineKeyboardButton(
                text="✅ " + i18n.get("admin-broadcast-confirm"),
                callback_data="admin:broadcast:confirm",
            )
        )
        builder.row(
            InlineKeyboardButton(
                text="❌ " + i18n.get("button-cancel"),
                callback_data="admin:broadcast:cancel",
            )
        )

        await callback.message.edit_text(
            text=i18n.get(
                "admin-broadcast-confirm-prompt",
                audience=i18n.get(f"admin-broadcast-audience-{audience_type}"),
                count=count,
            ),
            reply_markup=builder.as_markup(),
        )

        await state.set_state(AdminBroadcastState.confirming)
        logger.info(
            "admin_broadcast_audience_selected",
            admin_id=callback.from_user.id,
            audience_type=audience_type,
            estimated_count=count,
        )

    except Exception as e:
        logger.error("admin_broadcast_audience_error", admin_id=callback.from_user.id, error=str(e))
        await callback.answer(i18n.get("error-generic"), show_alert=True)
        await state.clear()

    await callback.answer()


@router.callback_query(AdminBroadcastState.confirming, F.data == "admin:broadcast:confirm")
async def broadcast_confirm_handler(
    callback: CallbackQuery,
    i18n: I18nContext,
    api_client: APIClient,
    state: FSMContext,
) -> None:
    """Confirm and send broadcast."""
    try:
        # Get stored data
        data = await state.get_data()
        message_data = data.get("broadcast_message")
        audience_type = data.get("audience_type")

        if not message_data or not audience_type:
            await callback.answer(i18n.get("error-generic"), show_alert=True)
            await state.clear()
            return

        # Create broadcast via API
        broadcast = await api_client.create_broadcast(
            message_text=message_data.get("text"),
            audience_type=audience_type,
            photo_file_id=message_data.get("photo_file_id"),
            video_file_id=message_data.get("video_file_id"),
        )

        broadcast_id = broadcast.get("id")

        await callback.message.edit_text(
            text=i18n.get(
                "admin-broadcast-sending",
                broadcast_id=broadcast_id,
            ),
        )

        # Clear state
        await state.clear()

        logger.info(
            "admin_broadcast_confirmed",
            admin_id=callback.from_user.id,
            broadcast_id=broadcast_id,
            audience_type=audience_type,
        )

        # Note: Actual sending is handled by broadcast_service via background task

    except Exception as e:
        logger.error("admin_broadcast_confirm_error", admin_id=callback.from_user.id, error=str(e))
        await callback.answer(i18n.get("error-generic"), show_alert=True)
        await state.clear()

    await callback.answer()


@router.callback_query(F.data == "admin:broadcast:cancel")
async def broadcast_cancel_handler(
    callback: CallbackQuery,
    i18n: I18nContext,
    state: FSMContext,
) -> None:
    """Cancel broadcast."""
    await state.clear()

    from keyboards.admin_main import admin_main_keyboard

    await callback.message.edit_text(
        text=i18n.get("admin-broadcast-cancelled"),
        reply_markup=admin_main_keyboard(i18n),
    )

    logger.info("admin_broadcast_cancelled", admin_id=callback.from_user.id)
    await callback.answer()


@router.callback_query(F.data == "admin:broadcast:history")
async def broadcast_history_handler(
    callback: CallbackQuery,
    i18n: I18nContext,
    api_client: APIClient,
) -> None:
    """Show broadcast history."""
    try:
        # Get recent broadcasts
        broadcasts = await api_client.get_broadcast_history(limit=10)

        if not broadcasts:
            await callback.answer(i18n.get("admin-broadcast-no-history"), show_alert=True)
            return

        # Format history
        history_text = i18n.get("admin-broadcast-history-title") + "\n\n"

        for broadcast in broadcasts:
            broadcast_id = broadcast.get("id")
            created_at = broadcast.get("created_at", "N/A")[:16]
            audience = broadcast.get("audience_type", "N/A")
            status = broadcast.get("status", "N/A")
            sent = broadcast.get("sent_count", 0)
            failed = broadcast.get("failed_count", 0)

            history_text += (
                f"🆔 {broadcast_id} | {created_at}\n"
                f"👥 {audience} | {status}\n"
                f"✅ {sent} / ❌ {failed}\n\n"
            )

        from aiogram.types import InlineKeyboardButton
        from aiogram.utils.keyboard import InlineKeyboardBuilder

        builder = InlineKeyboardBuilder()
        builder.row(
            InlineKeyboardButton(
                text="🔙 " + i18n.get("button-back"),
                callback_data="admin:menu",
            )
        )

        await callback.message.edit_text(
            text=history_text,
            reply_markup=builder.as_markup(),
        )

        logger.info("admin_broadcast_history_viewed", admin_id=callback.from_user.id)

    except Exception as e:
        logger.error("admin_broadcast_history_error", admin_id=callback.from_user.id, error=str(e))
        await callback.answer(i18n.get("error-generic"), show_alert=True)

    await callback.answer()
