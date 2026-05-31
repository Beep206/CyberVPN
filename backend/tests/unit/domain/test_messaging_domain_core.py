from datetime import UTC, datetime
from uuid import uuid4

import pytest

from src.domain.entities.messaging import (
    MessagingBodyFormat,
    MessagingConversation,
    MessagingConversationCategory,
    MessagingConversationClosedError,
    MessagingConversationStatus,
    MessagingForbiddenError,
    MessagingMessage,
    MessagingMessageVisibility,
    MessagingParticipantType,
    MessagingPresenceProjection,
    MessagingPriority,
    MessagingResponseState,
    MessagingSenderType,
    PresenceStatus,
    assert_customer_cannot_start_conversation,
    assert_message_sender_attribution,
    assert_message_write_allowed,
    customer_visible_messages,
    response_state_after_public_message,
)
from src.domain.value_objects.messaging import (
    assert_relative_action_url,
    build_message_idempotency_key,
    normalize_message_body,
    normalize_subject,
)


def _conversation(status: MessagingConversationStatus = MessagingConversationStatus.OPEN) -> MessagingConversation:
    now = datetime.now(UTC)
    return MessagingConversation(
        id=uuid4(),
        public_id="msg_test",
        customer_account_id=uuid4(),
        status=status,
        response_state=MessagingResponseState.NONE,
        category=MessagingConversationCategory.SUBSCRIPTION,
        priority=MessagingPriority.NORMAL,
        subject="Subscription renewal",
        created_by_admin_id=uuid4(),
        assigned_admin_id=None,
        metadata={},
        created_at=now,
        updated_at=now,
    )


def _message(visibility: MessagingMessageVisibility) -> MessagingMessage:
    now = datetime.now(UTC)
    return MessagingMessage(
        id=uuid4(),
        public_id=f"msg_{visibility.value}",
        conversation_id=uuid4(),
        sender_type=MessagingSenderType.ADMIN,
        sender_id=uuid4(),
        visibility=visibility,
        body="Synthetic message",
        body_format=MessagingBodyFormat.PLAIN_TEXT,
        idempotency_key=f"idem_{visibility.value}",
        created_at=now,
        updated_at=now,
    )


def test_customer_cannot_start_private_conversation() -> None:
    with pytest.raises(MessagingForbiddenError, match="Customer cannot start"):
        assert_customer_cannot_start_conversation()


def test_customer_cannot_write_internal_note() -> None:
    with pytest.raises(MessagingForbiddenError, match="Internal notes"):
        assert_message_write_allowed(
            conversation=_conversation(),
            sender_type=MessagingSenderType.CUSTOMER,
            visibility=MessagingMessageVisibility.INTERNAL,
        )


def test_customer_and_admin_messages_require_actor_attribution() -> None:
    assert_message_sender_attribution(sender_type=MessagingSenderType.SYSTEM, sender_id=None)
    with pytest.raises(MessagingForbiddenError, match="sender attribution"):
        assert_message_sender_attribution(sender_type=MessagingSenderType.CUSTOMER, sender_id=None)
    with pytest.raises(MessagingForbiddenError, match="sender attribution"):
        assert_message_sender_attribution(sender_type=MessagingSenderType.ADMIN, sender_id=None)


def test_closed_conversation_rejects_message_write() -> None:
    with pytest.raises(MessagingConversationClosedError, match="not open"):
        assert_message_write_allowed(
            conversation=_conversation(MessagingConversationStatus.CLOSED),
            sender_type=MessagingSenderType.ADMIN,
            visibility=MessagingMessageVisibility.PUBLIC,
        )


def test_customer_visible_messages_excludes_internal_notes() -> None:
    public = _message(MessagingMessageVisibility.PUBLIC)
    internal = _message(MessagingMessageVisibility.INTERNAL)

    assert customer_visible_messages((public, internal)) == (public,)


def test_response_state_tracks_public_message_author() -> None:
    assert response_state_after_public_message(MessagingSenderType.CUSTOMER) == MessagingResponseState.WAITING_ADMIN
    assert response_state_after_public_message(MessagingSenderType.ADMIN) == MessagingResponseState.WAITING_CUSTOMER
    assert response_state_after_public_message(MessagingSenderType.SYSTEM) == MessagingResponseState.NONE


def test_idempotency_key_is_deterministic_and_bounded() -> None:
    conversation_id = uuid4()
    actor_id = uuid4()

    first = build_message_idempotency_key(
        actor_type="admin",
        actor_id=actor_id,
        conversation_id=conversation_id,
        client_message_id="client-message",
    )
    second = build_message_idempotency_key(
        actor_type="admin",
        actor_id=actor_id,
        conversation_id=conversation_id,
        client_message_id="client-message",
    )

    assert first == second
    assert len(first) <= 160


def test_message_body_and_subject_are_plain_text_required_values() -> None:
    assert normalize_message_body("  hello  ") == "hello"
    assert normalize_subject("  Renewal   notice  ") == "Renewal notice"
    with pytest.raises(ValueError, match="body is required"):
        normalize_message_body("   ")
    with pytest.raises(ValueError, match="subject is required"):
        normalize_subject("   ")


def test_notification_action_url_must_be_relative() -> None:
    assert_relative_action_url("/status")
    with pytest.raises(ValueError, match="relative"):
        assert_relative_action_url("https://example.com/status")


def test_presence_projection_is_ephemeral_domain_state() -> None:
    projection = MessagingPresenceProjection(
        participant_type=MessagingParticipantType.CUSTOMER,
        participant_id=uuid4(),
        status=PresenceStatus.ONLINE,
        observed_at=datetime.now(UTC),
        connection_count=2,
    )

    assert projection.status == PresenceStatus.ONLINE
    assert projection.connection_count == 2
