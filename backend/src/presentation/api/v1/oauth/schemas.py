"""OAuth social account linking API schemas (CRIT-2)."""

from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class OAuthProvider(StrEnum):
    """Valid OAuth providers (HIGH-7)."""

    TELEGRAM = "telegram"
    GITHUB = "github"


class OAuthAuthorizeResponse(BaseModel):
    """Response containing OAuth authorization URL and state token."""

    model_config = ConfigDict(from_attributes=True)

    authorize_url: str = Field(
        ..., max_length=2000, description="OAuth provider authorization URL"
    )
    state: str = Field(
        ..., description="CSRF protection state token (include in callback)"
    )


class TelegramCallbackRequest(BaseModel):
    """Telegram OAuth callback data.

    Contains all fields sent by Telegram Login Widget.
    The hash field is used to validate the data integrity.
    """

    id: str = Field(..., description="Telegram user ID")
    first_name: str = Field(..., description="User's first name")
    last_name: str | None = Field(default=None, description="User's last name")
    username: str | None = Field(default=None, description="Telegram username")
    photo_url: str | None = Field(default=None, description="Profile photo URL")
    auth_date: str = Field(..., description="Unix timestamp of authentication")
    hash: str = Field(..., description="HMAC-SHA256 signature for validation")
    state: str = Field(..., description="OAuth state token for CSRF protection")


class GitHubCallbackRequest(BaseModel):
    """GitHub OAuth callback request."""

    code: str = Field(..., description="Authorization code from GitHub")
    state: str = Field(..., description="OAuth state token for CSRF protection")
    redirect_uri: str = Field(..., description="Redirect URI used in authorization")


class OAuthLinkResponse(BaseModel):
    """Response for account link/unlink operations."""

    model_config = ConfigDict(from_attributes=True)

    status: Literal["linked", "unlinked"] = Field(
        ..., description="Link operation result"
    )
    provider: str = Field(
        ..., description="OAuth provider name"
    )
    provider_user_id: str | None = Field(
        default=None, description="User ID from the OAuth provider"
    )
