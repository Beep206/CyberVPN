# CyberVPN PostHog Feature Flag Governance

**Date:** 2026-04-21  
**Status:** Frozen baseline for `T0.4`

This document freezes the approved feature-flag use cases, prohibited flag boundaries, evaluation model, fallback rule, ownership contract, and experiment governance baseline for `PostHog` in CyberVPN.

It is the `Phase 0` companion to:

- [2026-04-21-platform-foundation-target-state-architecture.md](../plans/2026-04-21-platform-foundation-target-state-architecture.md)
- [2026-04-21-platform-foundation-phase-0-execution-packet.md](../plans/2026-04-21-platform-foundation-phase-0-execution-packet.md)
- [posthog-product-taxonomy-and-privacy-baseline.md](posthog-product-taxonomy-and-privacy-baseline.md)

## 1. Canonical Decisions Frozen Here

The following decisions are fixed and are not reopened by this document:

1. `PostHog` is the canonical product-facing feature flag and experimentation platform.
2. Feature flags are for product behavior and rollout control, not for infrastructure or security kill switches.
3. CyberVPN must have one approved product-flag usage model and one deterministic fallback rule.
4. Every production flag must have an owner, purpose, scope, expected removal date, and cleanup rule.
5. Experiments are temporary and auditable; they are not a hiding place for permanent unowned configuration.

## 2. Current-State Mapping

Current repository baseline:

- [frontend/src/features/dev/lib/feature-flags.ts](/home/beep/projects/VPNBussiness/frontend/src/features/dev/lib/feature-flags.ts:1) is a local browser `localStorage` dev/testing toggle system.
- It is explicitly classified as `legacy dev-only`.
- It is not an approved production rollout mechanism.

Consequences:

1. Future `PostHog` flag integrations must not copy this local-state pattern into production flows.
2. Existing dev flags may remain for local development, but they must stay clearly segregated from product flags.
3. New product flags must use the governance contract defined in this document.

## 3. Allowed Feature Flag Use Cases

Approved flag categories:

- product UX rollouts;
- checkout copy or layout experiments;
- onboarding variants;
- partner dashboard UX variants;
- admin UX variants that do not change authorization decisions;
- beta-access groups;
- non-critical product feature exposure;
- experiment cohort assignment;
- staged product release exposure where fallback is safe and deterministic.

Rules:

1. Flags may change presentation, non-critical flow variants, or product exposure.
2. Flags must not become a substitute for source-of-truth business state.
3. Flags must be removable after rollout completion.

## 4. Prohibited Feature Flag Use Cases

The following uses are prohibited:

- auth authorization decisions;
- payment authorization logic;
- OpenBao policy behavior;
- PKI issuance policy;
- NATS subject security or routing rules;
- infrastructure kill switches;
- cluster fail-safe controls;
- VPN traffic safety controls;
- fleet emergency stop logic;
- certificate revocation logic;
- secrets delivery behavior;
- compliance-critical audit behavior.

Rule:

If disabling or mis-evaluating a flag could create a security, infrastructure, or trust-boundary incident, that behavior is outside PostHog feature flag scope.

## 5. Approved Product Flag Usage Model

CyberVPN uses one approved product-flag usage model:

```text
PostHog defines the flag
  -> backend or edge-owned wrapper resolves it server-side when the backend owns behavior
  -> result is safely bootstrapped to the client for UX rendering when needed
  -> application code consumes a typed wrapper, not raw SDK calls spread across the UI
```

Rules:

1. Backend-owned behavior prefers server-side evaluation.
2. Client-side evaluation is allowed only for explicitly approved UX cases.
3. Frontend code should consume project wrappers or typed access helpers, not arbitrary direct flag lookups throughout the codebase.
4. Every flag must have one owning code wrapper path during implementation phases.

## 6. Deterministic Fallback Rule

CyberVPN uses one fallback rule:

