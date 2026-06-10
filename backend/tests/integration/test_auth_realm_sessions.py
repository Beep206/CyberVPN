from datetime import UTC, datetime, timedelta
from hashlib import sha256
from uuid import UUID, uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from src.application.services.auth_service import AuthService
from src.infrastructure.cache.redis_client import get_redis
from src.infrastructure.database.models.admin_user_model import AdminUserModel
from src.infrastructure.database.models.principal_session_model import PrincipalSessionModel
from src.infrastructure.database.models.refresh_token_model import RefreshToken
from src.infrastructure.database.models.user_device_model import UserDeviceModel
from src.infrastructure.database.repositories.auth_realm_repo import AuthRealmRepository
from src.main import app
from src.presentation.middleware.rate_limit import RateLimitMiddleware
from tests.helpers.realm_auth import (
    FakeRedis,
    SyncSessionAdapter,
    cleanup_sqlite_file,
    create_realm_test_sessionmaker,
    initialize_realm_test_database,
    override_realm_test_db,
)


@pytest.fixture(autouse=True)
def _disable_rate_limit_middleware_for_realm_session_contract_tests(monkeypatch: pytest.MonkeyPatch):
    async def passthrough(self, request, call_next):
        return await call_next(request)

    monkeypatch.setattr(RateLimitMiddleware, "dispatch", passthrough)


@pytest.fixture(autouse=True)
def _reset_rate_limit_circuit_breaker():
    cb = RateLimitMiddleware._circuit_breaker
    if cb is not None:
        cb._failure_count = 0
        cb._state = cb.CLOSED
    yield


async def _seed_admin_realm_user(
    sessionmaker,
    auth_service: AuthService,
    *,
    login: str,
    email: str,
    password: str,
) -> tuple[UUID, UUID]:
    with sessionmaker() as db:
        realm_repo = AuthRealmRepository(SyncSessionAdapter(db))
        admin_realm = await realm_repo.get_or_create_default_realm("admin")
        user = AdminUserModel(
            login=login,
            email=email,
            auth_realm_id=admin_realm.id,
            password_hash=await auth_service.hash_password(password),
            role="admin",
            is_active=True,
            is_email_verified=True,
        )
        db.add(user)
        db.commit()
        return user.id, admin_realm.id


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
                assert sessions[0].user_device_id is not None
                assert sessions[0].current_refresh_token_id is not None

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
                assert "access_token" not in refresh_payload
                assert "refresh_token" not in refresh_payload
                assert "token_type" not in refresh_payload
                assert "expires_in" not in refresh_payload

                refreshed_access_cookie = refresh_response.cookies.get("access_token")
                assert refreshed_access_cookie is not None
                assert refreshed_access_cookie != access_cookie
                refreshed_claims = auth_service.decode_token(refreshed_access_cookie, audience=audience)
                assert refreshed_claims["realm_id"] == str(realm_id)
                assert refreshed_claims["principal_type"] == "admin"

            with sessionmaker() as db:
                sessions_result = await SyncSessionAdapter(db).execute(
                    select(PrincipalSessionModel)
                    .where(PrincipalSessionModel.principal_subject == str(user_id))
                    .order_by(PrincipalSessionModel.issued_at.asc())
                )
                rotated_sessions = list(sessions_result.scalars().all())
                assert len(rotated_sessions) == 1
                assert rotated_sessions[0].status == "active"

                refresh_tokens_result = await SyncSessionAdapter(db).execute(
                    select(RefreshToken).where(RefreshToken.user_id == user_id)
                )
                refresh_tokens = list(refresh_tokens_result.scalars().all())
                assert len(refresh_tokens) == 2

                old_refresh_record = next(
                    token for token in refresh_tokens if token.token_hash == sha256(refresh_cookie.encode()).hexdigest()
                )
                new_refresh_record = next(
                    token for token in refresh_tokens if token.parent_token_id == old_refresh_record.id
                )
                assert old_refresh_record.consumed_at is not None
                assert old_refresh_record.revoked_at is not None
                assert old_refresh_record.revoked_reason == "rotated"
                assert old_refresh_record.replaced_by_token_id == new_refresh_record.id
                assert old_refresh_record.principal_session_id == rotated_sessions[0].id
                assert new_refresh_record.principal_session_id == rotated_sessions[0].id
                assert old_refresh_record.family_id == new_refresh_record.family_id
                assert rotated_sessions[0].current_refresh_token_id == new_refresh_record.id
    finally:
        app.dependency_overrides.pop(get_redis, None)
        engine.dispose()
        cleanup_sqlite_file(sqlite_path)


