from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _write_snapshot(path: Path) -> None:
    snapshot = {
        "metadata": {
            "snapshot_id": "phase8-shadow-001",
            "source": "phase8-shadow-fixture",
            "replay_generated_at": "2026-04-19T15:30:00+00:00",
            "default_max_divergence_rate": "0.25",
        },
        "phase3_snapshot": {
            "metadata": {
                "snapshot_id": "phase3-shadow-ref-001",
                "source": "phase8-shadow-fixture",
                "replay_generated_at": "2026-04-19T15:30:00+00:00",
            },
            "orders": [
                {"id": "order-1", "user_id": "user-1", "storefront_id": "storefront-1"},
                {"id": "order-2", "user_id": "user-2", "storefront_id": "storefront-2"},
                {"id": "order-3", "user_id": "user-3", "storefront_id": "storefront-3"},
            ],
            "partner_codes": [
                {"id": "code-aff-1", "partner_account_id": None},
                {"id": "code-res-1", "partner_account_id": "account-res-1"},
            ],
            "touchpoints": [
                {
                    "id": "tp-explicit-1",
                    "order_id": "order-1",
                    "touchpoint_type": "explicit_code",
                    "partner_code_id": "code-aff-1",
                    "occurred_at": "2026-04-19T14:00:00+00:00",
                    "created_at": "2026-04-19T14:00:00+00:00",
                }
            ],
            "bindings": [
                {
                    "id": "binding-reseller-2",
                    "user_id": "user-2",
                    "storefront_id": "storefront-2",
                    "binding_type": "reseller_binding",
                    "binding_status": "active",
                    "owner_type": "reseller",
                    "partner_account_id": "account-res-1",
                    "partner_code_id": "code-res-1",
                    "effective_from": "2026-04-19T13:50:00+00:00",
                    "created_at": "2026-04-19T13:50:00+00:00",
                }
            ],
            "attribution_results": [
                {
                    "order_id": "order-1",
                    "owner_type": "affiliate",
                    "owner_source": "explicit_code",
                    "partner_account_id": None,
                    "partner_code_id": "code-aff-1",
                    "winning_touchpoint_id": "tp-explicit-1",
                    "winning_binding_id": None,
                },
                {
                    "order_id": "order-2",
                    "owner_type": "reseller",
                    "owner_source": "persistent_reseller_binding",
                    "partner_account_id": "account-res-1",
                    "partner_code_id": "code-res-1",
                    "winning_touchpoint_id": None,
                    "winning_binding_id": "binding-reseller-2",
                },
                {
                    "order_id": "order-3",
                    "owner_type": "none",
                    "owner_source": None,
                    "partner_account_id": None,
                    "partner_code_id": None,
                    "winning_touchpoint_id": None,
                    "winning_binding_id": None,
                },
            ],
            "growth_reward_allocations": [
                {
                    "id": "alloc-referral-3",
                    "order_id": "order-3",
                    "reward_type": "referral_credit",
                    "allocation_status": "allocated",
                }
            ],
            "renewal_orders": [
                {
                    "order_id": "order-2",
                    "renewal_mode": "manual",
                    "renewal_sequence_number": 1,
                    "effective_owner_type": "reseller",
                    "effective_owner_source": "persistent_reseller_binding",
                    "effective_partner_account_id": "account-res-1",
                    "effective_partner_code_id": "code-res-1",
                    "payout_eligible": True,
                }
            ],
        },
        "analytical_snapshot": {
            "metadata": {
                "snapshot_id": "phase7-shadow-ref-001",
                "source": "phase8-shadow-fixture",
                "replay_generated_at": "2026-04-19T15:30:00+00:00",
            },
            "orders": [
                {
                    "id": "order-1",
                    "user_id": "user-1",
                    "sale_channel": "web",
                    "currency_code": "USD",
                    "order_status": "committed",
                    "settlement_status": "paid",
                    "commission_base_amount": "50.00",
                    "displayed_price": "50.00",
                    "created_at": "2026-04-19T14:10:00+00:00",
                },
                {
                    "id": "order-2",
                    "user_id": "user-2",
                    "sale_channel": "web",
                    "currency_code": "USD",
                    "order_status": "committed",
                    "settlement_status": "paid",
                    "commission_base_amount": "70.00",
                    "displayed_price": "70.00",
                    "created_at": "2026-04-19T14:20:00+00:00",
                },
                {
                    "id": "order-3",
                    "user_id": "user-3",
                    "sale_channel": "web",
                    "currency_code": "USD",
                    "order_status": "committed",
                    "settlement_status": "paid",
                    "commission_base_amount": "15.00",
                    "displayed_price": "15.00",
                    "created_at": "2026-04-19T14:30:00+00:00",
                },
            ],
            "order_attribution_results": [
                {
                    "id": "attr-1",
                    "order_id": "order-1",
                    "partner_account_id": None,
                    "partner_code_id": "code-aff-1",
                    "owner_type": "affiliate",
                    "owner_source": "explicit_code",
                    "created_at": "2026-04-19T14:11:00+00:00",
                },
                {
                    "id": "attr-2",
                    "order_id": "order-2",
                    "partner_account_id": "account-res-1",
                    "partner_code_id": "code-res-1",
                    "owner_type": "reseller",
                    "owner_source": "persistent_reseller_binding",
                    "created_at": "2026-04-19T14:21:00+00:00",
                },
                {
                    "id": "attr-3",
                    "order_id": "order-3",
                    "partner_account_id": None,
                    "partner_code_id": None,
                    "owner_type": "none",
                    "owner_source": None,
                    "created_at": "2026-04-19T14:31:00+00:00",
                },
            ],
            "commissionability_evaluations": [
                {"id": "eval-1", "order_id": "order-1", "commissionability_status": "eligible"},
                {"id": "eval-2", "order_id": "order-2", "commissionability_status": "eligible"},
                {"id": "eval-3", "order_id": "order-3", "commissionability_status": "eligible"},
            ],
            "renewal_orders": [
                {
                    "id": "renewal-2",
                    "order_id": "order-2",
                    "effective_partner_account_id": "account-res-1",
                    "effective_partner_code_id": "code-res-1",
                    "effective_owner_type": "reseller",
                    "effective_owner_source": "persistent_reseller_binding",
                    "created_at": "2026-04-19T14:22:00+00:00",
                }
            ],
            "refunds": [],
            "payment_disputes": [],
            "earning_events": [
                {
                    "id": "earning-1",
                    "partner_account_id": "account-res-1",
                    "currency_code": "USD",
                    "available_amount": "20.00",
                    "created_at": "2026-04-19T14:45:00+00:00",
                }
            ],
            "partner_statements": [
                {
                    "id": "statement-1",
                    "partner_account_id": "account-res-1",
                    "currency_code": "USD",
                    "available_amount": "20.00",
                    "superseded_by_statement_id": None,
                    "created_at": "2026-04-19T14:50:00+00:00",
                }
            ],
            "outbox_events": [
                {
                    "id": "evt-1",
                    "event_family": "order",
                    "event_name": "order.created",
                    "created_at": "2026-04-19T15:00:00+00:00",
                }
            ],
            "outbox_publications": [
                {
                    "id": "pub-1",
                    "outbox_event_id": "evt-1",
                    "consumer_key": "analytics_mart",
                    "publication_status": "published",
                    "created_at": "2026-04-19T15:01:00+00:00",
                },
                {
                    "id": "pub-2",
                    "outbox_event_id": "evt-1",
                    "consumer_key": "operational_replay",
                    "publication_status": "published",
                    "created_at": "2026-04-19T15:02:00+00:00",
                },
            ],
        },
        "legacy_shadow_observations": [
            {
                "order_id": "order-1",
                "legacy_owner_type": "affiliate",
                "legacy_owner_source": "explicit_code",
                "legacy_partner_account_id": None,
                "legacy_partner_code_id": "code-aff-1",
                "legacy_rule_path": [
                    "explicit_code_touchpoint_selected",
                    "owner_type_inferred_as_affiliate",
                ],
            },
            {
                "order_id": "order-2",
                "legacy_owner_type": "reseller",
                "legacy_owner_source": "persistent_reseller_binding",
                "legacy_partner_account_id": "account-res-1",
                "legacy_partner_code_id": "code-res-1",
                "legacy_binding_type": None,
                "legacy_binding_partner_account_id": None,
                "legacy_binding_partner_code_id": None,
                "legacy_renewal_effective_owner_type": "affiliate",
                "legacy_renewal_effective_owner_source": "initial_order_inheritance",
                "legacy_renewal_partner_account_id": None,
                "legacy_renewal_partner_code_id": None,
                "legacy_rule_path": ["persistent_reseller_binding_selected"],
            },
        ],
        "approved_divergences": [
            {
                "id": "approval-binding-gap",
                "code": "legacy_binding_reference_missing",
                "lane_key": "renewal_chain",
                "approval_reference": "risk-approval-001",
            }
        ],
        "lane_tolerances": [
            {"lane_key": "creator_affiliate", "max_divergence_rate": "0.10"},
            {"lane_key": "renewal_chain", "max_divergence_rate": "0.40"},
            {"lane_key": "consumer_referral", "max_divergence_rate": "0.00"},
        ],
    }
    path.write_text(json.dumps(snapshot, indent=2) + "\n", encoding="utf-8")


