# CyberVPN Partner Platform Phase 7 Execution Ticket Decomposition

**Date:** 2026-04-18  
**Status:** Execution ticket decomposition for `Phase 7` implementation start  
**Purpose:** translate `Phase 7` from the detailed phased implementation plan into executable backlog tickets for event publication, analytical marts, reporting surfaces, channel parity, and partner-facing integration contracts.

---

## 1. Document Role

This document is the `Phase 7` execution bridge between:

- the canonical specification package;
- the domain dependency matrix;
- the detailed phased implementation plan;
- the operational readiness package;
- the completed `Phase 6` gate evidence pack.

It exists so analytics, backend platform, channel teams, partner portal, and QA do not invent ad-hoc reporting pipelines or channel-specific state models after the customer and operator surfaces are already frozen.

This document does not reopen:

- identity, storefront, policy, and partner-workspace foundations frozen in `Phase 1`;
- canonical commerce, order, refund, and dispute seams frozen in `Phase 2`;
- attribution, growth reward, stacking, and renewal ownership rules frozen in `Phase 3`;
- settlement, statement, payout-account, and payout workflow rules frozen in `Phase 4`;
- service-identity and entitlement truth frozen in `Phase 5`;
- surface-boundary rules and partner-portal/operator constraints frozen in `Phase 6`.

If a proposed `Phase 7` ticket changes any of those, the canonical documents must be updated first.

---

## 2. Execution Rules

Execution for `Phase 7` follows these rules:

1. `Phase 7` starts only after `Phase 6` engineering gate is green.
2. The event/outbox layer is canonical infrastructure, not a provider-specific webhook queue.
3. Analytical marts must reconcile to canonical OLTP objects instead of re-deriving core business truth from frontend telemetry.
4. Channel parity must consume the same identity, order, entitlement, and reporting contracts already frozen in earlier phases.
5. Partner exports and reporting APIs remain row-level scoped to workspace and role visibility.
6. Postback and reporting publication semantics must be replay-safe and idempotent.
7. No channel-specific rollout may invent alternative entitlement or order-history semantics to “simplify” adoption.
8. Every `Phase 7` ticket must produce at least one of:
   - merged code;
   - frozen event or API contract updates;
   - executable tests;
   - deterministic replay or reconciliation evidence.

---

## 3. Ticket Naming And Board Model

Ticket identifiers use the format:

- `T7.x` for `Phase 7`

Recommended workboards:

| Board | Scope | Primary owners |
|---|---|---|
| `B24` | event/outbox layer, publication state, replay-safe reporting contracts | backend platform, data platform |
| `B25` | analytical marts, reconciliation views, exports, explainability reporting | data/BI, backend platform |
| `B26` | partner reporting and external integration APIs, postbacks, export delivery | backend platform, partner ops |
| `B27` | Telegram, mobile, desktop parity on canonical contracts | channel teams, backend platform |
| `B28` | replay evidence, parity evidence, and phase closure | QA, platform, data/BI |

Suggested backlog labels:

- `phase-7`
- `event-outbox`
- `reporting`
- `analytical-marts`
- `partner-exports`
- `channel-parity`
- `postbacks`
- `blocking`

---

## 4. Sequencing Summary

| Ticket | Packet alignment | Primary board | Size | Hard blockers |
|---|---|---|---|---|
| `T7.1` | `P7.1` | `B24` | `L` | `Phase 6 gate`, `T2.3`, `T3.3`, `T4.2`, `T5.2` |
| `T7.2` | `P7.2` | `B25` | `L` | `T7.1`, `T4.6` |
| `T7.3` | `P7.3` | `B25`, `B26` | `L` | `T7.2`, `T6.3`, `T3.7`, `T4.6` |
| `T7.4` | `P7.4` | `B27` | `L` | `T5.2`, `T6.5`, `T7.1` |
| `T7.5` | `P7.5` | `B27` | `L` | `T5.2`, `T6.5`, `T7.1` |
| `T7.6` | `P7.6` | `B26` | `L` | `T3.7`, `T4.6`, `T7.1` |
| `T7.7` | parity, replay, and analytical evidence | `B28` | `M` | `T7.2`, `T7.3`, `T7.4`, `T7.5`, `T7.6` |
| `T7.8` | phase-exit evidence | `B28` | `M` | `T7.1`, `T7.2`, `T7.3`, `T7.4`, `T7.5`, `T7.6`, `T7.7` |

`T7.1` is the only valid starting point for `Phase 7` implementation.

---

## 5. Ticket Decomposition

## 5.1 `T7.1` Reliable Outbox And Event Publication Foundation

**Packet alignment:** `P7.1`  
**Primary owners:** backend platform, data platform  
**Supporting owners:** QA

**Repository touchpoints:**

