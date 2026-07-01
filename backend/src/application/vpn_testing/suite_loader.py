"""Load bundled VPN Tester suite and route registry specifications."""

from __future__ import annotations

import json
from importlib.resources import files
from typing import Any

SUITE_PACKAGE = "src.application.vpn_testing.suites"
REGISTRY_PACKAGE = "src.application.vpn_testing.route_registry"
DEFAULT_SUITE_FILES = (
    "premium_smart_ru_v1.yaml",
    "all_tariffs_contract_v1.yaml",
    "default_subscription_smoke_v1.yaml",
)
DEFAULT_ROUTE_REGISTRY_FILES = ("premium_smart_ru_v1.yaml",)


def _load_json_resource(package: str, file_name: str) -> dict[str, Any]:
    raw = files(package).joinpath(file_name).read_text(encoding="utf-8")
    parsed = json.loads(raw)
    if not isinstance(parsed, dict):
        raise ValueError(f"{package}:{file_name} must contain a JSON object")
    return parsed


def load_default_suites() -> list[dict[str, Any]]:
    return [_load_json_resource(SUITE_PACKAGE, file_name) for file_name in DEFAULT_SUITE_FILES]


def load_default_route_registries() -> list[dict[str, Any]]:
    return [_load_json_resource(REGISTRY_PACKAGE, file_name) for file_name in DEFAULT_ROUTE_REGISTRY_FILES]
