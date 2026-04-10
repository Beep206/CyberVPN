"""SEC-02: Entrypoint that runs the main API and metrics server on separate ports."""

import logging

import uvicorn
from prometheus_client import start_http_server

from src.config.settings import settings

logger = logging.getLogger("cybervpn.serve")


def _forwarded_allow_ips() -> str | None:
    if not settings.trust_proxy_headers:
        return None

    if settings.trusted_proxy_ips:
        return ",".join(settings.trusted_proxy_ips)

    logger.warning(
        "TRUST_PROXY_HEADERS enabled without TRUSTED_PROXY_IPS; defaulting forwarded_allow_ips to loopback only"
    )
    return "127.0.0.1"


def _build_api_server() -> uvicorn.Server:
    api_config = uvicorn.Config(
        "src.main:app",
        host=settings.api_host,
        port=settings.api_port,
        log_level=settings.log_level.lower(),
        access_log=settings.uvicorn_access_log,
        proxy_headers=settings.trust_proxy_headers,
        forwarded_allow_ips=_forwarded_allow_ips(),
        server_header=settings.uvicorn_server_header,
        date_header=settings.uvicorn_date_header,
        backlog=settings.uvicorn_backlog,
        timeout_keep_alive=settings.uvicorn_timeout_keep_alive,
        timeout_graceful_shutdown=settings.uvicorn_timeout_graceful_shutdown,
        limit_concurrency=settings.uvicorn_limit_concurrency,
        limit_max_requests=settings.uvicorn_limit_max_requests,
    )
    return uvicorn.Server(api_config)


def main() -> None:
    api_server = _build_api_server()
    logger.info(
        "Starting API on %s:%s and metrics on %s:%s",
        settings.api_host,
        settings.api_port,
        settings.metrics_host,
        settings.metrics_port,
    )
    start_http_server(settings.metrics_port, addr=settings.metrics_host)

    api_server.run()


if __name__ == "__main__":
    main()
