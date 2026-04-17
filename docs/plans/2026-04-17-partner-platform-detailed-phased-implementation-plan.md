# CyberVPN Partner Platform Detailed Phased Implementation Plan

**Date:** 2026-04-17  
**Status:** Detailed phase-by-phase execution plan  
**Purpose:** translate the target-state architecture, domain specification package, delivery program, and dependency matrix into an executable implementation decomposition for engineering, data, finance operations, risk, support, and QA teams.

---

## 1. Document Role

This document is the detailed execution companion to the platform specification package.

It expands the high-level delivery program into:

- phase-by-phase implementation packets;
- parallel workstreams inside each phase;
- contract freeze expectations;
- validation and evidence packs;
- lane readiness gates;
- handoff points into migration, cutover, QA, operational readiness, and rollout planning.

This document is not the canonical business rulebook and is not the cutover package. It exists to let multiple teams execute the same platform plan without inventing hidden intermediate steps.

This document should be read together with:

- [2026-04-17-partner-platform-target-state-architecture.md](2026-04-17-partner-platform-target-state-architecture.md)
- [2026-04-17-partner-platform-domain-dependency-matrix.md](2026-04-17-partner-platform-domain-dependency-matrix.md)
- [2026-04-17-partner-platform-delivery-program.md](2026-04-17-partner-platform-delivery-program.md)
- the full domain specification package listed in [2026-04-17-partner-platform-spec-package-index.md](2026-04-17-partner-platform-spec-package-index.md)

---

## 2. Execution Principles

The detailed plan follows these execution principles:

1. `Order` is the commercial center.
2. `partner_code` remains the external commercial carrier, but economic behavior must resolve through versioned policy objects.
3. Consumer growth programs and partner revenue programs must never collapse into one shared implementation path.
4. No payable partner lane is production-ready until settlement, reserves, disputes, and reconciliation exist.
5. No cross-channel rollout is valid until service entitlements are channel-neutral and realm-aware.
6. `Wallet` is not the accounting system for partner payouts.
7. Risk foundations are early dependencies, not late hardening.
8. Event vocabulary must stabilize before replay, shadow comparison, finance reconciliation, and reporting scale-out.
9. Shadow-mode evidence is required before any broad production activation.
10. Frontend surfaces must consume backend-owned contracts rather than reproducing business logic locally.
11. Each phase must end with contract evidence, not only with feature completion claims.

---

## 3. Release Progression Model

Every phase may move work through the following release rings:

| Ring | Meaning |
|---|---|
| `R0` | schema, API, and workflow development in isolated environments |
| `R1` | synthetic and internal staff validation |
| `R2` | shadow-mode evaluation against legacy or reference behavior |
| `R3` | limited trusted-partner or controlled customer pilot |
| `R4` | broad production activation |

Rules:

- `R4` is never allowed without the required `R2` evidence.
- partner payout behavior cannot move past `R1` before finance reconciliation exists.
- performance lane cannot move to `R3` without risk review workflows, traffic declarations, and payout holds.
- partner storefront cannot move to `R4` until realm isolation, merchant behavior, and support routing are proven.

---

## 4. Workstream Topology

