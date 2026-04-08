"""Squad API schemas for Remnawave proxy."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class CreateSquadRequest(BaseModel):
    """Request schema for creating a squad."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "name": "Premium Users",
                "squad_type": "internal",
                "inbounds": ["985d2bf6-b0c5-4299-8c75-bd78422bb47d"],
            }
        }
    )

    name: str = Field(..., min_length=1, max_length=100, description="Squad name")
    squad_type: Literal["internal", "external"] = Field(..., description="Squad type")
    inbounds: list[str] = Field(default_factory=list, description="Internal squad inbound UUIDs")
    max_members: int | None = Field(None, ge=1, le=10_000, description="Maximum squad members")
    is_active: bool = Field(True, description="Whether squad is active")
    description: str | None = Field(None, max_length=500, description="Squad description")


class SquadResponse(BaseModel):
    """Expected response from Remnawave squads API."""

    model_config = ConfigDict(from_attributes=True)

    uuid: str = Field(..., description="Squad UUID")
    name: str = Field(..., max_length=100, description="Squad name")
    squad_type: str = Field(..., max_length=50, description="Squad type")
    max_members: int | None = Field(None, description="Maximum squad members")
    is_active: bool = Field(..., description="Whether squad is active")
    description: str | None = Field(None, max_length=500, description="Squad description")
    member_count: int | None = Field(None, description="Current member count")
