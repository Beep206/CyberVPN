from __future__ import annotations

from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.application.use_cases.settlement._statement_snapshot import build_statement_snapshot
from src.application.use_cases.settlement.earning_holds import _recompute_event_status
from src.application.use_cases.settlement.partner_statements import _apply_snapshot
from src.domain.enums import (
    EarningEventStatus,
    PaymentDisputeOutcomeClass,
    PaymentDisputeStatus,
    PaymentDisputeSubtype,
    RefundStatus,
    ReserveReasonType,
    ReserveScope,
    ReserveStatus,
    StatementAdjustmentDirection,
    StatementAdjustmentType,
)
from src.infrastructure.database.models.payment_dispute_model import PaymentDisputeModel
from src.infrastructure.database.models.reserve_model import ReserveModel
from src.infrastructure.database.models.statement_adjustment_model import StatementAdjustmentModel
from src.infrastructure.database.repositories.order_repo import OrderRepository
from src.infrastructure.database.repositories.payment_dispute_repo import PaymentDisputeRepository
from src.infrastructure.database.repositories.refund_repo import RefundRepository
from src.infrastructure.database.repositories.settlement_repo import SettlementRepository

_PENNY = Decimal("0.01")
_REFUND_PENDING_RESERVE_REASON = "refund_clawback_pending_statement"
_DISPUTE_OPEN_RESERVE_REASON = "payment_dispute_open"
_DISPUTE_PENDING_RESERVE_REASON = "payment_dispute_clawback_pending_statement"


@dataclass(frozen=True)
class SettlementEffectResult:
    statement_adjustment_ids: tuple[UUID, ...]
    reserve_ids: tuple[UUID, ...]


class ApplyRefundSettlementEffectsUseCase:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._orders = OrderRepository(session)
        self._refunds = RefundRepository(session)
        self._settlement = SettlementRepository(session)

    async def execute(
        self,
        *,
        refund_id: UUID,
        created_by_admin_user_id: UUID | None = None,
    ) -> SettlementEffectResult:
        refund = await self._refunds.get_by_id(refund_id)
        if refund is None:
            raise ValueError("Refund not found")
        if refund.refund_status != RefundStatus.SUCCEEDED.value:
            return SettlementEffectResult(statement_adjustment_ids=(), reserve_ids=())

        order = await self._orders.get_by_id(refund.order_id)
        if order is None:
            raise ValueError("Refund order not found")
        earning_event = await self._settlement.get_earning_event_by_order_id(order.id)
        if earning_event is None or earning_event.partner_account_id is None:
            return SettlementEffectResult(statement_adjustment_ids=(), reserve_ids=())

        clawback_amount = _calculate_proportional_amount(
            numerator=Decimal(str(refund.amount)),
            denominator=Decimal(str(order.displayed_price)),
            base_amount=Decimal(str(earning_event.total_amount)),
        )
        if clawback_amount <= 0:
            return SettlementEffectResult(statement_adjustment_ids=(), reserve_ids=())

        adjustment_ids: list[UUID] = []
        reserve_ids: list[UUID] = []
        statement = await self._settlement.get_latest_open_partner_statement_for_account(
            partner_account_id=earning_event.partner_account_id,
        )
        if statement is not None:
            adjustment = await _ensure_statement_adjustment(
                settlement=self._settlement,
                partner_statement_id=statement.id,
                partner_account_id=earning_event.partner_account_id,
                source_reference_type="refund",
                source_reference_id=refund.id,
                adjustment_type=StatementAdjustmentType.REFUND_CLAWBACK.value,
                adjustment_direction=StatementAdjustmentDirection.DEBIT.value,
                amount=clawback_amount,
                currency_code=refund.currency_code,
                reason_code=refund.reason_code or "refund_succeeded",
                adjustment_payload={
                    "order_id": str(order.id),
                    "earning_event_id": str(earning_event.id),
                    "refund_id": str(refund.id),
                    "refund_amount": float(refund.amount),
                    "clawback_amount": float(clawback_amount),
                },
                created_by_admin_user_id=created_by_admin_user_id,
            )
            adjustment_ids.append(adjustment.id)
        else:
            reserve = await _ensure_partner_scope_reserve(
                settlement=self._settlement,
                partner_account_id=earning_event.partner_account_id,
                amount=clawback_amount,
                currency_code=refund.currency_code,
                reason_code=_REFUND_PENDING_RESERVE_REASON,
                reserve_payload={
                    "source_reference_type": "refund",
                    "source_reference_id": str(refund.id),
                    "order_id": str(order.id),
                    "earning_event_id": str(earning_event.id),
                    "clawback_amount": float(clawback_amount),
                },
                created_by_admin_user_id=created_by_admin_user_id,
            )
            reserve_ids.append(reserve.id)

        if order.settlement_status == "refunded":
            earning_event.event_status = EarningEventStatus.REVERSED.value
            earning_event.available_at = None

        await self._settlement.flush()
        await _refresh_latest_open_statement_snapshot(
            settlement=self._settlement,
            partner_account_id=earning_event.partner_account_id,
        )
        return SettlementEffectResult(
            statement_adjustment_ids=tuple(adjustment_ids),
            reserve_ids=tuple(reserve_ids),
        )


