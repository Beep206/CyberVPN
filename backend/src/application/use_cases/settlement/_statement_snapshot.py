from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

from src.domain.enums import StatementAdjustmentDirection
from src.infrastructure.database.repositories.settlement_repo import SettlementRepository


@dataclass(frozen=True)
class StatementSnapshotResult:
    currency_code: str
    accrual_amount: float
    on_hold_amount: float
    reserve_amount: float
    adjustment_net_amount: float
    available_amount: float
    source_event_count: int
    held_event_count: int
    active_reserve_count: int
    adjustment_count: int
    statement_snapshot: dict


async def build_statement_snapshot(
    *,
    settlement: SettlementRepository,
    partner_account_id: UUID,
    settlement_period,
    partner_statement_id: UUID | None = None,
) -> StatementSnapshotResult:
    window_start = _normalize_utc(settlement_period.window_start)
    window_end = _normalize_utc(settlement_period.window_end)

    earning_events = await settlement.list_earning_events_for_period(
        partner_account_id=partner_account_id,
        window_start=window_start,
        window_end=window_end,
    )
    event_ids = [item.id for item in earning_events]
    active_holds = await settlement.list_active_holds_for_events(event_ids)
    active_reserves = await settlement.list_active_reserves_for_statement_scope(
        partner_account_id=partner_account_id,
        earning_event_ids=event_ids,
        window_start=window_start,
        window_end=window_end,
    )
    adjustments = (
        await settlement.list_statement_adjustments(partner_statement_id=partner_statement_id)
        if partner_statement_id is not None
        else []
    )

    accrual_amount = round(sum(float(item.total_amount) for item in earning_events), 2)
    held_event_ids = {item.earning_event_id for item in active_holds}
    held_events = [item for item in earning_events if item.id in held_event_ids]
    on_hold_amount = round(sum(float(item.total_amount) for item in held_events), 2)
    reserve_amount = round(sum(float(item.amount) for item in active_reserves), 2)

    adjustment_net_amount = 0.0
    for adjustment in adjustments:
        amount = float(adjustment.amount)
        if adjustment.adjustment_direction == StatementAdjustmentDirection.CREDIT.value:
            adjustment_net_amount += amount
        else:
            adjustment_net_amount -= amount
    adjustment_net_amount = round(adjustment_net_amount, 2)

    available_amount = round(accrual_amount - on_hold_amount - reserve_amount + adjustment_net_amount, 2)
    currency_code = (
        earning_events[0].currency_code
        if earning_events
        else settlement_period.currency_code
    )

    snapshot = {
        "window_start": window_start.isoformat(),
        "window_end": window_end.isoformat(),
        "currency_code": currency_code,
        "earning_event_ids": [str(item.id) for item in earning_events],
        "held_event_ids": [str(item.id) for item in held_events],
        "reserve_ids": [str(item.id) for item in active_reserves],
        "adjustment_ids": [str(item.id) for item in adjustments],
        "totals": {
            "accrual_amount": accrual_amount,
            "on_hold_amount": on_hold_amount,
            "reserve_amount": reserve_amount,
            "adjustment_net_amount": adjustment_net_amount,
            "available_amount": available_amount,
        },
    }

    return StatementSnapshotResult(
        currency_code=currency_code,
        accrual_amount=accrual_amount,
        on_hold_amount=on_hold_amount,
        reserve_amount=reserve_amount,
        adjustment_net_amount=adjustment_net_amount,
        available_amount=available_amount,
        source_event_count=len(earning_events),
        held_event_count=len(held_events),
        active_reserve_count=len(active_reserves),
        adjustment_count=len(adjustments),
        statement_snapshot=snapshot,
    )


def _normalize_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)
