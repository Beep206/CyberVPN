"""Unit tests for OAuth account linking conflict policy."""

from uuid import uuid4

import pytest

from src.application.use_cases.auth.account_linking import AccountLinkingUseCase
from src.infrastructure.database.models.oauth_account_model import OAuthAccount


class _Result:
    def __init__(self, value: OAuthAccount | None) -> None:
        self._value = value

    def scalar_one_or_none(self) -> OAuthAccount | None:
        return self._value


class _FakeSession:
    def __init__(self, *results: OAuthAccount | None) -> None:
        self._results = list(results)
        self.added: list[OAuthAccount] = []
        self.flush_count = 0

    async def execute(self, _statement) -> _Result:
        return _Result(self._results.pop(0))

    def add(self, account: OAuthAccount) -> None:
        self.added.append(account)

    async def flush(self) -> None:
        self.flush_count += 1


@pytest.mark.unit
async def test_link_account_creates_new_link_when_no_conflict():
    user_id = uuid4()
    session = _FakeSession(None, None)
    use_case = AccountLinkingUseCase(session)  # type: ignore[arg-type]

    account = await use_case.link_account(
        user_id=user_id,
        provider="telegram",
        provider_user_id="424242",
        provider_username="alice",
        access_token="telegram_access",
    )

    assert account.user_id == user_id
    assert account.provider == "telegram"
    assert account.provider_user_id == "424242"
    assert account.provider_username == "alice"
    assert session.added == [account]
    assert session.flush_count == 1


@pytest.mark.unit
async def test_link_account_rejects_identity_already_linked_to_another_user():
    current_user_id = uuid4()
    existing = OAuthAccount(
        user_id=uuid4(),
        provider="telegram",
        provider_user_id="424242",
    )
    session = _FakeSession(existing)
    use_case = AccountLinkingUseCase(session)  # type: ignore[arg-type]

    with pytest.raises(ValueError, match="already linked to another user"):
        await use_case.link_account(
            user_id=current_user_id,
            provider="telegram",
            provider_user_id="424242",
        )

    assert session.added == []
    assert session.flush_count == 0


@pytest.mark.unit
async def test_link_account_rejects_different_identity_for_same_provider():
    user_id = uuid4()
    existing = OAuthAccount(
        user_id=user_id,
        provider="telegram",
        provider_user_id="old-telegram-id",
    )
    session = _FakeSession(None, existing)
    use_case = AccountLinkingUseCase(session)  # type: ignore[arg-type]

    with pytest.raises(ValueError, match="different account linked"):
        await use_case.link_account(
            user_id=user_id,
            provider="telegram",
            provider_user_id="new-telegram-id",
        )

    assert session.added == []
    assert session.flush_count == 0


@pytest.mark.unit
async def test_link_account_is_idempotent_for_same_user_and_identity():
    user_id = uuid4()
    existing = OAuthAccount(
        user_id=user_id,
        provider="telegram",
        provider_user_id="424242",
    )
    session = _FakeSession(existing)
    use_case = AccountLinkingUseCase(session)  # type: ignore[arg-type]

    account = await use_case.link_account(
        user_id=user_id,
        provider="telegram",
        provider_user_id="424242",
        provider_username="alice_updated",
        access_token="updated_access",
    )

    assert account is existing
    assert existing.provider_username == "alice_updated"
    assert session.added == []
    assert session.flush_count == 1
