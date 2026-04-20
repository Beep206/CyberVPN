from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.application.use_cases.settlement.partner_payout_accounts import (
    EvaluatePartnerPayoutAccountEligibilityUseCase,
)
from src.domain.enums import (
    PartnerStatementStatus,
    PayoutExecutionMode,
    PayoutExecutionStatus,
    PayoutInstructionStatus,
)
from src.infrastructure.database.models.payout_execution_model import PayoutExecutionModel
from src.infrastructure.database.models.payout_instruction_model import PayoutInstructionModel
from src.infrastructure.database.repositories.settlement_repo import SettlementRepository

_ACTIVE_PAYOUT_EXECUTION_STATUSES = {
    PayoutExecutionStatus.REQUESTED.value,
    PayoutExecutionStatus.SUBMITTED.value,
}
_TERMINAL_PAYOUT_EXECUTION_STATUSES = {
    PayoutExecutionStatus.SUCCEEDED.value,
    PayoutExecutionStatus.FAILED.value,
    PayoutExecutionStatus.RECONCILED.value,
    PayoutExecutionStatus.CANCELLED.value,
}


@dataclass(frozen=True)
class CreatePayoutInstructionResult:
    payout_instruction: PayoutInstructionModel
    created: bool


@dataclass(frozen=True)
class CreatePayoutExecutionResult:
    payout_execution: PayoutExecutionModel
    created: bool


class CreatePayoutInstructionUseCase:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._settlement = SettlementRepository(session)
        self._eligibility = EvaluatePartnerPayoutAccountEligibilityUseCase(session)

    async def execute(
        self,
        *,
        partner_statement_id: UUID,
        partner_payout_account_id: UUID | None,
        created_by_admin_user_id: UUID | None,
    ) -> CreatePayoutInstructionResult:
        statement = await self._settlement.get_partner_statement_by_id(partner_statement_id)
        if statement is None:
            raise ValueError("Partner statement not found")
        if statement.statement_status != PartnerStatementStatus.CLOSED.value:
            raise ValueError("Payout instructions may only be created from closed statements")
        if statement.superseded_by_statement_id is not None:
            raise ValueError("Payout instructions may only be created from the latest closed statement version")
        if float(statement.available_amount) <= 0:
            raise ValueError("Partner statement has no available payout amount")

        existing = await self._settlement.get_payout_instruction_by_statement_id(statement.id)
        if existing is not None:
            return CreatePayoutInstructionResult(payout_instruction=existing, created=False)

        payout_account = await self._resolve_payout_account(
            partner_account_id=statement.partner_account_id,
            partner_payout_account_id=partner_payout_account_id,
        )

        eligibility = await self._eligibility.execute(payout_account_id=payout_account.id)
        if not eligibility.eligible:
            raise ValueError(
                "Partner payout account is not eligible: " + ", ".join(eligibility.reason_codes),
            )

        instruction = PayoutInstructionModel(
            partner_account_id=statement.partner_account_id,
            partner_statement_id=statement.id,
            partner_payout_account_id=payout_account.id,
            instruction_key=f"statement:{statement.id}",
            instruction_status=PayoutInstructionStatus.PENDING_APPROVAL.value,
            payout_amount=float(statement.available_amount),
            currency_code=statement.currency_code.upper(),
            instruction_snapshot=_build_instruction_snapshot(statement=statement, payout_account=payout_account),
            created_by_admin_user_id=created_by_admin_user_id,
        )
        created = await self._settlement.create_payout_instruction(instruction)
        await self._session.commit()
        await self._session.refresh(created)
        return CreatePayoutInstructionResult(payout_instruction=created, created=True)

    async def _resolve_payout_account(
        self,
        *,
        partner_account_id: UUID,
        partner_payout_account_id: UUID | None,
    ):
        if partner_payout_account_id is not None:
            payout_account = await self._settlement.get_partner_payout_account_by_id(partner_payout_account_id)
            if payout_account is None:
                raise ValueError("Partner payout account not found")
            if payout_account.partner_account_id != partner_account_id:
                raise ValueError("Partner payout account does not belong to the statement workspace")
            return payout_account

        payout_account = await self._settlement.get_partner_payout_account_default(
            partner_account_id=partner_account_id,
        )
        if payout_account is None:
            raise ValueError("Default partner payout account not found")
        return payout_account


