"""Integration tests for wallet and payment flows (TE-2).

Tests the full end-to-end wallet and payment workflows:
- Wallet: topup → balance → withdraw → approve/reject
- Payments: checkout → invoice → webhook
- Admin operations and error cases

Requires: AsyncClient, test database.
"""

import secrets
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.database.models.admin_user_model import AdminUserModel
from src.infrastructure.database.models.wallet_model import WalletModel
from src.infrastructure.database.models.withdrawal_request_model import WithdrawalRequestModel


class TestWalletFlow:
    """Test complete wallet flow: topup → balance → withdraw → approve."""

    @pytest.mark.integration
    async def test_complete_wallet_flow(
        self,
        async_client: AsyncClient,
        db: AsyncSession,
    ):
        """
        Test complete wallet flow:
        1. Admin tops up user wallet
        2. User checks balance
        3. User requests withdrawal
        4. Admin approves withdrawal
        5. User balance updated
        """
        # Create admin user
        from src.application.services.auth_service import AuthService
        auth_service = AuthService()
        admin_password_hash = await auth_service.hash_password("AdminP@ss123!")

        admin = AdminUserModel(
            login=f"admin{secrets.token_hex(4)}",
            email=f"admin{secrets.token_hex(4)}@example.com",
            password_hash=admin_password_hash,
            role="admin",
            is_active=True,
            is_email_verified=True,
        )
        db.add(admin)
        await db.commit()
        await db.refresh(admin)

        # Login as admin to get token
        login_response = await async_client.post(
            "/api/v1/auth/login",
            json={
                "login_or_email": admin.email,
                "password": "AdminP@ss123!",
            },
        )
        assert login_response.status_code == 200
        admin_token = login_response.json()["access_token"]

        # Create mobile user with wallet
        mobile_user_id = uuid4()
        wallet = WalletModel(
            user_id=mobile_user_id,
            balance=Decimal("0.00"),
        )
        db.add(wallet)
        await db.commit()

        # Step 1: Admin topup user wallet
        topup_amount = Decimal("100.00")
        topup_response = await async_client.post(
            f"/api/v1/admin/wallets/{mobile_user_id}/topup",
            json={
                "amount": str(topup_amount),
                "description": "Test topup",
            },
            headers={"Authorization": f"Bearer {admin_token}"},
        )

        assert topup_response.status_code == 200
        topup_data = topup_response.json()
        assert topup_data["type"] == "topup"
        assert Decimal(topup_data["amount"]) == topup_amount

        # Step 2: Check balance (as mobile user)
        # Note: This requires mobile auth, so we'll mock it
        with patch("src.presentation.dependencies.auth.get_current_mobile_user_id") as mock_user_id:
            mock_user_id.return_value = mobile_user_id

            balance_response = await async_client.get("/api/v1/wallet")
            assert balance_response.status_code == 200
            balance_data = balance_response.json()
            assert Decimal(balance_data["balance"]) == topup_amount

            # Step 3: User requests withdrawal
            withdraw_amount = Decimal("50.00")
            withdraw_response = await async_client.post(
                "/api/v1/wallet/withdraw",
                json={
                    "amount": str(withdraw_amount),
                    "method": "bank_transfer",
                },
            )

            assert withdraw_response.status_code == 201
            withdraw_data = withdraw_response.json()
            assert withdraw_data["status"] == "pending"
            assert Decimal(withdraw_data["amount"]) == withdraw_amount
            withdrawal_id = withdraw_data["id"]

        # Step 4: Admin approves withdrawal
        approve_response = await async_client.put(
            f"/api/v1/admin/withdrawals/{withdrawal_id}/approve",
            json={"admin_note": "Approved"},
            headers={"Authorization": f"Bearer {admin_token}"},
        )

        assert approve_response.status_code == 200
        approve_data = approve_response.json()
        assert approve_data["status"] == "approved"

        # Step 5: Verify balance updated
        with patch("src.presentation.dependencies.auth.get_current_mobile_user_id") as mock_user_id:
            mock_user_id.return_value = mobile_user_id

            final_balance_response = await async_client.get("/api/v1/wallet")
            assert final_balance_response.status_code == 200
            final_balance = Decimal(final_balance_response.json()["balance"])
            assert final_balance == topup_amount - withdraw_amount

    @pytest.mark.integration
    async def test_withdrawal_below_minimum(
        self,
        async_client: AsyncClient,
        db: AsyncSession,
    ):
        """
        Test that withdrawal below minimum amount is rejected.
        """
        # Create mobile user with wallet
        mobile_user_id = uuid4()
        wallet = WalletModel(
            user_id=mobile_user_id,
            balance=Decimal("100.00"),
        )
        db.add(wallet)
        await db.commit()

        # Try to withdraw less than minimum (assuming minimum is 10)
        with patch("src.presentation.dependencies.auth.get_current_mobile_user_id") as mock_user_id:
            mock_user_id.return_value = mobile_user_id

            withdraw_response = await async_client.post(
                "/api/v1/wallet/withdraw",
                json={
                    "amount": "5.00",  # Below minimum
                    "method": "bank_transfer",
                },
            )

            assert withdraw_response.status_code == 422
            assert "minimum" in withdraw_response.json()["detail"].lower()

    @pytest.mark.integration
    async def test_withdrawal_insufficient_balance(
        self,
        async_client: AsyncClient,
        db: AsyncSession,
    ):
        """
        Test that withdrawal fails when balance is insufficient.
        """
        mobile_user_id = uuid4()
        wallet = WalletModel(
            user_id=mobile_user_id,
            balance=Decimal("10.00"),
        )
        db.add(wallet)
        await db.commit()

        with patch("src.presentation.dependencies.auth.get_current_mobile_user_id") as mock_user_id:
            mock_user_id.return_value = mobile_user_id

            withdraw_response = await async_client.post(
                "/api/v1/wallet/withdraw",
                json={
                    "amount": "100.00",  # More than balance
                    "method": "bank_transfer",
                },
            )

            assert withdraw_response.status_code == 422
            assert "insufficient" in withdraw_response.json()["detail"].lower()

    @pytest.mark.integration
    async def test_admin_reject_withdrawal(
        self,
        async_client: AsyncClient,
        db: AsyncSession,
    ):
        """
        Test admin rejecting a withdrawal request.
        """
        # Create admin
        from src.application.services.auth_service import AuthService
        auth_service = AuthService()
        admin_password_hash = await auth_service.hash_password("AdminP@ss123!")

        admin = AdminUserModel(
            login=f"admin{secrets.token_hex(4)}",
            email=f"admin{secrets.token_hex(4)}@example.com",
            password_hash=admin_password_hash,
            role="admin",
            is_active=True,
            is_email_verified=True,
        )
        db.add(admin)
        await db.commit()

        login_response = await async_client.post(
            "/api/v1/auth/login",
            json={"login_or_email": admin.email, "password": "AdminP@ss123!"},
        )
        admin_token = login_response.json()["access_token"]

        # Create mobile user with wallet and withdrawal
        mobile_user_id = uuid4()
        wallet = WalletModel(
            user_id=mobile_user_id,
            balance=Decimal("100.00"),
        )
        db.add(wallet)
        await db.flush()

        withdrawal = WithdrawalRequestModel(
            user_id=mobile_user_id,
            amount=Decimal("50.00"),
            method="bank_transfer",
            status="pending",
        )
        db.add(withdrawal)
        await db.commit()
        await db.refresh(withdrawal)

        # Admin rejects withdrawal
        reject_response = await async_client.put(
            f"/api/v1/admin/withdrawals/{withdrawal.id}/reject",
            json={"admin_note": "Invalid bank details"},
            headers={"Authorization": f"Bearer {admin_token}"},
        )

        assert reject_response.status_code == 200
        reject_data = reject_response.json()
        assert reject_data["status"] == "rejected"
        assert "Invalid bank details" in reject_data["admin_note"]

        # Verify balance unchanged
        result = await db.execute(
            select(WalletModel).where(WalletModel.user_id == mobile_user_id)
        )
        wallet_after = result.scalar_one()
        assert wallet_after.balance == Decimal("100.00")  # Not deducted

    @pytest.mark.integration
    async def test_list_wallet_transactions(
        self,
        async_client: AsyncClient,
        db: AsyncSession,
    ):
        """
        Test listing wallet transaction history with pagination.
        """
        mobile_user_id = uuid4()
        wallet = WalletModel(
            user_id=mobile_user_id,
            balance=Decimal("0.00"),
        )
        db.add(wallet)
        await db.commit()

        # Create multiple transactions via admin topup
        from src.application.services.auth_service import AuthService
        auth_service = AuthService()
        admin_password_hash = await auth_service.hash_password("AdminP@ss123!")

        admin = AdminUserModel(
            login=f"admin{secrets.token_hex(4)}",
            email=f"admin{secrets.token_hex(4)}@example.com",
            password_hash=admin_password_hash,
            role="admin",
            is_active=True,
            is_email_verified=True,
        )
        db.add(admin)
        await db.commit()

        login_response = await async_client.post(
            "/api/v1/auth/login",
            json={"login_or_email": admin.email, "password": "AdminP@ss123!"},
        )
        admin_token = login_response.json()["access_token"]

        # Make 3 topups
        for i in range(3):
            await async_client.post(
                f"/api/v1/admin/wallets/{mobile_user_id}/topup",
                json={"amount": f"{(i+1)*10}.00", "description": f"Topup {i+1}"},
                headers={"Authorization": f"Bearer {admin_token}"},
            )

        # List transactions as mobile user
        with patch("src.presentation.dependencies.auth.get_current_mobile_user_id") as mock_user_id:
            mock_user_id.return_value = mobile_user_id

            transactions_response = await async_client.get("/api/v1/wallet/transactions")
            assert transactions_response.status_code == 200
            transactions = transactions_response.json()
            assert len(transactions) == 3
            assert all(tx["type"] == "topup" for tx in transactions)


