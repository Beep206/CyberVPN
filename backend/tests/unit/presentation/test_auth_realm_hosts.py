import pytest
from starlette.requests import Request

from src.config.settings import settings
from src.presentation.dependencies.auth_realms import _public_capture_host, _web_realm_hint_for_host


def _request_for_host(host: str) -> Request:
    return Request(
        {
            "type": "http",
            "method": "POST",
            "path": "/api/v1/auth/login",
            "headers": [(b"host", host.encode("ascii"))],
        }
    )


def _public_request(*, host: str, forwarded_host: str | None = None, client_host: str = "203.0.113.10") -> Request:
    headers = [(b"host", host.encode("ascii"))]
    if forwarded_host is not None:
        headers.append((b"x-forwarded-host", forwarded_host.encode("ascii")))
    return Request(
        {
            "type": "http",
            "method": "POST",
            "path": "/api/v1/partner-attribution/capture",
            "headers": headers,
            "client": (client_host, 52344),
        }
    )


def test_partner_local_portal_host_resolves_partner_realm_hint() -> None:
    assert _web_realm_hint_for_host(_request_for_host("portal.localhost:3004")) == "partner"


def test_partner_local_storefront_host_resolves_partner_realm_hint() -> None:
    assert _web_realm_hint_for_host(_request_for_host("storefront.localhost:3004")) == "partner"


def test_loopback_backend_host_stays_customer_realm_hint() -> None:
    assert _web_realm_hint_for_host(_request_for_host("127.0.0.1:18080")) == "customer"


def test_production_admin_host_stays_admin_realm_hint() -> None:
    assert _web_realm_hint_for_host(_request_for_host("admin.cyber-vpn.net")) == "admin"


def test_public_capture_ignores_spoofed_forwarded_host_from_untrusted_peer(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "environment", "production")
    monkeypatch.setattr(settings, "trusted_proxy_ips", ["10.0.0.0/8"])

    request = _public_request(host="cyber-vpn.net", forwarded_host="evil.example", client_host="203.0.113.10")

    assert _public_capture_host(request) == "cyber-vpn.net"


def test_public_capture_accepts_forwarded_host_from_trusted_proxy(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "environment", "production")
    monkeypatch.setattr(settings, "trusted_proxy_ips", ["10.0.0.0/8"])

    request = _public_request(host="internal-gateway", forwarded_host="cyber-vpn.net", client_host="10.0.0.5")

    assert _public_capture_host(request) == "cyber-vpn.net"
