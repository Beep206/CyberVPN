from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

import pytest
from fastapi import Response
from pydantic import ValidationError
from starlette.requests import Request

from src.application.use_cases.private_catalog.preflight import (
    PrivateCatalogApplicationResult,
    PrivateCatalogGrantResult,
    PrivateCatalogOfferResult,
    PrivateCatalogPreflightResult,
    PrivateCatalogRiskResult,
)
from src.presentation.api.shared.private_catalog_session import PRIVATE_CATALOG_ANONYMOUS_SESSION_COOKIE
from src.presentation.api.v3 import growth_code_sets

CODE_SET_ID = UUID("20000000-0000-0000-0000-000000000001")
GRANT_ID = UUID("20000000-0000-0000-0000-000000000002")
PLAN_ID = UUID("20000000-0000-0000-0000-000000000003")


class RecordingUseCase:
    def __init__(self) -> None:
        self.commands = []

    async def execute(self, command):
        self.commands.append(command)
        return PrivateCatalogPreflightResult(
            code_set_id=CODE_SET_ID,
            code_set_hash="8" * 64,
            status="accepted",
            applications=(
                PrivateCatalogApplicationResult(
                    client_slot_id="slot-private",
                    masked_code="PR-R...SS",
                    status="accepted",
                    roles=("catalog_access",),
                    message_key="growth.code.privateOfferUnlocked",
                ),
            ),
            private_catalog_grant=PrivateCatalogGrantResult(
                id=GRANT_ID,
                expires_at=datetime(2026, 6, 25, 12, 15, tzinfo=UTC),
            ),
            private_offers=(
                PrivateCatalogOfferResult(
                    plan_id=PLAN_ID,
                    display_name="RU Basic 90",
                    duration_days=90,
                    price_amount="990.00",
                    price_currency="RUB",
                    entitlement_summary={"devices_included": 3},
                    private_catalog_grant_id=GRANT_ID,
                ),
            ),
            risk=PrivateCatalogRiskResult(action="allow"),
        )


def _request(*, cookie: str | None = None) -> Request:
    headers = [(b"host", b"testserver")]
    if cookie is not None:
        headers.append((b"cookie", f"{PRIVATE_CATALOG_ANONYMOUS_SESSION_COOKIE}={cookie}".encode()))
    return Request({"type": "http", "method": "POST", "path": "/api/v3/growth/code-sets/preflight", "headers": headers})


@pytest.mark.asyncio
async def test_code_set_preflight_route_binds_anonymous_subject_to_server_cookie(monkeypatch) -> None:
    use_case = RecordingUseCase()
    monkeypatch.setattr(growth_code_sets, "_use_case", lambda _db: use_case)
    response = Response()

    result = await growth_code_sets.preflight_growth_code_set(
        payload=growth_code_sets.CodeSetPreflightRequest(
            codes=[
                growth_code_sets.CodeSetPreflightCodeRequest(
                    code="PR-RU90-ACCESS",
                    client_slot_id="slot-private",
                )
            ],
            storefront_key="ru",
            channel="WEB",
            currency="rub",
            anonymous_session_id="client-supplied-id",
        ),
        request=_request(),
        response=response,
        db=object(),
        user_id=None,
    )

    assert use_case.commands[0].user_id is None
    assert use_case.commands[0].anonymous_session_id is not None
    assert use_case.commands[0].anonymous_session_id != "client-supplied-id"
    assert use_case.commands[0].channel == "web"
    assert use_case.commands[0].currency == "RUB"
    assert response.headers["Cache-Control"] == "no-store, private"
    assert PRIVATE_CATALOG_ANONYMOUS_SESSION_COOKIE in response.headers["set-cookie"]
    assert result.status == "accepted"
    assert result.private_catalog_grant is not None
    assert result.private_catalog_grant.id == GRANT_ID
    assert result.private_offers[0].quote_handoff.private_catalog_grant_id == GRANT_ID


@pytest.mark.asyncio
async def test_code_set_preflight_route_binds_authenticated_user_without_anonymous_cookie(monkeypatch) -> None:
    use_case = RecordingUseCase()
    monkeypatch.setattr(growth_code_sets, "_use_case", lambda _db: use_case)
    response = Response()
    user_id = UUID("20000000-0000-0000-0000-000000000099")

    await growth_code_sets.preflight_growth_code_set(
        payload=growth_code_sets.CodeSetPreflightRequest(
            codes=[
                growth_code_sets.CodeSetPreflightCodeRequest(
                    code="PR-RU90-ACCESS",
                    client_slot_id="slot-private",
                )
            ],
            storefront_key="ru",
            channel="WEB",
            currency="rub",
            anonymous_session_id="client-supplied-id",
        ),
        request=_request(),
        response=response,
        db=object(),
        user_id=user_id,
    )

    assert use_case.commands[0].user_id == user_id
    assert use_case.commands[0].anonymous_session_id is None
    assert "set-cookie" not in response.headers


def test_code_set_preflight_request_forbids_user_id_mass_assignment() -> None:
    with pytest.raises(ValidationError):
        growth_code_sets.CodeSetPreflightRequest.model_validate(
            {
                "codes": [{"code": "PR-RU90-ACCESS", "client_slot_id": "slot-private"}],
                "storefront_key": "ru",
                "channel": "web",
                "currency": "RUB",
                "anonymous_session_id": "anon-checkout-1",
                "user_id": str(UUID("20000000-0000-0000-0000-000000000099")),
            }
        )