@pytest.mark.integration
async def test_refresh_replay_revokes_token_family_after_benign_race_window() -> None:
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
                    login="realm_refresh_replay_admin",
                    email="realm-refresh-replay@example.com",
                    auth_realm_id=admin_realm.id,
                    password_hash=await auth_service.hash_password("RealmRefreshReplayP@ssword123!"),
                    role="admin",
                    is_active=True,
                    is_email_verified=True,
                )
                db.add(user)
                db.commit()
                user_id = user.id

            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="https://admin.cyber-vpn.net",
            ) as client:
                login_response = await client.post(
                    "/api/v1/auth/login",
                    json={
                        "login_or_email": "realm-refresh-replay@example.com",
                        "password": "RealmRefreshReplayP@ssword123!",
                    },
                )
                assert login_response.status_code == 200
                old_refresh_cookie = client.cookies.get("refresh_token")
                assert old_refresh_cookie is not None

                refresh_response = await client.post("/api/v1/auth/refresh", json={})
                assert refresh_response.status_code == 200
                assert client.cookies.get("refresh_token") != old_refresh_cookie

            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="https://admin.cyber-vpn.net",
                cookies={"refresh_token": old_refresh_cookie},
            ) as benign_race_client:
                benign_race_response = await benign_race_client.post("/api/v1/auth/refresh", json={})
                assert benign_race_response.status_code == 401
                assert "Max-Age=0" not in "\n".join(benign_race_response.headers.get_list("set-cookie"))

            with sessionmaker() as db:
                adapter = SyncSessionAdapter(db)
                sessions_result = await adapter.execute(
                    select(PrincipalSessionModel).where(PrincipalSessionModel.principal_subject == str(user_id))
                )
                sessions = list(sessions_result.scalars().all())
                assert len(sessions) == 1
                assert sessions[0].status == "active"

                refresh_tokens_result = await adapter.execute(
                    select(RefreshToken).where(RefreshToken.user_id == user_id)
                )
                refresh_tokens = list(refresh_tokens_result.scalars().all())
                old_refresh_record = next(
                    token
                    for token in refresh_tokens
                    if token.token_hash == sha256(old_refresh_cookie.encode()).hexdigest()
                )
                current_refresh_record = next(token for token in refresh_tokens if token.id != old_refresh_record.id)
                assert current_refresh_record.revoked_at is None

                old_refresh_record.consumed_at = datetime.now(UTC) - timedelta(seconds=30)
                db.commit()

            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="https://admin.cyber-vpn.net",
                cookies={"refresh_token": old_refresh_cookie},
            ) as replay_client:
                replay_response = await replay_client.post("/api/v1/auth/refresh", json={})
                assert replay_response.status_code == 401
                replay_set_cookies = "\n".join(replay_response.headers.get_list("set-cookie"))
                assert "refresh_token=" in replay_set_cookies
                assert "Max-Age=0" in replay_set_cookies

            with sessionmaker() as db:
                adapter = SyncSessionAdapter(db)
                sessions_result = await adapter.execute(
                    select(PrincipalSessionModel).where(PrincipalSessionModel.principal_subject == str(user_id))
                )
                sessions = list(sessions_result.scalars().all())
                assert len(sessions) == 1
                assert sessions[0].status == "revoked"
                assert sessions[0].revoked_at is not None

                refresh_tokens_result = await adapter.execute(
                    select(RefreshToken).where(RefreshToken.user_id == user_id)
                )
                refresh_tokens = list(refresh_tokens_result.scalars().all())
                assert len(refresh_tokens) == 2
                assert {token.revoked_reason for token in refresh_tokens} == {"replay_detected"}
                assert all(token.revoked_at is not None for token in refresh_tokens)
    finally:
        app.dependency_overrides.pop(get_redis, None)
        engine.dispose()
        cleanup_sqlite_file(sqlite_path)


