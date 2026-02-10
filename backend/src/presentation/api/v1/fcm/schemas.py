"""Pydantic schemas for FCM token management endpoints."""

from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class FCMTokenRequest(BaseModel):
    """Request body for registering an FCM push-notification token.

    Sent by mobile clients after obtaining a token from Firebase.
    Each ``(device_id, platform)`` pair identifies a unique device.
    """

    model_config = ConfigDict(from_attributes=True)

    token: str = Field(
        ...,
        min_length=1,
        max_length=4096,
        description="FCM registration token obtained from Firebase SDK",
    )
    device_id: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Unique device identifier (e.g. Android ID, IDFV)",
    )
    platform: Literal["android", "ios"] = Field(
        ...,
        description="Mobile platform that generated the token",
    )


class FCMTokenDeleteRequest(BaseModel):
    """Request body for unregistering an FCM push-notification token.

    Sent by mobile clients on logout or when the user disables
    push notifications.
    """

    model_config = ConfigDict(from_attributes=True)

    device_id: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Device identifier whose token should be removed",
    )


class FCMTokenResponse(BaseModel):
    """Response returned after a successful FCM token registration."""

    model_config = ConfigDict(from_attributes=True)

    token: str = Field(
        ...,
        description="Registered FCM token",
    )
    device_id: str = Field(
        ...,
        description="Device identifier associated with the token",
    )
    platform: str = Field(
        ...,
        description="Mobile platform (android / ios)",
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="Timestamp when the token was registered (ISO 8601)",
    )
