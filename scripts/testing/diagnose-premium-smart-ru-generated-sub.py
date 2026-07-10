#!/usr/bin/env python3
from __future__ import annotations

import json
import re
import sys
from collections import Counter
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError:  # pragma: no cover - covered only in stripped tooling envs
    yaml = None

INPUT_ERROR_EXIT = 2
RAW_COUNT_EXIT = 10
XHTTP_COUNT_EXIT = 11
RAW_INVALID_EXIT = 12
XHTTP_INVALID_EXIT = 13
RAW_LOCATION_MATRIX_EXIT = 14
XHTTP_LOCATION_MATRIX_EXIT = 15

REQUIRED_SERVERS = frozenset(
    {
        "de-3.cyber-vpn.org",
        "nl-4.cyber-vpn.org",
        "ru-msk-3.cyber-vpn.org",
        "ru-spb-3.cyber-vpn.org",
    }
)

SAFE_PROXY_FIELDS = {
    "name",
    "server",
    "port",
    "network",
    "tls",
    "flow",
    "has_servername",
    "has_public_key",
    "has_short_id_field",
}
URL_RE = re.compile(r"(?i)(?:[a-z][a-z0-9+.-]*://|www\.)")
UUID_RE = re.compile(
    r"\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b|"
    r"\b[0-9a-f]{32}\b",
    re.IGNORECASE,
)
SHORT_ID_RE = re.compile(r"\b[0-9a-f]{8,16}\b", re.IGNORECASE)
LONG_TOKEN_RE = re.compile(r"^[A-Za-z0-9_-]{24,}$")
LONG_TOKEN_SUBSTRING_RE = re.compile(r"[A-Za-z0-9_-]{24,}")
HOST_RE = re.compile(r"^[A-Za-z0-9_.:-]+$")


def _error(message: str) -> int:
    print(f"error: {message}", file=sys.stderr)
    return INPUT_ERROR_EXIT


def _must_redact(value: str) -> bool:
    return bool(
        URL_RE.search(value)
        or UUID_RE.search(value)
        or SHORT_ID_RE.search(value)
        or LONG_TOKEN_RE.fullmatch(value)
        or LONG_TOKEN_SUBSTRING_RE.search(value)
    )


def _safe_text(value: Any, *, fallback: str | None = None) -> str | None:
    if value is None:
        return fallback
    text = str(value).strip()
    if not text:
        return fallback
    if _must_redact(text):
        return "[redacted]"
    return text


def _safe_server(value: Any) -> str | None:
    text = _safe_text(value)
    if text is None or text == "[redacted]":
        return text
    if not HOST_RE.fullmatch(text):
        return "[redacted]"
    return text