@pytest.mark.integration
async def test_repeated_admin_login_reuses_browser_device_and_replaces_session() -> None:
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
                    login="realm_repeat_admin",
                    email="realm-repeat@example.com",
                    auth_realm_id=admin_realm.id,
                    password_hash=await auth_service.hash_password("RealmRepeatP@ssword123!"),
                    role="admin",
                    is_active=True,
                    is_email_verified=True,
                )
                db.add(user)
                db.commit()
                user_id = user.id
                realm_id = admin_realm.id

            browser_headers = {
                "User-Agent": "CyberVPNRealmTest/1.0",
                "Accept-Language": "en-US,en;q=0.9",
            }
            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="https://admin.cyber-vpn.net",
                headers=browser_headers,
            ) as client:
                first_login_response = await client.post(
                    "/api/v1/auth/login",
                    json={"login_or_email": "realm-repeat@example.com", "password": "RealmRepeatP@ssword123!"},
                )
                assert first_login_response.status_code == 200
                first_device_cookie = client.cookies.get("__Host-cvpn_device_id")
                assert first_device_cookie is not None

                second_login_response = await client.post(
                    "/api/v1/auth/login",
                    headers={"User-Agent": "CyberVPNRealmTest/2.0"},
                    json={"login_or_email": "realm-repeat@example.com", "password": "RealmRepeatP@ssword123!"},
                )
                assert second_login_response.status_code == 200
                assert client.cookies.get("__Host-cvpn_device_id") == first_device_cookie

            with sessionmaker() as db:
                adapter = SyncSessionAdapter(db)
                devices_result = await adapter.execute(
                    select(UserDeviceModel).where(UserDeviceModel.principal_subject == str(user_id))
                )
                devices = list(devices_result.scalars().all())
                assert len(devices) == 1
                assert devices[0].auth_realm_id == realm_id
                assert devices[0].revoked_at is None
                assert devices[0].first_user_agent == "CyberVPNRealmTest/1.0"
                assert devices[0].last_user_agent == "CyberVPNRealmTest/2.0"
                assert devices[0].user_agent == "CyberVPNRealmTest/2.0"
                assert devices[0].ip_address == devices[0].last_ip_address
                assert devices[0].last_ip_address is not None
                assert devices[0].last_ip_source == "direct"
                assert devices[0].last_proxy_peer == devices[0].last_ip_address
                assert devices[0].device_key_hash != first_device_cookie
                assert devices[0].device_key_hash != sha256(first_device_cookie.encode()).hexdigest()
                assert (
                    devices[0].device_key_hash
                    == sha256(f"{first_device_cookie}pytest-device-cookie-pepper".encode()).hexdigest()
                )

                sessions_result = await adapter.execute(
                    select(PrincipalSessionModel)
                    .where(PrincipalSessionModel.principal_subject == str(user_id))
                    .order_by(PrincipalSessionModel.issued_at.asc())
                )
                sessions = list(sessions_result.scalars().all())
                assert len(sessions) == 2
                assert {session.user_device_id for session in sessions} == {devices[0].id}
                assert sessions[0].status == "revoked"
                assert sessions[0].revoked_at is not None
                assert sessions[1].status == "active"
                assert sessions[1].current_refresh_token_id is not None

                refresh_tokens_result = await adapter.execute(
                    select(RefreshToken).where(RefreshToken.user_id == user_id).order_by(RefreshToken.created_at.asc())
                )
                refresh_tokens = list(refresh_tokens_result.scalars().all())
                assert len(refresh_tokens) == 2
                assert refresh_tokens[0].revoked_at is not None
                assert refresh_tokens[0].revoked_reason == "replaced_by_new_login"
                assert refresh_tokens[1].revoked_at is None
    finally:
        app.dependency_overrides.pop(get_redis, None)
        engine.dispose()
        cleanup_sqlite_file(sqlite_path)


