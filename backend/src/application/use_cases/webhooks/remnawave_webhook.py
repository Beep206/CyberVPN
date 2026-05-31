from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from src.application.use_cases.webhooks.webhook_log_redaction import (
    build_invalid_body_webhook_log_payload,
    build_remnawave_webhook_log_payload,
    remnawave_event_type,
    signature_fingerprint,
)
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
        "nodeUuid",
        "nodeName",
        "squadUuid",
        "squadName",
    }
)
_REMNAWAVE_WEBSOCKET_VALUE_TYPES = (str, int, float, bool, type(None))


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

        log = WebhookLog(
            source="remnawave",
            event_type=remnawave_event_type(payload),
            payload=build_remnawave_webhook_log_payload(
                payload,
                signature=signature,
                is_valid=validation.is_valid,
                validation_reason=validation.reason,
            ),
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

        websocket_payload = _build_remnawave_websocket_payload(event, data)
        await ws_manager.broadcast("events", websocket_payload)

        return {"status": "processed", "event": websocket_payload["event"]}


def _build_remnawave_websocket_payload(event: object, data: object) -> dict[str, Any]:
    safe_event = event if isinstance(event, str) else ""
    safe_data: dict[str, Any] = {}

    if isinstance(data, dict):
        safe_data = {
            key: value
            for key, value in data.items()
            if key in _REMNAWAVE_WEBSOCKET_DATA_ALLOWLIST
            and isinstance(key, str)
            and isinstance(value, _REMNAWAVE_WEBSOCKET_VALUE_TYPES)
        }

    return {"event": safe_event, "data": safe_data}
