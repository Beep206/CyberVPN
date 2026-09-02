from __future__ import annotations

from types import SimpleNamespace
from typing import cast
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.use_cases.service_access import access_delivery_channels as delivery_module
from src.application.use_cases.service_access.access_delivery_channels import (
    CurrentServiceIdentityConflict,
    GetCurrentServiceStateUseCase,
    ResolveCurrentAccessDeliveryChannelUseCase,
)
from src.domain.value_objects.remnawave_user_ref import RemnawaveUserRef


class _Repo:
    async def get_service_identity_by_customer_realm_provider(self, **_kwargs):
        return None

    async def get_service_identity_by_customer_realm_provider_numeric_subject(self, **_kwargs):
        return None


class _Session:
    def __init__(self, customer) -> None:
        self.customer = customer

    async def get(self, _model, _identity):
        return self.customer


@pytest.mark.asyncio
async def test_access_delivery_auto_bridge_passes_numeric_only_remnawave_identity(monkeypatch) -> None:
    customer_id = uuid4()
    realm_id = uuid4()
    session = _Session(
        SimpleNamespace(
            id=customer_id,
            auth_realm_id=realm_id,
            remnawave_user_id=4201,
            remnawave_uuid=None,
        )
    )
    captured: dict[str, object] = {}
    expected = SimpleNamespace(created=True, service_identity=SimpleNamespace(id=uuid4()))

    class _CreateServiceIdentity:
        def __init__(self, received_session) -> None:
            assert received_session is session

        async def execute(self, **kwargs):
            captured.update(kwargs)
            return expected

    async def resolve_exact_ref(_session, *, subject_type, numeric_user_id, **_kwargs):
        assert subject_type == "mobile_user"
        return RemnawaveUserRef(id=numeric_user_id)

    monkeypatch.setattr(delivery_module, "CreateServiceIdentityUseCase", _CreateServiceIdentity)
    monkeypatch.setattr(delivery_module, "resolve_exact_mapped_remnawave_ref", resolve_exact_ref)
    use_case = ResolveCurrentAccessDeliveryChannelUseCase(cast(AsyncSession, session))
    monkeypatch.setattr(use_case, "_repo", _Repo())

    result = await use_case._ensure_current_service_identity(
        customer_account_id=customer_id,
        current_realm=SimpleNamespace(auth_realm=SimpleNamespace(id=realm_id)),
        provider_name="remnawave",
        service_context={},
    )

    assert result is expected
    assert captured["provider_numeric_subject_id"] == 4201
    assert captured["provider_subject_ref"] is None


@pytest.mark.asyncio
async def test_access_delivery_reuses_exact_subscription_identity_without_duplicate_mapping(monkeypatch) -> None:
    customer_id = uuid4()
    realm_id = uuid4()
    legacy_uuid = uuid4()
    canonical_identity = SimpleNamespace(
        id=uuid4(),
        customer_account_id=customer_id,
        auth_realm_id=realm_id,
        provider_name="remnawave",
        provider_numeric_subject_id=4202,
        provider_subject_ref=str(legacy_uuid),
        identity_scope="subscription",
        identity_status="active",
    )
    session = _Session(
        SimpleNamespace(
            id=customer_id,
            auth_realm_id=realm_id,
            remnawave_user_id=4202,
            remnawave_uuid=str(legacy_uuid),
        )
    )

    class _CanonicalRepo(_Repo):
        async def get_service_identity_by_customer_realm_provider_numeric_subject(self, **kwargs):
            assert kwargs == {
                "customer_account_id": customer_id,
                "auth_realm_id": realm_id,
                "provider_name": "remnawave",
                "provider_numeric_subject_id": 4202,
            }
            return canonical_identity

    async def resolve_exact_ref(_session, *, subject_type, numeric_user_id, legacy_uuid_raw, **_kwargs):
        assert subject_type in {"mobile_user", "service_identity"}
        assert numeric_user_id == 4202
        assert legacy_uuid_raw == str(legacy_uuid)
        return RemnawaveUserRef(id=4202, legacy_uuid=legacy_uuid)

    class _ForbiddenCreateServiceIdentity:
        def __init__(self, _session) -> None:
            raise AssertionError("an exact subscription identity must be reused, not duplicated")

    monkeypatch.setattr(delivery_module, "resolve_exact_mapped_remnawave_ref", resolve_exact_ref)
    monkeypatch.setattr(delivery_module, "CreateServiceIdentityUseCase", _ForbiddenCreateServiceIdentity)
    use_case = ResolveCurrentAccessDeliveryChannelUseCase(cast(AsyncSession, session))
    monkeypatch.setattr(use_case, "_repo", _CanonicalRepo())

    result = await use_case._ensure_current_service_identity(
        customer_account_id=customer_id,
        current_realm=SimpleNamespace(auth_realm=SimpleNamespace(id=realm_id)),
        provider_name="remnawave",
        service_context={},
    )

    assert result.created is False
    assert result.service_identity is canonical_identity


