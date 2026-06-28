"""Typed Telegram connection bootstrap contracts."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

ConnectionPlatform = Literal["ios", "android", "windows", "macos", "linux", "unknown"]
ConnectionStatus = Literal[
    "available",
    "no_active_entitlement",
    "service_identity_pending",
    "config_unavailable",
    "disabled",
]


class ConnectionInstructionStep(BaseModel):
    """Single backend-provided connection instruction step."""

    model_config = ConfigDict(extra="ignore")

    order: int = Field(ge=1, le=6)
    title_key: str | None = None
    body_key: str | None = None
    title: str | None = None
    body: str | None = None


class ConnectionInstruction(BaseModel):
    """Connection instructions for one client platform."""

    model_config = ConfigDict(extra="ignore")

    platform: ConnectionPlatform
    title_key: str | None = None
    body_key: str | None = None
    steps: list[ConnectionInstructionStep] = Field(default_factory=list, max_length=6)


class TelegramConnectionPayload(BaseModel):
    """Telegram-specific backend connection payload metadata."""

    model_config = ConfigDict(extra="ignore")

    intro_message_key: str | None = None
    safe_profile_label: str | None = None
    subscription_url_button_text_key: str = "onboarding.connection.openLink"
    instructions_button_text_key: str = "onboarding.connection.instructions"
    mark_connected_button_text_key: str = "onboarding.connection.connected"
    dashboard_button_text_key: str = "onboarding.connection.goDashboard"
    qr_caption_key: str = "onboarding.connection.qrCaption"
    bot_connection_session_id: str | None = None
    message_key: str | None = None
    preferred_platform: ConnectionPlatform = "unknown"


class ConnectionBootstrapResponse(BaseModel):
    """Response from the shared customer connection bootstrap endpoint."""

    model_config = ConfigDict(extra="ignore")

    status: ConnectionStatus
    available: bool = False
    message_key: str | None = None
    subscription_url: str | None = None
    qr_payload: str | None = None
    instructions: list[ConnectionInstruction] = Field(default_factory=list)
    surface: str = "telegram_bot"
    preferred_layout: str | None = None
    supported_actions: list[str] = Field(default_factory=list)
    telegram_payload: TelegramConnectionPayload | None = None
    config_profile_name: str | None = None
    flow_key: str | None = None
    version: int | None = None
    connection_session_id: str | None = None

    @field_validator("available", mode="before")
    @classmethod
    def _coerce_available(cls, value: object) -> bool:
        if isinstance(value, bool):
            return value
        if value is None:
            return False
        return bool(value)

    @property
    def has_private_payload(self) -> bool:
        """Whether a private chat can reveal a connection URL or QR payload."""
        return bool(self.subscription_url or self.qr_payload)


class MarkConnectedResponse(BaseModel):
    """Response from the shared mark-connected endpoint."""

    model_config = ConfigDict(extra="ignore")

    status: str = "accepted"
    connected_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    flow_key: str | None = None
    version: int | None = None


class ConnectionSession(BaseModel):
    """Short-lived Telegram callback session without raw config payloads."""

    model_config = ConfigDict(extra="forbid")

    session_id: str = Field(min_length=8, max_length=24)
    telegram_id: int
    platform_hint: ConnectionPlatform = "unknown"
    flow_key: str | None = None
    version: int | None = None
    backend_connection_session_id: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
