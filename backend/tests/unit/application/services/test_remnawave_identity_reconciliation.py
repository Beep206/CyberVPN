from datetime import UTC, datetime
from itertools import permutations
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID, uuid4

import pytest

from src.application.services.remnawave_identity_reconciliation import (
    LocalRemnawaveSubject,
    ReconcileRemnawaveIdentitiesService,
    RemnawaveCutoverBlocked,
    build_remnawave_reconciliation_plan,
)
from src.domain.entities.user import User
from src.domain.enums import UserStatus


def _upstream(*, numeric_id: int, legacy_uuid: UUID, auto_renew: bool | None = None) -> User:
    now = datetime(2026, 8, 30, tzinfo=UTC)
    return User(
        uuid=legacy_uuid,
        remnawave_id=numeric_id,
        username=f"user-{numeric_id}",
        status=UserStatus.ACTIVE,
        short_uuid=f"short-{numeric_id}",
        created_at=now,
        updated_at=now,
        auto_renew=auto_renew,
    )


@pytest.mark.unit
def test_reconciliation_maps_every_subject_and_is_deterministic() -> None:
    legacy_uuid = uuid4()
    subject_id = uuid4()
    subject = LocalRemnawaveSubject(
        subject_type="mobile_user",
        subject_id=subject_id,
        customer_account_id=subject_id,
        legacy_uuid=legacy_uuid,
        current_numeric_id=None,
    )

    first = build_remnawave_reconciliation_plan(
        upstream_users=[_upstream(numeric_id=42, legacy_uuid=legacy_uuid)],
        local_subjects=[subject],
    )
    second = build_remnawave_reconciliation_plan(
        upstream_users=[_upstream(numeric_id=42, legacy_uuid=legacy_uuid)],
        local_subjects=[subject],
    )

    assert first.ready_for_cutover is True
    assert first.mappings[0].numeric_user_id == 42
    assert first.fingerprint == second.fingerprint


@pytest.mark.unit
def test_reconciliation_blocks_missing_local_mapping() -> None:
    subject_id = uuid4()
    plan = build_remnawave_reconciliation_plan(
        upstream_users=[_upstream(numeric_id=42, legacy_uuid=uuid4())],
        local_subjects=[
            LocalRemnawaveSubject(
                subject_type="mobile_user",
                subject_id=subject_id,
                customer_account_id=subject_id,
                legacy_uuid=uuid4(),
                current_numeric_id=None,
            )
        ],
    )

    assert plan.ready_for_cutover is False
    assert {issue.code for issue in plan.issues} == {"local_subject_missing_upstream"}


@pytest.mark.unit
def test_reconciliation_blocks_duplicate_upstream_numeric_id() -> None:
    first_uuid = uuid4()
    second_uuid = uuid4()
    subject_id = uuid4()
    plan = build_remnawave_reconciliation_plan(
        upstream_users=[
            _upstream(numeric_id=42, legacy_uuid=first_uuid),
            _upstream(numeric_id=42, legacy_uuid=second_uuid),
        ],
        local_subjects=[
            LocalRemnawaveSubject(
                subject_type="mobile_user",
                subject_id=subject_id,
                customer_account_id=subject_id,
                legacy_uuid=first_uuid,
                current_numeric_id=None,
            )
        ],
    )

    assert plan.ready_for_cutover is False
    assert "duplicate_upstream_numeric_id" in {issue.code for issue in plan.issues}


@pytest.mark.unit
def test_reconciliation_blocks_existing_numeric_conflict() -> None:
    legacy_uuid = uuid4()
    plan = build_remnawave_reconciliation_plan(
        upstream_users=[_upstream(numeric_id=42, legacy_uuid=legacy_uuid)],
        local_subjects=[
            LocalRemnawaveSubject(
                subject_type="service_identity",
                subject_id=uuid4(),
                customer_account_id=uuid4(),
                legacy_uuid=legacy_uuid,
                current_numeric_id=99,
                identity_scope="subscription",
            )
        ],
    )

    assert plan.ready_for_cutover is False
    assert {issue.code for issue in plan.issues} == {"numeric_identity_conflict"}


