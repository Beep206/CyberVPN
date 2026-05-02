#!/usr/bin/env python3
"""Poll an HTTP endpoint until it satisfies the expected smoke contract."""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", required=True, help="Endpoint to poll")
    parser.add_argument(
        "--expect-status",
        type=int,
        default=200,
        help="Expected HTTP status code",
    )
    parser.add_argument(
        "--contains",
        action="append",
        default=[],
        help="Substring that must appear in the response body",
    )
    parser.add_argument(
        "--header",
        action="append",
        default=[],
        help="Request header in 'Name: Value' form",
    )
    parser.add_argument(
        "--expect-json-field",
        action="append",
        default=[],
        help="JSON assertion in 'path=value' form. Paths use dot notation.",
    )
    parser.add_argument(
        "--timeout-seconds",
        type=float,
        default=60.0,
        help="Overall deadline for retries",
    )
    parser.add_argument(
        "--retry-delay-seconds",
        type=float,
        default=2.0,
        help="Delay between attempts",
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


def _headers(raw_headers: list[str]) -> dict[str, str]:
    parsed: dict[str, str] = {}
    for header in raw_headers:
        if ":" not in header:
            raise ValueError(f"Invalid header `{header}`. Expected 'Name: Value'.")
        name, value = header.split(":", 1)
        parsed[name.strip()] = value.strip()
    return parsed


def _resolve_json_path(payload: Any, path: str) -> Any:
    current = payload
    for segment in path.split("."):
        if not isinstance(current, dict) or segment not in current:
            raise KeyError(path)
        current = current[segment]
    return current


def _coerce_expected(value: str) -> Any:
    lowered = value.lower()
    if lowered == "true":
        return True
    if lowered == "false":
        return False
    if lowered == "null":
        return None
    return value


def _append_summary(summary_file: str, label: str, result: str, details: list[str]) -> None:
    if not summary_file:
        return

    path = Path(summary_file)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(f"### {label}\n\n")
        handle.write(f"- result: `{result}`\n")
        for detail in details:
            handle.write(f"- {detail}\n")
        handle.write("\n")


def main() -> int:
    args = parse_args()
    headers = _headers(args.header)
    deadline = time.monotonic() + args.timeout_seconds
    label = args.summary_label or f"HTTP smoke check ({args.url})"
    last_error = "request did not complete"

    while time.monotonic() <= deadline:
        request = Request(args.url, headers=headers, method="GET")

        try:
            with urlopen(request, timeout=max(args.retry_delay_seconds, 5.0)) as response:
                status = response.status
                body = response.read().decode("utf-8", errors="replace")
        except HTTPError as exc:
            status = exc.code
            body = exc.read().decode("utf-8", errors="replace")
        except URLError as exc:
            last_error = f"connection error: {exc}"
            time.sleep(args.retry_delay_seconds)
            continue

        if status != args.expect_status:
            last_error = f"expected status {args.expect_status}, got {status}"
            time.sleep(args.retry_delay_seconds)
            continue

        missing_substring = next((item for item in args.contains if item not in body), None)
        if missing_substring is not None:
            last_error = f"missing body substring `{missing_substring}`"
            time.sleep(args.retry_delay_seconds)
            continue

        if args.expect_json_field:
            try:
                payload = json.loads(body)
            except json.JSONDecodeError as exc:
                last_error = f"response is not valid JSON: {exc}"
                time.sleep(args.retry_delay_seconds)
                continue

            json_error = None
            for assertion in args.expect_json_field:
                if "=" not in assertion:
                    raise ValueError(
                        f"Invalid JSON assertion `{assertion}`. Expected 'path=value'."
                    )
                raw_path, raw_expected = assertion.split("=", 1)
                try:
                    actual = _resolve_json_path(payload, raw_path)
                except KeyError:
                    json_error = f"missing JSON field `{raw_path}`"
                    break

                expected = _coerce_expected(raw_expected)
                if actual != expected:
                    json_error = (
                        f"JSON field `{raw_path}` expected `{expected}` but got `{actual}`"
                    )
                    break

            if json_error is not None:
                last_error = json_error
                time.sleep(args.retry_delay_seconds)
                continue

        details = [
            f"url: `{args.url}`",
            f"status: `{status}`",
        ]
        if args.expect_json_field:
            details.append("json_contract: `passed`")
        _append_summary(args.summary_file, label, "passed", details)
        print(f"[http-smoke] url={args.url} status={status}")
        return 0

    _append_summary(
        args.summary_file,
        label,
        "failed",
        [
            f"url: `{args.url}`",
            f"error: `{last_error}`",
        ],
    )
    print(f"ERROR: {last_error}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
