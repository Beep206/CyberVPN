from __future__ import annotations

import argparse
from datetime import datetime, timezone
from pathlib import Path
import re
from typing import Any

import yaml


DIGEST_REF_PATTERN = re.compile(r"^.+@sha256:[a-f0-9]{64}$")


def validate_image_ref(component: str, image_ref: str) -> None:
    if not DIGEST_REF_PATTERN.match(image_ref):
        raise RuntimeError(
            f"{component} image must be a digest-pinned ref like "
            f"'ghcr.io/org/repo/{component}@sha256:<64-hex>'."
        )


def default_release_name(environment: str, source_commit: str, created_at: str) -> str:
    timestamp = created_at.replace("-", "").replace(":", "").replace("T", "-").replace("Z", "")
    short_commit = (source_commit[:12] if source_commit else "manual").lower()
    return f"control-plane-{environment}-{timestamp}-{short_commit}"


def build_release_manifest(
    *,
    environment: str,
    backend_image: str,
    worker_image: str,
    helix_adapter_image: str,
    source_commit: str,
    source_run_url: str,
    created_at: str,
    release_name: str,
) -> dict[str, Any]:
    validate_image_ref("backend", backend_image)
    validate_image_ref("worker", worker_image)
    validate_image_ref("helix-adapter", helix_adapter_image)

    effective_release_name = release_name or default_release_name(
        environment=environment,
        source_commit=source_commit,
        created_at=created_at,
    )

    return {
        "control_plane_release_name": effective_release_name,
        "control_plane_release_source_commit": source_commit,
        "control_plane_release_source_run_url": source_run_url,
        "control_plane_release_created_at": created_at,
        "control_plane_release_images": {
            "backend": backend_image,
            "worker": worker_image,
            "helix_adapter": helix_adapter_image,
        },
    }


def write_yaml(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        yaml.safe_dump(payload, sort_keys=False, allow_unicode=False),
        encoding="utf-8",
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Update the control-plane release manifest with digest-pinned image refs.",
    )
    parser.add_argument(
        "--environment",
        required=True,
        choices=("staging", "production"),
        help="Inventory environment to update.",
    )
    parser.add_argument(
        "--inventory-root",
        type=Path,
        default=Path(__file__).resolve().parent.parent / "inventories",
        help="Path to the ansible inventories root.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Optional explicit output path. Defaults to the group_vars release.yml for the environment.",
    )
    parser.add_argument("--backend-image", required=True, help="Digest-pinned backend image ref.")
    parser.add_argument("--worker-image", required=True, help="Digest-pinned worker image ref.")
    parser.add_argument(
        "--helix-adapter-image",
        required=True,
        help="Digest-pinned Helix adapter image ref.",
    )
    parser.add_argument(
        "--source-commit",
        default="",
        help="Git commit SHA that produced the images.",
    )
    parser.add_argument(
        "--source-run-url",
        default="",
        help="CI run URL or build evidence URL for the promoted images.",
    )
    parser.add_argument(
        "--created-at",
        default=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        help="RFC3339 UTC timestamp for the manifest update.",
    )
    parser.add_argument(
        "--release-name",
        default="",
        help="Optional explicit release name. Defaults to control-plane-<env>-<timestamp>-<sha>.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    output_path = args.output or (
        args.inventory_root
        / args.environment
        / "group_vars"
        / f"control_plane_{args.environment}"
        / "release.yml"
    )

    payload = build_release_manifest(
        environment=args.environment,
        backend_image=args.backend_image,
        worker_image=args.worker_image,
        helix_adapter_image=args.helix_adapter_image,
        source_commit=args.source_commit,
        source_run_url=args.source_run_url,
        created_at=args.created_at,
        release_name=args.release_name,
    )
    write_yaml(output_path, payload)
    print(output_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
