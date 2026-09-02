from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import UUID, uuid4

import pytest
from fastapi import HTTPException

from src.application.dto.mobile_auth import SubscriptionInfoDTO, SubscriptionStatus
from src.application.services.helix_service import HelixCustomerAccess, HelixService
from src.application.use_cases.auth_realms import RealmResolution
from src.domain.enums import PrincipalClass
from src.domain.value_objects.remnawave_user_ref import RemnawaveUserRef
from src.presentation.api.v1.helix import routes
from src.presentation.dependencies.auth import CurrentPrincipalActor


def _realm(realm_type: str) -> RealmResolution:
    realm_id = uuid4()
    return RealmResolution(
        auth_realm=SimpleNamespace(
            id=realm_id,
            realm_type=realm_type,
            realm_key=realm_type,
            audience=f"cybervpn:{realm_type}",
        ),
        source="test",
    )


def _actor(realm: RealmResolution, principal_id: UUID, principal_type: str) -> CurrentPrincipalActor:
    return CurrentPrincipalActor(
        principal_id=principal_id,
        principal_type=principal_type,
        auth_realm_id=realm.auth_realm.id,
        auth_realm_key=realm.realm_key,
        audience=realm.audience,
    )


@pytest.mark.security
@pytest.mark.asyncio
async def test_helix_customer_access_uses_authenticated_local_customer_and_exact_mapping(monkeypatch) -> None:
    realm = _realm("customer")
    customer_id = uuid4()
    actor = _actor(realm, customer_id, PrincipalClass.CUSTOMER.value)
    legacy_uuid = uuid4()
    db = object()
    resolver = AsyncMock(
        return_value=(
            SimpleNamespace(id=customer_id),
            RemnawaveUserRef(id=42, legacy_uuid=legacy_uuid),
        )
    )
    monkeypatch.setattr(routes, "resolve_exact_mobile_user_ref", resolver)

    access = await routes.get_helix_customer_access(actor, realm, db)

    assert access.customer_id == customer_id
    assert access.remnawave_user_ref == RemnawaveUserRef(id=42, legacy_uuid=legacy_uuid)
    resolver.assert_awaited_once_with(
        db,
        customer_id=customer_id,
        expected_auth_realm_id=realm.auth_realm.id,
    )


@pytest.mark.security
@pytest.mark.asyncio
async def test_helix_customer_access_rejects_cross_customer_resolution(monkeypatch) -> None:
    realm = _realm("customer")
    actor = _actor(realm, uuid4(), PrincipalClass.CUSTOMER.value)
    resolver = AsyncMock(
        return_value=(
            SimpleNamespace(id=uuid4()),
            RemnawaveUserRef(id=42, legacy_uuid=uuid4()),
        )
    )
    monkeypatch.setattr(routes, "resolve_exact_mobile_user_ref", resolver)

    with pytest.raises(HTTPException) as exc_info:
        await routes.get_helix_customer_access(actor, realm, object())

    assert exc_info.value.status_code == 404


@pytest.mark.security
@pytest.mark.asyncio
async def test_helix_customer_access_rejects_foreign_realm_before_mapping_lookup(monkeypatch) -> None:
    realm = _realm("admin")
    actor = _actor(realm, uuid4(), PrincipalClass.ADMIN.value)
    resolver = AsyncMock()
    monkeypatch.setattr(routes, "resolve_exact_mobile_user_ref", resolver)

    with pytest.raises(HTTPException) as exc_info:
        await routes.get_helix_customer_access(actor, realm, object())

    assert exc_info.value.status_code == 403
    resolver.assert_not_awaited()


@pytest.mark.security
@pytest.mark.asyncio
async def test_helix_customer_access_fails_closed_on_legacy_mapping_mismatch(monkeypatch) -> None:
    realm = _realm("customer")
    actor = _actor(realm, uuid4(), PrincipalClass.CUSTOMER.value)
    resolver = AsyncMock(
        side_effect=HTTPException(status_code=409, detail="Customer VPN identity is not exactly reconciled")
    )
    monkeypatch.setattr(routes, "resolve_exact_mobile_user_ref", resolver)

    with pytest.raises(HTTPException) as exc_info:
        await routes.get_helix_customer_access(actor, realm, object())

    assert exc_info.value.status_code == 409


@pytest.mark.security
@pytest.mark.asyncio
async def test_helix_entitlement_reads_numeric_identity_not_local_customer_uuid(monkeypatch) -> None:
    monkeypatch.setattr("src.application.services.helix_service.settings.helix_enabled", True)
    customer_id = uuid4()
    user_ref = RemnawaveUserRef(id=314, legacy_uuid=uuid4())
    subscription_client = SimpleNamespace(
        get_subscription=AsyncMock(return_value=SubscriptionInfoDTO(status=SubscriptionStatus.ACTIVE))
    )
    adapter = SimpleNamespace(get_client_capability_defaults=AsyncMock(return_value={"safe": True}))
    service = HelixService(adapter, subscription_client)

    result = await service.get_capability_defaults_for_user(
        HelixCustomerAccess(customer_id=customer_id, remnawave_user_ref=user_ref)
    )

    assert result == {"safe": True}
    subscription_client.get_subscription.assert_awaited_once_with(user_ref)
    assert subscription_client.get_subscription.await_args.args[0] != customer_id
