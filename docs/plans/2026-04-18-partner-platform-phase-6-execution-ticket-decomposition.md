# CyberVPN Partner Platform Phase 6 Execution Ticket Decomposition

**Date:** 2026-04-18  
**Status:** Execution ticket decomposition for `Phase 6` implementation start  
**Purpose:** translate `Phase 6` from the detailed phased implementation plan into executable backlog tickets for official frontend, partner storefront, partner portal, admin surfaces, and surface-policy enforcement.

---

## 1. Document Role

This document is the `Phase 6` execution bridge between:

- the canonical specification package;
- the domain dependency matrix;
- the detailed phased implementation plan;
- the operational readiness package;
- the completed `Phase 5` gate evidence pack;
- the partner portal product package created on 2026-04-18.

It exists so web frontend, partner portal, admin platform, support, finance, and QA teams do not assemble incompatible customer and operator surfaces on top of already-frozen backend contracts.

This document does not reopen:

- realm, storefront, merchant, workspace, and legal foundations frozen in `Phase 1`;
- order, quote, checkout, refund, and dispute seams frozen in `Phase 2`;
- attribution, growth reward, stacking, and renewal rules frozen in `Phase 3`;
- settlement, statements, payout accounts, and payout workflow frozen in `Phase 4`;
- service identity, entitlements, and service-consumption truth frozen in `Phase 5`.

If a proposed `Phase 6` ticket changes any of those, the canonical documents must be updated first.

---

## 2. Execution Rules

Execution for `Phase 6` follows these rules:

1. `Phase 6` starts only after `Phase 5` engineering gate is green.
2. Official customer web, partner storefront, partner portal, and admin surfaces remain separate surface families even when they share route primitives, UI atoms, or transport helpers.
3. Customer-facing commerce surfaces must read and write backend-owned contracts only.
4. Official CyberVPN surfaces must never expose self-serve markup, payout, or workspace-operator controls.
5. Partner portal must remain a workspace operating surface and must not become a shadow admin console.
6. Partner storefront must remain a customer-branded commerce surface and must not absorb partner-operator tasks.
7. Admin surfaces must own review, override, freeze, maker-checker, and internal explainability flows.
8. Surface policy matrix enforcement is a product invariant, not a documentation-only concern.
9. With `cacheComponents: true`, server-side reads must stay server-first by default; cached scopes must not capture request-scoped auth or cookie state implicitly.
10. Every `Phase 6` ticket must produce at least one of:
    - merged code;
    - frozen UI/API contract updates;
    - executable tests;
    - replay, shadow, or gate evidence.

---

## 3. Ticket Naming And Board Model

Ticket identifiers use the format:

- `T6.x` for `Phase 6`

Recommended workboards:

| Board | Scope | Primary owners |
|---|---|---|
| `B19` | official customer frontend and canonical commerce/service-access integration | frontend platform, backend platform |
| `B20` | partner storefront engine, host resolution, brand/storefront/legal bindings | frontend platform, commerce platform |
| `B21` | partner portal workspace modules, finance, reporting, compliance, cases | frontend platform, partner domain |
| `B22` | admin support, finance, attribution, disputes, entitlements, governance surfaces | admin platform, finance ops, support enablement |
| `B23` | surface policy enforcement, realm isolation, support routing, QA, and gate closure | platform, security, QA |

Suggested backlog labels:

- `phase-6`
- `surface-delivery`
- `official-frontend`
- `partner-storefront`
- `partner-portal`
- `admin-ops`
- `surface-policy`
- `realm-aware`
- `blocking`

---

## 4. Sequencing Summary

| Ticket | Packet alignment | Primary board | Size | Hard blockers |
|---|---|---|---|---|
| `T6.1` | `P6.1` | `B19` | `L` | `Phase 5 gate`, `T2.2`, `T2.3`, `T2.4`, `T5.2`, `T5.4` |
| `T6.2` | `P6.2` | `B20` | `L` | `T1.1`, `T1.3`, `T1.6`, `T3.5`, `T6.1` |
| `T6.3` | `P6.3` | `B21` | `L` | `T1.4`, `T4.2`, `T4.3`, `T4.4`, `T6.1` |
| `T6.4` | portal finance, reporting, and case-operating surfaces | `B21` | `L` | `T6.3`, `T3.7`, `T4.6` |
| `T6.5` | `P6.4` | `B22` | `L` | `T3.3`, `T4.4`, `T4.5`, `T5.5` |
| `T6.6` | `P6.5` | `B23` | `M` | `T6.1`, `T6.2`, `T6.3`, `T6.5` |
| `T6.7` | `P6.6` | `B23` | `M` | `T1.1`, `T1.6`, `T6.2`, `T6.3`, `T6.5` |
| `T6.8` | phase-exit evidence | `B23` | `M` | `T6.1`, `T6.2`, `T6.3`, `T6.4`, `T6.5`, `T6.6`, `T6.7` |

