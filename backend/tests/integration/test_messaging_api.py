from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest
from httpx import AsyncClient
from sqlalchemy import select

from src.domain.enums import AdminRole
from src.infrastructure.database.models.admin_user_model import AdminUserModel
from src.infrastructure.database.models.auth_realm_model import AuthRealmModel
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
from src.infrastructure.database.models.mobile_user_model import MobileUserModel
from src.infrastructure.database.models.outbox_event_model import OutboxEventModel, OutboxPublicationModel
from src.infrastructure.database.models.support_ticket_model import (
    SupportTicketEventModel,
    SupportTicketMessageModel,
    SupportTicketModel,
)
from src.main import app
from src.presentation.dependencies.auth import get_current_active_user, get_current_mobile_user_id
from tests.helpers.realm_auth import (
    cleanup_sqlite_file,
    create_realm_test_sessionmaker,
    initialize_realm_test_database,
    override_realm_test_db,
)

pytestmark = [pytest.mark.integration]

ADMIN_HOST_HEADERS = {"host": "testserver"}


@pytest.fixture(autouse=True)
def _clear_dependency_overrides():
    yield
    app.dependency_overrides.pop(get_current_mobile_user_id, None)
    app.dependency_overrides.pop(get_current_active_user, None)


def _create_messaging_tables(engine) -> None:
    with engine.begin() as conn:
        for table in (
            SupportTicketModel.__table__,
            SupportTicketMessageModel.__table__,
            SupportTicketEventModel.__table__,
            MessagingConversationModel.__table__,
            MessagingConversationParticipantModel.__table__,
            MessagingMessageModel.__table__,
            MessagingMessageReadStateModel.__table__,
            BroadcastCampaignModel.__table__,
            SiteNotificationModel.__table__,
            SiteNotificationDeliveryModel.__table__,
            BroadcastCampaignRecipientModel.__table__,
        ):
            table.create(conn, checkfirst=True)
        # SQLite ignores the PostgreSQL partial-index predicate on this model.
        # The PostgreSQL migration/model keeps the invariant; this local harness
        # drops the degraded test index so admin participants can coexist.
        conn.exec_driver_sql("DROP INDEX IF EXISTS uq_messaging_participants_active_customer")


def _override_mobile_user(user_id: uuid.UUID) -> None:
    app.dependency_overrides[get_current_mobile_user_id] = lambda: user_id


def _override_admin_user(user: AdminUserModel) -> None:
    app.dependency_overrides[get_current_active_user] = lambda: user


def _admin_user(role: AdminRole | str = AdminRole.SUPPORT) -> AdminUserModel:
    role_value = role.value if isinstance(role, AdminRole) else role
    now = datetime.now(UTC)
    return AdminUserModel(
        id=uuid.uuid4(),
        login=f"messaging-{role_value}",
        email=f"messaging-{role_value}@example.test",
        password_hash="not-used",
        role=role_value,
        is_active=True,
        totp_enabled=False,
        created_at=now,
        updated_at=now,
    )


def _seed_context(sessionmaker) -> dict[str, uuid.UUID | AdminUserModel]:
    customer_realm_id = uuid.uuid4()
    customer_a_id = uuid.uuid4()
    customer_b_id = uuid.uuid4()
    admin = _admin_user(AdminRole.SUPPORT)

    with sessionmaker() as db:
        db.add_all(
            [
                AuthRealmModel(
                    id=customer_realm_id,
                    realm_key="customer",
                    realm_type="customer",
                    display_name="Customer Realm",
                    audience="cybervpn:customer",
                    cookie_namespace="customer",
                    status="active",
                    is_default=True,
                ),
                MobileUserModel(
                    id=customer_a_id,
                    auth_realm_id=customer_realm_id,
                    email="messaging-a@example.test",
                    password_hash="not-used",
                    is_active=True,
                    status="active",
                ),
                MobileUserModel(
                    id=customer_b_id,
                    auth_realm_id=customer_realm_id,
                    email="messaging-b@example.test",
                    password_hash="not-used",
                    is_active=True,
                    status="active",
                ),
                admin,
            ]
        )
        db.commit()

    return {
        "customer_a_id": customer_a_id,
        "customer_b_id": customer_b_id,
        "admin": admin,
    }


