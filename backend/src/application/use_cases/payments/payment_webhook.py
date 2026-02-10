import logging

from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.database.models.webhook_log_model import WebhookLog
from src.infrastructure.database.repositories.payment_repo import PaymentRepository
from src.infrastructure.payments.cryptobot.webhook_handler import CryptoBotWebhookHandler

logger = logging.getLogger(__name__)


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
            invoice_id = invoice.get("invoice_id")
            return await self._handle_invoice_paid(str(invoice_id))

        return {"status": "ignored", "update_type": update_type}

    async def _handle_invoice_paid(self, external_id: str) -> dict:
        """Process a paid invoice: mark completed, run post-payment logic."""
        from src.application.use_cases.payments.post_payment import PostPaymentProcessingUseCase

        payment_repo = PaymentRepository(self._session)
        payment = await payment_repo.get_by_external_id(external_id)

        if payment is None:
            logger.warning("Webhook invoice_paid: payment not found for external_id=%s", external_id)
            return {"status": "processed", "invoice_id": external_id, "warning": "payment_not_found"}

        if payment.status == "completed":
            return {"status": "already_processed", "invoice_id": external_id}

        # Mark payment as completed
        payment.status = "completed"
        await payment_repo.update(payment)

        # Run post-payment processing (invites, commissions, wallet debit, promo)
        post_payment = PostPaymentProcessingUseCase(self._session)
        post_results = await post_payment.execute(payment.id)

        await self._session.commit()

        logger.info(
            "Webhook invoice_paid processed",
            extra={"external_id": external_id, "payment_id": str(payment.id), **post_results},
        )
        return {"status": "processed", "invoice_id": external_id, "post_payment": post_results}
