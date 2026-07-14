#!/usr/bin/env python3
"""Stage trusted Premium Smart RU artifacts and optionally run both SQL seeds.

Run this on the PostgreSQL host/container so the server can read the private
stage directory. Database credentials remain in the standard libpq environment
or .pgpass; trusted artifact digests are passed directly to psql variables.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import importlib
import json
import os
import re
import runpy
import shutil
import stat
import subprocess
import tempfile
import uuid
from dataclasses import dataclass
from fnmatch import fnmatchcase
from pathlib import Path
from pathlib import PurePosixPath
from typing import Any

try:
    yaml = importlib.import_module("yaml")
except ModuleNotFoundError:  # pragma: no cover - production seed fails closed below
    yaml = None

REPO_ROOT = Path(__file__).resolve().parents[2]
GENERATED_DIR = REPO_ROOT / "scripts/remnawave/generated/premium_smart_ru"
MIHOMO_SOURCE = GENERATED_DIR / "mihomo.yaml"
INCY_SOURCE = (
    REPO_ROOT / "scripts/remnawave/templates/cybervpn-premium-smart-ru-incy-xray.json"
)
INCY_CANARY_SOURCE = REPO_ROOT / (
    "scripts/remnawave/templates/"
    "cybervpn-premium-smart-ru-incy-xray-failover-canary.json"
)
LEGACY_HEADER_SOURCE = GENERATED_DIR / "legacy-routing-header.json"
COMPILER_MANIFEST_SOURCE = GENERATED_DIR / "manifest.json"
INCY_GENERATOR_SOURCE = (
    REPO_ROOT / "scripts/remnawave/generate-premium-smart-ru-incy-xray.py"
)
MAIN_SEED = REPO_ROOT / "scripts/remnawave/seed-cybervpn-premium-smart-ru.sql"
INCY_SEED = REPO_ROOT / "scripts/remnawave/seed-cybervpn-premium-smart-ru-incy-xray.sql"
STAGED_NAMES = {
    "mihomo": "mihomo.yaml",
    "incy": "incy-xray.json",
    "incy_canary": "incy-xray-failover-canary.json",
    "legacy_header": "legacy-routing-header.json",
}
INCY_TEMPLATE_NAMES = (
    "CyberVPN Premium Smart RU INCY",
    "CyberVPN Premium Smart RU INCY Failover Canary",
)
TORRENT_CATALOG_DOMAINS = {
    "domain:1337x.to",
    "domain:eztv.re",
    "domain:kinozal.tv",
    "domain:limetorrents.lol",
    "domain:nnmclub.to",
    "domain:rutracker.org",
    "domain:rutor.info",
    "domain:thepiratebay.org",
    "domain:torrentdownload.info",
    "domain:torrentgalaxy.to",
    "domain:yts.mx",
}
REQUIRED_EU_TORRENT_CATALOG_DOMAINS = TORRENT_CATALOG_DOMAINS
TORRENT_CATALOG_HOSTS = {
    value.removeprefix("domain:") for value in TORRENT_CATALOG_DOMAINS
}
REQUIRED_EU_TORRENT_CATALOG_HOSTS = TORRENT_CATALOG_HOSTS
MIHOMO_TRAILING_RULE_OPTIONS = frozenset({"no-resolve"})
MIHOMO_DOMAIN_MATCHER_PATTERN = re.compile(
    r"(?:^|[^a-z0-9_-])domain-(keyword|regex|regexp|wildcard),([^,)\r\n]+)",
    re.IGNORECASE,
)
MIHOMO_TORRENT_BLOCK_TARGETS = frozenset(
    {
        "reject",
        "reject-drop",
        "block",
        "block policy",
        "⛔ block",
        "torrents",
        "🧲 torrents",
    }
)
MIHOMO_CATALOG_ACCESS_PROVIDER = "catalog-access-inline"
MIHOMO_CATALOG_ACCESS_TARGET = "🌍 world / eu"


def _sha256(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def _canonical_json(value: Any) -> bytes:
    return (
        json.dumps(
            value,
            ensure_ascii=True,
            sort_keys=True,
            separators=(",", ":"),
        )
        + "\n"
    ).encode()


def _load_json(content: bytes, label: str) -> dict[str, Any]:
    try:
        value = json.loads(content)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"{label} must be valid UTF-8 JSON") from exc
    if not isinstance(value, dict):
        raise RuntimeError(f"{label} must be a JSON object")
    return value


def _xray_domain_hosts(value: Any) -> set[str]:
    values = (
        value if isinstance(value, list) else [value] if isinstance(value, str) else []
    )
    return {
        str(item).strip().casefold().removeprefix("domain:").removeprefix("full:")
        for item in values
        if str(item).strip()
    }


def _xray_matcher_blocks_catalog(value: Any) -> bool:
    normalized = str(value).strip().casefold()
    if normalized.startswith("keyword:"):
        keyword = normalized.removeprefix("keyword:").strip()
        return not keyword or any(keyword in host for host in TORRENT_CATALOG_HOSTS)
    if normalized.startswith("regexp:"):
        pattern = normalized.removeprefix("regexp:").strip()
        if not pattern or len(pattern) > 512:
            return True
        try:
            return any(
                re.search(pattern, candidate, flags=re.IGNORECASE) is not None
                for host in TORRENT_CATALOG_HOSTS
                for candidate in (host, f"www.{host}")
            )
        except re.error:
            return True
    return _xray_domain_hosts(normalized).intersection(TORRENT_CATALOG_HOSTS) != set()


def _mihomo_text_matches_catalog(text: str) -> bool:
    normalized = text.casefold()
    unescaped = normalized.replace("\\", "")
    if any(host in normalized or host in unescaped for host in TORRENT_CATALOG_HOSTS):
        return True
    for match in MIHOMO_DOMAIN_MATCHER_PATTERN.finditer(normalized):
        matcher_type = match.group(1).casefold()
        matcher = match.group(2).strip().strip("'\"")
        if not matcher or len(matcher) > 512:
            return True
        if matcher_type == "keyword":
            if any(matcher in host for host in TORRENT_CATALOG_HOSTS):
                return True
            continue
        if matcher_type == "wildcard":
            if any(fnmatchcase(host, matcher) for host in TORRENT_CATALOG_HOSTS):
                return True
            continue
        try:
            if any(
                re.search(matcher, host, flags=re.IGNORECASE)
                for host in TORRENT_CATALOG_HOSTS
            ):
                return True
        except re.error:
            return True
    return False


def _split_mihomo_rule(rule: str) -> list[str]:
    parts: list[str] = []
    current: list[str] = []
    depth = 0
    for character in rule:
        if character == "(":
            depth += 1
        elif character == ")" and depth:
            depth -= 1
        if character == "," and depth == 0:
            parts.append("".join(current).strip())
            current = []
        else:
            current.append(character)
    parts.append("".join(current).strip())
    return parts


def _mihomo_rule_subject_and_target(rule: str) -> tuple[str, str]:
    parts = _split_mihomo_rule(rule)
    while parts and parts[-1].casefold() in MIHOMO_TRAILING_RULE_OPTIONS:
        parts.pop()
    if len(parts) < 2:
        return "", ""
    return ",".join(parts[:-1]).casefold(), parts[-1].casefold()


def _mihomo_rule_provider_ids(subject: str) -> set[str]:
    return {
        match.group(1).strip().casefold()
        for match in re.finditer(
            r"(?:^|[,(])rule-set,([^,)]+)", subject, flags=re.IGNORECASE
        )
        if match.group(1).strip()
    }


def _load_mihomo_mapping(text: str) -> dict[str, Any]:
    if yaml is None:
        raise RuntimeError("PyYAML is required to validate the Mihomo artifact")
    try:
        value = yaml.safe_load(text)
    except yaml.YAMLError as exc:
        raise RuntimeError("Mihomo artifact must be valid YAML") from exc
    if not isinstance(value, dict):
        raise RuntimeError("Mihomo artifact must be a YAML mapping")
    return value


def _mihomo_block_targets(artifact: dict[str, Any]) -> set[str]:
    targets = set(MIHOMO_TORRENT_BLOCK_TARGETS)
    group_proxies: dict[str, set[str]] = {}
    groups = artifact.get("proxy-groups")
    if not isinstance(groups, list):
        raise RuntimeError("Mihomo artifact proxy-groups must be a list")
    for group in groups:
        if not isinstance(group, dict):
            raise RuntimeError("Mihomo proxy-groups entries must be mappings")
        name = str(group.get("name") or "").strip().casefold()
        raw_proxies = group.get("proxies", [])
        if not isinstance(raw_proxies, list):
            raise RuntimeError("Mihomo proxy-group proxies must be a list")
        proxies = {
            str(proxy).strip().casefold() for proxy in raw_proxies if str(proxy).strip()
        }
        if name and proxies:
            group_proxies[name] = proxies
    changed = True
    while changed:
        changed = False
        for name, proxies in group_proxies.items():
            if name not in targets and proxies.issubset(targets):
                targets.add(name)
                changed = True
    return targets


def _manual_mihomo_torrent_rules(artifact: dict[str, Any]) -> list[str]:
    rules = artifact.get("rules")
    providers = artifact.get("rule-providers")
    if not isinstance(rules, list) or not all(isinstance(rule, str) for rule in rules):
        raise RuntimeError("Mihomo artifact rules must be a list of strings")
    if not isinstance(providers, dict):
        raise RuntimeError("Mihomo artifact rule-providers must be a mapping")
    provider_ids = {
        str(name).strip().casefold()
        for name, provider in providers.items()
        if str(name).strip()
        for provider_text in [
            json.dumps(provider, ensure_ascii=False, sort_keys=True, default=str)
        ]
        if "torrent" in provider_text or _mihomo_text_matches_catalog(provider_text)
    }
    block_targets = _mihomo_block_targets(artifact)
    manual_rules: list[str] = []
    for rule in rules:
        subject, target = _mihomo_rule_subject_and_target(rule)
        torrent_related = "torrent" in subject or _mihomo_text_matches_catalog(subject)
        torrent_related = torrent_related or bool(
            _mihomo_rule_provider_ids(subject) & provider_ids
        )
        if torrent_related and target in block_targets:
            manual_rules.append(rule)
    return manual_rules


def _mihomo_catalog_access_is_safe(artifact: dict[str, Any]) -> bool:
    providers = artifact.get("rule-providers")
    rules = artifact.get("rules")
    dns = artifact.get("dns")
    if (
        not isinstance(providers, dict)
        or not isinstance(rules, list)
        or not isinstance(dns, dict)
    ):
        return False

    provider = providers.get(MIHOMO_CATALOG_ACCESS_PROVIDER)
    if not isinstance(provider, dict):
        return False
    payload = provider.get("payload")
    if not isinstance(payload, list):
        return False
    catalog_hosts = {
        parts[1].strip().casefold()
        for item in payload
        if isinstance(item, str)
        for parts in [_split_mihomo_rule(item)]
        if len(parts) >= 2 and parts[0].casefold() in {"domain", "domain-suffix"}
    }
    if not REQUIRED_EU_TORRENT_CATALOG_HOSTS.issubset(catalog_hosts):
        return False

    block_targets = _mihomo_block_targets(artifact)
    parsed_rules = [
        _mihomo_rule_subject_and_target(rule) for rule in rules if isinstance(rule, str)
    ]
    catalog_rule_indexes = [
        index
        for index, (subject, target) in enumerate(parsed_rules)
        if MIHOMO_CATALOG_ACCESS_PROVIDER in _mihomo_rule_provider_ids(subject)
        and target == MIHOMO_CATALOG_ACCESS_TARGET
    ]
    block_rule_indexes = [
        index
        for index, (_subject, target) in enumerate(parsed_rules)
        if target in block_targets
    ]
    if (
        len(parsed_rules) != len(rules)
        or len(catalog_rule_indexes) != 1
        or not block_rule_indexes
        or not all(catalog_rule_indexes[0] < index for index in block_rule_indexes)
    ):
        return False

    nameserver_policy = dns.get("nameserver-policy")
    if not isinstance(nameserver_policy, dict):
        return False
    dns_keys = [str(key).strip().casefold() for key in nameserver_policy]
    catalog_dns_key = f"rule-set:{MIHOMO_CATALOG_ACCESS_PROVIDER}"
    if catalog_dns_key not in dns_keys:
        return False
    catalog_dns_index = dns_keys.index(catalog_dns_key)
    blocked_dns_indexes = [
        index
        for index, value in enumerate(nameserver_policy.values())
        if isinstance(value, list)
        and any(str(item).strip().casefold() == "rcode://name_error" for item in value)
    ]
    return bool(blocked_dns_indexes) and all(
        catalog_dns_index < index for index in blocked_dns_indexes
    )


def _validate_mihomo(content: bytes) -> None:
    try:
        text = content.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise RuntimeError("Mihomo artifact must be valid UTF-8") from exc
    artifact = _load_mihomo_mapping(text)
    required = (
        "MATCH,🌍 World / EU",
        "name: 🇷🇺 RU Sites",
        "name: 🌍 World / EU",
        "RULE-SET,smtp-abuse,⛔ BLOCK",
        "DOMAIN-SUFFIX,rutracker.org",
        "RULE-SET,ru-eu-exceptions,🌍 World / EU",
    )
    forbidden = (
        "name: Torrents",
        "torrent-websites",
        "torrent-trackers",
        "torrent-clients",
        "PROCESS-NAME-REGEX,(?i).*torrent.*",
        "DOMAIN-SUFFIX,rutracker.org,REJECT",
    )
    normalized_text = text.casefold()
    if (
        any(marker not in text for marker in required)
        or any(marker in text for marker in forbidden)
        or "name: torrents" in normalized_text
        or "name: 🧲 torrents" in normalized_text
        or _manual_mihomo_torrent_rules(artifact)
        or not _mihomo_catalog_access_is_safe(artifact)
        or "MATCH,DIRECT" in text
    ):
        raise RuntimeError("Mihomo artifact semantics are invalid")


def _validate_incy(
    content: bytes,
    *,
    automatic_failover: bool = True,
    canary: bool = False,
) -> None:
    artifact_label = "INCY canary" if canary else "INCY"
    artifact = _load_json(content, "INCY artifact")
    remnawave = artifact.get("remnawave")
    routing = artifact.get("routing")
    if not isinstance(remnawave, dict) or not isinstance(routing, dict):
        raise RuntimeError("INCY artifact lacks Remnawave routing metadata")
    route_policy = remnawave.get("routePolicy")
    inject_hosts = remnawave.get("injectHosts")
    if (
        not isinstance(route_policy, dict)
        or route_policy.get("schemaVersion") != 1
        or route_policy.get("product") != "premium_smart_ru"
        or not isinstance(inject_hosts, list)
        or len(inject_hosts) != 4
    ):
        raise RuntimeError("INCY artifact has an invalid product contract")
    if not isinstance(artifact.get("inbounds"), list) or len(artifact["inbounds"]) != 2:
        raise RuntimeError("INCY artifact must define exactly two local inbounds")
    if not isinstance(routing.get("rules"), list) or not routing["rules"]:
        raise RuntimeError("INCY artifact contains no routing rules")
    if not automatic_failover and (
        "balancers" in routing
        or "observatory" in artifact
        or "burstObservatory" in artifact
    ):
        raise RuntimeError(
            "INCY artifact must not enable unstable Xray observatory failover"
        )
    if automatic_failover:
        balancers = routing.get("balancers")
        expected_balancers = [
            {
                "tag": "eu-primary",
                "selector": ["eu-de-2"],
                "strategy": {"type": "leastPing"},
                "fallbackTag": "eu-fallback-loop",
            },
            {
                "tag": "eu-fallback",
                "selector": ["eu-nl-2"],
                "strategy": {"type": "leastPing"},
                "fallbackTag": "block",
            },
            {
                "tag": "ru-primary",
                "selector": ["ru-msk-2"],
                "strategy": {"type": "leastPing"},
                "fallbackTag": "ru-fallback-loop",
            },
            {
                "tag": "ru-fallback",
                "selector": ["ru-spb-2"],
                "strategy": {"type": "leastPing"},
                "fallbackTag": "block",
            },
        ]
        regional_health = route_policy.get("regionalHealth")
        ru_health = (
            regional_health.get("ru") if isinstance(regional_health, dict) else None
        )
        ru_probe = ru_health.get("probe") if isinstance(ru_health, dict) else None
        expected_probe_url = ru_probe.get("url") if isinstance(ru_probe, dict) else None
        expected_observatory = {
            "subjectSelector": ["eu-de-2", "eu-nl-2", "ru-msk-2", "ru-spb-2"],
            "probeUrl": expected_probe_url,
            "probeInterval": "10s",
            "enableConcurrency": True,
        }
        if (
            route_policy.get("rendererMode")
            != ("automatic-failover-canary" if canary else "automatic-failover")
            or balancers != expected_balancers
            or not isinstance(expected_probe_url, str)
            or artifact.get("observatory") != expected_observatory
            or artifact.get("burstObservatory") is not None
        ):
            raise RuntimeError(
                f"{artifact_label} artifact lacks regional failover health checks"
            )
    routes_by_tag = {
        rule.get("ruleTag"): rule
        for rule in routing["rules"]
        if isinstance(rule, dict) and isinstance(rule.get("ruleTag"), str)
    }
    block_outbound_tags = {"block", "rw_tb_outbound_block"}
    for outbound in artifact.get("outbounds", []):
        if not isinstance(outbound, dict):
            continue
        if str(outbound.get("protocol") or "").casefold() != "blackhole":
            continue
        tag = str(outbound.get("tag") or "").strip().casefold()
        if tag:
            block_outbound_tags.add(tag)
    for rule in routing["rules"]:
        if not isinstance(rule, dict):
            continue
        protocols = rule.get("protocol")
        protocols = protocols if isinstance(protocols, list) else [protocols]
        processes = rule.get("process")
        processes = processes if isinstance(processes, list) else [processes]
        domains = rule.get("domain")
        domains = domains if isinstance(domains, list) else [domains]
        if (
            str(rule.get("ruleTag") or "")
            in {
                "block_bittorrent_protocol",
                "block_torrent_processes",
                "block_torrent_sources",
            }
            or any(str(protocol).casefold() == "bittorrent" for protocol in protocols)
            or any("torrent" in str(process).casefold() for process in processes)
            or (
                str(rule.get("outboundTag") or "").casefold() in block_outbound_tags
                and any(_xray_matcher_blocks_catalog(domain) for domain in domains)
            )
        ):
            raise RuntimeError(
                "INCY artifact must delegate BitTorrent enforcement to the Remnawave node plugin"
            )
    route_key = "balancerTag" if automatic_failover else "outboundTag"
    expected_eu = "eu-primary" if automatic_failover else "eu-de-2"
    expected_ru = "ru-primary" if automatic_failover else "ru-msk-2"
    if routes_by_tag.get("route_final_eu", {}).get(route_key) != expected_eu:
        raise RuntimeError(
            "INCY artifact must route default traffic to the DE-first path"
        )
    if routes_by_tag.get("route_ru_services", {}).get(route_key) != expected_ru:
        raise RuntimeError(
            "INCY artifact must route RU services to the Moscow-first path"
        )
    catalog_rule_indexes = [
        index
        for index, rule in enumerate(routing["rules"])
        if isinstance(rule, dict) and rule.get("ruleTag") == "route_catalog_exceptions"
    ]
    block_rule_indexes = [
        index
        for index, rule in enumerate(routing["rules"])
        if isinstance(rule, dict)
        and str(rule.get("outboundTag") or "").casefold() in block_outbound_tags
    ]
    if len(catalog_rule_indexes) != 1:
        raise RuntimeError(
            "INCY torrent-catalog websites require one dedicated EU access route"
        )
    catalog_rule = routing["rules"][catalog_rule_indexes[0]]
    if (
        not isinstance(catalog_rule, dict)
        or catalog_rule.get(route_key) != expected_eu
        or not REQUIRED_EU_TORRENT_CATALOG_HOSTS.issubset(
            _xray_domain_hosts(catalog_rule.get("domain"))
        )
        or not block_rule_indexes
        or not all(catalog_rule_indexes[0] < index for index in block_rule_indexes)
    ):
        raise RuntimeError(
            "INCY torrent-catalog websites must route through EU before block policies"
        )
    if automatic_failover:
        expected_loop_rules = [
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
        if (
            routing["rules"][:2] != expected_loop_rules
            or routes_by_tag.get("route_eu_failover_loop") != expected_loop_rules[0]
            or routes_by_tag.get("route_ru_failover_loop") != expected_loop_rules[1]
        ):
            raise RuntimeError(
                f"{artifact_label} failover must remain regional and fail closed"
            )
    smtp_rule = routes_by_tag.get("block_smtp_abuse", {})
    if smtp_rule != {
        "type": "field",
        "ruleTag": "block_smtp_abuse",
        "network": "tcp",
        "port": "25,465,587",
        "outboundTag": "block",
    }:
        raise RuntimeError("INCY artifact must block SMTP abuse ports")


def _validate_legacy_header(content: bytes) -> None:
    artifact = _load_json(content, "legacy routing header")
    value = artifact.get("value")
    decoded = artifact.get("decoded")
    if (
        artifact.get("schemaVersion") != 1
        or artifact.get("product") != "premium_smart_ru"
        or artifact.get("consumer") != "remnawave-legacy-routing-header"
        or artifact.get("encoding") != "base64-json"
        or not isinstance(value, str)
        or not isinstance(decoded, dict)
    ):
        raise RuntimeError("Legacy routing header contract is invalid")
    try:
        encoded_payload = json.loads(base64.b64decode(value, validate=True))
    except (ValueError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RuntimeError("Legacy routing header value is not base64 JSON") from exc
    if encoded_payload != decoded:
        raise RuntimeError("Legacy routing header decoded payload does not match value")
    required_values = {
        "Name": "CyberVPN Premium Smart RU",
        "GlobalProxy": "true",
        "DomainStrategy": "AsIs",
        "FakeDNS": "false",
        "RemoteDNSType": "DoH",
        "RemoteDNSDomain": "https://cloudflare-dns.com/dns-query",
        "RemoteDNSIP": "1.1.1.1",
    }
    if any(decoded.get(key) != expected for key, expected in required_values.items()):
        raise RuntimeError("Legacy routing header semantics are invalid")
    block_sites = decoded.get("BlockSites")
    direct_ip = decoded.get("DirectIp")
    if (
        not isinstance(block_sites, list)
        or any(
            str(site).strip().casefold() in TORRENT_CATALOG_DOMAINS
            for site in block_sites
        )
        or "geosite:category-ads-all" not in block_sites
        or not isinstance(direct_ip, list)
        or "10.0.0.0/8" not in direct_ip
    ):
        raise RuntimeError("Legacy routing header lists are invalid")


def _load_and_validate_sources() -> dict[str, bytes]:
    try:
        artifacts = {
            "mihomo": MIHOMO_SOURCE.read_bytes(),
            "legacy_header": LEGACY_HEADER_SOURCE.read_bytes(),
        }
        compiler_manifest_content = COMPILER_MANIFEST_SOURCE.read_bytes()
    except OSError as exc:
        raise RuntimeError(f"Cannot read Premium Smart RU artifact: {exc}") from exc

    try:
        generator = runpy.run_path(str(INCY_GENERATOR_SOURCE))
        expected_incy = generator["build_template"]()
        expected_incy_canary = generator["build_template"](canary=True)
    except (KeyError, OSError, RuntimeError) as exc:
        raise RuntimeError(
            "Cannot regenerate INCY artifact from the canonical compiler output"
        ) from exc
    expected_incy_content = (
        json.dumps(expected_incy, ensure_ascii=False, indent=2) + "\n"
    ).encode()
    artifacts["incy"] = expected_incy_content
    artifacts["incy_canary"] = (
        json.dumps(expected_incy_canary, ensure_ascii=False, indent=2) + "\n"
    ).encode()
    _validate_mihomo(artifacts["mihomo"])
    _validate_incy(artifacts["incy"])
    _validate_incy(artifacts["incy_canary"], canary=True)
    _validate_legacy_header(artifacts["legacy_header"])
    compiler_manifest = _load_json(compiler_manifest_content, "compiler manifest")
    if (
        compiler_manifest.get("schemaVersion") != 1
        or compiler_manifest.get("product") != "premium_smart_ru"
    ):
        raise RuntimeError("Compiler manifest contract is invalid")
    declared = compiler_manifest.get("artifacts")
    if not isinstance(declared, dict):
        raise RuntimeError("Compiler manifest artifacts are invalid")
    for key in ("mihomo", "legacy_header"):
        name = STAGED_NAMES[key]
        metadata = declared.get(name)
        content = artifacts[key]
        if not isinstance(metadata, dict) or metadata != {
            "bytes": len(content),
            "sha256": _sha256(content),
        }:
            raise RuntimeError(f"Compiler manifest does not authenticate {name}")
    artifacts["compiler_manifest"] = compiler_manifest_content
    return artifacts


def _validate_private_stage_root(path: Path) -> Path:
    if path.is_symlink():
        raise RuntimeError("Stage root must not be a symlink")
    try:
        resolved = path.expanduser().resolve(strict=True)
        root_stat = resolved.lstat()
    except OSError as exc:
        raise RuntimeError(f"Cannot access stage root: {exc}") from exc
    if not stat.S_ISDIR(root_stat.st_mode):
        raise RuntimeError("Stage root must be a directory")
    if os.name != "nt":
        if root_stat.st_uid != os.geteuid():
            raise RuntimeError("Stage root must be owned by the operator")
        if root_stat.st_mode & 0o022:
            raise RuntimeError("Stage root must not be group/world-writable")
    return resolved


def _fsync_directory(path: Path) -> None:
    if os.name == "nt":
        return
    descriptor = os.open(path, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _atomic_write(path: Path, content: bytes) -> None:
    temporary = path.parent / f".{path.name}.{uuid.uuid4().hex}.tmp"
    descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(temporary, 0o600)
        os.replace(temporary, path)
        os.chmod(path, 0o600)
    finally:
        if temporary.exists():
            temporary.unlink()


@dataclass(frozen=True)
class StageContract:
    root: Path
    directory: Path
    manifest_sha256: str
    artifact_sha256: dict[str, str]

    def psql_variables(self, *, stage_directory: str | None = None) -> dict[str, str]:
        return {
            "cybervpn_premium_smart_ru_stage_dir": stage_directory
            or self.directory.as_posix(),
            "cybervpn_premium_smart_ru_stage_manifest_sha256": self.manifest_sha256,
            "cybervpn_premium_smart_ru_mihomo_sha256": self.artifact_sha256["mihomo"],
            "cybervpn_premium_smart_ru_incy_sha256": self.artifact_sha256["incy"],
            "cybervpn_premium_smart_ru_incy_canary_sha256": self.artifact_sha256[
                "incy_canary"
            ],
            "cybervpn_premium_smart_ru_legacy_header_sha256": self.artifact_sha256[
                "legacy_header"
            ],
        }


def _stage_artifacts(stage_root: Path) -> StageContract:
    root = _validate_private_stage_root(stage_root)
    artifacts = _load_and_validate_sources()
    directory = Path(tempfile.mkdtemp(prefix="premium-smart-ru-", dir=root)).resolve(
        strict=True
    )
    os.chmod(directory, 0o700)
    try:
        artifact_sha256 = {key: _sha256(artifacts[key]) for key in STAGED_NAMES}
        for key, name in STAGED_NAMES.items():
            _atomic_write(directory / name, artifacts[key])
        manifest = {
            "schemaVersion": 1,
            "product": "premium_smart_ru",
            "validation": {
                "mihomoProtocolOnlyTorrentPolicy": True,
            },
            "sourceCompilerManifestSha256": _sha256(artifacts["compiler_manifest"]),
            "artifacts": {
                STAGED_NAMES[key]: {
                    "bytes": len(artifacts[key]),
                    "sha256": artifact_sha256[key],
                }
                for key in STAGED_NAMES
            },
        }
        manifest_content = _canonical_json(manifest)
        _atomic_write(directory / "manifest.json", manifest_content)
        _fsync_directory(directory)
        _fsync_directory(root)
        return StageContract(
            root=root,
            directory=directory,
            manifest_sha256=_sha256(manifest_content),
            artifact_sha256=artifact_sha256,
        )
    except BaseException:
        shutil.rmtree(directory, ignore_errors=True)
        raise


def _remove_stage(contract: StageContract) -> None:
    if contract.directory.parent != contract.root:
        raise RuntimeError("Refusing to remove stage outside the trusted root")
    shutil.rmtree(contract.directory)
    _fsync_directory(contract.root)


def _seed_paths(selection: str) -> list[Path]:
    if selection == "main":
        return [MAIN_SEED]
    if selection == "incy":
        return [INCY_SEED]
    return [MAIN_SEED, INCY_SEED]


def _psql_command(contract: StageContract, *, psql: str, selection: str) -> list[str]:
    command = [psql, "-X", "-v", "ON_ERROR_STOP=1"]
    for name, value in contract.psql_variables().items():
        command.extend(["-v", f"{name}={value}"])
    for seed in _seed_paths(selection):
        command.extend(["-f", str(seed)])
    return command


def _validate_container_stage_root(value: str) -> PurePosixPath:
    path = PurePosixPath(value)
    if not path.is_absolute() or ".." in path.parts or path == PurePosixPath("/"):
        raise RuntimeError("Container stage root must be a safe absolute path")
    return path


def _docker_command(docker: str, container: str, *command: str) -> list[str]:
    return [docker, "exec", container, *command]


def _copy_stage_to_container(
    contract: StageContract,
    *,
    docker: str,
    container: str,
    container_stage_root: str,
    owner: str,
) -> str:
    root = _validate_container_stage_root(container_stage_root)
    directory = root / f"premium-smart-ru-{uuid.uuid4().hex}"
    if not owner or any(
        character
        not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-"
        for character in owner
    ):
        raise RuntimeError("Container stage owner is invalid")

    subprocess.run(
        _docker_command(
            docker,
            container,
            "install",
            "-d",
            "-m",
            "0700",
            "-o",
            owner,
            "-g",
            owner,
            str(root),
            str(directory),
        ),
        check=True,
    )
    try:
        for source in sorted(contract.directory.iterdir(), key=lambda item: item.name):
            if not source.is_file() or source.is_symlink():
                raise RuntimeError(f"Unexpected staged artifact: {source.name}")
            destination = f"{container}:{directory}/{source.name}"
            subprocess.run([docker, "cp", str(source), destination], check=True)
            subprocess.run(
                _docker_command(
                    docker,
                    container,
                    "chown",
                    f"{owner}:{owner}",
                    f"{directory}/{source.name}",
                ),
                check=True,
            )
            subprocess.run(
                _docker_command(
                    docker,
                    container,
                    "chmod",
                    "0600",
                    f"{directory}/{source.name}",
                ),
                check=True,
            )
        return str(directory)
    except BaseException:
        subprocess.run(
            _docker_command(docker, container, "rm", "-rf", "--", str(directory)),
            check=False,
        )
        raise


def _remove_container_stage(
    *,
    docker: str,
    container: str,
    container_stage_root: str,
    directory: str,
) -> None:
    root = _validate_container_stage_root(container_stage_root)
    target = PurePosixPath(directory)
    if target.parent != root or not target.name.startswith("premium-smart-ru-"):
        raise RuntimeError(
            "Refusing to remove container stage outside the trusted root"
        )
    subprocess.run(
        _docker_command(docker, container, "rm", "-rf", "--", str(target)),
        check=True,
    )


def _run_container_psql(
    contract: StageContract,
    *,
    docker: str,
    container: str,
    container_stage_directory: str,
    selection: str,
    database_user: str | None,
    database_name: str | None,
) -> None:
    variables = contract.psql_variables(stage_directory=container_stage_directory)
    # docker exec does not attach stdin unless -i is set. Without it psql sees
    # EOF, returns success, and none of the validated SQL is actually applied.
    base = [docker, "exec", "-i", container, "psql", "-X", "-v", "ON_ERROR_STOP=1"]
    if database_user:
        base.extend(["-U", database_user])
    if database_name:
        base.extend(["-d", database_name])
    for name, value in variables.items():
        base.extend(["-v", f"{name}={value}"])
    for seed in _seed_paths(selection):
        subprocess.run(base, input=seed.read_bytes(), check=True)


def _validate_cache_key_prefix(value: str) -> str:
    if (
        not value
        or len(value) > 128
        or any(character.isspace() or ord(character) < 32 for character in value)
        or any(character in "*?[]" for character in value)
    ):
        raise RuntimeError("Cache key prefix is invalid")
    return value


def _validate_cache_execution(
    *,
    allow_empty_cache: bool,
    allow_skip_cache_invalidation: bool,
    cache_container: str | None,
    docker_container: str | None,
    execute: bool,
    selection: str,
) -> None:
    requires_cache = (
        execute and docker_container is not None and selection in {"incy", "both"}
    )
    if requires_cache and not cache_container and not allow_skip_cache_invalidation:
        raise RuntimeError(
            "Docker INCY seed requires --cache-container or an explicit "
            "--allow-skip-cache-invalidation override"
        )
    if allow_skip_cache_invalidation and cache_container:
        raise RuntimeError(
            "Cannot combine cache invalidation with --allow-skip-cache-invalidation"
        )
    if allow_empty_cache and not cache_container:
        raise RuntimeError("--allow-empty-template-cache requires --cache-container")
    if not cache_container:
        return
    if not execute or not docker_container:
        raise RuntimeError(
            "Cache invalidation requires --execute and --docker-container"
        )
    if selection == "main":
        raise RuntimeError("Cache invalidation requires the INCY seed")


def _invalidate_container_template_cache(
    *,
    docker: str,
    database_container: str,
    cache_container: str,
    cache_binary: str,
    cache_key_prefix: str,
    allow_empty_cache: bool,
    database_user: str | None,
    database_name: str | None,
) -> int:
    prefix = _validate_cache_key_prefix(cache_key_prefix)
    query = """
