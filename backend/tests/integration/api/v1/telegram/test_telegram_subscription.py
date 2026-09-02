from datetime import UTC, datetime
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.database.models.mobile_user_model import MobileUserModel
from src.infrastructure.database.models.remnawave_upgrade_model import RemnawaveIdentityReconciliationModel
from src.infrastructure.remnawave.contracts import (
    RemnawaveCreatedSubscriptionResponse,
    RemnawaveUserResponse,
)
from tests.integration.conftest import get_default_test_realm


class TestTelegramSubscriptionFlow:
    @pytest.mark.integration
    async def test_create_subscription_uses_validated_upstream_response(
        self,
        async_client: AsyncClient,
        auth_headers: dict[str, str],
        db: AsyncSession,
    ):
        expires_at = datetime(2026, 5, 1, 12, 0, tzinfo=UTC)
        now = datetime(2026, 4, 1, 12, 0, tzinfo=UTC)
        suffix = uuid4().hex
        telegram_id = int(suffix[:12], 16)
        remnawave_user_id = int(suffix[12:24], 16)
        remnawave_uuid = uuid4()
        customer_realm = await get_default_test_realm(db, "customer")
        mobile_user = MobileUserModel(
            auth_realm_id=customer_realm.id,
            email=f"telegram-subscription-{suffix}@example.com",
            password_hash="not-used-by-telegram-subscription-test",
            username=f"telegram-sub-{suffix[:12]}",
            telegram_id=telegram_id,
            is_active=True,
            status="active",
            remnawave_user_id=remnawave_user_id,
            remnawave_uuid=str(remnawave_uuid),
        )
        db.add(mobile_user)
        await db.flush()
        db.add(
            RemnawaveIdentityReconciliationModel(
                subject_type="mobile_user",
                subject_id=mobile_user.id,
                legacy_uuid=str(remnawave_uuid),
                numeric_user_id=remnawave_user_id,
                reconciliation_state="mapped",
                evidence={"source": "telegram-subscription-integration-test"},
            )
        )
        await db.commit()

        upstream_user = RemnawaveUserResponse.model_validate(
            {
                "id": remnawave_user_id,
                "uuid": str(remnawave_uuid),
                "username": mobile_user.username,
                "status": "active",
                "createdAt": now,
                "updatedAt": now,
                "telegramId": telegram_id,
            }
        )
        upstream_subscription = RemnawaveCreatedSubscriptionResponse(
            uuid="sub-uuid-1",
            expiresAt=expires_at,
        )

        try:
            with patch(
                "src.infrastructure.remnawave.client.RemnawaveClient.get_validated",
                AsyncMock(return_value=upstream_user),
            ) as mock_get_validated:
                with patch(
                    "src.infrastructure.remnawave.client.RemnawaveClient.post_validated",
                    AsyncMock(return_value=upstream_subscription),
                ) as mock_post_validated:
                    response = await async_client.post(
                        f"/api/v1/telegram/user/{telegram_id}/subscription",
                        headers=auth_headers,
                        json={"plan_name": "Premium Monthly", "duration_days": 30},
                    )

            assert response.status_code == 201
            assert response.json() == {
                "status": "success",
                "subscription_id": "sub-uuid-1",
                "expires_at": "2026-05-01T12:00:00Z",
            }
            mock_get_validated.assert_awaited_once_with(
                f"/api/users/{remnawave_user_id}",
                RemnawaveUserResponse,
            )
            mock_post_validated.assert_awaited_once_with(
                "/api/subscriptions",
                RemnawaveCreatedSubscriptionResponse,
                json={
                    "userId": remnawave_user_id,
                    "planName": "Premium Monthly",
                    "durationDays": 30,
                },
            )
        finally:
            await db.execute(
                delete(RemnawaveIdentityReconciliationModel).where(
                    RemnawaveIdentityReconciliationModel.subject_id == mobile_user.id
                )
            )
            await db.execute(delete(MobileUserModel).where(MobileUserModel.id == mobile_user.id))
            await db.commit()
