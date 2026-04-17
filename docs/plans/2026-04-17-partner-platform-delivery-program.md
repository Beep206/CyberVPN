# CyberVPN Partner Platform Delivery Program

**Date:** 2026-04-17  
**Status:** Delivery and cutover companion document  
**Purpose:** define the phased execution, dependency management, migration tracks, QA gates, and cutover program for the target-state platform specified in [2026-04-17-partner-platform-target-state-architecture.md](2026-04-17-partner-platform-target-state-architecture.md).

---

## 1. Document Role

This document is operational by design.

It contains:

- phased implementation sequencing;
- critical-path dependencies;
- workstream ownership;
- migration and replay tracks;
- QA, shadow-mode, and cutover gates;
- rollback themes.

It is expected to change more often than the target-state architecture.

Detailed phase decomposition lives in [2026-04-17-partner-platform-detailed-phased-implementation-plan.md](2026-04-17-partner-platform-detailed-phased-implementation-plan.md).
Operational readiness, migration, cutover, QA, and rollout guidance lives in [2026-04-17-partner-platform-operational-readiness-package.md](2026-04-17-partner-platform-operational-readiness-package.md).

---

## 2. Delivery Ownership Map

| Workstream | Primary owner | Supporting owners |
|---|---|---|
| Identity, realms, RBAC, scopes | platform/backend team | frontend, admin, infra/security |
| Brand, storefront, merchant, billing | platform/backend team | frontend, finance ops, support enablement |
| Commerce and order domain | backend commerce team | frontend, finance ops, QA |
| Attribution and growth engine | backend growth/platform team | data/BI, risk/fraud, frontend |
| Partner organizations and workspace | admin/platform team | backend, finance ops, support |
| Settlement and payout operations | finance platform team | backend, admin, finance ops |
| Risk and compliance | risk/fraud platform team | backend, data/BI, support, finance |
| Service identities and entitlements | backend platform team | mobile, desktop, Telegram, frontend |
| Official frontend and partner storefront | web frontend team | backend, design, support |
| Telegram, mobile, desktop parity | channel teams | backend platform, QA |
| Analytics and reporting | data/BI team | backend, finance ops, risk, partner ops |
| Cutover, rollback, rehearsal | platform/infra team | all domain owners |

Ownership must be explicit per phase so teams do not block each other on ambiguous boundaries.

---

## 3. Critical Path And Dependency Graph

## 3.1 Critical Path

The minimum critical path is:

1. Canonical rule freeze
2. Identity/storefront/policy foundations
3. Order domain
4. Attribution and qualifying-event engine
5. Settlement and payout model
6. Service identity and entitlements
7. External and internal surfaces
8. Shadow-mode validation and cutover

## 3.2 Dependency Rules

| Dependency | Why it exists |
|---|---|
| Rule freeze -> all later phases | avoids schema and API churn on core invariants |
| Identity/storefront/policy -> order domain | orders must snapshot realm, storefront, merchant, and policy context |
| Identity/storefront/policy -> attribution | bindings and policies depend on resolved principals and surfaces |
| Order domain -> attribution | attribution resolves against orders, not loose payments |
| Order domain + attribution -> settlement | earnings, statements, holds, and clawbacks depend on order-level ownership |
| Identity/storefront + service identity -> surfaces | clients need realm-aware auth and entitlement access |
| Attribution + settlement + risk foundation -> reporting | metrics are not trustworthy before these layers exist |

## 3.3 Parallelizable Tracks

These tracks can run in parallel after Phase 1 foundations exist:

- partner organization workspace APIs;
- early admin scaffolding;
- analytics event contracts;
- service identity abstraction;
- storefront engine scaffolding.

---

## 4. Migration Tracks

The migration program must be tracked independently from feature development.

Required migration tracks:

- `auth_realm_migration`
- `storefront_binding_migration`
- `partner_code_versioning_migration`
- `legacy_referral_closure_migration`
- `wallet_bucket_separation_migration`
- `order_domain_backfill_migration`
- `historical_attribution_replay`
- `risk_subject_foundation_migration`
- `merchant_billing_snapshot_migration`

Each track must define:

- source data;
- target model;
- replay or backfill strategy;
- reconciliation method;
- rollback or containment method;
- success metrics.

---

## 5. Phase Plan

## Phase 0. Canonical Rule Freeze And Metric Definition