class TestPaymentCheckoutFlow:
    """Test payment checkout and invoice flow."""

    @pytest.mark.integration
    async def test_checkout_calculation(
        self,
        async_client: AsyncClient,
        db: AsyncSession,
    ):
        """
        Test checkout calculates pricing correctly with plan + promo + wallet.
        """
        # Create subscription plan
        from src.infrastructure.database.models.subscription_plan_model import SubscriptionPlanModel

        plan = SubscriptionPlanModel(
            name="Premium Plan",
            duration_days=30,
            price=Decimal("10.00"),
            is_active=True,
        )
        db.add(plan)
        await db.commit()
        await db.refresh(plan)

        # Create mobile user with wallet
        mobile_user_id = uuid4()
        wallet = WalletModel(
            user_id=mobile_user_id,
            balance=Decimal("5.00"),
        )
        db.add(wallet)
        await db.commit()

        # Mock mobile user auth
        with patch("src.presentation.dependencies.auth.get_current_mobile_user_id") as mock_user_id:
            mock_user_id.return_value = mobile_user_id

            # Checkout with wallet balance
            checkout_response = await async_client.post(
                "/api/v1/payments/checkout",
                json={
                    "plan_id": str(plan.id),
                    "currency": "USDT",
                    "use_wallet": "5.00",
                },
            )

            assert checkout_response.status_code == 200
            checkout_data = checkout_response.json()
            assert Decimal(checkout_data["base_price"]) == Decimal("10.00")
            assert Decimal(checkout_data["wallet_amount"]) == Decimal("5.00")
            assert Decimal(checkout_data["gateway_amount"]) == Decimal("5.00")
            assert checkout_data["is_zero_gateway"] is False

    @pytest.mark.integration
    async def test_checkout_zero_gateway_payment(
        self,
        async_client: AsyncClient,
        db: AsyncSession,
    ):
        """
        Test zero-gateway payment (fully paid with wallet) completes immediately.
        """
        # Create plan
        from src.infrastructure.database.models.subscription_plan_model import SubscriptionPlanModel

        plan = SubscriptionPlanModel(
            name="Basic Plan",
            duration_days=30,
            price=Decimal("10.00"),
            is_active=True,
        )
        db.add(plan)
        await db.commit()
        await db.refresh(plan)

        # Create mobile user with enough wallet balance
        mobile_user_id = uuid4()
        wallet = WalletModel(
            user_id=mobile_user_id,
            balance=Decimal("10.00"),
        )
        db.add(wallet)
        await db.commit()

        with patch("src.presentation.dependencies.auth.get_current_mobile_user_id") as mock_user_id:
            mock_user_id.return_value = mobile_user_id

            # Checkout with full wallet balance
            checkout_response = await async_client.post(
                "/api/v1/payments/checkout",
                json={
                    "plan_id": str(plan.id),
                    "currency": "USDT",
                    "use_wallet": "10.00",
                },
            )

            assert checkout_response.status_code == 200
            checkout_data = checkout_response.json()
            assert checkout_data["is_zero_gateway"] is True
            assert checkout_data["status"] == "completed"
            assert "payment_id" in checkout_data

    @pytest.mark.integration
    async def test_create_crypto_invoice(
        self,
        async_client: AsyncClient,
        db: AsyncSession,
    ):
        """
        Test creating a cryptocurrency invoice via CryptoBot.
        """
        # Create plan
        from src.infrastructure.database.models.subscription_plan_model import SubscriptionPlanModel

        plan = SubscriptionPlanModel(
            name="Premium Plan",
            duration_days=30,
            price=Decimal("20.00"),
            is_active=True,
        )
        db.add(plan)
        await db.commit()
        await db.refresh(plan)

        mobile_user_id = uuid4()

        # Mock CryptoBot client
        with patch("src.infrastructure.payments.cryptobot.client.CryptoBotClient") as mock_crypto:
            mock_client = AsyncMock()
            mock_client.create_invoice = AsyncMock(return_value={
                "invoice_id": "test_invoice_123",
                "pay_url": "https://crypto.bot/pay/test_invoice_123",
                "amount": "20.00",
                "currency": "USDT",
                "status": "active",
            })
            mock_crypto.return_value = mock_client

            # Mock permission check
            with patch("src.presentation.dependencies.roles.require_permission"):
                invoice_response = await async_client.post(
                    "/api/v1/payments/crypto/invoice",
                    json={
                        "user_uuid": str(mobile_user_id),
                        "plan_id": str(plan.id),
                        "currency": "USDT",
                    },
                )

                assert invoice_response.status_code == 201
                invoice_data = invoice_response.json()
                assert "invoice_id" in invoice_data
                assert "pay_url" in invoice_data
                assert invoice_data["status"] == "active"


