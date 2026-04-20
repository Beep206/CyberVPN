# CyberVPN Partner Platform Phase 3 Execution Ticket Decomposition

**Date:** 2026-04-18  
**Status:** Execution ticket decomposition for `Phase 3` implementation start  
**Purpose:** translate `Phase 3` from the detailed phased implementation plan into executable backlog tickets with clear ownership, repository touchpoints, dependencies, acceptance criteria, and evidence requirements.

---

## 1. Document Role

This document is the `Phase 3` execution bridge between:

- the canonical specification package;
- the domain dependency matrix;
- the detailed phased implementation plan;
- the operational readiness package;
- the completed `Phase 2` gate evidence pack.

It exists so attribution, growth, risk, finance, QA, and support do not invent incompatible ownership logic on top of the now-canonical order domain.

This document does not reopen:

- identity and storefront rules already frozen in `Phase 1`;
- order, refund, dispute, and commissionability semantics already frozen in `Phase 2`;
- partner settlement semantics reserved for `Phase 4`;
- entitlement grant semantics reserved for `Phase 5`.

If a proposed `Phase 3` ticket changes any of those, the canonical documents must be updated first.

---

## 2. Execution Rules

Execution for `Phase 3` follows these rules:

1. `Phase 3` starts only after `Phase 2` gate evidence is green.
2. `attribution_touchpoints`, `customer_commercial_bindings`, `order_attribution_results`, and `growth_reward_allocations` must remain separate entity families.
3. `attribution_touchpoints` are append-only evidence records, not payout outcomes.
4. `customer_commercial_bindings` may constrain ownership, but they do not replace touchpoint evidence.
5. `order_attribution_results` are immutable per-order snapshots.
6. `growth_reward_allocations` must stay non-cash and separate from commercial payout ownership.
7. `Phase 3` must not leak `Phase 4` payout semantics into attribution or reward logic.
8. Every `Phase 3` ticket must produce at least one of:
   - merged code;
   - frozen API contract updates;
   - executable tests;
   - replay or explainability evidence.

---

## 3. Ticket Naming And Board Model

Ticket identifiers use the format:

- `T3.x` for `Phase 3`

Recommended workboards:

| Board | Scope | Primary owners |
|---|---|---|
| `B8` | touchpoints and bindings | backend attribution, QA |
| `B9` | order attribution and reward allocations | backend attribution, growth platform, risk |
| `B10` | qualifying events, renewals, explainability, replay | backend attribution, QA, support, finance ops |

Suggested backlog labels:

- `phase-3`
- `attribution`
- `touchpoints`
- `commercial-bindings`
- `growth-rewards`
- `qualifying-events`
- `renewals`
- `explainability`
- `blocking`

---

## 4. Sequencing Summary

| Ticket | Packet alignment | Primary board | Size | Hard blockers |
|---|---|---|---|---|
| `T3.1` | `P3.1` | `B8` | `M` | `Phase 2 gate` |
| `T3.2` | `P3.2` | `B8` | `M` | `Phase 2 gate`, `T3.1` contracts frozen |
| `T3.3` | `P3.3` | `B9` | `L` | `T3.1`, `T3.2`, `T2.6` |
| `T3.4` | `P3.4` | `B9` | `L` | `T2.3`, `T1.5`, `T1.6` |
| `T3.5` | `P3.5` | `B10` | `L` | `T3.3`, `T3.4`, `T2.6` |
| `T3.6` | `P3.6` | `B10` | `M` | `T3.3`, `T3.5`, `T2.3` |
| `T3.7` | `P3.7` | `B10` | `M` | `T3.3`, `T3.4`, `T3.5` |
| `T3.8` | phase-exit evidence | `B10` | `M` | `T3.1`, `T3.2`, `T3.3`, `T3.4`, `T3.5`, `T3.6`, `T3.7` |

`T3.1` and `T3.2` are the only valid starting tickets for `Phase 3` implementation.

---

## 5. Ticket Decomposition

## 5.1 `T3.1` Attribution Touchpoint Ingestion And Evidence Capture

