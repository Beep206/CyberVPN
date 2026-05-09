#!/usr/bin/env python3
"""Validate the Stage 1 edge WAF/rate-limit baseline."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
BASELINE_PATH = REPO_ROOT / "infra" / "edge" / "stage1-cloudflare-waf-baseline.json"

REQUIRED_ZONES = {"cyber-vpn.net", "cyber-vpn.org"}
REQUIRED_SURFACES = {
    "public_web",
    "public_mirror_redirect",
    "api",
    "admin",
    "admin_mirror_redirect",
    "telegram_webhook",
    "payment_webhooks",
    "oauth_callbacks",
}
REQUIRED_RATE_LIMITS = {
    "s1-auth-sensitive",
    "s1-admin-sensitive",
    "s1-trial-and-checkout",
    "s1-payment-webhooks-conservative",
    "s1-telegram-webhook-conservative",
    "s1-support-and-privacy-requests",
    "s1-public-web-abuse",
}
REQUIRED_EXCEPTIONS = {
    "s1-no-interactive-challenge-payment-webhooks",
    "s1-no-interactive-challenge-telegram-webhook",
    "s1-no-interactive-challenge-oauth-callback",
    "s1-next-static-assets",
}
REQUIRED_EVIDENCE_TERMS = {
    "DNS records",
    "TLS certificate",
    "admin.cyber-vpn.net protected",
    "WAF managed rules",
    "custom sensitive-path block",
    "rate-limit transcript",
    "payment webhook callback transcript",
    "Telegram webhook transcript",
    "Cloudflare Security Events",
}
SECRET_PATTERNS = [
    re.compile(pattern, re.IGNORECASE)
    for pattern in (
        r"api[_-]?token\s*[:=]\s*[a-z0-9_-]{16,}",
        r"secret\s*[:=]\s*[a-z0-9_-]{16,}",
        r"private[_-]?key",
        r"-----BEGIN [A-Z ]+PRIVATE KEY-----",
        r"cf-[a-z0-9]{20,}",
        r"zone[_-]?id\s*[:=]\s*[a-f0-9]{16,}",
    )
]


def load_baseline(path: Path = BASELINE_PATH) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _collect_ids(items: list[dict[str, Any]]) -> set[str]:
    return {str(item.get("id", "")) for item in items}


def _walk_values(value: Any) -> list[str]:
    if isinstance(value, dict):
        output: list[str] = []
        for key, nested in value.items():
            output.append(str(key))
            output.extend(_walk_values(nested))
        return output
    if isinstance(value, list):
        output = []
        for nested in value:
            output.extend(_walk_values(nested))
        return output
    if value is None:
        return []
    return [str(value)]


def validate_baseline(data: dict[str, Any]) -> list[str]:
    errors: list[str] = []

    if data.get("backlog_id") != "S1-INFRA-008":
        errors.append("backlog_id must be S1-INFRA-008")
    if data.get("status") != "local_baseline_only_external_enablement_required":
        errors.append("status must clearly state this is local baseline only")
    if data.get("provider") != "cloudflare_or_equivalent_edge":
        errors.append("provider must be cloudflare_or_equivalent_edge")

    zones = {zone.get("domain") for zone in data.get("zones", [])}
    if not REQUIRED_ZONES.issubset(zones):
        errors.append(f"zones must include {sorted(REQUIRED_ZONES)}")

    context = data.get("decision_context", {})
    if context.get("primary_public_domain") != "cyber-vpn.net":
        errors.append("primary_public_domain must be cyber-vpn.net")
    if context.get("public_mirror_domain") != "cyber-vpn.org":
        errors.append("public_mirror_domain must be cyber-vpn.org")
    if context.get("primary_admin_domain") != "admin.cyber-vpn.net":
        errors.append("primary_admin_domain must be admin.cyber-vpn.net")
    if context.get("admin_mirror_domain") != "admin.cyber-vpn.org":
        errors.append("admin_mirror_domain must be admin.cyber-vpn.org")
    if context.get("home_lab_allowed_for_non_critical_evidence_only") is not True:
        errors.append("home lab must be limited to non-critical evidence only")

    surfaces = data.get("surfaces", [])
    surface_ids = _collect_ids(surfaces)
    if not REQUIRED_SURFACES.issubset(surface_ids):
        errors.append(f"surfaces must include {sorted(REQUIRED_SURFACES)}")

    admin_surface = next((surface for surface in surfaces if surface.get("id") == "admin"), {})
    admin_controls = set(admin_surface.get("edge_controls", []))
    if "cloudflare_access_or_ip_allowlist_required" not in admin_controls:
        errors.append("admin surface must require Access or IP allowlist")

    not_proxied = _collect_ids(data.get("not_proxied_or_not_edge_protected", []))
    for required_id in {"vpn_transport_ports", "remnawave_private_api", "managed_postgresql", "private_valkey"}:
        if required_id not in not_proxied:
            errors.append(f"not_proxied_or_not_edge_protected must include {required_id}")

    managed_rules = data.get("managed_rules", [])
    if not managed_rules:
        errors.append("managed_rules must not be empty")
    if not any(rule.get("phase") == "http_request_firewall_managed" for rule in managed_rules):
        errors.append("managed_rules must include http_request_firewall_managed")

    custom_rules = data.get("custom_rules", [])
    if "s1-block-sensitive-and-scanner-paths" not in _collect_ids(custom_rules):
        errors.append("custom_rules must include sensitive/scanner path block")
    if "s1-admin-requires-access-or-allowlist" not in _collect_ids(custom_rules):
        errors.append("custom_rules must include admin access/allowlist guard")
    if "s1-admin-org-redirect-only" not in _collect_ids(custom_rules):
        errors.append("custom_rules must include admin .org redirect-only guard")

    rate_limits = data.get("rate_limits", [])
    rate_limit_ids = _collect_ids(rate_limits)
    if not REQUIRED_RATE_LIMITS.issubset(rate_limit_ids):
        errors.append(f"rate_limits must include {sorted(REQUIRED_RATE_LIMITS)}")
    for limit in rate_limits:
        if not limit.get("paths"):
            errors.append(f"rate limit {limit.get('id')} must define paths")
        if not isinstance(limit.get("period_seconds"), int) or limit["period_seconds"] <= 0:
            errors.append(f"rate limit {limit.get('id')} must define positive period_seconds")
        if not isinstance(limit.get("requests_per_period"), int) or limit["requests_per_period"] <= 0:
            errors.append(f"rate limit {limit.get('id')} must define positive requests_per_period")
        if "webhook" in str(limit.get("id")) and "challenge" in str(limit.get("action")).lower():
            errors.append(f"webhook rate limit {limit.get('id')} must not use challenge action")

    exceptions = _collect_ids(data.get("exceptions", []))
    if not REQUIRED_EXCEPTIONS.issubset(exceptions):
        errors.append(f"exceptions must include {sorted(REQUIRED_EXCEPTIONS)}")

    evidence = "\n".join(data.get("evidence_required_before_go_live", []))
    for term in REQUIRED_EVIDENCE_TERMS:
        if term not in evidence:
            errors.append(f"evidence_required_before_go_live must mention {term}")

    blockers = set(data.get("go_live_blockers_if_missing", []))
    for blocker in {"admin access protection", "DNS/TLS/redirect proof", "WAF/custom-rule event evidence"}:
        if blocker not in blockers:
            errors.append(f"go_live_blockers_if_missing must include {blocker}")

    for value in _walk_values(data):
        for pattern in SECRET_PATTERNS:
            if pattern.search(value):
                errors.append(f"secret-looking value found: {value[:80]}")

    return errors


def main() -> int:
    errors = validate_baseline(load_baseline())
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1
    print(f"PASS: {BASELINE_PATH.relative_to(REPO_ROOT)} is valid for S1-INFRA-008")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
