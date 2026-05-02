from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.application.use_cases.refunds.update_refund import UpdateRefundUseCase
from src.domain.enums import PaymentProvider, RefundStatus
from src.infrastructure.database.models.refund_model import RefundModel
from src.infrastructure.database.repositories.mobile_user_repo import MobileUserRepository
from src.infrastructure.database.repositories.order_repo import OrderRepository
from src.infrastructure.database.repositories.payment_attempt_repo import PaymentAttemptRepository
from src.infrastructure.database.repositories.payment_repo import PaymentRepository
from src.infrastructure.database.repositories.refund_repo import RefundRepository


@dataclass(frozen=True)
class TelegramStarsRefundReconciliationResult:
    action: str
    payment_id: UUID | None = None
    refund_id: UUID | None = None
    refund_status: str | None = None
    already_reconciled: bool = False


class ReconcileTelegramStarsRefundUseCase:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._mobile_users = MobileUserRepository(session)
        self._orders = OrderRepository(session)
        self._payment_attempts = PaymentAttemptRepository(session)
        self._payments = PaymentRepository(session)
        self._refunds = RefundRepository(session)
        self._update_refund = UpdateRefundUseCase(session)

    async def execute(
        self,
        *,
        telegram_id: int,
        telegram_payment_charge_id: str,
        amount: int,
        transaction_id: str,
        refunded_at: datetime | None = None,
        invoice_payload: str | None = None,
        raw_transaction: dict | None = None,
    ) -> TelegramStarsRefundReconciliationResult:
        payment = await self._payments.get_telegram_stars_by_charge_id(telegram_payment_charge_id)
        if payment is None:
            return TelegramStarsRefundReconciliationResult(action="payment_not_found")
        if payment.provider != PaymentProvider.TELEGRAM_STARS.value:
            raise ValueError("Payment provider does not match telegram_stars")

        mobile_user = await self._mobile_users.get_by_id(payment.user_uuid)
        if mobile_user is None or mobile_user.telegram_id != telegram_id:
            raise ValueError("Telegram Stars reconciliation user mismatch")

        payment_attempt = await self._payment_attempts.get_by_payment_id(payment.id)
        if payment_attempt is None:
            raise ValueError("Payment attempt was not found for the Telegram Stars payment")

        order = await self._orders.get_by_id(payment_attempt.order_id)
        if order is None:
            raise ValueError("Order was not found for the Telegram Stars payment")

        existing_refund = await self._resolve_refund(
            order_id=order.id,
            payment_id=payment.id,
            charge_id=telegram_payment_charge_id,
        )
        created_new_refund = False
        if existing_refund is None:
            existing_refund = await self._refunds.create(
                RefundModel(
                    order_id=order.id,
                    payment_attempt_id=payment_attempt.id,
                    payment_id=payment.id,
                    refund_status=RefundStatus.REQUESTED.value,
                    amount=float(Decimal(str(amount))),
                    currency_code=payment.currency,
                    provider=PaymentProvider.TELEGRAM_STARS.value,
                    reason_code="provider_reconciled",
                    reason_text="Refund detected via Telegram Stars reconciliation",
                    external_reference=transaction_id,
                    idempotency_key=f"telegram-stars-reconcile:{telegram_payment_charge_id}",
                    provider_snapshot={
                        "provider": PaymentProvider.TELEGRAM_STARS.value,
                        "telegram_payment_charge_id": telegram_payment_charge_id,
                        "telegram_transaction_id": transaction_id,
                    },
                    request_snapshot={
                        "source": "telegram_stars_reconciliation",
                        "telegram_id": telegram_id,
                        "invoice_payload": invoice_payload,
                        "amount": amount,
                        "currency_code": payment.currency,
                        "payment_id": str(payment.id),
                        "payment_attempt_id": str(payment_attempt.id),
                        "order_id": str(order.id),
                    },
                    submitted_at=_normalize_utc(refunded_at or datetime.now(UTC)),
                )
            )
            created_new_refund = True

        prior_status = existing_refund.refund_status
        prior_external_reference = existing_refund.external_reference
        updated = await self._update_refund.execute(
            refund_id=existing_refund.id,
            refund_status=RefundStatus.SUCCEEDED.value,
            external_reference=transaction_id,
            provider_snapshot={
                "provider": PaymentProvider.TELEGRAM_STARS.value,
                "provider_result": "reconciled_from_get_star_transactions",
                "telegram_payment_charge_id": telegram_payment_charge_id,
                "telegram_transaction_id": transaction_id,
                "invoice_payload": invoice_payload,
                "reconciled_at": datetime.now(UTC).isoformat(),
                "provider_refunded_at": _normalize_utc(refunded_at).isoformat() if refunded_at is not None else None,
                "raw_transaction": dict(raw_transaction or {}),
            },
            skip_provider_execution=True,
            source_context={
                "source_use_case": "ReconcileTelegramStarsRefundUseCase",
                "provider_sync": "getStarTransactions",
            },
        )

        action = "reconciled_existing"
        already_reconciled = False
        if created_new_refund:
            action = "created_and_reconciled"
        elif (
            prior_status == RefundStatus.SUCCEEDED.value
            and prior_external_reference == transaction_id
        ):
            action = "already_reconciled"
            already_reconciled = True

        return TelegramStarsRefundReconciliationResult(
            action=action,
            payment_id=payment.id,
            refund_id=updated.id,
            refund_status=updated.refund_status,
            already_reconciled=already_reconciled,
        )

    async def _resolve_refund(self, *, order_id: UUID, payment_id: UUID, charge_id: str):
        refunds = await self._refunds.list_for_order(order_id)
        for refund in reversed(refunds):
            if refund.payment_id == payment_id and refund.refund_status in {
                RefundStatus.REQUESTED.value,
                RefundStatus.PROCESSING.value,
                RefundStatus.SUCCEEDED.value,
            }:
                return refund
        return await self._refunds.get_by_order_and_idempotency_key(
            order_id=order_id,
            idempotency_key=f"telegram-stars-reconcile:{charge_id}",
        )


def _normalize_utc(value: datetime | None) -> datetime:
    if value is None:
        return datetime.now(UTC)
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)
