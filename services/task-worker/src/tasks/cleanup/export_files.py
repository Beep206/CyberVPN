"""Cleanup old export files from temporary directory.

Periodic task that removes export files older than 24 hours to prevent
disk space accumulation from CSV/JSON exports.
"""

import time
from pathlib import Path

import structlog

from src.broker import broker

logger = structlog.get_logger(__name__)

# Export files directory
EXPORT_DIR = Path("/tmp/exports")  # noqa: S108 - task exports are intentionally temporary files.

# File age threshold in seconds (24 hours)
MAX_FILE_AGE_SECONDS = 86400


def _delete_old_export_files(cutoff_time: float) -> tuple[int, int, int]:
    deleted = 0
    errors = 0
    total_size_freed = 0

    if not EXPORT_DIR.exists():
        logger.info("export_dir_not_found", path=str(EXPORT_DIR))
        EXPORT_DIR.mkdir(exist_ok=True)
        return deleted, errors, total_size_freed

    for file_path in EXPORT_DIR.iterdir():
        if not file_path.is_file():
            continue

        try:
            stat = file_path.stat()
            if stat.st_mtime >= cutoff_time:
                continue

            file_path.unlink()
            deleted += 1
            total_size_freed += stat.st_size

            logger.debug(
                "export_file_deleted",
                file=file_path.name,
                age_hours=(time.time() - stat.st_mtime) / 3600,
                size_bytes=stat.st_size,
            )
        except OSError as e:
            errors += 1
            logger.warning("export_file_delete_failed", file=file_path.name, error=str(e))

    return deleted, errors, total_size_freed


@broker.task(task_name="cleanup_export_files", queue="cleanup")
async def cleanup_export_files() -> dict:
    """Delete export files older than 24 hours from /tmp/exports/.

    Scans the export directory and removes files whose modification time
    is older than the configured threshold.

    Returns:
        Dictionary with cleanup statistics
    """
    cutoff_time = time.time() - MAX_FILE_AGE_SECONDS

    try:
        deleted, errors, total_size_freed = _delete_old_export_files(cutoff_time)
    except Exception as e:
        logger.error("export_cleanup_failed", error=str(e))
        raise

    logger.info(
        "export_cleanup_completed",
        deleted=deleted,
        errors=errors,
        size_freed_mb=round(total_size_freed / 1024 / 1024, 2),
    )

    return {
        "deleted": deleted,
        "errors": errors,
        "size_freed_bytes": total_size_freed,
    }
