"""SQLAlchemy repository for messaging persistence."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import String, cast, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.domain.entities.messaging import (
    BroadcastAudienceType,
    BroadcastCampaign,
    BroadcastCampaignNotFoundError,
    BroadcastCampaignRecipient,
    BroadcastCampaignStatus,
    BroadcastRecipientStatus,
    MessagingBodyFormat,
    MessagingConversation,
    MessagingConversationCategory,
    MessagingConversationParticipant,
    MessagingConversationStatus,
    MessagingForbiddenError,
    MessagingMessage,
    MessagingMessageReadState,
    MessagingMessageVisibility,
    MessagingParticipantRole,
    MessagingParticipantType,
    MessagingPriority,
    MessagingResponseState,
    MessagingSenderType,
    SiteNotification,
    SiteNotificationDelivery,
    SiteNotificationDeliveryChannel,
    SiteNotificationDeliveryStatus,
    SiteNotificationRecipientType,
    SiteNotificationSeverity,
    SiteNotificationType,
    assert_message_sender_attribution,
    assert_message_write_allowed,
    response_state_after_public_message,
)
from src.domain.repositories.messaging_repository import (
    MessagingConversationListResult,
    MessagingMessageWriteResult,
    MessagingRepository,
    SiteNotificationDeliveryView,
    SiteNotificationListResult,
    SiteNotificationWriteResult,
)
from src.domain.value_objects.messaging import (
    assert_relative_action_url,
    normalize_message_body,
    normalize_subject,
)
from src.infrastructure.database.models.messaging_broadcast_model import (
    BroadcastCampaignModel,
    BroadcastCampaignRecipientModel,
)
from src.infrastructure.database.models.messaging_conversation_model import (
    MessagingConversationModel,
    MessagingConversationParticipantModel,
    MessagingMessageModel,
    MessagingMessageReadStateModel,
)
from src.infrastructure.database.models.messaging_notification_model import (
    SiteNotificationDeliveryModel,
    SiteNotificationModel,
)


def _utc_now() -> datetime:
    return datetime.now(UTC)


def _parse_uuid(value: str) -> UUID | None:
    try:
        return UUID(value)
    except ValueError:
        return None


def _parse_cursor(cursor: str | None) -> int:
    if cursor is None:
        return 0
    try:
        value = int(cursor)
    except ValueError:
        return 0
    return max(value, 0)


class SQLAlchemyMessagingRepository(MessagingRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create_conversation(
        self,
        *,
        conversation_id: UUID | None = None,
        public_id: str,
        customer_account_id: UUID,
        created_by_admin_id: UUID | None,
        assigned_admin_id: UUID | None,
        category: MessagingConversationCategory,
        priority: MessagingPriority,
        subject: str,
        initial_message_public_id: str,
        initial_message_body: str,
        initial_message_client_id: str | None,
        initial_message_idempotency_key: str,
        related_support_ticket_id: UUID | None = None,
        metadata: dict[str, object] | None = None,
        now: datetime | None = None,
    ) -> MessagingConversation:
        now = now or _utc_now()
        conversation_kwargs: dict[str, object] = {}
        if conversation_id is not None:
            conversation_kwargs["id"] = conversation_id
        conversation = MessagingConversationModel(
            **conversation_kwargs,
            public_id=public_id,
            customer_account_id=customer_account_id,
            status=MessagingConversationStatus.OPEN.value,
            response_state=MessagingResponseState.WAITING_CUSTOMER.value,
            category=category.value,
            priority=priority.value,
            subject=normalize_subject(subject),
            created_by_admin_id=created_by_admin_id,
            assigned_admin_id=assigned_admin_id,
            related_support_ticket_id=related_support_ticket_id,
            metadata_json=metadata or {},
            created_at=now,
            updated_at=now,
        )
        self._session.add(conversation)
        await self._session.flush()

        participants = [
            MessagingConversationParticipantModel(
                conversation_id=conversation.id,
                participant_type=MessagingParticipantType.CUSTOMER.value,
                participant_id=customer_account_id,
                role=MessagingParticipantRole.CUSTOMER.value,
                can_read=True,
                can_write=True,
                joined_at=now,
                metadata_json={},
            )
        ]
        if created_by_admin_id is not None:
            participants.append(
                MessagingConversationParticipantModel(
                    conversation_id=conversation.id,
                    participant_type=MessagingParticipantType.ADMIN.value,
                    participant_id=created_by_admin_id,
                    role=MessagingParticipantRole.CREATOR.value,
                    can_read=True,
                    can_write=True,
                    joined_at=now,
                    metadata_json={},
                )
            )
        if assigned_admin_id is not None and assigned_admin_id != created_by_admin_id:
            participants.append(
                MessagingConversationParticipantModel(
                    conversation_id=conversation.id,
                    participant_type=MessagingParticipantType.ADMIN.value,
                    participant_id=assigned_admin_id,
                    role=MessagingParticipantRole.ASSIGNEE.value,
                    can_read=True,
                    can_write=True,
                    joined_at=now,
                    metadata_json={},
                )
            )
        self._session.add_all(participants)

        message = MessagingMessageModel(
            public_id=initial_message_public_id,
            conversation_id=conversation.id,
            sender_type=MessagingSenderType.ADMIN.value
            if created_by_admin_id is not None
            else MessagingSenderType.SYSTEM.value,
            sender_id=created_by_admin_id,
            visibility=MessagingMessageVisibility.PUBLIC.value,
            body=normalize_message_body(initial_message_body),
            body_format=MessagingBodyFormat.PLAIN_TEXT.value,
            client_message_id=initial_message_client_id,
            idempotency_key=initial_message_idempotency_key,
            metadata_json={},
            created_at=now,
            updated_at=now,
        )
        self._session.add(message)
        await self._session.flush()

        conversation.last_message_id = message.id
        conversation.last_message_at = now
        await self._session.flush()
        return await self._get_required_conversation(conversation.id)

    async def get_conversation(self, conversation_ref: str) -> MessagingConversation | None:
        stmt = self._detail_select()
        conversation_id = _parse_uuid(conversation_ref)
        if conversation_id is None:
            stmt = stmt.where(MessagingConversationModel.public_id == conversation_ref)
        else:
            stmt = stmt.where(
                or_(
                    MessagingConversationModel.id == conversation_id,
                    MessagingConversationModel.public_id == conversation_ref,
                )
            )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return self._to_conversation_domain(model) if model is not None else None

    async def list_for_customer(
        self,
        *,
        customer_account_id: UUID,
        status: MessagingConversationStatus | None = None,
        cursor: str | None = None,
        limit: int = 50,
    ) -> MessagingConversationListResult:
        offset = _parse_cursor(cursor)
        bounded_limit = min(max(limit, 1), 100)
        stmt = self._detail_select().where(MessagingConversationModel.customer_account_id == customer_account_id)
        if status is not None:
            stmt = stmt.where(MessagingConversationModel.status == status.value)
        result = await self._session.execute(
            stmt.order_by(MessagingConversationModel.updated_at.desc(), MessagingConversationModel.id.desc())
            .offset(offset)
            .limit(bounded_limit + 1)
        )
        models = list(result.scalars().unique().all())
        next_cursor = str(offset + bounded_limit) if len(models) > bounded_limit else None
        return MessagingConversationListResult(
            conversations=tuple(
                self._to_conversation_domain(model, include_internal_messages=False) for model in models[:bounded_limit]
            ),
            next_cursor=next_cursor,
        )

    async def list_for_admin(
        self,
        *,
        status: MessagingConversationStatus | None = None,
        category: MessagingConversationCategory | None = None,
        priority: MessagingPriority | None = None,
        assigned_admin_id: UUID | None = None,
        customer_account_id: UUID | None = None,
        query: str | None = None,
        cursor: str | None = None,
        limit: int = 50,
    ) -> MessagingConversationListResult:
        offset = _parse_cursor(cursor)
        bounded_limit = min(max(limit, 1), 100)
        stmt = self._detail_select()
        if status is not None:
            stmt = stmt.where(MessagingConversationModel.status == status.value)
        if category is not None:
            stmt = stmt.where(MessagingConversationModel.category == category.value)
        if priority is not None:
            stmt = stmt.where(MessagingConversationModel.priority == priority.value)
        if assigned_admin_id is not None:
            stmt = stmt.where(MessagingConversationModel.assigned_admin_id == assigned_admin_id)
        if customer_account_id is not None:
            stmt = stmt.where(MessagingConversationModel.customer_account_id == customer_account_id)
        if query:
            pattern = f"%{query.strip()}%"
            stmt = stmt.where(
                or_(
                    MessagingConversationModel.public_id.ilike(pattern),
                    MessagingConversationModel.subject.ilike(pattern),
                    cast(MessagingConversationModel.customer_account_id, String).ilike(pattern),
                )
            )
        result = await self._session.execute(
            stmt.order_by(MessagingConversationModel.updated_at.desc(), MessagingConversationModel.id.desc())
            .offset(offset)
            .limit(bounded_limit + 1)
        )
        models = list(result.scalars().unique().all())
        next_cursor = str(offset + bounded_limit) if len(models) > bounded_limit else None
        return MessagingConversationListResult(
            conversations=tuple(self._to_conversation_domain(model) for model in models[:bounded_limit]),
            next_cursor=next_cursor,
        )

    async def add_message(
        self,
        *,
        public_id: str,
        conversation_id: UUID,
        sender_type: MessagingSenderType,
        sender_id: UUID | None,
        visibility: MessagingMessageVisibility,
        body: str,
        client_message_id: str | None,
        idempotency_key: str,
        body_format: MessagingBodyFormat = MessagingBodyFormat.PLAIN_TEXT,
        reply_to_message_id: UUID | None = None,
        metadata: dict[str, object] | None = None,
        now: datetime | None = None,
    ) -> MessagingMessageWriteResult:
        existing = await self._get_message_by_idempotency_key(idempotency_key)
        if existing is not None:
            conversation = await self._get_required_conversation(existing.conversation_id)
            return MessagingMessageWriteResult(
                conversation=conversation,
                message=self._to_message_domain(existing),
                created=False,
            )

        assert_message_sender_attribution(sender_type=sender_type, sender_id=sender_id)
        conversation = await self._get_required_conversation(conversation_id)
        assert_message_write_allowed(
            conversation=conversation,
            sender_type=sender_type,
            visibility=visibility,
        )
        now = now or _utc_now()
        model = MessagingMessageModel(
            public_id=public_id,
            conversation_id=conversation_id,
            sender_type=sender_type.value,
            sender_id=sender_id,
            visibility=visibility.value,
            body=normalize_message_body(body),
            body_format=body_format.value,
            client_message_id=client_message_id,
            idempotency_key=idempotency_key,
            reply_to_message_id=reply_to_message_id,
            metadata_json=metadata or {},
            created_at=now,
            updated_at=now,
        )
        self._session.add(model)
        await self._session.flush()

        conversation_model = await self._get_conversation_model(conversation_id)
        if conversation_model is None:
            raise LookupError("Conversation not found")
        conversation_model.updated_at = now
        if visibility == MessagingMessageVisibility.PUBLIC:
            conversation_model.last_message_id = model.id
            conversation_model.last_message_at = now
            conversation_model.response_state = response_state_after_public_message(sender_type).value
        await self._session.flush()
        return MessagingMessageWriteResult(
            conversation=await self._get_required_conversation(conversation_id),
            message=self._to_message_domain(model),
            created=True,
        )

    async def mark_read(
        self,
        *,
        conversation_id: UUID,
        participant_type: MessagingParticipantType,
        participant_id: UUID,
        last_read_message_id: UUID | None,
        now: datetime | None = None,
    ) -> MessagingMessageReadState:
        now = now or _utc_now()
        await self._assert_participant_can_read(
            conversation_id=conversation_id,
            participant_type=participant_type,
            participant_id=participant_id,
        )
        if last_read_message_id is not None:
            await self._assert_message_readable_by_participant(
                conversation_id=conversation_id,
                participant_type=participant_type,
                message_id=last_read_message_id,
            )
        result = await self._session.execute(
            select(MessagingMessageReadStateModel).where(
                MessagingMessageReadStateModel.conversation_id == conversation_id,
                MessagingMessageReadStateModel.participant_type == participant_type.value,
                MessagingMessageReadStateModel.participant_id == participant_id,
            )
        )
        model = result.scalar_one_or_none()
        if model is None:
            model = MessagingMessageReadStateModel(
                conversation_id=conversation_id,
                participant_type=participant_type.value,
                participant_id=participant_id,
                last_read_message_id=last_read_message_id,
                last_read_at=now,
                updated_at=now,
            )
            self._session.add(model)
        else:
            model.last_read_message_id = last_read_message_id
            model.last_read_at = now
            model.updated_at = now
        await self._session.flush()
        return self._to_read_state_domain(model)

    async def update_conversation(
        self,
        *,
        conversation_id: UUID,
        status: MessagingConversationStatus | None = None,
        category: MessagingConversationCategory | None = None,
        priority: MessagingPriority | None = None,
        assigned_admin_id: UUID | None = None,
        assigned_admin_id_set: bool = False,
        closed_at: datetime | None = None,
        now: datetime | None = None,
    ) -> MessagingConversation:
        now = now or _utc_now()
        model = await self._get_conversation_model(conversation_id)
        if model is None:
            raise LookupError("Conversation not found")

        if status is not None:
            model.status = status.value
            model.closed_at = closed_at if status == MessagingConversationStatus.CLOSED else None
        if category is not None:
            model.category = category.value
        if priority is not None:
            model.priority = priority.value
        if assigned_admin_id_set:
            model.assigned_admin_id = assigned_admin_id
            if assigned_admin_id is not None:
                await self._upsert_admin_participant(
                    conversation_id=conversation_id,
                    admin_id=assigned_admin_id,
                    now=now,
                )
        model.updated_at = now
        await self._session.flush()
        return await self._get_required_conversation(conversation_id)

    async def create_site_notification(
        self,
        *,
        notification_type: SiteNotificationType,
        severity: SiteNotificationSeverity,
        title: str,
        recipient_type: SiteNotificationRecipientType,
        recipient_id: UUID | None,
        delivery_channel: SiteNotificationDeliveryChannel = SiteNotificationDeliveryChannel.SITE,
        body: str | None = None,
        action_url: str | None = None,
        aggregate_type: str | None = None,
        aggregate_id: str | None = None,
        conversation_id: UUID | None = None,
        message_id: UUID | None = None,
        broadcast_campaign_id: UUID | None = None,
        created_by_actor_type: str = "system",
        created_by_actor_id: UUID | None = None,
        payload: dict[str, object] | None = None,
        expires_at: datetime | None = None,
        now: datetime | None = None,
    ) -> SiteNotificationWriteResult:
        assert_relative_action_url(action_url)
        if recipient_id is None:
            raise MessagingForbiddenError("Notification delivery recipient_id is required")
        now = now or _utc_now()
        notification = SiteNotificationModel(
            notification_type=notification_type.value,
            severity=severity.value,
            title=title.strip(),
            body=body.strip() if body is not None else None,
            action_url=action_url,
            aggregate_type=aggregate_type,
            aggregate_id=aggregate_id,
            conversation_id=conversation_id,
            message_id=message_id,
            broadcast_campaign_id=broadcast_campaign_id,
            created_by_actor_type=created_by_actor_type,
            created_by_actor_id=created_by_actor_id,
            payload=payload or {},
            expires_at=expires_at,
            created_at=now,
            updated_at=now,
        )
        self._session.add(notification)
        await self._session.flush()

        delivery = SiteNotificationDeliveryModel(
            notification_id=notification.id,
            recipient_type=recipient_type.value,
            recipient_id=recipient_id,
            delivery_channel=delivery_channel.value,
            status=SiteNotificationDeliveryStatus.PENDING.value,
            attempts=0,
            created_at=now,
            updated_at=now,
        )
        self._session.add(delivery)
        await self._session.flush()
        return SiteNotificationWriteResult(
            notification=self._to_site_notification_domain(notification),
            delivery=self._to_site_delivery_domain(delivery),
            created=True,
        )

    async def list_site_notifications(
        self,
        *,
        recipient_type: SiteNotificationRecipientType,
        recipient_id: UUID,
        cursor: str | None = None,
        limit: int = 50,
    ) -> SiteNotificationListResult:
        offset = _parse_cursor(cursor)
        bounded_limit = min(max(limit, 1), 100)
        result = await self._session.execute(
            select(SiteNotificationDeliveryModel, SiteNotificationModel)
            .join(SiteNotificationModel, SiteNotificationModel.id == SiteNotificationDeliveryModel.notification_id)
            .where(
                SiteNotificationDeliveryModel.recipient_type == recipient_type.value,
                SiteNotificationDeliveryModel.recipient_id == recipient_id,
                SiteNotificationDeliveryModel.status != SiteNotificationDeliveryStatus.DISMISSED.value,
            )
            .order_by(SiteNotificationModel.created_at.desc(), SiteNotificationDeliveryModel.id.desc())
            .offset(offset)
            .limit(bounded_limit + 1)
        )
        rows = list(result.all())
        next_cursor = str(offset + bounded_limit) if len(rows) > bounded_limit else None
        return SiteNotificationListResult(
            notifications=tuple(
                SiteNotificationDeliveryView(
                    notification=self._to_site_notification_domain(notification),
                    delivery=self._to_site_delivery_domain(delivery),
                )
                for delivery, notification in rows[:bounded_limit]
            ),
            next_cursor=next_cursor,
        )

    async def mark_site_notifications(
        self,
        *,
        recipient_type: SiteNotificationRecipientType,
        recipient_id: UUID,
        notification_ids: tuple[UUID, ...],
        read_all_before: datetime | None,
        status: SiteNotificationDeliveryStatus,
        now: datetime | None = None,
    ) -> tuple[SiteNotificationDeliveryView, ...]:
        now = now or _utc_now()
        stmt = (
            select(SiteNotificationDeliveryModel, SiteNotificationModel)
            .join(SiteNotificationModel, SiteNotificationModel.id == SiteNotificationDeliveryModel.notification_id)
            .where(
                SiteNotificationDeliveryModel.recipient_type == recipient_type.value,
                SiteNotificationDeliveryModel.recipient_id == recipient_id,
            )
        )
        if notification_ids:
            stmt = stmt.where(SiteNotificationModel.id.in_(notification_ids))
        elif read_all_before is not None:
            stmt = stmt.where(SiteNotificationModel.created_at <= read_all_before)
        else:
            return ()

        result = await self._session.execute(stmt)
        rows = list(result.all())
        for delivery, _notification in rows:
            delivery.status = status.value
            delivery.updated_at = now
            if status == SiteNotificationDeliveryStatus.READ:
                delivery.read_at = now
            elif status == SiteNotificationDeliveryStatus.DISMISSED:
                delivery.dismissed_at = now
        await self._session.flush()
        return tuple(
            SiteNotificationDeliveryView(
                notification=self._to_site_notification_domain(notification),
                delivery=self._to_site_delivery_domain(delivery),
            )
            for delivery, notification in rows
        )

    async def count_unread_site_notifications(
        self,
        *,
        recipient_type: SiteNotificationRecipientType,
        recipient_id: UUID,
    ) -> int:
        result = await self._session.execute(
            select(func.count(SiteNotificationDeliveryModel.id)).where(
                SiteNotificationDeliveryModel.recipient_type == recipient_type.value,
                SiteNotificationDeliveryModel.recipient_id == recipient_id,
                SiteNotificationDeliveryModel.status.not_in(
                    (
                        SiteNotificationDeliveryStatus.READ.value,
                        SiteNotificationDeliveryStatus.DISMISSED.value,
                        SiteNotificationDeliveryStatus.EXPIRED.value,
                    )
                ),
            )
        )
        return int(result.scalar_one())

    async def create_broadcast_campaign(
        self,
        *,
        public_id: str,
        name: str,
        audience_type: BroadcastAudienceType,
        audience_filter: dict[str, object],
        title: str,
        body: str,
        created_by_admin_id: UUID,
        status: BroadcastCampaignStatus = BroadcastCampaignStatus.DRAFT,
        template_key: str | None = None,
        action_url: str | None = None,
        scheduled_at: datetime | None = None,
        metadata: dict[str, object] | None = None,
        now: datetime | None = None,
    ) -> BroadcastCampaign:
        assert_relative_action_url(action_url)
        now = now or _utc_now()
        model = BroadcastCampaignModel(
            public_id=public_id,
            name=name.strip(),
            status=status.value,
            audience_type=audience_type.value,
            audience_filter=audience_filter,
            template_key=template_key,
            title=title.strip(),
            body=normalize_message_body(body),
            action_url=action_url,
            scheduled_at=scheduled_at,
            created_by_admin_id=created_by_admin_id,
            metadata_json=metadata or {},
            created_at=now,
            updated_at=now,
        )
        self._session.add(model)
        await self._session.flush()
        return self._to_broadcast_campaign_domain(model)

    async def cancel_broadcast_campaign(
        self,
        *,
        campaign_ref: str,
        cancelled_at: datetime | None = None,
    ) -> BroadcastCampaign:
        now = cancelled_at or _utc_now()
        stmt = select(BroadcastCampaignModel)
        campaign_id = _parse_uuid(campaign_ref)
        if campaign_id is None:
            stmt = stmt.where(BroadcastCampaignModel.public_id == campaign_ref)
        else:
            stmt = stmt.where(
                or_(
                    BroadcastCampaignModel.id == campaign_id,
                    BroadcastCampaignModel.public_id == campaign_ref,
                )
            )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        if model is None:
            raise BroadcastCampaignNotFoundError("Broadcast campaign not found")
        if model.status in {
            BroadcastCampaignStatus.SENT.value,
            BroadcastCampaignStatus.FAILED.value,
        }:
            raise MessagingForbiddenError("Broadcast campaign cannot be cancelled")
        if model.status != BroadcastCampaignStatus.CANCELLED.value:
            model.status = BroadcastCampaignStatus.CANCELLED.value
            model.cancelled_at = now
            model.updated_at = now
            await self._session.flush()
        return self._to_broadcast_campaign_domain(model)

    async def add_broadcast_recipient(
        self,
        *,
        campaign_id: UUID,
        recipient_type: SiteNotificationRecipientType,
        recipient_id: UUID,
        status: BroadcastRecipientStatus = BroadcastRecipientStatus.PENDING,
        site_notification_id: UUID | None = None,
        skip_reason: str | None = None,
        failure_reason: str | None = None,
        now: datetime | None = None,
    ) -> BroadcastCampaignRecipient:
        now = now or _utc_now()
        model = BroadcastCampaignRecipientModel(
            campaign_id=campaign_id,
            recipient_type=recipient_type.value,
            recipient_id=recipient_id,
            site_notification_id=site_notification_id,
            status=status.value,
            skip_reason=skip_reason,
            failure_reason=failure_reason,
            materialized_at=now,
            created_at=now,
            updated_at=now,
        )
        self._session.add(model)
        await self._session.flush()
        return self._to_broadcast_recipient_domain(model)

    def _detail_select(self):
        return select(MessagingConversationModel).options(
            selectinload(MessagingConversationModel.participants),
            selectinload(MessagingConversationModel.messages),
            selectinload(MessagingConversationModel.read_states),
        )

    async def _get_conversation_model(self, conversation_id: UUID) -> MessagingConversationModel | None:
        result = await self._session.execute(
            select(MessagingConversationModel).where(MessagingConversationModel.id == conversation_id)
        )
        return result.scalar_one_or_none()

    async def _get_required_conversation(self, conversation_id: UUID) -> MessagingConversation:
        result = await self._session.execute(
            self._detail_select().where(MessagingConversationModel.id == conversation_id)
        )
        model = result.scalar_one_or_none()
        if model is None:
            raise LookupError("Conversation not found")
        return self._to_conversation_domain(model)

    async def _get_message_by_idempotency_key(self, idempotency_key: str) -> MessagingMessageModel | None:
        result = await self._session.execute(
            select(MessagingMessageModel).where(MessagingMessageModel.idempotency_key == idempotency_key)
        )
        return result.scalar_one_or_none()

    async def _upsert_admin_participant(
        self,
        *,
        conversation_id: UUID,
        admin_id: UUID,
        now: datetime,
    ) -> None:
        result = await self._session.execute(
            select(MessagingConversationParticipantModel).where(
                MessagingConversationParticipantModel.conversation_id == conversation_id,
                MessagingConversationParticipantModel.participant_type == MessagingParticipantType.ADMIN.value,
                MessagingConversationParticipantModel.participant_id == admin_id,
                MessagingConversationParticipantModel.role == MessagingParticipantRole.ASSIGNEE.value,
                MessagingConversationParticipantModel.left_at.is_(None),
            )
        )
        if result.scalar_one_or_none() is not None:
            return
        self._session.add(
            MessagingConversationParticipantModel(
                conversation_id=conversation_id,
                participant_type=MessagingParticipantType.ADMIN.value,
                participant_id=admin_id,
                role=MessagingParticipantRole.ASSIGNEE.value,
                can_read=True,
                can_write=True,
                joined_at=now,
                metadata_json={},
            )
        )

    async def _assert_participant_can_read(
        self,
        *,
        conversation_id: UUID,
        participant_type: MessagingParticipantType,
        participant_id: UUID,
    ) -> None:
        result = await self._session.execute(
            select(MessagingConversationParticipantModel).where(
                MessagingConversationParticipantModel.conversation_id == conversation_id,
                MessagingConversationParticipantModel.participant_type == participant_type.value,
                MessagingConversationParticipantModel.participant_id == participant_id,
                MessagingConversationParticipantModel.left_at.is_(None),
                MessagingConversationParticipantModel.can_read.is_(True),
            )
        )
        if result.scalar_one_or_none() is None:
            raise MessagingForbiddenError("Participant cannot read conversation")

    async def _assert_message_readable_by_participant(
        self,
        *,
        conversation_id: UUID,
        participant_type: MessagingParticipantType,
        message_id: UUID,
    ) -> None:
        result = await self._session.execute(
            select(MessagingMessageModel).where(MessagingMessageModel.id == message_id)
        )
        message = result.scalar_one_or_none()
        if message is None or message.conversation_id != conversation_id:
            raise MessagingForbiddenError("Message does not belong to readable conversation")
        if (
            participant_type == MessagingParticipantType.CUSTOMER
            and message.visibility != MessagingMessageVisibility.PUBLIC.value
        ):
            raise MessagingForbiddenError("Customer read state cannot target internal messages")

    @staticmethod
    def _to_conversation_domain(
        model: MessagingConversationModel,
        *,
        include_internal_messages: bool = True,
    ) -> MessagingConversation:
        messages = tuple(SQLAlchemyMessagingRepository._to_message_domain(item) for item in model.messages)
        if not include_internal_messages:
            messages = tuple(message for message in messages if message.visibility == MessagingMessageVisibility.PUBLIC)
        return MessagingConversation(
            id=model.id,
            public_id=model.public_id,
            customer_account_id=model.customer_account_id,
            status=MessagingConversationStatus(model.status),
            response_state=MessagingResponseState(model.response_state),
            category=MessagingConversationCategory(model.category),
            priority=MessagingPriority(model.priority),
            subject=model.subject,
            created_by_admin_id=model.created_by_admin_id,
            assigned_admin_id=model.assigned_admin_id,
            related_support_ticket_id=model.related_support_ticket_id,
            last_message_id=model.last_message_id,
            last_message_at=model.last_message_at,
            closed_at=model.closed_at,
            metadata=dict(model.metadata_json or {}),
            created_at=model.created_at,
            updated_at=model.updated_at,
            participants=tuple(
                SQLAlchemyMessagingRepository._to_participant_domain(item) for item in model.participants
            ),
            messages=messages,
            read_states=tuple(SQLAlchemyMessagingRepository._to_read_state_domain(item) for item in model.read_states),
        )

    @staticmethod
    def _to_participant_domain(model: MessagingConversationParticipantModel) -> MessagingConversationParticipant:
        return MessagingConversationParticipant(
            id=model.id,
            conversation_id=model.conversation_id,
            participant_type=MessagingParticipantType(model.participant_type),
            participant_id=model.participant_id,
            role=MessagingParticipantRole(model.role),
            can_read=model.can_read,
            can_write=model.can_write,
            joined_at=model.joined_at,
            left_at=model.left_at,
            metadata=dict(model.metadata_json or {}),
        )

    @staticmethod
    def _to_message_domain(model: MessagingMessageModel) -> MessagingMessage:
        return MessagingMessage(
            id=model.id,
            public_id=model.public_id,
            conversation_id=model.conversation_id,
            sender_type=MessagingSenderType(model.sender_type),
            sender_id=model.sender_id,
            visibility=MessagingMessageVisibility(model.visibility),
            body=model.body,
            body_format=MessagingBodyFormat(model.body_format),
            client_message_id=model.client_message_id,
            idempotency_key=model.idempotency_key,
            reply_to_message_id=model.reply_to_message_id,
            redacted_at=model.redacted_at,
            created_at=model.created_at,
            updated_at=model.updated_at,
            metadata=dict(model.metadata_json or {}),
        )

    @staticmethod
    def _to_read_state_domain(model: MessagingMessageReadStateModel) -> MessagingMessageReadState:
        return MessagingMessageReadState(
            id=model.id,
            conversation_id=model.conversation_id,
            participant_type=MessagingParticipantType(model.participant_type),
            participant_id=model.participant_id,
            last_read_message_id=model.last_read_message_id,
            last_read_at=model.last_read_at,
            updated_at=model.updated_at,
        )

    @staticmethod
    def _to_site_notification_domain(model: SiteNotificationModel) -> SiteNotification:
        return SiteNotification(
            id=model.id,
            notification_type=SiteNotificationType(model.notification_type),
            severity=SiteNotificationSeverity(model.severity),
            title=model.title,
            body=model.body,
            action_url=model.action_url,
            aggregate_type=model.aggregate_type,
            aggregate_id=model.aggregate_id,
            conversation_id=model.conversation_id,
            message_id=model.message_id,
            broadcast_campaign_id=model.broadcast_campaign_id,
            created_by_actor_type=model.created_by_actor_type,
            created_by_actor_id=model.created_by_actor_id,
            payload=dict(model.payload or {}),
            expires_at=model.expires_at,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )

    @staticmethod
    def _to_site_delivery_domain(model: SiteNotificationDeliveryModel) -> SiteNotificationDelivery:
        return SiteNotificationDelivery(
            id=model.id,
            notification_id=model.notification_id,
            recipient_type=SiteNotificationRecipientType(model.recipient_type),
            recipient_id=model.recipient_id,
            delivery_channel=SiteNotificationDeliveryChannel(model.delivery_channel),
            status=SiteNotificationDeliveryStatus(model.status),
            delivered_at=model.delivered_at,
            read_at=model.read_at,
            dismissed_at=model.dismissed_at,
            attempts=model.attempts,
            last_error=model.last_error,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )

    @staticmethod
    def _to_broadcast_campaign_domain(model: BroadcastCampaignModel) -> BroadcastCampaign:
        return BroadcastCampaign(
            id=model.id,
            public_id=model.public_id,
            name=model.name,
            status=BroadcastCampaignStatus(model.status),
            audience_type=BroadcastAudienceType(model.audience_type),
            audience_filter=dict(model.audience_filter or {}),
            template_key=model.template_key,
            title=model.title,
            body=model.body,
            action_url=model.action_url,
            scheduled_at=model.scheduled_at,
            created_by_admin_id=model.created_by_admin_id,
            approved_by_admin_id=model.approved_by_admin_id,
            cancelled_at=model.cancelled_at,
            created_at=model.created_at,
            updated_at=model.updated_at,
            metadata=dict(model.metadata_json or {}),
        )

    @staticmethod
    def _to_broadcast_recipient_domain(model: BroadcastCampaignRecipientModel) -> BroadcastCampaignRecipient:
        return BroadcastCampaignRecipient(
            id=model.id,
            campaign_id=model.campaign_id,
            recipient_type=SiteNotificationRecipientType(model.recipient_type),
            recipient_id=model.recipient_id,
            site_notification_id=model.site_notification_id,
            status=BroadcastRecipientStatus(model.status),
            skip_reason=model.skip_reason,
            failure_reason=model.failure_reason,
            materialized_at=model.materialized_at,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )
