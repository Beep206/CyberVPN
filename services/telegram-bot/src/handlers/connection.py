"""Telegram growth connection UX handlers."""

from __future__ import annotations

import hashlib
from html import escape
from typing import TYPE_CHECKING, cast

import structlog
from aiogram import F, Router
from aiogram.filters import Command, CommandObject
from aiogram.types import BufferedInputFile, CallbackQuery, Message
from prometheus_client import Counter

from src.keyboards.connection import (
    connection_help_keyboard,
    connection_instruction_keyboard,
    connection_keyboard,
    connection_private_chat_keyboard,
)
from src.services.api_client import APIError
from src.services.connection_session import ConnectionSessionStore
from src.services.qr_service import generate_subscription_qr

if TYPE_CHECKING:
    from aiogram_i18n import I18nContext

    from src.config import BotSettings
    from src.models.connection import ConnectionBootstrapResponse, ConnectionPlatform, ConnectionSession
    from src.services.api_client import CyberVPNAPIClient
    from src.services.cache_service import CacheService

logger = structlog.get_logger(__name__)

router = Router(name="connection")

CONNECTION_FLOW_TOTAL = Counter(
    "telegram_bot_connection_flow_total",
    "Telegram bot connection flow events.",
    ("status", "action"),
)
CONNECTION_PRIVATE_CHAT_REQUIRED_TOTAL = Counter(
    "telegram_bot_connection_private_chat_required_total",
    "Telegram bot connection flow attempts blocked outside private chat.",
)

_SUPPORTED_PLATFORMS: set[str] = {"ios", "android", "windows", "macos", "linux", "unknown"}


def _i18n_get(i18n: I18nContext, key: str, **kwargs: object) -> str:
    return cast("str", i18n.get(key, **kwargs))


def _callback_message(callback: CallbackQuery) -> Message | None:
    message = callback.message
    if message is None or not hasattr(message, "answer"):
        return None
    return cast("Message", message)


def _is_private_chat(target: Message | CallbackQuery) -> bool:
    message = _callback_message(target) if isinstance(target, CallbackQuery) else target
    if message is None:
        return False
    chat = getattr(message, "chat", None)
    chat_type = getattr(chat, "type", None)
    if chat_type is None or not isinstance(chat_type, str):
        return False
    return bool(chat_type == "private")


def _safe_error_context(exc: Exception) -> dict[str, object]:
    context: dict[str, object] = {"error_type": type(exc).__name__}
    if isinstance(exc, APIError):
        context["status_code"] = exc.status_code
    return context


def code_fingerprint(code: str) -> str:
    return hashlib.sha256(code.encode("utf-8")).hexdigest()[:12]


def telegram_user_fingerprint(telegram_id: int) -> str:
    return hashlib.sha256(f"telegram_user:{telegram_id}".encode()).hexdigest()[:16]


def mask_code(code: str) -> str:
    normalized = code.strip()
    if len(normalized) <= 4:
        return "****"
    return f"{normalized[:2]}***{normalized[-2:]}"


def _as_dict(value: object) -> dict[str, object]:
    return dict(value) if isinstance(value, dict) else {}


def _safe_int(value: object) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, str) and value.isdigit():
        return int(value)
    return None


def _render_apply_notice(i18n: I18nContext, apply_result: dict[str, object], *, code: str) -> str:
    lines = [_i18n_get(i18n, "bot-onboarding-code-applied", code=mask_code(code))]
    child_invites = _as_dict(apply_result.get("child_invites"))
    generated_count = _safe_int(child_invites.get("generated_count"))
    available_count = _safe_int(child_invites.get("available_count"))
    if generated_count is not None and generated_count > 0:
        lines.append(
            _i18n_get(
                i18n,
                "bot-onboarding-code-child-invites",
                count=generated_count,
                available=available_count if available_count is not None else generated_count,
            )
        )
    return "\n".join(lines)


def onboarding_code_idempotency_key(
    *,
    telegram_id: int,
    code: str,
    message_id: int | None = None,
    session_id: str | None = None,
) -> str:
    attempt_ref = str(message_id or session_id or "manual")
    digest = hashlib.sha256(code.strip().encode()).hexdigest()[:16]
    return f"tg-code:{telegram_id}:{attempt_ref}:{digest}"


