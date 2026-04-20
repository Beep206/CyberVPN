"""Immutable order attribution result ORM model."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import JSON, DateTime, ForeignKey, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from src.infrastructure.database.session import Base


class OrderAttributionResultModel(Base):
    __tablename__ = "order_attribution_results"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    order_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("orders.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("mobile_users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    auth_realm_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("auth_realms.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    storefront_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("storefronts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    owner_type: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    owner_source: Mapped[str | None] = mapped_column(String(40), nullable=True, index=True)
    partner_account_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("partner_accounts.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    partner_code_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("partner_codes.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    winning_touchpoint_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("attribution_touchpoints.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    winning_binding_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("customer_commercial_bindings.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    rule_path: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    evidence_snapshot: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    explainability_snapshot: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    policy_snapshot: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    resolved_at: Mapped[datetime] = mapped_column(
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