@pytest.mark.integration
async def test_customer_devices_do_not_expose_vpn_entitlement_device_quota(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def fail_on_entitlement_snapshot(*args, **kwargs):
        raise AssertionError("web session device listing must not read VPN entitlement device quotas")

    monkeypatch.setattr(
        "src.application.services.entitlements_service.EntitlementsService.get_current_snapshot",
        fail_on_entitlement_snapshot,
    )

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
                customer_realm = await realm_repo.get_or_create_default_realm("customer")

                user = AdminUserModel(
                    login="realm_customer_devices_user",
                    email="customer-devices@example.com",
                    auth_realm_id=customer_realm.id,
                    password_hash=await auth_service.hash_password("RealmCustomerDevicesP@ssword123!"),
                    role="viewer",
                    is_active=True,
                    is_email_verified=True,
                )
                db.add(user)
                db.commit()

            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://127.0.0.1:13000",
                headers={"User-Agent": "CyberVPNCustomerDeviceList/1.0"},
            ) as client:
                login_response = await client.post(
                    "/api/v1/auth/login",
                    headers={"Origin": "http://127.0.0.1:13000"},
                    json={
                        "login_or_email": "customer-devices@example.com",
                        "password": "RealmCustomerDevicesP@ssword123!",
                    },
                )
                assert login_response.status_code == 200

                devices_response = await client.get("/api/v1/auth/devices")
                assert devices_response.status_code == 200
                payload = devices_response.json()
                assert payload["total"] == 1
                assert payload["total_devices"] == 1
                assert payload["device_limit"] is None
                assert payload["remaining_devices"] is None
                assert payload["devices"][0]["user_agent"] == "CyberVPNCustomerDeviceList/1.0"
    finally:
        app.dependency_overrides.pop(get_redis, None)
        engine.dispose()
        cleanup_sqlite_file(sqlite_path)


@pytest.mark.integration
async def test_admin_devices_list_returns_unique_devices_after_refresh_rotation() -> None:
    auth_service = AuthService()
    fake_redis = FakeRedis()
    sessionmaker, engine, sqlite_path = create_realm_test_sessionmaker()
    await initialize_realm_test_database(engine)

    async def _override_redis():
        yield fake_redis

    app.dependency_overrides[get_redis] = _override_redis

    try:
        async with override_realm_test_db(sessionmaker):
            user_id, _realm_id = await _seed_admin_realm_user(
                sessionmaker,
                auth_service,
                login="realm_device_list_admin",
                email="realm-device-list@example.com",
                password="RealmDeviceListP@ssword123!",
            )

            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="https://admin.cyber-vpn.net",
                headers={"User-Agent": "CyberVPNDeviceList/1.0"},
            ) as client:
                login_response = await client.post(
                    "/api/v1/auth/login",
                    json={"login_or_email": "realm-device-list@example.com", "password": "RealmDeviceListP@ssword123!"},
                )
                assert login_response.status_code == 200

                refresh_response = await client.post("/api/v1/auth/refresh", json={})
                assert refresh_response.status_code == 200

                devices_response = await client.get("/api/v1/auth/devices")
                assert devices_response.status_code == 200
                payload = devices_response.json()
                assert payload["total"] == 1
                assert payload["total_devices"] == 1
                assert payload["device_limit"] is None
                assert payload["remaining_devices"] is None
                assert len(payload["devices"]) == 1
                assert payload["devices"][0]["is_current"] is True
                assert payload["devices"][0]["user_agent"] == "CyberVPNDeviceList/1.0"

            with sessionmaker() as db:
                adapter = SyncSessionAdapter(db)
                devices_result = await adapter.execute(
                    select(UserDeviceModel).where(UserDeviceModel.principal_subject == str(user_id))
                )
                devices = list(devices_result.scalars().all())
                assert len(devices) == 1
                assert payload["devices"][0]["device_id"] == str(devices[0].id)

                refresh_tokens_result = await adapter.execute(
                    select(RefreshToken).where(RefreshToken.user_id == user_id)
                )
                assert len(list(refresh_tokens_result.scalars().all())) == 2
    finally:
        app.dependency_overrides.pop(get_redis, None)
        engine.dispose()
        cleanup_sqlite_file(sqlite_path)