| Workstream | Scope | Primary owners | Main outputs |
|---|---|---|---|
| `WS0` Program Governance And Contracts | phase governance, glossary, contract freeze discipline, RACI | platform architecture, product, program management | freezes, acceptance criteria, decision log |
| `WS1` Brand, Storefront, Identity, And Policy Foundations | brands, storefronts, realms, principals, policies, legal acceptance | platform/backend, security, admin | realm-aware foundations and policy versioning |
| `WS2` Product, Merchant, Billing, And Commerce | offers, pricebooks, merchant behavior, orders, refunds, disputes | backend commerce, billing, finance platform | canonical commercial object model |
| `WS3` Attribution, Growth, And Renewal Logic | touchpoints, bindings, attribution, growth rewards, renewals | growth/platform backend, data, risk | deterministic ownership and reward engines |
| `WS4` Finance And Settlement | earnings, holds, reserves, statements, payouts, reconciliation | finance platform, finance ops | partner finance operating layer |
| `WS5` Risk, Compliance, And Governance | risk graph, reviews, declarations, legal evidence, governance actions | risk platform, support, finance ops | anti-abuse and control layer |
| `WS6` Service Identity And Entitlements | service identities, entitlement grants, provisioning, channel adapters | backend platform, channel teams | channel-neutral service access |
| `WS7` Surface Delivery | official frontend, partner storefront, partner portal, admin | web frontend, admin/platform, design | operator and customer surfaces |
| `WS8` Analytics And Reporting | event layer, marts, exports, reconciliations, dashboards | data/BI, finance ops, risk, backend | trustworthy platform reporting |
| `WS9` Migration, Replay, QA, And Readiness | backfills, replay, test packs, pilot evidence, readiness review | QA, platform/infra, all domain owners | proof that rollout is safe |

`WS0`, `WS8`, and `WS9` span the whole program. The other workstreams activate heavily in specific phases.

---

## 5. Phase Overview

| Phase | Primary focus | Main workstreams | Major unlocks |
|---|---|---|---|
| `Phase 0` | rule, metric, and contract freeze | `WS0`, `WS8`, `WS9` | stable implementation vocabulary |
| `Phase 1` | `L1` foundations and early risk | `WS1`, `WS5`, `WS9` | realms, storefronts, partner orgs, policy versions |
| `Phase 2` | merchant and order core | `WS2`, `WS5`, `WS9` | canonical order domain and dispute normalization |
| `Phase 3` | attribution, growth, qualifying events, renewals | `WS3`, `WS5`, `WS8`, `WS9` | deterministic ownership and reward logic |
| `Phase 4` | settlement, statements, payouts, finance controls | `WS4`, `WS5`, `WS8`, `WS9` | auditable partner finance |
| `Phase 5` | service identity and entitlements | `WS6`, `WS8`, `WS9` | channel-neutral access layer |
| `Phase 6` | customer, partner, and admin surfaces | `WS7`, `WS1`, `WS4`, `WS5`, `WS6`, `WS9` | usable platform surfaces |
| `Phase 7` | channel parity and analytical readiness | `WS6`, `WS7`, `WS8`, `WS9` | reporting truth and channel completeness |
| `Phase 8` | shadow mode, pilot, and production-readiness hardening | all workstreams | safe path to broad activation |

---

## 6. Detailed Phase Decomposition

## 6.1 Phase 0. Canonical Rule Freeze And Delivery Mobilization

**Goal:** remove ambiguity before schema, API, and workflow implementation begins.

**Entry prerequisites:**

- target-state architecture approved;
- domain spec package approved;
- dependency matrix approved.

**Implementation packets:**

| Packet | Description | Primary workstreams | Blocking inputs |
|---|---|---|---|
| `P0.1` | freeze canonical glossary, enums, and owner semantics | `WS0` | target-state architecture |
| `P0.2` | freeze metric definitions and reconciliation vocabulary | `WS0`, `WS8` | rulebook, analytics spec |
| `P0.3` | freeze policy version lifecycle semantics | `WS0`, `WS1` | target-state architecture, data model spec |
| `P0.4` | freeze API conventions: auth families, idempotency, async jobs, error model | `WS0` | API spec package |
| `P0.5` | freeze draft event taxonomy for orders, attribution, rewards, finance, risk, entitlements, and reporting | `WS0`, `WS8` | target-state architecture, analytics spec, lifecycle spec |
| `P0.6` | define ownership model, review cadence, and acceptance sign-off flow | `WS0` | delivery program |
| `P0.7` | define synthetic-data, replay, and QA evidence strategy | `WS8`, `WS9` | delivery program, lifecycle spec |

**Primary outputs:**

- approved glossary and metric dictionary;
- frozen canonical enums and owner semantics;
- draft event taxonomy baseline;
- published phase governance model;
- approved contract-freeze checklist;
- approved QA evidence checklist.

