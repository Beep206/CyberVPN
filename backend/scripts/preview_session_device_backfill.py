"""Preview legacy refresh-token rows as user device backfill candidates.

This script is intentionally file-based and dry-run only. It accepts synthetic or
local fixture JSON and never connects to a database.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import defaultdict
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any

REPORT_SCHEMA = "session-device-backfill.dry-run.v1"
DEFAULT_PEPPER_LABEL = "synthetic-device-cookie-pepper"


def build_backfill_preview(
    rows: Iterable[Mapping[str, Any]],
    *,
    default_auth_realm_id: str | None = None,
    principal_class: str = "admin_user",
    audience: str = "cybervpn:admin",
    pepper_label: str = DEFAULT_PEPPER_LABEL,
) -> dict[str, Any]:
    """Group active legacy refresh-token rows into device candidates."""

    skipped: list[dict[str, str]] = []
    groups: dict[tuple[str, str], list[Mapping[str, Any]]] = defaultdict(list)
    row_count = 0

    for row in rows:
        row_count += 1
        token_id = _safe_str(row.get("id")) or f"row-{row_count}"
        if _safe_str(row.get("revoked_at")):
            skipped.append({"id": token_id, "reason": "revoked_token"})
            continue

        user_id = _safe_str(row.get("user_id"))
        device_id = _safe_str(row.get("device_id"))
        if not user_id:
            skipped.append({"id": token_id, "reason": "missing_user_id"})
            continue
        if not device_id:
            skipped.append({"id": token_id, "reason": "missing_device_id"})
            continue

        groups[(user_id, device_id)].append(row)

    candidates = [
        _build_candidate(
            user_id=user_id,
            device_id=device_id,
            rows=grouped_rows,
            default_auth_realm_id=default_auth_realm_id,
            principal_class=principal_class,
            audience=audience,
            pepper_label=pepper_label,
        )
        for (user_id, device_id), grouped_rows in sorted(groups.items())
    ]

    return {
        "schema": REPORT_SCHEMA,
        "mode": "dry_run_only",
        "writes_database": False,
        "input_rows": row_count,
        "device_candidates": len(candidates),
        "skipped_rows": skipped,
        "candidates": candidates,
    }


def _build_candidate(
    *,
    user_id: str,
    device_id: str,
    rows: list[Mapping[str, Any]],
    default_auth_realm_id: str | None,
    principal_class: str,
    audience: str,
    pepper_label: str,
) -> dict[str, Any]:
    ordered = sorted(rows, key=lambda row: _safe_str(row.get("last_used_at")) or _safe_str(row.get("created_at")))
    first = ordered[0]
    last = ordered[-1]

    return {
        "auth_realm_id": default_auth_realm_id,
        "principal_subject": user_id,
        "principal_class": principal_class,
        "audience": audience,
        "device_key_hash": _device_key_hash(pepper_label=pepper_label, user_id=user_id, device_id=device_id),
        "legacy_refresh_token_count": len(rows),
        "legacy_refresh_token_ids": [_safe_str(row.get("id")) for row in ordered if _safe_str(row.get("id"))],
        "first_seen_at": _safe_str(first.get("created_at")) or _safe_str(first.get("last_used_at")),
        "last_seen_at": _safe_str(last.get("last_used_at")) or _safe_str(last.get("created_at")),
        "ip_address": _safe_str(last.get("ip_address")),
        "user_agent": _safe_str(last.get("user_agent")),
    }


def _device_key_hash(*, pepper_label: str, user_id: str, device_id: str) -> str:
    payload = f"{pepper_label}:{user_id}:{device_id}".encode()
    return hashlib.sha256(payload).hexdigest()


def _safe_str(value: Any) -> str | None:
    if value is None:
        return None
    normalized = str(value).strip()
    return normalized or None


def _load_rows(path: Path) -> list[Mapping[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        raise ValueError("Input JSON must be a list of legacy refresh token rows.")
    if not all(isinstance(item, Mapping) for item in payload):
        raise ValueError("Every input row must be an object.")
    return payload


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path, help="Synthetic/local legacy refresh token rows JSON.")
    parser.add_argument("--output", type=Path, help="Optional path for the dry-run JSON report.")
    parser.add_argument("--default-auth-realm-id", help="Optional realm UUID to include in report candidates.")
    parser.add_argument("--principal-class", default="admin_user", help="Principal class for fixture rows.")
    parser.add_argument("--audience", default="cybervpn:admin", help="Audience for fixture rows.")
    parser.add_argument(
        "--pepper-label",
        default=DEFAULT_PEPPER_LABEL,
        help="Non-secret label for deterministic synthetic hashes; do not pass production secret material.",
    )
    args = parser.parse_args()

    report = build_backfill_preview(
        _load_rows(args.input),
        default_auth_realm_id=args.default_auth_realm_id,
        principal_class=args.principal_class,
        audience=args.audience,
        pepper_label=args.pepper_label,
    )
    encoded = json.dumps(report, indent=2, sort_keys=True)

    if args.output:
        args.output.write_text(f"{encoded}\n", encoding="utf-8")
    else:
        print(encoded)


if __name__ == "__main__":
    main()
