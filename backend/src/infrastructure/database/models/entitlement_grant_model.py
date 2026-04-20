"""Canonical entitlement grant ORM model."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import JSON, DateTime, ForeignKey, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from src.infrastructure.database.session import Base


class EntitlementGrantModel(Base):
    __tablename__ = "entitlement_grants"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    grant_key: Mapped[str] = mapped_column(String(160), nullable=False, unique=True, index=True)
    service_identity_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("service_identities.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    customer_account_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("mobile_users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    auth_realm_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("auth_realms.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    origin_storefront_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("storefronts.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    source_type: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    source_order_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("orders.id", ondelete="SET NULL"),
        nullable=True,
        unique=True,
        index=True,
    )
    source_growth_reward_allocation_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("growth_reward_allocations.id", ondelete="SET NULL"),
        nullable=True,
        unique=True,
        index=True,
    )
    source_renewal_order_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("renewal_orders.id", ondelete="SET NULL"),
        nullable=True,
        unique=True,
        index=True,
    )
    manual_source_key: Mapped[str | None] = mapped_column(String(160), nullable=True, unique=True, index=True)
    grant_status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="pending",
        server_default="pending",
        index=True,
    )
    grant_snapshot: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    source_snapshot: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    effective_from: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    created_by_admin_user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("admin_users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    activated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    activated_by_admin_user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("admin_users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    suspended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    suspended_by_admin_user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("admin_users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    suspension_reason_code: Mapped[str | None] = mapped_column(String(80), nullable=True)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    revoked_by_admin_user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("admin_users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    revoke_reason_code: Mapped[str | None] = mapped_column(String(80), nullable=True)
    expired_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    expired_by_admin_user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("admin_users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    expiry_reason_code: Mapped[str | None] = mapped_column(String(80), nullable=True)
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
