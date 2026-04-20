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


async def _create_admin_user(
    *,
    session,
    auth_service: AuthService,
    auth_realm_id,
    login: str,
    email: str,
    password: str,
    role: str,
) -> AdminUserModel:
    user = AdminUserModel(
        login=login,
        email=email,
        auth_realm_id=auth_realm_id,
        password_hash=await auth_service.hash_password(password),
        role=role,
        is_active=True,
        is_email_verified=True,
    )
    session.add(user)
    session.commit()
    return user


async def _login(async_client: AsyncClient, login_or_email: str, password: str) -> str:
    response = await async_client.post(
        "/api/v1/auth/login",
        headers={"X-Auth-Realm": "admin"},
        json={"login_or_email": login_or_email, "password": password},
    )
    assert response.status_code == 200
    return response.json()["access_token"]


@pytest.mark.security
@pytest.mark.integration
async def test_partner_workspace_scope_enforcement(async_client: AsyncClient) -> None:
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

                await _create_admin_user(
                    session=db,
                    auth_service=auth_service,
                    auth_realm_id=admin_realm.id,
                    login="scope_admin",
                    email="scope-admin@example.com",
                    password="ScopeAdminP@ssword123!",
                    role="admin",
                )
                owner_operator = await _create_admin_user(
                    session=db,
                    auth_service=auth_service,
                    auth_realm_id=admin_realm.id,
                    login="scope_owner",
                    email="scope-owner@example.com",
                    password="ScopeOwnerP@ssword123!",
                    role="viewer",
                )
                analyst_operator = await _create_admin_user(
                    session=db,
                    auth_service=auth_service,
                    auth_realm_id=admin_realm.id,
                    login="scope_analyst",
                    email="scope-analyst@example.com",
                    password="ScopeAnalystP@ssword123!",
                    role="viewer",
                )
                outsider_operator = await _create_admin_user(
                    session=db,
                    auth_service=auth_service,
                    auth_realm_id=admin_realm.id,
                    login="scope_outsider",
                    email="scope-outsider@example.com",
                    password="ScopeOutsiderP@ssword123!",
                    role="viewer",
                )

            admin_token = await _login(async_client, "scope-admin@example.com", "ScopeAdminP@ssword123!")
            create_response = await async_client.post(
                "/api/v1/admin/partner-workspaces",
                headers={
                    "Authorization": f"Bearer {admin_token}",
                    "X-Auth-Realm": "admin",
                },
                json={
                    "display_name": "Scope Guard Partners",
                    "owner_admin_user_id": str(owner_operator.id),
                },
            )
            assert create_response.status_code == 201
            workspace_id = create_response.json()["id"]

            owner_token = await _login(async_client, "scope-owner@example.com", "ScopeOwnerP@ssword123!")
            analyst_add_response = await async_client.post(
                f"/api/v1/partner-workspaces/{workspace_id}/members",
                headers={
                    "Authorization": f"Bearer {owner_token}",
                    "X-Auth-Realm": "admin",
                },
                json={
                    "admin_user_id": str(analyst_operator.id),
                    "role_key": "analyst",
                },
            )
            assert analyst_add_response.status_code == 201

            analyst_token = await _login(async_client, "scope-analyst@example.com", "ScopeAnalystP@ssword123!")
            analyst_detail = await async_client.get(
                f"/api/v1/partner-workspaces/{workspace_id}",
                headers={
                    "Authorization": f"Bearer {analyst_token}",
                    "X-Auth-Realm": "admin",
                },
            )
            assert analyst_detail.status_code == 200
            assert analyst_detail.json()["current_role_key"] == "analyst"

            analyst_add_attempt = await async_client.post(
                f"/api/v1/partner-workspaces/{workspace_id}/members",
                headers={
                    "Authorization": f"Bearer {analyst_token}",
                    "X-Auth-Realm": "admin",
                },
                json={
                    "admin_user_id": str(outsider_operator.id),
                    "role_key": "support_manager",
                },
            )
            assert analyst_add_attempt.status_code == 403

            outsider_token = await _login(async_client, "scope-outsider@example.com", "ScopeOutsiderP@ssword123!")
            outsider_detail = await async_client.get(
                f"/api/v1/partner-workspaces/{workspace_id}",
                headers={
                    "Authorization": f"Bearer {outsider_token}",
                    "X-Auth-Realm": "admin",
                },
            )
            assert outsider_detail.status_code == 403
    finally:
        app.dependency_overrides.pop(get_redis, None)
        engine.dispose()
        cleanup_sqlite_file(sqlite_path)
