from __future__ import annotations

import base64
import hashlib
import importlib.util
import json
import sys
from pathlib import Path
from types import ModuleType

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[4]
POLICY_PATH = REPO_ROOT / "scripts" / "remnawave" / "policies" / "premium_smart_ru.yaml"
GENERATOR_PATH = REPO_ROOT / "scripts" / "remnawave" / "generate-premium-smart-ru-incy-xray.py"
OPERATOR_PATH = REPO_ROOT / "scripts" / "remnawave" / "apply-premium-smart-ru-server-routing.py"

sys.path.insert(0, str(REPO_ROOT))

from scripts.remnawave.policy_compiler.compiler import (  # noqa: E402
    MANIFEST_NAME,
    build_outputs,
    generate,
)
from scripts.remnawave.policy_compiler.loader import load_policy  # noqa: E402
from scripts.remnawave.policy_compiler.models import PolicySource  # noqa: E402
from scripts.remnawave.policy_compiler.renderers import (  # noqa: E402
    LEGACY_HEADER_NAME,
    MIHOMO_NAME,
    XRAY_CLIENT_NAME,
    XRAY_SERVER_NAME,
    _xray_domain,
    _xray_matches,
)


def _load_script(path: Path, name: str) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _decoded_outputs() -> tuple[dict[str, object], dict[str, dict[str, object]]]:
    policy, outputs = build_outputs(POLICY_PATH)
    return policy.model_dump(mode="python"), {
        name: yaml.safe_load(content) if name.endswith(".yaml") else json.loads(content)
        for name, content in outputs.items()
    }


def test_renderers_preserve_canonical_rule_and_eu_provider_order() -> None:
    policy = load_policy(POLICY_PATH)
    _policy_dump, artifacts = _decoded_outputs()
    expected_stages = [rule.stage for rule in policy.rules]
    expected_eu_sources = list(policy.source_groups.eu_exceptions)

    assert len(policy.sources) == 42
    assert sum(source.kind == "http" for source in policy.sources.values()) == 29
    assert expected_eu_sources[:14] == [
        "manual-eu-inline",
        "youtube",
        "discord-domains",
        "discord-voice",
        "cloudflare-ips",
        "telegram-domains",
        "telegram-ips",
        "additional-telegram-domains",
        "additional-telegram-ips",
        "whatsapp",
        "meta-ips",
        "ai",
        "google-deepmind",
        "github",
    ]

    for artifact_name in (
        XRAY_CLIENT_NAME,
        XRAY_SERVER_NAME,
    ):
        artifact = artifacts[artifact_name]
        assert artifact["ruleOrder"] == expected_stages
        eu_rule = next(rule for rule in artifact["rules"] if rule["stage"] == "eu_exceptions")
        assert eu_rule["sourceIds"] == expected_eu_sources
        assert expected_stages.index("eu_exceptions") < expected_stages.index("ru_services")
        assert expected_stages.index("eu_exceptions") < expected_stages.index("broad_ru")


