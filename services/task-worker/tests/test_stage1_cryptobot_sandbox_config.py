"""S1-PAY-002 CryptoBot sandbox/testnet config guards for task-worker."""

from __future__ import annotations

import pytest
from pydantic import SecretStr, ValidationError

from src.config import Settings


def _settings(**overrides: object) -> Settings:
    values = {
        "remnawave_api_token": SecretStr("remnawave-token-for-s1-pay-002"),
        "telegram_bot_token": SecretStr("123456:telegram-token-for-s1-pay-002"),
        "cryptobot_token": SecretStr("cryptobot-token-for-s1-pay-002"),
        "backend_api_url": "https://api.cyber-vpn.net/api/v1",
        "backend_internal_secret": SecretStr("InternalBackendCredentialForChecksOnly"),
        "telegram_bot_internal_secret": SecretStr("TelegramBotInternalCredentialForChecksOnly"),
        "payment_settlement_worker_secret": SecretStr("SettlementWorkerCredentialForChecksOnly"),
        "email_dev_mode": False,
        "resend_api_key": None,
        "brevo_api_key": None,
        "email_resend_fallback_enabled": False,
        "metrics_protect": False,
    }
    values.update(overrides)
    return Settings(**values)


def test_task_worker_allows_cryptobot_testnet_outside_production() -> None:
    settings = _settings(environment="staging", cryptobot_network="testnet")

    assert settings.cryptobot_network == "testnet"


def test_task_worker_production_rejects_cryptobot_testnet() -> None:
    with pytest.raises(ValidationError, match="CRYPTOBOT_NETWORK=testnet is not allowed in production"):
        _settings(environment="production", cryptobot_network="testnet")


def test_task_worker_production_rejects_placeholder_cryptobot_token() -> None:
    with pytest.raises(ValidationError, match="CRYPTOBOT_TOKEN must not be a placeholder/test value"):
        _settings(
            environment="production",
            cryptobot_token=SecretStr("your_cryptobot_api_token_here"),
        )


def test_task_worker_production_accepts_non_placeholder_provider_shaped_token() -> None:
    settings = _settings(
        environment="production",
        cryptobot_token=SecretStr("ValidProviderTokenValueForChecksOnly"),
        magic_link_base_url="https://cyber-vpn.net",
        smtp_auth_username="noreply@cyber-vpn.net",
        smtp_auth_password=SecretStr("ValidSmtpMailboxPasswordForChecksOnly"),
        email_verified_sender_domains=["cyber-vpn.net"],
    )

    assert settings.cryptobot_token.get_secret_value() == "ValidProviderTokenValueForChecksOnly"


def test_task_worker_production_rejects_short_backend_internal_secret() -> None:
    with pytest.raises(ValidationError, match="BACKEND_INTERNAL_SECRET"):
        _settings(
            environment="production",
            backend_internal_secret=SecretStr("short-secret"),
            cryptobot_token=SecretStr("ValidProviderTokenValueForChecksOnly"),
            magic_link_base_url="https://cyber-vpn.net",
            smtp_auth_username="noreply@cyber-vpn.net",
            smtp_auth_password=SecretStr("ValidSmtpMailboxPasswordForChecksOnly"),
            email_verified_sender_domains=["cyber-vpn.net"],
        )


def test_task_worker_production_rejects_placeholder_backend_internal_secret() -> None:
    with pytest.raises(ValidationError, match="BACKEND_INTERNAL_SECRET"):
        _settings(
            environment="production",
            backend_internal_secret=SecretStr("local-backend-internal-placeholder-secret"),
            cryptobot_token=SecretStr("ValidProviderTokenValueForChecksOnly"),
            magic_link_base_url="https://cyber-vpn.net",
            smtp_auth_username="noreply@cyber-vpn.net",
            smtp_auth_password=SecretStr("ValidSmtpMailboxPasswordForChecksOnly"),
            email_verified_sender_domains=["cyber-vpn.net"],
        )


def test_task_worker_production_rejects_missing_telegram_bot_internal_secret() -> None:
    with pytest.raises(ValidationError, match="TELEGRAM_BOT_INTERNAL_SECRET"):
        _settings(
            environment="production",
            telegram_bot_internal_secret=None,
            cryptobot_token=SecretStr("ValidProviderTokenValueForChecksOnly"),
            magic_link_base_url="https://cyber-vpn.net",
            smtp_auth_username="noreply@cyber-vpn.net",
            smtp_auth_password=SecretStr("ValidSmtpMailboxPasswordForChecksOnly"),
            email_verified_sender_domains=["cyber-vpn.net"],
        )


