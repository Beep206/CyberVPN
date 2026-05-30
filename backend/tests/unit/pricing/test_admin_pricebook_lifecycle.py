from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

from src.application.use_cases.offers.admin_pricebook_lifecycle import pricebook_lifecycle_status


def test_pricebook_lifecycle_status_marks_future_active_version_as_scheduled() -> None:
    now = datetime(2026, 5, 30, 12, 0, tzinfo=UTC)
    pricebook = SimpleNamespace(
        version_status="active",
        is_active=True,
        effective_from=now + timedelta(days=1),
        effective_to=None,
    )

    assert pricebook_lifecycle_status(pricebook, now=now) == "scheduled"


def test_pricebook_lifecycle_status_marks_current_active_version_as_published() -> None:
    now = datetime(2026, 5, 30, 12, 0, tzinfo=UTC)
    pricebook = SimpleNamespace(
        version_status="active",
        is_active=True,
        effective_from=now - timedelta(days=1),
        effective_to=None,
    )

    assert pricebook_lifecycle_status(pricebook, now=now) == "published"


def test_pricebook_lifecycle_status_marks_closed_version_as_superseded() -> None:
    now = datetime(2026, 5, 30, 12, 0, tzinfo=UTC)
    pricebook = SimpleNamespace(
        version_status="active",
        is_active=True,
        effective_from=now - timedelta(days=10),
        effective_to=now - timedelta(days=1),
    )

    assert pricebook_lifecycle_status(pricebook, now=now) == "superseded"
