from __future__ import annotations

import uuid
from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException
from httpx import ReadTimeout, Request

from src.application.services.remnawave_create_attempts import (
    RemnawaveCreateAttemptService as RealRemnawaveCreateAttemptService,
)
from src.application.use_cases.customer_subscriptions import service_access as service_access_module
from src.application.use_cases.customer_subscriptions.service_access import (
    CustomerSubscriptionServiceAccessUseCase,
)
from src.config.settings import settings
from src.domain.enums import AccessDeliveryChannelType, DeviceCredentialType
from src.domain.value_objects.remnawave_user_ref import RemnawaveUserRef
from src.infrastructure.remnawave.user_gateway import RemnawaveMutationAcceptedPending
from src.presentation.api.v1.access_delivery_channels.schemas import GetCurrentServiceStateRequest
from src.presentation.api.v1.customer_subscriptions import routes as customer_subscription_routes
from tests.helpers.spb_de_readiness import enable_spb_de_readiness, manifest_pointer_json


@pytest.fixture(autouse=True)
def _stub_runtime_identity_ledger(monkeypatch: pytest.MonkeyPatch):
    """Keep routing-focused fixtures independent from the ledger unit suite."""

    async def resolve(_session, *, numeric_user_id, legacy_uuid_raw, **_kwargs):
        if numeric_user_id is None and not legacy_uuid_raw:
            return None
        numeric_id = numeric_user_id if isinstance(numeric_user_id, int) else 42
        legacy_uuid = uuid.UUID(str(legacy_uuid_raw)) if legacy_uuid_raw else uuid.uuid4()
        return RemnawaveUserRef(id=numeric_id, legacy_uuid=legacy_uuid)

    async def persist_mobile(_session, *, customer, remnawave_user_id, remnawave_uuid, **_kwargs):
        numeric_id = remnawave_user_id if isinstance(remnawave_user_id, int) else 42
        legacy_uuid = uuid.UUID(str(remnawave_uuid)) if remnawave_uuid else uuid.uuid4()
        customer.remnawave_user_id = numeric_id
        customer.remnawave_uuid = str(legacy_uuid)
        return RemnawaveUserRef(id=numeric_id, legacy_uuid=legacy_uuid)

    async def persist_service(_session, *, service_identity, remnawave_user_id, remnawave_uuid, **_kwargs):
        numeric_id = remnawave_user_id if isinstance(remnawave_user_id, int) else 42
        legacy_uuid = uuid.UUID(str(remnawave_uuid)) if remnawave_uuid else uuid.uuid4()
        service_identity.provider_numeric_subject_id = numeric_id
        service_identity.provider_subject_ref = str(legacy_uuid)
        return RemnawaveUserRef(id=numeric_id, legacy_uuid=legacy_uuid)

    class RoutingOnlyCreateAttemptService:
        def __init__(self, _session) -> None:
            self.record = SimpleNamespace(status="pending", response_payload={})

        async def begin(self, **_kwargs):
            return SimpleNamespace(record=self.record, should_mutate=True)

        async def mark_reconciliation_required(self, _record) -> None:
            return None

        async def mark_completed(self, _record, *, user_ref) -> None:
            return None

    monkeypatch.setattr(service_access_module, "resolve_exact_mapped_remnawave_ref", resolve)
    monkeypatch.setattr(service_access_module, "persist_runtime_mapped_mobile_identity", persist_mobile)
    monkeypatch.setattr(service_access_module, "persist_runtime_mapped_service_identity", persist_service)
    monkeypatch.setattr(
        service_access_module,
        "RemnawaveCreateAttemptService",
        RoutingOnlyCreateAttemptService,
    )


def _subscription_summary() -> SimpleNamespace:
    return SimpleNamespace(
        addons=[],
        display_name="Safe Pro",
        effective_entitlements={"device_limit": 5},
        entitlement_grant_id=uuid.uuid4(),
        expires_at="2026-07-10T00:00:00Z",
        invite_bundle={},
        is_trial=False,
        plan_code="pro",
        plan_uuid=str(uuid.uuid4()),
        status="active",
        subscription_key=f"grant:{uuid.uuid4()}",
    )


def _spb_de_context(external_squad_uuid: str, internal_squad_uuid: str) -> dict[str, object]:
    return {
        "remnawave_routing_product": "premium_spb_de_exceptions",
        "remnawave_external_squad_uuid": external_squad_uuid,
        "remnawave_internal_squad_uuids": [internal_squad_uuid],
        "remnawave_config_profile": "S1 SPB DE Exceptions",
        "remnawave_policy_version": "premium_spb_de_exceptions.v1",
        "remnawave_fail_closed_for_matched_exceptions": True,
    }


def _enable_spb_de_data_plane(monkeypatch: pytest.MonkeyPatch) -> None:
    enable_spb_de_readiness(monkeypatch)


class _CreateAttemptScalarResult:
    def __init__(self, record) -> None:
        self._record = record

    def scalars(self):
        return self

    def one_or_none(self):
        return self._record


class _CreateAttemptSession:
    def __init__(self) -> None:
        self.record = None
        self.commits = 0

    async def execute(self, _statement):
        return _CreateAttemptScalarResult(self.record)

    def add(self, record) -> None:
        self.record = record

    async def commit(self) -> None:
        self.commits += 1

    async def rollback(self) -> None:
        return None

    async def flush(self) -> None:
        return None


@pytest.mark.asyncio
@pytest.mark.parametrize("failure_kind", ["accepted", "timeout"])
async def test_selected_service_ambiguous_create_is_latched_and_never_reposted(
    failure_kind: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        service_access_module,
        "RemnawaveCreateAttemptService",
        RealRemnawaveCreateAttemptService,
    )
    session = _CreateAttemptSession()
    use_case = CustomerSubscriptionServiceAccessUseCase(session)

    class AmbiguousGateway:
        def __init__(self) -> None:
            self.calls = 0

        async def create(self, username: str, **_payload):
            self.calls += 1
            if failure_kind == "accepted":
                raise RemnawaveMutationAcceptedPending(operation="create")
            raise ReadTimeout("ambiguous create", request=Request("POST", "https://remnawave.test/api/users"))

    gateway = AmbiguousGateway()
    customer_account_id = uuid.uuid4()
    business_key = f"grant:{uuid.uuid4()}"
    for _attempt in range(2):
        with pytest.raises(HTTPException) as exc_info:
            await use_case._create_remnawave_user_once(
                gateway=gateway,
                username="cvpn_s_safe",
                customer_account_id=customer_account_id,
                business_key=business_key,
                payload={"expire_at": "2026-09-01T00:00:00Z"},
            )
        assert exc_info.value.status_code == 409

    assert gateway.calls == 1
    assert session.record.status == "reconciliation_required"
    assert session.record.response_payload == {}
    assert session.commits == 2


@pytest.mark.asyncio
async def test_selected_subscription_state_returns_ready_requested_device_credential() -> None:
    use_case = CustomerSubscriptionServiceAccessUseCase(SimpleNamespace())
    subscription = _subscription_summary()
    service_identity = SimpleNamespace(
        id=uuid.uuid4(),
        provider_name="remnawave",
        service_key="svc_safe_ready",
        subscription_key=subscription.subscription_key,
    )
    provisioning_profile = SimpleNamespace(id=uuid.uuid4(), profile_key="shared_client-default")
    device_credential = SimpleNamespace(
        id=uuid.uuid4(),
        credential_status="active",
        credential_type="desktop_client",
        subject_key="desktop-ready",
    )
    access_delivery_channel = SimpleNamespace(
        id=uuid.uuid4(),
        channel_status="active",
        channel_subject_ref="desktop-ready",
        device_credential_id=device_credential.id,
    )

    use_case._get_subscription = AsyncMock(return_value=subscription)
    use_case._get_selected_grant = AsyncMock(return_value=SimpleNamespace(id=subscription.entitlement_grant_id))
    use_case._ensure_subscription_service_identity = AsyncMock(return_value=service_identity)
    use_case._ensure_provisioning_profile = AsyncMock(return_value=provisioning_profile)
    use_case._ensure_device_credential = AsyncMock(return_value=device_credential)
    use_case._ensure_access_delivery_channel = AsyncMock(return_value=access_delivery_channel)
    use_case._repo = SimpleNamespace(get_device_credential_by_id=AsyncMock())

    result = await use_case.get_service_state(
        customer_account_id=uuid.uuid4(),
        auth_realm_id=uuid.uuid4(),
        subscription_key=subscription.subscription_key,
        channel_type="shared_client",
        credential_type="desktop_client",
        credential_subject_key="desktop-ready",
        remnawave_client=SimpleNamespace(),
    )

    use_case._ensure_device_credential.assert_awaited_once_with(
        service_identity=service_identity,
        provisioning_profile=provisioning_profile,
        credential_type="desktop_client",
        credential_subject_key="desktop-ready",
    )
    channel_call = use_case._ensure_access_delivery_channel.await_args.kwargs
    assert channel_call["channel_subject_ref"] == "desktop-ready"
    assert channel_call["device_credential"] is device_credential
    assert result.device_credential is device_credential
    assert result.access_delivery_channel is access_delivery_channel
    assert result.resolved_channel_subject_ref == "desktop-ready"


