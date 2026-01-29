import uuid

from sqlalchemy import Boolean, Integer, Numeric, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from src.infrastructure.database.session import Base


class SubscriptionPlanModel(Base):
    __tablename__ = "subscription_plans"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    tier: Mapped[str] = mapped_column(String(20), nullable=False)
    duration_days: Mapped[int] = mapped_column(Integer, nullable=False)
    traffic_limit_bytes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    device_limit: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    price_usd: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    price_rub: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)
    features: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[str] = mapped_column(server_default=func.now())
    updated_at: Mapped[str] = mapped_column(server_default=func.now(), onupdate=func.now())
