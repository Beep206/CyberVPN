from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest
from httpx import AsyncClient
from sqlalchemy import func, select

from src.domain.entities.partner_permission import PartnerPermission
from src.domain.enums import AdminRole
from src.infrastructure.database.models.admin_user_model import AdminUserModel
from src.infrastructure.database.models.auth_realm_model import AuthRealmModel
from src.infrastructure.database.models.messaging_broadcast_model import BroadcastCampaignModel
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
from src.infrastructure.database.models.partner_account_user_model import PartnerAccountUserModel
from src.infrastructure.database.models.partner_model import PartnerAccountModel
from src.infrastructure.database.models.partner_role_model import PartnerRoleModel
from src.infrastructure.database.models.support_ticket_model import (
    SupportTicketEventModel,
    SupportTicketMessageModel,
    SupportTicketModel,
)
from src.main import app
from src.presentation.dependencies.auth import (
    get_current_active_user,
    get_current_active_web_user,
    get_current_mobile_user_id,
)
from tests.helpers.realm_auth import (
    PARTNER_AUTH_REALM_HEADERS,
    cleanup_sqlite_file,
    create_realm_test_sessionmaker,
    initialize_realm_test_database,
    override_realm_test_db,
)

pytestmark = [pytest.mark.integration]

ADMIN_HOST_HEADERS = {"host": "testserver"}
PARTNER_HOST_HEADERS = PARTNER_AUTH_REALM_HEADERS


@pytest.fixture(autouse=True)
def _clear_dependency_overrides():
    yield
    app.dependency_overrides.pop(get_current_mobile_user_id, None)
    app.dependency_overrides.pop(get_current_active_user, None)
    app.dependency_overrides.pop(get_current_active_web_user, None)


def _create_support_ticket_tables(engine) -> None:
    with engine.begin() as conn:
        SupportTicketModel.__table__.create(conn, checkfirst=True)
        SupportTicketMessageModel.__table__.create(conn, checkfirst=True)
        SupportTicketEventModel.__table__.create(conn, checkfirst=True)


def _create_support_ticket_messaging_tables(engine) -> None:
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
            OutboxEventModel.__table__,
            OutboxPublicationModel.__table__,
        ):
            table.create(conn, checkfirst=True)
        conn.exec_driver_sql("DROP INDEX IF EXISTS uq_messaging_participants_active_customer")


def _count_model_rows(db, model) -> int:
    return int(db.scalar(select(func.count()).select_from(model)) or 0)


def _assert_no_customer_messaging_outbox_rows(sessionmaker) -> None:
    with sessionmaker() as db:
        assert _count_model_rows(db, MessagingConversationModel) == 0
        assert _count_model_rows(db, MessagingMessageModel) == 0
        assert _count_model_rows(db, OutboxEventModel) == 0
        assert _count_model_rows(db, OutboxPublicationModel) == 0
        assert _count_model_rows(db, SiteNotificationModel) == 0
        assert _count_model_rows(db, SiteNotificationDeliveryModel) == 0


def _override_mobile_user(user_id: uuid.UUID) -> None:
    app.dependency_overrides[get_current_mobile_user_id] = lambda: user_id


def _override_admin_user(user: AdminUserModel) -> None:
    app.dependency_overrides[get_current_active_user] = lambda: user
    app.dependency_overrides[get_current_active_web_user] = lambda: user


def _admin_user(role: AdminRole | str) -> AdminUserModel:
    role_value = role.value if isinstance(role, AdminRole) else role
    now = datetime.now(UTC)
    return AdminUserModel(
        id=uuid.uuid4(),
        login=f"support-ticket-{role_value}",
        email=f"support-ticket-{role_value}@example.test",
        password_hash="not-used",
        role=role_value,
        is_active=True,
        totp_enabled=False,
        created_at=now,
        updated_at=now,
    )


