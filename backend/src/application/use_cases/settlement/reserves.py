from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.enums import EarningEventStatus, ReserveScope, ReserveStatus
from src.infrastructure.database.models.reserve_model import ReserveModel
from src.infrastructure.database.repositories.settlement_repo import SettlementRepository


class CreateReserveUseCase:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._settlement = SettlementRepository(session)

    async def execute(
        self,
        *,
        partner_account_id: UUID,
        amount: Decimal | float | int,
        currency_code: str,
        reserve_scope: str,
        reserve_reason_type: str,
        source_earning_event_id: UUID | None = None,
        reason_code: str | None = None,
        reserve_payload: dict | None = None,
        created_by_admin_user_id: UUID | None = None,
        commit: bool = True,
    ):
        if reserve_scope not in {member.value for member in ReserveScope}:
            raise ValueError("Reserve scope is invalid")
        if Decimal(str(amount)) <= 0:
            raise ValueError("Reserve amount must be positive")
        if reserve_scope == ReserveScope.EARNING_EVENT.value and source_earning_event_id is None:
            raise ValueError("source_earning_event_id is required for earning_event reserves")

        event = None
        if source_earning_event_id is not None:
            event = await self._settlement.get_earning_event_by_id(source_earning_event_id)
            if event is None:
                raise ValueError("Source earning event not found")
            if event.partner_account_id != partner_account_id:
                raise ValueError("source_earning_event_id does not belong to the specified partner account")

        reserve = ReserveModel(
            partner_account_id=partner_account_id,
            source_earning_event_id=source_earning_event_id,
            reserve_scope=reserve_scope,
            reserve_reason_type=reserve_reason_type,
            reserve_status=ReserveStatus.ACTIVE.value,
            amount=float(Decimal(str(amount))),
            currency_code=currency_code.upper(),
            reason_code=reason_code.strip() if reason_code else None,
            reserve_payload=dict(reserve_payload or {}),
            created_by_admin_user_id=created_by_admin_user_id,
        )
        created = await self._settlement.create_reserve(reserve)
        if event is not None:
            event.event_status = EarningEventStatus.BLOCKED.value
            event.available_at = None
            await self._settlement.flush()
        if commit:
            await self._session.commit()
            await self._session.refresh(created)
        return created


class ListReservesUseCase:
    def __init__(self, session: AsyncSession) -> None:
        self._settlement = SettlementRepository(session)

    async def execute(
        self,
        *,
        partner_account_id: UUID | None = None,
        source_earning_event_id: UUID | None = None,
        reserve_status: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ):
        return await self._settlement.list_reserves(
            partner_account_id=partner_account_id,
            source_earning_event_id=source_earning_event_id,
            reserve_status=reserve_status,
            limit=limit,
            offset=offset,
        )


class GetReserveUseCase:
    def __init__(self, session: AsyncSession) -> None:
        self._settlement = SettlementRepository(session)

    async def execute(self, *, reserve_id: UUID):
        return await self._settlement.get_reserve_by_id(reserve_id)


class ReleaseReserveUseCase:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._settlement = SettlementRepository(session)

    async def execute(
        self,
        *,
        reserve_id: UUID,
        released_by_admin_user_id: UUID | None = None,
        release_reason_code: str | None = None,
        commit: bool = True,
    ):
        reserve = await self._settlement.get_reserve_by_id(reserve_id)
        if reserve is None:
            raise ValueError("Reserve not found")
        if reserve.reserve_status != ReserveStatus.ACTIVE.value:
            return reserve

        reserve.reserve_status = ReserveStatus.RELEASED.value
        reserve.released_at = datetime.now(UTC)
        reserve.released_by_admin_user_id = released_by_admin_user_id
        if release_reason_code:
            reserve.reason_code = release_reason_code.strip()

        if reserve.source_earning_event_id is not None:
            event = await self._settlement.get_earning_event_by_id(reserve.source_earning_event_id)
            if event is None:
                raise ValueError("Linked earning event not found")
            active_holds = await self._settlement.list_active_holds_for_event(event.id)
            active_reserves = await self._settlement.list_active_reserves_for_event(event.id)
            if not [item for item in active_reserves if item.id != reserve.id]:
                if active_holds:
                    event.event_status = EarningEventStatus.ON_HOLD.value
                    event.available_at = None
                else:
                    event.event_status = EarningEventStatus.AVAILABLE.value
                    event.available_at = datetime.now(UTC)
                await self._settlement.flush()

        if commit:
            await self._session.commit()
            await self._session.refresh(reserve)
        return reserve
