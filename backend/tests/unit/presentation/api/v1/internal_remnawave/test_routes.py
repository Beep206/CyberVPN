from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from fastapi import HTTPException
from pydantic import SecretStr, ValidationError

from src.config.settings import settings
from src.presentation.api.v1.internal_remnawave.routes import (
    InternalAutoRenewEligibilityRequest,
    InternalRemnawaveDeadLetterRequest,
    InternalRemnawaveStreamGapRequest,
    list_auto_renew_eligible_users,
    require_backend_internal_secret,
    resolve_customer_for_numeric_user,
    resolve_numeric_user_for_worker,
)


class _Headers:
    def __init__(self, values: list[str]) -> None:
        self._values = values

    def getlist(self, _name: str) -> list[str]:
        return self._values


def _identity_mapping(
    customer_id,
    *,
    numeric_id: int,
    legacy_uuid,
    state: str = "mapped",
) -> SimpleNamespace:
    return SimpleNamespace(
        subject_type="mobile_user",
        subject_id=customer_id,
        reconciliation_state=state,
        numeric_user_id=numeric_id,
        legacy_uuid=None if legacy_uuid is None else str(legacy_uuid),
    )


def _identity_result(value: object | None) -> SimpleNamespace:
    values = [] if value is None else [value]
    return SimpleNamespace(scalars=lambda: SimpleNamespace(all=lambda: values))


@pytest.mark.unit
def test_internal_resolver_rejects_duplicate_secret_headers(monkeypatch) -> None:
    monkeypatch.setattr(settings, "backend_internal_secret", SecretStr("strong-internal-secret"))
    request = SimpleNamespace(headers=_Headers(["strong-internal-secret", "strong-internal-secret"]))

    with pytest.raises(HTTPException) as exc_info:
        require_backend_internal_secret(request)

    assert exc_info.value.status_code == 401


@pytest.mark.unit
async def test_internal_resolver_returns_numeric_id_for_exact_dual_mapping() -> None:
    customer_id = uuid4()
    legacy_uuid = uuid4()
    session = AsyncMock()
    session.get.return_value = SimpleNamespace(
        id=customer_id,
        remnawave_user_id=42,
        remnawave_uuid=str(legacy_uuid),
    )
    state_result = _identity_result(_identity_mapping(customer_id, numeric_id=42, legacy_uuid=legacy_uuid))
    session.execute.return_value = state_result

    response = await resolve_numeric_user_for_worker(customer_id=customer_id, db=session)

    assert response.model_dump() == {
        "customer_id": customer_id,
        "remnawave_user_id": 42,
        "reconciliation_state": "mapped",
    }


@pytest.mark.unit
async def test_internal_resolver_fails_closed_before_reconciliation() -> None:
    customer_id = uuid4()
    session = AsyncMock()
    session.get.return_value = SimpleNamespace(id=customer_id, remnawave_user_id=None, remnawave_uuid=None)

    with pytest.raises(HTTPException) as exc_info:
        await resolve_numeric_user_for_worker(customer_id=customer_id, db=session)

    assert exc_info.value.status_code == 409


@pytest.mark.unit
@pytest.mark.parametrize(
    "reconciliation",
    [
        None,
        SimpleNamespace(reconciliation_state="pending", numeric_user_id=42),
        SimpleNamespace(reconciliation_state="conflict", numeric_user_id=42),
        SimpleNamespace(reconciliation_state="mapped", numeric_user_id=99),
    ],
)
async def test_internal_resolver_rejects_missing_incomplete_or_wrong_numeric_mapping(reconciliation) -> None:
    customer_id = uuid4()
    legacy_uuid = uuid4()
    session = AsyncMock()
    session.get.return_value = SimpleNamespace(
        id=customer_id,
        remnawave_user_id=42,
        remnawave_uuid=str(legacy_uuid),
    )
    if reconciliation is not None and not hasattr(reconciliation, "legacy_uuid"):
        reconciliation.legacy_uuid = str(legacy_uuid)
    if reconciliation is not None:
        reconciliation.subject_type = "mobile_user"
        reconciliation.subject_id = customer_id
    session.execute.return_value = _identity_result(reconciliation)

    with pytest.raises(HTTPException) as exc_info:
        await resolve_numeric_user_for_worker(customer_id=customer_id, db=session)

    assert exc_info.value.status_code == 409


@pytest.mark.unit
async def test_internal_resolver_accepts_exact_numeric_only_mapping() -> None:
    customer_id = uuid4()
    session = AsyncMock()
    session.get.return_value = SimpleNamespace(
        id=customer_id,
        remnawave_user_id=42,
        remnawave_uuid=None,
    )
    session.execute.return_value = _identity_result(_identity_mapping(customer_id, numeric_id=42, legacy_uuid=None))

    response = await resolve_numeric_user_for_worker(customer_id=customer_id, db=session)

    assert response.remnawave_user_id == 42


@pytest.mark.unit
async def test_internal_resolver_rejects_invalid_local_legacy_mapping() -> None:
    customer_id = uuid4()
    session = AsyncMock()
    session.get.return_value = SimpleNamespace(
        id=customer_id,
        remnawave_user_id=42,
        remnawave_uuid="not-a-uuid",
    )

    with pytest.raises(HTTPException) as exc_info:
        await resolve_numeric_user_for_worker(customer_id=customer_id, db=session)

    assert exc_info.value.status_code == 409


