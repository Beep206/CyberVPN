import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from src.application.services.auth_service import AuthService
from src.infrastructure.cache.redis_client import get_redis
from src.infrastructure.database.models.admin_user_model import AdminUserModel
from src.infrastructure.database.models.principal_session_model import PrincipalSessionModel
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


@pytest.mark.integration
async def test_admin_login_issues_realm_aware_cookies_and_principal_session() -> None:
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

                user = AdminUserModel(
                    login="realm_session_admin",
                    email="realm-session@example.com",
                    auth_realm_id=admin_realm.id,
                    password_hash=await auth_service.hash_password("RealmSessionP@ssword123!"),
                    role="admin",
                    is_active=True,
                    is_email_verified=True,
                )
                db.add(user)
                db.commit()
                user_id = user.id
                audience = admin_realm.audience
                realm_id = admin_realm.id

            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="https://admin.cyber-vpn.net",
            ) as client:
                resolve_response = await client.get("/api/v1/realms/resolve", headers={"X-Auth-Realm": "admin"})
                assert resolve_response.status_code == 200
                assert resolve_response.json()["realm"]["audience"] == audience

                login_response = await client.post(
                    "/api/v1/auth/login",
                    json={"login_or_email": "realm-session@example.com", "password": "RealmSessionP@ssword123!"},
                )
                assert login_response.status_code == 200
                login_payload = login_response.json()
                assert "access_token" not in login_payload
                assert "refresh_token" not in login_payload
                assert login_payload["auth_realm_id"] == str(realm_id)
                assert login_payload["auth_realm_key"] == "admin"
                assert login_payload["audience"] == audience
                assert login_payload["principal_type"] == "admin"
                assert login_payload["scope_family"] == "admin"

                access_cookie = client.cookies.get("access_token")
                refresh_cookie = client.cookies.get("refresh_token")
                assert access_cookie is not None
                assert refresh_cookie is not None

            access_claims = auth_service.decode_token(access_cookie, audience=audience)
            assert access_claims["aud"] == audience
            assert access_claims["realm_key"] == "admin"
            assert access_claims["principal_type"] == "admin"

            with sessionmaker() as db:
                sessions_result = await SyncSessionAdapter(db).execute(
                    select(PrincipalSessionModel).where(PrincipalSessionModel.principal_subject == str(user_id))
                )
                sessions = list(sessions_result.scalars().all())
                assert len(sessions) == 1
                assert sessions[0].auth_realm_id == realm_id
                assert sessions[0].audience == audience
                assert sessions[0].scope_family == "admin"
                assert sessions[0].status == "active"

            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="https://admin.cyber-vpn.net",
                cookies={"access_token": access_cookie, "refresh_token": refresh_cookie},
            ) as refresh_client:
                refresh_response = await refresh_client.post("/api/v1/auth/refresh", json={})
                assert refresh_response.status_code == 200
                refresh_payload = refresh_response.json()
                assert refresh_payload["auth_realm_id"] == str(realm_id)
                assert refresh_payload["auth_realm_key"] == "admin"
                assert refresh_payload["audience"] == audience
                assert refresh_payload["principal_type"] == "admin"
                assert refresh_payload["scope_family"] == "admin"

                refreshed_claims = auth_service.decode_token(refresh_payload["access_token"], audience=audience)
                assert refreshed_claims["realm_id"] == str(realm_id)
                assert refreshed_claims["principal_type"] == "admin"

            with sessionmaker() as db:
                sessions_result = await SyncSessionAdapter(db).execute(
                    select(PrincipalSessionModel)
                    .where(PrincipalSessionModel.principal_subject == str(user_id))
                    .order_by(PrincipalSessionModel.issued_at.asc())
                )
                rotated_sessions = list(sessions_result.scalars().all())
                assert len(rotated_sessions) == 2
                assert rotated_sessions[0].status == "revoked"
                assert rotated_sessions[1].status == "active"
    finally:
        app.dependency_overrides.pop(get_redis, None)
        engine.dispose()
        cleanup_sqlite_file(sqlite_path)


