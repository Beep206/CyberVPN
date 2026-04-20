from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.enums import EarningEventStatus, EarningHoldStatus
from src.infrastructure.database.repositories.settlement_repo import SettlementRepository


class ListEarningHoldsUseCase:
    def __init__(self, session: AsyncSession) -> None:
        self._settlement = SettlementRepository(session)

    async def execute(
        self,
        *,
        earning_event_id: UUID | None = None,
        hold_status: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ):
        return await self._settlement.list_earning_holds(
            earning_event_id=earning_event_id,
            hold_status=hold_status,
            limit=limit,
            offset=offset,
        )


class GetEarningHoldUseCase:
    def __init__(self, session: AsyncSession) -> None:
        self._settlement = SettlementRepository(session)

    async def execute(self, *, hold_id: UUID):
        return await self._settlement.get_earning_hold_by_id(hold_id)


class ReleaseEarningHoldUseCase:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._settlement = SettlementRepository(session)

    async def execute(
        self,
        *,
        hold_id: UUID,
        released_by_admin_user_id: UUID | None = None,
        release_reason_code: str | None = None,
        force: bool = False,
        commit: bool = True,
    ):
        hold = await self._settlement.get_earning_hold_by_id(hold_id)
        if hold is None:
            raise ValueError("Earning hold not found")
        if hold.hold_status != EarningHoldStatus.ACTIVE.value:
            return hold
        if not force and hold.hold_until is not None and _normalize_utc(hold.hold_until) > datetime.now(UTC):
            raise ValueError("Earning hold has not matured for release")

        hold.hold_status = EarningHoldStatus.RELEASED.value
        hold.released_at = datetime.now(UTC)
        hold.released_by_admin_user_id = released_by_admin_user_id
        if release_reason_code:
            hold.reason_code = release_reason_code.strip()

        event = await self._settlement.get_earning_event_by_id(hold.earning_event_id)
        if event is None:
            raise ValueError("Linked earning event not found")
        await _recompute_event_status(self._settlement, event)
        if commit:
            await self._session.commit()
            await self._session.refresh(hold)
            await self._session.refresh(event)
        return hold


async def _recompute_event_status(settlement: SettlementRepository, event) -> None:
    active_holds = await settlement.list_active_holds_for_event(event.id)
    active_reserves = await settlement.list_active_reserves_for_event(event.id)
    if active_reserves:
        event.event_status = EarningEventStatus.BLOCKED.value
        event.available_at = None
    elif active_holds:
        event.event_status = EarningEventStatus.ON_HOLD.value
        event.available_at = None
    else:
        event.event_status = EarningEventStatus.AVAILABLE.value
        event.available_at = datetime.now(UTC)
    await settlement.flush()


def _normalize_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)