class ApplyPaymentDisputeSettlementEffectsUseCase:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._orders = OrderRepository(session)
        self._disputes = PaymentDisputeRepository(session)
        self._settlement = SettlementRepository(session)

    async def execute(
        self,
        *,
        payment_dispute_id: UUID,
        created_by_admin_user_id: UUID | None = None,
    ) -> SettlementEffectResult:
        dispute = await self._disputes.get_by_id(payment_dispute_id)
        if dispute is None:
            raise ValueError("Payment dispute not found")

        order = await self._orders.get_by_id(dispute.order_id)
        if order is None:
            raise ValueError("Dispute order not found")
        earning_event = await self._settlement.get_earning_event_by_order_id(order.id)
        if earning_event is None or earning_event.partner_account_id is None:
            return SettlementEffectResult(statement_adjustment_ids=(), reserve_ids=())

        impact_amount = _calculate_proportional_amount(
            numerator=Decimal(str(dispute.disputed_amount)),
            denominator=Decimal(str(order.displayed_price)),
            base_amount=Decimal(str(earning_event.total_amount)),
        )
        if impact_amount <= 0:
            return SettlementEffectResult(statement_adjustment_ids=(), reserve_ids=())

        adjustment_ids: list[UUID] = []
        reserve_ids: list[UUID] = []
        existing_open_reserves = await self._settlement.list_reserves_for_reason(
            partner_account_id=earning_event.partner_account_id,
            reserve_status=ReserveStatus.ACTIVE.value,
            reserve_scope=ReserveScope.EARNING_EVENT.value,
            reserve_reason_type=ReserveReasonType.DISPUTE_BUFFER.value,
            reason_code=_DISPUTE_OPEN_RESERVE_REASON,
            source_earning_event_id=earning_event.id,
        )
        matching_open_reserves = [
            item
            for item in existing_open_reserves
            if _reserve_matches_source(
                reserve=item,
                source_reference_type="payment_dispute",
                source_reference_id=dispute.id,
            )
        ]

        if _is_open_dispute(dispute):
            if matching_open_reserves:
                reserve = matching_open_reserves[0]
                reserve.amount = float(impact_amount)
                reserve.currency_code = dispute.currency_code.upper()
                reserve.reserve_payload = {
                    **dict(reserve.reserve_payload or {}),
                    "source_reference_type": "payment_dispute",
                    "source_reference_id": str(dispute.id),
                    "order_id": str(order.id),
                    "impact_amount": float(impact_amount),
                    "outcome_class": dispute.outcome_class,
                    "lifecycle_status": dispute.lifecycle_status,
                }
                reserve_ids.append(reserve.id)
            else:
                reserve = await _create_event_reserve(
                    settlement=self._settlement,
                    partner_account_id=earning_event.partner_account_id,
                    source_earning_event_id=earning_event.id,
                    amount=impact_amount,
                    currency_code=dispute.currency_code,
                    reason_code=_DISPUTE_OPEN_RESERVE_REASON,
                    reserve_payload={
                        "source_reference_type": "payment_dispute",
                        "source_reference_id": str(dispute.id),
                        "order_id": str(order.id),
                        "impact_amount": float(impact_amount),
                        "outcome_class": dispute.outcome_class,
                        "lifecycle_status": dispute.lifecycle_status,
                    },
                    created_by_admin_user_id=created_by_admin_user_id,
                )
                reserve_ids.append(reserve.id)
            await _recompute_event_status(self._settlement, earning_event)
            await _refresh_latest_open_statement_snapshot(
                settlement=self._settlement,
                partner_account_id=earning_event.partner_account_id,
            )
            return SettlementEffectResult(
                statement_adjustment_ids=tuple(adjustment_ids),
                reserve_ids=tuple(reserve_ids),
            )

        for reserve in matching_open_reserves:
            reserve.reserve_status = ReserveStatus.RELEASED.value
            reserve.reason_code = reserve.reason_code or _DISPUTE_OPEN_RESERVE_REASON
            reserve_ids.append(reserve.id)

        if _is_lost_dispute(dispute):
            statement = await self._settlement.get_latest_open_partner_statement_for_account(
                partner_account_id=earning_event.partner_account_id,
            )
            if statement is not None:
                adjustment = await _ensure_statement_adjustment(
                    settlement=self._settlement,
                    partner_statement_id=statement.id,
                    partner_account_id=earning_event.partner_account_id,
                    source_reference_type="payment_dispute",
                    source_reference_id=dispute.id,
                    adjustment_type=StatementAdjustmentType.DISPUTE_CLAWBACK.value,
                    adjustment_direction=StatementAdjustmentDirection.DEBIT.value,
                    amount=impact_amount,
                    currency_code=dispute.currency_code,
                    reason_code=dispute.reason_code or "payment_dispute_lost",
                    adjustment_payload={
                        "order_id": str(order.id),
                        "earning_event_id": str(earning_event.id),
                        "payment_dispute_id": str(dispute.id),
                        "disputed_amount": float(dispute.disputed_amount),
                        "fee_amount": float(dispute.fee_amount),
                        "impact_amount": float(impact_amount),
                        "subtype": dispute.subtype,
                        "outcome_class": dispute.outcome_class,
                    },
                    created_by_admin_user_id=created_by_admin_user_id,
                )
                adjustment_ids.append(adjustment.id)
            else:
                reserve = await _ensure_partner_scope_reserve(
                    settlement=self._settlement,
                    partner_account_id=earning_event.partner_account_id,
                    amount=impact_amount,
                    currency_code=dispute.currency_code,
                    reason_code=_DISPUTE_PENDING_RESERVE_REASON,
                    reserve_payload={
                        "source_reference_type": "payment_dispute",
                        "source_reference_id": str(dispute.id),
                        "order_id": str(order.id),
                        "earning_event_id": str(earning_event.id),
                        "impact_amount": float(impact_amount),
                        "outcome_class": dispute.outcome_class,
                    },
                    created_by_admin_user_id=created_by_admin_user_id,
                )
                reserve_ids.append(reserve.id)
            if _is_full_dispute(
                order_amount=Decimal(str(order.displayed_price)),
                dispute_amount=Decimal(str(dispute.disputed_amount)),
            ):
                earning_event.event_status = EarningEventStatus.REVERSED.value
                earning_event.available_at = None
            else:
                await _recompute_event_status(self._settlement, earning_event)
        elif _is_reversal_outcome(dispute):
            prior_clawbacks = await self._settlement.list_statement_adjustments_by_source_reference(
                source_reference_type="payment_dispute",
                source_reference_id=dispute.id,
                adjustment_type=StatementAdjustmentType.DISPUTE_CLAWBACK.value,
                adjustment_direction=StatementAdjustmentDirection.DEBIT.value,
            )
            if prior_clawbacks:
                statement = await self._settlement.get_latest_open_partner_statement_for_account(
                    partner_account_id=earning_event.partner_account_id,
                )
                if statement is not None:
                    adjustment = await _ensure_statement_adjustment(
                        settlement=self._settlement,
                        partner_statement_id=statement.id,
                        partner_account_id=earning_event.partner_account_id,
                        source_reference_type="payment_dispute",
                        source_reference_id=dispute.id,
                        adjustment_type=StatementAdjustmentType.RESERVE_RELEASE.value,
                        adjustment_direction=StatementAdjustmentDirection.CREDIT.value,
                        amount=impact_amount,
                        currency_code=dispute.currency_code,
                        reason_code=dispute.reason_code or "payment_dispute_reversed",
                        adjustment_payload={
                            "order_id": str(order.id),
                            "earning_event_id": str(earning_event.id),
                            "payment_dispute_id": str(dispute.id),
                            "impact_amount": float(impact_amount),
                            "reversal_of_adjustment_ids": [str(item.id) for item in prior_clawbacks],
                        },
                        created_by_admin_user_id=created_by_admin_user_id,
                    )
                adjustment_ids.append(adjustment.id)
            pending_reserves = await self._settlement.list_reserves_for_reason(
                partner_account_id=earning_event.partner_account_id,
                reserve_status=ReserveStatus.ACTIVE.value,
                reserve_scope=ReserveScope.PARTNER_ACCOUNT.value,
                reserve_reason_type=ReserveReasonType.MANUAL.value,
                reason_code=_DISPUTE_PENDING_RESERVE_REASON,
                source_earning_event_id=None,
            )
            for reserve in pending_reserves:
                if not _reserve_matches_source(
                    reserve=reserve,
                    source_reference_type="payment_dispute",
                    source_reference_id=dispute.id,
                ):
                    continue
                reserve.reserve_status = ReserveStatus.RELEASED.value
                reserve_ids.append(reserve.id)
            await _recompute_event_status(self._settlement, earning_event)

        await self._settlement.flush()
        await _refresh_latest_open_statement_snapshot(
            settlement=self._settlement,
            partner_account_id=earning_event.partner_account_id,
        )
        return SettlementEffectResult(
            statement_adjustment_ids=tuple(adjustment_ids),
            reserve_ids=tuple(reserve_ids),
        )