def test_critical_inline_block_entries_are_shared_by_all_renderers() -> None:
    policy = load_policy(POLICY_PATH)
    _policy_dump, artifacts = _decoded_outputs()
    block_stages = ("torrent_sources", "ads_trackers", "tor")
    rules_by_stage = {rule.stage: rule for rule in policy.rules}
    expected_sites = {
        converted
        for stage in block_stages
        for source_id in getattr(policy.source_groups, stage)
        for entry in policy.sources[source_id].entries
        if policy.sources[source_id].kind != "process"
        if (converted := _xray_domain(entry)) is not None
    }

    legacy = artifacts[LEGACY_HEADER_NAME]
    decoded = json.loads(base64.b64decode(legacy["value"]))
    assert decoded == legacy["decoded"]
    assert expected_sites <= set(decoded["BlockSites"])
    assert {
        "domain:1337x.to",
        "domain:eztv.re",
        "domain:limetorrents.lol",
        "domain:thepiratebay.org",
        "domain:torrentdownload.info",
        "domain:torrentgalaxy.to",
        "domain:yts.mx",
        "domain:scorecardresearch.com",
        "domain:torproject.org",
        "domain:torproject.net",
        r"regexp:\.onion$",
    } <= set(decoded["BlockSites"])

    for artifact_name in (XRAY_CLIENT_NAME, XRAY_SERVER_NAME):
        artifact = artifacts[artifact_name]
        actual_sites = {
            domain
            for rule in artifact["rules"]
            if rule["stage"] in block_stages
            for match in rule["matches"]
            for domain in match.get("domain", [])
        }
        assert expected_sites <= actual_sites

    mihomo = artifacts[MIHOMO_NAME]
    mihomo_rules = mihomo["rules"]
    for stage in block_stages:
        for source_id in getattr(policy.source_groups, stage):
            source = policy.sources[source_id]
            if source.kind == "process":
                assert all(f"PROCESS-NAME-REGEX,{entry}," in "\n".join(mihomo_rules) for entry in source.entries)
            else:
                target = "Torrents" if stage == "torrent_sources" else "REJECT"
                assert any(rule.startswith(f"RULE-SET,{source_id},{target}") for rule in mihomo_rules)
    assert all(rules_by_stage[stage].action == "block" for stage in block_stages)


def test_xray_network_port_pairs_do_not_expand_to_a_cross_product() -> None:
    policy = load_policy(POLICY_PATH)
    mixed = PolicySource(
        kind="inline",
        behavior="classical",
        entries=(
            "AND,((NETWORK,tcp),(DST-PORT,25))",
            "AND,((NETWORK,udp),(DST-PORT,853))",
        ),
    )
    mixed_policy = policy.model_copy(update={"sources": {**policy.sources, "mixed-network-port": mixed}})

    matches, providers = _xray_matches(mixed_policy, ("mixed-network-port",))

    assert providers == []
    assert matches == [
        {"network": "tcp", "port": "25"},
        {"network": "udp", "port": "853"},
    ]


def test_outputs_are_deterministic_and_manifest_hashes_every_renderer() -> None:
    _policy, first = build_outputs(POLICY_PATH)
    _policy, second = build_outputs(POLICY_PATH)
    assert first == second

    manifest = json.loads(first[MANIFEST_NAME])
    expected_coverage = {
        "mihomo": MIHOMO_NAME,
        "xrayClient": XRAY_CLIENT_NAME,
        "xrayServer": XRAY_SERVER_NAME,
        "legacyHeader": LEGACY_HEADER_NAME,
    }
    for renderer, artifact_name in expected_coverage.items():
        coverage = manifest["rendererCoverage"][renderer]
        content = first[artifact_name]
        assert coverage["status"] == "rendered"
        assert coverage["artifact"] == artifact_name
        assert manifest["artifacts"][artifact_name] == {
            "bytes": len(content),
            "sha256": hashlib.sha256(content).hexdigest(),
        }


