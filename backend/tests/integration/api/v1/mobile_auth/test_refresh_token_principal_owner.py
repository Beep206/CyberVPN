"""Regression coverage for mobile refresh token principal ownership."""

from datetime import UTC, datetime, timedelta
from hashlib import sha256
from uuid import uuid4

import pytest
from sqlalchemy import select

from src.application.services.auth_service import AuthService
from src.application.services.auth_session_issuer import hash_device_key
from src.domain.entities.auth_realm import DEFAULT_AUTH_REALMS
from src.infrastructure.database.models.admin_user_model import AdminUserModel
from src.infrastructure.database.models.mobile_user_model import MobileUserModel
from src.infrastructure.database.models.principal_session_model import PrincipalSessionModel
from src.infrastructure.database.models.refresh_token_model import RefreshToken
from src.infrastructure.database.models.user_device_model import UserDeviceModel
from src.infrastructure.database.repositories.auth_realm_repo import AuthRealmRepository
from src.main import app
from src.presentation.api.v1.mobile_auth.routes import _get_subscription_client
from src.presentation.dependencies.database import get_db
from src.presentation.dependencies.mobile_rate_limit import check_login_rate_limit

CUSTOMER_AUDIENCE = str(DEFAULT_AUTH_REALMS["customer"]["audience"])
CUSTOMER_SCOPE = str(DEFAULT_AUTH_REALMS["customer"]["realm_type"])


