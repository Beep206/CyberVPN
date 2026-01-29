"""CyberVPN Telegram Bot — YooKassa payment gateway service.

Handles payment creation and verification through the
CyberVPN Backend API's YooKassa integration.
"""

from __future__ import annotations

from typing import Any

import structlog

from src.services.api_client import APIError, CyberVPNAPIClient

logger = structlog.get_logger(__name__)


class YooKassaPaymentService:
    """YooKassa payment gateway integration.

    All operations are proxied through the CyberVPN Backend API.
    The bot never communicates directly with the YooKassa API.
    """

    def __init__(self, api_client: CyberVPNAPIClient) -> None:
        self._api = api_client

    async def create_payment(
        self,
        amount: str,
        description: str,
        user_uuid: str,
        plan_id: str,
        duration_days: int,
        return_url: str | None = None,
    ) -> dict[str, Any]:
        """Create a YooKassa payment.

        Args:
            amount: Payment amount in RUB as string.
            description: Payment description.
            user_uuid: User's backend UUID.
            plan_id: Subscription plan ID.
            duration_days: Subscription duration.
            return_url: URL to redirect after payment.

        Returns:
            Payment data with confirmation URL.

        Raises:
            APIError: On backend errors.
        """
        metadata = {
            "user_uuid": user_uuid,
            "plan_id": plan_id,
            "duration_days": str(duration_days),
        }
        if return_url:
            metadata["return_url"] = return_url

        logger.info(
            "creating_yookassa_payment",
            amount=amount,
            user_uuid=user_uuid,
            plan_id=plan_id,
        )

        result = await self._api.create_yookassa_payment(
            amount=amount,
            description=description,
            metadata=metadata,
        )

        logger.info(
            "yookassa_payment_created",
            payment_id=result.get("payment_id"),
        )
        return result

    async def check_payment_status(self, payment_id: str) -> dict[str, Any]:
        """Check the status of a YooKassa payment.

        Args:
            payment_id: Payment identifier.

        Returns:
            Payment status data.
        """
        return await self._api.get_invoice_status(payment_id)

    async def is_available(self) -> bool:
        """Check if YooKassa gateway is operational.

        Returns:
            True if the gateway is available.
        """
        try:
            await self._api.get_gateway_settings()
            return True
        except APIError:
            return False
