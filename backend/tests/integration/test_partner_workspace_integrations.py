from __future__ import annotations

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

pytestmark = [pytest.mark.integration]


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


async def _create_workspace(
    async_client: AsyncClient,
    *,
    admin_headers: dict[str, str],
    owner_admin_user_id: str,
) -> str:
    response = await async_client.post(
        "/api/v1/admin/partner-workspaces",
        headers=admin_headers,
        json={
            "display_name": "Integration Workspace",
            "owner_admin_user_id": owner_admin_user_id,
        },
    )
    assert response.status_code == 201
    return response.json()["id"]


@pytest.mark.asyncio
async def test_partner_workspace_integration_credentials_and_reporting_snapshot(
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
                await _create_admin_user(
                    session=db,
                    auth_service=auth_service,
                    auth_realm_id=admin_realm.id,
                    login="integrations_admin",
                    email="integrations-admin@example.com",
                    password="IntegrationsAdmin123!",
                    role="admin",
                )
                owner_user = await _create_admin_user(
                    session=db,
                    auth_service=auth_service,
                    auth_realm_id=admin_realm.id,
                    login="integrations_owner",
                    email="integrations-owner@example.com",
                    password="IntegrationsOwner123!",
                    role="viewer",
                )

            admin_token = await _login(async_client, "integrations-admin@example.com", "IntegrationsAdmin123!")
            owner_token = await _login(async_client, "integrations-owner@example.com", "IntegrationsOwner123!")

            admin_headers = {"Authorization": f"Bearer {admin_token}", "X-Auth-Realm": "admin"}
            owner_headers = {"Authorization": f"Bearer {owner_token}", "X-Auth-Realm": "admin"}

            workspace_id = await _create_workspace(
                async_client,
                admin_headers=admin_headers,
                owner_admin_user_id=str(owner_user.id),
            )

            credentials_response = await async_client.get(
                f"/api/v1/partner-workspaces/{workspace_id}/integration-credentials",
                headers=owner_headers,
            )
            assert credentials_response.status_code == 200
            assert credentials_response.json() == []

            reporting_rotate_response = await async_client.post(
                (
                    f"/api/v1/partner-workspaces/{workspace_id}/integration-credentials/"
                    "reporting_api_token/rotate"
                ),
                headers=owner_headers,
                json={"credential_metadata": {"surface": "partner_portal"}},
            )
            assert reporting_rotate_response.status_code == 200
            reporting_payload = reporting_rotate_response.json()
            assert reporting_payload["credential"]["kind"] == "reporting_api_token"
            assert reporting_payload["credential"]["status"] == "ready"
            assert reporting_payload["issued_secret"].startswith("rpt_")

            postback_rotate_response = await async_client.post(
                (
                    f"/api/v1/partner-workspaces/{workspace_id}/integration-credentials/"
                    "postback_secret/rotate"
                ),
                headers=owner_headers,
                json={"destination_ref": "https://partner.example.com/postback"},
            )
            assert postback_rotate_response.status_code == 200
            postback_payload = postback_rotate_response.json()
            assert postback_payload["credential"]["kind"] == "postback_secret"
            assert postback_payload["issued_secret"].startswith("pbs_")

            listed_credentials_response = await async_client.get(
                f"/api/v1/partner-workspaces/{workspace_id}/integration-credentials",
                headers=owner_headers,
            )
            assert listed_credentials_response.status_code == 200
            listed_credentials = listed_credentials_response.json()
            assert {item["kind"] for item in listed_credentials} == {
                "reporting_api_token",
                "postback_secret",
            }

            delivery_logs_response = await async_client.get(
                f"/api/v1/partner-workspaces/{workspace_id}/integration-delivery-logs",
                headers=owner_headers,
            )
            assert delivery_logs_response.status_code == 200
            delivery_logs = delivery_logs_response.json()
            assert {item["channel"] for item in delivery_logs} == {"reporting_export", "postback"}

            readiness_response = await async_client.get(
                f"/api/v1/partner-workspaces/{workspace_id}/postback-readiness",
                headers=owner_headers,
            )
            assert readiness_response.status_code == 200
            readiness_payload = readiness_response.json()
            assert readiness_payload["status"] == "complete"
            assert readiness_payload["delivery_status"] == "paused"

            reporting_snapshot_response = await async_client.get(
                f"/api/v1/reporting/partner-workspaces/{workspace_id}/snapshot",
                headers={"Authorization": f"Bearer {reporting_payload['issued_secret']}"},
            )
            assert reporting_snapshot_response.status_code == 200
            snapshot_payload = reporting_snapshot_response.json()
            assert snapshot_payload["workspace_id"] == workspace_id
            assert snapshot_payload["workspace_key"]
            assert isinstance(snapshot_payload["consumer_health_views"], list)
            assert {item["channel"] for item in snapshot_payload["delivery_logs"]} == {
                "reporting_export",
                "postback",
            }

            mismatched_snapshot_response = await async_client.get(
                f"/api/v1/reporting/partner-workspaces/{uuid.uuid4()}/snapshot",
                headers={"Authorization": f"Bearer {reporting_payload['issued_secret']}"},
            )
            assert mismatched_snapshot_response.status_code == 403
    finally:
        app.dependency_overrides.pop(get_redis, None)
        cleanup_sqlite_file(sqlite_path)
