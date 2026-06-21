"""Partner workspace, code, and earning ORM models."""

import secrets
import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Integer, Numeric, String, UniqueConstraint, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from src.infrastructure.database.session import Base

_PUBLIC_SLUG_ALPHABET = "abcdefghijklmnopqrstuvwxyz23456789"


def _generate_partner_public_slug_default() -> str:
    body = "".join(secrets.choice(_PUBLIC_SLUG_ALPHABET) for _ in range(24))
    return f"px_{body}"


class PartnerAccountModel(Base):
    """Canonical partner workspace root."""

    __tablename__ = "partner_accounts"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4,
    )

    account_key: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        nullable=False,
        index=True,
    )

    display_name: Mapped[str] = mapped_column(
        String(120),
        nullable=False,
    )

    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="active",
    )

    legacy_owner_user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("mobile_users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    created_by_admin_user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("admin_users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    def __repr__(self) -> str:
        return f"<PartnerAccount(id={self.id}, account_key={self.account_key}, status={self.status})>"


class PartnerCommissionContractModel(Base):
    """Immutable partner earning terms referenced by attributed orders."""

    __tablename__ = "partner_commission_contracts"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    partner_account_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("partner_accounts.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    partner_user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("mobile_users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    partner_code_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("partner_codes.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    owner_type: Mapped[str] = mapped_column(String(30), nullable=False, default="affiliate", server_default="affiliate")
    contract_status: Mapped[str] = mapped_column(String(24), nullable=False, default="active", server_default="active")
    commission_model: Mapped[str] = mapped_column(
        String(40),
        nullable=False,
        default="base_plus_markup",
        server_default="base_plus_markup",
    )
    commission_pct: Mapped[Decimal] = mapped_column(Numeric(10, 4), nullable=False, default=0, server_default="0")
    markup_pct: Mapped[Decimal] = mapped_column(Numeric(10, 4), nullable=False, default=0, server_default="0")
    markup_cap_amount: Mapped[Decimal | None] = mapped_column(Numeric(20, 8), nullable=True)
    payout_hold_days: Mapped[int] = mapped_column(Integer, nullable=False, default=30, server_default="30")
    currency_code: Mapped[str] = mapped_column(String(12), nullable=False, default="USD", server_default="USD")
    currency_policy: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    rounding_mode: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="ROUND_HALF_UP",
        server_default="ROUND_HALF_UP",
    )
    renewal_policy: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    refund_policy: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    terms_snapshot: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    source: Mapped[str] = mapped_column(
        String(60),
        nullable=False,
        default="runtime_code_create",
        server_default="runtime_code_create",
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default="1")
    effective_from: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    effective_to: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    def __repr__(self) -> str:
        return f"<PartnerCommissionContract(id={self.id}, code={self.partner_code_id}, status={self.contract_status})>"


class PartnerCodeModel(Base):
    """Partner-created referral codes with canonical partner-account ownership."""

    __tablename__ = "partner_codes"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4,
    )

    code: Mapped[str] = mapped_column(
        String(30),
        unique=True,
        nullable=False,
        index=True,
    )

    code_normalized: Mapped[str | None] = mapped_column(
        String(30),
        unique=True,
        nullable=True,
        index=True,
    )

    public_token_hash: Mapped[str | None] = mapped_column(
        String(128),
        unique=True,
        nullable=True,
        index=True,
    )

    public_slug: Mapped[str] = mapped_column(
        String(80),
        unique=True,
        nullable=False,
        index=True,
        default=_generate_partner_public_slug_default,
    )

    partner_account_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("partner_accounts.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    partner_user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("mobile_users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    code_kind: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="starter_code",
        server_default="starter_code",
    )

    lifecycle_status: Mapped[str] = mapped_column(
        String(24),
        nullable=False,
        default="active",
        server_default="active",
        index=True,
    )

    owner_type: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default="affiliate",
        server_default="affiliate",
        index=True,
    )

    lane_key: Mapped[str] = mapped_column(
        String(60),
        nullable=False,
        default="creator_affiliate",
        server_default="creator_affiliate",
        index=True,
    )

    attribution_model: Mapped[str] = mapped_column(
        String(40),
        nullable=False,
        default="last_eligible_touch",
        server_default="last_eligible_touch",
    )

    attribution_window_seconds: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=30 * 24 * 60 * 60,
        server_default=str(30 * 24 * 60 * 60),
    )

    commission_contract_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("partner_commission_contracts.id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )

    policy_version_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("policy_versions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    default_storefront_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("storefronts.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    destination_path: Mapped[str | None] = mapped_column(String(500), nullable=True)

    allowed_channels: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    allowed_storefront_ids: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    allowed_geographies: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    sub_id_schema: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)

    approval_status: Mapped[str] = mapped_column(
        String(24),
        nullable=False,
        default="approved",
        server_default="approved",
        index=True,
    )

    markup_pct: Mapped[Decimal] = mapped_column(
        Numeric(5, 2),
        nullable=False,
        default=0,
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
    )

    active_from: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    paused_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    created_by_admin_user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("admin_users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    updated_by_admin_user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("admin_users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default="1")

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    def __repr__(self) -> str:
        return f"<PartnerCode(id={self.id}, code={self.code}, markup={self.markup_pct}%)>"


class PartnerCodeLinkModel(Base):
    """Durable public link for a partner code."""

    __tablename__ = "partner_code_links"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4,
    )

    public_slug: Mapped[str] = mapped_column(
        String(80),
        unique=True,
        nullable=False,
        index=True,
    )

    partner_code_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("partner_codes.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    partner_account_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("partner_accounts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    link_kind: Mapped[str] = mapped_column(
        String(40),
        nullable=False,
        default="deep_link",
        server_default="deep_link",
        index=True,
    )

    destination_key: Mapped[str] = mapped_column(
        String(80),
        nullable=False,
        default="register",
        server_default="register",
        index=True,
    )

    destination_path: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
        default="/register",
        server_default="/register",
    )

    locale: Mapped[str | None] = mapped_column(String(16), nullable=True)
    sale_channel: Mapped[str | None] = mapped_column(String(40), nullable=True, index=True)
    campaign_params: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    sub_ids: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)

    status: Mapped[str] = mapped_column(
        String(24),
        nullable=False,
        default="active",
        server_default="active",
        index=True,
    )

    active_from: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)

    created_by_admin_user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("admin_users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class PartnerEarningModel(Base):
    """Ledger of partner earnings per client payment."""

    __tablename__ = "partner_earnings"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4,
    )

    partner_account_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("partner_accounts.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    partner_user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("mobile_users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    client_user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("mobile_users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    payment_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("payments.id", ondelete="CASCADE"),
        nullable=False,
    )

    partner_code_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("partner_codes.id", ondelete="SET NULL"),
        nullable=True,
    )

    base_price: Mapped[Decimal] = mapped_column(
        Numeric(20, 8),
        nullable=False,
    )

    markup_amount: Mapped[Decimal] = mapped_column(
        Numeric(20, 8),
        nullable=False,
    )

    commission_pct: Mapped[Decimal] = mapped_column(
        Numeric(5, 2),
        nullable=False,
    )

    commission_amount: Mapped[Decimal] = mapped_column(
        Numeric(20, 8),
        nullable=False,
    )

    total_earning: Mapped[Decimal] = mapped_column(
        Numeric(20, 8),
        nullable=False,
    )

    currency: Mapped[str] = mapped_column(
        String(10),
        nullable=False,
        default="USD",
    )

    wallet_tx_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("wallet_transactions.id", ondelete="SET NULL"),
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    def __repr__(self) -> str:
        return f"<PartnerEarning(id={self.id}, partner={self.partner_user_id}, total={self.total_earning})>"


