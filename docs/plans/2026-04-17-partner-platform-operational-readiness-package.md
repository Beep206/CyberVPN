# CyberVPN Partner Platform Operational Readiness Package

**Date:** 2026-04-17  
**Status:** Operational readiness, migration, cutover, QA, and rollout package  
**Purpose:** define the operational path from completed implementation phases to safe production activation across migration, cutover, QA, rollout rings, rollback, reconciliation, and governance for the five-lane CyberVPN partner platform.

---

## 1. Document Role

This document is the operational readiness companion to:

- [2026-04-17-partner-platform-delivery-program.md](2026-04-17-partner-platform-delivery-program.md)
- [2026-04-17-partner-platform-detailed-phased-implementation-plan.md](2026-04-17-partner-platform-detailed-phased-implementation-plan.md)
- [2026-04-17-partner-platform-domain-dependency-matrix.md](2026-04-17-partner-platform-domain-dependency-matrix.md)

It turns completed implementation work into a controlled production-readiness model.

It covers:

- cutover units;
- migration waves;
- QA and conformance matrices;
- ring-promotion rules;
- shadow and live comparison procedures;
- reconciliation procedures;
- rollback triggers and rollback boundaries;
- lane-by-lane rollout strategy;
- go/no-go governance;
- operational appendices for seam ownership and contract discipline.

The readiness layer assumes the Phase 0 validation baseline defined in [../testing/partner-platform-phase-0-and-phase-1-validation-pack.md](../testing/partner-platform-phase-0-and-phase-1-validation-pack.md) already exists before any foundation phase is promoted beyond internal validation.

The first operational readiness checkpoint that may consume `Phase 1` foundations also requires the signed evidence pack in [../testing/partner-platform-phase1-exit-evidence.md](../testing/partner-platform-phase1-exit-evidence.md).

The first operational readiness checkpoint that may consume `Phase 2` order-domain foundations also requires the signed evidence pack in [../testing/partner-platform-phase2-exit-evidence.md](../testing/partner-platform-phase2-exit-evidence.md).

The first operational readiness checkpoint that may consume `Phase 3` attribution, growth-reward, and renewal foundations also requires the signed evidence pack in [../testing/partner-platform-phase3-exit-evidence.md](../testing/partner-platform-phase3-exit-evidence.md).

The first operational readiness checkpoint that may consume `Phase 4` settlement and payout foundations also requires the signed evidence pack in [../testing/partner-platform-phase4-exit-evidence.md](../testing/partner-platform-phase4-exit-evidence.md).

Any internal payout rehearsal that consumes `Phase 4` settlement and payout foundations also requires the dry-run evidence specification in [../testing/partner-platform-phase4-dry-run-settlement-evidence.md](../testing/partner-platform-phase4-dry-run-settlement-evidence.md) together with the reconciliation pack definition in [../testing/partner-platform-phase4-settlement-reconciliation-pack.md](../testing/partner-platform-phase4-settlement-reconciliation-pack.md).

The first operational readiness checkpoint that may consume `Phase 5` service identity, entitlement, provisioning, and access-delivery foundations also requires the signed evidence pack in [../testing/partner-platform-phase5-exit-evidence.md](../testing/partner-platform-phase5-exit-evidence.md) together with the replay/parity pack definition in [../testing/partner-platform-phase5-service-access-replay-pack.md](../testing/partner-platform-phase5-service-access-replay-pack.md).

The first operational readiness checkpoint that may consume `Phase 6` official-web, partner-storefront, partner-portal, or admin surface foundations also requires the signed evidence pack in [../testing/partner-platform-phase6-exit-evidence.md](../testing/partner-platform-phase6-exit-evidence.md). No surface rollout ring may treat `Phase 6` customer or operator surfaces as promotion-ready without that signed closure record.