async def _ensure_statement_adjustment(
    *,
    settlement: SettlementRepository,
    partner_statement_id: UUID,
    partner_account_id: UUID,
    source_reference_type: str,
    source_reference_id: UUID,
    adjustment_type: str,
    adjustment_direction: str,
    amount: Decimal,
    currency_code: str,
    reason_code: str | None,
    adjustment_payload: dict,
    created_by_admin_user_id: UUID | None,
) -> StatementAdjustmentModel:
    existing = await settlement.list_statement_adjustments_by_source_reference(
        source_reference_type=source_reference_type,
        source_reference_id=source_reference_id,
        adjustment_type=adjustment_type,
        adjustment_direction=adjustment_direction,
    )
    if existing:
        return existing[-1]

    return await settlement.create_statement_adjustment(
        StatementAdjustmentModel(
            partner_statement_id=partner_statement_id,
            partner_account_id=partner_account_id,
            source_reference_type=source_reference_type,
            source_reference_id=source_reference_id,
            adjustment_type=adjustment_type,
            adjustment_direction=adjustment_direction,
            amount=float(amount),
            currency_code=currency_code.upper(),
            reason_code=reason_code,
            adjustment_payload=dict(adjustment_payload),
            created_by_admin_user_id=created_by_admin_user_id,
        )
    )


