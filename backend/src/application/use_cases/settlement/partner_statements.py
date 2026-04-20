from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.application.events import EventOutboxService, OutboxActorContext
from src.application.use_cases.settlement._statement_snapshot import build_statement_snapshot
from src.domain.enums import PartnerStatementStatus, SettlementPeriodStatus
from src.infrastructure.database.models.partner_statement_model import PartnerStatementModel
from src.infrastructure.database.models.statement_adjustment_model import StatementAdjustmentModel
from src.infrastructure.database.repositories.settlement_repo import SettlementRepository


class GeneratePartnerStatementUseCase:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._settlement = SettlementRepository(session)
        self._outbox = EventOutboxService(session)

    async def execute(self, *, settlement_period_id: UUID) -> PartnerStatementModel:
        period = await self._settlement.get_settlement_period_by_id(settlement_period_id)
        if period is None:
            raise ValueError("Settlement period not found")

        existing = await self._settlement.get_open_partner_statement(
            partner_account_id=period.partner_account_id,
            settlement_period_id=period.id,
        )
        if existing is not None:
            snapshot = await build_statement_snapshot(
                settlement=self._settlement,
                partner_account_id=period.partner_account_id,
                settlement_period=period,
                partner_statement_id=existing.id,
            )
            _apply_snapshot(existing, snapshot)
            await self._session.commit()
            await self._session.refresh(existing)
            return existing

        prior_statements = await self._settlement.list_partner_statements_for_period(
            partner_account_id=period.partner_account_id,
            settlement_period_id=period.id,
        )
        next_version = max((item.statement_version for item in prior_statements), default=0) + 1
        statement = PartnerStatementModel(
            partner_account_id=period.partner_account_id,
            settlement_period_id=period.id,
            statement_key=f"{period.period_key}-v{next_version}",
            statement_version=next_version,
            statement_status=PartnerStatementStatus.OPEN.value,
            currency_code=period.currency_code,
        )
        created = await self._settlement.create_partner_statement(statement)
        snapshot = await build_statement_snapshot(
            settlement=self._settlement,
            partner_account_id=period.partner_account_id,
            settlement_period=period,
            partner_statement_id=created.id,
        )
        _apply_snapshot(created, snapshot)
        created.statement_snapshot = dict(snapshot.statement_snapshot)
        await self._outbox.append_event(
            event_name="settlement.statement.generated",
            aggregate_type="partner_statement",
            aggregate_id=str(created.id),
            partition_key=str(created.partner_account_id),
            event_payload={
                "partner_statement_id": str(created.id),
                "partner_account_id": str(created.partner_account_id),
                "settlement_period_id": str(created.settlement_period_id),
                "statement_key": created.statement_key,
                "statement_version": created.statement_version,
                "currency_code": created.currency_code,
                "available_amount": float(created.available_amount),
                "source_event_count": created.source_event_count,
            },
            source_context={"source_use_case": "GeneratePartnerStatementUseCase"},
        )
        await self._session.commit()
        await self._session.refresh(created)
        return created


