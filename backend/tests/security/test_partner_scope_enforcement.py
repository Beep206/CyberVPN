import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy import select

from src.application.services.auth_service import AuthService
from src.config.settings import settings
from src.infrastructure.cache.redis_client import get_redis
from src.infrastructure.database.models.admin_user_model import AdminUserModel
from src.infrastructure.database.models.partner_model import PartnerAccountModel, PartnerCodeLinkModel, PartnerCodeModel
from src.infrastructure.database.repositories.auth_realm_repo import AuthRealmRepository
from src.main import app
from tests.helpers.realm_auth import (
    FakeRedis,
    SyncSessionAdapter,
    cleanup_sqlite_file,
    create_realm_test_sessionmaker,
    fresh_auth_headers,
    initialize_realm_test_database,
    override_realm_test_db,
)

ADMIN_AUTH_HOST = "admin.cyber-vpn.net"
PARTNER_AUTH_HOST = "portal.localhost"


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
    realm: str,
) -> str:
    response = await async_client.post(
        "/api/v1/auth/login",
        headers={"Host": ADMIN_AUTH_HOST if realm == "admin" else PARTNER_AUTH_HOST},
        json={"login_or_email": login_or_email, "password": password},
    )
    assert response.status_code == 200
    cookie_name = "access_token" if realm == "admin" else f"{realm}_access_token"
    return response.cookies[cookie_name]


def _auth_headers(token: str, *, realm: str, host: str) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {token}",
        "X-Auth-Realm": realm,
        "Host": host,
    }