async def _create_event_reserve(
    *,
    settlement: SettlementRepository,
    partner_account_id: UUID,
    source_earning_event_id: UUID,
    amount: Decimal,
    currency_code: str,
    reason_code: str,
    reserve_payload: dict,
    created_by_admin_user_id: UUID | None,
):
    return await settlement.create_reserve(
        ReserveModel(
            partner_account_id=partner_account_id,
            source_earning_event_id=source_earning_event_id,
            reserve_scope=ReserveScope.EARNING_EVENT.value,
            reserve_reason_type=ReserveReasonType.DISPUTE_BUFFER.value,
            reserve_status=ReserveStatus.ACTIVE.value,
            amount=float(amount),
            currency_code=currency_code.upper(),
            reason_code=reason_code,
            reserve_payload=dict(reserve_payload),
            created_by_admin_user_id=created_by_admin_user_id,
        )
    )


async def _ensure_partner_scope_reserve(
    *,
    settlement: SettlementRepository,
    partner_account_id: UUID,
    amount: Decimal,
    currency_code: str,
    reason_code: str,
    reserve_payload: dict,
    created_by_admin_user_id: UUID | None,
):
    existing_candidates = await settlement.list_reserves_for_reason(
        partner_account_id=partner_account_id,
        reserve_status=ReserveStatus.ACTIVE.value,
        reserve_scope=ReserveScope.PARTNER_ACCOUNT.value,
        reserve_reason_type=ReserveReasonType.MANUAL.value,
        reason_code=reason_code,
        source_earning_event_id=None,
    )
    existing = [
        item
        for item in existing_candidates
        if _reserve_matches_source(
            reserve=item,
            source_reference_type=str(reserve_payload.get("source_reference_type")),
            source_reference_id=UUID(str(reserve_payload["source_reference_id"])),
        )
    ]
    if existing:
        reserve = existing[-1]
        reserve.amount = float(amount)
        reserve.currency_code = currency_code.upper()
        reserve.reserve_payload = dict(reserve_payload)
        return reserve

    return await settlement.create_reserve(
        ReserveModel(
            partner_account_id=partner_account_id,
            source_earning_event_id=None,
            reserve_scope=ReserveScope.PARTNER_ACCOUNT.value,
            reserve_reason_type=ReserveReasonType.MANUAL.value,
            reserve_status=ReserveStatus.ACTIVE.value,
            amount=float(amount),
            currency_code=currency_code.upper(),
            reason_code=reason_code,
            reserve_payload=dict(reserve_payload),
            created_by_admin_user_id=created_by_admin_user_id,
        )
    )


