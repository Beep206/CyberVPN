from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from src.application.services.remnawave_identity_access import (
    RemnawaveIdentityAccessConflict,
    _acquire_runtime_mapping_locks,
    persist_runtime_mapped_mobile_identity,
    persist_runtime_mapped_service_identity,
    resolve_exact_mapped_remnawave_ref,
)
from src.domain.value_objects.remnawave_user_ref import RemnawaveUserRef


def _session_with_candidates(candidates):
    for candidate in candidates:
        if not hasattr(candidate, "subject_type"):
            candidate.subject_type = "mobile_user"
    result = MagicMock()
    result.scalars.return_value.all.return_value = list(candidates)
    session = MagicMock()
    session.get_bind.return_value.dialect.name = "sqlite"
    session.execute = AsyncMock(return_value=result)
    session.flush = AsyncMock()
    return session


@pytest.mark.unit
@pytest.mark.asyncio
async def test_runtime_mobile_identity_persists_local_pair_and_mapped_ledger_atomically():
    customer = SimpleNamespace(id=uuid4(), remnawave_user_id=None, remnawave_uuid=None)
    legacy_uuid = uuid4()
    session = _session_with_candidates([])

    result = await persist_runtime_mapped_mobile_identity(
        session,
        customer=customer,
        remnawave_user_id=42,
        remnawave_uuid=legacy_uuid,
        source="unit_runtime_create",
    )

    assert result.id == 42
    assert result.legacy_uuid == legacy_uuid
    assert customer.remnawave_user_id == 42
    assert customer.remnawave_uuid == str(legacy_uuid)
    ledger = session.add.call_args.args[0]
    assert ledger.subject_type == "mobile_user"
    assert ledger.subject_id == customer.id
    assert ledger.reconciliation_state == "mapped"
    assert ledger.numeric_user_id == 42
    assert ledger.legacy_uuid == str(legacy_uuid)
    assert ledger.evidence["source"] == "unit_runtime_create"
    assert ledger.evidence["provider_auto_renew_authoritative"] is False
    assert session.flush.await_count == 2


@pytest.mark.unit
@pytest.mark.asyncio
async def test_runtime_mobile_identity_persists_numeric_only_without_fabricated_uuid():
    customer = SimpleNamespace(id=uuid4(), remnawave_user_id=None, remnawave_uuid=None)
    session = _session_with_candidates([])

    result = await persist_runtime_mapped_mobile_identity(
        session,
        customer=customer,
        remnawave_user_id=42,
        remnawave_uuid=None,
        source="unit_runtime_numeric_only_create",
    )

    assert result.id == 42
    assert result.legacy_uuid is None
    assert customer.remnawave_user_id == 42
    assert customer.remnawave_uuid is None
    ledger = session.add.call_args.args[0]
    assert ledger.numeric_user_id == 42
    assert ledger.legacy_uuid is None


@pytest.mark.unit
@pytest.mark.asyncio
async def test_runtime_numeric_only_replay_preserves_existing_legacy_rollback_evidence():
    subject_id = uuid4()
    legacy_uuid = uuid4()
    customer = SimpleNamespace(
        id=subject_id,
        remnawave_user_id=42,
        remnawave_uuid=str(legacy_uuid),
    )
    existing = SimpleNamespace(
        subject_id=subject_id,
        reconciliation_state="mapped",
        numeric_user_id=42,
        legacy_uuid=str(legacy_uuid),
    )
    session = _session_with_candidates([existing])

    result = await persist_runtime_mapped_mobile_identity(
        session,
        customer=customer,
        remnawave_user_id=42,
        remnawave_uuid=None,
        source="unit_runtime_numeric_only_replay",
    )

    assert result == RemnawaveUserRef(id=42, legacy_uuid=legacy_uuid)
    assert customer.remnawave_uuid == str(legacy_uuid)
    assert existing.legacy_uuid == str(legacy_uuid)


