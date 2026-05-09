from src.shared.observability import before_send, before_send_transaction


class TestSentryPrivacy:
    def test_before_send_scrubs_sensitive_fields(self) -> None:
        event = {
            "request": {
                "url": "https://api.cybervpn.io/api/v1/auth/login?token=secret",
                "headers": {
                    "Authorization": "Bearer top-secret",
                "Cookie": "session=secret",
                "X-Telegram-Bot-Api-Secret-Token": "telegram-secret",
                "X-Request-Id": "req-1",
            },
                "data": {"password": "secret"},
                "cookies": {"session": "secret"},
            },
            "user": {
                "id": "internal-user-id",
                "email": "user@example.com",
                "username": "alice",
                "ip_address": "127.0.0.1",
            },
            "extra": {
                "payment_token": "secret",
                "oauth_access_token": "oauth-secret",
                "totp_secret": "totp-secret",
                "support_excerpt": "user pasted vless://sensitive-config",
                "provider_name": "cryptobot",
                "safe_value": "ok",
            },
            "contexts": {
                "provisioning": {
                    "subscription_url": "https://cyber-vpn.net/api/v1/vpn/config/user",
                    "region": "nl",
                },
            },
        }

        scrubbed = before_send(event, {})

        assert scrubbed is event
        assert scrubbed["request"]["headers"]["Authorization"] == "[Filtered]"
        assert scrubbed["request"]["headers"]["Cookie"] == "[Filtered]"
        assert scrubbed["request"]["headers"]["X-Telegram-Bot-Api-Secret-Token"] == "[Filtered]"
        assert scrubbed["request"]["headers"]["X-Request-Id"] == "req-1"
        assert scrubbed["request"]["url"] == "https://api.cybervpn.io/api/v1/auth/login"
        assert scrubbed["request"]["data"] == "[Filtered]"
        assert scrubbed["request"]["cookies"] == "[Filtered]"
        assert scrubbed["user"] == {"id": "internal-user-id"}
        assert scrubbed["extra"]["payment_token"] == "[Filtered]"
        assert scrubbed["extra"]["oauth_access_token"] == "[Filtered]"
        assert scrubbed["extra"]["totp_secret"] == "[Filtered]"
        assert scrubbed["extra"]["support_excerpt"] == "[Filtered]"
        assert scrubbed["extra"]["provider_name"] == "cryptobot"
        assert scrubbed["extra"]["safe_value"] == "ok"
        assert scrubbed["contexts"]["provisioning"]["subscription_url"] == "[Filtered]"
        assert scrubbed["contexts"]["provisioning"]["region"] == "nl"

    def test_before_send_transaction_drops_health_and_metrics(self) -> None:
        assert (
            before_send_transaction(
                {"request": {"url": "https://api.cybervpn.io/health"}},
                {},
            )
            is None
        )
        assert (
            before_send_transaction(
                {"request": {"url": "https://api.cybervpn.io/metrics?verbose=true"}},
                {},
            )
            is None
        )

        regular_event = {"request": {"url": "https://api.cybervpn.io/api/v1/orders?token=secret"}}
        scrubbed = before_send_transaction(regular_event, {})
        assert scrubbed is regular_event
        assert scrubbed["request"]["url"] == "https://api.cybervpn.io/api/v1/orders"
