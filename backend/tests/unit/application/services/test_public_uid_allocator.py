"""Unit tests for public UID allocation."""

import pytest

from src.application.services import public_uid_allocator


class _FakePublicUIDRepository:
    def __init__(self, existing_uids: set[int]) -> None:
        self._existing_uids = existing_uids
        self.lookups: list[int] = []

    async def get_by_public_uid(self, public_uid: int) -> object | None:
        self.lookups.append(public_uid)
        if public_uid in self._existing_uids:
            return object()
        return None


@pytest.mark.unit
async def test_allocate_public_uid_retries_collisions(monkeypatch) -> None:
    candidates = iter([14_677_650, 81_245_999])
    monkeypatch.setattr(
        public_uid_allocator.public_uid,
        "generate_public_uid_candidate",
        lambda: next(candidates),
    )
    repo = _FakePublicUIDRepository({14_677_650})

    allocated_uid = await public_uid_allocator.allocate_public_uid(repo)

    assert allocated_uid == 81_245_999
    assert repo.lookups == [14_677_650, 81_245_999]


@pytest.mark.unit
async def test_allocate_public_uid_raises_after_bounded_collisions(monkeypatch) -> None:
    monkeypatch.setattr(
        public_uid_allocator.public_uid,
        "generate_public_uid_candidate",
        lambda: 14_677_650,
    )
    repo = _FakePublicUIDRepository({14_677_650})

    with pytest.raises(public_uid_allocator.PublicUIDCollisionExhaustedError):
        await public_uid_allocator.allocate_public_uid(repo, max_attempts=2)

    assert repo.lookups == [14_677_650, 14_677_650]
