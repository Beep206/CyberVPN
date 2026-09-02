from __future__ import annotations

from types import SimpleNamespace
from typing import cast
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.use_cases.customer_subscriptions.service_access import (
    CustomerSubscriptionServiceAccessUseCase,
)
from src.domain.value_objects.remnawave_user_ref import RemnawaveUserRef


@pytest.mark.asyncio
async def test_provider_read_syncs_only_exact_active_subscription_delivery_state(
    caplog: pytest.LogCaptureFixture,
) -> None:
    customer_id = uuid4()
    realm_id = uuid4()
    legacy_uuid = uuid4()
    user_ref = RemnawaveUserRef(id=4202, legacy_uuid=legacy_uuid)
    customer = SimpleNamespace(
        id=customer_id,
        auth_realm_id=realm_id,
        remnawave_user_id=4202,
        remnawave_uuid=str(legacy_uuid),
        subscription_url="https://sub.example/old",
    )
    service_identity = SimpleNamespace(
        id=uuid4(),
        identity_scope="subscription",
        identity_status="active",
        subscription_key=f"grant:{uuid4()}",
        service_context={"plan_code": "premium_smart_ru", "subscription_url": "https://sub.example/old"},
    )
    active_channel = SimpleNamespace(
        delivery_payload={"entitlement_status": "active", "subscription_url": "https://sub.example/old"}
    )
    session = SimpleNamespace(get=AsyncMock(return_value=customer), flush=AsyncMock())
    repo = SimpleNamespace(
        get_service_identity_by_customer_realm_provider_numeric_subject=AsyncMock(return_value=service_identity),
        list_active_access_delivery_channels_for_update=AsyncMock(return_value=[active_channel]),
    )
    use_case = CustomerSubscriptionServiceAccessUseCase(cast(AsyncSession, session))
    use_case._repo = repo
    use_case._resolve_mobile_identity_ref = AsyncMock(return_value=user_ref)
    use_case._resolve_service_identity_ref = AsyncMock(return_value=user_ref)

    await use_case.sync_current_remnawave_subscription_url(
        customer_account_id=customer_id,
        auth_realm_id=realm_id,
        remnawave_ref=user_ref,
        subscription_url="https://sub.example/current",
    )

    repo.get_service_identity_by_customer_realm_provider_numeric_subject.assert_awaited_once_with(
        customer_account_id=customer_id,
        auth_realm_id=realm_id,
        provider_name="remnawave",
        provider_numeric_subject_id=4202,
    )
    repo.list_active_access_delivery_channels_for_update.assert_awaited_once_with(
        service_identity_id=service_identity.id,
        channel_type="shared_client",
        limit=1_001,
    )
    assert customer.subscription_url == "https://sub.example/current"
    assert service_identity.service_context == {
        "plan_code": "premium_smart_ru",
        "subscription_url": "https://sub.example/current",
    }
    assert active_channel.delivery_payload == {
        "entitlement_status": "active",
        "subscription_url": "https://sub.example/current",
        "subscription_key": service_identity.subscription_key,
    }
    session.flush.assert_awaited_once()
    assert "https://sub.example/old" not in caplog.text
    assert "https://sub.example/current" not in caplog.text


@pytest.mark.asyncio
async def test_provider_read_does_not_refresh_inactive_subscription_delivery_channel() -> None:
    customer_id = uuid4()
    realm_id = uuid4()
    user_ref = RemnawaveUserRef(id=4203)
    customer = SimpleNamespace(
        id=customer_id,
        auth_realm_id=realm_id,
        remnawave_user_id=4203,
        remnawave_uuid=None,
        subscription_url="https://sub.example/old",
    )
    inactive_identity = SimpleNamespace(
        id=uuid4(),
        identity_scope="subscription",
        identity_status="suspended",
        service_context={"subscription_url": "https://sub.example/old"},
    )
    session = SimpleNamespace(get=AsyncMock(return_value=customer), flush=AsyncMock())
    repo = SimpleNamespace(
        get_service_identity_by_customer_realm_provider_numeric_subject=AsyncMock(return_value=inactive_identity),
        list_active_access_delivery_channels_for_update=AsyncMock(),
    )
    use_case = CustomerSubscriptionServiceAccessUseCase(cast(AsyncSession, session))
    use_case._repo = repo
    use_case._resolve_mobile_identity_ref = AsyncMock(return_value=user_ref)

    await use_case.sync_current_remnawave_subscription_url(
        customer_account_id=customer_id,
        auth_realm_id=realm_id,
        remnawave_ref=user_ref,
        subscription_url="https://sub.example/current",
    )

    assert customer.subscription_url == "https://sub.example/current"
    assert inactive_identity.service_context == {"subscription_url": "https://sub.example/old"}
    repo.list_active_access_delivery_channels_for_update.assert_not_awaited()


