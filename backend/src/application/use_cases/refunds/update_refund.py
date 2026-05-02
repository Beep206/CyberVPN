from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.application.events import EventOutboxService, OutboxActorContext
from src.application.use_cases.referrals.reverse_referral_rewards import (
    ReverseReferralRewardsForOrderUseCase,
)
from src.application.use_cases.settlement.adjustments import ApplyRefundSettlementEffectsUseCase
from src.domain.enums import PaymentProvider, PaymentStatus, RefundStatus
from src.infrastructure.database.repositories.mobile_user_repo import MobileUserRepository
from src.infrastructure.database.repositories.order_repo import OrderRepository
from src.infrastructure.database.repositories.payment_repo import PaymentRepository
from src.infrastructure.database.repositories.refund_repo import RefundRepository
from src.infrastructure.payments.telegram_stars import TelegramStarsClient, TelegramStarsRefundError

TERMINAL_REFUND_STATUSES = {
    RefundStatus.SUCCEEDED.value,
    RefundStatus.FAILED.value,
    RefundStatus.CANCELLED.value,
}
SUCCEEDED_REFUND_STATUSES = (RefundStatus.SUCCEEDED.value,)


@dataclass(frozen=True)
class ProviderRefundExecutionResult:
    external_reference: str | None
    provider_snapshot: dict


class RefundProviderExecutionError(RuntimeError):
    def __init__(self, message: str, *, status_code: int = 502) -> None:
        super().__init__(message)
        self.status_code = status_code