**Parallelism notes:**

- only documentation and planning work is parallelizable here;
- no schema or public contract work should start before `P0.1` through `P0.4` are complete.

**Phase exit evidence:**

- signed glossary package;
- signed metric glossary;
- approved API contract baseline;
- approved draft event taxonomy baseline;
- approved phase sign-off template.

---

## 6.2 Phase 1. Brand, Storefront, Identity, Policy, Partner Organization, And Early Risk Foundations

**Goal:** establish the platform namespace and actor model required by every later domain.

**Entry prerequisites:**

- Phase 0 exit complete.

**Implementation packets:**

| Packet | Description | Primary workstreams | Blocking inputs |
|---|---|---|---|
| `P1.1` | build brand and storefront core: brands, storefronts, host resolution, profile bindings | `WS1` | `P0.1`, `P0.3` |
| `P1.2` | implement auth realms, principal classes, sessions, token audiences, scope families | `WS1` | `P0.1`, `P0.4` |
| `P1.3` | implement partner account, partner account users, roles, permissions, workspace memberships | `WS1` | `P0.1` |
| `P1.4` | implement offer, pricebook, and program-eligibility foundations needed for later order snapshots | `WS1`, `WS2` | `P1.1`, `P0.3` |
| `P1.5` | implement policy version objects, effective dating, approval states, and legal document acceptance | `WS1`, `WS5` | `P0.3`, `P0.4` |
| `P1.6` | implement early risk graph: risk subjects, identifiers, links, baseline eligibility checks | `WS5` | `P1.2`, `P1.3` |

**Primary outputs:**

- realm-aware identity core;
- storefront core with binding anchors;
- partner workspace identity model;
- policy version lifecycle foundation;
- accepted-legal-document evidence model;
- early risk identity graph.

**Can run in parallel after start:**

- `P1.1` and `P1.2` can run in parallel after Phase 0;
- `P1.3` can run mostly in parallel with `P1.2`;
- `P1.6` starts once identity and partner-account primitives exist.

**Validation packs:**

- same-email different-realm registration tests;
- no cross-login across realms tests;
- role and scope enforcement tests;
- host-based storefront resolution tests;
- accepted-legal-document evidence capture tests;
- risk-subject linkage tests.

**Phase exit evidence:**

- schema freeze for storefront, realm, partner account, policy-version, and risk foundation objects;
- API freeze for auth, partner-account, storefront, policy, and legal-acceptance surfaces;
- audit evidence that policy changes capture actor attribution;
- internal demo showing realm isolation across official and partner surfaces.

---

## 6.3 Phase 2. Product, Merchant, Billing, Tax, Disputes, And Order Core

**Goal:** establish the canonical commercial object and all liability snapshots that surround it.

**Entry prerequisites:**

- Phase 1 exit complete.

**Implementation packets:**

| Packet | Description | Primary workstreams | Blocking inputs |
|---|---|---|---|
| `P2.1` | implement merchant profiles, invoice profiles, billing descriptors, tax behavior snapshots | `WS2` | `P1.1`, `P1.5` |
| `P2.2` | implement quote sessions and checkout sessions with storefront, realm, policy, and merchant context | `WS2` | `P1.1`, `P1.2`, `P1.4`, `P2.1` |
| `P2.3` | implement orders and order items as canonical committed commercial objects | `WS2` | `P2.2` |
| `P2.4` | implement payment attempts, retry semantics, and commit idempotency | `WS2` | `P2.2`, `P2.3` |
| `P2.5` | implement refunds, canonical payment disputes, and chargeback outcome normalization | `WS2`, `WS5` | `P2.3`, `P2.4`, `P2.1` |
| `P2.6` | implement commissionability evaluation scaffolding and order snapshot explainability | `WS2`, `WS3` | `P2.3`, `P2.5` |
| `P2.7` | build order-domain migration and backfill harness from legacy payment-centric flows | `WS9` | `P2.3`, `P2.4`, `P2.5` |

**Primary outputs:**

