from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from fastapi import HTTPException

from src.domain.value_objects.remnawave_user_ref import RemnawaveUserRef
from src.presentation.api.v1.customer_subscriptions import routes as module


class _ScalarResult:
    def __init__(self, value=None, *, duplicate: bool = False) -> None:
        self._value = value
        self._duplicate = duplicate

    def scalars(self):
        return self

    def all(self) -> list[object]:
        if self._value is None:
            return []
        return [self._value, self._value] if self._duplicate else [self._value]


def _install_subscription_repositories(
    monkeypatch: pytest.MonkeyPatch,
    *,
    item: object,
    mobile_user: object | None = None,
    service_identity: object | None = None,
) -> None:
    class FakeListSubscriptions:
        def __init__(self, _db) -> None:
            pass

        async def get_by_key(self, **_kwargs):
            return item

    class FakeMobileUsers:
        def __init__(self, _db) -> None:
            pass

        async def get_by_id(self, _customer_id):
            return mobile_user

    class FakeServiceAccess:
        def __init__(self, _db) -> None:
            pass

        async def get_service_identity_by_id(self, _service_identity_id):
            return service_identity

    monkeypatch.setattr(module, "ListCustomerSubscriptionsUseCase", FakeListSubscriptions)
    monkeypatch.setattr(module, "MobileUserRepository", FakeMobileUsers)
    monkeypatch.setattr(module, "ServiceAccessRepository", FakeServiceAccess)


def _identity_fixture(*, kind: str):
    customer_id = uuid4()
    realm_id = uuid4()
    subject_id = customer_id if kind == "trial" else uuid4()
    legacy_uuid = uuid4()
    item = SimpleNamespace(
        kind=kind,
        service_identity_id=subject_id if kind == "grant" else None,
    )
    mobile_user = SimpleNamespace(
        id=customer_id,
        remnawave_user_id=42,
        remnawave_uuid=str(legacy_uuid),
    )
    service_identity = SimpleNamespace(
        id=subject_id,
        customer_account_id=customer_id,
        auth_realm_id=realm_id,
        identity_status="active",
        provider_numeric_subject_id=42,
        provider_subject_ref=str(legacy_uuid),
    )
    return customer_id, realm_id, legacy_uuid, item, mobile_user, service_identity


@pytest.mark.unit
@pytest.mark.asyncio
@pytest.mark.parametrize("kind", ["trial", "grant"])
async def test_subscription_usage_uses_only_exact_mapped_numeric_identity(
    monkeypatch: pytest.MonkeyPatch,
    kind: str,
) -> None:
    customer_id, realm_id, legacy_uuid, item, mobile_user, service_identity = _identity_fixture(kind=kind)
    _install_subscription_repositories(
        monkeypatch,
        item=item,
        mobile_user=mobile_user,
        service_identity=service_identity,
    )
    calls: list[RemnawaveUserRef] = []

    class FakeUsage:
        def __init__(self, _gateway) -> None:
            pass

        async def execute(self, user_ref: RemnawaveUserRef):
            calls.append(user_ref)
            now = datetime.now(UTC)
            return SimpleNamespace(
                bandwidth_used_bytes=10,
                bandwidth_limit_bytes=100,
                connections_active=1,
                connections_limit=2,
                period_start=now,
                period_end=now,
                last_connection_at=now,
            )

    monkeypatch.setattr(module, "GetUserUsageUseCase", FakeUsage)
    session = AsyncMock()
    subject_type = "mobile_user" if kind == "trial" else "service_identity"
    subject_id = customer_id if kind == "trial" else service_identity.id
    session.execute.return_value = _ScalarResult(
        SimpleNamespace(
            subject_type=subject_type,
            subject_id=subject_id,
            reconciliation_state="mapped",
            numeric_user_id=42,
            legacy_uuid=str(legacy_uuid),
        )
    )

    response = await module.get_customer_subscription_usage(
        subscription_key="trial:test" if kind == "trial" else "grant:test",
        db=session,
        customer_account_id=customer_id,
        current_realm=SimpleNamespace(auth_realm=SimpleNamespace(id=realm_id)),
        remnawave_client=SimpleNamespace(),
    )

    assert response.usage_available is True
    assert calls == [RemnawaveUserRef(id=42, legacy_uuid=legacy_uuid)]


