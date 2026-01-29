"""Prometheus metrics HTTP server for exposing /metrics endpoint.

Starts a simple HTTP server that serves Prometheus metrics on a configurable port.
The server runs in a separate thread and is automatically started on worker startup.
"""

import structlog
from prometheus_client import REGISTRY, start_http_server

logger = structlog.get_logger(__name__)


def start_metrics_server(port: int = 9091) -> None:
    """Start Prometheus metrics HTTP server.

    Args:
        port: Port number to listen on (default: 9091)

    Raises:
        OSError: If the port is already in use
    """
    try:
        start_http_server(port, registry=REGISTRY)
        logger.info("metrics_server_started", port=port, endpoint="/metrics")
    except OSError as e:
        if "Address already in use" in str(e):
            logger.warning(
                "metrics_server_already_running",
                port=port,
                message="Metrics server port already in use, skipping startup",
            )
        else:
            logger.exception("metrics_server_start_failed", port=port, error=str(e))
            raise
