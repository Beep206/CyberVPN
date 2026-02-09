"""OAuth social account linking API schemas (CRIT-2)."""

from datetime import datetime
from enum import StrEnum
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class OAuthProvider(StrEnum):
    """Valid OAuth providers (HIGH-7)."""

    TELEGRAM = "telegram"
    GITHUB = "github"
    GOOGLE = "google"
    DISCORD = "discord"
    APPLE = "apple"
    MICROSOFT = "microsoft"
    TWITTER = "twitter"


class OAuthAuthorizeResponse(BaseModel):
    """Response containing OAuth authorization URL and state token."""

    model_config = ConfigDict(from_attributes=True)

    authorize_url: str = Field(..., max_length=2000, description="OAuth provider authorization URL")
    state: str = Field(..., description="CSRF protection state token (include in callback)")


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

    status: Literal["linked", "unlinked"] = Field(..., description="Link operation result")
    provider: str = Field(..., description="OAuth provider name")
    provider_user_id: str | None = Field(default=None, description="User ID from the OAuth provider")


class OAuthLoginCallbackRequest(BaseModel):
    """OAuth login callback request (unauthenticated)."""

    code: str = Field(..., description="Authorization code from provider")
    state: str = Field(..., description="CSRF state token")
    redirect_uri: str = Field(..., description="Redirect URI used in authorization")


class OAuthLoginUserResponse(BaseModel):
    """User info in OAuth login response."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    login: str
    email: str | None = None
    is_active: bool
    is_email_verified: bool = False
    created_at: datetime


class OAuthLoginResponse(BaseModel):
    """Response for OAuth login (unauthenticated)."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int = 0
    user: OAuthLoginUserResponse
    is_new_user: bool = False
    requires_2fa: bool = False
    tfa_token: str | None = None