class ListPayoutInstructionsUseCase:
    def __init__(self, session: AsyncSession) -> None:
        self._settlement = SettlementRepository(session)

    async def execute(
        self,
        *,
        partner_account_id: UUID | None = None,
        partner_statement_id: UUID | None = None,
        instruction_status: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[PayoutInstructionModel]:
        return await self._settlement.list_payout_instructions(
            partner_account_id=partner_account_id,
            partner_statement_id=partner_statement_id,
            instruction_status=instruction_status,
            limit=limit,
            offset=offset,
        )


class GetPayoutInstructionUseCase:
    def __init__(self, session: AsyncSession) -> None:
        self._settlement = SettlementRepository(session)

    async def execute(self, *, payout_instruction_id: UUID) -> PayoutInstructionModel | None:
        return await self._settlement.get_payout_instruction_by_id(payout_instruction_id)


class ApprovePayoutInstructionUseCase:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._settlement = SettlementRepository(session)

    async def execute(
        self,
        *,
        payout_instruction_id: UUID,
        approved_by_admin_user_id: UUID,
    ) -> PayoutInstructionModel:
        instruction = await self._settlement.get_payout_instruction_by_id(payout_instruction_id)
        if instruction is None:
            raise ValueError("Payout instruction not found")
        if instruction.instruction_status == PayoutInstructionStatus.COMPLETED.value:
            raise ValueError("Completed payout instructions cannot be approved again")
        if instruction.instruction_status == PayoutInstructionStatus.REJECTED.value:
            raise ValueError("Rejected payout instructions cannot be approved")
        if instruction.instruction_status == PayoutInstructionStatus.APPROVED.value:
            return instruction
        if instruction.created_by_admin_user_id == approved_by_admin_user_id:
            raise ValueError("Maker-checker approval requires a different admin user")

        instruction.instruction_status = PayoutInstructionStatus.APPROVED.value
        instruction.approved_by_admin_user_id = approved_by_admin_user_id
        instruction.approved_at = datetime.now(UTC)
        await self._session.commit()
        await self._session.refresh(instruction)
        return instruction


class RejectPayoutInstructionUseCase:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._settlement = SettlementRepository(session)

    async def execute(
        self,
        *,
        payout_instruction_id: UUID,
        rejected_by_admin_user_id: UUID,
        rejection_reason_code: str,
    ) -> PayoutInstructionModel:
        instruction = await self._settlement.get_payout_instruction_by_id(payout_instruction_id)
        if instruction is None:
            raise ValueError("Payout instruction not found")
        if not rejection_reason_code.strip():
            raise ValueError("rejection_reason_code is required")
        if instruction.instruction_status == PayoutInstructionStatus.COMPLETED.value:
            raise ValueError("Completed payout instructions cannot be rejected")
        if instruction.instruction_status == PayoutInstructionStatus.APPROVED.value:
            raise ValueError("Approved payout instructions cannot be rejected")
        if instruction.instruction_status == PayoutInstructionStatus.REJECTED.value:
            return instruction
        if instruction.created_by_admin_user_id == rejected_by_admin_user_id:
            raise ValueError("Maker-checker rejection requires a different admin user")

        instruction.instruction_status = PayoutInstructionStatus.REJECTED.value
        instruction.rejected_by_admin_user_id = rejected_by_admin_user_id
        instruction.rejected_at = datetime.now(UTC)
        instruction.rejection_reason_code = rejection_reason_code.strip()
        await self._session.commit()
        await self._session.refresh(instruction)
        return instruction


class CreatePayoutExecutionUseCase:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._settlement = SettlementRepository(session)
        self._eligibility = EvaluatePartnerPayoutAccountEligibilityUseCase(session)

    async def execute(
        self,
        *,
        payout_instruction_id: UUID,
        execution_mode: str,
        request_idempotency_key: str,
        execution_payload: dict | None,
        requested_by_admin_user_id: UUID | None,
    ) -> CreatePayoutExecutionResult:
        instruction = await self._settlement.get_payout_instruction_by_id(payout_instruction_id)
        if instruction is None:
            raise ValueError("Payout instruction not found")
        if instruction.instruction_status != PayoutInstructionStatus.APPROVED.value:
            raise ValueError("Payout executions require an approved payout instruction")
        if execution_mode not in {member.value for member in PayoutExecutionMode}:
            raise ValueError("Unsupported payout execution mode")
        normalized_idempotency_key = request_idempotency_key.strip()
        if not normalized_idempotency_key:
            raise ValueError("Idempotency-Key is required")

        existing = await self._settlement.get_payout_execution_by_instruction_and_idempotency_key(
            payout_instruction_id=payout_instruction_id,
            request_idempotency_key=normalized_idempotency_key,
        )
        if existing is not None:
            return CreatePayoutExecutionResult(payout_execution=existing, created=False)

        payout_account = await self._settlement.get_partner_payout_account_by_id(instruction.partner_payout_account_id)
        if payout_account is None:
            raise ValueError("Partner payout account not found")
        eligibility = await self._eligibility.execute(payout_account_id=payout_account.id)
        if not eligibility.eligible:
            raise ValueError(
                "Partner payout account is not eligible: " + ", ".join(eligibility.reason_codes),
            )

        for execution in await self._settlement.list_payout_executions_for_instruction(
            payout_instruction_id=payout_instruction_id
        ):
            if execution.execution_status in _ACTIVE_PAYOUT_EXECUTION_STATUSES:
                raise ValueError("An active payout execution already exists for this instruction")

        sequence = len(
            await self._settlement.list_payout_executions_for_instruction(
                payout_instruction_id=payout_instruction_id,
            )
        ) + 1
        execution = PayoutExecutionModel(
            payout_instruction_id=instruction.id,
            partner_account_id=instruction.partner_account_id,
            partner_statement_id=instruction.partner_statement_id,
            partner_payout_account_id=instruction.partner_payout_account_id,
            execution_key=f"{instruction.instruction_key}:execution:{sequence}",
            execution_mode=execution_mode,
            execution_status=PayoutExecutionStatus.REQUESTED.value,
            request_idempotency_key=normalized_idempotency_key,
            execution_payload=dict(execution_payload or {}),
            result_payload={
                "instruction_status_at_request": instruction.instruction_status,
                "execution_mode": execution_mode,
            },
            requested_by_admin_user_id=requested_by_admin_user_id,
        )
        created = await self._settlement.create_payout_execution(execution)
        await self._session.commit()
        await self._session.refresh(created)
        return CreatePayoutExecutionResult(payout_execution=created, created=True)


class ListPayoutExecutionsUseCase:
    def __init__(self, session: AsyncSession) -> None:
        self._settlement = SettlementRepository(session)

    async def execute(
        self,
        *,
        payout_instruction_id: UUID | None = None,
        partner_account_id: UUID | None = None,
        partner_statement_id: UUID | None = None,
        execution_status: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[PayoutExecutionModel]:
        return await self._settlement.list_payout_executions(
            payout_instruction_id=payout_instruction_id,
            partner_account_id=partner_account_id,
            partner_statement_id=partner_statement_id,
            execution_status=execution_status,
            limit=limit,
            offset=offset,
        )


class GetPayoutExecutionUseCase:
    def __init__(self, session: AsyncSession) -> None:
        self._settlement = SettlementRepository(session)

    async def execute(self, *, payout_execution_id: UUID) -> PayoutExecutionModel | None:
        return await self._settlement.get_payout_execution_by_id(payout_execution_id)


class SubmitPayoutExecutionUseCase:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._settlement = SettlementRepository(session)

    async def execute(
        self,
        *,
        payout_execution_id: UUID,
        submitted_by_admin_user_id: UUID,
        external_reference: str | None,
        submission_payload: dict | None,
    ) -> PayoutExecutionModel:
        execution = await self._settlement.get_payout_execution_by_id(payout_execution_id)
        if execution is None:
            raise ValueError("Payout execution not found")
        if execution.execution_status == PayoutExecutionStatus.SUBMITTED.value:
            return execution
        if execution.execution_status != PayoutExecutionStatus.REQUESTED.value:
            raise ValueError("Only requested payout executions may be submitted")

        execution.execution_status = PayoutExecutionStatus.SUBMITTED.value
        execution.submitted_by_admin_user_id = submitted_by_admin_user_id
        execution.submitted_at = datetime.now(UTC)
        if external_reference:
            execution.external_reference = external_reference.strip()
        execution.result_payload = {
            **dict(execution.result_payload or {}),
            "submission_payload": dict(submission_payload or {}),
        }
        await self._session.commit()
        await self._session.refresh(execution)
        return execution


class CompletePayoutExecutionUseCase:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._settlement = SettlementRepository(session)

    async def execute(
        self,
        *,
        payout_execution_id: UUID,
        completed_by_admin_user_id: UUID,
        external_reference: str | None,
        completion_payload: dict | None,
    ) -> PayoutExecutionModel:
        execution = await self._settlement.get_payout_execution_by_id(payout_execution_id)
        if execution is None:
            raise ValueError("Payout execution not found")
        if execution.execution_status == PayoutExecutionStatus.SUCCEEDED.value:
            return execution
        if execution.execution_status == PayoutExecutionStatus.RECONCILED.value:
            raise ValueError("Reconciled payout executions cannot be completed again")
        allowed_statuses = {
            PayoutExecutionStatus.REQUESTED.value,
            PayoutExecutionStatus.SUBMITTED.value,
        }
        if execution.execution_status not in allowed_statuses:
            raise ValueError("Only requested or submitted payout executions may be completed")
        if (
            execution.execution_mode == PayoutExecutionMode.LIVE.value
            and execution.execution_status != PayoutExecutionStatus.SUBMITTED.value
        ):
            raise ValueError("Live payout executions must be submitted before completion")

        execution.execution_status = PayoutExecutionStatus.SUCCEEDED.value
        execution.completed_by_admin_user_id = completed_by_admin_user_id
        execution.completed_at = datetime.now(UTC)
        if external_reference:
            execution.external_reference = external_reference.strip()
        execution.result_payload = {
            **dict(execution.result_payload or {}),
            "completion_payload": dict(completion_payload or {}),
        }
        await self._session.commit()
        await self._session.refresh(execution)
        return execution


class FailPayoutExecutionUseCase:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._settlement = SettlementRepository(session)

    async def execute(
        self,
        *,
        payout_execution_id: UUID,
        failure_reason_code: str,
        failure_payload: dict | None,
    ) -> PayoutExecutionModel:
        execution = await self._settlement.get_payout_execution_by_id(payout_execution_id)
        if execution is None:
            raise ValueError("Payout execution not found")
        if execution.execution_status == PayoutExecutionStatus.FAILED.value:
            return execution
        if execution.execution_status in {
            PayoutExecutionStatus.RECONCILED.value,
            PayoutExecutionStatus.CANCELLED.value,
        }:
            raise ValueError("Terminal payout executions cannot be failed")
        if not failure_reason_code.strip():
            raise ValueError("failure_reason_code is required")

        execution.execution_status = PayoutExecutionStatus.FAILED.value
        execution.failure_reason_code = failure_reason_code.strip()
        execution.result_payload = {
            **dict(execution.result_payload or {}),
            "failure_payload": dict(failure_payload or {}),
        }
        await self._session.commit()
        await self._session.refresh(execution)
        return execution


class ReconcilePayoutExecutionUseCase:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._settlement = SettlementRepository(session)

    async def execute(
        self,
        *,
        payout_execution_id: UUID,
        reconciled_by_admin_user_id: UUID,
        reconciliation_payload: dict | None,
    ) -> PayoutExecutionModel:
        execution = await self._settlement.get_payout_execution_by_id(payout_execution_id)
        if execution is None:
            raise ValueError("Payout execution not found")
        if execution.execution_status == PayoutExecutionStatus.RECONCILED.value:
            return execution
        if execution.execution_status != PayoutExecutionStatus.SUCCEEDED.value:
            raise ValueError("Only succeeded payout executions may be reconciled")

        execution.execution_status = PayoutExecutionStatus.RECONCILED.value
        execution.reconciled_by_admin_user_id = reconciled_by_admin_user_id
        execution.reconciled_at = datetime.now(UTC)
        execution.result_payload = {
            **dict(execution.result_payload or {}),
            "reconciliation_payload": dict(reconciliation_payload or {}),
        }

        instruction = await self._settlement.get_payout_instruction_by_id(execution.payout_instruction_id)
        if instruction is None:
            raise ValueError("Payout instruction not found")
        if execution.execution_mode == PayoutExecutionMode.LIVE.value:
            instruction.instruction_status = PayoutInstructionStatus.COMPLETED.value
            instruction.completed_at = execution.reconciled_at

        await self._session.commit()
        await self._session.refresh(execution)
        return execution


def _build_instruction_snapshot(*, statement, payout_account) -> dict:
    return {
        "statement": {
            "statement_id": str(statement.id),
            "statement_key": statement.statement_key,
            "statement_version": statement.statement_version,
            "currency_code": statement.currency_code,
            "available_amount": float(statement.available_amount),
            "statement_snapshot": dict(statement.statement_snapshot or {}),
        },
        "partner_payout_account": {
            "partner_payout_account_id": str(payout_account.id),
            "payout_rail": payout_account.payout_rail,
            "display_label": payout_account.display_label,
            "masked_destination": payout_account.masked_destination,
        },
    }
