from starlette.requests import Request

from src.presentation.dependencies.auth_realms import _web_realm_hint_for_host


def _request_for_host(host: str) -> Request:
    return Request(
        {
            "type": "http",
            "method": "POST",
            "path": "/api/v1/auth/login",
            "headers": [(b"host", host.encode("ascii"))],
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
