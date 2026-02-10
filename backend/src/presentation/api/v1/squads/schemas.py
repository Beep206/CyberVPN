"""Squad API schemas for Remnawave proxy."""

from pydantic import BaseModel, ConfigDict, Field


class CreateSquadRequest(BaseModel):
    """Request schema for creating a squad."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "name": "Premium Users",
                "squad_type": "internal",
                "max_members": 100,
                "is_active": True,
            }
        }
    )

    name: str = Field(..., min_length=1, max_length=100, description="Squad name")
    squad_type: str = Field(..., min_length=1, max_length=50, description="Squad type (internal/external)")
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
