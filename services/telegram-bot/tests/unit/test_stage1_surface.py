from __future__ import annotations

import pytest
from aiogram.types import MenuButtonCommands, MenuButtonWebApp
from pydantic import ValidationError

from src.config import BotSettings
from src.stage1_surface import (
    STAGE1_PUBLIC_COMMANDS,
    build_stage1_menu_button,
    build_stage1_public_commands,
)


def _clone_settings(settings: BotSettings, **overrides: object) -> BotSettings:
    data = settings.model_dump()
    data.update(overrides)
    return BotSettings(**data)


def test_stage1_public_commands_match_implemented_s1_entrypoints() -> None:
    commands = build_stage1_public_commands()

    assert [command.command for command in commands] == [
        "start",
        "menu",
        "connect",
        "plans",
        "trial",
        "support",
        "paysupport",
    ]
    assert len(commands) == len(STAGE1_PUBLIC_COMMANDS)
    assert all(command.description for command in commands)


def test_stage1_menu_button_defaults_to_command_menu(mock_settings: BotSettings) -> None:
    menu_button = build_stage1_menu_button(mock_settings)

    assert isinstance(menu_button, MenuButtonCommands)


def test_stage1_menu_button_supports_miniapp_when_url_is_configured(mock_settings: BotSettings) -> None:
    settings = _clone_settings(
        mock_settings,
        bot_menu_button="miniapp",
        miniapp_url="https://cyber-vpn.net/ru-RU/miniapp",
    )

    menu_button = build_stage1_menu_button(settings)

    assert isinstance(menu_button, MenuButtonWebApp)
    assert menu_button.web_app.url == "https://cyber-vpn.net/ru-RU/miniapp"


def test_stage1_menu_button_rejects_miniapp_without_url(mock_settings: BotSettings) -> None:
    with pytest.raises(ValidationError, match="TELEGRAM_MINIAPP_URL is required"):
        _clone_settings(mock_settings, bot_menu_button="miniapp", miniapp_url=None)


def test_stage1_rejects_same_staging_and_production_bot_username(mock_settings: BotSettings) -> None:
    with pytest.raises(ValidationError, match="must be different"):
        _clone_settings(
            mock_settings,
            staging_bot_username="@CyberVPNBot",
            production_bot_username="CyberVPNBot",
        )


def test_stage1_rejects_staging_bot_username_mismatch(mock_settings: BotSettings) -> None:
    with pytest.raises(ValidationError, match="BOT_USERNAME must match TELEGRAM_BOT_STAGING_USERNAME"):
        _clone_settings(
            mock_settings,
            environment="staging",
            bot_username="CyberVPNProdBot",
            staging_bot_username="CyberVPNStageBot",
            production_bot_username="CyberVPNProdBot",
        )
