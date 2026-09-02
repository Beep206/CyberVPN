from dataclasses import replace
from datetime import UTC, datetime
from typing import cast
from uuid import uuid4

import pytest
from fastapi import HTTPException, Response
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.entities.user import User
from src.domain.enums import UserStatus
from src.domain.value_objects.remnawave_user_ref import RemnawaveUserRef
from src.infrastructure.remnawave.user_gateway import RemnawaveMutationAcceptedPending
from src.presentation.api.v1.users import actions, bulk, routes
from src.presentation.api.v1.users.schemas import BulkUserActionRequest, CreateUserRequest, UpdateUserRequest


def _user(
    *,
    numeric_id: int = 42,
    with_legacy_uuid: bool = True,
    status: UserStatus = UserStatus.ACTIVE,
) -> User:
    now = datetime(2026, 8, 30, 14, 0, tzinfo=UTC)
    return User(
        uuid=uuid4() if with_legacy_uuid else None,
        remnawave_id=numeric_id,
        username=f"numeric-{numeric_id}",
        status=status,
        short_uuid=f"short-{numeric_id}",
        created_at=now,
        updated_at=now,
    )


class _Gateway:
    def __init__(self) -> None:
        self.user = _user()
        self.lookups: list[int] = []
        self.updates: list[tuple[RemnawaveUserRef, dict[str, object]]] = []
        self.deletes: list[RemnawaveUserRef] = []
        self.creates = 0

    async def get_by_id(self, user_id: int) -> User | None:
        self.lookups.append(user_id)
        return self.user

    async def update(self, user_ref: RemnawaveUserRef, **kwargs: object) -> User:
        self.updates.append((user_ref, kwargs))
        return self.user

    async def delete(self, user_ref: RemnawaveUserRef) -> None:
        self.deletes.append(user_ref)

    async def create(self, username: str, **_kwargs: object) -> User:
        self.creates += 1
        self.user = replace(self.user, username=username)
        return self.user

    async def get_by_ref(self, user_ref: RemnawaveUserRef) -> User | None:
        assert user_ref == self.user.ref
        return self.user


class _AcceptedGateway(_Gateway):
    async def create(self, username: str, **_kwargs: object) -> User:
        self.creates += 1
        raise RemnawaveMutationAcceptedPending(operation="create")


class _ScalarResult:
    def __init__(self, record) -> None:
        self._record = record

    def scalars(self):
        return self

    def one_or_none(self):
        return self._record


class _CreateAttemptSession:
    def __init__(self) -> None:
        self.record = None
        self.commits = 0

    async def execute(self, _statement):
        return _ScalarResult(self.record)

    def add(self, record) -> None:
        self.record = record

    async def commit(self) -> None:
        self.commits += 1

    async def rollback(self) -> None:
        return None

    async def flush(self) -> None:
        return None


@pytest.mark.unit
async def test_user_detail_update_and_delete_paths_use_numeric_identity(monkeypatch) -> None:
    gateway = _Gateway()
    monkeypatch.setattr(routes, "RemnawaveUserGateway", lambda client: gateway)

    detail = await routes.get_user(user_id=42, client=object(), _=None)
    updated = await routes.update_user(
        user_id=42,
        request=UpdateUserRequest(email="updated@example.com"),
        client=object(),
        _=None,
    )
    deleted = await routes.delete_user(user_id=42, client=object(), _=None)

    assert detail.id == updated.id == 42
    assert gateway.lookups == [42]
    assert gateway.updates == [(RemnawaveUserRef(id=42), {"email": "updated@example.com"})]
    assert gateway.deletes == [RemnawaveUserRef(id=42)]
    assert deleted is None


@pytest.mark.unit
async def test_single_and_bulk_actions_construct_only_numeric_references(monkeypatch) -> None:
    gateway = _Gateway()
    monkeypatch.setattr(actions, "RemnawaveUserGateway", lambda client: gateway)
    monkeypatch.setattr(bulk, "RemnawaveUserGateway", lambda client: gateway)

    disabled = await actions.disable_user(user_id=42, client=object(), _=None)
    with pytest.raises(HTTPException) as exc_info:
        await bulk.bulk_enable_users(
            request=BulkUserActionRequest(user_ids=[42]),
            client=object(),
            _=None,
        )

    assert disabled.id == 42
    assert exc_info.value.status_code == 503
    assert [item[0] for item in gateway.updates] == [RemnawaveUserRef(id=42)]


