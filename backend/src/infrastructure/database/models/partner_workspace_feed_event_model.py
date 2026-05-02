from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import JSON, DateTime, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from src.infrastructure.database.session import Base


class PartnerWorkspaceFeedEventModel(Base):
    __tablename__ = "partner_workspace_feed_events"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workspace_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), nullable=False, index=True)
    event_key: Mapped[str] = mapped_column(String(160), nullable=False, unique=True, index=True)
    event_name: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    event_family: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    aggregate_type: Mapped[str] = mapped_column(String(60), nullable=False, index=True)
    aggregate_id: Mapped[str] = mapped_column(String(160), nullable=False, index=True)
    consumer_key: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    subject: Mapped[str] = mapped_column(String(255), nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
    )
