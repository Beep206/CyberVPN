from __future__ import annotations

from typing import Any

from src.keyboards.miniapp import miniapp_onboarding_keyboard


def _clone_settings(settings: Any, **overrides: object):
    data = settings.model_dump()
    data.update(overrides)
    return settings.__class__(**data)


def _contains_key(value: object, key: str) -> bool:
    if isinstance(value, dict):
        return key in value or any(_contains_key(item, key) for item in value.values())
    if isinstance(value, list):
        return any(_contains_key(item, key) for item in value)
    return False


def test_miniapp_onboarding_keyboard_omits_telegram_unsupported_style(mock_settings) -> None:
    settings = _clone_settings(
        mock_settings,
        miniapp_url="https://cyber-vpn.net/ru-RU/miniapp",
    )

    keyboard = miniapp_onboarding_keyboard(lambda key: key, settings)
    payload = keyboard.model_dump(mode="json", exclude_none=True)

    assert not _contains_key(payload, "style")
    assert payload["inline_keyboard"][0][0]["web_app"]["url"] == "https://cyber-vpn.net/ru-RU/miniapp/onboarding/code"
    assert payload["inline_keyboard"][1][0]["callback_data"] == "growth:code"
    assert payload["inline_keyboard"][2][0]["callback_data"] == "menu:support"