@pytest.mark.integration
async def test_admin_logout_revokes_realm_session_and_access_token() -> None:
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

                user = AdminUserModel(
                    login="realm_logout_admin",
                    email="realm-logout@example.com",
                    auth_realm_id=admin_realm.id,
                    password_hash=await auth_service.hash_password("RealmLogoutP@ssword123!"),
                    role="admin",
                    is_active=True,
                    is_email_verified=True,
                )
                db.add(user)
                db.commit()
                user_id = user.id
                realm_id = admin_realm.id

            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="https://admin.cyber-vpn.net",
            ) as client:
                login_response = await client.post(
                    "/api/v1/auth/login",
                    json={"login_or_email": "realm-logout@example.com", "password": "RealmLogoutP@ssword123!"},
                )
                assert login_response.status_code == 200
                access_token = client.cookies.get("access_token")
                assert access_token is not None

                session_response = await client.get("/api/v1/auth/session")
                assert session_response.status_code == 200

                logout_response = await client.post("/api/v1/auth/logout")
                assert logout_response.status_code == 204

                stale_access_response = await client.get(
                    "/api/v1/auth/session",
                    headers={"Authorization": f"Bearer {access_token}"},
                )
                assert stale_access_response.status_code == 401

            with sessionmaker() as db:
                sessions_result = await SyncSessionAdapter(db).execute(
                    select(PrincipalSessionModel).where(PrincipalSessionModel.principal_subject == str(user_id))
                )
                sessions = list(sessions_result.scalars().all())
                assert len(sessions) == 1
                assert sessions[0].auth_realm_id == realm_id
                assert sessions[0].status == "revoked"
                assert sessions[0].revoked_at is not None
    finally:
        app.dependency_overrides.pop(get_redis, None)
        engine.dispose()
        cleanup_sqlite_file(sqlite_path)


@pytest.mark.integration
async def test_partner_login_issues_partner_realm_cookies_and_session() -> None:
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
                partner_realm = await realm_repo.get_or_create_default_realm("partner")

                user = AdminUserModel(
                    login="realm_partner_operator",
                    email="partner-session@example.com",
                    auth_realm_id=partner_realm.id,
                    password_hash=await auth_service.hash_password("RealmPartnerP@ssword123!"),
                    role="operator",
                    is_active=True,
                    is_email_verified=True,
                )
                db.add(user)
                db.commit()
                user_id = user.id
                audience = partner_realm.audience
                realm_id = partner_realm.id

            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="https://partner.cyber-vpn.net",
            ) as client:
                resolve_response = await client.get("/api/v1/realms/resolve", headers={"X-Auth-Realm": "partner"})
                assert resolve_response.status_code == 200
                assert resolve_response.json()["realm"]["audience"] == audience

                login_response = await client.post(
                    "/api/v1/auth/login",
                    json={"login_or_email": "partner-session@example.com", "password": "RealmPartnerP@ssword123!"},
                )
                assert login_response.status_code == 200
                login_payload = login_response.json()
                assert "access_token" not in login_payload
                assert "refresh_token" not in login_payload
                assert login_payload["auth_realm_id"] == str(realm_id)
                assert login_payload["auth_realm_key"] == "partner"
                assert login_payload["audience"] == audience
                assert login_payload["principal_type"] == "partner_operator"
                assert login_payload["scope_family"] == "partner"

                set_cookie_headers = login_response.headers.get_list("set-cookie")
                assert "partner_access_token=" in "\n".join(set_cookie_headers)
                assert "partner_refresh_token=" in "\n".join(set_cookie_headers)

                access_cookie = client.cookies.get("partner_access_token")
                assert access_cookie is not None
                access_claims = auth_service.decode_token(access_cookie, audience=audience)
                assert access_claims["aud"] == audience
                assert access_claims["realm_key"] == "partner"
                assert access_claims["principal_type"] == "partner_operator"

                session_response = await client.get("/api/v1/auth/session")
                assert session_response.status_code == 200
                session_payload = session_response.json()
                assert session_payload["auth_realm_id"] == str(realm_id)
                assert session_payload["auth_realm_key"] == "partner"
                assert session_payload["audience"] == audience
                assert session_payload["principal_type"] == "partner_operator"
                assert session_payload["scope_family"] == "partner"
                assert session_payload["login"] == "realm_partner_operator"

                refresh_response = await client.post("/api/v1/auth/refresh", json={})
                assert refresh_response.status_code == 200
                refresh_payload = refresh_response.json()
                assert refresh_payload["auth_realm_id"] == str(realm_id)
                assert refresh_payload["auth_realm_key"] == "partner"
                assert refresh_payload["audience"] == audience
                assert refresh_payload["principal_type"] == "partner_operator"
                assert refresh_payload["scope_family"] == "partner"

                refreshed_claims = auth_service.decode_token(refresh_payload["access_token"], audience=audience)
                assert refreshed_claims["realm_id"] == str(realm_id)
                assert refreshed_claims["principal_type"] == "partner_operator"

            with sessionmaker() as db:
                sessions_result = await SyncSessionAdapter(db).execute(
                    select(PrincipalSessionModel)
                    .where(PrincipalSessionModel.principal_subject == str(user_id))
                    .order_by(PrincipalSessionModel.issued_at.asc())
                )
                sessions = list(sessions_result.scalars().all())
                assert len(sessions) == 2
                assert sessions[0].status == "revoked"
                assert sessions[1].status == "active"
                assert sessions[1].auth_realm_id == realm_id
                assert sessions[1].audience == audience
                assert sessions[1].scope_family == "partner"
                assert sessions[1].principal_class == "partner_operator"
    finally:
        app.dependency_overrides.pop(get_redis, None)
        engine.dispose()
        cleanup_sqlite_file(sqlite_path)


