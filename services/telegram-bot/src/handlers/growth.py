"""Growth/rewards menu handlers for Telegram Bot."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import structlog
from aiogram import F, Router

from src.keyboards.growth import growth_menu_keyboard, has_growth_actions
from src.keyboards.miniapp import miniapp_open_keyboard

if TYPE_CHECKING:
    from aiogram.types import CallbackQuery
    from aiogram_i18n import I18nContext

    from src.config import BotSettings
    from src.services.api_client import CyberVPNAPIClient

logger = structlog.get_logger(__name__)

router = Router(name="growth")


async def get_safe_client_capabilities(api_client: CyberVPNAPIClient) -> dict[str, Any] | None:
    """Fetch public client capabilities without blocking the bot menu on failures."""
    try:
        return await api_client.get_client_capabilities()
    except Exception as exc:
        logger.warning("client_capabilities_fetch_failed", error=str(exc))
        return None


@router.callback_query(F.data.in_({"menu:growth", "growth:menu"}))
async def growth_menu_handler(
    callback: CallbackQuery,
    i18n: I18nContext,
    api_client: CyberVPNAPIClient,
    settings: BotSettings | None = None,
) -> None:
    """Open the unified Rewards menu."""
    capabilities = await get_safe_client_capabilities(api_client)
    if not has_growth_actions(capabilities):
        await callback.message.edit_text(
            text=i18n.get("growth-disabled"),
            reply_markup=miniapp_open_keyboard(i18n, settings, path="/rewards"),
        )
        await callback.answer()
        return

    await callback.message.edit_text(
        text=i18n.get("growth-menu-title"),
        reply_markup=growth_menu_keyboard(i18n, settings=settings, capabilities=capabilities),
    )
    await callback.answer()


@router.callback_query(F.data == "menu:finance")
async def finance_menu_handler(
    callback: CallbackQuery,
    i18n: I18nContext,
    settings: BotSettings | None = None,
) -> None:
    """Open finance entry points without starting payment-side effects."""
    await callback.message.edit_text(
        text=i18n.get("finance-menu-title"),
        reply_markup=miniapp_open_keyboard(i18n, settings, path="/wallet", text_key="btn-finance-open"),
    )
    await callback.answer()


@router.callback_query(F.data == "miniapp:unavailable")
async def miniapp_unavailable_handler(callback: CallbackQuery, i18n: I18nContext) -> None:
    """Tell the user that Mini App links are not configured for this bot."""
    await callback.answer(i18n.get("miniapp-unavailable"), show_alert=True)
