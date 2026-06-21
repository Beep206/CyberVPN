"""Partner attribution capture session ORM model."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import JSON, DateTime, ForeignKey, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from src.infrastructure.database.session import Base


class PartnerAttributionSessionModel(Base):
    """Opaque public-click session that can be claimed by an authenticated customer."""

    __tablename__ = "partner_attribution_sessions"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_token_hash: Mapped[str | None] = mapped_column(String(128), nullable=True, unique=True, index=True)
    transfer_token_hash: Mapped[str | None] = mapped_column(String(128), nullable=True, unique=True, index=True)
    consumed_transfer_token_hash: Mapped[str | None] = mapped_column(
        String(128), nullable=True, unique=True, index=True
    )
    transfer_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    transfer_consumed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    partner_code_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("partner_codes.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    partner_code_link_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("partner_code_links.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    partner_account_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("partner_accounts.id", ondelete="SET NULL"),
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
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="pending", server_default="pending")
    owner_type: Mapped[str] = mapped_column(String(30), nullable=False, default="affiliate", server_default="affiliate")
    attribution_model: Mapped[str] = mapped_column(
        String(40),
        nullable=False,
        default="last_eligible_touch",
        server_default="last_eligible_touch",
    )
    policy_version_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("policy_versions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    commission_contract_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("partner_commission_contracts.id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )
    source_host: Mapped[str | None] = mapped_column(String(255), nullable=True)
    source_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    destination_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    locale: Mapped[str] = mapped_column(String(16), nullable=False, default="ru-RU", server_default="ru-RU")
    sale_channel: Mapped[str | None] = mapped_column(String(40), nullable=True, index=True)
    sub_ids: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    click_id: Mapped[str | None] = mapped_column(String(160), nullable=True, index=True)
    browser_key_hash: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    capture_idempotency_key_hash: Mapped[str | None] = mapped_column(
        String(128), nullable=True, unique=True, index=True
    )
    destination_url: Mapped[str] = mapped_column(String(1000), nullable=False)
    campaign_params: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    evidence_payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    policy_snapshot: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    rejection_reason_code: Mapped[str | None] = mapped_column(String(80), nullable=True)
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("mobile_users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    touchpoint_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("attribution_touchpoints.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    binding_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("customer_commercial_bindings.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    first_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    transferred_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    claimed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        index=True,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )
