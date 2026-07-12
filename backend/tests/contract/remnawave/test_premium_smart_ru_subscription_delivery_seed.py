from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
SEED = REPO_ROOT / "scripts/remnawave/seed-cybervpn-premium-smart-ru-incy-xray.sql"


def test_smart_ru_response_rules_require_trusted_product_and_client_family() -> None:
    sql = SEED.read_text(encoding="utf-8")

    for rule_name, family, response_type in (
        ("Mihomo Premium Smart RU", "mihomo", "MIHOMO"),
        ("HAPP Premium Smart RU Failover Canary", "happ", "XRAY_JSON"),
        ("INCY Premium Smart RU Failover Canary", "incy", "XRAY_JSON"),
        ("HAPP Premium Smart RU", "happ", "XRAY_JSON"),
        ("INCY Premium Smart RU", "incy", "XRAY_JSON"),
    ):
        assert sql.count(f"'name', '{rule_name}'") == 1
        rule = sql.split(f"'name', '{rule_name}'", 1)[1].split("'responseType'", 1)[0]
        assert "'headerName', 'x-cybervpn-product'" in rule
        assert "'value', 'premium_smart_ru'" in rule
        assert "'headerName', 'x-cybervpn-client-family'" in rule
        assert f"'value', '{family}'" in rule
        assert f"'responseType', '{response_type}'" in sql.split(f"'name', '{rule_name}'", 1)[1]

    assert "'headerName', 'user-agent'" not in sql
    for rule_name in (
        "HAPP Premium Smart RU Failover Canary",
        "INCY Premium Smart RU Failover Canary",
    ):
        rule = sql.split(f"'name', '{rule_name}'", 1)[1].split("'responseType'", 1)[0]
        assert "'headerName', 'x-cybervpn-xray-failover-canary'" in rule
        assert "'value', '1'" in rule


def test_smart_ru_response_rule_order_preserves_browser_and_base64_fallback() -> None:
    sql = SEED.read_text(encoding="utf-8")
    rebuild = sql.split("rebuilt_rules as (", 1)[1].split(")\nupdate subscription_settings", 1)[0]

    browser_position = rebuild.index("value->>'responseType' = 'BROWSER'")
    product_rules_position = rebuild.index("|| new_rules.rules")
    generic_position = rebuild.index("value->>'responseType' not in ('BROWSER', 'XRAY_BASE64')")
    fallback_position = rebuild.index("value->>'responseType' = 'XRAY_BASE64'")

    assert browser_position < product_rules_position < generic_position < fallback_position
    assert "v_mihomo_rule_position >= v_happ_canary_rule_position" in sql
    assert "v_happ_canary_rule_position >= v_incy_canary_rule_position" in sql
    assert "v_incy_canary_rule_position >= v_happ_rule_position" in sql
    assert "v_happ_rule_position >= v_incy_rule_position" in sql
    assert "v_incy_rule_position >= v_fallback_rule_position" in sql
    assert sql.count("'key', 'X-CyberVPN-Profile'") == 4
    assert sql.count("'value', 'premium_smart_ru_xray'") == 2
    assert sql.count("'value', 'premium_smart_ru_xray_failover_canary'") == 2
    assert sql.count("'applyHeadersToEnd', true") == 4


def test_legacy_routing_header_is_loaded_from_compiler_artifact() -> None:
    sql = SEED.read_text(encoding="utf-8")

    assert "/tmp/cybervpn-premium-smart-ru" not in sql  # noqa: S108
    assert "pg_read_binary_file(v_contract.stage_dir || '/manifest.json')" in sql
    assert "pg_read_binary_file(v_contract.stage_dir || '/incy-xray.json')" in sql
    assert "v_contract.stage_dir || '/incy-xray-failover-canary.json'" in sql
    assert "v_contract.stage_dir || '/legacy-routing-header.json'" in sql
    assert "encode(sha256(v_manifest_bytes), 'hex') <> v_contract.stage_manifest_sha256" in sql
    assert "encode(sha256(v_incy_bytes), 'hex') <> v_contract.incy_sha256" in sql
    assert "encode(sha256(v_incy_canary_bytes), 'hex') <> v_contract.incy_canary_sha256" in sql
    assert "encode(sha256(v_legacy_header_bytes), 'hex') <> v_contract.legacy_header_sha256" in sql
    assert "v_manifest#>>'{artifacts,mihomo.yaml,sha256}' is distinct from v_contract.mihomo_sha256" in sql
    assert "v_manifest#>>'{artifacts,incy-xray.json,sha256}' is distinct from v_contract.incy_sha256" in sql
    assert "v_manifest#>>'{artifacts,incy-xray-failover-canary.json,sha256}'" in sql
    assert "select incy_template from cybervpn_premium_smart_ru_artifact_contract" in sql
    assert "select incy_canary_template from cybervpn_premium_smart_ru_artifact_contract" in sql
    assert "select legacy_header->>'value'" in sql
    assert "convert_from(decode(v_legacy_value, 'base64'), 'UTF8')::jsonb" in sql
    assert "v_legacy_header->'decoded' is distinct from v_legacy_decoded" in sql
    assert "v_contract.stage_dir ~ '^/(tmp|var/tmp)(/|$)'" in sql
    assert "remnawave-legacy-routing-header" in sql
    assert "base64-json" in sql
    assert "eyJOYW1lIjoiQ3liZXJWUE4gUHJlbWl1bSBTbWFydCBSVSI" not in sql


