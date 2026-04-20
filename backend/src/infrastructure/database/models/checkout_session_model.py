"""Checkout session ORM model for order-commit preparation."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import JSON, DateTime, ForeignKey, String, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from src.infrastructure.database.session import Base


class CheckoutSessionModel(Base):
    __tablename__ = "checkout_sessions"
    __table_args__ = (
        UniqueConstraint("quote_session_id", name="uq_checkout_sessions_quote_session_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    quote_session_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("quote_sessions.id", ondelete="CASCADE"),
        nullable=False,
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
    sale_channel: Mapped[str] = mapped_column(String(30), nullable=False, default="web", server_default="web")
    currency_code: Mapped[str] = mapped_column(String(12), nullable=False, default="USD", server_default="USD")
    checkout_status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="open", server_default="open", index=True
    )
    idempotency_key: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    promo_code_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True, index=True)
    partner_code_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True, index=True)
    request_snapshot: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    checkout_snapshot: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    context_snapshot: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
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