- Create: `backend/src/infrastructure/database/models/outbox_event_model.py`
- Create: `backend/src/infrastructure/database/repositories/outbox_repo.py`
- Create: `backend/src/application/events/outbox.py`
- Create: `backend/src/application/use_cases/reporting/`
- Create: `backend/src/presentation/api/v1/reporting/`
- Modify: `backend/src/application/use_cases/orders/create_order_from_checkout.py`
- Modify: `backend/src/application/use_cases/attribution/order_resolution/resolve_order_attribution.py`
- Modify: `backend/src/application/use_cases/settlement/partner_statements.py`
- Modify: `backend/src/application/use_cases/risk/create_risk_review.py`
- Modify: `backend/src/application/use_cases/service_access/entitlements.py`
- Modify: `backend/src/application/use_cases/payments/post_payment.py`
- Modify: `backend/tests/helpers/realm_auth.py`
- Create: `backend/tests/integration/test_reporting_outbox.py`
- Create: `backend/tests/contract/test_reporting_outbox_openapi_contract.py`
- Create: `backend/tests/contract/test_phase7_api_surface_contract.py`
- Modify: `docs/api/partner-platform-enum-registry.md`
- Modify: `docs/api/partner-platform-event-taxonomy.md`
- Modify: `docs/plans/2026-04-17-partner-platform-api-specification-package.md`

**Scope:**

- first-class `outbox_events` and `outbox_publications`;
- canonical `analytics_mart` and `operational_replay` consumer keys for the baseline publication model;
- frozen publication lifecycle for analytics/replay consumers;
- canonical event recording from order, attribution, settlement, risk, and entitlement transitions;
- internal reporting inspection and publication lifecycle APIs.

**Acceptance criteria:**

- canonical domain transitions produce outbox rows in the same database transaction as the source-of-truth objects;
- outbox publications are claimable and reconcilable without duplicate side effects;
- event family names stay aligned with the frozen `Phase 0` taxonomy;
- no reporting or replay path depends on scraping ad-hoc logs.

## 5.2 `T7.2` Analytical Marts And Reconciliation Views

**Packet alignment:** `P7.2`  
**Primary owners:** data/BI, backend platform  
**Supporting owners:** finance ops, QA

**Scope:**

- canonical analytical grains;
- order, attribution, settlement, entitlement, and export marts;
- reconciliation views from outbox-driven or replay-safe contracts.

**Repository touchpoints:**

- Create: `backend/src/application/services/phase7_reporting_marts.py`
- Create: `backend/scripts/build_phase7_reporting_marts_pack.py`
- Create: `backend/scripts/print_phase7_reporting_marts_summary.py`
- Create: `backend/tests/contract/test_phase7_reporting_marts_pack.py`
- Create: `docs/testing/partner-platform-phase7-analytical-marts-and-reconciliation-pack.md`

**Acceptance criteria:**

- marts reconcile to OLTP truth;
- dimensions and grains stay canonical;
- finance and partner-reporting numbers do not diverge silently.

## 5.3 `T7.3` Partner Dashboards, Exports, And Explainability Reports

**Packet alignment:** `P7.3`  
**Primary owners:** data/BI, frontend platform, backend platform  
**Supporting owners:** finance ops, partner ops, QA

**Scope:**

- partner dashboards and export jobs on canonical marts;
- explainability-ready reporting drilldowns;
- row-level scoped partner reporting APIs.

**Repository touchpoints:**

- Create: `backend/src/application/use_cases/reporting/workspace_reporting.py`
- Modify: `backend/src/application/use_cases/reporting/__init__.py`
- Modify: `backend/src/presentation/api/v1/partners/routes.py`
- Modify: `backend/src/presentation/api/v1/partners/schemas.py`
- Modify: `backend/tests/integration/test_partner_portal_reporting_reads.py`
- Modify: `backend/tests/contract/test_partner_statement_openapi_contract.py`
- Modify: `partner/src/lib/api/partner-portal.ts`
- Modify: `partner/src/lib/api/__tests__/partner-portal.test.ts`

**Acceptance criteria:**

- partner reporting uses canonical analytical contracts;
- exports preserve workspace and role isolation;
- explainability reporting matches operational truth.

## 5.4 `T7.4` Telegram Parity On Canonical Contracts

**Packet alignment:** `P7.4`  
**Primary owners:** channel teams, backend platform  
**Supporting owners:** QA

**Scope:**

- Telegram Bot and Mini App consume canonical identity, order, entitlement, and reporting contracts;
- parity on order history, entitlement state, and basic reporting visibility.

**Acceptance criteria:**

- Telegram surfaces do not invent alternate entitlement or order semantics;
- Telegram reads the same current-service-state and order/reporting primitives already frozen for web.

**Implementation touchpoints:**

