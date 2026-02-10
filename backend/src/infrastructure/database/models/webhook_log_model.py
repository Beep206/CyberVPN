"""WebhookLog ORM model for webhook event tracking and debugging."""

from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import Boolean, DateTime, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from src.infrastructure.database.session import Base


class WebhookLog(Base):
    """
    Webhook log model for tracking incoming webhook events.

    Stores webhook payloads, signatures, and processing status for
    debugging and audit purposes.
    """

    __tablename__ = "webhook_logs"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4, nullable=False)

    source: Mapped[str] = mapped_column(String(50), nullable=False, index=True)

    event_type: Mapped[str | None] = mapped_column(String(100), nullable=True)

    payload: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)

    signature: Mapped[str | None] = mapped_column(String(255), nullable=True)

    is_valid: Mapped[bool | None] = mapped_column(Boolean, nullable=True)

    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )

    def __repr__(self) -> str:
        return f"<WebhookLog(id={self.id}, source='{self.source}', event_type='{self.event_type}')>"
