from src.shared.observability import before_send, before_send_transaction


class TestSentryPrivacy:
    def test_before_send_scrubs_sensitive_fields(self) -> None:
        event = {
            "request": {
                "url": "https://api.cybervpn.io/api/v1/auth/login?token=secret",
                "headers": {
                    "Authorization": "Bearer top-secret",
                    "Cookie": "session=secret",
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
                "safe_value": "ok",
            },
        }

        scrubbed = before_send(event, {})

        assert scrubbed is event
        assert scrubbed["request"]["headers"]["Authorization"] == "[Filtered]"
        assert scrubbed["request"]["headers"]["Cookie"] == "[Filtered]"
        assert scrubbed["request"]["headers"]["X-Request-Id"] == "req-1"
        assert scrubbed["request"]["url"] == "https://api.cybervpn.io/api/v1/auth/login"
        assert scrubbed["request"]["data"] == "[Filtered]"
        assert scrubbed["request"]["cookies"] == "[Filtered]"
        assert scrubbed["user"] == {"id": "internal-user-id"}
        assert scrubbed["extra"]["payment_token"] == "[Filtered]"
        assert scrubbed["extra"]["safe_value"] == "ok"

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