def _code_apply_error_message_key(exc: Exception) -> str:
    if isinstance(exc, APIError):
        detail: object = exc.detail
        detail_code = detail.get("code") if isinstance(detail, dict) else None
        if exc.status_code in {401, 403} or detail_code in {
            "CUSTOMER_ONBOARDING_STATE_UNAVAILABLE",
            "CUSTOMER_ONBOARDING_TELEGRAM_CODE_APPLY_UNAVAILABLE",
        }:
            return "bot-onboarding-code-apply-unavailable"
    return "code-not-found"


def _parse_platform(raw: str) -> ConnectionPlatform:
    if raw in _SUPPORTED_PLATFORMS:
        return cast("ConnectionPlatform", raw)
    return "unknown"


def _extract_callback_parts(callback_data: str | None, prefix: str, expected_parts: int) -> list[str] | None:
    if not callback_data or not callback_data.startswith(prefix):
        return None
    parts = callback_data.split(":")
    if len(parts) != expected_parts:
        return None
    return parts


async def _send_private_chat_required(
    target: Message | CallbackQuery,
    i18n: I18nContext,
    settings: BotSettings | None,
) -> None:
    CONNECTION_PRIVATE_CHAT_REQUIRED_TOTAL.inc()
    CONNECTION_FLOW_TOTAL.labels(status="blocked", action="private_chat_required").inc()
    text = _i18n_get(i18n, "bot-onboarding-connection-private-chat-required")
    reply_markup = connection_private_chat_keyboard(i18n.get, settings)
    if isinstance(target, CallbackQuery):
        await target.answer(text, show_alert=True)
        message = _callback_message(target)
        if message is not None:
            await message.answer(text=text, reply_markup=reply_markup)
        return

    await target.answer(text=text, reply_markup=reply_markup)


async def _private_gate(
    target: Message | CallbackQuery,
    i18n: I18nContext,
    settings: BotSettings | None,
) -> bool:
    if _is_private_chat(target):
        return True
    await _send_private_chat_required(target, i18n, settings)
    return False


async def _create_connection_session(
    cache: CacheService,
    *,
    telegram_id: int,
    bootstrap: ConnectionBootstrapResponse,
    platform_hint: ConnectionPlatform = "unknown",
) -> ConnectionSession:
    backend_hint = bootstrap.telegram_payload.preferred_platform if bootstrap.telegram_payload else "unknown"
    selected_platform = platform_hint if platform_hint != "unknown" else backend_hint
    backend_connection_session_id = (
        bootstrap.telegram_payload.bot_connection_session_id
        if bootstrap.telegram_payload and bootstrap.telegram_payload.bot_connection_session_id
        else bootstrap.connection_session_id
    )
    store = ConnectionSessionStore(cache)
    return await store.create(
        telegram_id=telegram_id,
        platform_hint=selected_platform,
        flow_key=bootstrap.flow_key,
        version=bootstrap.version,
        backend_connection_session_id=backend_connection_session_id,
    )


async def _load_owned_session(
    cache: CacheService,
    *,
    session_id: str,
    telegram_id: int,
) -> ConnectionSession | None:
    session = await ConnectionSessionStore(cache).get(session_id)
    if session is None or session.telegram_id != telegram_id:
        return None
    return session


async def _bootstrap_connection(
    api_client: CyberVPNAPIClient,
    *,
    telegram_id: int,
    platform_hint: ConnectionPlatform = "unknown",
) -> ConnectionBootstrapResponse:
    return await api_client.get_customer_connection_bootstrap(
        telegram_id,
        platform_hint=platform_hint,
    )


def _render_bootstrap_text(i18n: I18nContext, bootstrap: ConnectionBootstrapResponse) -> str:
    if bootstrap.available and bootstrap.has_private_payload:
        profile = bootstrap.config_profile_name or _i18n_get(i18n, "bot-onboarding-connection-profile-default")
        return _i18n_get(i18n, "bot-onboarding-connection-ready", profile=escape(profile))

    status_key = {
        "no_active_entitlement": "bot-onboarding-connection-no-active-entitlement",
        "service_identity_pending": "bot-onboarding-connection-pending-config",
        "config_unavailable": "bot-onboarding-connection-config-unavailable",
        "disabled": "bot-onboarding-connection-disabled",
        "available": "bot-onboarding-connection-config-unavailable",
    }.get(bootstrap.status, "bot-onboarding-connection-config-unavailable")
    return _i18n_get(i18n, status_key)


