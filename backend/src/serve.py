"""SEC-02: Entrypoint that runs the main API and metrics server on separate ports."""

import asyncio
import logging

import uvicorn

from src.config.settings import settings

logger = logging.getLogger("cybervpn.serve")


async def main() -> None:
    api_config = uvicorn.Config(
        "src.main:app",
        host="0.0.0.0",
        port=8000,
        log_level=settings.log_level.lower(),
    )
    metrics_config = uvicorn.Config(
        "src.main:metrics_app",
        host="0.0.0.0",
        port=settings.metrics_port,
        log_level="warning",
        access_log=False,
    )

    api_server = uvicorn.Server(api_config)
    metrics_server = uvicorn.Server(metrics_config)

    logger.info("Starting API on :8000 and metrics on :%s", settings.metrics_port)

    await asyncio.gather(api_server.serve(), metrics_server.serve())


if __name__ == "__main__":
    asyncio.run(main())
