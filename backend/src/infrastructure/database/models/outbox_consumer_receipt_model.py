from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import JSON, DateTime, String, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from src.infrastructure.database.session import Base


class OutboxConsumerReceiptModel(Base):
    __tablename__ = "outbox_consumer_receipts"
    __table_args__ = (
        UniqueConstraint("consumer_key", "event_key", name="uq_outbox_consumer_receipts_consumer_event"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    consumer_key: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    event_key: Mapped[str] = mapped_column(String(160), nullable=False, index=True)
    event_name: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    subject: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="processed", server_default="processed")
    metadata_payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    processed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
    )