async def _create_conversation(
    async_client: AsyncClient,
    *,
    customer_account_id: uuid.UUID,
) -> dict:
    response = await async_client.post(
        "/api/v1/admin/messaging/conversations",
        json={
            "customer_account_id": str(customer_account_id),
            "subject": "VPN access after renewal",
            "category": "subscription",
            "priority": "normal",
            "initial_message": {
                "client_message_id": "admin-create-1",
                "body": "Your renewal is complete. Please reopen the app and try again.",
            },
        },
        headers=ADMIN_HOST_HEADERS,
    )
    assert response.status_code == 201
    return response.json()


@pytest.mark.asyncio
async def test_customer_messaging_is_owner_scoped_and_hides_internal_notes(async_client: AsyncClient) -> None:
    sessionmaker, engine, sqlite_path = create_realm_test_sessionmaker()
    await initialize_realm_test_database(engine)
    _create_messaging_tables(engine)

    try:
        async with override_realm_test_db(sessionmaker):
            context = _seed_context(sessionmaker)
            customer_a_id = context["customer_a_id"]
            customer_b_id = context["customer_b_id"]
            admin = context["admin"]
            assert isinstance(customer_a_id, uuid.UUID)
            assert isinstance(customer_b_id, uuid.UUID)
            assert isinstance(admin, AdminUserModel)

            _override_admin_user(admin)
            create_payload = await _create_conversation(async_client, customer_account_id=customer_a_id)
            public_id = create_payload["public_id"]

            note_response = await async_client.post(
                f"/api/v1/admin/messaging/conversations/{public_id}/internal-notes",
                json={"client_message_id": "note-1", "body": "Internal triage note: synthetic only."},
                headers=ADMIN_HOST_HEADERS,
            )
            assert note_response.status_code == 200
            assert note_response.json()["message"]["visibility"] == "internal"

            _override_mobile_user(customer_a_id)
            customer_create_response = await async_client.post(
                "/api/v1/me/conversations",
                json={"subject": "Should not exist"},
            )
            assert customer_create_response.status_code == 405

            detail_response = await async_client.get(f"/api/v1/me/conversations/{public_id}")
            assert detail_response.status_code == 200
            customer_payload = detail_response.json()
            assert customer_payload["public_id"] == public_id
            assert "customer_account_id" not in customer_payload
            assert "Internal triage note" not in str(customer_payload)
            assert all(message["visibility"] == "public" for message in customer_payload["messages"])

            list_response = await async_client.get("/api/v1/me/conversations")
            assert list_response.status_code == 200
            assert list_response.json()["conversations"][0]["public_id"] == public_id

            _override_mobile_user(customer_b_id)
            cross_owner_response = await async_client.get(f"/api/v1/me/conversations/{public_id}")
            assert cross_owner_response.status_code == 404
    finally:
        cleanup_sqlite_file(sqlite_path)


