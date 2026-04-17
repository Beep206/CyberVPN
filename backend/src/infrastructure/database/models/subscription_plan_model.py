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
    tier: Mapped[str | None] = mapped_column(String(20), nullable=True)
    plan_code: Mapped[str | None] = mapped_column(String(20), nullable=True, index=True)
    display_name: Mapped[str] = mapped_column(String(100), nullable=False, default="")
    catalog_visibility: Mapped[str] = mapped_column(String(20), nullable=False, default="hidden")
    duration_days: Mapped[int] = mapped_column(Integer, nullable=False)
    traffic_limit_bytes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    device_limit: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    price_usd: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    price_rub: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)
    sale_channels: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    traffic_policy: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    connection_modes: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    server_pool: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    support_sla: Mapped[str] = mapped_column(String(20), nullable=False, default="standard")
    dedicated_ip: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    invite_bundle: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    trial_eligible: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    features: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[str] = mapped_column(server_default=func.now())
    updated_at: Mapped[str] = mapped_column(server_default=func.now(), onupdate=func.now())
