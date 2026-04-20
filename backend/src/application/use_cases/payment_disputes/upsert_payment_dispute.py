from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.application.use_cases.settlement.adjustments import (
    ApplyPaymentDisputeSettlementEffectsUseCase,
)
from src.domain.enums import (
    PaymentDisputeOutcomeClass,
    PaymentDisputeStatus,
    PaymentDisputeSubtype,
)
from src.infrastructure.database.models.payment_dispute_model import PaymentDisputeModel
from src.infrastructure.database.repositories.order_repo import OrderRepository
from src.infrastructure.database.repositories.payment_attempt_repo import PaymentAttemptRepository
from src.infrastructure.database.repositories.payment_dispute_repo import PaymentDisputeRepository
from src.infrastructure.database.repositories.payment_repo import PaymentRepository


@dataclass(frozen=True)
class UpsertPaymentDisputeResult:
    payment_dispute: PaymentDisputeModel
    created: bool


class UpsertPaymentDisputeUseCase:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._orders = OrderRepository(session)
        self._attempts = PaymentAttemptRepository(session)
        self._payments = PaymentRepository(session)
        self._payment_disputes = PaymentDisputeRepository(session)
        self._settlement_effects = ApplyPaymentDisputeSettlementEffectsUseCase(session)

    async def execute(
        self,
        *,
        order_id: UUID,
        subtype: str,
        outcome_class: str,
        lifecycle_status: str,
        disputed_amount: Decimal,
        currency_code: str | None = None,
        fee_amount: Decimal = Decimal("0"),
        fee_status: str = "none",
        payment_attempt_id: UUID | None = None,
        payment_id: UUID | None = None,
        provider: str | None = None,
        external_reference: str | None = None,
        reason_code: str | None = None,
        evidence_snapshot: dict | None = None,
        provider_snapshot: dict | None = None,
        opened_at: datetime | None = None,
        closed_at: datetime | None = None,
    ) -> UpsertPaymentDisputeResult:
        if subtype not in {member.value for member in PaymentDisputeSubtype}:
            raise ValueError("Payment dispute subtype is invalid")
        if outcome_class not in {member.value for member in PaymentDisputeOutcomeClass}:
            raise ValueError("Payment dispute outcome class is invalid")
        if lifecycle_status not in {member.value for member in PaymentDisputeStatus}:
            raise ValueError("Payment dispute lifecycle status is invalid")
        if disputed_amount <= 0:
            raise ValueError("Disputed amount must be greater than zero")
        if fee_amount < 0:
            raise ValueError("Fee amount must be zero or greater")

        order = await self._orders.get_by_id(order_id)
        if order is None:
            raise ValueError("Order not found")

        payment_attempt = None
        if payment_attempt_id is not None:
            payment_attempt = await self._attempts.get_by_id(payment_attempt_id)
            if payment_attempt is None or payment_attempt.order_id != order.id:
                raise ValueError("Payment attempt does not belong to the order")
            payment_id = payment_id or payment_attempt.payment_id
            provider = provider or payment_attempt.provider

        if payment_id is not None:
            payment = await self._payments.get_by_id(payment_id)
            if payment is None:
                raise ValueError("Payment not found")
            provider = provider or payment.provider

        existing = None
        if provider and external_reference:
            existing = await self._payment_disputes.get_by_provider_reference(
                provider=provider,
                external_reference=external_reference,
            )
            if existing is not None and existing.order_id != order.id:
                raise ValueError("Payment dispute provider reference belongs to a different order")

        dispute = existing or PaymentDisputeModel(
            order_id=order.id,
            payment_attempt_id=payment_attempt.id if payment_attempt is not None else payment_attempt_id,
            payment_id=payment_id,
            provider=provider,
            external_reference=external_reference,
            subtype=subtype,
            outcome_class=outcome_class,
            lifecycle_status=lifecycle_status,
            disputed_amount=float(disputed_amount),
            fee_amount=float(fee_amount),
            fee_status=fee_status,
            currency_code=currency_code or order.currency_code,
            reason_code=reason_code,
            evidence_snapshot=evidence_snapshot or {},
            provider_snapshot=provider_snapshot or {},
            opened_at=opened_at or datetime.now(UTC),
            closed_at=None,
        )
        if existing is None:
            await self._payment_disputes.create(dispute)
        else:
            if payment_attempt is not None:
                dispute.payment_attempt_id = payment_attempt.id
            dispute.payment_id = payment_id or dispute.payment_id
            dispute.provider = provider or dispute.provider
            dispute.external_reference = external_reference or dispute.external_reference
            dispute.subtype = subtype
            dispute.outcome_class = outcome_class
            dispute.lifecycle_status = lifecycle_status
            dispute.disputed_amount = float(disputed_amount)
            dispute.fee_amount = float(fee_amount)
            dispute.fee_status = fee_status
            dispute.currency_code = currency_code or dispute.currency_code
            dispute.reason_code = reason_code
            if evidence_snapshot is not None:
                dispute.evidence_snapshot = dict(evidence_snapshot)
            if provider_snapshot is not None:
                dispute.provider_snapshot = dict(provider_snapshot)
            if opened_at is not None:
                dispute.opened_at = opened_at

        if (
            outcome_class != PaymentDisputeOutcomeClass.OPEN.value
            or lifecycle_status == PaymentDisputeStatus.CLOSED.value
        ):
            dispute.closed_at = closed_at or datetime.now(UTC)
            if lifecycle_status != PaymentDisputeStatus.CLOSED.value:
                dispute.lifecycle_status = PaymentDisputeStatus.CLOSED.value
        elif closed_at is not None:
            dispute.closed_at = closed_at

        await self._settlement_effects.execute(payment_dispute_id=dispute.id)

        await self._session.commit()
        refreshed = await self._payment_disputes.get_by_id(dispute.id)
        if refreshed is None:
            raise ValueError("Payment dispute was saved but could not be reloaded")
        return UpsertPaymentDisputeResult(payment_dispute=refreshed, created=existing is None)
