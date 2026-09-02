from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from src.application.use_cases.gifts.provisioning import (
    GiftProvisioningError,
    GiftProvisioningResult,
    GiftProvisioningService,
    build_gift_provisioning_request,
)
from src.infrastructure.remnawave.stage1_gift_gateway import RemnawaveGiftProvisioningGateway


def _request():
    return build_gift_provisioning_request(
        customer_account_id=uuid4(),
        gift_code_id=uuid4(),
        email="Gift@Example.Test",
        username="gift-recipient",
        telegram_id=123,
        plan_code=None,
        access_expires_at=datetime(2026, 10, 1, tzinfo=UTC),
        traffic_limit_bytes=None,
        device_limit=3,
        existing_remnawave_uuid=None,
        existing_remnawave_user_id=None,
    )


@pytest.mark.asyncio
async def test_gift_provisioning_validates_exact_numeric_result() -> None:
    request = _request()
    gateway = SimpleNamespace(
        provision_gift_access=AsyncMock(
            return_value=GiftProvisioningResult(
                customer_account_id=request.customer_account_id,
                gift_code_id=request.gift_code_id,
                remnawave_uuid=None,
                remnawave_user_id=42,
                profile_id=request.profile_id,
                status="active",
                expires_at=request.access_expires_at,
            )
        )
    )

    result = await GiftProvisioningService(gateway).provision(request)

    assert result.remnawave_user_id == 42
    gateway.provision_gift_access.assert_awaited_once_with(request)


@pytest.mark.asyncio
@pytest.mark.parametrize("remnawave_user_id", [None, True, 0, -1])
async def test_gift_provisioning_rejects_incomplete_numeric_result(remnawave_user_id: int | None) -> None:
    request = _request()
    gateway = SimpleNamespace(
        provision_gift_access=AsyncMock(
            return_value=GiftProvisioningResult(
                customer_account_id=request.customer_account_id,
                gift_code_id=request.gift_code_id,
                remnawave_uuid=None,
                remnawave_user_id=remnawave_user_id,
                profile_id=request.profile_id,
                status="active",
                expires_at=request.access_expires_at,
            )
        )
    )

    with pytest.raises(GiftProvisioningError, match="incomplete Remnawave identity"):
        await GiftProvisioningService(gateway).provision(request)


@pytest.mark.asyncio
async def test_gift_provisioning_rejects_non_active_provider_result() -> None:
    request = _request()
    gateway = SimpleNamespace(
        provision_gift_access=AsyncMock(
            return_value=GiftProvisioningResult(
                customer_account_id=request.customer_account_id,
                gift_code_id=request.gift_code_id,
                remnawave_uuid=None,
                remnawave_user_id=42,
                profile_id=request.profile_id,
                status="disabled",
                expires_at=request.access_expires_at,
            )
        )
    )

    with pytest.raises(GiftProvisioningError, match="active Remnawave access"):
        await GiftProvisioningService(gateway).provision(request)


@pytest.mark.asyncio
async def test_remnawave_gift_gateway_uses_plan_limits_without_trial_defaults() -> None:
    request = _request()
    upstream_user = SimpleNamespace(
        uuid=uuid4(),
        remnawave_id=42,
        status=SimpleNamespace(value="ACTIVE"),
        expires_at=request.access_expires_at,
        subscription_url="https://sub.example.test/redacted",
    )
    user_gateway = SimpleNamespace(create=AsyncMock(return_value=upstream_user), update=AsyncMock())

    result = await RemnawaveGiftProvisioningGateway(user_gateway).provision_gift_access(request)

    assert result.remnawave_user_id == 42
    create_kwargs = user_gateway.create.await_args.kwargs
    assert create_kwargs["username"] == request.remnawave_username
    assert create_kwargs["hwid_device_limit"] == 3
    assert create_kwargs["traffic_limit_bytes"] is None
    assert create_kwargs["expire_at"] == request.access_expires_at
    user_gateway.update.assert_not_awaited()
