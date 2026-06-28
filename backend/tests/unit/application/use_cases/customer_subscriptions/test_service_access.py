from __future__ import annotations

import uuid
from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException

from src.application.use_cases.customer_subscriptions import service_access as service_access_module
from src.application.use_cases.customer_subscriptions.service_access import (
    CustomerSubscriptionServiceAccessUseCase,
)
from src.config.settings import settings
from src.domain.enums import AccessDeliveryChannelType, DeviceCredentialType
from src.presentation.api.v1.access_delivery_channels.schemas import GetCurrentServiceStateRequest
from src.presentation.api.v1.customer_subscriptions import routes as customer_subscription_routes


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
async def test_selected_subscription_lazy_provisioning_uses_smart_ru_squads(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}
    customer_account_id = uuid.uuid4()
    auth_realm_id = uuid.uuid4()
    service_identity_id = uuid.uuid4()
    smart_external_squad_uuid = str(uuid.uuid4())
    smart_internal_squad_uuid = str(uuid.uuid4())

    class FakeRemnawaveUserGateway:
        def __init__(self, client) -> None:
            captured["remnawave_client"] = client

        async def create(self, username: str, **kwargs):
            captured["remnawave_username"] = username
            captured["remnawave_payload"] = kwargs
            return SimpleNamespace(
                uuid=uuid.uuid4(),
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
    monkeypatch.setattr(service_access_module, "RemnawaveUserGateway", FakeRemnawaveUserGateway)
    monkeypatch.setattr(service_access_module, "CreateServiceIdentityUseCase", FakeCreateServiceIdentityUseCase)

    session = SimpleNamespace(
        get=AsyncMock(return_value=SimpleNamespace(email="smart-user@example.test")),
        flush=AsyncMock(),
    )
    use_case = CustomerSubscriptionServiceAccessUseCase(session)
    use_case._ensure_provisioning_profile = AsyncMock()
    use_case._store_subscription_url = AsyncMock()
    item = _subscription_summary()
    item.plan_code = "premium_smart_ru"
    item.display_name = "Premium Smart RU"
    item.effective_entitlements = {"device_limit": 5}
    grant = SimpleNamespace(
        id=item.entitlement_grant_id,
        customer_account_id=customer_account_id,
        auth_realm_id=auth_realm_id,
        source_order_id=uuid.uuid4(),
        origin_storefront_id=None,
        service_identity_id=None,
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
    assert captured["identity_kwargs"]["service_context"]["plan_code"] == "premium_smart_ru"
    assert grant.service_identity_id == service_identity_id
    assert service_identity.id == service_identity_id
    session.flush.assert_awaited_once()


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
async def test_selected_subscription_service_state_route_serializes_ready_delivery_payload(
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
    assert response.access_delivery_channel is not None
    assert response.access_delivery_channel.channel_status == "active"
    assert response.access_delivery_channel.device_credential_id == device_credential_id
    assert response.access_delivery_channel.delivery_payload["subscription_url"].endswith("/ready")
    assert response.consumption_context.credential_subject_key == "desktop-ready"
