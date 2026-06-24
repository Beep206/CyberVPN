"""WebAuthn passkey credential persistence model."""

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Integer, LargeBinary, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from src.infrastructure.database.session import Base


class PasskeyCredentialModel(Base):
    """Stored public-key credential metadata for WebAuthn ceremonies."""

    __tablename__ = "passkey_credentials"
    __table_args__ = (UniqueConstraint("credential_id_hash", name="uq_passkey_credentials_credential_id_hash"),)

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4, nullable=False)
    credential_id: Mapped[str] = mapped_column(Text, nullable=False)
    credential_id_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    credential_public_key: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    sign_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")

    auth_realm_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("auth_realms.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    realm_key: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    audience: Mapped[str] = mapped_column(String(120), nullable=False)
    principal_class: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    principal_subject: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    user_handle: Mapped[str] = mapped_column(String(128), nullable=False, index=True)

    label: Mapped[str] = mapped_column(String(120), nullable=False)
    surface: Mapped[str] = mapped_column(String(40), nullable=False)
    rp_id: Mapped[str] = mapped_column(String(253), nullable=False)
    origin: Mapped[str | None] = mapped_column(String(255), nullable=True)
    aaguid: Mapped[str | None] = mapped_column(String(36), nullable=True)
    attestation_format: Mapped[str | None] = mapped_column(String(40), nullable=True)
    credential_type: Mapped[str] = mapped_column(
        String(40),
        nullable=False,
        default="public-key",
        server_default="public-key",
    )
    device_type: Mapped[str | None] = mapped_column(String(40), nullable=True)
    transports: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list, server_default="[]")
    backed_up: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")
    user_verified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")
    authenticator_attachment: Mapped[str | None] = mapped_column(String(40), nullable=True)
    policy_snapshot: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict, server_default="{}")

    status: Mapped[str] = mapped_column(
        String(24),
        nullable=False,
        default="active",
        server_default="active",
        index=True,
    )
    clone_suspected_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