`T6.1` is the only valid starting point for `Phase 6` implementation.

---

## 5. Ticket Decomposition

## 5.1 `T6.1` Official Frontend Canonical Commerce And Service-Access Integration

**Packet alignment:** `P6.1`  
**Primary owners:** frontend platform, backend platform  
**Supporting owners:** QA

**Repository touchpoints:**

- Create or extend: `frontend/src/lib/api/`
- Modify: `frontend/src/app/[locale]/(dashboard)/subscriptions/`
- Modify: `frontend/src/app/[locale]/(dashboard)/payment-history/` where needed
- Modify: `frontend/src/app/[locale]/miniapp/` only where shared client helpers must stay compatible
- Create or extend: `frontend/src/lib/api/__tests__/`
- Create or extend: `frontend/src/app/[locale]/(dashboard)/subscriptions/components/__tests__/`

**Scope:**

- move official CyberVPN purchase flow to canonical `quote -> checkout_session -> order -> payment_attempt`;
- read active service state from canonical `entitlements/current` and `access-delivery-channels/current/service-state`;
- keep official customer dashboard separate from partner/operator concepts;
- keep official frontend on same-origin cookie auth and backend-owned policy enforcement.

**Acceptance criteria:**

- official web purchase flow no longer depends on legacy `payments/checkout/*` as the primary happy path;
- active subscription summary reads canonical entitlement state;
- official customer service-consumption summary is visible without partner/admin leakage;
- no official-surface path exposes reseller markup or payout controls.

## 5.2 `T6.2` Partner Storefront Engine, Host Resolution, And Realm-Aware Commerce Shell

**Packet alignment:** `P6.2`  
**Primary owners:** frontend platform, commerce platform  
**Supporting owners:** QA, legal/compliance

**Scope:**

- convert the separate `partner` app into a generic multi-brand storefront and partner workspace shell;
- establish host-based storefront resolution and brand-aware public routing;
- bind storefront to merchant, legal-document set, communication profile, and support profile at runtime;
- enforce storefront-specific login and checkout boundaries.

**Acceptance criteria:**

- host resolution selects storefront and realm deterministically;
- partner-branded customer routes do not silently reuse official-web customer assumptions;
- legal and support context are storefront-aware.

## 5.3 `T6.3` Partner Portal Workspace Data Integration

**Packet alignment:** `P6.3`  
**Primary owners:** frontend platform, partner domain  
**Supporting owners:** finance ops, partner ops, QA

**Scope:**

- replace local or static portal-state dependencies with canonical workspace APIs;
- integrate organization, team, workspace status, codes, statements, payout accounts, and backend-owned permission overlays into portal runtime state;
- preserve status and visibility matrices already defined in the partner portal package.

**Acceptance criteria:**

- partner portal reads workspace state and role/permission scope from backend contracts where those contracts already exist;
- statements and payout accounts are visible in portal without admin leakage;
- workspace role behavior is backend-owned;
- unresolved partner-facing seams are recorded explicitly instead of being papered over with synthetic local data.

### 5.3.1 `T6.3` Follow-Up Seams Captured During Implementation

`T6.3` is the runtime integration baseline for the partner portal, not the final closure of every portal module. During implementation, the following follow-up seams were identified and must be completed in later slices instead of being faked inside the portal shell:

- partner-facing `traffic_declarations` and `creative_approvals` APIs;
- canonical lane membership and lane-readiness contracts for the `programs` surface;
- explicit workspace switcher UX on top of canonical `partner-workspaces/me`, instead of query-param-first fallback selection; later closed by `RB-004`;
- richer partner inbox/workflow actions on top of canonical `review_requests` and `cases` resources;
- richer reporting/export contracts after the first canonical `T6.4` workspace overlays.

