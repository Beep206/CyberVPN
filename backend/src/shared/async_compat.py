from __future__ import annotations

from collections.abc import Awaitable
from inspect import isawaitable
from typing import Any, cast


async def resolve_maybe_awaitable(value: Awaitable[Any] | Any) -> Any:
    if isawaitable(value):
        return await cast(Awaitable[Any], value)
    return value
