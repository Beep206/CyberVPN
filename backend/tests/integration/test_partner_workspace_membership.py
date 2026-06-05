import pytest
from httpx import AsyncClient

from src.application.services.auth_service import AuthService
from src.infrastructure.cache.redis_client import get_redis
from src.infrastructure.database.models.admin_user_model import AdminUserModel
from src.infrastructure.database.repositories.auth_realm_repo import AuthRealmRepository
from src.main import app
from tests.helpers.realm_auth import (
    ADMIN_AUTH_REALM_HEADERS,
    PARTNER_ACCESS_COOKIE_NAME,
    PARTNER_AUTH_REALM_HEADERS,
    FakeRedis,
    SyncSessionAdapter,
    access_token_from_client_cookies,
    cleanup_sqlite_file,
    create_realm_test_sessionmaker,
    fresh_auth_headers,
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


async def _login(
    async_client: AsyncClient,
    login_or_email: str,
    password: str,
    *,
    headers: dict[str, str] = ADMIN_AUTH_REALM_HEADERS,
    cookie_name: str = "access_token",
) -> str:
    response = await async_client.post(
        "/api/v1/auth/login",
        headers=headers,
        json={"login_or_email": login_or_email, "password": password},
    )
    assert response.status_code == 200
    return access_token_from_client_cookies(async_client, cookie_name=cookie_name, response=response)


@pytest.mark.integration
async def test_partner_workspace_membership_flow(async_client: AsyncClient) -> None:
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
                partner_realm = await realm_repo.get_or_create_default_realm("partner")

                await _create_admin_user(
                    session=db,
                    auth_service=auth_service,
                    auth_realm_id=admin_realm.id,
                    login="workspace_admin",
                    email="workspace-admin@example.com",
                    password="WorkspaceAdminP@ssword123!",
                    role="admin",
                )
                owner_operator = await _create_admin_user(
                    session=db,
                    auth_service=auth_service,
                    auth_realm_id=partner_realm.id,
                    login="workspace_owner",
                    email="workspace-owner@example.com",
                    password="WorkspaceOwnerP@ssword123!",
                    role="viewer",
                )
                finance_operator = await _create_admin_user(
                    session=db,
                    auth_service=auth_service,
                    auth_realm_id=partner_realm.id,
                    login="workspace_finance",
                    email="workspace-finance@example.com",
                    password="WorkspaceFinanceP@ssword123!",
                    role="viewer",
                )

            admin_token = await _login(async_client, "workspace-admin@example.com", "WorkspaceAdminP@ssword123!")
            create_response = await async_client.post(
                "/api/v1/admin/partner-workspaces",
                headers={
                    "Authorization": f"Bearer {admin_token}",
                    **ADMIN_AUTH_REALM_HEADERS,
                },
                json={
                    "display_name": "Nebula Partners",
                    "owner_admin_user_id": str(owner_operator.id),
                },
            )
            assert create_response.status_code == 201
            workspace_payload = create_response.json()
            workspace_id = workspace_payload["id"]
            assert workspace_payload["account_key"].startswith("nebula-partners")
            assert workspace_payload["members"][0]["admin_user_id"] == str(owner_operator.id)
            assert workspace_payload["members"][0]["role_key"] == "owner"

            owner_token = await _login(
                async_client,
                "workspace-owner@example.com",
                "WorkspaceOwnerP@ssword123!",
                headers=PARTNER_AUTH_REALM_HEADERS,
                cookie_name=PARTNER_ACCESS_COOKIE_NAME,
            )
            owner_workspaces = await async_client.get(
                "/api/v1/partner-workspaces/me",
                headers={
                    "Authorization": f"Bearer {owner_token}",
                    **PARTNER_AUTH_REALM_HEADERS,
                },
            )
            assert owner_workspaces.status_code == 200
            assert len(owner_workspaces.json()) == 1
            assert owner_workspaces.json()[0]["id"] == workspace_id

            add_member_response = await async_client.post(
                f"/api/v1/partner-workspaces/{workspace_id}/members",
                headers=await fresh_auth_headers(
                    fake_redis=fake_redis,
                    base_headers={"Authorization": f"Bearer {owner_token}", **PARTNER_AUTH_REALM_HEADERS},
                    user=owner_operator,
                    auth_realm_id=partner_realm.id,
                    realm_key="partner",
                    principal_class="partner_operator",
                    action=f"partner.member.create:{workspace_id}",
                ),
                json={
                    "admin_user_id": str(finance_operator.id),
                    "role_key": "finance",
                },
            )
            assert add_member_response.status_code == 201
            assert add_member_response.json()["role_key"] == "finance"

            owner_workspace_detail = await async_client.get(
                f"/api/v1/partner-workspaces/{workspace_id}",
                headers={
                    "Authorization": f"Bearer {owner_token}",
                    **PARTNER_AUTH_REALM_HEADERS,
                },
            )
            assert owner_workspace_detail.status_code == 200
            detail_payload = owner_workspace_detail.json()
            assert detail_payload["current_role_key"] == "owner"
            assert "membership_write" in detail_payload["current_permission_keys"]
            assert {member["role_key"] for member in detail_payload["members"]} == {"owner", "finance"}
    finally:
        app.dependency_overrides.pop(get_redis, None)
        engine.dispose()
        cleanup_sqlite_file(sqlite_path)
