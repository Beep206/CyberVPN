from __future__ import annotations

from typing import TYPE_CHECKING

import structlog
from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from middleware.admin import admin_required

if TYPE_CHECKING:
    from aiogram_i18n import I18nContext

logger = structlog.get_logger(__name__)

router = Router(name="admin_help")
router.message.middleware(admin_required)


@router.message(Command("adminhelp"))
async def admin_help_handler(
    message: Message,
    i18n: I18nContext,
) -> None:
    """Show admin help with available commands."""
    help_text = i18n.get("admin-help-title") + "\n\n"

    help_text += "🎛️ " + i18n.get("admin-help-commands") + ":\n\n"

    commands = [
        ("/admin", i18n.get("admin-help-admin-panel")),
        ("/adminhelp", i18n.get("admin-help-show-help")),
        ("", ""),  # Separator
        ("👤 " + i18n.get("admin-help-user-management"), ""),
        ("  • " + i18n.get("admin-help-search-users"), ""),
        ("  • " + i18n.get("admin-help-view-users"), ""),
        ("  • " + i18n.get("admin-help-ban-users"), ""),
        ("  • " + i18n.get("admin-help-extend-subs"), ""),
        ("", ""),  # Separator
        ("📊 " + i18n.get("admin-help-statistics"), ""),
        ("  • " + i18n.get("admin-help-view-stats"), ""),
        ("  • " + i18n.get("admin-help-detailed-stats"), ""),
        ("", ""),  # Separator
        ("📢 " + i18n.get("admin-help-broadcast"), ""),
        ("  • " + i18n.get("admin-help-send-broadcast"), ""),
        ("  • " + i18n.get("admin-help-broadcast-history"), ""),
        ("", ""),  # Separator
        ("💰 " + i18n.get("admin-help-plans"), ""),
        ("  • " + i18n.get("admin-help-manage-plans"), ""),
        ("  • " + i18n.get("admin-help-create-plans"), ""),
        ("", ""),  # Separator
        ("🎟️ " + i18n.get("admin-help-promos"), ""),
        ("  • " + i18n.get("admin-help-manage-promos"), ""),
        ("  • " + i18n.get("admin-help-create-promos"), ""),
        ("", ""),  # Separator
        ("⚙️ " + i18n.get("admin-help-settings"), ""),
        ("  • " + i18n.get("admin-help-access-control"), ""),
        ("  • " + i18n.get("admin-help-payment-gateways"), ""),
        ("  • " + i18n.get("admin-help-referral-program"), ""),
        ("  • " + i18n.get("admin-help-notifications"), ""),
        ("", ""),  # Separator
        ("🔄 " + i18n.get("admin-help-import-sync"), ""),
        ("  • " + i18n.get("admin-help-sync-remnawave"), ""),
        ("  • " + i18n.get("admin-help-import-data"), ""),
        ("", ""),  # Separator
        ("🖥️ " + i18n.get("admin-help-system"), ""),
        ("  • " + i18n.get("admin-help-system-health"), ""),
        ("  • " + i18n.get("admin-help-system-logs"), ""),
        ("  • " + i18n.get("admin-help-cache-management"), ""),
    ]

    for cmd, desc in commands:
        if cmd and desc:
            help_text += f"{cmd} - {desc}\n"
        elif cmd:
            help_text += f"\n{cmd}\n"
        else:
            help_text += "\n"

    help_text += "\n" + i18n.get("admin-help-footer")

    await message.answer(text=help_text)

    logger.info("admin_help_viewed", admin_id=message.from_user.id)
