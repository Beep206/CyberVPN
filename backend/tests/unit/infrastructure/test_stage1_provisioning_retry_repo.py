"""Stage 1 provisioning retry repository contract checks."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy.dialects import postgresql

from src.infrastructure.database.repositories.stage1_provisioning_retry_repo import build_claim_due_jobs_statement


def test_claim_due_jobs_statement_uses_skip_locked_row_locks() -> None:
    stmt = build_claim_due_jobs_statement(now=datetime(2026, 5, 30, 12, tzinfo=UTC), limit=25)

    compiled = str(stmt.compile(dialect=postgresql.dialect()))

    assert "FOR UPDATE SKIP LOCKED" in compiled
    assert "stage1_provisioning_retry_jobs.state IN" in compiled
    assert "stage1_provisioning_retry_jobs.next_attempt_at <=" in compiled
