"""Unit tests for FCM token management endpoints.

Tests cover:
- POST /api/v1/users/me/fcm-token  (register FCM token)
- DELETE /api/v1/users/me/fcm-token (unregister FCM token)
"""

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from src.main import app
from src.presentation.dependencies.auth import get_current_active_user

BASE_URL = "/api/v1/users/me/fcm-token"

# ---------------------------------------------------------------------------
# Mock user
# ---------------------------------------------------------------------------

_MOCK_USER_ID = uuid4()
_MOCK_USER_UPDATED_AT = datetime(2025, 6, 1, 12, 0, 0, tzinfo=UTC)


class _MockUser:
    """Lightweight stand-in for AdminUserModel used in dependency overrides."""

    id = _MOCK_USER_ID
    login = "testadmin"
    email = "test@cybervpn.dev"
    is_active = True
    updated_at = _MOCK_USER_UPDATED_AT


def _mock_current_active_user() -> _MockUser:
    return _MockUser()


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _clean_overrides():
    """Ensure dependency overrides are removed after every test."""
    yield
    app.dependency_overrides.clear()


def _override_auth() -> None:
    """Install the mock auth dependency override."""
    app.dependency_overrides[get_current_active_user] = _mock_current_active_user


# ---------------------------------------------------------------------------
# POST /api/v1/users/me/fcm-token
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_register_fcm_token_success():
    """POST with valid payload returns 201 and echoes the token data."""
    _override_auth()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        payload = {
            "token": "fcm-token-abc123",
            "device_id": "device-001",
            "platform": "android",
        }
        response = await client.post(BASE_URL, json=payload)

    assert response.status_code == 201
    body = response.json()
    assert body["token"] == "fcm-token-abc123"
    assert body["device_id"] == "device-001"
    assert body["platform"] == "android"
    assert "created_at" in body


@pytest.mark.asyncio
async def test_register_fcm_token_ios_platform():
    """POST with platform='ios' is also accepted."""
    _override_auth()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        payload = {
            "token": "apns-token-xyz",
            "device_id": "iphone-42",
            "platform": "ios",
        }
        response = await client.post(BASE_URL, json=payload)

    assert response.status_code == 201
    body = response.json()
    assert body["platform"] == "ios"


@pytest.mark.asyncio
async def test_register_fcm_token_empty_token_rejected():
    """POST with an empty token string returns 422."""
    _override_auth()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        payload = {
            "token": "",
            "device_id": "device-001",
            "platform": "android",
        }
        response = await client.post(BASE_URL, json=payload)

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_register_fcm_token_missing_device_id():
    """POST without device_id returns 422."""
    _override_auth()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        payload = {
            "token": "some-token",
            "platform": "android",
        }
        response = await client.post(BASE_URL, json=payload)

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_register_fcm_token_invalid_platform():
    """POST with an unsupported platform value returns 422."""
    _override_auth()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        payload = {
            "token": "some-token",
            "device_id": "device-001",
            "platform": "windows",
        }
        response = await client.post(BASE_URL, json=payload)

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_register_fcm_token_missing_token_field():
    """POST without the token field returns 422."""
    _override_auth()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        payload = {
            "device_id": "device-001",
            "platform": "android",
        }
        response = await client.post(BASE_URL, json=payload)

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_register_fcm_token_no_auth():
    """POST without authentication returns 401 (HTTPBearer auto_error)."""
    # Do NOT install auth override -- the real dependency will reject.
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        payload = {
            "token": "some-token",
            "device_id": "device-001",
            "platform": "android",
        }
        response = await client.post(BASE_URL, json=payload)

    assert response.status_code == 401


# ---------------------------------------------------------------------------
# DELETE /api/v1/users/me/fcm-token
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_unregister_fcm_token_success():
    """DELETE with valid device_id returns 204 No Content."""
    _override_auth()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        payload = {"device_id": "device-001"}
        response = await client.request("DELETE", BASE_URL, json=payload)

    assert response.status_code == 204


@pytest.mark.asyncio
async def test_unregister_fcm_token_empty_device_id():
    """DELETE with empty device_id returns 422."""
    _override_auth()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        payload = {"device_id": ""}
        response = await client.request("DELETE", BASE_URL, json=payload)

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_unregister_fcm_token_missing_device_id():
    """DELETE without device_id field returns 422."""
    _override_auth()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.request("DELETE", BASE_URL, json={})

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_unregister_fcm_token_no_auth():
    """DELETE without authentication returns 401."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        payload = {"device_id": "device-001"}
        response = await client.request("DELETE", BASE_URL, json=payload)

    assert response.status_code == 401
