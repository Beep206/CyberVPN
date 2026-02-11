"""Redis cache instrumentation for metrics.

Tracks cache hit/miss rates and operation counts.
"""

from functools import wraps
from typing import Any, Callable

from src.infrastructure.monitoring.metrics import cache_operations_total


def track_cache_operation(operation: str) -> Callable:
    """Decorator to track cache operations (get/set/delete) with metrics.

    Args:
        operation: Cache operation type ("get", "set", "delete")

    Usage:
        @track_cache_operation("get")
        async def get_from_cache(key: str) -> Any:
            ...
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def async_wrapper(*args, **kwargs) -> Any:
            try:
                result = await func(*args, **kwargs)

                # For get operations, track hit/miss
                if operation == "get":
                    status = "hit" if result is not None else "miss"
                else:
                    status = "success"

                cache_operations_total.labels(operation=operation, status=status).inc()
                return result

            except Exception as exc:
                cache_operations_total.labels(operation=operation, status="error").inc()
                raise exc

        @wraps(func)
        def sync_wrapper(*args, **kwargs) -> Any:
            try:
                result = func(*args, **kwargs)

                # For get operations, track hit/miss
                if operation == "get":
                    status = "hit" if result is not None else "miss"
                else:
                    status = "success"

                cache_operations_total.labels(operation=operation, status=status).inc()
                return result

            except Exception as exc:
                cache_operations_total.labels(operation=operation, status="error").inc()
                raise exc

        # Return appropriate wrapper based on whether function is async
        import inspect

        if inspect.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper

    return decorator