def _password_login_payload(
    *,
    device_id: str,
    email: str | None = None,
    password: str = "MobileOwnerSchema123!",
    device_model: str = "iPhone 15 Pro",
    platform: str = "ios",
) -> dict:
    return {
        "email": email or f"mobile-owner-{uuid4().hex[:8]}@example.com",
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
    customer_realm = await AuthRealmRepository(db).get_or_create_default_realm("customer")
    auth_service = AuthService()
    user = MobileUserModel(
        id=uuid4(),
        auth_realm_id=customer_realm.id,
        email=payload["email"],
        password_hash=await auth_service.hash_password(payload["password"]),
        username=f"mobile_owner_{uuid4().hex[:8]}",
        is_active=True,
        status="active",
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


async def _override_db(db):
    yield db


@pytest.fixture(autouse=True)
def _disable_mobile_login_rate_limit():
    app.dependency_overrides[check_login_rate_limit] = lambda: None
    try:
        yield
    finally:
        app.dependency_overrides.pop(check_login_rate_limit, None)


@pytest.fixture(autouse=True)
def _override_subscription_client():
    app.dependency_overrides[_get_subscription_client] = lambda: None
    try:
        yield
    finally:
        app.dependency_overrides.pop(_get_subscription_client, None)


@pytest.mark.integration
async def test_customer_refresh_persists_owner_metadata_and_replay_revokes_family(async_client, db) -> None:
    payload = _password_login_payload(device_id="523e4567-e89b-12d3-a456-426614174000")
    user = await _create_password_mobile_user(db, payload)
    device_id = payload["device"]["device_id"]

    async def override_db():
        async for session in _override_db(db):
            yield session

    app.dependency_overrides[get_db] = override_db
    try:
        login_response = await async_client.post("/api/v1/mobile/auth/login", json=payload)
        assert login_response.status_code == 200

        refresh_token = login_response.json()["tokens"]["refresh_token"]
        refresh_record = (
            await db.execute(
                select(RefreshToken).where(RefreshToken.token_hash == sha256(refresh_token.encode()).hexdigest())
            )
        ).scalar_one()

        assert await db.get(AdminUserModel, user.id) is None
        assert refresh_record.user_id == user.id
        assert refresh_record.auth_realm_id == user.auth_realm_id
        assert refresh_record.principal_class == "customer"
        assert refresh_record.principal_subject == str(user.id)
        assert refresh_record.audience == CUSTOMER_AUDIENCE
        assert refresh_record.scope_family == CUSTOMER_SCOPE
        assert refresh_record.principal_session_id is not None
        assert refresh_record.family_id is not None

        principal_session = await db.get(PrincipalSessionModel, refresh_record.principal_session_id)
        assert principal_session is not None
        assert principal_session.auth_realm_id == refresh_record.auth_realm_id
        assert principal_session.principal_class == refresh_record.principal_class
        assert principal_session.principal_subject == refresh_record.principal_subject
        assert principal_session.audience == refresh_record.audience
        assert principal_session.scope_family == refresh_record.scope_family
        assert principal_session.current_refresh_token_id == refresh_record.id

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
        assert refresh_record.revoked_reason == "rotated"
        assert refresh_record.replaced_by_token_id == rotated_refresh_record.id
        assert rotated_refresh_record.parent_token_id == refresh_record.id
        assert rotated_refresh_record.family_id == refresh_record.family_id
        assert rotated_refresh_record.auth_realm_id == refresh_record.auth_realm_id
        assert rotated_refresh_record.principal_class == "customer"
        assert rotated_refresh_record.principal_subject == str(user.id)
        assert rotated_refresh_record.audience == CUSTOMER_AUDIENCE
        assert rotated_refresh_record.scope_family == CUSTOMER_SCOPE
        assert principal_session.current_refresh_token_id == rotated_refresh_record.id

        refresh_record.consumed_at = datetime.now(UTC) - timedelta(seconds=20)
        await db.commit()
        replay_response = await async_client.post(
            "/api/v1/mobile/auth/refresh",
            json={"refresh_token": refresh_token, "device_id": device_id},
        )
        assert replay_response.status_code == 401

        replayed_family = (
            (await db.execute(select(RefreshToken).where(RefreshToken.family_id == refresh_record.family_id)))
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


@pytest.mark.integration
async def test_remove_device_revokes_only_selected_customer_refresh_family(async_client, db) -> None:
    first_device_id = "623e4567-e89b-12d3-a456-426614174000"
    second_device_id = "723e4567-e89b-12d3-a456-426614174000"
    first_payload = _password_login_payload(device_id=first_device_id)
    second_payload = _password_login_payload(
        device_id=second_device_id,
        email=first_payload["email"],
        password=first_payload["password"],
        device_model="Pixel 9",
        platform="android",
    )
    user = await _create_password_mobile_user(db, first_payload)

    async def override_db():
        async for session in _override_db(db):
            yield session

    app.dependency_overrides[get_db] = override_db
    try:
        first_login = await async_client.post("/api/v1/mobile/auth/login", json=first_payload)
        second_login = await async_client.post("/api/v1/mobile/auth/login", json=second_payload)
        assert first_login.status_code == 200
        assert second_login.status_code == 200

        first_access_token = first_login.json()["tokens"]["access_token"]
        first_refresh_token = first_login.json()["tokens"]["refresh_token"]
        second_refresh_token = second_login.json()["tokens"]["refresh_token"]

        first_refresh = (
            await db.execute(
                select(RefreshToken).where(RefreshToken.token_hash == sha256(first_refresh_token.encode()).hexdigest())
            )
        ).scalar_one()
        second_refresh = (
            await db.execute(
                select(RefreshToken).where(RefreshToken.token_hash == sha256(second_refresh_token.encode()).hexdigest())
            )
        ).scalar_one()
        first_device = (
            await db.execute(
                select(UserDeviceModel).where(
                    UserDeviceModel.principal_subject == str(user.id),
                    UserDeviceModel.device_key_hash == hash_device_key(first_device_id),
                )
            )
        ).scalar_one()
        second_device = (
            await db.execute(
                select(UserDeviceModel).where(
                    UserDeviceModel.principal_subject == str(user.id),
                    UserDeviceModel.device_key_hash == hash_device_key(second_device_id),
                )
            )
        ).scalar_one()
        assert first_refresh.auth_realm_id == second_refresh.auth_realm_id == user.auth_realm_id
        assert {first_refresh.principal_class, second_refresh.principal_class} == {"customer"}

        delete_response = await async_client.delete(
            f"/api/v1/mobile/auth/devices/{second_device_id}",
            headers={"Authorization": f"Bearer {first_access_token}"},
        )
        assert delete_response.status_code == 204

        await db.refresh(first_refresh)
        await db.refresh(second_refresh)
        await db.refresh(first_device)
        await db.refresh(second_device)
        assert first_device.revoked_at is None
        assert second_device.revoked_at is not None
        assert first_refresh.revoked_at is None
        assert second_refresh.revoked_at is not None
        assert second_refresh.revoked_reason == "mobile_device_removed"
    finally:
        app.dependency_overrides.pop(get_db, None)
