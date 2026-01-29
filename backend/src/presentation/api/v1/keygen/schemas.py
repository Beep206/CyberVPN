"""Keygen API schemas for Remnawave proxy."""

from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class SignPayloadRequest(BaseModel):
    """Request schema for signing a payload."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "payload": "data_to_sign",
                "algorithm": "RS256",
            }
        }
    )

    payload: str = Field(
        ..., min_length=1, max_length=10_000, description="Payload to sign"
    )
    algorithm: Optional[str] = Field(
        "RS256", max_length=20, description="Signing algorithm"
    )
