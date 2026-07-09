"""Monitor worker process memory usage.

Periodic task that tracks RSS and VMS memory usage of the worker process
and exposes them as Prometheus metrics for resource monitoring and alerting.
"""

from typing import Protocol, cast

try:
    import resource as _resource_module
except ImportError:  # pragma: no cover - Windows local development fallback
    _resource: object | None = None
else:
    _resource = _resource_module

import structlog
from prometheus_client import Gauge

from src.broker import broker

logger = structlog.get_logger(__name__)

# Prometheus metrics for memory usage
MEMORY_RSS = Gauge("cybervpn_worker_memory_rss_bytes", "Worker RSS (resident set size) memory in bytes")
MEMORY_VMS = Gauge("cybervpn_worker_memory_vms_bytes", "Worker VMS (virtual memory size) memory in bytes")


class _ResourceUsage(Protocol):
    ru_maxrss: int


class _ResourceModule(Protocol):
    RUSAGE_SELF: int

    def getrusage(self, who: int) -> _ResourceUsage: ...


@broker.task(task_name="monitor_worker_memory", queue="monitoring")
async def monitor_worker_memory() -> dict:
    """Monitor worker process memory usage.

    Collects memory metrics using resource.getrusage() and exposes them
    as Prometheus gauges. RSS (resident set size) represents actual
    physical memory usage.

    Returns:
        Dictionary with memory statistics in bytes

    Note:
        On Linux, ru_maxrss is in kilobytes. On macOS, it's in bytes.
        This implementation assumes Linux (converts KB to bytes).
    """
    try:
        if _resource is None:
            memory_stats = {
                "rss_bytes": 0,
                "rss_mb": 0.0,
                "max_rss_kb": 0,
                "degraded": True,
            }
            MEMORY_RSS.set(0)
            logger.warning("worker_memory_resource_unavailable", **memory_stats)
            return memory_stats

        # Get resource usage for current process
        resource = cast(_ResourceModule, _resource)
        usage = resource.getrusage(resource.RUSAGE_SELF)

        # Convert maxrss from kilobytes to bytes (Linux convention)
        # On macOS, maxrss is already in bytes, but since this is a Linux-focused
        # project (Docker, PostgreSQL), we assume Linux behavior
        rss_bytes = usage.ru_maxrss * 1024

        # Update Prometheus metrics
        MEMORY_RSS.set(rss_bytes)

        # Note: VMS is not directly available via resource.getrusage()
        # Would need psutil for VMS, but keeping lightweight for now

        memory_stats = {
            "rss_bytes": rss_bytes,
            "rss_mb": round(rss_bytes / 1024 / 1024, 2),
            "max_rss_kb": usage.ru_maxrss,
        }

        logger.debug("worker_memory_monitored", **memory_stats)

        return memory_stats

    except Exception as e:
        logger.error("memory_monitor_failed", error=str(e))
        raise
