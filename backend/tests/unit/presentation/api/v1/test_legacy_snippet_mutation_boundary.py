from __future__ import annotations

import asyncio

import pytest
from fastapi import HTTPException, status

from src.presentation.api.v1.snippets import routes
from src.presentation.api.v1.snippets.schemas import CreateSnippetRequest


def test_legacy_snippet_create_fails_closed_before_provider_mutation() -> None:
    request = CreateSnippetRequest(
        name="legacy-guard",
        snippet_type="header",
        content="safe fixture",
        is_active=True,
    )

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(routes.create_snippet(request, _current_user=object()))

    assert exc_info.value.status_code == status.HTTP_410_GONE
    assert "Idempotency-Key" in str(exc_info.value.detail)
