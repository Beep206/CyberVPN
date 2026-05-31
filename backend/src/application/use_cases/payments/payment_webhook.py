import logging
from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from src.application.services.wallet_service import WalletService
from src.application.use_cases.webhooks.webhook_log_redaction import (
    build_cryptobot_webhook_log_payload,
    cryptobot_event_type,
    signature_fingerprint,
)
from src.domain.enums import PaymentAttemptStatus
from src.infrastructure.database.models.webhook_log_model import WebhookLog
from src.infrastructure.database.repositories.order_repo import OrderRepository
from src.infrastructure.database.repositories.payment_attempt_repo import PaymentAttemptRepository
from src.infrastructure.database.repositories.payment_repo import PaymentRepository
from src.infrastructure.database.repositories.wallet_repo import WalletRepository
from src.infrastructure.payments.cryptobot.webhook_handler import CryptoBotWebhookHandler

logger = logging.getLogger(__name__)


class ProcessPaymentWebhookUseCase:
    def __init__(self, session: AsyncSession, webhook_handler: CryptoBotWebhookHandler) -> None:
        self._session = session
        self._handler = webhook_handler
        self._attempts = PaymentAttemptRepository(session)
        self._orders = OrderRepository(session)
        wallet_repo = WalletRepository(session)
        self._wallet = WalletService(wallet_repo)

    async def execute(self, provider: str, body: bytes, signature: str) -> dict:
        is_valid = self._handler.validate_signature(body, signature)
        payload = self._handler.parse_payload(body)

        log = WebhookLog(
            source=provider,
            event_type=cryptobot_event_type(payload),
            payload=build_cryptobot_webhook_log_payload(
                payload,
                signature=signature,
                is_valid=is_valid,
            ),
            signature_fingerprint=signature_fingerprint(signature),
            is_valid=is_valid,
        )
        self._session.add(log)

        if not is_valid:
            return {"status": "invalid_signature"}

        update_type = payload.get("update_type")
        invoice = payload.get("payload", {})
        invoice_id = invoice.get("invoice_id")
        external_id = str(invoice_id or "")

        if update_type in {"invoice_paid", "invoice_expired", "invoice_cancelled", "invoice_failed"}:
            payment_valid, validation_error = await self._handler.validate_payment(
                external_id,
                body=body,
                signature=signature,
            )
            if not payment_valid:
                if validation_error == "Invoice already processed":
                    return {"status": "already_processed", "invoice_id": external_id}
                return {
                    "status": "invalid_payment",
                    "invoice_id": external_id or None,
                    "reason": validation_error or "Invalid payment webhook",
                }

        if update_type == "invoice_paid":
            result = await self._handle_invoice_paid(external_id)
            await self._mark_invoice_paid_processed_after_result(external_id, result)
            return result
        if update_type in {"invoice_expired", "invoice_cancelled", "invoice_failed"}:
            return await self._handle_invoice_failed(external_id, update_type)

        return {"status": "ignored", "update_type": update_type}

    async def _mark_invoice_paid_processed_after_result(self, external_id: str, result: dict) -> None:
        """Mark a paid webhook only after safe paid side effects finished."""
        if result.get("warning") == "payment_not_found":
            return
        if result.get("status") in {"processed", "already_processed", "ignored_terminal_attempt"}:
            await self._handler.mark_invoice_processed(external_id)

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

        payment_attempt = await self._attempts.get_by_payment_id(payment.id)
        if payment_attempt is not None and payment_attempt.status in {
            PaymentAttemptStatus.FAILED.value,
            PaymentAttemptStatus.EXPIRED.value,
            PaymentAttemptStatus.CANCELLED.value,
        }:
            return {
                "status": "ignored_terminal_attempt",
                "invoice_id": external_id,
                "payment_attempt_id": str(payment_attempt.id),
            }

        # Mark payment as completed
        payment.status = "completed"
        await payment_repo.update(payment)

        if payment_attempt is not None:
            payment_attempt.status = PaymentAttemptStatus.SUCCEEDED.value
            payment_attempt.terminal_at = datetime.now(UTC)
            if payment_attempt.order_id:
                order = await self._orders.get_by_id(payment_attempt.order_id)
                if order is not None:
                    order.settlement_status = "paid"

        # Run post-payment processing (invites, commissions, wallet debit, promo)
        post_payment = PostPaymentProcessingUseCase(self._session)
        post_results = await post_payment.execute(payment.id)

        await self._session.commit()

        logger.info(
            "Webhook invoice_paid processed",
            extra={"external_id": external_id, "payment_id": str(payment.id), **post_results},
        )
        return {"status": "processed", "invoice_id": external_id, "post_payment": post_results}

    async def _handle_invoice_failed(self, external_id: str, update_type: str) -> dict:
        """Release any frozen wallet amount for abandoned invoices."""
        payment_repo = PaymentRepository(self._session)
        payment = await payment_repo.get_by_external_id(external_id)

        if payment is None:
            logger.warning("Webhook %s: payment not found for external_id=%s", update_type, external_id)
            return {"status": "processed", "invoice_id": external_id, "warning": "payment_not_found"}

        if payment.status in {"completed", "failed"}:
            return {"status": "already_processed", "invoice_id": external_id}

        payment_attempt = await self._attempts.get_by_payment_id(payment.id)
        wallet_used = Decimal(str(payment.wallet_amount_used or 0))
        if wallet_used > 0 and (payment.metadata_ or {}).get("wallet_frozen"):
            try:
                await self._wallet.unfreeze(payment.user_uuid, wallet_used)
            except Exception:
                logger.exception(
                    "payment_webhook_wallet_unfreeze_failed",
                    extra={"external_id": external_id, "payment_id": str(payment.id)},
                )

        payment.status = "failed"
        await payment_repo.update(payment)

        if payment_attempt is not None and payment_attempt.status not in {
            PaymentAttemptStatus.SUCCEEDED.value,
            PaymentAttemptStatus.FAILED.value,
            PaymentAttemptStatus.EXPIRED.value,
            PaymentAttemptStatus.CANCELLED.value,
        }:
            payment_attempt.status = _map_attempt_failure_status(update_type)
            payment_attempt.terminal_at = datetime.now(UTC)
            if payment_attempt.order_id:
                order = await self._orders.get_by_id(payment_attempt.order_id)
                if order is not None and order.settlement_status != "paid":
                    order.settlement_status = "failed"

        await self._session.commit()
        logger.info(
            "Webhook invoice failure processed",
            extra={"external_id": external_id, "payment_id": str(payment.id), "update_type": update_type},
        )
        return {"status": "processed", "invoice_id": external_id, "update_type": update_type}


def _map_attempt_failure_status(update_type: str) -> str:
    if update_type == "invoice_expired":
        return PaymentAttemptStatus.EXPIRED.value
    if update_type == "invoice_cancelled":
        return PaymentAttemptStatus.CANCELLED.value
    return PaymentAttemptStatus.FAILED.value
