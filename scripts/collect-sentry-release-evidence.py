#!/usr/bin/env python3
from __future__ import annotations

import argparse
import datetime as dt
import glob
import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any


DEBUG_ID_PATTERN = re.compile(r"debugId=([A-Fa-f0-9-]+)")
ELF_BUILD_ID_PATTERN = re.compile(r"Build ID:\s*([A-Fa-f0-9]+)")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Collect local release artifact evidence for Sentry proof manifests.")
    parser.add_argument("--surface", required=True)
    parser.add_argument("--release", required=True)
    parser.add_argument("--environment", required=True)
    parser.add_argument("--project", action="append", default=[])
    parser.add_argument("--artifact", action="append", default=[], help="label=glob pattern")
    parser.add_argument("--output", required=True)
    parser.add_argument("--summary-label", default="")
    parser.add_argument("--proof-scope", default="release_workflow")
    parser.add_argument("--deploy-marker-mode", default="release_workflow")
    return parser.parse_args()


def parse_artifact_specs(values: list[str]) -> list[tuple[str, str]]:
    specs: list[tuple[str, str]] = []
    for value in values:
        if "=" not in value:
            raise ValueError(f"artifact spec must use label=glob syntax: {value}")
        label, pattern = value.split("=", 1)
        label = label.strip()
        pattern = pattern.strip()
        if not label or not pattern:
            raise ValueError(f"artifact spec must use non-empty label and glob: {value}")
        specs.append((label, pattern))
    return specs


def sha256_for_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def summarize_directory(path: Path) -> dict[str, Any]:
    files = [candidate for candidate in path.rglob("*") if candidate.is_file()]
    total_size = sum(candidate.stat().st_size for candidate in files)
    sample_files = [str(candidate.relative_to(path).as_posix()) for candidate in sorted(files)[:20]]
    return {
        "kind": detect_kind(path),
        "path": path.as_posix(),
        "exists": True,
        "is_directory": True,
        "file_count": len(files),
        "total_size_bytes": total_size,
        "sample_files": sample_files,
    }


def detect_kind(path: Path) -> str:
    suffix = path.suffix.lower()
    if path.is_dir():
        if path.name.endswith(".dSYM"):
            return "dsym_bundle"
        if "debug-info" in path.parts:
            return "debug_info_directory"
        if path.name == "dist":
            return "web_dist_directory"
        return "directory"
    if path.name == "mapping.txt":
        return "proguard_mapping"
    if suffix == ".map":
        return "sourcemap"
    if suffix in {".js", ".mjs", ".cjs"}:
        return "javascript_bundle"
    if suffix in {".apk", ".aab", ".ipa"}:
        return "packaged_app"
    if suffix == ".pdb":
        return "pdb"
    if path.name in {"desktop-client", "desktop-client.exe", "helix-adapter", "helix-node"}:
        return "native_binary"
    return "file"


def maybe_extract_debug_id(path: Path) -> str | None:
    if path.suffix.lower() != ".js":
        return None
    try:
        content = path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return None
    match = DEBUG_ID_PATTERN.search(content)
    if match:
        return match.group(1)
    if "_sentryDebugIds" in content:
        return "embedded-debug-id-present"
    return None


def maybe_extract_elf_build_id(path: Path) -> str | None:
    if not path.is_file():
        return None
    try:
        result = subprocess.run(
            ["readelf", "-n", str(path)],
            capture_output=True,
            text=True,
            check=False,
            timeout=5,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
        return None

    if result.returncode != 0:
        return None

    match = ELF_BUILD_ID_PATTERN.search(result.stdout)
    if match:
        return match.group(1)
    return None


def describe_path(path: Path) -> dict[str, Any]:
    if path.is_dir():
        return summarize_directory(path)

    description: dict[str, Any] = {
        "kind": detect_kind(path),
        "path": path.as_posix(),
        "exists": True,
        "is_directory": False,
        "size_bytes": path.stat().st_size,
        "sha256": sha256_for_file(path),
    }

    debug_id = maybe_extract_debug_id(path)
    if debug_id:
        description["debug_id"] = debug_id

    build_id = maybe_extract_elf_build_id(path)
    if build_id:
        description["elf_build_id"] = build_id

    return description


def collect_artifacts(specs: list[tuple[str, str]]) -> dict[str, list[dict[str, Any]]]:
    manifest: dict[str, list[dict[str, Any]]] = {}
    for label, pattern in specs:
        matches = sorted({Path(match) for match in glob.glob(pattern, recursive=True)})
        if not matches:
            raise FileNotFoundError(f"artifact pattern matched no files: {label}={pattern}")
        manifest[label] = [describe_path(match) for match in matches]
    return manifest


def write_summary(args: argparse.Namespace, manifest: dict[str, list[dict[str, Any]]]) -> None:
    summary_path = os.environ.get("GITHUB_STEP_SUMMARY")
    if not summary_path:
        return

    label = args.summary_label or f"{args.surface} release evidence"
    with open(summary_path, "a", encoding="utf-8") as summary:
        summary.write(f"### {label}\n")
        summary.write(f"- Surface: `{args.surface}`\n")
        summary.write(f"- Environment: `{args.environment}`\n")
        summary.write(f"- Release: `{args.release}`\n")
        summary.write(f"- Projects: `{', '.join(args.project) if args.project else 'unconfigured'}`\n")
        summary.write(f"- Deploy marker mode: `{args.deploy_marker_mode}`\n")
        for artifact_label, files in manifest.items():
            summary.write(f"- `{artifact_label}` entries: `{len(files)}`\n")


def main() -> None:
    args = parse_args()
    try:
        artifact_specs = parse_artifact_specs(args.artifact)
    except ValueError as exc:
        print(f"[sentry-release-evidence] ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc

    if not artifact_specs:
        print("[sentry-release-evidence] ERROR: at least one --artifact is required", file=sys.stderr)
        raise SystemExit(1)

    try:
        manifest = collect_artifacts(artifact_specs)
    except FileNotFoundError as exc:
        print(f"[sentry-release-evidence] ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "surface": args.surface,
        "release": args.release,
        "environment": args.environment,
        "projects": args.project,
        "proof_scope": args.proof_scope,
        "deploy_marker_mode": args.deploy_marker_mode,
        "generated_at": dt.datetime.now(dt.UTC).isoformat(),
        "artifacts": manifest,
    }
    output_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    write_summary(args, manifest)
    print(f"[sentry-release-evidence] surface={args.surface} output={output_path.as_posix()} artifacts={len(manifest)}")


if __name__ == "__main__":
    main()