`If a flag value cannot be resolved, the application must use the contract-defined fallback value, which is default-off unless an explicitly approved safe fallback says otherwise.`

Consequences:

1. Undefined, stale, timed-out, or unreachable flag evaluations must not create ambiguous behavior.
2. Fallback behavior must be declared in the flag contract before rollout begins.
3. Cosmetic or equivalent-behavior flags may define another safe fallback only if documented.

## 7. Feature Flag Contract

Every production feature flag must define:

| Field | Meaning |
|---|---|
| `flag_key` | stable identifier used across code, product, and analytics |
| `owner` | responsible team or role |
| `purpose` | why the flag exists |
| `created_at` | creation date |
| `expected_removal_date` | cleanup deadline |
| `allowed_contexts` | `server`, `client`, or `both` |
| `fallback_behavior` | deterministic fallback rule |
| `blast_radius` | scope of impact if misconfigured |
| `experiment_link` | linked experiment id when applicable |
| `cleanup_rule` | removal condition after rollout or experiment |
| `documentation_link` | source document or ADR |

Rules:

1. A production flag without a contract is prohibited.
2. Flags without an owner or removal date are prohibited.
3. Long-lived flags require explicit re-approval rather than silent expiration drift.

## 8. Exposure And Analytics Rules

Feature flag analytics must follow these rules:

1. Exposure events are recorded intentionally through the approved taxonomy.
2. Exposure data must not include blocked privacy fields from the product analytics baseline.
3. Exposure should be tied to the evaluated flag key and cohort, not raw payload dumps.
4. Server-side exposure is preferred where server-side evaluation owns behavior.

## 9. Experiment Governance Template

Every experiment must define:

- `experiment_key`
- `hypothesis`
- `owner`
- `primary_success_metric`
- `guardrail_metrics`
- `sample_definition`
- `exposure_event`
- `start_criteria`
- `stop_criteria`
- `rollback_rule`
- `privacy_review_required`

Frozen template example:

```text
experiment_key: checkout_payment_method_layout_v1
hypothesis: simplified payment layout increases checkout_step_completed
owner: growth-product
primary_success_metric: checkout_payment_captured / checkout_started
guardrail_metrics: payment_failed rate, refund rate, support contacts
sample_definition: eligible checkout sessions in approved locales
exposure_event: experiment_exposure_recorded
start_criteria: feature contract approved and privacy baseline satisfied
stop_criteria: required sample reached or max calendar window reached
rollback_rule: disable experiment if guardrail metrics regress past threshold
privacy_review_required: no
```

## 10. Lifecycle And Cleanup Rules

Flags and experiments must not become permanent clutter.

Required lifecycle:

1. create contract;
2. implement typed wrapper;
3. run rollout or experiment;
4. measure result;
5. remove dead path or graduate behavior;
6. close contract and analytics references.

Rules:

1. Expired flags must be removed, not ignored.
2. Completed experiments must be archived and cleaned up.
3. Permanent configuration belongs in application configuration or business state, not in stale experiment flags.

## 11. Ownership And Approval

Approval expectations for production flag families:

| Flag type | Required approval |
|---|---|
| product UX rollout | product owner + engineering owner |
| checkout experiment | product owner + billing owner |
| partner/admin UX | product owner + owning engineering team |
| privacy-sensitive experiment | product owner + security/privacy review |

Security or infrastructure approvals do not legitimize prohibited flag categories. Those categories remain out of scope.

## 12. Implementation Implications For Later Phases

This document freezes these later-phase expectations:

1. Product flag rollout must be implemented through a governed wrapper model, not raw ad hoc SDK calls.
2. Existing dev-only flags may stay local, but must remain visibly separate from `PostHog` production flags.
3. Infrastructure and security controls must use dedicated control planes and configuration systems, not PostHog.
4. Phase 1 and Phase 3 work must treat this contract as the authoritative flag-governance baseline.
