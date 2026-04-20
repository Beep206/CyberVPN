# CyberVPN Partner Platform Event Taxonomy

**Date:** 2026-04-17  
**Status:** Draft event taxonomy baseline for `T0.5`

This document freezes the canonical event family naming baseline required before replay, reconciliation, shadow-mode comparison, and reporting scale-out.

## 1. Naming Rules

1. Event names are object-centric, not provider-centric.
2. Family names are frozen even if payloads expand later.
3. Event names use dot-separated lower-case identifiers.
4. Provider-specific terminology may appear only inside payload snapshots, not as canonical family names.

## 2. Frozen Event Families

### Storefront

- `storefront.resolved`
- `storefront.binding.changed`

### Realm

- `realm.session.issued`
- `realm.session.revoked`

### Order

- `order.created`
- `order.finalized`
- `order.refunded`

### Attribution

- `attribution.touchpoint.recorded`
- `attribution.result.finalized`

### Growth Reward

- `growth_reward.allocation.created`
- `growth_reward.allocation.reversed`

### Settlement

- `settlement.earning.created`
- `settlement.earning_hold.released`
- `settlement.statement.generated`
- `settlement.statement.closed`
- `settlement.statement.reopened`
- `settlement.payout_account.created`
- `settlement.payout_account.verified`
- `settlement.payout_account.default_selected`
- `settlement.payout_instruction.created`
- `settlement.payout_instruction.approved`
- `settlement.payout.execution.requested`
- `settlement.payout.execution.submitted`
- `settlement.payout.execution.reconciled`

### Risk

- `risk.review.opened`
- `risk.decision.recorded`
- `risk.review.resolved`
- `risk.evidence.attached`
- `risk.governance_action.recorded`

### Rollout

- `rollout.pilot_cohort.created`
- `rollout.pilot_cohort.activated`
- `rollout.pilot_cohort.paused`
- `rollout.runbook_acknowledged`
- `rollout.rollback_drill.recorded`
- `rollout.go_no_go.recorded`

### Entitlement

- `entitlement.grant.activated`
- `entitlement.grant.revoked`

### Service Access

- `service_access.device_credential.registered`
- `service_access.device_credential.revoked`
- `service_access.delivery_channel.resolved`
- `service_access.delivery_channel.archived`

### Reporting

- `reporting.export.generated`
- `reporting.mart.refreshed`

## 3. Minimum Payload Expectations

Every canonical event payload must be able to carry:

- event identifier
- event family name
- created timestamp
- actor or system source where relevant
- subject object identifiers
- correlation or request identifier where relevant

## 4. Canonical Rules

1. Shadow, replay, and reconciliation logic must reference these family names.
2. Event payload schema versions may evolve without renaming the canonical family.
3. `payment_dispute` remains the canonical dispute object; dispute events must still live under the normalized platform family chosen later, not under provider-native names.
4. Reliable publication uses canonical `outbox_events` and `outbox_publications`; the outbox layer must not mint alternate event names.
