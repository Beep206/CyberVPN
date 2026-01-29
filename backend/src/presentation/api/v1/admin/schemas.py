"""Admin API schemas."""

from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class AuditLogResponse(BaseModel):
    """Response schema for audit log entry."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: Optional[UUID] = None
    username: Optional[str] = None
    action: str
    resource_type: str
    resource_id: Optional[str] = None
    details: Optional[dict[str, Any]] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    created_at: datetime


class WebhookLogResponse(BaseModel):
    """Response schema for webhook log entry."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    source: str
    event_type: str
    payload: dict[str, Any]
    status: str
    error_message: Optional[str] = None
    processed_at: Optional[datetime] = None
    created_at: datetime


class AdminSettingsResponse(BaseModel):
    """Response schema for admin settings."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    key: str
    value: Any
    description: Optional[str] = None
    updated_at: datetime
