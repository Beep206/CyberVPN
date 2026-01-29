"""Structlog configuration for the CyberVPN task worker.

Configures JSON-formatted structured logging with:
- Timestamp processor (ISO 8601)
- Log level filtering from settings
- Correlation ID binding via contextvars (async-safe)
- Exception formatting with stack traces
- Event renaming for consistency
"""

import logging
import sys

import structlog

from src.config import get_settings


def configure_logging() -> None:
    """Configure structlog and stdlib logging for JSON output.

    Must be called once at application startup before any log calls.
    Uses ``structlog.contextvars`` for async-safe context propagation
    across ``await`` boundaries, ensuring correlation IDs and task
    metadata persist through the async call chain.
    """
    settings = get_settings()

    # Map string log level to numeric
    log_level = getattr(logging, settings.log_level.upper(), logging.INFO)

    # Shared processors used by both structlog and stdlib integration
    shared_processors: list[structlog.types.Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.StackInfoRenderer(),
        structlog.dev.set_exc_info,
        structlog.processors.TimeStamper(fmt="iso"),
    ]

    # Configure structlog
    structlog.configure(
        processors=[
            *shared_processors,
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(log_level),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )

    # Also configure stdlib logging to route through structlog
    # This captures logs from third-party libraries (httpx, sqlalchemy, etc.)
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(log_level)

    # Use structlog formatter for stdlib logs
    formatter = structlog.stdlib.ProcessorFormatter(
        processors=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            structlog.processors.JSONRenderer(),
        ],
        foreign_pre_chain=shared_processors,
    )
    handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.addHandler(handler)
    root_logger.setLevel(log_level)

    # Quiet noisy loggers
    for noisy in ("httpx", "httpcore", "asyncio"):
        logging.getLogger(noisy).setLevel(logging.WARNING)
