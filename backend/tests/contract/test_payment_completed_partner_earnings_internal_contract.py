from __future__ import annotations

import json
from pathlib import Path

from src.main import app

INTERNAL_PAYMENT_EARNING_PATH = "/api/v1/payments/internal/partner-earnings/run"
INTERNAL_PAYMENT_EARNING_HEADER = "X-Payment-Settlement-Worker-Secret"


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def test_payment_completed_partner_earning_runner_is_excluded_from_public_openapi() -> None:
    live_schema = app.openapi()
    exported_schema = json.loads((_repo_root() / "backend/docs/api/openapi.json").read_text(encoding="utf-8"))

    assert INTERNAL_PAYMENT_EARNING_PATH not in live_schema["paths"]
    assert INTERNAL_PAYMENT_EARNING_PATH not in exported_schema["paths"]


def test_payment_completed_partner_earning_runner_is_excluded_from_browser_generated_clients() -> None:
    repo_root = _repo_root()
    for relative_path in (
        "frontend/src/lib/api/generated/types.ts",
        "admin/src/lib/api/generated/types.ts",
        "partner/src/lib/api/generated/types.ts",
    ):
        content = (repo_root / relative_path).read_text(encoding="utf-8")
        assert INTERNAL_PAYMENT_EARNING_PATH not in content
        assert INTERNAL_PAYMENT_EARNING_HEADER not in content
