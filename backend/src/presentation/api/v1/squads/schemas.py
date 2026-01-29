"""Squad API schemas for Remnawave proxy."""

from typing import Optional

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
    squad_type: str = Field(
        ..., min_length=1, max_length=50, description="Squad type (internal/external)"
    )
    max_members: Optional[int] = Field(
        None, ge=1, le=10_000, description="Maximum squad members"
    )
    is_active: bool = Field(True, description="Whether squad is active")
    description: Optional[str] = Field(
        None, max_length=500, description="Squad description"
    )
