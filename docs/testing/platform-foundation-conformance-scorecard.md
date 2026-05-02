# CyberVPN Platform Foundation Conformance Scorecard

**Date:** 2026-04-22  
**Status:** canonical scorecard template  
**Purpose:** convert the production-conformance criteria from the platform target-state document into a reusable scoring model for `Gate B`, `Gate C`, and `Gate D`.

---

## 1. Scorecard Role

This scorecard is the authoritative scoring layer for:

- [../plans/2026-04-21-platform-foundation-target-state-architecture.md](../plans/2026-04-21-platform-foundation-target-state-architecture.md)
- [../plans/2026-04-21-platform-foundation-phased-implementation-plan.md](../plans/2026-04-21-platform-foundation-phased-implementation-plan.md)
- [../evidence/platform-foundation/platform-foundation-phase-evidence-template.md](../evidence/platform-foundation/platform-foundation-phase-evidence-template.md)

The source of truth for the conformance criteria remains Section `16` of the target-state architecture.

This scorecard does not invent new architecture. It only translates the frozen criteria into a consistent gate-scoring model.

---

## 2. Scoring Scale

| Score | Meaning |
|---|---|
| `0` | not implemented, contradicted, or unsupported by evidence |
| `1` | documented, owned, and frozen, but not yet proven in runtime |
| `2` | implemented and validated in non-prod or controlled rehearsal scope |
| `3` | production-conformant, drill-backed, and ready for `Gate D` closure |
| `N/A` | not yet in scope for the named gate |

Important interpretation:

- `1` is not operational readiness.
- `2` is non-prod readiness, not final conformance.
- `3` requires evidence, drills where applicable, and explicit sign-off.

---

## 3. Gate Threshold Rules

| Gate | What the score means |
|---|---|
| `Gate B` | foundational services exist safely in non-prod; only the criteria marked with a `Gate B` floor are gating |
| `Gate C` | end-to-end non-prod platform flows are real; only the criteria marked with a `Gate C` floor are gating |
| `Gate D` | production conformance; every criterion with a `Gate D` floor must meet it |

Rules:

- a gate is blocked if any in-scope criterion scores below its minimum floor;
- a linked temporary exception may explain a tolerated shortfall only when the phased plan allows it;
- no temporary exception may permanently waive a `Gate D` production-conformance criterion;
- score changes must be backed by linked evidence, not verbal status.

---

## 4. Conformance Matrix

Fill the `Current score` and `Evidence links` columns for each gate run.

| Id | Criterion | Canonical source | Owner lane | Gate B minimum | Gate C minimum | Gate D minimum | Evidence links | Current score | Notes |
|---|---|---|---|---|---|---|---|---|---|
| `C01` | business-critical events use transactional outbox | Section `16.1` | backend platform | `1` | `2` | `3` | fill in | `TBD` | outbox is contractual at `B`, operational by `C` |
| `C02` | NATS streams and durable consumers are declared and governed | Section `16.2` | backend platform, infra/platform | `1` | `2` | `3` | fill in | `TBD` | no ad-hoc production state |
| `C03` | every durable consumer has owner, replay, idempotency, alert policy, and runbook | Section `16.3` | backend platform | `1` | `2` | `3` | fill in | `TBD` | contract and runtime ownership both required |
| `C04` | payment-to-notification and payment-to-dashboard `p95 <= 1s` | Section `16.4` | backend platform, SRE | `N/A` | `2` | `3` | fill in | `TBD` | `Gate C` proves non-prod latency path |
| `C05` | loss of one NATS node does not lose committed business events | Section `16.5` | infra/platform, SRE | `2` | `2` | `3` | fill in | `TBD` | requires quorum and drill evidence |
| `C06` | NATS downtime creates outbox backlog, not silent event loss | Section `16.6` | backend platform, SRE | `1` | `2` | `3` | fill in | `TBD` | backlog and recovery must be visible |
| `C07` | Node Fleet Controller owns durable desired and observed fleet state | Section `16.7` | transport/backend, infra/platform | `N/A` | `N/A` | `3` | fill in | `TBD` | becomes gating only when controller is authoritative |
| `C08` | external VPN and edge nodes are provisioned through controller workflows | Section `16.8` | transport/backend, infra/platform | `N/A` | `N/A` | `3` | fill in | `TBD` | manual secret copy and runbook-only paths must be retired |
| `C09` | node traffic eligibility requires enrollment, health, synthetic checks, and runtime-adapter acknowledgment | Section `16.9` | transport/backend | `N/A` | `N/A` | `3` | fill in | `TBD` | must be proven on exercised workflows |
| `C10` | DPI or provider failover executes only through policy guardrails | Section `16.10` | transport/backend, SRE | `N/A` | `N/A` | `3` | fill in | `TBD` | uncontrolled heuristics are non-conformant |
| `C11` | PostHog receives critical commercial events through server-side or authoritative bridge paths | Section `16.11` | product, backend platform | `1` | `1` | `3` | fill in | `TBD` | authoritative bridge becomes gating at `D` |
| `C12` | PostHog does not receive VPN usage, destination, or raw traffic telemetry | Section `16.12` | product, security | `1` | `2` | `3` | fill in | `TBD` | privacy baseline must be runtime-validated by `C` |
| `C13` | PostHog feature flags are not used for infra or security kill switches | Section `16.13` | product, platform architecture | `1` | `2` | `3` | fill in | `TBD` | requires code-path review and deterministic fallback evidence |
| `C14` | product analytics, operational observability, and authoritative business state remain distinct domains | Section `16.14` | platform architecture | `1` | `2` | `3` | fill in | `TBD` | source-of-truth boundaries must remain explicit |
| `C15` | backup and restore drills exist for NATS, OpenBao, PostgreSQL, GitOps state, PostHog, and fleet reprovisioning | Section `16.15` | SRE, infra/platform | `1` | `2` | `3` | fill in | `TBD` | `Gate D` requires the full drill bundle |

---

## 5. Domain Coverage Notes

The scorecard tracks only the canonical production-conformance criteria.

Additional domains that still require gate evidence through the evidence template:

- `OpenBao` topology, auth, trust, and restore evidence;
- `Flux` and GitOps bootstrap or rollback evidence;
- `Alloy` migration evidence across Kubernetes and external nodes;
- concrete `Node Fleet Controller` workflow transcripts;
- `PostHog` placement, privacy, and flag-governance evidence beyond the specific criteria above.

These domains may block a gate even when the scorecard rows above are satisfied.

---

## 6. Gate Evaluation Workflow

Use this order for every gate run:

1. Attach the concrete gate evidence pack built from the canonical evidence template.
2. Fill the `Evidence links` and `Current score` columns for all in-scope criteria.
3. Confirm that every in-scope criterion meets the minimum floor for the current gate.
4. Record any linked temporary exceptions or residual blockers.
5. End the evidence pack with an explicit `PASSED` or `BLOCKED` statement.

---

## 7. Scorecard Snapshot Template

Copy this block into each concrete gate pack:

```md
## Conformance Scorecard Snapshot

**Assessment date:** YYYY-MM-DD
**Gate:** Gate <B|C|D>
**Assessed by:** <names or owner lanes>

| Id | Minimum for gate | Current score | Result | Evidence |
|---|---|---|---|---|
| `C01` | fill in | fill in | pass or fail | fill in |
| `C02` | fill in | fill in | pass or fail | fill in |
| ... | ... | ... | ... | ... |
```

Recommended result rule:

- `pass` only if `Current score >= Minimum for gate`;
- `fail` if lower, unsupported by evidence, or contradicted by a registered blocker.
