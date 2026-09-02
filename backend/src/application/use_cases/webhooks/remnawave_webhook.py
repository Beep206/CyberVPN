import math
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.use_cases.webhooks.webhook_log_redaction import (
    build_invalid_body_webhook_log_payload,
    build_remnawave_webhook_log_payload,
    remnawave_event_type,
    signature_fingerprint,
    webhook_log_fingerprint,
)
from src.config.settings import settings
from src.infrastructure.database.models.webhook_log_model import WebhookLog
from src.infrastructure.messaging.websocket_manager import ws_manager
from src.infrastructure.remnawave.webhook_validator import RemnawaveWebhookValidator

_REMNAWAVE_WEBSOCKET_DATA_ALLOWLIST = frozenset(
    {
        "uuid",
        "shortUuid",
        "status",
        "isDisabled",
        "usedTrafficBytes",
        "trafficLimitBytes",
        "lifetimeUsedTrafficBytes",
        "userId",
        "userUuid",
        "user_uuid",
        "node_uuid",
        "nodeUuid",
        "nodeName",
        "node_name",
        "squadUuid",
        "squadName",
        "blocked",
        "blockDuration",
        "block_duration",
    }
)
_REMNAWAVE_TORRENT_BLOCKER_REPORT_EVENT = "torrent_blocker.report"
_REMNAWAVE_WEBSOCKET_EVENT_MAX_LENGTH = 100
_REMNAWAVE_WEBSOCKET_STRING_MAX_LENGTH = 160
_REMNAWAVE_WEBSOCKET_NUMBER_ABS_MAX = 10**15
_UNSAFE_WEBSOCKET_VALUE = object()


class ProcessRemnawaveWebhookUseCase:
    def __init__(self, session: AsyncSession, validator: RemnawaveWebhookValidator) -> None:
        self._session = session
        self._validator = validator

    async def execute(
        self,
        body: bytes,
        signature: str | None,
        timestamp: str | None,
    ) -> dict:
        import json

        if len(body) > settings.remnawave_webhook_max_body_bytes:
            log = WebhookLog(
                source="remnawave",
                event_type=None,
                payload=build_invalid_body_webhook_log_payload(
                    source="remnawave",
                    body=body,
                    signature=signature,
                    validation_reason="body_too_large",
                ),
                signature_fingerprint=signature_fingerprint(signature),
                is_valid=False,
                error_message="body_too_large",
            )
            self._session.add(log)
            return {"status": "invalid_payload"}

        validation = self._validator.validate_request(
            body,
            signature,
            timestamp,
        )

        try:
            payload = json.loads(body)
        except json.JSONDecodeError:
            log = WebhookLog(
                source="remnawave",
                event_type=None,
                payload=build_invalid_body_webhook_log_payload(
                    source="remnawave",
                    body=body,
                    signature=signature,
                    validation_reason="invalid_payload",
                ),
                signature_fingerprint=signature_fingerprint(signature),
                is_valid=False,
                error_message="invalid_payload",
            )
            self._session.add(log)
            return {"status": "invalid_payload"}

        body_fingerprint = webhook_log_fingerprint(body, namespace="remnawave_body")
        log_payload = build_remnawave_webhook_log_payload(
            payload,
            signature=signature,
            is_valid=validation.is_valid,
            validation_reason=validation.reason,
        )
        if body_fingerprint is not None:
            log_payload["body_fingerprint"] = body_fingerprint
        log = WebhookLog(
            source="remnawave",
            event_type=remnawave_event_type(payload),
            payload=log_payload,
            signature_fingerprint=signature_fingerprint(signature),
            is_valid=validation.is_valid,
            error_message=validation.reason,
        )
        self._session.add(log)

        if not validation.is_valid:
            if validation.reason in {"missing_timestamp", "invalid_timestamp", "future_timestamp", "stale_timestamp"}:
                return {"status": "invalid_timestamp"}
            return {"status": "invalid_signature"}

        event = payload.get("event", "")
        data = payload.get("data", {})
        if event == _REMNAWAVE_TORRENT_BLOCKER_REPORT_EVENT and not isinstance(data, dict):
            log.is_valid = False
            log.error_message = "invalid_torrent_blocker_report"
            return {"status": "invalid_payload"}
        if await _has_seen_remnawave_webhook(
            self._session,
            event=remnawave_event_type(payload),
            body_fingerprint=body_fingerprint,
        ):
            log.error_message = "duplicate_webhook"
            return {"status": "duplicate", "event": remnawave_event_type(payload) or ""}

        websocket_payload = _build_remnawave_websocket_payload(event, data)
        await ws_manager.broadcast("events", websocket_payload)

        return {"status": "processed", "event": websocket_payload["event"]}


def _build_remnawave_websocket_payload(event: object, data: object) -> dict[str, Any]:
    safe_event = event if isinstance(event, str) and len(event) <= _REMNAWAVE_WEBSOCKET_EVENT_MAX_LENGTH else ""
    safe_data: dict[str, Any] = {}

    if isinstance(data, dict):
        for key, value in data.items():
            if not isinstance(key, str) or key not in _REMNAWAVE_WEBSOCKET_DATA_ALLOWLIST:
                continue
            safe_value = _safe_websocket_value(value)
            if safe_value is not _UNSAFE_WEBSOCKET_VALUE:
                safe_data[key] = safe_value

    payload: dict[str, Any] = {"event": safe_event, "data": safe_data}
    if safe_event == _REMNAWAVE_TORRENT_BLOCKER_REPORT_EVENT:
        payload["abuse_type"] = "torrent"
        payload["admin_notification"] = True
    return payload


async def _has_seen_remnawave_webhook(
    session: AsyncSession,
    *,
    event: str | None,
    body_fingerprint: str | None,
) -> bool:
    if event is None or body_fingerprint is None or not hasattr(session, "execute"):
        return False

    statement = (
        select(WebhookLog.id)
        .where(
            WebhookLog.source == "remnawave",
            WebhookLog.event_type == event,
            WebhookLog.is_valid.is_(True),
            WebhookLog.payload["body_fingerprint"].as_string() == body_fingerprint,
        )
        .limit(1)
    )
    no_autoflush = getattr(session, "no_autoflush", None)
    if no_autoflush is None:
        result = await session.execute(statement)
    else:
        with no_autoflush:
            result = await session.execute(statement)
    return result.scalar_one_or_none() is not None


def _safe_websocket_value(value: object) -> object:
    if isinstance(value, str):
        return value if len(value) <= _REMNAWAVE_WEBSOCKET_STRING_MAX_LENGTH else _UNSAFE_WEBSOCKET_VALUE
    if isinstance(value, bool) or value is None:
        return value
    if isinstance(value, int):
        return value if abs(value) <= _REMNAWAVE_WEBSOCKET_NUMBER_ABS_MAX else _UNSAFE_WEBSOCKET_VALUE
    if isinstance(value, float):
        if math.isfinite(value) and abs(value) <= _REMNAWAVE_WEBSOCKET_NUMBER_ABS_MAX:
            return value
        return _UNSAFE_WEBSOCKET_VALUE
    return _UNSAFE_WEBSOCKET_VALUE
