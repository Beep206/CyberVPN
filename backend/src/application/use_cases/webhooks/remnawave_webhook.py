from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.database.models.webhook_log_model import WebhookLog
from src.infrastructure.messaging.websocket_manager import ws_manager
from src.infrastructure.remnawave.webhook_validator import RemnawaveWebhookValidator


class ProcessRemnawaveWebhookUseCase:
    def __init__(self, session: AsyncSession, validator: RemnawaveWebhookValidator) -> None:
        self._session = session
        self._validator = validator

    async def execute(
        self,
        body: bytes,
        signature: str | None,
        timestamp: str | None,
        *,
        allow_missing_timestamp: bool = False,
    ) -> dict:
        import json

        validation = self._validator.validate_request(
            body,
            signature,
            timestamp,
            allow_missing_timestamp=allow_missing_timestamp,
        )

        try:
            payload = json.loads(body)
        except json.JSONDecodeError:
            payload = {"raw_body": body.decode("utf-8", errors="replace")}
            log = WebhookLog(
                source="remnawave",
                event_type=None,
                payload=payload,
                signature=signature,
                is_valid=False,
                error_message="invalid_payload",
            )
            self._session.add(log)
            return {"status": "invalid_payload"}

        log = WebhookLog(
            source="remnawave",
            event_type=payload.get("event"),
            payload=payload,
            signature=signature,
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

        await ws_manager.broadcast("events", {"event": event, "data": data})

        return {"status": "processed", "event": event}
