"""Telegram bot registration response helpers."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from src.services.api_client import APIError

REGISTRATION_DISABLED_CODE = "TELEGRAM_BOT_REGISTRATION_DISABLED"
REGISTRATION_REQUIRES_INVITE_CODE = "TELEGRAM_BOT_REGISTRATION_REQUIRES_INVITE"
EXPECTED_REGISTRATION_CODES = {
    REGISTRATION_DISABLED_CODE,
    REGISTRATION_REQUIRES_INVITE_CODE,
}


def api_error_detail(exc: APIError) -> dict[str, Any]:
    detail = exc.detail
    if isinstance(detail, dict):
        return detail
    if isinstance(detail, str):
        try:
            parsed = json.loads(detail)
        except json.JSONDecodeError:
            return {}
        return parsed if isinstance(parsed, dict) else {}
    return {}


def api_error_code(exc: APIError) -> str | None:
    detail = api_error_detail(exc)
    code = detail.get("code")
    return code if isinstance(code, str) else None


def is_expected_registration_error(exc: APIError) -> bool:
    return api_error_code(exc) in EXPECTED_REGISTRATION_CODES


def message_key_for_registration_error(exc: APIError) -> str:
    detail = api_error_detail(exc)
    message_key = detail.get("message_key")
    if isinstance(message_key, str):
        return _fluent_key(message_key)
    if api_error_code(exc) == REGISTRATION_DISABLED_CODE:
        return "telegram-registration-disabled"
    return "telegram-registration-requires-invite"


def miniapp_url_from_registration_response(user: dict[str, Any] | None) -> str | None:
    if not isinstance(user, dict):
        return None
    miniapp_url = user.get("miniapp_url")
    return miniapp_url.strip() if isinstance(miniapp_url, str) and miniapp_url.strip() else None


def miniapp_url_from_registration_error(exc: APIError) -> str | None:
    detail = api_error_detail(exc)
    miniapp_url = detail.get("miniapp_url")
    return miniapp_url.strip() if isinstance(miniapp_url, str) and miniapp_url.strip() else None


def requires_onboarding(user: dict[str, Any] | None) -> bool:
    return bool(isinstance(user, dict) and user.get("requires_onboarding") is True)


def _fluent_key(value: str) -> str:
    normalized = value.strip().replace(".", "-").replace("_", "-")
    if normalized == "telegram-registration-requiresInvite":
        return "telegram-registration-requires-invite"
    return normalized
