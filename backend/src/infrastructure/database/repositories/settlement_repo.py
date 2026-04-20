from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.database.models.earning_event_model import EarningEventModel
from src.infrastructure.database.models.earning_hold_model import EarningHoldModel
from src.infrastructure.database.models.partner_payout_account_model import PartnerPayoutAccountModel
from src.infrastructure.database.models.partner_statement_model import PartnerStatementModel
from src.infrastructure.database.models.payout_execution_model import PayoutExecutionModel
from src.infrastructure.database.models.payout_instruction_model import PayoutInstructionModel
from src.infrastructure.database.models.reserve_model import ReserveModel
from src.infrastructure.database.models.settlement_period_model import SettlementPeriodModel
from src.infrastructure.database.models.statement_adjustment_model import StatementAdjustmentModel


class SettlementRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create_earning_event(self, model: EarningEventModel) -> EarningEventModel:
        self._session.add(model)
        await self._session.flush()
        return model

    async def get_earning_event_by_id(self, event_id: UUID) -> EarningEventModel | None:
        return await self._session.get(EarningEventModel, event_id)

    async def get_earning_event_by_order_id(self, order_id: UUID) -> EarningEventModel | None:
        result = await self._session.execute(select(EarningEventModel).where(EarningEventModel.order_id == order_id))
        return result.scalar_one_or_none()

    async def list_earning_events(
        self,
        *,
        partner_account_id: UUID | None = None,
        order_id: UUID | None = None,
        event_status: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[EarningEventModel]:
        query = select(EarningEventModel)
        if partner_account_id is not None:
            query = query.where(EarningEventModel.partner_account_id == partner_account_id)
        if order_id is not None:
            query = query.where(EarningEventModel.order_id == order_id)
        if event_status is not None:
            query = query.where(EarningEventModel.event_status == event_status)
        query = query.order_by(EarningEventModel.created_at.desc()).offset(offset).limit(limit)
        result = await self._session.execute(query)
        return list(result.scalars().all())

    async def create_earning_hold(self, model: EarningHoldModel) -> EarningHoldModel:
        self._session.add(model)
        await self._session.flush()
        return model

    async def get_earning_hold_by_id(self, hold_id: UUID) -> EarningHoldModel | None:
        return await self._session.get(EarningHoldModel, hold_id)

    async def list_earning_holds(
        self,
        *,
        earning_event_id: UUID | None = None,
        hold_status: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[EarningHoldModel]:
        query = select(EarningHoldModel)
        if earning_event_id is not None:
            query = query.where(EarningHoldModel.earning_event_id == earning_event_id)
        if hold_status is not None:
            query = query.where(EarningHoldModel.hold_status == hold_status)
        query = query.order_by(EarningHoldModel.created_at.desc()).offset(offset).limit(limit)
        result = await self._session.execute(query)
        return list(result.scalars().all())

    async def list_active_holds_for_event(self, earning_event_id: UUID) -> list[EarningHoldModel]:
        result = await self._session.execute(
            select(EarningHoldModel).where(
                EarningHoldModel.earning_event_id == earning_event_id,
                EarningHoldModel.hold_status == "active",
            )
        )
        return list(result.scalars().all())

    async def list_active_holds_for_events(self, earning_event_ids: list[UUID]) -> list[EarningHoldModel]:
        if not earning_event_ids:
            return []
        result = await self._session.execute(
            select(EarningHoldModel).where(
                EarningHoldModel.earning_event_id.in_(earning_event_ids),
                EarningHoldModel.hold_status == "active",
            )
        )
        return list(result.scalars().all())

    async def create_reserve(self, model: ReserveModel) -> ReserveModel:
        self._session.add(model)
        await self._session.flush()
        return model

    async def get_reserve_by_id(self, reserve_id: UUID) -> ReserveModel | None:
        return await self._session.get(ReserveModel, reserve_id)

    async def list_reserves(
        self,
        *,
        partner_account_id: UUID | None = None,
        source_earning_event_id: UUID | None = None,
        reserve_status: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[ReserveModel]:
        query = select(ReserveModel)
        if partner_account_id is not None:
            query = query.where(ReserveModel.partner_account_id == partner_account_id)
        if source_earning_event_id is not None:
            query = query.where(ReserveModel.source_earning_event_id == source_earning_event_id)
        if reserve_status is not None:
            query = query.where(ReserveModel.reserve_status == reserve_status)
        query = query.order_by(ReserveModel.created_at.desc()).offset(offset).limit(limit)
        result = await self._session.execute(query)
        return list(result.scalars().all())

    async def list_active_reserves_for_event(self, earning_event_id: UUID) -> list[ReserveModel]:
        result = await self._session.execute(
            select(ReserveModel).where(
                ReserveModel.source_earning_event_id == earning_event_id,
                ReserveModel.reserve_status == "active",
            )
        )
        return list(result.scalars().all())

    async def list_active_reserves_for_statement_scope(
        self,
        *,
        partner_account_id: UUID,
        earning_event_ids: list[UUID],
        window_start: datetime,
        window_end: datetime,
    ) -> list[ReserveModel]:
        query = select(ReserveModel).where(
            ReserveModel.partner_account_id == partner_account_id,
            ReserveModel.reserve_status == "active",
        )
        if earning_event_ids:
            query = query.where(
                (ReserveModel.source_earning_event_id.in_(earning_event_ids))
                | (
                    (ReserveModel.source_earning_event_id.is_(None))
                    & (ReserveModel.created_at >= window_start)
                    & (ReserveModel.created_at < window_end)
                )
            )
        else:
            query = query.where(
                ReserveModel.source_earning_event_id.is_(None),
                ReserveModel.created_at >= window_start,
                ReserveModel.created_at < window_end,
            )
        result = await self._session.execute(query)
        return list(result.scalars().all())

    async def list_earning_events_for_period(
        self,
        *,
        partner_account_id: UUID,
        window_start: datetime,
        window_end: datetime,
    ) -> list[EarningEventModel]:
        result = await self._session.execute(
            select(EarningEventModel).where(
                EarningEventModel.partner_account_id == partner_account_id,
                EarningEventModel.created_at >= window_start,
                EarningEventModel.created_at < window_end,
            )
        )
        return list(result.scalars().all())

    async def create_settlement_period(self, model: SettlementPeriodModel) -> SettlementPeriodModel:
        self._session.add(model)
        await self._session.flush()
        return model

    async def get_settlement_period_by_id(self, settlement_period_id: UUID) -> SettlementPeriodModel | None:
        return await self._session.get(SettlementPeriodModel, settlement_period_id)

    async def list_settlement_periods(
        self,
        *,
        partner_account_id: UUID | None = None,
        period_status: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[SettlementPeriodModel]:
        query = select(SettlementPeriodModel)
        if partner_account_id is not None:
            query = query.where(SettlementPeriodModel.partner_account_id == partner_account_id)
        if period_status is not None:
            query = query.where(SettlementPeriodModel.period_status == period_status)
        query = query.order_by(SettlementPeriodModel.window_start.desc()).offset(offset).limit(limit)
        result = await self._session.execute(query)
        return list(result.scalars().all())

    async def get_settlement_period_by_key(
        self,
        *,
        partner_account_id: UUID,
        period_key: str,
    ) -> SettlementPeriodModel | None:
        result = await self._session.execute(
            select(SettlementPeriodModel).where(
                SettlementPeriodModel.partner_account_id == partner_account_id,
                SettlementPeriodModel.period_key == period_key,
            )
        )
        return result.scalar_one_or_none()

    async def create_partner_statement(self, model: PartnerStatementModel) -> PartnerStatementModel:
        self._session.add(model)
        await self._session.flush()
        return model

    async def create_partner_payout_account(self, model: PartnerPayoutAccountModel) -> PartnerPayoutAccountModel:
        self._session.add(model)
        await self._session.flush()
        return model

    async def get_partner_payout_account_by_id(self, payout_account_id: UUID) -> PartnerPayoutAccountModel | None:
        return await self._session.get(PartnerPayoutAccountModel, payout_account_id)

    async def list_partner_payout_accounts(
        self,
        *,
        partner_account_id: UUID | None = None,
        payout_account_status: str | None = None,
        verification_status: str | None = None,
        approval_status: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[PartnerPayoutAccountModel]:
        query = select(PartnerPayoutAccountModel)
        if partner_account_id is not None:
            query = query.where(PartnerPayoutAccountModel.partner_account_id == partner_account_id)
        if payout_account_status is not None:
            query = query.where(PartnerPayoutAccountModel.account_status == payout_account_status)
        if verification_status is not None:
            query = query.where(PartnerPayoutAccountModel.verification_status == verification_status)
        if approval_status is not None:
            query = query.where(PartnerPayoutAccountModel.approval_status == approval_status)
        query = query.order_by(
            PartnerPayoutAccountModel.is_default.desc(),
            PartnerPayoutAccountModel.created_at.asc(),
        ).offset(offset).limit(limit)
        result = await self._session.execute(query)
        return list(result.scalars().all())

    async def get_partner_statement_by_id(self, statement_id: UUID) -> PartnerStatementModel | None:
        return await self._session.get(PartnerStatementModel, statement_id)

    async def get_partner_payout_account_default(
        self,
        *,
        partner_account_id: UUID,
    ) -> PartnerPayoutAccountModel | None:
        result = await self._session.execute(
            select(PartnerPayoutAccountModel).where(
                PartnerPayoutAccountModel.partner_account_id == partner_account_id,
                PartnerPayoutAccountModel.is_default.is_(True),
            )
        )
        return result.scalar_one_or_none()

    async def list_partner_statements(
        self,
        *,
        partner_account_id: UUID | None = None,
        settlement_period_id: UUID | None = None,
        statement_status: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[PartnerStatementModel]:
        query = select(PartnerStatementModel)
        if partner_account_id is not None:
            query = query.where(PartnerStatementModel.partner_account_id == partner_account_id)
        if settlement_period_id is not None:
            query = query.where(PartnerStatementModel.settlement_period_id == settlement_period_id)
        if statement_status is not None:
            query = query.where(PartnerStatementModel.statement_status == statement_status)
        query = query.order_by(
            PartnerStatementModel.created_at.desc(),
            PartnerStatementModel.statement_version.desc(),
        ).offset(offset).limit(limit)
        result = await self._session.execute(query)
        return list(result.scalars().all())

    async def get_open_partner_statement(
        self,
        *,
        partner_account_id: UUID,
        settlement_period_id: UUID,
    ) -> PartnerStatementModel | None:
        result = await self._session.execute(
            select(PartnerStatementModel).where(
                PartnerStatementModel.partner_account_id == partner_account_id,
                PartnerStatementModel.settlement_period_id == settlement_period_id,
                PartnerStatementModel.statement_status == "open",
                PartnerStatementModel.superseded_by_statement_id.is_(None),
            )
        )
        return result.scalar_one_or_none()

    async def get_latest_open_partner_statement_for_account(
        self,
        *,
        partner_account_id: UUID,
    ) -> PartnerStatementModel | None:
        result = await self._session.execute(
            select(PartnerStatementModel)
            .where(
                PartnerStatementModel.partner_account_id == partner_account_id,
                PartnerStatementModel.statement_status == "open",
                PartnerStatementModel.superseded_by_statement_id.is_(None),
            )
            .order_by(
                PartnerStatementModel.created_at.desc(),
                PartnerStatementModel.statement_version.desc(),
            )
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def list_partner_statements_for_period(
        self,
        *,
        partner_account_id: UUID,
        settlement_period_id: UUID,
    ) -> list[PartnerStatementModel]:
        result = await self._session.execute(
            select(PartnerStatementModel).where(
                PartnerStatementModel.partner_account_id == partner_account_id,
                PartnerStatementModel.settlement_period_id == settlement_period_id,
            )
        )
        return list(result.scalars().all())

    async def create_statement_adjustment(self, model: StatementAdjustmentModel) -> StatementAdjustmentModel:
        self._session.add(model)
        await self._session.flush()
        return model

    async def list_statement_adjustments(
        self,
        *,
        partner_statement_id: UUID,
    ) -> list[StatementAdjustmentModel]:
        result = await self._session.execute(
            select(StatementAdjustmentModel)
            .where(StatementAdjustmentModel.partner_statement_id == partner_statement_id)
            .order_by(StatementAdjustmentModel.created_at.asc())
        )
        return list(result.scalars().all())

    async def list_statement_adjustments_by_source_reference(
        self,
        *,
        source_reference_type: str,
        source_reference_id: UUID,
        adjustment_type: str | None = None,
        adjustment_direction: str | None = None,
    ) -> list[StatementAdjustmentModel]:
        query = select(StatementAdjustmentModel).where(
            StatementAdjustmentModel.source_reference_type == source_reference_type,
            StatementAdjustmentModel.source_reference_id == source_reference_id,
        )
        if adjustment_type is not None:
            query = query.where(StatementAdjustmentModel.adjustment_type == adjustment_type)
        if adjustment_direction is not None:
            query = query.where(StatementAdjustmentModel.adjustment_direction == adjustment_direction)
        query = query.order_by(StatementAdjustmentModel.created_at.asc())
        result = await self._session.execute(query)
        return list(result.scalars().all())

    async def get_statement_adjustment_by_id(self, adjustment_id: UUID) -> StatementAdjustmentModel | None:
        return await self._session.get(StatementAdjustmentModel, adjustment_id)

    async def list_reserves_for_reason(
        self,
        *,
        partner_account_id: UUID,
        reserve_status: str | None = None,
        reserve_scope: str | None = None,
        reserve_reason_type: str | None = None,
        reason_code: str | None = None,
        source_earning_event_id: UUID | None = None,
    ) -> list[ReserveModel]:
        query = select(ReserveModel).where(ReserveModel.partner_account_id == partner_account_id)
        if reserve_status is not None:
            query = query.where(ReserveModel.reserve_status == reserve_status)
        if reserve_scope is not None:
            query = query.where(ReserveModel.reserve_scope == reserve_scope)
        if reserve_reason_type is not None:
            query = query.where(ReserveModel.reserve_reason_type == reserve_reason_type)
        if reason_code is not None:
            query = query.where(ReserveModel.reason_code == reason_code)
        if source_earning_event_id is None:
            query = query.where(ReserveModel.source_earning_event_id.is_(None))
        else:
            query = query.where(ReserveModel.source_earning_event_id == source_earning_event_id)
        query = query.order_by(ReserveModel.created_at.asc())
        result = await self._session.execute(query)
        return list(result.scalars().all())

    async def create_payout_instruction(self, model: PayoutInstructionModel) -> PayoutInstructionModel:
        self._session.add(model)
        await self._session.flush()
        return model

    async def get_payout_instruction_by_id(self, instruction_id: UUID) -> PayoutInstructionModel | None:
        return await self._session.get(PayoutInstructionModel, instruction_id)

    async def get_payout_instruction_by_statement_id(self, partner_statement_id: UUID) -> PayoutInstructionModel | None:
        result = await self._session.execute(
            select(PayoutInstructionModel).where(PayoutInstructionModel.partner_statement_id == partner_statement_id)
        )
        return result.scalar_one_or_none()

    async def list_payout_instructions(
        self,
        *,
        partner_account_id: UUID | None = None,
        partner_statement_id: UUID | None = None,
        instruction_status: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[PayoutInstructionModel]:
        query = select(PayoutInstructionModel)
        if partner_account_id is not None:
            query = query.where(PayoutInstructionModel.partner_account_id == partner_account_id)
        if partner_statement_id is not None:
            query = query.where(PayoutInstructionModel.partner_statement_id == partner_statement_id)
        if instruction_status is not None:
            query = query.where(PayoutInstructionModel.instruction_status == instruction_status)
        query = query.order_by(PayoutInstructionModel.created_at.desc()).offset(offset).limit(limit)
        result = await self._session.execute(query)
        return list(result.scalars().all())

    async def create_payout_execution(self, model: PayoutExecutionModel) -> PayoutExecutionModel:
        self._session.add(model)
        await self._session.flush()
        return model

    async def get_payout_execution_by_id(self, execution_id: UUID) -> PayoutExecutionModel | None:
        return await self._session.get(PayoutExecutionModel, execution_id)

    async def get_payout_execution_by_instruction_and_idempotency_key(
        self,
        *,
        payout_instruction_id: UUID,
        request_idempotency_key: str,
    ) -> PayoutExecutionModel | None:
        result = await self._session.execute(
            select(PayoutExecutionModel).where(
                PayoutExecutionModel.payout_instruction_id == payout_instruction_id,
                PayoutExecutionModel.request_idempotency_key == request_idempotency_key,
            )
        )
        return result.scalar_one_or_none()

    async def list_payout_executions(
        self,
        *,
        payout_instruction_id: UUID | None = None,
        partner_account_id: UUID | None = None,
        partner_statement_id: UUID | None = None,
        execution_status: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[PayoutExecutionModel]:
        query = select(PayoutExecutionModel)
        if payout_instruction_id is not None:
            query = query.where(PayoutExecutionModel.payout_instruction_id == payout_instruction_id)
        if partner_account_id is not None:
            query = query.where(PayoutExecutionModel.partner_account_id == partner_account_id)
        if partner_statement_id is not None:
            query = query.where(PayoutExecutionModel.partner_statement_id == partner_statement_id)
        if execution_status is not None:
            query = query.where(PayoutExecutionModel.execution_status == execution_status)
        query = query.order_by(PayoutExecutionModel.created_at.desc()).offset(offset).limit(limit)
        result = await self._session.execute(query)
        return list(result.scalars().all())

    async def list_payout_executions_for_instruction(
        self,
        *,
        payout_instruction_id: UUID,
    ) -> list[PayoutExecutionModel]:
        result = await self._session.execute(
            select(PayoutExecutionModel)
            .where(PayoutExecutionModel.payout_instruction_id == payout_instruction_id)
            .order_by(PayoutExecutionModel.created_at.asc())
        )
        return list(result.scalars().all())

    async def flush(self) -> None:
        await self._session.flush()
