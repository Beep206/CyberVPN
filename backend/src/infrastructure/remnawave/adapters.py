"""Adapters for Remnawave gateway to match use case protocols."""

from typing import Any

import structlog

from src.infrastructure.remnawave.user_gateway import RemnawaveUserGateway

logger = structlog.get_logger(__name__)


class RemnawaveUserAdapter:
    """
    Adapter for RemnawaveUserGateway that matches VerifyOtpUseCase.RemnawaveGateway protocol.

    Wraps the existing gateway to provide a simplified interface for user creation
    during email verification.
    """

    def __init__(self, gateway: RemnawaveUserGateway) -> None:
        self._gateway = gateway

    async def create_user(
        self,
        username: str,
        email: str,
        telegram_id: int | None = None,
    ) -> dict:
        """
        Create user in Remnawave VPN backend.

        Args:
            username: User's login name
            email: User's email address
            telegram_id: Optional Telegram ID for linking

        Returns:
            dict with user data from Remnawave

        Raises:
            Exception: If Remnawave API call fails
        """
        logger.info(
            "creating_remnawave_user",
            username=username,
            email=email,
            has_telegram_id=telegram_id is not None,
        )

        kwargs: dict[str, Any] = {"email": email}
        if telegram_id:
            kwargs["telegram_id"] = telegram_id

        user = await self._gateway.create(username=username, **kwargs)

        logger.info(
            "remnawave_user_created",
            username=username,
            remnawave_uuid=str(user.uuid) if user else None,
        )

        # Return dict for protocol compatibility
        return {
            "uuid": str(user.uuid) if user else None,
            "username": user.username if user else username,
            "email": email,
        }


def get_remnawave_adapter() -> RemnawaveUserAdapter:
    """
    Get Remnawave user adapter instance.

    For use as a FastAPI dependency.
    """
    from src.infrastructure.remnawave.client import remnawave_client

    gateway = RemnawaveUserGateway(remnawave_client)
    return RemnawaveUserAdapter(gateway)
