from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from src.application.services.remnawave_identity_access import RemnawaveIdentityAccessConflict
from src.application.use_cases.service_access import service_identities as service_identity_module
from src.application.use_cases.service_access.service_identities import (
    BindProvisionedRemnawaveServiceIdentityUseCase,
    CreateServiceIdentityUseCase,
)

LEGACY_UUID = "4ecf46a0-e030-4d4b-8adf-870164e67c97"
NUMERIC_ID = 4_201


def _customer() -> SimpleNamespace:
    return SimpleNamespace(
        id=uuid4(),
        auth_realm_id=uuid4(),
        remnawave_uuid=LEGACY_UUID,
        remnawave_user_id=NUMERIC_ID,
        subscription_url=None,
    )


def _reconciliation(
    customer: SimpleNamespace,
    *,
    state: str = "mapped",
    numeric_id: int = NUMERIC_ID,
    legacy_uuid: str = LEGACY_UUID,
) -> SimpleNamespace:
    return SimpleNamespace(
        subject_type="mobile_user",
        subject_id=customer.id,
        reconciliation_state=state,
        numeric_user_id=numeric_id,
        legacy_uuid=legacy_uuid,
    )


def _use_case(
    *,
    customer: SimpleNamespace,
    reconciliation: SimpleNamespace | None,
    existing: SimpleNamespace | None = None,
) -> tuple[CreateServiceIdentityUseCase, SimpleNamespace, SimpleNamespace]:
    if reconciliation is not None:
        reconciliation.subject_type = getattr(reconciliation, "subject_type", "mobile_user")
        reconciliation.subject_id = getattr(reconciliation, "subject_id", customer.id)
        reconciliation.numeric_user_id = getattr(reconciliation, "numeric_user_id", NUMERIC_ID)
        reconciliation.legacy_uuid = getattr(reconciliation, "legacy_uuid", LEGACY_UUID)

    identity_holder = {"identity": existing}

    class _Result:
        def scalar_one_or_none(self):
            return reconciliation

        def scalars(self):
            values = [] if reconciliation is None else [reconciliation]
            return SimpleNamespace(all=lambda: values)

        def all(self):
            identity = identity_holder["identity"]
            return [] if identity is None else [(identity.id, customer.id)]

    def capture_created_identity(model):
        identity_holder["identity"] = model
        return model

    session = SimpleNamespace(
        get=AsyncMock(side_effect=[customer, SimpleNamespace(id=customer.auth_realm_id)]),
        execute=AsyncMock(return_value=_Result()),
        add=MagicMock(),
        flush=AsyncMock(),
    )
    repo = SimpleNamespace(
        get_service_identity_by_customer_realm_provider=AsyncMock(return_value=existing),
        get_service_identity_by_subscription_key=AsyncMock(return_value=existing),
        create_service_identity=AsyncMock(side_effect=capture_created_identity),
    )
    use_case = CreateServiceIdentityUseCase(session)
    use_case._repo = repo
    return use_case, session, repo


@pytest.mark.asyncio
async def test_account_identity_uses_only_exact_reconciled_customer_provider_identity() -> None:
    customer = _customer()
    use_case, session, repo = _use_case(
        customer=customer,
        reconciliation=_reconciliation(customer),
    )

    result = await use_case.execute(
        customer_account_id=customer.id,
        auth_realm_id=customer.auth_realm_id,
        provider_name=" Remnawave ",
    )

    assert result.created is True
    assert result.service_identity.provider_name == "remnawave"
    assert result.service_identity.provider_subject_ref == LEGACY_UUID
    assert result.service_identity.provider_numeric_subject_id == NUMERIC_ID
    assert session.execute.await_count == 3
    assert session.flush.await_count == 2
    repo.create_service_identity.assert_awaited_once()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "reconciliation",
    [
        None,
        SimpleNamespace(reconciliation_state="pending"),
        SimpleNamespace(
            reconciliation_state="mapped",
            numeric_user_id=NUMERIC_ID + 1,
            legacy_uuid=LEGACY_UUID,
        ),
        SimpleNamespace(
            reconciliation_state="mapped",
            numeric_user_id=NUMERIC_ID,
            legacy_uuid="af244be0-60c0-4eb1-96d1-74f6701d4c52",
        ),
    ],
)
async def test_account_identity_fails_closed_without_exact_mapped_reconciliation(
    reconciliation: SimpleNamespace | None,
) -> None:
    customer = _customer()
    use_case, _, repo = _use_case(customer=customer, reconciliation=reconciliation)

    with pytest.raises(ValueError, match="Customer Remnawave identity is not exactly reconciled"):
        await use_case.execute(
            customer_account_id=customer.id,
            auth_realm_id=customer.auth_realm_id,
            provider_name="remnawave",
        )

    repo.get_service_identity_by_customer_realm_provider.assert_not_awaited()
    repo.create_service_identity.assert_not_awaited()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("overrides", "message"),
    [
        (
            {"provider_numeric_subject_id": NUMERIC_ID + 99},
            "Provider numeric subject id does not belong to customer account",
        ),
        (
            {"provider_subject_ref": "5c31dbd8-4de0-4e89-af1e-6a33379728e2"},
            "Provider subject reference does not belong to customer account",
        ),
    ],
)
async def test_account_identity_rejects_cross_customer_provider_references(
    overrides: dict[str, object],
    message: str,
) -> None:
    customer = _customer()
    use_case, session, repo = _use_case(
        customer=customer,
        reconciliation=_reconciliation(customer),
    )

    with pytest.raises(ValueError, match=message):
        await use_case.execute(
            customer_account_id=customer.id,
            auth_realm_id=customer.auth_realm_id,
            provider_name="remnawave",
            **overrides,
        )

    session.execute.assert_awaited_once()
    repo.create_service_identity.assert_not_awaited()


