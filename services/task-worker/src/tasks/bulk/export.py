"""Generate CSV/JSON data exports."""

import csv
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import structlog
from sqlalchemy import text

from src.broker import broker
from src.database.session import get_session_factory
from src.services.redis_client import get_redis_client

logger = structlog.get_logger(__name__)

EXPORT_DIR = Path("/tmp/exports")  # noqa: S108 - task exports are intentionally temporary files.

# Export types and their corresponding SQL queries
EXPORT_QUERIES = {
    "users": "SELECT uuid, username, status, created_at, expires_at FROM users ORDER BY created_at DESC",
    "payments": "SELECT id, user_uuid, amount, currency, status, created_at FROM payments ORDER BY created_at DESC",
    "servers": "SELECT uuid, name, country_code, is_connected, created_at FROM servers ORDER BY name",
    "audit": "SELECT id, user_uuid, action, resource, created_at FROM audit_log ORDER BY created_at DESC",
}


def _to_csv_value(value: Any) -> Any:
    if isinstance(value, datetime):
        return value.isoformat()
    return value


def _to_json_value(value: Any) -> Any:
    if isinstance(value, datetime):
        return value.isoformat()
    return str(value) if value is not None else None


def _write_csv_export(file_path: Path, result: Any) -> int:
    rows_exported = 0

    with file_path.open("w", newline="", encoding="utf-8") as file:
        writer = None
        batch_size = 1000

        while True:
            rows = result.fetchmany(batch_size)
            if not rows:
                break

            if writer is None:
                writer = csv.DictWriter(file, fieldnames=rows[0]._mapping.keys())
                writer.writeheader()

            for row in rows:
                writer.writerow({key: _to_csv_value(value) for key, value in row._mapping.items()})
                rows_exported += 1

            if len(rows) < batch_size:
                break

    return rows_exported


def _prepare_export_file_path(export_type: str, export_format: str, timestamp: str, job_id: str) -> Path:
    EXPORT_DIR.mkdir(exist_ok=True)
    return EXPORT_DIR / f"{export_type}_{timestamp}_{job_id}.{export_format}"


def _write_json_export(file_path: Path, result: Any) -> int:
    rows_exported = 0

    with file_path.open("w", encoding="utf-8") as file:
        file.write("[\n")
        batch_size = 1000
        first_item = True

        while True:
            rows = result.fetchmany(batch_size)
            if not rows:
                break

            for row in rows:
                row_dict = {key: _to_json_value(value) for key, value in row._mapping.items()}

                if not first_item:
                    file.write(",\n")
                json.dump(row_dict, file, ensure_ascii=False, indent=2)
                first_item = False
                rows_exported += 1

            if len(rows) < batch_size:
                break

        file.write("\n]")

    return rows_exported


@broker.task(task_name="bulk_export", queue="bulk")
async def bulk_export(export_type: str, format: str = "csv", job_id: str | None = None) -> dict:  # noqa: A002
    """Generate CSV/JSON data exports.

    Queries data from PostgreSQL in batches of 1000, streams to file,
    and stores file path in Redis for download.

    Args:
        export_type: Type of data to export (users, payments, servers, audit)
        format: Export format (csv or json). This name is part of the task payload contract.
        job_id: Optional job ID for tracking

    Returns:
        Dictionary with file_path, rows_exported, and job_id
    """
    if export_type not in EXPORT_QUERIES:
        raise ValueError(f"Invalid export_type: {export_type}. Must be one of {list(EXPORT_QUERIES.keys())}")

    if format not in ["csv", "json"]:
        raise ValueError(f"Invalid format: {format}. Must be 'csv' or 'json'")

    if not job_id:
        import uuid

        job_id = str(uuid.uuid4())

    session_factory = get_session_factory()
    redis = get_redis_client()

    try:
        timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
        file_path = _prepare_export_file_path(export_type, format, timestamp, job_id)

        async with session_factory() as session:
            query = text(EXPORT_QUERIES[export_type])
            result = await session.execute(query)
            rows_exported = (
                _write_csv_export(file_path, result) if format == "csv" else _write_json_export(file_path, result)
            )

        export_key = f"cybervpn:export:{job_id}"
        export_meta = {
            "file_path": str(file_path),
            "export_type": export_type,
            "format": format,
            "rows": rows_exported,
            "created_at": datetime.now(UTC).isoformat(),
        }
        await redis.set(export_key, json.dumps(export_meta), ex=86400)

        logger.info("bulk_export_complete", export_type=export_type, format=format, rows=rows_exported, job_id=job_id)

    except Exception as e:
        logger.exception("bulk_export_failed", export_type=export_type, error=str(e), job_id=job_id)
        raise
    finally:
        await redis.aclose()

    return {"file_path": str(file_path), "rows_exported": rows_exported, "job_id": job_id}