@pytest.mark.asyncio
async def test_provider_read_sync_fails_closed_on_cross_realm_customer() -> None:
    customer_id = uuid4()
    customer = SimpleNamespace(
        id=customer_id,
        auth_realm_id=uuid4(),
        subscription_url="https://sub.example/old",
    )
    session = SimpleNamespace(get=AsyncMock(return_value=customer), flush=AsyncMock())
    use_case = CustomerSubscriptionServiceAccessUseCase(cast(AsyncSession, session))
    use_case._repo = SimpleNamespace(get_service_identity_by_customer_realm_provider_numeric_subject=AsyncMock())

    with pytest.raises(PermissionError, match="does not belong to auth realm"):
        await use_case.sync_current_remnawave_subscription_url(
            customer_account_id=customer_id,
            auth_realm_id=uuid4(),
            remnawave_ref=RemnawaveUserRef(id=4204),
            subscription_url="https://sub.example/current",
        )

    assert customer.subscription_url == "https://sub.example/old"
    session.flush.assert_not_awaited()


@pytest.mark.asyncio
async def test_provider_read_sync_updates_bounded_101_row_locked_snapshot_without_touching_inactive_rows() -> None:
    customer_id = uuid4()
    realm_id = uuid4()
    user_ref = RemnawaveUserRef(id=4208)
    customer = SimpleNamespace(
        id=customer_id,
        auth_realm_id=realm_id,
        subscription_url="https://sub.example/old",
    )
    service_identity = SimpleNamespace(
        id=uuid4(),
        identity_scope="subscription",
        identity_status="active",
        subscription_key=f"grant:{uuid4()}",
        service_context={"subscription_url": "https://sub.example/old"},
    )
    active_channels = [
        SimpleNamespace(delivery_payload={"subscription_url": "https://sub.example/old"}) for _ in range(101)
    ]
    archived_channel = SimpleNamespace(delivery_payload={"subscription_url": "https://sub.example/archived"})
    list_channels = AsyncMock(return_value=active_channels)
    session = SimpleNamespace(get=AsyncMock(return_value=customer), flush=AsyncMock())
    use_case = CustomerSubscriptionServiceAccessUseCase(cast(AsyncSession, session))
    use_case._repo = SimpleNamespace(
        get_service_identity_by_customer_realm_provider_numeric_subject=AsyncMock(return_value=service_identity),
        list_active_access_delivery_channels_for_update=list_channels,
    )
    use_case._resolve_mobile_identity_ref = AsyncMock(return_value=user_ref)
    use_case._resolve_service_identity_ref = AsyncMock(return_value=user_ref)

    await use_case.sync_current_remnawave_subscription_url(
        customer_account_id=customer_id,
        auth_realm_id=realm_id,
        remnawave_ref=user_ref,
        subscription_url="https://sub.example/current",
    )

    list_channels.assert_awaited_once_with(
        service_identity_id=service_identity.id,
        channel_type="shared_client",
        limit=1_001,
    )
    assert all(
        channel.delivery_payload["subscription_url"] == "https://sub.example/current" for channel in active_channels
    )
    assert archived_channel.delivery_payload == {"subscription_url": "https://sub.example/archived"}


