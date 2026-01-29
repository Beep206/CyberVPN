"""CyberVPN Telegram Bot — Telegram Stars payment service.

Handles Telegram Stars payment flow using Telegram's built-in
payment system via the CyberVPN Backend API.
"""

from __future__ import annotations

from typing import Any

import structlog

from src.services.api_client import APIError, CyberVPNAPIClient

logger = structlog.get_logger(__name__)


class StarsPaymentService:
    """Telegram Stars payment integration.

    Uses Telegram's native payment system where users pay with Stars.
    Invoice creation is proxied through the CyberVPN Backend API.
    """

    def __init__(self, api_client: CyberVPNAPIClient) -> None:
        self._api = api_client

    async def create_invoice(
        self,
        telegram_id: int,
        plan_id: str,
        duration_days: int,
        stars_amount: int,
    ) -> dict[str, Any]:
        """Create a Telegram Stars invoice.

        Args:
            telegram_id: User's Telegram ID.
            plan_id: Subscription plan ID.
            duration_days: Subscription duration.
            stars_amount: Amount in Telegram Stars.

        Returns:
            Invoice data for creating Telegram payment.

        Raises:
            APIError: On backend errors.
        """
        logger.info(
            "creating_stars_invoice",
            telegram_id=telegram_id,
            plan_id=plan_id,
            stars_amount=stars_amount,
        )

        result = await self._api.create_stars_invoice(
            telegram_id=telegram_id,
            plan_id=plan_id,
            duration_days=duration_days,
            amount=stars_amount,
        )

        logger.info(
            "stars_invoice_created",
            invoice_id=result.get("invoice_id"),
        )
        return result

    async def check_payment_status(self, invoice_id: str) -> dict[str, Any]:
        """Check Telegram Stars payment status.

        Args:
            invoice_id: Invoice identifier.

        Returns:
            Payment status data.
        """
        return await self._api.get_invoice_status(invoice_id)

    async def is_available(self) -> bool:
        """Check if Stars payments are enabled.

        Returns:
            True if Stars gateway is available.
        """
        try:
            settings = await self._api.get_gateway_settings()
            return settings.get("stars_enabled", False)
        except APIError:
            return False
