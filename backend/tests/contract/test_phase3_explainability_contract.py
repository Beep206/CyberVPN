from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from src.main import app
from src.presentation.api.v1.router import API_V1_PREFIX

REQUIRED_PHASE3_PATHS = (
    f"{API_V1_PREFIX}/orders/{{order_id}}/explainability",
    f"{API_V1_PREFIX}/attribution/orders/{{order_id}}/result",
    f"{API_V1_PREFIX}/growth-rewards/allocations",
    f"{API_V1_PREFIX}/renewal-orders/by-order/{{order_id}}",
)


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _exported_openapi_schema() -> dict:
    repo_root = _repo_root()
    exported_schema_path = repo_root / "backend" / "docs" / "api" / "openapi.json"
    assert exported_schema_path.exists(), "backend/docs/api/openapi.json must exist for frozen Phase 3 contracts"
    return json.loads(exported_schema_path.read_text(encoding="utf-8"))


def _write_snapshot(path: Path) -> None:
    snapshot = {
        "metadata": {
            "snapshot_id": "phase3-synthetic-001",
            "source": "phase3-evidence-fixture",
            "replay_generated_at": "2026-04-18T13:30:00+00:00",
        },
        "orders": [
            {
                "id": "order-1",
                "user_id": "user-1",
                "storefront_id": "storefront-1",
            },
            {
                "id": "order-2",
                "user_id": "user-1",
                "storefront_id": "storefront-1",
            },
        ],
        "partner_codes": [
            {"id": "code-aff", "partner_account_id": None},
            {"id": "code-res", "partner_account_id": "account-res"},
        ],
        "touchpoints": [
            {
                "id": "tp-explicit",
                "order_id": "order-1",
                "touchpoint_type": "explicit_code",
                "partner_code_id": "code-aff",
                "occurred_at": "2026-04-18T13:00:00+00:00",
                "created_at": "2026-04-18T13:00:00+00:00",
            },
            {
                "id": "tp-passive",
                "order_id": "order-2",
                "touchpoint_type": "passive_click",
                "partner_code_id": "code-aff",
                "occurred_at": "2026-04-18T13:01:00+00:00",
                "created_at": "2026-04-18T13:01:00+00:00",
            },
        ],
        "bindings": [
            {
                "id": "binding-reseller",
                "user_id": "user-1",
                "storefront_id": "storefront-1",
                "binding_type": "reseller_binding",
                "binding_status": "active",
                "owner_type": "reseller",
                "partner_account_id": "account-res",
                "partner_code_id": "code-res",
                "effective_from": "2026-04-18T12:59:00+00:00",
                "created_at": "2026-04-18T12:59:00+00:00",
            }
        ],
        "attribution_results": [
            {
                "order_id": "order-1",
                "owner_type": "affiliate",
                "owner_source": "explicit_code",
                "partner_account_id": None,
                "partner_code_id": "code-aff",
                "winning_touchpoint_id": "tp-explicit",
                "winning_binding_id": None,
            },
            {
                "order_id": "order-2",
                "owner_type": "affiliate",
                "owner_source": "passive_click",
                "partner_account_id": None,
                "partner_code_id": "code-aff",
                "winning_touchpoint_id": "tp-passive",
                "winning_binding_id": None,
            },
        ],
        "growth_reward_allocations": [
            {
                "id": "alloc-1",
                "order_id": "order-1",
                "reward_type": "invite_reward",
                "allocation_status": "allocated",
            },
            {
                "id": "alloc-2",
                "order_id": "order-2",
                "reward_type": "referral_credit",
                "allocation_status": "allocated",
            },
        ],
        "renewal_orders": [
            {
                "order_id": "order-2",
                "renewal_mode": "manual",
                "renewal_sequence_number": 1,
                "effective_owner_type": "reseller",
                "effective_owner_source": "persistent_reseller_binding",
                "payout_eligible": True,
            }
        ],
    }
    path.write_text(json.dumps(snapshot, indent=2) + "\n", encoding="utf-8")


def test_phase3_live_and_exported_openapi_contain_explainability_surfaces() -> None:
    live_schema = app.openapi()
    exported_schema = _exported_openapi_schema()

    for required_path in REQUIRED_PHASE3_PATHS:
        assert required_path in live_schema["paths"]
        assert required_path in exported_schema["paths"]


def test_phase3_explainability_replay_builder_and_summary_are_deterministic(tmp_path: Path) -> None:
    repo_root = _repo_root()
    builder = repo_root / "backend/scripts/build_phase3_explainability_replay_pack.py"
    summary_script = repo_root / "backend/scripts/print_phase3_explainability_replay_summary.py"
    snapshot_path = tmp_path / "snapshot.json"
    output_a = tmp_path / "report-a.json"
    output_b = tmp_path / "report-b.json"

    _write_snapshot(snapshot_path)

    for output_path in (output_a, output_b):
        subprocess.run(  # noqa: S603
            [sys.executable, str(builder), "--input", str(snapshot_path), "--output", str(output_path)],
            check=True,
            cwd=repo_root,
        )

    first = output_a.read_text(encoding="utf-8")
    second = output_b.read_text(encoding="utf-8")
    assert first == second

    report = json.loads(first)
    assert report["metadata"]["report_version"] == "phase3-explainability-replay-v1"
    assert report["metadata"]["generated_at"] == "2026-04-18T13:30:00+00:00"
    assert report["comparison"]["status"] == "red"
    assert report["comparison"]["mismatch_counts"]["owner_type_mismatch"] == 1
    assert report["comparison"]["mismatch_counts"]["owner_source_mismatch"] == 1
    assert report["comparison"]["mismatch_counts"]["partner_code_mismatch"] == 1
    assert report["comparison"]["mismatch_counts"]["partner_account_mismatch"] == 1
    assert report["order_cases"][0]["lane_views"]["invite_gift"]["active"] is True
    assert report["order_cases"][1]["lane_views"]["consumer_referral"]["active"] is True
    assert report["order_cases"][1]["lane_views"]["renewal_chain"]["active"] is True

    result = subprocess.run(  # noqa: S603
        [sys.executable, str(summary_script), "--input", str(output_a)],
        check=True,
        cwd=repo_root,
        text=True,
        capture_output=True,
    )
    assert "status: red" in result.stdout
    assert "owner_type_mismatch: 1" in result.stdout


def test_phase3_explainability_doc_covers_lane_views_and_replay_generated_at() -> None:
    repo_root = _repo_root()
    content = (
        repo_root / "docs/testing/partner-platform-phase3-explainability-and-replay-pack.md"
    ).read_text(encoding="utf-8")

    for required_term in (
        "replay_generated_at",
        "commercial_resolution_summary",
        "growth_reward_summary",
        "lane_views",
        "owner_type_mismatch",
        "consumer_referral",
        "reseller_distribution",
        "renewal_chain",
        "identical input snapshots with fixed `replay_generated_at` produce identical replay packs",
    ):
        assert required_term in content
