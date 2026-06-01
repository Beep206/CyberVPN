from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock
from urllib.parse import parse_qs, urlparse

import pytest
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message, User

from src.handlers.growth import growth_menu_handler
from src.handlers.promocode import enter_promocode_handler
from src.handlers.referral import _referral_identity, share_referral_link_handler
from src.keyboards.growth import growth_menu_keyboard
from src.keyboards.menu import main_menu_keyboard
from src.models.user import UserDTO, UserStatus


class _I18nStub:
    def __call__(self, key: str, **kwargs: object) -> str:
        return self.get(key, **kwargs)

    def get(self, key: str, **kwargs: object) -> str:
        if kwargs:
            suffix = " ".join(f"{name}={value}" for name, value in sorted(kwargs.items()))
            return f"{key} {suffix}"
        return key


def _callback_data(reply_markup: object) -> set[str]:
    keyboard = getattr(reply_markup, "inline_keyboard", [])
    return {
        button.callback_data
        for row in keyboard
        for button in row
        if getattr(button, "callback_data", None)
    }


def _web_app_urls(reply_markup: object) -> list[str]:
    keyboard = getattr(reply_markup, "inline_keyboard", [])
    urls: list[str] = []
    for row in keyboard:
        for button in row:
            web_app = getattr(button, "web_app", None)
            if web_app is not None:
                urls.append(str(web_app.url))
    return urls


def _first_button_url(reply_markup: object) -> str:
    keyboard = getattr(reply_markup, "inline_keyboard", [])
    return str(keyboard[0][0].url)


def _clone_settings(settings, **overrides: object):
    data = settings.model_dump()
    data.update(overrides)
    return settings.__class__(**data)


def _user(*, status: UserStatus = UserStatus.ACTIVE, is_admin: bool = False) -> UserDTO:
    now = datetime(2026, 6, 1, tzinfo=UTC)
    return UserDTO(
        uuid="user-1",
        telegram_id=123456,
        username="test",
        first_name="Test",
        status=status,
        is_admin=is_admin,
        created_at=now,
        updated_at=now,
    )


def test_main_menu_exposes_unified_cabinet_items_and_admin_gate(mock_settings) -> None:
    settings = _clone_settings(mock_settings, miniapp_url="https://cyber-vpn.net/ru-RU/miniapp")

    keyboard = main_menu_keyboard(_I18nStub(), _user(is_admin=True), settings=settings)

    callbacks = _callback_data(keyboard)
    assert {
        "menu:vpn",
        "menu:subscription",
        "menu:finance",
        "menu:growth",
        "account:profile",
        "menu:support",
        "admin:menu",
    }.issubset(callbacks)
    assert _web_app_urls(keyboard) == ["https://cyber-vpn.net/ru-RU/miniapp"]


def test_growth_keyboard_hides_disabled_capabilities(mock_settings) -> None:
    capabilities = {
        "growth": {
            "invites": False,
            "referral": False,
            "promo_codes": False,
            "gift_codes": False,
            "checkout_code_discounts": False,
            "growth_hub": False,
        }
    }

    keyboard = growth_menu_keyboard(_I18nStub(), settings=mock_settings, capabilities=capabilities)

    callbacks = _callback_data(keyboard)
    assert "growth:referral" not in callbacks
    assert "growth:invites" not in callbacks
    assert "growth:code" not in callbacks
    assert {"miniapp:unavailable", "nav:menu"}.issubset(callbacks)


def test_growth_keyboard_uses_miniapp_buttons_for_complex_flows(mock_settings) -> None:
    settings = _clone_settings(mock_settings, miniapp_url="https://cyber-vpn.net/en-EN/miniapp")
    capabilities = {
        "growth": {
            "invites": True,
            "referral": True,
            "promo_codes": True,
            "gift_codes": True,
            "checkout_code_discounts": True,
            "growth_hub": True,
        }
    }

    keyboard = growth_menu_keyboard(_I18nStub(), settings=settings, capabilities=capabilities)

    callbacks = _callback_data(keyboard)
    assert {"growth:referral", "growth:invites", "growth:code", "nav:menu"}.issubset(callbacks)
    assert _web_app_urls(keyboard) == [
        "https://cyber-vpn.net/en-EN/miniapp/rewards/gifts",
        "https://cyber-vpn.net/en-EN/miniapp/rewards/notifications",
        "https://cyber-vpn.net/en-EN/miniapp/rewards",
    ]


def test_referral_identity_prefers_backend_issued_link_and_code(mock_settings) -> None:
    settings = _clone_settings(mock_settings, bot_username="CyberVPNBot")

    link, code = _referral_identity(
        stats={"referral_link": "https://t.me/CyberVPNBot?start=CANON", "referral_code": "CANON"},
        user_id=123456,
        settings=settings,
    )

    assert link == "https://t.me/CyberVPNBot?start=CANON"
    assert code == "CANON"


