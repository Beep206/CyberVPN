"""Internal staff notes attached to mobile users for customer operations."""

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from src.infrastructure.database.session import Base


class CustomerStaffNoteModel(Base):
    """Persistent internal staff notes for mobile-user support workflows."""

    __tablename__ = "customer_staff_notes"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4, nullable=False)

    user_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("mobile_users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    admin_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("admin_users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    category: Mapped[str] = mapped_column(String(20), nullable=False, default="general")

    note: Mapped[str] = mapped_column(Text, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    def __repr__(self) -> str:
        return f"<CustomerStaffNoteModel(id={self.id}, user_id={self.user_id}, category={self.category})>"