@pytest.mark.unit
@pytest.mark.asyncio
@pytest.mark.parametrize("legacy_on_local", [True, False])
async def test_runtime_persist_rejects_one_sided_legacy_evidence(legacy_on_local):
    subject_id = uuid4()
    legacy_uuid = uuid4()
    customer = SimpleNamespace(
        id=subject_id,
        remnawave_user_id=42,
        remnawave_uuid=str(legacy_uuid) if legacy_on_local else None,
    )
    existing = SimpleNamespace(
        subject_id=subject_id,
        reconciliation_state="mapped",
        numeric_user_id=42,
        legacy_uuid=None if legacy_on_local else str(legacy_uuid),
    )
    session = _session_with_candidates([existing])

    with pytest.raises(RemnawaveIdentityAccessConflict, match="conflicts with the runtime identity"):
        await persist_runtime_mapped_mobile_identity(
            session,
            customer=customer,
            remnawave_user_id=42,
            remnawave_uuid=None,
            source="unit_runtime_one_sided_legacy",
        )


@pytest.mark.unit
@pytest.mark.asyncio
async def test_runtime_identity_idempotently_accepts_only_the_same_mapped_pair():
    subject_id = uuid4()
    legacy_uuid = uuid4()
    customer = SimpleNamespace(
        id=subject_id,
        remnawave_user_id=42,
        remnawave_uuid=str(legacy_uuid),
    )
    existing = SimpleNamespace(
        subject_id=subject_id,
        reconciliation_state="mapped",
        numeric_user_id=42,
        legacy_uuid=str(legacy_uuid),
    )
    session = _session_with_candidates([existing])

    result = await persist_runtime_mapped_mobile_identity(
        session,
        customer=customer,
        remnawave_user_id=42,
        remnawave_uuid=legacy_uuid,
        source="unit_runtime_existing",
    )

    assert result.id == 42
    session.add.assert_not_called()


@pytest.mark.unit
@pytest.mark.asyncio
@pytest.mark.parametrize("state", ["pending", "missing", "duplicate", "conflict"])
async def test_runtime_identity_rejects_non_mapped_existing_ledger(state):
    subject_id = uuid4()
    legacy_uuid = uuid4()
    customer = SimpleNamespace(
        id=subject_id,
        remnawave_user_id=42,
        remnawave_uuid=str(legacy_uuid),
    )
    existing = SimpleNamespace(
        subject_id=subject_id,
        reconciliation_state=state,
        numeric_user_id=42,
        legacy_uuid=str(legacy_uuid),
    )
    session = _session_with_candidates([existing])

    with pytest.raises(RemnawaveIdentityAccessConflict, match="conflicts"):
        await persist_runtime_mapped_mobile_identity(
            session,
            customer=customer,
            remnawave_user_id=42,
            remnawave_uuid=legacy_uuid,
            source="unit_runtime_conflict",
        )

    session.add.assert_not_called()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_runtime_identity_rejects_foreign_numeric_or_legacy_mapping():
    customer = SimpleNamespace(id=uuid4(), remnawave_user_id=None, remnawave_uuid=None)
    legacy_uuid = uuid4()
    foreign = SimpleNamespace(
        subject_id=uuid4(),
        reconciliation_state="mapped",
        numeric_user_id=42,
        legacy_uuid=str(legacy_uuid),
    )
    session = _session_with_candidates([foreign])

    with pytest.raises(RemnawaveIdentityAccessConflict, match="another subject"):
        await persist_runtime_mapped_mobile_identity(
            session,
            customer=customer,
            remnawave_user_id=42,
            remnawave_uuid=legacy_uuid,
            source="unit_runtime_foreign",
        )

    assert customer.remnawave_user_id is None
    session.add.assert_not_called()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_runtime_identity_never_overwrites_a_stale_local_pair():
    customer = SimpleNamespace(id=uuid4(), remnawave_user_id=41, remnawave_uuid=str(uuid4()))
    session = _session_with_candidates([])

    with pytest.raises(RemnawaveIdentityAccessConflict, match="Local Remnawave identity conflicts"):
        await persist_runtime_mapped_mobile_identity(
            session,
            customer=customer,
            remnawave_user_id=42,
            remnawave_uuid=uuid4(),
            source="unit_runtime_stale",
        )

    session.execute.assert_not_awaited()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_runtime_service_identity_persists_exact_provider_pair():
    identity = SimpleNamespace(
        id=uuid4(),
        customer_account_id=uuid4(),
        provider_name="remnawave",
        provider_numeric_subject_id=None,
        provider_subject_ref=None,
    )
    legacy_uuid = uuid4()
    session = _session_with_candidates([])

    await persist_runtime_mapped_service_identity(
        session,
        service_identity=identity,
        remnawave_user_id=73,
        remnawave_uuid=legacy_uuid,
        source="unit_service_create",
    )

    assert identity.provider_numeric_subject_id == 73
    assert identity.provider_subject_ref == str(legacy_uuid)
    assert session.add.call_args.args[0].subject_type == "service_identity"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_runtime_service_identity_persists_numeric_only_provider_identity():
    identity = SimpleNamespace(
        id=uuid4(),
        customer_account_id=uuid4(),
        provider_name="remnawave",
        provider_numeric_subject_id=None,
        provider_subject_ref=None,
    )
    session = _session_with_candidates([])

    result = await persist_runtime_mapped_service_identity(
        session,
        service_identity=identity,
        remnawave_user_id=73,
        remnawave_uuid=None,
        source="unit_service_numeric_only_create",
    )

    assert result == RemnawaveUserRef(id=73)
    assert identity.provider_numeric_subject_id == 73
    assert identity.provider_subject_ref is None
    assert session.add.call_args.args[0].legacy_uuid is None


