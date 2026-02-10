"""Unit tests for user profile endpoints.

Tests cover:
- GET   /api/v1/users/me/profile  (read profile)
- PATCH /api/v1/users/me/profile  (update profile)
"""

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from src.main import app
from src.presentation.dependencies.auth import get_current_active_user

BASE_URL = "/api/v1/users/me/profile"

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
# GET /api/v1/users/me/profile
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_profile_success():
    """GET returns profile data derived from the authenticated user model."""
    _override_auth()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get(BASE_URL)

    assert response.status_code == 200
    body = response.json()
    assert body["id"] == str(_MOCK_USER_ID)
    assert body["email"] == "test@cybervpn.dev"
    assert body["display_name"] == "testadmin"
    assert body["language"] == "en"
    assert body["timezone"] == "UTC"
    assert body["avatar_url"] is None
    assert "updated_at" in body


@pytest.mark.asyncio
async def test_get_profile_no_auth():
    """GET without authentication returns 401."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get(BASE_URL)

    assert response.status_code == 401


# ---------------------------------------------------------------------------
# PATCH /api/v1/users/me/profile
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_patch_profile_display_name():
    """PATCH with display_name returns the updated value."""
    _override_auth()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.patch(BASE_URL, json={"display_name": "New Name"})

    assert response.status_code == 200
    body = response.json()
    assert body["display_name"] == "New Name"
    # Other fields should keep defaults
    assert body["language"] == "en"
    assert body["timezone"] == "UTC"


@pytest.mark.asyncio
async def test_patch_profile_language_and_timezone():
    """PATCH with language and timezone returns merged values."""
    _override_auth()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.patch(BASE_URL, json={"language": "ru", "timezone": "Europe/Moscow"})

    assert response.status_code == 200
    body = response.json()
    assert body["language"] == "ru"
    assert body["timezone"] == "Europe/Moscow"


@pytest.mark.asyncio
async def test_patch_profile_valid_avatar_url():
    """PATCH with a valid HTTPS avatar_url is accepted."""
    _override_auth()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.patch(
            BASE_URL,
            json={"avatar_url": "https://cdn.example.com/avatar.png"},
        )

    assert response.status_code == 200
    body = response.json()
    assert body["avatar_url"] == "https://cdn.example.com/avatar.png"


@pytest.mark.asyncio
async def test_patch_profile_invalid_avatar_url():
    """PATCH with a non-HTTP avatar_url returns 422."""
    _override_auth()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.patch(BASE_URL, json={"avatar_url": "ftp://files.example.com/img.png"})

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_patch_profile_language_normalization():
    """PATCH normalizes language to lowercase, stripping whitespace."""
    _override_auth()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.patch(BASE_URL, json={"language": "  EN  "})

    assert response.status_code == 200
    body = response.json()
    assert body["language"] == "en"


@pytest.mark.asyncio
async def test_patch_profile_empty_body():
    """PATCH with an empty body returns 200 with unchanged defaults."""
    _override_auth()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.patch(BASE_URL, json={})

    assert response.status_code == 200
    body = response.json()
    assert body["display_name"] == "testadmin"
    assert body["language"] == "en"


@pytest.mark.asyncio
async def test_patch_profile_no_auth():
    """PATCH without authentication returns 401."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.patch(BASE_URL, json={"display_name": "Hacker"})

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_patch_profile_preserves_user_identity():
    """PATCH response always includes the authenticated user id and email."""
    _override_auth()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.patch(BASE_URL, json={"display_name": "Changed"})

    assert response.status_code == 200
    body = response.json()
    assert body["id"] == str(_MOCK_USER_ID)
    assert body["email"] == "test@cybervpn.dev"