**Packet alignment:** `P3.1`  
**Primary owners:** backend attribution  
**Supporting owners:** frontend, channel teams, QA

**Repository touchpoints:**

- Create: `backend/src/domain/entities/attribution_touchpoint.py`
- Create: `backend/src/infrastructure/database/models/attribution_touchpoint_model.py`
- Create: `backend/src/infrastructure/database/repositories/attribution_touchpoint_repo.py`
- Create: `backend/src/application/use_cases/attribution/`
- Create: `backend/src/presentation/api/v1/attribution/`
- Modify: `backend/src/presentation/api/v1/router.py`
- Modify: `backend/src/application/use_cases/commerce_sessions/create_quote_session.py`
- Modify: `backend/src/presentation/api/v1/quotes/`
- Create: `backend/tests/integration/test_attribution_touchpoints.py`
- Create: `backend/tests/contract/test_attribution_touchpoint_openapi_contract.py`

**Scope:**

- append-only touchpoint ingestion;
- canonical touchpoint vocabulary for explicit code, passive click, deep link, QR, and storefront-origin evidence;
- quote-path recording for at least explicit code and storefront-origin evidence;
- request-context snapshot capture for explainability and later attribution resolution.

**Acceptance criteria:**

- explicit code and storefront-origin touchpoints are recorded on the canonical quote path;
- passive click, deep link, and QR touchpoints are representable through the ingestion surface;
- touchpoints remain evidence-only and do not compute ownership or rewards;
- touchpoint records are listable for support and admin inspection.

**Evidence required:**

- OpenAPI contract test for attribution touchpoint routes;
- integration tests proving explicit code and storefront-origin capture on quote creation;
- enum registry updated with canonical touchpoint vocabulary.

## 5.2 `T3.2` Customer Commercial Bindings

**Packet alignment:** `P3.2`  
**Primary owners:** backend attribution  
**Supporting owners:** risk, support, QA

**Repository touchpoints:**

- Create: `backend/src/domain/entities/customer_commercial_binding.py`
- Create: `backend/src/infrastructure/database/models/customer_commercial_binding_model.py`
- Create: `backend/src/presentation/api/v1/commercial_bindings/`
- Create: `backend/tests/integration/test_customer_commercial_bindings.py`

**Scope:**

- persistent reseller binding;
- storefront default-owner binding;
- manual override or contract-assignment bindings;
- binding explainability inputs for later order resolution.

**Acceptance criteria:**

- reseller persistence can survive unrelated affiliate clicks;
- bindings are distinguishable from touchpoints;
- bindings can be inspected without mutating order results.

## 5.3 `T3.3` Order Attribution Resolver And Immutable Results

**Packet alignment:** `P3.3`  
**Primary owners:** backend attribution, risk  
**Supporting owners:** finance ops, support

**Repository touchpoints:**

- Create: `backend/src/domain/entities/order_attribution_result.py`
- Create: `backend/src/infrastructure/database/models/order_attribution_result_model.py`
- Create: `backend/src/application/use_cases/attribution/order_resolution/`
- Create: `backend/tests/integration/test_order_attribution_resolution.py`

**Scope:**

- deterministic precedence engine;
- immutable order-level result snapshot;
- explicit code, passive click, and persistent binding resolution;
- explainability payload for winner path and evidence used.

**Acceptance criteria:**

- one finalized order resolves to zero or one cash owner;
- explicit code beats passive click;
- reseller binding beats unrelated later click traffic;
- results remain reproducible after order finalization.

## 5.4 `T3.4` Growth Reward Allocations

**Packet alignment:** `P3.4`  
**Primary owners:** backend attribution, growth platform  
**Supporting owners:** risk, support

**Repository touchpoints:**

- Create: `backend/src/domain/entities/growth_reward_allocation.py`
- Create: `backend/src/infrastructure/database/models/growth_reward_allocation_model.py`
- Create: `backend/src/presentation/api/v1/growth_rewards/`
- Create: `backend/tests/integration/test_growth_reward_allocations.py`

**Scope:**

