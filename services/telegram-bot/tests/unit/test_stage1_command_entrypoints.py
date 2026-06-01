from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from aiogram.filters import CommandObject
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, User

from src.handlers.config import send_config_link_handler
from src.handlers.menu import connect_command_handler, invite_codes_command_handler, main_menu_command_handler
from src.handlers.start import start_handler
from src.handlers.subscription import plans_command_handler
from src.handlers.support import support_command
from src.handlers.trial import activate_trial_command_handler


class _I18nStub:
    def __call__(self, key: str, **kwargs: object) -> str:
        return self.get(key, **kwargs)

    def get(self, key: str, **kwargs: object) -> str:
        if kwargs:
            suffix = " ".join(f"{name}={value}" for name, value in sorted(kwargs.items()))
            return f"{key} {suffix}"
        return key


def _message() -> Message:
    message = MagicMock(spec=Message)
    message.from_user = User(id=123456, is_bot=False, first_name="Test")
    message.text = "/start"
    message.answer = AsyncMock()
    return message


def _callback_data(reply_markup: object) -> set[str]:
    keyboard = getattr(reply_markup, "inline_keyboard", [])
    return {
        button.callback_data
        for row in keyboard
        for button in row
        if getattr(button, "callback_data", None)
    }


@pytest.mark.asyncio
async def test_start_command_registers_user_and_shows_s1_onboarding_menu() -> None:
    message = _message()
    api_client = SimpleNamespace(
        register_user=AsyncMock(
            return_value={
                "telegram_id": 123456,
                "username": "test",
                "status": "none",
                "is_admin": False,
            }
        ),
        update_user=AsyncMock(),
    )
    state = MagicMock(spec=FSMContext)

    await start_handler(
        message,
        CommandObject(prefix="/", command="start", mention=None, args=None),
        _I18nStub(),
        api_client,
        state,
    )

    api_client.register_user.assert_awaited_once()
    api_client.update_user.assert_not_awaited()
    message.answer.assert_awaited_once()
    assert message.answer.await_args.kwargs["text"].startswith("welcome-message")
    callbacks = _callback_data(message.answer.await_args.kwargs["reply_markup"])
    assert {"trial:activate", "menu:vpn", "menu:subscription", "menu:growth", "menu:support"}.issubset(callbacks)


@pytest.mark.asyncio
async def test_menu_command_opens_main_menu_without_registered_user() -> None:
    message = _message()
    api_client = SimpleNamespace(get_user=AsyncMock(side_effect=RuntimeError("backend unavailable")))

    await main_menu_command_handler(message, _I18nStub(), api_client)

    message.answer.assert_awaited_once()
    assert message.answer.await_args.kwargs["text"] == "menu-main-title"
    assert message.answer.await_args.kwargs["reply_markup"] is not None


@pytest.mark.asyncio
async def test_connect_command_opens_subscription_surface_for_inactive_user() -> None:
    message = _message()
    api_client = SimpleNamespace(
        get_current_entitlements=AsyncMock(return_value={"status": "none"}),
        get_current_service_state=AsyncMock(),
    )

    await connect_command_handler(message, _I18nStub(), api_client)

    api_client.get_current_entitlements.assert_awaited_once_with(123456)
    api_client.get_current_service_state.assert_not_awaited()
    message.answer.assert_awaited_once()
    assert message.answer.await_args.kwargs["text"] == "subscription-none"
    assert message.answer.await_args.kwargs["reply_markup"] is not None


@pytest.mark.asyncio
async def test_plans_command_opens_public_telegram_catalog() -> None:
    message = _message()
    api_client = SimpleNamespace(
        get_plans=AsyncMock(
            return_value=[
                {
                    "uuid": "plan-basic-30",
                    "plan_code": "basic",
                    "display_name": "Basic",
                    "duration_days": 30,
                    "price_usd": 3,
                    "catalog_visibility": "public",
                    "sale_channels": ["telegram_bot"],
                    "is_active": True,
                }
            ]
        )
    )
    state = MagicMock(spec=FSMContext)
    state.clear = AsyncMock()
    state.update_data = AsyncMock()
    state.set_state = AsyncMock()

    await plans_command_handler(message, _I18nStub(), api_client, state)

    api_client.get_plans.assert_awaited_once()
    state.clear.assert_awaited_once()
    state.update_data.assert_awaited_once()
    state.set_state.assert_awaited_once()
    message.answer.assert_awaited_once()
    assert message.answer.await_args.kwargs["text"] == "subscription-select-plan"
    assert message.answer.await_args.kwargs["reply_markup"] is not None


