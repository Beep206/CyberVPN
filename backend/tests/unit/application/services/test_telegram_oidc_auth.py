"""Unit tests for TelegramOIDCAuthService."""

from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

import jwt
import pytest

from src.application.services.telegram_oidc_auth import (
    InvalidTelegramOIDCTokenError,
    TelegramOIDCAuthService,
)
from src.infrastructure.oauth.errors import OAuthProviderUnavailableError


class TestTelegramOIDCAuthService:
    @pytest.mark.unit
    async def test_validate_id_token_success_returns_normalized_claims(self) -> None:
        with patch("src.application.services.telegram_oidc_auth.settings") as mock_settings:
            mock_settings.telegram_oidc_client_id = "client-id"
            mock_settings.telegram_oidc_allowed_audience = "client-id"
            mock_settings.telegram_oidc_issuer = "https://oauth.telegram.org"
            mock_settings.telegram_oidc_discovery_url = "https://oauth.telegram.org/.well-known/openid-configuration"
            mock_settings.telegram_oidc_jwks_url = "https://oauth.telegram.org/.well-known/jwks.json"
            mock_settings.telegram_oidc_clock_skew_seconds = 60

            service = TelegramOIDCAuthService()

            discovery = {
                "issuer": "https://oauth.telegram.org",
                "jwks_uri": "https://oauth.telegram.org/.well-known/jwks.json",
            }
            jwks = {"keys": [{"kid": "kid-1", "kty": "RSA"}]}
            claims = {
                "iss": "https://oauth.telegram.org",
                "aud": "client-id",
                "sub": "telegram-subject",
                "id": "123456789",
                "preferred_username": "telegram_user",
                "name": "Telegram User",
                "picture": "https://cdn.example/avatar.jpg",
                "phone_number": "+15551234567",
                "iat": 1_700_000_000,
                "exp": 1_700_000_900,
            }

            with (
                patch(
                    "src.application.services.telegram_oidc_auth.jwt.get_unverified_header",
                    return_value={"kid": "kid-1", "alg": "RS256"},
                ),
                patch(
                    "src.application.services.telegram_oidc_auth.AsyncOIDCTokenVerifier._fetch_json_cached",
                    side_effect=[discovery, jwks],
                ),
                patch("src.application.services.telegram_oidc_auth.RSAAlgorithm.from_jwk", return_value=MagicMock()),
                patch("src.application.services.telegram_oidc_auth.jwt.decode", return_value=claims),
            ):
                result = await service.validate_id_token("id-token")

            assert result.subject == "telegram-subject"
            assert result.telegram_id == 123456789
            assert result.preferred_username == "telegram_user"
            assert result.name == "Telegram User"
            assert result.picture == "https://cdn.example/avatar.jpg"
            assert result.phone_number == "+15551234567"
            assert result.issued_at == datetime.fromtimestamp(claims["iat"], tz=UTC)
            assert result.expires_at == datetime.fromtimestamp(claims["exp"], tz=UTC)

    @pytest.mark.unit
    async def test_validate_id_token_invalid_audience_raises_reasoned_error(self) -> None:
        with patch("src.application.services.telegram_oidc_auth.settings") as mock_settings:
            mock_settings.telegram_oidc_client_id = "client-id"
            mock_settings.telegram_oidc_allowed_audience = "client-id"
            mock_settings.telegram_oidc_issuer = "https://oauth.telegram.org"
            mock_settings.telegram_oidc_discovery_url = "https://oauth.telegram.org/.well-known/openid-configuration"
            mock_settings.telegram_oidc_jwks_url = "https://oauth.telegram.org/.well-known/jwks.json"
            mock_settings.telegram_oidc_clock_skew_seconds = 60

            service = TelegramOIDCAuthService()

            discovery = {
                "issuer": "https://oauth.telegram.org",
                "jwks_uri": "https://oauth.telegram.org/.well-known/jwks.json",
            }
            jwks = {"keys": [{"kid": "kid-1", "kty": "RSA"}]}

            with (
                patch(
                    "src.application.services.telegram_oidc_auth.jwt.get_unverified_header",
                    return_value={"kid": "kid-1", "alg": "RS256"},
                ),
                patch(
                    "src.application.services.telegram_oidc_auth.AsyncOIDCTokenVerifier._fetch_json_cached",
                    side_effect=[discovery, jwks],
                ),
                patch("src.application.services.telegram_oidc_auth.RSAAlgorithm.from_jwk", return_value=MagicMock()),
                patch(
                    "src.application.services.telegram_oidc_auth.jwt.decode",
                    side_effect=jwt.InvalidAudienceError("bad aud"),
                ),
            ):
                with pytest.raises(InvalidTelegramOIDCTokenError) as exc_info:
                    await service.validate_id_token("id-token")

            assert exc_info.value.reason == "aud_invalid"

    @pytest.mark.unit
    async def test_validate_id_token_propagates_provider_unavailable(self) -> None:
        with patch("src.application.services.telegram_oidc_auth.settings") as mock_settings:
            mock_settings.telegram_oidc_client_id = "client-id"
            mock_settings.telegram_oidc_allowed_audience = "client-id"
            mock_settings.telegram_oidc_issuer = "https://oauth.telegram.org"
            mock_settings.telegram_oidc_discovery_url = "https://oauth.telegram.org/.well-known/openid-configuration"
            mock_settings.telegram_oidc_jwks_url = "https://oauth.telegram.org/.well-known/jwks.json"
            mock_settings.telegram_oidc_clock_skew_seconds = 60

            service = TelegramOIDCAuthService()

            with (
                patch(
                    "src.application.services.telegram_oidc_auth.jwt.get_unverified_header",
                    return_value={"kid": "kid-1", "alg": "RS256"},
                ),
                patch(
                    "src.application.services.telegram_oidc_auth.AsyncOIDCTokenVerifier._fetch_json_cached",
                    side_effect=OAuthProviderUnavailableError("OIDC provider metadata is temporarily unavailable"),
                ),
            ):
                with pytest.raises(OAuthProviderUnavailableError):
                    await service.validate_id_token("id-token")
