"""Growth Codes v6 onboarding, principal-link, and registration-access ORM models."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, Index, Integer, String, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from src.infrastructure.database.session import Base


class CustomerOnboardingStateModel(Base):
    """Server-owned post-registration universal-code prompt state machine."""

    __tablename__ = "customer_onboarding_states"
    __table_args__ = (
        UniqueConstraint(
            "mobile_user_id",
            "flow_key",
            "flow_version",
            name="uq_customer_onboarding_states_user_flow_version",
        ),
        CheckConstraint(
            "status IN ('pending','shown','submitted','completed','skipped','expired','failed_retryable')",
            name="ck_customer_onboarding_states_status",
        ),
        CheckConstraint("display_count >= 0", name="ck_customer_onboarding_states_display_count_non_negative"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    mobile_user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("mobile_users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    flow_key: Mapped[str] = mapped_column(String(80), nullable=False)
    flow_version: Mapped[int] = mapped_column(Integer, nullable=False)
    source_channel: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    skippable: Mapped[bool] = mapped_column(Boolean, nullable=False)
    policy_version_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("policy_versions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    first_eligible_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    first_shown_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_shown_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    display_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    skipped_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    result_code_application_id: Mapped[uuid.UUID | None] = mapped_column(nullable=True, index=True)
    result_payload: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    signup_finalization_id: Mapped[uuid.UUID | None] = mapped_column(nullable=True, index=True)
    referral_terminal_state: Mapped[str | None] = mapped_column(String(30), nullable=True)
    canonical_identity_link_id: Mapped[uuid.UUID | None] = mapped_column(nullable=True, index=True)
    auth_channel: Mapped[str] = mapped_column(String(40), nullable=False)
    return_route_key: Mapped[str | None] = mapped_column(String(60), nullable=True)
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


class CustomerCodeIntentModel(Base):
    """Deferred promo/private access intent entered without checkout context."""

    __tablename__ = "customer_code_intents"
    __table_args__ = (UniqueConstraint("mobile_user_id", "idempotency_key", name="uq_customer_code_intents_user_idem"),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    mobile_user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("mobile_users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    growth_code_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("growth_codes.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    onboarding_state_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("customer_onboarding_states.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    intent_type: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    policy_version_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("policy_versions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    source_channel: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    private_access_grant_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("private_catalog_access_grants.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    consumed_by_quote_session_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("quote_sessions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    consumed_by_order_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("orders.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    idempotency_key: Mapped[str] = mapped_column(String(120), nullable=False)
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


class CustomerOnboardingCodeApplicationModel(Base):
    """Immutable attempt ledger for post-registration code submissions."""

    __tablename__ = "customer_onboarding_code_applications"
    __table_args__ = (
        UniqueConstraint(
            "mobile_user_id",
            "idempotency_key",
            name="uq_customer_onboarding_code_apps_user_idem",
        ),
        UniqueConstraint(
            "onboarding_state_id",
            "idempotency_key",
            name="uq_customer_onboarding_code_apps_state_idem",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    onboarding_state_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("customer_onboarding_states.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    mobile_user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("mobile_users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    growth_code_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("growth_codes.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    resolved_code_type: Mapped[str | None] = mapped_column(String(20), nullable=True, index=True)
    action_context: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    result: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    reject_reason: Mapped[str | None] = mapped_column(String(80), nullable=True, index=True)
    policy_version_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("policy_versions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    risk_decision_id: Mapped[uuid.UUID | None] = mapped_column(nullable=True, index=True)
    redemption_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("growth_code_redemptions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    fulfillment_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("growth_benefit_fulfillments.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    code_intent_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("customer_code_intents.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    idempotency_key: Mapped[str] = mapped_column(String(120), nullable=False)
    code_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    code_prefix: Mapped[str] = mapped_column(String(12), nullable=False)
    safe_result_snapshot: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    signup_finalization_id: Mapped[uuid.UUID | None] = mapped_column(nullable=True, index=True)
    referral_terminal_state: Mapped[str | None] = mapped_column(String(30), nullable=True)
    canonical_identity_link_id: Mapped[uuid.UUID | None] = mapped_column(nullable=True, index=True)
    auth_channel: Mapped[str] = mapped_column(String(40), nullable=False)
    return_route_key: Mapped[str | None] = mapped_column(String(60), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
    )


class CustomerPrincipalLinkModel(Base):
    """Canonical mapping from external principals to a mobile user."""

    __tablename__ = "customer_principal_links"
    __table_args__ = (
        Index(
            "uq_customer_principal_links_active_realm",
            "principal_type",
            "principal_id",
            "auth_realm_id",
            unique=True,
            postgresql_where=text("status = 'active' AND auth_realm_id IS NOT NULL"),
        ),
        Index(
            "uq_customer_principal_links_active_global",
            "principal_type",
            "principal_id",
            unique=True,
            postgresql_where=text("status = 'active' AND auth_realm_id IS NULL"),
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    canonical_mobile_user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("mobile_users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    principal_type: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    principal_id: Mapped[str] = mapped_column(String(160), nullable=False, index=True)
    auth_realm_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("auth_realms.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    provider: Mapped[str | None] = mapped_column(String(40), nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    linked_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    metadata_: Mapped[dict[str, Any]] = mapped_column("metadata", JSONB, nullable=False, default=dict)


class RegistrationAccessGrantModel(Base):
    """Durable registration-access lifecycle record keyed by token hash."""

    __tablename__ = "registration_access_grants"
    __table_args__ = (
        UniqueConstraint("token_hash", name="uq_registration_access_grants_token_hash"),
        UniqueConstraint("reservation_key", name="uq_registration_access_grants_reservation_key"),
        CheckConstraint(
            "status IN ('issued','exchanged','reserved','consumed','released','expired','revoked')",
            name="ck_registration_access_grants_status",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    token_hash: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(24), nullable=False, index=True)
    created_by_admin_user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("admin_users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    role_key: Mapped[str] = mapped_column(String(40), nullable=False)
    email_hint_hash: Mapped[str | None] = mapped_column(String(128), nullable=True)
    auth_realm_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("auth_realms.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    issued_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    exchanged_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    exchange_session_hash: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    reserved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    reservation_key: Mapped[str | None] = mapped_column(String(120), nullable=True)
    registration_idempotency_key: Mapped[str | None] = mapped_column(String(120), nullable=True, index=True)
    consumed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    consumed_user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("mobile_users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    released_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    release_reason: Mapped[str | None] = mapped_column(String(80), nullable=True)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    metadata_: Mapped[dict[str, Any]] = mapped_column("metadata", JSONB, nullable=False, default=dict)
