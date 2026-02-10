"""Test dependency override utilities.

Usage in tests:

    from src.infrastructure.di.overrides import override_dependency

    @pytest.fixture
    def mock_db(mock_session):
        with override_dependency("db", lambda: mock_session):
            yield
"""

from collections.abc import Callable, Generator
from contextlib import contextmanager
from typing import Any

from src.infrastructure.di.container import container


@contextmanager
def override_dependency(key: str, factory: Callable[..., Any]) -> Generator[None, None, None]:
    """Context manager to temporarily override a DI dependency.

    Restores the original factory on exit.
    """
    original = container.get(key)
    container.override(key, factory)
    try:
        yield
    finally:
        container.override(key, original)
