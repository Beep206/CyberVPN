"""ServerGeolocation ORM model for VPN server location data."""

from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4

from sqlalchemy import CheckConstraint, DateTime, Numeric, String, func
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from src.infrastructure.database.session import Base


class ServerGeolocation(Base):
    """
    Server geolocation model for VPN node geographic data.

    Stores location information for VPN servers to enable geographic
    filtering and display on admin dashboard maps.
    """

    __tablename__ = "server_geolocations"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4, nullable=False)

    node_uuid: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), unique=True, nullable=False, index=True)

    country_code: Mapped[str] = mapped_column(String(2), nullable=False)

    city: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    latitude: Mapped[float] = mapped_column(Numeric(10, 7), nullable=False)

    longitude: Mapped[float] = mapped_column(Numeric(10, 7), nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    __table_args__ = (
        CheckConstraint("latitude >= -90 AND latitude <= 90", name="ck_latitude_bounds"),
        CheckConstraint("longitude >= -180 AND longitude <= 180", name="ck_longitude_bounds"),
    )

    def __repr__(self) -> str:
        return f"<ServerGeolocation(node_uuid={self.node_uuid}, country='{self.country_code}', city='{self.city}')>"
