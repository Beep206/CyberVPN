"""Utility modules for telegram bot."""

from __future__ import annotations

from .constants import (
    CACHE_TTL_DEFAULT,
    CACHE_TTL_LONG,
    CACHE_TTL_SHORT,
    MAX_MESSAGE_LENGTH,
    RATE_LIMIT_COMMANDS,
    RATE_LIMIT_MESSAGES,
    REDIS_KEY_PREFIX_CACHE,
    REDIS_KEY_PREFIX_RATE_LIMIT,
    REDIS_KEY_PREFIX_SESSION,
    REDIS_KEY_PREFIX_SUBSCRIPTION,
    REDIS_KEY_PREFIX_USER,
)
from .deep_links import decode_deep_link, encode_deep_link
from .formatting import (
    format_datetime,
    format_duration,
    format_money,
    format_traffic_bytes,
)
from .pagination import Paginator, create_pagination_keyboard

__all__ = [
    # Constants
    "CACHE_TTL_DEFAULT",
    "CACHE_TTL_LONG",
    "CACHE_TTL_SHORT",
    "MAX_MESSAGE_LENGTH",
    "RATE_LIMIT_COMMANDS",
    "RATE_LIMIT_MESSAGES",
    "REDIS_KEY_PREFIX_CACHE",
    "REDIS_KEY_PREFIX_RATE_LIMIT",
    "REDIS_KEY_PREFIX_SESSION",
    "REDIS_KEY_PREFIX_SUBSCRIPTION",
    "REDIS_KEY_PREFIX_USER",
    # Deep links
    "decode_deep_link",
    "encode_deep_link",
    # Formatting
    "format_datetime",
    "format_duration",
    "format_money",
    "format_traffic_bytes",
    # Pagination
    "Paginator",
    "create_pagination_keyboard",
]
