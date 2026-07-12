from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
SEED = REPO_ROOT / "scripts/deploy/upsert-dual-product-invites.sql"


def test_dual_product_invite_seed_is_explicit_idempotent_and_fail_closed() -> None:
    sql = SEED.read_text(encoding="utf-8")

    assert "pg_advisory_xact_lock" in sql
    assert "for update" in sql.lower()
    assert "jsonb_populate_record(null::invite_codes" in sql
    assert "on conflict" not in sql.lower()
    for variable in (
        "legacy_invite_code",
        "task1_invite_code",
        "task2_invite_code",
    ):
        assert f":{{?{variable}}}" in sql
        assert f":'{variable}'" in sql
        assert f"cybervpn.rollout.{variable}" in sql

    assert "\\quit 3" in sql
    assert "premium_smart_ru" in sql
    assert "premium_spb_de_exceptions" in sql
    assert "grant_duration_mode', 'lifetime'" in sql
    assert "grant_device_limit_override', 5" in sql
    assert "per_user_redemption_cap', 1" in sql
    assert "max_redemptions', 100000" in sql
    assert "require_no_active_access" in sql
    assert "block_self_redemption" in sql
    assert "status = 'revoked'" in sql
    assert "where code = v_legacy_code" in sql
    assert "select i.code" not in sql.lower()
    assert "end as invite_role" in sql.lower()
    assert "commit;" in sql.lower()
