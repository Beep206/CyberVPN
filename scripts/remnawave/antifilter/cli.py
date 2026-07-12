from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

from .compiler import compile_routes
from .models import RouteCompilerError, load_policy, parse_utc_timestamp
from .publish import (
    approve_candidate,
    promote_active,
    publish_candidate,
    record_failure,
    rollback_to_lkg,
)


def _timestamp(value: str | None) -> datetime:
    return (
        datetime.now(UTC) if value is None else parse_utc_timestamp(value, "timestamp")
    )


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Offline Antifilter route compiler and versioned publisher"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    compile_parser = subparsers.add_parser(
        "compile", help="compile an immutable candidate"
    )
    compile_parser.add_argument("--source", required=True, type=Path)
    compile_parser.add_argument("--policy", required=True, type=Path)
    compile_parser.add_argument("--output", required=True, type=Path)
    compile_parser.add_argument("--previous", type=Path)
    compile_parser.add_argument(
        "--state",
        type=Path,
        help="optional external state root for safe failure records",
    )
    compile_parser.add_argument("--now", help="controlled RFC3339 UTC freshness clock")

    approve_parser = subparsers.add_parser(
        "approve", help="record a checksum-bound suspicious-delta approval"
    )
    approve_parser.add_argument("--candidate", required=True, type=Path)
    approve_parser.add_argument("--output", required=True, type=Path)
    approve_parser.add_argument("--approved-by", required=True)
    approve_parser.add_argument("--ticket", required=True)
    approve_parser.add_argument("--approved-at")

    publish_parser = subparsers.add_parser(
        "publish", help="atomically publish an immutable candidate"
    )
    publish_parser.add_argument("--candidate", required=True, type=Path)
    publish_parser.add_argument("--store", required=True, type=Path)
    publish_parser.add_argument("--policy", required=True, type=Path)
    publish_parser.add_argument("--approval", type=Path)

    promote_parser = subparsers.add_parser(
        "promote", help="promote active after an external post-check"
    )
    promote_parser.add_argument("--store", required=True, type=Path)
    rollback_parser = subparsers.add_parser(
        "rollback", help="atomically restore last-known-good"
    )
    rollback_parser.add_argument("--store", required=True, type=Path)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        if args.command == "compile":
            now = _timestamp(args.now)
            try:
                manifest = compile_routes(
                    args.source,
                    load_policy(args.policy),
                    args.output,
                    now=now,
                    previous_dir=args.previous,
                )
            except RouteCompilerError as exc:
                if args.state is not None:
                    source_sha256 = None
                    try:
                        source_sha256 = hashlib.sha256(
                            args.source.read_bytes()
                        ).hexdigest()
                    except OSError:
                        pass
                    record_failure(
                        args.state,
                        reason=str(exc),
                        source_sha256=source_sha256,
                        failed_at=now,
                    )
                raise
            print(
                json.dumps(
                    {
                        "candidateStatus": manifest["safety"]["status"],
                        "version": manifest["version"],
                    }
                )
            )
            return 2 if manifest["safety"]["status"] == "approval_required" else 0
        if args.command == "approve":
            result = approve_candidate(
                args.candidate,
                args.output,
                approved_by=args.approved_by,
                ticket=args.ticket,
                approved_at=_timestamp(args.approved_at),
            )
        elif args.command == "publish":
            result = publish_candidate(
                args.candidate,
                args.store,
                policy=load_policy(args.policy),
                approval_path=args.approval,
            )
        elif args.command == "promote":
            result = promote_active(args.store)
        else:
            result = rollback_to_lkg(args.store)
        print(json.dumps(result, sort_keys=True))
        return 0
    except RouteCompilerError as exc:
        print(
            json.dumps({"status": "rejected", "reason": str(exc)}, sort_keys=True),
            file=sys.stderr,
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
