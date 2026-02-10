"""WebSocket message schemas (HIGH-3)."""

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


class WSSubscribeMessage(BaseModel):
    """Client message to subscribe to monitoring topics."""

    type: Literal["subscribe"] = Field("subscribe", description="Message type")
    topics: list[str] = Field(..., max_length=20, description="List of topics to subscribe to")


class WSNotification(BaseModel):
    """Server-sent notification message."""

    type: str = Field(..., max_length=50, description="Notification type")
    data: dict[str, Any] = Field(..., description="Notification payload")
    timestamp: datetime = Field(..., description="Notification timestamp")


class WSTicketResponse(BaseModel):
    """Response containing a WebSocket authentication ticket."""

    ticket: str = Field(..., description="Single-use WebSocket ticket (valid for 30 seconds)")
    expires_in: int = Field(30, description="Seconds until ticket expires")


class WSTicketRequest(BaseModel):
    """Optional request body for ticket creation."""

    # Could be extended with additional fields like preferred_topics
    pass
