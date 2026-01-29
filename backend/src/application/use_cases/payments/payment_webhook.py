from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.database.models.webhook_log_model import WebhookLog
from src.infrastructure.payments.cryptobot.webhook_handler import CryptoBotWebhookHandler


class ProcessPaymentWebhookUseCase:
    def __init__(self, session: AsyncSession, webhook_handler: CryptoBotWebhookHandler) -> None:
        self._session = session
        self._handler = webhook_handler

    async def execute(self, provider: str, body: bytes, signature: str) -> dict:
        is_valid = self._handler.validate_signature(body, signature)
        payload = self._handler.parse_payload(body)

        log = WebhookLog(
            source=provider,
            event_type=payload.get("update_type"),
            payload=payload,
            signature=signature,
            is_valid=is_valid,
        )
        self._session.add(log)

        if not is_valid:
            return {"status": "invalid_signature"}

        update_type = payload.get("update_type")
        if update_type == "invoice_paid":
            invoice = payload.get("payload", {})
            return {"status": "processed", "invoice_id": invoice.get("invoice_id")}

        return {"status": "ignored", "update_type": update_type}