@pytest.mark.unit
def test_reconciliation_records_numeric_only_match_truthfully() -> None:
    subject_id = uuid4()
    plan = build_remnawave_reconciliation_plan(
        upstream_users=[_upstream(numeric_id=42, legacy_uuid=uuid4())],
        local_subjects=[
            LocalRemnawaveSubject(
                subject_type="mobile_user",
                subject_id=subject_id,
                customer_account_id=subject_id,
                legacy_uuid=None,
                current_numeric_id=42,
            )
        ],
    )

    assert plan.ready_for_cutover is True
    assert plan.mappings[0].matched_by == "numeric_id"


@pytest.mark.unit
async def test_reconciliation_never_imports_provider_auto_renew_as_billing_consent() -> None:
    legacy_uuid = uuid4()
    subject_id = uuid4()
    mobile_user = SimpleNamespace(
        id=subject_id,
        remnawave_uuid=str(legacy_uuid),
        remnawave_user_id=None,
        subscription_auto_renew_enabled=False,
    )
    inventory = AsyncMock()
    inventory.get_all_cursor.return_value = [_upstream(numeric_id=42, legacy_uuid=legacy_uuid, auto_renew=True)]
    mobile_result = MagicMock()
    mobile_result.scalars.return_value.all.return_value = [mobile_user]
    service_result = MagicMock()
    service_result.scalars.return_value.all.return_value = []
    session = MagicMock()
    session.execute = AsyncMock(side_effect=[mobile_result, service_result, MagicMock()])
    session.flush = AsyncMock()

    plan = await ReconcileRemnawaveIdentitiesService(session, inventory).execute(apply=True)

    assert plan.ready_for_cutover is True
    assert mobile_user.remnawave_user_id == 42
    assert mobile_user.remnawave_uuid == str(legacy_uuid)
    assert mobile_user.subscription_auto_renew_enabled is False
    reconciliation = session.add.call_args.args[0]
    assert reconciliation.evidence["provider_auto_renew_authoritative"] is False
    assert reconciliation.evidence["backend_auto_renew_consent_preserved"] is True


@pytest.mark.unit
async def test_reconciliation_inventory_selects_inactive_service_identities_for_rollback() -> None:
    legacy_uuid = uuid4()
    subject_id = uuid4()
    inactive_service_identity = SimpleNamespace(
        id=subject_id,
        customer_account_id=uuid4(),
        provider_name="remnawave",
        identity_status="disabled",
        provider_subject_ref=str(legacy_uuid),
        provider_numeric_subject_id=None,
        identity_scope="account",
    )
    inventory = AsyncMock()
    inventory.get_all_cursor.return_value = [_upstream(numeric_id=84, legacy_uuid=legacy_uuid)]
    mobile_result = MagicMock()
    mobile_result.scalars.return_value.all.return_value = []
    service_result = MagicMock()
    service_result.scalars.return_value.all.return_value = [inactive_service_identity]
    session = MagicMock()
    session.execute = AsyncMock(side_effect=[mobile_result, service_result])

    plan = await ReconcileRemnawaveIdentitiesService(session, inventory).execute()

    assert plan.ready_for_cutover is True
    assert [(mapping.subject.subject_id, mapping.numeric_user_id) for mapping in plan.mappings] == [(subject_id, 84)]
    service_inventory_statement = session.execute.await_args_list[1].args[0]
    service_inventory_predicates = " ".join(str(item) for item in service_inventory_statement._where_criteria)
    assert "service_identities.identity_status" not in service_inventory_predicates


