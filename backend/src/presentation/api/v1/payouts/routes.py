from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.use_cases.settlement import (
    ApprovePayoutInstructionUseCase,
    CompletePayoutExecutionUseCase,
    CreatePayoutExecutionUseCase,
    CreatePayoutInstructionUseCase,
    FailPayoutExecutionUseCase,
    GetPayoutExecutionUseCase,
    GetPayoutInstructionUseCase,
    ListPayoutExecutionsUseCase,
    ListPayoutInstructionsUseCase,
    ReconcilePayoutExecutionUseCase,
    RejectPayoutInstructionUseCase,
    SubmitPayoutExecutionUseCase,
)
from src.domain.enums import AdminRole, PayoutExecutionStatus, PayoutInstructionStatus
from src.infrastructure.database.models.admin_user_model import AdminUserModel
from src.presentation.dependencies.database import get_db
from src.presentation.dependencies.roles import require_role

from .schemas import (
    CompletePayoutExecutionRequest,
    CreatePayoutExecutionRequest,
    CreatePayoutInstructionRequest,
    FailPayoutExecutionRequest,
    PayoutExecutionResponse,
    PayoutInstructionResponse,
    ReconcilePayoutExecutionRequest,
    RejectPayoutInstructionRequest,
    SubmitPayoutExecutionRequest,
)

router = APIRouter(prefix="/payouts", tags=["payouts"])