def _assert_public_ticket_payload_is_minimized(payload: dict) -> None:
    for key in {
        "id",
        "owner_type",
        "customer_account_id",
        "partner_workspace_id",
        "source",
        "assigned_admin_id",
    }:
        assert key not in payload

    for message in payload.get("messages", []):
        for key in {"id", "ticket_id", "author_type", "author_id", "visibility"}:
            assert key not in message
        assert set(message) == {"author_label", "body", "created_at"}

    for event in payload.get("events", []):
        for key in {"id", "ticket_id", "actor_type", "actor_id"}:
            assert key not in event
        assert set(event) == {
            "actor_label",
            "event_type",
            "from_value",
            "to_value",
            "audit_summary",
            "created_at",
        }


def _seed_support_context(sessionmaker) -> dict[str, uuid.UUID | AdminUserModel]:
    now = datetime.now(UTC)
    customer_realm_id = uuid.uuid4()
    customer_a_id = uuid.uuid4()
    customer_b_id = uuid.uuid4()
    admin_id = uuid.uuid4()
    partner_workspace_a_id = uuid.uuid4()
    partner_workspace_b_id = uuid.uuid4()
    partner_role_id = uuid.uuid4()

    with sessionmaker() as db:
        realm = AuthRealmModel(
            id=customer_realm_id,
            realm_key="customer",
            realm_type="customer",
            display_name="Customer Realm",
            audience="cybervpn:customer",
            cookie_namespace="customer",
            status="active",
            is_default=True,
        )
        customer_a = MobileUserModel(
            id=customer_a_id,
            auth_realm_id=customer_realm_id,
            email="support-a@example.test",
            password_hash="not-used",
            is_active=True,
            status="active",
        )
        customer_b = MobileUserModel(
            id=customer_b_id,
            auth_realm_id=customer_realm_id,
            email="support-b@example.test",
            password_hash="not-used",
            is_active=True,
            status="active",
        )
        admin = AdminUserModel(
            id=admin_id,
            login="support-admin",
            email="support-admin@example.test",
            password_hash="not-used",
            role="support",
            is_active=True,
            totp_enabled=False,
            created_at=now,
            updated_at=now,
        )
        partner_a = PartnerAccountModel(
            id=partner_workspace_a_id,
            account_key="partner-a",
            display_name="Partner A",
            status="active",
        )
        partner_b = PartnerAccountModel(
            id=partner_workspace_b_id,
            account_key="partner-b",
            display_name="Partner B",
            status="active",
        )
        partner_role = PartnerRoleModel(
            id=partner_role_id,
            role_key="support_operator",
            display_name="Support Operator",
            description="Can use partner support tickets",
            permission_keys=[
                PartnerPermission.WORKSPACE_READ.value,
                PartnerPermission.OPERATIONS_WRITE.value,
            ],
            is_system=False,
        )
        membership_a = PartnerAccountUserModel(
            id=uuid.uuid4(),
            partner_account_id=partner_workspace_a_id,
            admin_user_id=admin_id,
            role_id=partner_role_id,
            membership_status="active",
        )
        membership_b = PartnerAccountUserModel(
            id=uuid.uuid4(),
            partner_account_id=partner_workspace_b_id,
            admin_user_id=admin_id,
            role_id=partner_role_id,
            membership_status="active",
        )
        db.add_all(
            [
                realm,
                customer_a,
                customer_b,
                admin,
                partner_a,
                partner_b,
                partner_role,
                membership_a,
                membership_b,
            ]
        )
        db.commit()

    return {
        "customer_a_id": customer_a_id,
        "customer_b_id": customer_b_id,
        "admin": admin,
        "partner_workspace_a_id": partner_workspace_a_id,
        "partner_workspace_b_id": partner_workspace_b_id,
    }


