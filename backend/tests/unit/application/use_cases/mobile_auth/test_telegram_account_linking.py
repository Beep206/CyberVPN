"""Unit tests for mobile Telegram bot account linking."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from sqlalchemy.exc import IntegrityError

from src.application.use_cases.mobile_auth import telegram_account_linking as module
from src.application.use_cases.mobile_auth.telegram_account_linking import (
    MobileTelegramAccountLinkConflictError,
    MobileTelegramAccountLinkingUseCase,
)


class _FakeMobileUserRepository:
    def __init__(self, *, user: object | None, existing_user: object | None = None) -> None:
        self.user = user
        self.existing_user = existing_user

    async def get_by_id(self, user_id):
        if self.user is not None and self.user.id == user_id:
            return self.user
        return None

    async def get_by_telegram_id(self, telegram_id: int):
        if self.existing_user is not None and self.existing_user.telegram_id == telegram_id:
            return self.existing_user
        return None


def _make_user(**overrides: object) -> SimpleNamespace:
    data = {
        "id": uuid4(),
        "telegram_id": None,
        "telegram_username": None,
        "telegram_subject": "telegram-oidc-subject",
        "email": "customer@example.com",
    }
    data.update(overrides)
    return SimpleNamespace(**data)


def _build_use_case(monkeypatch: pytest.MonkeyPatch, repo: _FakeMobileUserRepository, session: object):
    monkeypatch.setattr(module, "MobileUserRepository", lambda _session: repo)
    return MobileTelegramAccountLinkingUseCase(session)


@pytest.mark.unit
async def test_link_account_updates_mobile_user_without_touching_telegram_subject(monkeypatch: pytest.MonkeyPatch):
    user = _make_user()
    session = SimpleNamespace(flush=AsyncMock())
    repo = _FakeMobileUserRepository(user=user)
    use_case = _build_use_case(monkeypatch, repo, session)

    result = await use_case.link_account(user_id=user.id, telegram_id="424242", username="alice")

    assert result is user
    assert user.telegram_id == 424242
    assert user.telegram_username == "alice"
    assert user.telegram_subject == "telegram-oidc-subject"
    session.flush.assert_awaited_once()


@pytest.mark.unit
async def test_link_account_is_idempotent_for_same_telegram_id(monkeypatch: pytest.MonkeyPatch):
    user = _make_user(telegram_id=424242, telegram_username="old_name")
    session = SimpleNamespace(flush=AsyncMock())
    repo = _FakeMobileUserRepository(user=user, existing_user=user)
    use_case = _build_use_case(monkeypatch, repo, session)

    await use_case.link_account(user_id=user.id, telegram_id=424242, username="alice")

    assert user.telegram_id == 424242
    assert user.telegram_username == "alice"
    session.flush.assert_awaited_once()


@pytest.mark.unit
async def test_link_account_rejects_telegram_id_owned_by_another_mobile_user(monkeypatch: pytest.MonkeyPatch):
    user = _make_user()
    other_user = _make_user(telegram_id=424242)
    session = SimpleNamespace(flush=AsyncMock())
    repo = _FakeMobileUserRepository(user=user, existing_user=other_user)
    use_case = _build_use_case(monkeypatch, repo, session)

    with pytest.raises(MobileTelegramAccountLinkConflictError):
        await use_case.link_account(user_id=user.id, telegram_id=424242, username="alice")

    session.flush.assert_not_awaited()


@pytest.mark.unit
async def test_link_account_rejects_replacing_existing_telegram_id(monkeypatch: pytest.MonkeyPatch):
    user = _make_user(telegram_id=111111)
    session = SimpleNamespace(flush=AsyncMock())
    repo = _FakeMobileUserRepository(user=user)
    use_case = _build_use_case(monkeypatch, repo, session)

    with pytest.raises(MobileTelegramAccountLinkConflictError):
        await use_case.link_account(user_id=user.id, telegram_id=424242, username="alice")

    session.flush.assert_not_awaited()


@pytest.mark.unit
async def test_link_account_rejects_invalid_telegram_id(monkeypatch: pytest.MonkeyPatch):
    user = _make_user()
    session = SimpleNamespace(flush=AsyncMock())
    repo = _FakeMobileUserRepository(user=user)
    use_case = _build_use_case(monkeypatch, repo, session)

    with pytest.raises(MobileTelegramAccountLinkConflictError):
        await use_case.link_account(user_id=user.id, telegram_id="not-a-number", username="alice")

    session.flush.assert_not_awaited()


@pytest.mark.unit
async def test_link_account_converts_integrity_error_to_conflict(monkeypatch: pytest.MonkeyPatch):
    user = _make_user()
    session = SimpleNamespace(flush=AsyncMock(side_effect=IntegrityError("stmt", {}, Exception("unique"))))
    repo = _FakeMobileUserRepository(user=user)
    use_case = _build_use_case(monkeypatch, repo, session)

    with pytest.raises(MobileTelegramAccountLinkConflictError):
        await use_case.link_account(user_id=user.id, telegram_id=424242, username="alice")
