# ruff: noqa: S101

from __future__ import annotations

import importlib.util
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
VALIDATOR_PATH = REPO_ROOT / "scripts" / "validate_s1_edge_waf_baseline.py"


def _load_validator():
    spec = importlib.util.spec_from_file_location("validate_s1_edge_waf_baseline", VALIDATOR_PATH)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_stage1_edge_waf_baseline_validates() -> None:
    validator = _load_validator()
    errors = validator.validate_baseline(validator.load_baseline())
    assert errors == []


def test_stage1_edge_waf_baseline_has_webhook_no_challenge_exceptions() -> None:
    validator = _load_validator()
    data = validator.load_baseline()
    exception_ids = {item["id"] for item in data["exceptions"]}

    assert "s1-no-interactive-challenge-payment-webhooks" in exception_ids
    assert "s1-no-interactive-challenge-telegram-webhook" in exception_ids
    assert "s1-no-interactive-challenge-oauth-callback" in exception_ids


def test_stage1_edge_waf_baseline_keeps_non_http_surfaces_off_public_edge() -> None:
    validator = _load_validator()
    data = validator.load_baseline()
    excluded_ids = {item["id"] for item in data["not_proxied_or_not_edge_protected"]}

    assert "vpn_transport_ports" in excluded_ids
    assert "remnawave_private_api" in excluded_ids
    assert "managed_postgresql" in excluded_ids
    assert "private_valkey" in excluded_ids