@pytest.mark.unit
@pytest.mark.asyncio
async def test_resolve_exact_mapped_identity_accepts_numeric_only_local_and_ledger():
    subject_id = uuid4()
    result = MagicMock()
    result.scalars.return_value.all.return_value = [
        SimpleNamespace(
            subject_type="service_identity",
            subject_id=subject_id,
            reconciliation_state="mapped",
            numeric_user_id=73,
            legacy_uuid=None,
        )
    ]
    session = MagicMock()
    session.execute = AsyncMock(return_value=result)

    resolved = await resolve_exact_mapped_remnawave_ref(
        session,
        subject_type="service_identity",
        subject_id=subject_id,
        numeric_user_id=73,
        legacy_uuid_raw=None,
    )

    assert resolved == RemnawaveUserRef(id=73)


@pytest.mark.unit
@pytest.mark.asyncio
@pytest.mark.parametrize("legacy_on_local", [True, False])
async def test_resolve_exact_mapped_identity_rejects_one_sided_legacy_evidence(legacy_on_local):
    subject_id = uuid4()
    legacy_uuid = uuid4()
    result = MagicMock()
    result.scalars.return_value.all.return_value = [
        SimpleNamespace(
            subject_type="service_identity",
            subject_id=subject_id,
            reconciliation_state="mapped",
            numeric_user_id=73,
            legacy_uuid=None if legacy_on_local else str(legacy_uuid),
        )
    ]
    session = MagicMock()
    session.execute = AsyncMock(return_value=result)

    with pytest.raises(RemnawaveIdentityAccessConflict, match="conflicts with the local subject"):
        await resolve_exact_mapped_remnawave_ref(
            session,
            subject_type="service_identity",
            subject_id=subject_id,
            numeric_user_id=73,
            legacy_uuid_raw=str(legacy_uuid) if legacy_on_local else None,
        )


@pytest.mark.unit
@pytest.mark.asyncio
async def test_runtime_mapping_locks_subject_numeric_and_normalized_legacy_dimensions():
    session = MagicMock()
    session.get_bind.return_value.dialect.name = "postgresql"
    session.execute = AsyncMock()

    await _acquire_runtime_mapping_locks(
        session,
        subject_type="mobile_user",
        subject_id=uuid4(),
        numeric_user_id=42,
        legacy_uuid=uuid4(),
    )

    assert session.execute.await_count == 4
    assert "pg_advisory_xact_lock_shared" in str(session.execute.await_args_list[0].args[0])
    lock_ids = [call.args[1]["lock_id"] for call in session.execute.await_args_list]
    assert lock_ids[1:] == sorted(lock_ids[1:])
    assert len(set(lock_ids)) == 4


