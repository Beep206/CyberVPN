from __future__ import annotations

import pytest


@pytest.fixture(scope="session", autouse=True)
def ensure_repo_schema() -> None:
    """Contract tests in this package are file/DTO based and do not need database bootstrap."""

