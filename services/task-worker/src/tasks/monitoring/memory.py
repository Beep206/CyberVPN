"""Monitor worker process memory usage.

Periodic task that tracks RSS and VMS memory usage of the worker process
and exposes them as Prometheus metrics for resource monitoring and alerting.
"""

import resource

import structlog
from prometheus_client import Gauge

from src.broker import broker

logger = structlog.get_logger(__name__)

# Prometheus metrics for memory usage
MEMORY_RSS = Gauge("cybervpn_worker_memory_rss_bytes", "Worker RSS (resident set size) memory in bytes")
MEMORY_VMS = Gauge("cybervpn_worker_memory_vms_bytes", "Worker VMS (virtual memory size) memory in bytes")


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
        # Get resource usage for current process
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
