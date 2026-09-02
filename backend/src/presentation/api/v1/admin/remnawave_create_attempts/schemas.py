from __future__ import annotations

from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, Field, StringConstraints, field_validator

SafeReasonCode = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=3, max_length=80, pattern=r"^[a-z0-9][a-z0-9_.:-]+$"),
]


class SettleCustomerCreateAttemptRequest(BaseModel):
    provider_numeric_user_id: int = Field(ge=1, le=2**63 - 1)
    provider_legacy_uuid: UUID | None = None
    reason_code: SafeReasonCode = "authoritative_provider_readback"

    @field_validator("provider_numeric_user_id", mode="before")
    @classmethod
    def reject_boolean_numeric_id(cls, value: object) -> object:
        if isinstance(value, bool):
            raise ValueError("provider_numeric_user_id must be an integer")
        return value


class ReopenCustomerCreateAttemptRequest(BaseModel):
    reason_code: SafeReasonCode = "operator_reconciliation_requested"


class CustomerCreateAttemptTransitionResponse(BaseModel):
    attempt_id: UUID
    customer_account_id: UUID
    state: Literal["completed", "reconciliation_required"]
    changed: bool
    provider_numeric_user_id: int | None = None
    provider_legacy_uuid: UUID | None = None
