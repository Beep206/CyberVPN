"""Audit-safe public schemas for the CyberVPN Remnawave Node SSH boundary."""

from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class _AdminRemnawaveNodeSshReasonRequest(BaseModel):
    reason: str = Field(min_length=8, max_length=256)

    @field_validator("reason", mode="before")
    @classmethod
    def strip_reason_before_length_validation(cls, value: object) -> object:
        return value.strip() if isinstance(value, str) else value


class AdminRemnawaveNodeSshTicketRequest(_AdminRemnawaveNodeSshReasonRequest):
    pass


class AdminRemnawaveNodeSshTicketResponse(BaseModel):
    ticket: str = Field(min_length=32, max_length=96)
    node_uuid: UUID
    websocket_path: str
    websocket_protocol: str
    expires_in_seconds: int = Field(ge=1, le=15)


class AdminRemnawaveNodeSshRevokeRequest(_AdminRemnawaveNodeSshReasonRequest):
    ticket: str = Field(min_length=32, max_length=96, pattern=r"^[A-Za-z0-9_-]+$")


class AdminRemnawaveNodeSshVaultEvaluateRequest(BaseModel):
    blinded: str = Field(min_length=1, max_length=128, pattern=r"^[A-Za-z0-9+/]*={0,2}$")


class AdminRemnawaveNodeSshVaultEvaluateResponse(BaseModel):
    evaluated: str = Field(min_length=1, max_length=512, pattern=r"^[A-Za-z0-9+/]*={0,2}$")