@pytest.mark.unit
@pytest.mark.asyncio
async def test_runtime_cross_type_alias_allows_only_the_same_customer_and_exact_pair():
    customer_id = uuid4()
    service_identity_id = uuid4()
    legacy_uuid = uuid4()
    customer = SimpleNamespace(id=customer_id, remnawave_user_id=None, remnawave_uuid=None)
    existing_service_alias = SimpleNamespace(
        subject_type="service_identity",
        subject_id=service_identity_id,
        reconciliation_state="mapped",
        numeric_user_id=42,
        legacy_uuid=str(legacy_uuid),
    )
    candidate_result = MagicMock()
    candidate_result.scalars.return_value.all.return_value = [existing_service_alias]
    owner_result = MagicMock()
    owner_result.all.return_value = [(service_identity_id, customer_id)]
    session = MagicMock()
    session.get_bind.return_value.dialect.name = "sqlite"
    session.execute = AsyncMock(side_effect=[candidate_result, owner_result])
    session.flush = AsyncMock()

    result = await persist_runtime_mapped_mobile_identity(
        session,
        customer=customer,
        remnawave_user_id=42,
        remnawave_uuid=legacy_uuid,
        source="unit_cross_type_same_owner",
    )

    assert result == RemnawaveUserRef(id=42, legacy_uuid=legacy_uuid)
    assert session.add.call_args.args[0].subject_type == "mobile_user"


@pytest.mark.unit
@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("existing_numeric_id", "existing_legacy_uuid", "target_numeric_id", "target_legacy_uuid"),
    [
        (42, uuid4(), 42, uuid4()),
        (41, uuid4(), 42, None),
    ],
)
async def test_runtime_cross_type_alias_rejects_different_customer_for_numeric_or_legacy_collision(
    existing_numeric_id,
    existing_legacy_uuid,
    target_numeric_id,
    target_legacy_uuid,
):
    first_customer_id = uuid4()
    second_customer_id = uuid4()
    service_identity_id = uuid4()
    if target_legacy_uuid is None:
        target_legacy_uuid = existing_legacy_uuid
    customer = SimpleNamespace(id=first_customer_id, remnawave_user_id=None, remnawave_uuid=None)
    existing_service_alias = SimpleNamespace(
        subject_type="service_identity",
        subject_id=service_identity_id,
        reconciliation_state="mapped",
        numeric_user_id=existing_numeric_id,
        legacy_uuid=str(existing_legacy_uuid),
    )
    candidate_result = MagicMock()
    candidate_result.scalars.return_value.all.return_value = [existing_service_alias]
    owner_result = MagicMock()
    owner_result.all.return_value = [(service_identity_id, second_customer_id)]
    session = MagicMock()
    session.get_bind.return_value.dialect.name = "sqlite"
    session.execute = AsyncMock(side_effect=[candidate_result, owner_result])
    session.flush = AsyncMock()

    with pytest.raises(RemnawaveIdentityAccessConflict, match="different customer account"):
        await persist_runtime_mapped_mobile_identity(
            session,
            customer=customer,
            remnawave_user_id=target_numeric_id,
            remnawave_uuid=target_legacy_uuid,
            source="unit_cross_type_different_owner",
        )

    session.add.assert_not_called()
    candidate_statement = session.execute.await_args_list[0].args[0]
    assert "lower(trim(remnawave_identity_reconciliations.legacy_uuid))" in str(candidate_statement).lower()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_resolve_rejects_already_persisted_cross_owner_alias():
    customer_id = uuid4()
    legacy_uuid = uuid4()
    own_row = SimpleNamespace(
        subject_type="mobile_user",
        subject_id=customer_id,
        reconciliation_state="mapped",
        numeric_user_id=73,
        legacy_uuid=str(legacy_uuid),
    )
    foreign_service_id = uuid4()
    foreign_row = SimpleNamespace(
        subject_type="service_identity",
        subject_id=foreign_service_id,
        reconciliation_state="mapped",
        numeric_user_id=73,
        legacy_uuid=str(legacy_uuid),
    )
    candidate_result = MagicMock()
    candidate_result.scalars.return_value.all.return_value = [own_row, foreign_row]
    owner_result = MagicMock()
    owner_result.all.return_value = [(foreign_service_id, uuid4())]
    session = MagicMock()
    session.execute = AsyncMock(side_effect=[candidate_result, owner_result])

    with pytest.raises(RemnawaveIdentityAccessConflict, match="different customer account"):
        await resolve_exact_mapped_remnawave_ref(
            session,
            subject_type="mobile_user",
            subject_id=customer_id,
            numeric_user_id=73,
            legacy_uuid_raw=legacy_uuid,
        )
