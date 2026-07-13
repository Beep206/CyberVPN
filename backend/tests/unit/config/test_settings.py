"""Unit tests for settings validation.

MED-005: Test weak secret pattern rejection.
"""

import pytest
from pydantic import SecretStr, ValidationError

from src.config.settings import S1_LOCAL_STAGE_BROWSER_ORIGINS, S1_PRODUCTION_CORS_ORIGINS, Settings


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
    VALID_WORKER_SECRET = "liveSettlementWorkerCredentialAlpha123456"
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
                payment_settlement_worker_secret=SecretStr(self.VALID_WORKER_SECRET),
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
            payment_settlement_worker_secret=SecretStr(self.VALID_WORKER_SECRET),
            telegram_bot_internal_secret=SecretStr(""),
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

    def test_default_remnawave_squad_targets_premium_smart_ru(self) -> None:
        settings = Settings(
            _env_file=None,
            environment="development",
            jwt_secret=SecretStr(self.STRONG_SECRET),
            remnawave_token=SecretStr(self.VALID_TOKEN),
            cryptobot_token=SecretStr(self.VALID_TOKEN),
        )

        assert settings.remnawave_default_internal_squad_name == "CYBERVPN_PREMIUM_SMART_RU_NODES"

    def test_default_spb_de_exceptions_settings_are_explicit_and_isolated(self) -> None:
        settings = Settings(
            _env_file=None,
            environment="development",
            jwt_secret=SecretStr(self.STRONG_SECRET),
            remnawave_token=SecretStr(self.VALID_TOKEN),
            cryptobot_token=SecretStr(self.VALID_TOKEN),
        )

        assert settings.remnawave_spb_de_exceptions_plan_codes == "premium_spb_de_exceptions"
        assert settings.remnawave_spb_de_exceptions_external_squad_uuid == ""
        assert settings.remnawave_spb_de_exceptions_internal_squad_uuid == ""
        assert settings.remnawave_spb_de_exceptions_bridge_squad_uuid == ""
        assert settings.remnawave_spb_de_exceptions_profile_name == "S1 SPB DE Exceptions"
        assert settings.remnawave_spb_de_exceptions_policy_version == "premium_spb_de_exceptions.v1"
        assert settings.remnawave_spb_de_exceptions_data_plane_ready is False
        assert settings.remnawave_spb_de_exceptions_readiness_attestation == ""
        assert settings.remnawave_spb_de_exceptions_readiness_attestation_path == ""
        assert settings.remnawave_spb_de_exceptions_readiness_public_key == ""
        assert settings.remnawave_spb_de_exceptions_readiness_public_key_path == ""
        assert settings.remnawave_spb_de_exceptions_readiness_active_pointer == ""
        assert settings.remnawave_spb_de_exceptions_readiness_active_pointer_path == ""
        assert settings.remnawave_spb_de_exceptions_readiness_lkg_pointer == ""
        assert settings.remnawave_spb_de_exceptions_readiness_lkg_pointer_path == ""
        assert settings.remnawave_spb_de_exceptions_readiness_revoked_attestation_ids == ""
        assert settings.remnawave_spb_de_exceptions_plan_codes != settings.remnawave_smart_ru_plan_codes

    def test_spb_de_exceptions_data_plane_ready_must_be_explicitly_enabled(self) -> None:
        settings = Settings(
            _env_file=None,
            environment="development",
            jwt_secret=SecretStr(self.STRONG_SECRET),
            remnawave_token=SecretStr(self.VALID_TOKEN),
            cryptobot_token=SecretStr(self.VALID_TOKEN),
            remnawave_spb_de_exceptions_data_plane_ready=True,
        )

        assert settings.remnawave_spb_de_exceptions_data_plane_ready is True

    @pytest.mark.parametrize(("raw_value", "expected"), [("true", True), ("false", False)])
    def test_spb_de_exceptions_data_plane_ready_env_override(
        self,
        monkeypatch: pytest.MonkeyPatch,
        raw_value: str,
        expected: bool,
    ) -> None:
        monkeypatch.setenv("REMNAWAVE_SPB_DE_EXCEPTIONS_DATA_PLANE_READY", raw_value)

        settings = Settings(
            _env_file=None,
            environment="development",
            jwt_secret=SecretStr(self.STRONG_SECRET),
            remnawave_token=SecretStr(self.VALID_TOKEN),
            cryptobot_token=SecretStr(self.VALID_TOKEN),
        )

        assert settings.remnawave_spb_de_exceptions_data_plane_ready is expected

    def test_spb_de_exceptions_readiness_attestation_settings_accept_env_overrides(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setenv("REMNAWAVE_SPB_DE_EXCEPTIONS_READINESS_ATTESTATION", "signed.jwt")
        monkeypatch.setenv("REMNAWAVE_SPB_DE_EXCEPTIONS_READINESS_ATTESTATION_PATH", "/run/cybervpn/task2.jwt")
        monkeypatch.setenv("REMNAWAVE_SPB_DE_EXCEPTIONS_READINESS_PUBLIC_KEY", "-----BEGIN PUBLIC KEY-----")
        monkeypatch.setenv("REMNAWAVE_SPB_DE_EXCEPTIONS_READINESS_PUBLIC_KEY_PATH", "/run/cybervpn/task2.pub")
        monkeypatch.setenv("REMNAWAVE_SPB_DE_EXCEPTIONS_READINESS_ACTIVE_POINTER", '{"version":"active"}')
        monkeypatch.setenv(
            "REMNAWAVE_SPB_DE_EXCEPTIONS_READINESS_ACTIVE_POINTER_PATH",
            "/run/cybervpn/task2-active.json",
        )
        monkeypatch.setenv("REMNAWAVE_SPB_DE_EXCEPTIONS_READINESS_LKG_POINTER", '{"version":"lkg"}')
        monkeypatch.setenv(
            "REMNAWAVE_SPB_DE_EXCEPTIONS_READINESS_LKG_POINTER_PATH",
            "/run/cybervpn/task2-lkg.json",
        )
        monkeypatch.setenv("REMNAWAVE_SPB_DE_EXCEPTIONS_READINESS_MANIFEST", '{"version":"manifest"}')
        monkeypatch.setenv(
            "REMNAWAVE_SPB_DE_EXCEPTIONS_READINESS_STORE_PATH",
            "/run/cybervpn/task2-store",
        )
        monkeypatch.setenv(
            "REMNAWAVE_SPB_DE_EXCEPTIONS_READINESS_REVOKED_ATTESTATION_IDS",
            "task2-attestation-20260711",
        )

        settings = Settings(
            _env_file=None,
            environment="development",
            jwt_secret=SecretStr(self.STRONG_SECRET),
            remnawave_token=SecretStr(self.VALID_TOKEN),
            cryptobot_token=SecretStr(self.VALID_TOKEN),
        )

        assert settings.remnawave_spb_de_exceptions_readiness_attestation == "signed.jwt"
        assert settings.remnawave_spb_de_exceptions_readiness_attestation_path == "/run/cybervpn/task2.jwt"
        assert settings.remnawave_spb_de_exceptions_readiness_public_key == "-----BEGIN PUBLIC KEY-----"
        assert settings.remnawave_spb_de_exceptions_readiness_public_key_path == "/run/cybervpn/task2.pub"
        assert settings.remnawave_spb_de_exceptions_readiness_active_pointer == '{"version":"active"}'
        assert settings.remnawave_spb_de_exceptions_readiness_active_pointer_path == ("/run/cybervpn/task2-active.json")
        assert settings.remnawave_spb_de_exceptions_readiness_lkg_pointer == '{"version":"lkg"}'
        assert settings.remnawave_spb_de_exceptions_readiness_lkg_pointer_path == "/run/cybervpn/task2-lkg.json"
        assert settings.remnawave_spb_de_exceptions_readiness_manifest == '{"version":"manifest"}'
        assert settings.remnawave_spb_de_exceptions_readiness_store_path == "/run/cybervpn/task2-store"
        assert settings.remnawave_spb_de_exceptions_readiness_revoked_attestation_ids == ("task2-attestation-20260711")

    def test_spb_de_exceptions_data_plane_ready_false_is_allowed_in_production(self) -> None:
        settings = Settings(
            _env_file=None,
            environment="production",
            jwt_secret=SecretStr(self.STRONG_SECRET),
            remnawave_token=SecretStr(self.VALID_TOKEN),
            cryptobot_token=SecretStr(self.VALID_PRODUCTION_PROVIDER_TOKEN),
            payment_settlement_worker_secret=SecretStr(self.VALID_WORKER_SECRET),
            telegram_bot_internal_secret=SecretStr(""),
            oauth_token_encryption_key=SecretStr(self.STRONG_SECRET),
            oauth_enabled_login_providers=[],
            cors_origins=self.PRODUCTION_CORS_ORIGINS,
            cookie_secure=True,
            admin_2fa_required=True,
        )

        assert settings.remnawave_spb_de_exceptions_data_plane_ready is False


class TestS1CorsAndCookieSettings:
    """Test S1 production browser-origin and cookie constraints."""

    STRONG_SECRET = TestWeakSecretPatterns.STRONG_SECRET
    VALID_TOKEN = TestWeakSecretPatterns.VALID_TOKEN
    VALID_PRODUCTION_PROVIDER_TOKEN = TestWeakSecretPatterns.VALID_PRODUCTION_PROVIDER_TOKEN
    VALID_WORKER_SECRET = TestWeakSecretPatterns.VALID_WORKER_SECRET
    VALID_BACKEND_INTERNAL_SECRET = "liveBackendInternalCredentialAlpha123456"

    def _production_settings(self, **overrides):
        values = {
            "environment": "production",
            "jwt_secret": SecretStr(self.STRONG_SECRET),
            "remnawave_token": SecretStr(self.VALID_TOKEN),
            "cryptobot_token": SecretStr(self.VALID_PRODUCTION_PROVIDER_TOKEN),
            "payment_settlement_worker_secret": SecretStr(self.VALID_WORKER_SECRET),
            "telegram_bot_internal_secret": SecretStr(""),
            "oauth_token_encryption_key": SecretStr(self.STRONG_SECRET),
            "oauth_enabled_login_providers": [],
            "cors_origins": [
                "https://cyber-vpn.net",
                "https://admin.cyber-vpn.net",
                "https://partner.cyber-vpn.net",
            ],
            "cookie_secure": True,
            "admin_2fa_required": True,
        }
        values.update(overrides)
        return Settings(**values)

    def test_s1_production_cors_origins_are_accepted_and_normalized(self) -> None:
        settings = self._production_settings(
            cors_origins="https://cyber-vpn.net/, https://admin.cyber-vpn.net/, https://partner.cyber-vpn.net/"
        )

        assert settings.cors_origins == [
            "https://cyber-vpn.net",
            "https://admin.cyber-vpn.net",
            "https://partner.cyber-vpn.net",
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

    def test_s1_production_rejects_short_telegram_bot_internal_secret(self) -> None:
        with pytest.raises(ValidationError, match="TELEGRAM_BOT_INTERNAL_SECRET"):
            self._production_settings(telegram_bot_internal_secret=SecretStr("short-secret"))

    def test_s1_production_rejects_placeholder_telegram_bot_internal_secret(self) -> None:
        with pytest.raises(ValidationError, match="TELEGRAM_BOT_INTERNAL_SECRET"):
            self._production_settings(
                telegram_bot_internal_secret=SecretStr("local-telegram-internal-placeholder-secret")
            )

    def test_s1_production_accepts_strong_telegram_bot_internal_secret(self) -> None:
        settings = self._production_settings(
            telegram_bot_internal_secret=SecretStr("StrongTelegramInternalCredentialForChecksOnly")
        )

        assert settings.telegram_bot_internal_secret.get_secret_value() == (
            "StrongTelegramInternalCredentialForChecksOnly"
        )

    def test_s1_production_rejects_short_backend_internal_secret(self) -> None:
        with pytest.raises(ValidationError, match="BACKEND_INTERNAL_SECRET"):
            self._production_settings(backend_internal_secret=SecretStr("short-secret"))

    def test_s1_production_rejects_placeholder_backend_internal_secret(self) -> None:
        with pytest.raises(ValidationError, match="BACKEND_INTERNAL_SECRET"):
            self._production_settings(backend_internal_secret=SecretStr("local-backend-internal-placeholder-secret"))

    def test_s1_production_rejects_backend_internal_secret_reuse_for_telegram_bot(self) -> None:
        with pytest.raises(ValidationError, match="must differ"):
            self._production_settings(
                backend_internal_secret=SecretStr(self.VALID_BACKEND_INTERNAL_SECRET),
                telegram_bot_internal_secret=SecretStr(self.VALID_BACKEND_INTERNAL_SECRET),
            )

    def test_s1_production_rejects_backend_internal_secret_reuse_for_payment_settlement_worker(self) -> None:
        with pytest.raises(ValidationError, match="must differ"):
            self._production_settings(
                backend_internal_secret=SecretStr(self.VALID_BACKEND_INTERNAL_SECRET),
                payment_settlement_worker_secret=SecretStr(self.VALID_BACKEND_INTERNAL_SECRET),
            )

    def test_s1_production_accepts_strong_backend_internal_secret_distinct_from_telegram(self) -> None:
        settings = self._production_settings(
            backend_internal_secret=SecretStr(self.VALID_BACKEND_INTERNAL_SECRET),
            telegram_bot_internal_secret=SecretStr("StrongTelegramInternalCredentialForChecksOnly"),
        )

        assert settings.backend_internal_secret.get_secret_value() == self.VALID_BACKEND_INTERNAL_SECRET

    def test_s1_production_rejects_cors_origin_with_path(self) -> None:
        with pytest.raises(ValidationError, match="path"):
            self._production_settings(cors_origins="https://cyber-vpn.net/app")

    def test_s1_production_rejects_local_stage_http_origins(self) -> None:
        with pytest.raises(ValidationError, match="https"):
            self._production_settings(cors_origins=sorted(S1_LOCAL_STAGE_BROWSER_ORIGINS))

    def test_s1_local_stage_accepts_approved_browser_origins(self) -> None:
        settings = Settings(
            environment="local-stage",
            jwt_secret=SecretStr(self.STRONG_SECRET),
            remnawave_token=SecretStr(self.VALID_TOKEN),
            cryptobot_token=SecretStr(self.VALID_TOKEN),
            cors_origins=(
                "http://localhost:13000/,http://localhost:13001/,http://127.0.0.1:13000/,http://127.0.0.1:13001/"
            ),
            cookie_secure=False,
        )

        assert settings.cors_origins == [
            "http://localhost:13000",
            "http://localhost:13001",
            "http://127.0.0.1:13000",
            "http://127.0.0.1:13001",
        ]

    def test_s1_local_stage_rejects_missing_approved_browser_origin(self) -> None:
        with pytest.raises(ValidationError, match="127.0.0.1:13001"):
            Settings(
                environment="local-stage",
                jwt_secret=SecretStr(self.STRONG_SECRET),
                remnawave_token=SecretStr(self.VALID_TOKEN),
                cryptobot_token=SecretStr(self.VALID_TOKEN),
                cors_origins=("http://localhost:13000,http://localhost:13001,http://127.0.0.1:13000"),
                cookie_secure=False,
            )

    def test_s1_local_stage_rejects_unapproved_loopback_origin(self) -> None:
        with pytest.raises(ValidationError, match="not approved"):
            Settings(
                environment="local-stage",
                jwt_secret=SecretStr(self.STRONG_SECRET),
                remnawave_token=SecretStr(self.VALID_TOKEN),
                cryptobot_token=SecretStr(self.VALID_TOKEN),
                cors_origins=(
                    "http://localhost:13000,"
                    "http://localhost:13001,"
                    "http://127.0.0.1:13000,"
                    "http://127.0.0.1:13001,"
                    "http://127.0.0.1:13002"
                ),
                cookie_secure=False,
            )

    def test_s1_local_stage_rejects_unapproved_non_loopback_origin(self) -> None:
        with pytest.raises(ValidationError, match="not approved"):
            Settings(
                environment="local-stage",
                jwt_secret=SecretStr(self.STRONG_SECRET),
                remnawave_token=SecretStr(self.VALID_TOKEN),
                cryptobot_token=SecretStr(self.VALID_TOKEN),
                cors_origins=(
                    "http://localhost:13000,"
                    "http://localhost:13001,"
                    "http://127.0.0.1:13000,"
                    "http://127.0.0.1:13001,"
                    "https://evil.example"
                ),
                cookie_secure=False,
            )

    def test_s1_local_stage_rejects_wildcard_cors(self) -> None:
        with pytest.raises(ValidationError, match="not allowed in local-stage"):
            Settings(
                environment="local-stage",
                jwt_secret=SecretStr(self.STRONG_SECRET),
                remnawave_token=SecretStr(self.VALID_TOKEN),
                cryptobot_token=SecretStr(self.VALID_TOKEN),
                cors_origins="*",
                cookie_secure=False,
            )

    def test_development_passkey_dev_origins_include_admin_localhost_smoke_origin(self) -> None:
        settings = Settings(
            _env_file=None,
            environment="development",
            jwt_secret=SecretStr(self.STRONG_SECRET),
            remnawave_token=SecretStr(self.VALID_TOKEN),
            cryptobot_token=SecretStr(self.VALID_TOKEN),
        )

        assert {
            "http://admin.localhost:3001",
            "http://127.0.0.1:9464",
        } <= set(settings.passkey_dev_allowed_origins)

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

    def test_web_device_cookie_defaults_to_host_prefixed_name(self) -> None:
        settings = self._production_settings()

        assert settings.web_device_cookie_name == "__Host-cvpn_device_id"
        assert settings.device_cookie_pepper_secret_name == "CYBERVPN_DEVICE_COOKIE_PEPPER"

    def test_web_device_cookie_name_must_use_host_prefix(self) -> None:
        with pytest.raises(ValidationError, match="__Host-"):
            self._production_settings(web_device_cookie_name="cvpn_device_id")

    def test_device_cookie_pepper_setting_names_secret_not_value(self) -> None:
        settings = self._production_settings(device_cookie_pepper_secret_name="CUSTOM_DEVICE_COOKIE_PEPPER")

        assert settings.device_cookie_pepper_secret_name == "CUSTOM_DEVICE_COOKIE_PEPPER"

    def test_device_cookie_pepper_secret_name_rejects_non_env_name(self) -> None:
        with pytest.raises(ValidationError, match="uppercase env-var"):
            self._production_settings(device_cookie_pepper_secret_name="raw-secret-value")

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


class TestPaymentSettlementWorkerSettings:
    """Test dedicated payment settlement worker credential guards."""

    STRONG_SECRET = TestWeakSecretPatterns.STRONG_SECRET
    VALID_TOKEN = TestWeakSecretPatterns.VALID_TOKEN
    VALID_PRODUCTION_PROVIDER_TOKEN = TestWeakSecretPatterns.VALID_PRODUCTION_PROVIDER_TOKEN
    VALID_WORKER_SECRET = TestWeakSecretPatterns.VALID_WORKER_SECRET

    def _production_settings(self, **overrides):
        values = {
            "environment": "production",
            "jwt_secret": SecretStr(self.STRONG_SECRET),
            "remnawave_token": SecretStr(self.VALID_TOKEN),
            "cryptobot_token": SecretStr(self.VALID_PRODUCTION_PROVIDER_TOKEN),
            "oauth_token_encryption_key": SecretStr(self.STRONG_SECRET),
            "oauth_enabled_login_providers": [],
            "cors_origins": list(S1_PRODUCTION_CORS_ORIGINS),
            "cookie_secure": True,
            "admin_2fa_required": True,
            "payment_settlement_worker_secret": SecretStr(self.VALID_WORKER_SECRET),
            "telegram_bot_internal_secret": SecretStr(""),
        }
        values.update(overrides)
        return Settings(**values)

    def test_production_requires_payment_settlement_worker_secret_when_enabled(self) -> None:
        with pytest.raises(ValidationError, match="PAYMENT_SETTLEMENT_WORKER_SECRET"):
            self._production_settings(payment_settlement_worker_secret=SecretStr(""))

    def test_production_rejects_telegram_secret_reuse_for_payment_settlement_worker(self) -> None:
        with pytest.raises(ValidationError, match="must differ"):
            self._production_settings(
                telegram_bot_internal_secret=SecretStr(self.VALID_WORKER_SECRET),
                payment_settlement_worker_secret=SecretStr(self.VALID_WORKER_SECRET),
            )

    def test_production_rejects_backend_secret_reuse_for_payment_settlement_worker(self) -> None:
        with pytest.raises(ValidationError, match="must differ"):
            self._production_settings(
                backend_internal_secret=SecretStr(self.VALID_WORKER_SECRET),
                payment_settlement_worker_secret=SecretStr(self.VALID_WORKER_SECRET),
            )

    def test_production_allows_worker_disabled_without_settlement_secret(self) -> None:
        settings = self._production_settings(
            payment_settlement_worker_enabled=False,
            payment_settlement_worker_secret=SecretStr(""),
        )

        assert settings.payment_settlement_worker_enabled is False


class TestVpnRuntimeAgentProductionSettings:
    def _production_settings(self, **overrides):
        values = {
            "environment": "production",
            "jwt_secret": SecretStr(TestWeakSecretPatterns.STRONG_SECRET),
            "remnawave_token": SecretStr(TestWeakSecretPatterns.VALID_TOKEN),
            "cryptobot_token": SecretStr(TestWeakSecretPatterns.VALID_PRODUCTION_PROVIDER_TOKEN),
            "payment_settlement_worker_secret": SecretStr(TestWeakSecretPatterns.VALID_WORKER_SECRET),
            "telegram_bot_internal_secret": SecretStr(""),
            "oauth_token_encryption_key": SecretStr(TestWeakSecretPatterns.STRONG_SECRET),
            "oauth_enabled_login_providers": [],
            "cors_origins": list(S1_PRODUCTION_CORS_ORIGINS),
            "cookie_secure": True,
            "admin_2fa_required": True,
            "vpn_tester_runtime_enabled": True,
            "vpn_test_agent_url": "http://cybervpn-vpn-test-agent:8080",
            "vpn_test_agent_secret": SecretStr("liveVpnRuntimeAgentCredentialAlpha123456"),
        }
        values.update(overrides)
        return Settings(**values)

    @pytest.mark.parametrize("secret", ["short", "replace-before-live-vpn-test-agent", "example-test-secret-value"])
    def test_production_runtime_rejects_weak_agent_secret(self, secret: str) -> None:
        with pytest.raises(ValidationError, match="VPN_TEST_AGENT_SECRET"):
            self._production_settings(vpn_test_agent_secret=SecretStr(secret))

    def test_production_runtime_requires_primary_agent_url_and_secret(self) -> None:
        with pytest.raises(ValidationError, match="configured together|required"):
            self._production_settings(vpn_test_agent_url="", vpn_test_agent_secret=None)

    def test_production_runtime_rejects_partial_regional_target(self) -> None:
        with pytest.raises(ValidationError, match="VPN_TEST_AGENT_MOSCOW"):
            self._production_settings(vpn_test_agent_moscow_url="http://moscow-agent:18080")

    def test_production_runtime_accepts_strong_agent_targets(self) -> None:
        configured = self._production_settings(
            vpn_test_agent_moscow_url="https://moscow-agent.example:18080",
            vpn_test_agent_moscow_secret=SecretStr("liveMoscowRuntimeAgentCredentialAlpha123"),
        )

        assert configured.vpn_tester_runtime_enabled is True

    @pytest.mark.parametrize(
        ("url_field", "secret_field"),
        [
            ("vpn_test_agent_url", "vpn_test_agent_secret"),
            ("vpn_test_agent_moscow_url", "vpn_test_agent_moscow_secret"),
            ("vpn_test_agent_spb_url", "vpn_test_agent_spb_secret"),
        ],
    )
    def test_production_runtime_rejects_remote_plaintext_agent_urls(self, url_field: str, secret_field: str) -> None:
        with pytest.raises(ValidationError, match="must use HTTPS"):
            self._production_settings(
                **{
                    url_field: "http://remote-agent.example:18080",
                    secret_field: SecretStr("liveRegionalRuntimeAgentCredentialAlpha123"),
                }
            )


class TestS2OAuthProductionReadiness:
    """Test S2 production OAuth login provider credential guards."""

    STRONG_SECRET = TestWeakSecretPatterns.STRONG_SECRET
    VALID_TOKEN = TestWeakSecretPatterns.VALID_TOKEN
    VALID_PRODUCTION_PROVIDER_TOKEN = TestWeakSecretPatterns.VALID_PRODUCTION_PROVIDER_TOKEN
    VALID_WORKER_SECRET = TestWeakSecretPatterns.VALID_WORKER_SECRET

    def _production_settings(self, **overrides):
        values = {
            "environment": "production",
            "jwt_secret": SecretStr(self.STRONG_SECRET),
            "remnawave_token": SecretStr(self.VALID_TOKEN),
            "cryptobot_token": SecretStr(self.VALID_PRODUCTION_PROVIDER_TOKEN),
            "payment_settlement_worker_secret": SecretStr(self.VALID_WORKER_SECRET),
            "telegram_bot_internal_secret": SecretStr(""),
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
