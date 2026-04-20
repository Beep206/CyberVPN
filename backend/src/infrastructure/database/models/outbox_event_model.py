"""Canonical outbox event models for Phase 7 reporting foundations."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.infrastructure.database.session import Base


class OutboxEventModel(Base):
    __tablename__ = "outbox_events"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    event_key: Mapped[str] = mapped_column(String(160), nullable=False, unique=True, index=True)
    event_name: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    event_family: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    aggregate_type: Mapped[str] = mapped_column(String(60), nullable=False, index=True)
    aggregate_id: Mapped[str] = mapped_column(String(160), nullable=False, index=True)
    partition_key: Mapped[str] = mapped_column(String(160), nullable=False, index=True)
    schema_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default="1")
    event_status: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default="pending_publication",
        server_default="pending_publication",
        index=True,
    )
    event_payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    actor_context: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    source_context: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    publications: Mapped[list[OutboxPublicationModel]] = relationship(
        back_populates="outbox_event",
        cascade="all, delete-orphan",
        lazy="selectin",
    )


class OutboxPublicationModel(Base):
    __tablename__ = "outbox_publications"
    __table_args__ = (
        UniqueConstraint("outbox_event_id", "consumer_key", name="uq_outbox_publications_event_consumer"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    outbox_event_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("outbox_events.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    consumer_key: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    publication_status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="pending",
        server_default="pending",
        index=True,
    )
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    lease_owner: Mapped[str | None] = mapped_column(String(120), nullable=True, index=True)
    leased_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    next_attempt_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    publication_payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    outbox_event: Mapped[OutboxEventModel] = relationship(back_populates="publications", lazy="raise")