@pytest.mark.asyncio
async def test_customer_support_ticket_is_owner_scoped_and_hides_internal_notes(async_client: AsyncClient) -> None:
    sessionmaker, engine, sqlite_path = create_realm_test_sessionmaker()
    await initialize_realm_test_database(engine)
    _create_support_ticket_tables(engine)

    try:
        async with override_realm_test_db(sessionmaker):
            context = _seed_support_context(sessionmaker)
            customer_a_id = context["customer_a_id"]
            customer_b_id = context["customer_b_id"]
            admin = context["admin"]

            assert isinstance(customer_a_id, uuid.UUID)
            assert isinstance(customer_b_id, uuid.UUID)
            assert isinstance(admin, AdminUserModel)

            _override_mobile_user(customer_a_id)
            create_response = await async_client.post(
                "/api/v1/support/tickets",
                json={
                    "category": "setup",
                    "subject": "Cannot find setup steps",
                    "message": "I need help finding the Windows setup flow.",
                },
            )
            assert create_response.status_code == 201
            create_payload = create_response.json()
            _assert_public_ticket_payload_is_minimized(create_payload)
            assert create_payload["messages"][0]["author_label"] == "customer"
            public_id = create_payload["public_id"]

            _override_admin_user(admin)
            note_response = await async_client.post(
                f"/api/v1/admin/support/tickets/{public_id}/internal-notes",
                json={"message": "Internal triage note: synthetic only."},
                headers=ADMIN_HOST_HEADERS,
            )
            assert note_response.status_code == 200
            assert any(message["visibility"] == "internal" for message in note_response.json()["messages"])

            _override_mobile_user(customer_a_id)
            customer_detail_response = await async_client.get(f"/api/v1/support/tickets/{public_id}")
            assert customer_detail_response.status_code == 200
            customer_payload = customer_detail_response.json()
            _assert_public_ticket_payload_is_minimized(customer_payload)
            assert "Internal triage note" not in str(customer_payload)

            customer_list_response = await async_client.get("/api/v1/support/tickets")
            assert customer_list_response.status_code == 200
            assert customer_list_response.json()["tickets"]
            _assert_public_ticket_payload_is_minimized(customer_list_response.json()["tickets"][0])

            _override_mobile_user(customer_b_id)
            cross_owner_response = await async_client.get(f"/api/v1/support/tickets/{public_id}")
            assert cross_owner_response.status_code == 404
    finally:
        cleanup_sqlite_file(sqlite_path)


@pytest.mark.asyncio
async def test_admin_support_ticket_read_requires_support_ticket_permission(async_client: AsyncClient) -> None:
    sessionmaker, engine, sqlite_path = create_realm_test_sessionmaker()
    await initialize_realm_test_database(engine)
    _create_support_ticket_tables(engine)

    try:
        async with override_realm_test_db(sessionmaker):
            context = _seed_support_context(sessionmaker)
            customer_a_id = context["customer_a_id"]
            admin = context["admin"]
            assert isinstance(customer_a_id, uuid.UUID)
            assert isinstance(admin, AdminUserModel)

            _override_mobile_user(customer_a_id)
            create_response = await async_client.post(
                "/api/v1/support/tickets",
                json={
                    "category": "setup",
                    "subject": "RBAC read gate",
                    "message": "Synthetic ticket used for RBAC checks.",
                },
            )
            assert create_response.status_code == 201
            public_id = create_response.json()["public_id"]

            _override_admin_user(admin)
            note_response = await async_client.post(
                f"/api/v1/admin/support/tickets/{public_id}/internal-notes",
                json={"message": "Internal note hidden behind support-ticket read."},
                headers=ADMIN_HOST_HEADERS,
            )
            assert note_response.status_code == 200
            assert any(message["visibility"] == "internal" for message in note_response.json()["messages"])

            for role in (AdminRole.VIEWER, AdminRole.FINANCE):
                _override_admin_user(_admin_user(role))

                list_response = await async_client.get(
                    "/api/v1/admin/support/tickets",
                    headers=ADMIN_HOST_HEADERS,
                )
                assert list_response.status_code == 403
                assert list_response.json()["detail"] == "Missing permission: support_ticket_read"

                detail_response = await async_client.get(
                    f"/api/v1/admin/support/tickets/{public_id}",
                    headers=ADMIN_HOST_HEADERS,
                )
                assert detail_response.status_code == 403
                assert detail_response.json()["detail"] == "Missing permission: support_ticket_read"
                assert "Internal note hidden" not in detail_response.text
    finally:
        cleanup_sqlite_file(sqlite_path)


