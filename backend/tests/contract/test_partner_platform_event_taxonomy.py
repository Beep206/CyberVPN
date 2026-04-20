from pathlib import Path

from src.application.events.partner_platform_events import PARTNER_PLATFORM_EVENT_FAMILIES


def _read_event_taxonomy() -> str:
    repo_root = Path(__file__).resolve().parents[3]
    return (repo_root / "docs/api/partner-platform-event-taxonomy.md").read_text(encoding="utf-8")


def test_event_taxonomy_document_contains_frozen_families() -> None:
    content = _read_event_taxonomy()

    for event_name in (
        "storefront.resolved",
        "realm.session.issued",
        "order.finalized",
        "attribution.result.finalized",
        "growth_reward.allocation.created",
        "settlement.statement.generated",
        "risk.review.opened",
        "risk.review.resolved",
        "risk.governance_action.recorded",
        "rollout.pilot_cohort.created",
        "rollout.runbook_acknowledged",
        "rollout.rollback_drill.recorded",
        "rollout.go_no_go.recorded",
        "entitlement.grant.activated",
        "reporting.export.generated",
    ):
        assert event_name in content


def test_application_event_registry_matches_document_baseline() -> None:
    flattened = {name for family in PARTNER_PLATFORM_EVENT_FAMILIES.values() for name in family}

    assert "storefront.resolved" in flattened
    assert "settlement.payout.execution.requested" in flattened
    assert "settlement.payout.execution.reconciled" in flattened
    assert "risk.evidence.attached" in flattened
    assert "rollout.pilot_cohort.activated" in flattened
    assert "rollout.runbook_acknowledged" in flattened
    assert "rollout.go_no_go.recorded" in flattened
    assert "reporting.mart.refreshed" in flattened
    assert len(flattened) >= 10
