"""Configuration snippet API schemas for Remnawave proxy."""

from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class CreateSnippetRequest(BaseModel):
    """Request schema for creating a configuration snippet."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "name": "CDN Headers",
                "snippet_type": "header",
                "content": "Host: cloudflare.com",
                "is_active": True,
            }
        }
    )

    name: str = Field(..., min_length=1, max_length=100, description="Snippet name")
    snippet_type: str = Field(
        ..., min_length=1, max_length=50, description="Snippet type"
    )
    content: str = Field(
        ..., min_length=1, max_length=50_000, description="Snippet content"
    )
    is_active: bool = Field(True, description="Whether snippet is active")
    order: Optional[int] = Field(None, ge=0, description="Display/execution order")
