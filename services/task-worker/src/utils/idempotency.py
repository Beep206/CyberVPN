"""Idempotency utilities for task-worker using Redis-based locking.

Provides decorators and utilities to ensure tasks are only executed once,
even if they are enqueued multiple times. This prevents duplicate processing
of payments, notifications, or other critical operations.

Uses Redis SET NX (set if not exists) with TTL for distributed locking across
multiple worker instances.
"""

import functools
import hashlib
import json
from typing import Any, Callable, TypeVar

import structlog

from src.services.redis_client import get_redis_client

logger = structlog.get_logger(__name__)

IDEMPOTENCY_PREFIX = "cybervpn:idempotency:"
DEFAULT_TTL = 3600  # 1 hour

F = TypeVar("F", bound=Callable[..., Any])


def idempotency_key(task_name: str, *args: Any, **kwargs: Any) -> str:
    """Generate deterministic idempotency key from task name and arguments.

    Creates a SHA-256 hash of the task name and all arguments to ensure the same
    task with the same parameters always generates the same key.

    Args:
        task_name: Name of the task function
        *args: Positional arguments passed to the task
        **kwargs: Keyword arguments passed to the task

    Returns:
        Redis key for idempotency check in format "cybervpn:idempotency:{hash}"

    Example:
        >>> key = idempotency_key("send_notification", user_id=123, message="Hello")
        >>> print(key)
        cybervpn:idempotency:a1b2c3d4...
    """
    # Sort kwargs for deterministic ordering
    sorted_kwargs = sorted(kwargs.items())

    # Create a deterministic string representation
    # Use json.dumps with sort_keys for nested dicts/lists
    try:
        args_str = json.dumps(args, sort_keys=True, default=str)
        kwargs_str = json.dumps(sorted_kwargs, sort_keys=True, default=str)
    except (TypeError, ValueError):
        # Fallback to string representation if JSON serialization fails
        args_str = str(args)
        kwargs_str = str(sorted_kwargs)

    payload = f"{task_name}:{args_str}:{kwargs_str}"

    # Generate SHA-256 hash for compact, deterministic key
    key_hash = hashlib.sha256(payload.encode()).hexdigest()

    return f"{IDEMPOTENCY_PREFIX}{key_hash}"


def idempotent(ttl: int = DEFAULT_TTL) -> Callable[[F], F]:
    """Decorator to make an async task idempotent using Redis locks.

    Prevents duplicate execution of the same task with the same arguments.
    If a task is already in progress or completed within the TTL period,
    subsequent calls will be skipped.

    Args:
        ttl: Time-to-live for the idempotency lock in seconds (default: 3600 = 1 hour)

    Returns:
        Decorator function that wraps the task

    Example:
        >>> @idempotent(ttl=3600)
        ... async def process_payment(payment_id: int, amount: float):
        ...     # Process payment logic
        ...     return {"status": "success"}
        >>>
        >>> # First call executes normally
        >>> result1 = await process_payment(123, 50.0)
        >>> # Second call within TTL is skipped
        >>> result2 = await process_payment(123, 50.0)
        >>> assert result2["skipped"] is True

    Notes:
        - The idempotency key is based on function name and ALL arguments
        - Changing any argument will generate a new key
        - TTL should be set based on how long duplicate prevention is needed
        - For payment processing, use a longer TTL (hours)
        - For notifications, a shorter TTL (minutes) may be sufficient
    """

    def decorator(func: F) -> F:
        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            # Generate idempotency key from function name and arguments
            key = idempotency_key(func.__name__, *args, **kwargs)

            redis = get_redis_client()
            try:
                # Try to acquire lock with SET NX (set if not exists) and TTL
                # Returns True if key was set, False if it already exists
                acquired = await redis.set(key, "1", nx=True, ex=ttl)

                if not acquired:
                    # Task is already being processed or was recently completed
                    logger.info(
                        "task_skipped_idempotent",
                        task=func.__name__,
                        key_suffix=key[-12:],  # Log last 12 chars for debugging
                        ttl=ttl,
                        args=args[:3] if args else [],  # Log first 3 args for context
                    )
                    return {"skipped": True, "reason": "idempotent_duplicate"}

                # Lock acquired, proceed with task execution
                logger.debug(
                    "idempotency_lock_acquired",
                    task=func.__name__,
                    key_suffix=key[-12:],
                    ttl=ttl,
                )

                # Execute the wrapped function
                result = await func(*args, **kwargs)

                # Mark result as successful execution (not skipped)
                if isinstance(result, dict):
                    result["skipped"] = False

                return result

            except Exception as exc:
                # On error, delete the lock to allow retry
                # This ensures transient errors don't permanently block the task
                try:
                    await redis.delete(key)
                    logger.warning(
                        "idempotency_lock_released_on_error",
                        task=func.__name__,
                        key_suffix=key[-12:],
                        error=str(exc),
                    )
                except Exception as delete_exc:
                    logger.error(
                        "idempotency_lock_cleanup_failed",
                        task=func.__name__,
                        key_suffix=key[-12:],
                        error=str(delete_exc),
                    )
                # Re-raise the original exception
                raise exc

            finally:
                await redis.aclose()

        return wrapper  # type: ignore

    return decorator


