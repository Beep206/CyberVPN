from __future__ import annotations

from typing import TYPE_CHECKING

import structlog
from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from middleware.admin import admin_required
from states.admin import AdminUserState

if TYPE_CHECKING:
    from aiogram_i18n import I18nContext

    from clients.api_client import APIClient

logger = structlog.get_logger(__name__)

router = Router(name="admin_users")
router.message.middleware(admin_required)
router.callback_query.middleware(admin_required)


@router.callback_query(F.data == "admin:users")
async def users_menu_handler(
    callback: CallbackQuery,
    i18n: I18nContext,
) -> None:
    """Show users management menu."""
    from aiogram.types import InlineKeyboardButton
    from aiogram.utils.keyboard import InlineKeyboardBuilder

    builder = InlineKeyboardBuilder()

    builder.row(
        InlineKeyboardButton(
            text=i18n.get("admin-users-search"),
            callback_data="admin:users:search",
        )
    )
    builder.row(
        InlineKeyboardButton(
            text=i18n.get("admin-users-list-recent"),
            callback_data="admin:users:list",
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="🔙 " + i18n.get("button-back"),
            callback_data="admin:menu",
        )
    )

    await callback.message.edit_text(
        text=i18n.get("admin-users-title"),
        reply_markup=builder.as_markup(),
    )

    await callback.answer()


@router.callback_query(F.data == "admin:users:search")
async def users_search_prompt_handler(
    callback: CallbackQuery,
    i18n: I18nContext,
    state: FSMContext,
) -> None:
    """Prompt for user search."""
    await callback.message.edit_text(
        text=i18n.get("admin-users-search-prompt"),
    )

    await state.set_state(AdminUserState.searching)
    logger.info("admin_user_search_started", admin_id=callback.from_user.id)

    await callback.answer()


@router.message(AdminUserState.searching, F.text)
async def users_search_handler(
    message: Message,
    i18n: I18nContext,
    api_client: APIClient,
    state: FSMContext,
) -> None:
    """Search for users."""
    search_query = message.text.strip()

    try:
        # Search users via API
        users = await api_client.search_users(search_query)

        if not users:
            await message.answer(i18n.get("admin-users-search-no-results"))
            await state.clear()
            return

        # Display search results
        from aiogram.types import InlineKeyboardButton
        from aiogram.utils.keyboard import InlineKeyboardBuilder

        builder = InlineKeyboardBuilder()

        for user in users[:10]:  # Limit to 10 results
            user_id = user.get("telegram_id")
            username = user.get("username") or user.get("first_name", "N/A")

            builder.row(
                InlineKeyboardButton(
                    text=f"👤 {username} (ID: {user_id})",
                    callback_data=f"admin:user:view:{user_id}",
                )
            )

        builder.row(
            InlineKeyboardButton(
                text="🔙 " + i18n.get("button-back"),
                callback_data="admin:users",
            )
        )

        await message.answer(
            text=i18n.get("admin-users-search-results", count=len(users)),
            reply_markup=builder.as_markup(),
        )

        await state.clear()
        logger.info("admin_user_search_completed", admin_id=message.from_user.id, results=len(users))

    except Exception as e:
        logger.error("admin_user_search_error", admin_id=message.from_user.id, error=str(e))
        await message.answer(i18n.get("error-generic"))
        await state.clear()


@router.callback_query(F.data == "admin:users:list")
async def users_list_handler(
    callback: CallbackQuery,
    i18n: I18nContext,
    api_client: APIClient,
) -> None:
    """List recent users."""
    try:
        # Get recent users
        users = await api_client.get_recent_users(limit=20)

        if not users:
            await callback.answer(i18n.get("admin-users-no-users"), show_alert=True)
            return

        # Display user list
        from aiogram.types import InlineKeyboardButton
        from aiogram.utils.keyboard import InlineKeyboardBuilder

        builder = InlineKeyboardBuilder()

        for user in users:
            user_id = user.get("telegram_id")
            username = user.get("username") or user.get("first_name", "N/A")
            created_at = user.get("created_at", "N/A")[:10]  # Date only

            builder.row(
                InlineKeyboardButton(
                    text=f"👤 {username} - {created_at}",
                    callback_data=f"admin:user:view:{user_id}",
                )
            )

        builder.row(
            InlineKeyboardButton(
                text="🔙 " + i18n.get("button-back"),
                callback_data="admin:users",
            )
        )

        await callback.message.edit_text(
            text=i18n.get("admin-users-list-title"),
            reply_markup=builder.as_markup(),
        )

        logger.info("admin_users_list_viewed", admin_id=callback.from_user.id)

    except Exception as e:
        logger.error("admin_users_list_error", admin_id=callback.from_user.id, error=str(e))
        await callback.answer(i18n.get("error-generic"), show_alert=True)

    await callback.answer()