def test_full_mihomo_config_replaces_critical_sections_and_retains_base_features() -> None:
    policy = load_policy(POLICY_PATH)
    _policy_dump, artifacts = _decoded_outputs()
    config = artifacts[MIHOMO_NAME]

    assert config["remnawave"] == {"includeHiddenHosts": False}
    assert config["tun"]["enable"] is True
    assert config["tun"]["stack"] == "gvisor"
    assert config["dns"]["enhanced-mode"] == "fake-ip"
    assert config["dns"]["fake-ip-range"] == "198.18.0.1/16"
    bootstrap_nameservers = config["dns"]["proxy-server-nameserver"]
    assert bootstrap_nameservers
    assert "system" in bootstrap_nameservers
    assert all("#" not in nameserver for nameserver in bootstrap_nameservers)
    dns_policy = config["dns"]["nameserver-policy"]
    assert "rule-set:youtube" in dns_policy
    assert "rule-set:ru-services-inline" in dns_policy
    assert "rule-set:ads-all" in dns_policy
    assert all("," not in key for key in dns_policy)
    provider_ids = set(config["rule-providers"])
    dns_rule_set_ids = {key.removeprefix("rule-set:") for key in dns_policy if key.startswith("rule-set:")}
    assert dns_rule_set_ids <= provider_ids
    assert "rule-set:tor-processes" not in dns_policy

    providers = config["rule-providers"]
    http_sources = {source_id: source for source_id, source in policy.sources.items() if source.kind == "http"}
    assert len(http_sources) == 29
    for source_id, source in http_sources.items():
        provider = providers[source_id]
        assert provider["url"] == source.url
        assert provider["format"] == source.format
        assert provider["interval"] == source.interval_seconds
        assert source.integrity is not None and source.integrity.pinned
        assert source.integrity.revision in source.url
        assert all(ref not in provider["url"] for ref in ("/main/", "/meta/", "/release/", "@main/"))

    groups = {group["name"]: group for group in config["proxy-groups"]}
    assert groups["World / EU"]["type"] == "fallback"
    assert groups["World / EU"]["proxies"] == ["🇩🇪 DE Auto", "🇳🇱 NL Auto"]
    assert groups["World / EU"]["url"] == policy.transport_groups.eu.health.probe_url
    assert groups["RU Sites"]["type"] == "fallback"
    assert groups["RU Sites"]["proxies"] == ["🇷🇺 SPB Auto", "🇷🇺 Moscow Auto"]
    assert groups["RU Sites"]["url"] == policy.transport_groups.ru.health.probe_url
    assert "DIRECT" not in groups["World / EU"]["proxies"]
    assert "DIRECT" not in groups["RU Sites"]["proxies"]
    assert "World / EU" not in groups["RU Sites"]["proxies"]
    assert groups["Torrents"]["proxies"] == ["REJECT"]

    rules = config["rules"]
    eu_first = rules.index("RULE-SET,manual-eu-inline,World / EU")
    ru_first = rules.index("RULE-SET,ru-services-inline,RU Sites")
    assert eu_first < ru_first
    assert rules[0] == "RULE-SET,private-ips,DIRECT"
    assert rules[-1] == "MATCH,World / EU"
    assert yaml.safe_load(yaml.safe_dump(config, allow_unicode=True)) == config


def test_xray_generator_uses_regional_policy_without_ru_to_eu_fallback(
    tmp_path: Path,
) -> None:
    output_dir = tmp_path / "compiled"
    generate(POLICY_PATH, output_dir)
    generator = _load_script(GENERATOR_PATH, "premium_smart_ru_xray_generator")

    template = generator.build_template(output_dir)
    route_policy = template["remnawave"]["routePolicy"]
    health = route_policy["regionalHealth"]
    assert health["eu"]["probe"]["url"] == "https://www.gstatic.com/generate_204"
    assert health["eu"]["primaryTransport"] == "xhttp"
    assert health["eu"]["fallbackTransport"] == "xhttp"
    assert health["ru"]["primaryTransport"] == "xhttp"
    assert health["ru"]["fallbackTransport"] == "xhttp"
    assert health["ru"]["probe"]["url"] == "https://www.ozon.ru/"
    assert health["eu"]["probe"]["url"] != health["ru"]["probe"]["url"]
    assert health["eu"]["degraded"]["crossRegionFallback"] is False
    assert health["ru"]["degraded"]["crossRegionFallback"] is False
    assert "observatory" not in template
    assert "burstObservatory" not in template
    deviations = route_policy["rendererDeviations"]
    assert deviations == [
        {
            "id": "xray-single-observatory-shared-ru-safe-probe",
            "reason": "Xray 26.6.27 observatory caused user-traffic stalls with XHTTP",
            "effect": "INCY uses deterministic XHTTP primaries; fallback transports remain manual",
            "probeUrl": "https://www.ozon.ru/",
        }
    ]

    assert "balancers" not in template["routing"]

    smtp_rules = [rule for rule in template["routing"]["rules"] if rule["ruleTag"] == "block_smtp_abuse"]
    assert smtp_rules == [
        {
            "type": "field",
            "ruleTag": "block_smtp_abuse",
            "network": "tcp",
            "port": "25,465,587",
            "outboundTag": "block",
        }
    ]

    rule_tags = [rule["ruleTag"] for rule in template["routing"]["rules"]]
    assert rule_tags.index("block_smtp_abuse") < rule_tags.index("route_eu_exceptions")
    assert rule_tags.index("route_eu_exceptions") < rule_tags.index("route_ru_services")
    eu_rules = [rule for rule in template["routing"]["rules"] if rule["ruleTag"] == "route_eu_exceptions"]
    eu_domains = {domain for rule in eu_rules for domain in rule.get("domain", [])}
    eu_ips = {ip for rule in eu_rules for ip in rule.get("ip", [])}
    assert {
        "geosite:youtube",
        "geosite:discord",
        "geosite:telegram",
        "geosite:whatsapp",
        "geosite:category-ai-!cn",
        "geosite:google-deepmind",
        "geosite:github",
    } <= eu_domains
    assert {"geoip:telegram", "geoip:facebook"} <= eu_ips
    assert "geoip:cloudflare" not in eu_ips
    assert {rule["outboundTag"] for rule in eu_rules} == {"eu-de-2"}
    ru_rules = [rule for rule in template["routing"]["rules"] if rule["ruleTag"] == "route_ru_services"]
    assert {rule["outboundTag"] for rule in ru_rules} == {"ru-spb-2"}
    provider_ids = {provider["id"] for provider in template["remnawave"]["routePolicy"]["providerSources"]}
    assert {
        "youtube",
        "discord-domains",
        "cloudflare-ips",
        "telegram-domains",
        "telegram-ips",
        "whatsapp",
        "meta-ips",
        "ai",
        "google-deepmind",
        "github",
    } <= provider_ids
    assert rule_tags[-1] == "route_final_eu"
    assert template["routing"]["rules"][-1]["network"] == "tcp,udp"


