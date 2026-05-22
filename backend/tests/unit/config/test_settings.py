"""Unit tests for settings validation.

MED-005: Test weak secret pattern rejection.
"""

import pytest
from pydantic import SecretStr, ValidationError

from src.config.settings import S1_PRODUCTION_CORS_ORIGINS, Settings


class TestWeakSecretPatterns:
    """Test JWT secret validation rejects weak patterns in production."""

    # Generate a valid-length secret with weak pattern embedded
    WEAK_SECRETS = [
        "sample_placeholder_for_dev_mode_32_chars",
        "this_is_a_dev_secret_for_testing_purposes",
        "local_secret_key_with_minimum_length_ok",
        "dummy_secret_for_unit_tests_32_chars_min",
        "changeme_this_is_a_placeholder_secret_key",
        "password_based_secret_key_is_not_allowed",
        "development_environment_secret_key_here",
        "example_secret_key_should_be_rejected_too",
        "placeholder_secret_key_not_for_production",
    ]

    STRONG_SECRET = "xVanw-qakEZA0v_T5mJ9GSCJkTzoWYpHMJDX02lFg-B8"
    VALID_TOKEN = "valid_token_for_testing_purposes_32characters"
    VALID_PRODUCTION_PROVIDER_TOKEN = "liveProviderCredentialAlphaBeta123456"
    PRODUCTION_CORS_ORIGINS = list(S1_PRODUCTION_CORS_ORIGINS)

    @pytest.mark.parametrize("weak_secret", WEAK_SECRETS)
    def test_weak_secrets_rejected_in_production(self, weak_secret: str) -> None:
        """Verify weak secrets are rejected in production environment."""
        with pytest.raises(ValidationError) as exc_info:
            Settings(
                environment="production",
                jwt_secret=SecretStr(weak_secret),
                remnawave_token=SecretStr(self.VALID_TOKEN),
                cryptobot_token=SecretStr(self.VALID_TOKEN),
                cors_origins=self.PRODUCTION_CORS_ORIGINS,
                oauth_enabled_login_providers=[],
                admin_2fa_required=True,
            )

        # Verify the error is about weak secret
        error_str = str(exc_info.value).lower()
        assert "weak" in error_str or "test" in error_str

    def test_strong_secret_accepted_in_production(self) -> None:
        """Verify strong secrets are accepted in production environment."""
        # Should not raise
        settings = Settings(
            environment="production",
            jwt_secret=SecretStr(self.STRONG_SECRET),
            remnawave_token=SecretStr(self.VALID_TOKEN),
            cryptobot_token=SecretStr(self.VALID_PRODUCTION_PROVIDER_TOKEN),
            cors_origins=self.PRODUCTION_CORS_ORIGINS,
            oauth_token_encryption_key=SecretStr(self.STRONG_SECRET),
            oauth_enabled_login_providers=[],
            cookie_secure=True,
            admin_2fa_required=True,
        )
        assert settings.jwt_secret.get_secret_value() == self.STRONG_SECRET

    def test_weak_secrets_allowed_in_development(self) -> None:
        """Verify weak secrets are allowed in development environment."""
        weak_secret = "sample_placeholder_for_dev_mode_32_chars"

        # Should not raise in development
        settings = Settings(
            environment="development",
            jwt_secret=SecretStr(weak_secret),
            remnawave_token=SecretStr(self.VALID_TOKEN),
            cryptobot_token=SecretStr(self.VALID_TOKEN),
        )
        assert "placeholder" in settings.jwt_secret.get_secret_value()

    def test_short_secret_rejected_in_any_environment(self) -> None:
        """Verify secrets shorter than 32 chars are always rejected."""
        with pytest.raises(ValidationError) as exc_info:
            Settings(
                environment="development",
                jwt_secret=SecretStr("short_secret"),
                remnawave_token=SecretStr(self.VALID_TOKEN),
                cryptobot_token=SecretStr(self.VALID_TOKEN),
            )

        assert "32" in str(exc_info.value)

    def test_all_weak_patterns_are_checked(self) -> None:
        """Verify all patterns in WEAK_SECRET_PATTERNS are actually checked."""
        expected_patterns = {
            "test_token",
            "test_secret",
            "dev_secret",
            "local_secret",
            "dummy_secret",
            "changeme",
            "password",
            "secret",
            "development",
            "example",
            "placeholder",
        }
        assert Settings.WEAK_SECRET_PATTERNS == expected_patterns

    def test_debug_release_string_normalizes_to_false(self) -> None:
        """Host-level DEBUG=release should not crash app startup."""
        settings = Settings(
            environment="development",
            debug="release",
            jwt_secret=SecretStr(self.STRONG_SECRET),
            remnawave_token=SecretStr(self.VALID_TOKEN),
            cryptobot_token=SecretStr(self.VALID_TOKEN),
        )

        assert settings.debug is False