async def check_idempotency(task_name: str, *args: Any, **kwargs: Any) -> bool:
    """Check if a task has already been executed without acquiring a lock.

    Useful for pre-flight checks before enqueueing tasks.

    Args:
        task_name: Name of the task to check
        *args: Task positional arguments
        **kwargs: Task keyword arguments

    Returns:
        True if task has already been executed, False otherwise

    Example:
        >>> already_processed = await check_idempotency("send_notification", user_id=123)
        >>> if not already_processed:
        ...     await enqueue_task("send_notification", user_id=123)
    """
    key = idempotency_key(task_name, *args, **kwargs)
    redis = get_redis_client()

    try:
        exists = await redis.exists(key)
        return bool(exists)
    finally:
        await redis.aclose()


async def clear_idempotency(task_name: str, *args: Any, **kwargs: Any) -> bool:
    """Manually clear idempotency lock for a task.

    Use with caution - this allows re-execution of a task that was previously completed.
    Primarily useful for testing or manual intervention.

    Args:
        task_name: Name of the task
        *args: Task positional arguments
        **kwargs: Task keyword arguments

    Returns:
        True if lock was cleared, False if lock didn't exist

    Example:
        >>> # Clear lock to allow re-processing
        >>> cleared = await clear_idempotency("process_payment", payment_id=123)
        >>> if cleared:
        ...     logger.info("idempotency_lock_cleared_manually")
    """
    key = idempotency_key(task_name, *args, **kwargs)
    redis = get_redis_client()

    try:
        deleted = await redis.delete(key)
        if deleted:
            logger.warning(
                "idempotency_lock_cleared",
                task=task_name,
                key_suffix=key[-12:],
                args=args[:3] if args else [],
            )
        return bool(deleted)
    finally:
        await redis.aclose()


async def extend_idempotency_ttl(task_name: str, additional_ttl: int, *args: Any, **kwargs: Any) -> bool:
    """Extend the TTL of an existing idempotency lock.

    Useful for long-running tasks that need to maintain their lock longer than
    the initial TTL.

    Args:
        task_name: Name of the task
        additional_ttl: Additional seconds to add to TTL
        *args: Task positional arguments
        **kwargs: Task keyword arguments

    Returns:
        True if TTL was extended, False if lock doesn't exist

    Example:
        >>> # Extend lock by 30 minutes for long-running export
        >>> extended = await extend_idempotency_ttl("export_data", 1800, export_id=456)
    """
    key = idempotency_key(task_name, *args, **kwargs)
    redis = get_redis_client()

    try:
        current_ttl = await redis.ttl(key)
        if current_ttl <= 0:
            # Key doesn't exist or has no TTL
            return False

        new_ttl = current_ttl + additional_ttl
        await redis.expire(key, new_ttl)

        logger.debug(
            "idempotency_ttl_extended",
            task=task_name,
            key_suffix=key[-12:],
            previous_ttl=current_ttl,
            new_ttl=new_ttl,
        )
        return True

    finally:
        await redis.aclose()