@pytest.mark.unit
@pytest.mark.asyncio
@pytest.mark.parametrize("kind", ["trial", "grant"])
@pytest.mark.parametrize("mapping_case", ["missing", "pending", "wrong_numeric", "wrong_legacy", "duplicate"])
async def test_subscription_usage_rejects_non_exact_mapping_before_upstream(
    monkeypatch: pytest.MonkeyPatch,
    kind: str,
    mapping_case: str,
) -> None:
    customer_id, realm_id, legacy_uuid, item, mobile_user, service_identity = _identity_fixture(kind=kind)
    _install_subscription_repositories(
        monkeypatch,
        item=item,
        mobile_user=mobile_user,
        service_identity=service_identity,
    )
    usage = AsyncMock()
    monkeypatch.setattr(module, "GetUserUsageUseCase", lambda _gateway: SimpleNamespace(execute=usage))
    subject_type = "mobile_user" if kind == "trial" else "service_identity"
    subject_id = customer_id if kind == "trial" else service_identity.id

    def reconciliation(*, state: str, numeric_id: int, mapped_legacy_uuid) -> SimpleNamespace:
        return SimpleNamespace(
            subject_type=subject_type,
            subject_id=subject_id,
            reconciliation_state=state,
            numeric_user_id=numeric_id,
            legacy_uuid=str(mapped_legacy_uuid),
        )

    mapping = {
        "missing": None,
        "pending": reconciliation(state="pending", numeric_id=42, mapped_legacy_uuid=legacy_uuid),
        "wrong_numeric": reconciliation(state="mapped", numeric_id=99, mapped_legacy_uuid=legacy_uuid),
        "wrong_legacy": reconciliation(state="mapped", numeric_id=42, mapped_legacy_uuid=uuid4()),
        "duplicate": reconciliation(state="mapped", numeric_id=42, mapped_legacy_uuid=legacy_uuid),
    }
    session = AsyncMock()
    session.execute.return_value = _ScalarResult(
        mapping.get(mapping_case),
        duplicate=mapping_case == "duplicate",
    )

    with pytest.raises(HTTPException) as exc_info:
        await module.get_customer_subscription_usage(
            subscription_key="trial:test" if kind == "trial" else "grant:test",
            db=session,
            customer_account_id=customer_id,
            current_realm=SimpleNamespace(auth_realm=SimpleNamespace(id=realm_id)),
            remnawave_client=SimpleNamespace(),
        )

    assert exc_info.value.status_code == 409
    usage.assert_not_awaited()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_subscription_usage_rejects_cross_customer_service_identity_before_upstream(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    customer_id, realm_id, _legacy_uuid, item, mobile_user, service_identity = _identity_fixture(kind="grant")
    service_identity.customer_account_id = uuid4()
    _install_subscription_repositories(
        monkeypatch,
        item=item,
        mobile_user=mobile_user,
        service_identity=service_identity,
    )
    usage = AsyncMock()
    monkeypatch.setattr(module, "GetUserUsageUseCase", lambda _gateway: SimpleNamespace(execute=usage))
    session = AsyncMock()

    with pytest.raises(HTTPException) as exc_info:
        await module.get_customer_subscription_usage(
            subscription_key="grant:test",
            db=session,
            customer_account_id=customer_id,
            current_realm=SimpleNamespace(auth_realm=SimpleNamespace(id=realm_id)),
            remnawave_client=SimpleNamespace(),
        )

    assert exc_info.value.status_code == 409
    session.execute.assert_not_awaited()
    usage.assert_not_awaited()


@pytest.mark.unit
@pytest.mark.asyncio
@pytest.mark.parametrize("kind", ["trial", "grant"])
async def test_subscription_usage_without_provider_identity_is_unavailable_without_legacy_fallback(
    monkeypatch: pytest.MonkeyPatch,
    kind: str,
) -> None:
    customer_id, realm_id, _legacy_uuid, item, mobile_user, service_identity = _identity_fixture(kind=kind)
    mobile_user.remnawave_user_id = None
    mobile_user.remnawave_uuid = None
    service_identity.provider_numeric_subject_id = None
    service_identity.provider_subject_ref = None
    _install_subscription_repositories(
        monkeypatch,
        item=item,
        mobile_user=mobile_user,
        service_identity=service_identity,
    )
    usage = AsyncMock()
    monkeypatch.setattr(module, "GetUserUsageUseCase", lambda _gateway: SimpleNamespace(execute=usage))
    session = AsyncMock()

    response = await module.get_customer_subscription_usage(
        subscription_key="trial:test" if kind == "trial" else "grant:test",
        db=session,
        customer_account_id=customer_id,
        current_realm=SimpleNamespace(auth_realm=SimpleNamespace(id=realm_id)),
        remnawave_client=SimpleNamespace(),
    )

    assert response.usage_available is False
    assert response.usage_unavailable_reason == "upstream_user_not_found"
    session.execute.assert_not_awaited()
    usage.assert_not_awaited()
