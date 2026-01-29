"""Security hardening utilities for the task-worker microservice.

Provides functions for:
- Masking sensitive values in logs (tokens, API keys, passwords)
- Validating that required secrets are properly configured
- Startup security checks to warn about missing or weak configuration

These utilities help prevent credential leakage and ensure secure deployment.
"""

import structlog

from src.config import get_settings

logger = structlog.get_logger(__name__)


def mask_secret(value: str, visible_chars: int = 4) -> str:
    """Mask a secret string, showing only last N characters.

    Args:
        value: The secret string to mask
        visible_chars: Number of characters to show at the end (default: 4)

    Returns:
        Masked string in format "***XXXX" where X are the last visible_chars

    Example:
        >>> mask_secret("sk_live_1234567890abcdef", 4)
        "***cdef"
        >>> mask_secret("short", 4)
        "***"
    """
    if not value:
        return "***"

    if len(value) <= visible_chars:
        return "***"

    return f"***{value[-visible_chars:]}"


def validate_secrets() -> list[str]:
    """Check all required secrets are configured and not using defaults.

    Validates:
    - REMNAWAVE_API_TOKEN is set and non-empty
    - TELEGRAM_BOT_TOKEN is set and non-empty
    - CRYPTOBOT_TOKEN is set and non-empty
    - DATABASE_URL is not using default development credentials

    Returns:
        List of warning messages for any missing or weak secrets.
        Empty list if all secrets are properly configured.

    Example:
        >>> warnings = validate_secrets()
        >>> if warnings:
        ...     for w in warnings:
        ...         print(f"Security warning: {w}")
    """
    settings = get_settings()
    warnings = []

    # Check Remnawave API token
    remnawave_token = settings.remnawave_api_token.get_secret_value()
    if not remnawave_token or remnawave_token.strip() == "":
        warnings.append("REMNAWAVE_API_TOKEN is not set or empty")
    elif len(remnawave_token) < 16:
        warnings.append("REMNAWAVE_API_TOKEN appears too short (minimum 16 characters recommended)")

    # Check Telegram bot token
    telegram_token = settings.telegram_bot_token.get_secret_value()
    if not telegram_token or telegram_token.strip() == "":
        warnings.append("TELEGRAM_BOT_TOKEN is not set or empty")
    elif not telegram_token.count(":") == 1:
        warnings.append("TELEGRAM_BOT_TOKEN format appears invalid (expected format: 'bot_id:token')")

    # Check CryptoBot token
    cryptobot_token = settings.cryptobot_token.get_secret_value()
    if not cryptobot_token or cryptobot_token.strip() == "":
        warnings.append("CRYPTOBOT_TOKEN is not set or empty")
    elif len(cryptobot_token) < 16:
        warnings.append("CRYPTOBOT_TOKEN appears too short (minimum 16 characters recommended)")

    # Check database URL for default credentials
    default_db_url = "postgresql+asyncpg://cybervpn:cybervpn@localhost:6767/cybervpn"
    if settings.database_url == default_db_url:
        warnings.append("DATABASE_URL appears to be using default development credentials")
    elif "cybervpn:cybervpn" in settings.database_url:
        warnings.append("DATABASE_URL contains default username/password 'cybervpn:cybervpn'")

    # Check Redis URL for default configuration in production
    if settings.environment.lower() == "production":
        if settings.redis_url == "redis://localhost:6379/0":
            warnings.append("REDIS_URL is using default localhost configuration in production")
        if "redis://:@" not in settings.redis_url and "redis://localhost" in settings.redis_url:
            warnings.append("REDIS_URL may not have authentication configured")

    return warnings


def run_security_checks() -> None:
    """Run all security validations at application startup.

    Validates secrets and logs warnings for any security issues found.
    If all checks pass, logs a confirmation message.

    This should be called during application initialization before
    starting any background tasks or accepting requests.

    Example:
        >>> # In your main.py startup function
        >>> from src.security import run_security_checks
        >>> run_security_checks()
    """
    logger.info("running_security_checks", environment=get_settings().environment)

    warnings = validate_secrets()

    if warnings:
        logger.warning(
            "security_checks_completed_with_warnings",
            warning_count=len(warnings),
            warnings=warnings,
        )
        for warning in warnings:
            logger.warning("security_check_warning", issue=warning)
    else:
        logger.info("security_checks_passed", message="All required secrets are properly configured")


def log_masked_config() -> None:
    """Log configuration with masked secrets for debugging.

    Useful for verifying configuration at startup without exposing secrets.
    """
    settings = get_settings()

    logger.info(
        "configuration_loaded",
        environment=settings.environment,
        log_level=settings.log_level,
        database_url=mask_secret(settings.database_url, 8),
        redis_url=mask_secret(settings.redis_url, 8),
        remnawave_url=settings.remnawave_url,
        remnawave_api_token=mask_secret(settings.remnawave_api_token.get_secret_value()),
        telegram_bot_token=mask_secret(settings.telegram_bot_token.get_secret_value()),
        cryptobot_token=mask_secret(settings.cryptobot_token.get_secret_value()),
        worker_concurrency=settings.worker_concurrency,
        metrics_port=settings.metrics_port,
    )