async def _send_bootstrap_message(
    message: Message,
    i18n: I18nContext,
    api_client: CyberVPNAPIClient,
    cache: CacheService,
    *,
    platform_hint: ConnectionPlatform = "unknown",
) -> None:
    if message.from_user is None:
        return

    try:
        bootstrap = await _bootstrap_connection(
            api_client,
            telegram_id=message.from_user.id,
            platform_hint=platform_hint,
        )
    except Exception as exc:
        logger.warning(
            "telegram_connection_bootstrap_failed",
            telegram_user_fingerprint=telegram_user_fingerprint(message.from_user.id),
            action="message",
            **_safe_error_context(exc),
        )
        CONNECTION_FLOW_TOTAL.labels(status="error", action="bootstrap").inc()
        await message.answer(_i18n_get(i18n, "error-generic"))
        return

    if not bootstrap.available or not bootstrap.has_private_payload:
        CONNECTION_FLOW_TOTAL.labels(status=bootstrap.status, action="bootstrap").inc()
        await message.answer(_render_bootstrap_text(i18n, bootstrap))
        return

    session = await _create_connection_session(
        cache,
        telegram_id=message.from_user.id,
        bootstrap=bootstrap,
        platform_hint=platform_hint,
    )
    CONNECTION_FLOW_TOTAL.labels(status="success", action="bootstrap").inc()
    await message.answer(
        text=_render_bootstrap_text(i18n, bootstrap),
        reply_markup=connection_keyboard(i18n.get, session_id=session.session_id),
    )


async def _edit_or_send_bootstrap_message(
    callback: CallbackQuery,
    i18n: I18nContext,
    api_client: CyberVPNAPIClient,
    cache: CacheService,
    *,
    session: ConnectionSession | None = None,
) -> None:
    if session is None:
        bootstrap = await _bootstrap_connection(api_client, telegram_id=callback.from_user.id)
        if not bootstrap.available or not bootstrap.has_private_payload:
            CONNECTION_FLOW_TOTAL.labels(status=bootstrap.status, action="bootstrap").inc()
            message = _callback_message(callback)
            if message is None:
                await callback.answer(_i18n_get(i18n, "error-generic"), show_alert=True)
                return
            await message.edit_text(text=_render_bootstrap_text(i18n, bootstrap))
            return
        session = await _create_connection_session(
            cache,
            telegram_id=callback.from_user.id,
            bootstrap=bootstrap,
        )
    else:
        bootstrap = await _bootstrap_connection(
            api_client,
            telegram_id=callback.from_user.id,
            platform_hint=session.platform_hint,
        )

    CONNECTION_FLOW_TOTAL.labels(status="success", action="bootstrap").inc()
    message = _callback_message(callback)
    if message is None:
        await callback.answer(_i18n_get(i18n, "error-generic"), show_alert=True)
        return
    await message.edit_text(
        text=_render_bootstrap_text(i18n, bootstrap),
        reply_markup=connection_keyboard(i18n.get, session_id=session.session_id),
    )


async def open_connection_from_message(
    message: Message,
    i18n: I18nContext,
    api_client: CyberVPNAPIClient,
    cache: CacheService,
    settings: BotSettings | None = None,
    *,
    platform_hint: ConnectionPlatform = "unknown",
) -> None:
    """Open the shared Telegram connection UX from any message handler."""
    if not await _private_gate(message, i18n, settings):
        return
    await _send_bootstrap_message(message, i18n, api_client, cache, platform_hint=platform_hint)


async def open_connection_from_callback(
    callback: CallbackQuery,
    i18n: I18nContext,
    api_client: CyberVPNAPIClient,
    cache: CacheService,
    settings: BotSettings | None = None,
) -> None:
    """Open the shared Telegram connection UX from menu callbacks."""
    if not await _private_gate(callback, i18n, settings):
        return
    try:
        await _edit_or_send_bootstrap_message(callback, i18n, api_client, cache)
    except Exception as exc:
        logger.warning(
            "telegram_connection_bootstrap_failed",
            telegram_user_fingerprint=telegram_user_fingerprint(callback.from_user.id),
            action="callback",
            **_safe_error_context(exc),
        )
        CONNECTION_FLOW_TOTAL.labels(status="error", action="bootstrap").inc()
        await callback.answer(_i18n_get(i18n, "error-generic"), show_alert=True)
        return
    await callback.answer()


