"""Dry-run/apply the fail-closed Remnawave 2.8 numeric-id reconciliation.

Default execution is read-only. Applying requires the exact fingerprint from a
successful dry run so inventory drift cannot silently cross the cutover gate.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true", help="Persist mappings after a verified dry run")
    parser.add_argument(
        "--expected-fingerprint",
        help="Required with --apply; must equal the immediately preceding dry-run fingerprint",
    )
    args = parser.parse_args()
    if args.apply and not args.expected_fingerprint:
        parser.error("--apply requires --expected-fingerprint")
    return args


async def _run(*, apply: bool, expected_fingerprint: str | None) -> int:
    from src.application.services.remnawave_identity_reconciliation import (
        ReconcileRemnawaveIdentitiesService,
        RemnawaveCutoverBlocked,
    )
    from src.infrastructure.database.session import AsyncSessionLocal
    from src.infrastructure.remnawave.client import RemnawaveClient
    from src.infrastructure.remnawave.user_gateway import RemnawaveUserGateway

    client = RemnawaveClient()
    try:
        async with AsyncSessionLocal() as session:
            service = ReconcileRemnawaveIdentitiesService(session, RemnawaveUserGateway(client))
            try:
                plan = await service.execute(apply=False)
            except RemnawaveCutoverBlocked as exc:
                print(
                    json.dumps(
                        {
                            "ready_for_cutover": False,
                            "upstream_count": exc.plan.upstream_count,
                            "mapping_count": len(exc.plan.mappings),
                            "fingerprint": exc.plan.fingerprint,
                            "issues": [
                                {
                                    "code": issue.code,
                                    "subject_type": issue.subject_type,
                                    "subject_id": str(issue.subject_id) if issue.subject_id else None,
                                    "detail": issue.detail,
                                }
                                for issue in exc.plan.issues
                            ],
                        },
                        indent=2,
                        sort_keys=True,
                    )
                )
                return 2

            if apply:
                if plan.fingerprint != expected_fingerprint:
                    print("Inventory fingerprint changed; refusing to apply", file=sys.stderr)
                    return 3
                plan = await service.execute(apply=True)
                if plan.fingerprint != expected_fingerprint:
                    await session.rollback()
                    print("Inventory changed during apply; transaction rolled back", file=sys.stderr)
                    return 3
                await session.commit()

            print(
                json.dumps(
                    {
                        "ready_for_cutover": plan.ready_for_cutover,
                        "applied": apply,
                        "upstream_count": plan.upstream_count,
                        "mapping_count": len(plan.mappings),
                        "fingerprint": plan.fingerprint,
                        "issues": [],
                    },
                    indent=2,
                    sort_keys=True,
                )
            )
            return 0
    finally:
        await client.close()


def main() -> int:
    args = _parse_args()
    return asyncio.run(_run(apply=args.apply, expected_fingerprint=args.expected_fingerprint))


if __name__ == "__main__":
    raise SystemExit(main())
