"""Dependency injection factories for services and clients.

This module provides factory functions for dependency injection following FastAPI best practices.
Each factory returns a new instance of the service/client to ensure proper lifecycle management
and enable easy testing through dependency overrides.
"""

from src.application.services.auth_service import AuthService
from src.config.settings import settings
from src.infrastructure.payments.cryptobot.client import CryptoBotClient
from src.infrastructure.remnawave.client import RemnawaveClient


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
    """Factory for RemnawaveClient dependency injection.

    Returns:
        RemnawaveClient: New instance of the Remnawave API client.

    Usage:
        @app.get("/endpoint")
        async def endpoint(client: RemnawaveClient = Depends(get_remnawave_client)):
            ...
    """
    return RemnawaveClient()


def get_crypto_client() -> CryptoBotClient:
    """Factory for CryptoBotClient dependency injection.

    Returns:
        CryptoBotClient: New instance of the CryptoBot payment client.

    Usage:
        @app.post("/endpoint")
        async def endpoint(crypto: CryptoBotClient = Depends(get_crypto_client)):
            ...

    Note:
        Requires settings.cryptobot_token to be configured.
    """
    return CryptoBotClient(token=settings.cryptobot_token)
