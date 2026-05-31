import os

os.environ.setdefault("ENVIRONMENT", "test")
os.environ.setdefault("REMNAWAVE_TOKEN", "local-remnawave-token")
os.environ.setdefault("CRYPTOBOT_TOKEN", "local-cryptobot-token")
os.environ.setdefault("JWT_SECRET", "0123456789abcdef0123456789abcdef")

from src.infrastructure.database.models.messaging_broadcast_model import (  # noqa: E402
    BroadcastCampaignModel,
    BroadcastCampaignRecipientModel,
)
from src.infrastructure.database.models.messaging_conversation_model import (  # noqa: E402
    MessagingConversationModel,
    MessagingConversationParticipantModel,
    MessagingMessageModel,
    MessagingMessageReadStateModel,
)
from src.infrastructure.database.models.messaging_notification_model import (  # noqa: E402
    SiteNotificationDeliveryModel,
    SiteNotificationModel,
)


def test_messaging_models_use_rfc_table_names() -> None:
    assert MessagingConversationModel.__tablename__ == "messaging_conversations"
    assert MessagingConversationParticipantModel.__tablename__ == "messaging_conversation_participants"
    assert MessagingMessageModel.__tablename__ == "messaging_messages"
    assert MessagingMessageReadStateModel.__tablename__ == "messaging_message_read_states"
    assert SiteNotificationModel.__tablename__ == "site_notifications"
    assert SiteNotificationDeliveryModel.__tablename__ == "site_notification_deliveries"
    assert BroadcastCampaignModel.__tablename__ == "broadcast_campaigns"
    assert BroadcastCampaignRecipientModel.__tablename__ == "broadcast_campaign_recipients"


def test_message_model_has_idempotency_and_internal_note_constraints() -> None:
    table = MessagingMessageModel.__table__

    assert "uq_messaging_messages_idempotency_key" in {constraint.name for constraint in table.constraints}
    assert "ck_messaging_messages_internal_sender" in {constraint.name for constraint in table.constraints}
    assert "ck_messaging_messages_actor_required" in {constraint.name for constraint in table.constraints}
    assert "uq_messaging_messages_client_message" in {index.name for index in table.indexes}

    client_index = next(index for index in table.indexes if index.name == "uq_messaging_messages_client_message")
    assert client_index.unique is True
    assert str(client_index.dialect_options["postgresql"]["where"]) == "client_message_id IS NOT NULL"


def test_participant_model_limits_active_customer_per_conversation() -> None:
    table = MessagingConversationParticipantModel.__table__
    index = next(index for index in table.indexes if index.name == "uq_messaging_participants_active_customer")

    assert index.unique is True
    assert "participant_type = 'customer'" in str(index.dialect_options["postgresql"]["where"])


def test_notification_delivery_model_is_unique_per_recipient_channel() -> None:
    table = SiteNotificationDeliveryModel.__table__

    assert "uq_site_notification_deliveries_recipient_channel" in {constraint.name for constraint in table.constraints}
    assert "ck_site_notification_deliveries_recipient_required" in {constraint.name for constraint in table.constraints}
    assert "ix_site_notification_deliveries_recipient_status_created" in {index.name for index in table.indexes}
