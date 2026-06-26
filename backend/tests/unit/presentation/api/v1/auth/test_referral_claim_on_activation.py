"""Customer web referral claim hook tests."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock
from uuid import uuid4

import pytest
from fastapi import Request, Response


class _FakeNestedTransaction:
    def __init__(self, calls: list[str]) -> None:
        self._calls = calls

    async def __aenter__(self):
        self._calls.append("begin_nested")
        return self

    async def __aexit__(self, exc_type, _exc, _tb):
        self._calls.append(f"exit:{exc_type.__name__ if exc_type else 'none'}")
        return False


class _FakeSession:
    def __init__(self, calls: list[str]) -> None:
        self._calls = calls

    def begin_nested(self):
        return _FakeNestedTransaction(self._calls)


@pytest.mark.asyncio
async def test_customer_web_referral_claim_runs_after_activation_and_clears_cookie(monkeypatch) -> None:
    from src.presentation.api.v1.auth import routes

    user_id = uuid4()
    calls: list[str] = []
    captured_command = None
    fake_db = _FakeSession(calls)

    class FakeClaimReferralAttributionUseCase:
        def __init__(self, db):
            assert db is fake_db

        async def execute(self, command):
            nonlocal captured_command
            captured_command = command
            return SimpleNamespace(clear_cookie=True)

    monkeypatch.setattr(routes, "ClaimReferralAttributionUseCase", FakeClaimReferralAttributionUseCase)

    request = MagicMock(spec=Request)
    request.cookies = {routes.REFERRAL_ATTRIBUTION_COOKIE_NAME: "cookie-token-42"}
    response = Response()

    await routes._claim_customer_web_referral_after_activation(
        db=fake_db,
        user=SimpleNamespace(id=user_id),
        mobile_user=SimpleNamespace(id=user_id),
        current_realm=SimpleNamespace(realm_type="customer"),
        http_request=request,
        response=response,
    )

    assert calls == ["begin_nested", "exit:none"]
    assert captured_command is not None
    assert captured_command.user_id == user_id
    assert captured_command.cookie_token == "cookie-token-42"
    set_cookie = response.headers["set-cookie"]
    assert routes.REFERRAL_ATTRIBUTION_COOKIE_NAME in set_cookie
    assert "Max-Age=0" in set_cookie


@pytest.mark.asyncio
async def test_customer_web_referral_claim_skips_without_customer_cookie(monkeypatch) -> None:
    from src.presentation.api.v1.auth import routes

    class UnexpectedClaimReferralAttributionUseCase:
        def __init__(self, _db):
            raise AssertionError("claim use case must not be constructed without a pending cookie")

    monkeypatch.setattr(routes, "ClaimReferralAttributionUseCase", UnexpectedClaimReferralAttributionUseCase)

    request = MagicMock(spec=Request)
    request.cookies = {}
    response = Response()

    await routes._claim_customer_web_referral_after_activation(
        db=_FakeSession([]),
        user=SimpleNamespace(id=uuid4()),
        mobile_user=SimpleNamespace(id=uuid4()),
        current_realm=SimpleNamespace(realm_type="customer"),
        http_request=request,
        response=response,
    )

    assert "set-cookie" not in response.headers
