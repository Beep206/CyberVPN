"""Integration tests for mobile Telegram OIDC authentication route."""

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
from prometheus_client import REGISTRY

from src.application.services.auth_service import AuthService
from src.application.services.telegram_oidc_auth import (
    InvalidTelegramOIDCTokenError,
    TelegramOIDCUserInfo,
)
from src.domain.entities.auth_realm import DEFAULT_AUTH_REALMS, stable_auth_realm_id
from src.infrastructure.database.models.mobile_device_model import MobileDeviceModel
from src.infrastructure.database.models.mobile_user_model import MobileUserModel
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


@pytest.fixture(autouse=True)
def _disable_mobile_login_rate_limit():
    app.dependency_overrides[check_login_rate_limit] = lambda: None
    try:
        yield
    finally:
        app.dependency_overrides.pop(check_login_rate_limit, None)


@pytest.mark.integration
async def test_route_creates_new_user_and_persists_subject(async_client, db):
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
    user = MobileUserModel(
        id=uuid4(),
        auth_realm_id=stable_auth_realm_id(str(DEFAULT_AUTH_REALMS["customer"]["realm_key"])),
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