def test_xray_generator_builds_isolated_fail_closed_automatic_failover_canary(
    tmp_path: Path,
) -> None:
    output_dir = tmp_path / "compiled"
    generate(POLICY_PATH, output_dir)
    generator = _load_script(GENERATOR_PATH, "premium_smart_ru_xray_failover_generator")

    stable = generator.build_template(output_dir)
    canary = generator.build_template(output_dir, automatic_failover=True)

    assert "balancers" not in stable["routing"]
    assert "observatory" not in stable
    assert canary["remnawave"]["routePolicy"]["rendererMode"] == "automatic-failover-canary"
    assert canary["remnawave"]["routePolicy"]["rendererDeviations"] == [
        {
            "id": "xray-canary-single-observatory-shared-ru-safe-probe",
            "reason": "Xray 26.6.27 must use one deterministic observatory feature for all failover balancers",
            "effect": (
                "All four transports use the shared RU-accessible probe for liveness; "
                "destination routing remains policy-driven and is validated separately"
            ),
            "probeUrl": "https://www.ozon.ru/",
        }
    ]
    assert canary["observatory"]["subjectSelector"] == [
        "eu-de-2",
        "eu-nl-2",
        "ru-spb-2",
        "ru-msk-2",
    ]
    assert canary["observatory"]["probeUrl"] == "https://www.ozon.ru/"
    assert "burstObservatory" not in canary

    balancers = {item["tag"]: item for item in canary["routing"]["balancers"]}
    assert balancers["eu-primary"]["selector"] == ["eu-de-2"]
    assert balancers["eu-primary"]["strategy"] == {"type": "leastPing"}
    assert balancers["eu-primary"]["fallbackTag"] == "eu-fallback-loop"
    assert balancers["eu-fallback"]["selector"] == ["eu-nl-2"]
    assert balancers["eu-fallback"]["fallbackTag"] == "block"
    assert balancers["ru-primary"]["selector"] == ["ru-spb-2"]
    assert balancers["ru-primary"]["strategy"] == {"type": "leastPing"}
    assert balancers["ru-primary"]["fallbackTag"] == "ru-fallback-loop"
    assert balancers["ru-fallback"]["selector"] == ["ru-msk-2"]
    assert balancers["ru-fallback"]["fallbackTag"] == "block"
    assert all(item["fallbackTag"] != "direct" for item in balancers.values())

    rules = canary["routing"]["rules"]
    assert rules[0]["ruleTag"] == "route_eu_failover_loop"
    assert rules[0]["balancerTag"] == "eu-fallback"
    assert rules[1]["ruleTag"] == "route_ru_failover_loop"
    assert rules[1]["balancerTag"] == "ru-fallback"
    by_tag = {item["ruleTag"]: item for item in rules}
    assert by_tag["route_ru_services"]["balancerTag"] == "ru-primary"
    assert by_tag["route_final_eu"]["balancerTag"] == "eu-primary"
    assert by_tag["block_smtp_abuse"]["outboundTag"] == "block"


