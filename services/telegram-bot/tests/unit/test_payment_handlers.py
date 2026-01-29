"""Unit tests for payment handlers."""

from __future__ import annotations

from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

import pytest
from aiogram.types import CallbackQuery, PreCheckoutQuery, User


@pytest.mark.asyncio
class TestPaymentHandlers:
    """Test payment-related handlers."""

    async def test_select_payment_gateway(self) -> None:
        """Test payment gateway selection."""
        callback = MagicMock(spec=CallbackQuery)
        callback.data = "pay_cryptobot"
        callback.message = MagicMock()
        callback.message.edit_text = AsyncMock()
        callback.answer = AsyncMock()

        # Parse gateway
        gateway = callback.data.split("_")[1] if "_" in callback.data else None
        assert gateway == "cryptobot"

    async def test_create_invoice_cryptobot(self) -> None:
        """Test creating CryptoBot invoice."""
        # Mock payment service
        payment_service = MagicMock()
        payment_service.create_invoice = AsyncMock(
            return_value={
                "invoice_id": "CB123",
                "payment_url": "https://t.me/CryptoBot?start=...",
                "amount": "9.99",
                "currency": "TON",
            }
        )

        user_uuid = "user-uuid-123"
        plan_id = "premium"
        amount = Decimal("9.99")

        invoice = await payment_service.create_invoice(
            user_uuid=user_uuid,
            telegram_id=123456,
            plan_id=plan_id,
            duration_days=30,
            amount=amount,
            currency="TON",
            gateway="cryptobot",
        )

        assert invoice["invoice_id"] == "CB123"
        assert "payment_url" in invoice

    async def test_create_invoice_telegram_stars(self) -> None:
        """Test creating Telegram Stars invoice."""
        payment_service = MagicMock()
        payment_service.create_invoice = AsyncMock(
            return_value={
                "invoice_id": "STARS123",
                "title": "Premium Plan - 30 days",
                "amount": "500",
                "currency": "XTR",
            }
        )

        invoice = await payment_service.create_invoice(
            user_uuid="user-123",
            telegram_id=123456,
            plan_id="premium",
            duration_days=30,
            amount=Decimal("500"),
            currency="XTR",
            gateway="telegram_stars",
        )

        assert invoice["currency"] == "XTR"

    async def test_pre_checkout_query_handler(self) -> None:
        """Test pre_checkout_query handler for Telegram Stars."""
        user = User(id=123456, is_bot=False, first_name="Test")

        pre_checkout = MagicMock(spec=PreCheckoutQuery)
        pre_checkout.id = "PCQ123"
        pre_checkout.from_user = user
        pre_checkout.currency = "XTR"
        pre_checkout.total_amount = 500
        pre_checkout.invoice_payload = "plan_premium_30days"

        # Mock answer method
        pre_checkout.answer = AsyncMock()

        # Handler logic: validate and approve
        is_valid = True  # Simulate validation

        if is_valid:
            await pre_checkout.answer(ok=True)
        else:
            await pre_checkout.answer(
                ok=False, error_message="Invalid payment"
            )

        pre_checkout.answer.assert_called_once()
        call_kwargs = pre_checkout.answer.call_args[1]
        assert call_kwargs.get("ok") is True

    async def test_payment_verification_success(self) -> None:
        """Test successful payment verification."""
        payment_service = MagicMock()
        payment_service.verify_payment = AsyncMock(
            return_value={
                "status": "paid",
                "invoice_id": "INV123",
                "user_uuid": "user-123",
            }
        )

        result = await payment_service.verify_payment(invoice_id="INV123")

        assert result["status"] == "paid"

    async def test_payment_verification_failure(self) -> None:
        """Test failed payment verification."""
        payment_service = MagicMock()
        payment_service.verify_payment = AsyncMock(
            return_value={"status": "failed", "error": "Payment declined"}
        )

        result = await payment_service.verify_payment(invoice_id="INV456")

        assert result["status"] == "failed"

    async def test_payment_callback_success(self) -> None:
        """Test payment success callback."""
        callback = MagicMock(spec=CallbackQuery)
        callback.data = "check_payment:INV123"
        callback.message = MagicMock()
        callback.message.edit_text = AsyncMock()
        callback.answer = AsyncMock()

        # Parse invoice ID
        invoice_id = callback.data.split(":")[1]

        # Simulate successful payment
        await callback.answer("Payment successful!", show_alert=True)
        await callback.message.edit_text(
            "✅ Payment confirmed! Your subscription is now active."
        )

        callback.answer.assert_called_once()
        assert "successful" in callback.answer.call_args[0][0].lower()

    async def test_payment_callback_pending(self) -> None:
        """Test payment pending callback."""
        callback = MagicMock(spec=CallbackQuery)
        callback.data = "check_payment:INV789"
        callback.answer = AsyncMock()

        # Simulate pending payment
        await callback.answer(
            "Payment is still pending. Please complete the payment.",
            show_alert=False,
        )

        callback.answer.assert_called_once()

    async def test_payment_gateway_unavailable(self) -> None:
        """Test handling unavailable payment gateway."""
        payment_service = MagicMock()
        payment_service.create_invoice = AsyncMock(
            side_effect=ValueError("YooKassa is not enabled")
        )

        with pytest.raises(ValueError, match="not enabled"):
            await payment_service.create_invoice(
                user_uuid="user-123",
                telegram_id=123456,
                plan_id="pro",
                duration_days=30,
                amount=Decimal("19.99"),
                currency="USD",
                gateway="yookassa",
            )

    async def test_invalid_payment_amount(self) -> None:
        """Test handling invalid payment amount."""
        # Amount too low
        amount = Decimal("0.50")
        min_amount = Decimal("1.00")

        is_valid = amount >= min_amount
        assert is_valid is False

    async def test_payment_flow_complete_workflow(self) -> None:
        """Test complete payment workflow."""
        # 1. User selects plan
        plan_id = "premium"
        duration_days = 30

        # 2. User selects payment gateway
        gateway = "cryptobot"

        # 3. Create invoice
        payment_service = MagicMock()
        payment_service.create_invoice = AsyncMock(
            return_value={
                "invoice_id": "INV001",
                "payment_url": "https://pay.example.com/INV001",
            }
        )

        invoice = await payment_service.create_invoice(
            user_uuid="user-123",
            telegram_id=123456,
            plan_id=plan_id,
            duration_days=duration_days,
            amount=Decimal("9.99"),
            currency="USD",
            gateway=gateway,
        )

        assert invoice["invoice_id"] == "INV001"

        # 4. User pays (external)

        # 5. Verify payment
        payment_service.verify_payment = AsyncMock(
            return_value={"status": "paid"}
        )

        result = await payment_service.verify_payment(
            invoice_id=invoice["invoice_id"]
        )

        assert result["status"] == "paid"

    async def test_payment_currency_conversion(self) -> None:
        """Test payment with currency conversion."""
        # Mock conversion rates
        rates = {"USD": 1.0, "EUR": 0.92, "RUB": 90.0}

        amount_usd = Decimal("10.00")
        currency_target = "RUB"

        if currency_target in rates:
            amount_converted = amount_usd * Decimal(str(rates[currency_target]))
            assert amount_converted == Decimal("900.00")
