#!/usr/bin/env python3
"""Redact Stage 3 partner sandbox import files.

Supports JSON, JSONL, and CSV input. The output keeps analytical shape while
removing direct identifiers and sensitive payment/contact fields.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
from pathlib import Path
from typing import Any

SENSITIVE_KEY = re.compile(
    r"(email|phone|telegram|token|secret|password|authorization|signature|payment_payload|subscription_url|payout_destination|bank|card|wallet_address)",
    re.IGNORECASE,
)
IDENTIFIER_KEY = re.compile(r"(^id$|_id$|uuid|external_id|order_id|partner_account_id|user_id)", re.IGNORECASE)


def stable_hash(value: object, salt: str) -> str:
    digest = hashlib.sha256(f"{salt}:{value}".encode("utf-8")).hexdigest()
    return f"anon_{digest[:16]}"


def redact_value(key: str, value: Any, salt: str) -> Any:
    if value is None:
        return None
    if SENSITIVE_KEY.search(key):
        return "[REDACTED]"
    if IDENTIFIER_KEY.search(key):
        return stable_hash(value, salt)
    if isinstance(value, dict):
        return {str(child_key): redact_value(str(child_key), child_value, salt) for child_key, child_value in value.items()}
    if isinstance(value, list):
        return [redact_value(key, item, salt) for item in value]
    return value


def redact_record(record: dict[str, Any], salt: str) -> dict[str, Any]:
    return {str(key): redact_value(str(key), value, salt) for key, value in record.items()}


def redact_json(input_path: Path, output_path: Path, salt: str) -> int:
    payload = json.loads(input_path.read_text(encoding="utf-8"))
    if isinstance(payload, list):
        redacted = [redact_record(item, salt) if isinstance(item, dict) else item for item in payload]
        count = len(payload)
    elif isinstance(payload, dict):
        redacted = redact_record(payload, salt)
        count = 1
    else:
        raise ValueError("JSON root must be an object or array of objects")
    output_path.write_text(json.dumps(redacted, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return count


def redact_jsonl(input_path: Path, output_path: Path, salt: str) -> int:
    count = 0
    with input_path.open("r", encoding="utf-8") as source, output_path.open("w", encoding="utf-8") as target:
        for line in source:
            if not line.strip():
                continue
            payload = json.loads(line)
            if not isinstance(payload, dict):
                raise ValueError("JSONL rows must be objects")
            target.write(json.dumps(redact_record(payload, salt), sort_keys=True) + "\n")
            count += 1
    return count


def redact_csv(input_path: Path, output_path: Path, salt: str) -> int:
    count = 0
    with input_path.open("r", newline="", encoding="utf-8") as source, output_path.open("w", newline="", encoding="utf-8") as target:
        reader = csv.DictReader(source)
        if not reader.fieldnames:
            raise ValueError("CSV has no header")
        writer = csv.DictWriter(target, fieldnames=reader.fieldnames)
        writer.writeheader()
        for row in reader:
            writer.writerow(redact_record(row, salt))
            count += 1
    return count


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--format", choices=("json", "jsonl", "csv"), default=None)
    parser.add_argument("--salt", required=True, help="Non-secret stable salt for repeatable anonymization")
    args = parser.parse_args()

    input_path: Path = args.input
    output_path: Path = args.output
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fmt = args.format or input_path.suffix.lower().lstrip(".")

    if fmt == "json":
        count = redact_json(input_path, output_path, args.salt)
    elif fmt == "jsonl":
        count = redact_jsonl(input_path, output_path, args.salt)
    elif fmt == "csv":
        count = redact_csv(input_path, output_path, args.salt)
    else:
        raise ValueError(f"Unsupported format: {fmt}")

    manifest = {
        "input": input_path.as_posix(),
        "output": output_path.as_posix(),
        "format": fmt,
        "records": count,
        "redaction": "direct identifiers hashed, sensitive fields redacted",
    }
    manifest_path = output_path.with_suffix(output_path.suffix + ".manifest.json")
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(manifest, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
