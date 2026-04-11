"""Integration tests for wallet and payment flows (TE-2).

These scenarios exercise the current mobile-user wallet and payments contract:
- wallet topup, balance, withdrawal, approve/reject
- checkout calculation and zero-gateway payments
- crypto invoice creation
- payment history and admin wallet views
"""

import secrets
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.services.auth_service import AuthService
from src.infrastructure.database.models.admin_user_model import AdminUserModel
from src.infrastructure.database.models.mobile_user_model import MobileUserModel
from src.infrastructure.database.models.payment_model import PaymentModel
from src.infrastructure.database.models.subscription_plan_model import SubscriptionPlanModel
from src.infrastructure.database.models.wallet_model import WalletModel
from src.infrastructure.database.models.withdrawal_request_model import WithdrawalRequestModel
from src.main import app
from src.presentation.dependencies.auth import get_current_active_user, get_current_mobile_user_id
from src.presentation.dependencies.services import get_crypto_client


@pytest.fixture(autouse=True)
def _clear_dependency_overrides():
    yield
    app.dependency_overrides.pop(get_current_active_user, None)
    app.dependency_overrides.pop(get_current_mobile_user_id, None)
    app.dependency_overrides.pop(get_crypto_client, None)


def _override_admin_user(user: AdminUserModel) -> None:
    app.dependency_overrides[get_current_active_user] = lambda: user


def _override_mobile_user(user_id) -> None:
    app.dependency_overrides[get_current_mobile_user_id] = lambda: user_id


