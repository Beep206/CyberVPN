"""Remove legacy webhook fingerprints in resumable batches before cutover.

The default mode is read-only. ``--apply`` requires the exact fingerprint from
an immediately preceding dry run. Every write batch is committed separately,
so an interruption can be resumed without one unbounded WAL/lock transaction.
No webhook identifiers or payload values are printed.
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import importlib.util
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

_MIGRATION_PATH = PROJECT_ROOT / "alembic" / "versions" / "20260830_webhook_hmac_cleanup.py"
_TARGET_SCHEMA = "webhook_log.redacted.v2"
_DEFAULT_BATCH_SIZE = 500
_MAX_BATCH_SIZE = 1_000


class _Sanitizer(Protocol):
    def __call__(
        self,
        value: Any,
        *,
        signature_fingerprint_present: bool,
    ) -> dict[str, Any]: ...


@dataclass(frozen=True)
class CleanupSnapshot:
    candidate_count: int
    upper_bound: Any | None
    fingerprint: str


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true", help="Commit bounded cleanup batches")
    parser.add_argument(
        "--expected-fingerprint",
        help="Required with --apply; copied from the immediately preceding dry run",
    )
    parser.add_argument("--batch-size", type=int, default=_DEFAULT_BATCH_SIZE)
    args = parser.parse_args()
    if args.apply and not args.expected_fingerprint:
        parser.error("--apply requires --expected-fingerprint")
    if not 1 <= args.batch_size <= _MAX_BATCH_SIZE:
        parser.error(f"--batch-size must be between 1 and {_MAX_BATCH_SIZE}")
    return args


def _candidate_filter(webhook_log: Any) -> sa.ColumnElement[bool]:
    schema_value = webhook_log.payload["schema"].as_string()
    return sa.or_(
        webhook_log.signature_fingerprint.is_not(None),
        sa.func.coalesce(schema_value, "") != _TARGET_SCHEMA,
    )


def _load_sanitizer() -> _Sanitizer:
    spec = importlib.util.spec_from_file_location("webhook_hmac_cleanup", _MIGRATION_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError("Webhook cleanup migration could not be loaded")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module._sanitize_payload


async def build_snapshot(session: AsyncSession, *, page_size: int = _DEFAULT_BATCH_SIZE) -> CleanupSnapshot:
    """Fingerprint candidate primary keys using bounded, read-only pages."""

    from src.infrastructure.database.models.webhook_log_model import WebhookLog

    digest = hashlib.sha256(b"cybervpn/webhook-log-cleanup-snapshot/v1\x00")
    count = 0
    last_id: Any | None = None
    upper_bound: Any | None = None
    while True:
        statement = (
            sa.select(WebhookLog.id).where(_candidate_filter(WebhookLog)).order_by(WebhookLog.id).limit(page_size)
        )
        if last_id is not None:
            statement = statement.where(WebhookLog.id > last_id)
        result = await session.execute(statement)
        identifiers = list(result.scalars().all())
        if not identifiers:
            break
        for identifier in identifiers:
            digest.update(str(identifier).encode("ascii"))
            digest.update(b"\x00")
        count += len(identifiers)
        last_id = identifiers[-1]
        upper_bound = last_id
    digest.update(str(count).encode("ascii"))
    return CleanupSnapshot(candidate_count=count, upper_bound=upper_bound, fingerprint=digest.hexdigest())


async def cleanup_in_batches(
    session: AsyncSession,
    *,
    upper_bound: Any,
    batch_size: int,
    sanitizer: _Sanitizer,
) -> int:
    """Commit one locked, bounded candidate page at a time."""

    from src.infrastructure.database.models.webhook_log_model import WebhookLog

    processed = 0
    while True:
        statement = (
            sa.select(WebhookLog)
            .where(
                _candidate_filter(WebhookLog),
                WebhookLog.id <= upper_bound,
            )
            .order_by(WebhookLog.id)
            .limit(batch_size)
            .with_for_update(skip_locked=True)
        )
        try:
            result = await session.execute(statement)
            rows = list(result.scalars().all())
            if not rows:
                await session.rollback()
                break
            for row in rows:
                row.payload = sanitizer(
                    row.payload,
                    signature_fingerprint_present=row.signature_fingerprint is not None,
                )
                row.signature_fingerprint = None
            await session.commit()
            processed += len(rows)
        except Exception:
            await session.rollback()
            raise
    return processed


async def _run(*, apply: bool, expected_fingerprint: str | None, batch_size: int) -> int:
    from src.infrastructure.database.session import AsyncSessionLocal, engine

    try:
        async with AsyncSessionLocal() as session:
            snapshot = await build_snapshot(session, page_size=batch_size)
            if not apply:
                print(
                    json.dumps(
                        {
                            "applied": False,
                            "candidate_count": snapshot.candidate_count,
                            "fingerprint": snapshot.fingerprint,
                            "ready_for_alembic": snapshot.candidate_count == 0,
                        },
                        indent=2,
                        sort_keys=True,
                    )
                )
                return 0

            if snapshot.fingerprint != expected_fingerprint:
                print("Cleanup snapshot changed; refusing to apply", file=sys.stderr)
                return 3
            if snapshot.upper_bound is None:
                processed = 0
            else:
                processed = await cleanup_in_batches(
                    session,
                    upper_bound=snapshot.upper_bound,
                    batch_size=batch_size,
                    sanitizer=_load_sanitizer(),
                )
            remaining = await build_snapshot(session, page_size=batch_size)
            print(
                json.dumps(
                    {
                        "applied": True,
                        "processed": processed,
                        "remaining_candidates": remaining.candidate_count,
                        "ready_for_alembic": remaining.candidate_count == 0,
                    },
                    indent=2,
                    sort_keys=True,
                )
            )
            return 0 if remaining.candidate_count == 0 else 4
    finally:
        await engine.dispose()


def main() -> int:
    args = _parse_args()
    return asyncio.run(
        _run(
            apply=args.apply,
            expected_fingerprint=args.expected_fingerprint,
            batch_size=args.batch_size,
        )
    )


if __name__ == "__main__":
    raise SystemExit(main())
