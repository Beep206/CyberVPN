from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
from httpx import AsyncClient


class TestTelegramSubscriptionFlow:
    @pytest.mark.integration
    async def test_create_subscription_uses_validated_upstream_response(
        self,
        async_client: AsyncClient,
        auth_headers: dict[str, str],
    ):
        expires_at = datetime(2026, 5, 1, 12, 0, tzinfo=UTC)

        with patch(
            "src.infrastructure.remnawave.user_gateway.RemnawaveUserGateway.get_by_telegram_id",
            AsyncMock(return_value=SimpleNamespace(uuid=uuid4())),
        ):
            with patch(
                "src.infrastructure.remnawave.client.RemnawaveClient.post_validated",
                AsyncMock(return_value=SimpleNamespace(uuid="sub-uuid-1", id=None, expires_at=expires_at)),
            ) as mock_post_validated:
                response = await async_client.post(
                    "/api/v1/telegram/user/123456/subscription",
                    headers=auth_headers,
                    json={"plan_name": "Premium Monthly", "duration_days": 30},
                )

        assert response.status_code == 201
        assert response.json() == {
            "status": "success",
            "subscription_id": "sub-uuid-1",
            "expires_at": "2026-05-01T12:00:00Z",
        }
        mock_post_validated.assert_awaited_once()
