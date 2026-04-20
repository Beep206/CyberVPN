from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from httpx import AsyncClient

from src.application.services.auth_service import AuthService
from src.infrastructure.cache.redis_client import get_redis
from src.infrastructure.database.models.admin_user_model import AdminUserModel
from src.infrastructure.database.models.auth_realm_model import AuthRealmModel
from src.infrastructure.database.models.mobile_user_model import MobileUserModel
from src.infrastructure.database.repositories.auth_realm_repo import AuthRealmRepository
from src.main import app
from tests.helpers.realm_auth import (
    FakeRedis,
    SyncSessionAdapter,
    cleanup_sqlite_file,
    create_realm_test_sessionmaker,
    initialize_realm_test_database,
    override_realm_test_db,
)
from tests.integration.test_order_commit import _seed_order_context

pytestmark = [pytest.mark.integration]


def _make_admin_access_token(auth_service: AuthService, *, user_id, admin_realm: AuthRealmModel) -> str:
    token, _, _ = auth_service.create_access_token(
        str(user_id),
        "admin",
        audience=admin_realm.audience,
        principal_type="admin",
        realm_id=str(admin_realm.id),
        realm_key=admin_realm.realm_key,
        scope_family="admin",
    )
    return token


@pytest.mark.asyncio
async def test_legacy_service_access_shadow_and_migration_bridge_are_idempotent(
    async_client: AsyncClient,
) -> None:
    auth_service = AuthService()
    fake_redis = FakeRedis()
    sessionmaker, engine, sqlite_path = create_realm_test_sessionmaker()
    await initialize_realm_test_database(engine)

    async def _override_redis():
        yield fake_redis

    app.dependency_overrides[get_redis] = _override_redis

    try:
        async with override_realm_test_db(sessionmaker):
            seeded = await _seed_order_context(sessionmaker, auth_service)

            with sessionmaker() as db:
                realm_repo = AuthRealmRepository(SyncSessionAdapter(db))
                admin_realm = await realm_repo.get_or_create_default_realm("admin")
                admin_user = AdminUserModel(
                    login="service-legacy-migration-admin",
                    email="service-legacy-migration-admin@example.com",
                    auth_realm_id=admin_realm.id,
                    password_hash=await auth_service.hash_password("ServiceLegacyMigrationAdmin123!"),
                    role="admin",
                    is_active=True,
                    is_email_verified=True,
                )
                customer_user = db.get(MobileUserModel, uuid.UUID(seeded["customer_user_id"]))
                assert customer_user is not None
                customer_user.remnawave_uuid = "legacy-remnawave-subject-001"
                customer_user.subscription_url = "https://partner.example.test/sub/legacy-bridge-001"
                customer_user.trial_expires_at = datetime.now(UTC) + timedelta(days=4)
                db.add(admin_user)
                db.commit()
                admin_token = _make_admin_access_token(
                    auth_service,
                    user_id=admin_user.id,
                    admin_realm=admin_realm,
                )

            admin_headers = {
                "Authorization": f"Bearer {admin_token}",
                "X-Auth-Realm": "admin",
            }
            payload = {
                "customer_account_id": seeded["customer_user_id"],
                "auth_realm_id": seeded["customer_realm_id"],
                "provider_name": "remnawave",
            }

            shadow_before_response = await async_client.post(
                "/api/v1/service-identities/legacy/shadow-parity",
                headers=admin_headers,
                json=payload,
            )
            assert shadow_before_response.status_code == 200
            shadow_before = shadow_before_response.json()
            assert shadow_before["legacy_provider_subject_ref"] == "legacy-remnawave-subject-001"
            assert shadow_before["legacy_subscription_url"] == "https://partner.example.test/sub/legacy-bridge-001"
            assert shadow_before["legacy_entitlement_snapshot"]["status"] == "trial"
            assert shadow_before["canonical_entitlement_snapshot"]["status"] == "trial"
            assert shadow_before["service_identity"] is None
            assert shadow_before["provisioning_profile"] is None
            assert shadow_before["access_delivery_channel"] is None
            assert set(shadow_before["mismatch_codes"]) == {
                "missing_canonical_service_identity",
                "missing_canonical_subscription_profile",
                "missing_canonical_subscription_channel",
            }

            first_migrate_response = await async_client.post(
                "/api/v1/service-identities/legacy/migrate",
                headers=admin_headers,
                json=payload,
            )
            assert first_migrate_response.status_code == 200
            first_migrate_payload = first_migrate_response.json()
            assert first_migrate_payload["service_identity_created"] is True
            assert first_migrate_payload["provisioning_profile_created"] is True
            assert first_migrate_payload["access_delivery_channel_created"] is True
            assert (
                first_migrate_payload["service_identity"]["provider_subject_ref"]
                == "legacy-remnawave-subject-001"
            )
            assert first_migrate_payload["provisioning_profile"]["profile_key"] == "subscription_url-default"
            assert first_migrate_payload["access_delivery_channel"]["channel_type"] == "subscription_url"
            assert (
                first_migrate_payload["access_delivery_channel"]["delivery_payload"]["subscription_url"]
                == "https://partner.example.test/sub/legacy-bridge-001"
            )
            assert (
                first_migrate_payload["access_delivery_channel"]["delivery_payload"]["legacy_subscription_url"]
                == "https://partner.example.test/sub/legacy-bridge-001"
            )
            assert first_migrate_payload["shadow_before"]["mismatch_codes"] == shadow_before["mismatch_codes"]
            assert first_migrate_payload["shadow_after"]["mismatch_codes"] == []
            assert first_migrate_payload["shadow_after"]["service_identity"] is not None
            assert first_migrate_payload["shadow_after"]["provisioning_profile"] is not None
            assert first_migrate_payload["shadow_after"]["access_delivery_channel"] is not None
            assert first_migrate_payload["shadow_after"]["canonical_entitlement_snapshot"]["status"] == "trial"

            second_migrate_response = await async_client.post(
                "/api/v1/service-identities/legacy/migrate",
                headers=admin_headers,
                json=payload,
            )
            assert second_migrate_response.status_code == 200
            second_migrate_payload = second_migrate_response.json()
            assert second_migrate_payload["service_identity_created"] is False
            assert second_migrate_payload["provisioning_profile_created"] is False
            assert second_migrate_payload["access_delivery_channel_created"] is False
            assert (
                second_migrate_payload["service_identity"]["id"]
                == first_migrate_payload["service_identity"]["id"]
            )
            assert (
                second_migrate_payload["provisioning_profile"]["id"]
                == first_migrate_payload["provisioning_profile"]["id"]
            )
            assert (
                second_migrate_payload["access_delivery_channel"]["id"]
                == first_migrate_payload["access_delivery_channel"]["id"]
            )
            assert second_migrate_payload["shadow_before"]["mismatch_codes"] == []
            assert second_migrate_payload["shadow_after"]["mismatch_codes"] == []
    finally:
        app.dependency_overrides.pop(get_redis, None)
        engine.dispose()
        cleanup_sqlite_file(sqlite_path)
