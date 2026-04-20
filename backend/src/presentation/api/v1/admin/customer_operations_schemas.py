"""Schemas for canonical admin customer operations inspection."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from src.presentation.api.v1.attribution.schemas import OrderAttributionResultResponse
from src.presentation.api.v1.dispute_cases.schemas import DisputeCaseResponse
from src.presentation.api.v1.orders.explainability.schemas import OrderExplainabilityResponse
from src.presentation.api.v1.partner_payout_accounts.schemas import PartnerPayoutAccountResponse
from src.presentation.api.v1.partner_statements.schemas import PartnerStatementResponse
from src.presentation.api.v1.payment_disputes.schemas import PaymentDisputeResponse
from src.presentation.api.v1.payouts.schemas import PayoutExecutionResponse, PayoutInstructionResponse
from src.presentation.api.v1.security.schemas import RiskReviewResponse, RiskSubjectResponse
from src.presentation.api.v1.service_identities.schemas import (
    ServiceAccessObservabilityResponse,
    ServiceIdentityResponse,
)


class AdminCustomerOperationsActionKind(StrEnum):
    VERIFY_PAYOUT_ACCOUNT = "verify_payout_account"
    SUSPEND_PAYOUT_ACCOUNT = "suspend_payout_account"
    APPROVE_PAYOUT_INSTRUCTION = "approve_payout_instruction"
    REJECT_PAYOUT_INSTRUCTION = "reject_payout_instruction"


class AdminCustomerOperationsExportKind(StrEnum):
    WORKSPACE_FINANCE_EVIDENCE = "workspace_finance_evidence"
    PARTNER_STATEMENT_EVIDENCE = "partner_statement_evidence"
    PAYOUT_INSTRUCTION_EVIDENCE = "payout_instruction_evidence"
    PAYOUT_EXECUTION_EVIDENCE = "payout_execution_evidence"


class AdminCustomerOperationsSectionAccessResponse(BaseModel):
    explainability_visible: bool = True
    finance_visible: bool = False
    finance_actions_visible: bool = False
    risk_visible: bool = False


class AdminCustomerOrderInsightResponse(BaseModel):
    model_config = ConfigDict(from_attributes=False)

    order_explainability: OrderExplainabilityResponse
    auth_realm_id: UUID
    storefront_id: UUID
    attribution_result: OrderAttributionResultResponse | None = None
    payment_disputes: list[PaymentDisputeResponse] = Field(default_factory=list)
    dispute_cases: list[DisputeCaseResponse] = Field(default_factory=list)
    resolved_partner_account_id: UUID | None = None


class AdminCustomerSettlementWorkspaceInsightResponse(BaseModel):
    model_config = ConfigDict(from_attributes=False)

    partner_account_id: UUID
    payout_accounts: list[PartnerPayoutAccountResponse] = Field(default_factory=list)
    partner_statements: list[PartnerStatementResponse] = Field(default_factory=list)
    payout_instructions: list[PayoutInstructionResponse] = Field(default_factory=list)
    payout_executions: list[PayoutExecutionResponse] = Field(default_factory=list)
    payout_account_actions: dict[str, list[AdminCustomerOperationsActionKind]] = Field(default_factory=dict)
    payout_instruction_actions: dict[str, list[AdminCustomerOperationsActionKind]] = Field(default_factory=dict)


class AdminCustomerServiceAccessInsightResponse(BaseModel):
    model_config = ConfigDict(from_attributes=False)

    service_identity: ServiceIdentityResponse
    service_state: ServiceAccessObservabilityResponse


class AdminCustomerRiskSubjectInsightResponse(BaseModel):
    model_config = ConfigDict(from_attributes=False)

    risk_subject: RiskSubjectResponse
    reviews: list[RiskReviewResponse] = Field(default_factory=list)


class AdminCustomerOperationsInsightResponse(BaseModel):
    model_config = ConfigDict(from_attributes=False)

    user_id: UUID
    section_access: AdminCustomerOperationsSectionAccessResponse
    order_insights: list[AdminCustomerOrderInsightResponse] = Field(default_factory=list)
    settlement_workspaces: list[AdminCustomerSettlementWorkspaceInsightResponse] = Field(default_factory=list)
    service_access_insights: list[AdminCustomerServiceAccessInsightResponse] = Field(default_factory=list)
    risk_subject_insights: list[AdminCustomerRiskSubjectInsightResponse] = Field(default_factory=list)


class AdminCustomerOperationsActionRequest(BaseModel):
    action_kind: AdminCustomerOperationsActionKind
    payout_account_id: UUID | None = None
    payout_instruction_id: UUID | None = None
    reason_code: str | None = Field(default=None, max_length=80)


class AdminCustomerOperationsActionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=False)

    action_kind: AdminCustomerOperationsActionKind
    target_kind: str
    target_id: UUID
    payout_account: PartnerPayoutAccountResponse | None = None
    payout_instruction: PayoutInstructionResponse | None = None


class AdminCustomerOperationsExportResponse(BaseModel):
    model_config = ConfigDict(from_attributes=False)

    export_kind: AdminCustomerOperationsExportKind
    filename: str
    exported_at: datetime
    user_id: UUID
    partner_account_id: UUID
    scope: dict[str, Any] = Field(default_factory=dict)
    evidence: dict[str, Any] = Field(default_factory=dict)
