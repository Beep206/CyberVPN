"""Unit contract tests for mobile customer profile responses."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from src.application.dto.mobile_auth import SubscriptionInfoDTO, SubscriptionStatus, UserResponseDTO
from src.presentation.api.v1.mobile_auth.routes import get_me


@pytest.mark.unit
async def test_get_me_returns_public_uid_for_customer_profile() -> None:
    user_id = uuid4()
    use_case = MagicMock()
    use_case.execute = AsyncMock(
        return_value=UserResponseDTO(
            id=user_id,
            public_uid=14_677_650,
            email="public-uid-profile@example.com",
            username="public_uid_profile",
            status="active",
            created_at=datetime.now(UTC),
            subscription=SubscriptionInfoDTO(status=SubscriptionStatus.NONE),
        )
    )

    with (
        patch("src.presentation.api.v1.mobile_auth.routes.MobileUserRepository"),
        patch("src.presentation.api.v1.mobile_auth.routes.MobileGetProfileUseCase", return_value=use_case),
    ):
        response = await get_me(user_id=user_id, db=AsyncMock(), sub_client=None)

    assert response.id == user_id
    assert response.public_uid == 14_677_650
    assert response.email == "public-uid-profile@example.com"
    use_case.execute.assert_awaited_once_with(user_id)
