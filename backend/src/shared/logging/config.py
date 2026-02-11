"""Structured JSON logging configuration using structlog.

This module configures structlog for production-grade structured logging:
- JSON output for log aggregation (Loki, ELK, etc.)
- Request ID correlation via contextvars
- Consistent timestamps in UTC
- Source code location tracking
- Performance-optimized processors
"""

import logging
import sys

import structlog


def configure_logging(
    json_logs: bool = True,
    log_level: str = "INFO",
) -> None:
    """Configure structlog for structured JSON logging.

    Args:
        json_logs: If True, output JSON logs. If False, use ConsoleRenderer for development.
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL).

    This should be called early in application startup (in lifespan context manager)
    before any logging occurs.
    """
    # Set standard library logging level
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, log_level.upper(), logging.INFO),
    )

    # Configure structlog processors
    shared_processors = [
        # Add log level name
        structlog.stdlib.add_log_level,
        # Add logger name
        structlog.stdlib.add_logger_name,
        # Add timestamp in ISO 8601 format (UTC)
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        # Add source code location (file, function, line)
        structlog.processors.CallsiteParameterAdder(
            parameters=[
                structlog.processors.CallsiteParameter.FILENAME,
                structlog.processors.CallsiteParameter.FUNC_NAME,
                structlog.processors.CallsiteParameter.LINENO,
            ],
        ),
        # Add exception info if present
        structlog.processors.format_exc_info,
        # Add request context from contextvars (request_id, user_id, etc.)
        structlog.contextvars.merge_contextvars,
        # Stack unwinder for exceptions
        structlog.processors.StackInfoRenderer(),
    ]

    # Choose renderer based on environment
    if json_logs:
        # Production: JSON logs for log aggregation
        renderer = structlog.processors.JSONRenderer()
    else:
        # Development: Human-readable console output with colors
        renderer = structlog.dev.ConsoleRenderer(colors=True)

    # Configure structlog
    structlog.configure(
        processors=[
            *shared_processors,
            # Prepare event dict for stdlib logging
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        # Use standard library logging as the final output
        logger_factory=structlog.stdlib.LoggerFactory(),
        # Cache logger instances for performance
        cache_logger_on_first_use=True,
    )

    # Configure standard library logging to use structlog formatter
    formatter = structlog.stdlib.ProcessorFormatter(
        processors=[
            # Remove _record and _from_structlog keys added by ProcessorFormatter
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            renderer,
        ],
        foreign_pre_chain=shared_processors,
    )

    # Apply formatter to root logger handler
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)
    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.addHandler(handler)
    root_logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))
