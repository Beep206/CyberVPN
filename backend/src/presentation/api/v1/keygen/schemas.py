"""Keygen API schemas for Remnawave proxy."""

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

    payload: str = Field(..., min_length=1, max_length=10_000, description="Payload to sign")
    algorithm: str | None = Field("RS256", max_length=20, description="Signing algorithm")


class PublicKeyResponse(BaseModel):
    """Expected response for public key retrieval."""

    model_config = ConfigDict(from_attributes=True)

    public_key: str = Field(..., description="Public key in PEM format")
    algorithm: str = Field(..., max_length=20, description="Key algorithm")


class SignPayloadResponse(BaseModel):
    """Expected response from payload signing."""

    model_config = ConfigDict(from_attributes=True)

    signature: str = Field(..., description="Generated signature")
    algorithm: str = Field(..., max_length=20, description="Signing algorithm used")
