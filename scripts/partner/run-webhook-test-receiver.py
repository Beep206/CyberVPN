#!/usr/bin/env python3
"""Small local-only partner webhook test receiver.

The receiver stores redacted payload evidence for staging webhook tests. It is
not designed to be an internet-facing production endpoint.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import re
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

HOST = os.environ.get("PARTNER_WEBHOOK_RECEIVER_HOST", "127.0.0.1")
PORT = int(os.environ.get("PARTNER_WEBHOOK_RECEIVER_PORT", "9088"))
EVIDENCE_DIR = Path(os.environ.get("PARTNER_WEBHOOK_EVIDENCE_DIR", "docs/evidence/partner-platform/webhook-receiver"))
MAX_BODY_BYTES = int(os.environ.get("PARTNER_WEBHOOK_MAX_BODY_BYTES", "262144"))
SECRET_FILE = os.environ.get("PARTNER_WEBHOOK_SHARED_SECRET_FILE")
SECRET = os.environ.get("PARTNER_WEBHOOK_SHARED_SECRET", "")
REPLAY_WINDOW_SECONDS = int(os.environ.get("PARTNER_WEBHOOK_REPLAY_WINDOW_SECONDS", "300"))
SIGNATURE_HEADER = "X-CyberVPN-Partner-Signature"
TIMESTAMP_HEADER = "X-CyberVPN-Partner-Timestamp"
EVENT_ID_HEADER = "X-CyberVPN-Partner-Event-Id"

SENSITIVE_KEYS = re.compile(
    r"(token|secret|password|authorization|signature|email|phone|telegram|subscription_url|payment_payload)",
    re.IGNORECASE,
)
IDENTIFIER_KEYS = re.compile(r"(^id$|_id$|uuid|external_id|order_id|partner_account_id|user_id)", re.IGNORECASE)
SEEN_EVENTS: dict[str, float] = {}


def _load_secret() -> bytes:
    if SECRET_FILE and Path(SECRET_FILE).exists():
        return Path(SECRET_FILE).read_text(encoding="utf-8").strip().encode("utf-8")
    return SECRET.encode("utf-8")


def _hash_identifier(value: Any) -> str:
    digest = hashlib.sha256(str(value).encode("utf-8")).hexdigest()
    return f"anon_{digest[:16]}"


def _redact(value: Any, key_name: str = "") -> Any:
    if key_name and IDENTIFIER_KEYS.search(key_name):
        return _hash_identifier(value)
    if isinstance(value, dict):
        return {
            str(key): "[REDACTED]" if SENSITIVE_KEYS.search(str(key)) else _redact(item, str(key))
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [_redact(item, key_name) for item in value]
    if isinstance(value, str) and len(value) > 128:
        return value[:32] + "...[TRUNCATED]"
    return value


def _verify_signature(body: bytes, provided: str | None) -> bool:
    secret = _load_secret()
    if not secret:
        return True
    if not provided:
        return False
    expected = hmac.new(secret, body, hashlib.sha256).hexdigest()
    normalized = provided.removeprefix("sha256=").strip()
    return hmac.compare_digest(expected, normalized)


def _verify_timestamp(value: str | None, *, now: float | None = None) -> bool:
    if not value:
        return False
    try:
        timestamp = int(value)
    except ValueError:
        return False
    current_time = int(now if now is not None else time.time())
    return abs(current_time - timestamp) <= REPLAY_WINDOW_SECONDS


def _remember_event_or_replay(event_id: str | None, *, body_sha: str, now: float | None = None) -> bool:
    if not event_id:
        return False
    current_time = now if now is not None else time.time()
    expired_before = current_time - REPLAY_WINDOW_SECONDS
    for key, seen_at in list(SEEN_EVENTS.items()):
        if seen_at < expired_before:
            SEEN_EVENTS.pop(key, None)
    replay_key = f"{event_id}:{body_sha}"
    if replay_key in SEEN_EVENTS:
        return False
    SEEN_EVENTS[replay_key] = current_time
    return True


def _evidence_counts_by_result() -> dict[str, int]:
    counts: dict[str, int] = {}
    if not EVIDENCE_DIR.exists():
        return counts
    for path in EVIDENCE_DIR.glob("partner-webhook-*.json"):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            result = "unreadable"
        else:
            result = str(payload.get("result") or "unknown")
        counts[result] = counts.get(result, 0) + 1
    return counts


class Handler(BaseHTTPRequestHandler):
    server_version = "CyberVPNPartnerWebhookTestReceiver/1.0"

    def do_GET(self) -> None:  # noqa: N802
        if self.path == "/health":
            self._json_response(200, {"status": "ok"})
            return
        if self.path == "/metrics":
            self._metrics_response()
            return
        self._json_response(404, {"error": "not_found"})

    def do_POST(self) -> None:  # noqa: N802
        started = time.time()
        result = "success"
        length = int(self.headers.get("Content-Length", "0"))
        if length > MAX_BODY_BYTES:
            self._write_evidence(result="too_large", body={}, raw_sha256="", duration_seconds=time.time() - started)
            self._json_response(413, {"error": "payload_too_large"})
            return

        body = self.rfile.read(length)
        body_sha = hashlib.sha256(body).hexdigest()
        signature = self.headers.get(SIGNATURE_HEADER)
        if not _verify_signature(body, signature):
            self._write_evidence(
                result="invalid_signature",
                body={},
                raw_sha256=body_sha,
                duration_seconds=time.time() - started,
            )
            self._json_response(401, {"error": "invalid_signature"})
            return

        if _load_secret():
            timestamp = self.headers.get(TIMESTAMP_HEADER)
            event_id = self.headers.get(EVENT_ID_HEADER)
            if not _verify_timestamp(timestamp):
                self._write_evidence(
                    result="invalid_timestamp",
                    body={},
                    raw_sha256=body_sha,
                    duration_seconds=time.time() - started,
                )
                self._json_response(401, {"error": "invalid_timestamp"})
                return
            if not _remember_event_or_replay(event_id, body_sha=body_sha):
                self._write_evidence(
                    result="replay",
                    body={},
                    raw_sha256=body_sha,
                    duration_seconds=time.time() - started,
                )
                self._json_response(409, {"error": "replay_detected"})
                return

        try:
            parsed = json.loads(body.decode("utf-8")) if body else {}
        except json.JSONDecodeError:
            self._write_evidence(
                result="invalid_json",
                body={},
                raw_sha256=body_sha,
                duration_seconds=time.time() - started,
            )
            self._json_response(400, {"error": "invalid_json"})
            return

        self._write_evidence(
            result=result,
            body=_redact(parsed),
            raw_sha256=body_sha,
            duration_seconds=time.time() - started,
        )
        self._json_response(202, {"status": "accepted", "sha256": body_sha})

    def _write_evidence(self, *, result: str, body: dict[str, Any], raw_sha256: str, duration_seconds: float) -> None:
        EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
        stamp = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
        payload = {
            "received_at": stamp,
            "path": self.path,
            "result": result,
            "raw_sha256": raw_sha256,
            "duration_seconds": round(duration_seconds, 6),
            "headers": {
                "content_type": self.headers.get("Content-Type", ""),
                "user_agent": self.headers.get("User-Agent", ""),
            },
            "body_redacted": body,
        }
        target = EVIDENCE_DIR / f"partner-webhook-{stamp}-{raw_sha256[:12] or result}.json"
        target.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    def _json_response(self, status: int, payload: dict[str, Any]) -> None:
        encoded = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def _metrics_response(self) -> None:
        counts = _evidence_counts_by_result()
        count = sum(counts.values())
        lines = [
            "# HELP cybervpn_partner_webhook_test_receiver_evidence_files Current evidence file count.\n"
            "# TYPE cybervpn_partner_webhook_test_receiver_evidence_files gauge\n"
            f"cybervpn_partner_webhook_test_receiver_evidence_files {count}\n"
            "# HELP cybervpn_partner_webhook_test_receiver_requests_total "
            "Partner webhook test receiver requests by result.\n"
            "# TYPE cybervpn_partner_webhook_test_receiver_requests_total counter\n"
        ]
        for result, result_count in sorted(counts.items()):
            safe_result = re.sub(r"[^a-zA-Z0-9_:.-]", "_", result)
            lines.append(
                f'cybervpn_partner_webhook_test_receiver_requests_total{{result="{safe_result}"}} '
                f"{result_count}\n"
            )
        body = "".join(lines).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/plain; version=0.0.4")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args: object) -> None:
        return


def main() -> int:
    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
    server = ThreadingHTTPServer((HOST, PORT), Handler)
    print(f"partner webhook test receiver listening on {HOST}:{PORT}", flush=True)
    server.serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
