"""Generate CSV/JSON data exports."""

import csv
import json
from datetime import datetime, timezone
from pathlib import Path

import structlog
from sqlalchemy import select, text

from src.broker import broker
from src.database.session import get_session_factory
from src.services.redis_client import get_redis_client

logger = structlog.get_logger(__name__)

# Export types and their corresponding SQL queries
EXPORT_QUERIES = {
    "users": "SELECT uuid, username, status, created_at, expires_at FROM users ORDER BY created_at DESC",
    "payments": "SELECT id, user_uuid, amount, currency, status, created_at FROM payments ORDER BY created_at DESC",
    "servers": "SELECT uuid, name, country_code, is_connected, created_at FROM servers ORDER BY name",
    "audit": "SELECT id, user_uuid, action, resource, created_at FROM audit_log ORDER BY created_at DESC",
}


@broker.task(task_name="bulk_export", queue="bulk")
async def bulk_export(export_type: str, format: str = "csv", job_id: str | None = None) -> dict:
    """Generate CSV/JSON data exports.

    Queries data from PostgreSQL in batches of 1000, streams to file,
    and stores file path in Redis for download.

    Args:
        export_type: Type of data to export (users, payments, servers, audit)
        format: Export format (csv or json)
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
    rows_exported = 0

    try:
        # Prepare export file
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        export_dir = Path("/tmp/exports")
        export_dir.mkdir(exist_ok=True)
        file_path = export_dir / f"{export_type}_{timestamp}_{job_id}.{format}"

        async with session_factory() as session:
            # Execute query
            query = text(EXPORT_QUERIES[export_type])
            result = await session.execute(query)

            if format == "csv":
                # CSV export
                with open(file_path, "w", newline="", encoding="utf-8") as f:
                    writer = None
                    batch_size = 1000

                    # Fetch in batches
                    while True:
                        rows = result.fetchmany(batch_size)
                        if not rows:
                            break

                        # Initialize CSV writer with column names from first row
                        if writer is None and rows:
                            writer = csv.DictWriter(f, fieldnames=rows[0]._mapping.keys())
                            writer.writeheader()

                        for row in rows:
                            # Convert row to dict, handling datetime serialization
                            row_dict = {}
                            for key, value in row._mapping.items():
                                if isinstance(value, datetime):
                                    row_dict[key] = value.isoformat()
                                else:
                                    row_dict[key] = value
                            writer.writerow(row_dict)
                            rows_exported += 1

                        if len(rows) < batch_size:
                            break

            else:
                # JSON export
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write("[\n")
                    batch_size = 1000
                    first_item = True

                    while True:
                        rows = result.fetchmany(batch_size)
                        if not rows:
                            break

                        for row in rows:
                            # Convert row to dict
                            row_dict = {}
                            for key, value in row._mapping.items():
                                if isinstance(value, datetime):
                                    row_dict[key] = value.isoformat()
                                else:
                                    row_dict[key] = str(value) if value is not None else None

                            if not first_item:
                                f.write(",\n")
                            json.dump(row_dict, f, ensure_ascii=False, indent=2)
                            first_item = False
                            rows_exported += 1

                        if len(rows) < batch_size:
                            break

                    f.write("\n]")

        # Store file path in Redis for retrieval (24h TTL)
        export_key = f"cybervpn:export:{job_id}"
        export_meta = {
            "file_path": str(file_path),
            "export_type": export_type,
            "format": format,
            "rows": rows_exported,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        await redis.set(export_key, json.dumps(export_meta), ex=86400)

        logger.info("bulk_export_complete", export_type=export_type, format=format, rows=rows_exported, job_id=job_id)

    except Exception as e:
        logger.exception("bulk_export_failed", export_type=export_type, error=str(e), job_id=job_id)
        raise
    finally:
        await redis.aclose()

    return {"file_path": str(file_path), "rows_exported": rows_exported, "job_id": job_id}