The first operational readiness checkpoint that may consume `Phase 7` event/outbox, analytical marts, partner exports, reporting API, or channel-parity foundations also requires the signed evidence pack in [../testing/partner-platform-phase7-exit-evidence.md](../testing/partner-platform-phase7-exit-evidence.md) together with the deterministic packs in [../testing/partner-platform-phase7-analytical-marts-and-reconciliation-pack.md](../testing/partner-platform-phase7-analytical-marts-and-reconciliation-pack.md) and [../testing/partner-platform-phase7-parity-and-evidence-pack.md](../testing/partner-platform-phase7-parity-and-evidence-pack.md). No `Phase 8` shadow, pilot, or rollout-ring promotion may treat `Phase 7` reporting or parity surfaces as ready without those signed artifacts.

Any `Phase 8` promotion from limited pilot posture into broad production activation also requires the signed readiness bundle in [../testing/partner-platform-phase8-production-readiness-bundle.md](../testing/partner-platform-phase8-production-readiness-bundle.md), the signed gate record in [../testing/partner-platform-phase8-exit-evidence.md](../testing/partner-platform-phase8-exit-evidence.md), and the completed human-approval tracker in [../testing/partner-platform-broad-activation-sign-off-tracker.md](../testing/partner-platform-broad-activation-sign-off-tracker.md). No `R3 -> R4` broad activation or broad cutover readiness may proceed without all three records.

This document does not redefine business rules or target-state architecture. It assumes those are already frozen enough to support operational execution.

Derived operational documents:

- [2026-04-17-partner-platform-environment-specific-cutover-runbooks.md](2026-04-17-partner-platform-environment-specific-cutover-runbooks.md)
- [2026-04-17-partner-platform-rehearsal-logs-and-evidence-archive-template.md](2026-04-17-partner-platform-rehearsal-logs-and-evidence-archive-template.md)
- [2026-04-19-partner-platform-environment-command-inventory-sheet.md](2026-04-19-partner-platform-environment-command-inventory-sheet.md)
- [2026-04-17-partner-platform-pilot-cohort-roster-and-rollout-calendar.md](2026-04-17-partner-platform-pilot-cohort-roster-and-rollout-calendar.md)
- [2026-04-17-partner-platform-post-launch-stabilization-package.md](2026-04-17-partner-platform-post-launch-stabilization-package.md)

---

## 2. Readiness Principles

Operational readiness follows these principles:

1. No broad rollout without shadow evidence.
2. No payable partner lane without settlement maturity.
3. No partner storefront broad release without realm isolation, merchant correctness, and support routing proof.
4. No full channel rollout without entitlement neutrality.
5. No rollback may destroy immutable financial, attribution, or legal evidence.
6. Every promotion between release rings requires named owners and explicit evidence.
7. Cutover must happen in units smaller than the whole platform.
8. Reconciliation is a release gate, not a reporting afterthought.
9. Risk controls must activate before traffic scale, not after abuse appears.
10. Customer-facing and operator-facing surfaces must promote independently when their dependencies differ.

---

## 3. Cutover Units

The platform must not be treated as one monolithic cutover. The following cutover units are canonical.

