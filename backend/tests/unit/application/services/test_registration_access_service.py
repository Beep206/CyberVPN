from __future__ import annotations

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from src.application.services.registration_access_service import RegistrationAccessGrantService
from src.infrastructure.database.models.customer_onboarding_model import RegistrationAccessGrantModel


def _grant() -> RegistrationAccessGrantModel:
    return RegistrationAccessGrantModel(
        id=uuid4(),
        token_hash="0" * 64,
        status="issued",
        role_key="viewer",
        auth_realm_id=uuid4(),
        issued_at=datetime.now(UTC),
        expires_at=datetime.now(UTC) + timedelta(hours=1),
        metadata_={"issuer": "test"},
    )


@pytest.mark.asyncio
async def test_registration_access_exchange_hashes_idempotency_and_allows_same_replay(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    grant = _grant()
    session = AsyncMock()
    service = RegistrationAccessGrantService(session)
    monkeypatch.setattr(service, "_get_by_token_hash", AsyncMock(return_value=grant))

    result = await service.exchange_for_browser(
        token="raw-registration-token",
        idempotency_key="raw-idempotency-key@example.test",
        host="Public.Example",
        auth_realm_id=grant.auth_realm_id,
    )

    assert result is not None
    assert grant.status == "exchanged"
    assert grant.metadata_["exchange_idempotency_key_hash"].startswith("hmac:")
    assert "exchange_idempotency_key" not in grant.metadata_
    assert "raw-idempotency-key@example.test" not in str(grant.metadata_)

    replay = await service.exchange_for_browser(
        token="raw-registration-token",
        idempotency_key="raw-idempotency-key@example.test",
        host="public.example",
        auth_realm_id=grant.auth_realm_id,
    )

    assert replay is not None
    assert replay.session_token == result.session_token
    assert session.flush.await_count == 1


@pytest.mark.asyncio
async def test_registration_access_registration_reservation_hashes_idempotency_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    grant = _grant()
    grant.status = "exchanged"
    grant.exchanged_at = datetime.now(UTC)
    grant.exchange_session_hash = "hash"
    grant.metadata_ = {"exchange_host": "public.example"}
    session = AsyncMock()
    service = RegistrationAccessGrantService(session)
    monkeypatch.setattr(service, "_get_by_exchange_session", AsyncMock(return_value=grant))

    data = await service.reserve_exchange_session_for_registration(
        session_token="ragx_v1_" + "a" * 64,
        reservation_id="reservation-1",
        host="public.example",
        registration_idempotency_key="raw-registration-idempotency-key",
    )

    assert data is not None
    assert grant.registration_idempotency_key is not None
    assert grant.registration_idempotency_key.startswith("hmac:")
    assert "raw-registration-idempotency-key" not in str(grant.registration_idempotency_key)
