"""Unit tests for normalized auth client context labels."""

from src.infrastructure.monitoring.client_context import resolve_mobile_client_context, resolve_web_client_context


def test_resolve_web_client_context_for_desktop_chrome() -> None:
    context = resolve_web_client_context(
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36"
    )

    assert context.client_type == "desktop"
    assert context.os_family == "windows"
    assert context.client_app == "chrome"


def test_resolve_web_client_context_for_mobile_safari() -> None:
    context = resolve_web_client_context(
        "Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X) AppleWebKit/605.1.15 "
        "(KHTML, like Gecko) Version/18.0 Mobile/15E148 Safari/604.1",
        sec_ch_ua_mobile="?1",
    )

    assert context.client_type == "mobile"
    assert context.os_family == "ios"
    assert context.client_app == "safari"


def test_resolve_web_client_context_for_telegram_webview() -> None:
    context = resolve_web_client_context("Telegram/10.0 (iPhone; iOS 18.0; Scale/3.00) Mobile")

    assert context.client_type == "mobile"
    assert context.client_app == "telegram_webview"


def test_resolve_mobile_client_context_for_ios() -> None:
    context = resolve_mobile_client_context("ios")

    assert context.client_type == "mobile"
    assert context.os_family == "ios"
    assert context.client_app == "mobile_app"