**Primary objective:** freeze the rules that would otherwise create cascading rework across every domain.

**Deliverables:**

- five-lane taxonomy freeze;
- consumer-growth versus partner-revenue separation;
- commercial owner invariants;
- typed policy-version model;
- merchant-of-record baseline;
- qualifying-first-payment baseline;
- renewal-baseline decisions;
- draft event taxonomy baseline for orders, attribution, rewards, settlement, risk, and entitlements;
- core metric definitions.

**Depends on:** none

**Exit criteria:**

- platform, product, finance, support, and risk sign off the same invariant set;
- one definition exists for `paid conversion`, `qualifying first payment`, `refund rate`, `D30 paid retention`, and `payout liability`;
- no unresolved ambiguity remains around official-surface no-markup policy.

**Required validation:**

- architecture review approved;
- metric glossary approved;
- policy glossary approved.

**Freeze checkpoint:**

- core glossary freeze;
- phase-0 policy vocabulary freeze;
- draft event taxonomy freeze;
- metric definition freeze for platform KPIs.

**Shadow metric gate:**

- not required yet.

## Phase 1. Identity, Storefront, Policy, And Early Risk Foundations

**Primary objective:** establish the namespace, actor, and policy backbone that all later domains depend on.

**Deliverables:**

- `brands`, `storefronts`, `auth_realms`, `merchant_profiles`, `support_profiles`, `communication_profiles`;
- principal classes and realm model;
- partner organization model;
- RBAC/scopes/token model;
- policy version lifecycle and effective dating;
- `accepted_legal_documents`;
- early risk foundation:
  - `risk_subjects`
  - `risk_identifiers`
  - `risk_links`
  - baseline eligibility rules.

**Depends on:** Phase 0

**Exit criteria:**

- same email can exist across realms without cross-login;
- realm-aware credentials, token scopes, and session audiences are defined and testable;
- partner operators are represented as organization users, not only customer upgrades;
- risk subject foundation exists early enough to support trial, referral, and payout abuse rules.

**Required validation:**

- automated realm-isolation tests;
- RBAC scope enforcement tests;
- same-email/different-realm registration tests;
- actor-attribution audit tests for policy changes.

**Freeze checkpoint:**

- schema freeze for identity, realm, storefront, and policy-version foundations;
- API contract freeze for auth, principal, and policy-management surfaces.

**Shadow metric gate:**

- identity and realm metrics available for shadow monitoring, but no hard comparison gate yet.

## Phase 2. Merchant, Billing, Tax, And Order Domain

**Primary objective:** move the platform to an order-centric commerce model with explicit billing responsibility.

**Deliverables:**

- `quote_sessions`
- `checkout_sessions`
- `orders`
- `order_items`
- `payment_attempts`
- `refunds`
- `payment_disputes`
- `chargeback subtype and outcome mapping inside payment_disputes`
- merchant, invoice, tax, and descriptor snapshots on orders;
- commissionability evaluation scaffolding.

**Depends on:** Phase 1

**Exit criteria:**

- one order can support multiple payment attempts without losing identity or pricing snapshots;
- merchant-of-record, tax, descriptor, refund responsibility, and chargeback liability are explicit per order;
- refunds and disputes exist as first-class objects and not only payment-side side effects.

**Required validation:**

- one-to-many order/payment retry tests;
- invoice/tax snapshot tests;
- partial refund and dispute lifecycle tests;
- idempotent checkout-commit tests.

**Freeze checkpoint:**

- schema freeze for order, payment-attempt, refund, and dispute foundations;
- API contract freeze for quote, checkout-session, order, refund, and dispute APIs.

**Shadow metric gate:**

- order-count, payment-attempt, and refund shadow reporting must reconcile with legacy operational views.

## Phase 3. Attribution, Stacking, Qualifying Events, And Renewal Logic

**Primary objective:** make commercial ownership, growth rewards, compatibility rules, and renewals deterministic.

**Deliverables:**

- `attribution_touchpoints`
- `customer_commercial_bindings`
- `order_attribution_results`
- `growth_reward_allocations`
- stacking and compatibility matrix implementation;
- qualifying-event evaluator;
- renewal ownership and renewal economics rules;
- explainability payloads.

**Depends on:** Phase 1, Phase 2

**Exit criteria:**

