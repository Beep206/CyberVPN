from __future__ import annotations

import logging
import re
from datetime import UTC, datetime
from typing import Literal

from fastapi import APIRouter, Request, status
from pydantic import BaseModel, ConfigDict, Field

router = APIRouter(prefix="/client-errors", tags=["client-errors"])
logger = logging.getLogger(__name__)

_SENSITIVE_PATTERNS = (
    re.compile(r"(?:vless|vmess|trojan|ss)://[^\s\"']+", re.IGNORECASE),
    re.compile(
        r"(?:tgWebAppData|initData|init_data|telegram_init_data|telegramInitData|access_token|refresh_token|customer_access_token)=\S+",
        re.IGNORECASE,
    ),
    re.compile(r"\bquery_id=[^&\s]+&user=[^&\s]+&auth_date=\d+&hash=[A-Za-z0-9_-]+", re.IGNORECASE),
    re.compile(r"\b[A-Za-z0-9_-]{24,}\.[A-Za-z0-9_-]{24,}\.[A-Za-z0-9_-]{16,}\b"),
)

MiniAppClientErrorEventType = Literal[
    "miniapp_webview_js_error",
    "miniapp_window_error",
    "miniapp_unhandled_rejection",
    "miniapp_auth_failed",
    "miniapp_route_error_boundary",
]


class MiniAppClientErrorRequest(BaseModel):
    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    surface: Literal["miniapp"] = "miniapp"
    route: str = Field("/", max_length=256)
    telegram_platform: str | None = Field(None, max_length=40)
    telegram_version: str | None = Field(None, max_length=40)
    webapp_version: str | None = Field(None, max_length=40)
    error_name: str = Field("Error", max_length=80)
    error_message: str = Field("", max_length=500)
    event_type: MiniAppClientErrorEventType = "miniapp_webview_js_error"
    chunk: str | None = Field(None, max_length=160)
    release: str | None = Field(None, max_length=120)
    git_sha: str | None = Field(None, max_length=80)


class MiniAppClientErrorAck(BaseModel):
    status: Literal["accepted"]
    received_at: datetime


def _sanitize(value: str | None, *, fallback: str = "", max_length: int = 500) -> str:
    text = (value or fallback).strip()[:max_length]
    for pattern in _SENSITIVE_PATTERNS:
        text = pattern.sub("[filtered]", text)
    return text


@router.post("/miniapp", response_model=MiniAppClientErrorAck, status_code=status.HTTP_202_ACCEPTED)
async def ingest_miniapp_client_error(
    payload: MiniAppClientErrorRequest,
    request: Request,
) -> MiniAppClientErrorAck:
    event = {
        "surface": "miniapp",
        "route": _sanitize(payload.route, fallback="/", max_length=256),
        "event_type": _sanitize(payload.event_type, fallback="miniapp_webview_js_error", max_length=80),
        "telegram_platform": _sanitize(payload.telegram_platform, fallback="unknown", max_length=40),
        "telegram_version": _sanitize(payload.telegram_version, fallback="unknown", max_length=40),
        "webapp_version": _sanitize(payload.webapp_version, fallback="unknown", max_length=40),
        "error_name": _sanitize(payload.error_name, fallback="Error", max_length=80),
        "error_message": _sanitize(payload.error_message, max_length=500),
        "chunk": _sanitize(payload.chunk, fallback="none", max_length=160),
        "release": _sanitize(payload.release, fallback="unknown", max_length=120),
        "git_sha": _sanitize(payload.git_sha, fallback="unknown", max_length=80),
        "user_agent_present": bool(request.headers.get("user-agent")),
    }
    logger.info("miniapp_client_error_ingested", extra=event)
    return MiniAppClientErrorAck(status="accepted", received_at=datetime.now(UTC))
