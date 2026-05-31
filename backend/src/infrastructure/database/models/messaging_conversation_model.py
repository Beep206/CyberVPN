"""SQLAlchemy models for messaging conversations and messages."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
    UniqueConstraint,
    Uuid,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.infrastructure.database.session import Base


def _utc_now() -> datetime:
    return datetime.now(UTC)


class MessagingConversationModel(Base):
    __tablename__ = "messaging_conversations"
    __table_args__ = (
        UniqueConstraint("public_id", name="uq_messaging_conversations_public_id"),
        CheckConstraint(
            "status in ('open', 'closed', 'archived', 'locked')",
            name="ck_messaging_conversations_status",
        ),
        CheckConstraint("customer_account_id is not null", name="ck_messaging_conversations_customer_required"),
        Index(
            "ix_messaging_conversations_customer_status_updated",
            "customer_account_id",
            "status",
            "updated_at",
        ),
        Index(
            "ix_messaging_conversations_assigned_status_updated",
            "assigned_admin_id",
            "status",
            "updated_at",
        ),
        Index(
            "ix_messaging_conversations_status_priority_category_updated",
            "status",
            "priority",
            "category",
            "updated_at",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    public_id: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    customer_account_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("mobile_users.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    status: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    response_state: Mapped[str] = mapped_column(String(30), nullable=False, default="none")
    category: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    priority: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    subject: Mapped[str] = mapped_column(String(160), nullable=False)
    created_by_admin_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("admin_users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    assigned_admin_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("admin_users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    related_support_ticket_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("support_tickets.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    last_message_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey(
            "messaging_messages.id",
            use_alter=True,
            name="fk_messaging_conversations_last_message_id",
            ondelete="SET NULL",
        ),
        nullable=True,
        index=True,
    )
    last_message_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    metadata_json: Mapped[dict[str, Any]] = mapped_column("metadata", JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=_utc_now,
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=_utc_now,
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    participants: Mapped[list[MessagingConversationParticipantModel]] = relationship(
        back_populates="conversation",
        cascade="all, delete-orphan",
        lazy="selectin",
        order_by="MessagingConversationParticipantModel.joined_at",
        foreign_keys="MessagingConversationParticipantModel.conversation_id",
    )
    messages: Mapped[list[MessagingMessageModel]] = relationship(
        back_populates="conversation",
        cascade="all, delete-orphan",
        lazy="selectin",
        order_by="MessagingMessageModel.created_at",
        foreign_keys="MessagingMessageModel.conversation_id",
    )
    read_states: Mapped[list[MessagingMessageReadStateModel]] = relationship(
        back_populates="conversation",
        cascade="all, delete-orphan",
        lazy="selectin",
        order_by="MessagingMessageReadStateModel.updated_at",
    )


class MessagingConversationParticipantModel(Base):
    __tablename__ = "messaging_conversation_participants"
    __table_args__ = (
        CheckConstraint(
            "participant_type in ('customer', 'admin', 'team', 'system')",
            name="ck_messaging_participants_type",
        ),
        CheckConstraint(
            "(participant_type in ('customer', 'admin') and participant_id is not null) "
            "or participant_type in ('team', 'system')",
            name="ck_messaging_participants_actor_required",
        ),
        Index(
            "uq_messaging_participants_active_role",
            "conversation_id",
            "participant_type",
            "participant_id",
            "role",
            unique=True,
            postgresql_where=text("left_at IS NULL"),
        ),
        Index(
            "uq_messaging_participants_active_customer",
            "conversation_id",
            unique=True,
            postgresql_where=text("left_at IS NULL AND participant_type = 'customer'"),
        ),
        Index(
            "ix_messaging_participants_actor_can_read",
            "participant_type",
            "participant_id",
            "can_read",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    conversation_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("messaging_conversations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    participant_type: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    participant_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True, index=True)
    role: Mapped[str] = mapped_column(String(20), nullable=False)
    can_read: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    can_write: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    joined_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=_utc_now,
        server_default=func.now(),
        nullable=False,
    )
    left_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    metadata_json: Mapped[dict[str, Any]] = mapped_column("metadata", JSON, nullable=False, default=dict)

    conversation: Mapped[MessagingConversationModel] = relationship(
        back_populates="participants",
        lazy="raise",
        foreign_keys=[conversation_id],
    )


class MessagingMessageModel(Base):
    __tablename__ = "messaging_messages"
    __table_args__ = (
        UniqueConstraint("public_id", name="uq_messaging_messages_public_id"),
        UniqueConstraint("idempotency_key", name="uq_messaging_messages_idempotency_key"),
        CheckConstraint(
            "sender_type in ('customer', 'admin', 'system')",
            name="ck_messaging_messages_sender_type",
        ),
        CheckConstraint(
            "visibility != 'internal' or sender_type in ('admin', 'system')",
            name="ck_messaging_messages_internal_sender",
        ),
        CheckConstraint(
            "sender_type = 'system' or sender_id is not null",
            name="ck_messaging_messages_actor_required",
        ),
        CheckConstraint("body_format = 'plain_text'", name="ck_messaging_messages_plain_text"),
        Index(
            "uq_messaging_messages_client_message",
            "conversation_id",
            "sender_type",
            "sender_id",
            "client_message_id",
            unique=True,
            postgresql_where=text("client_message_id IS NOT NULL"),
        ),
        Index("ix_messaging_messages_conversation_created", "conversation_id", "created_at"),
        Index("ix_messaging_messages_sender_created", "sender_type", "sender_id", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    public_id: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    conversation_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("messaging_conversations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    sender_type: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    sender_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True, index=True)
    visibility: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    body_format: Mapped[str] = mapped_column(String(20), nullable=False, default="plain_text")
    client_message_id: Mapped[str | None] = mapped_column(String(80), nullable=True)
    idempotency_key: Mapped[str] = mapped_column(String(160), nullable=False, index=True)
    reply_to_message_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("messaging_messages.id", ondelete="SET NULL"),
        nullable=True,
    )
    redacted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=_utc_now,
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=_utc_now,
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
    metadata_json: Mapped[dict[str, Any]] = mapped_column("metadata", JSON, nullable=False, default=dict)

    conversation: Mapped[MessagingConversationModel] = relationship(
        back_populates="messages",
        lazy="raise",
        foreign_keys=[conversation_id],
    )


class MessagingMessageReadStateModel(Base):
    __tablename__ = "messaging_message_read_states"
    __table_args__ = (
        UniqueConstraint(
            "conversation_id",
            "participant_type",
            "participant_id",
            name="uq_messaging_read_states_conversation_actor",
        ),
        Index("ix_messaging_read_states_actor_updated", "participant_type", "participant_id", "updated_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    conversation_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("messaging_conversations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    participant_type: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    participant_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), nullable=False, index=True)
    last_read_message_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("messaging_messages.id", ondelete="SET NULL"),
        nullable=True,
    )
    last_read_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=_utc_now,
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=_utc_now,
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    conversation: Mapped[MessagingConversationModel] = relationship(back_populates="read_states", lazy="raise")