@pytest.mark.asyncio
async def test_account_identity_replay_rejects_persisted_cross_customer_binding() -> None:
    customer = _customer()
    existing = SimpleNamespace(
        id=uuid4(),
        customer_account_id=customer.id,
        provider_name="remnawave",
        provider_subject_ref=LEGACY_UUID,
        provider_numeric_subject_id=NUMERIC_ID + 1,
    )
    use_case, _, repo = _use_case(
        customer=customer,
        reconciliation=_reconciliation(customer),
        existing=existing,
    )

    with pytest.raises(ValueError, match="Existing service identity does not match"):
        await use_case.execute(
            customer_account_id=customer.id,
            auth_realm_id=customer.auth_realm_id,
            provider_name="remnawave",
        )

    repo.create_service_identity.assert_not_awaited()


@pytest.mark.asyncio
async def test_subscription_identity_keeps_internal_upstream_binding_path() -> None:
    customer = _customer()
    subscription_legacy_uuid = "86412557-8f05-4572-a4d2-a426ec800448"
    subscription_numeric_id = NUMERIC_ID + 100
    use_case, session, _ = _use_case(customer=customer, reconciliation=None)

    result = await use_case.execute(
        customer_account_id=customer.id,
        auth_realm_id=customer.auth_realm_id,
        provider_name="remnawave",
        identity_scope="subscription",
        subscription_key="sub:trusted-upstream-result",
        provider_subject_ref=subscription_legacy_uuid,
        provider_numeric_subject_id=subscription_numeric_id,
    )

    assert result.service_identity.provider_subject_ref == subscription_legacy_uuid
    assert result.service_identity.provider_numeric_subject_id == subscription_numeric_id
    session.execute.assert_awaited_once()
    assert session.flush.await_count == 2


@pytest.mark.asyncio
async def test_subscription_identity_accepts_exact_numeric_only_upstream_binding() -> None:
    customer = _customer()
    subscription_numeric_id = NUMERIC_ID + 100
    use_case, session, _ = _use_case(customer=customer, reconciliation=None)

    result = await use_case.execute(
        customer_account_id=customer.id,
        auth_realm_id=customer.auth_realm_id,
        provider_name="remnawave",
        identity_scope="subscription",
        subscription_key="sub:numeric-only-upstream-result",
        provider_numeric_subject_id=subscription_numeric_id,
    )

    assert result.service_identity.provider_subject_ref is None
    assert result.service_identity.provider_numeric_subject_id == subscription_numeric_id
    ledger = session.add.call_args.args[0]
    assert ledger.numeric_user_id == subscription_numeric_id
    assert ledger.legacy_uuid is None


@pytest.mark.asyncio
async def test_invite_path_creates_only_suspended_unbound_pending_identity() -> None:
    customer = _customer()
    customer.remnawave_uuid = None
    customer.remnawave_user_id = None
    use_case, _, repo = _use_case(customer=customer, reconciliation=None)

    result = await use_case.execute(
        customer_account_id=customer.id,
        auth_realm_id=customer.auth_realm_id,
        provider_name="remnawave",
        allow_pending_remnawave_binding=True,
    )

    assert result.created is True
    assert result.service_identity.identity_status == "suspended"
    assert result.service_identity.provider_subject_ref is None
    assert result.service_identity.provider_numeric_subject_id is None
    assert result.service_identity.service_context["remnawave_binding_state"] == "pending_provider_create"
    repo.create_service_identity.assert_awaited_once()


@pytest.mark.asyncio
async def test_default_path_still_rejects_unbound_remnawave_identity() -> None:
    customer = _customer()
    customer.remnawave_uuid = None
    customer.remnawave_user_id = None
    use_case, _, repo = _use_case(customer=customer, reconciliation=None)

    with pytest.raises(ValueError, match="no canonical Remnawave identity"):
        await use_case.execute(
            customer_account_id=customer.id,
            auth_realm_id=customer.auth_realm_id,
            provider_name="remnawave",
        )

    repo.get_service_identity_by_customer_realm_provider.assert_not_awaited()
    repo.create_service_identity.assert_not_awaited()


