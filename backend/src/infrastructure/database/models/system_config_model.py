"""SystemConfig model for admin-configurable settings (key-value JSONB)."""

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from src.infrastructure.database.session import Base


class SystemConfigModel(Base):
    """Global system configuration stored as key-value pairs with JSONB values.

    Used for invite rules, referral settings, partner tiers, wallet config, etc.
    """

    __tablename__ = "system_config"

    key: Mapped[str] = mapped_column(String(100), primary_key=True)

    value: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)

    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    updated_by: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        nullable=True,
    )

    def __repr__(self) -> str:
        return f"<SystemConfig(key={self.key!r})>"
