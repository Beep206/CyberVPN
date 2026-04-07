"""SEC-02: Entrypoint that runs the main API and metrics server on separate ports."""

import logging

import uvicorn
from prometheus_client import start_http_server

from src.config.settings import settings

logger = logging.getLogger("cybervpn.serve")


def _build_api_server() -> uvicorn.Server:
    api_config = uvicorn.Config("src.main:app", host="0.0.0.0", port=8000, log_level=settings.log_level.lower())
    return uvicorn.Server(api_config)


def main() -> None:
    api_server = _build_api_server()
    logger.info("Starting API on :8000 and metrics on :%s", settings.metrics_port)
    start_http_server(settings.metrics_port)

    api_server.run()


if __name__ == "__main__":
    main()