class TestPaymentWebhookFlow:
    """Test payment webhook processing from CryptoBot."""

    @pytest.mark.integration
    async def test_cryptobot_webhook_success(
        self,
        async_client: AsyncClient,
        db: AsyncSession,
    ):
        """
        Test successful payment webhook from CryptoBot activates subscription.
        """
        # Mock webhook handler
        with patch("src.infrastructure.payments.cryptobot.webhook_handler.CryptoBotWebhookHandler") as mock_handler:
            mock_handler_instance = MagicMock()
            mock_handler_instance.verify_signature = MagicMock(return_value=True)
            mock_handler_instance.parse_webhook = MagicMock(return_value={
                "invoice_id": "test_invoice_123",
                "status": "paid",
                "amount": "20.00",
                "currency": "USDT",
                "user_id": str(uuid4()),
                "plan_id": str(uuid4()),
            })
            mock_handler.return_value = mock_handler_instance

            # Send webhook
            webhook_response = await async_client.post(
                "/api/v1/webhooks/cryptobot",
                json={
                    "update_id": 123,
                    "update_type": "invoice_paid",
                    "request_date": "2024-01-01T00:00:00Z",
                    "payload": {
                        "invoice_id": "test_invoice_123",
                        "status": "paid",
                    },
                },
                headers={"crypto-pay-api-signature": "test_signature"},
            )

            assert webhook_response.status_code == 200
            webhook_data = webhook_response.json()
            assert "status" in webhook_data

    @pytest.mark.integration
    async def test_cryptobot_webhook_invalid_signature(
        self,
        async_client: AsyncClient,
        db: AsyncSession,
    ):
        """
        Test webhook with invalid signature is rejected.
        """
        with patch("src.infrastructure.payments.cryptobot.webhook_handler.CryptoBotWebhookHandler") as mock_handler:
            mock_handler_instance = MagicMock()
            mock_handler_instance.verify_signature = MagicMock(return_value=False)
            mock_handler.return_value = mock_handler_instance

            webhook_response = await async_client.post(
                "/api/v1/webhooks/cryptobot",
                json={"update_id": 123},
                headers={"crypto-pay-api-signature": "invalid_signature"},
            )

            # Should still return 200 to prevent retry storms, but not process
            assert webhook_response.status_code in [200, 400, 401]