class TestS1CorsAndCookieSettings:
    """Test S1 production browser-origin and cookie constraints."""

    STRONG_SECRET = TestWeakSecretPatterns.STRONG_SECRET
    VALID_TOKEN = TestWeakSecretPatterns.VALID_TOKEN
    VALID_PRODUCTION_PROVIDER_TOKEN = TestWeakSecretPatterns.VALID_PRODUCTION_PROVIDER_TOKEN

    def _production_settings(self, **overrides):
        values = {
            "environment": "production",
            "jwt_secret": SecretStr(self.STRONG_SECRET),
            "remnawave_token": SecretStr(self.VALID_TOKEN),
            "cryptobot_token": SecretStr(self.VALID_PRODUCTION_PROVIDER_TOKEN),
            "oauth_token_encryption_key": SecretStr(self.STRONG_SECRET),
            "oauth_enabled_login_providers": [],
            "cors_origins": [
                "https://cyber-vpn.net",
                "https://admin.cyber-vpn.net",
            ],
            "cookie_secure": True,
            "admin_2fa_required": True,
        }
        values.update(overrides)
        return Settings(**values)

    def test_s1_production_cors_origins_are_accepted_and_normalized(self) -> None:
        settings = self._production_settings(cors_origins="https://cyber-vpn.net/, https://admin.cyber-vpn.net/")

        assert settings.cors_origins == [
            "https://cyber-vpn.net",
            "https://admin.cyber-vpn.net",
        ]

    def test_s1_production_rejects_wildcard_cors(self) -> None:
        with pytest.raises(ValidationError, match="not allowed in production"):
            self._production_settings(cors_origins="*")

    def test_s1_production_rejects_redirect_only_org_origins(self) -> None:
        with pytest.raises(ValidationError, match="redirect-only"):
            self._production_settings(cors_origins="https://cyber-vpn.org")

    def test_s1_production_rejects_unapproved_cors_origin(self) -> None:
        with pytest.raises(ValidationError, match="not approved"):
            self._production_settings(cors_origins="https://evil.example")

    def test_s1_production_rejects_http_cors_origin(self) -> None:
        with pytest.raises(ValidationError, match="https"):
            self._production_settings(cors_origins="http://cyber-vpn.net")

    def test_s1_production_rejects_cors_origin_with_path(self) -> None:
        with pytest.raises(ValidationError, match="path"):
            self._production_settings(cors_origins="https://cyber-vpn.net/app")

    def test_s1_production_accepts_host_only_cookie_domain(self) -> None:
        settings = self._production_settings(cookie_domain="")

        assert settings.cookie_domain == ""
        assert settings.cookie_secure is True

    def test_s1_production_accepts_primary_net_cookie_domain(self) -> None:
        settings = self._production_settings(cookie_domain=".cyber-vpn.net")

        assert settings.cookie_domain == "cyber-vpn.net"

    def test_s1_production_rejects_org_cookie_domain(self) -> None:
        with pytest.raises(ValidationError, match="COOKIE_DOMAIN"):
            self._production_settings(cookie_domain="cyber-vpn.org")

    def test_s1_production_rejects_cookie_secure_false(self) -> None:
        with pytest.raises(ValidationError, match="COOKIE_SECURE"):
            self._production_settings(cookie_secure=False)

    def test_s1_production_rejects_csrf_disabled(self) -> None:
        with pytest.raises(ValidationError, match="CSRF_PROTECTION_ENABLED"):
            self._production_settings(csrf_protection_enabled=False)

    def test_s1_production_accepts_admin_primary_host_only(self) -> None:
        settings = self._production_settings(admin_allowed_hosts=".ADMIN.CYBER-VPN.NET")

        assert settings.admin_host_protection_enabled is True
        assert settings.admin_allowed_hosts == ["admin.cyber-vpn.net"]

    def test_s1_production_rejects_admin_host_protection_disabled(self) -> None:
        with pytest.raises(ValidationError, match="ADMIN_HOST_PROTECTION_ENABLED"):
            self._production_settings(admin_host_protection_enabled=False)

    def test_s1_production_rejects_admin_2fa_disabled(self) -> None:
        with pytest.raises(ValidationError, match="ADMIN_2FA_REQUIRED"):
            self._production_settings(admin_2fa_required=False)

    @pytest.mark.parametrize(
        "host",
        [
            "cyber-vpn.net",
            "cyber-vpn.org",
            "admin.cyber-vpn.org",
            "https://admin.cyber-vpn.net",
            "admin.cyber-vpn.net:443",
            "localhost",
        ],
    )
    def test_s1_production_rejects_unapproved_admin_allowed_hosts(self, host: str) -> None:
        with pytest.raises(ValidationError, match="ADMIN_ALLOWED_HOSTS"):
            self._production_settings(admin_allowed_hosts=f"admin.cyber-vpn.net,{host}")


