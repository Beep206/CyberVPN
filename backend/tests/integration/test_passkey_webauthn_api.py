from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from hashlib import sha256
from types import SimpleNamespace

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from webauthn.helpers import base64url_to_bytes
from webauthn.helpers.exceptions import InvalidAuthenticationResponse

from src.application.services.auth_service import AuthService
from src.application.services.passkey_webauthn import (
    PasskeyAuthenticationVerification,
    PasskeyRegistrationVerification,
    passkey_user_handle,
)
from src.config.settings import settings
from src.infrastructure.cache.passkey_challenges import PasskeyChallengeError, PasskeyChallengeStore
from src.infrastructure.cache.passkey_fresh_auth import PasskeyFreshAuthGrantStore
from src.infrastructure.cache.redis_client import get_redis
from src.infrastructure.database.models.admin_user_model import AdminUserModel
from src.infrastructure.database.models.audit_log_model import AuditLog
from src.infrastructure.database.models.passkey_credential_model import PasskeyCredentialModel
from src.infrastructure.database.models.principal_session_model import PrincipalSessionModel
from src.infrastructure.database.repositories.auth_realm_repo import AuthRealmRepository
from src.main import app
from src.presentation.dependencies.passkey_fresh_auth import FRESH_AUTH_GRANT_ID_HEADER, FRESH_AUTH_REQUIRED_DETAIL
from tests.helpers.realm_auth import (
    FakeRedis,
    SyncSessionAdapter,
    cleanup_sqlite_file,
    create_realm_test_sessionmaker,
    initialize_realm_test_database,
    override_realm_test_db,
)

_ADMIN_ORIGIN = "https://admin.cyber-vpn.net"
_ADMIN_HEADERS = {"Origin": _ADMIN_ORIGIN}
_RAW_CREDENTIAL_ID = "dGVzdF9wYXNza2V5X2NyZWQ"
_CREDENTIAL_HASH = sha256(base64url_to_bytes(_RAW_CREDENTIAL_ID)).hexdigest()
_OTHER_RAW_CREDENTIAL_ID = "b3RoZXJfcGFzc2tleV9jcmVk"
_OTHER_CREDENTIAL_HASH = sha256(base64url_to_bytes(_OTHER_RAW_CREDENTIAL_ID)).hexdigest()
_ADMIN_POLICY_UPDATE_ACTION = "admin.passkeys.policy.update"


def _admin_url(path: str) -> str:
    return f"{_ADMIN_ORIGIN}{path}"


def _credential_payload(raw_id: str = _RAW_CREDENTIAL_ID) -> dict:
    return {
        "id": raw_id,
        "rawId": raw_id,
        "type": "public-key",
        "response": {
            "clientDataJSON": "Y2xpZW50",
            "attestationObject": "YXR0ZXN0YXRpb24",
            "authenticatorData": "YXV0aERhdGE",
            "signature": "c2lnbmF0dXJl",
            "transports": ["internal"],
        },
        "authenticatorAttachment": "platform",
    }


@pytest.fixture(autouse=True)
def enable_passkeys(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "passkey_enabled", True)
    monkeypatch.setattr(settings, "passkey_admin_enabled", True)
    monkeypatch.setattr(settings, "passkey_customer_enabled", True)
    monkeypatch.setattr(settings, "passkey_partner_enabled", True)
    monkeypatch.setattr(settings, "passkey_admin_security_dashboard_enabled", True)
    monkeypatch.setattr(settings, "passkey_partner_workspace_policy_enabled", True)
    monkeypatch.setattr(settings, "passkey_allowed_origins", list(settings.passkey_allowed_origins))


async def _seed_realm_admin_user(
    sessionmaker,
    *,
    login: str,
    email: str,
    password: str,
    role: str,
) -> tuple[str, str]:
    auth_service = AuthService()
    with sessionmaker() as db:
        realm_repo = AuthRealmRepository(SyncSessionAdapter(db))
        admin_realm = await realm_repo.get_or_create_default_realm("admin")
        user = AdminUserModel(
            login=login,
            email=email,
            auth_realm_id=admin_realm.id,
            password_hash=await auth_service.hash_password(password),
            role=role,
            is_active=True,
            is_email_verified=True,
        )
        db.add(user)
        db.commit()
        return str(user.id), admin_realm.audience


async def _seed_admin_user(sessionmaker) -> tuple[str, str]:
    return await _seed_realm_admin_user(
        sessionmaker,
        login="passkey_admin",
        email="passkey-admin@example.com",
        password="PasskeyAdminP@ssword123!",
        role="admin",
    )


async def _seed_default_realm(sessionmaker, realm_type: str) -> None:
    with sessionmaker() as db:
        await AuthRealmRepository(SyncSessionAdapter(db)).get_or_create_default_realm(realm_type)
        db.commit()


async def _login_token(async_client: AsyncClient, *, login_or_email: str, password: str) -> str:
    response = await async_client.post(
        _admin_url("/api/v1/auth/login"),
        headers=_ADMIN_HEADERS,
        json={"login_or_email": login_or_email, "password": password},
    )
    assert response.status_code == 200
    return response.json()["access_token"]


