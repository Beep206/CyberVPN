import os
from datetime import UTC, datetime
from uuid import uuid4

import pytest

os.environ.setdefault("ENVIRONMENT", "test")
os.environ.setdefault("REMNAWAVE_TOKEN", "local-remnawave-token")
os.environ.setdefault("CRYPTOBOT_TOKEN", "local-cryptobot-token")
os.environ.setdefault("JWT_SECRET", "0123456789abcdef0123456789abcdef")

from src.domain.entities.messaging import (  # noqa: E402
    MessagingBodyFormat,
    MessagingConversationCategory,
    MessagingConversationStatus,
    MessagingForbiddenError,
    MessagingMessageVisibility,
    MessagingParticipantRole,
    MessagingParticipantType,
    MessagingPriority,
    MessagingResponseState,
    MessagingSenderType,
    SiteNotificationRecipientType,
    SiteNotificationSeverity,
    SiteNotificationType,
)
from src.infrastructure.database.models.messaging_conversation_model import (  # noqa: E402
    MessagingConversationModel,
    MessagingConversationParticipantModel,
    MessagingMessageModel,
)
from src.infrastructure.database.repositories.messaging_repository import SQLAlchemyMessagingRepository  # noqa: E402


class _ScalarResult:
    def __init__(self, value):
        self._value = value

    def scalar_one_or_none(self):
        return self._value


class _ListResult:
    def __init__(self, values):
        self._values = values

    def scalars(self):
        return self

    def unique(self):
        return self

    def all(self):
        return self._values


class _FakeSession:
    def __init__(self, results):
        self.results = list(results)
        self.added = []
        self.flush_count = 0

    async def execute(self, _stmt):
        value = self.results.pop(0)
        if isinstance(value, list):
            return _ListResult(value)
        return _ScalarResult(value)

    def add(self, item):
        self.added.append(item)

    async def flush(self):
        self.flush_count += 1


@pytest.mark.asyncio
async def test_repository_duplicate_idempotency_key_returns_existing_message_without_insert() -> None:
    now = datetime.now(UTC)
    existing = MessagingMessageModel(
        id=uuid4(),
        public_id="msg_existing",
        conversation_id=uuid4(),
        sender_type=MessagingSenderType.ADMIN.value,
        sender_id=uuid4(),
        visibility=MessagingMessageVisibility.PUBLIC.value,
        body="Already stored",
        body_format=MessagingBodyFormat.PLAIN_TEXT.value,
        client_message_id="client-1",
        idempotency_key="idem-1",
        created_at=now,
        updated_at=now,
        metadata_json={},
    )
    conversation = MessagingConversationModel(
        id=existing.conversation_id,
        public_id="conv_existing",
        customer_account_id=uuid4(),
        status=MessagingConversationStatus.OPEN.value,
        response_state=MessagingResponseState.WAITING_CUSTOMER.value,
        category=MessagingConversationCategory.SUBSCRIPTION.value,
        priority=MessagingPriority.NORMAL.value,
        subject="Synthetic conversation",
        created_by_admin_id=existing.sender_id,
        assigned_admin_id=existing.sender_id,
        metadata_json={},
        created_at=now,
        updated_at=now,
    )
    conversation.participants = []
    conversation.messages = [existing]
    conversation.read_states = []
    fake_session = _FakeSession([existing, conversation])
    repo = SQLAlchemyMessagingRepository(fake_session)  # type: ignore[arg-type]

    result = await repo.add_message(
        public_id="msg_new",
        conversation_id=existing.conversation_id,
        sender_type=MessagingSenderType.ADMIN,
        sender_id=existing.sender_id,
        visibility=MessagingMessageVisibility.PUBLIC,
        body="Should not be inserted",
        client_message_id="client-1",
        idempotency_key="idem-1",
    )

    assert result.created is False
    assert result.message.id == existing.id
    assert fake_session.added == []
    assert fake_session.flush_count == 0


def _conversation_model(*, customer_account_id=None) -> MessagingConversationModel:
    now = datetime.now(UTC)
    admin_id = uuid4()
    return MessagingConversationModel(
        id=uuid4(),
        public_id="conv_existing",
        customer_account_id=customer_account_id or uuid4(),
        status=MessagingConversationStatus.OPEN.value,
        response_state=MessagingResponseState.WAITING_CUSTOMER.value,
        category=MessagingConversationCategory.SUBSCRIPTION.value,
        priority=MessagingPriority.NORMAL.value,
        subject="Synthetic conversation",
        created_by_admin_id=admin_id,
        assigned_admin_id=admin_id,
        metadata_json={},
        created_at=now,
        updated_at=now,
    )


