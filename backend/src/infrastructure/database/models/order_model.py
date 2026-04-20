"""Canonical order ORM models."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import JSON, DateTime, ForeignKey, Numeric, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.infrastructure.database.session import Base


class OrderModel(Base):
    __tablename__ = "orders"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    quote_session_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("quote_sessions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    checkout_session_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("checkout_sessions.id", ondelete="CASCADE"),
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
    merchant_profile_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("merchant_profiles.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    invoice_profile_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("invoice_profiles.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    billing_descriptor_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("billing_descriptors.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    pricebook_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("pricebook_versions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    pricebook_entry_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("pricebook_entries.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    offer_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("offer_versions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    legal_document_set_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("storefront_legal_doc_sets.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    program_eligibility_policy_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("program_eligibility_versions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    subscription_plan_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("subscription_plans.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    promo_code_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True, index=True)
    partner_code_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True, index=True)
    sale_channel: Mapped[str] = mapped_column(String(30), nullable=False, default="web", server_default="web")
    currency_code: Mapped[str] = mapped_column(String(12), nullable=False, default="USD", server_default="USD")
    order_status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="committed", server_default="committed", index=True
    )
    settlement_status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="pending_payment", server_default="pending_payment", index=True
    )
    base_price: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    addon_amount: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False, default=0, server_default="0")
    displayed_price: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    discount_amount: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False, default=0, server_default="0")
    wallet_amount: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False, default=0, server_default="0")
    gateway_amount: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False, default=0, server_default="0")
    partner_markup: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False, default=0, server_default="0")
    commission_base_amount: Mapped[float] = mapped_column(
        Numeric(12, 2), nullable=False, default=0, server_default="0"
    )
    merchant_snapshot: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    pricing_snapshot: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    policy_snapshot: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    entitlements_snapshot: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
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

    items: Mapped[list[OrderItemModel]] = relationship(
        back_populates="order",
        cascade="all, delete-orphan",
        lazy="selectin",
    )


class OrderItemModel(Base):
    __tablename__ = "order_items"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    order_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("orders.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    item_type: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    subject_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True, index=True)
    subject_code: Mapped[str | None] = mapped_column(String(80), nullable=True, index=True)
    display_name: Mapped[str] = mapped_column(String(200), nullable=False)
    quantity: Mapped[int] = mapped_column(nullable=False, default=1, server_default="1")
    unit_price: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    total_price: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    currency_code: Mapped[str] = mapped_column(String(12), nullable=False, default="USD", server_default="USD")
    item_snapshot: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
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

    order: Mapped[OrderModel] = relationship(back_populates="items", lazy="raise")
