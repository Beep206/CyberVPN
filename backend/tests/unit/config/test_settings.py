"""Unit tests for settings validation.

MED-005: Test weak secret pattern rejection.
"""

import pytest
from pydantic import SecretStr, ValidationError

from src.config.settings import Settings


class TestWeakSecretPatterns:
    """Test JWT secret validation rejects weak patterns in production."""

    # Generate a valid-length secret with weak pattern embedded
    WEAK_SECRETS = [
        "test_secret_key_that_is_long_enough_32chars",
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

    @pytest.mark.parametrize("weak_secret", WEAK_SECRETS)
    def test_weak_secrets_rejected_in_production(self, weak_secret: str) -> None:
        """Verify weak secrets are rejected in production environment."""
        with pytest.raises(ValidationError) as exc_info:
            Settings(
                environment="production",
                jwt_secret=SecretStr(weak_secret),
                remnawave_token=SecretStr(self.VALID_TOKEN),
                cryptobot_token=SecretStr(self.VALID_TOKEN),
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
            cryptobot_token=SecretStr(self.VALID_TOKEN),
        )
        assert settings.jwt_secret.get_secret_value() == self.STRONG_SECRET

    def test_weak_secrets_allowed_in_development(self) -> None:
        """Verify weak secrets are allowed in development environment."""
        weak_secret = "test_secret_key_that_is_long_enough_32chars"

        # Should not raise in development
        settings = Settings(
            environment="development",
            jwt_secret=SecretStr(weak_secret),
            remnawave_token=SecretStr(self.VALID_TOKEN),
            cryptobot_token=SecretStr(self.VALID_TOKEN),
        )
        assert "test_secret" in settings.jwt_secret.get_secret_value()

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
