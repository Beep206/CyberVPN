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
CANARY_OUTPUT_PATH = REPO_ROOT / (
    "scripts/remnawave/templates/"
    "cybervpn-premium-smart-ru-incy-xray-failover-canary.json"
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
    policy: dict[str, Any], automatic_destinations: dict[str, dict[str, str]]
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
                else automatic_destinations[action]
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
    for region, expected_order in (
        ("eu", ("de", "nl")),
        ("ru", ("moscow", "spb")),
    ):
        group = transport_policy.get(region)
        if not isinstance(group, dict):
            raise RuntimeError(
                f"Compiled Xray client policy lacks {region} transport group"
            )
        if (group.get("primary"), group.get("fallback")) != expected_order:
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


def _failover_balancer(
    *, tag: str, selector: str, fallback_tag: str, strategy: str
) -> dict[str, object]:
    strategy_config: dict[str, object] = {"type": strategy}
    if strategy == "leastLoad":
        strategy_config["settings"] = {"expected": 1}
    return {
        "tag": tag,
        "selector": [selector],
        "strategy": strategy_config,
        "fallbackTag": fallback_tag,
    }


def _loopback_outbound(tag: str, inbound_tag: str) -> dict[str, object]:
    return {
        "tag": tag,
        "protocol": "loopback",
        "settings": {"inboundTag": inbound_tag},
    }


def _validate_failover_selectors(
    selectors: tuple[str, ...], outbound_tags: tuple[str, ...]
) -> None:
    for selector in selectors:
        matches = [tag for tag in outbound_tags if tag.startswith(selector)]
        if matches != [selector]:
            raise RuntimeError(
                f"Xray failover selector {selector!r} must match exactly one outbound"
            )


def build_template(
    artifact_dir: Path = POLICY_ARTIFACT_DIR,
    *,
    automatic_failover: bool = True,
    canary: bool = False,
) -> dict[str, object]:
    if canary and not automatic_failover:
        raise RuntimeError("The failover canary requires automatic failover")
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
    eu_fallback_tag = _automatic_outbound_tag(eu_transport, "fallback")
    ru_primary_tag = _automatic_outbound_tag(ru_transport, "primary")
    ru_fallback_tag = _automatic_outbound_tag(ru_transport, "fallback")
    failover_selectors = (
        eu_primary_tag,
        eu_fallback_tag,
        ru_primary_tag,
        ru_fallback_tag,
    )
    injected_outbound_tags = (
        "eu-de",
        "eu-de-2",
        "eu-nl",
        "eu-nl-2",
        "ru-msk",
        "ru-msk-2",
        "ru-spb",
        "ru-spb-2",
    )
    _validate_failover_selectors(failover_selectors, injected_outbound_tags)
    automatic_destinations = {
        "eu": {"balancerTag": "eu-primary"}
        if automatic_failover
        else {"outboundTag": eu_primary_tag},
        "ru": {"balancerTag": "ru-primary"}
        if automatic_failover
        else {"outboundTag": ru_primary_tag},
    }
    renderer_deviations = (
        [
            {
                "id": (
                    "xray-canary-single-observatory-shared-ru-safe-probe"
                    if canary
                    else "xray-stable-single-observatory-shared-ru-safe-probe"
                ),
                "reason": "Xray 26.6.27 must use one deterministic observatory feature for all failover balancers",
                "effect": "All four transports use the shared RU-accessible probe for liveness; destination routing remains policy-driven and is validated separately",
                "probeUrl": shared_probe_url,
            }
        ]
        if automatic_failover
        else [
            {
                "id": "xray-single-observatory-shared-ru-safe-probe",
                "reason": "Xray 26.6.27 observatory caused user-traffic stalls with XHTTP",
                "effect": "INCY uses deterministic XHTTP primaries; fallback transports remain manual",
                "probeUrl": shared_probe_url,
            }
        ]
    )
    outbounds: list[dict[str, object]] = [
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
    ]
    routing_rules: list[dict[str, object]] = []
    routing: dict[str, object] = {
        "domainMatcher": "hybrid",
        "domainStrategy": "IPIfNonMatch",
    }
    if automatic_failover:
        outbounds.extend(
            [
                _loopback_outbound("eu-fallback-loop", "eu-fallback-in"),
                _loopback_outbound("ru-fallback-loop", "ru-fallback-in"),
            ]
        )
        routing["balancers"] = [
            _failover_balancer(
                tag="eu-primary",
                selector=eu_primary_tag,
                fallback_tag="eu-fallback-loop",
                strategy="leastPing",
            ),
            _failover_balancer(
                tag="eu-fallback",
                selector=eu_fallback_tag,
                fallback_tag="block",
                strategy="leastPing",
            ),
            _failover_balancer(
                tag="ru-primary",
                selector=ru_primary_tag,
                fallback_tag="ru-fallback-loop",
                strategy="leastPing",
            ),
            _failover_balancer(
                tag="ru-fallback",
                selector=ru_fallback_tag,
                fallback_tag="block",
                strategy="leastPing",
            ),
        ]
        routing_rules.extend(
            [
                {
                    "type": "field",
                    "ruleTag": "route_eu_failover_loop",
                    "inboundTag": ["eu-fallback-in"],
                    "network": "tcp,udp",
                    "balancerTag": "eu-fallback",
                },
                {
                    "type": "field",
                    "ruleTag": "route_ru_failover_loop",
                    "inboundTag": ["ru-fallback-in"],
                    "network": "tcp,udp",
                    "balancerTag": "ru-fallback",
                },
            ]
        )
    routing_rules.extend(_xray_rules(policy, automatic_destinations))
    routing["rules"] = routing_rules
    template: dict[str, object] = {
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
                "rendererDeviations": renderer_deviations,
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
        "outbounds": outbounds,
        "routing": routing,
        "stats": {},
    }
    if automatic_failover:
        route_policy = template["remnawave"]
        assert isinstance(route_policy, dict)
        route_policy = route_policy["routePolicy"]
        assert isinstance(route_policy, dict)
        route_policy["rendererMode"] = (
            "automatic-failover-canary" if canary else "automatic-failover"
        )
        template["observatory"] = {
            "subjectSelector": [
                eu_primary_tag,
                eu_fallback_tag,
                ru_primary_tag,
                ru_fallback_tag,
            ],
            "probeUrl": shared_probe_url,
            "probeInterval": "10s",
            "enableConcurrency": True,
        }
    return template


def main() -> int:
    template = build_template()
    OUTPUT_PATH.write_bytes(
        (json.dumps(template, ensure_ascii=False, indent=2) + "\n").encode()
    )
    routing = template["routing"]
    assert isinstance(routing, dict)
    rules = routing["rules"]
    assert isinstance(rules, list)
    canary_template = build_template(canary=True)
    CANARY_OUTPUT_PATH.write_bytes(
        (json.dumps(canary_template, ensure_ascii=False, indent=2) + "\n").encode()
    )
    canary_routing = canary_template["routing"]
    assert isinstance(canary_routing, dict)
    canary_rules = canary_routing["rules"]
    assert isinstance(canary_rules, list)
    print(
        f"generated={OUTPUT_PATH} routing_rules={len(rules)} "
        f"canary={CANARY_OUTPUT_PATH} canary_routing_rules={len(canary_rules)}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
