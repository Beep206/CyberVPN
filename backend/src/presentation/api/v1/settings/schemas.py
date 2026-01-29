"""System settings API schemas for Remnawave proxy."""

from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field


class CreateSettingRequest(BaseModel):
    """Request schema for creating a system setting."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "key": "max_devices_per_user",
                "value": 5,
                "description": "Maximum devices allowed per user",
            }
        }
    )

    key: str = Field(
        ..., min_length=1, max_length=100, description="Setting key"
    )
    value: Any = Field(..., description="Setting value (any JSON type)")
    description: Optional[str] = Field(
        None, max_length=500, description="Setting description"
    )
    is_public: bool = Field(
        False, description="Whether setting is publicly readable"
    )


class UpdateSettingRequest(BaseModel):
    """Request schema for updating a system setting."""

    value: Optional[Any] = Field(None, description="New setting value")
    description: Optional[str] = Field(None, max_length=500)
    is_public: Optional[bool] = None