def test_task_worker_production_rejects_backend_secret_reuse_for_telegram_bot() -> None:
    with pytest.raises(ValidationError, match="TELEGRAM_BOT_INTERNAL_SECRET must differ"):
        _settings(
            environment="production",
            backend_internal_secret=SecretStr("SharedInternalCredentialForChecksOnly"),
            telegram_bot_internal_secret=SecretStr("SharedInternalCredentialForChecksOnly"),
            cryptobot_token=SecretStr("ValidProviderTokenValueForChecksOnly"),
            magic_link_base_url="https://cyber-vpn.net",
            smtp_auth_username="noreply@cyber-vpn.net",
            smtp_auth_password=SecretStr("ValidSmtpMailboxPasswordForChecksOnly"),
            email_verified_sender_domains=["cyber-vpn.net"],
        )


def test_task_worker_production_rejects_enabled_payment_earnings_without_backend_url() -> None:
    with pytest.raises(ValidationError, match="BACKEND_API_URL"):
        _settings(
            environment="production",
            backend_api_url=None,
            backend_internal_secret=None,
            cryptobot_token=SecretStr("ValidProviderTokenValueForChecksOnly"),
            email_dev_mode=False,
            magic_link_base_url="https://cyber-vpn.net",
            smtp_auth_username="noreply@cyber-vpn.net",
            smtp_auth_password=SecretStr("ValidSmtpMailboxPasswordForChecksOnly"),
            email_verified_sender_domains=["cyber-vpn.net"],
        )


def test_task_worker_production_rejects_enabled_payment_earnings_without_worker_secret() -> None:
    with pytest.raises(ValidationError, match="PAYMENT_SETTLEMENT_WORKER_SECRET"):
        _settings(
            environment="production",
            payment_settlement_worker_secret=None,
            cryptobot_token=SecretStr("ValidProviderTokenValueForChecksOnly"),
            email_dev_mode=False,
            magic_link_base_url="https://cyber-vpn.net",
            smtp_auth_username="noreply@cyber-vpn.net",
            smtp_auth_password=SecretStr("ValidSmtpMailboxPasswordForChecksOnly"),
            email_verified_sender_domains=["cyber-vpn.net"],
        )


def test_task_worker_production_rejects_backend_secret_reuse_for_payment_earnings_worker() -> None:
    with pytest.raises(ValidationError, match="PAYMENT_SETTLEMENT_WORKER_SECRET must differ"):
        _settings(
            environment="production",
            backend_internal_secret=SecretStr("SharedInternalCredentialForChecksOnly"),
            payment_settlement_worker_secret=SecretStr("SharedInternalCredentialForChecksOnly"),
            cryptobot_token=SecretStr("ValidProviderTokenValueForChecksOnly"),
            email_dev_mode=False,
            magic_link_base_url="https://cyber-vpn.net",
            smtp_auth_username="noreply@cyber-vpn.net",
            smtp_auth_password=SecretStr("ValidSmtpMailboxPasswordForChecksOnly"),
            email_verified_sender_domains=["cyber-vpn.net"],
        )


def test_task_worker_production_rejects_telegram_secret_reuse_for_payment_earnings_worker() -> None:
    with pytest.raises(ValidationError, match="PAYMENT_SETTLEMENT_WORKER_SECRET must differ"):
        _settings(
            environment="production",
            telegram_bot_internal_secret=SecretStr("SharedTelegramSettlementCredential"),
            payment_settlement_worker_secret=SecretStr("SharedTelegramSettlementCredential"),
            cryptobot_token=SecretStr("ValidProviderTokenValueForChecksOnly"),
            email_dev_mode=False,
            magic_link_base_url="https://cyber-vpn.net",
            smtp_auth_username="noreply@cyber-vpn.net",
            smtp_auth_password=SecretStr("ValidSmtpMailboxPasswordForChecksOnly"),
            email_verified_sender_domains=["cyber-vpn.net"],
        )


