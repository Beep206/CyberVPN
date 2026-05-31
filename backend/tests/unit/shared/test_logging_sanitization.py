from urllib.parse import parse_qs, urlparse

from src.shared.logging.sanitization import (
    REDACTED,
    sanitize_headers,
    sanitize_path_params,
    sanitize_url,
)


class TestLoggingSanitization:
    def test_sanitize_url_redacts_s1_query_values(self) -> None:
        sanitized = sanitize_url(
            "https://api.cyber-vpn.net/api/v1/auth/oauth/callback"
            "?code=oauth-code&state=oauth-state&tgWebAppData=telegram-init"
            "&initData=miniapp-init&init_data=miniapp-init-snake&hash=telegram-hash"
            "&provider_payment_id=pay_123&region=nl"
        )
        params = parse_qs(urlparse(sanitized).query)

        assert params["code"] == [REDACTED]
        assert params["state"] == [REDACTED]
        assert params["tgWebAppData"] == [REDACTED]
        assert params["initData"] == [REDACTED]
        assert params["init_data"] == [REDACTED]
        assert params["hash"] == [REDACTED]
        assert params["provider_payment_id"] == [REDACTED]
        assert params["region"] == ["nl"]

    def test_sanitize_headers_redacts_s1_secret_headers(self) -> None:
        sanitized = sanitize_headers(
            {
                "Authorization": "Bearer secret",
                "X-Observability-Secret": "internal-secret",
                "X-Telegram-Bot-Api-Secret-Token": "telegram-secret",
                "X-Request-Id": "req-1",
            }
        )

        assert sanitized["Authorization"] == REDACTED
        assert sanitized["X-Observability-Secret"] == REDACTED
        assert sanitized["X-Telegram-Bot-Api-Secret-Token"] == REDACTED
        assert sanitized["X-Request-Id"] == "req-1"

    def test_sanitize_path_params_redacts_config_delivery_material(self) -> None:
        sanitized = sanitize_path_params("/api/v1/vpn/config/vless-secret-token")

        assert sanitized == f"/api/v1/vpn/config/{REDACTED}"