def test_incy_template_is_semantically_validated_before_first_mutation() -> None:
    sql = SEED.read_text(encoding="utf-8")
    preflight = sql.index("do $cybervpn_premium_smart_ru_incy_artifact_preflight$")
    first_mutation = sql.index("insert into subscription_templates")

    assert preflight < first_mutation
    assert "v_incy#>>'{remnawave,routePolicy,product}' is distinct from 'premium_smart_ru'" in sql
    assert "jsonb_array_length(v_incy#>'{remnawave,injectHosts}') <> 4" in sql
    assert "jsonb_array_length(v_incy->'inbounds') <> 2" in sql
    assert "jsonb_array_length(v_incy#>'{routing,rules}') = 0" in sql
    assert "v_incy#>'{routing,balancers}' is not null" in sql
    assert "v_incy->'observatory' is not null" in sql
    assert "rule->>'ruleTag' = 'route_final_eu'" in sql
    assert "rule->>'outboundTag' = 'eu-de-2'" in sql
    assert "rule->>'ruleTag' = 'route_ru_services'" in sql
    assert "rule->>'outboundTag' = 'ru-spb-2'" in sql
    assert "rule->>'ruleTag' = 'block_smtp_abuse'" in sql
    assert "rule->>'port' = '25,465,587'" in sql
    assert "rule->>'outboundTag' = 'block'" in sql
    assert "v_incy_canary#>>'{remnawave,routePolicy,rendererMode}'" in sql
    assert "is distinct from 'automatic-failover-canary'" in sql
    assert "jsonb_array_length(v_incy_canary#>'{routing,balancers}') <> 4" in sql
    assert "rule->>'balancerTag' = 'eu-primary'" in sql
    assert "rule->>'balancerTag' = 'ru-primary'" in sql
    assert "where balancer->>'fallbackTag' = 'direct'" in sql
    assert '"tag":"eu-primary","selector":["eu-de-2"]' in sql
    assert '"tag":"eu-fallback","selector":["eu-nl-2"]' in sql
    assert '"tag":"ru-primary","selector":["ru-spb-2"]' in sql
    assert '"tag":"ru-fallback","selector":["ru-msk-2"]' in sql
    assert '"subjectSelector":["eu-de-2","eu-nl-2","ru-spb-2","ru-msk-2"]' in sql
    assert "v_incy_canary#>'{routing,rules,0}' is distinct from" in sql
    assert "v_incy_canary#>'{routing,rules,1}' is distinct from" in sql


def test_incy_injected_hosts_pin_bootstrap_addresses_without_changing_reality_sni() -> None:
    sql = SEED.read_text(encoding="utf-8")
    insert_start = sql.index("insert into hosts (")
    insert_end = sql.index("from incy_host_specs specs", insert_start)
    clean_insert = sql[insert_start:insert_end]

    assert "target_address text" in sql
    assert "address = coalesce(specs.target_address, source_host.address)" in sql
    assert "specs.target_remark,\n    coalesce(specs.target_address, source_host.address)," in clean_insert
    assert "v_wrong_bootstrap_count <> 0" in sql
    assert "v_invalid_target_count <> 0" in sql
    assert "having count(target_host.uuid) <> 1" in sql
    assert "target_host.address is distinct from specs.target_address" in sql
    assert sql.count("'138.16.140.44'") == 4
    assert sql.count("'193.233.91.99'") == 4
    assert "sni = source_host.sni" in sql
    assert "override_sni_from_address = source_host.override_sni_from_address" in sql


def test_incy_seed_requires_one_enabled_source_and_one_external_squad() -> None:
    sql = SEED.read_text(encoding="utf-8")
    source_preflight = sql.split("do $cybervpn_incy_preflight$", 1)[1].split("$cybervpn_incy_preflight$;", 1)[0]
    host_update = sql.split("update hosts target_host", 1)[1].split("insert into hosts (", 1)[0]
    host_insert = sql.split("insert into hosts (", 1)[1].split("delete from hosts_to_nodes", 1)[0]
    node_link_copy = sql.split("insert into hosts_to_nodes", 1)[1].split("update hosts source_host", 1)[0]
    source_exclusion = sql.split("update hosts source_host", 1)[1].split("with new_rules as (", 1)[0]
    external_squad_update = sql.split("do $cybervpn_incy_external_squad_update$", 1)[1].split(
        "$cybervpn_incy_external_squad_update$;", 1
    )[0]

    assert "select distinct source_tag\n            from incy_host_specs" in source_preflight
    assert "and source_host.is_disabled = false" in source_preflight
    assert "having count(source_host.uuid) <> 1" in source_preflight
    assert "and source_host.is_disabled = false" in host_update
    assert "and source_host.is_disabled = false" in host_insert
    assert "and source_host.is_disabled = false" in node_link_copy
    assert "and source_host.is_disabled = false" in source_exclusion
    assert "update external_squads" in external_squad_update
    assert "get diagnostics v_updated_external_squad_count = row_count" in external_squad_update
    assert "if v_updated_external_squad_count <> 1" in external_squad_update
