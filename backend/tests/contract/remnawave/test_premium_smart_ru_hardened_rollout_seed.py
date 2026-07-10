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
DIAGNOSTIC_SQL = REPO_ROOT / "scripts/remnawave/diagnose-premium-smart-ru-inbounds.sql"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _extract_seed_template(sql: str) -> str:
    delimiter = "$cybervpn_premium_smart_ru_yaml$"
    first = sql.index(delimiter)
    second = sql.index(delimiter, first + len(delimiter))
    return sql[first + len(delimiter) : second].strip()


def _jsonb_literal(sql: str, marker: str) -> dict[str, object]:
    for match in re.finditer(r"'(?P<json>(?:[^']|'')*)'::jsonb", sql, re.DOTALL):
        raw_json = match.group("json")
        if marker in raw_json:
            try:
                return json.loads(raw_json)
            except json.JSONDecodeError:
                continue
    raise AssertionError(f"JSONB literal containing {marker!r} was not found")


def _compact(sql: str) -> str:
    return re.sub(r"\s+", " ", sql.strip())


def _validation_block(sql: str) -> str:
    start_marker = "do $premium_smart_ru_inbound_validation$"
    end_marker = "$premium_smart_ru_inbound_validation$;"
    start = sql.index(start_marker)
    end = sql.index(end_marker, start) + len(end_marker)
    return sql[start:end]


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
    assert "'🇩🇪 DE Frankfurt 01 25G Reality 443'" in seed_sql
    assert "'🇩🇪 DE Frankfurt 01 25G XHTTP Reality 8443'" in seed_sql
    assert "'🇳🇱 NL Amsterdam 01 10G Reality 443'" in seed_sql
    assert "'🇳🇱 NL Amsterdam 01 10G XHTTP Reality 8443'" in seed_sql
    assert "'🇷🇺 RU Moscow 01 25G Reality 443'" in seed_sql
    assert "'🇷🇺 RU Moscow 01 25G XHTTP Reality 8443'" in seed_sql
    assert "'🇷🇺 RU SPB 01 25G Reality 443'" in seed_sql
    assert "'🇷🇺 RU SPB 01 25G XHTTP Reality 8443'" in seed_sql
    assert "'de-3.cyber-vpn.org'" in seed_sql
    assert "'nl-4.cyber-vpn.org'" in seed_sql
    assert "'ru-msk-3.cyber-vpn.org'" in seed_sql
    assert "'ru-spb-3.cyber-vpn.org'" in seed_sql
    assert "where tag in ('VLESS_REALITY_443', 'VLESS_XHTTP_REALITY_8443')" in seed_sql
    assert "linked_node_inbounds" in seed_sql
    assert "smart_host_specs" in seed_sql
    assert "smart_host_node_links" in seed_sql
    assert "premium_host_exclusions" in seed_sql
    assert "internal_squad_host_exclusions" in seed_sql
    assert "host_tags.tag like 'PREMIUM\\_SMART\\_RU\\_%' escape '\\'" in seed_sql
    assert "Expected 8 Premium Smart RU Remnawave hosts" in seed_sql
    assert "Expected 8 Premium Smart RU host-to-node links" in seed_sql
    assert "Expected Premium Smart RU squad to exclude non-Smart-RU shared inbound hosts" in seed_sql
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


def test_premium_smart_ru_seed_validates_inbounds_before_transaction_and_mutations() -> None:
    seed_sql = _read(SEED_SQL)
    validation_start = seed_sql.index("do $premium_smart_ru_inbound_validation$")
    validation_end = seed_sql.index(
        "$premium_smart_ru_inbound_validation$;",
        validation_start,
    )
    transaction_begin = seed_sql.index("\nbegin;\n", validation_end)

    assert validation_start < transaction_begin
    assert transaction_begin < seed_sql.index("with template_upsert as")

    mutation_markers = [
        "insert into subscription_templates",
        "insert into external_squads",
        "insert into external_squads_templates",
        "insert into internal_squads",
        "insert into internal_squad_inbounds",
        "insert into config_profile_inbounds_to_nodes",
        "update hosts",
        "insert into hosts",
        "insert into hosts_to_nodes",
        "insert into internal_squad_host_exclusions",
        "update node_plugin",
        "insert into node_plugin",
        "update nodes",
    ]
    for marker in mutation_markers:
        assert validation_start < validation_end < transaction_begin < seed_sql.index(marker)


