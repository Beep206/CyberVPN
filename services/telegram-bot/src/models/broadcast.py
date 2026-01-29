"""Broadcast DTO models for telegram-bot service.

This module contains Pydantic models for broadcast messaging to users.
"""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field


class BroadcastStatus(StrEnum):
    """Broadcast status enumeration."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    ERROR = "error"


class BroadcastButton(BaseModel):
    """Broadcast message inline button.

    Attributes:
        text: Button text displayed to user
        url: URL to open when button is clicked (optional)
        callback_data: Callback data for inline button handlers (optional)
    """

    model_config = ConfigDict(from_attributes=True, frozen=True)

    text: str = Field(..., min_length=1, max_length=100, description="Button text")
    url: str | None = Field(None, description="Button URL")
    callback_data: str | None = Field(None, description="Callback data")


class BroadcastAudience(StrEnum):
    """Broadcast audience type enumeration."""

    ALL = "all"
    ACTIVE = "active"
    EXPIRED = "expired"
    NEVER_PAID = "never_paid"
    CUSTOM = "custom"


class BroadcastDTO(BaseModel):
    """Broadcast data transfer object.

    Attributes:
        id: Unique broadcast identifier
        status: Current broadcast status
        audience_type: Target audience type
        custom_user_ids: List of specific Telegram IDs for CUSTOM audience
        content: Message content (supports HTML formatting)
        buttons: List of inline keyboard buttons (max 2 rows)
        media_url: Optional media URL (photo/video/document)
        media_type: Media type if media_url is provided
        total_users: Total number of target users
        sent_count: Number of successfully sent messages
        failed_count: Number of failed sends
        created_at: Broadcast creation timestamp
        started_at: Broadcast start timestamp
        completed_at: Broadcast completion timestamp
        created_by: Telegram ID of admin who created broadcast
        error_message: Error message if status is ERROR
    """

    model_config = ConfigDict(from_attributes=True, frozen=True)

    id: str = Field(..., description="Unique broadcast identifier")
    status: BroadcastStatus = Field(default=BroadcastStatus.PENDING, description="Broadcast status")
    audience_type: BroadcastAudience = Field(..., description="Target audience type")
    custom_user_ids: list[int] = Field(default_factory=list, description="Custom audience Telegram IDs")
    content: str = Field(..., min_length=1, max_length=4096, description="Message content (HTML)")
    buttons: list[list[BroadcastButton]] = Field(
        default_factory=list, max_length=2, description="Inline keyboard buttons (max 2 rows)"
    )
    media_url: str | None = Field(None, description="Media URL")
    media_type: Literal["photo", "video", "document"] | None = Field(None, description="Media type")
    total_users: Annotated[int, Field(ge=0, description="Total target users")]
    sent_count: Annotated[int, Field(ge=0, description="Successfully sent count")] = 0
    failed_count: Annotated[int, Field(ge=0, description="Failed sends count")] = 0
    created_at: datetime = Field(..., description="Creation timestamp")
    started_at: datetime | None = Field(None, description="Start timestamp")
    completed_at: datetime | None = Field(None, description="Completion timestamp")
    created_by: int = Field(..., description="Creator Telegram ID")
    error_message: str | None = Field(None, description="Error message")


class BroadcastStats(BaseModel):
    """Broadcast statistics summary.

    Attributes:
        total_broadcasts: Total number of broadcasts created
        pending_broadcasts: Number of pending broadcasts
        running_broadcasts: Number of currently running broadcasts
        completed_broadcasts: Number of completed broadcasts
        total_messages_sent: Total messages sent across all broadcasts
        average_success_rate: Average success rate percentage
    """

    model_config = ConfigDict(from_attributes=True, frozen=True)

    total_broadcasts: Annotated[int, Field(ge=0, description="Total broadcasts")]
    pending_broadcasts: Annotated[int, Field(ge=0, description="Pending broadcasts")]
    running_broadcasts: Annotated[int, Field(ge=0, description="Running broadcasts")]
    completed_broadcasts: Annotated[int, Field(ge=0, description="Completed broadcasts")]
    total_messages_sent: Annotated[int, Field(ge=0, description="Total messages sent")]
    average_success_rate: Annotated[float, Field(ge=0, le=100, description="Average success rate %")]
