from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.enums import SettlementPeriodStatus
from src.infrastructure.database.models.settlement_period_model import SettlementPeriodModel
from src.infrastructure.database.repositories.partner_account_repository import PartnerAccountRepository
from src.infrastructure.database.repositories.settlement_repo import SettlementRepository


class CreateSettlementPeriodUseCase:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._partners = PartnerAccountRepository(session)
        self._settlement = SettlementRepository(session)

    async def execute(
        self,
        *,
        partner_account_id: UUID,
        period_key: str,
        window_start: datetime,
        window_end: datetime,
        currency_code: str,
    ) -> SettlementPeriodModel:
        if window_end <= window_start:
            raise ValueError("window_end must be greater than window_start")
        partner_account = await self._partners.get_account_by_id(partner_account_id)
        if partner_account is None:
            raise ValueError("Partner account not found")
        existing = await self._settlement.get_settlement_period_by_key(
            partner_account_id=partner_account_id,
            period_key=period_key.strip(),
        )
        if existing is not None:
            return existing

        period = SettlementPeriodModel(
            partner_account_id=partner_account_id,
            period_key=period_key.strip(),
            period_status=SettlementPeriodStatus.OPEN.value,
            currency_code=currency_code.upper(),
            window_start=_normalize_utc(window_start),
            window_end=_normalize_utc(window_end),
        )
        created = await self._settlement.create_settlement_period(period)
        await self._session.commit()
        await self._session.refresh(created)
        return created


class ListSettlementPeriodsUseCase:
    def __init__(self, session: AsyncSession) -> None:
        self._settlement = SettlementRepository(session)

    async def execute(
        self,
        *,
        partner_account_id: UUID | None = None,
        period_status: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[SettlementPeriodModel]:
        return await self._settlement.list_settlement_periods(
            partner_account_id=partner_account_id,
            period_status=period_status,
            limit=limit,
            offset=offset,
        )


class GetSettlementPeriodUseCase:
    def __init__(self, session: AsyncSession) -> None:
        self._settlement = SettlementRepository(session)

    async def execute(self, *, settlement_period_id: UUID) -> SettlementPeriodModel | None:
        return await self._settlement.get_settlement_period_by_id(settlement_period_id)


class CloseSettlementPeriodUseCase:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._settlement = SettlementRepository(session)

    async def execute(self, *, settlement_period_id: UUID, closed_by_admin_user_id: UUID) -> SettlementPeriodModel:
        period = await self._settlement.get_settlement_period_by_id(settlement_period_id)
        if period is None:
            raise ValueError("Settlement period not found")
        if period.period_status == SettlementPeriodStatus.CLOSED.value:
            return period
        period.period_status = SettlementPeriodStatus.CLOSED.value
        period.closed_at = datetime.now(UTC)
        period.closed_by_admin_user_id = closed_by_admin_user_id
        await self._session.commit()
        await self._session.refresh(period)
        return period


class ReopenSettlementPeriodUseCase:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._settlement = SettlementRepository(session)

    async def execute(self, *, settlement_period_id: UUID, reopened_by_admin_user_id: UUID) -> SettlementPeriodModel:
        period = await self._settlement.get_settlement_period_by_id(settlement_period_id)
        if period is None:
            raise ValueError("Settlement period not found")
        period.period_status = SettlementPeriodStatus.OPEN.value
        period.reopened_at = datetime.now(UTC)
        period.reopened_by_admin_user_id = reopened_by_admin_user_id
        await self._session.commit()
        await self._session.refresh(period)
        return period


def _normalize_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)