def _safe_port(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _safe_bool(value: Any) -> bool | None:
    return value if isinstance(value, bool) else None


def _lower_text(value: Any, *, default: str = "") -> str:
    text = str(value if value is not None else default).strip().lower()
    return text or default


def _proxy_name(item: Mapping[str, Any], index: int) -> str:
    name = _safe_text(item.get("name"))
    if name is None:
        return f"<unnamed:{index}>"
    if name == "[redacted]":
        return f"<redacted:{index}>"
    return name


def _reality_opts(item: Mapping[str, Any]) -> Mapping[str, Any]:
    reality = item.get("reality-opts")
    return reality if isinstance(reality, Mapping) else {}


def _safe_proxy_fields(item: Mapping[str, Any], index: int) -> dict[str, Any]:
    reality = _reality_opts(item)
    return {
        "name": _proxy_name(item, index),
        "server": _safe_server(item.get("server")),
        "port": _safe_port(item.get("port")),
        "network": _safe_text(_lower_text(item.get("network"), default="tcp")),
        "tls": _safe_bool(item.get("tls")),
        "flow": _safe_text(item.get("flow")),
        "has_servername": bool(item.get("servername") or item.get("sni")),
        "has_public_key": bool(reality.get("public-key")),
        "has_short_id_field": "short-id" in reality,
    }


def _is_valid_raw_tcp(item: Mapping[str, Any], safe: Mapping[str, Any]) -> bool:
    return (
        _has_usable_server(safe)
        and safe["port"] == 443
        and item.get("tls") is True
        and item.get("flow") == "xtls-rprx-vision"
        and safe["has_servername"] is True
        and safe["has_public_key"] is True
        and safe["has_short_id_field"] is True
    )


def _has_usable_server(safe: Mapping[str, Any]) -> bool:
    server = safe.get("server")
    return isinstance(server, str) and bool(server.strip()) and server != "[redacted]"


def _is_valid_xhttp(item: Mapping[str, Any], safe: Mapping[str, Any]) -> bool:
    return (
        _has_usable_server(safe)
        and safe["port"] == 8443
        and item.get("tls") is True
        and safe["has_servername"] is True
        and safe["has_public_key"] is True
        and safe["has_short_id_field"] is True
    )


def _print_json(value: Mapping[str, Any]) -> None:
    print(json.dumps(value, ensure_ascii=False, sort_keys=True))


def _load_config(path: Path) -> Mapping[str, Any] | int:
    if yaml is None:
        return _error("PyYAML is required")
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return _error("cannot read YAML file")
    try:
        config = yaml.safe_load(text)
    except yaml.YAMLError:
        return _error("malformed YAML")
    if not isinstance(config, Mapping):
        return _error("generated config root is not an object")
    return config


def diagnose(path: Path) -> int:
    config = _load_config(path)
    if isinstance(config, int):
        return config

    proxies = config.get("proxies") or []
    if not isinstance(proxies, list):
        return _error("generated config proxies is not a list")

    raw_count = 0
    xhttp_count = 0
    invalid_raw: list[str] = []
    invalid_xhttp: list[str] = []
    raw_server_counts: Counter[str] = Counter()
    xhttp_server_counts: Counter[str] = Counter()

    for index, item in enumerate(proxies):
        if not isinstance(item, Mapping):
            return _error("generated config proxy entry is not an object")
        if _lower_text(item.get("type")) != "vless":
            continue

        safe = _safe_proxy_fields(item, index)
        if set(safe) != SAFE_PROXY_FIELDS:
            return _error("internal safe proxy field contract mismatch")
        _print_json(safe)

        network = _lower_text(item.get("network"), default="tcp")
        name = str(safe["name"])
        if network in {"", "tcp", "raw"}:
            raw_count += 1
            if not _is_valid_raw_tcp(item, safe):
                invalid_raw.append(name)
            else:
                raw_server_counts[str(safe["server"]).lower()] += 1
        elif network == "xhttp":
            xhttp_count += 1
            if not _is_valid_xhttp(item, safe):
                invalid_xhttp.append(name)
            else:
                xhttp_server_counts[str(safe["server"]).lower()] += 1

    expected_server_counts = Counter({server: 1 for server in REQUIRED_SERVERS})
    raw_location_matrix_valid = raw_server_counts == expected_server_counts
    xhttp_location_matrix_valid = xhttp_server_counts == expected_server_counts

    summary = {
        "vless_reality_raw_tcp_count": raw_count,
        "vless_reality_xhttp_count": xhttp_count,
        "invalid_raw_tcp": invalid_raw,
        "invalid_xhttp": invalid_xhttp,
        "raw_location_matrix_valid": raw_location_matrix_valid,
        "xhttp_location_matrix_valid": xhttp_location_matrix_valid,
    }
    _print_json(summary)

    if raw_count != 4:
        return RAW_COUNT_EXIT
    if xhttp_count != 4:
        return XHTTP_COUNT_EXIT
    if invalid_raw:
        return RAW_INVALID_EXIT
    if invalid_xhttp:
        return XHTTP_INVALID_EXIT
    if not raw_location_matrix_valid:
        return RAW_LOCATION_MATRIX_EXIT
    if not xhttp_location_matrix_valid:
        return XHTTP_LOCATION_MATRIX_EXIT
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if len(args) != 1:
        print(
            "usage: diagnose-premium-smart-ru-generated-sub.py <generated.yaml>",
            file=sys.stderr,
        )
        return INPUT_ERROR_EXIT
    return diagnose(Path(args[0]))


if __name__ == "__main__":
    raise SystemExit(main())