- canonical order domain;
- normalized dispute object model;
- merchant and tax snapshots on orders;
- commissionability preconditions for later phases;
- backfill path out of payment-centric legacy logic.

**Parallelism notes:**

- `P2.1` can begin immediately once Phase 1 exits;
- `P2.5` can partially start in parallel with late `P2.4`, but no dispute normalization should finalize before order and payment-attempt contracts freeze;
- `P2.7` can start as a replay harness before full data migration.

**Validation packs:**

- multiple payment attempts for a single order tests;
- wallet-plus-card mixed payment tests if applicable;
- partial refund tests;
- dispute subtype normalization tests;
- tax snapshot reproducibility tests;
- order snapshot reproducibility tests.

**Phase exit evidence:**

- schema freeze for quote, checkout, order, payment-attempt, refund, and payment-dispute models;
- API freeze for quote, checkout, order, refund, and dispute families;
- reconciliation pack proving that legacy operational totals can be mapped into the new order vocabulary;
- internal order-history review demonstrating order-first explainability.

---

## 6.4 Phase 3. Attribution, Growth Rewards, Stacking, Qualifying Events, And Renewals

**Goal:** make commercial ownership and non-cash reward logic deterministic at order level.

**Entry prerequisites:**

- Phase 2 exit complete.

**Implementation packets:**

| Packet | Description | Primary workstreams | Blocking inputs |
|---|---|---|---|
| `P3.1` | implement attribution touchpoint ingestion for explicit codes, passive clicks, deep links, QR, and surface-origin evidence | `WS3` | `P1.1`, `P1.2`, `P2.2` |
| `P3.2` | implement customer commercial bindings for reseller persistence and other long-lived ownership constraints | `WS3` | `P1.3`, `P2.3`, `P1.6` |
| `P3.3` | implement order attribution resolver and immutable attribution results | `WS3` | `P3.1`, `P3.2`, `P2.3`, `P2.6` |
| `P3.4` | implement growth reward allocations for invite, referral credit, bonus days, and gift outputs | `WS3` | `P2.3`, `P1.4`, `P1.6` |
| `P3.5` | implement stacking matrix and qualifying-event evaluator | `WS3`, `WS5` | `P3.3`, `P3.4`, `P1.5`, `P2.6` |
| `P3.6` | implement renewal lineage, renewal ownership, and recurring-economics rules | `WS3` | `P2.3`, `P3.3`, `P3.5` |
| `P3.7` | implement explainability APIs and replay tooling for attribution and growth outcomes | `WS3`, `WS8`, `WS9` | `P3.3`, `P3.4`, `P3.5` |

**Primary outputs:**

- deterministic order attribution results;
- separated growth reward allocation layer;
- program compatibility and qualifying-event engine;
- renewal ownership semantics;
- explainability payloads for finance, support, and partner ops.

**Parallelism notes:**

- `P3.1` and `P3.2` can run in parallel;
- `P3.4` can start before `P3.3` completes, but only on the separated non-cash model;
- `P3.7` should start as soon as early outputs from `P3.3` exist so replay harnesses are available before settlement work begins.

**Validation packs:**

- explicit code versus passive click precedence tests;
- reseller binding persistence tests;
- no double payout between referral and affiliate tests;
- qualifying-first-payment tests;
- renewal inheritance and override tests;
- explainability replay comparison tests.

**Phase exit evidence:**

- schema freeze for touchpoints, bindings, attribution results, reward allocations, and renewal lineage;
- API freeze for attribution, growth rewards, and policy evaluation surfaces;
- shadow comparison of attribution winners against legacy or reference logic within approved tolerance;
- support-facing explainability evidence for at least one case per lane.
- canonical domain event naming freeze for commerce, attribution, growth rewards, settlement, risk, and entitlement domains before Phase 4 work begins.

---

## 6.5 Phase 4. Finance, Settlement, Statements, Payout Accounts, Payout Execution, And Adjustments

**Goal:** create a true partner-finance operating layer independent of consumer wallet behavior.

