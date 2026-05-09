"""Stage 1 Telegram Bot public surface contract."""

from __future__ import annotations

from typing import TYPE_CHECKING

import structlog
from aiogram.types import (
    BotCommand,
    MenuButtonCommands,
    MenuButtonDefault,
    MenuButtonWebApp,
    WebAppInfo,
)

if TYPE_CHECKING:
    from aiogram import Bot

    from src.config import BotSettings

logger = structlog.get_logger(__name__)

STAGE1_PUBLIC_COMMANDS: tuple[tuple[str, str], ...] = (
    ("start", "Start CyberVPN and open onboarding"),
    ("menu", "Open the main menu"),
    ("connect", "Get VPN access and config"),
    ("plans", "View subscription plans"),
    ("trial", "Start a trial if available"),
    ("support", "Contact support"),
    ("paysupport", "Payment and refund support"),
)


def build_stage1_public_commands() -> list[BotCommand]:
    """Build the default S1 command list exposed in Telegram clients."""
    return [
        BotCommand(command=command, description=description)
        for command, description in STAGE1_PUBLIC_COMMANDS
    ]


def build_stage1_menu_button(settings: BotSettings) -> MenuButtonCommands | MenuButtonDefault | MenuButtonWebApp:
    """Build the S1 default Telegram menu button from settings."""
    if settings.bot_menu_button == "miniapp":
        if settings.miniapp_url is None:
            raise ValueError("TELEGRAM_MINIAPP_URL is required for the miniapp menu button")
        return MenuButtonWebApp(
            text="Open CyberVPN",
            web_app=WebAppInfo(url=str(settings.miniapp_url)),
        )

    if settings.bot_menu_button == "default":
        return MenuButtonDefault()

    return MenuButtonCommands()


async def apply_stage1_telegram_surface(bot: Bot, settings: BotSettings) -> None:
    """Apply S1 Telegram commands and default menu button via Bot API."""
    commands = build_stage1_public_commands()
    await bot.set_my_commands(commands=commands)
    await bot.set_chat_menu_button(menu_button=build_stage1_menu_button(settings))

    logger.info(
        "stage1_telegram_surface_configured",
        environment=settings.environment,
        bot_menu_button=settings.bot_menu_button,
        command_count=len(commands),
    )