| Cutover unit | Primary domain owners | Main dependencies | Rollback class | Irreversible elements |
|---|---|---|---|---|
| `CU1` Auth realm activation | identity/platform, security, frontend | realm model, token audiences, support routing | traffic and config rollback | accepted legal evidence already captured |
| `CU2` Storefront routing activation | storefront/platform, frontend, support | host resolution, realm bindings, support/communication profiles | routing rollback | persisted storefront-origin order history |
| `CU3` Order-domain cutover | commerce, billing, QA | quote, checkout, order, payment attempts, refunds, disputes | write-path rollback with preserved evidence | immutable committed orders |
| `CU4` Attribution engine activation | growth/platform, risk, data | touchpoints, bindings, attribution results, explainability | decision-path rollback to shadowed legacy path where available | immutable attribution evidence snapshots |
| `CU5` Growth reward activation | growth/platform, risk, support | reward allocations, caps, qualifying events | allocation rollback with preserved evidence | already granted non-cash rewards may require adjustment events |
| `CU6` Settlement and statement activation | finance platform, finance ops, risk | earning events, holds, reserves, statements, adjustments | availability rollback, not history deletion | statements, payout audit, adjustments |
| `CU7` Partner payout activation | finance platform, finance ops, risk | payout accounts, payout instructions, maker-checker, reserves | payout execution halt, not ledger deletion | payout decisions and audit trail |
| `CU8` Entitlement activation | platform backend, channel teams, support | service identities, entitlements, provisioning | access-path rollback with preserved grants | issued entitlement history |
| `CU9` Official frontend activation | frontend, backend, support | CU1, CU3, CU4, CU8 | traffic rollback | customer action history |
| `CU10` Partner storefront activation | frontend, storefront/platform, support, finance | CU1, CU2, CU3, CU4, CU8 | host and traffic rollback | created realm-scoped accounts and orders |
| `CU11` Partner portal activation | admin/platform, finance, risk | CU6, CU7, governance actions, reporting views | portal-feature rollback | operator audit trail |
| `CU12` Admin and support activation | admin/platform, support, finance, risk | explainability, disputes, entitlements, statements | feature-flag rollback | audit trail and case history |
| `CU13` Reporting and export activation | data/BI, finance ops, partner ops | event layer, marts, reconciliation | export rollback | generated historical metrics remain as evidence |
| `CU14` Channel parity activation | channel teams, backend platform, QA | CU8, CU13, surface policy matrix | channel-specific rollout rollback | channel usage and audit records |

Rules:

- `CU3`, `CU4`, `CU6`, and `CU8` are the highest-risk units.
- `CU7` can never promote faster than `CU6`.
- `CU10` can never promote faster than `CU1`, `CU2`, `CU3`, and `CU8`.
- `CU14` promotes separately per channel.

---

## 4. Migration Waves

Migration must proceed in controlled waves rather than as one big switchover.

## 4.1 Wave Structure

| Wave | Purpose | Typical activities | Allowed release rings |
|---|---|---|---|
| `MW0` Schema-first foundations | prepare storage and contracts | additive schemas, version tables, new enums, baseline APIs behind flags | `R0` |
| `MW1` Reference and binding backfills | move non-transactional foundation state | realm bindings, storefront bindings, partner org links, policy versions, risk-subject seeds | `R0`, `R1` |
| `MW2` Commercial backfills and replay harnesses | build replayability without traffic cutover | order backfills, payment/dispute normalization, historical attribution replay, wallet separation views | `R1`, `R2` |
| `MW3` Dual-write and shadow evaluation | compare new behavior to reference truth | shadow attribution, shadow statements, shadow reporting, dual-read or mirrored events where needed | `R2` |
| `MW4` Pilot activations | activate limited trusted traffic | lane-limited pilots, partner pilot cohorts, controlled storefront traffic, payout dry-runs | `R3` |
| `MW5` Broad activation and stabilization | scale after evidence | traffic promotion, payout enablement, channel rollout, reporting export activation | `R4` |

## 4.2 Migration Tracks Mapped To Waves

| Migration track | Primary waves | Notes |
|---|---|---|
| `auth_realm_migration` | `MW0`, `MW1`, `MW4` | foundation first, then pilot with strict login separation |
| `storefront_binding_migration` | `MW0`, `MW1`, `MW4` | host routing must stabilize before partner storefront rollout |
| `partner_code_versioning_migration` | `MW0`, `MW1`, `MW2` | historical code state must map to policy-version references |
| `legacy_referral_closure_migration` | `MW1`, `MW2`, `MW3` | old indefinite or ambiguous reward logic must be contained before broad rollout |
| `wallet_bucket_separation_migration` | `MW1`, `MW2`, `MW3` | partner finance must separate from consumer balances before settlement activation |
| `order_domain_backfill_migration` | `MW2`, `MW3` | no settlement or reporting confidence without order-centric replay |
| `historical_attribution_replay` | `MW2`, `MW3` | must complete before CU4 broad promotion |
| `risk_subject_foundation_migration` | `MW1`, `MW2` | early anti-abuse dependency |
| `merchant_billing_snapshot_migration` | `MW1`, `MW2`, `MW3` | descriptor and tax snapshots must reconcile before partner storefront pilots |