class UpdateRefundUseCase:
    def __init__(
        self,
        session: AsyncSession,
        *,
        telegram_stars_client: TelegramStarsClient | None = None,
    ) -> None:
        self._session = session
        self._mobile_users = MobileUserRepository(session)
        self._orders = OrderRepository(session)
        self._payments = PaymentRepository(session)
        self._refunds = RefundRepository(session)
        self._settlement_effects = ApplyRefundSettlementEffectsUseCase(session)
        self._reverse_referral_rewards = ReverseReferralRewardsForOrderUseCase(session)
        self._telegram_stars_client = telegram_stars_client or TelegramStarsClient()
        self._outbox = EventOutboxService(session)

    async def execute(
        self,
        *,
        refund_id: UUID,
        refund_status: str,
        external_reference: str | None = None,
        provider_snapshot: dict | None = None,
        acted_by_admin_user_id: UUID | None = None,
        acted_by_auth_realm_id: UUID | None = None,
        skip_provider_execution: bool = False,
        source_context: dict | None = None,
    ):
        refund = await self._refunds.get_by_id(refund_id)
        if refund is None:
            raise ValueError("Refund not found")
        if refund_status not in {member.value for member in RefundStatus}:
            raise ValueError("Refund status is invalid")
        if refund.refund_status in TERMINAL_REFUND_STATUSES and refund.refund_status != refund_status:
            raise ValueError("Refund is already in a terminal state")

        previous_status = refund.refund_status
        previous_external_reference = refund.external_reference
        previous_provider_snapshot = dict(refund.provider_snapshot or {})
        transitioned_to_succeeded = (
            previous_status != RefundStatus.SUCCEEDED.value and refund_status == RefundStatus.SUCCEEDED.value
        )
        provider_execution: ProviderRefundExecutionResult | None = None
        if transitioned_to_succeeded and not skip_provider_execution:
            provider_execution = await self._execute_provider_refund(refund)

        refund.refund_status = refund_status
        if provider_execution is not None and provider_execution.external_reference is not None:
            refund.external_reference = provider_execution.external_reference
        elif external_reference is not None:
            refund.external_reference = external_reference

        merged_provider_snapshot = dict(refund.provider_snapshot or {})
        if provider_snapshot is not None:
            merged_provider_snapshot.update(dict(provider_snapshot))
        if provider_execution is not None:
            merged_provider_snapshot.update(provider_execution.provider_snapshot)
        if provider_snapshot is not None or provider_execution is not None:
            refund.provider_snapshot = merged_provider_snapshot

        if transitioned_to_succeeded and refund.completed_at is None:
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

        if transitioned_to_succeeded:
            await self._settlement_effects.execute(refund_id=refund.id)
            await self._reverse_referral_rewards.execute(
                order_id=refund.order_id,
                reversal_reason="refund_succeeded",
                commit=False,
            )

        state_or_provider_changed = (
            previous_status != refund.refund_status
            or previous_external_reference != refund.external_reference
            or previous_provider_snapshot != dict(refund.provider_snapshot or {})
        )
        if state_or_provider_changed:
            await self._outbox.append_event(
                event_name=(
                    "refund.provider_state_reconciled"
                    if skip_provider_execution
                    else "refund.status_changed"
                ),
                aggregate_type="refund",
                aggregate_id=str(refund.id),
                partition_key=str(refund.order_id),
                event_payload={
                    "refund_id": str(refund.id),
                    "order_id": str(refund.order_id),
                    "payment_id": str(refund.payment_id) if refund.payment_id is not None else None,
                    "previous_status": previous_status,
                    "current_status": refund.refund_status,
                    "provider": refund.provider,
                    "amount": float(refund.amount),
                    "currency_code": refund.currency_code,
                    "external_reference": refund.external_reference,
                    "completed_at": refund.completed_at.isoformat() if refund.completed_at is not None else None,
                    "skip_provider_execution": skip_provider_execution,
                },
                actor_context=_build_actor_context(
                    acted_by_admin_user_id=acted_by_admin_user_id,
                    acted_by_auth_realm_id=acted_by_auth_realm_id,
                    skip_provider_execution=skip_provider_execution,
                ),
                source_context={
                    "source_use_case": "UpdateRefundUseCase",
                    **dict(source_context or {}),
                },
            )

        await self._session.commit()
        refreshed = await self._refunds.get_by_id(refund.id)
        if refreshed is None:
            raise ValueError("Refund was updated but could not be reloaded")
        return refreshed

    async def _execute_provider_refund(self, refund) -> ProviderRefundExecutionResult | None:
        if refund.provider != PaymentProvider.TELEGRAM_STARS.value:
            return None

        if refund.payment_id is None:
            raise RefundProviderExecutionError("Telegram Stars refund requires a linked payment record")

        payment = await self._payments.get_by_id(refund.payment_id)
        if payment is None:
            raise RefundProviderExecutionError("Telegram Stars refund payment record was not found")
        if payment.provider != PaymentProvider.TELEGRAM_STARS.value:
            raise RefundProviderExecutionError("Refund payment provider does not match telegram_stars")

        mobile_user = await self._mobile_users.get_by_id(payment.user_uuid)
        if mobile_user is None or mobile_user.telegram_id is None:
            raise RefundProviderExecutionError("Telegram Stars refund requires a Telegram-linked customer account")

        metadata = dict(payment.metadata_ or {})
        telegram_payment_charge_id = str(
            payment.external_id or metadata.get("telegram_payment_charge_id") or ""
        ).strip()
        if not telegram_payment_charge_id:
            raise RefundProviderExecutionError("Telegram Stars refund requires a stored Telegram payment charge id")

        provider_payment_charge_id = str(metadata.get("provider_payment_charge_id") or "").strip() or None

        try:
            result = await self._telegram_stars_client.refund_payment(
                user_id=mobile_user.telegram_id,
                telegram_payment_charge_id=telegram_payment_charge_id,
                provider_payment_charge_id=provider_payment_charge_id,
            )
        except TelegramStarsRefundError as exc:
            raise RefundProviderExecutionError(str(exc), status_code=exc.status_code) from exc

        return ProviderRefundExecutionResult(
            external_reference=result.external_reference,
            provider_snapshot=result.provider_snapshot,
        )


def _resolve_order_settlement_status(*, refunded_total: Decimal, displayed_price: Decimal) -> str:
    if refunded_total >= displayed_price:
        return "refunded"
    if refunded_total > 0:
        return "partially_refunded"
    return "paid"


def _build_actor_context(
    *,
    acted_by_admin_user_id: UUID | None,
    acted_by_auth_realm_id: UUID | None,
    skip_provider_execution: bool,
) -> OutboxActorContext | None:
    if acted_by_admin_user_id is not None:
        return OutboxActorContext(
            principal_type="admin",
            principal_id=str(acted_by_admin_user_id),
            auth_realm_id=str(acted_by_auth_realm_id) if acted_by_auth_realm_id is not None else None,
        )
    if skip_provider_execution:
        return OutboxActorContext(
            principal_type="system",
            principal_id="telegram-stars-reconciliation",
        )
    return None
