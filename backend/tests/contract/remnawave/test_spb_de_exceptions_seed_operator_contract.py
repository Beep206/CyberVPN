from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
SEED = REPO_ROOT / "scripts/remnawave/seed-cybervpn-spb-de-exceptions.sql"
OPERATOR = REPO_ROOT / "scripts/remnawave/apply-spb-de-exceptions-server-routing.py"


def test_spb_de_seed_and_operator_keep_customer_and_bridge_squads_separate() -> None:
    seed_sql = SEED.read_text(encoding="utf-8")
    operator_source = OPERATOR.read_text(encoding="utf-8")

    assert 'CUSTOMER_SQUAD_NAME = "CYBERVPN_SPB_DE_NODES"' in operator_source
    assert 'BRIDGE_SQUAD_NAME = "CYBERVPN_SPB_DE_BRIDGE"' in operator_source
    assert "CUSTOMER_SQUAD_NAME = BRIDGE_SQUAD_NAME" not in operator_source

    customer_name_position = seed_sql.index("'CYBERVPN_SPB_DE_NODES'")
    bridge_name_position = seed_sql.index("'CYBERVPN_SPB_DE_BRIDGE'")
    assert customer_name_position < bridge_name_position
    assert "customer_internal_squad_uuid" in seed_sql
    assert "bridge_internal_squad_uuid" in seed_sql
    assert "bridge_inbound_customer_cleanup" in seed_sql
    assert "where internal_squad_inbounds.internal_squad_uuid = v_customer_squad_uuid" in seed_sql
    assert "and config_profile_inbounds.tag = 'DE_SPB_EXCEPTIONS_BRIDGE_9444'" in seed_sql
    assert "Task2 customer squad must not contain the DE bridge inbound" in seed_sql
