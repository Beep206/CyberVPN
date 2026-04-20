from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.application.use_cases.settlement._statement_snapshot import build_statement_snapshot
from src.domain.enums import PartnerStatementStatus, StatementAdjustmentDirection, StatementAdjustmentType
from src.infrastructure.database.models.statement_adjustment_model import StatementAdjustmentModel
from src.infrastructure.database.repositories.settlement_repo import SettlementRepository

from .partner_statements import _apply_snapshot


class CreateStatementAdjustmentUseCase:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._settlement = SettlementRepository(session)

    async def execute(
        self,
        *,
        partner_statement_id: UUID,
        adjustment_type: str,
        adjustment_direction: str,
        amount: float,
        currency_code: str,
        reason_code: str | None,
        adjustment_payload: dict | None,
        source_reference_type: str | None,
        source_reference_id: UUID | None,
        created_by_admin_user_id: UUID | None,
    ) -> StatementAdjustmentModel:
        if adjustment_type not in {member.value for member in StatementAdjustmentType}:
            raise ValueError("Unsupported statement adjustment type")
        if adjustment_direction not in {member.value for member in StatementAdjustmentDirection}:
            raise ValueError("Unsupported statement adjustment direction")
        if amount <= 0:
            raise ValueError("amount must be greater than zero")

        statement = await self._settlement.get_partner_statement_by_id(partner_statement_id)
        if statement is None:
            raise ValueError("Partner statement not found")
        if statement.statement_status != PartnerStatementStatus.OPEN.value:
            raise ValueError("Adjustments may only be added to open statements")

        adjustment = StatementAdjustmentModel(
            partner_statement_id=statement.id,
            partner_account_id=statement.partner_account_id,
            source_reference_type=source_reference_type,
            source_reference_id=source_reference_id,
            adjustment_type=adjustment_type,
            adjustment_direction=adjustment_direction,
            amount=amount,
            currency_code=currency_code.upper(),
            reason_code=reason_code,
            adjustment_payload=dict(adjustment_payload or {}),
            created_by_admin_user_id=created_by_admin_user_id,
        )
        created = await self._settlement.create_statement_adjustment(adjustment)
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
        await self._session.commit()
        await self._session.refresh(created)
        return created


class ListStatementAdjustmentsUseCase:
    def __init__(self, session: AsyncSession) -> None:
        self._settlement = SettlementRepository(session)

    async def execute(self, *, partner_statement_id: UUID) -> list[StatementAdjustmentModel]:
        return await self._settlement.list_statement_adjustments(partner_statement_id=partner_statement_id)