@pytest.mark.asyncio
async def test_public_support_ticket_create_rejects_metadata_and_source_spoofing(
    async_client: AsyncClient,
) -> None:
    sessionmaker, engine, sqlite_path = create_realm_test_sessionmaker()
    await initialize_realm_test_database(engine)
    _create_support_ticket_tables(engine)

    try:
        async with override_realm_test_db(sessionmaker):
            context = _seed_support_context(sessionmaker)
            customer_a_id = context["customer_a_id"]
            admin = context["admin"]
            workspace_a_id = context["partner_workspace_a_id"]
            assert isinstance(customer_a_id, uuid.UUID)
            assert isinstance(admin, AdminUserModel)
            assert isinstance(workspace_a_id, uuid.UUID)

            _override_mobile_user(customer_a_id)
            spoof_response = await async_client.post(
                "/api/v1/support/tickets",
                json={
                    "category": "setup",
                    "subject": "Spoof source",
                    "message": "Trying to spoof source and metadata.",
                    "source": "telegram_bot",
                    "metadata": {"internal_tag": "should-not-persist"},
                },
            )
            assert spoof_response.status_code == 422

            create_response = await async_client.post(
                "/api/v1/support/tickets",
                json={
                    "category": "setup",
                    "subject": "Server source",
                    "message": "Source should be server derived.",
                },
            )
            assert create_response.status_code == 201
            public_payload = create_response.json()
            _assert_public_ticket_payload_is_minimized(public_payload)

            with sessionmaker() as db:
                ticket_model = (
                    db.query(SupportTicketModel)
                    .filter(SupportTicketModel.public_id == public_payload["public_id"])
                    .one()
                )
                assert ticket_model.source == "customer_web"
                assert ticket_model.metadata_json == {}

            _override_admin_user(admin)
            partner_metadata_response = await async_client.post(
                f"/api/v1/partner-workspaces/{workspace_a_id}/support/tickets",
                headers=PARTNER_HOST_HEADERS,
                json={
                    "category": "account",
                    "subject": "Partner metadata",
                    "message": "Trying to attach metadata from partner surface.",
                    "metadata": {"internal_tag": "should-not-persist"},
                },
            )
            assert partner_metadata_response.status_code == 422
    finally:
        cleanup_sqlite_file(sqlite_path)


@pytest.mark.asyncio
async def test_admin_status_transition_and_invalid_transition_conflict(async_client: AsyncClient) -> None:
    sessionmaker, engine, sqlite_path = create_realm_test_sessionmaker()
    await initialize_realm_test_database(engine)
    _create_support_ticket_tables(engine)

    try:
        async with override_realm_test_db(sessionmaker):
            context = _seed_support_context(sessionmaker)
            customer_a_id = context["customer_a_id"]
            admin = context["admin"]
            assert isinstance(customer_a_id, uuid.UUID)
            assert isinstance(admin, AdminUserModel)

            _override_mobile_user(customer_a_id)
            create_response = await async_client.post(
                "/api/v1/support/tickets",
                json={
                    "category": "vpn_access",
                    "subject": "VPN access question",
                    "message": "Synthetic VPN access question, no credentials included.",
                },
            )
            assert create_response.status_code == 201
            create_payload = create_response.json()
            _assert_public_ticket_payload_is_minimized(create_payload)
            public_id = create_payload["public_id"]

            _override_admin_user(admin)
            update_response = await async_client.patch(
                f"/api/v1/admin/support/tickets/{public_id}",
                json={"status": "resolved", "priority": "high"},
                headers=ADMIN_HOST_HEADERS,
            )
            assert update_response.status_code == 200
            update_payload = update_response.json()
            assert update_payload["status"] == "resolved"
            event_types = {event["event_type"] for event in update_payload["events"]}
            assert "status_changed" in event_types
            assert "priority_changed" in event_types

            invalid_response = await async_client.patch(
                f"/api/v1/admin/support/tickets/{public_id}",
                json={"status": "open"},
                headers=ADMIN_HOST_HEADERS,
            )
            assert invalid_response.status_code == 409
    finally:
        cleanup_sqlite_file(sqlite_path)


