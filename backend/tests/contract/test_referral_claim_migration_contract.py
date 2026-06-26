"""Referral attribution claim migration contract tests."""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest
import sqlalchemy as sa


def _load_migration():
    migration_path = Path(__file__).resolve().parents[2] / "alembic" / "versions" / "20260625_referral_claim_unique.py"
    spec = importlib.util.spec_from_file_location("referral_claim_unique_migration", migration_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_referral_claim_unique_migration_blocks_duplicate_claimed_users() -> None:
    migration = _load_migration()
    engine = sa.create_engine("sqlite:///:memory:")
    with engine.begin() as conn:
        conn.execute(
            sa.text(
                """
                CREATE TABLE referral_attribution_sessions (
                    id TEXT PRIMARY KEY,
                    claimed_by_user_id TEXT NULL
                )
                """
            )
        )
        conn.execute(
            sa.text(
                """
                INSERT INTO referral_attribution_sessions (id, claimed_by_user_id)
                VALUES
                    ('session-1', 'user-1'),
                    ('session-2', 'user-1'),
                    ('session-3', NULL),
                    ('session-4', NULL)
                """
            )
        )

        with pytest.raises(RuntimeError, match="multiple claimed referral attribution sessions"):
            migration._assert_no_duplicate_claimed_users(conn)

        conn.execute(sa.text("DELETE FROM referral_attribution_sessions WHERE id = 'session-2'"))
        migration._assert_no_duplicate_claimed_users(conn)
