"""Configuration profile API schemas for Remnawave proxy."""

from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class CreateConfigProfileRequest(BaseModel):
    """Request schema for creating a configuration profile."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "name": "Mobile Optimized",
                "profile_type": "clash",
                "content": "# Clash config content here",
                "is_default": False,
            }
        }
    )

    name: str = Field(..., min_length=1, max_length=100, description="Profile name")
    profile_type: str = Field(
        ..., min_length=1, max_length=50, description="Profile type"
    )
    content: str = Field(
        ..., min_length=1, max_length=100_000, description="Profile content/template"
    )
    is_default: bool = Field(False, description="Whether this is the default profile")
    description: Optional[str] = Field(
        None, max_length=500, description="Profile description"
    )