async def _create_admin_user(db: AsyncSession, *, role: str = "admin") -> AdminUserModel:
    auth_service = AuthService()
    user = AdminUserModel(
        login=f"admin{secrets.token_hex(4)}",
        email=f"admin{secrets.token_hex(4)}@example.com",
        password_hash=await auth_service.hash_password("AdminP@ss123!"),
        role=role,
        is_active=True,
        is_email_verified=True,
        language="en-EN",
        timezone="UTC",
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


async def _create_mobile_user(
    db: AsyncSession,
    *,
    balance: str = "0.00",
) -> tuple[MobileUserModel, WalletModel]:
    auth_service = AuthService()
    user = MobileUserModel(
        email=f"mobile{secrets.token_hex(4)}@example.com",
        password_hash=await auth_service.hash_password("MobileP@ss123!"),
        username=f"mobile{secrets.token_hex(4)}",
        is_active=True,
        status="active",
    )
    db.add(user)
    await db.flush()

    wallet = WalletModel(
        user_id=user.id,
        balance=Decimal(balance),
        currency="USD",
        frozen=Decimal("0.00"),
    )
    db.add(wallet)
    await db.commit()
    await db.refresh(user)
    await db.refresh(wallet)
    return user, wallet


async def _create_plan(
    db: AsyncSession,
    *,
    name: str,
    price_usd: str,
    duration_days: int = 30,
) -> SubscriptionPlanModel:
    plan = SubscriptionPlanModel(
        name=f"{name}-{secrets.token_hex(4)}",
        tier="pro",
        duration_days=duration_days,
        traffic_limit_bytes=None,
        device_limit=3,
        price_usd=Decimal(price_usd),
        price_rub=None,
        features={},
        is_active=True,
        sort_order=0,
    )
    db.add(plan)
    await db.commit()
    await db.refresh(plan)
    return plan


class TestWalletFlow:
    """Test wallet flows for the current mobile-user domain."""

    @pytest.mark.integration
    async def test_complete_wallet_flow(
        self,
        async_client: AsyncClient,
        db: AsyncSession,
    ):
        admin = await _create_admin_user(db)
        mobile_user, _wallet = await _create_mobile_user(db, balance="0.00")

        _override_admin_user(admin)
        topup_response = await async_client.post(
            f"/api/v1/admin/wallets/{mobile_user.id}/topup",
            json={"amount": "100.00", "description": "Test topup"},
        )

        assert topup_response.status_code == 200
        topup_data = topup_response.json()
        assert topup_data["type"] == "credit"
        assert Decimal(str(topup_data["amount"])) == Decimal("100.00")
        assert topup_data["reason"] == "admin_topup"

        _override_mobile_user(mobile_user.id)
        balance_response = await async_client.get("/api/v1/wallet")
        assert balance_response.status_code == 200
        assert Decimal(str(balance_response.json()["balance"])) == Decimal("100.00")

        withdraw_response = await async_client.post(
            "/api/v1/wallet/withdraw",
            json={"amount": "50.00", "method": "cryptobot"},
        )
        assert withdraw_response.status_code == 201
        withdrawal_id = withdraw_response.json()["id"]
        assert withdraw_response.json()["status"] == "pending"

        _override_admin_user(admin)
        approve_response = await async_client.put(
            f"/api/v1/admin/withdrawals/{withdrawal_id}/approve",
            json={"admin_note": "Approved"},
        )

        assert approve_response.status_code == 200
        assert approve_response.json()["status"] == "completed"

        _override_mobile_user(mobile_user.id)
        final_balance_response = await async_client.get("/api/v1/wallet")
        assert final_balance_response.status_code == 200
        assert Decimal(str(final_balance_response.json()["balance"])) == Decimal("50.00")
        assert Decimal(str(final_balance_response.json()["frozen"])) == Decimal("0.00")

    @pytest.mark.integration
    async def test_withdrawal_below_minimum(
        self,
        async_client: AsyncClient,
        db: AsyncSession,
    ):
        mobile_user, _wallet = await _create_mobile_user(db, balance="100.00")
        _override_mobile_user(mobile_user.id)

        withdraw_response = await async_client.post(
            "/api/v1/wallet/withdraw",
            json={"amount": "4.99", "method": "cryptobot"},
        )

        assert withdraw_response.status_code == 422
        assert "minimum" in withdraw_response.json()["detail"].lower()

    @pytest.mark.integration
    async def test_withdrawal_insufficient_balance(
        self,
        async_client: AsyncClient,
        db: AsyncSession,
    ):
        mobile_user, _wallet = await _create_mobile_user(db, balance="10.00")
        _override_mobile_user(mobile_user.id)

        withdraw_response = await async_client.post(
            "/api/v1/wallet/withdraw",
            json={"amount": "100.00", "method": "cryptobot"},
        )

        assert withdraw_response.status_code == 422
        assert "insufficient" in withdraw_response.json()["detail"].lower()

    @pytest.mark.integration
    async def test_admin_reject_withdrawal(
        self,
        async_client: AsyncClient,
        db: AsyncSession,
    ):
        admin = await _create_admin_user(db)
        mobile_user, _wallet = await _create_mobile_user(db, balance="100.00")

        _override_mobile_user(mobile_user.id)
        withdraw_response = await async_client.post(
            "/api/v1/wallet/withdraw",
            json={"amount": "50.00", "method": "cryptobot"},
        )
        assert withdraw_response.status_code == 201
        withdrawal_id = withdraw_response.json()["id"]

        _override_admin_user(admin)
        reject_response = await async_client.put(
            f"/api/v1/admin/withdrawals/{withdrawal_id}/reject",
            json={"admin_note": "Invalid bank details"},
        )

        assert reject_response.status_code == 200
        reject_data = reject_response.json()
        assert reject_data["status"] == "failed"

        result = await db.execute(select(WalletModel).where(WalletModel.user_id == mobile_user.id))
        wallet_after = result.scalar_one()
        assert wallet_after.balance == Decimal("100.00")
        assert wallet_after.frozen == Decimal("0.00")

    @pytest.mark.integration
    async def test_list_wallet_transactions(
        self,
        async_client: AsyncClient,
        db: AsyncSession,
    ):
        admin = await _create_admin_user(db)
        mobile_user, _wallet = await _create_mobile_user(db, balance="0.00")

        _override_admin_user(admin)
        for idx in range(3):
            response = await async_client.post(
                f"/api/v1/admin/wallets/{mobile_user.id}/topup",
                json={"amount": f"{(idx + 1) * 10}.00", "description": f"Topup {idx + 1}"},
            )
            assert response.status_code == 200

        _override_mobile_user(mobile_user.id)
        transactions_response = await async_client.get("/api/v1/wallet/transactions")

        assert transactions_response.status_code == 200
        transactions = transactions_response.json()
        assert len(transactions) == 3
        assert all(tx["type"] == "credit" for tx in transactions)
        assert all(tx["reason"] == "admin_topup" for tx in transactions)


class TestPaymentCheckoutFlow:
    """Test checkout and invoice flows with current plan/payment models."""

    @pytest.mark.integration
    async def test_checkout_calculation(
        self,
        async_client: AsyncClient,
        db: AsyncSession,
    ):
        plan = await _create_plan(db, name="Premium Plan", price_usd="10.00")
        mobile_user, _wallet = await _create_mobile_user(db, balance="5.00")

        _override_mobile_user(mobile_user.id)
        checkout_response = await async_client.post(
            "/api/v1/payments/checkout",
            json={"plan_id": str(plan.id), "currency": "USD", "use_wallet": 5.00},
        )

        assert checkout_response.status_code == 200
        checkout_data = checkout_response.json()
        assert Decimal(str(checkout_data["base_price"])) == Decimal("10.00")
        assert Decimal(str(checkout_data["wallet_amount"])) == Decimal("5.00")
        assert Decimal(str(checkout_data["gateway_amount"])) == Decimal("5.00")
        assert checkout_data["is_zero_gateway"] is False

    @pytest.mark.integration
    async def test_checkout_zero_gateway_payment(
        self,
        async_client: AsyncClient,
        db: AsyncSession,
    ):
        plan = await _create_plan(db, name="Basic Plan", price_usd="10.00")
        mobile_user, _wallet = await _create_mobile_user(db, balance="10.00")

        _override_mobile_user(mobile_user.id)
        checkout_response = await async_client.post(
            "/api/v1/payments/checkout",
            json={"plan_id": str(plan.id), "currency": "USD", "use_wallet": 10.00},
        )

        assert checkout_response.status_code == 200
        checkout_data = checkout_response.json()
        assert checkout_data["is_zero_gateway"] is True
        assert checkout_data["status"] == "completed"
        assert checkout_data["payment_id"] is not None

    @pytest.mark.integration
    async def test_create_crypto_invoice(
        self,
        async_client: AsyncClient,
        db: AsyncSession,
    ):
        admin = await _create_admin_user(db)
        plan = await _create_plan(db, name="Invoice Plan", price_usd="20.00")
        mobile_user, _wallet = await _create_mobile_user(db, balance="0.00")

        mock_crypto = AsyncMock()
        mock_crypto.create_invoice.return_value = {
            "invoice_id": "test_invoice_123",
            "pay_url": "https://crypto.bot/pay/test_invoice_123",
            "amount": "20.00",
            "currency": "USD",
            "status": "active",
        }

        _override_admin_user(admin)
        app.dependency_overrides[get_crypto_client] = lambda: mock_crypto
        invoice_response = await async_client.post(
            "/api/v1/payments/crypto/invoice",
            json={"user_uuid": str(mobile_user.id), "plan_id": str(plan.id), "currency": "USD"},
        )

        assert invoice_response.status_code == 201
        invoice_data = invoice_response.json()
        assert invoice_data["invoice_id"] == "test_invoice_123"
        assert invoice_data["payment_url"] == "https://crypto.bot/pay/test_invoice_123"
        assert invoice_data["status"] == "active"


class TestPaymentWebhookFlow:
    """Test payment webhook processing from CryptoBot."""

    @pytest.mark.integration
    async def test_cryptobot_webhook_success(
        self,
        async_client: AsyncClient,
        db: AsyncSession,
    ):
        with patch("src.infrastructure.payments.cryptobot.webhook_handler.CryptoBotWebhookHandler") as mock_handler:
            mock_handler_instance = MagicMock()
            mock_handler_instance.verify_signature = MagicMock(return_value=True)
            mock_handler_instance.parse_webhook = MagicMock(
                return_value={
                    "invoice_id": "test_invoice_123",
                    "status": "paid",
                    "amount": "20.00",
                    "currency": "USD",
                    "user_id": str(secrets.token_hex(16)),
                    "plan_id": str(secrets.token_hex(16)),
                }
            )
            mock_handler.return_value = mock_handler_instance

            webhook_response = await async_client.post(
                "/api/v1/webhooks/cryptobot",
                json={
                    "update_id": 123,
                    "update_type": "invoice_paid",
                    "request_date": "2024-01-01T00:00:00Z",
                    "payload": {"invoice_id": "test_invoice_123", "status": "paid"},
                },
                headers={"crypto-pay-api-signature": "test_signature"},
            )

        assert webhook_response.status_code == 200
        assert "status" in webhook_response.json()

    @pytest.mark.integration
    async def test_cryptobot_webhook_invalid_signature(
        self,
        async_client: AsyncClient,
        db: AsyncSession,
    ):
        with patch("src.infrastructure.payments.cryptobot.webhook_handler.CryptoBotWebhookHandler") as mock_handler:
            mock_handler_instance = MagicMock()
            mock_handler_instance.verify_signature = MagicMock(return_value=False)
            mock_handler.return_value = mock_handler_instance

            webhook_response = await async_client.post(
                "/api/v1/webhooks/cryptobot",
                json={"update_id": 123},
                headers={"crypto-pay-api-signature": "invalid_signature"},
            )

        assert webhook_response.status_code in [200, 400, 401]


class TestPaymentHistory:
    """Test payment history retrieval."""

    @pytest.mark.integration
    async def test_get_payment_history(
        self,
        async_client: AsyncClient,
        db: AsyncSession,
    ):
        admin = await _create_admin_user(db)
        mobile_user, _wallet = await _create_mobile_user(db, balance="0.00")

        for idx in range(5):
            payment = PaymentModel(
                user_uuid=mobile_user.id,
                amount=Decimal(f"{(idx + 1) * 10}.00"),
                currency="USD",
                status="completed",
                provider="cryptobot",
                subscription_days=30,
                external_id=f"pay_{idx}",
            )
            db.add(payment)

        await db.commit()

        _override_admin_user(admin)
        history_response = await async_client.get(
            f"/api/v1/payments/history?user_uuid={mobile_user.id}&limit=3"
        )

        assert history_response.status_code == 200
        history_data = history_response.json()
        assert "payments" in history_data
        assert len(history_data["payments"]) <= 3


class TestAdminWalletOperations:
    """Test admin-only wallet operations."""

    @pytest.mark.integration
    async def test_admin_view_user_wallet(
        self,
        async_client: AsyncClient,
        db: AsyncSession,
    ):
        admin = await _create_admin_user(db)
        mobile_user, _wallet = await _create_mobile_user(db, balance="123.45")

        _override_admin_user(admin)
        wallet_response = await async_client.get(f"/api/v1/admin/wallets/{mobile_user.id}")

        assert wallet_response.status_code == 200
        assert Decimal(str(wallet_response.json()["balance"])) == Decimal("123.45")

    @pytest.mark.integration
    async def test_admin_list_pending_withdrawals(
        self,
        async_client: AsyncClient,
        db: AsyncSession,
    ):
        admin = await _create_admin_user(db)

        for idx in range(3):
            mobile_user, wallet = await _create_mobile_user(db, balance=f"{(idx + 1) * 100}.00")
            withdrawal = WithdrawalRequestModel(
                user_id=mobile_user.id,
                wallet_id=wallet.id,
                amount=Decimal(f"{(idx + 1) * 50}.00"),
                currency="USD",
                method="cryptobot",
                status="pending",
            )
            db.add(withdrawal)

        await db.commit()

        _override_admin_user(admin)
        withdrawals_response = await async_client.get("/api/v1/admin/withdrawals")

        assert withdrawals_response.status_code == 200
        withdrawals = withdrawals_response.json()
        assert len(withdrawals) >= 3
        assert all(item["status"] == "pending" for item in withdrawals)