@pytest.mark.asyncio
async def test_admin_customer_support_reply_creates_customer_messaging_notification_outbox(
    async_client: AsyncClient,
) -> None:
    sessionmaker, engine, sqlite_path = create_realm_test_sessionmaker()
    await initialize_realm_test_database(engine)
    _create_support_ticket_messaging_tables(engine)

    try:
        async with override_realm_test_db(sessionmaker):
            context = _seed_support_context(sessionmaker)
            customer_a_id = context["customer_a_id"]
            admin = context["admin"]
            assert isinstance(customer_a_id, uuid.UUID)
            assert isinstance(admin, AdminUserModel)

            _override_mobile_user(customer_a_id)
            create_response = await async_client.post(
                "/api/v1/support/tickets",
                json={
                    "category": "setup",
                    "subject": "Support fanout bridge",
                    "message": "Customer needs a public support reply.",
                },
            )
            assert create_response.status_code == 201
            public_id = create_response.json()["public_id"]

            _override_admin_user(admin)
            first_reply_response = await async_client.post(
                f"/api/v1/admin/support/tickets/{public_id}/replies",
                json={"message": "Support reply should reach customer messaging."},
                headers=ADMIN_HOST_HEADERS,
            )
            assert first_reply_response.status_code == 200

            with sessionmaker() as db:
                ticket = db.execute(
                    select(SupportTicketModel).where(SupportTicketModel.public_id == public_id)
                ).scalar_one()
                conversations = (
                    db.execute(
                        select(MessagingConversationModel).where(
                            MessagingConversationModel.related_support_ticket_id == ticket.id
                        )
                    )
                    .scalars()
                    .all()
                )
                assert len(conversations) == 1
                conversation = conversations[0]
                first_conversation_id = conversation.id
                assert conversation.customer_account_id == customer_a_id
                assert conversation.category == "support"
                assert conversation.subject == "Support fanout bridge"

                messages = (
                    db.execute(
                        select(MessagingMessageModel)
                        .where(MessagingMessageModel.conversation_id == conversation.id)
                        .order_by(MessagingMessageModel.created_at.asc())
                    )
                    .scalars()
                    .all()
                )
                assert len(messages) == 1
                support_messages = (
                    db.execute(
                        select(SupportTicketMessageModel).where(
                            SupportTicketMessageModel.ticket_id == ticket.id,
                            SupportTicketMessageModel.author_type == "admin",
                            SupportTicketMessageModel.visibility == "public",
                        )
                    )
                    .scalars()
                    .all()
                )
                assert len(support_messages) == 1
                assert messages[0].sender_type == "admin"
                assert messages[0].sender_id == admin.id
                assert messages[0].visibility == "public"
                assert messages[0].body == "Support reply should reach customer messaging."
                assert messages[0].client_message_id == f"support-ticket-message:{support_messages[0].id}"
                assert len(messages[0].client_message_id) <= 80

                outbox_events = (
                    db.execute(select(OutboxEventModel).order_by(OutboxEventModel.created_at.asc())).scalars().all()
                )
                event_by_name = {event.event_name: event for event in outbox_events}
                assert set(event_by_name) == {
                    "messaging.conversation.created",
                    "messaging.message.created",
                }
                message_event = event_by_name["messaging.message.created"]
                assert message_event.aggregate_id == str(messages[0].id)
                assert message_event.partition_key == str(customer_a_id)
                assert message_event.event_payload["conversation_id"] == str(conversation.id)
                assert message_event.event_payload["conversation_public_id"] == conversation.public_id
                assert message_event.event_payload["body_included"] is False
                assert "body" not in message_event.event_payload
                assert message_event.event_payload["recipient_refs"] == [
                    {"type": "customer", "id": str(customer_a_id)},
                    {"type": "admin", "id": str(admin.id)},
                ]

                publication_keys = (
                    db.execute(
                        select(OutboxPublicationModel.consumer_key).where(
                            OutboxPublicationModel.outbox_event_id == message_event.id
                        )
                    )
                    .scalars()
                    .all()
                )
                assert set(publication_keys) == {
                    "messaging_realtime_projection",
                    "site_notification_fanout",
                    "messaging_audit_projection",
                }

            second_reply_response = await async_client.post(
                f"/api/v1/admin/support/tickets/{public_id}/replies",
                json={"message": "Second public support update."},
                headers=ADMIN_HOST_HEADERS,
            )
            assert second_reply_response.status_code == 200

            with sessionmaker() as db:
                ticket = db.execute(
                    select(SupportTicketModel).where(SupportTicketModel.public_id == public_id)
                ).scalar_one()
                conversations = (
                    db.execute(
                        select(MessagingConversationModel).where(
                            MessagingConversationModel.related_support_ticket_id == ticket.id
                        )
                    )
                    .scalars()
                    .all()
                )
                assert len(conversations) == 1
                assert conversations[0].id == first_conversation_id

                messages = (
                    db.execute(
                        select(MessagingMessageModel)
                        .where(MessagingMessageModel.conversation_id == first_conversation_id)
                        .order_by(MessagingMessageModel.created_at.asc())
                    )
                    .scalars()
                    .all()
                )
                assert [message.body for message in messages] == [
                    "Support reply should reach customer messaging.",
                    "Second public support update.",
                ]

                outbox_event_names = (
                    db.execute(select(OutboxEventModel.event_name).order_by(OutboxEventModel.created_at.asc()))
                    .scalars()
                    .all()
                )
                assert outbox_event_names.count("messaging.conversation.created") == 1
                assert outbox_event_names.count("messaging.message.created") == 2
    finally:
        cleanup_sqlite_file(sqlite_path)