**Entry prerequisites:**

- Phase 3 exit complete.

**Implementation packets:**

| Packet | Description | Primary workstreams | Blocking inputs |
|---|---|---|---|
| `P4.1` | implement earning events, holds, reserves, and hold-release policies | `WS4` | `P3.3`, `P3.4`, `P3.5` |
| `P4.2` | implement settlement periods and partner statements with close, reopen, and adjustment semantics | `WS4` | `P4.1`, `P2.5` |
| `P4.3` | implement partner payout accounts, payout instructions, and payout eligibility checks | `WS4`, `WS5` | `P1.3`, `P1.6`, `P4.1` |
| `P4.4` | implement payout executions, maker-checker workflow, and execution audit | `WS4` | `P4.2`, `P4.3` |
| `P4.5` | implement dispute-, refund-, and clawback-driven adjustment policies | `WS4`, `WS5` | `P2.5`, `P4.1`, `P4.2` |
| `P4.6` | implement finance reconciliation views and liability reporting baselines | `WS4`, `WS8` | `P4.2`, `P4.4`, `P4.5` |

**Primary outputs:**

- statement-based partner finance;
- auditable payout setup and execution;
- reserve and hold controls;
- typed financial adjustments;
- finance-approved liability views.

**Parallelism notes:**

- `P4.3` can begin as soon as payout semantics and partner identity are stable;
- `P4.6` should begin before payout execution goes beyond internal dry-run;
- no partner-surface finance UI should ship before `P4.2` and `P4.3` are stable.

**Validation packs:**

- statement close and reopen tests;
- payout-account verification and approval tests;
- maker-checker approval tests;
- refund and chargeback adjustment tests;
- reserve extension and payout-freeze tests;
- finance reconciliation pack.

**Phase exit evidence:**

- schema freeze for statement, payout account, payout instruction, payout execution, hold, reserve, and adjustment objects;
- API freeze for statement, payout account, payout execution, and reconciliation surfaces;
- finance sign-off that wallet is no longer treated as the accounting system for partner payouts;
- internal dry-run payout evidence with immutable audit trail.

---

## 6.6 Phase 5. Service Identity, Entitlements, Provisioning, And Access Delivery

**Goal:** detach service access from storefront-specific account assumptions.

**Entry prerequisites:**

- Phase 3 exit complete;
- Phase 4 may run in parallel, but service access cannot rely on unfinished payout surfaces.

**Implementation packets:**

| Packet | Description | Primary workstreams | Blocking inputs |
|---|---|---|---|
| `P5.1` | implement service identities and provisioning profiles | `WS6` | `P1.2`, `P2.3` |
| `P5.2` | implement entitlement grants and entitlement lifecycle transitions | `WS6` | `P5.1`, `P2.3`, `P3.4` |
| `P5.3` | implement device credentials and access delivery channels | `WS6` | `P5.1`, `P5.2`, `P1.1` |
| `P5.4` | implement admin and support observability around entitlements and consumption surfaces | `WS6`, `WS7`, `WS8` | `P5.2`, `P5.3` |
| `P5.5` | build migration path from legacy subscription/provisioning semantics to entitlement-driven service access | `WS6`, `WS9` | `P5.2`, `P5.3` |

**Primary outputs:**

- channel-neutral entitlement layer;
- service identities independent of storefront-specific login assumptions;
- delivery-channel adapters for service access;
- support and analytics visibility into purchase surface versus service-consumption surface.

**Parallelism notes:**

- `P5.1` can begin before full Phase 4 completion;
- `P5.4` and `P5.5` should start before surface rollout so channels are not retrofitted later.

**Validation packs:**

- entitlement grant lifecycle tests;
- provisioning and revocation tests;
- realm-aware access delivery tests;
- channel parity tests for service access;
- legacy subscription to entitlement reconciliation tests.

**Phase exit evidence:**

- schema freeze for service identities, entitlements, credentials, and provisioning profiles;
- API freeze for entitlement and provisioning surfaces;
- cross-channel parity proof across at least web and one non-web consumption channel;
- support demo showing purchase versus consumption context separation.

