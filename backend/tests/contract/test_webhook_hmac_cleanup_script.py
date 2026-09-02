from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

SCRIPT_PATH = Path(__file__).resolve().parents[2] / "scripts" / "cleanup_legacy_webhook_fingerprints.py"


def _load_script() -> Any:
    spec = importlib.util.spec_from_file_location("cleanup_legacy_webhook_fingerprints", SCRIPT_PATH)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _result(items: list[Any]) -> MagicMock:
    result = MagicMock()
    result.scalars.return_value.all.return_value = items
    return result


@pytest.mark.asyncio
async def test_cleanup_commits_each_bounded_batch_and_is_resumable() -> None:
    script = _load_script()
    first = SimpleNamespace(payload={"raw": "secret-1"}, signature_fingerprint="a" * 64)
    second = SimpleNamespace(payload={"raw": "secret-2"}, signature_fingerprint="b" * 64)
    third = SimpleNamespace(payload={"raw": "secret-3"}, signature_fingerprint=None)
    session = AsyncMock()
    session.execute.side_effect = [
        _result([first, second]),
        _result([third]),
        _result([]),
    ]

    def sanitizer(value: Any, *, signature_fingerprint_present: bool) -> dict[str, Any]:
        del value
        return {
            "schema": "webhook_log.redacted.v2",
            "legacy_fingerprints_removed": signature_fingerprint_present,
        }

    processed = await script.cleanup_in_batches(
        session,
        upper_bound=uuid4(),
        batch_size=2,
        sanitizer=sanitizer,
    )

    assert processed == 3
    assert session.commit.await_count == 2
    assert session.rollback.await_count == 1
    assert session.execute.await_count == 3
    assert first.payload == {
        "schema": "webhook_log.redacted.v2",
        "legacy_fingerprints_removed": True,
    }
    assert second.signature_fingerprint is None
    assert third.payload == {
        "schema": "webhook_log.redacted.v2",
        "legacy_fingerprints_removed": False,
    }


@pytest.mark.asyncio
async def test_cleanup_rolls_back_only_the_current_failed_batch() -> None:
    script = _load_script()
    session = AsyncMock()
    session.execute.side_effect = RuntimeError("database unavailable")

    with pytest.raises(RuntimeError, match="database unavailable"):
        await script.cleanup_in_batches(
            session,
            upper_bound=uuid4(),
            batch_size=10,
            sanitizer=lambda value, **kwargs: value,
        )

    session.commit.assert_not_awaited()
    session.rollback.assert_awaited_once()


@pytest.mark.asyncio
async def test_cleanup_resumes_after_an_interruption_without_rolling_back_committed_batches() -> None:
    script = _load_script()
    committed = SimpleNamespace(payload={"raw": "secret-1"}, signature_fingerprint="a" * 64)
    remaining = SimpleNamespace(payload={"raw": "secret-2"}, signature_fingerprint="b" * 64)

    def sanitizer(value: Any, *, signature_fingerprint_present: bool) -> dict[str, Any]:
        del value
        return {
            "schema": "webhook_log.redacted.v2",
            "legacy_fingerprints_removed": signature_fingerprint_present,
        }

    interrupted_session = AsyncMock()
    interrupted_session.execute.side_effect = [
        _result([committed]),
        RuntimeError("operator interruption"),
    ]
    with pytest.raises(RuntimeError, match="operator interruption"):
        await script.cleanup_in_batches(
            interrupted_session,
            upper_bound=uuid4(),
            batch_size=1,
            sanitizer=sanitizer,
        )

    interrupted_session.commit.assert_awaited_once()
    interrupted_session.rollback.assert_awaited_once()
    assert committed.payload["schema"] == "webhook_log.redacted.v2"
    assert committed.signature_fingerprint is None

    resumed_session = AsyncMock()
    resumed_session.execute.side_effect = [_result([remaining]), _result([])]
    processed_after_resume = await script.cleanup_in_batches(
        resumed_session,
        upper_bound=uuid4(),
        batch_size=1,
        sanitizer=sanitizer,
    )

    assert processed_after_resume == 1
    resumed_session.commit.assert_awaited_once()
    resumed_session.rollback.assert_awaited_once()
    assert remaining.payload["schema"] == "webhook_log.redacted.v2"
    assert remaining.signature_fingerprint is None