def _fake_registration_verification() -> PasskeyRegistrationVerification:
    return PasskeyRegistrationVerification(
        credential_id_b64=_RAW_CREDENTIAL_ID,
        credential_id_hash=_CREDENTIAL_HASH,
        credential_public_key=b"credential-public-key",
        sign_count=1,
        aaguid="00000000-0000-0000-0000-000000000000",
        attestation_format="none",
        credential_type="public-key",
        user_verified=True,
        device_type="single_device",
        backed_up=False,
        transports=["internal"],
        authenticator_attachment="platform",
    )


def _fake_authentication_verification(
    sign_count: int = 2,
    *,
    credential_id_b64: str = _RAW_CREDENTIAL_ID,
    credential_id_hash: str = _CREDENTIAL_HASH,
) -> PasskeyAuthenticationVerification:
    return PasskeyAuthenticationVerification(
        credential_id_b64=credential_id_b64,
        credential_id_hash=credential_id_hash,
        new_sign_count=sign_count,
        user_verified=True,
        device_type="single_device",
        backed_up=False,
    )


def _patch_webauthn_counter_guard(
    monkeypatch: pytest.MonkeyPatch,
    *,
    new_sign_count: int,
    raw_id: str = _RAW_CREDENTIAL_ID,
) -> None:
    def _verify_authentication_response(*, credential_current_sign_count: int, **_kwargs):
        if (
            new_sign_count > 0 or credential_current_sign_count > 0
        ) and new_sign_count <= credential_current_sign_count:
            raise InvalidAuthenticationResponse(
                f"Response sign count of {new_sign_count} was not greater than current count "
                f"of {credential_current_sign_count}"
            )
        return SimpleNamespace(
            credential_id=base64url_to_bytes(raw_id),
            new_sign_count=new_sign_count,
            user_verified=True,
            credential_device_type="single_device",
            credential_backed_up=False,
        )

    monkeypatch.setattr(
        "src.application.services.passkey_webauthn.verify_authentication_response",
        _verify_authentication_response,
    )


async def _seed_passkey_credential(
    sessionmaker,
    *,
    realm_type: str,
    principal_subject: str,
    credential_id: str = _RAW_CREDENTIAL_ID,
    credential_id_hash: str = _CREDENTIAL_HASH,
    sign_count: int = 1,
) -> None:
    with sessionmaker() as db:
        realm = await AuthRealmRepository(SyncSessionAdapter(db)).get_or_create_default_realm(realm_type)
        principal_class = "partner_operator" if realm_type == "partner" else realm_type
        db.add(
            PasskeyCredentialModel(
                credential_id=credential_id,
                credential_id_hash=credential_id_hash,
                credential_public_key=b"credential-public-key",
                sign_count=sign_count,
                auth_realm_id=realm.id,
                realm_key=realm.realm_key,
                audience=realm.audience,
                principal_class=principal_class,
                principal_subject=principal_subject,
                user_handle=passkey_user_handle(
                    auth_realm_id=realm.id,
                    principal_class=principal_class,
                    principal_subject=principal_subject,
                ),
                label="Work laptop",
                surface=realm_type,
                rp_id=settings.passkey_rp_id,
                origin=_ADMIN_ORIGIN,
                credential_type="public-key",
                device_type="single_device",
                transports=["internal"],
                backed_up=False,
                user_verified=True,
                authenticator_attachment="platform",
                status="active",
            )
        )
        db.commit()


async def _fresh_auth_grants(fake_redis: FakeRedis) -> list[dict]:
    grants: list[dict] = []
    async for key in fake_redis.scan_iter(match="passkey:fresh:*"):
        raw = await fake_redis.get(key)
        assert isinstance(raw, str)
        grants.append(json.loads(raw))
    return grants


async def _fresh_auth_grant_id(
    fake_redis: FakeRedis,
    sessionmaker,
    *,
    principal_subject: str,
    action: str,
    realm_type: str = "admin",
    principal_class: str = "admin",
) -> str:
    with sessionmaker() as db:
        realm = await AuthRealmRepository(SyncSessionAdapter(db)).get_or_create_default_realm(realm_type)
        db.commit()

    grant = await PasskeyFreshAuthGrantStore(fake_redis).create(
        principal_subject=principal_subject,
        principal_class=principal_class,
        auth_realm_id=str(realm.id),
        realm_key=realm.realm_key,
        action=action,
        ttl_seconds=300,
    )
    return grant.grant_id


