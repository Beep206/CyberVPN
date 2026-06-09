from starlette.requests import Request

from src.presentation.dependencies.client_ip import resolve_client_ip


def _request(*, client_host: str | None = "198.51.100.20", headers: dict[str, str] | None = None) -> Request:
    raw_headers = [(name.lower().encode("latin-1"), value.encode("latin-1")) for name, value in (headers or {}).items()]
    scope = {
        "type": "http",
        "method": "GET",
        "path": "/api/v1/auth/login",
        "headers": raw_headers,
        "scheme": "https",
        "server": ("testserver", 443),
    }
    if client_host is not None:
        scope["client"] = (client_host, 52344)
    return Request(scope)


def test_direct_spoofed_forwarded_for_is_ignored() -> None:
    request = _request(headers={"X-Forwarded-For": "203.0.113.10"})

    result = resolve_client_ip(
        request,
        trust_proxy_headers=False,
        trusted_proxy_ips=["198.51.100.1"],
    )

    assert result.ip == "198.51.100.20"
    assert result.ip_source == "direct"
    assert result.proxy_peer == "198.51.100.20"


def test_untrusted_peer_forwarded_for_is_ignored_even_when_proxy_headers_enabled() -> None:
    request = _request(headers={"X-Forwarded-For": "203.0.113.10"})

    result = resolve_client_ip(
        request,
        trust_proxy_headers=True,
        trusted_proxy_ips=["10.0.0.10"],
    )

    assert result.ip == "198.51.100.20"
    assert result.ip_source == "direct"
    assert result.proxy_peer == "198.51.100.20"


def test_trusted_proxy_x_real_ip_is_accepted() -> None:
    request = _request(
        client_host="10.0.0.10",
        headers={"X-Real-IP": "203.0.113.10"},
    )

    result = resolve_client_ip(
        request,
        trust_proxy_headers=True,
        trusted_proxy_ips=["10.0.0.10"],
    )

    assert result.ip == "203.0.113.10"
    assert result.ip_source == "x_real_ip"
    assert result.proxy_peer == "10.0.0.10"
    assert request.state.client_ip_result == result
    assert request.state.client_ip == "203.0.113.10"
    assert request.state.client_ip_source == "x_real_ip"
    assert request.state.proxy_peer == "10.0.0.10"


def test_trusted_proxy_x_forwarded_for_first_hop_is_accepted() -> None:
    request = _request(
        client_host="10.0.0.10",
        headers={"X-Forwarded-For": "203.0.113.11, 10.0.0.20"},
    )

    result = resolve_client_ip(
        request,
        trust_proxy_headers=True,
        trusted_proxy_ips=["10.0.0.10"],
    )

    assert result.ip == "203.0.113.11"
    assert result.ip_source == "x_forwarded_for"
    assert result.proxy_peer == "10.0.0.10"


def test_trusted_proxy_x_real_ip_takes_precedence_over_x_forwarded_for() -> None:
    request = _request(
        client_host="10.0.0.10",
        headers={"X-Real-IP": "203.0.113.20", "X-Forwarded-For": "203.0.113.21, 10.0.0.20"},
    )

    result = resolve_client_ip(
        request,
        trust_proxy_headers=True,
        trusted_proxy_ips=["10.0.0.10"],
    )

    assert result.ip == "203.0.113.20"
    assert result.ip_source == "x_real_ip"
    assert result.proxy_peer == "10.0.0.10"


def test_trusted_proxy_cidr_is_accepted() -> None:
    request = _request(
        client_host="10.0.0.25",
        headers={"X-Forwarded-For": "203.0.113.12"},
    )

    result = resolve_client_ip(
        request,
        trust_proxy_headers=True,
        trusted_proxy_ips=["10.0.0.0/24"],
    )

    assert result.ip == "203.0.113.12"
    assert result.ip_source == "x_forwarded_for"
    assert result.proxy_peer == "10.0.0.25"


def test_empty_trusted_proxy_config_does_not_trust_non_loopback_peer() -> None:
    request = _request(headers={"X-Forwarded-For": "203.0.113.13"})

    result = resolve_client_ip(
        request,
        trust_proxy_headers=True,
        trusted_proxy_ips=[],
    )

    assert result.ip == "198.51.100.20"
    assert result.ip_source == "direct"
    assert result.proxy_peer == "198.51.100.20"


def test_empty_trusted_proxy_config_accepts_loopback_peer() -> None:
    request = _request(
        client_host="127.0.0.1",
        headers={"X-Forwarded-For": "203.0.113.14"},
    )

    result = resolve_client_ip(
        request,
        trust_proxy_headers=True,
        trusted_proxy_ips=[],
    )

    assert result.ip == "203.0.113.14"
    assert result.ip_source == "x_forwarded_for"
    assert result.proxy_peer == "127.0.0.1"


def test_malformed_forwarded_header_falls_back_to_direct_peer() -> None:
    request = _request(
        client_host="10.0.0.10",
        headers={"X-Forwarded-For": "not-an-ip"},
    )

    result = resolve_client_ip(
        request,
        trust_proxy_headers=True,
        trusted_proxy_ips=["10.0.0.10"],
    )

    assert result.ip == "10.0.0.10"
    assert result.ip_source == "direct"
    assert result.proxy_peer == "10.0.0.10"


def test_missing_request_client_returns_unknown_without_trusting_headers() -> None:
    request = _request(client_host=None, headers={"X-Forwarded-For": "203.0.113.15"})

    result = resolve_client_ip(
        request,
        trust_proxy_headers=True,
        trusted_proxy_ips=["10.0.0.10"],
    )

    assert result.ip == "unknown"
    assert result.ip_source == "unknown"
    assert result.proxy_peer is None
