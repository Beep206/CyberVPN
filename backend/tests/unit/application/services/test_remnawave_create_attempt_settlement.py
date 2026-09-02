from __future__ import annotations

from datetime import UTC, datetime
from typing import Protocol, cast
from unittest.mock import AsyncMock
from uuid import UUID, uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.services import remnawave_create_attempt_settlement as module
from src.application.services.remnawave_create_attempt_settlement import (
    CUSTOMER_CREATE_ATTEMPT_SCOPE,
    CUSTOMER_CREATE_RESOURCE_TYPE,
    RemnawaveCustomerCreateAttemptConflict,
    RemnawaveCustomerCreateAttemptNotFound,
    RemnawaveCustomerCreateAttemptSettlementService,
    canonical_customer_provider_usernames,
)
from src.application.services.remnawave_create_attempts import RemnawaveMutationAttemptService
from src.domain.entities.user import User
from src.domain.enums import UserStatus
from src.domain.value_objects.remnawave_user_ref import RemnawaveUserRef
from src.infrastructure.database.models.mobile_user_model import MobileUserModel
from src.infrastructure.database.models.partner_model import ApiIdempotencyRecordModel


class _ScalarResult:
    def __init__(self, value: object) -> None:
        self._value = value

    def scalars(self) -> _ScalarResult:
        return self

    def one_or_none(self) -> object:
        return self._value


class _StatementDescription(Protocol):
    column_descriptions: list[dict[str, object]]


class _Session:
    def __init__(self, *, attempt: ApiIdempotencyRecordModel | None, customer: MobileUserModel | None) -> None:
        self.attempt = attempt
        self.customer = customer
        self.statements: list[object] = []
        self.flush_count = 0

    async def execute(self, statement: object) -> _ScalarResult:
        self.statements.append(statement)
        column_descriptions = cast(_StatementDescription, statement).column_descriptions
        entity = column_descriptions[0].get("entity")
        if entity is ApiIdempotencyRecordModel:
            return _ScalarResult(self.attempt)
        if entity is MobileUserModel:
            return _ScalarResult(self.customer)
        raise AssertionError(f"Unexpected statement: {statement}")

    async def flush(self) -> None:
        self.flush_count += 1


class _ProviderUsers:
    def __init__(self, user: User | None) -> None:
        self.user = user
        self.refs: list[RemnawaveUserRef] = []

    async def get_by_ref(self, ref: RemnawaveUserRef) -> User | None:
        self.refs.append(ref)
        return self.user


def _attempt(
    *,
    customer_id: UUID | None = None,
    status: str = "reconciliation_required",
    scope: str = CUSTOMER_CREATE_ATTEMPT_SCOPE,
    resource_type: str = CUSTOMER_CREATE_RESOURCE_TYPE,
    response_payload: dict[str, object] | None = None,
) -> ApiIdempotencyRecordModel:
    return ApiIdempotencyRecordModel(
        id=uuid4(),
        scope=scope,
        idempotency_key="a" * 64,
        resource_type=resource_type,
        resource_id=customer_id,
        request_hash="b" * 64,
        response_payload=response_payload or {},
        status=status,
        expires_at=None,
    )


def _customer(*, customer_id: UUID | None = None, status: str = "active") -> MobileUserModel:
    return MobileUserModel(
        id=customer_id or uuid4(),
        public_uid=123456789012,
        email="customer@example.com",
        username="customer-local",
        password_hash="not-used",
        status=status,
        is_active=status == "active",
        remnawave_user_id=None,
        remnawave_uuid=None,
    )


def _provider_user(
    customer_id: UUID,
    *,
    numeric_id: int = 731,
    legacy_uuid: UUID | None = None,
    username: str | None = None,
    email: str | None = "customer@example.com",
) -> User:
    now = datetime(2026, 9, 1, tzinfo=UTC)
    return User(
        uuid=legacy_uuid,
        username=username or f"cvpn_t_{customer_id.hex[:28]}",
        status=UserStatus.ACTIVE,
        short_uuid="safe-short-id",
        created_at=now,
        updated_at=now,
        remnawave_id=numeric_id,
        email=email,
    )