@pytest.mark.integration
async def test_admin_logout_others_revokes_only_non_current_device() -> None:
    auth_service = AuthService()
    fake_redis = FakeRedis()
    sessionmaker, engine, sqlite_path = create_realm_test_sessionmaker()
    await initialize_realm_test_database(engine)

    async def _override_redis():
        yield fake_redis

    app.dependency_overrides[get_redis] = _override_redis

    try:
        async with override_realm_test_db(sessionmaker):
            user_id, _realm_id = await _seed_admin_realm_user(
                sessionmaker,
                auth_service,
                login="realm_logout_others_admin",
                email="realm-logout-others@example.com",
                password="RealmLogoutOthersP@ssword123!",
            )

            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="https://admin.cyber-vpn.net",
                headers={"User-Agent": "CyberVPNCurrentDevice/1.0"},
            ) as current_client:
                current_login = await current_client.post(
                    "/api/v1/auth/login",
                    json={
                        "login_or_email": "realm-logout-others@example.com",
                        "password": "RealmLogoutOthersP@ssword123!",
                    },
                )
                assert current_login.status_code == 200
                current_access = current_client.cookies.get("access_token")
                assert current_access is not None

                async with AsyncClient(
                    transport=ASGITransport(app=app),
                    base_url="https://admin.cyber-vpn.net",
                    headers={"User-Agent": "CyberVPNOtherDevice/1.0"},
                ) as other_client:
                    other_login = await other_client.post(
                        "/api/v1/auth/login",
                        json={
                            "login_or_email": "realm-logout-others@example.com",
                            "password": "RealmLogoutOthersP@ssword123!",
                        },
                    )
                    assert other_login.status_code == 200
                    other_access = other_client.cookies.get("access_token")
                    assert other_access is not None

                    devices_response = await current_client.get("/api/v1/auth/devices")
                    assert devices_response.status_code == 200
                    devices_payload = devices_response.json()
                    assert devices_payload["total_devices"] == 2
                    assert sum(1 for device in devices_payload["devices"] if device["is_current"]) == 1

                    logout_others_response = await current_client.post("/api/v1/auth/devices/logout-others")
                    assert logout_others_response.status_code == 200
                    assert logout_others_response.json()["sessions_revoked"] == 1

                    current_session_response = await current_client.get("/api/v1/auth/session")
                    assert current_session_response.status_code == 200

                    stale_other_response = await other_client.get(
                        "/api/v1/auth/session",
                        headers={"Authorization": f"Bearer {other_access}"},
                    )
                    assert stale_other_response.status_code == 401

                    devices_after_response = await current_client.get("/api/v1/auth/devices")
                    assert devices_after_response.status_code == 200
                    devices_after_payload = devices_after_response.json()
                    assert devices_after_payload["total_devices"] == 1
                    assert devices_after_payload["devices"][0]["is_current"] is True

            with sessionmaker() as db:
                sessions_result = await SyncSessionAdapter(db).execute(
                    select(PrincipalSessionModel)
                    .where(PrincipalSessionModel.principal_subject == str(user_id))
                    .order_by(PrincipalSessionModel.issued_at.asc())
                )
                sessions = list(sessions_result.scalars().all())
                assert [session.status for session in sessions].count("active") == 1
                assert [session.status for session in sessions].count("revoked") == 1
    finally:
        app.dependency_overrides.pop(get_redis, None)
        engine.dispose()
        cleanup_sqlite_file(sqlite_path)


