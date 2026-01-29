"""Formatting utilities for displaying data to users."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Literal

import structlog

logger = structlog.get_logger(__name__)

# Locale-specific formatting configurations
LOCALE_FORMATS = {
    "en": {
        "decimal_sep": ".",
        "thousand_sep": ",",
        "currency_symbol": "$",
        "currency_position": "before",
        "date_format": "%Y-%m-%d %H:%M",
    },
    "ru": {
        "decimal_sep": ",",
        "thousand_sep": " ",
        "currency_symbol": "₽",
        "currency_position": "after",
        "date_format": "%d.%m.%Y %H:%M",
    },
    "uk": {
        "decimal_sep": ",",
        "thousand_sep": " ",
        "currency_symbol": "₴",
        "currency_position": "after",
        "date_format": "%d.%m.%Y %H:%M",
    },
    "de": {
        "decimal_sep": ",",
        "thousand_sep": ".",
        "currency_symbol": "€",
        "currency_position": "after",
        "date_format": "%d.%m.%Y %H:%M",
    },
    "es": {
        "decimal_sep": ",",
        "thousand_sep": ".",
        "currency_symbol": "€",
        "currency_position": "before",
        "date_format": "%d/%m/%Y %H:%M",
    },
}


def format_traffic_bytes(
    bytes_count: int,
    locale: str = "en",
    decimal_places: int = 2,
) -> str:
    """
    Format byte count into human-readable traffic string.

    Args:
        bytes_count: Number of bytes
        locale: Locale code for formatting (not used for units, but for decimal separator)
        decimal_places: Number of decimal places to show

    Returns:
        Formatted string like "1.5 GB" or "500 MB"

    Examples:
        >>> format_traffic_bytes(1536)
        "1.50 KB"
        >>> format_traffic_bytes(1073741824)
        "1.00 GB"
        >>> format_traffic_bytes(1536, locale="ru")
        "1,50 KB"
    """
    units = ["B", "KB", "MB", "GB", "TB", "PB"]
    size = float(bytes_count)
    unit_index = 0

    while size >= 1024.0 and unit_index < len(units) - 1:
        size /= 1024.0
        unit_index += 1

    locale_config = LOCALE_FORMATS.get(locale, LOCALE_FORMATS["en"])
    decimal_sep = locale_config["decimal_sep"]

    # Format with proper decimal separator
    formatted_size = f"{size:.{decimal_places}f}".replace(".", decimal_sep)

    return f"{formatted_size} {units[unit_index]}"


def format_duration(
    seconds: int | None = None,
    days: int | None = None,
    delta: timedelta | None = None,
    locale: str = "en",
    short: bool = False,
) -> str:
    """
    Format duration into human-readable string.

    Args:
        seconds: Duration in seconds
        days: Duration in days
        delta: timedelta object
        locale: Locale code for i18n-aware units
        short: Use short format (1d 2h instead of 1 day 2 hours)

    Returns:
        Formatted duration string

    Examples:
        >>> format_duration(seconds=3661)
        "1 hour 1 minute"
        >>> format_duration(days=30)
        "30 days"
        >>> format_duration(seconds=3661, short=True)
        "1h 1m"
    """
    # Simple i18n mappings (in production, use proper i18n library)
    units_long = {
        "en": {"day": "day", "days": "days", "hour": "hour", "hours": "hours", "minute": "minute", "minutes": "minutes"},
        "ru": {"day": "день", "days": "дней", "hour": "час", "hours": "часов", "minute": "минута", "minutes": "минут"},
        "uk": {"day": "день", "days": "днів", "hour": "година", "hours": "годин", "minute": "хвилина", "minutes": "хвилин"},
    }

    units_short = {
        "d": "d",
        "h": "h",
        "m": "m",
        "s": "s",
    }

    # Convert to timedelta
    if delta is not None:
        td = delta
    elif seconds is not None:
        td = timedelta(seconds=seconds)
    elif days is not None:
        td = timedelta(days=days)
    else:
        raise ValueError("Must provide seconds, days, or delta")

    total_seconds = int(td.total_seconds())
    days_count = total_seconds // 86400
    hours_count = (total_seconds % 86400) // 3600
    minutes_count = (total_seconds % 3600) // 60
    seconds_count = total_seconds % 60

    parts = []

    if short:
        if days_count > 0:
            parts.append(f"{days_count}{units_short['d']}")
        if hours_count > 0:
            parts.append(f"{hours_count}{units_short['h']}")
        if minutes_count > 0:
            parts.append(f"{minutes_count}{units_short['m']}")
        if not parts and seconds_count > 0:
            parts.append(f"{seconds_count}{units_short['s']}")
    else:
        units = units_long.get(locale, units_long["en"])
        if days_count > 0:
            day_unit = units["day"] if days_count == 1 else units["days"]
            parts.append(f"{days_count} {day_unit}")
        if hours_count > 0:
            hour_unit = units["hour"] if hours_count == 1 else units["hours"]
            parts.append(f"{hours_count} {hour_unit}")
        if minutes_count > 0:
            minute_unit = units["minute"] if minutes_count == 1 else units["minutes"]
            parts.append(f"{minutes_count} {minute_unit}")

    return " ".join(parts) if parts else "0" + units_short["m"] if short else f"0 {units_long.get(locale, units_long['en'])['minutes']}"


def format_money(
    amount: float,
    currency: Literal["USD", "EUR", "RUB", "UAH"] = "USD",
    locale: str = "en",
    show_currency: bool = True,
) -> str:
    """
    Format monetary amount with proper locale and currency.

    Args:
        amount: Monetary amount
        currency: Currency code (USD, EUR, RUB, UAH)
        locale: Locale code for formatting
        show_currency: Whether to show currency symbol

    Returns:
        Formatted money string

    Examples:
        >>> format_money(1234.56, "USD", "en")
        "$1,234.56"
        >>> format_money(1234.56, "EUR", "ru")
        "1 234,56 €"
        >>> format_money(1234.56, "USD", "en", show_currency=False)
        "1,234.56"
    """
    currency_symbols = {
        "USD": "$",
        "EUR": "€",
        "RUB": "₽",
        "UAH": "₴",
    }

    locale_config = LOCALE_FORMATS.get(locale, LOCALE_FORMATS["en"])
    decimal_sep = locale_config["decimal_sep"]
    thousand_sep = locale_config["thousand_sep"]

    # Split into integer and decimal parts
    integer_part = int(amount)
    decimal_part = int(round((amount - integer_part) * 100))

    # Format integer part with thousand separators
    integer_str = f"{integer_part:,}".replace(",", thousand_sep)

    # Format full amount
    formatted_amount = f"{integer_str}{decimal_sep}{decimal_part:02d}"

    if not show_currency:
        return formatted_amount

    # Add currency symbol
    symbol = currency_symbols.get(currency, currency)
    position = locale_config["currency_position"]

    if position == "before":
        return f"{symbol}{formatted_amount}"
    else:
        return f"{formatted_amount} {symbol}"


def format_datetime(
    dt: datetime,
    locale: str = "en",
    include_time: bool = True,
    relative: bool = False,
) -> str:
    """
    Format datetime with locale-aware formatting.

    Args:
        dt: Datetime to format
        locale: Locale code for formatting
        include_time: Whether to include time component
        relative: Show relative time (e.g., "2 hours ago") if recent

    Returns:
        Formatted datetime string

    Examples:
        >>> dt = datetime(2024, 1, 15, 14, 30)
        >>> format_datetime(dt, "en")
        "2024-01-15 14:30"
        >>> format_datetime(dt, "ru")
        "15.01.2024 14:30"
    """
    locale_config = LOCALE_FORMATS.get(locale, LOCALE_FORMATS["en"])
    date_format = locale_config["date_format"]

    if not include_time:
        # Remove time part from format
        date_format = date_format.split(" ")[0] if " " in date_format else date_format

    if relative:
        now = datetime.now(dt.tzinfo) if dt.tzinfo else datetime.now()
        diff = now - dt

        # If less than 24 hours, show relative
        if diff.total_seconds() < 86400:
            hours = int(diff.total_seconds() // 3600)
            if hours > 0:
                unit = "hour" if hours == 1 else "hours"
                return f"{hours} {unit} ago"
            minutes = int(diff.total_seconds() // 60)
            if minutes > 0:
                unit = "minute" if minutes == 1 else "minutes"
                return f"{minutes} {unit} ago"
            return "just now"

    return dt.strftime(date_format)
