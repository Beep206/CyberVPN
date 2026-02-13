"""AuditLog ORM model for tracking admin actions and changes."""

from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from src.infrastructure.database.session import Base


class AuditLog(Base):
    """
    Audit log model for tracking administrative actions.

    Records all significant actions performed by admin users, including
    entity changes with before/after values for compliance and debugging.
    """

    __tablename__ = "audit_logs"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4, nullable=False)

    admin_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("admin_users.id", ondelete="SET NULL"), nullable=True, index=True
    )

    action: Mapped[str] = mapped_column(String(100), nullable=False, index=True)

    entity_type: Mapped[str | None] = mapped_column(String(50), nullable=True, index=True)

    entity_id: Mapped[str | None] = mapped_column(String(255), nullable=True)

    old_value: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)

    new_value: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)

    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)

    user_agent: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )

    def __repr__(self) -> str:
        return f"<AuditLog(id={self.id}, action='{self.action}', entity_type='{self.entity_type}')>"
