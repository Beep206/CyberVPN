from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.database.models.webhook_log_model import WebhookLog
from src.infrastructure.messaging.websocket_manager import ws_manager
from src.infrastructure.remnawave.webhook_validator import RemnawaveWebhookValidator


class ProcessRemnawaveWebhookUseCase:
    def __init__(self, session: AsyncSession, validator: RemnawaveWebhookValidator) -> None:
        self._session = session
        self._validator = validator

    async def execute(self, body: bytes, signature: str) -> dict:
        import json
        is_valid = self._validator.validate_signature(body, signature)
        payload = json.loads(body)

        log = WebhookLog(
            source="remnawave",
            event_type=payload.get("event"),
            payload=payload,
            signature=signature,
            is_valid=is_valid,
        )
        self._session.add(log)

        if not is_valid:
            return {"status": "invalid_signature"}

        event = payload.get("event", "")
        data = payload.get("data", {})

        await ws_manager.broadcast("events", {"event": event, "data": data})

        return {"status": "processed", "event": event}
