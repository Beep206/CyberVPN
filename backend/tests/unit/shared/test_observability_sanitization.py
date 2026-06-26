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


def test_before_send_scrubs_growth_code_and_registration_token_markers() -> None:
    event = {
        "request": {
            "url": "https://api.cyber-vpn.net/checkout?code_input=SAVE100&registration_access_token=secret",
            "headers": {"X-Request-Id": "req-2"},
        },
        "extra": {
            "growth_code": "SAVE100",
            "promo_code": "SAVE100",
            "invite_code": "INVITE100",
            "gift_code": "GIFT100",
            "referral_code": "REF100",
            "raw_code": "RAW100",
            "code_input": "SAVE100",
            "registration_access_token": "registration-secret",
            "onboarding_flow_token": "flow-secret",
            "safe_code_ref": {"code_hash": "abc", "code_prefix": "SAV"},
        },
        "contexts": {
            "checkout": {
                "nested": {
                    "raw_code": "RAW100",
                    "safe_result": "accepted",
                }
            }
        },
    }

    sanitized = before_send(event, {})

    assert sanitized is event
    assert event["request"]["url"] == "https://api.cyber-vpn.net/checkout"
    assert event["extra"]["growth_code"] == "[Filtered]"
    assert event["extra"]["promo_code"] == "[Filtered]"
    assert event["extra"]["invite_code"] == "[Filtered]"
    assert event["extra"]["gift_code"] == "[Filtered]"
    assert event["extra"]["referral_code"] == "[Filtered]"
    assert event["extra"]["raw_code"] == "[Filtered]"
    assert event["extra"]["code_input"] == "[Filtered]"
    assert event["extra"]["registration_access_token"] == "[Filtered]"
    assert event["extra"]["onboarding_flow_token"] == "[Filtered]"
    assert event["extra"]["safe_code_ref"] == {"code_hash": "abc", "code_prefix": "SAV"}
    assert event["contexts"]["checkout"] == "[Filtered]"
