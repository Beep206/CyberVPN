from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from httpx import AsyncClient
from sqlalchemy import select

from src.application.services.auth_service import AuthService
from src.application.services.config_service import ConfigService
from src.application.use_cases.growth_notifications.admin_controls import (
    ManageCustomerGrowthNotificationDeliveryUseCase,
)
from src.application.use_cases.growth_notifications.automation import (
    AutomateCustomerGrowthNotificationRepairUseCase,
)
from src.application.use_cases.growth_notifications.catalog import (
    admin_manual_notification_key,
    invite_issued_notification_key,
    referral_available_notification_key,
    referral_reversed_notification_key,
)
from src.application.use_cases.growth_notifications.fanout import (
    PlanCustomerGrowthNotificationFanoutUseCase,
)
from src.application.use_cases.invites.admin_create_invite import AdminCreateInviteUseCase
from src.application.use_cases.referrals.release_referral_rewards import (
    ReleaseReferralRewardsUseCase,
)
from src.application.use_cases.referrals.reverse_referral_rewards import (
    ReverseReferralRewardsForOrderUseCase,
)
from src.infrastructure.database.models.admin_user_model import AdminUserModel
from src.infrastructure.database.models.auth_realm_model import AuthRealmModel
from src.infrastructure.database.models.customer_growth_notification_delivery_event_model import (
    CustomerGrowthNotificationDeliveryEventModel,
)
from src.infrastructure.database.models.customer_growth_notification_delivery_model import (
    CustomerGrowthNotificationDeliveryModel,
)
from src.infrastructure.database.models.growth_reward_allocation_model import GrowthRewardAllocationModel
from src.infrastructure.database.models.invite_code_model import InviteCodeModel
from src.infrastructure.database.models.mobile_user_model import MobileUserModel
from src.infrastructure.database.models.notification_queue_model import NotificationQueue
from src.infrastructure.database.repositories.invite_code_repo import InviteCodeRepository
from src.infrastructure.database.repositories.system_config_repo import SystemConfigRepository
from src.main import app
from src.presentation.dependencies.auth import get_current_mobile_user_id
from tests.helpers.realm_auth import (
    SyncSessionAdapter,
    cleanup_sqlite_file,
    create_realm_test_sessionmaker,
    initialize_realm_test_database,
    override_realm_test_db,
)

pytestmark = [pytest.mark.integration]


@pytest.fixture(autouse=True)
def _clear_mobile_override():
    yield
    app.dependency_overrides.pop(get_current_mobile_user_id, None)


def _override_mobile_user(user_id: uuid.UUID) -> None:
    app.dependency_overrides[get_current_mobile_user_id] = lambda: user_id


