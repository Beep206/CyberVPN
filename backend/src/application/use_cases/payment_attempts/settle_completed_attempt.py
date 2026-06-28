from __future__ import annotations

import hashlib
import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Literal
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.application.events import EventOutboxService, OutboxActorContext
from src.application.use_cases.growth_benefits.fulfill import FulfillmentResult
from src.application.use_cases.payment_attempts.finalize_completed_payment import FinalizeCompletedPaymentUseCase
from src.application.use_cases.payments.payment_completed_earnings import (
    append_payment_completed_partner_earning_publication,
)
from src.domain.enums import PaymentAttemptStatus
from src.infrastructure.database.models.order_model import OrderModel
from src.infrastructure.database.models.payment_attempt_model import PaymentAttemptModel
from src.infrastructure.database.models.payment_model import PaymentModel
from src.infrastructure.database.repositories.order_repo import OrderRepository
from src.infrastructure.database.repositories.payment_attempt_repo import PaymentAttemptRepository
from src.infrastructure.database.repositories.payment_repo import PaymentRepository

logger = logging.getLogger(__name__)

SettlementStatus = Literal[
    "finalized",
    "already_finalized",
    "legacy_non_order",
    "unlinked",
    "order_attempt_missing",
    "ignored_terminal_attempt",
]

TERMINAL_FAILED_PAYMENT_ATTEMPT_STATUSES = {
    PaymentAttemptStatus.FAILED.value,
    PaymentAttemptStatus.EXPIRED.value,
    PaymentAttemptStatus.CANCELLED.value,
}


@dataclass(frozen=True, slots=True)
class SettlementResult:
    status: SettlementStatus
    payment_id: UUID
    payment_attempt_id: UUID | None
    order_id: UUID | None
    benefit_results: tuple[FulfillmentResult, ...] = ()
    reason: str | None = None

    @property
    def legacy_post_payment_required(self) -> bool:
        return self.status == "legacy_non_order"


