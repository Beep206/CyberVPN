"""Pytest fixtures for integration tests."""

import secrets
import uuid

import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.services.auth_service import AuthService
from src.infrastructure.database.models.admin_user_model import AdminUserModel


@pytest_asyncio.fixture
async def test_user_with_token(
    db: AsyncSession,
) -> tuple[AdminUserModel, str]:
    """Create a test user and generate an access token.

    Returns:
        tuple[AdminUserModel, str]: User model and access token
    """
    auth_service = AuthService()

    # Create test user
    user = AdminUserModel(
        id=uuid.uuid4(),
        login=f"testuser_{secrets.token_hex(4)}",
        email=f"test_{secrets.token_hex(4)}@example.com",
        password_hash=auth_service.hash_password("TestPassword123!"),
        role="user",
        is_active=True,
        language="en-EN",
        timezone="UTC",
    )

    db.add(user)
    await db.commit()
    await db.refresh(user)

    # Generate access token
    access_token, _, _ = auth_service.create_access_token(
        subject=str(user.id),
        role=user.role,
    )

    return user, access_token