@pytest.mark.unit
async def test_internal_resolver_rejects_wrong_legacy_uuid_mapping() -> None:
    customer_id = uuid4()
    session = AsyncMock()
    session.get.return_value = SimpleNamespace(
        id=customer_id,
        remnawave_user_id=42,
        remnawave_uuid=str(uuid4()),
    )
    session.execute.return_value = _identity_result(_identity_mapping(customer_id, numeric_id=42, legacy_uuid=uuid4()))

    with pytest.raises(HTTPException) as exc_info:
        await resolve_numeric_user_for_worker(customer_id=customer_id, db=session)

    assert exc_info.value.status_code == 409


@pytest.mark.unit
async def test_internal_reverse_resolver_returns_customer_for_numeric_id() -> None:
    customer_id = uuid4()
    legacy_uuid = uuid4()
    session = AsyncMock()
    customer_result = SimpleNamespace(
        scalar_one_or_none=lambda: SimpleNamespace(
            id=customer_id,
            remnawave_user_id=42,
            remnawave_uuid=str(legacy_uuid),
        )
    )
    state_result = _identity_result(_identity_mapping(customer_id, numeric_id=42, legacy_uuid=legacy_uuid))
    session.execute.side_effect = [customer_result, state_result]

    response = await resolve_customer_for_numeric_user(remnawave_user_id=42, db=session)

    assert response.customer_id == customer_id
    assert response.remnawave_user_id == 42


@pytest.mark.unit
async def test_internal_reverse_resolver_rejects_foreign_numeric_mapping() -> None:
    customer_id = uuid4()
    legacy_uuid = uuid4()
    session = AsyncMock()
    customer_result = SimpleNamespace(
        scalar_one_or_none=lambda: SimpleNamespace(
            id=customer_id,
            remnawave_user_id=42,
            remnawave_uuid=str(legacy_uuid),
        )
    )
    foreign_mapping = _identity_mapping(customer_id, numeric_id=99, legacy_uuid=legacy_uuid)
    state_result = _identity_result(foreign_mapping)
    session.execute.side_effect = [customer_result, state_result]

    with pytest.raises(HTTPException) as exc_info:
        await resolve_customer_for_numeric_user(remnawave_user_id=42, db=session)

    assert exc_info.value.status_code == 409


@pytest.mark.unit
async def test_auto_renew_eligibility_requires_exact_reconciliation_numeric_id(monkeypatch) -> None:
    monkeypatch.setattr(settings, "payment_autorenewal_enabled", True)
    session = AsyncMock()
    session.execute.return_value = SimpleNamespace(scalars=lambda: SimpleNamespace(all=lambda: [42]))

    response = await list_auto_renew_eligible_users(
        payload=InternalAutoRenewEligibilityRequest(user_ids=[42]),
        db=session,
    )

    statement = str(session.execute.await_args.args[0])
    assert "remnawave_identity_reconciliations.numeric_user_id = mobile_users.remnawave_user_id" in statement
    assert "remnawave_identity_reconciliations.legacy_uuid = mobile_users.remnawave_uuid" in statement
    assert "mobile_users.remnawave_uuid IS NULL" in statement
    assert "remnawave_identity_reconciliations.legacy_uuid IS NULL" in statement
    assert response.eligible_user_ids == [42]


@pytest.mark.unit
async def test_auto_renew_eligibility_is_empty_when_global_feature_is_disabled(monkeypatch) -> None:
    monkeypatch.setattr(settings, "payment_autorenewal_enabled", False)
    session = AsyncMock()

    response = await list_auto_renew_eligible_users(
        payload=InternalAutoRenewEligibilityRequest(user_ids=[42, 43]),
        db=session,
    )

    assert response.eligible_user_ids == []
    session.execute.assert_not_awaited()


@pytest.mark.unit
def test_dead_letter_contract_forbids_raw_payload_fields() -> None:
    with pytest.raises(ValidationError):
        InternalRemnawaveDeadLetterRequest.model_validate(
            {
                "stream_name": "user_usage",
                "message_id": "1725024000000-9",
                "schema_version": "1",
                "error_type": "schema_validation",
                "redacted_reason": "invalid_record",
                "payload_fingerprint": "a" * 64,
                "attempts": 3,
                "raw_payload": {"request_ip": "203.0.113.99"},
            }
        )


@pytest.mark.unit
def test_stream_gap_contract_is_bounded_exact_and_forbids_raw_payload() -> None:
    with pytest.raises(ValidationError):
        InternalRemnawaveStreamGapRequest.model_validate(
            {
                "stream_name": "user_usage",
                "missing_message_ids": ["1725024000000-1", "1725024000000-1"],
                "detected_at": "2026-08-30T14:00:00Z",
            }
        )

    with pytest.raises(ValidationError):
        InternalRemnawaveStreamGapRequest.model_validate(
            {
                "stream_name": "node_connections",
                "missing_message_ids": ["1725024000000-1"],
                "detected_at": "2026-08-30T14:00:00Z",
                "raw_payload": {"users": [{"ip": "203.0.113.9"}]},
            }
        )
