from __future__ import annotations

from typing import TYPE_CHECKING

import structlog
from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery

from keyboards.profile import language_selection_keyboard, profile_keyboard
from states.account import AccountState

if TYPE_CHECKING:
    from aiogram_i18n import I18nContext

    from clients.api_client import APIClient

logger = structlog.get_logger(__name__)

router = Router(name="account")


@router.callback_query(F.data == "account:profile")
async def show_profile_handler(
    callback: CallbackQuery,
    i18n: I18nContext,
    api_client: APIClient,
) -> None:
    """Show user profile."""
    user_id = callback.from_user.id

    try:
        user = await api_client.get_user(user_id)

        profile_text = i18n.get(
            "profile-details",
            username=user.get("username", "N/A"),
            first_name=user.get("first_name", "N/A"),
            language=user.get("language_code", "en").upper(),
            registered=user.get("created_at", "N/A"),
        )

        await callback.message.edit_text(
            text=profile_text,
            reply_markup=profile_keyboard(i18n),
        )

        logger.info("profile_viewed", user_id=user_id)

    except Exception as e:
        logger.error("profile_view_error", user_id=user_id, error=str(e))
        await callback.answer(i18n.get("error-generic"), show_alert=True)

    await callback.answer()


@router.callback_query(F.data == "account:language")
async def change_language_handler(
    callback: CallbackQuery,
    i18n: I18nContext,
    state: FSMContext,
) -> None:
    """Start language change flow."""
    await callback.message.edit_text(
        text=i18n.get("language-select-prompt"),
        reply_markup=language_selection_keyboard(i18n),
    )

    await state.set_state(AccountState.changing_language)
    logger.info("language_change_started", user_id=callback.from_user.id)

    await callback.answer()


@router.callback_query(AccountState.changing_language, F.data.startswith("language:"))
async def language_selected_handler(
    callback: CallbackQuery,
    i18n: I18nContext,
    api_client: APIClient,
    state: FSMContext,
) -> None:
    """Handle language selection."""
    user_id = callback.from_user.id
    language_code = callback.data.split(":")[1]

    try:
        # Update user language
        await api_client.update_user(user_id, {"language_code": language_code})

        # Update i18n locale
        await i18n.set_locale(language_code)

        await callback.message.edit_text(
            text=i18n.get("language-changed", language=language_code.upper()),
        )

        # Clear state
        await state.clear()

        logger.info("language_changed", user_id=user_id, new_language=language_code)

    except Exception as e:
        logger.error("language_change_error", user_id=user_id, error=str(e))
        await callback.answer(i18n.get("error-generic"), show_alert=True)
        await state.clear()

    await callback.answer()


@router.callback_query(F.data == "account:subscriptions")
async def show_subscriptions_handler(
    callback: CallbackQuery,
    i18n: I18nContext,
    api_client: APIClient,
) -> None:
    """Show user subscriptions history."""
    user_id = callback.from_user.id

    try:
        subscriptions = await api_client.get_user_subscriptions(user_id)

        if not subscriptions:
            await callback.answer(i18n.get("subscriptions-none"), show_alert=True)
            return

        # Format subscriptions list
        subs_text = i18n.get("subscriptions-title") + "\n\n"

        for sub in subscriptions:
            status_emoji = "✅" if sub.get("status") == "active" else "❌"
            subs_text += (
                f"{status_emoji} {sub.get('plan_name', 'N/A')}\n"
                f"   {i18n.get('status')}: {sub.get('status', 'N/A')}\n"
                f"   {i18n.get('expires')}: {sub.get('expires_at', 'N/A')}\n\n"
            )

        await callback.message.edit_text(
            text=subs_text,
            reply_markup=profile_keyboard(i18n),
        )

        logger.info("subscriptions_viewed", user_id=user_id, count=len(subscriptions))

    except Exception as e:
        logger.error("subscriptions_view_error", user_id=user_id, error=str(e))
        await callback.answer(i18n.get("error-generic"), show_alert=True)

    await callback.answer()
