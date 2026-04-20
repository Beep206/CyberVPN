from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.enums import RefundStatus
from src.infrastructure.database.models.refund_model import RefundModel
from src.infrastructure.database.repositories.order_repo import OrderRepository
from src.infrastructure.database.repositories.payment_attempt_repo import PaymentAttemptRepository
from src.infrastructure.database.repositories.refund_repo import RefundRepository
from src.presentation.dependencies.auth_realms import RealmResolution

RESERVED_REFUND_STATUSES = (
    RefundStatus.REQUESTED.value,
    RefundStatus.PROCESSING.value,
    RefundStatus.SUCCEEDED.value,
)


@dataclass(frozen=True)
class CreateRefundResult:
    refund: RefundModel
    created: bool


class CreateRefundUseCase:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._orders = OrderRepository(session)
        self._attempts = PaymentAttemptRepository(session)
        self._refunds = RefundRepository(session)

    async def execute(
        self,
        *,
        order_id: UUID,
        user_id: UUID,
        current_realm: RealmResolution,
        idempotency_key: str,
        amount: Decimal,
        payment_attempt_id: UUID | None = None,
        reason_code: str | None = None,
        reason_text: str | None = None,
    ) -> CreateRefundResult:
        order = await self._orders.get_by_id(order_id)
        if order is None or order.user_id != user_id:
            raise ValueError("Order not found")
        if str(order.auth_realm_id) != current_realm.realm_id:
            raise ValueError("Order does not belong to the current auth realm")
        if order.settlement_status not in {"paid", "partially_refunded", "refunded"}:
            raise ValueError("Refunds are only available for paid orders")

        existing = await self._refunds.get_by_order_and_idempotency_key(
            order_id=order_id,
            idempotency_key=idempotency_key,
        )
        if existing is not None:
            return CreateRefundResult(refund=existing, created=False)

        tracked_amount = await self._refunds.sum_for_order_by_statuses(
            order_id=order_id,
            statuses=RESERVED_REFUND_STATUSES,
        )
        remaining_amount = Decimal(str(order.displayed_price)) - tracked_amount
        if amount <= 0:
            raise ValueError("Refund amount must be greater than zero")
        if amount > remaining_amount:
            raise ValueError("Refund amount exceeds the remaining refundable order balance")

        payment_attempt = None
        if payment_attempt_id is not None:
            payment_attempt = await self._attempts.get_by_id(payment_attempt_id)
            if payment_attempt is None or payment_attempt.order_id != order.id:
                raise ValueError("Payment attempt does not belong to the order")
        else:
            payment_attempt = await self._attempts.get_latest_succeeded_for_order(order.id)

        refund = RefundModel(
            order_id=order.id,
            payment_attempt_id=payment_attempt.id if payment_attempt is not None else None,
            payment_id=payment_attempt.payment_id if payment_attempt is not None else None,
            refund_status=RefundStatus.REQUESTED.value,
            amount=float(amount),
            currency_code=order.currency_code,
            provider=payment_attempt.provider if payment_attempt is not None else None,
            reason_code=reason_code,
            reason_text=reason_text,
            idempotency_key=idempotency_key,
            provider_snapshot={
                "provider": payment_attempt.provider if payment_attempt is not None else None,
                "external_reference": payment_attempt.external_reference if payment_attempt is not None else None,
            },
            request_snapshot={
                "order_id": str(order.id),
                "checkout_session_id": str(order.checkout_session_id),
                "requested_by_user_id": str(user_id),
                "auth_realm_id": current_realm.realm_id,
                "amount": float(amount),
                "currency_code": order.currency_code,
                "reason_code": reason_code,
                "reason_text": reason_text,
                "payment_attempt_id": str(payment_attempt.id) if payment_attempt is not None else None,
                "order_settlement_status": order.settlement_status,
            },
            submitted_at=datetime.now(UTC),
        )
        created_refund = await self._refunds.create(refund)
        await self._session.commit()
        refreshed = await self._refunds.get_by_id(created_refund.id)
        if refreshed is None:
            raise ValueError("Refund was created but could not be reloaded")
        return CreateRefundResult(refund=refreshed, created=True)
