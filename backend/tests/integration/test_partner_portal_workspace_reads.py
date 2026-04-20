from __future__ import annotations

import uuid
from datetime import UTC, datetime
from decimal import Decimal

import pytest
from httpx import AsyncClient

from src.application.services.auth_service import AuthService
from src.infrastructure.cache.redis_client import get_redis
from src.infrastructure.database.models.admin_user_model import AdminUserModel
from src.infrastructure.database.models.partner_model import PartnerCodeModel
from src.infrastructure.database.models.partner_statement_model import PartnerStatementModel
from src.infrastructure.database.models.settlement_period_model import SettlementPeriodModel
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
            "display_name": "Portal Workspace",
            "owner_admin_user_id": owner_admin_user_id,
        },
    )
    assert response.status_code == 201
    return response.json()["id"]


@pytest.mark.asyncio
async def test_partner_workspace_codes_and_statements_are_visible_to_workspace_members(
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
                    login="portal_admin",
                    email="portal-admin@example.com",
                    password="PortalAdmin123!",
                    role="admin",
                )
                owner_user = await _create_admin_user(
                    session=db,
                    auth_service=auth_service,
                    auth_realm_id=admin_realm.id,
                    login="portal_owner",
                    email="portal-owner@example.com",
                    password="PortalOwner123!",
                    role="viewer",
                )
                await _create_admin_user(
                    session=db,
                    auth_service=auth_service,
                    auth_realm_id=admin_realm.id,
                    login="portal_outsider",
                    email="portal-outsider@example.com",
                    password="PortalOutsider123!",
                    role="viewer",
                )

            admin_token = await _login(async_client, "portal-admin@example.com", "PortalAdmin123!")
            owner_token = await _login(async_client, "portal-owner@example.com", "PortalOwner123!")
            outsider_token = await _login(async_client, "portal-outsider@example.com", "PortalOutsider123!")

            admin_headers = {"Authorization": f"Bearer {admin_token}", "X-Auth-Realm": "admin"}
            owner_headers = {"Authorization": f"Bearer {owner_token}", "X-Auth-Realm": "admin"}
            outsider_headers = {"Authorization": f"Bearer {outsider_token}", "X-Auth-Realm": "admin"}

            workspace_id = await _create_workspace(
                async_client,
                admin_headers=admin_headers,
                owner_admin_user_id=str(owner_user.id),
            )

            with sessionmaker() as db:
                settlement_period = SettlementPeriodModel(
                    id=uuid.uuid4(),
                    partner_account_id=uuid.UUID(workspace_id),
                    period_key="2026-04",
                    period_status="closed",
                    currency_code="USD",
                    window_start=datetime(2026, 4, 1, tzinfo=UTC),
                    window_end=datetime(2026, 5, 1, tzinfo=UTC),
                )
                statement = PartnerStatementModel(
                    id=uuid.uuid4(),
                    partner_account_id=uuid.UUID(workspace_id),
                    settlement_period_id=settlement_period.id,
                    statement_key="portal-workspace-2026-04-v1",
                    statement_version=1,
                    statement_status="closed",
                    currency_code="USD",
                    accrual_amount=Decimal("125.00"),
                    on_hold_amount=Decimal("15.00"),
                    reserve_amount=Decimal("10.00"),
                    adjustment_net_amount=Decimal("0.00"),
                    available_amount=Decimal("100.00"),
                    source_event_count=4,
                    held_event_count=1,
                    active_reserve_count=1,
                    adjustment_count=0,
                    statement_snapshot={"source": "portal-test"},
                )
                code = PartnerCodeModel(
                    id=uuid.uuid4(),
                    partner_account_id=uuid.UUID(workspace_id),
                    partner_user_id=uuid.uuid4(),
                    code="PORTAL42",
                    markup_pct=Decimal("15.00"),
                    is_active=True,
                )
                db.add_all([settlement_period, statement, code])
                db.commit()

            workspace_response = await async_client.get(
                f"/api/v1/partner-workspaces/{workspace_id}",
                headers=owner_headers,
            )
            assert workspace_response.status_code == 200
            assert workspace_response.json()["current_role_key"] == "owner"

            codes_response = await async_client.get(
                f"/api/v1/partner-workspaces/{workspace_id}/codes",
                headers=owner_headers,
            )
            assert codes_response.status_code == 200
            codes_payload = codes_response.json()
            assert len(codes_payload) == 1
            assert codes_payload[0]["code"] == "PORTAL42"
            assert codes_payload[0]["partner_account_id"] == workspace_id

            statements_response = await async_client.get(
                f"/api/v1/partner-workspaces/{workspace_id}/statements",
                headers=owner_headers,
            )
            assert statements_response.status_code == 200
            statements_payload = statements_response.json()
            assert len(statements_payload) == 1
            assert statements_payload[0]["statement_key"] == "portal-workspace-2026-04-v1"
            assert statements_payload[0]["partner_account_id"] == workspace_id
            assert statements_payload[0]["available_amount"] == 100.0

            outsider_codes_response = await async_client.get(
                f"/api/v1/partner-workspaces/{workspace_id}/codes",
                headers=outsider_headers,
            )
            assert outsider_codes_response.status_code == 403

            outsider_statements_response = await async_client.get(
                f"/api/v1/partner-workspaces/{workspace_id}/statements",
                headers=outsider_headers,
            )
            assert outsider_statements_response.status_code == 403
    finally:
        app.dependency_overrides.pop(get_redis, None)
        engine.dispose()
        cleanup_sqlite_file(sqlite_path)