@pytest.mark.asyncio
async def test_trial_command_activates_trial_and_prompts_for_config() -> None:
    message = _message()
    api_client = SimpleNamespace(
        check_trial_eligibility=AsyncMock(return_value={"eligible": True}),
        activate_trial=AsyncMock(return_value={"id": "trial-1", "duration_days": 3, "expires_at": "2026-05-07"}),
    )

    await activate_trial_command_handler(message, _I18nStub(), api_client)

    api_client.check_trial_eligibility.assert_awaited_once_with(123456)
    api_client.activate_trial.assert_awaited_once_with(123456)
    assert message.answer.await_count == 2
    assert "trial-activated" in message.answer.await_args_list[0].kwargs["text"]
    assert message.answer.await_args_list[1].kwargs["text"] == "config-delivery-prompt"
    assert message.answer.await_args_list[1].kwargs["reply_markup"] is not None


@pytest.mark.asyncio
async def test_invites_command_shows_owned_invite_codes() -> None:
    message = _message()
    api_client = SimpleNamespace(
        get_invite_codes=AsyncMock(
            return_value=[
                {
                    "id": "invite-1",
                    "code": "OWNER123",
                    "free_days": 7,
                    "is_used": False,
                    "expires_at": "2026-05-24T11:54:13Z",
                    "created_at": "2026-05-21T11:54:13Z",
                }
            ]
        )
    )

    await invite_codes_command_handler(message, _I18nStub(), api_client)

    api_client.get_invite_codes.assert_awaited_once_with(123456)
    message.answer.assert_awaited_once()
    assert "my-invites-info" in message.answer.await_args.kwargs["text"]
    assert "OWNER123" in message.answer.await_args.kwargs["text"]
    assert message.answer.await_args.kwargs["reply_markup"] is not None


@pytest.mark.asyncio
async def test_config_link_handler_sends_subscription_url_not_direct_proxy_uri() -> None:
    from aiogram.types import CallbackQuery

    callback = MagicMock(spec=CallbackQuery)
    callback.from_user = User(id=123456, is_bot=False, first_name="Test")
    callback.message = MagicMock()
    callback.message.answer = AsyncMock()
    callback.answer = AsyncMock()
    api_client = SimpleNamespace(
        get_user_subscriptions=AsyncMock(return_value=[]),
        get_user_config=AsyncMock(
            return_value={
                "config_string": "vless://direct-proxy-uri",
                "client_type": "vless",
                "subscription_url": "https://cyber-vpn.org/api/sub/redacted",
            }
        )
    )

    await send_config_link_handler(callback, _I18nStub(), api_client)

    callback.message.answer.assert_awaited_once()
    text = callback.message.answer.await_args.kwargs["text"]
    assert "https://cyber-vpn.org/api/sub/redacted" in text
    assert "vless://direct-proxy-uri" not in text


@pytest.mark.asyncio
async def test_config_link_handler_rejects_direct_proxy_uri_without_subscription_url() -> None:
    from aiogram.types import CallbackQuery

    callback = MagicMock(spec=CallbackQuery)
    callback.from_user = User(id=123456, is_bot=False, first_name="Test")
    callback.message = MagicMock()
    callback.message.answer = AsyncMock()
    callback.answer = AsyncMock()
    api_client = SimpleNamespace(
        get_user_subscriptions=AsyncMock(return_value=[]),
        get_user_config=AsyncMock(
            return_value={
                "config_string": "vless://direct-proxy-uri",
                "client_type": "vless",
            }
        )
    )

    await send_config_link_handler(callback, _I18nStub(), api_client)

    callback.message.answer.assert_not_awaited()
    callback.answer.assert_any_await("error-config-not-ready", show_alert=True)


@pytest.mark.asyncio
@pytest.mark.parametrize("command_text", ["/support", "/paysupport"])
async def test_support_commands_return_configured_support_contact(command_text: str) -> None:
    message = _message()
    message.text = command_text
    settings = SimpleNamespace(support_username="CyberVPNSupport")

    await support_command(message, _I18nStub(), settings)

    message.answer.assert_awaited_once_with("support-message contact=@CyberVPNSupport")
