"""SQLAlchemy instrumentation for database metrics.

Tracks query duration and connection pool metrics using SQLAlchemy event listeners.
"""

import time

from sqlalchemy import event
from sqlalchemy.engine import Engine
from sqlalchemy.pool import Pool

from src.infrastructure.monitoring.metrics import db_connections_active, db_query_duration_seconds


def instrument_database(engine: Engine) -> None:
    """Instrument SQLAlchemy engine with Prometheus metrics.

    Args:
        engine: SQLAlchemy async engine to instrument

    This should be called once during application startup after creating the engine.
    """

    @event.listens_for(engine.sync_engine, "before_cursor_execute")
    def before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
        """Record query start time."""
        context._query_start_time = time.perf_counter()

    @event.listens_for(engine.sync_engine, "after_cursor_execute")
    def after_cursor_execute(conn, cursor, statement, parameters, context, executemany):
        """Record query duration."""
        if hasattr(context, "_query_start_time"):
            duration = time.perf_counter() - context._query_start_time

            # Extract table name from SQL statement (simplified)
            table = "unknown"
            statement_lower = statement.lower()
            if "from" in statement_lower:
                # Extract table after FROM
                try:
                    parts = statement_lower.split("from")[1].split()
                    if parts:
                        table = parts[0].strip().split(".")[
                            -1
                        ]  # Handle schema.table
                except (IndexError, AttributeError):
                    pass
            elif "into" in statement_lower:
                # Extract table after INTO (for INSERT)
                try:
                    parts = statement_lower.split("into")[1].split()
                    if parts:
                        table = parts[0].strip().split(".")[
                            -1
                        ]  # Handle schema.table
                except (IndexError, AttributeError):
                    pass
            elif "update" in statement_lower:
                # Extract table after UPDATE
                try:
                    parts = statement_lower.split("update")[1].split()
                    if parts:
                        table = parts[0].strip().split(".")[
                            -1
                        ]  # Handle schema.table
                except (IndexError, AttributeError):
                    pass

            # Determine operation type
            operation = "unknown"
            if statement_lower.startswith("select"):
                operation = "select"
            elif statement_lower.startswith("insert"):
                operation = "insert"
            elif statement_lower.startswith("update"):
                operation = "update"
            elif statement_lower.startswith("delete"):
                operation = "delete"

            db_query_duration_seconds.labels(operation=operation, table=table).observe(
                duration
            )

    @event.listens_for(Pool, "connect")
    def on_connect(dbapi_conn, connection_record):
        """Increment active connections gauge on connect."""
        db_connections_active.inc()

    @event.listens_for(Pool, "close")
    def on_close(dbapi_conn, connection_record):
        """Decrement active connections gauge on close."""
        db_connections_active.dec()
