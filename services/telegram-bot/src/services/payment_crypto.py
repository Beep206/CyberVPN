"""CyberVPN Telegram Bot — Crypto Bot payment gateway service.

Handles invoice creation and payment verification through the
CyberVPN Backend API's Crypto Bot payment integration.
"""

from __future__ import annotations

from typing import Any

import structlog

from src.services.api_client import APIError, CyberVPNAPIClient

logger = structlog.get_logger(__name__)


class CryptoPaymentService:
    """Crypto Bot payment gateway integration.

    All operations are proxied through the CyberVPN Backend API.
    The bot never communicates directly with the Crypto Bot API.
    """

    def __init__(self, api_client: CyberVPNAPIClient) -> None:
        self._api = api_client

    async def create_invoice(
        self,
        amount: str,
        currency: str,
        user_uuid: str,
        plan_id: str,
        duration_days: int,
    ) -> dict[str, Any]:
        """Create a Crypto Bot payment invoice.

        Args:
            amount: Payment amount as string (e.g., "5.00").
            currency: Cryptocurrency code (e.g., "TON", "USDT").
            user_uuid: User's backend UUID.
            plan_id: Subscription plan ID.
            duration_days: Subscription duration.

        Returns:
            Invoice data with payment URL for the user.

        Raises:
            APIError: On backend errors.
        """
        payload = f"plan:{plan_id}:days:{duration_days}"
        logger.info(
            "creating_crypto_invoice",
            amount=amount,
            currency=currency,
            user_uuid=user_uuid,
            plan_id=plan_id,
        )

        result = await self._api.create_crypto_invoice(
            amount=amount,
            currency=currency,
            user_uuid=user_uuid,
            plan_id=plan_id,
            payload=payload,
        )

        logger.info(
            "crypto_invoice_created",
            invoice_id=result.get("invoice_id"),
        )
        return result

    async def check_payment_status(self, invoice_id: str) -> dict[str, Any]:
        """Check the status of a Crypto Bot payment.

        Args:
            invoice_id: Invoice identifier.

        Returns:
            Payment status data.
        """
        return await self._api.get_invoice_status(invoice_id)

    async def is_available(self) -> bool:
        """Check if Crypto Bot gateway is operational.

        Returns:
            True if the gateway is available.
        """
        try:
            await self._api.get_gateway_settings()
            return True
        except APIError:
            return False