def test_phase8_attribution_shadow_builder_and_summary_are_deterministic(tmp_path: Path) -> None:
    repo_root = _repo_root()
    builder = repo_root / "backend/scripts/build_phase8_attribution_shadow_pack.py"
    summary_script = repo_root / "backend/scripts/print_phase8_attribution_shadow_summary.py"
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
    assert report["metadata"]["report_version"] == "phase8-attribution-shadow-v1"
    assert report["metadata"]["generated_at"] == "2026-04-19T15:30:00+00:00"
    assert report["phase3_reference"]["status"] == "green"
    assert report["analytical_reference"]["status"] == "green"
    assert report["reconciliation"]["status"] == "red"
    assert report["reconciliation"]["mismatch_counts"]["legacy_binding_reference_missing"] == 1
    assert report["reconciliation"]["mismatch_counts"]["legacy_renewal_owner_type_mismatch"] == 1
    assert report["reconciliation"]["mismatch_counts"]["legacy_renewal_owner_source_mismatch"] == 1
    assert report["reconciliation"]["mismatch_counts"]["legacy_renewal_partner_account_mismatch"] == 1
    assert report["reconciliation"]["mismatch_counts"]["missing_legacy_shadow_observation"] == 1
    assert report["reconciliation"]["mismatch_counts"]["lane_divergence_rate_exceeded"] == 2
    assert report["pilot_promotion_gate"]["blocking_lanes"] == ["consumer_referral", "renewal_chain"]
    assert len(report["reconciliation"]["tolerated_mismatches"]) == 1
    tolerated = report["reconciliation"]["tolerated_mismatches"][0]
    assert tolerated["code"] == "legacy_binding_reference_missing"
    assert tolerated["approval_reference"] == "risk-approval-001"

    lane_views = {item["lane_key"]: item for item in report["lane_divergence_views"]}
    assert lane_views["creator_affiliate"]["within_tolerance"] is True
    assert lane_views["renewal_chain"]["within_tolerance"] is False
    assert lane_views["consumer_referral"]["within_tolerance"] is False

    result = subprocess.run(  # noqa: S603
        [sys.executable, str(summary_script), "--input", str(output_a)],
        check=True,
        cwd=repo_root,
        text=True,
        capture_output=True,
    )
    stdout = result.stdout
    assert "status: red" in stdout
    assert "phase3 reference: green" in stdout
    assert "analytical reference: green" in stdout
    assert "lane renewal_chain: rate=1.0000 max=0.40" in stdout
    assert "missing_legacy_shadow_observation: 1" in stdout
    assert "lane_divergence_rate_exceeded: 2" in stdout


def test_phase8_attribution_shadow_doc_covers_vocabulary_and_tolerances() -> None:
    repo_root = _repo_root()
    content = (
        repo_root / "docs/testing/partner-platform-phase8-attribution-shadow-pack.md"
    ).read_text(encoding="utf-8")

    for required_term in (
        "replay_generated_at",
        "phase3_snapshot",
        "analytical_snapshot",
        "legacy_shadow_observations",
        "approved_divergences",
        "lane_tolerances",
        "legacy_owner_type_mismatch",
        "legacy_binding_reference_missing",
        "legacy_renewal_owner_type_mismatch",
        "lane_divergence_rate_exceeded",
        "identical input snapshots with fixed `replay_generated_at` produce identical packs",
    ):
        assert required_term in content
