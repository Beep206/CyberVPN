"""Persist checkout results as completed or pending payments."""

import logging
from dataclasses import dataclass
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.application.dto.payment_dto import InvoiceResponseDTO
from src.application.services.wallet_service import WalletService
from src.application.use_cases.payments.complete_zero_gateway import (
    CompleteZeroGatewayUseCase,
)
from src.application.use_cases.payments.post_payment import (
    PostPaymentProcessingUseCase,
)
from src.infrastructure.database.models.payment_model import PaymentModel
from src.infrastructure.database.repositories.payment_repo import PaymentRepository
from src.infrastructure.database.repositories.wallet_repo import WalletRepository
from src.infrastructure.payments.cryptobot.client import CryptoBotClient

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class CommitCheckoutResult:
    payment: PaymentModel
    status: str
    invoice: InvoiceResponseDTO | None = None


class CommitCheckoutUseCase:
    """Turn a checkout quote into a payment record and optional invoice."""

    def __init__(self, session: AsyncSession, crypto_client: CryptoBotClient) -> None:
        self._session = session
        self._crypto_client = crypto_client
        self._payments = PaymentRepository(session)
        wallet_repo = WalletRepository(session)
        self._wallet = WalletService(wallet_repo)

    async def execute(
        self,
        *,
        user_id: UUID,
        quote_result,
        currency: str,
        channel: str,
        description: str,
        payload: str,
        checkout_mode: str = "new_purchase",
        payment_plan_id: UUID | None = None,
        use_quote_plan_id_for_payment: bool = True,
        subscription_days_override: int | None = None,
        metadata_extra: dict | None = None,
    ) -> CommitCheckoutResult:
        addons_snapshot = [
            {
                "addon_id": str(line.addon_id),
                "code": line.code,
                "qty": line.qty,
                "unit_price": float(line.unit_price),
                "total_price": float(line.total_price),
                "location_code": line.location_code,
                "delta_entitlements": line.delta_entitlements,
            }
            for line in quote_result.addons
        ]

        metadata = {
            "commission_base_amount": str(quote_result.commission_base_amount),
            "addon_amount": str(quote_result.addon_amount),
            "channel": channel,
            "plan_name": quote_result.plan_name,
            "checkout_mode": checkout_mode,
        }
        if metadata_extra:
            metadata.update(metadata_extra)

        resolved_plan_id = quote_result.plan_id if use_quote_plan_id_for_payment else payment_plan_id
        if payment_plan_id is not None:
            resolved_plan_id = payment_plan_id

        if quote_result.is_zero_gateway:
            zero_gateway = CompleteZeroGatewayUseCase(self._session)
            payment = await zero_gateway.execute(
                user_id=user_id,
                plan_id=resolved_plan_id,
                displayed_price=quote_result.displayed_price,
                discount_amount=quote_result.discount_amount,
                wallet_amount=quote_result.wallet_amount,
                promo_code_id=quote_result.promo_code_id,
                partner_code_id=quote_result.partner_code_id,
                currency=currency,
                addons_snapshot=addons_snapshot,
                entitlements_snapshot=quote_result.entitlements_snapshot,
                commission_base_amount=quote_result.commission_base_amount,
                metadata_extra=metadata,
                subscription_days_override=subscription_days_override,
            )
            post_payment = PostPaymentProcessingUseCase(self._session)
            await post_payment.execute(payment.id)
            return CommitCheckoutResult(payment=payment, status="completed")

        if quote_result.wallet_amount > 0:
            await self._wallet.freeze(user_id, quote_result.wallet_amount)
            metadata["wallet_frozen"] = True

        invoice_data = await self._crypto_client.create_invoice(
            amount=str(quote_result.gateway_amount),
            currency=currency,
            description=description,
            payload=payload,
        )

        invoice = InvoiceResponseDTO(
            invoice_id=str(invoice_data.get("invoice_id", "")),
            payment_url=invoice_data.get("pay_url", invoice_data.get("bot_invoice_url", "")),
            amount=quote_result.gateway_amount,
            currency=currency,
            status=invoice_data.get("status", "pending"),
            expires_at=self._parse_invoice_expiration(invoice_data.get("expiration_date")),
        )

        payment = PaymentModel(
            external_id=invoice.invoice_id,
            user_uuid=user_id,
            amount=float(quote_result.displayed_price),
            currency=currency,
            status="pending",
            provider="cryptobot",
            subscription_days=subscription_days_override or quote_result.duration_days or 0,
            plan_id=resolved_plan_id,
            promo_code_id=quote_result.promo_code_id,
            partner_code_id=quote_result.partner_code_id,
            discount_amount=float(quote_result.discount_amount),
            wallet_amount_used=float(quote_result.wallet_amount),
            final_amount=float(quote_result.gateway_amount),
            addons_snapshot=addons_snapshot,
            entitlements_snapshot=quote_result.entitlements_snapshot,
            metadata_=metadata,
        )
        payment = await self._payments.create(payment)

        logger.info(
            "pending_checkout_payment_created",
            extra={
                "payment_id": str(payment.id),
                "external_id": invoice.invoice_id,
                "checkout_mode": checkout_mode,
            },
        )
        return CommitCheckoutResult(payment=payment, status="pending", invoice=invoice)

    @staticmethod
    def _parse_invoice_expiration(value: str | None):
        from datetime import UTC, datetime

        if not value:
            return datetime.now(UTC)

        normalized = value.replace("Z", "+00:00") if value.endswith("Z") else value
        try:
            return datetime.fromisoformat(normalized)
        except ValueError:
            return datetime.now(UTC)