@pytest.mark.asyncio
async def test_message_idempotency_read_counts_and_closed_conversation_behavior(
    async_client: AsyncClient,
) -> None:
    sessionmaker, engine, sqlite_path = create_realm_test_sessionmaker()
    await initialize_realm_test_database(engine)
    _create_messaging_tables(engine)

    try:
        async with override_realm_test_db(sessionmaker):
            context = _seed_context(sessionmaker)
            customer_a_id = context["customer_a_id"]
            admin = context["admin"]
            assert isinstance(customer_a_id, uuid.UUID)
            assert isinstance(admin, AdminUserModel)

            _override_admin_user(admin)
            create_payload = await _create_conversation(async_client, customer_account_id=customer_a_id)
            public_id = create_payload["public_id"]
            admin_message_id = create_payload["messages"][0]["id"]

            _override_mobile_user(customer_a_id)
            unread_response = await async_client.get(f"/api/v1/me/conversations/{public_id}")
            assert unread_response.status_code == 200
            assert unread_response.json()["unread_count"] == 1

            read_response = await async_client.post(
                f"/api/v1/me/conversations/{public_id}/read",
                json={"last_read_message_id": admin_message_id},
            )
            assert read_response.status_code == 200

            read_detail_response = await async_client.get(f"/api/v1/me/conversations/{public_id}")
            assert read_detail_response.status_code == 200
            assert read_detail_response.json()["unread_count"] == 0

            first_reply = await async_client.post(
                f"/api/v1/me/conversations/{public_id}/messages",
                json={"client_message_id": "customer-reply-1", "body": "I can connect now."},
            )
            duplicate_reply = await async_client.post(
                f"/api/v1/me/conversations/{public_id}/messages",
                json={"client_message_id": "customer-reply-1", "body": "I can connect now."},
            )
            assert first_reply.status_code == 200
            assert duplicate_reply.status_code == 200
            assert first_reply.json()["message"]["id"] == duplicate_reply.json()["message"]["id"]
            assert first_reply.json()["created"] is True
            assert duplicate_reply.json()["created"] is False
            with sessionmaker() as db:
                message_events = list(
                    db.execute(
                        select(OutboxEventModel)
                        .where(
                            OutboxEventModel.event_name == "messaging.message.created",
                            OutboxEventModel.aggregate_id == first_reply.json()["message"]["id"],
                        )
                        .order_by(OutboxEventModel.created_at.asc())
                    )
                    .scalars()
                    .all()
                )
                assert len(message_events) == 1
                assert message_events[0].event_payload["body_included"] is False
                publications = list(
                    db.execute(
                        select(OutboxPublicationModel)
                        .where(OutboxPublicationModel.outbox_event_id == message_events[0].id)
                        .order_by(OutboxPublicationModel.consumer_key.asc())
                    )
                    .scalars()
                    .all()
                )
                assert {item.consumer_key for item in publications} == {
                    "messaging_audit_projection",
                    "messaging_realtime_projection",
                    "site_notification_fanout",
                }
                assert {item.publication_status for item in publications} == {"pending"}

            _override_admin_user(admin)
            close_response = await async_client.post(
                f"/api/v1/admin/messaging/conversations/{public_id}/close",
                headers=ADMIN_HOST_HEADERS,
            )
            assert close_response.status_code == 200
            assert close_response.json()["status"] == "closed"

            _override_mobile_user(customer_a_id)
            closed_reply = await async_client.post(
                f"/api/v1/me/conversations/{public_id}/messages",
                json={"client_message_id": "customer-reply-after-close", "body": "Still here."},
            )
            assert closed_reply.status_code == 409
    finally:
        cleanup_sqlite_file(sqlite_path)


@pytest.mark.asyncio
async def test_messaging_rbac_and_broadcast_scope(async_client: AsyncClient) -> None:
    sessionmaker, engine, sqlite_path = create_realm_test_sessionmaker()
    await initialize_realm_test_database(engine)
    _create_messaging_tables(engine)

    try:
        async with override_realm_test_db(sessionmaker):
            _seed_context(sessionmaker)

            _override_admin_user(_admin_user(AdminRole.VIEWER))
            list_response = await async_client.get(
                "/api/v1/admin/messaging/conversations",
                headers=ADMIN_HOST_HEADERS,
            )
            assert list_response.status_code == 403
            assert list_response.json()["detail"] == "Missing permission: messaging:conversation:read"

            support_broadcast_response = await async_client.post(
                "/api/v1/admin/notifications/broadcasts",
                json={
                    "name": "Maintenance notice",
                    "audience_type": "customer_segment",
                    "audience_filter": {"region": "test"},
                    "title": "Maintenance",
                    "body": "Synthetic maintenance notice.",
                    "action_url": "/status",
                },
                headers=ADMIN_HOST_HEADERS,
            )
            assert support_broadcast_response.status_code == 403
            assert support_broadcast_response.json()["detail"] == "Missing permission: notification:broadcast:create"

            _override_admin_user(_admin_user(AdminRole.ADMIN))
            broadcast_response = await async_client.post(
                "/api/v1/admin/notifications/broadcasts",
                json={
                    "name": "Maintenance notice",
                    "audience_type": "customer_segment",
                    "audience_filter": {"region": "test"},
                    "title": "Maintenance",
                    "body": "Synthetic maintenance notice.",
                    "action_url": "/status",
                },
                headers=ADMIN_HOST_HEADERS,
            )
            assert broadcast_response.status_code == 201
            assert broadcast_response.json()["status"] == "draft"
            cancel_response = await async_client.post(
                f"/api/v1/admin/notifications/broadcasts/{broadcast_response.json()['public_id']}/cancel",
                headers=ADMIN_HOST_HEADERS,
            )
            assert cancel_response.status_code == 200
            assert cancel_response.json()["status"] == "cancelled"
            with sessionmaker() as db:
                cancel_events = list(
                    db.execute(
                        select(OutboxEventModel).where(
                            OutboxEventModel.event_name == "broadcast.cancelled",
                            OutboxEventModel.aggregate_id == cancel_response.json()["id"],
                        )
                    )
                    .scalars()
                    .all()
                )
                assert len(cancel_events) == 1
    finally:
        cleanup_sqlite_file(sqlite_path)