def test_xray_generator_rejects_reversed_primary_fallback_order(tmp_path: Path) -> None:
    output_dir = tmp_path / "compiled"
    generate(POLICY_PATH, output_dir)
    generator = _load_script(GENERATOR_PATH, "premium_smart_ru_xray_order_guard")
    artifact = json.loads((output_dir / XRAY_CLIENT_NAME).read_text(encoding="utf-8"))
    artifact["transportPolicy"]["eu"]["primary"] = "nl"
    artifact["transportPolicy"]["eu"]["fallback"] = "de"

    with pytest.raises(RuntimeError, match="invalid eu order"):
        generator._transport_metadata(artifact)


def test_xray_generator_rejects_prefix_selector_collisions() -> None:
    generator = _load_script(GENERATOR_PATH, "premium_smart_ru_xray_selector_guard")

    with pytest.raises(RuntimeError, match="must match exactly one outbound"):
        generator._validate_failover_selectors(
            ("eu-de-2",),
            ("eu-de-2", "eu-de-20"),
        )


def test_consumers_validate_compiled_artifact_checksums_fail_closed(
    tmp_path: Path,
) -> None:
    output_dir = tmp_path / "compiled"
    generate(POLICY_PATH, output_dir)
    operator = _load_script(OPERATOR_PATH, "premium_smart_ru_server_operator")
    server, header = operator._load_policy_artifacts(output_dir)

    assert server["consumer"] == "remnawave-xray-server"
    assert json.loads(base64.b64decode(header))["BlockSites"]

    server_path = output_dir / XRAY_SERVER_NAME
    server_path.write_bytes(server_path.read_bytes() + b"\n")
    with pytest.raises(RuntimeError, match="checksum or size mismatch"):
        operator._load_policy_artifacts(output_dir)


def test_consumers_reject_artifacts_for_another_policy_revision(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    output_dir = tmp_path / "compiled"
    generate(POLICY_PATH, output_dir)
    stale_policy = tmp_path / "premium_smart_ru.yaml"
    stale_policy.write_bytes(POLICY_PATH.read_bytes() + b"\n")
    operator = _load_script(OPERATOR_PATH, "premium_smart_ru_stale_server_operator")
    generator = _load_script(GENERATOR_PATH, "premium_smart_ru_stale_xray_generator")
    monkeypatch.setattr(operator, "POLICY_PATH", stale_policy)
    monkeypatch.setattr(generator, "POLICY_PATH", stale_policy)

    with pytest.raises(RuntimeError, match="stale for canonical policy"):
        operator._load_policy_artifacts(output_dir)
    with pytest.raises(RuntimeError, match="stale for canonical policy"):
        generator._load_policy_artifact(output_dir)


def test_consumer_scripts_do_not_define_independent_critical_lists() -> None:
    generator_source = GENERATOR_PATH.read_text(encoding="utf-8")
    operator_source = OPERATOR_PATH.read_text(encoding="utf-8")

    assert "XRAY_CLIENT_ARTIFACT" in generator_source
    assert "_load_policy_artifact" in generator_source
    assert "urllib.request" not in generator_source
    for duplicated_name in (
        "DIRECT_DOMAINS",
        "RU_DOMAINS",
        "BLOCKED_TORRENT_DOMAINS",
        "INCY_ROUTING_HEADER",
    ):
        assert duplicated_name not in generator_source
        assert duplicated_name not in operator_source
    assert "XRAY_SERVER_ARTIFACT" in operator_source
    assert "LEGACY_HEADER_ARTIFACT" in operator_source