class ListPartnerStatementsUseCase:
    def __init__(self, session: AsyncSession) -> None:
        self._settlement = SettlementRepository(session)

    async def execute(
        self,
        *,
        partner_account_id: UUID | None = None,
        settlement_period_id: UUID | None = None,
        statement_status: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[PartnerStatementModel]:
        return await self._settlement.list_partner_statements(
            partner_account_id=partner_account_id,
            settlement_period_id=settlement_period_id,
            statement_status=statement_status,
            limit=limit,
            offset=offset,
        )


class GetPartnerStatementUseCase:
    def __init__(self, session: AsyncSession) -> None:
        self._settlement = SettlementRepository(session)

    async def execute(self, *, statement_id: UUID) -> PartnerStatementModel | None:
        return await self._settlement.get_partner_statement_by_id(statement_id)


class ClosePartnerStatementUseCase:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._settlement = SettlementRepository(session)
        self._outbox = EventOutboxService(session)

    async def execute(self, *, statement_id: UUID, closed_by_admin_user_id: UUID) -> PartnerStatementModel:
        statement = await self._settlement.get_partner_statement_by_id(statement_id)
        if statement is None:
            raise ValueError("Partner statement not found")
        if statement.statement_status == PartnerStatementStatus.CLOSED.value:
            return statement

        period = await self._settlement.get_settlement_period_by_id(statement.settlement_period_id)
        if period is None:
            raise ValueError("Settlement period not found")
        snapshot = await build_statement_snapshot(
            settlement=self._settlement,
            partner_account_id=statement.partner_account_id,
            settlement_period=period,
            partner_statement_id=statement.id,
        )
        _apply_snapshot(statement, snapshot)
        statement.statement_snapshot = dict(snapshot.statement_snapshot)
        statement.statement_status = PartnerStatementStatus.CLOSED.value
        statement.closed_at = datetime.now(UTC)
        statement.closed_by_admin_user_id = closed_by_admin_user_id
        await self._outbox.append_event(
            event_name="settlement.statement.closed",
            aggregate_type="partner_statement",
            aggregate_id=str(statement.id),
            partition_key=str(statement.partner_account_id),
            event_payload={
                "partner_statement_id": str(statement.id),
                "partner_account_id": str(statement.partner_account_id),
                "statement_key": statement.statement_key,
                "statement_version": statement.statement_version,
                "available_amount": float(statement.available_amount),
                "closed_by_admin_user_id": str(closed_by_admin_user_id),
            },
            actor_context=OutboxActorContext(principal_type="admin", principal_id=str(closed_by_admin_user_id)),
            source_context={"source_use_case": "ClosePartnerStatementUseCase"},
        )
        await self._session.commit()
        await self._session.refresh(statement)
        return statement


class ReopenPartnerStatementUseCase:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._settlement = SettlementRepository(session)
        self._outbox = EventOutboxService(session)

    async def execute(self, *, statement_id: UUID) -> PartnerStatementModel:
        statement = await self._settlement.get_partner_statement_by_id(statement_id)
        if statement is None:
            raise ValueError("Partner statement not found")
        if statement.statement_status != PartnerStatementStatus.CLOSED.value:
            raise ValueError("Only closed statements may be reopened")
        if statement.superseded_by_statement_id is not None:
            raise ValueError("Partner statement has already been reopened")

        period = await self._settlement.get_settlement_period_by_id(statement.settlement_period_id)
        if period is None:
            raise ValueError("Settlement period not found")
        if period.period_status != SettlementPeriodStatus.OPEN.value:
            raise ValueError("Settlement period must be open before reopening statement")

        cloned = PartnerStatementModel(
            partner_account_id=statement.partner_account_id,
            settlement_period_id=statement.settlement_period_id,
            statement_key=f"{period.period_key}-v{statement.statement_version + 1}",
            statement_version=statement.statement_version + 1,
            statement_status=PartnerStatementStatus.OPEN.value,
            reopened_from_statement_id=statement.id,
            currency_code=statement.currency_code,
        )
        created = await self._settlement.create_partner_statement(cloned)
        prior_adjustments = await self._settlement.list_statement_adjustments(partner_statement_id=statement.id)
        for prior in prior_adjustments:
            await self._settlement.create_statement_adjustment(
                StatementAdjustmentModel(
                    partner_statement_id=created.id,
                    partner_account_id=created.partner_account_id,
                    source_reference_type=prior.source_reference_type,
                    source_reference_id=prior.source_reference_id,
                    carried_from_adjustment_id=prior.id,
                    adjustment_type=prior.adjustment_type,
                    adjustment_direction=prior.adjustment_direction,
                    amount=float(prior.amount),
                    currency_code=prior.currency_code,
                    reason_code=prior.reason_code,
                    adjustment_payload=dict(prior.adjustment_payload or {}),
                    created_by_admin_user_id=prior.created_by_admin_user_id,
                )
            )

        statement.superseded_by_statement_id = created.id
        snapshot = await build_statement_snapshot(
            settlement=self._settlement,
            partner_account_id=created.partner_account_id,
            settlement_period=period,
            partner_statement_id=created.id,
        )
        _apply_snapshot(created, snapshot)
        created.statement_snapshot = dict(snapshot.statement_snapshot)
        await self._outbox.append_event(
            event_name="settlement.statement.reopened",
            aggregate_type="partner_statement",
            aggregate_id=str(created.id),
            partition_key=str(created.partner_account_id),
            event_payload={
                "partner_statement_id": str(created.id),
                "partner_account_id": str(created.partner_account_id),
                "statement_key": created.statement_key,
                "statement_version": created.statement_version,
                "reopened_from_statement_id": str(statement.id),
                "available_amount": float(created.available_amount),
            },
            source_context={"source_use_case": "ReopenPartnerStatementUseCase"},
        )
        await self._session.commit()
        await self._session.refresh(created)
        return created


def _apply_snapshot(statement: PartnerStatementModel, snapshot) -> None:
    statement.currency_code = snapshot.currency_code
    statement.accrual_amount = snapshot.accrual_amount
    statement.on_hold_amount = snapshot.on_hold_amount
    statement.reserve_amount = snapshot.reserve_amount
    statement.adjustment_net_amount = snapshot.adjustment_net_amount
    statement.available_amount = snapshot.available_amount
    statement.source_event_count = snapshot.source_event_count
    statement.held_event_count = snapshot.held_event_count
    statement.active_reserve_count = snapshot.active_reserve_count
    statement.adjustment_count = snapshot.adjustment_count