def test_task_worker_production_allows_disabled_payment_earnings_without_worker_secret() -> None:
    settings = _settings(
        environment="production",
        payment_completed_partner_earnings_enabled=False,
        payment_settlement_worker_secret=None,
        cryptobot_token=SecretStr("ValidProviderTokenValueForChecksOnly"),
        email_dev_mode=False,
        magic_link_base_url="https://cyber-vpn.net",
        smtp_auth_username="noreply@cyber-vpn.net",
        smtp_auth_password=SecretStr("ValidSmtpMailboxPasswordForChecksOnly"),
        email_verified_sender_domains=["cyber-vpn.net"],
    )

    assert settings.payment_completed_partner_earnings_enabled is False


def _production_mail_settings(**overrides: object) -> Settings:
    values = {
        "environment": "production",
        "cryptobot_token": SecretStr("ValidCryptoBotProviderTokenForMailChecks"),
        "magic_link_base_url": "https://cyber-vpn.net",
        "email_dev_mode": False,
        "smtp_auth_username": "noreply@cyber-vpn.net",
        "smtp_auth_password": SecretStr("ValidSmtpMailboxPasswordForMailChecks"),
        "smtp_system_from_email": "CyberVPN <noreply@cyber-vpn.net>",
        "smtp_billing_from_email": "CyberVPN Billing <billing@cyber-vpn.net>",
        "smtp_support_from_email": "CyberVPN Support <support@cyber-vpn.net>",
        "resend_from_email": "CyberVPN <verify@email.cyber-vpn.net>",
        "brevo_from_email": "CyberVPN <noreply@email.cyber-vpn.net>",
        "email_verified_sender_domains": ["cyber-vpn.net"],
    }
    values.update(overrides)
    return _settings(**values)


def test_task_worker_production_rejects_mail_dev_mode() -> None:
    with pytest.raises(ValidationError, match="EMAIL_DEV_MODE=true is not allowed in production"):
        _production_mail_settings(email_dev_mode=True)


def test_task_worker_production_rejects_non_https_magic_link_base_url() -> None:
    with pytest.raises(ValidationError, match="MAGIC_LINK_BASE_URL must be a canonical https origin"):
        _production_mail_settings(magic_link_base_url="http://cyber-vpn.net")


def test_task_worker_production_rejects_magic_link_base_url_with_query() -> None:
    with pytest.raises(ValidationError, match="MAGIC_LINK_BASE_URL must not include path, params, or query"):
        _production_mail_settings(magic_link_base_url="https://cyber-vpn.net/login?next=/dashboard")


def test_task_worker_production_rejects_resend_placeholder_token() -> None:
    with pytest.raises(ValidationError, match="RESEND_API_KEY must not be a placeholder/test value"):
        _production_mail_settings(
            email_resend_fallback_enabled=True,
            resend_api_key=SecretStr("your_resend_api_key_here"),
        )


def test_task_worker_production_requires_smtp_credentials() -> None:
    with pytest.raises(ValidationError, match="SMTP_AUTH_PASSWORD is required"):
        _production_mail_settings(smtp_auth_password=None)


def test_task_worker_production_requires_resend_key_when_fallback_enabled() -> None:
    with pytest.raises(ValidationError, match="RESEND_API_KEY is required"):
        _production_mail_settings(email_resend_fallback_enabled=True, resend_api_key=None)


def test_task_worker_production_requires_verified_sender_domain_evidence() -> None:
    with pytest.raises(ValidationError, match="EMAIL_VERIFIED_SENDER_DOMAINS"):
        _production_mail_settings(email_verified_sender_domains=["example.test"])


def test_task_worker_production_accepts_verified_brevo_sender_domain() -> None:
    settings = _production_mail_settings(
        brevo_api_key=SecretStr("ValidBrevoProviderTokenForMailChecks"),
        brevo_from_email="CyberVPN <noreply@email.cyber-vpn.net>",
        email_verified_sender_domains="cyber-vpn.net,email.cyber-vpn.net",
    )

    assert settings.brevo_api_key is not None


def test_task_worker_production_accepts_explicit_resend_fallback() -> None:
    settings = _production_mail_settings(
        email_resend_fallback_enabled=True,
        resend_api_key=SecretStr("ValidResendProviderTokenForMailChecks"),
        email_verified_sender_domains="cyber-vpn.net,email.cyber-vpn.net",
    )

    assert settings.email_resend_fallback_enabled is True
