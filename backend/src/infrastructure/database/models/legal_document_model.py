"""Legal document ORM model for versioned surface documents."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, String, Text, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.infrastructure.database.session import Base

if TYPE_CHECKING:
    from src.infrastructure.database.models.legal_document_set_model import LegalDocumentSetItemModel


class LegalDocumentModel(Base):
    __tablename__ = "legal_documents"
    __table_args__ = (
        UniqueConstraint("document_key", "locale", "policy_version_id", name="uq_legal_documents_key_locale_policy"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_key: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    document_type: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    locale: Mapped[str] = mapped_column(String(16), nullable=False, default="en-EN", index=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    content_markdown: Mapped[str] = mapped_column(Text, nullable=False)
    content_checksum: Mapped[str] = mapped_column(String(64), nullable=False)
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

    set_items: Mapped[list[LegalDocumentSetItemModel]] = relationship(
        back_populates="legal_document",
        lazy="raise",
    )
