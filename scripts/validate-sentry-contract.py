#!/usr/bin/env python3
"""Validate the resolved Sentry runtime contract for a surface.

This script is intentionally dependency-free so it can run in any CI job.
It validates environment / release / DSN presence and can append a short
summary to ``GITHUB_STEP_SUMMARY`` when that file is available.
"""

from __future__ import annotations

import argparse
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse


@dataclass(frozen=True)
class ContractSnapshot:
    surface: str
    environment: str
    release: str
    dsn: str

    @property
    def dsn_configured(self) -> bool:
        return bool(self.dsn.strip())


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--surface", required=True, help="Runtime surface name")
    parser.add_argument(
        "--environment-var",
        default="ENVIRONMENT",
        help="Environment variable that stores the resolved Sentry environment",
    )
    parser.add_argument(
        "--release-var",
        default="SENTRY_RELEASE",
        help="Environment variable that stores the resolved Sentry release",
    )
    parser.add_argument(
        "--dsn-var",
        default="SENTRY_DSN",
        help="Environment variable that stores the Sentry DSN",
    )
    parser.add_argument(
        "--expected-environment",
        help="Fail if the resolved environment differs from this value",
    )
    parser.add_argument(
        "--expected-release",
        help="Fail if the resolved release differs from this value",
    )
    parser.add_argument(
        "--expected-release-prefix",
        help="Fail if the resolved release does not start with this prefix",
    )
    parser.add_argument(
        "--require-dsn",
        action="store_true",
        help="Fail if the DSN is empty or malformed",
    )
    parser.add_argument(
        "--summary-label",
        help="Optional heading used when appending to the job summary",
    )
    parser.add_argument(
        "--summary-file",
        default=os.environ.get("GITHUB_STEP_SUMMARY", ""),
        help="Path to a GitHub Actions job summary file",
    )
    return parser.parse_args()


def _read_env(name: str) -> str:
    return os.environ.get(name, "").strip()


def _is_valid_dsn(dsn: str) -> bool:
    parsed = urlparse(dsn)
    return (
        parsed.scheme in {"http", "https"}
        and bool(parsed.netloc)
        and bool(parsed.path)
        and parsed.path != "/"
    )


def _append_summary(
    summary_path: str,
    label: str,
    snapshot: ContractSnapshot,
    errors: list[str],
) -> None:
    if not summary_path:
        return

    path = Path(summary_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    lines = [
        f"### {label}",
        "",
        f"- surface: `{snapshot.surface}`",
        f"- environment: `{snapshot.environment or 'unset'}`",
        f"- release: `{snapshot.release or 'unset'}`",
        f"- dsn_configured: `{'yes' if snapshot.dsn_configured else 'no'}`",
    ]

    if errors:
        lines.append("- result: `failed`")
        lines.append("- errors:")
        lines.extend([f"  - {error}" for error in errors])
    else:
        lines.append("- result: `passed`")

    with path.open("a", encoding="utf-8") as handle:
        handle.write("\n".join(lines))
        handle.write("\n\n")


def main() -> int:
    args = parse_args()

    snapshot = ContractSnapshot(
        surface=args.surface,
        environment=_read_env(args.environment_var),
        release=_read_env(args.release_var),
        dsn=_read_env(args.dsn_var),
    )

    errors: list[str] = []

    if not snapshot.environment:
        errors.append(f"{args.environment_var} is empty")
    if not snapshot.release:
        errors.append(f"{args.release_var} is empty")

    if args.expected_environment and snapshot.environment != args.expected_environment:
        errors.append(
            f"{args.environment_var} expected `{args.expected_environment}` but got `{snapshot.environment}`"
        )

    if args.expected_release and snapshot.release != args.expected_release:
        errors.append(
            f"{args.release_var} expected `{args.expected_release}` but got `{snapshot.release}`"
        )

    if args.expected_release_prefix and not snapshot.release.startswith(args.expected_release_prefix):
        errors.append(
            f"{args.release_var} expected prefix `{args.expected_release_prefix}` but got `{snapshot.release}`"
        )

    if args.require_dsn:
        if not snapshot.dsn:
            errors.append(f"{args.dsn_var} is empty")
        elif not _is_valid_dsn(snapshot.dsn):
            errors.append(f"{args.dsn_var} is not a valid Sentry DSN")

    label = args.summary_label or f"Sentry Contract Validation ({snapshot.surface})"
    _append_summary(args.summary_file, label, snapshot, errors)

    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1

    print(
        f"[sentry-contract] surface={snapshot.surface} "
        f"environment={snapshot.environment} release={snapshot.release} "
        f"dsn_configured={'yes' if snapshot.dsn_configured else 'no'}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