select uuid::text
from subscription_templates
where template_type = 'XRAY_JSON'
  and name in (
    'CyberVPN Premium Smart RU INCY',
    'CyberVPN Premium Smart RU INCY Failover Canary'
  )
order by name;
""".lstrip()
    command = [
        docker,
        "exec",
        "-i",
        database_container,
        "psql",
        "-X",
        "-At",
        "-v",
        "ON_ERROR_STOP=1",
    ]
    if database_user:
        command.extend(["-U", database_user])
    if database_name:
        command.extend(["-d", database_name])
    result = subprocess.run(
        command,
        input=query.encode(),
        stdout=subprocess.PIPE,
        check=True,
    )
    uuids = [
        line.strip() for line in result.stdout.decode().splitlines() if line.strip()
    ]
    if len(uuids) != len(INCY_TEMPLATE_NAMES):
        raise RuntimeError(
            "Expected both INCY subscription templates before cache invalidation"
        )
    try:
        normalized_uuids = [str(uuid.UUID(value)) for value in uuids]
    except ValueError as exc:
        raise RuntimeError("Subscription template UUID is invalid") from exc

    keys = [
        *(
            f"{prefix}subscription_template:{name}:XRAY_JSON"
            for name in INCY_TEMPLATE_NAMES
        ),
        *(f"{prefix}xray_json_template:{value}" for value in normalized_uuids),
    ]
    deleted = subprocess.run(
        [docker, "exec", cache_container, cache_binary, "--raw", "UNLINK", *keys],
        stdout=subprocess.PIPE,
        check=True,
    )
    try:
        deleted_count = int(deleted.stdout.decode().strip())
    except ValueError as exc:
        raise RuntimeError("Cache invalidation returned an invalid result") from exc
    if not 0 <= deleted_count <= len(keys):
        raise RuntimeError("Cache invalidation returned an impossible key count")
    if deleted_count == 0 and not allow_empty_cache:
        raise RuntimeError(
            "No template cache key was invalidated; verify the cache container, "
            "database and prefix or use --allow-empty-template-cache with an "
            "external generated-subscription freshness proof"
        )
    return deleted_count


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--stage-root",
        required=True,
        type=Path,
        help="Existing operator-owned directory without group/world write access",
    )
    parser.add_argument("--seed", choices=("main", "incy", "both"), default="both")
    parser.add_argument("--psql", default="psql")
    parser.add_argument(
        "--docker-container",
        help="Execute psql inside this PostgreSQL container and stage artifacts there",
    )
    parser.add_argument("--docker-binary", default="docker")
    parser.add_argument(
        "--container-stage-root",
        default="/var/lib/postgresql/cybervpn-seed-stage",
    )
    parser.add_argument("--container-stage-owner", default="postgres")
    parser.add_argument("--database-user")
    parser.add_argument("--database-name")
    parser.add_argument(
        "--cache-container",
        help="Invalidate exact Remnawave template cache keys after a successful Docker seed",
    )
    parser.add_argument("--cache-binary", default="valkey-cli")
    parser.add_argument("--cache-key-prefix", default="ioraw:")
    parser.add_argument(
        "--allow-empty-template-cache",
        action="store_true",
        help="Allow zero invalidated keys only when an external generated-body freshness proof will follow",
    )
    parser.add_argument(
        "--allow-skip-cache-invalidation",
        action="store_true",
        help="Emergency override for Docker INCY seed without cache refresh; requires external freshness proof",
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Run psql; without this flag only stage and validate artifacts",
    )
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    _validate_cache_execution(
        allow_empty_cache=args.allow_empty_template_cache,
        allow_skip_cache_invalidation=args.allow_skip_cache_invalidation,
        cache_container=args.cache_container,
        docker_container=args.docker_container,
        execute=args.execute,
        selection=args.seed,
    )
    contract = _stage_artifacts(args.stage_root)
    try:
        report = {
            "mode": "execute" if args.execute else "dry-run",
            "product": "premium_smart_ru",
            "seed": args.seed,
            "manifestSha256": contract.manifest_sha256,
            "artifactSha256": contract.artifact_sha256,
        }
        print(json.dumps(report, sort_keys=True))
        if args.execute:
            if args.docker_container:
                container_directory = _copy_stage_to_container(
                    contract,
                    docker=args.docker_binary,
                    container=args.docker_container,
                    container_stage_root=args.container_stage_root,
                    owner=args.container_stage_owner,
                )
                try:
                    _run_container_psql(
                        contract,
                        docker=args.docker_binary,
                        container=args.docker_container,
                        container_stage_directory=container_directory,
                        selection=args.seed,
                        database_user=args.database_user,
                        database_name=args.database_name,
                    )
                    if args.cache_container:
                        deleted = _invalidate_container_template_cache(
                            docker=args.docker_binary,
                            database_container=args.docker_container,
                            cache_container=args.cache_container,
                            cache_binary=args.cache_binary,
                            cache_key_prefix=args.cache_key_prefix,
                            allow_empty_cache=args.allow_empty_template_cache,
                            database_user=args.database_user,
                            database_name=args.database_name,
                        )
                        print(json.dumps({"invalidatedTemplateCacheKeys": deleted}))
                finally:
                    _remove_container_stage(
                        docker=args.docker_binary,
                        container=args.docker_container,
                        container_stage_root=args.container_stage_root,
                        directory=container_directory,
                    )
            else:
                subprocess.run(
                    _psql_command(contract, psql=args.psql, selection=args.seed),
                    check=True,
                )
    finally:
        _remove_stage(contract)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
