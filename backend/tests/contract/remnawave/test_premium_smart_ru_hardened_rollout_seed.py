from __future__ import annotations

import json
import re
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[4]
PLAN_TEMPLATE = REPO_ROOT / "docs/plans/cybervpn-premium-smart-ru-de-primary-hardened.yaml"
CANONICAL_TEMPLATE = REPO_ROOT / "scripts/remnawave/templates/cybervpn-premium-smart-ru.yaml"
HARDENED_TEMPLATE = REPO_ROOT / "scripts/remnawave/templates/cybervpn-premium-smart-ru-de-primary-hardened.yaml"
SEED_SQL = REPO_ROOT / "scripts/remnawave/seed-cybervpn-premium-smart-ru.sql"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _extract_seed_template(sql: str) -> str:
    delimiter = "$cybervpn_premium_smart_ru_yaml$"
    first = sql.index(delimiter)
    second = sql.index(delimiter, first + len(delimiter))
    return sql[first + len(delimiter) : second].strip()


def _jsonb_literal(sql: str, marker: str) -> dict[str, object]:
    for match in re.finditer(r"'(?P<json>\{.*?\})'::jsonb", sql, re.DOTALL):
        raw_json = match.group("json")
        if marker in raw_json:
            return json.loads(raw_json)
    raise AssertionError(f"JSONB literal containing {marker!r} was not found")


def test_premium_smart_ru_hardened_templates_are_canonical_and_parseable() -> None:
    plan_text = _read(PLAN_TEMPLATE).strip()
    canonical_text = _read(CANONICAL_TEMPLATE).strip()
    hardened_text = _read(HARDENED_TEMPLATE).strip()

    assert canonical_text == plan_text
    assert hardened_text == plan_text

    data = yaml.safe_load(canonical_text)
    assert data["bind-address"] == "127.0.0.1"
    assert len(data["proxy-groups"]) == 20
    assert len(data["rule-providers"]) == 39
    assert len(data["rules"]) == 59
    assert data["rules"][-1] == "MATCH,🌍 World / EU"

    torrent_group = next(group for group in data["proxy-groups"] if group["name"] == "🧲 Torrents")
    assert torrent_group["proxies"] == ["REJECT"]

    dns_policy = data["dns"]["nameserver-policy"]
    assert dns_policy["rule-set:oisd_big,ads-all,win-spy,tor-inline"] == ["rcode://name_error"]

    for group_name in ("🇩🇪 DE Auto", "🇳🇱 NL Auto", "⚡ RU Auto", "🇷🇺 Moscow Auto", "🇷🇺 SPB Auto"):
        group = next(item for item in data["proxy-groups"] if item["name"] == group_name)
        assert group["include-all"] is True
        assert group["remnawave"]["include-proxies"] is False
        assert "filter" in group
        assert "exclude-filter" in group


def test_premium_smart_ru_seed_embeds_hardened_template_and_rollout_settings() -> None:
    seed_sql = _read(SEED_SQL)
    canonical_text = _read(CANONICAL_TEMPLATE).strip()

    assert _extract_seed_template(seed_sql) == canonical_text
    assert "template_type = 'MIHOMO'" in seed_sql
    assert "name = 'CyberVPN Premium Smart RU'" in seed_sql
    assert "view_position = 202" in seed_sql
    assert "('🇩🇪 DE Frankfurt 01 25G')" in seed_sql
    assert "('🇳🇱 NL Amsterdam 01 10G')" in seed_sql
    assert "('🇷🇺 RU Moscow 01 25G')" in seed_sql
    assert "('🇷🇺 RU SPB 01 25G')" in seed_sql
    assert "where tag in ('VLESS_REALITY_443', 'VLESS_XHTTP_REALITY_8443')" in seed_sql
    assert "linked_node_inbounds" in seed_sql
    assert "nodes.active_plugin_uuid is null" in seed_sql
    assert "or nodes.active_plugin_uuid = plugin_row.uuid" in seed_sql
    assert "Refusing to overwrite existing active plugin on Premium Smart RU nodes" in seed_sql
    assert "Expected plugin_assigned_node_count=4" in seed_sql
    assert seed_sql.index("do $cybervpn_premium_smart_ru_validation$") < seed_sql.index("commit;")

    subscription_settings = _jsonb_literal(seed_sql, '"profileTitle": "CyberVPN Premium Smart RU"')
    assert subscription_settings["profileTitle"] == "CyberVPN Premium Smart RU"
    assert subscription_settings["supportLink"] == "https://cyber-vpn.org/support"
    assert subscription_settings["profileUpdateInterval"] == 24
    assert subscription_settings["isProfileWebpageUrlEnabled"] is True
    assert "Torrent запрещён" in str(subscription_settings["happAnnounce"])

    response_headers = _jsonb_literal(seed_sql, '"x-cybervpn-plan": "premium_smart_ru"')
    assert response_headers == {
        "x-cybervpn-plan": "premium_smart_ru",
        "x-cybervpn-routing": "de-primary-ru-smart",
        "x-cybervpn-unlimited": "true",
    }

    plugin_config = _jsonb_literal(seed_sql, '"ingressFilter": {"enabled": false')
    assert plugin_config["egressFilter"] == {
        "enabled": True,
        "blockedIps": ["ext:tor-exit-nodes", "ext:tor-relays"],
        "blockedPorts": [25, 465, 587],
    }
    assert plugin_config["torrentBlocker"] == {
        "enabled": True,
        "ignoreLists": {"ip": [], "userId": []},
        "blockDuration": 86400,
    }
