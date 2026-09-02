from __future__ import annotations

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from src.application.dto.mobile_auth import SubscriptionStatus
from src.domain.value_objects.remnawave_user_ref import RemnawaveUserRef
from src.infrastructure.remnawave.subscription_client import (
    CachedSubscriptionClient,
    RemnawaveSubscriptionClient,
    RemnawaveSubscriptionIdentityError,
    RemnawaveSubscriptionLegacyRollbackClient,
    RemnawaveSubscriptionUnavailableError,
    _cache_identity_binding,
    _cache_key,
    _serialize_dto,
)


def _upstream_user(*, numeric_id: int | None = 42, legacy_uuid=None) -> SimpleNamespace:
    return SimpleNamespace(
        remnawave_numeric_id=numeric_id,
        uuid=str(legacy_uuid or uuid4()),
        status="active",
        expire_at=datetime.now(UTC) + timedelta(days=30),
        sub_revoked_at=None,
        subscription_uuid=uuid4(),
        traffic_limit_bytes=1_000,
        used_traffic_bytes=100,
    )


@pytest.mark.asyncio
async def test_normal_subscription_client_uses_numeric_route() -> None:
    legacy_uuid = uuid4()
    upstream = SimpleNamespace(
        get_validated=AsyncMock(return_value=_upstream_user(numeric_id=42, legacy_uuid=legacy_uuid))
    )
    client = RemnawaveSubscriptionClient(upstream)

    result = await client.get_subscription(RemnawaveUserRef(id=42, legacy_uuid=legacy_uuid))

    assert result.status is SubscriptionStatus.ACTIVE
    upstream.get_validated.assert_awaited_once()
    assert upstream.get_validated.await_args.args[0] == "/api/users/42"


@pytest.mark.asyncio
async def test_target_3_4_uppercase_active_status_maps_to_active_entitlement() -> None:
    upstream_user = _upstream_user(numeric_id=42)
    upstream_user.status = "ACTIVE"
    upstream = SimpleNamespace(get_validated=AsyncMock(return_value=upstream_user))

    result = await RemnawaveSubscriptionClient(upstream).get_subscription(42)

    assert result.status is SubscriptionStatus.ACTIVE


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "upstream_user",
    [
        _upstream_user(numeric_id=None),
        _upstream_user(numeric_id=99),
        _upstream_user(numeric_id=True),
    ],
)
async def test_normal_subscription_client_fails_closed_for_wrong_or_missing_numeric_response(upstream_user) -> None:
    upstream = SimpleNamespace(get_validated=AsyncMock(return_value=upstream_user))

    with pytest.raises(RemnawaveSubscriptionIdentityError, match="numeric user"):
        await RemnawaveSubscriptionClient(upstream).get_subscription(42)


@pytest.mark.asyncio
@pytest.mark.parametrize("upstream_legacy_uuid", ["not-a-uuid", str(uuid4())])
async def test_normal_subscription_client_fails_closed_for_present_wrong_legacy_response(
    upstream_legacy_uuid,
) -> None:
    expected_legacy_uuid = uuid4()
    upstream_user = _upstream_user(numeric_id=42, legacy_uuid=expected_legacy_uuid)
    upstream_user.uuid = upstream_legacy_uuid
    upstream = SimpleNamespace(get_validated=AsyncMock(return_value=upstream_user))

    with pytest.raises(RemnawaveSubscriptionIdentityError, match="rollback identity"):
        await RemnawaveSubscriptionClient(upstream).get_subscription(
            RemnawaveUserRef(id=42, legacy_uuid=expected_legacy_uuid)
        )


