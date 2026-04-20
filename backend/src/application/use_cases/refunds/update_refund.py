from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.application.use_cases.settlement.adjustments import ApplyRefundSettlementEffectsUseCase
from src.domain.enums import PaymentStatus, RefundStatus
from src.infrastructure.database.repositories.order_repo import OrderRepository
from src.infrastructure.database.repositories.payment_repo import PaymentRepository
from src.infrastructure.database.repositories.refund_repo import RefundRepository

TERMINAL_REFUND_STATUSES = {
    RefundStatus.SUCCEEDED.value,
    RefundStatus.FAILED.value,
    RefundStatus.CANCELLED.value,
}
SUCCEEDED_REFUND_STATUSES = (RefundStatus.SUCCEEDED.value,)


class UpdateRefundUseCase:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._orders = OrderRepository(session)
        self._payments = PaymentRepository(session)
        self._refunds = RefundRepository(session)
        self._settlement_effects = ApplyRefundSettlementEffectsUseCase(session)

    async def execute(
        self,
        *,
        refund_id: UUID,
        refund_status: str,
        external_reference: str | None = None,
        provider_snapshot: dict | None = None,
    ):
        refund = await self._refunds.get_by_id(refund_id)
        if refund is None:
            raise ValueError("Refund not found")
        if refund_status not in {member.value for member in RefundStatus}:
            raise ValueError("Refund status is invalid")
        if refund.refund_status in TERMINAL_REFUND_STATUSES and refund.refund_status != refund_status:
            raise ValueError("Refund is already in a terminal state")

        refund.refund_status = refund_status
        if external_reference is not None:
            refund.external_reference = external_reference
        if provider_snapshot is not None:
            refund.provider_snapshot = dict(provider_snapshot)
        if refund_status == RefundStatus.SUCCEEDED.value and refund.completed_at is None:
            refund.completed_at = datetime.now(UTC)

        await self._session.flush()

        order = await self._orders.get_by_id(refund.order_id)
        if order is None:
            raise ValueError("Refund order not found")

        refunded_total = await self._refunds.sum_for_order_by_statuses(
            order_id=order.id,
            statuses=SUCCEEDED_REFUND_STATUSES,
        )
        order.settlement_status = _resolve_order_settlement_status(
            refunded_total=refunded_total,
            displayed_price=Decimal(str(order.displayed_price)),
        )

        if refund.payment_id is not None:
            payment = await self._payments.get_by_id(refund.payment_id)
            if payment is not None and refunded_total >= Decimal(str(order.displayed_price)):
                payment.status = PaymentStatus.REFUNDED.value
                await self._payments.update(payment)

        if refund.refund_status == RefundStatus.SUCCEEDED.value:
            await self._settlement_effects.execute(refund_id=refund.id)

        await self._session.commit()
        refreshed = await self._refunds.get_by_id(refund.id)
        if refreshed is None:
            raise ValueError("Refund was updated but could not be reloaded")
        return refreshed


def _resolve_order_settlement_status(*, refunded_total: Decimal, displayed_price: Decimal) -> str:
    if refunded_total >= displayed_price:
        return "refunded"
    if refunded_total > 0:
        return "partially_refunded"
    return "paid"