async def _create_admin_user(sessionmaker, auth_service: AuthService) -> tuple[AdminUserModel, str]:
    password = "GrowthDeliveryAdmin123!"
    with sessionmaker() as db:
        user = AdminUserModel(
            id=uuid.uuid4(),
            login="growthdeliveryadmin",
            email="growth-delivery-admin@example.test",
            password_hash=await auth_service.hash_password(password),
            role="admin",
            is_active=True,
            is_email_verified=True,
            language="en",
            timezone="UTC",
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        return user, password


@pytest.mark.asyncio
async def test_growth_notification_preferences_route_filters_in_app_feed(async_client: AsyncClient) -> None:
    sessionmaker, engine, sqlite_path = create_realm_test_sessionmaker()
    await initialize_realm_test_database(engine)

    try:
        async with override_realm_test_db(sessionmaker):
            now = datetime.now(UTC)
            user_id = uuid.uuid4()
            realm_id = uuid.uuid4()
            _override_mobile_user(user_id)

            with sessionmaker() as db:
                db.add_all(
                    [
                        AuthRealmModel(
                            id=realm_id,
                            realm_key="customer",
                            realm_type="customer",
                            display_name="Customer Realm",
                            audience="cybervpn:customer",
                            cookie_namespace="customer",
                            status="active",
                            is_default=True,
                        ),
                        MobileUserModel(
                            id=user_id,
                            auth_realm_id=realm_id,
                            email="growth-prefs@example.test",
                            password_hash="not-used",
                            is_active=True,
                            status="active",
                        ),
                        InviteCodeModel(
                            id=uuid.uuid4(),
                            code="INV-PREFS",
                            owner_user_id=user_id,
                            free_days=14,
                            source="admin_grant",
                            is_used=False,
                            expires_at=now + timedelta(days=10),
                            created_at=now - timedelta(hours=1),
                        ),
                    ]
                )
                db.commit()

            get_response = await async_client.get("/api/v1/growth-notifications/preferences")
            assert get_response.status_code == 200
            assert get_response.json()["growth_in_app_invites"] is True

            update_response = await async_client.patch(
                "/api/v1/growth-notifications/preferences",
                json={"growth_in_app_invites": False},
            )
            assert update_response.status_code == 200
            assert update_response.json()["growth_in_app_invites"] is False

            feed_response = await async_client.get("/api/v1/growth-notifications")
            assert feed_response.status_code == 200
            assert feed_response.json() == []
    finally:
        engine.dispose()
        cleanup_sqlite_file(sqlite_path)


@pytest.mark.asyncio
async def test_admin_invite_grant_creates_fanout_delivery_records() -> None:
    auth_service = AuthService()
    sessionmaker, engine, sqlite_path = create_realm_test_sessionmaker()
    await initialize_realm_test_database(engine)

    try:
        async with override_realm_test_db(sessionmaker):
            with sessionmaker() as db:
                realm = AuthRealmModel(
                    id=uuid.uuid4(),
                    realm_key="customer",
                    realm_type="customer",
                    display_name="Customer Realm",
                    audience="cybervpn:customer",
                    cookie_namespace="customer",
                    status="active",
                    is_default=True,
                )
                owner = MobileUserModel(
                    id=uuid.uuid4(),
                    auth_realm_id=realm.id,
                    email="invite-owner-fanout@example.test",
                    password_hash=await auth_service.hash_password("InviteOwner123!"),
                    telegram_id=772233,
                    is_active=True,
                    status="active",
                    notification_prefs={
                        "growth_in_app_invites": True,
                        "growth_email_invites": True,
                        "growth_telegram_invites": True,
                    },
                )
                db.add_all([realm, owner])
                db.commit()

                use_case = AdminCreateInviteUseCase(
                    invite_repo=InviteCodeRepository(SyncSessionAdapter(db)),
                    config_service=ConfigService(SystemConfigRepository(SyncSessionAdapter(db))),
                    notification_fanout=PlanCustomerGrowthNotificationFanoutUseCase(SyncSessionAdapter(db)),
                )
                created = await use_case.execute(owner_user_id=owner.id, free_days=21, count=1)
                invite = created[0]
                db.commit()

                deliveries = (
                    db.execute(
                        select(CustomerGrowthNotificationDeliveryModel).where(
                            CustomerGrowthNotificationDeliveryModel.mobile_user_id == owner.id,
                            CustomerGrowthNotificationDeliveryModel.notification_key
                            == invite_issued_notification_key(invite.id),
                        )
                    )
                    .scalars()
                    .all()
                )
                assert len(deliveries) == 3

                by_channel = {item.delivery_channel: item for item in deliveries}
                assert by_channel["in_app"].delivery_status == "delivered"
                assert by_channel["email"].delivery_status == "planned"
                assert by_channel["telegram"].delivery_status == "queued"
                assert by_channel["telegram"].notification_queue_id is not None

                queue_entry = db.execute(
                    select(NotificationQueue).where(
                        NotificationQueue.id == by_channel["telegram"].notification_queue_id
                    )
                ).scalar_one()
                assert queue_entry.telegram_id == owner.telegram_id
                assert "Invite ready to share" in queue_entry.message
    finally:
        engine.dispose()
        cleanup_sqlite_file(sqlite_path)


@pytest.mark.asyncio
async def test_referral_reward_release_and_reverse_create_delivery_records() -> None:
    auth_service = AuthService()
    sessionmaker, engine, sqlite_path = create_realm_test_sessionmaker()
    await initialize_realm_test_database(engine)

    try:
        async with override_realm_test_db(sessionmaker):
            with sessionmaker() as db:
                realm = AuthRealmModel(
                    id=uuid.uuid4(),
                    realm_key="customer",
                    realm_type="customer",
                    display_name="Customer Realm",
                    audience="cybervpn:customer",
                    cookie_namespace="customer",
                    status="active",
                    is_default=True,
                )
                beneficiary = MobileUserModel(
                    id=uuid.uuid4(),
                    auth_realm_id=realm.id,
                    email="referral-beneficiary@example.test",
                    password_hash=await auth_service.hash_password("ReferralBeneficiary123!"),
                    telegram_id=998877,
                    is_active=True,
                    status="active",
                    notification_prefs={
                        "growth_in_app_referral_rewards": True,
                        "growth_email_referral_rewards": True,
                        "growth_telegram_referral_rewards": True,
                    },
                )
                allocation = GrowthRewardAllocationModel(
                    id=uuid.uuid4(),
                    reward_type="referral_credit",
                    allocation_status="pending",
                    beneficiary_user_id=beneficiary.id,
                    auth_realm_id=realm.id,
                    order_id=uuid.uuid4(),
                    quantity=Decimal("10.00"),
                    unit="usd",
                    currency_code="USD",
                    reward_payload={},
                    hold_until=datetime.now(UTC) - timedelta(minutes=1),
                    allocated_at=datetime.now(UTC) - timedelta(days=1),
                )
                db.add_all([realm, beneficiary, allocation])
                db.commit()

                released = await ReleaseReferralRewardsUseCase(SyncSessionAdapter(db)).execute(commit=True)
                assert len(released) == 1

                available_deliveries = (
                    db.execute(
                        select(CustomerGrowthNotificationDeliveryModel).where(
                            CustomerGrowthNotificationDeliveryModel.mobile_user_id == beneficiary.id,
                            CustomerGrowthNotificationDeliveryModel.notification_key
                            == referral_available_notification_key(allocation.id),
                        )
                    )
                    .scalars()
                    .all()
                )
                assert len(available_deliveries) == 3
                assert {item.delivery_status for item in available_deliveries} == {"delivered", "planned", "queued"}

                reversed_items = await ReverseReferralRewardsForOrderUseCase(SyncSessionAdapter(db)).execute(
                    order_id=allocation.order_id,
                    reversal_reason="refund_issued",
                    commit=True,
                )
                assert len(reversed_items) == 1

                reversed_deliveries = (
                    db.execute(
                        select(CustomerGrowthNotificationDeliveryModel).where(
                            CustomerGrowthNotificationDeliveryModel.mobile_user_id == beneficiary.id,
                            CustomerGrowthNotificationDeliveryModel.notification_key
                            == referral_reversed_notification_key(allocation.id),
                        )
                    )
                    .scalars()
                    .all()
                )
                assert len(reversed_deliveries) == 3
                by_channel = {item.delivery_channel: item for item in reversed_deliveries}
                assert by_channel["in_app"].delivery_status == "delivered"
                assert by_channel["email"].delivery_status == "planned"
                assert by_channel["telegram"].delivery_status == "queued"
    finally:
        engine.dispose()
        cleanup_sqlite_file(sqlite_path)


@pytest.mark.asyncio
async def test_admin_manual_growth_notification_routes_create_feed_and_delivery_controls(
    async_client: AsyncClient,
) -> None:
    auth_service = AuthService()
    sessionmaker, engine, sqlite_path = create_realm_test_sessionmaker()
    await initialize_realm_test_database(engine)

    try:
        async with override_realm_test_db(sessionmaker):
            admin_user, admin_password = await _create_admin_user(sessionmaker, auth_service)
            with sessionmaker() as db:
                realm = AuthRealmModel(
                    id=uuid.uuid4(),
                    realm_key="customer",
                    realm_type="customer",
                    display_name="Customer Realm",
                    audience="cybervpn:customer",
                    cookie_namespace="customer",
                    status="active",
                    is_default=True,
                )
                customer = MobileUserModel(
                    id=uuid.uuid4(),
                    auth_realm_id=realm.id,
                    email="manual-notify@example.test",
                    password_hash=await auth_service.hash_password("ManualNotifyUser123!"),
                    telegram_id=445566,
                    is_active=True,
                    status="active",
                    notification_prefs={
                        "growth_in_app_admin_updates": True,
                        "growth_email_admin_updates": True,
                        "growth_telegram_admin_updates": True,
                    },
                )
                db.add_all([realm, customer])
                db.commit()

            login_response = await async_client.post(
                "/api/v1/auth/login",
                json={
                    "login_or_email": admin_user.login,
                    "password": admin_password,
                },
                headers={"X-Auth-Realm": "admin"},
            )
            assert login_response.status_code == 200
            admin_headers = {
                "Authorization": f"Bearer {login_response.json()['access_token']}",
                "X-Auth-Realm": "admin",
            }

            manual_response = await async_client.post(
                "/api/v1/admin/growth-notification-deliveries/manual",
                json={
                    "mobile_user_id": str(customer.id),
                    "title": "Account review update",
                    "message": "Support issued a manual growth notice.",
                    "route_slug": "/referral",
                    "locale": "en-EN",
                    "notes": ["Ticket: SUP-42"],
                    "channels": ["in_app", "email", "telegram"],
                },
                headers=admin_headers,
            )
            assert manual_response.status_code == 201
            manual_payload = manual_response.json()
            assert len(manual_payload["deliveries"]) == 3
            by_channel = {item["delivery_channel"]: item for item in manual_payload["deliveries"]}
            assert by_channel["in_app"]["delivery_status"] == "delivered"
            assert by_channel["email"]["delivery_status"] == "planned"
            assert by_channel["telegram"]["delivery_status"] == "queued"

            list_response = await async_client.get(
                f"/api/v1/admin/growth-notification-deliveries?mobile_user_id={customer.id}",
                headers=admin_headers,
            )
            assert list_response.status_code == 200
            assert list_response.json()["total"] == 3

            pause_response = await async_client.post(
                f"/api/v1/admin/growth-notification-deliveries/{by_channel['email']['id']}/pause",
                json={"reason_code": "ops_pause"},
                headers=admin_headers,
            )
            assert pause_response.status_code == 200
            assert pause_response.json()["delivery_status"] == "paused"
            assert pause_response.json()["status_reason"] == "ops_pause"

            resend_response = await async_client.post(
                f"/api/v1/admin/growth-notification-deliveries/{by_channel['email']['id']}/resend",
                json={"reason_code": "retry_after_pause"},
                headers=admin_headers,
            )
            assert resend_response.status_code == 200
            assert resend_response.json()["delivery_status"] == "planned"
            assert resend_response.json()["status_reason"] == "retry_after_pause"

            revoke_response = await async_client.post(
                f"/api/v1/admin/growth-notification-deliveries/{by_channel['telegram']['id']}/revoke",
                json={"reason_code": "ops_revoke"},
                headers=admin_headers,
            )
            assert revoke_response.status_code == 200
            assert revoke_response.json()["delivery_status"] == "revoked"
            assert revoke_response.json()["status_reason"] == "ops_revoke"

            detail_response = await async_client.get(
                f"/api/v1/admin/growth-notification-deliveries/{by_channel['email']['id']}",
                headers=admin_headers,
            )
            assert detail_response.status_code == 200
            detail_payload = detail_response.json()
            assert detail_payload["delivery"]["id"] == by_channel["email"]["id"]
            assert detail_payload["troubleshooting_state"] == "in_progress"
            assert detail_payload["customer_message_key"] == "growth_notifications.delivery.pending"
            assert len(detail_payload["sibling_deliveries"]) == 2
            assert any(item["event_type"] == "admin_paused" for item in detail_payload["event_timeline"])
            assert any(item["event_type"] == "admin_resend_requested" for item in detail_payload["event_timeline"])
            assert detail_payload["source_summary"]["source_kind"] == "admin_manual_notification"

            export_response = await async_client.get(
                f"/api/v1/admin/growth-notification-deliveries/{by_channel['email']['id']}/export",
                headers=admin_headers,
            )
            assert export_response.status_code == 200
            assert "attachment; filename=" in export_response.headers["content-disposition"]
            export_payload = export_response.json()
            assert export_payload["export_kind"] == "growth_notification_delivery_forensics"
            assert export_payload["payload"]["delivery"]["id"] == by_channel["email"]["id"]

            _override_mobile_user(customer.id)
            feed_response = await async_client.get("/api/v1/growth-notifications")
            assert feed_response.status_code == 200
            feed_items = feed_response.json()
            manual_item = next(item for item in feed_items if item["kind"] == "admin_manual_update")
            assert manual_item["title"] == "Account review update"
            assert manual_item["source_kind"] == "admin_manual_notification"
            assert manual_item["notes"] == ["Ticket: SUP-42"]

            with sessionmaker() as db:
                deliveries = (
                    db.execute(
                        select(CustomerGrowthNotificationDeliveryModel).where(
                            CustomerGrowthNotificationDeliveryModel.mobile_user_id == customer.id,
                            CustomerGrowthNotificationDeliveryModel.source_kind == "admin_manual_notification",
                        )
                    )
                    .scalars()
                    .all()
                )
                assert len(deliveries) == 3
                assert {item.notification_key for item in deliveries} == {
                    admin_manual_notification_key(uuid.UUID(str(item.source_id))) for item in deliveries
                }
                events = (
                    db.execute(
                        select(CustomerGrowthNotificationDeliveryEventModel).where(
                            CustomerGrowthNotificationDeliveryEventModel.delivery_id.in_(
                                [uuid.UUID(item["id"]) for item in manual_payload["deliveries"]]
                            )
                        )
                    )
                    .scalars()
                    .all()
                )
                assert len(events) >= 5
                event_types = {item.event_type for item in events}
                assert "fanout_planned" in event_types
                assert "fanout_queued" in event_types
                assert "fanout_delivered" in event_types
                assert "admin_paused" in event_types
                assert "admin_resend_requested" in event_types
                assert "admin_revoked" in event_types
    finally:
        engine.dispose()
        cleanup_sqlite_file(sqlite_path)


@pytest.mark.asyncio
async def test_customer_growth_notification_detail_and_recovery_surface(
    async_client: AsyncClient,
) -> None:
    auth_service = AuthService()
    sessionmaker, engine, sqlite_path = create_realm_test_sessionmaker()
    await initialize_realm_test_database(engine)

    try:
        async with override_realm_test_db(sessionmaker):
            with sessionmaker() as db:
                realm = AuthRealmModel(
                    id=uuid.uuid4(),
                    realm_key="customer",
                    realm_type="customer",
                    display_name="Customer Realm",
                    audience="cybervpn:customer",
                    cookie_namespace="customer",
                    status="active",
                    is_default=True,
                )
                customer = MobileUserModel(
                    id=uuid.uuid4(),
                    auth_realm_id=realm.id,
                    email="customer-troubleshoot@example.test",
                    password_hash=await auth_service.hash_password("CustomerTroubleshoot123!"),
                    telegram_id=112233,
                    is_active=True,
                    status="active",
                    notification_prefs={
                        "growth_in_app_admin_updates": True,
                        "growth_email_admin_updates": True,
                        "growth_telegram_admin_updates": True,
                    },
                )
                db.add_all([realm, customer])
                db.commit()

                notification_key = admin_manual_notification_key(uuid.uuid4())
                planned = await PlanCustomerGrowthNotificationFanoutUseCase(SyncSessionAdapter(db)).execute(
                    mobile_user_id=customer.id,
                    notification_key=notification_key,
                    notification_kind="admin_manual_update",
                    title="Growth delivery issue",
                    message="A delivery needs review.",
                    route_slug="/referral",
                    source_kind="admin_manual_notification",
                    source_id=str(uuid.uuid4()),
                    allowed_channels={"in_app", "email", "telegram"},
                )
                by_channel = {item.delivery_channel: item for item in planned}
                by_channel["email"].delivery_status = "failed"
                by_channel["email"].status_reason = "smtp_timeout"
                db.commit()

                _override_mobile_user(customer.id)

                detail_response = await async_client.get(f"/api/v1/growth-notifications/{notification_key}")
                assert detail_response.status_code == 200
                detail_payload = detail_response.json()
                assert detail_payload["notification"]["id"] == notification_key
                assert detail_payload["support_handoff"]["reference_code"] == f"GROWTH::{notification_key}"
                email_delivery = next(
                    item for item in detail_payload["deliveries"] if item["delivery_channel"] == "email"
                )
                assert email_delivery["delivery_status"] == "failed"
                assert email_delivery["troubleshooting_state"] == "actionable_retry"
                assert email_delivery["recovery_allowed"] is True

                recovery_response = await async_client.post(
                    f"/api/v1/growth-notifications/{notification_key}/recovery",
                    json={"delivery_channel": "email"},
                )
                assert recovery_response.status_code == 200
                recovery_payload = recovery_response.json()
                email_after = next(
                    item for item in recovery_payload["deliveries"] if item["delivery_channel"] == "email"
                )
                assert email_after["delivery_status"] == "planned"
                assert email_after["troubleshooting_state"] == "in_progress"
                assert any(event["event_type"] == "customer_recovery_requested" for event in email_after["events"])

                archive_response = await async_client.post(f"/api/v1/growth-notifications/{notification_key}/archive")
                assert archive_response.status_code == 200

                archived_list = await async_client.get(
                    "/api/v1/growth-notifications",
                    params={"include_archived": "true"},
                )
                assert archived_list.status_code == 200
                archived_item = next(item for item in archived_list.json() if item["id"] == notification_key)
                assert archived_item["archived_at"] is not None
    finally:
        engine.dispose()
        cleanup_sqlite_file(sqlite_path)


@pytest.mark.asyncio
async def test_customer_growth_notification_recovery_blocks_admin_paused_delivery(
    async_client: AsyncClient,
) -> None:
    auth_service = AuthService()
    sessionmaker, engine, sqlite_path = create_realm_test_sessionmaker()
    await initialize_realm_test_database(engine)

    try:
        async with override_realm_test_db(sessionmaker):
            with sessionmaker() as db:
                realm = AuthRealmModel(
                    id=uuid.uuid4(),
                    realm_key="customer",
                    realm_type="customer",
                    display_name="Customer Realm",
                    audience="cybervpn:customer",
                    cookie_namespace="customer",
                    status="active",
                    is_default=True,
                )
                customer = MobileUserModel(
                    id=uuid.uuid4(),
                    auth_realm_id=realm.id,
                    email="customer-paused@example.test",
                    password_hash=await auth_service.hash_password("CustomerPaused123!"),
                    telegram_id=445566,
                    is_active=True,
                    status="active",
                    notification_prefs={
                        "growth_in_app_admin_updates": True,
                        "growth_email_admin_updates": True,
                        "growth_telegram_admin_updates": True,
                    },
                )
                db.add_all([realm, customer])
                db.commit()

                notification_key = admin_manual_notification_key(uuid.uuid4())
                planned = await PlanCustomerGrowthNotificationFanoutUseCase(SyncSessionAdapter(db)).execute(
                    mobile_user_id=customer.id,
                    notification_key=notification_key,
                    notification_kind="admin_manual_update",
                    title="Growth delivery paused",
                    message="A delivery is paused.",
                    route_slug="/referral",
                    source_kind="admin_manual_notification",
                    source_id=str(uuid.uuid4()),
                    allowed_channels={"in_app", "email"},
                )
                by_channel = {item.delivery_channel: item for item in planned}
                await ManageCustomerGrowthNotificationDeliveryUseCase(SyncSessionAdapter(db)).pause(
                    delivery_id=by_channel["email"].id,
                    reason_code="ops_pause",
                )
                db.commit()

                _override_mobile_user(customer.id)

                blocked_response = await async_client.post(
                    f"/api/v1/growth-notifications/{notification_key}/recovery",
                    json={"delivery_channel": "email"},
                )
                assert blocked_response.status_code == 409
                assert "support review" in blocked_response.json()["detail"].lower()

                detail_response = await async_client.get(f"/api/v1/growth-notifications/{notification_key}")
                assert detail_response.status_code == 200
                email_delivery = next(
                    item for item in detail_response.json()["deliveries"] if item["delivery_channel"] == "email"
                )
                assert email_delivery["troubleshooting_state"] == "paused_admin"
                assert email_delivery["recovery_allowed"] is False
                assert email_delivery["support_required"] is True
                assert email_delivery["repair_target"]["kind"] == "support_contact"

                escalation_response = await async_client.post(
                    f"/api/v1/growth-notifications/{notification_key}/support-escalation",
                    json={
                        "delivery_channel": "email",
                        "escalation_channel": "support_email",
                    },
                )
                assert escalation_response.status_code == 200
                escalation_payload = escalation_response.json()
                assert escalation_payload["support_handoff"]["reference_code"] == f"GROWTH::{notification_key}"
                assert escalation_payload["support_handoff"]["contact_subject"].startswith(
                    f"[GROWTH::{notification_key}]"
                )

                with sessionmaker() as db:
                    delivery_id = uuid.UUID(email_delivery["delivery_id"])
                    event_types = {
                        item.event_type
                        for item in db.execute(
                            select(CustomerGrowthNotificationDeliveryEventModel).where(
                                CustomerGrowthNotificationDeliveryEventModel.delivery_id == delivery_id
                            )
                        )
                        .scalars()
                        .all()
                    }
                    assert "customer_support_escalation_requested" in event_types
    finally:
        engine.dispose()
        cleanup_sqlite_file(sqlite_path)


@pytest.mark.asyncio
async def test_preferences_reenable_auto_recovers_preference_blocked_delivery(
    async_client: AsyncClient,
) -> None:
    auth_service = AuthService()
    sessionmaker, engine, sqlite_path = create_realm_test_sessionmaker()
    await initialize_realm_test_database(engine)

    try:
        async with override_realm_test_db(sessionmaker):
            with sessionmaker() as db:
                realm = AuthRealmModel(
                    id=uuid.uuid4(),
                    realm_key="customer",
                    realm_type="customer",
                    display_name="Customer Realm",
                    audience="cybervpn:customer",
                    cookie_namespace="customer",
                    status="active",
                    is_default=True,
                )
                customer = MobileUserModel(
                    id=uuid.uuid4(),
                    auth_realm_id=realm.id,
                    email="prefs-repair@example.test",
                    password_hash=await auth_service.hash_password("PrefsRepair123!"),
                    is_active=True,
                    status="active",
                    notification_prefs={
                        "growth_in_app_admin_updates": True,
                        "growth_email_admin_updates": False,
                        "growth_telegram_admin_updates": False,
                    },
                )
                db.add_all([realm, customer])
                db.commit()

                notification_key = admin_manual_notification_key(uuid.uuid4())
                planned = await PlanCustomerGrowthNotificationFanoutUseCase(SyncSessionAdapter(db)).execute(
                    mobile_user_id=customer.id,
                    notification_key=notification_key,
                    notification_kind="admin_manual_update",
                    title="Email delivery paused by preferences",
                    message="A delivery was suppressed.",
                    route_slug="/referral",
                    source_kind="admin_manual_notification",
                    source_id=str(uuid.uuid4()),
                    allowed_channels={"in_app", "email"},
                )
                by_channel = {item.delivery_channel: item for item in planned}
                assert by_channel["email"].delivery_status == "skipped"
                assert by_channel["email"].status_reason == "preference_disabled"
                db.commit()

                _override_mobile_user(customer.id)
                response = await async_client.patch(
                    "/api/v1/growth-notifications/preferences",
                    json={"growth_email_admin_updates": True},
                )
                assert response.status_code == 200
                assert response.json()["growth_email_admin_updates"] is True

            with sessionmaker() as db:
                email_delivery = db.get(CustomerGrowthNotificationDeliveryModel, by_channel["email"].id)
                assert email_delivery is not None
                assert email_delivery.delivery_status == "planned"
                assert email_delivery.status_reason == "preferences_reenabled"
                event_types = {
                    item.event_type
                    for item in db.execute(
                        select(CustomerGrowthNotificationDeliveryEventModel).where(
                            CustomerGrowthNotificationDeliveryEventModel.delivery_id == by_channel["email"].id
                        )
                    )
                    .scalars()
                    .all()
                }
                assert "repair_completed" in event_types
                assert "delivery_recovered" in event_types

                closure_deliveries = (
                    db.execute(
                        select(CustomerGrowthNotificationDeliveryModel).where(
                            CustomerGrowthNotificationDeliveryModel.mobile_user_id == customer.id,
                            CustomerGrowthNotificationDeliveryModel.source_kind == "growth_notification_closure",
                        )
                    )
                    .scalars()
                    .all()
                )
                assert closure_deliveries
                assert any(item.delivery_channel == "in_app" for item in closure_deliveries)
    finally:
        engine.dispose()
        cleanup_sqlite_file(sqlite_path)


@pytest.mark.asyncio
async def test_admin_resolve_route_rearms_delivery_and_creates_closure_notice(
    async_client: AsyncClient,
) -> None:
    auth_service = AuthService()
    sessionmaker, engine, sqlite_path = create_realm_test_sessionmaker()
    await initialize_realm_test_database(engine)

    try:
        async with override_realm_test_db(sessionmaker):
            admin_user, admin_password = await _create_admin_user(sessionmaker, auth_service)
            with sessionmaker() as db:
                realm = AuthRealmModel(
                    id=uuid.uuid4(),
                    realm_key="customer",
                    realm_type="customer",
                    display_name="Customer Realm",
                    audience="cybervpn:customer",
                    cookie_namespace="customer",
                    status="active",
                    is_default=True,
                )
                customer = MobileUserModel(
                    id=uuid.uuid4(),
                    auth_realm_id=realm.id,
                    email="resolve-growth@example.test",
                    password_hash=await auth_service.hash_password("ResolveGrowth123!"),
                    is_active=True,
                    status="active",
                    notification_prefs={
                        "growth_in_app_admin_updates": True,
                        "growth_email_admin_updates": True,
                        "growth_telegram_admin_updates": False,
                    },
                )
                db.add_all([realm, customer])
                db.commit()

                notification_key = admin_manual_notification_key(uuid.uuid4())
                planned = await PlanCustomerGrowthNotificationFanoutUseCase(SyncSessionAdapter(db)).execute(
                    mobile_user_id=customer.id,
                    notification_key=notification_key,
                    notification_kind="admin_manual_update",
                    title="Support review required",
                    message="Email delivery needs resolution.",
                    route_slug="/referral",
                    source_kind="admin_manual_notification",
                    source_id=str(uuid.uuid4()),
                    allowed_channels={"in_app", "email"},
                )
                by_channel = {item.delivery_channel: item for item in planned}
                by_channel["email"].delivery_status = "paused"
                by_channel["email"].status_reason = "ops_pause"
                db.commit()

            login_response = await async_client.post(
                "/api/v1/auth/login",
                json={"login_or_email": admin_user.login, "password": admin_password},
                headers={"X-Auth-Realm": "admin"},
            )
            assert login_response.status_code == 200
            admin_headers = {
                "Authorization": f"Bearer {login_response.json()['access_token']}",
                "X-Auth-Realm": "admin",
            }

            resolve_response = await async_client.post(
                f"/api/v1/admin/growth-notification-deliveries/{by_channel['email'].id}/resolve",
                json={"reason_code": "support_resolved"},
                headers=admin_headers,
            )
            assert resolve_response.status_code == 200
            assert resolve_response.json()["delivery_status"] == "planned"
            assert resolve_response.json()["status_reason"] == "support_resolved"

            with sessionmaker() as db:
                closure_deliveries = (
                    db.execute(
                        select(CustomerGrowthNotificationDeliveryModel).where(
                            CustomerGrowthNotificationDeliveryModel.mobile_user_id == customer.id,
                            CustomerGrowthNotificationDeliveryModel.source_kind == "growth_notification_closure",
                        )
                    )
                    .scalars()
                    .all()
                )
                assert closure_deliveries
                event_types = {
                    item.event_type
                    for item in db.execute(
                        select(CustomerGrowthNotificationDeliveryEventModel).where(
                            CustomerGrowthNotificationDeliveryEventModel.delivery_id == by_channel["email"].id
                        )
                    )
                    .scalars()
                    .all()
                }
                assert "support_resolved" in event_types
                assert "repair_completed" in event_types
                assert "delivery_recovered" in event_types
    finally:
        engine.dispose()
        cleanup_sqlite_file(sqlite_path)


@pytest.mark.asyncio
async def test_contact_data_correction_and_telegram_link_recover_blocked_deliveries() -> None:
    auth_service = AuthService()
    sessionmaker, engine, sqlite_path = create_realm_test_sessionmaker()
    await initialize_realm_test_database(engine)

    try:
        async with override_realm_test_db(sessionmaker):
            with sessionmaker() as db:
                realm = AuthRealmModel(
                    id=uuid.uuid4(),
                    realm_key="customer",
                    realm_type="customer",
                    display_name="Customer Realm",
                    audience="cybervpn:customer",
                    cookie_namespace="customer",
                    status="active",
                    is_default=True,
                )
                customer = MobileUserModel(
                    id=uuid.uuid4(),
                    auth_realm_id=realm.id,
                    email="",
                    password_hash=await auth_service.hash_password("ContactRepair123!"),
                    is_active=True,
                    status="active",
                    notification_prefs={
                        "growth_in_app_admin_updates": True,
                        "growth_email_admin_updates": True,
                        "growth_telegram_admin_updates": True,
                    },
                )
                db.add_all([realm, customer])
                db.commit()

                notification_key = admin_manual_notification_key(uuid.uuid4())
                planned = await PlanCustomerGrowthNotificationFanoutUseCase(SyncSessionAdapter(db)).execute(
                    mobile_user_id=customer.id,
                    notification_key=notification_key,
                    notification_kind="admin_manual_update",
                    title="Repair candidate",
                    message="A delivery was blocked.",
                    route_slug="/referral",
                    source_kind="admin_manual_notification",
                    source_id=str(uuid.uuid4()),
                    allowed_channels={"email", "telegram"},
                )
                by_channel = {item.delivery_channel: item for item in planned}
                assert by_channel["email"].status_reason == "email_unavailable"
                assert by_channel["telegram"].status_reason == "telegram_unlinked"

                customer.email = "customer-fixed@example.test"
                customer.telegram_id = 555001
                db.commit()

                automation = AutomateCustomerGrowthNotificationRepairUseCase(SyncSessionAdapter(db))
                email_result = await automation.execute(
                    mobile_user_id=customer.id,
                    repair_trigger="contact_data_corrected",
                )
                telegram_result = await automation.execute(
                    mobile_user_id=customer.id,
                    repair_trigger="telegram_linked",
                )
                assert email_result.recovered_deliveries
                assert telegram_result.recovered_deliveries
                db.commit()

                refreshed_email = db.get(CustomerGrowthNotificationDeliveryModel, by_channel["email"].id)
                refreshed_telegram = db.get(CustomerGrowthNotificationDeliveryModel, by_channel["telegram"].id)
                assert refreshed_email is not None
                assert refreshed_email.delivery_status == "planned"
                assert refreshed_email.status_reason == "contact_data_corrected"
                assert refreshed_telegram is not None
                assert refreshed_telegram.delivery_status == "queued"
                assert refreshed_telegram.status_reason == "telegram_linked"
    finally:
        engine.dispose()
        cleanup_sqlite_file(sqlite_path)
