"""Append-only attribution touchpoint ORM model."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import JSON, DateTime, ForeignKey, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from src.infrastructure.database.session import Base


class AttributionTouchpointModel(Base):
    __tablename__ = "attribution_touchpoints"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    touchpoint_type: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("mobile_users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    auth_realm_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("auth_realms.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    storefront_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("storefronts.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    quote_session_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("quote_sessions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    checkout_session_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("checkout_sessions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    order_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("orders.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    partner_code_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("partner_codes.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    sale_channel: Mapped[str | None] = mapped_column(String(30), nullable=True, index=True)
    source_host: Mapped[str | None] = mapped_column(String(255), nullable=True)
    source_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    campaign_params: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    evidence_payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
    )
