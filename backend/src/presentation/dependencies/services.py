"""Dependency injection factories for services and clients.

This module provides factory functions for dependency injection following FastAPI best practices.
Services are lightweight per-request where appropriate, while HTTP clients reuse shared instances
managed during application lifespan for connection pooling.
"""

from src.application.services.auth_service import AuthService
from src.infrastructure.payments.cryptobot.client import CryptoBotClient, cryptobot_client
from src.infrastructure.remnawave.client import RemnawaveClient, remnawave_client


def get_auth_service() -> AuthService:
    """Factory for AuthService dependency injection.

    Returns:
        AuthService: New instance of the authentication service.

    Usage:
        @app.get("/endpoint")
        async def endpoint(auth_service: AuthService = Depends(get_auth_service)):
            ...
    """
    return AuthService()


def get_remnawave_client() -> RemnawaveClient:
    """Factory for RemnawaveClient dependency injection."""
    return remnawave_client


def get_crypto_client() -> CryptoBotClient:
    """Factory for CryptoBotClient dependency injection."""
    return cryptobot_client