def _message_model(
    *,
    conversation_id,
    visibility: MessagingMessageVisibility = MessagingMessageVisibility.PUBLIC,
) -> MessagingMessageModel:
    now = datetime.now(UTC)
    return MessagingMessageModel(
        id=uuid4(),
        public_id=f"msg_{visibility.value}",
        conversation_id=conversation_id,
        sender_type=MessagingSenderType.ADMIN.value,
        sender_id=uuid4(),
        visibility=visibility.value,
        body="Stored message",
        body_format=MessagingBodyFormat.PLAIN_TEXT.value,
        client_message_id=f"client-{visibility.value}",
        idempotency_key=f"idem-{visibility.value}",
        created_at=now,
        updated_at=now,
        metadata_json={},
    )


def _participant_model(*, conversation_id, participant_id) -> MessagingConversationParticipantModel:
    return MessagingConversationParticipantModel(
        conversation_id=conversation_id,
        participant_type=MessagingParticipantType.CUSTOMER.value,
        participant_id=participant_id,
        role=MessagingParticipantRole.CUSTOMER.value,
        can_read=True,
        can_write=True,
        joined_at=datetime.now(UTC),
        metadata_json={},
    )


@pytest.mark.asyncio
async def test_repository_customer_list_filters_internal_messages() -> None:
    customer_account_id = uuid4()
    conversation = _conversation_model(customer_account_id=customer_account_id)
    public = _message_model(conversation_id=conversation.id, visibility=MessagingMessageVisibility.PUBLIC)
    internal = _message_model(conversation_id=conversation.id, visibility=MessagingMessageVisibility.INTERNAL)
    conversation.participants = []
    conversation.messages = [public, internal]
    conversation.read_states = []
    fake_session = _FakeSession([[conversation]])
    repo = SQLAlchemyMessagingRepository(fake_session)  # type: ignore[arg-type]

    result = await repo.list_for_customer(customer_account_id=customer_account_id)

    assert len(result.conversations) == 1
    assert [message.id for message in result.conversations[0].messages] == [public.id]


@pytest.mark.asyncio
async def test_repository_rejects_customer_message_without_sender_id() -> None:
    fake_session = _FakeSession([None])
    repo = SQLAlchemyMessagingRepository(fake_session)  # type: ignore[arg-type]

    with pytest.raises(MessagingForbiddenError, match="sender attribution"):
        await repo.add_message(
            public_id="msg_new",
            conversation_id=uuid4(),
            sender_type=MessagingSenderType.CUSTOMER,
            sender_id=None,
            visibility=MessagingMessageVisibility.PUBLIC,
            body="Missing actor",
            client_message_id="client-1",
            idempotency_key="idem-1",
        )

    assert fake_session.added == []
    assert fake_session.flush_count == 0


@pytest.mark.asyncio
async def test_repository_mark_read_requires_active_readable_participant() -> None:
    fake_session = _FakeSession([None])
    repo = SQLAlchemyMessagingRepository(fake_session)  # type: ignore[arg-type]

    with pytest.raises(MessagingForbiddenError, match="Participant cannot read"):
        await repo.mark_read(
            conversation_id=uuid4(),
            participant_type=MessagingParticipantType.CUSTOMER,
            participant_id=uuid4(),
            last_read_message_id=None,
        )


@pytest.mark.asyncio
async def test_repository_customer_mark_read_rejects_internal_message() -> None:
    conversation = _conversation_model()
    participant_id = conversation.customer_account_id
    participant = _participant_model(conversation_id=conversation.id, participant_id=participant_id)
    internal = _message_model(conversation_id=conversation.id, visibility=MessagingMessageVisibility.INTERNAL)
    fake_session = _FakeSession([participant, internal])
    repo = SQLAlchemyMessagingRepository(fake_session)  # type: ignore[arg-type]

    with pytest.raises(MessagingForbiddenError, match="internal messages"):
        await repo.mark_read(
            conversation_id=conversation.id,
            participant_type=MessagingParticipantType.CUSTOMER,
            participant_id=participant_id,
            last_read_message_id=internal.id,
        )


@pytest.mark.asyncio
async def test_repository_rejects_unscoped_notification_recipient() -> None:
    fake_session = _FakeSession([])
    repo = SQLAlchemyMessagingRepository(fake_session)  # type: ignore[arg-type]

    with pytest.raises(MessagingForbiddenError, match="recipient_id is required"):
        await repo.create_site_notification(
            notification_type=SiteNotificationType.MESSAGE,
            severity=SiteNotificationSeverity.INFO,
            title="Message",
            recipient_type=SiteNotificationRecipientType.CUSTOMER,
            recipient_id=None,
        )

    assert fake_session.added == []
    assert fake_session.flush_count == 0