@pytest.mark.unit
async def test_reconciliation_apply_backfills_service_rollback_identity_atomically() -> None:
    legacy_uuid = uuid4()
    service_identity = SimpleNamespace(
        id=uuid4(),
        customer_account_id=uuid4(),
        provider_name="remnawave",
        identity_status="disabled",
        provider_subject_ref=None,
        provider_numeric_subject_id=84,
        identity_scope="account",
    )
    inventory = AsyncMock()
    inventory.get_all_cursor.return_value = [_upstream(numeric_id=84, legacy_uuid=legacy_uuid)]
    mobile_result = MagicMock()
    mobile_result.scalars.return_value.all.return_value = []
    service_result = MagicMock()
    service_result.scalars.return_value.all.return_value = [service_identity]
    session = MagicMock()
    session.execute = AsyncMock(side_effect=[mobile_result, service_result, MagicMock()])
    session.flush = AsyncMock()

    plan = await ReconcileRemnawaveIdentitiesService(session, inventory).execute(apply=True)

    assert plan.ready_for_cutover is True
    assert service_identity.provider_numeric_subject_id == 84
    assert service_identity.provider_subject_ref == str(legacy_uuid)
    assert session.add.call_args.args[0].legacy_uuid == str(legacy_uuid)


@pytest.mark.unit
async def test_reconciliation_blocks_nonempty_invalid_local_rollback_identity() -> None:
    service_identity = SimpleNamespace(
        id=uuid4(),
        customer_account_id=uuid4(),
        provider_name="remnawave",
        identity_status="disabled",
        provider_subject_ref="not-a-uuid",
        provider_numeric_subject_id=84,
        identity_scope="account",
    )
    inventory = AsyncMock()
    inventory.get_all_cursor.return_value = [_upstream(numeric_id=84, legacy_uuid=uuid4())]
    mobile_result = MagicMock()
    mobile_result.scalars.return_value.all.return_value = []
    service_result = MagicMock()
    service_result.scalars.return_value.all.return_value = [service_identity]
    session = MagicMock()
    session.execute = AsyncMock(side_effect=[mobile_result, service_result])

    with pytest.raises(RemnawaveCutoverBlocked) as exc_info:
        await ReconcileRemnawaveIdentitiesService(session, inventory).execute()

    assert {issue.code for issue in exc_info.value.plan.issues} == {"invalid_local_legacy_uuid"}


@pytest.mark.unit
def test_reconciliation_allows_exact_cross_type_alias_for_one_customer() -> None:
    customer_account_id = uuid4()
    service_identity_id = uuid4()
    legacy_uuid = uuid4()

    plan = build_remnawave_reconciliation_plan(
        upstream_users=[_upstream(numeric_id=42, legacy_uuid=legacy_uuid)],
        local_subjects=[
            LocalRemnawaveSubject(
                subject_type="mobile_user",
                subject_id=customer_account_id,
                customer_account_id=customer_account_id,
                legacy_uuid=legacy_uuid,
                current_numeric_id=42,
            ),
            LocalRemnawaveSubject(
                subject_type="service_identity",
                subject_id=service_identity_id,
                customer_account_id=customer_account_id,
                legacy_uuid=legacy_uuid,
                current_numeric_id=42,
                identity_scope="account",
            ),
        ],
    )

    assert plan.ready_for_cutover is True
    assert len(plan.mappings) == 2


@pytest.mark.unit
def test_reconciliation_rejects_cross_type_numeric_and_legacy_alias_for_different_customers() -> None:
    first_customer_id = uuid4()
    second_customer_id = uuid4()
    legacy_uuid = uuid4()

    plan = build_remnawave_reconciliation_plan(
        upstream_users=[_upstream(numeric_id=42, legacy_uuid=legacy_uuid)],
        local_subjects=[
            LocalRemnawaveSubject(
                subject_type="mobile_user",
                subject_id=first_customer_id,
                customer_account_id=first_customer_id,
                legacy_uuid=legacy_uuid,
                current_numeric_id=42,
            ),
            LocalRemnawaveSubject(
                subject_type="service_identity",
                subject_id=uuid4(),
                customer_account_id=second_customer_id,
                legacy_uuid=legacy_uuid,
                current_numeric_id=42,
                identity_scope="account",
            ),
        ],
    )

    assert plan.ready_for_cutover is False
    assert {issue.code for issue in plan.issues} == {
        "provider_numeric_identity_owner_conflict",
        "provider_legacy_identity_owner_conflict",
    }
    assert len(plan.mappings) == 1


