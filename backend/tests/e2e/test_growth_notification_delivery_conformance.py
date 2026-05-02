from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient

from src.application.services.auth_service import AuthService
from src.application.use_cases.growth_notifications.catalog import admin_manual_notification_key
from src.application.use_cases.growth_notifications.fanout import (
    PlanCustomerGrowthNotificationFanoutUseCase,
)
from src.infrastructure.database.models.admin_user_model import AdminUserModel
from src.infrastructure.database.models.auth_realm_model import AuthRealmModel
from src.infrastructure.database.models.mobile_user_model import MobileUserModel
from src.infrastructure.database.repositories.auth_realm_repo import AuthRealmRepository
from src.main import app
from src.presentation.dependencies.auth import get_current_mobile_user_id
from tests.helpers.realm_auth import (
    SyncSessionAdapter,
    cleanup_sqlite_file,
    create_realm_test_sessionmaker,
    initialize_realm_test_database,
    override_realm_test_db,
)

pytestmark = [pytest.mark.e2e, pytest.mark.integration]


@pytest.fixture(autouse=True)
def _clear_mobile_override():
    yield
    app.dependency_overrides.pop(get_current_mobile_user_id, None)


def _override_mobile_user(user_id: uuid.UUID) -> None:
    app.dependency_overrides[get_current_mobile_user_id] = lambda: user_id


