"""CyberVPN Telegram Bot — Client device info extraction.

Functions to extract device type, platform, and client information
from Telegram user-agent or client data for analytics and logging.
"""

from __future__ import annotations

import re
from enum import StrEnum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from aiogram.types import User


class DeviceType(StrEnum):
    """Device type enumeration."""

    MOBILE = "mobile"
    DESKTOP = "desktop"
    WEB = "web"
    UNKNOWN = "unknown"


class Platform(StrEnum):
    """Platform/OS enumeration."""

    IOS = "ios"
    ANDROID = "android"
    WINDOWS = "windows"
    MACOS = "macos"
    LINUX = "linux"
    WEB = "web"
    UNKNOWN = "unknown"


def get_device_type(user: User | None) -> DeviceType:
    """Extract device type from Telegram user info.

    Telegram doesn't expose direct device info, so we make educated
    guesses based on available data. For more accurate tracking,
    use platform-specific clients or ask user to select.

    Args:
        user: Telegram User object.

    Returns:
        Estimated device type.
    """
    if user is None:
        return DeviceType.UNKNOWN

    # Telegram doesn't provide direct device type info
    # We can only make rough estimates from language/username patterns
    # For production, consider asking users or using analytics events
    return DeviceType.UNKNOWN


def get_platform(user: User | None) -> Platform:
    """Extract platform/OS from Telegram user info.

    Note: Telegram API doesn't expose client platform directly.
    This function returns best-effort estimates. For accurate tracking,
    integrate with Telegram's WebApp or use analytics events.

    Args:
        user: Telegram User object.

    Returns:
        Estimated platform.
    """
    if user is None:
        return Platform.UNKNOWN

    # Telegram API doesn't expose platform info
    # language_code can give hints but is not reliable for platform detection
    return Platform.UNKNOWN


def extract_client_info(user: User | None) -> dict[str, str]:
    """Extract comprehensive client information.

    Combines device type, platform, and any other available metadata
    into a structured dict for logging/analytics.

    Args:
        user: Telegram User object.

    Returns:
        Dict with client info fields.
    """
    if user is None:
        return {
            "device_type": DeviceType.UNKNOWN,
            "platform": Platform.UNKNOWN,
            "language_code": "unknown",
            "is_bot": False,
            "is_premium": False,
        }

    return {
        "device_type": get_device_type(user),
        "platform": get_platform(user),
        "language_code": user.language_code or "unknown",
        "is_bot": user.is_bot,
        "is_premium": getattr(user, "is_premium", False),
        "username": user.username or "none",
    }


def parse_user_agent(user_agent: str | None) -> dict[str, str]:
    """Parse user-agent string for client details.

    Note: Telegram Bot API doesn't provide user-agent headers.
    This function is for future use if user-agent becomes available
    via WebApp or other means.

    Args:
        user_agent: User-agent string.

    Returns:
        Parsed client info dict.
    """
    if not user_agent:
        return {
            "device_type": DeviceType.UNKNOWN,
            "platform": Platform.UNKNOWN,
            "browser": "unknown",
            "version": "unknown",
        }

    ua_lower = user_agent.lower()

    # Detect platform
    platform = Platform.UNKNOWN
    if "android" in ua_lower:
        platform = Platform.ANDROID
    elif "iphone" in ua_lower or "ipad" in ua_lower:
        platform = Platform.IOS
    elif "windows" in ua_lower:
        platform = Platform.WINDOWS
    elif "mac os" in ua_lower or "macos" in ua_lower:
        platform = Platform.MACOS
    elif "linux" in ua_lower:
        platform = Platform.LINUX

    # Detect device type
    device_type = DeviceType.UNKNOWN
    if any(mobile in ua_lower for mobile in ["android", "iphone", "ipad", "mobile"]):
        device_type = DeviceType.MOBILE
    elif any(desktop in ua_lower for desktop in ["windows", "mac os", "linux", "x11"]):
        device_type = DeviceType.DESKTOP
    elif "mozilla" in ua_lower or "chrome" in ua_lower:
        device_type = DeviceType.WEB

    # Extract browser if web client
    browser = "unknown"
    if device_type == DeviceType.WEB:
        if "chrome" in ua_lower and "edg" not in ua_lower:
            browser = "chrome"
        elif "firefox" in ua_lower:
            browser = "firefox"
        elif "safari" in ua_lower and "chrome" not in ua_lower:
            browser = "safari"
        elif "edg" in ua_lower:
            browser = "edge"

    # Extract version (rough estimate)
    version = "unknown"
    version_match = re.search(r"(\d+\.\d+)", user_agent)
    if version_match:
        version = version_match.group(1)

    return {
        "device_type": device_type,
        "platform": platform,
        "browser": browser,
        "version": version,
    }


def is_mobile_client(user: User | None) -> bool:
    """Check if user is likely on a mobile device.

    Args:
        user: Telegram User object.

    Returns:
        True if mobile device detected (best effort).
    """
    device_type = get_device_type(user)
    return device_type == DeviceType.MOBILE


def get_client_summary(user: User | None) -> str:
    """Get a human-readable client summary string.

    Args:
        user: Telegram User object.

    Returns:
        Summary string like "Android Mobile" or "Unknown Client".
    """
    if user is None:
        return "Unknown Client"

    info = extract_client_info(user)
    platform = info["platform"].title()
    device_type = info["device_type"].title()

    if platform != "Unknown" and device_type != "Unknown":
        return f"{platform} {device_type}"
    if platform != "Unknown":
        return platform
    if device_type != "Unknown":
        return device_type

    return "Unknown Client"
