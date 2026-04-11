"""Schemas for customer support operations in admin."""

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from src.shared.validators.password import validate_password_strength

from .mobile_users_schemas import AdminMobileDeviceResponse


class AdminSupportActorSummary(BaseModel):
    id: UUID | None = None
    login: str | None = None
    email: str | None = None
    display_name: str | None = None


class AdminCustomerStaffNoteResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    admin_id: UUID | None
    category: str
    note: str
    created_at: datetime
    updated_at: datetime
    author: AdminSupportActorSummary | None = None


class AdminCreateCustomerStaffNoteRequest(BaseModel):
    category: Literal["general", "billing", "security", "support"] = "general"
    note: str = Field(..., min_length=1, max_length=4000)


class AdminCustomerSupportActionRequest(BaseModel):
    reason: str | None = Field(None, max_length=1000)


class AdminCustomerPasswordResetRequest(BaseModel):
    new_password: str | None = Field(None, min_length=12, max_length=128)
    generate_temporary_password: bool = False
    revoke_all_devices: bool = True
    reason: str | None = Field(None, max_length=1000)

    @field_validator("new_password")
    @classmethod
    def validate_password(cls, value: str | None) -> str | None:
        if value is None:
            return value
        return validate_password_strength(value)

    @model_validator(mode="after")
    def validate_reset_mode(self) -> "AdminCustomerPasswordResetRequest":
        if self.generate_temporary_password and self.new_password:
            raise ValueError("Provide either a custom password or generate a temporary password, not both.")

        if not self.generate_temporary_password and not self.new_password:
            raise ValueError("Provide a custom password or enable temporary password generation.")

        return self


class AdminBulkDeviceRevokeResponse(BaseModel):
    user_id: UUID
    revoked_count: int = 0
    revoked_devices: list[AdminMobileDeviceResponse] = Field(default_factory=list)


class AdminCustomerPasswordResetResponse(BaseModel):
    user_id: UUID
    password_mode: Literal["provided", "generated"]
    device_sessions_cleared: bool = False
    devices_revoked: int = 0
    generated_password: str | None = None


class AdminCustomerSubscriptionResyncResponse(BaseModel):
    user_id: UUID
    previous_subscription_url: str | None = None
    stored_subscription_url: str | None = None
    upstream_subscription_url: str
    changed: bool = False
    config_available: bool = False
    config_client_type: str | None = None
    links_count: int = 0


class AdminCustomerVpnUserResponse(BaseModel):
    exists: bool
    remnawave_uuid: UUID | None = None
    username: str | None = None
    email: str | None = None
    status: str | None = None
    short_uuid: str | None = None
    subscription_uuid: UUID | None = None
    expire_at: datetime | None = None
    traffic_limit_bytes: int | None = None
    used_traffic_bytes: int | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    telegram_id: int | None = None


class AdminCustomerTimelineItemResponse(BaseModel):
    id: str
    kind: Literal["payment", "wallet_transaction", "withdrawal", "device", "note", "audit"]
    occurred_at: datetime
    title: str
    description: str | None = None
    status: str | None = None
    amount: float | None = None
    currency: str | None = None
    actor_label: str | None = None
    metadata: dict[str, Any] | None = None


class AdminCustomerTimelineResponse(BaseModel):
    items: list[AdminCustomerTimelineItemResponse]
