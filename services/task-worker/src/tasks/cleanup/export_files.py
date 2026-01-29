"""Cleanup old export files from temporary directory.

Periodic task that removes export files older than 24 hours to prevent
disk space accumulation from CSV/JSON exports.
"""

import os
import time

import structlog

from src.broker import broker

logger = structlog.get_logger(__name__)

# Export files directory
EXPORT_DIR = "/tmp/exports"  # noqa: S108

# File age threshold in seconds (24 hours)
MAX_FILE_AGE_SECONDS = 86400


@broker.task(task_name="cleanup_export_files", queue="cleanup")
async def cleanup_export_files() -> dict:
    """Delete export files older than 24 hours from /tmp/exports/.

    Scans the export directory and removes files whose modification time
    is older than the configured threshold.

    Returns:
        Dictionary with cleanup statistics
    """
    deleted = 0
    errors = 0
    total_size_freed = 0
    cutoff_time = time.time() - MAX_FILE_AGE_SECONDS

    try:
        # Create directory if it doesn't exist
        if not os.path.exists(EXPORT_DIR):
            logger.info("export_dir_not_found", path=EXPORT_DIR)
            os.makedirs(EXPORT_DIR, exist_ok=True)
            return {"deleted": 0, "errors": 0, "size_freed_bytes": 0}

        # Scan directory for old files
        for filename in os.listdir(EXPORT_DIR):
            file_path = os.path.join(EXPORT_DIR, filename)

            # Skip directories
            if not os.path.isfile(file_path):
                continue

            try:
                # Check file age
                mtime = os.path.getmtime(file_path)
                if mtime < cutoff_time:
                    # Get file size before deletion
                    file_size = os.path.getsize(file_path)

                    # Delete the file
                    os.remove(file_path)

                    deleted += 1
                    total_size_freed += file_size

                    logger.debug(
                        "export_file_deleted",
                        file=filename,
                        age_hours=(time.time() - mtime) / 3600,
                        size_bytes=file_size,
                    )
            except OSError as e:
                errors += 1
                logger.warning("export_file_delete_failed", file=filename, error=str(e))

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