@pytest.mark.unit
@pytest.mark.asyncio
async def test_settle_locks_attempt_and_customer_then_maps_and_completes_atomically(monkeypatch) -> None:
    customer = _customer()
    legacy_uuid = uuid4()
    attempt = _attempt(customer_id=customer.id)
    session = _Session(attempt=attempt, customer=customer)
    provider = _ProviderUsers(_provider_user(customer.id, legacy_uuid=legacy_uuid))
    persisted: list[dict[str, object]] = []
    registry_lock = AsyncMock()

    async def persist(_session: object, **kwargs: object) -> RemnawaveUserRef:
        persisted.append(kwargs)
        customer.remnawave_user_id = 731
        customer.remnawave_uuid = str(legacy_uuid)
        return RemnawaveUserRef(id=731, legacy_uuid=legacy_uuid)

    monkeypatch.setattr(module, "persist_runtime_mapped_mobile_identity", persist)
    monkeypatch.setattr(module, "_acquire_remnawave_identity_registry_lock", registry_lock)
    result = await RemnawaveCustomerCreateAttemptSettlementService(
        cast(AsyncSession, session),
        provider,
    ).settle(
        attempt_id=attempt.id,
        provider_numeric_user_id=731,
        provider_legacy_uuid=legacy_uuid,
    )

    assert result.changed is True
    assert result.state == "completed"
    assert result.user_ref == RemnawaveUserRef(id=731, legacy_uuid=legacy_uuid)
    assert attempt.status == "completed"
    assert attempt.response_payload == {"numeric_user_id": 731, "legacy_uuid": str(legacy_uuid)}
    assert provider.refs == [RemnawaveUserRef(id=731, legacy_uuid=legacy_uuid)]
    registry_lock.assert_awaited_once_with(cast(AsyncSession, session), shared=True)
    assert persisted == [
        {
            "customer": customer,
            "remnawave_user_id": 731,
            "remnawave_uuid": legacy_uuid,
            "source": "admin_customer_create_settlement",
        }
    ]
    # Settlement locks attempt -> customer, then the shared monotonic marker
    # transition re-reads the already-held attempt row before completion.
    assert len(session.statements) == 3
    assert all("FOR UPDATE" in str(statement) for statement in session.statements)
    assert session.flush_count == 1


@pytest.mark.unit
@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("provider_user", "legacy_input"),
    [
        (lambda customer_id: _provider_user(customer_id, numeric_id=999), None),
        (lambda customer_id: _provider_user(customer_id, username="cvpn_t_someone_else"), None),
        (lambda customer_id: _provider_user(customer_id, email="someone@example.com"), None),
        (lambda customer_id: _provider_user(customer_id, legacy_uuid=uuid4()), uuid4()),
        (lambda customer_id: None, None),
    ],
)
async def test_settle_rejects_missing_or_noncanonical_provider_identity(
    monkeypatch,
    provider_user,
    legacy_input: UUID | None,
) -> None:
    customer = _customer()
    attempt = _attempt(customer_id=customer.id)
    persist = AsyncMock()
    monkeypatch.setattr(module, "persist_runtime_mapped_mobile_identity", persist)

    with pytest.raises(RemnawaveCustomerCreateAttemptConflict):
        await RemnawaveCustomerCreateAttemptSettlementService(
            cast(AsyncSession, _Session(attempt=attempt, customer=customer)),
            _ProviderUsers(provider_user(customer.id)),
        ).settle(
            attempt_id=attempt.id,
            provider_numeric_user_id=731,
            provider_legacy_uuid=legacy_input,
        )

    persist.assert_not_awaited()
    assert attempt.status == "reconciliation_required"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_placeholder_email_is_verified_against_exact_customer_derived_username(monkeypatch) -> None:
    customer = _customer()
    customer.email = "tg123@telegram.local"
    attempt = _attempt(customer_id=customer.id)
    username = f"cvpn_g_{customer.id.hex[:28]}"
    provider_user = _provider_user(
        customer.id,
        username=username,
        email=f"{username}@cyber-vpn.net",
    )
    monkeypatch.setattr(
        module,
        "persist_runtime_mapped_mobile_identity",
        AsyncMock(return_value=RemnawaveUserRef(id=731)),
    )

    result = await RemnawaveCustomerCreateAttemptSettlementService(
        cast(AsyncSession, _Session(attempt=attempt, customer=customer)),
        _ProviderUsers(provider_user),
    ).settle(attempt_id=attempt.id, provider_numeric_user_id=731, provider_legacy_uuid=None)

    assert result.state == "completed"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_pending_attempt_cannot_be_settled_while_original_create_may_still_be_live(monkeypatch) -> None:
    customer = _customer()
    attempt = _attempt(customer_id=customer.id, status="pending")
    provider = _ProviderUsers(_provider_user(customer.id))
    persist = AsyncMock()
    monkeypatch.setattr(module, "persist_runtime_mapped_mobile_identity", persist)

    with pytest.raises(RemnawaveCustomerCreateAttemptConflict, match="Only reconciliation-required"):
        await RemnawaveCustomerCreateAttemptSettlementService(
            cast(AsyncSession, _Session(attempt=attempt, customer=customer)),
            provider,
        ).settle(attempt_id=attempt.id, provider_numeric_user_id=731, provider_legacy_uuid=None)

    assert provider.refs == []
    persist.assert_not_awaited()
    assert attempt.status == "pending"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_completed_settlement_is_idempotent_without_provider_read_or_second_mapping(monkeypatch) -> None:
    customer = _customer()
    legacy_uuid = uuid4()
    customer.remnawave_user_id = 731
    customer.remnawave_uuid = str(legacy_uuid)
    attempt = _attempt(
        customer_id=customer.id,
        status="completed",
        response_payload={"numeric_user_id": 731, "legacy_uuid": str(legacy_uuid)},
    )
    provider = _ProviderUsers(None)
    persist = AsyncMock()
    monkeypatch.setattr(module, "persist_runtime_mapped_mobile_identity", persist)
    monkeypatch.setattr(
        module,
        "resolve_exact_mapped_mobile_user_ref",
        AsyncMock(return_value=RemnawaveUserRef(id=731, legacy_uuid=legacy_uuid)),
    )

    result = await RemnawaveCustomerCreateAttemptSettlementService(
        cast(AsyncSession, _Session(attempt=attempt, customer=customer)),
        provider,
    ).settle(
        attempt_id=attempt.id,
        provider_numeric_user_id=731,
        provider_legacy_uuid=None,
    )

    assert result.changed is False
    assert provider.refs == []
    persist.assert_not_awaited()