- Backend Telegram parity adapters: `backend/src/presentation/api/v1/telegram/routes.py`, `backend/src/presentation/api/v1/telegram/schemas.py`
- Telegram Bot canonical consumers: `services/telegram-bot/src/services/api_client.py`, `services/telegram-bot/src/handlers/menu.py`, `services/telegram-bot/src/handlers/account.py`
- Mini App canonical consumers: `frontend/src/app/[locale]/miniapp/home/page.tsx`, `frontend/src/app/[locale]/miniapp/payments/page.tsx`, `frontend/src/app/[locale]/miniapp/profile/page.tsx`

**Closure notes:**

- `T7.4` is closed when Telegram Bot and Mini App read canonical entitlements, orders, and current service state without fallback business semantics of their own;
- backend contract and integration packs plus Telegram Bot unit tests must be green before rollout-ring consumption;
- targeted Mini App lint is required; the historical `cssstyle -> @asamuzakjp/css-color` worker bootstrap issue was later retired by `RB-009`, so combined Mini App Vitest now starts and any remaining failures are ordinary application/test debt rather than harness boot failure.

## 5.5 `T7.5` Mobile And Desktop Parity On Canonical Contracts

**Packet alignment:** `P7.5`  
**Primary owners:** channel teams, backend platform  
**Supporting owners:** QA

**Scope:**

- mobile and desktop consume canonical identity, order, entitlement, and reporting contracts;
- service-access and order-history parity without provider-specific forks in business truth.

**Acceptance criteria:**

- mobile and desktop reuse canonical service-state and reporting semantics;
- parity proof exists against official web behavior.

**Closure notes:**

- mobile subscription data source now reads canonical `entitlements/current`, `current service-state`, and `orders`;
- desktop reads canonical customer profile, entitlements, service-state, and orders through Tauri IPC backed by stored Helix backend credentials, while preserving local engine-specific management surfaces.

## 5.6 `T7.6` Partner API, Reporting API, And Postback Readiness

**Packet alignment:** `P7.6`  
**Primary owners:** backend platform, partner ops  
**Supporting owners:** QA, risk

**Scope:**

- partner-facing reporting APIs;
- postback delivery readiness and status reporting;
- scoped reporting/export token usage on canonical contracts.

**Acceptance criteria:**

- external reporting and postback contracts are replay-safe and row-level scoped;
- partner-facing integrations do not bypass canonical attribution and settlement truth.

**Closure notes:**

- workspace-scoped `integration-credentials`, `integration-delivery-logs`, and `postback-readiness` overlays are backend-owned and no longer synthetic portal-only state;
- `reporting_api_token` and `postback_secret` are first-class canonical credential objects with explicit workspace scope;
- token-authenticated `reporting/partner-workspaces/{workspace_id}/snapshot` proves machine-readable reporting access on canonical marts without bypassing row-level isolation;
- partner integrations surface must read runtime overlays from canonical backend contracts before `T7.6` can be marked complete.

## 5.7 `T7.7` Replay, Parity, And Analytical Evidence

**Packet alignment:** replay and parity evidence  
**Primary owners:** QA, data/BI, backend platform  
**Supporting owners:** channel teams

**Scope:**

- deterministic analytical replay packs;
- parity evidence across official web and at least two additional channels;
- export and postback evidence packs.

**Acceptance criteria:**

- replay output is deterministic and mismatch vocabulary is explicit;
- channel parity and reporting parity are evidence-backed, not asserted.

**Closure notes:**

- `T7.7` is closed only when a deterministic replay/evidence builder exists for channel parity, partner exports, and postback delivery evidence;
- the pack must embed canonical analytical reference from `T7.2`, not re-invent an alternate reporting truth;
- parity coverage must include `official_web` plus at least two additional channels before the ticket can be considered rollout-ready.

## 5.8 `T7.8` Phase 7 Gate And Evidence Pack

**Packet alignment:** phase-exit evidence  
**Primary owners:** QA, backend platform, data/BI  
**Supporting owners:** finance ops, partner ops, channel teams

**Scope:**

- freeze evidence for event/outbox, marts, partner reporting, parity, and external integration surfaces;
- record unresolved but non-blocking residuals;
- attach replay, reconciliation, and parity evidence.

**Acceptance criteria:**

- event-contract freeze is recorded against canonical outbox families;
- reporting-schema freeze is recorded for marts and exports;
- parity evidence exists across official web and at least two additional channels.

---

## 6. Phase 7 Completion Gate

`Phase 7` is complete only when:

1. `T7.1` through `T7.7` are merged or explicitly waived by governance;
2. canonical outbox publication and analytical foundations exist and are replay-safe;
3. partner reporting and exports no longer depend on synthetic portal aggregates;
4. parity proof exists across official web and at least two additional channels;
5. `Phase 7` exit evidence exists and is ready for rollout-ring use.

Until then, `Phase 7` remains implementation in progress.
