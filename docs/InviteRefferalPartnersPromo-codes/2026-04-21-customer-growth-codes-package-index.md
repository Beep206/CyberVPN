# Customer Growth Codes & Rewards Package

**Date:** 2026-04-21  
**Status:** planning baseline  
**Scope:** client growth codes, rewards, checkout integration, admin operations, metrics, audit, and selected partner touchpoints  
**Out of scope:** partner revenue codes, partner payouts, partner attribution ownership model

---

## Purpose

This package defines the target model for the CyberVPN customer growth codes layer:

- invite codes
- referral codes
- promo codes
- gift codes
- reward allocations
- checkout code resolution
- wallet and entitlement interaction
- admin control surfaces
- tracking and audit
- metrics and observability
- limited partner-facing touchpoints

This package is intentionally separate from the partner portal package. These mechanics are customer growth mechanisms, not partner program mechanics.

---

## Baseline References

Read these first:

1. [Current State Invite / Referral / Promo / Gift Codes](./2026-04-21-current-state-invite-referral-promo-gift-codes.md)
2. [Partner Portal Full Overview](../plans/2026-04-21-partner-portal-full-overview-general-and-technical.md)

---

## Documents

1. [Customer Growth Codes Rulebook](./2026-04-21-customer-growth-codes-rulebook.md)
2. [Growth Code Taxonomy And Compatibility Matrix](./2026-04-21-growth-code-taxonomy-and-compatibility-matrix.md)
3. [Growth Codes Tracking, Attribution, And Audit Spec](./2026-04-21-growth-codes-tracking-attribution-and-audit-spec.md)
4. [Growth Codes Data Model Spec](./2026-04-21-growth-codes-data-model-spec.md)
5. [Growth Codes Checkout, Entitlement, Wallet Integration Spec](./2026-04-21-growth-codes-checkout-entitlement-wallet-integration-spec.md)
6. [Growth Codes Client Frontend UX And IA Spec](./2026-04-21-growth-codes-client-frontend-ux-and-ia-spec.md)
7. [Growth Codes Admin Operations Spec](./2026-04-21-growth-codes-admin-operations-spec.md)
8. [Growth Codes Partner Portal Touchpoints Spec](./2026-04-21-growth-codes-partner-portal-touchpoints-spec.md)
9. [Growth Codes API DTO Contract Freeze Spec](./2026-04-21-growth-codes-api-dto-contract-freeze-spec.md)
10. [Growth Codes Risk, Anti-Abuse, And Compliance Spec](./2026-04-21-growth-codes-risk-anti-abuse-and-compliance-spec.md)
11. [Growth Codes Analytics, Observability, And Reporting Spec](./2026-04-21-growth-codes-analytics-observability-and-reporting-spec.md)
12. [Growth Codes Lifecycle And State Machine Spec](./2026-04-21-growth-codes-lifecycle-and-state-machine-spec.md)
13. [Growth Codes E2E Conformance Test Plan](./2026-04-21-growth-codes-e2e-conformance-test-plan.md)
14. [Growth Codes Implementation Plan](./2026-04-21-growth-codes-implementation-plan.md)

---

## Reading Order

### Product and policy first

1. Rulebook
2. Taxonomy And Compatibility Matrix
3. Tracking, Attribution, And Audit Spec
4. Lifecycle And State Machine Spec

### Core backend contract layer

5. Data Model Spec
6. Checkout, Entitlement, Wallet Integration Spec
7. API DTO Contract Freeze Spec

### Product surfaces

8. Client Frontend UX And IA Spec
9. Admin Operations Spec
10. Partner Portal Touchpoints Spec

### Safety and operations

11. Risk, Anti-Abuse, And Compliance Spec
12. Analytics, Observability, And Reporting Spec
13. E2E Conformance Test Plan

### Execution

14. Implementation Plan

---

## Canonical Decisions Locked By This Package

- invite, referral, promo, gift and partner codes are different business mechanisms
- promo, referral and partner incentives must not be treated as one generic discount stack
- frontend must never decide eligibility, stacking or reward allocation
- all code effects must pass through backend quote or redeem flows
- every code must be traceable across issuer, owner, touchpoint, registration, redemption, reward and admin audit
- admin console and metrics are first-class requirements, not secondary reporting after launch
- partner portal may see only approved campaign touchpoints, not customer referral mechanics
- gift redemption is entitlement-oriented, not wallet top-up oriented
- referral rewards are non-withdrawable growth rewards, not partner earnings

---

## Immediate Next Step

Execution has already progressed through:

- `GC-WB-01` to `GC-WB-09`
- `GC-WB-10` referral cutover and canonical reward lifecycle
- `GC-WB-11` customer growth notification delivery and preferences
- `GC-WB-12` delivery execution and admin review controls
- `GC-WB-13` support timeline, export, and delivery forensics
- `GC-WB-14` customer troubleshooting and recovery surface
- `GC-WB-15` guided channel repair and structured support escalation
- `Phase 12 / GC-WB-16` repair automation and escalation closure
- `Phase 13 / GC-WB-17` growth notification conformance and rollout hardening
- `Phase 15 / GC-WB-19` growth reporting and rollup layer
- `Phase 16 / GC-WB-20` scheduled rollup refresh and executive reporting hardening
- `Phase 17 / GC-WB-21` reporting distribution, retention, and lifecycle maintenance
- `Phase 18 / GC-WB-22` reporting template governance and recipient policy controls
- `Phase 19 / GC-WB-23` reporting governance audit trail and coverage forensics
- `Phase 20 / GC-WB-24` reporting governance conformance, evidence, and gate automation
- `Phase 22 / GC-WB-26` reporting governance recovery automation and follow-up controls

Operationally still pending:

- `Phase 14 / GC-WB-18` growth notification staging rollout and governance gate
- `Phase 21 / GC-WB-25` growth reporting governance staging rollout and protected gate activation

Prepared in repository for the reporting-governance rollout slice:

- staging smoke runner
- gate-readiness assessment helper and decision artifacts
- staging rollout runbook
- disabled GitHub governance ruleset payload and sync helper
- remote disabled ruleset `customer-growth-reporting-governance-main-gate`
- required-check handoff document

The remaining step is the live staging rollout window and evidence capture against a real environment, followed by an explicit decision on whether to enable the protected gate.

Current post-plan code execution has also progressed through:

- `Phase 22 / GC-WB-26` governance recovery follow-up lifecycle, scheduled reminders, overdue queue management, and operator resolve or dismiss controls

The next operational step after repo-side `GC-WB-26` remains:

- `Phase 21 / GC-WB-25` live staging rollout execution and protected gate enablement decision

The next code-facing step after `GC-WB-26` is no longer required by the package baseline; any further slices are optional hardening beyond the current target-state implementation.

The full workboard breakdown is defined in the implementation plan.

---

## Legacy / Non-Canonical References

These documents are historical references only.
They are not canonical for target-state growth codes implementation.

- [codes-wallet-system-ru.md](./codes-wallet-system-ru.md)
- [reactive-booping-mist.md](./reactive-booping-mist.md)

Known conflicts with target-state package:

- indefinite referral commission
- simultaneous partner + promo + referral stacking
- mixed withdrawable wallet semantics
- old partner-code model
