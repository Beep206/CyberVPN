from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import ROUND_HALF_UP, Decimal
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.database.repositories.settlement_repo import SettlementRepository

_MONEY_QUANT = Decimal("0.01")
_ZERO = Decimal("0")


@dataclass(frozen=True)
class PartnerFinanceCurrencySummary:
    currency_code: str
    event_count: int
    pending_amount: str
    on_hold_amount: str
    available_amount: str
    paid_amount: str
    reserved_amount: str
    reversed_amount: str
    adjustment_amount: str
    total_amount: str
    statement_count: int
    statement_event_count: int
    statement_included_amount: str
    statement_on_hold_amount: str
    statement_available_amount: str
    statement_reserved_amount: str
    statement_adjustment_amount: str
    payout_instruction_count: int
    payout_instruction_amount: str
    payout_pending_amount: str
    payout_approved_amount: str
    payout_completed_amount: str
    next_payout_forecast_amount: str
    last_event_at: datetime | None


@dataclass(frozen=True)
class PartnerFinanceSummary:
    workspace_id: UUID
    generated_at: datetime
    source_of_truth: str
    currencies: tuple[PartnerFinanceCurrencySummary, ...]


class GetPartnerFinanceSummaryUseCase:
    def __init__(self, session: AsyncSession) -> None:
        self._settlement = SettlementRepository(session)

    async def execute(self, *, partner_account_id: UUID) -> PartnerFinanceSummary:
        rows = await self._settlement.get_partner_finance_currency_totals(partner_account_id=partner_account_id)
        currencies = tuple(_build_currency_summary(row) for row in rows)
        return PartnerFinanceSummary(
            workspace_id=partner_account_id,
            generated_at=datetime.now(UTC),
            source_of_truth=("earning_events,reserves,partner_statements,statement_adjustments,payout_instructions"),
            currencies=currencies,
        )


def _build_currency_summary(row) -> PartnerFinanceCurrencySummary:
    statement_available_amount = row.statement_available_amount
    active_reserved_amount = row.reserved_amount
    payout_instruction_amount = row.payout_instruction_amount
    uninstructed_statement_amount = max(statement_available_amount - payout_instruction_amount, _ZERO)
    next_payout_forecast_amount = row.payout_pending_amount + row.payout_approved_amount + uninstructed_statement_amount
    if next_payout_forecast_amount == _ZERO and statement_available_amount == _ZERO:
        next_payout_forecast_amount = max(row.available_amount - active_reserved_amount, _ZERO)

    adjustment_amount = row.adjustment_amount
    if adjustment_amount == _ZERO:
        adjustment_amount = row.statement_adjustment_amount

    visible_on_hold_amount = row.on_hold_amount
    if visible_on_hold_amount == _ZERO:
        visible_on_hold_amount = row.statement_on_hold_amount

    visible_available_amount = row.available_amount
    if visible_available_amount == _ZERO:
        visible_available_amount = row.statement_available_amount

    visible_reserved_amount = active_reserved_amount
    if visible_reserved_amount == _ZERO:
        visible_reserved_amount = row.statement_reserved_amount

    visible_total_amount = row.total_amount
    if visible_total_amount == _ZERO:
        visible_total_amount = row.statement_included_amount

    return PartnerFinanceCurrencySummary(
        currency_code=row.currency_code,
        event_count=row.event_count,
        pending_amount=_money(row.pending_amount),
        on_hold_amount=_money(visible_on_hold_amount),
        available_amount=_money(visible_available_amount),
        paid_amount=_money(row.paid_amount),
        reserved_amount=_money(visible_reserved_amount),
        reversed_amount=_money(row.reversed_amount),
        adjustment_amount=_money(adjustment_amount),
        total_amount=_money(visible_total_amount),
        statement_count=row.statement_count,
        statement_event_count=row.statement_event_count,
        statement_included_amount=_money(row.statement_included_amount),
        statement_on_hold_amount=_money(row.statement_on_hold_amount),
        statement_available_amount=_money(row.statement_available_amount),
        statement_reserved_amount=_money(row.statement_reserved_amount),
        statement_adjustment_amount=_money(row.statement_adjustment_amount),
        payout_instruction_count=row.payout_instruction_count,
        payout_instruction_amount=_money(row.payout_instruction_amount),
        payout_pending_amount=_money(row.payout_pending_amount),
        payout_approved_amount=_money(row.payout_approved_amount),
        payout_completed_amount=_money(row.payout_completed_amount),
        next_payout_forecast_amount=_money(next_payout_forecast_amount),
        last_event_at=row.last_event_at,
    )


def _money(value: Decimal) -> str:
    return format(value.quantize(_MONEY_QUANT, rounding=ROUND_HALF_UP), "f")