@pytest.mark.integration
async def test_passkey_registration_and_authentication_issue_realm_cookie_session(
    async_client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_redis = FakeRedis()
    sessionmaker, engine, sqlite_path = create_realm_test_sessionmaker()
    await initialize_realm_test_database(engine)

    async def _override_redis():
        yield fake_redis

    app.dependency_overrides[get_redis] = _override_redis
    monkeypatch.setattr(
        "src.application.services.passkey_webauthn.PasskeyWebAuthnService.verify_registration",
        lambda self, *, payload, challenge: _fake_registration_verification(),
    )
    monkeypatch.setattr(
        "src.application.services.passkey_webauthn.PasskeyWebAuthnService.verify_authentication",
        lambda self, *, payload, challenge, credential: _fake_authentication_verification(),
    )

    try:
        async with override_realm_test_db(sessionmaker):
            user_id, audience = await _seed_admin_user(sessionmaker)

            login_response = await async_client.post(
                _admin_url("/api/v1/auth/login"),
                headers=_ADMIN_HEADERS,
                json={"login_or_email": "passkey-admin@example.com", "password": "PasskeyAdminP@ssword123!"},
            )
            assert login_response.status_code == 200

            options_response = await async_client.post(
                _admin_url("/api/v1/auth/passkeys/registration/options"),
                headers=_ADMIN_HEADERS,
                json={"label": "Work laptop"},
            )
            assert options_response.status_code == 200
            options_payload = options_response.json()
            assert options_payload["publicKey"]["rp"]["id"] == settings.passkey_rp_id
            assert options_payload["publicKey"]["authenticatorSelection"]["userVerification"] == "required"

            verify_response = await async_client.post(
                _admin_url("/api/v1/auth/passkeys/registration/verify"),
                headers=_ADMIN_HEADERS,
                json={
                    "challengeId": options_payload["challengeId"],
                    "credential": _credential_payload(),
                    "label": "Work laptop",
                },
            )
            assert verify_response.status_code == 201
            assert verify_response.json()["label"] == "Work laptop"

            auth_options_response = await async_client.post(
                _admin_url("/api/v1/auth/passkeys/authentication/options"),
                headers=_ADMIN_HEADERS,
                json={"identifier": "passkey-admin@example.com"},
            )
            assert auth_options_response.status_code == 200
            auth_options_payload = auth_options_response.json()
            assert auth_options_payload["publicKey"]["allowCredentials"][0]["id"] == _RAW_CREDENTIAL_ID

            auth_verify_response = await async_client.post(
                _admin_url("/api/v1/auth/passkeys/authentication/verify"),
                headers=_ADMIN_HEADERS,
                json={
                    "challengeId": auth_options_payload["challengeId"],
                    "credential": _credential_payload(),
                },
            )
            assert auth_verify_response.status_code == 200
            auth_payload = auth_verify_response.json()
            assert auth_payload["auth_realm_key"] == "admin"
            assert auth_payload["audience"] == audience
            assert auth_payload["principal_type"] == "admin"
            assert "access_token=" in "\n".join(auth_verify_response.headers.get_list("set-cookie"))

            with sessionmaker() as db:
                sessions = list(
                    db.execute(
                        select(PrincipalSessionModel).where(PrincipalSessionModel.principal_subject == user_id)
                    )
                    .scalars()
                    .all()
                )
                assert len(sessions) >= 2
                credential = db.execute(select(PasskeyCredentialModel)).scalar_one()
                assert credential.credential_id_hash == _CREDENTIAL_HASH
                assert credential.sign_count == 2
                assert credential.last_used_at is not None
    finally:
        app.dependency_overrides.pop(get_redis, None)
        engine.dispose()
        cleanup_sqlite_file(sqlite_path)


@pytest.mark.integration
async def test_passkey_reauthentication_succeeds_and_stores_fresh_grant(
    async_client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_redis = FakeRedis()
    sessionmaker, engine, sqlite_path = create_realm_test_sessionmaker()
    await initialize_realm_test_database(engine)

    async def _override_redis():
        yield fake_redis

    app.dependency_overrides[get_redis] = _override_redis
    monkeypatch.setattr(
        "src.application.services.passkey_webauthn.PasskeyWebAuthnService.verify_authentication",
        lambda self, *, payload, challenge, credential: _fake_authentication_verification(),
    )

    try:
        async with override_realm_test_db(sessionmaker):
            user_id, _audience = await _seed_admin_user(sessionmaker)
            await _seed_passkey_credential(sessionmaker, realm_type="admin", principal_subject=user_id)

            login_response = await async_client.post(
                _admin_url("/api/v1/auth/login"),
                headers=_ADMIN_HEADERS,
                json={"login_or_email": "passkey-admin@example.com", "password": "PasskeyAdminP@ssword123!"},
            )
            assert login_response.status_code == 200

            options_response = await async_client.post(
                _admin_url("/api/v1/auth/passkeys/reauthentication/options"),
                headers=_ADMIN_HEADERS,
                json={"action": "partner.payout.approve"},
            )
            assert options_response.status_code == 200, options_response.text

            verify_response = await async_client.post(
                _admin_url("/api/v1/auth/passkeys/reauthentication/verify"),
                headers=_ADMIN_HEADERS,
                json={
                    "challengeId": options_response.json()["challengeId"],
                    "credential": _credential_payload(),
                    "action": "partner.payout.approve",
                },
            )
            assert verify_response.status_code == 200, verify_response.text
            verify_payload = verify_response.json()
            assert verify_payload["freshAuthGrantId"]
            assert verify_payload["expiresAt"]

            grants = await _fresh_auth_grants(fake_redis)
            assert len(grants) == 1
            assert grants[0]["principal_subject"] == user_id
            assert grants[0]["principal_class"] == "admin"
            assert grants[0]["realm_key"] == "admin"
            assert grants[0]["action"] == "partner.payout.approve"
            assert grants[0]["auth_realm_id"]
            assert grants[0]["expires_at"]

            with sessionmaker() as db:
                credential = db.execute(select(PasskeyCredentialModel)).scalar_one()
                assert credential.sign_count == 2
                assert credential.last_used_at is not None
    finally:
        app.dependency_overrides.pop(get_redis, None)
        engine.dispose()
        cleanup_sqlite_file(sqlite_path)


@pytest.mark.integration
@pytest.mark.parametrize("credential_scope", ["cross_realm", "wrong_principal"])
async def test_passkey_reauthentication_rejects_credential_scope_mismatch(
    async_client: AsyncClient,
    credential_scope: str,
) -> None:
    fake_redis = FakeRedis()
    sessionmaker, engine, sqlite_path = create_realm_test_sessionmaker()
    await initialize_realm_test_database(engine)

    async def _override_redis():
        yield fake_redis

    app.dependency_overrides[get_redis] = _override_redis

    try:
        async with override_realm_test_db(sessionmaker):
            user_id, _audience = await _seed_admin_user(sessionmaker)
            await _seed_passkey_credential(sessionmaker, realm_type="admin", principal_subject=user_id)

            if credential_scope == "cross_realm":
                await _seed_passkey_credential(
                    sessionmaker,
                    realm_type="partner",
                    principal_subject=user_id,
                    credential_id=_OTHER_RAW_CREDENTIAL_ID,
                    credential_id_hash=_OTHER_CREDENTIAL_HASH,
                )
            else:
                other_user_id, _other_audience = await _seed_realm_admin_user(
                    sessionmaker,
                    login="other_passkey_admin",
                    email="other-passkey-admin@example.com",
                    password="OtherPasskeyAdminP@ssword123!",
                    role="admin",
                )
                await _seed_passkey_credential(
                    sessionmaker,
                    realm_type="admin",
                    principal_subject=other_user_id,
                    credential_id=_OTHER_RAW_CREDENTIAL_ID,
                    credential_id_hash=_OTHER_CREDENTIAL_HASH,
                )

            login_response = await async_client.post(
                _admin_url("/api/v1/auth/login"),
                headers=_ADMIN_HEADERS,
                json={"login_or_email": "passkey-admin@example.com", "password": "PasskeyAdminP@ssword123!"},
            )
            assert login_response.status_code == 200

            options_response = await async_client.post(
                _admin_url("/api/v1/auth/passkeys/reauthentication/options"),
                headers=_ADMIN_HEADERS,
                json={"action": "admin.team.invite"},
            )
            assert options_response.status_code == 200, options_response.text

            verify_response = await async_client.post(
                _admin_url("/api/v1/auth/passkeys/reauthentication/verify"),
                headers=_ADMIN_HEADERS,
                json={
                    "challengeId": options_response.json()["challengeId"],
                    "credential": _credential_payload(_OTHER_RAW_CREDENTIAL_ID),
                    "action": "admin.team.invite",
                },
            )
            assert verify_response.status_code == 401
            assert await _fresh_auth_grants(fake_redis) == []
    finally:
        app.dependency_overrides.pop(get_redis, None)
        engine.dispose()
        cleanup_sqlite_file(sqlite_path)


@pytest.mark.integration
async def test_passkey_reauthentication_rejects_regressing_sign_count(
    async_client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_redis = FakeRedis()
    sessionmaker, engine, sqlite_path = create_realm_test_sessionmaker()
    await initialize_realm_test_database(engine)

    async def _override_redis():
        yield fake_redis

    app.dependency_overrides[get_redis] = _override_redis
    monkeypatch.setattr(
        "src.application.services.passkey_webauthn.PasskeyWebAuthnService.verify_authentication",
        lambda self, *, payload, challenge, credential: _fake_authentication_verification(sign_count=4),
    )

    try:
        async with override_realm_test_db(sessionmaker):
            user_id, _audience = await _seed_admin_user(sessionmaker)
            await _seed_passkey_credential(
                sessionmaker,
                realm_type="admin",
                principal_subject=user_id,
                sign_count=5,
            )

            login_response = await async_client.post(
                _admin_url("/api/v1/auth/login"),
                headers=_ADMIN_HEADERS,
                json={"login_or_email": "passkey-admin@example.com", "password": "PasskeyAdminP@ssword123!"},
            )
            assert login_response.status_code == 200

            options_response = await async_client.post(
                _admin_url("/api/v1/auth/passkeys/reauthentication/options"),
                headers=_ADMIN_HEADERS,
                json={"action": "admin.webhook.rotate"},
            )
            assert options_response.status_code == 200, options_response.text

            verify_response = await async_client.post(
                _admin_url("/api/v1/auth/passkeys/reauthentication/verify"),
                headers=_ADMIN_HEADERS,
                json={
                    "challengeId": options_response.json()["challengeId"],
                    "credential": _credential_payload(),
                    "action": "admin.webhook.rotate",
                },
            )
            assert verify_response.status_code == 401
            assert await _fresh_auth_grants(fake_redis) == []

            with sessionmaker() as db:
                credential = db.execute(select(PasskeyCredentialModel)).scalar_one()
                assert credential.sign_count == 5
                assert credential.clone_suspected_at is not None
    finally:
        app.dependency_overrides.pop(get_redis, None)
        engine.dispose()
        cleanup_sqlite_file(sqlite_path)


@pytest.mark.integration
async def test_passkey_reauthentication_persists_real_library_sign_count_anomaly(
    async_client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_redis = FakeRedis()
    sessionmaker, engine, sqlite_path = create_realm_test_sessionmaker()
    await initialize_realm_test_database(engine)

    async def _override_redis():
        yield fake_redis

    app.dependency_overrides[get_redis] = _override_redis
    _patch_webauthn_counter_guard(monkeypatch, new_sign_count=4)

    try:
        async with override_realm_test_db(sessionmaker):
            user_id, _audience = await _seed_admin_user(sessionmaker)
            await _seed_passkey_credential(
                sessionmaker,
                realm_type="admin",
                principal_subject=user_id,
                sign_count=5,
            )

            login_response = await async_client.post(
                _admin_url("/api/v1/auth/login"),
                headers=_ADMIN_HEADERS,
                json={"login_or_email": "passkey-admin@example.com", "password": "PasskeyAdminP@ssword123!"},
            )
            assert login_response.status_code == 200

            options_response = await async_client.post(
                _admin_url("/api/v1/auth/passkeys/reauthentication/options"),
                headers=_ADMIN_HEADERS,
                json={"action": "admin.webhook.rotate"},
            )
            assert options_response.status_code == 200, options_response.text

            verify_response = await async_client.post(
                _admin_url("/api/v1/auth/passkeys/reauthentication/verify"),
                headers=_ADMIN_HEADERS,
                json={
                    "challengeId": options_response.json()["challengeId"],
                    "credential": _credential_payload(),
                    "action": "admin.webhook.rotate",
                },
            )
            assert verify_response.status_code == 401
            assert await _fresh_auth_grants(fake_redis) == []

            with sessionmaker() as db:
                credential = db.execute(select(PasskeyCredentialModel)).scalar_one()
                assert credential.sign_count == 5
                assert credential.clone_suspected_at is not None

                audit = (
                    db.execute(
                        select(AuditLog).where(
                            AuditLog.action == "passkey.sign_count_anomaly",
                            AuditLog.entity_id == str(credential.id),
                        )
                    )
                    .scalars()
                    .one()
                )
                assert audit.new_value["stored_sign_count"] == 5
                assert audit.new_value["new_sign_count"] == 4
                assert audit.new_value["ceremony"] == "reauthentication"
    finally:
        app.dependency_overrides.pop(get_redis, None)
        engine.dispose()
        cleanup_sqlite_file(sqlite_path)


@pytest.mark.integration
async def test_passkey_authentication_persists_real_library_sign_count_anomaly_without_session(
    async_client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_redis = FakeRedis()
    sessionmaker, engine, sqlite_path = create_realm_test_sessionmaker()
    await initialize_realm_test_database(engine)

    async def _override_redis():
        yield fake_redis

    app.dependency_overrides[get_redis] = _override_redis
    _patch_webauthn_counter_guard(monkeypatch, new_sign_count=4)

    try:
        async with override_realm_test_db(sessionmaker):
            user_id, _audience = await _seed_admin_user(sessionmaker)
            await _seed_passkey_credential(
                sessionmaker,
                realm_type="admin",
                principal_subject=user_id,
                sign_count=5,
            )

            options_response = await async_client.post(
                _admin_url("/api/v1/auth/passkeys/authentication/options"),
                headers=_ADMIN_HEADERS,
                json={"identifier": "passkey-admin@example.com"},
            )
            assert options_response.status_code == 200, options_response.text

            verify_response = await async_client.post(
                _admin_url("/api/v1/auth/passkeys/authentication/verify"),
                headers=_ADMIN_HEADERS,
                json={
                    "challengeId": options_response.json()["challengeId"],
                    "credential": _credential_payload(),
                },
            )
            assert verify_response.status_code == 401
            assert "access_token=" not in "\n".join(verify_response.headers.get_list("set-cookie"))

            with sessionmaker() as db:
                credential = db.execute(select(PasskeyCredentialModel)).scalar_one()
                assert credential.sign_count == 5
                assert credential.clone_suspected_at is not None

                audit = (
                    db.execute(
                        select(AuditLog).where(
                            AuditLog.action == "passkey.sign_count_anomaly",
                            AuditLog.entity_id == str(credential.id),
                        )
                    )
                    .scalars()
                    .one()
                )
                assert audit.new_value["stored_sign_count"] == 5
                assert audit.new_value["new_sign_count"] == 4
                assert audit.new_value["ceremony"] == "authentication"

                sessions = list(
                    db.execute(select(PrincipalSessionModel).where(PrincipalSessionModel.principal_subject == user_id))
                    .scalars()
                    .all()
                )
                assert sessions == []
    finally:
        app.dependency_overrides.pop(get_redis, None)
        engine.dispose()
        cleanup_sqlite_file(sqlite_path)


@pytest.mark.integration
async def test_passkey_wrong_origin_rejected(async_client: AsyncClient) -> None:
    sessionmaker, engine, sqlite_path = create_realm_test_sessionmaker()
    await initialize_realm_test_database(engine)

    try:
        async with override_realm_test_db(sessionmaker):
            response = await async_client.post(
                _admin_url("/api/v1/auth/passkeys/authentication/options"),
                headers={"Origin": "https://evil.example"},
                json={},
            )
            assert response.status_code == 403
    finally:
        engine.dispose()
        cleanup_sqlite_file(sqlite_path)


@pytest.mark.integration
async def test_admin_passkey_policy_patch_persists_and_blocks_registration_options(
    async_client: AsyncClient,
) -> None:
    fake_redis = FakeRedis()
    sessionmaker, engine, sqlite_path = create_realm_test_sessionmaker()
    await initialize_realm_test_database(engine)

    async def _override_redis():
        yield fake_redis

    app.dependency_overrides[get_redis] = _override_redis

    try:
        async with override_realm_test_db(sessionmaker):
            user_id, _audience = await _seed_admin_user(sessionmaker)

            login_response = await async_client.post(
                _admin_url("/api/v1/auth/login"),
                headers=_ADMIN_HEADERS,
                json={"login_or_email": "passkey-admin@example.com", "password": "PasskeyAdminP@ssword123!"},
            )
            assert login_response.status_code == 200

            policy_update_payload = {
                "registrationEnabled": False,
                "challengeTtlSeconds": 120,
                "browserTimeoutMs": 45000,
                "freshAuthTtlSeconds": 180,
                "adminCountsAsMfa": True,
                "changeReason": "policy integration test",
            }

            policy_before = await async_client.get(
                _admin_url("/api/v1/auth/passkeys/policy"),
                headers=_ADMIN_HEADERS,
            )
            assert policy_before.status_code == 200, policy_before.text
            assert policy_before.json()["registrationEnabled"] is True

            missing_fresh_auth = await async_client.patch(
                _admin_url("/api/v1/security/passkeys/policy"),
                headers=_ADMIN_HEADERS,
                json=policy_update_payload,
            )
            assert missing_fresh_auth.status_code == 403, missing_fresh_auth.text
            assert missing_fresh_auth.json()["detail"] == FRESH_AUTH_REQUIRED_DETAIL

            policy_after_missing = await async_client.get(
                _admin_url("/api/v1/auth/passkeys/policy"),
                headers=_ADMIN_HEADERS,
            )
            assert policy_after_missing.status_code == 200, policy_after_missing.text
            assert policy_after_missing.json()["registrationEnabled"] is True

            wrong_action_grant_id = await _fresh_auth_grant_id(
                fake_redis,
                sessionmaker,
                principal_subject=user_id,
                action="admin.passkeys.policy.delete",
            )
            wrong_action_response = await async_client.patch(
                _admin_url("/api/v1/security/passkeys/policy"),
                headers={FRESH_AUTH_GRANT_ID_HEADER: wrong_action_grant_id, **_ADMIN_HEADERS},
                json=policy_update_payload,
            )
            assert wrong_action_response.status_code == 403, wrong_action_response.text
            assert wrong_action_response.json()["detail"] == FRESH_AUTH_REQUIRED_DETAIL

            policy_after_wrong_action = await async_client.get(
                _admin_url("/api/v1/auth/passkeys/policy"),
                headers=_ADMIN_HEADERS,
            )
            assert policy_after_wrong_action.status_code == 200, policy_after_wrong_action.text
            assert policy_after_wrong_action.json()["registrationEnabled"] is True
            assert await _fresh_auth_grants(fake_redis) == []

            fresh_auth_grant_id = await _fresh_auth_grant_id(
                fake_redis,
                sessionmaker,
                principal_subject=user_id,
                action=_ADMIN_POLICY_UPDATE_ACTION,
            )
            update_response = await async_client.patch(
                _admin_url("/api/v1/security/passkeys/policy"),
                headers={FRESH_AUTH_GRANT_ID_HEADER: fresh_auth_grant_id, **_ADMIN_HEADERS},
                json=policy_update_payload,
            )
            assert update_response.status_code == 200, update_response.text
            updated_policy = update_response.json()
            assert updated_policy["policySource"] == "system_config"
            assert updated_policy["configuredEnabled"] is True
            assert updated_policy["registrationEnabled"] is False
            assert updated_policy["authenticationEnabled"] is True
            assert updated_policy["challengeTtlSeconds"] == 120
            assert updated_policy["browserTimeoutMs"] == 45000
            assert updated_policy["freshAuthTtlSeconds"] == 180
            assert updated_policy["adminCountsAsMfa"] is True

            policy_response = await async_client.get(
                _admin_url("/api/v1/auth/passkeys/policy"),
                headers=_ADMIN_HEADERS,
            )
            assert policy_response.status_code == 200, policy_response.text
            assert policy_response.json()["registrationEnabled"] is False
            assert await _fresh_auth_grants(fake_redis) == []

            blocked_options = await async_client.post(
                _admin_url("/api/v1/auth/passkeys/registration/options"),
                headers=_ADMIN_HEADERS,
                json={"label": "Blocked by policy"},
            )
            assert blocked_options.status_code == 404, blocked_options.text
    finally:
        app.dependency_overrides.pop(get_redis, None)
        engine.dispose()
        cleanup_sqlite_file(sqlite_path)


@pytest.mark.integration
async def test_partner_workspace_passkey_policy_patch_updates_workspace_settings(
    async_client: AsyncClient,
) -> None:
    fake_redis = FakeRedis()
    sessionmaker, engine, sqlite_path = create_realm_test_sessionmaker()
    await initialize_realm_test_database(engine)

    async def _override_redis():
        yield fake_redis

    app.dependency_overrides[get_redis] = _override_redis

    try:
        async with override_realm_test_db(sessionmaker):
            _admin_user_id, _audience = await _seed_realm_admin_user(
                sessionmaker,
                login="policy_admin",
                email="policy-admin@example.com",
                password="PolicyAdminP@ssword123!",
                role="admin",
            )
            owner_user_id, _audience = await _seed_realm_admin_user(
                sessionmaker,
                login="policy_partner_owner",
                email="policy-owner@example.com",
                password="PolicyOwnerP@ssword123!",
                role="viewer",
            )
            await _seed_default_realm(sessionmaker, "partner")

            admin_token = await _login_token(
                async_client,
                login_or_email="policy-admin@example.com",
                password="PolicyAdminP@ssword123!",
            )
            create_workspace = await async_client.post(
                _admin_url("/api/v1/admin/partner-workspaces"),
                headers={"Authorization": f"Bearer {admin_token}", **_ADMIN_HEADERS},
                json={
                    "display_name": "Policy Workspace",
                    "owner_admin_user_id": owner_user_id,
                },
            )
            assert create_workspace.status_code == 201, create_workspace.text
            workspace_id = create_workspace.json()["id"]
            partner_policy_action = f"partner.passkeys.policy.update:{workspace_id}"

            owner_token = await _login_token(
                async_client,
                login_or_email="policy-owner@example.com",
                password="PolicyOwnerP@ssword123!",
            )
            policy_update_payload = {
                "preferPasskeys": True,
                "requireMfaForWorkspace": True,
                "changeReason": "partner workspace rollout",
            }

            settings_before = await async_client.get(
                _admin_url(f"/api/v1/partner-workspaces/{workspace_id}/settings"),
                headers={"Authorization": f"Bearer {owner_token}", **_ADMIN_HEADERS},
            )
            assert settings_before.status_code == 200, settings_before.text
            assert settings_before.json()["prefer_passkeys"] is False
            assert settings_before.json()["require_mfa_for_workspace"] is False

            missing_fresh_auth = await async_client.patch(
                _admin_url(f"/api/v1/partner-workspaces/{workspace_id}/security/passkeys/policy"),
                headers={"Authorization": f"Bearer {owner_token}", **_ADMIN_HEADERS},
                json=policy_update_payload,
            )
            assert missing_fresh_auth.status_code == 403, missing_fresh_auth.text
            assert missing_fresh_auth.json()["detail"] == FRESH_AUTH_REQUIRED_DETAIL

            settings_after_missing = await async_client.get(
                _admin_url(f"/api/v1/partner-workspaces/{workspace_id}/settings"),
                headers={"Authorization": f"Bearer {owner_token}", **_ADMIN_HEADERS},
            )
            assert settings_after_missing.status_code == 200, settings_after_missing.text
            assert settings_after_missing.json()["prefer_passkeys"] is False
            assert settings_after_missing.json()["require_mfa_for_workspace"] is False

            wrong_realm_grant_id = await _fresh_auth_grant_id(
                fake_redis,
                sessionmaker,
                principal_subject=owner_user_id,
                principal_class="partner_operator",
                realm_type="partner",
                action=partner_policy_action,
            )
            wrong_realm_response = await async_client.patch(
                _admin_url(f"/api/v1/partner-workspaces/{workspace_id}/security/passkeys/policy"),
                headers={
                    "Authorization": f"Bearer {owner_token}",
                    FRESH_AUTH_GRANT_ID_HEADER: wrong_realm_grant_id,
                    **_ADMIN_HEADERS,
                },
                json=policy_update_payload,
            )
            assert wrong_realm_response.status_code == 403, wrong_realm_response.text
            assert wrong_realm_response.json()["detail"] == FRESH_AUTH_REQUIRED_DETAIL

            settings_after_wrong_realm = await async_client.get(
                _admin_url(f"/api/v1/partner-workspaces/{workspace_id}/settings"),
                headers={"Authorization": f"Bearer {owner_token}", **_ADMIN_HEADERS},
            )
            assert settings_after_wrong_realm.status_code == 200, settings_after_wrong_realm.text
            assert settings_after_wrong_realm.json()["prefer_passkeys"] is False
            assert settings_after_wrong_realm.json()["require_mfa_for_workspace"] is False
            assert await _fresh_auth_grants(fake_redis) == []

            fresh_auth_grant_id = await _fresh_auth_grant_id(
                fake_redis,
                sessionmaker,
                principal_subject=owner_user_id,
                action=partner_policy_action,
            )
            update_policy = await async_client.patch(
                _admin_url(f"/api/v1/partner-workspaces/{workspace_id}/security/passkeys/policy"),
                headers={
                    "Authorization": f"Bearer {owner_token}",
                    FRESH_AUTH_GRANT_ID_HEADER: fresh_auth_grant_id,
                    **_ADMIN_HEADERS,
                },
                json=policy_update_payload,
            )
            assert update_policy.status_code == 200, update_policy.text
            policy_payload = update_policy.json()
            assert policy_payload["workspacePasskeysPreferred"] is True
            assert policy_payload["workspaceMfaRequired"] is True
            assert policy_payload["policy"]["workspacePolicyEnabled"] is True

            settings_response = await async_client.get(
                _admin_url(f"/api/v1/partner-workspaces/{workspace_id}/settings"),
                headers={"Authorization": f"Bearer {owner_token}", **_ADMIN_HEADERS},
            )
            assert settings_response.status_code == 200, settings_response.text
            settings_payload = settings_response.json()
            assert settings_payload["prefer_passkeys"] is True
            assert settings_payload["require_mfa_for_workspace"] is True
            assert await _fresh_auth_grants(fake_redis) == []
    finally:
        app.dependency_overrides.pop(get_redis, None)
        engine.dispose()
        cleanup_sqlite_file(sqlite_path)


@pytest.mark.integration
async def test_revoked_passkey_authentication_is_rejected(
    async_client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_redis = FakeRedis()
    sessionmaker, engine, sqlite_path = create_realm_test_sessionmaker()
    await initialize_realm_test_database(engine)

    async def _override_redis():
        yield fake_redis

    app.dependency_overrides[get_redis] = _override_redis
    monkeypatch.setattr(
        "src.application.services.passkey_webauthn.PasskeyWebAuthnService.verify_authentication",
        lambda self, *, payload, challenge, credential: _fake_authentication_verification(),
    )

    try:
        async with override_realm_test_db(sessionmaker):
            user_id, _audience = await _seed_admin_user(sessionmaker)
            with sessionmaker() as db:
                realm = await AuthRealmRepository(SyncSessionAdapter(db)).get_or_create_default_realm("admin")
                db.add(
                    PasskeyCredentialModel(
                        credential_id=_RAW_CREDENTIAL_ID,
                        credential_id_hash=_CREDENTIAL_HASH,
                        credential_public_key=b"credential-public-key",
                        sign_count=1,
                        auth_realm_id=realm.id,
                        realm_key="admin",
                        audience=realm.audience,
                        principal_class="admin",
                        principal_subject=user_id,
                        user_handle="handle",
                        label="Revoked",
                        surface="admin",
                        rp_id=settings.passkey_rp_id,
                        status="revoked",
                        revoked_at=datetime.now(UTC),
                    )
                )
                db.commit()

            options_response = await async_client.post(
                _admin_url("/api/v1/auth/passkeys/authentication/options"),
                headers=_ADMIN_HEADERS,
                json={},
            )
            assert options_response.status_code == 200

            verify_response = await async_client.post(
                _admin_url("/api/v1/auth/passkeys/authentication/verify"),
                headers=_ADMIN_HEADERS,
                json={
                    "challengeId": options_response.json()["challengeId"],
                    "credential": _credential_payload(),
                },
            )
            assert verify_response.status_code == 401
    finally:
        app.dependency_overrides.pop(get_redis, None)
        engine.dispose()
        cleanup_sqlite_file(sqlite_path)


@pytest.mark.integration
async def test_passkey_challenge_store_consumes_once_and_rejects_expired() -> None:
    fake_redis = FakeRedis()
    store = PasskeyChallengeStore(fake_redis)
    record = await store.create(
        challenge=b"challenge",
        ceremony="authentication",
        rp_id="cyber-vpn.net",
        expected_origin="https://admin.cyber-vpn.net",
        auth_realm_id="realm",
        realm_key="admin",
        audience="cybervpn:admin",
        principal_class="admin",
        principal_subject="subject",
        user_handle="handle",
        identifier_hash=None,
        require_user_verification=True,
    )

    consumed = await store.consume(record.challenge_id, expected_ceremony="authentication")
    assert consumed.challenge_hash == sha256(b"challenge").hexdigest()
    with pytest.raises(PasskeyChallengeError):
        await store.consume(record.challenge_id, expected_ceremony="authentication")

    expired = await store.create(
        challenge=b"expired",
        ceremony="authentication",
        rp_id="cyber-vpn.net",
        expected_origin="https://admin.cyber-vpn.net",
        auth_realm_id="realm",
        realm_key="admin",
        audience="cybervpn:admin",
        principal_class="admin",
        principal_subject="subject",
        user_handle="handle",
        identifier_hash=None,
        require_user_verification=True,
    )
    raw = await fake_redis.get(f"passkey:challenge:{expired.challenge_id}")
    assert isinstance(raw, str)
    raw_payload = json.loads(raw)
    raw_payload["expires_at"] = (datetime.now(UTC) - timedelta(seconds=1)).isoformat()
    await fake_redis.set(f"passkey:challenge:{expired.challenge_id}", json.dumps(raw_payload))
    with pytest.raises(PasskeyChallengeError):
        await store.consume(expired.challenge_id, expected_ceremony="authentication")