@pytest.mark.asyncio
async def test_current_service_state_reads_the_same_exact_subscription_identity(monkeypatch) -> None:
    customer_id = uuid4()
    realm_id = uuid4()
    legacy_uuid = uuid4()
    customer = SimpleNamespace(
        id=customer_id,
        auth_realm_id=realm_id,
        remnawave_user_id=4202,
        remnawave_uuid=str(legacy_uuid),
    )
    canonical_identity = SimpleNamespace(
        id=uuid4(),
        customer_account_id=customer_id,
        auth_realm_id=realm_id,
        provider_name="remnawave",
        provider_numeric_subject_id=4202,
        provider_subject_ref=str(legacy_uuid),
        identity_scope="subscription",
        identity_status="active",
    )

    class _CanonicalRepo(_Repo):
        async def get_service_identity_by_customer_realm_provider_numeric_subject(self, **_kwargs):
            return canonical_identity

    async def resolve_exact_ref(_session, *, numeric_user_id, legacy_uuid_raw, **_kwargs):
        assert numeric_user_id == 4202
        assert legacy_uuid_raw == str(legacy_uuid)
        return RemnawaveUserRef(id=4202, legacy_uuid=legacy_uuid)

    monkeypatch.setattr(delivery_module, "resolve_exact_mapped_remnawave_ref", resolve_exact_ref)
    use_case = GetCurrentServiceStateUseCase(cast(AsyncSession, SimpleNamespace()))
    monkeypatch.setattr(use_case, "_repo", _CanonicalRepo())

    result = await use_case._resolve_current_service_identity(
        customer=customer,
        current_realm=SimpleNamespace(auth_realm=SimpleNamespace(id=realm_id)),
        provider_name="remnawave",
    )

    assert result is canonical_identity


@pytest.mark.asyncio
async def test_current_service_state_returns_empty_without_numeric_or_local_identity(monkeypatch) -> None:
    customer = SimpleNamespace(
        id=uuid4(),
        remnawave_user_id=None,
        remnawave_uuid="legacy-read-only-reference",
    )
    use_case = GetCurrentServiceStateUseCase(cast(AsyncSession, SimpleNamespace()))
    monkeypatch.setattr(use_case, "_repo", _Repo())

    result = await use_case._resolve_current_service_identity(
        customer=customer,
        current_realm=SimpleNamespace(auth_realm=SimpleNamespace(id=uuid4())),
        provider_name="remnawave",
    )

    assert result is None


@pytest.mark.asyncio
async def test_current_service_state_rejects_legacy_account_identity_without_numeric_mapping(monkeypatch) -> None:
    stale_account_identity = SimpleNamespace(id=uuid4(), identity_scope="account", identity_status="active")
    customer = SimpleNamespace(
        id=uuid4(),
        remnawave_user_id=None,
        remnawave_uuid=str(uuid4()),
    )

    class _StaleAccountRepo(_Repo):
        async def get_service_identity_by_customer_realm_provider(self, **_kwargs):
            return stale_account_identity

    use_case = GetCurrentServiceStateUseCase(cast(AsyncSession, SimpleNamespace()))
    monkeypatch.setattr(use_case, "_repo", _StaleAccountRepo())

    with pytest.raises(CurrentServiceIdentityConflict, match="canonical Remnawave identity"):
        await use_case._resolve_current_service_identity(
            customer=customer,
            current_realm=SimpleNamespace(auth_realm=SimpleNamespace(id=uuid4())),
            provider_name="remnawave",
        )