class TestS2OAuthProductionReadiness:
    """Test S2 production OAuth login provider credential guards."""

    STRONG_SECRET = TestWeakSecretPatterns.STRONG_SECRET
    VALID_TOKEN = TestWeakSecretPatterns.VALID_TOKEN
    VALID_PRODUCTION_PROVIDER_TOKEN = TestWeakSecretPatterns.VALID_PRODUCTION_PROVIDER_TOKEN

    def _production_settings(self, **overrides):
        values = {
            "environment": "production",
            "jwt_secret": SecretStr(self.STRONG_SECRET),
            "remnawave_token": SecretStr(self.VALID_TOKEN),
            "cryptobot_token": SecretStr(self.VALID_PRODUCTION_PROVIDER_TOKEN),
            "oauth_token_encryption_key": SecretStr(self.STRONG_SECRET),
            "oauth_web_base_url": "",
            "google_client_id": "",
            "google_client_secret": SecretStr(""),
            "github_client_id": "",
            "github_client_secret": SecretStr(""),
            "cors_origins": list(S1_PRODUCTION_CORS_ORIGINS),
            "cookie_secure": True,
            "admin_2fa_required": True,
        }
        values.update(overrides)
        return Settings(**values)

    def test_production_allows_oauth_disabled_without_provider_credentials(self) -> None:
        settings = self._production_settings(oauth_enabled_login_providers=[])

        assert settings.oauth_enabled_login_providers == []

    def test_production_rejects_google_oauth_without_credentials(self) -> None:
        with pytest.raises(ValidationError, match="GOOGLE_CLIENT_ID"):
            self._production_settings(
                oauth_enabled_login_providers=["google"],
                oauth_web_base_url="https://cyber-vpn.net",
            )

    def test_production_rejects_github_oauth_without_credentials(self) -> None:
        with pytest.raises(ValidationError, match="GITHUB_CLIENT_ID"):
            self._production_settings(
                oauth_enabled_login_providers=["github"],
                oauth_web_base_url="https://cyber-vpn.net",
            )

    def test_production_rejects_oauth_enabled_without_web_base_url(self) -> None:
        with pytest.raises(ValidationError, match="OAUTH_WEB_BASE_URL"):
            self._production_settings(
                oauth_enabled_login_providers=["google"],
                google_client_id="google-client-id",
                google_client_secret=SecretStr("google-client-secret"),
            )

    def test_production_accepts_google_and_github_oauth_with_credentials(self) -> None:
        settings = self._production_settings(
            oauth_enabled_login_providers="google,github",
            oauth_web_base_url="https://cyber-vpn.net",
            google_client_id="google-client-id",
            google_client_secret=SecretStr("google-client-secret"),
            github_client_id="github-client-id",
            github_client_secret=SecretStr("github-client-secret"),
        )

        assert settings.oauth_enabled_login_providers == ["google", "github"]

    def test_runtime_rejects_unsupported_oauth_login_provider(self) -> None:
        with pytest.raises(ValidationError, match="only supports google and github"):
            self._production_settings(oauth_enabled_login_providers=["google", "facebook"])
