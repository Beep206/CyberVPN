"""Webhook log model for external event tracking."""

from datetime import datetime
from typing import Any, Optional
from uuid import UUID, uuid4

from sqlalchemy import Boolean, DateTime, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from src.database.session import Base


class WebhookLogModel(Base):
    """
    Webhook event log for external integrations.

    Stores incoming webhook payloads from payment providers and other services,
    including validation status and processing results.
    """

    __tablename__ = "webhook_logs"

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid4, nullable=False
    )
    source: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    event_type: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    signature: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    is_valid: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    processed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )

    def __repr__(self) -> str:
        return f"<WebhookLogModel(id={self.id}, source='{self.source}', event_type='{self.event_type}')>"
