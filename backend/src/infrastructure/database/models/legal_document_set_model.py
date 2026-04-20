"""Storefront-bound legal document set ORM models."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.infrastructure.database.session import Base

if TYPE_CHECKING:
    from src.infrastructure.database.models.legal_document_model import LegalDocumentModel


class LegalDocumentSetModel(Base):
    __tablename__ = "storefront_legal_doc_sets"
    __table_args__ = (UniqueConstraint("set_key", "policy_version_id", name="uq_legal_doc_sets_key_policy"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    set_key: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    storefront_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("storefronts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    auth_realm_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("auth_realms.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    display_name: Mapped[str] = mapped_column(String(120), nullable=False)
    policy_version_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("policy_versions.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
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

    documents: Mapped[list[LegalDocumentSetItemModel]] = relationship(
        back_populates="legal_document_set",
        cascade="all, delete-orphan",
        lazy="selectin",
    )


class LegalDocumentSetItemModel(Base):
    __tablename__ = "storefront_legal_doc_set_items"
    __table_args__ = (
        UniqueConstraint("legal_document_set_id", "legal_document_id", name="uq_legal_doc_set_item_document"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    legal_document_set_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("storefront_legal_doc_sets.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    legal_document_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("legal_documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    required: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    display_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
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

    legal_document_set: Mapped[LegalDocumentSetModel] = relationship(back_populates="documents", lazy="raise")
    legal_document: Mapped[LegalDocumentModel] = relationship(back_populates="set_items", lazy="raise")
