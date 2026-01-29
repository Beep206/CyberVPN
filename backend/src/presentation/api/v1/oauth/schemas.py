"""OAuth social account linking API schemas."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class OAuthAuthorizeResponse(BaseModel):
    """Response containing OAuth authorization URL."""

    model_config = ConfigDict(from_attributes=True)

    authorize_url: str = Field(
        ..., max_length=2000, description="OAuth provider authorization URL"
    )


class OAuthLinkResponse(BaseModel):
    """Response for account link/unlink operations."""

    model_config = ConfigDict(from_attributes=True)

    status: Literal["linked", "unlinked"] = Field(
        ..., description="Link operation result"
    )
    provider: Literal["telegram", "github"] = Field(
        ..., description="OAuth provider name"
    )
