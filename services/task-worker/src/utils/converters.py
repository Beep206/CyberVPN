"""Utility functions for data conversion and formatting.

This module provides helper functions for converting between different units,
formatting data for display, and parsing structured strings.
"""

from datetime import datetime, timezone

__all__ = [
    "bytes_to_gb",
    "bytes_to_mb",
    "format_duration",
    "format_bytes",
    "timestamp_to_iso",
    "parse_comma_separated_ids",
]


def bytes_to_gb(bytes_val: int) -> float:
    """Convert bytes to gigabytes, rounded to 2 decimal places.

    Args:
        bytes_val: Number of bytes to convert

    Returns:
        float: Value in gigabytes, rounded to 2 decimal places

    Examples:
        >>> bytes_to_gb(1073741824)
        1.0
        >>> bytes_to_gb(2147483648)
        2.0
    """
    return round(bytes_val / (1024**3), 2)


def bytes_to_mb(bytes_val: int) -> float:
    """Convert bytes to megabytes, rounded to 2 decimal places.

    Args:
        bytes_val: Number of bytes to convert

    Returns:
        float: Value in megabytes, rounded to 2 decimal places

    Examples:
        >>> bytes_to_mb(1048576)
        1.0
        >>> bytes_to_mb(5242880)
        5.0
    """
    return round(bytes_val / (1024**2), 2)


def format_duration(seconds: int) -> str:
    """Format seconds into human-readable duration string.

    Args:
        seconds: Duration in seconds

    Returns:
        str: Human-readable duration string

    Examples:
        >>> format_duration(90)
        '1m 30s'
        >>> format_duration(3600)
        '1h 0m'
        >>> format_duration(90000)
        '1d 1h'
    """
    if seconds < 0:
        return "0s"

    days, remainder = divmod(seconds, 86400)
    hours, remainder = divmod(remainder, 3600)
    minutes, secs = divmod(remainder, 60)

    parts = []
    if days:
        parts.append(f"{days}d")
    if hours:
        parts.append(f"{hours}h")
    if minutes:
        parts.append(f"{minutes}m")
    if secs or not parts:
        parts.append(f"{secs}s")

    return " ".join(parts)


def format_bytes(bytes_val: int) -> str:
    """Format bytes to human-readable string with appropriate unit.

    Args:
        bytes_val: Number of bytes to format

    Returns:
        str: Human-readable byte string with unit

    Examples:
        >>> format_bytes(0)
        '0 B'
        >>> format_bytes(1024)
        '1.00 KB'
        >>> format_bytes(1073741824)
        '1.00 GB'
    """
    if bytes_val == 0:
        return "0 B"

    units = ["B", "KB", "MB", "GB", "TB", "PB"]
    unit_index = 0
    value = float(bytes_val)

    while value >= 1024 and unit_index < len(units) - 1:
        value /= 1024
        unit_index += 1

    if unit_index == 0:
        return f"{int(value)} B"

    return f"{value:.2f} {units[unit_index]}"


def timestamp_to_iso(dt: datetime) -> str:
    """Convert datetime to ISO 8601 string. Ensures UTC timezone.

    Args:
        dt: Datetime object to convert

    Returns:
        str: ISO 8601 formatted timestamp string

    Examples:
        >>> from datetime import datetime, timezone
        >>> dt = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        >>> timestamp_to_iso(dt)
        '2024-01-01T12:00:00+00:00'
    """
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.isoformat()


def parse_comma_separated_ids(s: str) -> list[int]:
    """Parse comma-separated string of integer IDs.

    Args:
        s: Comma-separated string of integer IDs

    Returns:
        list[int]: List of parsed integer IDs

    Examples:
        >>> parse_comma_separated_ids('123,456,789')
        [123, 456, 789]
        >>> parse_comma_separated_ids('  1 , 2 , 3  ')
        [1, 2, 3]
        >>> parse_comma_separated_ids('')
        []
    """
    if not s or not s.strip():
        return []
    return [int(id_str.strip()) for id_str in s.split(",") if id_str.strip()]