- every finalized order resolves to zero or one cash owner;
- growth rewards and commercial ownership are stored separately;
- stacking rules no longer depend on frontend-only conditionals;
- renewal orders can explain owner provenance, policy version, and payout eligibility.

**Required validation:**

- precedence tests for explicit code, passive click, and persistent binding;
- no-recursive-payout tests on referral credits;
- qualifying-first-payment tests;
- renewal inheritance and override tests;
- historical explainability snapshot tests.

**Freeze checkpoint:**

- schema freeze for touchpoints, bindings, attribution results, and growth reward allocations;
- API contract freeze for attribution, growth-reward, and policy-evaluation surfaces.
- canonical domain event naming freeze for commerce, attribution, growth-reward, settlement, risk, and entitlement events before later rollout phases.

**Shadow metric gate:**

- attribution winner rates and qualifying-event counts must reconcile between legacy and new engines within approved tolerance.

## Phase 4. Settlement, Statements, Payouts, And Dispute Adjustments

**Primary objective:** separate partner finance from consumer wallet behavior and make finance operations auditable.

**Deliverables:**

- earning events;
- earning holds;
- reserves;
- `partner_statements`;
- `settlement_periods`;
- `payout_instructions`;
- `payout_executions`;
- dispute and refund adjustment policies;
- reconciliation and maker-checker controls.

**Depends on:** Phase 2, Phase 3

**Exit criteria:**

- wallet is no longer treated as the accounting system for partner payouts;
- statements can open, close, adjust, and reconcile independently of customer wallet state;
- chargebacks, refunds, and clawbacks flow through typed adjustment policies;
- payout approval and execution are auditable end to end.

**Required validation:**

- statement close and reopen tests;
- payout maker-checker tests;
- dispute-adjustment reconciliation tests;
- partner liability and reserve reporting checks.

**Freeze checkpoint:**

- schema freeze for statements, reserves, payout instructions, and payout executions;
- API contract freeze for statement, payout, reserve, and reconciliation surfaces.

**Shadow metric gate:**

- shadow statements, available earnings, and payout liability must reconcile with finance-approved tolerance.

## Phase 5. Service Identity And Entitlements

**Primary objective:** separate service access from customer-account and storefront layers.

**Deliverables:**

- `service_identities`
- `entitlement_grants`
- `device_credentials`
- `provisioning_profiles`
- `access_delivery_channels`
- shared entitlement APIs.

**Depends on:** Phase 1, Phase 2, Phase 3

**Exit criteria:**

- service access is driven by entitlement grants rather than loosely coupled customer rows;
- the same rules can be consumed by web, Telegram, mobile, and desktop channels;
- purchase surface and service-consumption surface are separable in support and analytics.

**Required validation:**

- entitlement-grant lifecycle tests;
- provisioning and revocation tests;
- realm-aware service login tests;
- cross-channel entitlement parity tests.

**Freeze checkpoint:**

- schema freeze for service identities and entitlement grants;
- API contract freeze for entitlement and provisioning surfaces.

**Shadow metric gate:**

- entitlement counts and service-access outcomes must match shadow verification packs across supported channels.

## Phase 6. Surface Rollout: Official Frontend, Partner Storefront, Partner Portal, Admin

**Primary objective:** expose the platform through the correct external and internal surfaces.

**Deliverables:**

- official CyberVPN frontend alignment;
- generic multi-brand `apps/partner-storefront/`;
- partner portal or workspace;
- admin operational modules for growth, finance, support, and risk;
- surface policy matrix enforcement.

**Depends on:** Phase 1, Phase 2, Phase 3, Phase 4, Phase 5

**Exit criteria:**

- official frontend never exposes self-serve reseller markup;
- partner storefront is host-resolved, realm-aware, and policy-aware;
- partner workspace supports org users, statements, payout accounts, and traffic declarations;
- admin can inspect attribution, payout, risk, and support context without direct SQL.

**Required validation:**

- host-based storefront resolution tests;
- realm-aware web auth tests;
- surface-specific code-entry policy tests;
- portal role and row-level access tests.

**Freeze checkpoint:**

- API contract freeze for partner portal, storefront, admin-ops, and portal-finance surfaces;
- UI contract freeze for host-based resolution and surface-policy enforcement.

**Shadow metric gate:**

- storefront traffic, auth success, and portal finance views must reconcile against backend source-of-truth APIs.

## Phase 7. Full-Channel Adoption And Analytical Readiness

