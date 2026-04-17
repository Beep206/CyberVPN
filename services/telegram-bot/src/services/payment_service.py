"""Payment service for CyberVPN Telegram Bot.

Base payment service with support for multiple payment gateways
(CryptoBot, YooKassa, Telegram Stars).
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Any

import structlog

from src.models.payment import InvoiceDTO, PaymentGateway, PaymentStatus
from src.services.api_client import APIError

if TYPE_CHECKING:
    from src.config import BotSettings
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
        settings: BotSettings,
    ) -> None:
        """Initialize payment service.

        Args:
            api_client: Backend API client instance.
            settings: Application settings with payment gateway configs.
        """
        self._api = api_client
        self._settings = settings

    @staticmethod
    def _status_from_value(value: str | None) -> PaymentStatus:
        normalized = (value or "pending").lower()
        try:
            return PaymentStatus(normalized)
        except ValueError:
            return PaymentStatus.PENDING

    @staticmethod
    def _gateway_to_method(gateway: PaymentGateway) -> str:
        return gateway.value

    @staticmethod
    def _parse_payload(payload: str | None) -> dict[str, Any]:
        if not payload:
            return {}
        try:
            data = json.loads(payload)
            return data if isinstance(data, dict) else {}
        except json.JSONDecodeError:
            return {}

    def _validate_gateway_enabled(self, gateway: PaymentGateway) -> None:
        if gateway == PaymentGateway.CRYPTOBOT and not self._settings.cryptobot.enabled:
            msg = "CryptoBot payment gateway is not enabled"
            raise ValueError(msg)
        if gateway == PaymentGateway.YOOKASSA and not self._settings.yookassa.enabled:
            msg = "YooKassa payment gateway is not enabled"
            raise ValueError(msg)
        if gateway == PaymentGateway.TELEGRAM_STARS and not self._settings.telegram_stars.enabled:
            msg = "Telegram Stars payment is not enabled"
            raise ValueError(msg)

    async def _create_checkout_invoice(
        self,
        *,
        telegram_id: int,
        plan_id: str,
        currency: str,
        gateway: PaymentGateway,
        payload: str | None = None,
    ) -> dict[str, Any]:
        parsed_payload = self._parse_payload(payload)
        commit_payload = {
            "plan_id": plan_id,
            "addons": parsed_payload.get("addons") or [],
            "promo_code": parsed_payload.get("promo_code"),
            "use_wallet": parsed_payload.get("use_wallet", 0),
            "currency": currency,
            "payment_method": self._gateway_to_method(gateway),
        }
        return await self._api.commit_checkout(telegram_id, commit_payload)

    @classmethod
    def _build_invoice_dto(
        cls,
        *,
        gateway: PaymentGateway,
        checkout_result: dict[str, Any],
        fallback_amount: Decimal,
        currency: str,
        payload: str | None,
    ) -> InvoiceDTO:
        invoice = checkout_result.get("invoice") or {}
        payment_id = str(checkout_result.get("payment_id") or invoice.get("invoice_id") or invoice.get("id") or "")
        amount_value = (
            checkout_result.get("gateway_amount")
            or checkout_result.get("displayed_price")
            or invoice.get("amount")
            or fallback_amount
        )
        amount = Decimal(str(amount_value))
        created_at = checkout_result.get("created_at") or invoice.get("created_at") or datetime.now(UTC)
        expires_at = invoice.get("expires_at")
        if not payment_id:
            msg = "Canonical checkout did not return a payment identifier"
            raise APIError(msg, status_code=500)

        return InvoiceDTO.model_validate(
            {
                "id": payment_id,
                "gateway": gateway,
                "amount": amount,
                "currency": str(checkout_result.get("currency") or invoice.get("currency") or currency).upper(),
                "status": cls._status_from_value(checkout_result.get("status")),
                "payment_url": invoice.get("payment_url"),
                "payload": payload or "",
                "created_at": created_at,
                "expires_at": expires_at,
            }
        )

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
        _ = user_uuid
        _ = duration_days
        self._validate_gateway_enabled(gateway)

        try:
            checkout_result = await self._create_checkout_invoice(
                telegram_id=telegram_id,
                plan_id=plan_id,
                currency=currency,
                gateway=gateway,
                payload=payload,
            )
            logger.info(
                "invoice_created",
                telegram_id=telegram_id,
                plan_id=plan_id,
                gateway=gateway,
                amount=float(amount),
                currency=currency,
            )
            return self._build_invoice_dto(
                gateway=gateway,
                checkout_result=checkout_result,
                fallback_amount=amount,
                currency=currency,
                payload=payload,
            )

        except APIError as exc:
            logger.error(
                "invoice_create_error",
                telegram_id=telegram_id,
                gateway=gateway,
                error=str(exc),
            )
            raise

    async def check_status(
        self,
        invoice_id: str,
        gateway: PaymentGateway,
        *,
        telegram_id: int | None = None,
    ) -> PaymentStatus:
        """Check payment status for an invoice.

        Args:
            invoice_id: Invoice identifier.
            gateway: Payment gateway used.
            telegram_id: Telegram user ID required by the canonical bot API.

        Returns:
            Current payment status.

        Raises:
            APIError: On backend errors.
        """
        _ = gateway
        if telegram_id is None:
            msg = "telegram_id is required for canonical payment status checks"
            raise ValueError(msg)

        try:
            status_data = await self._api.get_payment_status(telegram_id, invoice_id)
            logger.info(
                "payment_status_checked",
                invoice_id=invoice_id,
                telegram_id=telegram_id,
                status=status_data.get("status"),
            )
            return self._status_from_value(status_data.get("status"))

        except APIError as exc:
            logger.error(
                "payment_status_check_error",
                invoice_id=invoice_id,
                telegram_id=telegram_id,
                error=str(exc),
            )
            raise

    async def verify_payment(
        self,
        invoice_id: str,
        *,
        telegram_id: int,
    ) -> PaymentStatus:
        """Compatibility alias for legacy callers expecting verify_payment()."""

        return await self.check_status(
            invoice_id=invoice_id,
            gateway=PaymentGateway.CRYPTOBOT,
            telegram_id=telegram_id,
        )

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
            result = await self._api._request_dict(
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