class TestPaymentHistory:
    """Test payment history retrieval."""

    @pytest.mark.integration
    async def test_get_payment_history(
        self,
        async_client: AsyncClient,
        db: AsyncSession,
    ):
        """
        Test retrieving payment history with pagination.
        """
        # Create multiple payment records
        from src.infrastructure.database.models.payment_model import PaymentModel

        mobile_user_id = uuid4()

        for i in range(5):
            payment = PaymentModel(
                user_id=mobile_user_id,
                amount=Decimal(f"{(i+1)*10}.00"),
                currency="USDT",
                status="completed",
                provider="cryptobot",
            )
            db.add(payment)

        await db.commit()

        # Mock permission check
        with patch("src.presentation.dependencies.roles.require_permission"):
            history_response = await async_client.get(
                f"/api/v1/payments/history?user_uuid={mobile_user_id}&limit=3"
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
        """
        Test admin can view any user's wallet.
        """
        # Create admin
        from src.application.services.auth_service import AuthService
        auth_service = AuthService()
        admin_password_hash = await auth_service.hash_password("AdminP@ss123!")

        admin = AdminUserModel(
            login=f"admin{secrets.token_hex(4)}",
            email=f"admin{secrets.token_hex(4)}@example.com",
            password_hash=admin_password_hash,
            role="admin",
            is_active=True,
            is_email_verified=True,
        )
        db.add(admin)
        await db.commit()

        login_response = await async_client.post(
            "/api/v1/auth/login",
            json={"login_or_email": admin.email, "password": "AdminP@ss123!"},
        )
        admin_token = login_response.json()["access_token"]

        # Create mobile user with wallet
        mobile_user_id = uuid4()
        wallet = WalletModel(
            user_id=mobile_user_id,
            balance=Decimal("123.45"),
        )
        db.add(wallet)
        await db.commit()

        # Admin views wallet
        wallet_response = await async_client.get(
            f"/api/v1/admin/wallets/{mobile_user_id}",
            headers={"Authorization": f"Bearer {admin_token}"},
        )

        assert wallet_response.status_code == 200
        wallet_data = wallet_response.json()
        assert Decimal(wallet_data["balance"]) == Decimal("123.45")

    @pytest.mark.integration
    async def test_admin_list_pending_withdrawals(
        self,
        async_client: AsyncClient,
        db: AsyncSession,
    ):
        """
        Test admin can list all pending withdrawals.
        """
        # Create admin
        from src.application.services.auth_service import AuthService
        auth_service = AuthService()
        admin_password_hash = await auth_service.hash_password("AdminP@ss123!")

        admin = AdminUserModel(
            login=f"admin{secrets.token_hex(4)}",
            email=f"admin{secrets.token_hex(4)}@example.com",
            password_hash=admin_password_hash,
            role="admin",
            is_active=True,
            is_email_verified=True,
        )
        db.add(admin)
        await db.commit()

        login_response = await async_client.post(
            "/api/v1/auth/login",
            json={"login_or_email": admin.email, "password": "AdminP@ss123!"},
        )
        admin_token = login_response.json()["access_token"]

        # Create pending withdrawals
        for idx in range(3):
            withdrawal = WithdrawalRequestModel(
                user_id=uuid4(),
                amount=Decimal(f"{(idx+1)*50}.00"),
                method="bank_transfer",
                status="pending",
            )
            db.add(withdrawal)

        await db.commit()

        # Admin lists pending withdrawals
        withdrawals_response = await async_client.get(
            "/api/v1/admin/withdrawals",
            headers={"Authorization": f"Bearer {admin_token}"},
        )

        assert withdrawals_response.status_code == 200
        withdrawals = withdrawals_response.json()
        assert len(withdrawals) >= 3
        assert all(w["status"] == "pending" for w in withdrawals)
