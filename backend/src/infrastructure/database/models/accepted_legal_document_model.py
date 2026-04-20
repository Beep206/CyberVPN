"""Acceptance evidence ORM model for legal document acknowledgements."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import JSON, CheckConstraint, DateTime, ForeignKey, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from src.infrastructure.database.session import Base


class AcceptedLegalDocumentModel(Base):
    __tablename__ = "accepted_legal_documents"
    __table_args__ = (
        CheckConstraint(
            """
            (
                CASE WHEN legal_document_id IS NOT NULL THEN 1 ELSE 0 END +
                CASE WHEN legal_document_set_id IS NOT NULL THEN 1 ELSE 0 END
            ) = 1
            """,
            name="ck_accepted_legal_documents_exactly_one_target",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    legal_document_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("legal_documents.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    legal_document_set_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("storefront_legal_doc_sets.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    storefront_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("storefronts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    auth_realm_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("auth_realms.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    actor_principal_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), nullable=False, index=True)
    actor_principal_type: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    acceptance_channel: Mapped[str] = mapped_column(String(50), nullable=False)
    quote_session_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True, index=True)
    checkout_session_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True, index=True)
    order_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True, index=True)
    source_ip: Mapped[str | None] = mapped_column(String(64), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(Text, nullable=True)
    device_context: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    accepted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        index=True,
    )
