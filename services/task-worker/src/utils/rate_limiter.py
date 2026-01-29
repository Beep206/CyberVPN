"""Token bucket rate limiter for async operations.

Implements the token bucket algorithm for rate limiting API calls and other operations.
This ensures requests are distributed evenly over time and prevents bursting beyond capacity.

The token bucket algorithm works by:
1. Tokens are added to a bucket at a constant rate
2. Each request consumes one or more tokens
3. If insufficient tokens are available, the request waits until tokens are refilled

This is more flexible than simple request-per-second limiting because it allows
short bursts up to the bucket capacity while maintaining an average rate.
"""

import asyncio
import time
from typing import Optional

import structlog

logger = structlog.get_logger(__name__)


class AsyncTokenBucket:
    """Async token bucket rate limiter.

    Limits the rate of operations using the token bucket algorithm. Tokens are
    refilled continuously at a specified rate, and operations consume tokens.
    If insufficient tokens are available, the operation waits.

    Attributes:
        rate: Tokens added per second (e.g., 10.0 = 10 requests/second)
        capacity: Maximum number of tokens the bucket can hold (allows bursts)
        tokens: Current number of available tokens
        last_refill: Timestamp of last token refill

    Example:
        >>> # Allow 10 requests per second with burst capacity of 20
        >>> limiter = AsyncTokenBucket(rate=10.0, capacity=20)
        >>>
        >>> # Each request waits for tokens if needed
        >>> await limiter.acquire()
        >>> await api_call()
        >>>
        >>> # Can acquire multiple tokens at once
        >>> await limiter.acquire(tokens=5)
        >>> await batch_operation()

    Notes:
        - Thread-safe through asyncio.Lock
        - Tokens refill continuously based on elapsed time
        - Setting capacity > rate allows handling traffic bursts
        - Setting capacity = rate enforces strict rate limiting
    """

    def __init__(self, rate: float, capacity: int) -> None:
        """Initialize token bucket rate limiter.

        Args:
            rate: Number of tokens added per second (requests/second)
            capacity: Maximum tokens the bucket can hold (burst capacity)

        Example:
            >>> # 100 requests/second, burst up to 200
            >>> limiter = AsyncTokenBucket(rate=100.0, capacity=200)
        """
        if rate <= 0:
            raise ValueError(f"Rate must be positive, got {rate}")
        if capacity <= 0:
            raise ValueError(f"Capacity must be positive, got {capacity}")

        self.rate = rate
        self.capacity = capacity
        self.tokens = float(capacity)  # Start with full bucket
        self.last_refill = time.monotonic()
        self._lock = asyncio.Lock()

        logger.debug(
            "token_bucket_initialized",
            rate=rate,
            capacity=capacity,
            rate_per_minute=rate * 60,
        )

    async def acquire(self, tokens: int = 1, timeout: Optional[float] = None) -> bool:
        """Acquire tokens from the bucket, waiting if necessary.

        Refills tokens based on elapsed time, then consumes the requested number.
        If insufficient tokens are available, waits until enough tokens are refilled.

        Args:
            tokens: Number of tokens to acquire (default: 1)
            timeout: Maximum seconds to wait for tokens (None = wait forever)

        Returns:
            True if tokens were acquired, False if timeout was reached

        Raises:
            ValueError: If tokens < 1 or tokens > capacity

        Example:
            >>> # Simple single-token acquire
            >>> await limiter.acquire()
            >>> await make_api_call()
            >>>
            >>> # Acquire multiple tokens for batch operation
            >>> await limiter.acquire(tokens=10)
            >>> await batch_api_call(items[:10])
            >>>
            >>> # Acquire with timeout
            >>> acquired = await limiter.acquire(tokens=5, timeout=2.0)
            >>> if not acquired:
            ...     logger.warning("rate_limiter_timeout")
        """
        if tokens < 1:
            raise ValueError(f"Must acquire at least 1 token, got {tokens}")
        if tokens > self.capacity:
            raise ValueError(f"Cannot acquire {tokens} tokens, capacity is {self.capacity}")

        start_time = time.monotonic()

        async with self._lock:
            # Refill tokens based on elapsed time
            now = time.monotonic()
            elapsed = now - self.last_refill
            refilled = elapsed * self.rate

            # Add refilled tokens, capped at capacity
            self.tokens = min(self.capacity, self.tokens + refilled)
            self.last_refill = now

            # If we have enough tokens, consume and return immediately
            if self.tokens >= tokens:
                self.tokens -= tokens
                logger.debug(
                    "tokens_acquired_immediate",
                    tokens_requested=tokens,
                    tokens_remaining=round(self.tokens, 2),
                )
                return True

            # Calculate wait time for tokens to be available
            tokens_needed = tokens - self.tokens
            wait_time = tokens_needed / self.rate

            # Check if wait would exceed timeout
            if timeout is not None and wait_time > timeout:
                logger.warning(
                    "token_acquisition_timeout",
                    tokens_requested=tokens,
                    tokens_available=round(self.tokens, 2),
                    wait_time_needed=round(wait_time, 2),
                    timeout=timeout,
                )
                return False

            logger.debug(
                "tokens_waiting",
                tokens_requested=tokens,
                tokens_available=round(self.tokens, 2),
                wait_time=round(wait_time, 3),
            )

        # Wait outside the lock to allow other operations
        await asyncio.sleep(wait_time)

        # Acquire lock again and consume tokens
        async with self._lock:
            # Refill tokens again after waiting
            now = time.monotonic()
            elapsed = now - self.last_refill
            refilled = elapsed * self.rate
            self.tokens = min(self.capacity, self.tokens + refilled)
            self.last_refill = now

            # Consume tokens
            self.tokens -= tokens

            total_wait = time.monotonic() - start_time
            logger.debug(
                "tokens_acquired_after_wait",
                tokens_requested=tokens,
                tokens_remaining=round(self.tokens, 2),
                wait_time=round(total_wait, 3),
            )

        return True

    async def try_acquire(self, tokens: int = 1) -> bool:
        """Try to acquire tokens without waiting.

        Non-blocking version of acquire(). Returns immediately with success/failure.

        Args:
            tokens: Number of tokens to acquire (default: 1)

        Returns:
            True if tokens were acquired, False if insufficient tokens

        Example:
            >>> if await limiter.try_acquire():
            ...     await make_api_call()
            ... else:
            ...     logger.info("rate_limit_reached")
        """
        if tokens < 1:
            raise ValueError(f"Must acquire at least 1 token, got {tokens}")
        if tokens > self.capacity:
            return False

        async with self._lock:
            # Refill tokens based on elapsed time
            now = time.monotonic()
            elapsed = now - self.last_refill
            refilled = elapsed * self.rate
            self.tokens = min(self.capacity, self.tokens + refilled)
            self.last_refill = now

            # Try to consume tokens
            if self.tokens >= tokens:
                self.tokens -= tokens
                logger.debug(
                    "tokens_acquired_nonblocking",
                    tokens_requested=tokens,
                    tokens_remaining=round(self.tokens, 2),
                )
                return True

            logger.debug(
                "tokens_unavailable",
                tokens_requested=tokens,
                tokens_available=round(self.tokens, 2),
            )
            return False

    @property
    def available_tokens(self) -> float:
        """Get current number of available tokens (approximate).

        Note: This is an approximation since tokens are refilled lazily.
        The actual available tokens will be calculated on the next acquire().

        Returns:
            Approximate number of tokens currently available
        """
        now = time.monotonic()
        elapsed = now - self.last_refill
        refilled = elapsed * self.rate
        return min(self.capacity, self.tokens + refilled)

    async def reset(self) -> None:
        """Reset the bucket to full capacity.

        Useful for testing or manual intervention.

        Example:
            >>> await limiter.reset()  # Refill bucket to capacity
        """
        async with self._lock:
            self.tokens = float(self.capacity)
            self.last_refill = time.monotonic()
            logger.info("token_bucket_reset", capacity=self.capacity)

    async def set_rate(self, new_rate: float) -> None:
        """Dynamically change the token refill rate.

        Args:
            new_rate: New tokens per second rate

        Example:
            >>> # Reduce rate during high load
            >>> await limiter.set_rate(5.0)
        """
        if new_rate <= 0:
            raise ValueError(f"Rate must be positive, got {new_rate}")

        async with self._lock:
            # Refill with old rate before changing
            now = time.monotonic()
            elapsed = now - self.last_refill
            refilled = elapsed * self.rate
            self.tokens = min(self.capacity, self.tokens + refilled)
            self.last_refill = now

            # Update rate
            old_rate = self.rate
            self.rate = new_rate

            logger.info(
                "token_bucket_rate_changed",
                old_rate=old_rate,
                new_rate=new_rate,
                old_rate_per_minute=old_rate * 60,
                new_rate_per_minute=new_rate * 60,
            )