These seams did not block `T6.3` baseline closure, but they originally blocked claiming that the full partner portal was feature-complete. `RB-001` later closed the partner-facing `traffic_declarations / creative_approvals` action rails, `RB-002` later closed the canonical inbox/workflow actions for `review_requests` and `cases`, and `RB-003` later closed the backend-owned lane-membership and lane-readiness `programs` surface.

## 5.4 `T6.4` Partner Portal Finance, Reporting, And Case Operations

**Packet alignment:** derived from `P6.3` and finance/risk packets  
**Primary owners:** frontend platform, finance ops, partner ops  
**Supporting owners:** QA

**Scope:**

- partner-facing finance views from canonical statements, payout-account readiness, payout status, and explainability;
- partner-facing order, conversion, analytics, export, review-request, and case views with row-level visibility;
- scoped exports and finance history aligned with canonical reporting contracts.

**Acceptance criteria:**

- partner portal finance pages use statement and payout APIs, not synthetic local aggregates;
- partner-visible cases stay scoped and exclude internal moderation queues;
- exports reflect workspace scope and role scope.

## 5.5 `T6.5` Admin Support, Finance, Attribution, Dispute, And Entitlement Surfaces

**Packet alignment:** `P6.4`  
**Primary owners:** admin platform, finance ops, support enablement  
**Supporting owners:** QA, risk

**Scope:**

- admin read models for attribution explainability, payment disputes, statement lifecycle, payout workflow, risk reviews, and service consumption state;
- support-oriented inspection without direct SQL or internal scripts;
- finance/operator workflows aligned with maker-checker and audit controls.

**Acceptance criteria:**

- admin can inspect order, attribution, settlement, payout, and service-consumption context from UI contracts only;
- support and finance operator views remain role-scoped;
- internal overrides stay on admin surface only.

### 5.5.1 `T6.5` Follow-Up Seams Captured During Implementation

`T6.5` is the canonical admin-inspection baseline for customer operations, not the end-state admin console.
During implementation, the following follow-up seams were identified and explicitly deferred to later slices instead of being hidden behind local admin-only logic:

- customer operations insight is now aggregated through `/api/v1/admin/mobile-users/{user_id}/operations-insight`, and the later `RB-006` closure added a consolidated admin action rail through `/api/v1/admin/mobile-users/{user_id}/operations-insight/actions` while preserving canonical settlement resource ownership underneath;
- admin shell access still remains limited by the existing `admin/super_admin` surface gate, while the new aggregate already supports role-scoped data visibility for support and finance paths;
- richer case, dispute-evidence, and review-queue action flows were later closed by `RB-007` through an internal `security/review-queue` console and canonical dispute-case actions inside `customer operations`;
- finance-grade export/download affordances for customer-linked statement and payout evidence were later closed by `RB-008` through backend-owned admin attachment endpoints and settlement-card download affordances inside `customer operations`.

These seams do not block `T6.5` baseline closure, but they do block claiming that the admin operator surface is feature-complete.

## 5.6 `T6.6` Surface Policy Matrix Enforcement

**Packet alignment:** `P6.5`  
**Primary owners:** platform, security, frontend platform  
**Supporting owners:** QA

**Scope:**

- implement shared enforcement for surface capabilities across official frontend, partner storefront, partner portal, and admin;
- gate code entry, promo stacking, payout visibility, workspace operations, and internal review tools by surface and role;
- codify no-markup-on-official-surface rules in UI and route behavior.

**Acceptance criteria:**

- official web never renders partner markup controls;
- partner portal never renders admin-only moderation or maker-checker controls;
- partner storefront never renders workspace-operator modules;
- surface policy behavior is testable, not copy-only.

### 5.6.1 `T6.6` Closure Notes And Remaining Seams

`T6.6` is now enforced as runtime behavior rather than copy-only guidance.
The delivered baseline covers:

- official web surface policy helpers that keep invite/promo flows while explicitly suppressing partner markup visibility on the official checkout surface;
- partner surface capability matrix used by proxy routing, legacy admin route blocking, and client-side admin wallet moderation guards;
- admin console surface policy helpers that keep maker-checker controls attached to internal admin surfaces rather than partner-facing shells.

The following seams remain intentionally deferred:

