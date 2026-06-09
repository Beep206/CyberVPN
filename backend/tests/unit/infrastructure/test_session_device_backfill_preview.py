"""Dry-run planner tests for legacy refresh token device backfill."""

import importlib.util
from pathlib import Path
from types import ModuleType


def _load_preview_module() -> ModuleType:
    script_path = Path(__file__).resolve().parents[3] / "scripts" / "preview_session_device_backfill.py"
    spec = importlib.util.spec_from_file_location("preview_session_device_backfill", script_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_backfill_preview_groups_active_refresh_rows_by_user_and_device() -> None:
    module = _load_preview_module()

    report = module.build_backfill_preview(
        [
            {
                "id": "token-1",
                "user_id": "user-1",
                "device_id": "device-a",
                "created_at": "2026-06-09T10:00:00Z",
                "last_used_at": "2026-06-09T10:10:00Z",
                "ip_address": "203.0.113.10",
                "user_agent": "Synthetic Browser/1",
            },
            {
                "id": "token-2",
                "user_id": "user-1",
                "device_id": "device-a",
                "created_at": "2026-06-09T10:20:00Z",
                "last_used_at": "2026-06-09T10:30:00Z",
                "ip_address": "203.0.113.11",
                "user_agent": "Synthetic Browser/2",
            },
            {
                "id": "token-3",
                "user_id": "user-1",
                "device_id": "device-b",
                "revoked_at": "2026-06-09T10:40:00Z",
            },
        ],
        default_auth_realm_id="realm-1",
        pepper_label="unit-test-pepper-label",
    )

    assert report["schema"] == "session-device-backfill.dry-run.v1"
    assert report["writes_database"] is False
    assert report["input_rows"] == 3
    assert report["device_candidates"] == 1
    assert report["skipped_rows"] == [{"id": "token-3", "reason": "revoked_token"}]

    candidate = report["candidates"][0]
    assert candidate["auth_realm_id"] == "realm-1"
    assert candidate["principal_subject"] == "user-1"
    assert candidate["legacy_refresh_token_count"] == 2
    assert candidate["legacy_refresh_token_ids"] == ["token-1", "token-2"]
    assert candidate["last_seen_at"] == "2026-06-09T10:30:00Z"
    assert len(candidate["device_key_hash"]) == 64