@router.callback_query(F.data.startswith("admin:user:view:"))
async def user_view_handler(
    callback: CallbackQuery,
    i18n: I18nContext,
    api_client: APIClient,
) -> None:
    """View user details."""
    user_id = int(callback.data.split(":")[3])

    try:
        # Get user details
        user = await api_client.get_user(user_id)

        # Get user subscriptions
        subscriptions = await api_client.get_user_subscriptions(user_id)
        active_subs = [sub for sub in subscriptions if sub.get("status") == "active"]

        user_text = i18n.get(
            "admin-user-details",
            user_id=user_id,
            username=user.get("username", "N/A"),
            first_name=user.get("first_name", "N/A"),
            language=user.get("language_code", "en").upper(),
            registered=user.get("created_at", "N/A"),
            active_subs=len(active_subs),
            total_subs=len(subscriptions),
        )

        # Create action buttons
        from aiogram.types import InlineKeyboardButton
        from aiogram.utils.keyboard import InlineKeyboardBuilder

        builder = InlineKeyboardBuilder()

        builder.row(
            InlineKeyboardButton(
                text=i18n.get("admin-user-ban"),
                callback_data=f"admin:user:ban:{user_id}",
            )
        )
        builder.row(
            InlineKeyboardButton(
                text=i18n.get("admin-user-extend-sub"),
                callback_data=f"admin:user:extend:{user_id}",
            )
        )
        builder.row(
            InlineKeyboardButton(
                text="🔙 " + i18n.get("button-back"),
                callback_data="admin:users",
            )
        )

        await callback.message.edit_text(
            text=user_text,
            reply_markup=builder.as_markup(),
        )

        logger.info("admin_user_viewed", admin_id=callback.from_user.id, target_user_id=user_id)

    except Exception as e:
        logger.error("admin_user_view_error", admin_id=callback.from_user.id, target_user_id=user_id, error=str(e))
        await callback.answer(i18n.get("error-generic"), show_alert=True)

    await callback.answer()


@router.callback_query(F.data.startswith("admin:user:ban:"))
async def user_ban_handler(
    callback: CallbackQuery,
    i18n: I18nContext,
    api_client: APIClient,
) -> None:
    """Ban/unban user."""
    user_id = int(callback.data.split(":")[3])

    try:
        # Toggle ban status
        result = await api_client.toggle_user_ban(user_id)
        is_banned = result.get("is_banned", False)

        if is_banned:
            await callback.answer(i18n.get("admin-user-banned"), show_alert=True)
        else:
            await callback.answer(i18n.get("admin-user-unbanned"), show_alert=True)

        # Refresh user view
        await user_view_handler(callback, i18n, api_client)

        logger.info("admin_user_ban_toggled", admin_id=callback.from_user.id, target_user_id=user_id, is_banned=is_banned)

    except Exception as e:
        logger.error("admin_user_ban_error", admin_id=callback.from_user.id, target_user_id=user_id, error=str(e))
        await callback.answer(i18n.get("error-generic"), show_alert=True)


@router.callback_query(F.data.startswith("admin:user:extend:"))
async def user_extend_subscription_prompt_handler(
    callback: CallbackQuery,
    i18n: I18nContext,
    state: FSMContext,
) -> None:
    """Prompt for subscription extension days."""
    user_id = int(callback.data.split(":")[3])

    await state.update_data(extend_user_id=user_id)
    await state.set_state(AdminUserState.extending_subscription)

    await callback.message.edit_text(
        text=i18n.get("admin-user-extend-prompt"),
    )

    await callback.answer()


@router.message(AdminUserState.extending_subscription, F.text)
async def user_extend_subscription_handler(
    message: Message,
    i18n: I18nContext,
    api_client: APIClient,
    state: FSMContext,
) -> None:
    """Extend user subscription."""
    try:
        days = int(message.text.strip())

        if days <= 0 or days > 365:
            await message.answer(i18n.get("admin-user-extend-invalid-days"))
            return

        # Get user ID from state
        data = await state.get_data()
        user_id = data.get("extend_user_id")

        if not user_id:
            await message.answer(i18n.get("error-generic"))
            await state.clear()
            return

        # Extend subscription via API
        result = await api_client.extend_user_subscription(user_id, days)

        await message.answer(
            i18n.get(
                "admin-user-extended",
                user_id=user_id,
                days=days,
                new_expiry=result.get("new_expiry_date", "N/A"),
            )
        )

        await state.clear()
        logger.info("admin_user_subscription_extended", admin_id=message.from_user.id, target_user_id=user_id, days=days)

    except ValueError:
        await message.answer(i18n.get("admin-user-extend-invalid-number"))
    except Exception as e:
        logger.error("admin_user_extend_error", admin_id=message.from_user.id, error=str(e))
        await message.answer(i18n.get("error-generic"))
        await state.clear()