@pytest.mark.asyncio
async def test_admin_public_reply_on_partner_ticket_does_not_create_customer_messaging_outbox(
    async_client: AsyncClient,
) -> None:
    sessionmaker, engine, sqlite_path = create_realm_test_sessionmaker()
    await initialize_realm_test_database(engine)
    _create_support_ticket_messaging_tables(engine)

    try:
        async with override_realm_test_db(sessionmaker):
            context = _seed_support_context(sessionmaker)
            admin = context["admin"]
            workspace_a_id = context["partner_workspace_a_id"]
            assert isinstance(admin, AdminUserModel)
            assert isinstance(workspace_a_id, uuid.UUID)

            _override_admin_user(admin)
            create_response = await async_client.post(
                f"/api/v1/partner-workspaces/{workspace_a_id}/support/tickets",
                headers=PARTNER_HOST_HEADERS,
                json={
                    "category": "account",
                    "subject": "Partner-only support bridge",
                    "message": "Partner content must not fan out to customer messaging.",
                },
            )
            assert create_response.status_code == 201
            public_id = create_response.json()["public_id"]

            reply_response = await async_client.post(
                f"/api/v1/admin/support/tickets/{public_id}/replies",
                json={"message": "Public admin reply on partner ticket."},
                headers=ADMIN_HOST_HEADERS,
            )
            assert reply_response.status_code == 200
            assert reply_response.json()["owner_type"] == "partner"

            _assert_no_customer_messaging_outbox_rows(sessionmaker)
    finally:
        cleanup_sqlite_file(sqlite_path)


@pytest.mark.asyncio
async def test_admin_internal_note_on_customer_ticket_does_not_create_messaging_outbox(
    async_client: AsyncClient,
) -> None:
    sessionmaker, engine, sqlite_path = create_realm_test_sessionmaker()
    await initialize_realm_test_database(engine)
    _create_support_ticket_messaging_tables(engine)

    try:
        async with override_realm_test_db(sessionmaker):
            context = _seed_support_context(sessionmaker)
            customer_a_id = context["customer_a_id"]
            admin = context["admin"]
            assert isinstance(customer_a_id, uuid.UUID)
            assert isinstance(admin, AdminUserModel)

            _override_mobile_user(customer_a_id)
            create_response = await async_client.post(
                "/api/v1/support/tickets",
                json={
                    "category": "privacy",
                    "subject": "Internal note privacy",
                    "message": "Customer ticket used to verify internal-note privacy.",
                },
            )
            assert create_response.status_code == 201
            public_id = create_response.json()["public_id"]

            _override_admin_user(admin)
            note_response = await async_client.post(
                f"/api/v1/admin/support/tickets/{public_id}/internal-notes",
                json={"message": "Internal-only investigation note."},
                headers=ADMIN_HOST_HEADERS,
            )
            assert note_response.status_code == 200
            assert any(message["visibility"] == "internal" for message in note_response.json()["messages"])

            _assert_no_customer_messaging_outbox_rows(sessionmaker)
    finally:
        cleanup_sqlite_file(sqlite_path)


