"""Timing-safe security utilities (LOW-002).

Provides helpers to prevent timing attacks by normalizing response times.
"""

import asyncio
import secrets
import time


async def normalize_response_time(
    start_time: float,
    min_duration: float = 0.1,
    max_jitter: int = 50,
) -> None:
    """Ensure minimum response time with random jitter to prevent timing attacks.

    This function adds an async delay to ensure that the total time elapsed
    since start_time is at least min_duration seconds, plus random jitter.

    Args:
        start_time: The time.time() value when the operation started.
        min_duration: Minimum total duration in seconds (default 100ms).
        max_jitter: Maximum random jitter in milliseconds (default 50ms).

    Example:
        start_time = time.time()
        try:
            result = await authenticate_user(username, password)
        except AuthenticationError:
            await normalize_response_time(start_time)
            raise
    """
    elapsed = time.time() - start_time
    if elapsed < min_duration:
        # Add random jitter (0 to max_jitter ms)
        jitter = secrets.randbelow(max_jitter) / 1000.0
        await asyncio.sleep(min_duration - elapsed + jitter)