@pytest.mark.integration
async def test_customer_http_login_hides_tokens_and_establishes_browser_session(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    auth_service = AuthService()
    fake_redis = FakeRedis()
    sessionmaker, engine, sqlite_path = create_realm_test_sessionmaker()
    await initialize_realm_test_database(engine)

    monkeypatch.setattr("src.presentation.api.v1.auth.cookies.settings.environment", "production")
    monkeypatch.setattr("src.presentation.api.v1.auth.cookies.settings.cookie_secure", True)
    monkeypatch.setattr("src.presentation.api.v1.auth.cookies.settings.cookie_domain", "cyber-vpn.net")

    async def _override_redis():
        yield fake_redis

    app.dependency_overrides[get_redis] = _override_redis

    try:
        async with override_realm_test_db(sessionmaker):
            with sessionmaker() as db:
                realm_repo = AuthRealmRepository(SyncSessionAdapter(db))
                customer_realm = await realm_repo.get_or_create_default_realm("customer")

                user = AdminUserModel(
                    login="realm_customer_user",
                    email="customer-session@example.com",
                    auth_realm_id=customer_realm.id,
                    password_hash=await auth_service.hash_password("RealmCustomerP@ssword123!"),
                    role="viewer",
                    is_active=True,
                    is_email_verified=True,
                )
                db.add(user)
                db.commit()
                audience = customer_realm.audience
                realm_id = customer_realm.id

            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://127.0.0.1:13000",
            ) as client:
                login_response = await client.post(
                    "/api/v1/auth/login",
                    headers={"Origin": "http://127.0.0.1:13000"},
                    json={"login_or_email": "customer-session@example.com", "password": "RealmCustomerP@ssword123!"},
                )
                assert login_response.status_code == 200
                login_payload = login_response.json()
                assert "access_token" not in login_payload
                assert "refresh_token" not in login_payload
                assert login_payload["auth_realm_id"] == str(realm_id)
                assert login_payload["auth_realm_key"] == "customer"
                assert login_payload["audience"] == audience
                assert login_payload["principal_type"] == "customer"
                assert login_payload["scope_family"] == "customer"

                set_cookie_headers = login_response.headers.get_list("set-cookie")
                joined_headers = "\n".join(set_cookie_headers)
                assert "customer_access_token=" in joined_headers
                assert "customer_refresh_token=" in joined_headers
                assert "Secure" not in joined_headers
                assert "Domain=" not in joined_headers

                session_response = await client.get("/api/v1/auth/session")
                assert session_response.status_code == 200
                session_payload = session_response.json()
                assert session_payload["auth_realm_id"] == str(realm_id)
                assert session_payload["auth_realm_key"] == "customer"
                assert session_payload["audience"] == audience
                assert session_payload["principal_type"] == "customer"
                assert session_payload["scope_family"] == "customer"
                assert session_payload["login"] == "realm_customer_user"
    finally:
        app.dependency_overrides.pop(get_redis, None)
        engine.dispose()
        cleanup_sqlite_file(sqlite_path)