@pytest.mark.asyncio
async def test_provider_read_sync_rejects_mismatched_service_identity_before_mutation() -> None:
    customer_id = uuid4()
    realm_id = uuid4()
    customer_ref = RemnawaveUserRef(id=4205)
    customer = SimpleNamespace(
        id=customer_id,
        auth_realm_id=realm_id,
        subscription_url="https://sub.example/old",
    )
    service_identity = SimpleNamespace(
        id=uuid4(),
        identity_scope="subscription",
        identity_status="active",
        service_context={"subscription_url": "https://sub.example/old"},
    )
    session = SimpleNamespace(get=AsyncMock(return_value=customer), flush=AsyncMock())
    use_case = CustomerSubscriptionServiceAccessUseCase(cast(AsyncSession, session))
    use_case._repo = SimpleNamespace(
        get_service_identity_by_customer_realm_provider_numeric_subject=AsyncMock(return_value=service_identity)
    )
    use_case._resolve_mobile_identity_ref = AsyncMock(return_value=customer_ref)
    use_case._resolve_service_identity_ref = AsyncMock(return_value=RemnawaveUserRef(id=9999))

    with pytest.raises(HTTPException) as exc_info:
        await use_case.sync_current_remnawave_subscription_url(
            customer_account_id=customer_id,
            auth_realm_id=realm_id,
            remnawave_ref=customer_ref,
            subscription_url="https://sub.example/current",
        )

    assert exc_info.value.status_code == 409
    assert customer.subscription_url == "https://sub.example/old"
    assert service_identity.service_context == {"subscription_url": "https://sub.example/old"}
    session.flush.assert_not_awaited()


@pytest.mark.asyncio
async def test_provider_read_sync_fails_closed_on_ambiguous_local_identity_without_mutation() -> None:
    customer_id = uuid4()
    realm_id = uuid4()
    user_ref = RemnawaveUserRef(id=4206)
    customer = SimpleNamespace(
        id=customer_id,
        auth_realm_id=realm_id,
        subscription_url="https://sub.example/old",
    )
    session = SimpleNamespace(get=AsyncMock(return_value=customer), flush=AsyncMock())
    list_channels = AsyncMock()
    use_case = CustomerSubscriptionServiceAccessUseCase(cast(AsyncSession, session))
    use_case._repo = SimpleNamespace(
        get_service_identity_by_customer_realm_provider_numeric_subject=AsyncMock(
            side_effect=ValueError("Provider numeric subject maps to multiple local service identities")
        ),
        list_active_access_delivery_channels_for_update=list_channels,
    )
    use_case._resolve_mobile_identity_ref = AsyncMock(return_value=user_ref)

    with pytest.raises(HTTPException) as exc_info:
        await use_case.sync_current_remnawave_subscription_url(
            customer_account_id=customer_id,
            auth_realm_id=realm_id,
            remnawave_ref=user_ref,
            subscription_url="https://sub.example/current",
        )

    assert exc_info.value.status_code == 409
    assert customer.subscription_url == "https://sub.example/old"
    list_channels.assert_not_awaited()
    session.flush.assert_not_awaited()


@pytest.mark.asyncio
async def test_provider_read_sync_rejects_overflowing_locked_snapshot_before_mutation() -> None:
    customer_id = uuid4()
    realm_id = uuid4()
    user_ref = RemnawaveUserRef(id=4209)
    customer = SimpleNamespace(
        id=customer_id,
        auth_realm_id=realm_id,
        subscription_url="https://sub.example/old",
    )
    service_identity = SimpleNamespace(
        id=uuid4(),
        identity_scope="subscription",
        identity_status="active",
        subscription_key=f"grant:{uuid4()}",
        service_context={"subscription_url": "https://sub.example/old"},
    )
    channels = [SimpleNamespace(delivery_payload={"subscription_url": "https://sub.example/old"}) for _ in range(1_001)]
    session = SimpleNamespace(get=AsyncMock(return_value=customer), flush=AsyncMock())
    use_case = CustomerSubscriptionServiceAccessUseCase(cast(AsyncSession, session))
    use_case._repo = SimpleNamespace(
        get_service_identity_by_customer_realm_provider_numeric_subject=AsyncMock(return_value=service_identity),
        list_active_access_delivery_channels_for_update=AsyncMock(return_value=channels),
    )
    use_case._resolve_mobile_identity_ref = AsyncMock(return_value=user_ref)
    use_case._resolve_service_identity_ref = AsyncMock(return_value=user_ref)

    with pytest.raises(HTTPException) as exc_info:
        await use_case.sync_current_remnawave_subscription_url(
            customer_account_id=customer_id,
            auth_realm_id=realm_id,
            remnawave_ref=user_ref,
            subscription_url="https://sub.example/current",
        )

    assert exc_info.value.status_code == 409
    assert customer.subscription_url == "https://sub.example/old"
    assert service_identity.service_context == {"subscription_url": "https://sub.example/old"}
    assert all(channel.delivery_payload == {"subscription_url": "https://sub.example/old"} for channel in channels)
    session.flush.assert_not_awaited()
