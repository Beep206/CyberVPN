"""CyberVPN Telegram Bot — Support handler.

Displays support contact information and creates first-line S1 support escalations.
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from urllib.parse import urlsplit, urlunsplit

import structlog
from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo

from src.services.api_client import APIError
from src.services.support_triage import Stage1SupportTriageService

router = Router(name="support")
logger = structlog.get_logger(__name__)

if TYPE_CHECKING:
    from collections.abc import Callable

    from aiogram.filters.command import CommandObject
    from aiogram.types import CallbackQuery, Message

    from src.config import BotSettings
    from src.services.api_client import CyberVPNAPIClient


def _normalize_support_contact(raw_contact: str) -> str:
    """Format configured support username as Telegram handle."""
    return raw_contact if raw_contact.startswith("@") else f"@{raw_contact}"


def _render_support_message(
    i18n: Callable[..., str],
    settings: BotSettings,
) -> str:
    """Build localized support message shared by menu and command entrypoints."""
    return i18n("support-message", contact=_normalize_support_contact(settings.support_username))


def _support_miniapp_url(settings: BotSettings) -> str | None:
    raw_url = getattr(settings, "miniapp_url", None)
    if raw_url is None:
        return None

    parsed = urlsplit(str(raw_url))
    path = parsed.path.rstrip("/")
    if path.endswith("/miniapp/support"):
        support_path = path
    elif path.endswith("/miniapp"):
        support_path = f"{path}/support"
    else:
        support_path = f"{path}/miniapp/support"

    return urlunsplit((parsed.scheme, parsed.netloc, support_path, "", ""))


def _support_miniapp_keyboard(
    i18n: Callable[..., str],
    settings: BotSettings,
) -> InlineKeyboardMarkup | None:
    support_url = _support_miniapp_url(settings)
    if support_url is None:
        return None
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=i18n("btn-support"),
                    web_app=WebAppInfo(url=support_url),
                )
            ]
        ]
    )


async def _answer_support_message(
    message: Message,
    i18n: Callable[..., str],
    settings: BotSettings,
) -> None:
    reply_markup = _support_miniapp_keyboard(i18n, settings)
    text = _render_support_message(i18n, settings)
    if reply_markup is None:
        await message.answer(text)
        return
    await message.answer(text, reply_markup=reply_markup)


def _extract_support_request(message: Message, command: CommandObject | None = None) -> str:
    if command is not None and command.args:
        return command.args.strip()

    text = (message.text or "").strip()
    if not text.startswith("/"):
        return text

    parts = text.split(maxsplit=1)
    if len(parts) == 2:
        return parts[1].strip()
    return ""


def _render_triage_reply(
    i18n: Callable[..., str],
    *,
    first_line_key: str,
    contact: str,
    reference: str,
    escalation_created: bool,
    escalate: bool,
) -> str:
    first_line = i18n(first_line_key, contact=contact, reference=reference)
    if not escalate:
        return i18n(
            "support-first-line-without-escalation",
            first_line=first_line,
            contact=contact,
            reference=reference,
        )

    status_key = "support-escalation-created" if escalation_created else "support-escalation-fallback"
    status_line = i18n(status_key, contact=contact, reference=reference)
    return f"{first_line}\n\n{status_line}"


async def _create_support_escalation(
    *,
    api_client: CyberVPNAPIClient | None,
    telegram_id: int,
    payload: dict[str, object],
    reference: str,
) -> bool:
    if api_client is None or not hasattr(api_client, "create_support_escalation"):
        logger.warning("support_escalation_api_unavailable", reference=reference)
        return False

    try:
        await api_client.create_support_escalation(telegram_id, payload)
    except APIError as exc:
        logger.warning(
            "support_escalation_failed",
            reference=reference,
            status_code=exc.status_code,
            error_type=type(exc).__name__,
        )
        return False
    except Exception as exc:
        logger.exception("support_escalation_unexpected_error", reference=reference, error_type=type(exc).__name__)
        return False
    return True


@router.message(Command("support", "paysupport"))
async def support_command(
    message: Message,
    i18n: Callable[..., str],
    settings: BotSettings,
    api_client: CyberVPNAPIClient | None = None,
    command: CommandObject | None = None,
) -> None:
    """Provide support contact or triage a support request from command args."""
    support_request = _extract_support_request(message, command)
    if not support_request:
        await _answer_support_message(message, i18n, settings)
        return

    telegram_user = message.from_user
    if telegram_user is None:
        await _answer_support_message(message, i18n, settings)
        return

    contact = _normalize_support_contact(settings.support_username)
    triage = Stage1SupportTriageService().triage(text=support_request, telegram_id=telegram_user.id)
    escalation_created = False
    if triage.escalate:
        escalation_created = await _create_support_escalation(
            api_client=api_client,
            telegram_id=telegram_user.id,
            payload=triage.to_escalation_payload(telegram_username=telegram_user.username),
            reference=triage.support_reference,
        )

    await message.answer(
        _render_triage_reply(
            i18n,
            first_line_key=triage.first_line_reply_key,
            contact=contact,
            reference=triage.support_reference,
            escalation_created=escalation_created,
            escalate=triage.escalate,
        )
    )


@router.callback_query(F.data == "menu:support")
async def support_menu(
    callback: CallbackQuery,
    i18n: Callable[..., str],
    settings: BotSettings,
) -> None:
    """Show support contact information.

    Args:
        callback: Callback query from support menu button.
        i18n: Translator function.
        settings: Bot settings with support username.
    """
    await callback.answer()
    reply_markup = _support_miniapp_keyboard(i18n, settings)
    text = _render_support_message(i18n, settings)
    if reply_markup is None:
        await callback.message.edit_text(text)
        return
    await callback.message.edit_text(text, reply_markup=reply_markup)