@pytest.mark.asyncio
async def test_malformed_partner_ticket_with_customer_id_does_not_create_customer_messaging_outbox(
    async_client: AsyncClient,
) -> None:
    sessionmaker, engine, sqlite_path = create_realm_test_sessionmaker()
    await initialize_realm_test_database(engine)
    _create_support_ticket_messaging_tables(engine)

    try:
        async with override_realm_test_db(sessionmaker):
            context = _seed_support_context(sessionmaker)
            customer_a_id = context["customer_a_id"]
            admin = context["admin"]
            workspace_a_id = context["partner_workspace_a_id"]
            assert isinstance(customer_a_id, uuid.UUID)
            assert isinstance(admin, AdminUserModel)
            assert isinstance(workspace_a_id, uuid.UUID)

            _override_admin_user(admin)
            create_response = await async_client.post(
                f"/api/v1/partner-workspaces/{workspace_a_id}/support/tickets",
                headers=PARTNER_HOST_HEADERS,
                json={
                    "category": "account",
                    "subject": "Malformed partner ownership",
                    "message": "Synthetic partner ticket later mutated to mixed owner state.",
                },
            )
            assert create_response.status_code == 201
            public_id = create_response.json()["public_id"]

            with sessionmaker() as db:
                ticket = db.execute(
                    select(SupportTicketModel).where(SupportTicketModel.public_id == public_id)
                ).scalar_one()
                assert ticket.owner_type == "partner"
                ticket.customer_account_id = customer_a_id
                db.commit()

            reply_response = await async_client.post(
                f"/api/v1/admin/support/tickets/{public_id}/replies",
                json={"message": "Admin reply must not bridge a mixed-owner partner ticket."},
                headers=ADMIN_HOST_HEADERS,
            )
            assert reply_response.status_code == 200
            assert reply_response.json()["owner_type"] == "partner"
            assert reply_response.json()["customer_account_id"] == str(customer_a_id)

            _assert_no_customer_messaging_outbox_rows(sessionmaker)
    finally:
        cleanup_sqlite_file(sqlite_path)


@pytest.mark.asyncio
async def test_partner_support_ticket_is_workspace_scoped(async_client: AsyncClient) -> None:
    sessionmaker, engine, sqlite_path = create_realm_test_sessionmaker()
    await initialize_realm_test_database(engine)
    _create_support_ticket_tables(engine)

    try:
        async with override_realm_test_db(sessionmaker):
            context = _seed_support_context(sessionmaker)
            admin = context["admin"]
            workspace_a_id = context["partner_workspace_a_id"]
            workspace_b_id = context["partner_workspace_b_id"]
            assert isinstance(admin, AdminUserModel)
            assert isinstance(workspace_a_id, uuid.UUID)
            assert isinstance(workspace_b_id, uuid.UUID)

            _override_admin_user(admin)
            create_response = await async_client.post(
                f"/api/v1/partner-workspaces/{workspace_a_id}/support/tickets",
                headers=PARTNER_HOST_HEADERS,
                json={
                    "category": "account",
                    "subject": "Partner workspace support",
                    "message": "Partner needs support for a synthetic workspace.",
                },
            )
            assert create_response.status_code == 201
            public_id = create_response.json()["public_id"]

            own_response = await async_client.get(
                f"/api/v1/partner-workspaces/{workspace_a_id}/support/tickets/{public_id}",
                headers=PARTNER_HOST_HEADERS,
            )
            assert own_response.status_code == 200
            _assert_public_ticket_payload_is_minimized(own_response.json())
            assert own_response.json()["public_id"] == public_id

            other_workspace_response = await async_client.get(
                f"/api/v1/partner-workspaces/{workspace_b_id}/support/tickets/{public_id}",
                headers=PARTNER_HOST_HEADERS,
            )
            assert other_workspace_response.status_code == 404
    finally:
        cleanup_sqlite_file(sqlite_path)
