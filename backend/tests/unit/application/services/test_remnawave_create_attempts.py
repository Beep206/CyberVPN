from __future__ import annotations

import asyncio
from types import SimpleNamespace
from typing import cast
from uuid import uuid4

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.services.remnawave_create_attempts import (
    RemnawaveCreateAttemptConflict,
    RemnawaveCreateAttemptService,
    RemnawaveGiftProvisioningAttemptService,
    RemnawaveMutationAttemptService,
    _assert_customer_allows_new_provider_mutation,
    remnawave_create_request_hash,
)
from src.domain.value_objects.remnawave_user_ref import RemnawaveUserRef


class _ScalarResult:
    def __init__(self, record) -> None:
        self._record = record

    def scalars(self):
        return self

    def one_or_none(self):
        return self._record

    def scalar_one_or_none(self):
        return self._record


class _PostgresStatusSession:
    def __init__(self, customer_status) -> None:
        self.customer_status = customer_status
        self.statements = []

    def get_bind(self):
        return SimpleNamespace(dialect=SimpleNamespace(name="postgresql"))

    async def execute(self, statement):
        self.statements.append(statement)
        return _ScalarResult(self.customer_status)


@pytest.mark.unit
async def test_provider_mutation_customer_check_relies_on_registry_lock_without_row_update_lock() -> None:
    session = _PostgresStatusSession("active")

    await _assert_customer_allows_new_provider_mutation(cast(AsyncSession, session), uuid4())

    assert len(session.statements) == 1
    assert "FOR UPDATE" not in str(session.statements[0]).upper()


@pytest.mark.unit
@pytest.mark.parametrize("customer_status", [None, "deleting", "deleted"])
async def test_provider_mutation_customer_check_still_rejects_missing_or_terminal_owner(customer_status) -> None:
    session = _PostgresStatusSession(customer_status)

    with pytest.raises(RemnawaveCreateAttemptConflict, match="no longer accepts"):
        await _assert_customer_allows_new_provider_mutation(cast(AsyncSession, session), uuid4())


class _Session:
    def __init__(self) -> None:
        self.record = None
        self.commits = 0
        self.rollbacks = 0
        self.flushes = 0

    async def execute(self, _statement):
        return _ScalarResult(self.record)

    def add(self, record) -> None:
        self.record = record

    async def commit(self) -> None:
        self.commits += 1

    async def rollback(self) -> None:
        self.rollbacks += 1

    async def flush(self) -> None:
        self.flushes += 1


@pytest.mark.unit
async def test_create_attempt_latches_pending_and_reconciliation_across_replays() -> None:
    session = _Session()
    service = RemnawaveCreateAttemptService(cast(AsyncSession, session))
    request_hash = remnawave_create_request_hash({"operation": "selected-service"})

    first = await service.begin(
        scope="remnawave-service:create",
        idempotency_key="request-1",
        request_hash=request_hash,
    )
    replay = await service.begin(
        scope="remnawave-service:create",
        idempotency_key="request-1",
        request_hash=request_hash,
    )
    await service.mark_reconciliation_required(first.record)
    restart_replay = await RemnawaveCreateAttemptService(cast(AsyncSession, session)).begin(
        scope="remnawave-service:create",
        idempotency_key="request-1",
        request_hash=request_hash,
    )

    assert first.should_mutate is True
    assert replay.should_mutate is False
    assert restart_replay.should_mutate is False
    assert session.record.status == "reconciliation_required"
    assert session.record.response_payload == {}
    assert session.commits == 2


@pytest.mark.unit
async def test_create_attempt_rejects_same_key_with_different_payload() -> None:
    session = _Session()
    service = RemnawaveCreateAttemptService(cast(AsyncSession, session))
    await service.begin(
        scope="remnawave-user:create",
        idempotency_key="request-1",
        request_hash=remnawave_create_request_hash({"username": "first"}),
    )

    with pytest.raises(RemnawaveCreateAttemptConflict):
        await service.begin(
            scope="remnawave-user:create",
            idempotency_key="request-1",
            request_hash=remnawave_create_request_hash({"username": "second"}),
        )

    assert session.commits == 1


@pytest.mark.unit
async def test_generic_mutation_attempt_persists_exact_operation_type() -> None:
    session = _Session()
    service = RemnawaveMutationAttemptService(
        cast(AsyncSession, session),
        resource_type="remnawave_user_update",
    )

    decision = await service.begin(
        scope="remnawave-customer:update",
        idempotency_key="gift-update-1",
        request_hash=remnawave_create_request_hash({"gift_code_id": str(uuid4())}),
    )

    assert decision.should_mutate is True
    assert decision.record.resource_type == "remnawave_user_update"


