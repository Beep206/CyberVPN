"""Admin commercial pricebook lifecycle schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from src.presentation.api.v1.pricebooks.schemas import PricebookEntryRequest, PricebookResponse


class UpdateAdminPricebookRequest(BaseModel):
    display_name: str | None = Field(None, min_length=1, max_length=120)
    merchant_profile_id: UUID | None = None
    currency_code: str | None = Field(None, min_length=3, max_length=3)
    region_code: str | None = Field(None, min_length=2, max_length=16)
    discount_rules: dict[str, Any] | None = None
    renewal_pricing_policy: dict[str, Any] | None = None
    version_status: str | None = Field(None, min_length=1, max_length=20)
    effective_from: datetime | None = None
    effective_to: datetime | None = None
    is_active: bool | None = None
    entries: list[PricebookEntryRequest] | None = Field(None, min_length=1)
    change_reason: str | None = Field(None, max_length=500)

    @model_validator(mode="after")
    def require_mutation_field(self) -> UpdateAdminPricebookRequest:
        mutable = self.model_dump(exclude={"change_reason"}, exclude_unset=True)
        if not mutable:
            raise ValueError("At least one pricebook field must be provided")
        return self


class PublishAdminPricebookRequest(BaseModel):
    effective_from: datetime | None = None
    change_reason: str | None = Field(None, max_length=500)


class ScheduleAdminPricebookRequest(BaseModel):
    scheduled_for: datetime
    change_reason: str | None = Field(None, max_length=500)


class RollbackAdminPricebookRequest(BaseModel):
    target_pricebook_id: UUID | None = None
    change_reason: str | None = Field(None, max_length=500)


class AdminPricebookLifecycleResponse(BaseModel):
    pricebook: PricebookResponse
    lifecycle_status: str
    audit_action: str


class AdminPricebookVersionResponse(PricebookResponse):
    lifecycle_status: str


class AdminPricebookHistoryResponse(BaseModel):
    pricebook_key: str
    versions: list[AdminPricebookVersionResponse]


class AdminPricebookValidationIssueResponse(BaseModel):
    code: Literal["missing_price", "unsupported_currency", "missing_provisioning_profile", "incompatible_addon"]
    severity: Literal["error", "warning"]
    message: str
    field: str | None = None
    entry_id: UUID | None = None
    offer_id: UUID | None = None
    remediation: str | None = None


class AdminPricebookValidationResponse(BaseModel):
    pricebook_id: UUID
    valid: bool
    checked_at: datetime
    issues: list[AdminPricebookValidationIssueResponse]


class CommercialContextCountryOptionResponse(BaseModel):
    country_code: str
    default_currency_code: str
    supported_currency_codes: list[str]
    payment_country_code: str
    is_enabled: bool


class CommercialContextCurrencyOptionResponse(BaseModel):
    currency_code: str
    minor_units: int = Field(ge=0, le=4)
    is_enabled: bool


class CommercialContextOptionsResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    countries: list[CommercialContextCountryOptionResponse]
    currencies: list[CommercialContextCurrencyOptionResponse]
    source: Literal["default", "system_config"] = "default"


class UpdateCommercialContextCountryOptionRequest(BaseModel):
    country_code: str = Field(..., min_length=2, max_length=2)
    default_currency_code: str = Field(..., min_length=3, max_length=3)
    supported_currency_codes: list[str] = Field(..., min_length=1)
    payment_country_code: str | None = Field(None, min_length=2, max_length=2)
    is_enabled: bool = True


class UpdateCommercialContextCurrencyOptionRequest(BaseModel):
    currency_code: str = Field(..., min_length=3, max_length=3)
    minor_units: int = Field(2, ge=0, le=4)
    is_enabled: bool = True


class UpdateCommercialContextOptionsRequest(BaseModel):
    countries: list[UpdateCommercialContextCountryOptionRequest] = Field(..., min_length=1)
    currencies: list[UpdateCommercialContextCurrencyOptionRequest] = Field(default_factory=list)
    change_reason: str | None = Field(None, max_length=500)
