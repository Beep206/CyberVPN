import pytest

from src.application.services.public_uid_allocator import (
    PublicUIDCollisionExhaustedError,
    allocate_public_uid,
)
from src.domain.value_objects import public_uid


class _PublicUIDRepo:
    def __init__(self, existing: set[int]) -> None:
        self.existing = existing
        self.calls: list[int] = []

    async def get_by_public_uid(self, public_uid: int) -> object | None:
        self.calls.append(public_uid)
        return object() if public_uid in self.existing else None


@pytest.mark.unit
async def test_allocate_public_uid_retries_after_collision(monkeypatch: pytest.MonkeyPatch) -> None:
    candidates = iter([14_677_650, 81_245_999])
    repo = _PublicUIDRepo(existing={14_677_650})
    monkeypatch.setattr(public_uid, "generate_public_uid_candidate", lambda: next(candidates))

    allocated = await allocate_public_uid(repo)

    assert allocated == 81_245_999
    assert repo.calls == [14_677_650, 81_245_999]


@pytest.mark.unit
async def test_allocate_public_uid_raises_after_bounded_collisions(monkeypatch: pytest.MonkeyPatch) -> None:
    repo = _PublicUIDRepo(existing={14_677_650})
    monkeypatch.setattr(public_uid, "generate_public_uid_candidate", lambda: 14_677_650)

    with pytest.raises(PublicUIDCollisionExhaustedError):
        await allocate_public_uid(repo, max_attempts=3)

    assert repo.calls == [14_677_650, 14_677_650, 14_677_650]
