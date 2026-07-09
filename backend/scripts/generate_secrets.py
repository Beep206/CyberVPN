#!/usr/bin/env python3
"""Generate cryptographically strong CyberVPN secret material.

The default command writes raw values to the approved local secret store under
`.private/` with owner-only permissions and prints only static metadata. Do not
redirect raw secrets through shell history or CI logs.
"""

from __future__ import annotations

import argparse
import os
import secrets
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUTPUT = REPO_ROOT / ".private" / "generated" / "backend-secrets.env"
GENERATED_SECRET_NAMES = (
    "JWT_SECRET",
    "TOTP_ENCRYPTION_KEY",
    "REMNAWAVE_TOKEN",
    "REMNAWAVE_WEBHOOK_SECRET",
)


def generate_jwt_secret(length: int = 64) -> str:
    """Generate a cryptographically secure JWT secret."""
    return secrets.token_urlsafe(length)


def generate_encryption_key(length: int = 32) -> str:
    """Generate a cryptographically secure AES-256 encryption key."""
    return secrets.token_urlsafe(length)


def generate_api_token(length: int = 32) -> str:
    """Generate a cryptographically secure API token."""
    return secrets.token_urlsafe(length)


def generate_backend_secrets() -> dict[str, str]:
    return {
        GENERATED_SECRET_NAMES[0]: generate_jwt_secret(64),
        GENERATED_SECRET_NAMES[1]: generate_encryption_key(32),
        GENERATED_SECRET_NAMES[2]: generate_api_token(48),
        GENERATED_SECRET_NAMES[3]: generate_api_token(48),
    }


def render_env_file(values: dict[str, str]) -> str:
    lines = [
        "# Generated CyberVPN backend secret material.",
        "# Store this file securely, import it into the approved secret manager, then rotate/delete the local copy.",
        "",
    ]
    lines.extend(f"{name}={value}" for name, value in values.items())
    lines.extend(
        [
            "",
            "# Provider-managed values to fill separately:",
            "# CRYPTOBOT_TOKEN=<get-from-cryptobot-crypto-pay-app>",
            "# CRYPTOBOT_NETWORK=mainnet",
            "# TELEGRAM_BOT_TOKEN=<get-from-botfather>",
            "# GITHUB_CLIENT_ID=<your-client-id>",
            "# GITHUB_CLIENT_SECRET=<your-client-secret>",
            "",
        ]
    )
    return "\n".join(lines)


def write_owner_only_file(path: Path, content: str, *, force: bool) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        path.parent.chmod(0o700)
    except OSError:
        # Windows may not fully support POSIX mode bits; os.open still applies
        # owner-only semantics on platforms that do.
        pass

    flags = os.O_WRONLY | os.O_CREAT
    if force:
        flags |= os.O_TRUNC
    else:
        flags |= os.O_EXCL

    file_descriptor = os.open(path, flags, 0o600)
    try:
        os.write(file_descriptor, content.encode("utf-8"))
    finally:
        os.close(file_descriptor)

    try:
        path.chmod(0o600)
    except OSError:
        pass


def resolve_raw_secret_output_path(path: Path, *, allow_outside_private: bool = False) -> Path:
    output_path = path.expanduser()
    if not output_path.is_absolute():
        output_path = Path.cwd() / output_path

    resolved_output = output_path.resolve(strict=False)
    private_root = (REPO_ROOT / ".private").resolve(strict=False)
    try:
        resolved_output.relative_to(private_root)
    except ValueError as exc:
        if allow_outside_private:
            return resolved_output
        raise SystemExit(
            "Raw secret output must stay under the repository .private directory; "
            "pass --allow-outside-private only for an explicitly approved secret-store import path."
        ) from exc
    return resolved_output


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate CyberVPN backend secret material.")
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help="Owner-only output file for raw secret values. Defaults to the repository .private/generated directory.",
    )
    parser.add_argument("--force", action="store_true", help="Overwrite the output file if it already exists.")
    parser.add_argument(
        "--allow-outside-private",
        action="store_true",
        help="Allow raw secret output outside .private for an explicitly approved secret-store import path.",
    )
    args = parser.parse_args()

    values = generate_backend_secrets()
    output_path = resolve_raw_secret_output_path(args.output, allow_outside_private=args.allow_outside_private)
    try:
        write_owner_only_file(output_path, render_env_file(values), force=args.force)
    except FileExistsError as exc:
        raise SystemExit(f"{output_path} already exists; pass --force to replace it intentionally.") from exc

    print("CyberVPN backend secrets generated.")
    print(f"raw_values_file={output_path}")
    print("raw_values_printed=false")
    print(f"generated_value_count={len(GENERATED_SECRET_NAMES)}")
    print("Import the raw values into the approved secret manager and remove the local file when finished.")


if __name__ == "__main__":
    main()
