"""Pydantic schemas for security endpoints."""

from pydantic import BaseModel, Field


class SetAntiPhishingCodeRequest(BaseModel):
    """Request to set or update anti-phishing code."""

    code: str = Field(..., min_length=1, max_length=50, description="User's anti-phishing code")


class AntiPhishingCodeResponse(BaseModel):
    """Response with anti-phishing code."""

    code: str | None = Field(None, description="User's anti-phishing code (null if not set)")


class DeleteAntiPhishingCodeResponse(BaseModel):
    """Response after deleting anti-phishing code."""

    message: str = "Anti-phishing code deleted successfully"
