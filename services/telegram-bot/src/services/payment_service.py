"""Payment service for CyberVPN Telegram Bot.

Base payment service with support for multiple payment gateways
(CryptoBot, YooKassa, Telegram Stars).
"""

from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING, Any

import structlog

from src.models.payment import InvoiceDTO, PaymentGateway, PaymentStatus
from src.services.api_client import APIError

if TYPE_CHECKING:
    from src.config import Settings
    from src.services.api_client import CyberVPNAPIClient

logger = structlog.get_logger(__name__)


class PaymentService:
    """Base payment service with multi-gateway support.

    Provides unified interface for creating invoices, checking payment
    status, and handling callbacks from payment gateways.
    """

    def __init__(
        self,
        api_client: CyberVPNAPIClient,
        settings: Settings,
    ) -> None:
        """Initialize payment service.

        Args:
            api_client: Backend API client instance.
            settings: Application settings with payment gateway configs.
        """
        self._api = api_client
        self._settings = settings

    async def create_invoice(
        self,
        user_uuid: str,
        telegram_id: int,
        plan_id: str,
        duration_days: int,
        amount: Decimal,
        currency: str,
        gateway: PaymentGateway,
        *,
        payload: str | None = None,
    ) -> InvoiceDTO:
        """Create a payment invoice via specified gateway.

        Args:
            user_uuid: User's UUID in backend.
            telegram_id: User's Telegram ID.
            plan_id: Subscription plan identifier.
            duration_days: Subscription duration in days.
            amount: Payment amount.
            currency: Currency code (e.g., USD, EUR, TON).
            gateway: Payment gateway to use.
            payload: Optional custom payload/metadata.

        Returns:
            Created invoice with payment URL.

        Raises:
            APIError: On backend errors.
            ValueError: If gateway is not enabled or supported.
        """
        # Validate gateway availability
        if gateway == PaymentGateway.CRYPTOBOT and not self._settings.cryptobot.enabled:
            msg = "CryptoBot payment gateway is not enabled"
            raise ValueError(msg)
        if gateway == PaymentGateway.YOOKASSA and not self._settings.yookassa.enabled:
            msg = "YooKassa payment gateway is not enabled"
            raise ValueError(msg)
        if gateway == PaymentGateway.TELEGRAM_STARS and not self._settings.telegram_stars.enabled:
            msg = "Telegram Stars payment is not enabled"
            raise ValueError(msg)

        # Create invoice via appropriate gateway
        try:
            if gateway == PaymentGateway.CRYPTOBOT:
                invoice_data = await self._create_crypto_invoice(
                    user_uuid=user_uuid,
                    plan_id=plan_id,
                    amount=amount,
                    currency=currency,
                    payload=payload,
                )
            elif gateway == PaymentGateway.YOOKASSA:
                invoice_data = await self._create_yookassa_invoice(
                    user_uuid=user_uuid,
                    telegram_id=telegram_id,
                    plan_id=plan_id,
                    duration_days=duration_days,
                    amount=amount,
                    currency=currency,
                    payload=payload,
                )
            elif gateway == PaymentGateway.TELEGRAM_STARS:
                invoice_data = await self._create_stars_invoice(
                    telegram_id=telegram_id,
                    plan_id=plan_id,
                    amount=amount,
                    payload=payload,
                )
            else:
                msg = f"Unsupported payment gateway: {gateway}"
                raise ValueError(msg)

            logger.info(
                "invoice_created",
                telegram_id=telegram_id,
                plan_id=plan_id,
                gateway=gateway,
                amount=float(amount),
                currency=currency,
            )

            return InvoiceDTO.model_validate(invoice_data)

        except APIError as exc:
            logger.error(
                "invoice_create_error",
                telegram_id=telegram_id,
                gateway=gateway,
                error=str(exc),
            )
            raise

    async def _create_crypto_invoice(
        self,
        user_uuid: str,
        plan_id: str,
        amount: Decimal,
        currency: str,
        payload: str | None = None,
    ) -> dict[str, Any]:
        """Create CryptoBot invoice.

        Args:
            user_uuid: User's UUID.
            plan_id: Plan identifier.
            amount: Payment amount.
            currency: Crypto currency (e.g., TON, USDT).
            payload: Optional metadata.

        Returns:
            Invoice data from backend.
        """
        return await self._api.create_crypto_invoice(
            amount=str(amount),
            currency=currency,
            user_uuid=user_uuid,
            plan_id=plan_id,
            payload=payload or "",
        )

    async def _create_yookassa_invoice(
        self,
        user_uuid: str,
        telegram_id: int,
        plan_id: str,
        duration_days: int,
        amount: Decimal,
        currency: str,
        payload: str | None = None,
    ) -> dict[str, Any]:
        """Create YooKassa invoice.

        Args:
            user_uuid: User's UUID.
            telegram_id: User's Telegram ID.
            plan_id: Plan identifier.
            duration_days: Subscription duration.
            amount: Payment amount.
            currency: Currency code (RUB, USD, EUR).
            payload: Optional metadata.

        Returns:
            Invoice data from backend.
        """
        # YooKassa integration would go through backend API
        # This is a placeholder that assumes backend has a YooKassa endpoint
        return await self._api._request(
            "POST",
            "/telegram/payments/yookassa/invoice",
            json={
                "user_uuid": user_uuid,
                "telegram_id": telegram_id,
                "plan_id": plan_id,
                "duration_days": duration_days,
                "amount": str(amount),
                "currency": currency,
                "payload": payload or "",
            },
        )

    async def _create_stars_invoice(
        self,
        telegram_id: int,
        plan_id: str,
        amount: Decimal,
        payload: str | None = None,
    ) -> dict[str, Any]:
        """Create Telegram Stars invoice.

        Args:
            telegram_id: User's Telegram ID.
            plan_id: Plan identifier.
            amount: Payment amount in Stars.
            payload: Optional metadata.

        Returns:
            Invoice data from backend.
        """
        # Telegram Stars integration through backend
        return await self._api._request(
            "POST",
            "/telegram/payments/stars/invoice",
            json={
                "telegram_id": telegram_id,
                "plan_id": plan_id,
                "amount": int(amount),
                "payload": payload or "",
            },
        )

    async def check_status(
        self,
        invoice_id: str,
        gateway: PaymentGateway,
    ) -> PaymentStatus:
        """Check payment status for an invoice.

        Args:
            invoice_id: Invoice identifier.
            gateway: Payment gateway used.

        Returns:
            Current payment status.

        Raises:
            APIError: On backend errors.
        """
        try:
            status_data = await self._api._request(
                "GET",
                f"/telegram/payments/{gateway}/status/{invoice_id}",
            )
            logger.info(
                "payment_status_checked",
                invoice_id=invoice_id,
                gateway=gateway,
                status=status_data.get("status"),
            )
            return PaymentStatus(status_data.get("status", "pending"))

        except APIError as exc:
            logger.error(
                "payment_status_check_error",
                invoice_id=invoice_id,
                gateway=gateway,
                error=str(exc),
            )
            raise

    async def handle_callback(
        self,
        gateway: PaymentGateway,
        callback_data: dict[str, Any],
    ) -> dict[str, Any]:
        """Handle payment callback/webhook from gateway.

        Args:
            gateway: Payment gateway that sent the callback.
            callback_data: Callback payload from gateway.

        Returns:
            Processed payment data.

        Raises:
            APIError: On backend processing errors.
        """
        try:
            result = await self._api._request(
                "POST",
                f"/telegram/payments/{gateway}/callback",
                json=callback_data,
            )
            logger.info(
                "payment_callback_handled",
                gateway=gateway,
                status=result.get("status"),
            )
            return result

        except APIError as exc:
            logger.error(
                "payment_callback_error",
                gateway=gateway,
                error=str(exc),
            )
            raise
