from src.observability import before_send


class TestTaskWorkerSentryPrivacy:
    def test_before_send_scrubs_sensitive_fields(self) -> None:
        event = {
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
            "contexts": {
                "task": {
                    "authorization_header": "Bearer secret",
                    "queue": "payments",
                }
            },
        }

        scrubbed = before_send(event, {})

        assert scrubbed is event
        assert scrubbed["user"] == {"id": "internal-user-id"}
        assert scrubbed["extra"]["payment_token"] == "[Filtered]"
        assert scrubbed["extra"]["safe_value"] == "ok"
        assert scrubbed["contexts"]["task"]["authorization_header"] == "[Filtered]"
        assert scrubbed["contexts"]["task"]["queue"] == "payments"
