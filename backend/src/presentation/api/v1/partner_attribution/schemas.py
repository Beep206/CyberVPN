from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

_MAX_SUB_IDS = 16
_MAX_CAMPAIGN_PARAMS = 24
_MAX_ATTRIBUTION_KEY_LENGTH = 64
_MAX_SUB_ID_VALUE_LENGTH = 160
_MAX_CAMPAIGN_VALUE_LENGTH = 200
_SCALAR_ATTRIBUTION_VALUE_TYPES = str | int | float | bool


class PartnerAttributionCaptureRequest(BaseModel):
    public_token: str = Field(min_length=8, max_length=128)
    source_path: str | None = Field(default=None, max_length=500)
    destination_path: str | None = Field(default=None, max_length=500)
    locale: str | None = Field(default=None, max_length=16)
    sale_channel: str | None = Field(default=None, max_length=40)
    sub_ids: dict[str, str] | None = Field(default=None, max_length=_MAX_SUB_IDS)
    click_id: str | None = Field(default=None, max_length=160)
    browser_key: str = Field(min_length=1, max_length=160)
    campaign_params: dict[str, str] | None = Field(default=None, max_length=_MAX_CAMPAIGN_PARAMS)

    @field_validator("sub_ids", mode="before")
    @classmethod
    def _validate_sub_ids(cls, value):
        return _validate_string_map(
            value,
            max_items=_MAX_SUB_IDS,
            max_key_length=48,
            max_value_length=_MAX_SUB_ID_VALUE_LENGTH,
            field_name="sub_ids",
        )

    @field_validator("campaign_params", mode="before")
    @classmethod
    def _validate_campaign_params(cls, value):
        return _validate_string_map(
            value,
            max_items=_MAX_CAMPAIGN_PARAMS,
            max_key_length=_MAX_ATTRIBUTION_KEY_LENGTH,
            max_value_length=_MAX_CAMPAIGN_VALUE_LENGTH,
            field_name="campaign_params",
        )


def _validate_string_map(
    value,
    *,
    max_items: int,
    max_key_length: int,
    max_value_length: int,
    field_name: str,
) -> dict[str, str] | None:
    if value is None:
        return None
    if not isinstance(value, dict):
        raise ValueError(f"{field_name} must be an object")
    if len(value) > max_items:
        raise ValueError(f"{field_name} must contain at most {max_items} entries")

    validated: dict[str, str] = {}
    for raw_key, raw_value in value.items():
        if not isinstance(raw_key, str):
            raise ValueError(f"{field_name} keys must be strings")
        key = raw_key.strip()
        if not key or len(key) > max_key_length:
            raise ValueError(f"{field_name} keys must be 1-{max_key_length} characters")
        if not isinstance(raw_value, _SCALAR_ATTRIBUTION_VALUE_TYPES):
            raise ValueError(f"{field_name} values must be scalar strings, numbers, or booleans")
        value_text = str(raw_value)
        if len(value_text) > max_value_length:
            raise ValueError(f"{field_name} values must be at most {max_value_length} characters")
        validated[key] = value_text
    return validated


class PartnerAttributionCaptureResponse(BaseModel):
    attribution_id: UUID
    captured_at: datetime
    expires_at: datetime
    masked_code: str
    transfer_token: str
    redirect_url: str


class PartnerAttributionTransferConsumeRequest(BaseModel):
    transfer_token: str = Field(min_length=16, max_length=256)


class PartnerAttributionTransferConsumeResponse(BaseModel):
    attribution_id: UUID
    captured_at: datetime
    expires_at: datetime
    masked_code: str


class PartnerAttributionClaimRequest(BaseModel):
    pass


class PartnerAttributionClaimResponse(BaseModel):
    status: str
    partner_account_id: UUID | None = None
    partner_code_id: UUID | None = None
    binding_id: UUID | None = None
    claimed_at: datetime | None = None


class PartnerAttributionErrorDetail(BaseModel):
    code: str
    message: str
    retryable: bool | None = None
    scope: str | None = None


class PartnerAttributionErrorResponse(BaseModel):
    detail: PartnerAttributionErrorDetail