@pytest.mark.unit
async def test_completed_create_attempt_keeps_only_exact_provider_reference() -> None:
    session = _Session()
    service = RemnawaveCreateAttemptService(cast(AsyncSession, session))
    decision = await service.begin(
        scope="remnawave-user:create",
        idempotency_key="request-1",
        request_hash=remnawave_create_request_hash({"username": "safe"}),
    )
    expected = RemnawaveUserRef(id=42, legacy_uuid=uuid4())

    await service.mark_completed(decision.record, user_ref=expected)

    assert service.completed_ref(decision.record) == expected
    assert decision.record.response_payload == {
        "numeric_user_id": 42,
        "legacy_uuid": str(expected.legacy_uuid),
    }
    assert "username" not in str(decision.record.response_payload).lower()
    assert session.flushes == 1


@pytest.mark.unit
async def test_completed_numeric_only_create_replays_without_fabricated_legacy_uuid() -> None:
    session = _Session()
    service = RemnawaveCreateAttemptService(cast(AsyncSession, session))
    request_hash = remnawave_create_request_hash({"username": "numeric-only"})
    decision = await service.begin(
        scope="remnawave-user:create",
        idempotency_key="numeric-only-request",
        request_hash=request_hash,
    )

    await service.mark_completed(decision.record, user_ref=RemnawaveUserRef(id=73))
    replay = await service.begin(
        scope="remnawave-user:create",
        idempotency_key="numeric-only-request",
        request_hash=request_hash,
    )

    assert replay.should_mutate is False
    assert service.completed_ref(replay.record) == RemnawaveUserRef(id=73)
    assert replay.record.response_payload == {"numeric_user_id": 73}
    assert "legacy_uuid" not in replay.record.response_payload


@pytest.mark.unit
async def test_generic_completion_reference_is_bounded_and_replayable_without_payload_secrets() -> None:
    session = _Session()
    service = RemnawaveMutationAttemptService(
        cast(AsyncSession, session),
        resource_type="remnawave_snippet_create",
    )
    decision = await service.begin(
        scope="remnawave-snippet:create",
        idempotency_key="snippet-create-1",
        request_hash=remnawave_create_request_hash({"name": "safe snippet"}),
    )

    await service.mark_completed_reference(
        decision.record,
        reference={"resource_name": "safe snippet", "settled": True},
    )

    assert service.completed_reference(decision.record) == {
        "resource_name": "safe snippet",
        "settled": True,
    }
    assert decision.record.status == "completed"
    assert session.flushes == 1


@pytest.mark.unit
async def test_stale_reconciliation_transition_cannot_downgrade_completed_attempt() -> None:
    session = _Session()
    service = RemnawaveMutationAttemptService(
        cast(AsyncSession, session),
        resource_type="partner_remnawave_profile_tags",
    )
    decision = await service.begin(
        scope="partner-remnawave:profile-tags",
        idempotency_key="partner-profile-terminal",
        request_hash=remnawave_create_request_hash({"tags": ["SAFE"]}),
    )
    reference: dict[str, str | int | bool] = {"resource_uuid": str(uuid4())}
    await service.mark_completed_reference(decision.record, reference=reference)

    await service.stage_reconciliation_required(decision.record)

    assert decision.record.status == "completed"
    assert decision.record.response_payload == reference
    assert session.flushes == 1


@pytest.mark.unit
async def test_rejected_attempt_cannot_be_overwritten_by_stale_completion() -> None:
    session = _Session()
    service = RemnawaveMutationAttemptService(
        cast(AsyncSession, session),
        resource_type="remnawave_node_integration_create",
    )
    decision = await service.begin(
        scope="remnawave-operator:integration:create",
        idempotency_key="operator-integration-terminal",
        request_hash=remnawave_create_request_hash({"name": "safe"}),
    )
    await service.mark_rejected(decision.record, error_code="provider_request_rejected")

    with pytest.raises(RemnawaveCreateAttemptConflict, match="cannot be completed"):
        await service.mark_completed_reference(
            decision.record,
            reference={"resource_uuid": str(uuid4())},
        )

    assert decision.record.status == "rejected"
    assert decision.record.response_payload == {"error_code": "provider_request_rejected"}


@pytest.mark.unit
@pytest.mark.parametrize("unsafe_key", ["api_token", "password", "private_key", "client_secret"])
async def test_generic_completion_reference_rejects_secret_bearing_keys(unsafe_key: str) -> None:
    session = _Session()
    service = RemnawaveMutationAttemptService(
        cast(AsyncSession, session),
        resource_type="remnawave_integration_create",
    )
    decision = await service.begin(
        scope="remnawave-integration:create",
        idempotency_key="integration-create-1",
        request_hash=remnawave_create_request_hash({"name": "integration"}),
    )

    with pytest.raises(ValueError, match="key is unsafe"):
        await service.mark_completed_reference(
            decision.record,
            reference={unsafe_key: "must-not-persist"},
        )

    assert decision.record.status == "pending"
    assert decision.record.response_payload == {}


