"""Growth Codes v6 rule, private catalog, code-set, and ledger ORM models."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, Integer, Numeric, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from src.infrastructure.database.session import Base


class GrowthRuleCatalogVersionModel(Base):
    """Versioned server-side catalog of fields, operators, and actions."""

    __tablename__ = "growth_rule_catalog_versions"
    __table_args__ = (UniqueConstraint("catalog_version", name="uq_growth_rule_catalog_versions_catalog_version"),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    catalog_version: Mapped[str] = mapped_column(String(40), nullable=False)
    fields_schema: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    operators_schema: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    actions_schema: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    status: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    checksum: Mapped[str] = mapped_column(String(128), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
    )
    activated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    retired_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class GrowthRuleDefinitionModel(Base):
    """Operational index and compiled plan for a policy version rule AST."""

    __tablename__ = "growth_rule_definitions"
    __table_args__ = (
        CheckConstraint("complexity_score >= 0", name="ck_growth_rule_definitions_complexity_non_negative"),
        CheckConstraint("node_count >= 0", name="ck_growth_rule_definitions_node_count_non_negative"),
        CheckConstraint("max_depth >= 0", name="ck_growth_rule_definitions_max_depth_non_negative"),
        UniqueConstraint("policy_version_id", name="uq_growth_rule_definitions_policy_version_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    policy_version_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("policy_versions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    catalog_version_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("growth_rule_catalog_versions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    schema_version: Mapped[str] = mapped_column(String(40), nullable=False)
    ast_payload: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    compiled_plan_payload: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    compiled_checksum: Mapped[str] = mapped_column(String(128), nullable=False)
    complexity_score: Mapped[int] = mapped_column(Integer, nullable=False)
    node_count: Mapped[int] = mapped_column(Integer, nullable=False)
    max_depth: Mapped[int] = mapped_column(Integer, nullable=False)
    validation_status: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    validation_errors: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    compiled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
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


class GrowthPrivateCatalogPolicyModel(Base):
    """Policy binding a growth code to private catalog access semantics."""

    __tablename__ = "growth_private_catalog_policies"
    __table_args__ = (
        CheckConstraint("grant_ttl_seconds > 0", name="ck_growth_private_catalog_policies_grant_ttl_positive"),
        CheckConstraint(
            "max_quote_conversions IS NULL OR max_quote_conversions >= 0",
            name="ck_growth_private_catalog_policies_max_quote_conversions",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    policy_version_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("policy_versions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    growth_code_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("growth_codes.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    unlock_mode: Mapped[str] = mapped_column(String(30), nullable=False)
    target_plan_ids: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    target_offer_ids: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    target_offer_keys: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    auto_select_target_id: Mapped[uuid.UUID | None] = mapped_column(nullable=True)
    allowed_storefront_ids: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    allowed_channels: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    grant_ttl_seconds: Mapped[int] = mapped_column(Integer, nullable=False)
    max_quote_conversions: Mapped[int | None] = mapped_column(Integer, nullable=True)
    consume_mode: Mapped[str] = mapped_column(String(30), nullable=False)
    requires_auth: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="true")
    requires_risk_action_below: Mapped[str | None] = mapped_column(String(20), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="true", index=True)
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


class PrivateCatalogAccessGrantModel(Base):
    """Short-lived grant proving a private plan/offer was revealed by code policy."""

    __tablename__ = "private_catalog_access_grants"
    __table_args__ = (
        CheckConstraint(
            "user_id IS NOT NULL OR anonymous_session_id IS NOT NULL",
            name="ck_private_catalog_access_grants_subject_present",
        ),
        CheckConstraint(
            "quote_conversions_count >= 0",
            name="ck_private_catalog_access_grants_quote_conversions_non_negative",
        ),
        CheckConstraint(
            "max_quote_conversions IS NULL OR quote_conversions_count <= max_quote_conversions",
            name="ck_private_catalog_access_grants_quote_conversions_lte_max",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    policy_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("growth_private_catalog_policies.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    policy_version_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("policy_versions.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    growth_code_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("growth_codes.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    code_set_hash: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    grant_token_hash: Mapped[str | None] = mapped_column(String(128), nullable=True, unique=True, index=True)
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("mobile_users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    anonymous_session_id: Mapped[str | None] = mapped_column(String(120), nullable=True, index=True)
    risk_subject_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("risk_subjects.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    auth_realm_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("auth_realms.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    storefront_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("storefronts.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    sale_channel: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    allowed_plan_ids: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    allowed_offer_ids: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    risk_decision_id: Mapped[uuid.UUID | None] = mapped_column(nullable=True, index=True)
    status: Mapped[str] = mapped_column(String(24), nullable=False, index=True)
    max_quote_conversions: Mapped[int | None] = mapped_column(Integer, nullable=True)
    quote_conversions_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    issued_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    attached_quote_session_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("quote_sessions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    attached_checkout_session_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("checkout_sessions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    consumed_order_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("orders.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    revoked_reason: Mapped[str | None] = mapped_column(String(120), nullable=True)
    metadata_: Mapped[dict[str, Any]] = mapped_column("metadata", JSONB, nullable=False, default=dict)
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


class CheckoutCodeSetModel(Base):
    """Deterministic basket-level code evaluation and reservation root."""

    __tablename__ = "checkout_code_sets"
    __table_args__ = (
        CheckConstraint(
            "user_id IS NOT NULL OR anonymous_session_id IS NOT NULL",
            name="ck_checkout_code_sets_subject_present",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    code_set_hash: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("mobile_users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    anonymous_session_id: Mapped[str | None] = mapped_column(String(120), nullable=True, index=True)
    auth_realm_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("auth_realms.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    storefront_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("storefronts.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    sale_channel: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    action_context: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(24), nullable=False, index=True)
    acceptance_mode: Mapped[str] = mapped_column(String(24), nullable=False)
    aggregate_result: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    risk_snapshot: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    private_access_grant_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("private_catalog_access_grants.id", ondelete="SET NULL"),
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
    payment_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("payments.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
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


class CheckoutCodeApplicationModel(Base):
    """Per-code evaluation result inside a quote or checkout code set."""

    __tablename__ = "checkout_code_applications"
    __table_args__ = (
        CheckConstraint("position_entered >= 0", name="ck_checkout_code_applications_position_non_negative"),
        CheckConstraint("canonical_order >= 0", name="ck_checkout_code_applications_canonical_order_non_negative"),
        UniqueConstraint("code_set_id", "growth_code_id", name="uq_checkout_code_applications_code_set_growth_code"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    code_set_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("checkout_code_sets.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    position_entered: Mapped[int] = mapped_column(Integer, nullable=False)
    canonical_order: Mapped[int] = mapped_column(Integer, nullable=False)
    growth_code_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("growth_codes.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    legacy_code_type: Mapped[str | None] = mapped_column(String(20), nullable=True)
    legacy_code_id: Mapped[uuid.UUID | None] = mapped_column(nullable=True, index=True)
    masked_code: Mapped[str] = mapped_column(String(32), nullable=False)
    roles: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    resolution_status: Mapped[str] = mapped_column(String(24), nullable=False, index=True)
    reject_reason: Mapped[str | None] = mapped_column(String(80), nullable=True, index=True)
    conflict_code: Mapped[str | None] = mapped_column(String(80), nullable=True)
    policy_version_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("policy_versions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    rule_definition_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("growth_rule_definitions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    risk_decision_id: Mapped[uuid.UUID | None] = mapped_column(nullable=True, index=True)
    fx_conversion_id: Mapped[uuid.UUID | None] = mapped_column(nullable=True, index=True)
    reservation_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("growth_code_reservations.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    discount_snapshot: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    benefits_snapshot: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    private_access_snapshot: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    evaluation_trace: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
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


class GrowthCodeReservationGroupModel(Base):
    """Atomic multi-code reservation group with one idempotency key."""

    __tablename__ = "growth_code_reservation_groups"
    __table_args__ = (UniqueConstraint("idempotency_key", name="uq_growth_code_reservation_groups_idempotency_key"),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    code_set_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("checkout_code_sets.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    status: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("mobile_users.id", ondelete="SET NULL"),
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
    payment_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("payments.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    reserved_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    committed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    consumed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    released_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    release_reason: Mapped[str | None] = mapped_column(String(80), nullable=True)
    idempotency_key: Mapped[str] = mapped_column(String(160), nullable=False)
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


class OrderCodeApplicationModel(Base):
    """Immutable per-code order ledger used for refunds, reversals, and support."""

    __tablename__ = "order_code_applications"
    __table_args__ = (
        CheckConstraint("discount_amount >= 0", name="ck_order_code_applications_discount_non_negative"),
        UniqueConstraint("order_id", "growth_code_id", name="uq_order_code_applications_order_growth_code"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    order_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("orders.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    code_set_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("checkout_code_sets.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    growth_code_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("growth_codes.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    policy_version_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("policy_versions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    application_role: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    application_status: Mapped[str] = mapped_column(String(24), nullable=False, index=True)
    discount_amount: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)
    currency_code: Mapped[str] = mapped_column(String(12), nullable=False)
    source_amount: Mapped[Decimal | None] = mapped_column(Numeric(20, 8), nullable=True)
    source_currency_code: Mapped[str | None] = mapped_column(String(12), nullable=True)
    fx_conversion_id: Mapped[uuid.UUID | None] = mapped_column(nullable=True, index=True)
    reservation_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("growth_code_reservations.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    risk_decision_id: Mapped[uuid.UUID | None] = mapped_column(nullable=True, index=True)
    application_snapshot: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
    )


class GrowthReversalEventModel(Base):
    """Idempotent event ledger for refund, cancellation, and campaign reversal workflows."""

    __tablename__ = "growth_reversal_events"
    __table_args__ = (
        CheckConstraint(
            "event_type IN ('refund', 'zero_payment_cancellation', 'campaign_revoke')",
            name="ck_growth_reversal_events_event_type",
        ),
        UniqueConstraint("idempotency_key", name="uq_growth_reversal_events_idempotency_key"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    event_type: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    event_id: Mapped[uuid.UUID] = mapped_column(nullable=False, index=True)
    order_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("orders.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    refund_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("refunds.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    payment_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("payments.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    campaign_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("growth_campaigns.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    idempotency_key: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    reason_code: Mapped[str] = mapped_column(String(120), nullable=False)
    event_status: Mapped[str] = mapped_column(String(24), nullable=False, default="applied", server_default="applied")
    event_payload: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
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


class GrowthCodeNamespaceModel(Base):
    """Canonical customer-input namespace preventing cross-type code collisions."""

    __tablename__ = "growth_code_namespaces"

    normalized_code_hash: Mapped[str] = mapped_column(String(128), primary_key=True)
    canonical_growth_code_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("growth_codes.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    code_type: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    legacy_source_type: Mapped[str | None] = mapped_column(String(30), nullable=True, index=True)
    legacy_source_id: Mapped[uuid.UUID | None] = mapped_column(nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
    )