## 4.3 Migration Controls

Every migration wave must define:

- source-of-truth objects;
- target model;
- replay window;
- freeze window;
- data quality thresholds;
- containment method if the wave stalls;
- irreversible transitions if any;
- sign-off owners.

---

## 5. Release Ring Promotion Rules

## 5.1 Ring Definitions

| From | To | Promotion meaning | Minimum proof required |
|---|---|---|---|
| `R0` | `R1` | safe for internal and synthetic validation | schema stable, API contracts frozen for tested scope, basic test pass |
| `R1` | `R2` | safe for shadow or mirrored comparison | deterministic outputs, replay harness ready, metrics and explainability available |
| `R2` | `R3` | safe for controlled real traffic | shadow divergence within tolerance, rollback defined, support and finance briefed |
| `R3` | `R4` | safe for broad production | pilot success, reconciliation clean, no-go list cleared, executive or delegated approval complete |

## 5.2 Promotion Criteria By Capability Type

| Capability type | `R1 -> R2` | `R2 -> R3` | `R3 -> R4` |
|---|---|---|---|
| Identity and realms | auth and isolation tests pass | shadow login and routing clean | support and fraud sign off no cross-realm leaks |
| Order domain | order snapshots reproducible | shadow order totals reconcile | finance accepts order-ledger behavior |
| Attribution | explainability stable | winner divergence within approved tolerance | partner ops and risk sign off |
| Growth rewards | caps and anti-loop rules pass | shadow reward allocations reconcile | support accepts customer-facing outcomes |
| Settlement | dry statements and adjustments pass | shadow statements reconcile | finance signs off payout liability |
| Payouts | internal dry-run only | limited partner payout rehearsal | finance and risk approve broad release |
| Entitlements | lifecycle tests pass | channel parity shadow checks pass | support accepts service-consumption stability |
| Partner storefront | routing and auth pass | controlled host pilot passes | support, finance, and product approve broad launch |
| Reporting and exports | marts and definitions stable | OLTP reconciliation within tolerance | finance and partner ops approve external usage |

## 5.3 Ring Promotion Gates

No promotion is valid without:

- named approving owners;
- explicit evidence links;
- rollback class defined;
- freeze checkpoint complete;
- current blocker register reviewed.

---

## 6. QA Matrix

The QA package must be matrix-driven, not only theme-driven.

## 6.1 Domain x Lane x Surface x Ring Matrix