class SettleCompletedPaymentAttemptUseCase:
    """Finalize completed order-based payments while preserving legacy direct payments."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._payments = PaymentRepository(session)
        self._attempts = PaymentAttemptRepository(session)
        self._orders = OrderRepository(session)
        self._outbox = EventOutboxService(session)

    async def execute(
        self,
        *,
        payment_id: UUID | None = None,
        payment_attempt_id: UUID | None = None,
        external_reference: str | None = None,
        provider: str | None = None,
        source: str,
    ) -> SettlementResult:
        payment = await self._load_payment_for_update(
            payment_id=payment_id,
            external_reference=external_reference,
            provider=provider,
        )
        if payment is None:
            raise ValueError("Payment not found")
        if payment.status != "completed":
            raise ValueError("Payment is not completed")

        payment_attempt = await self._load_payment_attempt_for_update(
            payment=payment,
            payment_attempt_id=payment_attempt_id,
        )
        if payment_attempt is None:
            order_id = _metadata_order_id(payment)
            if _metadata_indicates_order_payment(payment):
                await self._append_unlinked_payment_event(
                    payment=payment,
                    payment_attempt=None,
                    order_id=order_id,
                    source=source,
                    reason="order_payment_attempt_not_found",
                    external_reference=external_reference,
                )
                return SettlementResult(
                    status="order_attempt_missing",
                    payment_id=payment.id,
                    payment_attempt_id=None,
                    order_id=order_id,
                    reason="order_payment_attempt_not_found",
                )

            await self._append_unlinked_payment_event(
                payment=payment,
                payment_attempt=None,
                order_id=None,
                source=source,
                reason="payment_attempt_not_found",
                external_reference=external_reference,
            )
            return SettlementResult(
                status="legacy_non_order",
                payment_id=payment.id,
                payment_attempt_id=None,
                order_id=None,
                reason="payment_attempt_not_found",
            )

        if payment_attempt.status in TERMINAL_FAILED_PAYMENT_ATTEMPT_STATUSES:
            await self._append_unlinked_payment_event(
                payment=payment,
                payment_attempt=payment_attempt,
                order_id=payment_attempt.order_id,
                source=source,
                reason="payment_attempt_terminal",
                external_reference=external_reference or payment_attempt.external_reference,
            )
            return SettlementResult(
                status="ignored_terminal_attempt",
                payment_id=payment.id,
                payment_attempt_id=payment_attempt.id,
                order_id=payment_attempt.order_id,
                reason="payment_attempt_terminal",
            )

        if payment_attempt.payment_id is None:
            payment_attempt.payment_id = payment.id
        elif payment_attempt.payment_id != payment.id:
            raise ValueError("Payment attempt does not belong to payment")

        order = await self._orders.get_by_id_for_update(payment_attempt.order_id)
        if order is None:
            await self._append_unlinked_payment_event(
                payment=payment,
                payment_attempt=payment_attempt,
                order_id=payment_attempt.order_id,
                source=source,
                reason="order_not_found",
                external_reference=external_reference or payment_attempt.external_reference,
            )
            return SettlementResult(
                status="unlinked",
                payment_id=payment.id,
                payment_attempt_id=payment_attempt.id,
                order_id=payment_attempt.order_id,
                reason="order_not_found",
            )

        if payment.user_uuid != order.user_id:
            raise ValueError("Payment user does not belong to order")

        if order.settlement_status == "paid":
            if payment_attempt.status != PaymentAttemptStatus.SUCCEEDED.value:
                payment_attempt.status = PaymentAttemptStatus.SUCCEEDED.value
                payment_attempt.terminal_at = payment_attempt.terminal_at or datetime.now(UTC)
            await append_payment_completed_partner_earning_publication(
                self._outbox,
                payment=payment,
                payment_attempt=payment_attempt,
                source=source,
            )
            await self._session.flush()
            return SettlementResult(
                status="already_finalized",
                payment_id=payment.id,
                payment_attempt_id=payment_attempt.id,
                order_id=order.id,
            )

        if payment_attempt.status != PaymentAttemptStatus.SUCCEEDED.value:
            payment_attempt.status = PaymentAttemptStatus.SUCCEEDED.value
            payment_attempt.terminal_at = datetime.now(UTC)
        await self._session.flush()

        benefit_results = await FinalizeCompletedPaymentUseCase(self._session).execute(
            order=order,
            payment=payment,
            payment_attempt=payment_attempt,
            quote_snapshot=_quote_snapshot_from_order(order),
            source=source,
        )
        return SettlementResult(
            status="finalized",
            payment_id=payment.id,
            payment_attempt_id=payment_attempt.id,
            order_id=order.id,
            benefit_results=tuple(benefit_results),
        )

    async def _load_payment_for_update(
        self,
        *,
        payment_id: UUID | None,
        external_reference: str | None,
        provider: str | None,
    ) -> PaymentModel | None:
        if payment_id is not None:
            payment = await self._payments.get_by_id_for_update(payment_id)
        elif external_reference:
            payment = await self._payments.get_by_external_id_for_update(external_reference)
        else:
            raise ValueError("Payment locator is required")
        if payment is not None and provider is not None and str(payment.provider) != provider:
            raise ValueError("Payment provider mismatch")
        return payment

    async def _load_payment_attempt_for_update(
        self,
        *,
        payment: PaymentModel,
        payment_attempt_id: UUID | None,
    ) -> PaymentAttemptModel | None:
        if payment_attempt_id is not None:
            return await self._attempts.get_by_id_for_update(payment_attempt_id)
        return await self._attempts.get_by_payment_id_for_update(payment.id)

    async def _append_unlinked_payment_event(
        self,
        *,
        payment: PaymentModel,
        payment_attempt: PaymentAttemptModel | None,
        order_id: UUID | None,
        source: str,
        reason: str,
        external_reference: str | None,
    ) -> None:
        logger.warning(
            "payment_settlement_unlinked",
            extra={
                "payment_id": str(payment.id),
                "payment_attempt_id": str(payment_attempt.id) if payment_attempt else None,
                "order_id": str(order_id) if order_id else None,
                "reason": reason,
                "provider": str(payment.provider or ""),
                "external_reference_fingerprint": _provider_reference_fingerprint(
                    external_reference or payment.external_id
                ),
            },
        )
        await self._outbox.append_event(
            event_name="payment.settlement.unlinked",
            aggregate_type="payment",
            aggregate_id=str(payment.id),
            partition_key=str(payment.user_uuid),
            event_key=f"payment.settlement.unlinked:{payment.id}:{reason}",
            event_payload={
                "payment_id": str(payment.id),
                "payment_attempt_id": str(payment_attempt.id) if payment_attempt else None,
                "order_id": str(order_id) if order_id else None,
                "payment_status": payment.status,
                "payment_attempt_status": payment_attempt.status if payment_attempt else None,
                "provider": payment.provider,
                "reason": reason,
                "source": source,
                "external_reference_fingerprint": _provider_reference_fingerprint(
                    external_reference or payment.external_id
                ),
            },
            actor_context=OutboxActorContext(principal_type="customer", principal_id=str(payment.user_uuid)),
            source_context={"source_use_case": "SettleCompletedPaymentAttemptUseCase", "source": source},
        )


def _quote_snapshot_from_order(order: OrderModel) -> dict:
    pricing_snapshot = dict(order.pricing_snapshot or {})
    quote_snapshot = dict(pricing_snapshot.get("quote") or pricing_snapshot)
    quote_snapshot.setdefault("gateway_amount", str(order.gateway_amount))
    quote_snapshot.setdefault("wallet_amount", str(order.wallet_amount))
    quote_snapshot.setdefault("displayed_price", str(order.displayed_price))
    quote_snapshot.setdefault("discount_amount", str(order.discount_amount))
    quote_snapshot.setdefault("currency_code", order.currency_code)
    quote_snapshot.setdefault("duration_days", 0)
    return quote_snapshot


def _metadata_dict(payment: PaymentModel) -> dict:
    metadata = getattr(payment, "metadata_", None)
    return dict(metadata or {}) if isinstance(metadata, dict) else {}


def _metadata_indicates_order_payment(payment: PaymentModel) -> bool:
    metadata = _metadata_dict(payment)
    checkout_mode = str(metadata.get("checkout_mode") or "")
    return checkout_mode in {
        "order_payment_attempt",
        "zero_gateway_order_payment_attempt",
    } or bool(metadata.get("order_id"))


def _metadata_order_id(payment: PaymentModel) -> UUID | None:
    raw_order_id = _metadata_dict(payment).get("order_id")
    if raw_order_id is None:
        return None
    try:
        return UUID(str(raw_order_id))
    except (TypeError, ValueError):
        return None


def _provider_reference_fingerprint(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = str(value).strip()
    if not normalized:
        return None
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()