class PartnerCodeEventModel(Base):
    """Append-only audit event for partner code governance changes."""

    __tablename__ = "partner_code_events"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    partner_code_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("partner_codes.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    partner_account_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("partner_accounts.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    event_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    previous_status: Mapped[str | None] = mapped_column(String(24), nullable=True)
    next_status: Mapped[str | None] = mapped_column(String(24), nullable=True)
    reason_code: Mapped[str | None] = mapped_column(String(120), nullable=True)
    actor_principal_id: Mapped[uuid.UUID | None] = mapped_column(nullable=True, index=True)
    event_payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )


class ApiIdempotencyRecordModel(Base):
    """Durable idempotency record for partner API mutations."""

    __tablename__ = "api_idempotency_records"
    __table_args__ = (UniqueConstraint("scope", "idempotency_key", name="uq_api_idempotency_records_scope_key"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    scope: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    idempotency_key: Mapped[str] = mapped_column(String(160), nullable=False)
    resource_type: Mapped[str] = mapped_column(String(80), nullable=False)
    resource_id: Mapped[uuid.UUID | None] = mapped_column(nullable=True, index=True)
    request_hash: Mapped[str | None] = mapped_column(String(128), nullable=True)
    response_payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="completed", server_default="completed")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True,
    )
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