| Domain | Lane | Surface | Required rings | Core scenarios | Primary owners |
|---|---|---|---|---|---|
| Identity and Access | Invite / Gift | official web | `R1`, `R2`, `R3` | realm separation, invite redemption auth, no cross-login | platform, frontend, QA |
| Identity and Access | Reseller / API / Distribution | partner storefront | `R1`, `R2`, `R3` | branded realm login, separate account namespace, password reuse without cross-access | platform, frontend, QA |
| Commerce and Orders | Consumer Referral Credits | official web | `R1`, `R2`, `R3` | qualifying checkout, first-payment semantics, wallet-credit behavior | commerce, QA |
| Commerce and Orders | Creator / Affiliate | official web | `R1`, `R2`, `R3` | code entry, discount application, order snapshots | commerce, frontend, QA |
| Commerce and Orders | Reseller / API / Distribution | partner storefront | `R1`, `R2`, `R3`, `R4` | alternate pricebook, markup policy, merchant display | commerce, frontend, finance |
| Attribution | Creator / Affiliate | official web | `R1`, `R2`, `R3` | explicit code beats passive click, explainability payload | growth, risk, QA |
| Attribution | Performance / Media Buyer | partner APIs and postbacks | `R1`, `R2`, `R3` | declared traffic, postback integrity, probation logic | growth, risk, QA |
| Growth Rewards | Invite / Gift | official web | `R1`, `R2`, `R3` | non-cash allocation only, no cash-owner conflict | growth, support, QA |
| Growth Rewards | Consumer Referral Credits | official web | `R1`, `R2`, `R3` | fixed credit, caps, no withdrawal eligibility | growth, risk, QA |
| Finance and Settlement | Creator / Affiliate | partner portal | `R1`, `R2`, `R3` | statement generation, holds, available earnings | finance, partner ops, QA |
| Finance and Settlement | Performance / Media Buyer | partner portal | `R1`, `R2`, `R3` | longer hold, reserve behavior, payout blocks | finance, risk, QA |
| Finance and Settlement | Reseller / API / Distribution | partner portal | `R1`, `R2`, `R3`, `R4` | markup-driven economics, no double payout, statement adjustments | finance, QA |
| Risk and Governance | Performance / Media Buyer | partner portal and admin | `R1`, `R2`, `R3` | traffic declaration, creative approval, abnormal velocity review | risk, support, QA |
| Risk and Governance | Consumer Referral Credits | official web and admin | `R1`, `R2`, `R3` | self-referral detection, cap abuse, duplicate subject controls | risk, QA |
| Entitlements | Invite / Gift | official web and service delivery | `R1`, `R2`, `R3` | bonus access activation, entitlement revocation | platform, QA |
| Entitlements | Reseller / API / Distribution | partner storefront plus service channels | `R1`, `R2`, `R3`, `R4` | separate purchase surface, correct service grant | platform, channel teams, QA |
| Surfaces | Creator / Affiliate | partner portal | `R1`, `R2`, `R3` | code management, statements, payout accounts | frontend/admin, finance, QA |
| Surfaces | Reseller / API / Distribution | partner storefront | `R1`, `R2`, `R3`, `R4` | branded price surface, support routing, legal docs | frontend, support, QA |
| Reporting | All lanes | partner portal, admin, exports | `R1`, `R2`, `R3`, `R4` | canonical metrics, export integrity, explainability consistency | data/BI, finance, QA |
| Channel parity | All applicable lanes | Telegram, mobile, desktop | `R1`, `R2`, `R3` | entitlement parity, order history, auth behavior | channel teams, platform, QA |

## 6.2 Mandatory Test Categories

Every relevant matrix row must include:

- happy path;
- boundary and cap behavior;
- replay and idempotency behavior;
- negative and abuse scenarios;
- role and scope enforcement;
- audit and explainability output checks.

---

## 7. Shadow And Live Comparison Procedures

Shadow procedures are mandatory before broad production activation.

## 7.1 Canonical Shadow Comparisons

| Comparison | Shadow source | Live or reference source | Owner | Blocking threshold |
|---|---|---|---|---|
| Attribution winners | new attribution engine | legacy or reference attribution behavior | growth, data/BI | divergence above approved lane-specific tolerance |
| Growth reward allocations | new reward engine | legacy reward outputs or policy-calculated reference | growth, support | cap, duplication, or reward-type mismatch |
| Partner statements | new settlement engine | finance reference calculations | finance platform, finance ops | liability mismatch beyond approved tolerance |
| Reporting marts | warehouse marts | OLTP reconciliation views | data/BI | metric mismatch above approved threshold |
| Entitlement counts | entitlement layer | service provider or legacy access truth | platform backend, channel teams | unexplained drift in active grants |
| Legal acceptance evidence | new acceptance records | surface event logs and checkout records | risk, legal, QA | missing or inconsistent evidence record |