@pytest.mark.security
@pytest.mark.integration
async def test_partner_workspace_scope_enforcement(
    async_client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "partner_portal_enabled", True)
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
                    login="scope_admin",
                    email="scope-admin@example.com",
                    password="ScopeAdminP@ssword123!",
                    role="admin",
                )
                await _create_admin_user(
                    session=db,
                    auth_service=auth_service,
                    auth_realm_id=partner_realm.id,
                    login="scope_partner_admin",
                    email="scope-partner-admin@example.com",
                    password="ScopePartnerAdminP@ssword123!",
                    role="admin",
                )
                owner_operator = await _create_admin_user(
                    session=db,
                    auth_service=auth_service,
                    auth_realm_id=partner_realm.id,
                    login="scope_owner",
                    email="scope-owner@example.com",
                    password="ScopeOwnerP@ssword123!",
                    role="viewer",
                )
                analyst_operator = await _create_admin_user(
                    session=db,
                    auth_service=auth_service,
                    auth_realm_id=partner_realm.id,
                    login="scope_analyst",
                    email="scope-analyst@example.com",
                    password="ScopeAnalystP@ssword123!",
                    role="viewer",
                )
                traffic_operator = await _create_admin_user(
                    session=db,
                    auth_service=auth_service,
                    auth_realm_id=partner_realm.id,
                    login="scope_traffic",
                    email="scope-traffic@example.com",
                    password="ScopeTrafficP@ssword123!",
                    role="viewer",
                )
                outsider_operator = await _create_admin_user(
                    session=db,
                    auth_service=auth_service,
                    auth_realm_id=partner_realm.id,
                    login="scope_outsider",
                    email="scope-outsider@example.com",
                    password="ScopeOutsiderP@ssword123!",
                    role="viewer",
                )

            admin_token = await _login(
                async_client,
                "scope-admin@example.com",
                "ScopeAdminP@ssword123!",
                realm="admin",
            )
            monkeypatch.setattr(settings, "environment", "production")
            misdirected_admin_attempt = await async_client.post(
                "/api/v1/admin/partner-workspaces",
                headers={
                    "Authorization": f"Bearer {admin_token}",
                    "Host": "partner.cyber-vpn.net",
                    "X-Auth-Realm": "admin",
                },
                json={
                    "display_name": "Spoofed Admin Workspace",
                    "owner_admin_user_id": str(owner_operator.id),
                },
            )
            assert misdirected_admin_attempt.status_code in {403, 404, 421}
            with sessionmaker() as db:
                spoofed_workspace = db.scalar(
                    select(PartnerAccountModel).where(PartnerAccountModel.display_name == "Spoofed Admin Workspace")
                )
                assert spoofed_workspace is None
            monkeypatch.setattr(settings, "environment", "test")

            partner_admin_token = await _login(
                async_client,
                "scope-partner-admin@example.com",
                "ScopePartnerAdminP@ssword123!",
                realm="partner",
            )
            partner_admin_attempt = await async_client.post(
                "/api/v1/admin/partner-workspaces",
                headers=_auth_headers(partner_admin_token, realm="partner", host=ADMIN_AUTH_HOST),
                json={
                    "display_name": "Forged Partner Admin Workspace",
                    "owner_admin_user_id": str(owner_operator.id),
                },
            )
            assert partner_admin_attempt.status_code in {401, 403}
            with sessionmaker() as db:
                forged_workspace = db.scalar(
                    select(PartnerAccountModel).where(
                        PartnerAccountModel.display_name == "Forged Partner Admin Workspace",
                    )
                )
                assert forged_workspace is None

            create_response = await async_client.post(
                "/api/v1/admin/partner-workspaces",
                headers=_auth_headers(admin_token, realm="admin", host=ADMIN_AUTH_HOST),
                json={
                    "display_name": "Scope Guard Partners",
                    "owner_admin_user_id": str(owner_operator.id),
                },
            )
            assert create_response.status_code == 201
            workspace_id = create_response.json()["id"]

            admin_realm_partner_detail = await async_client.get(
                f"/api/v1/partner-workspaces/{workspace_id}",
                headers=_auth_headers(admin_token, realm="admin", host=ADMIN_AUTH_HOST),
            )
            assert admin_realm_partner_detail.status_code == 403

            admin_realm_partner_code_attempt = await async_client.post(
                f"/api/v1/partner-workspaces/{workspace_id}/codes",
                headers=_auth_headers(admin_token, realm="admin", host=ADMIN_AUTH_HOST),
                json={
                    "code": "ADMINREALM42",
                    "destination_path": "/pricing",
                },
            )
            assert admin_realm_partner_code_attempt.status_code == 403
            with sessionmaker() as db:
                admin_realm_code = db.scalar(
                    select(PartnerCodeModel).where(PartnerCodeModel.code_normalized == "ADMINREALM42")
                )
                assert admin_realm_code is None

            partner_realm_admin_without_membership_detail = await async_client.get(
                f"/api/v1/partner-workspaces/{workspace_id}",
                headers=_auth_headers(partner_admin_token, realm="partner", host=PARTNER_AUTH_HOST),
            )
            assert partner_realm_admin_without_membership_detail.status_code == 403

            owner_token = await _login(
                async_client,
                "scope-owner@example.com",
                "ScopeOwnerP@ssword123!",
                realm="partner",
            )
            analyst_add_response = await async_client.post(
                f"/api/v1/partner-workspaces/{workspace_id}/members",
                headers=await fresh_auth_headers(
                    fake_redis=fake_redis,
                    base_headers=_auth_headers(owner_token, realm="partner", host=PARTNER_AUTH_HOST),
                    user=owner_operator,
                    auth_realm_id=partner_realm.id,
                    realm_key="partner",
                    action=f"partner.member.create:{workspace_id}",
                    principal_class="partner_operator",
                ),
                json={
                    "admin_user_id": str(analyst_operator.id),
                    "role_key": "analyst",
                },
            )
            assert analyst_add_response.status_code == 201

            traffic_add_response = await async_client.post(
                f"/api/v1/partner-workspaces/{workspace_id}/members",
                headers=await fresh_auth_headers(
                    fake_redis=fake_redis,
                    base_headers=_auth_headers(owner_token, realm="partner", host=PARTNER_AUTH_HOST),
                    user=owner_operator,
                    auth_realm_id=partner_realm.id,
                    realm_key="partner",
                    action=f"partner.member.create:{workspace_id}",
                    principal_class="partner_operator",
                ),
                json={
                    "admin_user_id": str(traffic_operator.id),
                    "role_key": "traffic_manager",
                },
            )
            assert traffic_add_response.status_code == 201

            analyst_token = await _login(
                async_client,
                "scope-analyst@example.com",
                "ScopeAnalystP@ssword123!",
                realm="partner",
            )
            traffic_token = await _login(
                async_client,
                "scope-traffic@example.com",
                "ScopeTrafficP@ssword123!",
                realm="partner",
            )
            analyst_detail = await async_client.get(
                f"/api/v1/partner-workspaces/{workspace_id}",
                headers=_auth_headers(analyst_token, realm="partner", host=PARTNER_AUTH_HOST),
            )
            assert analyst_detail.status_code == 200
            assert analyst_detail.json()["current_role_key"] == "analyst"

            monkeypatch.setattr(settings, "environment", "development")
            local_partner_detail = await async_client.get(
                f"/api/v1/partner-workspaces/{workspace_id}",
                headers={
                    "Authorization": f"Bearer {analyst_token}",
                    "Host": "testserver",
                    "X-Auth-Realm": "partner",
                },
            )
            assert local_partner_detail.status_code == 200
            assert local_partner_detail.json()["current_role_key"] == "analyst"

            local_without_partner_hint = await async_client.get(
                f"/api/v1/partner-workspaces/{workspace_id}",
                headers={
                    "Authorization": f"Bearer {analyst_token}",
                    "Host": "testserver",
                },
            )
            assert local_without_partner_hint.status_code == 401

            monkeypatch.setattr(settings, "environment", "production")
            production_partner_detail = await async_client.get(
                f"/api/v1/partner-workspaces/{workspace_id}",
                headers={
                    "Authorization": f"Bearer {analyst_token}",
                    "Host": "partner.cyber-vpn.net",
                },
            )
            assert production_partner_detail.status_code == 200
            assert production_partner_detail.json()["current_role_key"] == "analyst"

            production_spoofed_partner_hint = await async_client.get(
                f"/api/v1/partner-workspaces/{workspace_id}",
                headers={
                    "Authorization": f"Bearer {analyst_token}",
                    "Host": ADMIN_AUTH_HOST,
                    "X-Auth-Realm": "partner",
                },
            )
            assert production_spoofed_partner_hint.status_code in {401, 403}
            monkeypatch.setattr(settings, "environment", "test")

            owner_code_response = await async_client.post(
                f"/api/v1/partner-workspaces/{workspace_id}/codes",
                headers=_auth_headers(owner_token, realm="partner", host=PARTNER_AUTH_HOST),
                json={
                    "code": "SCOPEWRITE42",
                    "destination_path": "/pricing",
                },
            )
            assert owner_code_response.status_code == 201
            code_id = owner_code_response.json()["id"]
            with sessionmaker() as db:
                existing_links = (
                    db.execute(
                        select(PartnerCodeLinkModel).where(
                            PartnerCodeLinkModel.partner_code_id == uuid.UUID(code_id),
                        )
                    )
                    .scalars()
                    .all()
                )
                initial_link_count = len(existing_links)

            traffic_update_response = await async_client.patch(
                f"/api/v1/partner-workspaces/{workspace_id}/codes/{code_id}",
                headers=_auth_headers(traffic_token, realm="partner", host=PARTNER_AUTH_HOST),
                json={"destination_path": "/docs"},
            )
            assert traffic_update_response.status_code == 200
            assert traffic_update_response.json()["destination_path"] == "/docs"
            with sessionmaker() as db:
                code_after_traffic_update = db.get(PartnerCodeModel, uuid.UUID(code_id))
                assert code_after_traffic_update is not None
                contract_id_after_traffic_update = code_after_traffic_update.commission_contract_id
                version_after_traffic_update = code_after_traffic_update.version
                assert code_after_traffic_update.markup_pct == 0

            traffic_markup_update_response = await async_client.patch(
                f"/api/v1/partner-workspaces/{workspace_id}/codes/{code_id}",
                headers=_auth_headers(traffic_token, realm="partner", host=PARTNER_AUTH_HOST),
                json={"markup_pct": 12.5},
            )
            assert traffic_markup_update_response.status_code == 403

            traffic_markup_create_response = await async_client.post(
                f"/api/v1/partner-workspaces/{workspace_id}/codes",
                headers=_auth_headers(traffic_token, realm="partner", host=PARTNER_AUTH_HOST),
                json={
                    "code": "SCOPEMARKUP42",
                    "destination_path": "/pricing",
                    "markup_pct": 7.5,
                },
            )
            assert traffic_markup_create_response.status_code == 403
            with sessionmaker() as db:
                code_after_denied_markup = db.get(PartnerCodeModel, uuid.UUID(code_id))
                assert code_after_denied_markup is not None
                assert code_after_denied_markup.markup_pct == 0
                assert code_after_denied_markup.commission_contract_id == contract_id_after_traffic_update
                assert code_after_denied_markup.version == version_after_traffic_update
                forbidden_code = db.scalar(
                    select(PartnerCodeModel).where(PartnerCodeModel.code_normalized == "SCOPEMARKUP42")
                )
                assert forbidden_code is None

            analyst_codes_response = await async_client.get(
                f"/api/v1/partner-workspaces/{workspace_id}/codes",
                headers=_auth_headers(analyst_token, realm="partner", host=PARTNER_AUTH_HOST),
            )
            assert analyst_codes_response.status_code == 200
            assert analyst_codes_response.json()[0]["id"] == code_id

            analyst_link_attempt = await async_client.post(
                f"/api/v1/partner-workspaces/{workspace_id}/codes/{code_id}/links",
                headers=_auth_headers(analyst_token, realm="partner", host=PARTNER_AUTH_HOST),
                json={"destination_path": "/pricing", "campaign_params": {"utm_source": "analyst"}},
            )
            assert analyst_link_attempt.status_code == 403

            analyst_qr_attempt = await async_client.post(
                f"/api/v1/partner-workspaces/{workspace_id}/codes/{code_id}/qr",
                headers=_auth_headers(analyst_token, realm="partner", host=PARTNER_AUTH_HOST),
                json={"destination_path": "/pricing", "size": 128},
            )
            assert analyst_qr_attempt.status_code == 403

            with sessionmaker() as db:
                links_after_denied_attempts = (
                    db.execute(
                        select(PartnerCodeLinkModel).where(
                            PartnerCodeLinkModel.partner_code_id == uuid.UUID(code_id),
                        )
                    )
                    .scalars()
                    .all()
                )
                assert len(links_after_denied_attempts) == initial_link_count

            analyst_add_attempt = await async_client.post(
                f"/api/v1/partner-workspaces/{workspace_id}/members",
                headers=_auth_headers(analyst_token, realm="partner", host=PARTNER_AUTH_HOST),
                json={
                    "admin_user_id": str(outsider_operator.id),
                    "role_key": "support_manager",
                },
            )
            assert analyst_add_attempt.status_code == 403

            outsider_token = await _login(
                async_client,
                "scope-outsider@example.com",
                "ScopeOutsiderP@ssword123!",
                realm="partner",
            )
            outsider_detail = await async_client.get(
                f"/api/v1/partner-workspaces/{workspace_id}",
                headers=_auth_headers(outsider_token, realm="partner", host=PARTNER_AUTH_HOST),
            )
            assert outsider_detail.status_code == 403
    finally:
        app.dependency_overrides.pop(get_redis, None)
        engine.dispose()
        cleanup_sqlite_file(sqlite_path)