@pytest.mark.asyncio
async def test_invite_pending_replay_rejects_active_unbound_identity() -> None:
    customer = _customer()
    customer.remnawave_uuid = None
    customer.remnawave_user_id = None
    existing = SimpleNamespace(
        identity_status="active",
        provider_subject_ref=None,
        provider_numeric_subject_id=None,
        service_context={"remnawave_binding_state": "pending_provider_create"},
    )
    use_case, _, repo = _use_case(customer=customer, reconciliation=None, existing=existing)

    with pytest.raises(ValueError, match="not safely pending"):
        await use_case.execute(
            customer_account_id=customer.id,
            auth_realm_id=customer.auth_realm_id,
            provider_name="remnawave",
            allow_pending_remnawave_binding=True,
        )

    repo.create_service_identity.assert_not_awaited()


def _pending_service_identity(*, customer_id, auth_realm_id) -> SimpleNamespace:
    return SimpleNamespace(
        id=uuid4(),
        customer_account_id=customer_id,
        auth_realm_id=auth_realm_id,
        provider_name="remnawave",
        identity_scope="account",
        identity_status="suspended",
        provider_subject_ref=None,
        provider_numeric_subject_id=None,
        service_context={"remnawave_binding_state": "pending_provider_create"},
    )


@pytest.mark.asyncio
async def test_provider_binding_maps_then_activates_pending_identity(monkeypatch) -> None:
    customer_id = uuid4()
    auth_realm_id = uuid4()
    service_identity = _pending_service_identity(
        customer_id=customer_id,
        auth_realm_id=auth_realm_id,
    )
    session = SimpleNamespace(flush=AsyncMock())
    use_case = BindProvisionedRemnawaveServiceIdentityUseCase(session)
    use_case._repo = SimpleNamespace(get_service_identity_by_id=AsyncMock(return_value=service_identity))

    async def persist_mapping(_session, *, service_identity, remnawave_user_id, remnawave_uuid, source):
        assert source == "invite_redemption"
        service_identity.provider_numeric_subject_id = remnawave_user_id
        service_identity.provider_subject_ref = remnawave_uuid

    monkeypatch.setattr(
        service_identity_module,
        "persist_runtime_mapped_service_identity",
        persist_mapping,
    )

    result = await use_case.execute(
        service_identity_id=service_identity.id,
        customer_account_id=customer_id,
        auth_realm_id=auth_realm_id,
        remnawave_user_id=NUMERIC_ID,
        remnawave_uuid=LEGACY_UUID,
        mapping_source="invite_redemption",
    )

    assert result.identity_status == "active"
    assert result.provider_numeric_subject_id == NUMERIC_ID
    assert result.provider_subject_ref == LEGACY_UUID
    assert result.service_context["remnawave_binding_state"] == "mapped"
    session.flush.assert_awaited_once()


@pytest.mark.asyncio
async def test_provider_binding_rejects_cross_customer_before_mapping(monkeypatch) -> None:
    customer_id = uuid4()
    auth_realm_id = uuid4()
    service_identity = _pending_service_identity(
        customer_id=uuid4(),
        auth_realm_id=auth_realm_id,
    )
    session = SimpleNamespace(flush=AsyncMock())
    use_case = BindProvisionedRemnawaveServiceIdentityUseCase(session)
    use_case._repo = SimpleNamespace(get_service_identity_by_id=AsyncMock(return_value=service_identity))
    persist_mapping = AsyncMock()
    monkeypatch.setattr(
        service_identity_module,
        "persist_runtime_mapped_service_identity",
        persist_mapping,
    )

    with pytest.raises(ValueError, match="does not belong"):
        await use_case.execute(
            service_identity_id=service_identity.id,
            customer_account_id=customer_id,
            auth_realm_id=auth_realm_id,
            remnawave_user_id=NUMERIC_ID,
            remnawave_uuid=LEGACY_UUID,
            mapping_source="invite_redemption",
        )

    persist_mapping.assert_not_awaited()
    session.flush.assert_not_awaited()


@pytest.mark.asyncio
async def test_provider_binding_failure_never_activates_unbound_identity(monkeypatch) -> None:
    customer_id = uuid4()
    auth_realm_id = uuid4()
    service_identity = _pending_service_identity(
        customer_id=customer_id,
        auth_realm_id=auth_realm_id,
    )
    session = SimpleNamespace(flush=AsyncMock())
    use_case = BindProvisionedRemnawaveServiceIdentityUseCase(session)
    use_case._repo = SimpleNamespace(get_service_identity_by_id=AsyncMock(return_value=service_identity))

    async def reject_mapping(*_args, **_kwargs):
        raise RemnawaveIdentityAccessConflict("conflicting numeric mapping")

    monkeypatch.setattr(
        service_identity_module,
        "persist_runtime_mapped_service_identity",
        reject_mapping,
    )

    with pytest.raises(ValueError, match="could not be reconciled"):
        await use_case.execute(
            service_identity_id=service_identity.id,
            customer_account_id=customer_id,
            auth_realm_id=auth_realm_id,
            remnawave_user_id=NUMERIC_ID,
            remnawave_uuid=LEGACY_UUID,
            mapping_source="invite_redemption",
        )

    assert service_identity.identity_status == "suspended"
    assert service_identity.provider_numeric_subject_id is None
    assert service_identity.provider_subject_ref is None
    assert service_identity.service_context["remnawave_binding_state"] == "pending_provider_create"
    session.flush.assert_not_awaited()