@pytest.mark.asyncio
async def test_customer_notifications_read_and_sync_are_recipient_scoped(async_client: AsyncClient) -> None:
    sessionmaker, engine, sqlite_path = create_realm_test_sessionmaker()
    await initialize_realm_test_database(engine)
    _create_messaging_tables(engine)

    try:
        async with override_realm_test_db(sessionmaker):
            context = _seed_context(sessionmaker)
            customer_a_id = context["customer_a_id"]
            customer_b_id = context["customer_b_id"]
            assert isinstance(customer_a_id, uuid.UUID)
            assert isinstance(customer_b_id, uuid.UUID)

            now = datetime.now(UTC)
            notification_id = uuid.uuid4()
            with sessionmaker() as db:
                db.add(
                    SiteNotificationModel(
                        id=notification_id,
                        notification_type="system",
                        severity="info",
                        title="Synthetic notification",
                        body="Synthetic body.",
                        action_url="/status",
                        created_by_actor_type="system",
                        payload={},
                        created_at=now,
                        updated_at=now,
                    )
                )
                db.add(
                    SiteNotificationDeliveryModel(
                        id=uuid.uuid4(),
                        notification_id=notification_id,
                        recipient_type="customer",
                        recipient_id=customer_a_id,
                        delivery_channel="site",
                        status="pending",
                        attempts=0,
                        created_at=now,
                        updated_at=now,
                    )
                )
                db.commit()

            _override_mobile_user(customer_b_id)
            other_user_response = await async_client.get("/api/v1/me/notifications")
            assert other_user_response.status_code == 200
            assert other_user_response.json()["notifications"] == []

            _override_mobile_user(customer_a_id)
            list_response = await async_client.get("/api/v1/me/notifications")
            assert list_response.status_code == 200
            assert list_response.json()["notifications"][0]["id"] == str(notification_id)

            sync_response = await async_client.get("/api/v1/me/realtime/sync")
            assert sync_response.status_code == 200
            assert sync_response.json()["unread_counts"]["notifications"] == 1

            read_response = await async_client.post(
                "/api/v1/me/notifications/read",
                json={"notification_ids": [str(notification_id)], "read_all_before": None},
            )
            assert read_response.status_code == 200
            assert read_response.json()["notifications"][0]["status"] == "read"

            read_sync_response = await async_client.get("/api/v1/me/realtime/sync")
            assert read_sync_response.status_code == 200
            assert read_sync_response.json()["unread_counts"]["notifications"] == 0
    finally:
        cleanup_sqlite_file(sqlite_path)


def test_messaging_openapi_paths_are_registered() -> None:
    paths = app.openapi()["paths"]

    for path in (
        "/api/v1/me/conversations",
        "/api/v1/me/conversations/{conversation_id}",
        "/api/v1/me/conversations/{conversation_id}/messages",
        "/api/v1/me/conversations/{conversation_id}/read",
        "/api/v1/me/notifications",
        "/api/v1/me/notifications/read",
        "/api/v1/me/realtime/sync",
        "/api/v1/admin/messaging/conversations",
        "/api/v1/admin/messaging/conversations/{conversation_id}",
        "/api/v1/admin/messaging/conversations/{conversation_id}/messages",
        "/api/v1/admin/messaging/conversations/{conversation_id}/internal-notes",
        "/api/v1/admin/messaging/conversations/{conversation_id}/close",
        "/api/v1/admin/messaging/conversations/{conversation_id}/reopen",
        "/api/v1/admin/notifications/broadcasts",
        "/api/v1/admin/notifications/broadcasts/{campaign_id}/cancel",
    ):
        assert path in paths
