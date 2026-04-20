"""Canonical admin inspection routes for customer-linked operations context."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.use_cases.attribution import GetOrderAttributionResultUseCase
from src.application.use_cases.auth.permissions import Permission, check_minimum_role, has_permission
from src.application.use_cases.governance import ListDisputeCasesUseCase
from src.application.use_cases.orders.explainability import GetOrderExplainabilityUseCase
from src.application.use_cases.payment_disputes import ListPaymentDisputesUseCase
from src.application.use_cases.service_access import (
    GetServiceAccessObservabilityUseCase,
    ListServiceIdentitiesUseCase,
)
from src.application.use_cases.settlement import (
    ApprovePayoutInstructionUseCase,
    GetPartnerPayoutAccountUseCase,
    GetPartnerStatementUseCase,
    GetPayoutExecutionUseCase,
    GetPayoutInstructionUseCase,
    ListPartnerPayoutAccountsUseCase,
    ListPartnerStatementsUseCase,
    ListPayoutExecutionsUseCase,
    ListPayoutInstructionsUseCase,
    ListStatementAdjustmentsUseCase,
    RejectPayoutInstructionUseCase,
    SuspendPartnerPayoutAccountUseCase,
    VerifyPartnerPayoutAccountUseCase,
)
from src.domain.enums import AdminRole, PrincipalClass
from src.infrastructure.database.models.admin_user_model import AdminUserModel
from src.infrastructure.database.repositories.mobile_user_repo import MobileUserRepository
from src.infrastructure.database.repositories.order_repo import OrderRepository
from src.infrastructure.database.repositories.risk_subject_repo import RiskSubjectGraphRepository
from src.infrastructure.monitoring.metrics import route_operations_total
from src.presentation.api.v1.attribution.routes import _serialize_order_attribution_result
from src.presentation.api.v1.dispute_cases.schemas import DisputeCaseResponse
from src.presentation.api.v1.orders.explainability.routes import (
    _serialize_evaluation,
    _serialize_order_summary,
)
from src.presentation.api.v1.partner_payout_accounts.routes import _serialize_payout_account
from src.presentation.api.v1.partner_statements.routes import _serialize_adjustment, _serialize_statement
from src.presentation.api.v1.payment_disputes.routes import _serialize_payment_dispute
from src.presentation.api.v1.payouts.routes import _serialize_execution, _serialize_instruction
from src.presentation.api.v1.security.schemas import RiskReviewResponse, RiskSubjectResponse
from src.presentation.api.v1.service_identities.routes import (
    _build_service_access_observability_response,
    _serialize_service_identity,
)
from src.presentation.dependencies.auth import get_current_active_user
from src.presentation.dependencies.database import get_db
from src.presentation.dependencies.roles import require_permission, require_role

from .customer_operations_schemas import (
    AdminCustomerOperationsActionKind,
    AdminCustomerOperationsActionRequest,
    AdminCustomerOperationsActionResponse,
    AdminCustomerOperationsExportKind,
    AdminCustomerOperationsExportResponse,
    AdminCustomerOperationsInsightResponse,
    AdminCustomerOperationsSectionAccessResponse,
    AdminCustomerOrderInsightResponse,
    AdminCustomerRiskSubjectInsightResponse,
    AdminCustomerServiceAccessInsightResponse,
    AdminCustomerSettlementWorkspaceInsightResponse,
)

router = APIRouter(prefix="/admin/mobile-users", tags=["admin", "customer-operations"])

_ORDER_LIMIT = 12
_SETTLEMENT_LIMIT = 12
_SERVICE_IDENTITY_LIMIT = 12


def _parse_uuid_or_none(value: object) -> UUID | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        return UUID(value)
    except ValueError:
        return None


def _resolve_payout_account_actions(model) -> list[AdminCustomerOperationsActionKind]:
    actions: list[AdminCustomerOperationsActionKind] = []
    if model.account_status == "archived":
        return actions
    if model.verification_status != "verified" or model.approval_status != "approved":
        actions.append(AdminCustomerOperationsActionKind.VERIFY_PAYOUT_ACCOUNT)
    if model.account_status == "active":
        actions.append(AdminCustomerOperationsActionKind.SUSPEND_PAYOUT_ACCOUNT)
    return actions


def _resolve_payout_instruction_actions(model) -> list[AdminCustomerOperationsActionKind]:
    if model.instruction_status != "pending_approval":
        return []
    return [
        AdminCustomerOperationsActionKind.APPROVE_PAYOUT_INSTRUCTION,
        AdminCustomerOperationsActionKind.REJECT_PAYOUT_INSTRUCTION,
    ]


async def _collect_customer_partner_account_ids(
    *,
    user_id: UUID,
    db: AsyncSession,
) -> list[UUID]:
    order_repo = OrderRepository(db)
    orders = await order_repo.list_for_user(user_id=user_id, limit=_ORDER_LIMIT, offset=0)
    explainability_use_case = GetOrderExplainabilityUseCase(db)
    attribution_use_case = GetOrderAttributionResultUseCase(db)

    partner_account_ids: list[UUID] = []
    for order in orders:
        explainability_result = await explainability_use_case.execute(order_id=order.id)
        attribution_result = await attribution_use_case.execute(order_id=order.id)
        resolved_partner_account_id = _parse_uuid_or_none(
            (
                explainability_result.explainability_payload.get("commercial_resolution_summary", {})
                or {}
            ).get("resolved_partner_account_id"),
        )
        if resolved_partner_account_id is None and attribution_result is not None:
            resolved_partner_account_id = attribution_result.partner_account_id
        if (
            resolved_partner_account_id is not None
            and resolved_partner_account_id not in partner_account_ids
        ):
            partner_account_ids.append(resolved_partner_account_id)
    return partner_account_ids


async def _collect_customer_order_insights(
    *,
    user_id: UUID,
    finance_visible: bool,
    db: AsyncSession,
) -> tuple[list[AdminCustomerOrderInsightResponse], list[UUID]]:
    order_repo = OrderRepository(db)
    orders = await order_repo.list_for_user(user_id=user_id, limit=_ORDER_LIMIT, offset=0)
    explainability_use_case = GetOrderExplainabilityUseCase(db)
    attribution_use_case = GetOrderAttributionResultUseCase(db)
    disputes_use_case = ListPaymentDisputesUseCase(db)
    dispute_cases_use_case = ListDisputeCasesUseCase(db)

    order_insights: list[AdminCustomerOrderInsightResponse] = []
    partner_account_ids: list[UUID] = []

    for order in orders:
        explainability_result = await explainability_use_case.execute(order_id=order.id)
        attribution_result = await attribution_use_case.execute(order_id=order.id)
        payment_disputes = (
            await disputes_use_case.execute(order_id=order.id)
            if finance_visible
            else []
        )
        dispute_cases = []
        if finance_visible:
            for payment_dispute in payment_disputes:
                dispute_cases.extend(
                    await dispute_cases_use_case.execute(
                        payment_dispute_id=payment_dispute.id,
                        limit=_SETTLEMENT_LIMIT,
                        offset=0,
                    )
                )
        resolved_partner_account_id = _parse_uuid_or_none(
            (
                explainability_result.explainability_payload.get("commercial_resolution_summary", {}) or {}
            ).get("resolved_partner_account_id"),
        )
        if resolved_partner_account_id is None and attribution_result is not None:
            resolved_partner_account_id = attribution_result.partner_account_id
        if resolved_partner_account_id is not None and resolved_partner_account_id not in partner_account_ids:
            partner_account_ids.append(resolved_partner_account_id)

        order_insights.append(
            AdminCustomerOrderInsightResponse(
                order_explainability={
                    "order": _serialize_order_summary(explainability_result.order),
                    "commissionability_evaluation": _serialize_evaluation(
                        explainability_result.commissionability_evaluation
                    ),
                    "explainability": explainability_result.explainability_payload,
                },
                auth_realm_id=order.auth_realm_id,
                storefront_id=order.storefront_id,
                attribution_result=(
                    _serialize_order_attribution_result(attribution_result)
                    if attribution_result is not None
                    else None
                ),
                payment_disputes=[_serialize_payment_dispute(item) for item in payment_disputes],
                dispute_cases=[
                    DisputeCaseResponse.model_validate(item) for item in dispute_cases
                ],
                resolved_partner_account_id=resolved_partner_account_id,
            )
        )

    return order_insights, partner_account_ids


async def _collect_settlement_workspace_insights(
    *,
    partner_account_ids: list[UUID],
    finance_actions_visible: bool,
    db: AsyncSession,
) -> list[AdminCustomerSettlementWorkspaceInsightResponse]:
    settlement_workspaces: list[AdminCustomerSettlementWorkspaceInsightResponse] = []
    list_payout_accounts = ListPartnerPayoutAccountsUseCase(db)
    list_statements = ListPartnerStatementsUseCase(db)
    list_instructions = ListPayoutInstructionsUseCase(db)
    list_executions = ListPayoutExecutionsUseCase(db)

    for partner_account_id in partner_account_ids:
        payout_accounts = await list_payout_accounts.execute(
            partner_account_id=partner_account_id,
            limit=_SETTLEMENT_LIMIT,
            offset=0,
        )
        statements = await list_statements.execute(
            partner_account_id=partner_account_id,
            limit=_SETTLEMENT_LIMIT,
            offset=0,
        )
        payout_instructions = await list_instructions.execute(
            partner_account_id=partner_account_id,
            limit=_SETTLEMENT_LIMIT,
            offset=0,
        )
        payout_executions = await list_executions.execute(
            partner_account_id=partner_account_id,
            limit=_SETTLEMENT_LIMIT,
            offset=0,
        )
        settlement_workspaces.append(
            AdminCustomerSettlementWorkspaceInsightResponse(
                partner_account_id=partner_account_id,
                payout_accounts=[_serialize_payout_account(item) for item in payout_accounts],
                partner_statements=[_serialize_statement(item) for item in statements],
                payout_instructions=[_serialize_instruction(item) for item in payout_instructions],
                payout_executions=[_serialize_execution(item) for item in payout_executions],
                payout_account_actions=(
                    {
                        str(item.id): _resolve_payout_account_actions(item)
                        for item in payout_accounts
                        if _resolve_payout_account_actions(item)
                    }
                    if finance_actions_visible
                    else {}
                ),
                payout_instruction_actions=(
                    {
                        str(item.id): _resolve_payout_instruction_actions(item)
                        for item in payout_instructions
                        if _resolve_payout_instruction_actions(item)
                    }
                    if finance_actions_visible
                    else {}
                ),
            )
        )

    return settlement_workspaces


async def _get_customer_or_404(*, user_id: UUID, db: AsyncSession):
    user_repo = MobileUserRepository(db)
    user = await user_repo.get_by_id(user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Mobile user not found")
    return user


def _build_export_filename(
    *,
    export_kind: AdminCustomerOperationsExportKind,
    resource_id: UUID,
) -> str:
    return f"customer-operations-{export_kind.value}-{resource_id}.json"


def _build_export_response(
    *,
    export_kind: AdminCustomerOperationsExportKind,
    filename: str,
    user_id: UUID,
    partner_account_id: UUID,
    scope: dict[str, Any],
    evidence: dict[str, Any],
) -> JSONResponse:
    payload = AdminCustomerOperationsExportResponse(
        export_kind=export_kind,
        filename=filename,
        exported_at=datetime.now(UTC),
        user_id=user_id,
        partner_account_id=partner_account_id,
        scope=scope,
        evidence=evidence,
    )
    return JSONResponse(
        content=jsonable_encoder(payload),
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/{user_id}/operations-insight", response_model=AdminCustomerOperationsInsightResponse)
async def get_customer_operations_insight(
    user_id: UUID,
    current_user: AdminUserModel = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(require_permission(Permission.USER_READ)),
) -> AdminCustomerOperationsInsightResponse:
    user = await _get_customer_or_404(user_id=user_id, db=db)

    role = AdminRole(current_user.role)
    section_access = AdminCustomerOperationsSectionAccessResponse(
        explainability_visible=True,
        finance_visible=has_permission(role, Permission.PAYMENT_READ),
        finance_actions_visible=check_minimum_role(role, AdminRole.ADMIN),
        risk_visible=check_minimum_role(role, AdminRole.ADMIN),
    )
    order_insights, partner_account_ids = await _collect_customer_order_insights(
        user_id=user_id,
        finance_visible=section_access.finance_visible,
        db=db,
    )

    service_access_use_case = GetServiceAccessObservabilityUseCase(db)
    service_identity_use_case = ListServiceIdentitiesUseCase(db)
    service_identity_models = await service_identity_use_case.execute(
        customer_account_id=user_id,
        limit=_SERVICE_IDENTITY_LIMIT,
        offset=0,
    )
    service_access_insights: list[AdminCustomerServiceAccessInsightResponse] = []
    for service_identity in service_identity_models:
        observability_result = await service_access_use_case.execute(service_identity_id=service_identity.id)
        service_access_insights.append(
            AdminCustomerServiceAccessInsightResponse(
                service_identity=_serialize_service_identity(service_identity),
                service_state=_build_service_access_observability_response(
                    observability_result,
                    channel_type=None,
                    credential_type=None,
                    credential_subject_key=None,
                ),
            )
        )

    settlement_workspaces: list[AdminCustomerSettlementWorkspaceInsightResponse] = []
    if section_access.finance_visible:
        settlement_workspaces = await _collect_settlement_workspace_insights(
            partner_account_ids=partner_account_ids,
            finance_actions_visible=section_access.finance_actions_visible,
            db=db,
        )

    risk_subject_insights: list[AdminCustomerRiskSubjectInsightResponse] = []
    if section_access.risk_visible:
        risk_repo = RiskSubjectGraphRepository(db)
        risk_subjects = await risk_repo.list_subjects_by_principal(
            principal_class=PrincipalClass.CUSTOMER.value,
            principal_subject=str(user.id),
        )
        for risk_subject in risk_subjects:
            reviews = await risk_repo.list_reviews_for_subject(risk_subject.id)
            risk_subject_insights.append(
                AdminCustomerRiskSubjectInsightResponse(
                    risk_subject=RiskSubjectResponse.model_validate(risk_subject),
                    reviews=[RiskReviewResponse.model_validate(review) for review in reviews],
                )
            )

    route_operations_total.labels(
        route="admin_customer_operations",
        action="operations_insight",
        status="success",
    ).inc()
    return AdminCustomerOperationsInsightResponse(
        user_id=user.id,
        section_access=section_access,
        order_insights=order_insights,
        settlement_workspaces=settlement_workspaces,
        service_access_insights=service_access_insights,
        risk_subject_insights=risk_subject_insights,
    )


@router.get(
    "/{user_id}/operations-insight/exports/workspaces/{partner_account_id}",
    response_model=AdminCustomerOperationsExportResponse,
)
async def export_customer_workspace_finance_evidence(
    user_id: UUID,
    partner_account_id: UUID,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(require_permission(Permission.PAYMENT_READ)),
) -> JSONResponse:
    user = await _get_customer_or_404(user_id=user_id, db=db)
    order_insights, partner_account_ids = await _collect_customer_order_insights(
        user_id=user_id,
        finance_visible=True,
        db=db,
    )
    if partner_account_id not in partner_account_ids:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Customer-linked settlement workspace not found",
        )
    settlement_workspaces = await _collect_settlement_workspace_insights(
        partner_account_ids=[partner_account_id],
        finance_actions_visible=False,
        db=db,
    )
    workspace = settlement_workspaces[0] if settlement_workspaces else None
    if workspace is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Customer-linked settlement workspace not found",
        )

    filename = _build_export_filename(
        export_kind=AdminCustomerOperationsExportKind.WORKSPACE_FINANCE_EVIDENCE,
        resource_id=partner_account_id,
    )
    scoped_order_insights = [
        item
        for item in order_insights
        if item.resolved_partner_account_id == partner_account_id
    ]
    return _build_export_response(
        export_kind=AdminCustomerOperationsExportKind.WORKSPACE_FINANCE_EVIDENCE,
        filename=filename,
        user_id=user.id,
        partner_account_id=partner_account_id,
        scope={
            "customer_user_id": str(user.id),
            "partner_account_id": str(partner_account_id),
            "statement_ids": [str(item.id) for item in workspace.partner_statements],
            "payout_instruction_ids": [str(item.id) for item in workspace.payout_instructions],
            "payout_execution_ids": [str(item.id) for item in workspace.payout_executions],
        },
        evidence={
            "workspace": jsonable_encoder(workspace),
            "order_insights": jsonable_encoder(scoped_order_insights),
        },
    )


@router.get(
    "/{user_id}/operations-insight/exports/partner-statements/{statement_id}",
    response_model=AdminCustomerOperationsExportResponse,
)
async def export_customer_partner_statement_evidence(
    user_id: UUID,
    statement_id: UUID,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(require_permission(Permission.PAYMENT_READ)),
) -> JSONResponse:
    user = await _get_customer_or_404(user_id=user_id, db=db)
    statement = await GetPartnerStatementUseCase(db).execute(statement_id=statement_id)
    if statement is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Partner statement not found")
    partner_account_ids = await _collect_customer_partner_account_ids(user_id=user_id, db=db)
    if statement.partner_account_id not in partner_account_ids:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Partner statement not linked to customer",
        )
    adjustments = await ListStatementAdjustmentsUseCase(db).execute(partner_statement_id=statement.id)
    instructions = await ListPayoutInstructionsUseCase(db).execute(
        partner_account_id=statement.partner_account_id,
        partner_statement_id=statement.id,
        limit=_SETTLEMENT_LIMIT,
        offset=0,
    )
    executions = await ListPayoutExecutionsUseCase(db).execute(
        partner_account_id=statement.partner_account_id,
        partner_statement_id=statement.id,
        limit=_SETTLEMENT_LIMIT,
        offset=0,
    )
    order_insights, _ = await _collect_customer_order_insights(
        user_id=user_id,
        finance_visible=True,
        db=db,
    )
    filename = _build_export_filename(
        export_kind=AdminCustomerOperationsExportKind.PARTNER_STATEMENT_EVIDENCE,
        resource_id=statement.id,
    )
    return _build_export_response(
        export_kind=AdminCustomerOperationsExportKind.PARTNER_STATEMENT_EVIDENCE,
        filename=filename,
        user_id=user.id,
        partner_account_id=statement.partner_account_id,
        scope={
            "customer_user_id": str(user.id),
            "partner_account_id": str(statement.partner_account_id),
            "statement_id": str(statement.id),
            "payout_instruction_ids": [str(item.id) for item in instructions],
            "payout_execution_ids": [str(item.id) for item in executions],
        },
        evidence={
            "statement": _serialize_statement(statement),
            "statement_adjustments": [
                _serialize_adjustment(item) for item in adjustments
            ],
            "payout_instructions": [
                _serialize_instruction(item) for item in instructions
            ],
            "payout_executions": [
                _serialize_execution(item) for item in executions
            ],
            "order_insights": jsonable_encoder(
                [
                    item
                    for item in order_insights
                    if item.resolved_partner_account_id == statement.partner_account_id
                ]
            ),
        },
    )


@router.get(
    "/{user_id}/operations-insight/exports/payout-instructions/{payout_instruction_id}",
    response_model=AdminCustomerOperationsExportResponse,
)
async def export_customer_payout_instruction_evidence(
    user_id: UUID,
    payout_instruction_id: UUID,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(require_permission(Permission.PAYMENT_READ)),
) -> JSONResponse:
    user = await _get_customer_or_404(user_id=user_id, db=db)
    instruction = await GetPayoutInstructionUseCase(db).execute(
        payout_instruction_id=payout_instruction_id,
    )
    if instruction is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Payout instruction not found")
    partner_account_ids = await _collect_customer_partner_account_ids(user_id=user_id, db=db)
    if instruction.partner_account_id not in partner_account_ids:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payout instruction not linked to customer",
        )
    payout_account = await GetPartnerPayoutAccountUseCase(db).execute(
        payout_account_id=instruction.partner_payout_account_id,
    )
    statement = await GetPartnerStatementUseCase(db).execute(
        statement_id=instruction.partner_statement_id,
    )
    executions = await ListPayoutExecutionsUseCase(db).execute(
        payout_instruction_id=instruction.id,
        limit=_SETTLEMENT_LIMIT,
        offset=0,
    )
    filename = _build_export_filename(
        export_kind=AdminCustomerOperationsExportKind.PAYOUT_INSTRUCTION_EVIDENCE,
        resource_id=instruction.id,
    )
    return _build_export_response(
        export_kind=AdminCustomerOperationsExportKind.PAYOUT_INSTRUCTION_EVIDENCE,
        filename=filename,
        user_id=user.id,
        partner_account_id=instruction.partner_account_id,
        scope={
            "customer_user_id": str(user.id),
            "partner_account_id": str(instruction.partner_account_id),
            "payout_instruction_id": str(instruction.id),
            "linked_execution_ids": [str(item.id) for item in executions],
        },
        evidence={
            "payout_instruction": _serialize_instruction(instruction),
            "partner_statement": (
                _serialize_statement(statement) if statement is not None else None
            ),
            "partner_payout_account": (
                _serialize_payout_account(payout_account)
                if payout_account is not None
                else None
            ),
            "payout_executions": [
                _serialize_execution(item) for item in executions
            ],
        },
    )


@router.get(
    "/{user_id}/operations-insight/exports/payout-executions/{payout_execution_id}",
    response_model=AdminCustomerOperationsExportResponse,
)
async def export_customer_payout_execution_evidence(
    user_id: UUID,
    payout_execution_id: UUID,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(require_permission(Permission.PAYMENT_READ)),
) -> JSONResponse:
    user = await _get_customer_or_404(user_id=user_id, db=db)
    execution = await GetPayoutExecutionUseCase(db).execute(
        payout_execution_id=payout_execution_id,
    )
    if execution is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Payout execution not found")
    partner_account_ids = await _collect_customer_partner_account_ids(user_id=user_id, db=db)
    if execution.partner_account_id not in partner_account_ids:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payout execution not linked to customer",
        )
    instruction = await GetPayoutInstructionUseCase(db).execute(
        payout_instruction_id=execution.payout_instruction_id,
    )
    payout_account = await GetPartnerPayoutAccountUseCase(db).execute(
        payout_account_id=execution.partner_payout_account_id,
    )
    statement = await GetPartnerStatementUseCase(db).execute(
        statement_id=execution.partner_statement_id,
    )
    filename = _build_export_filename(
        export_kind=AdminCustomerOperationsExportKind.PAYOUT_EXECUTION_EVIDENCE,
        resource_id=execution.id,
    )
    return _build_export_response(
        export_kind=AdminCustomerOperationsExportKind.PAYOUT_EXECUTION_EVIDENCE,
        filename=filename,
        user_id=user.id,
        partner_account_id=execution.partner_account_id,
        scope={
            "customer_user_id": str(user.id),
            "partner_account_id": str(execution.partner_account_id),
            "payout_execution_id": str(execution.id),
            "payout_instruction_id": str(execution.payout_instruction_id),
        },
        evidence={
            "payout_execution": _serialize_execution(execution),
            "payout_instruction": (
                _serialize_instruction(instruction) if instruction is not None else None
            ),
            "partner_statement": (
                _serialize_statement(statement) if statement is not None else None
            ),
            "partner_payout_account": (
                _serialize_payout_account(payout_account)
                if payout_account is not None
                else None
            ),
        },
    )


@router.post(
    "/{user_id}/operations-insight/actions",
    response_model=AdminCustomerOperationsActionResponse,
)
async def perform_customer_operations_action(
    user_id: UUID,
    payload: AdminCustomerOperationsActionRequest,
    db: AsyncSession = Depends(get_db),
    current_admin: AdminUserModel = Depends(require_role(AdminRole.ADMIN)),
) -> AdminCustomerOperationsActionResponse:
    user_repo = MobileUserRepository(db)
    user = await user_repo.get_by_id(user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Mobile user not found")

    partner_account_ids = await _collect_customer_partner_account_ids(user_id=user.id, db=db)
    if not partner_account_ids:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No customer-linked settlement workspaces found",
        )

    try:
        if payload.action_kind == AdminCustomerOperationsActionKind.VERIFY_PAYOUT_ACCOUNT:
            if payload.payout_account_id is None:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="payout_account_id is required for verify_payout_account",
                )
            payout_account = await GetPartnerPayoutAccountUseCase(db).execute(
                payout_account_id=payload.payout_account_id,
            )
            if payout_account is None or payout_account.partner_account_id not in partner_account_ids:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Partner payout account not linked to customer",
                )
            updated = await VerifyPartnerPayoutAccountUseCase(db).execute(
                payout_account_id=payout_account.id,
                verified_by_admin_user_id=current_admin.id,
            )
            response = AdminCustomerOperationsActionResponse(
                action_kind=payload.action_kind,
                target_kind="payout_account",
                target_id=updated.id,
                payout_account=_serialize_payout_account(updated),
            )
        elif payload.action_kind == AdminCustomerOperationsActionKind.SUSPEND_PAYOUT_ACCOUNT:
            if payload.payout_account_id is None:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="payout_account_id is required for suspend_payout_account",
                )
            payout_account = await GetPartnerPayoutAccountUseCase(db).execute(
                payout_account_id=payload.payout_account_id,
            )
            if payout_account is None or payout_account.partner_account_id not in partner_account_ids:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Partner payout account not linked to customer",
                )
            updated = await SuspendPartnerPayoutAccountUseCase(db).execute(
                payout_account_id=payout_account.id,
                suspended_by_admin_user_id=current_admin.id,
                reason_code=payload.reason_code,
            )
            response = AdminCustomerOperationsActionResponse(
                action_kind=payload.action_kind,
                target_kind="payout_account",
                target_id=updated.id,
                payout_account=_serialize_payout_account(updated),
            )
        elif payload.action_kind == AdminCustomerOperationsActionKind.APPROVE_PAYOUT_INSTRUCTION:
            if payload.payout_instruction_id is None:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="payout_instruction_id is required for approve_payout_instruction",
                )
            instruction = await GetPayoutInstructionUseCase(db).execute(
                payout_instruction_id=payload.payout_instruction_id,
            )
            if instruction is None or instruction.partner_account_id not in partner_account_ids:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Payout instruction not linked to customer",
                )
            updated = await ApprovePayoutInstructionUseCase(db).execute(
                payout_instruction_id=instruction.id,
                approved_by_admin_user_id=current_admin.id,
            )
            response = AdminCustomerOperationsActionResponse(
                action_kind=payload.action_kind,
                target_kind="payout_instruction",
                target_id=updated.id,
                payout_instruction=_serialize_instruction(updated),
            )
        else:
            if payload.payout_instruction_id is None:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="payout_instruction_id is required for reject_payout_instruction",
                )
            instruction = await GetPayoutInstructionUseCase(db).execute(
                payout_instruction_id=payload.payout_instruction_id,
            )
            if instruction is None or instruction.partner_account_id not in partner_account_ids:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Payout instruction not linked to customer",
                )
            updated = await RejectPayoutInstructionUseCase(db).execute(
                payout_instruction_id=instruction.id,
                rejected_by_admin_user_id=current_admin.id,
                rejection_reason_code=payload.reason_code or "",
            )
            response = AdminCustomerOperationsActionResponse(
                action_kind=payload.action_kind,
                target_kind="payout_instruction",
                target_id=updated.id,
                payout_instruction=_serialize_instruction(updated),
            )
    except ValueError as exc:
        detail = str(exc)
        status_code = status.HTTP_409_CONFLICT if "Maker-checker" in detail else status.HTTP_400_BAD_REQUEST
        raise HTTPException(status_code=status_code, detail=detail) from exc

    route_operations_total.labels(
        route="admin_customer_operations",
        action="operations_action",
        status="success",
    ).inc()
    return response
