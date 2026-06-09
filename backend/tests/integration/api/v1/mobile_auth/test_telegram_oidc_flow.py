"""Integration tests for mobile Telegram OIDC authentication route."""

from datetime import UTC, datetime, timedelta
from hashlib import sha256
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
from prometheus_client import REGISTRY
from sqlalchemy import select

from src.application.services.auth_service import AuthService
from src.application.services.auth_session_issuer import hash_device_key
from src.application.services.telegram_oidc_auth import (
    InvalidTelegramOIDCTokenError,
    TelegramOIDCUserInfo,
)
from src.domain.entities.auth_realm import DEFAULT_AUTH_REALMS, stable_auth_realm_id
from src.infrastructure.database.models.mobile_device_model import MobileDeviceModel
from src.infrastructure.database.models.mobile_user_model import MobileUserModel
from src.infrastructure.database.models.principal_session_model import PrincipalSessionModel
from src.infrastructure.database.models.refresh_token_model import RefreshToken
from src.infrastructure.database.models.user_device_model import UserDeviceModel
from src.infrastructure.database.repositories.auth_realm_repo import AuthRealmRepository
from src.infrastructure.database.repositories.mobile_user_repo import MobileUserRepository
from src.infrastructure.totp.totp_service import TOTPService
from src.main import app
from src.presentation.api.v1.mobile_auth.routes import _get_subscription_client
from src.presentation.dependencies.database import get_db
from src.presentation.dependencies.mobile_rate_limit import check_login_rate_limit


def _payload() -> dict:
    return {
        "id_token": "telegram-id-token",
        "device": {
            "device_id": "123e4567-e89b-12d3-a456-426614174000",
            "platform": "ios",
            "platform_id": "ios-vendor-id",
            "os_version": "17.4",
            "app_version": "1.2.3",
            "device_model": "iPhone 15 Pro",
            "push_token": None,
        },
    }


def _password_login_payload(
    device_id: str = "123e4567-e89b-12d3-a456-426614174000",
    *,
    email: str | None = None,
    password: str = "MobileSession123!",
    device_model: str = "iPhone 15 Pro",
    platform: str = "ios",
) -> dict:
    return {
        "email": email or f"mobile-session-{uuid4().hex[:8]}@example.com",
        "password": password,
        "device": {
            "device_id": device_id,
            "platform": platform,
            "platform_id": f"{platform}-vendor-{device_id[:8]}",
            "os_version": "17.4",
            "app_version": "1.2.3",
            "device_model": device_model,
            "push_token": "push-token",
        },
    }


