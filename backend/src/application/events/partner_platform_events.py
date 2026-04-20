"""Canonical event families reserved for the partner platform baseline."""

PARTNER_PLATFORM_EVENT_FAMILIES = {
    "storefront": (
        "storefront.resolved",
        "storefront.binding.changed",
    ),
    "realm": (
        "realm.session.issued",
        "realm.session.revoked",
    ),
    "order": (
        "order.created",
        "order.finalized",
        "order.refunded",
    ),
    "attribution": (
        "attribution.touchpoint.recorded",
        "attribution.result.finalized",
    ),
    "growth_reward": (
        "growth_reward.allocation.created",
        "growth_reward.allocation.reversed",
    ),
    "settlement": (
        "settlement.earning.created",
        "settlement.earning_hold.released",
        "settlement.statement.generated",
        "settlement.statement.closed",
        "settlement.statement.reopened",
        "settlement.payout_account.created",
        "settlement.payout_account.verified",
        "settlement.payout_account.default_selected",
        "settlement.payout_instruction.created",
        "settlement.payout_instruction.approved",
        "settlement.payout.execution.requested",
        "settlement.payout.execution.submitted",
        "settlement.payout.execution.reconciled",
    ),
    "risk": (
        "risk.review.opened",
        "risk.decision.recorded",
        "risk.review.resolved",
        "risk.evidence.attached",
        "risk.governance_action.recorded",
    ),
    "rollout": (
        "rollout.pilot_cohort.created",
        "rollout.pilot_cohort.activated",
        "rollout.pilot_cohort.paused",
        "rollout.runbook_acknowledged",
        "rollout.rollback_drill.recorded",
        "rollout.go_no_go.recorded",
    ),
    "entitlement": (
        "entitlement.grant.activated",
        "entitlement.grant.revoked",
    ),
    "service_access": (
        "service_access.device_credential.registered",
        "service_access.device_credential.revoked",
        "service_access.delivery_channel.resolved",
        "service_access.delivery_channel.archived",
    ),
    "reporting": (
        "reporting.export.generated",
        "reporting.mart.refreshed",
    ),
}