- invite reward allocations;
- referral credit allocations;
- bonus days and gift bonus outputs;
- non-cash reward references from orders or invite/referral actions.

**Acceptance criteria:**

- reward allocations do not become commercial owners;
- multiple growth rewards can coexist with one order if policy allows;
- reward outputs are referenceable by support and risk.

## 5.5 `T3.5` Stacking Matrix And Qualifying Event Evaluator

**Packet alignment:** `P3.5`  
**Primary owners:** backend attribution, risk  
**Supporting owners:** finance ops, QA

**Repository touchpoints:**

- Create: `backend/src/application/use_cases/attribution/qualifying_events/`
- Create: `backend/src/presentation/api/v1/policy_evaluation/`
- Create: `backend/tests/integration/test_stacking_and_qualifying_events.py`

**Scope:**

- promo versus partner code stacking;
- wallet impact on qualifying-first-payment logic;
- referral and affiliate mutual-exclusion rules;
- no-double-payout enforcement.

**Acceptance criteria:**

- qualifying-first-payment logic is explicit and testable;
- wallet-heavy or almost-free orders follow canonical qualification rules;
- double payout between referral and affiliate remains impossible.

## 5.6 `T3.6` Renewal Lineage And Renewal Ownership

**Packet alignment:** `P3.6`  
**Primary owners:** backend attribution  
**Supporting owners:** finance ops, support, risk

**Repository touchpoints:**

- Create: `backend/src/domain/entities/renewal_order.py`
- Create: `backend/src/infrastructure/database/models/renewal_order_model.py`
- Create: `backend/tests/integration/test_renewal_ownership.py`

**Scope:**

- renewal lineage from initial order;
- renewal owner inheritance and override rules;
- manual renew versus auto-renew semantics;
- explainability of renewal economics.

**Acceptance criteria:**

- renewal ownership is traceable to policy and prior order lineage;
- incompatible overrides are blocked or explicitly explained;
- renewal objects stay distinct from initial orders.

## 5.7 `T3.7` Explainability APIs And Replay Tooling

**Packet alignment:** `P3.7`  
**Primary owners:** backend attribution, QA  
**Supporting owners:** finance ops, support, BI

**Repository touchpoints:**

- Extend: `backend/src/presentation/api/v1/orders/explainability/`
- Create: replay/backfill scripts under `backend/scripts/`
- Create: `backend/tests/contract/test_phase3_explainability_contract.py`
- Create: validation docs under `docs/testing/`

**Scope:**

- explainability payloads for attribution winners and growth rewards;
- replay tooling for touchpoints, bindings, attribution results, and reward allocations;
- support-facing inspection baselines per lane.

**Acceptance criteria:**

- finance and support can inspect why a specific order resolved to a given owner;
- replay output can compare resolved winners against reference logic;
- at least one explainability case exists per active lane.

## 5.8 `T3.8` Phase 3 Gate And Evidence Pack

**Packet alignment:** phase-exit evidence  
**Primary owners:** QA, backend attribution  
**Supporting owners:** finance ops, risk, support enablement

**Repository touchpoints:**

- Create: `docs/testing/partner-platform-phase3-exit-evidence.md`
- Modify: `docs/plans/2026-04-17-partner-platform-operational-readiness-package.md`
- Create: `backend/tests/e2e/test_phase3_attribution_foundations.py`

**Scope:**

- freeze evidence for touchpoints, bindings, attribution results, rewards, and renewals;
- attach shadow and replay outputs;
- record unresolved but non-blocking residuals.

**Acceptance criteria:**

- schema and API freeze for attribution, growth rewards, and policy-evaluation families;
- shadow comparison of attribution winners exists within approved tolerance;
- support-facing explainability evidence exists for at least one case per lane.

---

## 6. Phase 3 Completion Gate

`Phase 3` is complete only when:

1. `T3.1` through `T3.7` are merged or explicitly waived by governance;
2. order attribution results are demonstrably deterministic and immutable;
3. growth reward allocations remain separate from commercial ownership in persistence and API shape;
4. qualifying-event and stacking logic are covered by executable tests;
5. the `Phase 3` evidence pack is green.
