"""Dependency injection factories for services and clients.

This module delegates to the central DI container.
Override via container.override() for testing.
"""

from src.application.services.auth_service import AuthService
from src.infrastructure.di.container import container
from src.infrastructure.payments.cryptobot.client import CryptoBotClient
from src.infrastructure.remnawave.client import RemnawaveClient


def get_auth_service() -> AuthService:
    """Factory for AuthService dependency injection."""
    return container.get("auth_service")()


def get_remnawave_client() -> RemnawaveClient:
    """Factory for RemnawaveClient dependency injection."""
    return container.get("remnawave_client")()


def get_crypto_client() -> CryptoBotClient:
    """Factory for CryptoBotClient dependency injection."""
    return container.get("cryptobot_client")()