---

## 6.7 Phase 6. Official Frontend, Partner Storefront, Partner Portal, And Admin Surfaces

**Goal:** expose the platform through the right user and operator surfaces without leaking logic into UI.

**Entry prerequisites:**

- Phase 4 and Phase 5 exits complete.

**Implementation packets:**

| Packet | Description | Primary workstreams | Blocking inputs |
|---|---|---|---|
| `P6.1` | integrate official CyberVPN frontend with new quote, order, attribution, and entitlement contracts | `WS7` | `P2.3`, `P3.3`, `P5.2` |
| `P6.2` | build generic multi-brand `partner-storefront` engine with host resolution, realm routing, and pricebook binding | `WS7`, `WS1` | `P1.1`, `P1.2`, `P1.4`, `P5.2` |
| `P6.3` | build partner portal and workspace surfaces for codes, statements, payout accounts, traffic declarations, and reporting views | `WS7`, `WS4`, `WS5` | `P1.3`, `P4.2`, `P4.3`, `P3.7` |
| `P6.4` | build admin surfaces for support, finance, attribution, disputes, governance, and entitlements | `WS7`, `WS4`, `WS5`, `WS6` | `P2.5`, `P3.7`, `P4.6`, `P5.4` |
| `P6.5` | enforce surface policy matrix across official web, partner storefront, partner portal, and admin surfaces | `WS7`, `WS1`, `WS5` | `P1.1`, `P1.5`, `P3.5` |
| `P6.6` | implement support routing, communication profile behavior, and legal-surface integration | `WS7`, `WS1`, `WS5` | `P1.1`, `P1.5`, `P6.2` |

**Primary outputs:**

- official CyberVPN frontend aligned with target-state rules;
- multi-brand storefront engine;
- partner portal with finance and governance-aware operator flows;
- admin surfaces that do not rely on direct database access;
- surface policy enforcement across all core surfaces.

**Parallelism notes:**

- `P6.1` and `P6.2` can run in parallel after prerequisite APIs stabilize;
- `P6.3` should not start final UI assembly before statement and payout-account APIs are frozen;
- `P6.4` can begin in vertical slices as backend explainability surfaces become available.

**Validation packs:**

- host-based storefront resolution tests;
- official-surface no-markup enforcement tests;
- partner-portal RBAC tests;
- surface-policy matrix tests;
- realm-aware login and session tests;
- support-routing and communication-profile tests.

**Phase exit evidence:**

- UI contract freeze for official frontend, partner storefront, partner portal, and admin core modules;
- realm-isolation proof across official and partner storefront logins;
- partner portal evidence showing statements, payout accounts, and traffic declarations working from APIs only;
- support demo proving brand-specific support and communication routing.

---

## 6.8 Phase 7. Channel Parity, Event Layer, Reporting, And Partner Exports

**Goal:** make the platform measurable, explainable, and available across all supported channels.

**Entry prerequisites:**

- Phase 6 exit complete.

**Implementation packets:**

| Packet | Description | Primary workstreams | Blocking inputs |
|---|---|---|---|
| `P7.1` | implement reliable outbox and event publication for commercial, finance, risk, and entitlement domains | `WS8`, `WS9` | `P2.3`, `P3.3`, `P4.2`, `P5.2` |
| `P7.2` | build analytical marts, canonical grains, and reconciliation views | `WS8` | `P7.1`, `P4.6` |
| `P7.3` | build partner dashboards, exports, and explainability reports | `WS8`, `WS7` | `P7.2`, `P6.3`, `P3.7`, `P4.6` |
| `P7.4` | implement Telegram Bot and Telegram Mini App parity on identity, order, entitlements, and reporting contracts | `WS6`, `WS7` | `P5.2`, `P6.5`, `P7.1` |
| `P7.5` | implement mobile and desktop parity on identity, order, entitlements, and reporting contracts | `WS6`, `WS7` | `P5.2`, `P6.5`, `P7.1` |
| `P7.6` | implement partner API, reporting API, and postback/webhook readiness on canonical contracts | `WS7`, `WS8` | `P3.7`, `P4.6`, `P7.1` |