## 7.2 Shadow Procedure Steps

1. Freeze input dataset or time window.
2. Run new pipeline in non-authoritative mode.
3. Compare outputs against approved reference source.
4. Classify differences as expected, bug, data-gap, or policy-gap.
5. Produce divergence report with owner and disposition.
6. Re-run after fixes until threshold is clean.
7. Archive signed shadow report before ring promotion.

---

## 8. Reconciliation Procedures

Reconciliation is required both during migration and during ongoing readiness checks.

## 8.1 Reconciliation Register

| Object family | System of record | Comparison source | Frequency | Owner | Blocking condition |
|---|---|---|---|---|---|
| Orders | order domain | payment/provider and legacy order views | daily during readiness, per cutover window | commerce, finance ops | order count or value drift above tolerance |
| Attribution winners | order_attribution_results | reference attribution outputs | daily during shadow windows | growth, data/BI | unexplained winner divergence |
| Growth rewards | growth_reward_allocations | reward reference calculation | daily during pilot | growth, support | duplicate or missing allocations |
| Statements | partner_statements | finance reconciliation model | per settlement period and pre-payout | finance platform, finance ops | liability mismatch or missing adjustment chain |
| Payout liability | settlement views | statements, holds, reserves, payout execution totals | per payout window | finance platform | liability imbalance |
| Refunds and disputes | refunds and payment_disputes | provider reports | daily | commerce, finance ops, risk | dispute state mismatch or missing adjustment |
| Entitlement state | entitlement_grants | service-access and provisioning sources | daily and pre-channel rollout | platform backend, channel teams | active access drift |
| Accepted legal documents | legal acceptance records | session, checkout, and surface logs | daily during rollout | risk, legal, QA | missing evidence or wrong version linkage |

## 8.2 Reconciliation Procedure

Every reconciliation cycle must:

1. define the cutoff window;
2. define the comparison sources;
3. produce a diff with record counts and economic deltas;
4. classify every delta as expected or blocking;
5. assign owners for unresolved differences;
6. block promotion if unresolved differences exceed threshold.

---

## 9. Rollback Model

Rollback must be explicit and typed.

## 9.1 Rollback Classes

| Rollback class | Meaning | Allowed for | Not allowed for |
|---|---|---|---|
| `Config rollback` | disable new routing, flags, or traffic exposure | surfaces, channel rollout, reporting visibility | immutable history deletion |
| `Traffic rollback` | stop new traffic entering a new path | storefronts, portal features, channel activations | already committed orders |
| `Decision-path rollback` | revert authoritative evaluator to prior path while preserving evidence | attribution, growth allocation authority, support views | deletion of captured evidence |
| `Availability rollback` | halt payout availability or execution | payouts, exports, partner finance visibility | deletion of statements or payout audit |
| `Containment mode` | freeze or isolate problematic lane, partner cohort, or channel | performance traffic, partner cohorts, channel pilots | platform-wide data rewrite |

## 9.2 Rollback Triggers

| Trigger | Typical scope | Immediate action | Escalation owner |
|---|---|---|---|
| realm isolation breach | auth realms, partner storefront, official web | traffic rollback and incident response | platform/security |
| incorrect pricebook or merchant display | storefronts, checkout | config rollback and order review | commerce, finance |
| attribution divergence above threshold | attribution engine, partner reports | decision-path rollback or containment | growth, data/BI |
| duplicate or recursive reward allocation | invite and referral flows | reward-path rollback and adjustment review | growth, risk |
| statement or liability mismatch | settlement and payouts | availability rollback for payouts | finance platform |
| payout execution anomaly | payout operations | payout halt and maker-checker escalation | finance ops |
| entitlement grant drift | service access or channel parity | traffic rollback for affected channel | platform backend |
| legal-evidence capture gap | checkout, portal, storefront | traffic rollback for affected surface if material | risk, legal |
| risk-control bypass on performance lane | partner APIs, portal, media-buyer flows | containment mode for affected partner cohort | risk |

