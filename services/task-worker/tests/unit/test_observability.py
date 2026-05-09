from src.observability import before_send

FILTERED = "[Filtered]"


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
                "oauth_access_token": "oauth-secret",
                "totp_secret": "totp-secret",
                "support_excerpt": "user pasted vmess://sensitive-config",
                "provider_name": "nowpayments",
                "safe_value": "ok",
            },
            "contexts": {
                "task": {
                    "authorization_header": "Bearer secret",
                    "payment_provider_id": "pay_123",
                    "subscription_url": "https://cyber-vpn.net/api/v1/vpn/config/user",
                    "queue": "payments",
                }
            },
        }

        scrubbed = before_send(event, {})

        assert scrubbed is event
        assert scrubbed["user"] == {"id": "internal-user-id"}
        assert scrubbed["extra"]["payment_token"] == FILTERED
        assert scrubbed["extra"]["oauth_access_token"] == FILTERED
        assert scrubbed["extra"]["totp_secret"] == FILTERED
        assert scrubbed["extra"]["support_excerpt"] == FILTERED
        assert scrubbed["extra"]["provider_name"] == "nowpayments"
        assert scrubbed["extra"]["safe_value"] == "ok"
        assert scrubbed["contexts"]["task"]["authorization_header"] == FILTERED
        assert scrubbed["contexts"]["task"]["payment_provider_id"] == FILTERED
        assert scrubbed["contexts"]["task"]["subscription_url"] == FILTERED
        assert scrubbed["contexts"]["task"]["queue"] == "payments"
