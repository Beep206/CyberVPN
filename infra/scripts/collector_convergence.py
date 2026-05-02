#!/usr/bin/env python3
"""Audit repo-side collector convergence toward the Alloy-only target state."""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from pathlib import PurePosixPath
import re


TRACKED_LEGACY_PREFIXES = (
    "docs/evidence/",
    "docs/plans/",
    "docs/prompts/",
    "infra/tests/",
)

TRACKED_LEGACY_GLOBS = (
    "docs/CYBERVPN_FULL_DESCRIPTION.md",
    "docs/PROJECT_OVERVIEW.md",
    "infra/README.md",
    "infra/docker-compose.yml",
    "infra/prometheus/prometheus.yml",
    "infra/scripts/control_plane_observability.py",
    "backend/src/config/settings.py",
)

EXCLUDED_DIR_NAMES = {
    ".git",
    ".next",
    ".venv",
    "node_modules",
    "dist",
    "build",
    "__pycache__",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".turbo",
}

INCLUDED_SUFFIXES = {
    ".env",
    ".example",
    ".json",
    ".jsx",
    ".kt",
    ".md",
    ".py",
    ".rs",
    ".sh",
    ".swift",
    ".toml",
    ".ts",
    ".tsx",
    ".txt",
    ".yaml",
    ".yml",
}

INCLUDED_NAME_PREFIXES = {
    "Dockerfile",
    "Makefile",
}

MAX_FILE_BYTES = 1_000_000
SCAN_PATH_PREFIXES = (
    ".github/",
    "backend/",
    "docs/",
    "infra/",
    "services/",
)

PATTERNS = (
    re.compile(r"\bpromtail\b", re.IGNORECASE),
    re.compile(r"\botel-collector\b", re.IGNORECASE),
    re.compile(r"\bopentelemetry-collector(?:-contrib)?\b", re.IGNORECASE),
)


@dataclass(frozen=True)
class MatchRecord:
    path: str
    line: int
    pattern: str
    text: str
    classification: str


def should_skip(path: Path) -> bool:
    return any(part in EXCLUDED_DIR_NAMES for part in path.parts)


def should_scan_file(path: Path) -> bool:
    if should_skip(path):
        return False
    if path.stat().st_size > MAX_FILE_BYTES:
        return False
    if path.suffix.lower() in INCLUDED_SUFFIXES:
        return True
    return any(path.name.startswith(prefix) for prefix in INCLUDED_NAME_PREFIXES)


def classify(path: str) -> str:
    if path.startswith(TRACKED_LEGACY_PREFIXES):
        return "tracked_legacy"
    path_obj = PurePosixPath(path)
    return "tracked_legacy" if any(path_obj.match(pattern) for pattern in TRACKED_LEGACY_GLOBS) else "unexpected"


def should_scan_repo_relative_path(path: str) -> bool:
    return path.startswith(SCAN_PATH_PREFIXES)


def collect_matches(repo_root: Path) -> list[MatchRecord]:
    matches: list[MatchRecord] = []
    for prefix in SCAN_PATH_PREFIXES:
        root = repo_root / prefix
        if not root.exists():
            continue
        for candidate in root.rglob("*"):
            if not candidate.is_file() or not should_scan_file(candidate):
                continue

            relative_path = candidate.relative_to(repo_root).as_posix()
            try:
                lines = candidate.read_text(encoding="utf-8", errors="ignore").splitlines()
            except OSError:
                continue

            for line_number, line in enumerate(lines, start=1):
                for pattern in PATTERNS:
                    if pattern.search(line):
                        matches.append(
                            MatchRecord(
                                path=relative_path,
                                line=line_number,
                                pattern=pattern.pattern,
                                text=line.strip(),
                                classification=classify(relative_path),
                            )
                        )
    return matches


def build_report(repo_root: Path) -> dict[str, object]:
    matches = collect_matches(repo_root)
    tracked = [asdict(match) for match in matches if match.classification == "tracked_legacy"]
    unexpected = [asdict(match) for match in matches if match.classification == "unexpected"]

    return {
        "repo_root": str(repo_root),
        "tracked_legacy_prefixes": list(TRACKED_LEGACY_PREFIXES),
        "tracked_legacy_globs": list(TRACKED_LEGACY_GLOBS),
        "summary": {
            "total_matches": len(matches),
            "tracked_legacy_matches": len(tracked),
            "unexpected_matches": len(unexpected),
        },
        "tracked_legacy_matches": tracked,
        "unexpected_matches": unexpected,
    }


def render_markdown(report: dict[str, object]) -> str:
    summary = report["summary"]
    tracked = report["tracked_legacy_matches"]
    unexpected = report["unexpected_matches"]

    lines = [
        "# Collector Convergence Report",
        "",
        "Summary:",
        "",
        f"- total matches: `{summary['total_matches']}`",
        f"- tracked legacy matches: `{summary['tracked_legacy_matches']}`",
        f"- unexpected matches: `{summary['unexpected_matches']}`",
        "",
        "Tracked legacy globs:",
        "",
    ]
    for prefix in report["tracked_legacy_prefixes"]:
        lines.append(f"- prefix: `{prefix}`")
    for pattern in report["tracked_legacy_globs"]:
        lines.append(f"- glob: `{pattern}`")

    lines.extend(["", "Unexpected matches:"])
    if unexpected:
        lines.append("")
        for match in unexpected:
            lines.append(
                f"- `{match['path']}:{match['line']}` matched `{match['pattern']}` -> `{match['text']}`"
            )
    else:
        lines.append("")
        lines.append("- none")

    lines.extend(["", "Tracked legacy matches:"])
    if tracked:
        lines.append("")
        for match in tracked:
            lines.append(
                f"- `{match['path']}:{match['line']}` matched `{match['pattern']}` -> `{match['text']}`"
            )
    else:
        lines.append("")
        lines.append("- none")

    lines.append("")
    return "\n".join(lines)


def command_render_report(args: argparse.Namespace) -> int:
    repo_root = Path(args.repo_root).resolve()
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    report = build_report(repo_root)
    (output_dir / "collector-convergence-report.json").write_text(
        json.dumps(report, indent=2) + "\n",
        encoding="utf-8",
    )
    (output_dir / "collector-convergence-report.md").write_text(
        render_markdown(report),
        encoding="utf-8",
    )
    return 0


def command_validate(args: argparse.Namespace) -> int:
    repo_root = Path(args.repo_root).resolve()
    report = build_report(repo_root)
    unexpected = report["unexpected_matches"]
    if unexpected:
        for match in unexpected:
            print(f"unexpected collector reference: {match['path']}:{match['line']} -> {match['text']}")
        return 1
    print(
        "collector convergence validation passed: "
        f"{report['summary']['tracked_legacy_matches']} tracked legacy matches, "
        f"{report['summary']['unexpected_matches']} unexpected matches"
    )
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    render_report = subparsers.add_parser("render-report", help="Render collector convergence reports.")
    render_report.add_argument("--repo-root", default=".")
    render_report.add_argument("--output-dir", required=True)
    render_report.set_defaults(func=command_render_report)

    validate = subparsers.add_parser("validate", help="Fail if unexpected collector references exist.")
    validate.add_argument("--repo-root", default=".")
    validate.set_defaults(func=command_validate)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
