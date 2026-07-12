"""Generate the INCY/HAPP full Xray template from compiled Premium Smart RU policy."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
OUTPUT_PATH = (
    REPO_ROOT / "scripts/remnawave/templates/cybervpn-premium-smart-ru-incy-xray.json"
)
POLICY_ARTIFACT_DIR = REPO_ROOT / "scripts/remnawave/generated/premium_smart_ru"
POLICY_PATH = REPO_ROOT / "scripts/remnawave/policies/premium_smart_ru.yaml"
XRAY_CLIENT_ARTIFACT = "xray-client.json"


def _sha256(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def _load_policy_artifact(
    artifact_dir: Path = POLICY_ARTIFACT_DIR,
) -> dict[str, Any]:
    manifest_path = artifact_dir / "manifest.json"
    artifact_path = artifact_dir / XRAY_CLIENT_ARTIFACT
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        content = artifact_path.read_bytes()
        artifact = json.loads(content)
        policy_content = POLICY_PATH.read_bytes()
    except (OSError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"Cannot load compiled Xray client policy: {exc}") from exc

    metadata = manifest.get("artifacts", {}).get(XRAY_CLIENT_ARTIFACT)
    if not isinstance(metadata, dict):
        raise RuntimeError(
            "Compiler manifest does not declare the Xray client artifact"
        )
    if metadata.get("bytes") != len(content) or metadata.get("sha256") != _sha256(
        content
    ):
        raise RuntimeError("Compiled Xray client policy checksum or size mismatch")
    if manifest.get("source", {}).get("sha256") != _sha256(policy_content):
        raise RuntimeError("Compiled Xray client policy is stale for canonical policy")
    coverage = manifest.get("rendererCoverage", {}).get("xrayClient")
    if not isinstance(coverage, dict) or coverage.get("status") != "rendered":
        raise RuntimeError("Compiler manifest does not mark Xray client as rendered")
    if coverage.get("artifact") != XRAY_CLIENT_ARTIFACT:
        raise RuntimeError("Compiler manifest points Xray client to another artifact")
    if (
        artifact.get("schemaVersion") != 1
        or artifact.get("product") != "premium_smart_ru"
        or artifact.get("consumer") != "incy-happ-xray"
    ):
        raise RuntimeError("Compiled Xray client policy has an unsupported contract")
    if not isinstance(artifact.get("rules"), list) or not artifact["rules"]:
        raise RuntimeError("Compiled Xray client policy contains no rules")
    return artifact


def _inject_group(pattern: str, tag_prefix: str) -> dict[str, object]:
    return {
        "selector": {"type": "tagRegex", "pattern": pattern},
        "selectFrom": "HIDDEN",
        "tagPrefix": tag_prefix,
    }


def _xray_rules(
    policy: dict[str, Any], automatic_outbound_tags: dict[str, str]
) -> list[dict[str, object]]:
    target = {"direct": "direct", "block": "block"}
    rules: list[dict[str, object]] = []
    for typed_rule in policy["rules"]:
        action = typed_rule.get("action")
        matches = typed_rule.get("matches")
        if action not in {"direct", "block", "eu", "ru"}:
            raise RuntimeError("Compiled Xray client policy contains an invalid action")
        if not isinstance(matches, list) or not matches:
            raise RuntimeError(
                f"Compiled Xray client policy rule {typed_rule.get('id')} has no matcher"
            )
        for match in matches:
            if not isinstance(match, dict) or not match:
                raise RuntimeError(
                    "Compiled Xray client policy contains an empty matcher"
                )
            destination = (
                {"outboundTag": target[action]}
                if action in target
                else {"outboundTag": automatic_outbound_tags[action]}
            )
            rules.append(
                {
                    "type": "field",
                    "ruleTag": str(typed_rule["id"]),
                    **match,
                    **destination,
                }
            )
    return rules


def _transport_metadata(policy: dict[str, Any]) -> dict[str, object]:
    transport_policy = policy.get("transportPolicy")
    if not isinstance(transport_policy, dict) or set(transport_policy) != {"eu", "ru"}:
        raise RuntimeError(
            "Compiled Xray client policy lacks regional transport policy"
        )
    for region, expected_locations in (
        ("eu", {"de", "nl"}),
        ("ru", {"moscow", "spb"}),
    ):
        group = transport_policy.get(region)
        if not isinstance(group, dict):
            raise RuntimeError(
                f"Compiled Xray client policy lacks {region} transport group"
            )
        if {group.get("primary"), group.get("fallback")} != expected_locations:
            raise RuntimeError(
                f"Compiled Xray client policy has invalid {region} order"
            )
        for role in ("primary", "fallback"):
            transport = group.get(f"{role}Transport")
            location = group.get(role)
            members = group.get("members")
            if (
                transport not in {"raw", "xhttp"}
                or not isinstance(members, dict)
                or transport not in members.get(location, [])
            ):
                raise RuntimeError(
                    f"Compiled Xray client policy has invalid {region} {role} transport"
                )
        degraded = group.get("degraded")
        if (
            not isinstance(degraded, dict)
            or degraded.get("crossRegionFallback") is not False
        ):
            raise RuntimeError(
                f"Compiled Xray client policy permits {region} cross-region fallback"
            )
    eu_probe = transport_policy["eu"].get("probe", {}).get("url")
    ru_probe = transport_policy["ru"].get("probe", {}).get("url")
    if not eu_probe or not ru_probe or eu_probe == ru_probe:
        raise RuntimeError("EU and RU transport health probes must be independent")
    return transport_policy


def _automatic_outbound_tag(group: dict[str, object], role: str) -> str:
    location = str(group[role])
    transport = str(group[f"{role}Transport"])
    prefix = {
        "de": "eu-de",
        "nl": "eu-nl",
        "moscow": "ru-msk",
        "spb": "ru-spb",
    }[location]
    return prefix if transport == "raw" else f"{prefix}-2"


def build_template(
    artifact_dir: Path = POLICY_ARTIFACT_DIR,
) -> dict[str, object]:
    policy = _load_policy_artifact(artifact_dir)
    transport_policy = _transport_metadata(policy)
    eu_transport = transport_policy["eu"]
    ru_transport = transport_policy["ru"]
    assert isinstance(eu_transport, dict)
    assert isinstance(ru_transport, dict)
    ru_probe = ru_transport["probe"]
    assert isinstance(ru_probe, dict)
    shared_probe_url = str(ru_probe["url"])
    eu_primary_tag = _automatic_outbound_tag(eu_transport, "primary")
    ru_primary_tag = _automatic_outbound_tag(ru_transport, "primary")
    return {
        "remnawave": {
            "injectHosts": [
                _inject_group(r"^PREMIUM_SMART_RU_INCY_DE_", "eu-de"),
                _inject_group(r"^PREMIUM_SMART_RU_INCY_NL_", "eu-nl"),
                _inject_group(r"^PREMIUM_SMART_RU_INCY_MSK_", "ru-msk"),
                _inject_group(r"^PREMIUM_SMART_RU_INCY_SPB_", "ru-spb"),
            ],
            "routePolicy": {
                "schemaVersion": policy["schemaVersion"],
                "product": policy["product"],
                "ruleOrder": policy["ruleOrder"],
                "regionalHealth": transport_policy,
                "rendererDeviations": [
                    {
                        "id": "xray-single-observatory-shared-ru-safe-probe",
                        "reason": "Xray 26.6.27 observatory caused user-traffic stalls with XHTTP",
                        "effect": "INCY uses deterministic XHTTP primaries; fallback transports remain manual",
                        "probeUrl": shared_probe_url,
                    }
                ],
                "providerSources": [
                    provider
                    for rule in policy["rules"]
                    for provider in rule.get("providers", [])
                ],
            },
        },
        "log": {"loglevel": "warning"},
        "dns": {
            "hosts": {
                "cloudflare-dns.com": ["1.1.1.1", "1.0.0.1"],
                "dns.google": ["8.8.8.8", "8.8.4.4"],
            },
            "servers": [
                "https://cloudflare-dns.com/dns-query",
                "https://dns.google/dns-query",
            ],
            "queryStrategy": "UseIPv4",
        },
        "inbounds": [
            {
                "tag": "socks",
                "port": 10808,
                "listen": "127.0.0.1",
                "protocol": "socks",
                "settings": {"auth": "noauth", "udp": True},
                "sniffing": {
                    "enabled": True,
                    "routeOnly": True,
                    "destOverride": ["http", "tls", "quic", "fakedns"],
                },
            },
            {
                "tag": "http",
                "port": 10809,
                "listen": "127.0.0.1",
                "protocol": "http",
                "settings": {"allowTransparent": False},
                "sniffing": {
                    "enabled": True,
                    "routeOnly": True,
                    "destOverride": ["http", "tls", "quic", "fakedns"],
                },
            },
        ],
        "outbounds": [
            {
                "tag": "direct",
                "protocol": "freedom",
                "settings": {"domainStrategy": "UseIP"},
            },
            {
                "tag": "block",
                "protocol": "blackhole",
                "settings": {"response": {"type": "none"}},
            },
        ],
        "routing": {
            "domainMatcher": "hybrid",
            "domainStrategy": "IPIfNonMatch",
            "rules": _xray_rules(
                policy,
                {"eu": eu_primary_tag, "ru": ru_primary_tag},
            ),
        },
        "stats": {},
    }


def main() -> int:
    template = build_template()
    OUTPUT_PATH.write_text(
        json.dumps(template, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    routing = template["routing"]
    assert isinstance(routing, dict)
    rules = routing["rules"]
    assert isinstance(rules, list)
    print(f"generated={OUTPUT_PATH} routing_rules={len(rules)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
