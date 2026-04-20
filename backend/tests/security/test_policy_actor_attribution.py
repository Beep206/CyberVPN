import uuid

import pytest
from httpx import AsyncClient

from src.application.services.auth_service import AuthService
from src.infrastructure.cache.redis_client import get_redis
from src.infrastructure.database.models.admin_user_model import AdminUserModel
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


def _make_admin_token(auth_service: AuthService, *, user_id, realm) -> str:
    token, _, _ = auth_service.create_access_token(
        str(user_id),
        "admin",
        audience=realm.audience,
        principal_type="admin",
        realm_id=str(realm.id),
        realm_key=realm.realm_key,
        scope_family="admin",
    )
    return token


@pytest.mark.security
@pytest.mark.integration
async def test_policy_actor_attribution_is_derived_from_authenticated_admin_context(
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

                creator_admin = AdminUserModel(
                    login="creator_admin",
                    email="creator-admin@example.com",
                    auth_realm_id=admin_realm.id,
                    password_hash=await auth_service.hash_password("CreatorAdminP@ssword123!"),
                    role="admin",
                    is_active=True,
                    is_email_verified=True,
                )
                approver_admin = AdminUserModel(
                    login="approver_admin",
                    email="approver-admin@example.com",
                    auth_realm_id=admin_realm.id,
                    password_hash=await auth_service.hash_password("ApproverAdminP@ssword123!"),
                    role="admin",
                    is_active=True,
                    is_email_verified=True,
                )
                db.add_all([creator_admin, approver_admin])
                db.commit()

                creator_token = _make_admin_token(auth_service, user_id=creator_admin.id, realm=admin_realm)
                approver_token = _make_admin_token(auth_service, user_id=approver_admin.id, realm=admin_realm)

            create_response = await async_client.post(
                "/api/v1/policies/",
                headers={"Authorization": f"Bearer {creator_token}", "X-Auth-Realm": "admin"},
                json={
                    "policy_family": "surface_policy_matrix",
                    "policy_key": "official-web-policy",
                    "subject_type": "storefront",
                    "subject_id": None,
                    "version_number": 1,
                    "payload": {"wallet_spend": True},
                    "approval_state": "draft",
                    "version_status": "draft",
                    "created_by_admin_user_id": str(uuid.uuid4()),
                },
            )
            assert create_response.status_code == 201
            create_payload = create_response.json()
            assert create_payload["created_by_admin_user_id"] == str(creator_admin.id)
            assert create_payload["approved_by_admin_user_id"] is None

            approve_response = await async_client.post(
                f"/api/v1/policies/{create_payload['id']}/approve",
                headers={"Authorization": f"Bearer {approver_token}", "X-Auth-Realm": "admin"},
                json={
                    "approved_by_admin_user_id": str(uuid.uuid4()),
                    "version_status": "active",
                },
            )
            assert approve_response.status_code == 200
            approve_payload = approve_response.json()
            assert approve_payload["created_by_admin_user_id"] == str(creator_admin.id)
            assert approve_payload["approved_by_admin_user_id"] == str(approver_admin.id)
            assert approve_payload["approval_state"] == "approved"
            assert approve_payload["version_status"] == "active"
            assert approve_payload["approved_at"] is not None
    finally:
        app.dependency_overrides.pop(get_redis, None)
        engine.dispose()
        cleanup_sqlite_file(sqlite_path)