def test_referral_identity_uses_backend_code_before_legacy_ref_user_id(mock_settings) -> None:
    settings = _clone_settings(mock_settings, bot_username="CyberVPNBot")

    link, code = _referral_identity(stats={"referral_code": "CANON"}, user_id=123456, settings=settings)

    assert link == "https://t.me/CyberVPNBot?start=CANON"
    assert code == "CANON"


@pytest.mark.asyncio
async def test_referral_share_uses_backend_issued_link(mock_settings) -> None:
    settings = _clone_settings(mock_settings, bot_username="CyberVPNBot")
    callback = MagicMock(spec=CallbackQuery)
    callback.from_user = User(id=123456, is_bot=False, first_name="Test")
    callback.message = MagicMock()
    callback.message.edit_text = AsyncMock()
    callback.answer = AsyncMock()
    api_client = MagicMock()
    api_client.get_referral_stats = AsyncMock(
        return_value={"referral_link": "https://t.me/CyberVPNBot?start=CANON", "referral_code": "CANON"}
    )

    await share_referral_link_handler(callback, _I18nStub(), api_client, settings)

    callback.message.edit_text.assert_awaited_once()
    keyboard = callback.message.edit_text.await_args.kwargs["reply_markup"]
    share_button_url = _first_button_url(keyboard)
    assert parse_qs(urlparse(share_button_url).query) == {"url": ["https://t.me/CyberVPNBot?start=CANON"]}


@pytest.mark.asyncio
async def test_referral_share_url_encodes_backend_link_query_separators(mock_settings) -> None:
    settings = _clone_settings(mock_settings, bot_username="CyberVPNBot")
    backend_link = "https://t.me/CyberVPNBot?start=CANON&text=override%0aextra"
    callback = MagicMock(spec=CallbackQuery)
    callback.from_user = User(id=123456, is_bot=False, first_name="Test")
    callback.message = MagicMock()
    callback.message.edit_text = AsyncMock()
    callback.answer = AsyncMock()
    api_client = MagicMock()
    api_client.get_referral_stats = AsyncMock(return_value={"referral_link": backend_link, "referral_code": "CANON"})

    await share_referral_link_handler(callback, _I18nStub(), api_client, settings)

    keyboard = callback.message.edit_text.await_args.kwargs["reply_markup"]
    share_button_url = _first_button_url(keyboard)
    parsed_share_url = urlparse(share_button_url)
    query = parse_qs(parsed_share_url.query)
    assert parsed_share_url.scheme == "https"
    assert parsed_share_url.netloc == "t.me"
    assert parsed_share_url.path == "/share/url"
    assert query == {"url": [backend_link]}
    assert "text" not in query


@pytest.mark.asyncio
async def test_referral_share_url_encodes_generated_referral_code_fallback(mock_settings) -> None:
    settings = _clone_settings(mock_settings, bot_username="CyberVPNBot")
    callback = MagicMock(spec=CallbackQuery)
    callback.from_user = User(id=123456, is_bot=False, first_name="Test")
    callback.message = MagicMock()
    callback.message.edit_text = AsyncMock()
    callback.answer = AsyncMock()
    api_client = MagicMock()
    api_client.get_referral_stats = AsyncMock(return_value={"referral_code": "CANON&next=evil?line=%0a"})

    await share_referral_link_handler(callback, _I18nStub(), api_client, settings)

    keyboard = callback.message.edit_text.await_args.kwargs["reply_markup"]
    share_button_url = _first_button_url(keyboard)
    query = parse_qs(urlparse(share_button_url).query)
    assert query == {"url": ["https://t.me/CyberVPNBot?start=CANON%26next%3Devil%3Fline%3D%250a"]}


@pytest.mark.asyncio
async def test_growth_menu_handler_shows_disabled_state_when_backend_disables_growth(mock_settings) -> None:
    callback = MagicMock(spec=CallbackQuery)
    callback.message = MagicMock()
    callback.message.edit_text = AsyncMock()
    callback.answer = AsyncMock()
    api_client = MagicMock()
    api_client.get_client_capabilities = AsyncMock(
        return_value={
            "growth": {
                "invites": False,
                "referral": False,
                "promo_codes": False,
                "gift_codes": False,
                "checkout_code_discounts": False,
                "growth_hub": False,
            }
        }
    )

    await growth_menu_handler(callback, _I18nStub(), api_client, mock_settings)

    callback.message.edit_text.assert_awaited_once()
    assert callback.message.edit_text.await_args.kwargs["text"] == "growth-disabled"


@pytest.mark.asyncio
async def test_growth_code_callback_reuses_code_fsm_prompt() -> None:
    callback = MagicMock(spec=CallbackQuery)
    callback.data = "growth:code"
    callback.from_user = User(id=123456, is_bot=False, first_name="Test")
    callback.message = MagicMock(spec=Message)
    callback.message.edit_text = AsyncMock()
    callback.answer = AsyncMock()
    state = MagicMock(spec=FSMContext)
    state.set_state = AsyncMock()

    await enter_promocode_handler(callback, _I18nStub(), state)

    callback.message.edit_text.assert_awaited_once_with(text="code-enter-prompt")
    state.set_state.assert_awaited_once()