@pytest.mark.unit
async def test_definitive_rejection_is_terminal_and_contains_only_safe_code() -> None:
    session = _Session()
    service = RemnawaveMutationAttemptService(
        cast(AsyncSession, session),
        resource_type="remnawave_shared_list_update",
    )
    decision = await service.begin(
        scope="remnawave-shared-list:update",
        idempotency_key="shared-list-update-1",
        request_hash=remnawave_create_request_hash({"name": "blocked"}),
    )

    await service.mark_rejected(decision.record, error_code="provider_validation_rejected")

    assert decision.record.status == "rejected"
    assert decision.record.response_payload == {"error_code": "provider_validation_rejected"}
    assert session.commits == 2


class _ConcurrentStore:
    def __init__(self) -> None:
        self.record = None
        self.initial_reads = 0
        self.initial_reads_complete = asyncio.Event()


class _ConcurrentSession:
    def __init__(self, store: _ConcurrentStore) -> None:
        self.store = store
        self.pending_record = None

    async def execute(self, _statement):
        snapshot = self.store.record
        if self.store.record is None and self.pending_record is None:
            self.store.initial_reads += 1
            if self.store.initial_reads == 2:
                self.store.initial_reads_complete.set()
            await self.store.initial_reads_complete.wait()
        return _ScalarResult(snapshot if snapshot is not None else self.store.record if self.pending_record else None)

    def add(self, record) -> None:
        self.pending_record = record

    async def commit(self) -> None:
        if self.pending_record is None:
            return
        if self.store.record is not None and self.store.record is not self.pending_record:
            raise IntegrityError("concurrent create attempt", {}, RuntimeError("unique conflict"))
        self.store.record = self.pending_record
        self.pending_record = None

    async def rollback(self) -> None:
        self.pending_record = None

    async def flush(self) -> None:
        return None


@pytest.mark.unit
async def test_create_attempt_concurrency_elects_exactly_one_provider_mutation_winner() -> None:
    store = _ConcurrentStore()
    sessions = [_ConcurrentSession(store), _ConcurrentSession(store)]
    request_hash = remnawave_create_request_hash({"customer_account_id": str(uuid4())})

    decisions = await asyncio.gather(
        *(
            RemnawaveCreateAttemptService(cast(AsyncSession, session)).begin(
                scope="remnawave-trial:create",
                idempotency_key="same-customer",
                request_hash=request_hash,
            )
            for session in sessions
        )
    )

    assert sum(decision.should_mutate for decision in decisions) == 1
    assert store.record.status == "pending"


class _PairSession:
    def __init__(self, records: dict[tuple[str, str], object]) -> None:
        self.records = records
        self.pending: list[object] = []

    async def execute(self, statement):
        params = statement.compile().params
        scope = next(value for key, value in params.items() if key.startswith("scope_"))
        idempotency_key = next(value for key, value in params.items() if key.startswith("idempotency_key_"))
        return _ScalarResult(self.records.get((scope, idempotency_key)))

    def add_all(self, records) -> None:
        self.pending.extend(records)

    async def commit(self) -> None:
        for record in self.pending:
            self.records[(record.scope, record.idempotency_key)] = record
        self.pending.clear()

    async def rollback(self) -> None:
        self.pending.clear()

    async def flush(self) -> None:
        return None


@pytest.mark.unit
async def test_gift_level_ambiguous_claim_blocks_a_different_customer_before_provider_retry() -> None:
    records: dict[tuple[str, str], object] = {}
    gift_code_id = uuid4()
    first_customer_id = uuid4()
    first_hash = remnawave_create_request_hash(
        {"gift_code_id": str(gift_code_id), "customer_account_id": str(first_customer_id)}
    )
    first_service = RemnawaveGiftProvisioningAttemptService(
        cast(AsyncSession, _PairSession(records)),
        customer_resource_type="remnawave_user_create",
    )
    first = await first_service.begin(
        gift_code_id=gift_code_id,
        customer_account_id=first_customer_id,
        customer_scope="remnawave-customer:create",
        customer_idempotency_key="first-customer",
        request_hash=first_hash,
    )
    await first_service.mark_reconciliation_required(first)

    second_customer_id = uuid4()
    second_service = RemnawaveGiftProvisioningAttemptService(
        cast(AsyncSession, _PairSession(records)),
        customer_resource_type="remnawave_user_create",
    )
    with pytest.raises(RemnawaveCreateAttemptConflict):
        await second_service.begin(
            gift_code_id=gift_code_id,
            customer_account_id=second_customer_id,
            customer_scope="remnawave-customer:create",
            customer_idempotency_key="second-customer",
            request_hash=remnawave_create_request_hash(
                {"gift_code_id": str(gift_code_id), "customer_account_id": str(second_customer_id)}
            ),
        )

    assert len(records) == 2
    assert {record.status for record in records.values()} == {"reconciliation_required"}
