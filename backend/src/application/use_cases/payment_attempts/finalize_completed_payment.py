from __future__ import annotations

from decimal import Decimal
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.application.events import EventOutboxService, OutboxActorContext
from src.application.use_cases.growth_benefits.fulfill import FulfillGrowthBenefitsUseCase, FulfillmentResult
from src.application.use_cases.growth_code_sets.snapshots import read_growth_checkout_v3_snapshot
from src.application.use_cases.growth_codes.reservations import GrowthCodeReservationService
from src.application.use_cases.payments.payment_completed_earnings import (
    append_payment_completed_partner_earning_publication,
)
from src.infrastructure.database.models.order_model import OrderModel
from src.infrastructure.database.models.payment_attempt_model import PaymentAttemptModel
from src.infrastructure.database.models.payment_model import PaymentModel
from src.infrastructure.database.repositories.growth_benefit_fulfillment_repo import (
    GrowthBenefitFulfillmentRepository,
)


class FinalizeCompletedPaymentUseCase:
    """Finalize an order from a completed payment and succeeded attempt."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._outbox = EventOutboxService(session)
        self._reservations = GrowthCodeReservationService(session)
        self._benefits = FulfillGrowthBenefitsUseCase(GrowthBenefitFulfillmentRepository(session))

    async def execute(
        self,
        *,
        order: OrderModel,
        payment: PaymentModel,
        payment_attempt: PaymentAttemptModel,
        quote_snapshot: dict,
        source: str,
    ) -> list[FulfillmentResult]:
        if payment.status != "completed":
            raise ValueError("Payment is not completed")
        if payment_attempt.status != "succeeded":
            raise ValueError("Payment attempt is not succeeded")
        if payment_attempt.order_id != order.id:
            raise ValueError("Payment attempt does not belong to order")
        if payment_attempt.payment_id != payment.id:
            raise ValueError("Payment attempt does not belong to payment")

        if order.settlement_status == "paid":
            return []

        reservation_id = _extract_reservation_id(quote_snapshot)
        if reservation_id is not None:
            await self._reservations.consume_for_settlement(
                reservation_id=reservation_id,
                order_id=order.id,
                payment_id=payment.id,
                user_id=order.user_id,
            )

        order.settlement_status = "paid"
        benefit_results = await self._fulfill_benefits(
            order=order,
            payment=payment,
            quote_snapshot=quote_snapshot,
        )
        if benefit_results:
            payment.growth_snapshot = {
                **dict(payment.growth_snapshot or {}),
                "benefit_fulfillments": [_benefit_result_payload(result) for result in benefit_results],
            }

        await self._outbox.append_event(
            event_name="order.finalized",
            aggregate_type="order",
            aggregate_id=str(order.id),
            partition_key=str(order.user_id),
            event_payload={
                "order_id": str(order.id),
                "settlement_status": order.settlement_status,
                "payment_id": str(payment.id),
                "payment_attempt_id": str(payment_attempt.id),
                "source": source,
            },
            actor_context=OutboxActorContext(
                principal_type="customer",
                principal_id=str(order.user_id),
                auth_realm_id=str(order.auth_realm_id),
            ),
            source_context={"source_use_case": "FinalizeCompletedPaymentUseCase"},
        )
        await append_payment_completed_partner_earning_publication(
            self._outbox,
            payment=payment,
            payment_attempt=payment_attempt,
            source=source,
        )
        for benefit_result in benefit_results:
            await self._outbox.append_event(
                event_name="growth_benefit.fulfillment.completed",
                aggregate_type="growth_benefit_fulfillment",
                aggregate_id=str(benefit_result.fulfillment_id),
                partition_key=str(order.user_id),
                event_key=f"growth_benefit.fulfillment.completed:{benefit_result.fulfillment_id}",
                event_payload={
                    "order_id": str(order.id),
                    "payment_id": str(payment.id),
                    "benefit_id": str(benefit_result.benefit_id),
                    "benefit_type": benefit_result.benefit_type,
                    "growth_code_id": str(benefit_result.growth_code_id),
                    "status": benefit_result.status,
                    "result_payload": dict(benefit_result.result_payload),
                },
                actor_context=OutboxActorContext(
                    principal_type="customer",
                    principal_id=str(order.user_id),
                    auth_realm_id=str(order.auth_realm_id),
                ),
                source_context={
                    "source_use_case": "FinalizeCompletedPaymentUseCase",
                    "source": "growth_benefit_fulfillment",
                },
            )

        await self._session.flush()
        return benefit_results

    async def _fulfill_benefits(
        self,
        *,
        order: OrderModel,
        payment: PaymentModel,
        quote_snapshot: dict,
    ) -> list[FulfillmentResult]:
        growth_checkout_snapshot = read_growth_checkout_v3_snapshot(dict(order.pricing_snapshot or {}))
        if growth_checkout_snapshot is None:
            return []
        growth_effects_snapshot = {
            **dict(growth_checkout_snapshot.get("growth_effects") or {}),
            "code_set": dict(growth_checkout_snapshot.get("code_set") or {}),
            "settlement": {
                **dict((growth_checkout_snapshot.get("growth_effects") or {}).get("settlement") or {}),
                "net_customer_paid_amount": str(_decimal(quote_snapshot.get("gateway_amount"))),
                "gateway_amount": str(_decimal(quote_snapshot.get("gateway_amount"))),
                "settlement_mode": "internal_zero"
                if _decimal(quote_snapshot.get("gateway_amount")) <= Decimal("0")
                else "external_payment",
            },
        }
        return await self._benefits.execute(
            order_id=order.id,
            payment_id=payment.id,
            user_id=order.user_id,
            growth_effects_snapshot=growth_effects_snapshot,
            settlement_completed=True,
        )


def _extract_reservation_id(quote_snapshot: dict) -> UUID | None:
    code_resolution = dict(quote_snapshot.get("code_resolution") or {})
    raw_value = code_resolution.get("reservation_id")
    if not raw_value:
        return None
    return UUID(str(raw_value))


def _benefit_result_payload(result: FulfillmentResult) -> dict:
    return {
        "fulfillment_id": str(result.fulfillment_id),
        "benefit_id": str(result.benefit_id),
        "benefit_type": result.benefit_type,
        "growth_code_id": str(result.growth_code_id),
        "idempotency_key": result.idempotency_key,
        "status": result.status,
        "duplicate": result.duplicate,
        "result_payload": dict(result.result_payload),
    }


def _decimal(value) -> Decimal:
    return Decimal(str(value or "0"))