@pytest.mark.integration
async def test_admin_revoke_device_revokes_selected_device_only() -> None:
    auth_service = AuthService()
    fake_redis = FakeRedis()
    sessionmaker, engine, sqlite_path = create_realm_test_sessionmaker()
    await initialize_realm_test_database(engine)

    async def _override_redis():
        yield fake_redis

    app.dependency_overrides[get_redis] = _override_redis

    try:
        async with override_realm_test_db(sessionmaker):
            await _seed_admin_realm_user(
                sessionmaker,
                auth_service,
                login="realm_revoke_device_admin",
                email="realm-revoke-device@example.com",
                password="RealmRevokeDeviceP@ssword123!",
            )

            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="https://admin.cyber-vpn.net",
                headers={"User-Agent": "CyberVPNRevokeCurrent/1.0"},
            ) as current_client:
                current_login = await current_client.post(
                    "/api/v1/auth/login",
                    json={
                        "login_or_email": "realm-revoke-device@example.com",
                        "password": "RealmRevokeDeviceP@ssword123!",
                    },
                )
                assert current_login.status_code == 200

                async with AsyncClient(
                    transport=ASGITransport(app=app),
                    base_url="https://admin.cyber-vpn.net",
                    headers={"User-Agent": "CyberVPNRevokeTarget/1.0"},
                ) as target_client:
                    target_login = await target_client.post(
                        "/api/v1/auth/login",
                        json={
                            "login_or_email": "realm-revoke-device@example.com",
                            "password": "RealmRevokeDeviceP@ssword123!",
                        },
                    )
                    assert target_login.status_code == 200
                    target_access = target_client.cookies.get("access_token")
                    assert target_access is not None

                    devices_response = await current_client.get("/api/v1/auth/devices")
                    assert devices_response.status_code == 200
                    devices = devices_response.json()["devices"]
                    target_device = next(device for device in devices if not device["is_current"])

                    revoke_response = await current_client.delete(f"/api/v1/auth/devices/{target_device['device_id']}")
                    assert revoke_response.status_code == 200
                    assert revoke_response.json()["device_id"] == target_device["device_id"]

                    current_session_response = await current_client.get("/api/v1/auth/session")
                    assert current_session_response.status_code == 200

                    stale_target_response = await target_client.get(
                        "/api/v1/auth/session",
                        headers={"Authorization": f"Bearer {target_access}"},
                    )
                    assert stale_target_response.status_code == 401
    finally:
        app.dependency_overrides.pop(get_redis, None)
        engine.dispose()
        cleanup_sqlite_file(sqlite_path)


