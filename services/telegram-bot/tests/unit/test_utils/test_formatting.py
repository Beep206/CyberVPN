"""Unit tests for formatting utilities."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from src.utils.formatting import (
    format_datetime,
    format_duration,
    format_money,
    format_traffic_bytes,
)


class TestFormatTrafficBytes:
    """Test traffic byte formatting with locale support."""

    def test_format_bytes(self) -> None:
        """Test formatting bytes."""
        assert format_traffic_bytes(512) == "512.00 B"
        assert format_traffic_bytes(0) == "0.00 B"

    def test_format_kilobytes(self) -> None:
        """Test formatting kilobytes."""
        assert format_traffic_bytes(1536) == "1.50 KB"
        assert format_traffic_bytes(1024) == "1.00 KB"

    def test_format_megabytes(self) -> None:
        """Test formatting megabytes."""
        assert format_traffic_bytes(1_048_576) == "1.00 MB"
        assert format_traffic_bytes(5_242_880) == "5.00 MB"

    def test_format_gigabytes(self) -> None:
        """Test formatting gigabytes."""
        assert format_traffic_bytes(1_073_741_824) == "1.00 GB"
        assert format_traffic_bytes(10_737_418_240) == "10.00 GB"

    def test_format_terabytes(self) -> None:
        """Test formatting terabytes."""
        assert format_traffic_bytes(1_099_511_627_776) == "1.00 TB"

    def test_locale_russian(self) -> None:
        """Test Russian locale with comma decimal separator."""
        result = format_traffic_bytes(1536, locale="ru")
        assert "1,50 KB" == result

    def test_locale_german(self) -> None:
        """Test German locale formatting."""
        result = format_traffic_bytes(2048, locale="de")
        assert "2,00 KB" == result

    def test_custom_decimal_places(self) -> None:
        """Test custom decimal places."""
        assert format_traffic_bytes(1536, decimal_places=1) == "1.5 KB"
        assert format_traffic_bytes(1536, decimal_places=3) == "1.500 KB"

    def test_edge_case_boundary(self) -> None:
        """Test boundary between units."""
        assert format_traffic_bytes(1023) == "1023.00 B"
        assert format_traffic_bytes(1024) == "1.00 KB"


class TestFormatDuration:
    """Test duration formatting."""

    def test_format_seconds(self) -> None:
        """Test formatting seconds into minutes."""
        assert format_duration(seconds=90) == "1 minute"
        assert format_duration(seconds=120) == "2 minutes"

    def test_format_hours(self) -> None:
        """Test formatting hours."""
        assert format_duration(seconds=3600) == "1 hour"
        assert format_duration(seconds=3661) == "1 hour 1 minute"
        assert format_duration(seconds=7200) == "2 hours"

    def test_format_days(self) -> None:
        """Test formatting days."""
        assert format_duration(days=1) == "1 day"
        assert format_duration(days=30) == "30 days"
        assert format_duration(seconds=86400) == "1 day"

    def test_format_timedelta(self) -> None:
        """Test formatting from timedelta object."""
        delta = timedelta(days=2, hours=3, minutes=15)
        result = format_duration(delta=delta)
        assert "2 days" in result
        assert "3 hours" in result
        assert "15 minutes" in result

    def test_short_format(self) -> None:
        """Test short format output."""
        assert format_duration(seconds=3661, short=True) == "1h 1m"
        assert format_duration(days=2, short=True) == "2d"
        assert format_duration(seconds=90, short=True) == "1m"

    def test_locale_russian(self) -> None:
        """Test Russian locale duration formatting."""
        result = format_duration(days=5, locale="ru")
        assert "5 дней" in result

    def test_locale_ukrainian(self) -> None:
        """Test Ukrainian locale duration formatting."""
        result = format_duration(days=3, locale="uk")
        assert "3 днів" in result

    def test_zero_duration(self) -> None:
        """Test zero duration handling."""
        result = format_duration(seconds=0)
        assert "0" in result

    def test_complex_duration(self) -> None:
        """Test complex duration with all components."""
        result = format_duration(seconds=90061)  # 1 day, 1 hour, 1 minute, 1 second
        assert "1 day" in result
        assert "1 hour" in result
        assert "1 minute" in result

    def test_missing_parameters_raises(self) -> None:
        """Test that missing all parameters raises ValueError."""
        with pytest.raises(ValueError, match="Must provide"):
            format_duration()


class TestFormatMoney:
    """Test monetary formatting with currency and locale."""

    def test_format_usd_english(self) -> None:
        """Test USD formatting in English locale."""
        assert format_money(1234.56, "USD", "en") == "$1,234.56"

    def test_format_eur_russian(self) -> None:
        """Test EUR formatting in Russian locale."""
        assert format_money(1234.56, "EUR", "ru") == "1 234,56 €"

    def test_format_rub_russian(self) -> None:
        """Test RUB formatting in Russian locale."""
        assert format_money(999.99, "RUB", "ru") == "999,99 ₽"

    def test_format_uah_ukrainian(self) -> None:
        """Test UAH formatting in Ukrainian locale."""
        assert format_money(500.00, "UAH", "uk") == "500,00 ₴"

    def test_no_currency_symbol(self) -> None:
        """Test formatting without currency symbol."""
        assert format_money(1234.56, "USD", "en", show_currency=False) == "1,234.56"

    def test_zero_amount(self) -> None:
        """Test formatting zero amount."""
        assert format_money(0, "USD", "en") == "$0.00"

    def test_large_amount(self) -> None:
        """Test formatting large amounts."""
        assert format_money(1_000_000.00, "USD", "en") == "$1,000,000.00"

    def test_decimal_precision(self) -> None:
        """Test decimal precision handling."""
        assert format_money(9.99, "USD", "en") == "$9.99"
        assert format_money(10.00, "USD", "en") == "$10.00"

    def test_german_locale_eur(self) -> None:
        """Test German locale with EUR."""
        result = format_money(1234.56, "EUR", "de")
        assert "1.234,56 €" == result

    def test_spanish_locale_eur(self) -> None:
        """Test Spanish locale with EUR."""
        result = format_money(999.99, "EUR", "es")
        assert "€999,99" == result


class TestFormatDatetime:
    """Test datetime formatting with locale support."""

    def test_format_english_locale(self) -> None:
        """Test English locale datetime formatting."""
        dt = datetime(2024, 1, 15, 14, 30, tzinfo=timezone.utc)
        result = format_datetime(dt, "en")
        assert result == "2024-01-15 14:30"

    def test_format_russian_locale(self) -> None:
        """Test Russian locale datetime formatting."""
        dt = datetime(2024, 1, 15, 14, 30, tzinfo=timezone.utc)
        result = format_datetime(dt, "ru")
        assert result == "15.01.2024 14:30"

    def test_format_german_locale(self) -> None:
        """Test German locale datetime formatting."""
        dt = datetime(2024, 3, 5, 9, 15, tzinfo=timezone.utc)
        result = format_datetime(dt, "de")
        assert result == "05.03.2024 09:15"

    def test_format_without_time(self) -> None:
        """Test date-only formatting."""
        dt = datetime(2024, 1, 15, 14, 30, tzinfo=timezone.utc)
        result = format_datetime(dt, "en", include_time=False)
        assert result == "2024-01-15"

    def test_format_russian_without_time(self) -> None:
        """Test Russian date-only formatting."""
        dt = datetime(2024, 1, 15, 14, 30, tzinfo=timezone.utc)
        result = format_datetime(dt, "ru", include_time=False)
        assert result == "15.01.2024"

    def test_relative_just_now(self) -> None:
        """Test relative time 'just now'."""
        dt = datetime.now(timezone.utc)
        result = format_datetime(dt, "en", relative=True)
        assert result == "just now"

    def test_relative_minutes_ago(self) -> None:
        """Test relative time in minutes."""
        dt = datetime.now(timezone.utc) - timedelta(minutes=5)
        result = format_datetime(dt, "en", relative=True)
        assert "5 minutes ago" == result

    def test_relative_hours_ago(self) -> None:
        """Test relative time in hours."""
        dt = datetime.now(timezone.utc) - timedelta(hours=2)
        result = format_datetime(dt, "en", relative=True)
        assert "2 hours ago" == result

    def test_relative_over_24_hours(self) -> None:
        """Test that relative=True falls back to absolute for old dates."""
        dt = datetime.now(timezone.utc) - timedelta(days=2)
        result = format_datetime(dt, "en", relative=True)
        # Should fall back to absolute formatting
        assert "ago" not in result
        assert "-" in result or "/" in result

    def test_naive_datetime(self) -> None:
        """Test formatting naive datetime."""
        dt = datetime(2024, 12, 25, 18, 0)
        result = format_datetime(dt, "en")
        assert result == "2024-12-25 18:00"