- richer cross-surface policy overlays for lane memberships, workspace switching, and export scheduling remained part of later portal slices at `T6.6` time; these were later closed by `RB-003`, `RB-004`, and `RB-005`;
- frontend browser tests for the official surface policy were historically constrained by the Vitest `cssstyle -> @asamuzakjp/css-color` worker boot issue, but that workspace blocker was later removed by `RB-009` and the affected packs should now be interpreted as normal test runs rather than bootstrap failures.

## 5.7 `T6.7` Support Routing, Communication Profile, And Legal-Surface Integration

**Packet alignment:** `P6.6`  
**Primary owners:** frontend platform, support enablement, legal/compliance  
**Supporting owners:** QA

**Scope:**

- surface-specific support entry points;
- communication profile selection per brand/storefront/realm;
- legal-surface rendering and acceptance routing;
- customer versus partner/operator support-channel separation.

**Acceptance criteria:**

- official web and partner storefronts route to the correct support profile;
- partner portal workspace support does not reuse customer storefront messaging blindly;
- legal-document links and acceptance context are surface-aware.

### 5.7.1 `T6.7` Closure Notes And Remaining Seams

`T6.7` is considered closed with:

- explicit official-web support and communication routing surfaced on `/help` and `/contact`;
- branded storefront legal acceptance wired to canonical `/api/v1/policy-acceptance/*` with storefront-aware device context;
- storefront support copy explicitly separated from partner-portal workspace support;
- partner portal `cases` surface explicitly documenting the boundary between workspace support and storefront customer support.

Residual seams intentionally left for later slices:

- official-web legal dashboards remain marketing-first documents and do not record acceptance because canonical acceptance is still customer-authenticated and storefront-bound;
- the workspace-versus-storefront support boundary is explicit and persists, while the actual partner inbox/workflow actions were later closed by `RB-002`.

## 5.8 `T6.8` Phase 6 Gate And Evidence Pack

**Packet alignment:** phase-exit evidence  
**Primary owners:** QA, frontend platform, platform  
**Supporting owners:** support enablement, finance ops, partner ops

**Scope:**

- freeze evidence for official frontend, partner storefront, partner portal, and admin core modules;
- attach realm-isolation proof, surface-policy proof, and host-resolution proof;
- record unresolved but non-blocking residuals for rollout rings.

**Acceptance criteria:**

- official frontend UI contract freeze is recorded against canonical commerce and service-access APIs;
- partner portal proves statement, payout-account, and traffic-declaration visibility from backend contracts;
- host and realm isolation evidence exists for official and partner surfaces.

### 5.8.1 `T6.8` Closure Notes And Remaining Seams

`T6.8` is considered closed from the engineering side with:

- backend-owned `traffic_declarations` overlays exposed on `/api/v1/partner-workspaces/{workspace_id}/traffic-declarations`;
- partner portal runtime state consuming canonical traffic-declaration visibility instead of local compliance placeholders;
- generated-contract and surface-boundary freeze checks in place for backend, partner, admin, and official-web consumers;
- a named `Phase 6` exit evidence pack in [../testing/partner-platform-phase6-exit-evidence.md](../testing/partner-platform-phase6-exit-evidence.md), with the 2026-04-18 closure run recorded against real command output.

Residual seams intentionally deferred to later slices:

- `RB-001` later closed the dedicated workflow action rails for `traffic_declarations` and `creative_approvals`, and `RB-002` later closed richer inbox actions on canonical `review_requests` and `cases`;
- canonical lane-membership and lane-readiness overlays, explicit workspace-switcher UX, and export scheduling remain later portal slices;
- official-web combined Vitest execution that includes the surface-policy test was historically blocked by the pre-existing `cssstyle -> @asamuzakjp/css-color` worker issue and was therefore recorded as a non-blocking residual rather than a `Phase 6` regression; that blocker was later retired by `RB-009` on 2026-04-19.

---

## 6. Phase 6 Completion Gate

`Phase 6` is complete only when:

1. `T6.1` through `T6.7` are merged or explicitly waived by governance;
2. official frontend, partner storefront, partner portal, and admin each have distinct and enforced surface boundaries;
3. official web purchase and service-access flows are canonical-contract-driven;
4. partner portal no longer depends on mock-only operating state for finance-critical or compliance-critical sections;
5. realm-isolation, surface-policy, and host-resolution validation packs are green;
6. `Phase 6` exit evidence exists and is ready for rollout-ring use.

Until then, `Phase 6` remains implementation in progress.