async def _create_password_mobile_user(db, payload: dict) -> MobileUserModel:
    auth_service = AuthService()
    user = MobileUserModel(
        id=uuid4(),
        auth_realm_id=stable_auth_realm_id(str(DEFAULT_AUTH_REALMS["customer"]["realm_key"])),
        email=payload["email"],
        password_hash=await auth_service.hash_password(payload["password"]),
        username=f"mobile_session_{uuid4().hex[:8]}",
        is_active=True,
        status="active",
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


@pytest.fixture(autouse=True)
def _disable_mobile_login_rate_limit():
    app.dependency_overrides[check_login_rate_limit] = lambda: None
    try:
        yield
    finally:
        app.dependency_overrides.pop(check_login_rate_limit, None)


@pytest.mark.integration
async def test_mobile_password_login_persists_shared_session_and_refresh_rotates(async_client, db):
    payload = _password_login_payload()
    user = await _create_password_mobile_user(db, payload)
    device_id = payload["device"]["device_id"]

    async def override_db():
        yield db

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[_get_subscription_client] = lambda: None

    try:
        login_response = await async_client.post("/api/v1/mobile/auth/login", json=payload)

        assert login_response.status_code == 200
        login_body = login_response.json()
        refresh_token = login_body["tokens"]["refresh_token"]
        refresh_record = (
            await db.execute(
                select(RefreshToken).where(
                    RefreshToken.token_hash == sha256(refresh_token.encode()).hexdigest()
                )
            )
        ).scalar_one()
        assert refresh_record.principal_session_id is not None
        assert refresh_record.family_id is not None
        assert refresh_record.parent_token_id is None
        assert refresh_record.consumed_at is None

        principal_session = await db.get(PrincipalSessionModel, refresh_record.principal_session_id)
        assert principal_session is not None
        assert principal_session.current_refresh_token_id == refresh_record.id
        assert principal_session.principal_subject == str(user.id)
        assert principal_session.principal_class == "customer"
        assert principal_session.user_device_id is not None

        user_device = await db.get(UserDeviceModel, principal_session.user_device_id)
        assert user_device is not None
        assert user_device.device_key_hash == hash_device_key(device_id)
        assert refresh_record.device_id == str(user_device.id)

        refresh_response = await async_client.post(
            "/api/v1/mobile/auth/refresh",
            json={"refresh_token": refresh_token, "device_id": device_id},
        )
        assert refresh_response.status_code == 200
        rotated_refresh_token = refresh_response.json()["refresh_token"]
        rotated_refresh_record = (
            await db.execute(
                select(RefreshToken).where(
                    RefreshToken.token_hash == sha256(rotated_refresh_token.encode()).hexdigest()
                )
            )
        ).scalar_one()

        await db.refresh(refresh_record)
        await db.refresh(principal_session)
        assert refresh_record.consumed_at is not None
        assert refresh_record.revoked_reason == "rotated"
        assert refresh_record.replaced_by_token_id == rotated_refresh_record.id
        assert rotated_refresh_record.parent_token_id == refresh_record.id
        assert rotated_refresh_record.family_id == refresh_record.family_id
        assert rotated_refresh_record.principal_session_id == principal_session.id
        assert principal_session.current_refresh_token_id == rotated_refresh_record.id

        refresh_record.consumed_at = datetime.now(UTC) - timedelta(seconds=20)
        await db.commit()
        replay_response = await async_client.post(
            "/api/v1/mobile/auth/refresh",
            json={"refresh_token": refresh_token, "device_id": device_id},
        )
        assert replay_response.status_code == 401

        replayed_family = (
            (
                await db.execute(
                    select(RefreshToken).where(RefreshToken.family_id == refresh_record.family_id)
                )
            )
            .scalars()
            .all()
        )
        assert len(replayed_family) == 2
        assert {record.revoked_reason for record in replayed_family} == {"replay_detected"}
        assert all(record.revoked_at is not None for record in replayed_family)
        await db.refresh(principal_session)
        assert principal_session.status == "revoked"
    finally:
        app.dependency_overrides.pop(get_db, None)
        app.dependency_overrides.pop(_get_subscription_client, None)


@pytest.mark.integration
async def test_mobile_logout_revokes_current_shared_session(async_client, db):
    payload = _password_login_payload(device_id="223e4567-e89b-12d3-a456-426614174000")
    await _create_password_mobile_user(db, payload)
    device_id = payload["device"]["device_id"]

    async def override_db():
        yield db

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[_get_subscription_client] = lambda: None

    try:
        login_response = await async_client.post("/api/v1/mobile/auth/login", json=payload)
        assert login_response.status_code == 200
        refresh_token = login_response.json()["tokens"]["refresh_token"]
        refresh_record = (
            await db.execute(
                select(RefreshToken).where(
                    RefreshToken.token_hash == sha256(refresh_token.encode()).hexdigest()
                )
            )
        ).scalar_one()
        principal_session = await db.get(PrincipalSessionModel, refresh_record.principal_session_id)
        assert principal_session is not None

        logout_response = await async_client.post(
            "/api/v1/mobile/auth/logout",
            json={"refresh_token": refresh_token, "device_id": device_id},
        )
        assert logout_response.status_code == 204

        await db.refresh(refresh_record)
        await db.refresh(principal_session)
        assert refresh_record.revoked_at is not None
        assert refresh_record.revoked_reason == "logout"
        assert principal_session.status == "revoked"
        assert principal_session.revoked_at is not None

        refresh_response = await async_client.post(
            "/api/v1/mobile/auth/refresh",
            json={"refresh_token": refresh_token, "device_id": device_id},
        )
        assert refresh_response.status_code == 401
    finally:
        app.dependency_overrides.pop(get_db, None)
        app.dependency_overrides.pop(_get_subscription_client, None)


@pytest.mark.integration
async def test_mobile_remove_device_revokes_selected_session_only(async_client, db):
    device_one_id = "323e4567-e89b-12d3-a456-426614174000"
    device_two_id = "423e4567-e89b-12d3-a456-426614174000"
    first_payload = _password_login_payload(device_id=device_one_id, device_model="iPhone 15 Pro")
    second_payload = _password_login_payload(
        device_id=device_two_id,
        email=first_payload["email"],
        password=first_payload["password"],
        device_model="Pixel 9",
        platform="android",
    )
    user = await _create_password_mobile_user(db, first_payload)

    async def override_db():
        yield db

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[_get_subscription_client] = lambda: None

    try:
        first_login = await async_client.post("/api/v1/mobile/auth/login", json=first_payload)
        second_login = await async_client.post("/api/v1/mobile/auth/login", json=second_payload)
        assert first_login.status_code == 200
        assert second_login.status_code == 200
        first_access_token = first_login.json()["tokens"]["access_token"]

        list_response = await async_client.get(
            "/api/v1/mobile/auth/devices",
            headers={"Authorization": f"Bearer {first_access_token}"},
        )
        assert list_response.status_code == 200
        assert {device["id"] for device in list_response.json()} == {device_one_id, device_two_id}

        delete_response = await async_client.delete(
            f"/api/v1/mobile/auth/devices/{device_two_id}",
            headers={"Authorization": f"Bearer {first_access_token}"},
        )
        assert delete_response.status_code == 204

        device_one = (
            await db.execute(
                select(UserDeviceModel).where(
                    UserDeviceModel.principal_subject == str(user.id),
                    UserDeviceModel.device_key_hash == hash_device_key(device_one_id),
                )
            )
        ).scalar_one()
        device_two = (
            await db.execute(
                select(UserDeviceModel).where(
                    UserDeviceModel.principal_subject == str(user.id),
                    UserDeviceModel.device_key_hash == hash_device_key(device_two_id),
                )
            )
        ).scalar_one()
        await db.refresh(device_one)
        await db.refresh(device_two)
        assert device_one.revoked_at is None
        assert device_two.revoked_at is not None
        assert device_two.revoked_reason == "mobile_device_removed"

        sessions = (
            (
                await db.execute(
                    select(PrincipalSessionModel).where(
                        PrincipalSessionModel.principal_subject == str(user.id)
                    )
                )
            )
            .scalars()
            .all()
        )
        session_by_device = {session.user_device_id: session for session in sessions}
        assert session_by_device[device_one.id].status == "active"
        assert session_by_device[device_two.id].status == "revoked"

        list_after_delete = await async_client.get(
            "/api/v1/mobile/auth/devices",
            headers={"Authorization": f"Bearer {first_access_token}"},
        )
        assert list_after_delete.status_code == 200
        assert {device["id"] for device in list_after_delete.json()} == {device_one_id}
    finally:
        app.dependency_overrides.pop(get_db, None)
        app.dependency_overrides.pop(_get_subscription_client, None)


@pytest.mark.integration
async def test_route_creates_new_user_and_persists_subject(async_client, db, monkeypatch):
    monkeypatch.setattr("src.presentation.api.v1.mobile_auth.routes.settings.registration_enabled", True)
    monkeypatch.setattr("src.presentation.api.v1.mobile_auth.routes.settings.registration_invite_required", False)
    subject = f"telegram-subject-{uuid4()}"
    telegram_id = (uuid4().int % 9_000_000_000) + 100_000_000
    telegram_user = TelegramOIDCUserInfo(
        subject=subject,
        telegram_id=telegram_id,
        name="Telegram Integration User",
        preferred_username=f"tg_user_{uuid4().hex[:8]}",
        picture=None,
        phone_number=None,
        issued_at=datetime.now(UTC),
        expires_at=datetime.now(UTC) + timedelta(minutes=15),
    )

    async def override_db():
        yield db

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[_get_subscription_client] = lambda: None

    try:
        before_started = REGISTRY.get_sample_value(
            "telegram_native_login_started_total",
            {"platform": "ios"},
        ) or 0
        before_completed = REGISTRY.get_sample_value(
            "telegram_native_login_completed_total",
            {"platform": "ios"},
        ) or 0
        before_created = REGISTRY.get_sample_value("telegram_oidc_user_created_total") or 0
        before_resolved = REGISTRY.get_sample_value(
            "telegram_oidc_user_resolved_total",
            {"path": "new_user"},
        ) or 0
        before_device = REGISTRY.get_sample_value(
            "telegram_oidc_device_registered_total",
            {"platform": "ios", "action": "created"},
        ) or 0

        with (
            patch(
                "src.presentation.api.v1.mobile_auth.routes.TelegramOIDCAuthService.validate_id_token",
                new=AsyncMock(return_value=telegram_user),
            ),
            patch("src.presentation.api.v1.mobile_auth.routes.sync_auth_security_posture", new=AsyncMock()),
        ):
            response = await async_client.post("/api/v1/mobile/auth/telegram/oidc", json=_payload())

        assert response.status_code == 200
        body = response.json()
        assert body["is_new_user"] is True
        assert body["user"]["telegram_id"] == telegram_id
        assert body["user"]["telegram_username"] == telegram_user.preferred_username
        assert body["tokens"]["access_token"]
        assert body["tokens"]["refresh_token"]
        assert (
            REGISTRY.get_sample_value(
                "telegram_native_login_started_total",
                {"platform": "ios"},
            )
            or 0
        ) > before_started
        assert (
            REGISTRY.get_sample_value(
                "telegram_native_login_completed_total",
                {"platform": "ios"},
            )
            or 0
        ) > before_completed
        assert (REGISTRY.get_sample_value("telegram_oidc_user_created_total") or 0) > before_created
        assert (
            REGISTRY.get_sample_value(
                "telegram_oidc_user_resolved_total",
                {"path": "new_user"},
            )
            or 0
        ) > before_resolved
        assert (
            REGISTRY.get_sample_value(
                "telegram_oidc_device_registered_total",
                {"platform": "ios", "action": "created"},
            )
            or 0
        ) > before_device

        created_user = await MobileUserRepository(db).get_by_telegram_subject(subject)
        assert created_user is not None
        assert created_user.telegram_id == telegram_id
        assert created_user.password_hash
    finally:
        app.dependency_overrides.pop(get_db, None)
        app.dependency_overrides.pop(_get_subscription_client, None)


@pytest.mark.integration
async def test_route_backfills_subject_from_legacy_telegram_id(async_client, db):
    auth_service = AuthService()
    telegram_id = (uuid4().int % 9_000_000_000) + 100_000_000
    legacy_user = MobileUserModel(
        id=uuid4(),
        email=f"tg-legacy-{uuid4().hex[:8]}@telegram.local",
        password_hash=await auth_service.hash_password("LegacyPassword123!"),
        username=f"legacy_tg_{uuid4().hex[:8]}",
        telegram_id=telegram_id,
        telegram_username="legacy_user",
        is_active=True,
        status="active",
    )
    db.add(legacy_user)
    await db.commit()
    await db.refresh(legacy_user)

    subject = f"telegram-subject-{uuid4()}"
    telegram_user = TelegramOIDCUserInfo(
        subject=subject,
        telegram_id=telegram_id,
        name="Legacy Telegram User",
        preferred_username="legacy_user_updated",
        picture=None,
        phone_number=None,
        issued_at=datetime.now(UTC),
        expires_at=datetime.now(UTC) + timedelta(minutes=15),
    )

    async def override_db():
        yield db

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[_get_subscription_client] = lambda: None

    try:
        with (
            patch(
                "src.presentation.api.v1.mobile_auth.routes.TelegramOIDCAuthService.validate_id_token",
                new=AsyncMock(return_value=telegram_user),
            ),
            patch("src.presentation.api.v1.mobile_auth.routes.sync_auth_security_posture", new=AsyncMock()),
        ):
            response = await async_client.post("/api/v1/mobile/auth/telegram/oidc", json=_payload())

        assert response.status_code == 200
        body = response.json()
        assert body["is_new_user"] is False

        await db.refresh(legacy_user)
        assert legacy_user.telegram_subject == subject
        assert legacy_user.telegram_username == "legacy_user_updated"
    finally:
        app.dependency_overrides.pop(get_db, None)
        app.dependency_overrides.pop(_get_subscription_client, None)


@pytest.mark.integration
async def test_route_maps_invalid_token_to_401(async_client, db):
    async def override_db():
        yield db

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[_get_subscription_client] = lambda: None

    try:
        before_failed = REGISTRY.get_sample_value(
            "telegram_native_login_failed_total",
            {"platform": "ios", "reason": "signature_invalid"},
        ) or 0
        before_validation_failed = REGISTRY.get_sample_value(
            "telegram_oidc_token_validation_failed_total",
            {"reason": "signature_invalid"},
        ) or 0

        with patch(
            "src.presentation.api.v1.mobile_auth.routes.TelegramOIDCAuthService.validate_id_token",
            new=AsyncMock(
                side_effect=InvalidTelegramOIDCTokenError(
                    "Telegram ID token signature is invalid",
                    reason="signature_invalid",
                )
            ),
        ):
            response = await async_client.post("/api/v1/mobile/auth/telegram/oidc", json=_payload())

        assert response.status_code == 401
        body = response.json()
        assert body["detail"]["code"] == "INVALID_TELEGRAM_ID_TOKEN"
        assert body["detail"]["details"]["reason"] == "signature_invalid"
        assert (
            REGISTRY.get_sample_value(
                "telegram_native_login_failed_total",
                {"platform": "ios", "reason": "signature_invalid"},
            )
            or 0
        ) > before_failed
        assert (
            REGISTRY.get_sample_value(
                "telegram_oidc_token_validation_failed_total",
                {"reason": "signature_invalid"},
            )
            or 0
        ) > before_validation_failed
    finally:
        app.dependency_overrides.pop(get_db, None)
        app.dependency_overrides.pop(_get_subscription_client, None)


@pytest.mark.integration
async def test_route_returns_pending_2fa_and_completion_issues_session(async_client, db):
    auth_service = AuthService()
    totp_service = TOTPService()
    secret = totp_service.generate_secret()
    telegram_id = (uuid4().int % 9_000_000_000) + 100_000_000
    subject = f"telegram-subject-{uuid4()}"

    user = MobileUserModel(
        id=uuid4(),
        auth_realm_id=stable_auth_realm_id(str(DEFAULT_AUTH_REALMS["customer"]["realm_key"])),
        email=f"tg-2fa-{uuid4().hex[:8]}@telegram.local",
        password_hash=await auth_service.hash_password("Telegram2FA123!"),
        username=f"tg_2fa_{uuid4().hex[:8]}",
        telegram_subject=subject,
        telegram_id=telegram_id,
        telegram_username="tg_2fa_user",
        totp_secret=secret,
        totp_enabled=True,
        is_active=True,
        status="active",
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    telegram_user = TelegramOIDCUserInfo(
        subject=subject,
        telegram_id=telegram_id,
        name="Telegram Two Factor User",
        preferred_username="tg_2fa_user",
        picture=None,
        phone_number=None,
        issued_at=datetime.now(UTC),
        expires_at=datetime.now(UTC) + timedelta(minutes=15),
    )

    async def override_db():
        yield db

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[_get_subscription_client] = lambda: None

    try:
        before_requires_2fa = REGISTRY.get_sample_value(
            "telegram_oidc_requires_2fa_total",
            {"platform": "ios"},
        ) or 0
        before_completed = REGISTRY.get_sample_value(
            "telegram_native_login_completed_total",
            {"platform": "ios"},
        ) or 0

        with (
            patch(
                "src.presentation.api.v1.mobile_auth.routes.TelegramOIDCAuthService.validate_id_token",
                new=AsyncMock(return_value=telegram_user),
            ),
            patch("src.presentation.api.v1.mobile_auth.routes.sync_auth_security_posture", new=AsyncMock()),
        ):
            response = await async_client.post("/api/v1/mobile/auth/telegram/oidc", json=_payload())

        assert response.status_code == 200
        body = response.json()
        assert body["requires_2fa"] is True
        assert body["method"] == "totp"
        assert body["tokens"] is None
        pending_token = body["tfa_token"]
        assert (
            REGISTRY.get_sample_value(
                "telegram_oidc_requires_2fa_total",
                {"platform": "ios"},
            )
            or 0
        ) > before_requires_2fa

        completion_response = await async_client.post(
            "/api/v1/mobile/auth/2fa/complete",
            json={"code": totp_service.get_current_code(secret)},
            headers={"Authorization": f"Bearer {pending_token}"},
        )

        assert completion_response.status_code == 200
        completion_body = completion_response.json()
        assert completion_body["requires_2fa"] is False
        assert completion_body["tokens"]["access_token"]
        assert completion_body["tokens"]["refresh_token"]
        assert (
            REGISTRY.get_sample_value(
                "telegram_native_login_completed_total",
                {"platform": "ios"},
            )
            or 0
        ) > before_completed

        device = await MobileUserRepository(db).get_by_id_with_devices(user.id)
        assert device is not None
        assert len(device.devices) == 1
        assert device.devices[0].device_id == _payload()["device"]["device_id"]
    finally:
        app.dependency_overrides.pop(get_db, None)
        app.dependency_overrides.pop(_get_subscription_client, None)


@pytest.mark.integration
async def test_authenticated_route_links_telegram_identity(async_client, db):
    auth_service = AuthService()
    user = MobileUserModel(
        id=uuid4(),
        auth_realm_id=stable_auth_realm_id(str(DEFAULT_AUTH_REALMS["customer"]["realm_key"])),
        email=f"tg-link-{uuid4().hex[:8]}@example.com",
        password_hash=await auth_service.hash_password("TelegramLink123!"),
        username=f"tg_link_{uuid4().hex[:8]}",
        is_active=True,
        status="active",
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    access_token, _jti, _exp = auth_service.create_access_token(
        subject=str(user.id),
        role="mobile_user",
        audience=str(DEFAULT_AUTH_REALMS["customer"]["audience"]),
        principal_type="customer",
        realm_id=str(user.auth_realm_id),
        realm_key=str(DEFAULT_AUTH_REALMS["customer"]["realm_key"]),
        scope_family="customer",
    )

    telegram_user = TelegramOIDCUserInfo(
        subject=f"telegram-link-subject-{uuid4()}",
        telegram_id=(uuid4().int % 9_000_000_000) + 100_000_000,
        name="Linked Telegram User",
        preferred_username=f"linked_{uuid4().hex[:8]}",
        picture=None,
        phone_number=None,
        issued_at=datetime.now(UTC),
        expires_at=datetime.now(UTC) + timedelta(minutes=15),
    )

    async def override_db():
        yield db

    app.dependency_overrides[get_db] = override_db

    try:
        with (
            patch(
                "src.presentation.api.v1.mobile_auth.routes.TelegramOIDCAuthService.validate_id_token",
                new=AsyncMock(return_value=telegram_user),
            ),
            patch("src.presentation.api.v1.mobile_auth.routes.sync_auth_security_posture", new=AsyncMock()),
        ):
            response = await async_client.post(
                "/api/v1/mobile/auth/telegram/link",
                json={"id_token": "telegram-id-token"},
                headers={"Authorization": f"Bearer {access_token}"},
            )

        assert response.status_code == 200
        body = response.json()
        assert body["linked"] is True
        assert body["provider"] == "telegram"
        assert body["telegram_username"] == telegram_user.preferred_username

        await db.refresh(user)
        assert user.telegram_subject == telegram_user.subject
        assert user.telegram_id == telegram_user.telegram_id
        assert user.telegram_username == telegram_user.preferred_username
    finally:
        app.dependency_overrides.pop(get_db, None)


@pytest.mark.integration
async def test_authenticated_route_link_conflict_tracks_metric(async_client, db):
    auth_service = AuthService()
    linked_user = MobileUserModel(
        id=uuid4(),
        auth_realm_id=stable_auth_realm_id(str(DEFAULT_AUTH_REALMS["customer"]["realm_key"])),
        email=f"tg-linked-{uuid4().hex[:8]}@example.com",
        password_hash=await auth_service.hash_password("TelegramLink123!"),
        username=f"tg_linked_{uuid4().hex[:8]}",
        telegram_subject=f"telegram-link-conflict-{uuid4()}",
        telegram_id=(uuid4().int % 9_000_000_000) + 100_000_000,
        telegram_username=f"linked_{uuid4().hex[:8]}",
        is_active=True,
        status="active",
    )
    current_user = MobileUserModel(
        id=uuid4(),
        auth_realm_id=stable_auth_realm_id(str(DEFAULT_AUTH_REALMS["customer"]["realm_key"])),
        email=f"tg-current-{uuid4().hex[:8]}@example.com",
        password_hash=await auth_service.hash_password("TelegramLink123!"),
        username=f"tg_current_{uuid4().hex[:8]}",
        is_active=True,
        status="active",
    )
    db.add(linked_user)
    db.add(current_user)
    await db.commit()
    await db.refresh(linked_user)
    await db.refresh(current_user)

    access_token, _jti, _exp = auth_service.create_access_token(
        subject=str(current_user.id),
        role="mobile_user",
        audience=str(DEFAULT_AUTH_REALMS["customer"]["audience"]),
        principal_type="customer",
        realm_id=str(current_user.auth_realm_id),
        realm_key=str(DEFAULT_AUTH_REALMS["customer"]["realm_key"]),
        scope_family="customer",
    )

    telegram_user = TelegramOIDCUserInfo(
        subject=linked_user.telegram_subject,
        telegram_id=linked_user.telegram_id,
        name="Conflict Telegram User",
        preferred_username=linked_user.telegram_username,
        picture=None,
        phone_number=None,
        issued_at=datetime.now(UTC),
        expires_at=datetime.now(UTC) + timedelta(minutes=15),
    )

    async def override_db():
        yield db

    app.dependency_overrides[get_db] = override_db

    try:
        before_conflicts = REGISTRY.get_sample_value(
            "telegram_oidc_user_link_conflict_total",
            {"reason": "subject_conflict"},
        ) or 0

        with patch(
            "src.presentation.api.v1.mobile_auth.routes.TelegramOIDCAuthService.validate_id_token",
            new=AsyncMock(return_value=telegram_user),
        ):
            response = await async_client.post(
                "/api/v1/mobile/auth/telegram/link",
                json={"id_token": "telegram-id-token"},
                headers={"Authorization": f"Bearer {access_token}"},
            )

        assert response.status_code == 409
        body = response.json()
        assert body["detail"]["code"] == "TELEGRAM_IDENTITY_ALREADY_LINKED"
        assert (
            REGISTRY.get_sample_value(
                "telegram_oidc_user_link_conflict_total",
                {"reason": "subject_conflict"},
            )
            or 0
        ) > before_conflicts
    finally:
        app.dependency_overrides.pop(get_db, None)


@pytest.mark.integration
async def test_mobile_me_exposes_profile_contract(async_client, db):
    auth_service = AuthService()
    user = MobileUserModel(
        id=uuid4(),
        auth_realm_id=stable_auth_realm_id(str(DEFAULT_AUTH_REALMS["customer"]["realm_key"])),
        email=f"mobile-me-{uuid4().hex[:8]}@example.com",
        password_hash=await auth_service.hash_password("MobileMe123!"),
        username=f"mobile_me_{uuid4().hex[:8]}",
        telegram_subject=f"telegram-subject-{uuid4()}",
        telegram_id=(uuid4().int % 9_000_000_000) + 100_000_000,
        telegram_username=f"mobile_me_tg_{uuid4().hex[:8]}",
        totp_secret="totp-secret",
        totp_enabled=True,
        is_active=True,
        status="active",
        last_login_at=datetime.now(UTC),
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    access_token, _jti, _exp = auth_service.create_access_token(
        subject=str(user.id),
        role="mobile_user",
        extra={"device_id": "current-device"},
        audience=str(DEFAULT_AUTH_REALMS["customer"]["audience"]),
        principal_type="customer",
        realm_id=str(user.auth_realm_id),
        realm_key=str(DEFAULT_AUTH_REALMS["customer"]["realm_key"]),
        scope_family="customer",
    )

    async def override_db():
        yield db

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[_get_subscription_client] = lambda: None

    try:
        response = await async_client.get(
            "/api/v1/mobile/auth/me",
            headers={"Authorization": f"Bearer {access_token}"},
        )

        assert response.status_code == 200
        body = response.json()
        assert body["id"] == str(user.id)
        assert body["email"] == user.email
        assert body["telegram_id"] == user.telegram_id
        assert body["telegram_username"] == user.telegram_username
        assert body["is_email_verified"] is True
        assert body["is_2fa_enabled"] is True
        assert body["linked_providers"] == ["telegram"]
        assert body["last_login_at"] is not None
    finally:
        app.dependency_overrides.pop(get_db, None)
        app.dependency_overrides.pop(_get_subscription_client, None)


@pytest.mark.integration
async def test_mobile_devices_list_and_delete(async_client, db):
    auth_service = AuthService()
    customer_realm = await AuthRealmRepository(db).get_or_create_default_realm("customer")
    user = MobileUserModel(
        id=uuid4(),
        auth_realm_id=customer_realm.id,
        email=f"mobile-devices-{uuid4().hex[:8]}@example.com",
        password_hash=await auth_service.hash_password("MobileDevices123!"),
        username=f"mobile_devices_{uuid4().hex[:8]}",
        is_active=True,
        status="active",
    )
    db.add(user)
    db.add(
        MobileDeviceModel(
            device_id="device-ios-1",
            platform="ios",
            platform_id="ios-platform-id-1",
            os_version="17.4",
            app_version="1.2.3",
            device_model="iPhone 15 Pro",
            user_id=user.id,
            last_active_at=datetime.now(UTC),
        )
    )
    db.add(
        MobileDeviceModel(
            device_id="device-android-1",
            platform="android",
            platform_id="android-platform-id-1",
            os_version="15",
            app_version="1.2.3",
            device_model="Pixel 9",
            user_id=user.id,
            last_active_at=datetime.now(UTC),
        )
    )
    shared_devices: list[tuple[str, UserDeviceModel]] = []
    for device_id, label, platform in (
        ("device-ios-1", "iPhone 15 Pro", "ios"),
        ("device-android-1", "Pixel 9", "android"),
    ):
        user_device = UserDeviceModel(
            auth_realm_id=customer_realm.id,
            principal_subject=str(user.id),
            principal_class="customer",
            audience=customer_realm.audience,
            device_key_hash=hash_device_key(device_id),
            device_label=label,
            platform=platform,
            first_seen_at=datetime.now(UTC),
            last_seen_at=datetime.now(UTC),
        )
        db.add(user_device)
        shared_devices.append((device_id, user_device))
    await db.flush()
    for device_id, user_device in shared_devices:
        _refresh_token, refresh_jti, refresh_expires_at = auth_service.create_refresh_token(
            subject=str(user.id),
            audience=customer_realm.audience,
            principal_type="customer",
            realm_id=str(customer_realm.id),
            realm_key=customer_realm.realm_key,
            scope_family="customer",
        )
        refresh_record = RefreshToken(
            user_id=user.id,
            auth_realm_id=customer_realm.id,
            principal_class="customer",
            principal_subject=str(user.id),
            audience=customer_realm.audience,
            scope_family="customer",
            token_hash=sha256(f"{device_id}-refresh".encode()).hexdigest(),
            expires_at=refresh_expires_at,
            device_id=str(user_device.id),
            jti=refresh_jti,
            family_id=uuid4(),
        )
        db.add(refresh_record)
        await db.flush()
        db.add(
            PrincipalSessionModel(
                auth_realm_id=customer_realm.id,
                principal_subject=str(user.id),
                principal_class="customer",
                audience=customer_realm.audience,
                scope_family="customer",
                access_token_jti=str(uuid4()),
                refresh_token_id=refresh_record.id,
                user_device_id=user_device.id,
                current_refresh_token_id=refresh_record.id,
                expires_at=refresh_expires_at,
            )
        )
    await db.commit()
    user_id = user.id

    access_token, _jti, _exp = auth_service.create_access_token(
        subject=str(user_id),
        role="mobile_user",
        extra={"device_id": "device-ios-1"},
        audience=str(DEFAULT_AUTH_REALMS["customer"]["audience"]),
        principal_type="customer",
        realm_id=str(user.auth_realm_id),
        realm_key=str(DEFAULT_AUTH_REALMS["customer"]["realm_key"]),
        scope_family="customer",
    )

    async def override_db():
        yield db

    app.dependency_overrides[get_db] = override_db

    try:
        list_response = await async_client.get(
            "/api/v1/mobile/auth/devices",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        assert list_response.status_code == 200
        devices = list_response.json()
        assert len(devices) == 2
        assert {device["id"] for device in devices} == {"device-ios-1", "device-android-1"}
        assert {device["name"] for device in devices} == {"iPhone 15 Pro", "Pixel 9"}

        delete_response = await async_client.delete(
            "/api/v1/mobile/auth/devices/device-android-1",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        assert delete_response.status_code == 204

        db.expire_all()
        refreshed = await MobileUserRepository(db).get_by_id_with_devices(user_id)
        assert refreshed is not None
        assert {device.device_id for device in refreshed.devices} == {"device-ios-1"}
    finally:
        app.dependency_overrides.pop(get_db, None)


@pytest.mark.integration
async def test_authenticated_route_unlinks_telegram_identity(async_client, db):
    auth_service = AuthService()
    user = MobileUserModel(
        id=uuid4(),
        auth_realm_id=stable_auth_realm_id(str(DEFAULT_AUTH_REALMS["customer"]["realm_key"])),
        email=f"tg-unlink-{uuid4().hex[:8]}@example.com",
        password_hash=await auth_service.hash_password("TelegramUnlink123!"),
        username=f"tg_unlink_{uuid4().hex[:8]}",
        telegram_subject=f"telegram-unlink-subject-{uuid4()}",
        telegram_id=(uuid4().int % 9_000_000_000) + 100_000_000,
        telegram_username=f"unlink_{uuid4().hex[:8]}",
        is_active=True,
        status="active",
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    access_token, _jti, _exp = auth_service.create_access_token(
        subject=str(user.id),
        role="mobile_user",
        audience=str(DEFAULT_AUTH_REALMS["customer"]["audience"]),
        principal_type="customer",
        realm_id=str(user.auth_realm_id),
        realm_key=str(DEFAULT_AUTH_REALMS["customer"]["realm_key"]),
        scope_family="customer",
    )

    async def override_db():
        yield db

    app.dependency_overrides[get_db] = override_db

    try:
        with patch("src.presentation.api.v1.mobile_auth.routes.sync_auth_security_posture", new=AsyncMock()):
            response = await async_client.delete(
                "/api/v1/mobile/auth/telegram/link",
                headers={"Authorization": f"Bearer {access_token}"},
            )

        assert response.status_code == 200
        body = response.json()
        assert body["linked"] is False
        assert body["provider"] == "telegram"
        assert body["telegram_username"] is None

        await db.refresh(user)
        assert user.telegram_subject is None
        assert user.telegram_id is None
        assert user.telegram_username is None
    finally:
        app.dependency_overrides.pop(get_db, None)