**Primary objective:** extend platform semantics across all channels and make metrics trustworthy.

**Deliverables:**

- Telegram Bot parity;
- Telegram Mini App parity;
- mobile parity;
- desktop parity;
- partner API parity;
- event/outbox layer;
- analytical marts;
- partner dashboards and exports;
- alert definitions.

**Depends on:** Phase 3, Phase 4, Phase 5, Phase 6

**Exit criteria:**

- all major channels consume the same identity, order, attribution, entitlement, and reporting foundations;
- analytical marts reconcile against OLTP sources for key platform metrics;
- exports and dashboards explain the same platform numbers used by finance and partner ops.

**Required validation:**

- channel-by-channel entitlement parity tests;
- event idempotency and replay tests;
- metric reconciliation for orders, earnings, and payout liability;
- partner export contract tests.

**Freeze checkpoint:**

- event contract freeze;
- reporting schema freeze for canonical marts and partner exports;
- API contract freeze for public reporting and partner reporting surfaces.

**Shadow metric gate:**

- warehouse and OLTP metrics for key platform KPIs must reconcile within agreed tolerance before broad release.

## Phase 8. Advanced Risk, Shadow Mode, Pilot, And Cutover

**Primary objective:** prove the platform under real traffic without breaking finance, support, or brand isolation.

**Deliverables:**

- full risk-review workflows;
- policy acceptance and traffic declaration lifecycle;
- dispute cases and evidence attachments;
- shadow attribution and shadow settlement runs;
- phased production pilots;
- support runbooks;
- cutover and rollback rehearsals.

**Depends on:** all prior phases

**Exit criteria:**

- shadow attribution and live attribution agree within approved tolerance;
- settlement outputs reconcile with shadow statements;
- cross-realm abuse detection works before broad partner scale;
- finance, support, and risk sign off pilot results.

**Required validation:**

- shadow versus live attribution comparison;
- pilot payout dry-run reconciliation;
- cross-realm abuse simulation tests;
- runbook rehearsal and rollback drill completion.

**Freeze checkpoint:**

- cutover runbook freeze;
- rollback runbook freeze;
- pilot acceptance criteria freeze.

**Shadow metric gate:**

- live pilots cannot scale beyond approved thresholds until attribution, settlement, and risk shadow metrics remain within approved bounds.

---

## 6. Risk Foundation Positioning

Risk cannot be deferred until the end of the program.

The delivery program intentionally splits risk work into two layers:

- early risk foundation in Phase 1 for eligibility, duplicate-account, and cross-realm abuse controls;
- advanced governance and review workflows in Phase 8 for scaled operations.

This is required because trial, referral, payouts, and realm isolation all depend on risk foundations before full go-live.

---

## 7. QA Themes

Mandatory QA themes:

- same email across different realms;
- same password across different realms without cross-login;
- explicit code versus passive click precedence;
- reseller binding persistence;
- invite reward without cash-owner conflict;
- referral credit without withdrawal eligibility;
- qualifying-first-payment rules;
- renewal inheritance and override rules;
- policy version snapshot reproducibility;
- merchant-of-record and descriptor correctness;
- statement and payout reconciliation;
- chargeback and partial-refund adjustment behavior;
- channel parity on entitlements;
- cross-realm abuse visibility for risk tooling.

---

## 8. Cutover Priorities

The highest-risk cutover areas are:

- auth-realm isolation;
- order-domain migration from payment-centric logic;
- partner-code policy versioning;
- merchant and billing snapshot correctness;
- wallet-to-settlement separation;
- historical attribution replay;
- risk-subject linkage;
- reporting definition alignment.

These must be rehearsed before broad production migration.

---

## 9. Rollback Themes

Rollback plans must exist for:

- auth-realm activation;
- order-domain cutover;
- attribution-engine activation;
- statement and payout execution activation;
- partner storefront production enablement.

Rollback must preserve:

- immutable financial history;
- attribution evidence;
- policy version snapshots;
- accepted-legal-document evidence;
- audit trail completeness.

---

## 10. Success Criteria

Delivery is successful when:

- the target-state architecture is implemented without violating canonical invariants;
- workstream dependencies are explicit enough that teams can execute in parallel without hidden blockers;
- finance, support, risk, product, and engineering operate from the same metric definitions;
- shadow-mode and pilot evidence support safe production cutover.