## 9.3 Rollback Boundaries

Rollback must preserve:

- immutable orders;
- payment attempt history;
- attribution evidence and snapshots;
- reward allocation history and reversals;
- statements and financial audit trail;
- payout approval and execution audit;
- accepted legal document evidence;
- support and governance case history.

Rollback may disable authority, visibility, or traffic flow, but must not erase history.

---

## 10. Go / No-Go Governance

## 10.1 Approval Body

| Function | Required for which promotions |
|---|---|
| Platform engineering | all `R2 -> R3` and `R3 -> R4` promotions |
| Finance and finance ops | all settlement, statement, payout, reseller, creator, and performance promotions |
| Risk and compliance | all partner-revenue promotions and any cross-realm expansion |
| Support enablement | all customer-facing and partner-facing surface promotions |
| Product | all broad customer or partner rollout decisions |
| Partner operations | creator, reseller, performance, portal, and export promotions |
| Data/BI | reporting, exports, shadow metric sign-off |

## 10.2 Governance Meetings

| Meeting | Purpose | Cadence during rollout |
|---|---|---|
| Readiness review | review evidence, blockers, and promotion requests | weekly, then daily during pilot weeks |
| Cutover command review | approve scheduled cutover units and owners | before every cutover window |
| Shadow divergence review | review comparison results and thresholds | after every shadow cycle |
| Finance reconciliation review | approve statement, payout, and liability readiness | per settlement and payout window |
| Go / No-Go board | final ring promotion decision | before every `R3 -> R4` promotion |

## 10.3 No-Go Conditions

Promotion must stop if any of the following remain unresolved:

- realm isolation defect with customer impact;
- merchant or tax behavior inconsistent with authoritative order snapshots;
- attribution divergence above threshold for the lane being promoted;
- statement or payout liability mismatch above finance tolerance;
- unresolved legal acceptance evidence gap;
- entitlement drift causing incorrect service access;
- missing owner acknowledgements for the pilot cohort being promoted;
- missing or failed rollback drill for the cutover units in scope;
- latest pilot go/no-go decision is absent, `hold`, or `no_go`;
- missing rollback owner or undefined containment method;
- support not ready for the affected surface or lane.

---

## 11. Lane-By-Lane Rollout Strategy

Each lane has its own operational profile.

## 11.1 Invite / Gift

| Item | Strategy |
|---|---|
| Rollout shape | official web first, then channel parity |
| Earliest pilot | after attribution-independent reward logic and entitlements are stable |
| Critical dependencies | growth rewards, entitlements, official surface policy enforcement |
| Main risks | accidental cash-owner overlap, entitlement drift, duplicate reward grants |
| No-go triggers | any case where invite affects commercial cash ownership |

## 11.2 Consumer Referral Credits

| Item | Strategy |
|---|---|
| Rollout shape | official web first, then selected support-assisted flows |
| Earliest pilot | after qualifying-event logic, caps, and risk checks are stable |
| Critical dependencies | growth rewards, risk graph, qualifying-event engine, wallet-credit separation |
| Main risks | self-referral, duplicate-subject abuse, recursive reward behavior |
| No-go triggers | reward withdrawal leakage or unresolved cap-abuse cases |

## 11.3 Creator / Affiliate

| Item | Strategy |
|---|---|
| Rollout shape | internal portal first, then trusted creators, then broader approved affiliate cohort |
| Earliest pilot | after statements, payout accounts, explainability, and support tooling exist |
| Critical dependencies | attribution, settlement, portal, reporting |
| Main risks | incorrect owner resolution, payout disputes, explainability gaps |
| No-go triggers | unresolved statement mismatch or poor attribution explainability |

## 11.4 Performance / Media Buyer