@pytest.mark.asyncio
async def test_current_service_state_preserves_non_remnawave_account_lookup(monkeypatch) -> None:
    account_identity = SimpleNamespace(id=uuid4(), provider_name="other-provider")
    customer = SimpleNamespace(id=uuid4())

    class _OtherProviderRepo(_Repo):
        async def get_service_identity_by_customer_realm_provider(self, **_kwargs):
            return account_identity

    use_case = GetCurrentServiceStateUseCase(cast(AsyncSession, SimpleNamespace()))
    monkeypatch.setattr(use_case, "_repo", _OtherProviderRepo())

    result = await use_case._resolve_current_service_identity(
        customer=customer,
        current_realm=SimpleNamespace(auth_realm=SimpleNamespace(id=uuid4())),
        provider_name="other-provider",
    )

    assert result is account_identity


@pytest.mark.asyncio
async def test_access_delivery_rejects_cross_realm_customer_before_identity_reuse() -> None:
    customer_id = uuid4()
    session = _Session(
        SimpleNamespace(
            id=customer_id,
            auth_realm_id=uuid4(),
            remnawave_user_id=4203,
            remnawave_uuid=None,
        )
    )
    use_case = ResolveCurrentAccessDeliveryChannelUseCase(cast(AsyncSession, session))
    use_case._repo = _Repo()

    with pytest.raises(ValueError, match="does not belong to auth realm"):
        await use_case._ensure_current_service_identity(
            customer_account_id=customer_id,
            current_realm=SimpleNamespace(auth_realm=SimpleNamespace(id=uuid4())),
            provider_name="remnawave",
            service_context={},
        )


@pytest.mark.asyncio
async def test_access_delivery_rejects_ambiguous_canonical_identity_without_create(monkeypatch) -> None:
    customer_id = uuid4()
    realm_id = uuid4()
    session = _Session(
        SimpleNamespace(
            id=customer_id,
            auth_realm_id=realm_id,
            remnawave_user_id=4204,
            remnawave_uuid=None,
        )
    )

    class _AmbiguousRepo(_Repo):
        async def get_service_identity_by_customer_realm_provider_numeric_subject(self, **_kwargs):
            raise ValueError("Provider numeric subject maps to multiple local service identities")

    async def resolve_exact_ref(_session, *, numeric_user_id, **_kwargs):
        return RemnawaveUserRef(id=numeric_user_id)

    class _ForbiddenCreateServiceIdentity:
        def __init__(self, _session) -> None:
            raise AssertionError("an ambiguous canonical identity must fail before create")

    monkeypatch.setattr(delivery_module, "resolve_exact_mapped_remnawave_ref", resolve_exact_ref)
    monkeypatch.setattr(delivery_module, "CreateServiceIdentityUseCase", _ForbiddenCreateServiceIdentity)
    use_case = ResolveCurrentAccessDeliveryChannelUseCase(cast(AsyncSession, session))
    monkeypatch.setattr(use_case, "_repo", _AmbiguousRepo())

    with pytest.raises(ValueError, match="maps to multiple local service identities"):
        await use_case._ensure_current_service_identity(
            customer_account_id=customer_id,
            current_realm=SimpleNamespace(auth_realm=SimpleNamespace(id=realm_id)),
            provider_name="remnawave",
            service_context={},
        )


@pytest.mark.asyncio
@pytest.mark.parametrize("invalid_numeric_id", [None, 0, -1, True, "4201"])
async def test_access_delivery_auto_bridge_rejects_missing_or_inexact_numeric_identity(
    monkeypatch,
    invalid_numeric_id,
) -> None:
    customer_id = uuid4()
    realm_id = uuid4()
    session = _Session(
        SimpleNamespace(
            id=customer_id,
            auth_realm_id=realm_id,
            remnawave_user_id=invalid_numeric_id,
            remnawave_uuid=None,
        )
    )
    use_case = ResolveCurrentAccessDeliveryChannelUseCase(cast(AsyncSession, session))
    monkeypatch.setattr(use_case, "_repo", _Repo())

    with pytest.raises(ValueError, match="positive provider numeric identity"):
        await use_case._ensure_current_service_identity(
            customer_account_id=customer_id,
            current_realm=SimpleNamespace(auth_realm=SimpleNamespace(id=realm_id)),
            provider_name="remnawave",
            service_context={},
        )