async def _create_admin_user(
    sessionmaker,
    auth_service: AuthService,
) -> tuple[AdminUserModel, str]:
    password = "GrowthNotificationConformanceAdmin123!"
    with sessionmaker() as db:
        admin_realm = await AuthRealmRepository(SyncSessionAdapter(db)).get_or_create_default_realm("admin")
        user = AdminUserModel(
            id=uuid.uuid4(),
            login="growth_notification_conformance_admin",
            email="growth-notification-conformance-admin@example.test",
            auth_realm_id=admin_realm.id,
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
async def test_growth_notification_conformance_preferences_reenabled_and_support_resolved(
    async_client: AsyncClient,
) -> None:
    auth_service = AuthService()
    sessionmaker, engine, sqlite_path = create_realm_test_sessionmaker()
    await initialize_realm_test_database(engine)

    try:
        async with override_realm_test_db(sessionmaker):
            admin_user, admin_password = await _create_admin_user(sessionmaker, auth_service)
            notification_key = admin_manual_notification_key(uuid.uuid4())

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
                    email="prefs-growth@example.test",
                    password_hash=await auth_service.hash_password("PrefsGrowth123!"),
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

                planned = await PlanCustomerGrowthNotificationFanoutUseCase(SyncSessionAdapter(db)).execute(
                    mobile_user_id=customer.id,
                    notification_key=notification_key,
                    notification_kind="admin_manual_update",
                    title="Email delivery repair",
                    message="Enable email and retry the notice.",
                    route_slug="/referral",
                    source_kind="admin_manual_notification",
                    source_id=str(uuid.uuid4()),
                    allowed_channels={"in_app", "email"},
                )
                db.commit()

                email_delivery_id = next(
                    item.id for item in planned if item.delivery_channel == "email"
                )

            _override_mobile_user(customer.id)

            customer_detail_response = await async_client.get(
                f"/api/v1/growth-notifications/{notification_key}"
            )
            assert customer_detail_response.status_code == 200
            detail_payload = customer_detail_response.json()
            email_detail = next(item for item in detail_payload["deliveries"] if item["delivery_channel"] == "email")
            assert email_detail["delivery_status"] == "skipped"
            assert email_detail["troubleshooting_state"] == "suppressed"
            assert email_detail["repair_target"]["kind"] == "notification_preferences"

            update_response = await async_client.patch(
                "/api/v1/growth-notifications/preferences",
                json={"growth_email_admin_updates": True},
            )
            assert update_response.status_code == 200
            assert update_response.json()["growth_email_admin_updates"] is True

            repaired_detail_response = await async_client.get(
                f"/api/v1/growth-notifications/{notification_key}"
            )
            assert repaired_detail_response.status_code == 200
            repaired_payload = repaired_detail_response.json()
            repaired_email = next(
                item for item in repaired_payload["deliveries"] if item["delivery_channel"] == "email"
            )
            assert repaired_email["delivery_status"] == "planned"
            assert repaired_email["customer_message_key"] == "growth_notifications.delivery.pending"
            assert {event["event_type"] for event in repaired_email["events"]} >= {
                "repair_completed",
                "delivery_recovered",
            }

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

            pause_response = await async_client.post(
                f"/api/v1/admin/growth-notification-deliveries/{email_delivery_id}/pause",
                json={"reason_code": "ops_pause"},
                headers=admin_headers,
            )
            assert pause_response.status_code == 200
            assert pause_response.json()["delivery_status"] == "paused"

            resolve_response = await async_client.post(
                f"/api/v1/admin/growth-notification-deliveries/{email_delivery_id}/resolve",
                json={"reason_code": "support_resolved"},
                headers=admin_headers,
            )
            assert resolve_response.status_code == 200
            assert resolve_response.json()["delivery_status"] == "planned"
            assert resolve_response.json()["status_reason"] == "support_resolved"

            admin_detail_response = await async_client.get(
                f"/api/v1/admin/growth-notification-deliveries/{email_delivery_id}",
                headers=admin_headers,
            )
            assert admin_detail_response.status_code == 200
            admin_detail_payload = admin_detail_response.json()
            assert admin_detail_payload["delivery"]["status_reason"] == "support_resolved"
            assert {
                item["event_type"] for item in admin_detail_payload["event_timeline"]
            } >= {"repair_completed", "delivery_recovered", "support_resolved"}

            export_response = await async_client.get(
                f"/api/v1/admin/growth-notification-deliveries/{email_delivery_id}/export",
                headers=admin_headers,
            )
            assert export_response.status_code == 200
            export_payload = export_response.json()
            assert export_payload["export_kind"] == "growth_notification_delivery_forensics"
            assert export_payload["payload"]["support_summary"]
    finally:
        engine.dispose()
        cleanup_sqlite_file(sqlite_path)


@pytest.mark.asyncio
async def test_growth_notification_conformance_contact_data_corrected_and_telegram_linked(
    async_client: AsyncClient,
) -> None:
    auth_service = AuthService()
    sessionmaker, engine, sqlite_path = create_realm_test_sessionmaker()
    await initialize_realm_test_database(engine)

    try:
        async with override_realm_test_db(sessionmaker):
            admin_user, admin_password = await _create_admin_user(sessionmaker, auth_service)
            notification_key = admin_manual_notification_key(uuid.uuid4())

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
                    password_hash=await auth_service.hash_password("RepairGrowth123!"),
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

                planned = await PlanCustomerGrowthNotificationFanoutUseCase(SyncSessionAdapter(db)).execute(
                    mobile_user_id=customer.id,
                    notification_key=notification_key,
                    notification_kind="admin_manual_update",
                    title="Channel repair needed",
                    message="Correct the missing customer contact data.",
                    route_slug="/referral",
                    source_kind="admin_manual_notification",
                    source_id=str(uuid.uuid4()),
                    allowed_channels={"email", "telegram"},
                )
                db.commit()

                email_delivery_id = next(
                    item.id for item in planned if item.delivery_channel == "email"
                )
                telegram_delivery_id = next(
                    item.id for item in planned if item.delivery_channel == "telegram"
                )

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

            update_response = await async_client.patch(
                f"/api/v1/admin/mobile-users/{customer.id}",
                json={
                    "email": "customer-repaired@example.test",
                    "telegram_id": 5550001,
                },
                headers=admin_headers,
            )
            assert update_response.status_code == 200
            assert update_response.json()["email"] == "customer-repaired@example.test"
            assert update_response.json()["telegram_id"] == 5550001

            email_detail_response = await async_client.get(
                f"/api/v1/admin/growth-notification-deliveries/{email_delivery_id}",
                headers=admin_headers,
            )
            assert email_detail_response.status_code == 200
            email_detail_payload = email_detail_response.json()
            assert email_detail_payload["delivery"]["delivery_status"] == "planned"
            assert email_detail_payload["delivery"]["status_reason"] == "contact_data_corrected"
            assert {
                item["event_type"] for item in email_detail_payload["event_timeline"]
            } >= {"repair_completed", "delivery_recovered"}

            telegram_detail_response = await async_client.get(
                f"/api/v1/admin/growth-notification-deliveries/{telegram_delivery_id}",
                headers=admin_headers,
            )
            assert telegram_detail_response.status_code == 200
            telegram_detail_payload = telegram_detail_response.json()
            assert telegram_detail_payload["delivery"]["delivery_status"] == "queued"
            assert telegram_detail_payload["delivery"]["status_reason"] == "telegram_linked"
            assert {
                item["event_type"] for item in telegram_detail_payload["event_timeline"]
            } >= {"repair_completed", "delivery_recovered"}

    finally:
        engine.dispose()
        cleanup_sqlite_file(sqlite_path)