@pytest.mark.unit
@pytest.mark.parametrize("invalid", [[str(uuid4())], [0], [-1], [True], [42, 42]])
def test_bulk_user_actions_reject_legacy_or_invalid_identifiers(invalid) -> None:
    with pytest.raises(ValidationError):
        BulkUserActionRequest(user_ids=invalid)


@pytest.mark.unit
async def test_admin_create_accepted_without_body_is_durable_and_never_reposted(monkeypatch) -> None:
    gateway = _AcceptedGateway()
    session = _CreateAttemptSession()
    monkeypatch.setattr(routes, "RemnawaveUserGateway", lambda client: gateway)
    request = CreateUserRequest(username="accepted-pending")

    first = await routes.create_user(
        request=request,
        idempotency_key="admin-request-1",
        db=cast(AsyncSession, session),
        client=object(),
        _=None,
    )
    replay = await routes.create_user(
        request=request,
        idempotency_key="admin-request-1",
        db=cast(AsyncSession, session),
        client=object(),
        _=None,
    )

    assert isinstance(first, Response)
    assert isinstance(replay, Response)
    assert first.status_code == replay.status_code == 202
    assert gateway.creates == 1
    assert session.record.status == "reconciliation_required"
    assert session.commits == 2


@pytest.mark.unit
async def test_admin_create_success_replays_authoritative_exact_user_without_second_post(monkeypatch) -> None:
    gateway = _Gateway()
    session = _CreateAttemptSession()
    monkeypatch.setattr(routes, "RemnawaveUserGateway", lambda client: gateway)
    request = CreateUserRequest(username="created-once")

    first = await routes.create_user(
        request=request,
        idempotency_key="admin-request-2",
        db=cast(AsyncSession, session),
        client=object(),
        _=None,
    )
    replay = await routes.create_user(
        request=request,
        idempotency_key="admin-request-2",
        db=cast(AsyncSession, session),
        client=object(),
        _=None,
    )

    assert first.id == replay.id == 42
    assert gateway.creates == 1
    assert session.record.status == "completed"
    assert session.record.response_payload == {
        "numeric_user_id": 42,
        "legacy_uuid": str(gateway.user.uuid),
    }


@pytest.mark.unit
async def test_admin_numeric_only_create_success_replays_without_second_post(monkeypatch) -> None:
    gateway = _Gateway()
    gateway.user = _user(with_legacy_uuid=False)
    session = _CreateAttemptSession()
    monkeypatch.setattr(routes, "RemnawaveUserGateway", lambda client: gateway)
    request = CreateUserRequest(username="numeric-only-created-once")

    first = await routes.create_user(
        request=request,
        idempotency_key="admin-numeric-only-request",
        db=cast(AsyncSession, session),
        client=object(),
        _=None,
    )
    replay = await routes.create_user(
        request=request,
        idempotency_key="admin-numeric-only-request",
        db=cast(AsyncSession, session),
        client=object(),
        _=None,
    )

    assert first.id == replay.id == 42
    assert first.uuid is replay.uuid is None
    assert gateway.creates == 1
    assert session.record.response_payload == {"numeric_user_id": 42}


@pytest.mark.unit
@pytest.mark.parametrize(
    "changed_request",
    [
        CreateUserRequest(username="created-once", email="second@example.com", password="first-secret"),
        CreateUserRequest(username="created-once", email="first@example.com", password="second-secret"),
    ],
)
async def test_admin_create_replay_binds_exact_email_and_password_without_second_post(
    monkeypatch,
    changed_request: CreateUserRequest,
) -> None:
    gateway = _Gateway()
    session = _CreateAttemptSession()
    monkeypatch.setattr(routes, "RemnawaveUserGateway", lambda client: gateway)
    original = CreateUserRequest(
        username="created-once",
        email="first@example.com",
        password="first-secret",
    )

    await routes.create_user(
        request=original,
        idempotency_key="admin-request-sensitive-replay",
        db=cast(AsyncSession, session),
        client=object(),
        _=None,
    )

    with pytest.raises(HTTPException) as exc_info:
        await routes.create_user(
            request=changed_request,
            idempotency_key="admin-request-sensitive-replay",
            db=cast(AsyncSession, session),
            client=object(),
            _=None,
        )

    assert exc_info.value.status_code == 409
    assert gateway.creates == 1
    assert original.email not in session.record.request_hash
    assert original.password not in session.record.request_hash
