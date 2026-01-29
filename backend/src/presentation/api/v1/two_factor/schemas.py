"""Two-factor authentication API schemas."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class VerifyCodeRequest(BaseModel):
    """Request schema for verifying a 2FA code."""

    model_config = ConfigDict(
        json_schema_extra={"example": {"code": "123456"}}
    )

    code: str = Field(
        ..., min_length=6, max_length=6, pattern=r"^\d{6}$",
        description="Six-digit TOTP verification code",
    )


class TwoFactorSetupResponse(BaseModel):
    """Response from 2FA setup containing secret and provisioning info."""

    model_config = ConfigDict(from_attributes=True)

    secret: str = Field(..., description="TOTP secret key")
    qr_code_url: str = Field(..., max_length=2000, description="QR code provisioning URL")
    backup_codes: list[str] | None = Field(
        None, description="One-time backup recovery codes"
    )


class TwoFactorStatusResponse(BaseModel):
    """Response indicating 2FA enabled/disabled status."""

    model_config = ConfigDict(from_attributes=True)

    status: Literal["enabled", "disabled"] = Field(
        ..., description="2FA status"
    )


class TwoFactorValidateResponse(BaseModel):
    """Response from 2FA code validation."""

    model_config = ConfigDict(from_attributes=True)

    valid: bool = Field(..., description="Whether the code was valid")