@pytest.mark.asyncio
async def test_selected_subscription_existing_spb_de_identity_without_client_rejects_stale_smart_context(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    customer_account_id = uuid.uuid4()
    auth_realm_id = uuid.uuid4()
    service_identity_id = uuid.uuid4()
    smart_external_squad_uuid = str(uuid.uuid4())
    smart_internal_squad_uuid = str(uuid.uuid4())
    spb_de_external_squad_uuid = str(uuid.uuid4())
    spb_de_internal_squad_uuid = str(uuid.uuid4())
    _enable_spb_de_data_plane(monkeypatch)
    monkeypatch.setattr(settings, "remnawave_spb_de_exceptions_external_squad_uuid", spb_de_external_squad_uuid)
    monkeypatch.setattr(settings, "remnawave_spb_de_exceptions_internal_squad_uuid", spb_de_internal_squad_uuid)
    monkeypatch.setattr(settings, "remnawave_spb_de_exceptions_bridge_squad_uuid", str(uuid.uuid4()))
    monkeypatch.setattr(settings, "remnawave_spb_de_exceptions_plan_codes", "premium_spb_de_exceptions")
    monkeypatch.setattr(settings, "remnawave_smart_ru_external_squad_uuid", smart_external_squad_uuid)
    monkeypatch.setattr(settings, "remnawave_smart_ru_internal_squad_uuid", smart_internal_squad_uuid)
    monkeypatch.setattr(settings, "remnawave_smart_ru_plan_codes", "premium_smart_ru")

    item = _subscription_summary()
    item.plan_code = "premium_spb_de_exceptions"
    item.display_name = "Premium SPB + DE Exceptions"
    existing_identity = SimpleNamespace(
        id=service_identity_id,
        provider_subject_ref=str(uuid.uuid4()),
        identity_scope="subscription",
        subscription_key=item.subscription_key,
        service_context={
            "remnawave_routing_product": "premium_smart_ru",
            "remnawave_external_squad_uuid": smart_external_squad_uuid,
            "remnawave_internal_squad_uuids": [smart_internal_squad_uuid],
        },
    )
    grant = SimpleNamespace(
        service_identity_id=None,
        customer_account_id=customer_account_id,
        auth_realm_id=auth_realm_id,
    )
    session = SimpleNamespace(flush=AsyncMock())
    use_case = CustomerSubscriptionServiceAccessUseCase(session)
    use_case._repo = SimpleNamespace(
        get_service_identity_by_subscription_key=AsyncMock(return_value=existing_identity),
    )

    with pytest.raises(HTTPException) as exc_info:
        await use_case._ensure_subscription_service_identity(
            item=item,
            grant=grant,
            provider_name="remnawave",
            remnawave_client=None,
        )

    assert exc_info.value.status_code == 409
    assert exc_info.value.detail == (
        "Selected subscription VPN identity requires Premium SPB/DE Exceptions routing configuration"
    )
    assert grant.service_identity_id is None
    session.flush.assert_not_awaited()


@pytest.mark.asyncio
async def test_selected_subscription_existing_spb_de_identity_without_grant_rejects_stale_smart_context(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    customer_account_id = uuid.uuid4()
    auth_realm_id = uuid.uuid4()
    smart_external_squad_uuid = str(uuid.uuid4())
    smart_internal_squad_uuid = str(uuid.uuid4())
    spb_de_external_squad_uuid = str(uuid.uuid4())
    spb_de_internal_squad_uuid = str(uuid.uuid4())
    _enable_spb_de_data_plane(monkeypatch)
    monkeypatch.setattr(settings, "remnawave_spb_de_exceptions_external_squad_uuid", spb_de_external_squad_uuid)
    monkeypatch.setattr(settings, "remnawave_spb_de_exceptions_internal_squad_uuid", spb_de_internal_squad_uuid)
    monkeypatch.setattr(settings, "remnawave_spb_de_exceptions_bridge_squad_uuid", str(uuid.uuid4()))
    monkeypatch.setattr(settings, "remnawave_spb_de_exceptions_plan_codes", "premium_spb_de_exceptions")
    monkeypatch.setattr(settings, "remnawave_smart_ru_external_squad_uuid", smart_external_squad_uuid)
    monkeypatch.setattr(settings, "remnawave_smart_ru_internal_squad_uuid", smart_internal_squad_uuid)
    monkeypatch.setattr(settings, "remnawave_smart_ru_plan_codes", "premium_smart_ru")

    item = _subscription_summary()
    item.plan_code = "premium_spb_de_exceptions"
    item.display_name = "Premium SPB + DE Exceptions"
    existing_identity = SimpleNamespace(
        id=uuid.uuid4(),
        provider_subject_ref=str(uuid.uuid4()),
        identity_scope="subscription",
        subscription_key=item.subscription_key,
        service_context={
            "remnawave_routing_product": "premium_smart_ru",
            "remnawave_external_squad_uuid": smart_external_squad_uuid,
            "remnawave_internal_squad_uuids": [smart_internal_squad_uuid],
        },
    )
    session = SimpleNamespace(flush=AsyncMock())
    use_case = CustomerSubscriptionServiceAccessUseCase(session)
    use_case._customer_id = AsyncMock(return_value=customer_account_id)
    use_case._auth_realm_id = AsyncMock(return_value=auth_realm_id)
    use_case._repo = SimpleNamespace(
        get_service_identity_by_subscription_key=AsyncMock(return_value=existing_identity),
    )

    with pytest.raises(HTTPException) as exc_info:
        await use_case._ensure_subscription_service_identity(
            item=item,
            grant=None,
            provider_name="remnawave",
            remnawave_client=SimpleNamespace(),
        )

    assert exc_info.value.status_code == 409
    assert exc_info.value.detail == (
        "Selected subscription VPN identity requires Premium SPB/DE Exceptions routing configuration"
    )
    session.flush.assert_not_awaited()


@pytest.mark.asyncio
async def test_selected_subscription_existing_spb_de_identity_without_client_reuses_matching_context(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    customer_account_id = uuid.uuid4()
    auth_realm_id = uuid.uuid4()
    service_identity_id = uuid.uuid4()
    spb_de_external_squad_uuid = str(uuid.uuid4())
    spb_de_internal_squad_uuid = str(uuid.uuid4())
    _enable_spb_de_data_plane(monkeypatch)
    monkeypatch.setattr(settings, "remnawave_spb_de_exceptions_external_squad_uuid", spb_de_external_squad_uuid)
    monkeypatch.setattr(settings, "remnawave_spb_de_exceptions_internal_squad_uuid", spb_de_internal_squad_uuid)
    monkeypatch.setattr(settings, "remnawave_spb_de_exceptions_bridge_squad_uuid", str(uuid.uuid4()))
    monkeypatch.setattr(settings, "remnawave_spb_de_exceptions_plan_codes", "premium_spb_de_exceptions")
    monkeypatch.setattr(settings, "remnawave_smart_ru_plan_codes", "premium_smart_ru")

    item = _subscription_summary()
    item.plan_code = "premium_spb_de_exceptions"
    item.display_name = "Premium SPB + DE Exceptions"
    existing_identity = SimpleNamespace(
        id=service_identity_id,
        provider_subject_ref=str(uuid.uuid4()),
        identity_scope="subscription",
        subscription_key=item.subscription_key,
        service_context=_spb_de_context(spb_de_external_squad_uuid, spb_de_internal_squad_uuid),
    )
    grant = SimpleNamespace(
        service_identity_id=None,
        customer_account_id=customer_account_id,
        auth_realm_id=auth_realm_id,
    )
    session = SimpleNamespace(flush=AsyncMock())
    use_case = CustomerSubscriptionServiceAccessUseCase(session)
    use_case._repo = SimpleNamespace(
        get_service_identity_by_subscription_key=AsyncMock(return_value=existing_identity),
    )

    result = await use_case._ensure_subscription_service_identity(
        item=item,
        grant=grant,
        provider_name="remnawave",
        remnawave_client=None,
    )

    assert result is existing_identity
    assert grant.service_identity_id == service_identity_id
    session.flush.assert_awaited_once()


@pytest.mark.asyncio
async def test_selected_subscription_provisioning_acquires_postgres_lock_before_lookup() -> None:
    customer_account_id = uuid.uuid4()
    auth_realm_id = uuid.uuid4()
    item = _subscription_summary()
    item.kind = "paid"
    grant = SimpleNamespace(
        service_identity_id=None,
        customer_account_id=customer_account_id,
        auth_realm_id=auth_realm_id,
    )
    session = SimpleNamespace(
        get_bind=lambda: SimpleNamespace(dialect=SimpleNamespace(name="postgresql")),
        execute=AsyncMock(),
        flush=AsyncMock(),
    )

    async def _get_identity_after_lock(**kwargs):  # noqa: ARG001
        session.execute.assert_awaited_once()
        return None

    use_case = CustomerSubscriptionServiceAccessUseCase(session)
    use_case._repo = SimpleNamespace(
        get_service_identity_by_subscription_key=AsyncMock(side_effect=_get_identity_after_lock),
    )

    with pytest.raises(HTTPException) as exc_info:
        await use_case._ensure_subscription_service_identity(
            item=item,
            grant=grant,
            provider_name="remnawave",
            remnawave_client=None,
        )

    statement, params = session.execute.await_args.args
    assert exc_info.value.status_code == 409
    assert "pg_advisory_xact_lock" in str(statement)
    assert isinstance(params["lock_id"], int)
    assert -(2**63) <= params["lock_id"] < 2**63
    use_case._repo.get_service_identity_by_subscription_key.assert_awaited_once()


@pytest.mark.asyncio
async def test_selected_subscription_lazy_provisioning_uses_smart_ru_squads(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}
    customer_account_id = uuid.uuid4()
    auth_realm_id = uuid.uuid4()
    service_identity_id = uuid.uuid4()
    created_remnawave_uuid = uuid.uuid4()
    smart_external_squad_uuid = str(uuid.uuid4())
    smart_internal_squad_uuid = str(uuid.uuid4())
    customer = SimpleNamespace(email="smart-user@example.test", remnawave_uuid=None, subscription_url=None)

    class FakeRemnawaveUserGateway:
        def __init__(self, client) -> None:
            captured["remnawave_client"] = client

        async def create(self, username: str, **kwargs):
            captured["remnawave_username"] = username
            captured["remnawave_payload"] = kwargs
            return SimpleNamespace(
                uuid=created_remnawave_uuid,
                subscription_url="https://subscription.example.local/sub/redacted-smart",
            )

    class FakeCreateServiceIdentityUseCase:
        def __init__(self, session) -> None:
            captured["identity_session"] = session

        async def execute(self, **kwargs):
            captured["identity_kwargs"] = kwargs
            return SimpleNamespace(
                service_identity=SimpleNamespace(
                    id=service_identity_id,
                    service_key="svc-smart-ready",
                    provider_subject_ref=kwargs["provider_subject_ref"],
                    service_context=kwargs["service_context"],
                )
            )

    monkeypatch.setattr(settings, "remnawave_smart_ru_external_squad_uuid", smart_external_squad_uuid)
    monkeypatch.setattr(settings, "remnawave_smart_ru_internal_squad_uuid", smart_internal_squad_uuid)
    monkeypatch.setattr(settings, "remnawave_smart_ru_plan_codes", "premium_smart_ru")
    monkeypatch.setattr(settings, "remnawave_lifetime_expiry_mode", "sentinel")
    monkeypatch.setattr(settings, "remnawave_lifetime_expire_at", "2099-12-31T23:59:59Z")
    monkeypatch.setattr(service_access_module, "RemnawaveUserGateway", FakeRemnawaveUserGateway)
    monkeypatch.setattr(service_access_module, "CreateServiceIdentityUseCase", FakeCreateServiceIdentityUseCase)

    session = SimpleNamespace(
        get=AsyncMock(return_value=customer),
        flush=AsyncMock(),
    )
    use_case = CustomerSubscriptionServiceAccessUseCase(session)
    use_case._ensure_provisioning_profile = AsyncMock()
    use_case._store_subscription_url = AsyncMock()
    item = _subscription_summary()
    item.plan_code = "premium_smart_ru"
    item.display_name = "Premium Smart RU"
    item.effective_entitlements = {"device_limit": 5}
    item.expires_at = None
    grant = SimpleNamespace(
        id=item.entitlement_grant_id,
        customer_account_id=customer_account_id,
        auth_realm_id=auth_realm_id,
        source_order_id=uuid.uuid4(),
        origin_storefront_id=None,
        service_identity_id=None,
        grant_snapshot={"duration_mode": "lifetime", "lifetime": True},
    )

    service_identity = await use_case._ensure_grant_service_identity(
        item=item,
        grant=grant,
        provider_name="remnawave",
        remnawave_client=SimpleNamespace(),
        existing=None,
    )

    payload = captured["remnawave_payload"]
    assert payload["external_squad_uuid"] == smart_external_squad_uuid
    assert payload["active_internal_squads"] == [smart_internal_squad_uuid]
    assert payload["hwid_device_limit"] == 5
    assert payload["expire_at"] == "2099-12-31T23:59:59Z"
    assert payload["lifetime_expiry_mode"] == "sentinel"
    assert captured["identity_kwargs"]["service_context"]["plan_code"] == "premium_smart_ru"
    assert captured["identity_kwargs"]["service_context"]["duration_mode"] == "lifetime"
    assert captured["identity_kwargs"]["service_context"]["lifetime"] is True
    assert grant.service_identity_id == service_identity_id
    assert customer.remnawave_uuid == str(created_remnawave_uuid)
    assert customer.subscription_url == "https://subscription.example.local/sub/redacted-smart"
    assert service_identity.id == service_identity_id
    session.flush.assert_awaited_once()


@pytest.mark.asyncio
async def test_selected_subscription_recreates_stale_remnawave_identity(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}
    customer_account_id = uuid.uuid4()
    auth_realm_id = uuid.uuid4()
    service_identity_id = uuid.uuid4()
    stale_remnawave_uuid = uuid.uuid4()
    recreated_remnawave_uuid = uuid.uuid4()
    smart_external_squad_uuid = str(uuid.uuid4())
    smart_internal_squad_uuid = str(uuid.uuid4())
    old_subscription_url = "https://subscription.example.local/sub/old-stale"
    new_subscription_url = "https://subscription.example.local/sub/new-ready"
    customer = SimpleNamespace(
        email="smart-user@example.test",
        remnawave_uuid=str(stale_remnawave_uuid),
        subscription_url=old_subscription_url,
    )
    existing_identity = SimpleNamespace(
        id=service_identity_id,
        provider_subject_ref=str(stale_remnawave_uuid),
        identity_scope="subscription",
        subscription_key=None,
        identity_status="active",
        service_context={"subscription_url": old_subscription_url},
    )

    class FakeRemnawaveUserGateway:
        def __init__(self, client) -> None:
            captured["remnawave_client"] = client

        async def get_by_ref(self, user_ref: RemnawaveUserRef):
            captured["looked_up_remnawave_uuid"] = user_ref.legacy_uuid
            return None

        async def create(self, username: str, **kwargs):
            captured["remnawave_username"] = username
            captured["remnawave_payload"] = kwargs
            return SimpleNamespace(
                uuid=recreated_remnawave_uuid,
                subscription_url=new_subscription_url,
            )

    monkeypatch.setattr(settings, "remnawave_smart_ru_external_squad_uuid", smart_external_squad_uuid)
    monkeypatch.setattr(settings, "remnawave_smart_ru_internal_squad_uuid", smart_internal_squad_uuid)
    monkeypatch.setattr(settings, "remnawave_smart_ru_plan_codes", "premium_smart_ru")
    monkeypatch.setattr(service_access_module, "RemnawaveUserGateway", FakeRemnawaveUserGateway)

    session = SimpleNamespace(
        get=AsyncMock(return_value=customer),
        flush=AsyncMock(),
    )
    use_case = CustomerSubscriptionServiceAccessUseCase(session)
    use_case._ensure_provisioning_profile = AsyncMock()
    use_case._store_subscription_url = AsyncMock()
    item = _subscription_summary()
    item.plan_code = "premium_smart_ru"
    item.display_name = "Premium Smart RU"
    item.effective_entitlements = {"device_limit": 5}
    existing_identity.subscription_key = item.subscription_key
    grant = SimpleNamespace(
        id=item.entitlement_grant_id,
        customer_account_id=customer_account_id,
        auth_realm_id=auth_realm_id,
        source_order_id=uuid.uuid4(),
        origin_storefront_id=None,
        service_identity_id=service_identity_id,
        grant_snapshot={},
    )

    service_identity = await use_case._ensure_grant_service_identity(
        item=item,
        grant=grant,
        provider_name="remnawave",
        remnawave_client=SimpleNamespace(),
        existing=existing_identity,
    )

    assert captured["looked_up_remnawave_uuid"] == stale_remnawave_uuid
    assert captured["remnawave_payload"]["external_squad_uuid"] == smart_external_squad_uuid
    assert captured["remnawave_payload"]["active_internal_squads"] == [smart_internal_squad_uuid]
    assert existing_identity.provider_subject_ref == str(recreated_remnawave_uuid)
    assert existing_identity.identity_status == "active"
    assert existing_identity.service_context["subscription_url"] == new_subscription_url
    assert customer.remnawave_uuid == str(recreated_remnawave_uuid)
    assert customer.subscription_url == new_subscription_url
    assert grant.service_identity_id == service_identity_id
    assert service_identity is existing_identity
    use_case._store_subscription_url.assert_awaited_once_with(
        service_identity=existing_identity,
        subscription_url=new_subscription_url,
    )
    session.flush.assert_awaited_once()


@pytest.mark.asyncio
async def test_selected_subscription_config_recreates_stale_existing_identity(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}
    customer_account_id = uuid.uuid4()
    auth_realm_id = uuid.uuid4()
    service_identity_id = uuid.uuid4()
    stale_remnawave_uuid = uuid.uuid4()
    recreated_remnawave_uuid = uuid.uuid4()
    smart_external_squad_uuid = str(uuid.uuid4())
    smart_internal_squad_uuid = str(uuid.uuid4())
    new_subscription_url = "https://subscription.example.local/sub/new-ready"
    customer = SimpleNamespace(
        email="smart-user@example.test",
        remnawave_uuid=str(stale_remnawave_uuid),
        subscription_url="https://subscription.example.local/sub/old-stale",
    )
    item = _subscription_summary()
    item.plan_code = "premium_smart_ru"
    item.display_name = "Premium Smart RU"
    item.effective_entitlements = {"device_limit": 5}
    existing_identity = SimpleNamespace(
        id=service_identity_id,
        service_key="svc-stale-existing",
        provider_subject_ref=str(stale_remnawave_uuid),
        identity_scope="subscription",
        subscription_key=item.subscription_key,
        identity_status="active",
        service_context={"subscription_url": customer.subscription_url},
    )
    grant = SimpleNamespace(
        id=item.entitlement_grant_id,
        customer_account_id=customer_account_id,
        auth_realm_id=auth_realm_id,
        source_order_id=uuid.uuid4(),
        origin_storefront_id=None,
        service_identity_id=service_identity_id,
        grant_snapshot={},
    )

    class FakeRemnawaveUserGateway:
        def __init__(self, client) -> None:
            captured["remnawave_client"] = client

        async def get_by_ref(self, user_ref: RemnawaveUserRef):
            captured["looked_up_remnawave_uuid"] = user_ref.legacy_uuid
            return None

        async def create(self, username: str, **kwargs):
            captured["remnawave_username"] = username
            captured["remnawave_payload"] = kwargs
            return SimpleNamespace(
                uuid=recreated_remnawave_uuid,
                subscription_url=new_subscription_url,
            )

    class FakeGenerateConfigUseCase:
        def __init__(self, client) -> None:
            captured["config_client"] = client

        async def execute(self, user_ref: RemnawaveUserRef, *, plan_code: str | None = None, user_segments=None):
            captured["config_user_ref"] = user_ref
            captured["config_plan_code"] = plan_code
            captured["config_user_segments"] = user_segments
            return {"subscription_url": new_subscription_url}

    monkeypatch.setattr(settings, "remnawave_smart_ru_external_squad_uuid", smart_external_squad_uuid)
    monkeypatch.setattr(settings, "remnawave_smart_ru_internal_squad_uuid", smart_internal_squad_uuid)
    monkeypatch.setattr(settings, "remnawave_smart_ru_plan_codes", "premium_smart_ru")
    monkeypatch.setattr(service_access_module, "RemnawaveUserGateway", FakeRemnawaveUserGateway)
    monkeypatch.setattr(service_access_module, "GenerateConfigUseCase", FakeGenerateConfigUseCase)

    session = SimpleNamespace(
        get=AsyncMock(return_value=customer),
        flush=AsyncMock(),
    )
    use_case = CustomerSubscriptionServiceAccessUseCase(session)
    use_case._get_subscription = AsyncMock(return_value=item)
    use_case._get_selected_grant = AsyncMock(return_value=grant)
    use_case._repo = SimpleNamespace(
        get_service_identity_by_subscription_key=AsyncMock(return_value=existing_identity),
        get_device_credential_by_id=AsyncMock(),
    )
    use_case._ensure_provisioning_profile = AsyncMock(return_value=SimpleNamespace(id=uuid.uuid4()))
    use_case._ensure_access_delivery_channel = AsyncMock(
        return_value=SimpleNamespace(
            id=uuid.uuid4(),
            channel_subject_ref="svc-stale-existing",
            device_credential_id=None,
        )
    )
    use_case._store_subscription_url = AsyncMock()

    config = await use_case.get_config(
        customer_account_id=customer_account_id,
        auth_realm_id=auth_realm_id,
        subscription_key=item.subscription_key,
        remnawave_client=SimpleNamespace(),
    )

    assert config["subscription_url"] == new_subscription_url
    assert captured["looked_up_remnawave_uuid"] == stale_remnawave_uuid
    assert captured["config_user_ref"] == RemnawaveUserRef(id=42, legacy_uuid=recreated_remnawave_uuid)
    assert captured["config_plan_code"] == "premium_smart_ru"
    assert captured["config_user_segments"] is None
    assert existing_identity.provider_subject_ref == str(recreated_remnawave_uuid)
    assert existing_identity.service_context["subscription_url"] == new_subscription_url
    assert customer.remnawave_uuid == str(recreated_remnawave_uuid)
    assert customer.subscription_url == new_subscription_url
    assert grant.service_identity_id == service_identity_id
    assert use_case._store_subscription_url.await_count == 2


@pytest.mark.asyncio
async def test_selected_subscription_lazy_provisioning_fails_closed_when_smart_ru_squads_are_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    customer_account_id = uuid.uuid4()
    auth_realm_id = uuid.uuid4()
    monkeypatch.setattr(settings, "remnawave_smart_ru_external_squad_uuid", "")
    monkeypatch.setattr(settings, "remnawave_smart_ru_internal_squad_uuid", str(uuid.uuid4()))
    monkeypatch.setattr(settings, "remnawave_smart_ru_plan_codes", "premium_smart_ru")

    session = SimpleNamespace(
        get=AsyncMock(return_value=SimpleNamespace(email="smart-user@example.test")),
        flush=AsyncMock(),
    )
    use_case = CustomerSubscriptionServiceAccessUseCase(session)
    item = _subscription_summary()
    item.plan_code = "premium_smart_ru"
    item.display_name = "Premium Smart RU"
    grant = SimpleNamespace(
        id=item.entitlement_grant_id,
        customer_account_id=customer_account_id,
        auth_realm_id=auth_realm_id,
        source_order_id=uuid.uuid4(),
        origin_storefront_id=None,
        service_identity_id=None,
    )

    with pytest.raises(HTTPException) as exc_info:
        await use_case._ensure_grant_service_identity(
            item=item,
            grant=grant,
            provider_name="remnawave",
            remnawave_client=SimpleNamespace(),
            existing=None,
        )

    assert exc_info.value.status_code == 409
    assert exc_info.value.detail == "Selected subscription VPN identity requires Premium Smart RU routing configuration"
    session.flush.assert_not_awaited()


@pytest.mark.asyncio
async def test_selected_subscription_lazy_provisioning_uses_spb_de_exceptions_squads(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}
    customer_account_id = uuid.uuid4()
    auth_realm_id = uuid.uuid4()
    service_identity_id = uuid.uuid4()
    created_remnawave_uuid = uuid.uuid4()
    spb_de_external_squad_uuid = str(uuid.uuid4())
    spb_de_internal_squad_uuid = str(uuid.uuid4())
    spb_de_bridge_squad_uuid = str(uuid.uuid4())
    smart_external_squad_uuid = str(uuid.uuid4())
    smart_internal_squad_uuid = str(uuid.uuid4())
    customer = SimpleNamespace(email="spb-de-user@example.test", remnawave_uuid=None, subscription_url=None)
    _enable_spb_de_data_plane(monkeypatch)

    class FakeRemnawaveUserGateway:
        def __init__(self, client) -> None:
            captured["remnawave_client"] = client

        async def create(self, username: str, **kwargs):
            captured["remnawave_username"] = username
            captured["remnawave_payload"] = kwargs
            return SimpleNamespace(
                uuid=created_remnawave_uuid,
                subscription_url="https://subscription.example.local/sub/redacted-spb-de",
            )

    class FakeCreateServiceIdentityUseCase:
        def __init__(self, session) -> None:
            captured["identity_session"] = session

        async def execute(self, **kwargs):
            captured["identity_kwargs"] = kwargs
            return SimpleNamespace(
                service_identity=SimpleNamespace(
                    id=service_identity_id,
                    service_key="svc-spb-de-ready",
                    provider_subject_ref=kwargs["provider_subject_ref"],
                    service_context=kwargs["service_context"],
                )
            )

    monkeypatch.setattr(settings, "remnawave_spb_de_exceptions_external_squad_uuid", spb_de_external_squad_uuid)
    monkeypatch.setattr(settings, "remnawave_spb_de_exceptions_internal_squad_uuid", spb_de_internal_squad_uuid)
    monkeypatch.setattr(settings, "remnawave_spb_de_exceptions_bridge_squad_uuid", spb_de_bridge_squad_uuid)
    monkeypatch.setattr(settings, "remnawave_spb_de_exceptions_plan_codes", "premium_spb_de_exceptions")
    monkeypatch.setattr(
        settings,
        "remnawave_spb_de_exceptions_profile_name",
        "S1 SPB DE Exceptions",
    )
    monkeypatch.setattr(settings, "remnawave_spb_de_exceptions_policy_version", "premium_spb_de_exceptions.v1")
    monkeypatch.setattr(settings, "remnawave_smart_ru_external_squad_uuid", smart_external_squad_uuid)
    monkeypatch.setattr(settings, "remnawave_smart_ru_internal_squad_uuid", smart_internal_squad_uuid)
    monkeypatch.setattr(settings, "remnawave_smart_ru_plan_codes", "premium_smart_ru")
    monkeypatch.setattr(service_access_module, "RemnawaveUserGateway", FakeRemnawaveUserGateway)
    monkeypatch.setattr(service_access_module, "CreateServiceIdentityUseCase", FakeCreateServiceIdentityUseCase)

    session = SimpleNamespace(
        get=AsyncMock(return_value=customer),
        flush=AsyncMock(),
    )
    use_case = CustomerSubscriptionServiceAccessUseCase(session)
    use_case._ensure_provisioning_profile = AsyncMock()
    use_case._store_subscription_url = AsyncMock()
    item = _subscription_summary()
    item.plan_code = "premium_spb_de_exceptions"
    item.display_name = "Premium SPB + DE Exceptions"
    item.effective_entitlements = {"device_limit": 5}
    grant = SimpleNamespace(
        id=item.entitlement_grant_id,
        customer_account_id=customer_account_id,
        auth_realm_id=auth_realm_id,
        source_order_id=uuid.uuid4(),
        origin_storefront_id=None,
        service_identity_id=None,
        grant_snapshot={},
    )

    service_identity = await use_case._ensure_grant_service_identity(
        item=item,
        grant=grant,
        provider_name="remnawave",
        remnawave_client=SimpleNamespace(),
        existing=None,
    )

    payload = captured["remnawave_payload"]
    assert payload["external_squad_uuid"] == spb_de_external_squad_uuid
    assert payload["active_internal_squads"] == [spb_de_internal_squad_uuid]
    assert payload["external_squad_uuid"] != smart_external_squad_uuid
    assert smart_internal_squad_uuid not in payload["active_internal_squads"]
    assert payload["external_squad_uuid"] != spb_de_bridge_squad_uuid
    assert spb_de_bridge_squad_uuid not in payload["active_internal_squads"]
    assert payload["trafficLimitStrategy"] == service_access_module.STAGE1_PAID_TRAFFIC_LIMIT_STRATEGY
    assert payload["hwid_device_limit"] == 5
    assert set(payload).isdisjoint({"bridge_user", "bridge_password", "bridge_inbound_tag", "bridge_outbound_tag"})
    assert "CYBERVPN_SPB_DE_BRIDGE" not in str(payload)
    assert "DE_EXCEPTIONS_BRIDGE" not in str(payload)

    context = captured["identity_kwargs"]["service_context"]
    assert context["plan_code"] == "premium_spb_de_exceptions"
    assert context["subscription_key"] == item.subscription_key
    assert context["subscription_url"] == "https://subscription.example.local/sub/redacted-spb-de"
    assert context | _spb_de_context(spb_de_external_squad_uuid, spb_de_internal_squad_uuid) == context
    assert spb_de_bridge_squad_uuid not in str(context)
    assert grant.service_identity_id == service_identity_id
    assert customer.remnawave_uuid == str(created_remnawave_uuid)
    assert customer.subscription_url == "https://subscription.example.local/sub/redacted-spb-de"
    assert service_identity.id == service_identity_id
    session.flush.assert_awaited_once()


@pytest.mark.asyncio
@pytest.mark.parametrize("readiness_state", ["disabled", "stale_manifest"])
async def test_selected_subscription_task2_readiness_gate_blocks_new_provisioning_before_provider_mutation(
    monkeypatch: pytest.MonkeyPatch,
    readiness_state: str,
) -> None:
    customer_account_id = uuid.uuid4()
    auth_realm_id = uuid.uuid4()
    customer = SimpleNamespace(email="spb-de-user@example.test", remnawave_uuid=None, subscription_url=None)
    monkeypatch.setattr(settings, "remnawave_spb_de_exceptions_external_squad_uuid", str(uuid.uuid4()))
    monkeypatch.setattr(settings, "remnawave_spb_de_exceptions_internal_squad_uuid", str(uuid.uuid4()))
    monkeypatch.setattr(settings, "remnawave_spb_de_exceptions_bridge_squad_uuid", str(uuid.uuid4()))
    monkeypatch.setattr(settings, "remnawave_spb_de_exceptions_plan_codes", "premium_spb_de_exceptions")
    if readiness_state == "stale_manifest":
        enable_spb_de_readiness(monkeypatch)
        stale_pointer = manifest_pointer_json(manifest_sha256="c" * 64)
        monkeypatch.setattr(settings, "remnawave_spb_de_exceptions_readiness_active_pointer", stale_pointer)
        monkeypatch.setattr(settings, "remnawave_spb_de_exceptions_readiness_lkg_pointer", stale_pointer)
    else:
        monkeypatch.setattr(settings, "remnawave_spb_de_exceptions_data_plane_ready", False)
    monkeypatch.setattr(settings, "remnawave_smart_ru_plan_codes", "premium_smart_ru")

    class FailIfConstructedRemnawaveUserGateway:
        def __init__(self, client) -> None:  # noqa: ARG002
            raise AssertionError("readiness gate must fail before Remnawave gateway construction")

    monkeypatch.setattr(service_access_module, "RemnawaveUserGateway", FailIfConstructedRemnawaveUserGateway)
    session = SimpleNamespace(
        get=AsyncMock(return_value=customer),
        flush=AsyncMock(),
    )
    use_case = CustomerSubscriptionServiceAccessUseCase(session)
    use_case._ensure_provisioning_profile = AsyncMock()
    use_case._store_subscription_url = AsyncMock()
    item = _subscription_summary()
    item.plan_code = "premium_spb_de_exceptions"
    item.display_name = "Premium SPB + DE Exceptions"
    grant = SimpleNamespace(
        id=item.entitlement_grant_id,
        customer_account_id=customer_account_id,
        auth_realm_id=auth_realm_id,
        source_order_id=uuid.uuid4(),
        origin_storefront_id=None,
        service_identity_id=None,
    )

    for _ in range(2):
        with pytest.raises(HTTPException) as exc_info:
            await use_case._ensure_grant_service_identity(
                item=item,
                grant=grant,
                provider_name="remnawave",
                remnawave_client=SimpleNamespace(),
                existing=None,
            )

        assert exc_info.value.status_code == 409
        assert exc_info.value.detail == (
            "Selected subscription VPN identity requires Premium SPB/DE Exceptions routing configuration"
        )
        assert grant.service_identity_id is None
        assert customer.remnawave_uuid is None
        assert customer.subscription_url is None

    session.get.assert_not_awaited()
    session.flush.assert_not_awaited()
    use_case._ensure_provisioning_profile.assert_not_awaited()
    use_case._store_subscription_url.assert_not_awaited()


@pytest.mark.asyncio
async def test_selected_subscription_task2_readiness_gate_blocks_stale_identity_repair_before_provider_mutation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    customer_account_id = uuid.uuid4()
    auth_realm_id = uuid.uuid4()
    service_identity_id = uuid.uuid4()
    existing_remnawave_uuid = uuid.uuid4()
    stale_context = {
        "remnawave_routing_product": "premium_smart_ru",
        "remnawave_external_squad_uuid": str(uuid.uuid4()),
        "remnawave_internal_squad_uuids": [str(uuid.uuid4())],
        "remnawave_bridge_squad_uuid": str(uuid.uuid4()),
        "bridge_password": "redacted-bridge-secret",
        "subscription_url": "https://subscription.example.local/sub/old-smart",
    }
    customer = SimpleNamespace(
        email="spb-de-user@example.test",
        remnawave_uuid=str(existing_remnawave_uuid),
        subscription_url=stale_context["subscription_url"],
    )
    monkeypatch.setattr(settings, "remnawave_spb_de_exceptions_external_squad_uuid", str(uuid.uuid4()))
    monkeypatch.setattr(settings, "remnawave_spb_de_exceptions_internal_squad_uuid", str(uuid.uuid4()))
    monkeypatch.setattr(settings, "remnawave_spb_de_exceptions_bridge_squad_uuid", str(uuid.uuid4()))
    monkeypatch.setattr(settings, "remnawave_spb_de_exceptions_plan_codes", "premium_spb_de_exceptions")
    monkeypatch.setattr(settings, "remnawave_spb_de_exceptions_data_plane_ready", False)
    monkeypatch.setattr(settings, "remnawave_smart_ru_plan_codes", "premium_smart_ru")

    class FailIfConstructedRemnawaveUserGateway:
        def __init__(self, client) -> None:  # noqa: ARG002
            raise AssertionError("readiness gate must fail before stale Remnawave identity repair")

    monkeypatch.setattr(service_access_module, "RemnawaveUserGateway", FailIfConstructedRemnawaveUserGateway)
    session = SimpleNamespace(
        get=AsyncMock(return_value=customer),
        flush=AsyncMock(),
    )
    use_case = CustomerSubscriptionServiceAccessUseCase(session)
    use_case._ensure_provisioning_profile = AsyncMock()
    use_case._store_subscription_url = AsyncMock()
    item = _subscription_summary()
    item.plan_code = "premium_spb_de_exceptions"
    item.display_name = "Premium SPB + DE Exceptions"
    existing_identity = SimpleNamespace(
        id=service_identity_id,
        provider_subject_ref=str(existing_remnawave_uuid),
        identity_scope="subscription",
        subscription_key=item.subscription_key,
        identity_status="active",
        service_context=dict(stale_context),
    )
    grant = SimpleNamespace(
        id=item.entitlement_grant_id,
        customer_account_id=customer_account_id,
        auth_realm_id=auth_realm_id,
        source_order_id=uuid.uuid4(),
        origin_storefront_id=None,
        service_identity_id=service_identity_id,
        grant_snapshot={},
    )

    with pytest.raises(HTTPException) as exc_info:
        await use_case._ensure_grant_service_identity(
            item=item,
            grant=grant,
            provider_name="remnawave",
            remnawave_client=SimpleNamespace(),
            existing=existing_identity,
        )

    assert exc_info.value.status_code == 409
    assert exc_info.value.detail == (
        "Selected subscription VPN identity requires Premium SPB/DE Exceptions routing configuration"
    )
    assert grant.service_identity_id == service_identity_id
    assert existing_identity.provider_subject_ref == str(existing_remnawave_uuid)
    assert existing_identity.service_context == stale_context
    assert customer.remnawave_uuid == str(existing_remnawave_uuid)
    assert customer.subscription_url == stale_context["subscription_url"]
    session.get.assert_not_awaited()
    session.flush.assert_not_awaited()
    use_case._ensure_provisioning_profile.assert_not_awaited()
    use_case._store_subscription_url.assert_not_awaited()


@pytest.mark.asyncio
async def test_selected_subscription_lazy_provisioning_fails_closed_when_spb_de_settings_are_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    customer_account_id = uuid.uuid4()
    auth_realm_id = uuid.uuid4()
    _enable_spb_de_data_plane(monkeypatch)
    monkeypatch.setattr(settings, "remnawave_spb_de_exceptions_external_squad_uuid", "")
    monkeypatch.setattr(settings, "remnawave_spb_de_exceptions_internal_squad_uuid", str(uuid.uuid4()))
    monkeypatch.setattr(settings, "remnawave_spb_de_exceptions_bridge_squad_uuid", str(uuid.uuid4()))
    monkeypatch.setattr(settings, "remnawave_spb_de_exceptions_plan_codes", "premium_spb_de_exceptions")
    monkeypatch.setattr(settings, "remnawave_smart_ru_plan_codes", "premium_smart_ru")

    session = SimpleNamespace(
        get=AsyncMock(return_value=SimpleNamespace(email="spb-de-user@example.test")),
        flush=AsyncMock(),
    )
    use_case = CustomerSubscriptionServiceAccessUseCase(session)
    item = _subscription_summary()
    item.plan_code = "premium_spb_de_exceptions"
    item.display_name = "Premium SPB + DE Exceptions"
    grant = SimpleNamespace(
        id=item.entitlement_grant_id,
        customer_account_id=customer_account_id,
        auth_realm_id=auth_realm_id,
        source_order_id=uuid.uuid4(),
        origin_storefront_id=None,
        service_identity_id=None,
    )

    with pytest.raises(HTTPException) as exc_info:
        await use_case._ensure_grant_service_identity(
            item=item,
            grant=grant,
            provider_name="remnawave",
            remnawave_client=SimpleNamespace(),
            existing=None,
        )

    assert exc_info.value.status_code == 409
    assert exc_info.value.detail == (
        "Selected subscription VPN identity requires Premium SPB/DE Exceptions routing configuration"
    )
    session.get.assert_not_awaited()
    session.flush.assert_not_awaited()


@pytest.mark.asyncio
async def test_selected_subscription_lazy_provisioning_rejects_spb_de_bridge_squad_before_provider_calls(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    customer_account_id = uuid.uuid4()
    auth_realm_id = uuid.uuid4()
    bridge_squad_uuid = str(uuid.uuid4())
    _enable_spb_de_data_plane(monkeypatch)
    monkeypatch.setattr(settings, "remnawave_spb_de_exceptions_external_squad_uuid", str(uuid.uuid4()))
    monkeypatch.setattr(settings, "remnawave_spb_de_exceptions_internal_squad_uuid", bridge_squad_uuid)
    monkeypatch.setattr(settings, "remnawave_spb_de_exceptions_bridge_squad_uuid", bridge_squad_uuid)
    monkeypatch.setattr(settings, "remnawave_spb_de_exceptions_plan_codes", "premium_spb_de_exceptions")
    monkeypatch.setattr(settings, "remnawave_smart_ru_plan_codes", "premium_smart_ru")

    class FailIfConstructedRemnawaveUserGateway:
        def __init__(self, client) -> None:  # noqa: ARG002
            raise AssertionError("bridge squad collision must fail before Remnawave gateway construction")

    monkeypatch.setattr(service_access_module, "RemnawaveUserGateway", FailIfConstructedRemnawaveUserGateway)
    session = SimpleNamespace(
        get=AsyncMock(return_value=SimpleNamespace(email="spb-de-user@example.test")),
        flush=AsyncMock(),
    )
    use_case = CustomerSubscriptionServiceAccessUseCase(session)
    item = _subscription_summary()
    item.plan_code = "premium_spb_de_exceptions"
    item.display_name = "Premium SPB + DE Exceptions"
    grant = SimpleNamespace(
        id=item.entitlement_grant_id,
        customer_account_id=customer_account_id,
        auth_realm_id=auth_realm_id,
        source_order_id=uuid.uuid4(),
        origin_storefront_id=None,
        service_identity_id=None,
    )

    with pytest.raises(HTTPException) as exc_info:
        await use_case._ensure_grant_service_identity(
            item=item,
            grant=grant,
            provider_name="remnawave",
            remnawave_client=SimpleNamespace(),
            existing=None,
        )

    assert exc_info.value.status_code == 409
    assert exc_info.value.detail == (
        "Selected subscription VPN identity requires Premium SPB/DE Exceptions routing configuration"
    )
    session.get.assert_not_awaited()
    session.flush.assert_not_awaited()


@pytest.mark.asyncio
async def test_selected_subscription_spb_de_canonical_plan_fails_closed_when_plan_codes_are_typoed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    customer_account_id = uuid.uuid4()
    auth_realm_id = uuid.uuid4()
    _enable_spb_de_data_plane(monkeypatch)
    monkeypatch.setattr(settings, "remnawave_spb_de_exceptions_external_squad_uuid", "")
    monkeypatch.setattr(settings, "remnawave_spb_de_exceptions_internal_squad_uuid", str(uuid.uuid4()))
    monkeypatch.setattr(settings, "remnawave_spb_de_exceptions_bridge_squad_uuid", str(uuid.uuid4()))
    monkeypatch.setattr(settings, "remnawave_spb_de_exceptions_plan_codes", "premium_spb_de_exception")
    monkeypatch.setattr(settings, "remnawave_smart_ru_external_squad_uuid", str(uuid.uuid4()))
    monkeypatch.setattr(settings, "remnawave_smart_ru_internal_squad_uuid", str(uuid.uuid4()))
    monkeypatch.setattr(settings, "remnawave_smart_ru_plan_codes", "premium_smart_ru,premium_spb_de_exceptions")

    session = SimpleNamespace(
        get=AsyncMock(return_value=SimpleNamespace(email="spb-de-user@example.test")),
        flush=AsyncMock(),
    )
    use_case = CustomerSubscriptionServiceAccessUseCase(session)
    item = _subscription_summary()
    item.plan_code = "premium_spb_de_exceptions"
    item.display_name = "Premium SPB + DE Exceptions"
    grant = SimpleNamespace(
        id=item.entitlement_grant_id,
        customer_account_id=customer_account_id,
        auth_realm_id=auth_realm_id,
        source_order_id=uuid.uuid4(),
        origin_storefront_id=None,
        service_identity_id=None,
    )

    with pytest.raises(HTTPException) as exc_info:
        await use_case._ensure_grant_service_identity(
            item=item,
            grant=grant,
            provider_name="remnawave",
            remnawave_client=SimpleNamespace(),
            existing=None,
        )

    assert exc_info.value.status_code == 409
    assert exc_info.value.detail == (
        "Selected subscription VPN identity requires Premium SPB/DE Exceptions routing configuration"
    )
    session.get.assert_not_awaited()
    session.flush.assert_not_awaited()


@pytest.mark.asyncio
async def test_selected_subscription_existing_spb_de_identity_reuses_without_duplicate_create(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}
    customer_account_id = uuid.uuid4()
    auth_realm_id = uuid.uuid4()
    service_identity_id = uuid.uuid4()
    existing_remnawave_uuid = uuid.uuid4()
    spb_de_external_squad_uuid = str(uuid.uuid4())
    spb_de_internal_squad_uuid = str(uuid.uuid4())
    subscription_url = "https://subscription.example.local/sub/existing-spb-de"
    customer = SimpleNamespace(email="spb-de-user@example.test", remnawave_uuid=None, subscription_url=None)
    _enable_spb_de_data_plane(monkeypatch)

    class FakeRemnawaveUserGateway:
        def __init__(self, client) -> None:
            captured["remnawave_client"] = client

        async def get_by_ref(self, user_ref: RemnawaveUserRef):
            captured["looked_up_remnawave_uuid"] = user_ref.legacy_uuid
            return SimpleNamespace(uuid=existing_remnawave_uuid, subscription_url=subscription_url)

        async def update(self, remnawave_uuid: uuid.UUID, **kwargs):  # noqa: ARG002
            raise AssertionError("matching SPB/DE context must not update Remnawave user")

        async def create(self, username: str, **kwargs):  # noqa: ARG002
            raise AssertionError("existing SPB/DE identity must not create a second Remnawave user")

    monkeypatch.setattr(settings, "remnawave_spb_de_exceptions_external_squad_uuid", spb_de_external_squad_uuid)
    monkeypatch.setattr(settings, "remnawave_spb_de_exceptions_internal_squad_uuid", spb_de_internal_squad_uuid)
    monkeypatch.setattr(settings, "remnawave_spb_de_exceptions_bridge_squad_uuid", str(uuid.uuid4()))
    monkeypatch.setattr(settings, "remnawave_spb_de_exceptions_plan_codes", "premium_spb_de_exceptions")
    monkeypatch.setattr(settings, "remnawave_smart_ru_plan_codes", "premium_smart_ru")
    monkeypatch.setattr(service_access_module, "RemnawaveUserGateway", FakeRemnawaveUserGateway)

    item = _subscription_summary()
    item.plan_code = "premium_spb_de_exceptions"
    item.display_name = "Premium SPB + DE Exceptions"
    existing_identity = SimpleNamespace(
        id=service_identity_id,
        provider_subject_ref=str(existing_remnawave_uuid),
        identity_scope="subscription",
        subscription_key=item.subscription_key,
        identity_status="active",
        service_context={
            "subscription_url": subscription_url,
            **_spb_de_context(spb_de_external_squad_uuid, spb_de_internal_squad_uuid),
        },
    )
    grant = SimpleNamespace(
        id=item.entitlement_grant_id,
        customer_account_id=customer_account_id,
        auth_realm_id=auth_realm_id,
        source_order_id=uuid.uuid4(),
        origin_storefront_id=None,
        service_identity_id=None,
        grant_snapshot={},
    )
    session = SimpleNamespace(
        get=AsyncMock(return_value=customer),
        flush=AsyncMock(),
    )
    use_case = CustomerSubscriptionServiceAccessUseCase(session)
    use_case._store_subscription_url = AsyncMock()

    service_identity = await use_case._ensure_grant_service_identity(
        item=item,
        grant=grant,
        provider_name="remnawave",
        remnawave_client=SimpleNamespace(),
        existing=existing_identity,
    )

    assert service_identity is existing_identity
    assert captured["looked_up_remnawave_uuid"] == existing_remnawave_uuid
    assert grant.service_identity_id == service_identity_id
    assert customer.remnawave_uuid == str(existing_remnawave_uuid)
    assert customer.subscription_url == subscription_url
    use_case._store_subscription_url.assert_awaited_once_with(
        service_identity=existing_identity,
        subscription_url=subscription_url,
    )
    session.flush.assert_awaited_once()


@pytest.mark.asyncio
async def test_selected_subscription_existing_spb_de_identity_reasserts_dedicated_squads(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}
    customer_account_id = uuid.uuid4()
    auth_realm_id = uuid.uuid4()
    service_identity_id = uuid.uuid4()
    existing_remnawave_uuid = uuid.uuid4()
    spb_de_external_squad_uuid = str(uuid.uuid4())
    spb_de_internal_squad_uuid = str(uuid.uuid4())
    bridge_squad_uuid = str(uuid.uuid4())
    smart_external_squad_uuid = str(uuid.uuid4())
    smart_internal_squad_uuid = str(uuid.uuid4())
    updated_subscription_url = "https://subscription.example.local/sub/reasserted-spb-de"
    customer = SimpleNamespace(
        email="spb-de-user@example.test",
        remnawave_uuid=str(existing_remnawave_uuid),
        subscription_url="https://subscription.example.local/sub/old-smart",
    )
    _enable_spb_de_data_plane(monkeypatch)

    class FakeRemnawaveUserGateway:
        def __init__(self, client) -> None:
            captured["remnawave_client"] = client

        async def get_by_ref(self, user_ref: RemnawaveUserRef):
            captured["looked_up_remnawave_uuid"] = user_ref.legacy_uuid
            return SimpleNamespace(
                uuid=existing_remnawave_uuid,
                subscription_url="https://subscription.example.local/sub/old-smart",
            )

        async def update(self, user_ref: RemnawaveUserRef, **kwargs):
            captured["updated_remnawave_uuid"] = user_ref.legacy_uuid
            captured["remnawave_update_payload"] = kwargs
            return SimpleNamespace(uuid=existing_remnawave_uuid, subscription_url=updated_subscription_url)

        async def create(self, username: str, **kwargs):  # noqa: ARG002
            raise AssertionError("mismatched existing identity must be updated, not duplicated")

    monkeypatch.setattr(settings, "remnawave_spb_de_exceptions_external_squad_uuid", spb_de_external_squad_uuid)
    monkeypatch.setattr(settings, "remnawave_spb_de_exceptions_internal_squad_uuid", spb_de_internal_squad_uuid)
    monkeypatch.setattr(settings, "remnawave_spb_de_exceptions_bridge_squad_uuid", bridge_squad_uuid)
    monkeypatch.setattr(settings, "remnawave_spb_de_exceptions_plan_codes", "premium_spb_de_exceptions")
    monkeypatch.setattr(settings, "remnawave_smart_ru_external_squad_uuid", smart_external_squad_uuid)
    monkeypatch.setattr(settings, "remnawave_smart_ru_internal_squad_uuid", smart_internal_squad_uuid)
    monkeypatch.setattr(settings, "remnawave_smart_ru_plan_codes", "premium_smart_ru")
    monkeypatch.setattr(service_access_module, "RemnawaveUserGateway", FakeRemnawaveUserGateway)

    item = _subscription_summary()
    item.plan_code = "premium_spb_de_exceptions"
    item.display_name = "Premium SPB + DE Exceptions"
    existing_identity = SimpleNamespace(
        id=service_identity_id,
        provider_subject_ref=str(existing_remnawave_uuid),
        identity_scope="subscription",
        subscription_key=item.subscription_key,
        identity_status="active",
        service_context={
            "remnawave_routing_product": "premium_smart_ru",
            "remnawave_external_squad_uuid": smart_external_squad_uuid,
            "remnawave_internal_squad_uuids": [smart_internal_squad_uuid],
            "remnawave_bridge_squad_uuid": bridge_squad_uuid,
            "bridge_password": "redacted-bridge-secret",
            "bridge_inbound_tag": "DE_SPB_EXCEPTIONS_BRIDGE_9444",
            "subscription_url": customer.subscription_url,
        },
    )
    grant = SimpleNamespace(
        id=item.entitlement_grant_id,
        customer_account_id=customer_account_id,
        auth_realm_id=auth_realm_id,
        source_order_id=uuid.uuid4(),
        origin_storefront_id=None,
        service_identity_id=None,
        grant_snapshot={},
    )
    session = SimpleNamespace(
        get=AsyncMock(return_value=customer),
        flush=AsyncMock(),
    )
    use_case = CustomerSubscriptionServiceAccessUseCase(session)
    use_case._store_subscription_url = AsyncMock()

    service_identity = await use_case._ensure_grant_service_identity(
        item=item,
        grant=grant,
        provider_name="remnawave",
        remnawave_client=SimpleNamespace(),
        existing=existing_identity,
    )

    payload = captured["remnawave_update_payload"]
    assert service_identity is existing_identity
    assert captured["updated_remnawave_uuid"] == existing_remnawave_uuid
    assert payload["external_squad_uuid"] == spb_de_external_squad_uuid
    assert payload["active_internal_squads"] == [spb_de_internal_squad_uuid]
    assert payload["external_squad_uuid"] != smart_external_squad_uuid
    assert smart_internal_squad_uuid not in payload["active_internal_squads"]
    assert (
        existing_identity.service_context
        | _spb_de_context(
            spb_de_external_squad_uuid,
            spb_de_internal_squad_uuid,
        )
        == existing_identity.service_context
    )
    assert existing_identity.service_context["remnawave_routing_product"] == "premium_spb_de_exceptions"
    assert all("bridge" not in key.lower() for key in existing_identity.service_context)
    assert bridge_squad_uuid not in str(existing_identity.service_context)
    assert "redacted-bridge-secret" not in str(existing_identity.service_context)
    assert grant.service_identity_id == service_identity_id
    assert customer.subscription_url == updated_subscription_url
    use_case._store_subscription_url.assert_awaited_once_with(
        service_identity=existing_identity,
        subscription_url=updated_subscription_url,
    )
    session.flush.assert_awaited_once()


@pytest.mark.asyncio
async def test_selected_subscription_spb_de_provisioning_profile_persists_routing_context(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}
    service_identity_id = uuid.uuid4()
    spb_de_external_squad_uuid = str(uuid.uuid4())
    spb_de_internal_squad_uuid = str(uuid.uuid4())
    provisioning_profile = SimpleNamespace(id=uuid.uuid4())

    class FakeCreateProvisioningProfileUseCase:
        def __init__(self, session) -> None:
            captured["session"] = session

        async def execute(self, **kwargs):
            captured["kwargs"] = kwargs
            return SimpleNamespace(provisioning_profile=provisioning_profile)

    monkeypatch.setattr(
        service_access_module,
        "CreateProvisioningProfileUseCase",
        FakeCreateProvisioningProfileUseCase,
    )

    use_case = CustomerSubscriptionServiceAccessUseCase(SimpleNamespace())
    use_case._repo = SimpleNamespace(
        get_provisioning_profile_by_service_identity_and_key=AsyncMock(return_value=None),
    )
    service_identity = SimpleNamespace(
        id=service_identity_id,
        subscription_key=f"grant:{uuid.uuid4()}",
        provider_name="remnawave",
        service_context={
            "plan_code": "premium_spb_de_exceptions",
            "subscription_url": "https://subscription.example.local/sub/redacted-spb-de",
            **_spb_de_context(spb_de_external_squad_uuid, spb_de_internal_squad_uuid),
        },
    )

    result = await use_case._ensure_provisioning_profile(
        service_identity=service_identity,
        profile_key="shared_client-default",
        channel_type="shared_client",
    )

    payload = captured["kwargs"]["provisioning_payload"]
    assert result is provisioning_profile
    assert payload["resolved_from"] == "selected_customer_subscription"
    assert payload["subscription_key"] == service_identity.subscription_key
    assert payload["provider_name"] == "remnawave"
    assert payload["remnawave_routing"] == _spb_de_context(spb_de_external_squad_uuid, spb_de_internal_squad_uuid)
    assert "subscription_url" not in payload["remnawave_routing"]


@pytest.mark.asyncio
async def test_selected_subscription_spb_de_existing_provisioning_profile_repairs_routing_context() -> None:
    service_identity_id = uuid.uuid4()
    spb_de_external_squad_uuid = str(uuid.uuid4())
    spb_de_internal_squad_uuid = str(uuid.uuid4())
    existing_profile = SimpleNamespace(
        id=uuid.uuid4(),
        provisioning_payload={
            "resolved_from": "legacy",
            "remnawave_bridge_squad_uuid": str(uuid.uuid4()),
            "bridge_password": "redacted-bridge-secret",
            "nested": {"bridge_inbound_tag": "DE_SPB_EXCEPTIONS_BRIDGE_9444"},
        },
    )
    session = SimpleNamespace(flush=AsyncMock())
    use_case = CustomerSubscriptionServiceAccessUseCase(session)
    use_case._repo = SimpleNamespace(
        get_provisioning_profile_by_service_identity_and_key=AsyncMock(return_value=existing_profile),
    )
    service_identity = SimpleNamespace(
        id=service_identity_id,
        subscription_key=f"grant:{uuid.uuid4()}",
        provider_name="remnawave",
        service_context={
            "plan_code": "premium_spb_de_exceptions",
            "subscription_url": "https://subscription.example.local/sub/redacted-spb-de",
            **_spb_de_context(spb_de_external_squad_uuid, spb_de_internal_squad_uuid),
        },
    )

    result = await use_case._ensure_provisioning_profile(
        service_identity=service_identity,
        profile_key="shared_client-default",
        channel_type="shared_client",
    )

    assert result is existing_profile
    assert existing_profile.provisioning_payload["resolved_from"] == "legacy"
    assert existing_profile.provisioning_payload["remnawave_routing"] == _spb_de_context(
        spb_de_external_squad_uuid,
        spb_de_internal_squad_uuid,
    )
    assert "subscription_url" not in existing_profile.provisioning_payload["remnawave_routing"]
    assert all("bridge" not in key.lower() for key in existing_profile.provisioning_payload)
    assert "redacted-bridge-secret" not in str(existing_profile.provisioning_payload)
    assert "DE_SPB_EXCEPTIONS_BRIDGE_9444" not in str(existing_profile.provisioning_payload)
    session.flush.assert_awaited_once()


@pytest.mark.asyncio
async def test_selected_subscription_config_passes_plan_code_to_xhttp_gate(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}
    customer_account_id = uuid.uuid4()
    auth_realm_id = uuid.uuid4()
    legacy_uuid = uuid.uuid4()
    service_identity = SimpleNamespace(
        id=uuid.uuid4(),
        provider_subject_ref=str(legacy_uuid),
        provider_numeric_subject_id=42,
    )

    class FakeGenerateConfigUseCase:
        def __init__(self, client) -> None:
            captured["client"] = client

        async def execute(self, user_uuid: str, *, plan_code: str | None = None, user_segments=None):
            captured["user_uuid"] = user_uuid
            captured["plan_code"] = plan_code
            captured["user_segments"] = user_segments
            return {"subscription_url": "https://subscription.example.local/sub/redacted-smart"}

    monkeypatch.setattr(service_access_module, "GenerateConfigUseCase", FakeGenerateConfigUseCase)

    use_case = CustomerSubscriptionServiceAccessUseCase(SimpleNamespace())
    use_case.get_service_state = AsyncMock(
        return_value=SimpleNamespace(
            subscription=SimpleNamespace(plan_code="premium_smart_ru"),
            service_identity=service_identity,
            access_delivery_channel=SimpleNamespace(),
        )
    )
    use_case._store_subscription_url = AsyncMock()

    result = await use_case.get_config(
        customer_account_id=customer_account_id,
        auth_realm_id=auth_realm_id,
        subscription_key=f"grant:{uuid.uuid4()}",
        remnawave_client=SimpleNamespace(),
    )

    assert captured["user_uuid"] == RemnawaveUserRef(id=42, legacy_uuid=legacy_uuid)
    assert captured["plan_code"] == "premium_smart_ru"
    assert captured["user_segments"] is None
    assert result["subscription_url"] == "https://subscription.example.local/sub/redacted-smart"
    use_case._store_subscription_url.assert_awaited_once()


@pytest.mark.asyncio
async def test_selected_subscription_config_passes_spb_de_plan_code_to_xhttp_gate(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}
    customer_account_id = uuid.uuid4()
    auth_realm_id = uuid.uuid4()
    legacy_uuid = uuid.uuid4()
    service_identity = SimpleNamespace(
        id=uuid.uuid4(),
        provider_subject_ref=str(legacy_uuid),
        provider_numeric_subject_id=42,
    )

    class FakeGenerateConfigUseCase:
        def __init__(self, client) -> None:
            captured["client"] = client

        async def execute(self, user_uuid: str, *, plan_code: str | None = None, user_segments=None):
            captured["user_uuid"] = user_uuid
            captured["plan_code"] = plan_code
            captured["user_segments"] = user_segments
            return {"subscription_url": "https://subscription.example.local/sub/redacted-spb-de"}

    monkeypatch.setattr(service_access_module, "GenerateConfigUseCase", FakeGenerateConfigUseCase)

    use_case = CustomerSubscriptionServiceAccessUseCase(SimpleNamespace())
    use_case.get_service_state = AsyncMock(
        return_value=SimpleNamespace(
            subscription=SimpleNamespace(plan_code="premium_spb_de_exceptions"),
            service_identity=service_identity,
            access_delivery_channel=SimpleNamespace(),
        )
    )
    use_case._store_subscription_url = AsyncMock()

    result = await use_case.get_config(
        customer_account_id=customer_account_id,
        auth_realm_id=auth_realm_id,
        subscription_key=f"grant:{uuid.uuid4()}",
        remnawave_client=SimpleNamespace(),
    )

    assert captured["user_uuid"] == RemnawaveUserRef(id=42, legacy_uuid=legacy_uuid)
    assert captured["plan_code"] == "premium_spb_de_exceptions"
    assert captured["user_segments"] is None
    assert result["subscription_url"] == "https://subscription.example.local/sub/redacted-spb-de"
    use_case._store_subscription_url.assert_awaited_once()


@pytest.mark.asyncio
async def test_selected_subscription_service_state_route_forwards_credential_request(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}

    class FakeCustomerSubscriptionServiceAccessUseCase:
        def __init__(self, db) -> None:
            captured["db"] = db

        async def get_service_state(self, **kwargs):
            captured.update(kwargs)
            return SimpleNamespace(
                active_entitlement_grant=None,
                access_delivery_channel=None,
                device_credential=None,
                entitlement_snapshot={
                    "addons": [],
                    "display_name": "Safe Pro",
                    "effective_entitlements": {"device_limit": 5},
                    "expires_at": "2026-07-10T00:00:00Z",
                    "invite_bundle": {},
                    "is_trial": False,
                    "period_days": 30,
                    "plan_code": "pro",
                    "plan_uuid": str(uuid.uuid4()),
                    "status": "active",
                },
                provisioning_profile=None,
                resolved_channel_subject_ref="desktop-ready",
                resolved_provisioning_profile_key="shared_client-default",
                service_identity=None,
            )

    monkeypatch.setattr(
        customer_subscription_routes,
        "CustomerSubscriptionServiceAccessUseCase",
        FakeCustomerSubscriptionServiceAccessUseCase,
    )
    customer_account_id = uuid.uuid4()
    auth_realm_id = uuid.uuid4()
    payload = GetCurrentServiceStateRequest(
        provider_name="remnawave",
        channel_type=AccessDeliveryChannelType.SHARED_CLIENT,
        credential_type=DeviceCredentialType.DESKTOP_CLIENT,
        credential_subject_key="desktop-ready",
    )

    response = await customer_subscription_routes.get_customer_subscription_service_state(
        subscription_key=f"grant:{uuid.uuid4()}",
        payload=payload,
        db=SimpleNamespace(),
        customer_account_id=customer_account_id,
        current_realm=SimpleNamespace(auth_realm=SimpleNamespace(id=auth_realm_id)),
        remnawave_client=SimpleNamespace(),
    )

    assert captured["credential_type"] == "desktop_client"
    assert captured["credential_subject_key"] == "desktop-ready"
    assert response.customer_account_id == customer_account_id
    assert response.consumption_context.channel_subject_ref == "desktop-ready"
    assert response.consumption_context.credential_subject_key == "desktop-ready"


@pytest.mark.asyncio
async def test_selected_subscription_service_state_route_redacts_credential_payloads(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    now = datetime(2026, 6, 10, tzinfo=UTC)
    customer_account_id = uuid.uuid4()
    auth_realm_id = uuid.uuid4()
    service_identity_id = uuid.uuid4()
    provisioning_profile_id = uuid.uuid4()
    device_credential_id = uuid.uuid4()
    delivery_channel_id = uuid.uuid4()

    class FakeCustomerSubscriptionServiceAccessUseCase:
        def __init__(self, db) -> None:
            self.db = db

        async def get_service_state(self, **kwargs):
            return SimpleNamespace(
                active_entitlement_grant=None,
                access_delivery_channel=SimpleNamespace(
                    id=delivery_channel_id,
                    delivery_key="delivery-ready",
                    service_identity_id=service_identity_id,
                    auth_realm_id=auth_realm_id,
                    origin_storefront_id=None,
                    provisioning_profile_id=provisioning_profile_id,
                    device_credential_id=device_credential_id,
                    channel_type="shared_client",
                    channel_status="active",
                    channel_subject_ref="desktop-ready",
                    provider_name="remnawave",
                    delivery_context={"client_family": "desktop"},
                    delivery_payload={"subscription_url": "https://vpn.example.test/subscriptions/ready"},
                    last_delivered_at=now,
                    last_accessed_at=now,
                    archived_at=None,
                    archived_by_admin_user_id=None,
                    archive_reason_code=None,
                    created_at=now,
                    updated_at=now,
                ),
                device_credential=SimpleNamespace(
                    id=device_credential_id,
                    credential_key="credential-ready",
                    service_identity_id=service_identity_id,
                    auth_realm_id=auth_realm_id,
                    origin_storefront_id=None,
                    provisioning_profile_id=provisioning_profile_id,
                    credential_type="desktop_client",
                    credential_status="active",
                    subject_key="desktop-ready",
                    provider_name="remnawave",
                    provider_credential_ref="remnawave-credential-ready",
                    credential_context={"client_family": "desktop"},
                    issued_at=now,
                    last_used_at=None,
                    revoked_at=None,
                    revoked_by_admin_user_id=None,
                    revoke_reason_code=None,
                    created_at=now,
                    updated_at=now,
                ),
                entitlement_snapshot={
                    "addons": [],
                    "display_name": "Safe Pro",
                    "effective_entitlements": {"device_limit": 5},
                    "expires_at": "2026-07-10T00:00:00Z",
                    "invite_bundle": {},
                    "is_trial": False,
                    "period_days": 30,
                    "plan_code": "pro",
                    "plan_uuid": str(uuid.uuid4()),
                    "status": "active",
                },
                provisioning_profile=SimpleNamespace(
                    id=provisioning_profile_id,
                    service_identity_id=service_identity_id,
                    profile_key="shared_client-default",
                    target_channel="shared_client",
                    delivery_method="subscription_url",
                    profile_status="active",
                    provider_name="remnawave",
                    provider_profile_ref="profile-ready",
                    provisioning_payload={"config_format": "vless"},
                    created_at=now,
                    updated_at=now,
                ),
                resolved_channel_subject_ref="desktop-ready",
                resolved_provisioning_profile_key="shared_client-default",
                service_identity=SimpleNamespace(
                    id=service_identity_id,
                    service_key="svc-safe-ready",
                    customer_account_id=customer_account_id,
                    auth_realm_id=auth_realm_id,
                    source_order_id=uuid.uuid4(),
                    origin_storefront_id=None,
                    provider_name="remnawave",
                    identity_scope="subscription",
                    subscription_key=kwargs["subscription_key"],
                    provider_subject_ref="remnawave-user-ready",
                    provider_numeric_subject_id=42,
                    identity_status="active",
                    service_context={},
                    created_at=now,
                    updated_at=now,
                ),
            )

    monkeypatch.setattr(
        customer_subscription_routes,
        "CustomerSubscriptionServiceAccessUseCase",
        FakeCustomerSubscriptionServiceAccessUseCase,
    )
    payload = GetCurrentServiceStateRequest(
        provider_name="remnawave",
        channel_type=AccessDeliveryChannelType.SHARED_CLIENT,
        credential_type=DeviceCredentialType.DESKTOP_CLIENT,
        credential_subject_key="desktop-ready",
    )

    response = await customer_subscription_routes.get_customer_subscription_service_state(
        subscription_key=f"grant:{uuid.uuid4()}",
        payload=payload,
        db=SimpleNamespace(),
        customer_account_id=customer_account_id,
        current_realm=SimpleNamespace(auth_realm=SimpleNamespace(id=auth_realm_id)),
        remnawave_client=SimpleNamespace(),
    )

    assert response.entitlement_snapshot.status == "active"
    assert response.service_identity is not None
    assert response.provisioning_profile is not None
    assert response.device_credential is not None
    assert response.device_credential.credential_status == "active"
    assert response.device_credential.subject_key == "desktop-ready"
    assert response.device_credential.provider_credential_ref is None
    assert response.device_credential.credential_context == {}
    assert response.access_delivery_channel is not None
    assert response.access_delivery_channel.channel_status == "active"
    assert response.access_delivery_channel.device_credential_id == device_credential_id
    assert response.access_delivery_channel.delivery_payload == {}
    assert response.provisioning_profile.provisioning_payload == {}
    assert response.service_identity.subscription_key is None
    assert response.service_identity.service_context == {}
    assert response.consumption_context.credential_subject_key == "desktop-ready"
