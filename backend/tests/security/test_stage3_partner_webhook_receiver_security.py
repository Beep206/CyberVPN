from __future__ import annotations

import hashlib
import hmac
import importlib.util
import time
from pathlib import Path


def _load_receiver_module():
    repo_root = Path(__file__).resolve().parents[3]
    script_path = repo_root / "scripts" / "partner" / "run-webhook-test-receiver.py"
    spec = importlib.util.spec_from_file_location("stage3_partner_webhook_receiver", script_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_stage3_partner_webhook_receiver_requires_valid_hmac_timestamp_and_replay_guard() -> None:
    receiver = _load_receiver_module()
    receiver.SECRET = "stage3-webhook-test-secret"
    receiver.SECRET_FILE = None
    receiver.SEEN_EVENTS.clear()

    body = b'{"event":"partner.test","partner_account_id":"workspace-1"}'
    body_sha = hashlib.sha256(body).hexdigest()
    signature = hmac.new(receiver.SECRET.encode("utf-8"), body, hashlib.sha256).hexdigest()
    now = time.time()

    assert receiver._verify_signature(body, f"sha256={signature}") is True
    assert receiver._verify_signature(body, "sha256=bad") is False
    assert receiver._verify_timestamp(str(int(now)), now=now) is True
    assert receiver._verify_timestamp(str(int(now - receiver.REPLAY_WINDOW_SECONDS - 1)), now=now) is False
    assert receiver._remember_event_or_replay("evt_stage3_001", body_sha=body_sha, now=now) is True
    assert receiver._remember_event_or_replay("evt_stage3_001", body_sha=body_sha, now=now + 1) is False


def test_stage3_partner_webhook_receiver_redacts_sensitive_payload_fields() -> None:
    receiver = _load_receiver_module()
    redacted = receiver._redact(
        {
            "partner_account_id": "workspace-1",
            "email": "partner@example.com",
            "payment_payload": {"token": "secret-token"},
            "nested": {"user_id": "customer-1", "safe": "ok"},
        }
    )

    assert redacted["partner_account_id"].startswith("anon_")
    assert redacted["email"] == "[REDACTED]"
    assert redacted["payment_payload"] == "[REDACTED]"
    assert redacted["nested"]["user_id"].startswith("anon_")
    assert redacted["nested"]["safe"] == "ok"
