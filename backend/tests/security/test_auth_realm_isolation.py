import uuid

import pytest
from httpx import AsyncClient

from src.application.services.auth_service import AuthService
from src.infrastructure.cache.redis_client import get_redis
from src.infrastructure.database.models.admin_user_model import AdminUserModel
from src.infrastructure.database.models.auth_realm_model import AuthRealmModel
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


@pytest.mark.security
@pytest.mark.integration
async def test_same_email_can_exist_in_multiple_realms_without_cross_realm_login(
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
            with sessionmaker() as db:
                realm_repo = AuthRealmRepository(SyncSessionAdapter(db))
                admin_realm = await realm_repo.get_or_create_default_realm("admin")

                partner_admin_realm = AuthRealmModel(
                    id=uuid.uuid4(),
                    realm_key="partner-admin",
                    realm_type="admin",
                    display_name="Partner Admin Realm",
                    audience="cybervpn:partner-admin",
                    cookie_namespace="partner-admin",
                    status="active",
                    is_default=False,
                )
                db.add(partner_admin_realm)

                shared_email = "multi-realm@example.com"
                admin_password = "RealmAdminP@ssword123!"
                partner_password = "RealmPartnerP@ssword123!"

                db.add_all(
                    [
                        AdminUserModel(
                            login="realm_admin",
                            email=shared_email,
                            auth_realm_id=admin_realm.id,
                            password_hash=await auth_service.hash_password(admin_password),
                            role="admin",
                            is_active=True,
                            is_email_verified=True,
                        ),
                        AdminUserModel(
                            login="realm_partner_admin",
                            email=shared_email,
                            auth_realm_id=partner_admin_realm.id,
                            password_hash=await auth_service.hash_password(partner_password),
                            role="admin",
                            is_active=True,
                            is_email_verified=True,
                        ),
                    ]
                )
                db.commit()

            admin_login = await async_client.post(
                "/api/v1/auth/login",
                headers={"X-Auth-Realm": "admin"},
                json={"login_or_email": "multi-realm@example.com", "password": "RealmAdminP@ssword123!"},
            )
            assert admin_login.status_code == 200
            admin_token = admin_login.json()["access_token"]

            partner_login = await async_client.post(
                "/api/v1/auth/login",
                headers={"X-Auth-Realm": "partner-admin"},
                json={"login_or_email": "multi-realm@example.com", "password": "RealmPartnerP@ssword123!"},
            )
            assert partner_login.status_code == 200
            partner_token = partner_login.json()["access_token"]

            admin_me = await async_client.get(
                "/api/v1/auth/me",
                headers={
                    "Authorization": f"Bearer {admin_token}",
                    "X-Auth-Realm": "admin",
                },
            )
            assert admin_me.status_code == 200
            assert admin_me.json()["login"] == "realm_admin"

            partner_me = await async_client.get(
                "/api/v1/auth/me",
                headers={
                    "Authorization": f"Bearer {partner_token}",
                    "X-Auth-Realm": "partner-admin",
                },
            )
            assert partner_me.status_code == 200
            assert partner_me.json()["login"] == "realm_partner_admin"

            cross_realm_me = await async_client.get(
                "/api/v1/auth/me",
                headers={
                    "Authorization": f"Bearer {admin_token}",
                    "X-Auth-Realm": "partner-admin",
                },
            )
            assert cross_realm_me.status_code == 401
    finally:
        app.dependency_overrides.pop(get_redis, None)
        engine.dispose()
        cleanup_sqlite_file(sqlite_path)
