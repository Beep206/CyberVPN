from __future__ import annotations

import sys
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from fastapi.exceptions import RequestValidationError
from starlette.requests import Request

from src.presentation import exception_handlers


def _request(path: str) -> Request:
    return Request(
        {
            "type": "http",
            "method": "GET",
            "path": path,
            "headers": [],
            "client": ("203.0.113.10", 43120),
            "scheme": "https",
            "server": ("backend", 443),
        }
    )


@pytest.mark.asyncio
async def test_validation_handler_redacts_subscription_bearer_path(monkeypatch: pytest.MonkeyPatch) -> None:
    logger = MagicMock()
    monkeypatch.setattr(exception_handlers, "logger", logger)
    token = "validation-bearer-token"

    response = await exception_handlers.validation_exception_handler(
        _request(f"/api/sub/{token}"),
        RequestValidationError(
            [
                {
                    "type": "missing",
                    "loc": ("query", "client"),
                    "msg": "Field required",
                    "input": None,
                }
            ]
        ),
    )

    assert response.status_code == 422
    call = logger.warning.call_args
    assert call.args[2] == "/api/sub/[REDACTED]"
    assert call.kwargs["extra"]["path"] == "/api/sub/[REDACTED]"
    assert token not in str(call)


@pytest.mark.asyncio
async def test_unhandled_handler_redacts_subscription_bearer_path(monkeypatch: pytest.MonkeyPatch) -> None:
    logger = MagicMock()
    monkeypatch.setattr(exception_handlers, "logger", logger)
    monkeypatch.setitem(
        sys.modules,
        "sentry_sdk",
        SimpleNamespace(capture_exception=lambda exc: None),
    )
    token = "unhandled-bearer-token"

    response = await exception_handlers.unhandled_exception_handler(
        _request(f"/api/sub/{token}"),
        RuntimeError("synthetic failure"),
    )

    assert response.status_code == 500
    call = logger.exception.call_args
    assert call.kwargs["extra"]["path"] == "/api/sub/[REDACTED]"
    assert token not in str(call)