async def _refresh_latest_open_statement_snapshot(
    *,
    settlement: SettlementRepository,
    partner_account_id: UUID,
) -> None:
    statement = await settlement.get_latest_open_partner_statement_for_account(
        partner_account_id=partner_account_id,
    )
    if statement is None:
        return
    period = await settlement.get_settlement_period_by_id(statement.settlement_period_id)
    if period is None:
        return
    snapshot = await build_statement_snapshot(
        settlement=settlement,
        partner_account_id=statement.partner_account_id,
        settlement_period=period,
        partner_statement_id=statement.id,
    )
    _apply_snapshot(statement, snapshot)
    statement.statement_snapshot = dict(snapshot.statement_snapshot)
    await settlement.flush()


def _calculate_proportional_amount(
    *,
    numerator: Decimal,
    denominator: Decimal,
    base_amount: Decimal,
) -> Decimal:
    if denominator <= 0 or numerator <= 0 or base_amount <= 0:
        return Decimal("0.00")
    ratio = min(Decimal("1"), numerator / denominator)
    return (base_amount * ratio).quantize(_PENNY, rounding=ROUND_HALF_UP)


def _is_open_dispute(dispute: PaymentDisputeModel) -> bool:
    return (
        dispute.outcome_class == PaymentDisputeOutcomeClass.OPEN.value
        and dispute.lifecycle_status != PaymentDisputeStatus.CLOSED.value
    )


def _is_lost_dispute(dispute: PaymentDisputeModel) -> bool:
    return (
        dispute.lifecycle_status == PaymentDisputeStatus.CLOSED.value
        and dispute.outcome_class == PaymentDisputeOutcomeClass.LOST.value
    )


def _is_reversal_outcome(dispute: PaymentDisputeModel) -> bool:
    return (
        dispute.outcome_class == PaymentDisputeOutcomeClass.REVERSED.value
        or dispute.subtype == PaymentDisputeSubtype.DISPUTE_REVERSAL.value
    )


def _is_full_dispute(*, order_amount: Decimal, dispute_amount: Decimal) -> bool:
    if order_amount <= 0:
        return False
    return dispute_amount >= order_amount


def _reserve_matches_source(
    *,
    reserve,
    source_reference_type: str,
    source_reference_id: UUID,
) -> bool:
    payload = dict(reserve.reserve_payload or {})
    return (
        payload.get("source_reference_type") == source_reference_type
        and payload.get("source_reference_id") == str(source_reference_id)
    )