@pytest.mark.integration
async def test_admin_logout_all_is_realm_scoped_for_principal_subject() -> None:
    auth_service = AuthService()
    fake_redis = FakeRedis()
    sessionmaker, engine, sqlite_path = create_realm_test_sessionmaker()
    await initialize_realm_test_database(engine)

    async def _override_redis():
        yield fake_redis

    app.dependency_overrides[get_redis] = _override_redis

    try:
        async with override_realm_test_db(sessionmaker):
            user_id, admin_realm_id = await _seed_admin_realm_user(
                sessionmaker,
                auth_service,
                login="realm_logout_all_scope_admin",
                email="realm-logout-all-scope@example.com",
                password="RealmLogoutAllScopeP@ssword123!",
            )

            with sessionmaker() as db:
                realm_repo = AuthRealmRepository(SyncSessionAdapter(db))
                partner_realm = await realm_repo.get_or_create_default_realm("partner")
                partner_device = UserDeviceModel(
                    auth_realm_id=partner_realm.id,
                    principal_subject=str(user_id),
                    principal_class="partner_operator",
                    audience=partner_realm.audience,
                    device_key_hash=sha256(b"partner-device").hexdigest(),
                    platform="web",
                    ip_address="192.0.2.55",
                    user_agent="SyntheticPartnerDevice/1.0",
                )
                db.add(partner_device)
                db.flush()
                partner_refresh = RefreshToken(
                    user_id=user_id,
                    auth_realm_id=partner_realm.id,
                    principal_class="partner_operator",
                    principal_subject=str(user_id),
                    audience=partner_realm.audience,
                    scope_family="partner",
                    token_hash=sha256(b"partner-refresh").hexdigest(),
                    expires_at=datetime.now(UTC) + timedelta(days=7),
                    device_id=str(partner_device.id),
                    ip_address="192.0.2.55",
                    user_agent="SyntheticPartnerDevice/1.0",
                    jti=str(uuid4()),
                    family_id=uuid4(),
                )
                db.add(partner_refresh)
                db.flush()
                partner_session = PrincipalSessionModel(
                    auth_realm_id=partner_realm.id,
                    principal_subject=str(user_id),
                    principal_class="partner_operator",
                    audience=partner_realm.audience,
                    scope_family="partner",
                    access_token_jti=str(uuid4()),
                    refresh_token_id=partner_refresh.id,
                    user_device_id=partner_device.id,
                    current_refresh_token_id=partner_refresh.id,
                    expires_at=datetime.now(UTC) + timedelta(days=7),
                )
                db.add(partner_session)
                db.flush()
                partner_refresh.principal_session_id = partner_session.id
                db.commit()
                partner_session_id = partner_session.id
                partner_refresh_id = partner_refresh.id

            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="https://admin.cyber-vpn.net",
            ) as client:
                login_response = await client.post(
                    "/api/v1/auth/login",
                    json={
                        "login_or_email": "realm-logout-all-scope@example.com",
                        "password": "RealmLogoutAllScopeP@ssword123!",
                    },
                )
                assert login_response.status_code == 200

                logout_all_response = await client.post("/api/v1/auth/logout-all")
                assert logout_all_response.status_code == 200
                assert logout_all_response.json()["sessions_revoked"] == 1

            with sessionmaker() as db:
                adapter = SyncSessionAdapter(db)
                admin_sessions_result = await adapter.execute(
                    select(PrincipalSessionModel).where(
                        PrincipalSessionModel.principal_subject == str(user_id),
                        PrincipalSessionModel.auth_realm_id == admin_realm_id,
                    )
                )
                admin_sessions = list(admin_sessions_result.scalars().all())
                assert len(admin_sessions) == 1
                assert admin_sessions[0].status == "revoked"

                partner_session_after = await adapter.get(PrincipalSessionModel, partner_session_id)
                partner_refresh_after = await adapter.get(RefreshToken, partner_refresh_id)
                assert partner_session_after.status == "active"
                assert partner_session_after.revoked_at is None
                assert partner_refresh_after.revoked_at is None
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
async def test_admin_logout_revokes_current_access_session_when_refresh_cookie_missing() -> None:
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
                    login="realm_access_only_logout_admin",
                    email="realm-access-only-logout@example.com",
                    auth_realm_id=admin_realm.id,
                    password_hash=await auth_service.hash_password("RealmAccessOnlyLogoutP@ssword123!"),
                    role="admin",
                    is_active=True,
                    is_email_verified=True,
                )
                db.add(user)
                db.commit()
                user_id = user.id

            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="https://admin.cyber-vpn.net",
            ) as client:
                login_response = await client.post(
                    "/api/v1/auth/login",
                    json={
                        "login_or_email": "realm-access-only-logout@example.com",
                        "password": "RealmAccessOnlyLogoutP@ssword123!",
                    },
                )
                assert login_response.status_code == 200
                access_token = client.cookies.get("access_token")
                assert access_token is not None

            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="https://admin.cyber-vpn.net",
                cookies={"access_token": access_token},
            ) as logout_client:
                logout_response = await logout_client.post("/api/v1/auth/logout")
                assert logout_response.status_code == 204

            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="https://admin.cyber-vpn.net",
            ) as stale_client:
                stale_access_response = await stale_client.get(
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
                assert "access_token" not in refresh_payload
                assert "refresh_token" not in refresh_payload
                assert "token_type" not in refresh_payload
                assert "expires_in" not in refresh_payload

                refreshed_access_cookie = refresh_response.cookies.get("partner_access_token")
                assert refreshed_access_cookie is not None
                assert refreshed_access_cookie != access_cookie
                refreshed_claims = auth_service.decode_token(refreshed_access_cookie, audience=audience)
                assert refreshed_claims["realm_id"] == str(realm_id)
                assert refreshed_claims["principal_type"] == "partner_operator"

            with sessionmaker() as db:
                sessions_result = await SyncSessionAdapter(db).execute(
                    select(PrincipalSessionModel)
                    .where(PrincipalSessionModel.principal_subject == str(user_id))
                    .order_by(PrincipalSessionModel.issued_at.asc())
                )
                sessions = list(sessions_result.scalars().all())
                assert len(sessions) == 1
                assert sessions[0].status == "active"
                assert sessions[0].auth_realm_id == realm_id
                assert sessions[0].audience == audience
                assert sessions[0].scope_family == "partner"
                assert sessions[0].principal_class == "partner_operator"
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
