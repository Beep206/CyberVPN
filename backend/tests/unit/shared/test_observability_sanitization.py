from src.shared.observability import before_send


def test_before_send_scrubs_telegram_init_data_variants() -> None:
    event = {
        "request": {
            "url": "https://api.cyber-vpn.net/api/v1/auth/telegram/miniapp?initData=secret&hash=secret",
            "headers": {"Authorization": "Bearer secret", "X-Request-Id": "req-1"},
        },
        "extra": {
            "initData": "secret-init-data",
            "init_data": "secret-init-data",
            "tgWebAppData": "secret-webapp-data",
            "telegram_hash": "secret-hash",
            "safe_field": "safe",
            "nested": {"init_data_hash": "secret-hash"},
        },
    }

    sanitized = before_send(event, {})

    assert sanitized is event
    assert event["request"]["url"] == "https://api.cyber-vpn.net/api/v1/auth/telegram/miniapp"
    assert event["request"]["headers"]["Authorization"] == "[Filtered]"
    assert event["request"]["headers"]["X-Request-Id"] == "req-1"
    assert event["extra"]["initData"] == "[Filtered]"
    assert event["extra"]["init_data"] == "[Filtered]"
    assert event["extra"]["tgWebAppData"] == "[Filtered]"
    assert event["extra"]["telegram_hash"] == "[Filtered]"
    assert event["extra"]["safe_field"] == "safe"
    assert event["extra"]["nested"]["init_data_hash"] == "[Filtered]"
