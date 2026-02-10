"""Unit tests for AuthService."""

import pytest

from src.application.services.auth_service import AuthService


class TestAuthService:
    """Test suite for AuthService authentication and token management."""

    def setup_method(self):
        """Set up test fixtures."""
        self.auth_service = AuthService()

    @pytest.mark.unit
    async def test_hash_password_returns_different_hashes(self):
        """Test that hash_password returns different hash each time (due to salt)."""
        password = "test_password_123"

        hash1 = await self.auth_service.hash_password(password)
        hash2 = await self.auth_service.hash_password(password)

        assert hash1 != hash2, "Hashes should differ due to random salt"
        assert hash1.startswith("$argon2id$"), "Hash should be Argon2id format"

    @pytest.mark.unit
    async def test_verify_password_correct(self):
        """Test that verify_password returns True for correct password."""
        password = "correct_password"
        password_hash = await self.auth_service.hash_password(password)

        result = await self.auth_service.verify_password(password, password_hash)

        assert result is True

    @pytest.mark.unit
    async def test_verify_password_incorrect(self):
        """Test that verify_password returns False for incorrect password."""
        password = "correct_password"
        wrong_password = "wrong_password"
        password_hash = await self.auth_service.hash_password(password)

        result = await self.auth_service.verify_password(wrong_password, password_hash)

        assert result is False

    @pytest.mark.unit
    def test_create_access_token(self):
        """Test access token creation with correct payload."""
        subject = "user-uuid-123"
        role = "admin"

        token = self.auth_service.create_access_token(subject, role)

        assert isinstance(token, str)
        assert len(token) > 0

        # Decode and verify payload
        payload = self.auth_service.decode_token(token)
        assert payload["sub"] == subject
        assert payload["role"] == role
        assert payload["type"] == "access"
        assert "exp" in payload

    @pytest.mark.unit
    def test_create_refresh_token(self):
        """Test refresh token creation."""
        subject = "user-uuid-456"

        token = self.auth_service.create_refresh_token(subject)

        assert isinstance(token, str)

        payload = self.auth_service.decode_token(token)
        assert payload["sub"] == subject
        assert payload["type"] == "refresh"

    @pytest.mark.unit
    def test_decode_token_valid(self):
        """Test decoding a valid token."""
        subject = "user-123"
        role = "user"
        token = self.auth_service.create_access_token(subject, role)

        payload = self.auth_service.decode_token(token)

        assert payload["sub"] == subject
        assert payload["role"] == role
