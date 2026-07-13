#!/usr/bin/env python
"""Verify a public Task2 runtime fault evidence bundle offline."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


REPO_ROOT = _repo_root()
BACKEND_ROOT = REPO_ROOT / "backend"
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))


def _install_offline_import_defaults() -> None:
    defaults = {
        "ENVIRONMENT": "test",
        "CORS_ORIGINS": "http://localhost:3000",
        "ENABLE_METRICS": "false",
        "REDIS_URL": "redis://localhost:6379/15",
        "REMNAWAVE_TOKEN": "offline-remnawave-token-for-public-task2-bundle-verifier",
        "JWT_SECRET": "offline-jwt-key-for-public-task2-bundle-verifier-000000000000",
        "CRYPTOBOT_TOKEN": "offline-cryptobot-token-for-public-task2-bundle-verifier",
        "CYBERVPN_DEVICE_COOKIE_PEPPER": "offline-device-cookie-pepper-for-public-task2-bundle-verifier",
        "TOTP_ENCRYPTION_KEY": "offline-totp-key-for-public-task2-bundle-verifier",
        "OAUTH_TOKEN_ENCRYPTION_KEY": "offline-oauth-key-for-public-task2-bundle-verifier",
    }
    for key, value in defaults.items():
        os.environ.setdefault(key, value)


_install_offline_import_defaults()

from src.application.vpn_testing.task2_runtime_fault_evidence import (  # noqa: E402
    Task2RuntimeFaultEvidenceRejected,
)
from src.application.vpn_testing.task2_runtime_fault_public_bundle import (  # noqa: E402
    verify_task2_runtime_fault_public_bundle,
)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Verify a public Task2 runtime fault evidence bundle offline."
    )
    parser.add_argument(
        "bundle_dir",
        type=Path,
        help="Directory containing manifest.json and public evidence files",
    )
    parser.add_argument(
        "--expected-operator-public-key-sha256",
        required=True,
        help="Trusted out-of-band SHA-256 fingerprint of the raw Ed25519 public key",
    )
    parser.add_argument(
        "--expected-manifest-sha256",
        help="Optional trusted out-of-band SHA-256 of the canonical bundle manifest",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        verified = verify_task2_runtime_fault_public_bundle(
            args.bundle_dir,
            expected_operator_public_key_sha256=args.expected_operator_public_key_sha256,
            expected_manifest_sha256=args.expected_manifest_sha256,
        )
    except Task2RuntimeFaultEvidenceRejected as exc:
        print(
            json.dumps({"status": "rejected", "reason": exc.reason}, sort_keys=True),
            file=sys.stderr,
        )
        return 1
    print(json.dumps(verified.safe_summary(), sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
