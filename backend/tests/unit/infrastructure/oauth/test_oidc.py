"""Unit tests for AsyncOIDCTokenVerifier."""

from unittest.mock import MagicMock, patch

import pytest

from src.infrastructure.oauth.errors import OAuthProviderUnavailableError
from src.infrastructure.oauth.oidc import AsyncOIDCTokenVerifier


class TestAsyncOIDCTokenVerifier:
    @pytest.mark.unit
    async def test_verify_id_token_refreshes_jwks_when_kid_missing(self) -> None:
        discovery = {"jwks_uri": "https://accounts.google.com/oauth2/v3/certs"}
        stale_jwks = {"keys": [{"kid": "old-key"}]}
        fresh_jwks = {"keys": [{"kid": "new-key", "kty": "RSA"}]}
        claims = {"iss": "https://accounts.google.com", "sub": "123"}

        with (
            patch(
                "src.infrastructure.oauth.oidc.jwt.get_unverified_header",
                return_value={"kid": "new-key", "alg": "RS256"},
            ),
            patch.object(
                AsyncOIDCTokenVerifier,
                "_fetch_json_cached",
                side_effect=[discovery, stale_jwks, fresh_jwks],
            ) as mock_fetch,
            patch("src.infrastructure.oauth.oidc.RSAAlgorithm.from_jwk", return_value=MagicMock()),
            patch("src.infrastructure.oauth.oidc.jwt.decode", return_value=claims),
        ):
            result = await AsyncOIDCTokenVerifier.verify_id_token(
                id_token="token",
                audience="client-id",
                discovery_url="https://accounts.google.com/.well-known/openid-configuration",
                issuer_validator=lambda token_claims, _discovery: token_claims["iss"] == "https://accounts.google.com",
            )

        assert result == claims
        assert mock_fetch.call_count == 3
        assert mock_fetch.call_args_list[2].kwargs["force_refresh"] is True

    @pytest.mark.unit
    async def test_verify_id_token_raises_when_oidc_metadata_unavailable(self) -> None:
        with (
            patch(
                "src.infrastructure.oauth.oidc.jwt.get_unverified_header",
                return_value={"kid": "new-key", "alg": "RS256"},
            ),
            patch.object(
                AsyncOIDCTokenVerifier,
                "_fetch_json_cached",
                side_effect=OAuthProviderUnavailableError("OIDC provider metadata is temporarily unavailable"),
            ),
        ):
            with pytest.raises(OAuthProviderUnavailableError):
                await AsyncOIDCTokenVerifier.verify_id_token(
                    id_token="token",
                    audience="client-id",
                    discovery_url="https://accounts.google.com/.well-known/openid-configuration",
                    issuer_validator=lambda *_args: True,
                )
