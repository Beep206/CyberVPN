"""Trusted client IP resolution for request audit and rate limiting."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from ipaddress import ip_address, ip_network
from typing import Literal

from starlette.requests import HTTPConnection

from src.config.settings import settings

ClientIpSource = Literal["direct", "x_forwarded_for", "x_real_ip", "unknown"]

LOOPBACK_TRUSTED_PROXY_IPS = ("127.0.0.1", "::1")


@dataclass(frozen=True, slots=True)
class ClientIpResult:
    ip: str
    ip_source: ClientIpSource
    proxy_peer: str | None


def resolve_client_ip(
    request: HTTPConnection,
    *,
    trust_proxy_headers: bool | None = None,
    trusted_proxy_ips: Iterable[str] | None = None,
) -> ClientIpResult:
    """Resolve the client IP without trusting spoofable proxy headers by default."""
    direct_ip = request.client.host if request.client else None
    if direct_ip is None:
        return _store_result(request, ClientIpResult(ip="unknown", ip_source="unknown", proxy_peer=None))

    trust_headers = settings.trust_proxy_headers if trust_proxy_headers is None else trust_proxy_headers
    if not trust_headers:
        return _store_result(request, ClientIpResult(ip=direct_ip, ip_source="direct", proxy_peer=direct_ip))

    trusted_entries = tuple(settings.trusted_proxy_ips if trusted_proxy_ips is None else trusted_proxy_ips)
    if not trusted_entries:
        trusted_entries = LOOPBACK_TRUSTED_PROXY_IPS

    if not is_trusted_proxy_peer(direct_ip, trusted_entries):
        return _store_result(request, ClientIpResult(ip=direct_ip, ip_source="direct", proxy_peer=direct_ip))

    real_ip = _validated_header_ip(request.headers.get("x-real-ip"))
    if real_ip is not None:
        return _store_result(request, ClientIpResult(ip=real_ip, ip_source="x_real_ip", proxy_peer=direct_ip))

    forwarded_ip = _first_header_ip(request.headers.get("x-forwarded-for"))
    if forwarded_ip is not None:
        return _store_result(
            request, ClientIpResult(ip=forwarded_ip, ip_source="x_forwarded_for", proxy_peer=direct_ip)
        )

    return _store_result(request, ClientIpResult(ip=direct_ip, ip_source="direct", proxy_peer=direct_ip))


def _store_result(request: HTTPConnection, result: ClientIpResult) -> ClientIpResult:
    request.state.client_ip_result = result
    request.state.client_ip = result.ip
    request.state.client_ip_source = result.ip_source
    request.state.proxy_peer = result.proxy_peer
    return result


def is_trusted_proxy_peer(peer_ip: str | None, trusted_proxy_ips: Iterable[str]) -> bool:
    if peer_ip is None:
        return False

    try:
        peer = ip_address(peer_ip)
    except ValueError:
        return False

    for trusted_proxy in trusted_proxy_ips:
        trusted_proxy = trusted_proxy.strip()
        if not trusted_proxy:
            continue
        try:
            trusted_network = ip_network(trusted_proxy, strict=False)
        except ValueError:
            continue
        if peer in trusted_network:
            return True

    return False


def _first_header_ip(header_value: str | None) -> str | None:
    if not header_value:
        return None
    return _validated_header_ip(header_value.split(",", 1)[0])


def _validated_header_ip(header_value: str | None) -> str | None:
    if not header_value:
        return None

    candidate = header_value.strip(" \t\"'")
    if not candidate:
        return None

    try:
        return str(ip_address(candidate))
    except ValueError:
        return None