async def apply_code_and_open_connection(
    message: Message,
    i18n: I18nContext,
    api_client: CyberVPNAPIClient,
    cache: CacheService,
    settings: BotSettings | None,
    *,
    code: str,
) -> None:
    """Apply a private-chat onboarding code, then render connection state."""
    if message.from_user is None:
        return
    if not await _private_gate(message, i18n, settings):
        return

    normalized_code = code.strip()
    if not normalized_code:
        await message.answer(_i18n_get(i18n, "code-enter-prompt"))
        return

    try:
        apply_result = await api_client.apply_telegram_onboarding_code(
            message.from_user.id,
            normalized_code,
            idempotency_key=onboarding_code_idempotency_key(
                telegram_id=message.from_user.id,
                code=normalized_code,
                message_id=message.message_id,
            ),
        )
    except Exception as exc:
        logger.warning(
            "telegram_onboarding_code_apply_failed",
            telegram_user_fingerprint=telegram_user_fingerprint(message.from_user.id),
            code_fingerprint=code_fingerprint(normalized_code),
            **_safe_error_context(exc),
        )
        CONNECTION_FLOW_TOTAL.labels(status="error", action="apply_code").inc()
        await message.answer(_i18n_get(i18n, _code_apply_error_message_key(exc)))
        return

    CONNECTION_FLOW_TOTAL.labels(status="success", action="apply_code").inc()
    await message.answer(_render_apply_notice(i18n, apply_result, code=normalized_code))
    await _send_bootstrap_message(message, i18n, api_client, cache)


async def _send_connection_link(
    message: Message,
    i18n: I18nContext,
    bootstrap: ConnectionBootstrapResponse,
    session: ConnectionSession,
) -> None:
    url = bootstrap.subscription_url
    if not url:
        await message.answer(_i18n_get(i18n, "error-config-not-ready"))
        return

    await message.answer(
        text=_i18n_get(i18n, "bot-onboarding-connection-link-message", url=escape(url)),
        reply_markup=connection_instruction_keyboard(
            i18n.get,
            session_id=session.session_id,
            platform=session.platform_hint,
        ),
    )


def _instruction_text(i18n: I18nContext, platform: ConnectionPlatform) -> str:
    if platform not in {"ios", "android", "windows", "macos", "linux"}:
        return _i18n_get(i18n, "bot-onboarding-connection-instructions-generic")
    return _i18n_get(i18n, f"bot-onboarding-connection-instructions-{platform}")


@router.message(Command("connect"))
async def connect_command_handler(
    message: Message,
    i18n: I18nContext,
    api_client: CyberVPNAPIClient,
    cache: CacheService,
    settings: BotSettings | None = None,
) -> None:
    await open_connection_from_message(message, i18n, api_client, cache, settings)


@router.message(Command("instructions"))
async def instructions_command_handler(
    message: Message,
    i18n: I18nContext,
    api_client: CyberVPNAPIClient,
    cache: CacheService,
    settings: BotSettings | None = None,
) -> None:
    await open_connection_from_message(message, i18n, api_client, cache, settings)


@router.message(Command("help"))
async def help_command_handler(message: Message, i18n: I18nContext) -> None:
    await message.answer(
        text=_i18n_get(i18n, "bot-onboarding-connection-help"),
        reply_markup=connection_help_keyboard(i18n.get),
    )


@router.message(Command("code"))
async def code_command_handler(
    message: Message,
    command: CommandObject,
    i18n: I18nContext,
    api_client: CyberVPNAPIClient,
    cache: CacheService,
    settings: BotSettings | None = None,
) -> None:
    await apply_code_and_open_connection(
        message,
        i18n,
        api_client,
        cache,
        settings,
        code=(command.args or "").strip(),
    )


@router.callback_query(F.data == "connection:instructions")
async def instructions_entry_callback_handler(
    callback: CallbackQuery,
    i18n: I18nContext,
    api_client: CyberVPNAPIClient,
    cache: CacheService,
    settings: BotSettings | None = None,
) -> None:
    await open_connection_from_callback(callback, i18n, api_client, cache, settings)