@pytest.mark.unit
@pytest.mark.parametrize("reverse", [False, True])
@pytest.mark.parametrize("subject_type", ["mobile_user", "service_identity"])
def test_reconciliation_blocks_same_type_provider_alias_for_different_owners_in_any_order(
    reverse: bool,
    subject_type: str,
) -> None:
    legacy_uuid = uuid4()
    first_owner = uuid4()
    second_owner = uuid4()
    subjects = [
        LocalRemnawaveSubject(
            subject_type=subject_type,
            subject_id=first_owner if subject_type == "mobile_user" else uuid4(),
            customer_account_id=first_owner,
            legacy_uuid=legacy_uuid,
            current_numeric_id=42,
            identity_scope="account" if subject_type == "service_identity" else None,
        ),
        LocalRemnawaveSubject(
            subject_type=subject_type,
            subject_id=second_owner if subject_type == "mobile_user" else uuid4(),
            customer_account_id=second_owner,
            legacy_uuid=legacy_uuid,
            current_numeric_id=42,
            identity_scope="account" if subject_type == "service_identity" else None,
        ),
    ]
    if reverse:
        subjects.reverse()

    plan = build_remnawave_reconciliation_plan(
        upstream_users=[_upstream(numeric_id=42, legacy_uuid=legacy_uuid)],
        local_subjects=subjects,
    )

    assert plan.ready_for_cutover is False
    assert {
        "provider_numeric_identity_owner_conflict",
        "provider_legacy_identity_owner_conflict",
    }.issubset({issue.code for issue in plan.issues})


@pytest.mark.unit
@pytest.mark.parametrize("reverse", [False, True])
def test_reconciliation_blocks_third_cross_type_alias_owned_by_another_customer(
    reverse: bool,
) -> None:
    first_owner = uuid4()
    second_owner = uuid4()
    legacy_uuid = uuid4()
    subjects = [
        LocalRemnawaveSubject(
            subject_type="mobile_user",
            subject_id=first_owner,
            customer_account_id=first_owner,
            legacy_uuid=legacy_uuid,
            current_numeric_id=42,
        ),
        LocalRemnawaveSubject(
            subject_type="service_identity",
            subject_id=uuid4(),
            customer_account_id=first_owner,
            legacy_uuid=legacy_uuid,
            current_numeric_id=42,
            identity_scope="account",
        ),
        LocalRemnawaveSubject(
            subject_type="service_identity",
            subject_id=uuid4(),
            customer_account_id=second_owner,
            legacy_uuid=legacy_uuid,
            current_numeric_id=42,
            identity_scope="account",
        ),
    ]
    if reverse:
        subjects.reverse()

    plan = build_remnawave_reconciliation_plan(
        upstream_users=[_upstream(numeric_id=42, legacy_uuid=legacy_uuid)],
        local_subjects=subjects,
    )

    assert plan.ready_for_cutover is False
    assert {
        "provider_numeric_identity_owner_conflict",
        "provider_legacy_identity_owner_conflict",
    }.issubset({issue.code for issue in plan.issues})


@pytest.mark.unit
def test_reconciliation_tracks_every_binding_across_interleaved_subject_types() -> None:
    owner = uuid4()
    legacy_uuid = uuid4()
    subjects = (
        LocalRemnawaveSubject(
            subject_type="service_identity",
            subject_id=uuid4(),
            customer_account_id=owner,
            legacy_uuid=legacy_uuid,
            current_numeric_id=42,
            identity_scope="account",
        ),
        LocalRemnawaveSubject(
            subject_type="mobile_user",
            subject_id=owner,
            customer_account_id=owner,
            legacy_uuid=legacy_uuid,
            current_numeric_id=42,
        ),
        LocalRemnawaveSubject(
            subject_type="service_identity",
            subject_id=uuid4(),
            customer_account_id=owner,
            legacy_uuid=legacy_uuid,
            current_numeric_id=42,
            identity_scope="account",
        ),
    )

    for ordered_subjects in permutations(subjects):
        plan = build_remnawave_reconciliation_plan(
            upstream_users=[_upstream(numeric_id=42, legacy_uuid=legacy_uuid)],
            local_subjects=ordered_subjects,
        )

        assert plan.ready_for_cutover is False
        assert "duplicate_provider_numeric_id" in {issue.code for issue in plan.issues}