def _serialize_instruction(model) -> PayoutInstructionResponse:
    return PayoutInstructionResponse(
        id=model.id,
        partner_account_id=model.partner_account_id,
        partner_statement_id=model.partner_statement_id,
        partner_payout_account_id=model.partner_payout_account_id,
        instruction_key=model.instruction_key,
        instruction_status=model.instruction_status,
        payout_amount=float(model.payout_amount),
        currency_code=model.currency_code,
        instruction_snapshot=dict(model.instruction_snapshot or {}),
        created_by_admin_user_id=model.created_by_admin_user_id,
        approved_by_admin_user_id=model.approved_by_admin_user_id,
        approved_at=model.approved_at,
        rejected_by_admin_user_id=model.rejected_by_admin_user_id,
        rejected_at=model.rejected_at,
        rejection_reason_code=model.rejection_reason_code,
        completed_at=model.completed_at,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


def _serialize_execution(model) -> PayoutExecutionResponse:
    return PayoutExecutionResponse(
        id=model.id,
        payout_instruction_id=model.payout_instruction_id,
        partner_account_id=model.partner_account_id,
        partner_statement_id=model.partner_statement_id,
        partner_payout_account_id=model.partner_payout_account_id,
        execution_key=model.execution_key,
        execution_mode=model.execution_mode,
        execution_status=model.execution_status,
        request_idempotency_key=model.request_idempotency_key,
        external_reference=model.external_reference,
        execution_payload=dict(model.execution_payload or {}),
        result_payload=dict(model.result_payload or {}),
        requested_by_admin_user_id=model.requested_by_admin_user_id,
        submitted_by_admin_user_id=model.submitted_by_admin_user_id,
        submitted_at=model.submitted_at,
        completed_by_admin_user_id=model.completed_by_admin_user_id,
        completed_at=model.completed_at,
        reconciled_by_admin_user_id=model.reconciled_by_admin_user_id,
        reconciled_at=model.reconciled_at,
        failure_reason_code=model.failure_reason_code,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


@router.post("/instructions", response_model=PayoutInstructionResponse, status_code=status.HTTP_201_CREATED)
async def create_payout_instruction(
    payload: CreatePayoutInstructionRequest,
    http_response: Response,
    db: AsyncSession = Depends(get_db),
    current_admin: AdminUserModel = Depends(require_role(AdminRole.ADMIN)),
) -> PayoutInstructionResponse:
    try:
        result = await CreatePayoutInstructionUseCase(db).execute(
            partner_statement_id=payload.partner_statement_id,
            partner_payout_account_id=payload.partner_payout_account_id,
            created_by_admin_user_id=current_admin.id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    if not result.created:
        http_response.status_code = status.HTTP_200_OK
    return _serialize_instruction(result.payout_instruction)


@router.get("/instructions", response_model=list[PayoutInstructionResponse])
async def list_payout_instructions(
    partner_account_id: UUID | None = Query(None),
    partner_statement_id: UUID | None = Query(None),
    instruction_status: PayoutInstructionStatus | None = Query(None),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    _current_admin: AdminUserModel = Depends(require_role(AdminRole.SUPPORT)),
) -> list[PayoutInstructionResponse]:
    items = await ListPayoutInstructionsUseCase(db).execute(
        partner_account_id=partner_account_id,
        partner_statement_id=partner_statement_id,
        instruction_status=instruction_status.value if instruction_status else None,
        limit=limit,
        offset=offset,
    )
    return [_serialize_instruction(item) for item in items]


@router.get("/instructions/{payout_instruction_id}", response_model=PayoutInstructionResponse)
async def get_payout_instruction(
    payout_instruction_id: UUID,
    db: AsyncSession = Depends(get_db),
    _current_admin: AdminUserModel = Depends(require_role(AdminRole.SUPPORT)),
) -> PayoutInstructionResponse:
    item = await GetPayoutInstructionUseCase(db).execute(payout_instruction_id=payout_instruction_id)
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Payout instruction not found")
    return _serialize_instruction(item)


@router.post("/instructions/{payout_instruction_id}/approve", response_model=PayoutInstructionResponse)
async def approve_payout_instruction(
    payout_instruction_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_admin: AdminUserModel = Depends(require_role(AdminRole.ADMIN)),
) -> PayoutInstructionResponse:
    try:
        item = await ApprovePayoutInstructionUseCase(db).execute(
            payout_instruction_id=payout_instruction_id,
            approved_by_admin_user_id=current_admin.id,
        )
    except ValueError as exc:
        detail = str(exc)
        status_code = status.HTTP_409_CONFLICT if "Maker-checker" in detail else status.HTTP_400_BAD_REQUEST
        raise HTTPException(status_code=status_code, detail=detail) from exc
    return _serialize_instruction(item)


@router.post("/instructions/{payout_instruction_id}/reject", response_model=PayoutInstructionResponse)
async def reject_payout_instruction(
    payout_instruction_id: UUID,
    payload: RejectPayoutInstructionRequest,
    db: AsyncSession = Depends(get_db),
    current_admin: AdminUserModel = Depends(require_role(AdminRole.ADMIN)),
) -> PayoutInstructionResponse:
    try:
        item = await RejectPayoutInstructionUseCase(db).execute(
            payout_instruction_id=payout_instruction_id,
            rejected_by_admin_user_id=current_admin.id,
            rejection_reason_code=payload.rejection_reason_code,
        )
    except ValueError as exc:
        detail = str(exc)
        status_code = status.HTTP_409_CONFLICT if "Maker-checker" in detail else status.HTTP_400_BAD_REQUEST
        raise HTTPException(status_code=status_code, detail=detail) from exc
    return _serialize_instruction(item)


@router.post("/executions", response_model=PayoutExecutionResponse, status_code=status.HTTP_201_CREATED)
async def create_payout_execution(
    payload: CreatePayoutExecutionRequest,
    http_response: Response,
    db: AsyncSession = Depends(get_db),
    current_admin: AdminUserModel = Depends(require_role(AdminRole.ADMIN)),
    idempotency_key: str = Header(..., alias="Idempotency-Key", min_length=1, max_length=120),
) -> PayoutExecutionResponse:
    try:
        result = await CreatePayoutExecutionUseCase(db).execute(
            payout_instruction_id=payload.payout_instruction_id,
            execution_mode=payload.execution_mode.value,
            request_idempotency_key=idempotency_key,
            execution_payload=payload.execution_payload,
            requested_by_admin_user_id=current_admin.id,
        )
    except ValueError as exc:
        detail = str(exc)
        status_code = status.HTTP_409_CONFLICT if "active payout execution" in detail else status.HTTP_400_BAD_REQUEST
        raise HTTPException(status_code=status_code, detail=detail) from exc
    if not result.created:
        http_response.status_code = status.HTTP_200_OK
    return _serialize_execution(result.payout_execution)


@router.get("/executions", response_model=list[PayoutExecutionResponse])
async def list_payout_executions(
    payout_instruction_id: UUID | None = Query(None),
    partner_account_id: UUID | None = Query(None),
    partner_statement_id: UUID | None = Query(None),
    execution_status: PayoutExecutionStatus | None = Query(None),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    _current_admin: AdminUserModel = Depends(require_role(AdminRole.SUPPORT)),
) -> list[PayoutExecutionResponse]:
    items = await ListPayoutExecutionsUseCase(db).execute(
        payout_instruction_id=payout_instruction_id,
        partner_account_id=partner_account_id,
        partner_statement_id=partner_statement_id,
        execution_status=execution_status.value if execution_status else None,
        limit=limit,
        offset=offset,
    )
    return [_serialize_execution(item) for item in items]


@router.get("/executions/{payout_execution_id}", response_model=PayoutExecutionResponse)
async def get_payout_execution(
    payout_execution_id: UUID,
    db: AsyncSession = Depends(get_db),
    _current_admin: AdminUserModel = Depends(require_role(AdminRole.SUPPORT)),
) -> PayoutExecutionResponse:
    item = await GetPayoutExecutionUseCase(db).execute(payout_execution_id=payout_execution_id)
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Payout execution not found")
    return _serialize_execution(item)


@router.post("/executions/{payout_execution_id}/submit", response_model=PayoutExecutionResponse)
async def submit_payout_execution(
    payout_execution_id: UUID,
    payload: SubmitPayoutExecutionRequest,
    db: AsyncSession = Depends(get_db),
    current_admin: AdminUserModel = Depends(require_role(AdminRole.ADMIN)),
) -> PayoutExecutionResponse:
    try:
        item = await SubmitPayoutExecutionUseCase(db).execute(
            payout_execution_id=payout_execution_id,
            submitted_by_admin_user_id=current_admin.id,
            external_reference=payload.external_reference,
            submission_payload=payload.submission_payload,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return _serialize_execution(item)


@router.post("/executions/{payout_execution_id}/complete", response_model=PayoutExecutionResponse)
async def complete_payout_execution(
    payout_execution_id: UUID,
    payload: CompletePayoutExecutionRequest,
    db: AsyncSession = Depends(get_db),
    current_admin: AdminUserModel = Depends(require_role(AdminRole.ADMIN)),
) -> PayoutExecutionResponse:
    try:
        item = await CompletePayoutExecutionUseCase(db).execute(
            payout_execution_id=payout_execution_id,
            completed_by_admin_user_id=current_admin.id,
            external_reference=payload.external_reference,
            completion_payload=payload.completion_payload,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return _serialize_execution(item)


@router.post("/executions/{payout_execution_id}/fail", response_model=PayoutExecutionResponse)
async def fail_payout_execution(
    payout_execution_id: UUID,
    payload: FailPayoutExecutionRequest,
    db: AsyncSession = Depends(get_db),
    _current_admin: AdminUserModel = Depends(require_role(AdminRole.ADMIN)),
) -> PayoutExecutionResponse:
    try:
        item = await FailPayoutExecutionUseCase(db).execute(
            payout_execution_id=payout_execution_id,
            failure_reason_code=payload.failure_reason_code,
            failure_payload=payload.failure_payload,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return _serialize_execution(item)


@router.post("/executions/{payout_execution_id}/reconcile", response_model=PayoutExecutionResponse)
async def reconcile_payout_execution(
    payout_execution_id: UUID,
    payload: ReconcilePayoutExecutionRequest,
    db: AsyncSession = Depends(get_db),
    current_admin: AdminUserModel = Depends(require_role(AdminRole.ADMIN)),
) -> PayoutExecutionResponse:
    try:
        item = await ReconcilePayoutExecutionUseCase(db).execute(
            payout_execution_id=payout_execution_id,
            reconciled_by_admin_user_id=current_admin.id,
            reconciliation_payload=payload.reconciliation_payload,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return _serialize_execution(item)