@router.callback_query(F.data.startswith("connection:open_link:"))
async def connection_open_link_callback_handler(
    callback: CallbackQuery,
    i18n: I18nContext,
    api_client: CyberVPNAPIClient,
    cache: CacheService,
    settings: BotSettings | None = None,
) -> None:
    if not await _private_gate(callback, i18n, settings):
        return

    parts = _extract_callback_parts(callback.data, "connection:open_link:", 3)
    session_id = parts[2] if parts else ""
    session = await _load_owned_session(cache, session_id=session_id, telegram_id=callback.from_user.id)
    if session is None:
        await callback.answer(_i18n_get(i18n, "bot-onboarding-connection-session-expired"), show_alert=True)
        return

    bootstrap = await _bootstrap_connection(
        api_client,
        telegram_id=callback.from_user.id,
        platform_hint=session.platform_hint,
    )
    message = _callback_message(callback)
    if message is None:
        await callback.answer(_i18n_get(i18n, "error-generic"), show_alert=True)
        return
    await _send_connection_link(message, i18n, bootstrap, session)
    CONNECTION_FLOW_TOTAL.labels(status="success", action="open_link").inc()
    await callback.answer()


@router.callback_query(F.data.startswith("connection:show_qr:"))
async def connection_show_qr_callback_handler(
    callback: CallbackQuery,
    i18n: I18nContext,
    api_client: CyberVPNAPIClient,
    cache: CacheService,
    settings: BotSettings | None = None,
) -> None:
    if not await _private_gate(callback, i18n, settings):
        return

    parts = _extract_callback_parts(callback.data, "connection:show_qr:", 3)
    session_id = parts[2] if parts else ""
    session = await _load_owned_session(cache, session_id=session_id, telegram_id=callback.from_user.id)
    if session is None:
        await callback.answer(_i18n_get(i18n, "bot-onboarding-connection-session-expired"), show_alert=True)
        return

    bootstrap = await _bootstrap_connection(
        api_client,
        telegram_id=callback.from_user.id,
        platform_hint=session.platform_hint,
    )
    qr_payload = bootstrap.qr_payload or bootstrap.subscription_url
    if not qr_payload:
        await callback.answer(_i18n_get(i18n, "error-config-not-ready"), show_alert=True)
        return

    try:
        buffer = generate_subscription_qr(qr_payload)
        message = _callback_message(callback)
        if message is None:
            await callback.answer(_i18n_get(i18n, "error-generic"), show_alert=True)
            return
        await message.answer_photo(
            photo=BufferedInputFile(buffer.getvalue(), filename="cybervpn-connection.png"),
            caption=_i18n_get(i18n, "bot-onboarding-connection-qr-caption"),
            reply_markup=connection_instruction_keyboard(
                i18n.get,
                session_id=session.session_id,
                platform=session.platform_hint,
            ),
        )
        CONNECTION_FLOW_TOTAL.labels(status="success", action="show_qr").inc()
    except Exception as exc:
        logger.warning(
            "telegram_connection_qr_generation_failed",
            telegram_user_fingerprint=telegram_user_fingerprint(callback.from_user.id),
            action="show_qr",
            **_safe_error_context(exc),
        )
        CONNECTION_FLOW_TOTAL.labels(status="fallback", action="show_qr").inc()
        message = _callback_message(callback)
        if message is None:
            await callback.answer(_i18n_get(i18n, "error-generic"), show_alert=True)
            return
        await _send_connection_link(message, i18n, bootstrap, session)

    await callback.answer()


