"""Two-factor authentication API schemas (CRIT-3 secure)."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, SecretStr


class ReauthRequest(BaseModel):
    """Request for password re-authentication."""

    password: SecretStr = Field(..., min_length=1, description="Current password for re-authentication")


class VerifyCodeRequest(BaseModel):
    """Request schema for verifying a 2FA code."""

    model_config = ConfigDict(json_schema_extra={"example": {"code": "123456"}})

    code: str = Field(
        ...,
        min_length=6,
        max_length=6,
        pattern=r"^\d{6}$",
        description="Six-digit TOTP verification code",
    )


class TwoFactorSetupRequest(BaseModel):
    """Request to begin 2FA setup (requires recent re-auth)."""

    # No fields needed - re-auth is checked via dependency
    pass


class TwoFactorSetupResponse(BaseModel):
    """Response from 2FA setup containing secret and provisioning info."""

    model_config = ConfigDict(from_attributes=True)

    secret: str = Field(..., description="TOTP secret key")
    qr_uri: str = Field(..., max_length=2000, description="otpauth:// provisioning URI")
    message: str = Field(
        default="Scan the QR code with your authenticator app, then verify with a code.",
        description="User instructions",
    )


class TwoFactorVerifyRequest(BaseModel):
    """Request to verify 2FA setup and persist secret."""

    code: str = Field(
        ...,
        min_length=6,
        max_length=6,
        pattern=r"^\d{6}$",
        description="Six-digit TOTP verification code",
    )


class TwoFactorStatusResponse(BaseModel):
    """Response indicating 2FA enabled/disabled status."""

    model_config = ConfigDict(from_attributes=True)

    status: Literal["enabled", "disabled"] = Field(..., description="2FA status")
    recovery_codes: list[str] | None = Field(
        default=None,
        description="One-time recovery codes (only shown once when disabling)",
    )


class TwoFactorValidateResponse(BaseModel):
    """Response from 2FA code validation."""

    model_config = ConfigDict(from_attributes=True)

    valid: bool = Field(..., description="Whether the code was valid")


class TwoFactorDisableRequest(BaseModel):
    """Request to disable 2FA (requires password)."""

    password: SecretStr = Field(..., min_length=1, description="Current password")
    code: str = Field(
        ...,
        min_length=6,
        max_length=6,
        pattern=r"^\d{6}$",
        description="Current TOTP code to confirm disable",
    )


class ReauthResponse(BaseModel):
    """Response from successful re-authentication."""

    message: str = Field(
        default="Re-authentication successful. You can now perform sensitive operations.",
        description="Success message",
    )
    valid_for_minutes: int = Field(
        default=5,
        description="How long the re-authentication is valid",
    )
