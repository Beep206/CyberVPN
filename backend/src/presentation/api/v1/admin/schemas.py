"""Admin API schemas."""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class AuditLogResponse(BaseModel):
    """Response schema for audit log entry."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    admin_id: UUID | None = None
    action: str
    entity_type: str | None = None
    entity_id: str | None = None
    old_value: dict[str, Any] | None = None
    new_value: dict[str, Any] | None = None
    ip_address: str | None = None
    user_agent: str | None = None
    created_at: datetime


class WebhookLogResponse(BaseModel):
    """Response schema for webhook log entry."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    source: str
    event_type: str | None = None
    payload: dict[str, Any]
    is_valid: bool | None = None
    error_message: str | None = None
    processed_at: datetime | None = None
    created_at: datetime


class AdminSettingsResponse(BaseModel):
    """Response schema for admin settings."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    key: str
    value: Any
    description: str | None = None
    updated_at: datetime