@pytest.mark.unit
@pytest.mark.asyncio
@pytest.mark.parametrize("status", ["pending", "reconciliation_required", "completed"])
async def test_reopen_refuses_every_non_rejected_state(status: str) -> None:
    customer = _customer()
    attempt = _attempt(customer_id=customer.id, status=status)

    with pytest.raises(RemnawaveCustomerCreateAttemptConflict):
        await RemnawaveCustomerCreateAttemptSettlementService(
            cast(AsyncSession, _Session(attempt=attempt, customer=customer)),
            None,
        ).reopen(attempt_id=attempt.id)

    assert attempt.status == status


@pytest.mark.unit
@pytest.mark.asyncio
async def test_reopen_moves_only_rejected_to_non_mutating_reconciliation_state() -> None:
    customer = _customer()
    attempt = _attempt(
        customer_id=customer.id,
        status="rejected",
        response_payload={"error_code": "provider_validation_rejected"},
    )
    session = _Session(attempt=attempt, customer=customer)

    result = await RemnawaveCustomerCreateAttemptSettlementService(
        cast(AsyncSession, session),
        None,
    ).reopen(attempt_id=attempt.id)

    decision = RemnawaveMutationAttemptService._decision_for_existing(
        attempt,
        request_hash=attempt.request_hash or "",
    )
    assert result.state == "reconciliation_required"
    assert attempt.status == "reconciliation_required"
    assert attempt.response_payload == {}
    assert decision.should_mutate is False
    assert session.flush_count == 1


@pytest.mark.unit
@pytest.mark.asyncio
async def test_deleted_customer_cannot_be_settled_or_reopened(monkeypatch) -> None:
    customer = _customer(status="deleted")
    settle_attempt = _attempt(customer_id=customer.id)
    reopen_attempt = _attempt(customer_id=customer.id, status="rejected")
    persist = AsyncMock()
    monkeypatch.setattr(module, "persist_runtime_mapped_mobile_identity", persist)

    with pytest.raises(RemnawaveCustomerCreateAttemptConflict):
        await RemnawaveCustomerCreateAttemptSettlementService(
            cast(AsyncSession, _Session(attempt=settle_attempt, customer=customer)),
            _ProviderUsers(_provider_user(customer.id)),
        ).settle(attempt_id=settle_attempt.id, provider_numeric_user_id=731, provider_legacy_uuid=None)
    with pytest.raises(RemnawaveCustomerCreateAttemptConflict):
        await RemnawaveCustomerCreateAttemptSettlementService(
            cast(AsyncSession, _Session(attempt=reopen_attempt, customer=customer)),
            None,
        ).reopen(attempt_id=reopen_attempt.id)

    persist.assert_not_awaited()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_non_customer_attempt_uuid_is_hidden_as_not_found() -> None:
    service = RemnawaveCustomerCreateAttemptSettlementService(
        cast(AsyncSession, _Session(attempt=None, customer=None)),
        None,
    )

    with pytest.raises(RemnawaveCustomerCreateAttemptNotFound):
        await service.reopen(attempt_id=uuid4())


@pytest.mark.unit
def test_canonical_identity_set_is_bounded_to_known_customer_create_flows() -> None:
    customer_id = uuid4()

    assert canonical_customer_provider_usernames(customer_id) == {
        f"cvpn_t_{customer_id.hex[:28]}",
        f"cvpn_p_{customer_id.hex[:28]}",
        f"cvpn_m_{customer_id.hex[:28]}",
        f"cvpn_g_{customer_id.hex[:28]}",
        f"cvpn_ts_{customer_id.hex[:27]}",
    }