@router.callback_query(F.data.startswith("connection:instructions:"))
async def connection_instructions_callback_handler(
    callback: CallbackQuery,
    i18n: I18nContext,
    api_client: CyberVPNAPIClient,
    cache: CacheService,
    settings: BotSettings | None = None,
) -> None:
    if not await _private_gate(callback, i18n, settings):
        return

    parts = _extract_callback_parts(callback.data, "connection:instructions:", 4)
    platform = _parse_platform(parts[2]) if parts else "unknown"
    session_id = parts[3] if parts else ""
    session = await _load_owned_session(cache, session_id=session_id, telegram_id=callback.from_user.id)
    if session is None:
        await callback.answer(_i18n_get(i18n, "bot-onboarding-connection-session-expired"), show_alert=True)
        return

    message = _callback_message(callback)
    if message is None:
        await callback.answer(_i18n_get(i18n, "error-generic"), show_alert=True)
        return
    await message.edit_text(
        text=_instruction_text(i18n, platform),
        reply_markup=connection_instruction_keyboard(
            i18n.get,
            session_id=session.session_id,
            platform=platform,
        ),
    )
    CONNECTION_FLOW_TOTAL.labels(status="success", action="instructions").inc()
    await callback.answer()


@router.callback_query(F.data.startswith("connection:mark_connected:"))
async def connection_mark_connected_callback_handler(
    callback: CallbackQuery,
    i18n: I18nContext,
    api_client: CyberVPNAPIClient,
    cache: CacheService,
    settings: BotSettings | None = None,
) -> None:
    if not await _private_gate(callback, i18n, settings):
        return

    parts = _extract_callback_parts(callback.data, "connection:mark_connected:", 4)
    platform = _parse_platform(parts[2]) if parts else "unknown"
    session_id = parts[3] if parts else ""
    session = await _load_owned_session(cache, session_id=session_id, telegram_id=callback.from_user.id)
    if session is None:
        await callback.answer(_i18n_get(i18n, "bot-onboarding-connection-session-expired"), show_alert=True)
        return
    if session.backend_connection_session_id is None:
        CONNECTION_FLOW_TOTAL.labels(status="error", action="mark_connected").inc()
        await callback.answer(_i18n_get(i18n, "bot-onboarding-connection-session-expired"), show_alert=True)
        return

    try:
        await api_client.mark_customer_connection_connected(
            callback.from_user.id,
            platform=platform,
            source_surface="telegram_bot",
            flow_key=session.flow_key,
            version=session.version,
            connection_session_id=session.backend_connection_session_id,
        )
    except Exception as exc:
        logger.warning(
            "telegram_connection_mark_connected_failed",
            telegram_user_fingerprint=telegram_user_fingerprint(callback.from_user.id),
            action="mark_connected",
            **_safe_error_context(exc),
        )
        CONNECTION_FLOW_TOTAL.labels(status="error", action="mark_connected").inc()
        await callback.answer(_i18n_get(i18n, "error-generic"), show_alert=True)
        return

    CONNECTION_FLOW_TOTAL.labels(status="success", action="mark_connected").inc()
    message = _callback_message(callback)
    if message is None:
        await callback.answer(_i18n_get(i18n, "error-generic"), show_alert=True)
        return
    await message.edit_text(
        text=_i18n_get(i18n, "bot-onboarding-connection-mark-connected-confirmed"),
        reply_markup=connection_help_keyboard(i18n.get),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("connection:dashboard:"))
async def connection_dashboard_callback_handler(
    callback: CallbackQuery,
    i18n: I18nContext,
    settings: BotSettings | None = None,
) -> None:
    if not await _private_gate(callback, i18n, settings):
        return
    message = _callback_message(callback)
    if message is None:
        await callback.answer(_i18n_get(i18n, "error-generic"), show_alert=True)
        return
    await message.answer(_i18n_get(i18n, "bot-onboarding-connection-dashboard-message"))
    CONNECTION_FLOW_TOTAL.labels(status="success", action="dashboard").inc()
    await callback.answer()


@router.callback_query(F.data.startswith("connection:back:"))
async def connection_back_callback_handler(
    callback: CallbackQuery,
    i18n: I18nContext,
    api_client: CyberVPNAPIClient,
    cache: CacheService,
    settings: BotSettings | None = None,
) -> None:
    if not await _private_gate(callback, i18n, settings):
        return

    parts = _extract_callback_parts(callback.data, "connection:back:", 3)
    session_id = parts[2] if parts else ""
    session = await _load_owned_session(cache, session_id=session_id, telegram_id=callback.from_user.id)
    if session is None:
        await callback.answer(_i18n_get(i18n, "bot-onboarding-connection-session-expired"), show_alert=True)
        return

    await _edit_or_send_bootstrap_message(callback, i18n, api_client, cache, session=session)
    await callback.answer()
