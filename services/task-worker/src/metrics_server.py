"""Prometheus metrics HTTP server for exposing /metrics endpoint.

Starts a simple HTTP server that serves Prometheus metrics on a configurable port
with optional IP allowlist and BasicAuth protection.
"""

import base64
import hmac
import ipaddress
from threading import Thread

import structlog
from prometheus_client import REGISTRY, make_wsgi_app
from wsgiref.simple_server import make_server

logger = structlog.get_logger(__name__)


def _build_allowed_networks(allowed_ips: list[str]) -> list[ipaddress._BaseNetwork]:
    networks: list[ipaddress._BaseNetwork] = []
    for raw in allowed_ips:
        try:
            networks.append(ipaddress.ip_network(raw, strict=False))
        except ValueError:
            logger.warning("invalid_metrics_allowlist", entry=raw)
    return networks


def _parse_basic_auth(auth_header: str) -> tuple[str, str] | None:
    if not auth_header.startswith("Basic "):
        return None
    try:
        decoded = base64.b64decode(auth_header[6:]).decode("utf-8")
    except (ValueError, UnicodeDecodeError):
        return None
    if ":" not in decoded:
        return None
    username, password = decoded.split(":", 1)
    return username, password


def _build_metrics_app(
    *,
    protect: bool,
    allowed_networks: list[ipaddress._BaseNetwork],
    basic_auth_user: str | None,
    basic_auth_password: str | None,
):
    app = make_wsgi_app(REGISTRY)

    def metrics_app(environ, start_response):
        path = environ.get("PATH_INFO", "")
        if path and path != "/metrics":
            start_response("404 Not Found", [])
            return [b"Not Found"]

        if protect:
            if allowed_networks:
                remote = environ.get("REMOTE_ADDR")
                if not remote:
                    start_response("403 Forbidden", [])
                    return [b"Forbidden"]
                try:
                    ip = ipaddress.ip_address(remote)
                except ValueError:
                    start_response("403 Forbidden", [])
                    return [b"Forbidden"]
                if not any(ip in network for network in allowed_networks):
                    start_response("403 Forbidden", [])
                    return [b"Forbidden"]

            if basic_auth_user and basic_auth_password:
                auth_header = environ.get("HTTP_AUTHORIZATION", "")
                creds = _parse_basic_auth(auth_header)
                if (
                    creds is None
                    or not hmac.compare_digest(creds[0], basic_auth_user)
                    or not hmac.compare_digest(creds[1], basic_auth_password)
                ):
                    start_response(
                        "401 Unauthorized",
                        [("WWW-Authenticate", 'Basic realm="metrics"')],
                    )
                    return [b"Unauthorized"]

        return app(environ, start_response)

    return metrics_app


def start_metrics_server(
    port: int = 9091,
    *,
    protect: bool = True,
    allowed_ips: list[str] | None = None,
    basic_auth_user: str | None = None,
    basic_auth_password: str | None = None,
) -> None:
    """Start Prometheus metrics HTTP server.

    Args:
        port: Port number to listen on (default: 9091)
        protect: Enable IP allowlist and/or BasicAuth
        allowed_ips: List of IPs/CIDRs allowed to access metrics
        basic_auth_user: BasicAuth username (optional)
        basic_auth_password: BasicAuth password (optional)

    Raises:
        OSError: If the port is already in use
    """
    try:
        allowed_networks = _build_allowed_networks(allowed_ips or [])
        app = _build_metrics_app(
            protect=protect,
            allowed_networks=allowed_networks,
            basic_auth_user=basic_auth_user,
            basic_auth_password=basic_auth_password,
        )
        server = make_server("0.0.0.0", port, app=app)
        logger.info(
            "metrics_server_started",
            port=port,
            endpoint="/metrics",
            protect=protect,
        )
        thread = Thread(target=server.serve_forever, daemon=True)
        thread.start()
    except OSError as e:
        if "Address already in use" in str(e):
            logger.warning(
                "metrics_server_already_running",
                port=port,
                message="Metrics server port already in use, skipping startup",
            )
        else:
            logger.exception("metrics_server_start_failed", port=port, error=str(e))
            raise