@pytest.mark.asyncio
async def test_normal_subscription_client_accepts_omitted_uuid_when_numeric_binding_is_exact() -> None:
    expected_legacy_uuid = uuid4()
    upstream_user = _upstream_user(numeric_id=42, legacy_uuid=expected_legacy_uuid)
    upstream_user.uuid = None
    upstream = SimpleNamespace(get_validated=AsyncMock(return_value=upstream_user))

    result = await RemnawaveSubscriptionClient(upstream).get_subscription(
        RemnawaveUserRef(id=42, legacy_uuid=expected_legacy_uuid)
    )

    assert result.status is SubscriptionStatus.ACTIVE


@pytest.mark.asyncio
async def test_identity_failure_is_not_cached_as_an_entitlement() -> None:
    legacy_uuid = uuid4()
    upstream = SimpleNamespace(
        get_validated=AsyncMock(return_value=_upstream_user(numeric_id=99, legacy_uuid=legacy_uuid))
    )
    cache = SimpleNamespace(get=AsyncMock(return_value=None), set=AsyncMock(), delete=AsyncMock())
    client = CachedSubscriptionClient(RemnawaveSubscriptionClient(upstream), cache)

    with pytest.raises(RemnawaveSubscriptionIdentityError):
        await client.get_subscription(RemnawaveUserRef(id=42, legacy_uuid=legacy_uuid))

    cache.set.assert_not_awaited()


@pytest.mark.asyncio
async def test_provider_failure_is_typed_and_never_converted_to_none() -> None:
    upstream = SimpleNamespace(get_validated=AsyncMock(side_effect=TimeoutError("ambiguous")))

    with pytest.raises(RemnawaveSubscriptionUnavailableError, match="temporarily unavailable"):
        await RemnawaveSubscriptionClient(upstream).get_subscription(42)


@pytest.mark.asyncio
async def test_cached_entitlement_rejects_wrong_legacy_identity_without_upstream_fallback() -> None:
    expected_ref = RemnawaveUserRef(id=42, legacy_uuid=uuid4())
    wrong_ref = RemnawaveUserRef(id=42, legacy_uuid=uuid4())
    dto = RemnawaveSubscriptionClient._map_to_dto(_upstream_user(numeric_id=42, legacy_uuid=expected_ref.legacy_uuid))
    cached = _serialize_dto(dto, identity_binding=_cache_identity_binding(expected_ref))
    upstream = SimpleNamespace(get_validated=AsyncMock())
    cache = SimpleNamespace(get=AsyncMock(return_value=cached), set=AsyncMock(), delete=AsyncMock())

    with pytest.raises(RemnawaveSubscriptionIdentityError, match="[Cc]ache"):
        await CachedSubscriptionClient(RemnawaveSubscriptionClient(upstream), cache).get_subscription(wrong_ref)

    assert _cache_key(expected_ref) != _cache_key(wrong_ref)
    upstream.get_validated.assert_not_awaited()
    cache.set.assert_not_awaited()


@pytest.mark.asyncio
@pytest.mark.parametrize("legacy_identifier", [str(uuid4()), uuid4(), 0, -1, True])
async def test_normal_subscription_client_rejects_legacy_or_invalid_identifiers(legacy_identifier) -> None:
    upstream = SimpleNamespace(get_validated=AsyncMock())
    client = RemnawaveSubscriptionClient(upstream)

    with pytest.raises(ValueError, match="numeric user id"):
        await client.get_subscription(legacy_identifier)

    upstream.get_validated.assert_not_awaited()


@pytest.mark.asyncio
async def test_explicit_rollback_adapter_is_the_only_uuid_route() -> None:
    legacy_uuid = uuid4()
    upstream = SimpleNamespace(
        get_validated=AsyncMock(return_value=_upstream_user(numeric_id=42, legacy_uuid=legacy_uuid))
    )
    client = RemnawaveSubscriptionLegacyRollbackClient(upstream)

    result = await client.get_subscription(legacy_uuid)

    assert result.status is SubscriptionStatus.ACTIVE
    upstream.get_validated.assert_awaited_once()
    assert upstream.get_validated.await_args.args[0] == f"/api/users/{legacy_uuid}"