**Primary outputs:**

- reliable event layer;
- canonical analytical marts;
- partner-facing dashboards and exports;
- channel parity for major surfaces;
- external reporting and integration APIs.

**Parallelism notes:**

- `P7.4`, `P7.5`, and `P7.6` can run in parallel once shared contracts are frozen;
- `P7.2` should begin before full channel rollout to avoid retroactive metric reconstruction.

**Validation packs:**

- event idempotency and replay tests;
- warehouse versus OLTP reconciliation tests;
- partner export contract tests;
- channel parity tests for entitlements and order history;
- postback delivery and signature tests.

**Phase exit evidence:**

- event-contract freeze;
- reporting-schema freeze;
- partner export evidence approved by finance and partner ops;
- parity proof across official web and at least two additional channels.

---

## 6.9 Phase 8. Advanced Risk Workflows, Shadow Mode, Pilot, And Production Readiness

**Goal:** prove that the platform can survive real traffic, partner behavior, finance operations, and support load without violating core invariants.

**Entry prerequisites:**

- Phases 1 through 7 complete.

**Implementation packets:**

| Packet | Description | Primary workstreams | Blocking inputs |
|---|---|---|---|
| `P8.1` | complete advanced risk-review workflows, manual review queues, evidence attachments, and governance actions | `WS5`, `WS7` | `P1.6`, `P2.5`, `P3.7`, `P4.5`, `P6.4` |
| `P8.2` | harden policy acceptance, traffic declarations, creative approvals, and dispute-case overlays | `WS5` | `P6.3`, `P6.4`, `P2.5`, `P7.6` |
| `P8.3` | run shadow attribution, shadow settlement, and shadow reporting against pilot traffic | `WS8`, `WS9`, `WS3`, `WS4` | `P3.7`, `P4.6`, `P7.2` |
| `P8.4` | execute limited pilots for selected lanes and surfaces with finance, support, and risk sign-off | all workstreams | `P8.1`, `P8.2`, `P8.3` |
| `P8.5` | produce production-readiness evidence package and handoff into cutover plan | `WS0`, `WS9` | `P8.4` |

**Primary outputs:**

- advanced governance tooling;
- shadow-mode evidence across attribution, settlement, and reporting;
- pilot evidence by lane and by surface;
- production-readiness evidence package.

**Validation packs:**

- shadow versus live attribution comparison;
- shadow versus live statement comparison;
- cross-realm abuse simulation tests;
- payout dry-run reconciliation tests;
- support runbook rehearsal;
- rollback rehearsal evidence.

**Phase exit evidence:**

- finance, support, risk, product, and engineering sign-off on pilot evidence;
- approved production-readiness package;
- unresolved blocker list reduced to cutover-only items;
- explicit go or no-go recommendation per lane.

---

## 7. Lane Readiness Map

The five lanes do not become production-ready at the same time.

| Lane | Earliest internal ring | Earliest limited pilot | Broad activation preconditions |
|---|---|---|---|
| `Invite / Gift` | Phase 3 | Phase 6 | Phase 8 evidence proving no cash-owner conflict and entitlement parity |
| `Consumer Referral Credits` | Phase 3 | Phase 6 | Phase 8 evidence proving caps, anti-abuse, and no recursive payout behavior |
| `Creator / Affiliate` | Phase 4 | Phase 6 | Phase 8 evidence proving statements, payout holds, and explainable attribution |
| `Performance / Media Buyer` | Phase 4 internal only | Phase 8 | Phase 8 evidence proving risk reviews, traffic declarations, postbacks, reserves, and probation controls |
| `Reseller / API / Distribution` | Phase 4 | Phase 6 or Phase 7 depending on surface scope | Phase 8 evidence proving storefront isolation, markup policy enforcement, and settlement correctness |

Interpretation:

- consumer-growth lanes become logically ready earlier, but still require surface and risk evidence;
- revenue lanes are blocked on settlement and governance maturity;
- performance lane must remain the most conservative lane in release sequencing.

---

## 8. Cross-Phase Freeze And Evidence Model

Every phase must produce the following artifacts before it is considered complete:

| Artifact | Required in every phase |
|---|---|
| Schema package | yes |
| API or event contract delta | yes |
| Validation pack | yes |
| Replay or shadow evidence when relevant | yes |
| Audit and explainability review | yes for phases 1-8 |
| Support and operator impact note | yes for phases 4-8 |
| Rollback impact note | yes for phases that change live behavior |

Mandatory rule:

- a phase cannot claim completion on implementation alone;
- it must also prove contract stability, test evidence, and operational explainability.

Event discipline rule:

- draft event taxonomy freeze is required in Phase 0;
- canonical domain event naming freeze is required by the end of Phase 3;
- full reliable outbox and event publication still lands in Phase 7.

---

## 9. Cross-Phase Dependencies That Must Stay Visible

The following dependencies are easy to underestimate and must stay explicit in project tracking:

1. `accepted_legal_documents` blocks more than compliance. It also affects identity, checkout, dispute handling, and support explainability.
2. `surface_policy_matrix_versions` blocks official frontend, partner storefront, and cross-channel behavior.
3. `partner_payout_accounts` is not only a finance object. It also blocks partner portal completion and operational approvals.
4. `payment_dispute` is upstream of finance adjustments, risk overlays, partner reporting, and support runbooks.
5. `partner_traffic_declarations` and `creative_approvals` are mandatory prerequisites for performance-lane scaling.
6. `growth_reward_allocations` must remain separate from commercial ownership even when the same order triggers both.
7. `service_identities` and `entitlement_grants` must be ready before mobile, desktop, Telegram, or partner API parity work can finish.

---

## 10. Detailed Planning Outputs Produced By This Plan

The execution-layer artifacts produced from this plan now include:

1. [2026-04-17-partner-platform-operational-readiness-package.md](2026-04-17-partner-platform-operational-readiness-package.md)
2. [2026-04-17-partner-platform-environment-specific-cutover-runbooks.md](2026-04-17-partner-platform-environment-specific-cutover-runbooks.md)
3. [2026-04-17-partner-platform-rehearsal-logs-and-evidence-archive-template.md](2026-04-17-partner-platform-rehearsal-logs-and-evidence-archive-template.md)
4. [2026-04-17-partner-platform-pilot-cohort-roster-and-rollout-calendar.md](2026-04-17-partner-platform-pilot-cohort-roster-and-rollout-calendar.md)
5. [2026-04-17-partner-platform-post-launch-stabilization-package.md](2026-04-17-partner-platform-post-launch-stabilization-package.md)
6. [2026-04-17-partner-platform-phase-0-and-phase-1-execution-ticket-decomposition.md](2026-04-17-partner-platform-phase-0-and-phase-1-execution-ticket-decomposition.md)

The following execution details are already represented as appendices inside the operational readiness package and do not require separate mandatory follow-up documents unless teams choose to expand them:

- cross-domain seam ownership register;
- OpenAPI and contract-freeze checklist;
- integration and conformance test matrix.

Optional expansion artifacts may still be created later when execution pressure justifies them:

- environment-specific command inventories and resolved production command sheets;
- live evidence archive population and signed rehearsal records;
- environment calendars and named rollout windows;
- owner-specific workboards and tracker imports derived from the execution ticket decomposition.

These expansions extend execution detail only. They should not reopen business rules, target-state architecture, or the canonical domain model.

---

## 11. Success Condition For Step 3

Step 3 is complete when:

- every delivery phase has explicit implementation packets;
- phase sequencing matches the dependency matrix;
- lane readiness is mapped to phase maturity;
- contract freezes and evidence expectations are defined;
- the next artifact package can move directly into cutover, migration, QA, and rollout planning without rebuilding the execution structure.
