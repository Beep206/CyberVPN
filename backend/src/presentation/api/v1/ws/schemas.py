"""WebSocket message schemas."""

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


class WSSubscribeMessage(BaseModel):
    """Client message to subscribe to monitoring topics."""

    type: Literal["subscribe"] = Field("subscribe", description="Message type")
    topics: list[str] = Field(
        ..., max_length=20, description="List of topics to subscribe to"
    )


class WSNotification(BaseModel):
    """Server-sent notification message."""

    type: str = Field(..., max_length=50, description="Notification type")
    data: dict[str, Any] = Field(..., description="Notification payload")
    timestamp: datetime = Field(..., description="Notification timestamp")
