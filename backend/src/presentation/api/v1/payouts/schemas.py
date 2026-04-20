from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from src.domain.enums import PayoutExecutionMode, PayoutExecutionStatus, PayoutInstructionStatus


class CreatePayoutInstructionRequest(BaseModel):
    partner_statement_id: UUID
    partner_payout_account_id: UUID | None = None


class RejectPayoutInstructionRequest(BaseModel):
    rejection_reason_code: str = Field(..., min_length=1, max_length=80)


class CreatePayoutExecutionRequest(BaseModel):
    payout_instruction_id: UUID
    execution_mode: PayoutExecutionMode = PayoutExecutionMode.DRY_RUN
    execution_payload: dict[str, Any] = Field(default_factory=dict)


class SubmitPayoutExecutionRequest(BaseModel):
    external_reference: str | None = Field(None, min_length=1, max_length=255)
    submission_payload: dict[str, Any] = Field(default_factory=dict)


class CompletePayoutExecutionRequest(BaseModel):
    external_reference: str | None = Field(None, min_length=1, max_length=255)
    completion_payload: dict[str, Any] = Field(default_factory=dict)


class FailPayoutExecutionRequest(BaseModel):
    failure_reason_code: str = Field(..., min_length=1, max_length=80)
    failure_payload: dict[str, Any] = Field(default_factory=dict)


class ReconcilePayoutExecutionRequest(BaseModel):
    reconciliation_payload: dict[str, Any] = Field(default_factory=dict)


class PayoutInstructionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=False)

    id: UUID
    partner_account_id: UUID
    partner_statement_id: UUID
    partner_payout_account_id: UUID
    instruction_key: str
    instruction_status: PayoutInstructionStatus
    payout_amount: float
    currency_code: str
    instruction_snapshot: dict[str, Any] = Field(default_factory=dict)
    created_by_admin_user_id: UUID | None = None
    approved_by_admin_user_id: UUID | None = None
    approved_at: datetime | None = None
    rejected_by_admin_user_id: UUID | None = None
    rejected_at: datetime | None = None
    rejection_reason_code: str | None = None
    completed_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class PayoutExecutionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=False)

    id: UUID
    payout_instruction_id: UUID
    partner_account_id: UUID
    partner_statement_id: UUID
    partner_payout_account_id: UUID
    execution_key: str
    execution_mode: PayoutExecutionMode
    execution_status: PayoutExecutionStatus
    request_idempotency_key: str
    external_reference: str | None = None
    execution_payload: dict[str, Any] = Field(default_factory=dict)
    result_payload: dict[str, Any] = Field(default_factory=dict)
    requested_by_admin_user_id: UUID | None = None
    submitted_by_admin_user_id: UUID | None = None
    submitted_at: datetime | None = None
    completed_by_admin_user_id: UUID | None = None
    completed_at: datetime | None = None
    reconciled_by_admin_user_id: UUID | None = None
    reconciled_at: datetime | None = None
    failure_reason_code: str | None = None
    created_at: datetime
    updated_at: datetime