| Item | Strategy |
|---|---|
| Rollout shape | internal-only and probation-first, then tightly controlled external pilot |
| Earliest pilot | only after traffic declarations, creative approvals, reserves, payout holds, and risk review queues are proven |
| Critical dependencies | attribution, risk governance, settlement, postbacks, partner portal |
| Main risks | fraud velocity, synthetic first payments, payout leakage, compliance issues |
| No-go triggers | risk review backlog, undeclared traffic, unresolved shadow divergence, or payout-control weakness |

## 11.5 Reseller / API / Distribution

| Item | Strategy |
|---|---|
| Rollout shape | partner storefront and partner APIs in controlled cohorts, then broader approved resellers |
| Earliest pilot | after storefront isolation, pricebook binding, merchant behavior, and settlement logic are stable |
| Critical dependencies | partner storefront engine, order domain, settlement, support routing, entitlements |
| Main risks | wrong markup on official surfaces, brand leakage, support confusion, settlement mismatch |
| No-go triggers | any official-surface markup leak or unresolved merchant/storefront mismatch |

---

## 12. Appendices

## 12.1 Appendix A. Cross-Domain Seam Ownership Register

| Seam object | Canonical owner | Required participants | Why it matters operationally |
|---|---|---|---|
| `partner_payout_accounts` | Finance and Settlement | Partner Organizations, Risk, Partner Portal | blocks payouts and portal readiness |
| `partner_traffic_declarations` | Risk, Compliance, and Governance | Partner Organizations, Attribution, Portal | blocks performance lane promotion |
| `creative_approvals` | Risk, Compliance, and Governance | Partner Organizations, Campaign surfaces, Analytics | controls creative claims and compliance |
| `dispute_cases` | Risk, Compliance, and Governance | Merchant/Billing/Disputes, Finance, Support | separates operational casework from provider dispute state |
| `payment_dispute` | Merchant, Billing, Tax, and Disputes | Finance, Risk, Analytics | canonical dispute record for adjustments and reporting |
| `surface_policy_matrix_versions` | Brand and Storefront | Product and Offers, Growth, Frontend surfaces | blocks policy-consistent behavior by surface |
| `accepted_legal_documents` | Risk, Compliance, and Governance | Identity, Commerce, Legal, Support | blocks legally safe rollout |

## 12.2 Appendix B. OpenAPI And Contract-Freeze Checklist

Every cutover unit or promotion request must verify:

- schema version and compatibility status recorded;
- OpenAPI or event contract version recorded;
- auth scopes and token audience recorded;
- idempotency behavior recorded where relevant;
- immutable evidence behavior recorded;
- async job or webhook contract recorded where relevant;
- backward-compatibility note recorded;
- owner and approval recorded;
- rollback class recorded.

## 12.3 Appendix C. Integration And Conformance Test Matrix

| Integration seam | Must-pass tests |
|---|---|
| storefront -> identity | host resolution, realm routing, legal doc binding |
| identity -> commerce | principal resolution, scope validation, session audience |
| commerce -> attribution | order snapshot integrity, code precedence, binding resolution |
| commerce -> settlement | commissionability, refund adjustment, dispute linkage |
| settlement -> portal | statement visibility, payout-account access, row-level security |
| commerce -> entitlements | entitlement grant issue and revoke flows |
| risk -> all operator surfaces | review visibility, freeze actions, evidence attachments |
| reporting -> portal and admin | canonical metrics, explainability, export consistency |

---

## 13. Success Condition For Step 4

Step 4 is complete when:

- each high-risk capability is decomposed into cutover units;
- migration waves and ring-promotion rules are explicit;
- QA is mapped across domains, lanes, surfaces, and rings;
- reconciliation and shadow procedures exist for commercial, financial, risk, and entitlement objects;
- rollback triggers and rollback boundaries are explicit;
- go/no-go governance is defined with named functions;
- the package is strong enough to drive environment-specific runbooks and live rehearsals without reopening architecture.
