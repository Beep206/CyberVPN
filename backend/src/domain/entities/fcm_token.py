"""FCM token domain entity."""

from dataclasses import dataclass
from datetime import datetime
from typing import Literal
from uuid import UUID


@dataclass(frozen=True)
class FCMToken:
    """Firebase Cloud Messaging token for push notifications.

    Each user can have multiple tokens (one per device).
    Tokens are uniquely identified by (user_id, device_id).
    """

    id: UUID
    user_id: UUID
    token: str
    device_id: str
    platform: Literal["android", "ios"]
    created_at: datetime
    updated_at: datetime