def test_premium_smart_ru_seed_requires_full_raw_tcp_reality_contract() -> None:
    validation = _compact(_validation_block(_read(SEED_SQL)))

    required_fragments = [
        "where tag = 'VLESS_REALITY_443'",
        "v_raw_count <> 1",
        "VLESS_REALITY_443 inbound must exist exactly once",
        "lower(coalesce(v_raw.type, '')) <> 'vless'",
        "VLESS_REALITY_443 must use type=vless",
        "lower(coalesce(v_raw.network, '')) not in ('raw', 'tcp')",
        "VLESS_REALITY_443 must use raw/tcp network",
        "lower(coalesce(v_raw.security, '')) <> 'reality'",
        "VLESS_REALITY_443 must use reality security",
        "v_raw.port <> 443",
        "VLESS_REALITY_443 must use port 443",
        "v_raw.raw_inbound #>> '{settings,decryption}'",
        "VLESS_REALITY_443 must use decryption=none",
        "v_raw.raw_inbound #>> '{settings,flow}'",
        "xtls-rprx-vision",
        "VLESS_REALITY_443 must use settings.flow=xtls-rprx-vision",
        "v_raw.raw_inbound #>> '{streamSettings,network}'",
        "VLESS_REALITY_443 streamSettings.network must be raw/tcp",
        "v_raw.raw_inbound #>> '{streamSettings,security}'",
        "VLESS_REALITY_443 streamSettings.security must be reality",
        "v_raw.raw_inbound #> '{streamSettings,realitySettings,serverNames}'",
        "jsonb_array_length(v_raw.raw_inbound #> '{streamSettings,realitySettings,serverNames}')",
        "VLESS_REALITY_443 serverNames is empty",
        "v_raw.raw_inbound #> '{streamSettings,realitySettings,shortIds}'",
        "jsonb_array_length(v_raw.raw_inbound #> '{streamSettings,realitySettings,shortIds}')",
        "VLESS_REALITY_443 shortIds is empty",
        "v_raw.raw_inbound #>> '{streamSettings,realitySettings,privateKey}'",
        "VLESS_REALITY_443 privateKey is empty",
        "v_raw.raw_inbound #>> '{streamSettings,realitySettings,target}'",
        "v_raw.raw_inbound #>> '{streamSettings,realitySettings,dest}'",
        "VLESS_REALITY_443 Reality target is empty",
        "right(btrim(v_raw_reality_target), 4) <> ':443'",
        "VLESS_REALITY_443 Reality target must end with :443",
        "v_raw.raw_inbound #>> '{sniffing,enabled}'",
        "VLESS_REALITY_443 sniffing must be enabled",
        "v_raw.raw_inbound #> '{sniffing,destOverride}'",
        "v_raw_dest_override ?& array['http', 'tls', 'quic']",
        "VLESS_REALITY_443 sniffing.destOverride must contain http, tls, and quic",
    ]
    for fragment in required_fragments:
        assert fragment in validation


def test_premium_smart_ru_seed_requires_and_preserves_xhttp_contract() -> None:
    seed_sql = _read(SEED_SQL)
    validation = _compact(_validation_block(seed_sql))

    required_fragments = [
        "where tag = 'VLESS_XHTTP_REALITY_8443'",
        "v_xhttp_count <> 1",
        "VLESS_XHTTP_REALITY_8443 inbound must exist exactly once",
        "lower(coalesce(v_xhttp.type, '')) <> 'vless'",
        "VLESS_XHTTP_REALITY_8443 must use type=vless",
        "lower(coalesce(v_xhttp.network, '')) <> 'xhttp'",
        "VLESS_XHTTP_REALITY_8443 must use network=xhttp",
        "lower(coalesce(v_xhttp.security, '')) <> 'reality'",
        "VLESS_XHTTP_REALITY_8443 must use reality security",
        "v_xhttp.port <> 8443",
        "VLESS_XHTTP_REALITY_8443 must use port 8443",
    ]
    for fragment in required_fragments:
        assert fragment in validation

    for pattern in (
        r"\binsert\s+into\s+config_profile_inbounds\b",
        r"\bupdate\s+config_profile_inbounds\b",
        r"\bdelete\s+from\s+config_profile_inbounds\b",
    ):
        assert re.search(pattern, seed_sql, flags=re.IGNORECASE) is None


def test_premium_smart_ru_inbound_diagnostic_sql_is_safe_and_contract_focused() -> None:
    assert DIAGNOSTIC_SQL.is_file()

    diagnostic_sql = _read(DIAGNOSTIC_SQL)
    diagnostic_compact = _compact(diagnostic_sql)
    select_output = diagnostic_compact[diagnostic_compact.lower().index("select ") :]

    required_fragments = [
        "cpi.tag",
        "cpi.type",
        "cpi.network",
        "cpi.security",
        "cpi.port",
        "tag_row_count",
        "as decryption",
        "as settings_flow_is_xtls_rprx_vision",
        "as stream_network",
        "as stream_security",
        "as server_names_count",
        "as short_ids_count",
        "as reality_private_key_present",
        "as reality_target_present",
        "as reality_target_ends_443",
        "as sniffing_enabled",
        "as dest_override_has_http",
        "as dest_override_has_tls",
        "as dest_override_has_quic",
        "'VLESS_REALITY_443'",
        "'VLESS_XHTTP_REALITY_8443'",
    ]
    for fragment in required_fragments:
        assert fragment in diagnostic_sql

    forbidden_output_patterns = [
        r"\bcpi\.raw_inbound\b\s*(?:,|as\b)",
        r"#>?>\s+'\{streamSettings,realitySettings,serverNames\}'\s+as\b",
        r"#>?>\s+'\{streamSettings,realitySettings,shortIds\}'\s+as\b",
        r"#>?>\s+'\{streamSettings,realitySettings,privateKey\}'\s+as\b",
        r"#>?>\s+'\{streamSettings,realitySettings,target\}'\s+as\b",
        r"#>?>\s+'\{streamSettings,realitySettings,dest\}'\s+as\b",
        r"\bprofile_uuid\b",
        r"\bpublicKey\b",
        r"\bsni\b\s*(?:,|as\b)",
    ]
    for pattern in forbidden_output_patterns:
        assert re.search(pattern, select_output, flags=re.IGNORECASE) is None
