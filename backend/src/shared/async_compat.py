from __future__ import annotations

from collections.abc import Awaitable
from inspect import isawaitable
from typing import cast


async def resolve_maybe_awaitable[T](value: Awaitable[T] | T) -> T:
    if isawaitable(value):
        return await cast(Awaitable[T], value)
    return value
