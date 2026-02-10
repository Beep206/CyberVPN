"""Pydantic schemas for the authenticated user profile endpoint."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ProfileUpdateRequest(BaseModel):
    """Request schema for partial profile updates (PATCH semantics).

    All fields are optional.  Only the fields provided in the request
    body will be applied to the user profile.
    """

    display_name: str | None = Field(
        None,
        min_length=1,
        max_length=100,
        description="Human-readable display name",
    )
    avatar_url: str | None = Field(
        None,
        max_length=2048,
        description="URL to the user avatar image",
    )
    language: str | None = Field(
        None,
        min_length=2,
        max_length=10,
        description="BCP-47 language tag (e.g. 'en', 'ru', 'ja')",
    )
    timezone: str | None = Field(
        None,
        max_length=50,
        description="IANA timezone identifier (e.g. 'Europe/Moscow')",
    )

    @field_validator("avatar_url", mode="before")
    @classmethod
    def validate_avatar_url(cls, v: str | None) -> str | None:
        if v is not None and not v.startswith(("http://", "https://")):
            raise ValueError("avatar_url must be an HTTP or HTTPS URL")
        return v

    @field_validator("language", mode="before")
    @classmethod
    def normalize_language(cls, v: str | None) -> str | None:
        if v is not None:
            return v.strip().lower()
        return v


class ProfileResponse(BaseModel):
    """Response schema for the authenticated user profile."""

    model_config = ConfigDict(from_attributes=True)

    id: str = Field(
        ...,
        description="Unique identifier of the user",
    )
    email: str = Field(
        ...,
        description="Email address associated with the account",
    )
    display_name: str | None = Field(
        None,
        description="Human-readable display name",
    )
    avatar_url: str | None = Field(
        None,
        description="URL to the user avatar image",
    )
    language: str = Field(
        "en",
        description="BCP-47 language tag",
    )
    timezone: str = Field(
        "UTC",
        description="IANA timezone identifier",
    )
    updated_at: datetime = Field(
        ...,
        description="Timestamp of the last profile update",
    )
