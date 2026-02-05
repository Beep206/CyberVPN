#!/usr/bin/env python3
"""Generate cryptographically strong secrets for CyberVPN configuration.

SEC-004: This script generates secure secrets for production deployment.
Run: python scripts/generate_secrets.py

Outputs secrets suitable for .env file or environment variables.
"""

import secrets


def generate_jwt_secret(length: int = 64) -> str:
    """Generate a cryptographically secure JWT secret.

    Args:
        length: Number of bytes for the secret (default 64 = 512 bits)

    Returns:
        URL-safe base64-encoded secret string
    """
    return secrets.token_urlsafe(length)


def generate_encryption_key(length: int = 32) -> str:
    """Generate a cryptographically secure AES-256 encryption key.

    Args:
        length: Number of bytes for the key (32 = 256 bits for AES-256)

    Returns:
        URL-safe base64-encoded key string
    """
    return secrets.token_urlsafe(length)


def generate_api_token(length: int = 32) -> str:
    """Generate a cryptographically secure API token.

    Args:
        length: Number of bytes for the token

    Returns:
        URL-safe base64-encoded token string
    """
    return secrets.token_urlsafe(length)


def main() -> None:
    """Generate and print all required secrets."""
    print("=" * 60)
    print("CyberVPN Secret Generator")
    print("SEC-004: Cryptographically Strong Secrets")
    print("=" * 60)
    print()

    # JWT Secret (minimum 32 chars required by settings validator)
    jwt_secret = generate_jwt_secret(64)
    print("# JWT Authentication")
    print(f"JWT_SECRET={jwt_secret}")
    print()

    # TOTP Encryption Key (AES-256-GCM)
    totp_key = generate_encryption_key(32)
    print("# TOTP Secret Encryption (AES-256-GCM)")
    print(f"TOTP_ENCRYPTION_KEY={totp_key}")
    print()

    # Remnawave API Token
    remnawave_token = generate_api_token(48)
    print("# Remnawave VPN Backend API")
    print(f"REMNAWAVE_TOKEN={remnawave_token}")
    print()

    # CryptoBot Payment Token
    cryptobot_token = generate_api_token(48)
    print("# CryptoBot Payment Gateway")
    print(f"CRYPTOBOT_TOKEN={cryptobot_token}")
    print()

    # Telegram Bot Token (note: real token comes from BotFather)
    print("# Telegram Bot (get real token from @BotFather)")
    print("# TELEGRAM_BOT_TOKEN=<get-from-botfather>")
    print()

    # GitHub OAuth (note: real values come from GitHub Developer Settings)
    print("# GitHub OAuth (configure at github.com/settings/developers)")
    print("# GITHUB_CLIENT_ID=<your-client-id>")
    print("# GITHUB_CLIENT_SECRET=<your-client-secret>")
    print()

    print("=" * 60)
    print("IMPORTANT: Store these secrets securely!")
    print("- Never commit secrets to version control")
    print("- Use environment variables or secret management")
    print("- Rotate secrets periodically")
    print("=" * 60)


if __name__ == "__main__":
    main()
