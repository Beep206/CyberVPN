# CyberVPN Partner Platform Phase 8 Execution Ticket Decomposition

**Date:** 2026-04-19  
**Status:** Execution ticket decomposition for `Phase 8` implementation start  
**Purpose:** translate `Phase 8` from the detailed phased implementation plan into executable backlog tickets for advanced risk workflows, operational overlays, shadow mode, limited pilots, and production-readiness gating.

---

## 1. Document Role

This document is the `Phase 8` execution bridge between:

- the canonical specification package;
- the domain dependency matrix;
- the detailed phased implementation plan;
- the operational readiness package;
- the completed `Phase 7` gate evidence pack.

It exists so risk, finance, support, partner ops, QA, and rollout owners do not improvise pilot governance, shadow tolerances, or approval rails after reporting and channel-parity foundations are already frozen.

This document does not reopen:

- identity, workspace, and policy-version foundations frozen in `Phase 1`;
- order, refund, and dispute truth frozen in `Phase 2`;
- attribution, growth reward, and renewal ownership rules frozen in `Phase 3`;
- settlement and payout workflow rules frozen in `Phase 4`;
- service-access truth frozen in `Phase 5`;
- surface and operator boundary rules frozen in `Phase 6`;
- outbox, marts, exports, and channel-parity contracts frozen in `Phase 7`.

If a `Phase 8` ticket needs to change those contracts, the canonical documents must be updated first.

---

## 2. Execution Rules

Execution for `Phase 8` follows these rules:

1. `Phase 8` starts only after `Phase 7` engineering gate is green.
2. Risk and governance workflows must remain first-class operational objects, not portal-only placeholders.
3. Shadow comparisons must consume deterministic replay packs and canonical marts, not ad-hoc spreadsheet exports.
4. Pilot rollout controls must be lane-aware, surface-aware, and reversible at the routing or workflow layer.
5. No performance, media-buyer, or reseller pilot may bypass risk review queues, governance actions, traffic declarations, or creative approval posture.
6. Production-readiness evidence must combine engineering, finance, risk, support, and partner-ops sign-off.
7. `Phase 8` may add overlays and operational controls, but it may not mint alternate commercial, settlement, or entitlement truth.
8. Every `Phase 8` ticket must produce at least one of:
   - merged code;
   - frozen API or event contract updates;
   - executable tests;
   - deterministic shadow, replay, or pilot evidence.

---

## 3. Ticket Naming And Board Model

Ticket identifiers use the format:

- `T8.x` for `Phase 8`

Recommended workboards:

| Board | Scope | Primary owners |
|---|---|---|
| `B29` | advanced risk-review workflows, governance actions, operational review queues | backend platform, risk ops |
| `B30` | policy acceptance hardening, traffic declarations, creative approvals, dispute overlays | risk ops, partner ops, backend platform |
| `B31` | shadow attribution, settlement, reporting, and replay evidence | data/BI, finance ops, QA |
| `B32` | pilot cohort activation, lane-specific rollout controls, partner/storefront pilots | product ops, partner ops, support |
| `B33` | production-readiness evidence, no-go governance, final ring-promotion control | platform, finance, risk, support, QA |

Suggested backlog labels:

- `phase-8`
- `risk-ops`
- `governance`
- `shadow-mode`
- `pilot`
- `rollout-readiness`
- `blocking`

---

## 4. Sequencing Summary

| Ticket | Packet alignment | Primary board | Size | Hard blockers |
|---|---|---|---|---|
| `T8.1` | `P8.1` | `B29` | `L` | `Phase 7 gate`, `T1.6`, `T2.5`, `T3.7`, `T4.5`, `T6.4` |
| `T8.2` | `P8.2` | `B30` | `L` | `T8.1`, `T6.3`, `T6.4`, `T7.6` |
| `T8.3` | attribution shadow and explainability comparison | `B31` | `M` | `T3.7`, `T7.2`, `T7.7` |
| `T8.4` | settlement, payout, and reporting shadow comparison | `B31` | `L` | `T4.6`, `T4.7`, `T7.2`, `T7.7` |
| `T8.5` | pilot cohort activation and lane-limited real traffic | `B32` | `L` | `T8.1`, `T8.2`, `T8.3`, `T8.4` |
| `T8.6` | rollback triggers, no-go controls, and owner-runbook hardening | `B33` | `M` | `T8.5`, operational readiness package |
| `T8.7` | production-readiness package and cross-functional sign-off bundle | `B33` | `M` | `T8.3`, `T8.4`, `T8.5`, `T8.6` |
| `T8.8` | phase-exit evidence and ring-promotion gate | `B33` | `M` | `T8.1`, `T8.2`, `T8.3`, `T8.4`, `T8.5`, `T8.6`, `T8.7` |

`T8.1` is the only valid starting point for `Phase 8` implementation.

---

## 5. Ticket Decomposition

## 5.1 `T8.1` Advanced Risk Review Queue, Evidence Attachments, And Governance Actions

**Packet alignment:** `P8.1`  
**Primary owners:** backend platform, risk ops  
**Supporting owners:** finance ops, support, QA

**Repository touchpoints:**

- Create: `backend/src/infrastructure/database/models/risk_review_attachment_model.py`
- Create: `backend/src/infrastructure/database/models/governance_action_model.py`
- Modify: `backend/src/infrastructure/database/repositories/risk_subject_repo.py`
- Create: `backend/src/application/use_cases/risk/attach_risk_review_attachment.py`
- Create: `backend/src/application/use_cases/risk/resolve_risk_review.py`
- Create: `backend/src/application/use_cases/risk/create_governance_action.py`
- Create: `backend/src/application/use_cases/risk/get_risk_review.py`
- Create: `backend/src/application/use_cases/risk/list_risk_review_queue.py`
- Create: `backend/src/application/use_cases/risk/list_governance_actions.py`
- Modify: `backend/src/presentation/api/v1/security/routes.py`
- Modify: `backend/src/presentation/api/v1/security/schemas.py`
- Modify: `backend/src/presentation/api/v1/router.py`
- Modify: `backend/src/application/events/partner_platform_events.py`
- Modify: `backend/tests/helpers/realm_auth.py`
- Create: `backend/tests/integration/test_risk_governance_workflows.py`
- Create: `backend/tests/contract/test_risk_governance_workflow_openapi_contract.py`
- Modify: `docs/api/partner-platform-enum-registry.md`
- Modify: `docs/api/partner-platform-event-taxonomy.md`
- Modify: `docs/plans/2026-04-17-partner-platform-api-specification-package.md`

**Scope:**

- first-class operational review queue across `risk_reviews`;
- review detail read model with subject, attachments, and linked governance actions;
- evidence attachment lineage on risk reviews;
- risk review resolution workflow with canonical close states;
- governance action recording for payout freeze, code suspension, reserve extension, traffic probation, creative restriction, and manual override.

**Acceptance criteria:**

- operators can read queue and review detail without mutating risk state;
- admins can attach evidence, resolve reviews, and record governance actions on canonical resources;
- governance actions remain linked to `risk_subject` and optionally to a triggering `risk_review`;
- review and governance transitions emit canonical risk events for replay and reporting;
- `Phase 8` can reference real review queue objects instead of synthetic partner-portal placeholders.

## 5.2 `T8.2` Policy Acceptance Hardening, Traffic Declarations, Creative Approvals, And Dispute-Case Overlays

**Packet alignment:** `P8.2`  
**Primary owners:** backend platform, risk ops, partner ops  
**Supporting owners:** support, finance ops, QA

**Repository touchpoints:**

- Modify: `backend/src/infrastructure/database/repositories/legal_document_repo.py`
- Create: `backend/src/infrastructure/database/models/partner_traffic_declaration_model.py`
- Create: `backend/src/infrastructure/database/models/creative_approval_model.py`
- Create: `backend/src/infrastructure/database/models/dispute_case_model.py`
- Create: `backend/src/infrastructure/database/repositories/governance_repo.py`
- Create: `backend/src/application/use_cases/governance/traffic_declarations.py`
- Create: `backend/src/application/use_cases/governance/creative_approvals.py`
- Create: `backend/src/application/use_cases/governance/dispute_cases.py`
- Modify: `backend/src/presentation/api/v1/policy_acceptance/routes.py`
- Create: `backend/src/presentation/api/v1/traffic_declarations/routes.py`
- Create: `backend/src/presentation/api/v1/creative_approvals/routes.py`
- Create: `backend/src/presentation/api/v1/dispute_cases/routes.py`
- Modify: `backend/src/presentation/api/v1/partners/routes.py`
- Modify: `backend/src/presentation/api/v1/router.py`
- Modify: `backend/tests/helpers/realm_auth.py`
- Create: `backend/tests/contract/test_phase8_operational_overlay_openapi_contract.py`
- Create: `backend/tests/integration/test_phase8_operational_overlays.py`
- Modify: `backend/tests/integration/test_legal_document_acceptance.py`
- Modify: `backend/tests/integration/test_partner_portal_reporting_reads.py`
- Modify: `docs/api/partner-platform-enum-registry.md`
- Modify: `docs/plans/2026-04-17-partner-platform-api-specification-package.md`

**Scope:**

- harden `accepted_legal_documents` and compliance evidence retrieval;
- first-class `traffic_declarations`, `creative_approvals`, and `dispute_cases`;
- partner-workspace action rails instead of read-only placeholders;
- operational linkage from dispute cases to canonical `payment_disputes`.

**Acceptance criteria:**

- performance-lane pilots cannot start without declaration and approval posture;
- dispute casework is operationally distinct from provider dispute state;
- support and partner ops use backend-owned actions, not local portal-only state.

## 5.3 `T8.3` Shadow Attribution And Explainability Comparison

**Packet alignment:** `P8.3`  
**Primary owners:** data/BI, growth/platform, QA  
**Supporting owners:** risk ops, support

**Repository touchpoints:**

- Create: `backend/src/application/services/phase8_attribution_shadow.py`
- Create: `backend/scripts/build_phase8_attribution_shadow_pack.py`
- Create: `backend/scripts/print_phase8_attribution_shadow_summary.py`
- Create: `backend/tests/contract/test_phase8_attribution_shadow_pack.py`
- Create: `docs/testing/partner-platform-phase8-attribution-shadow-pack.md`

**Scope:**

- deterministic shadow attribution comparisons;
- explainability diff packs for order attribution, binding, and renewal ownership;
- approved divergence vocabulary and tolerances for pilot promotion.

**Acceptance criteria:**

- shadow attribution can be run repeatedly from canonical replay inputs;
- explainability reports call out why legacy and canonical outcomes differ;
- blocking mismatches stop pilot promotion.

## 5.4 `T8.4` Shadow Settlement, Payout, And Reporting Comparison

**Packet alignment:** `P8.3`  
**Primary owners:** finance ops, data/BI, backend platform  
**Supporting owners:** QA, partner ops

**Repository touchpoints:**

- Create: `backend/src/application/services/phase8_settlement_shadow.py`
- Create: `backend/scripts/build_phase8_settlement_shadow_pack.py`
- Create: `backend/scripts/print_phase8_settlement_shadow_summary.py`
- Create: `backend/tests/contract/test_phase8_settlement_shadow_pack.py`
- Create: `docs/testing/partner-platform-phase8-settlement-shadow-pack.md`

**Scope:**

- shadow statements and payout-liability comparison;
- pilot payout dry-run reconciliation against canonical settlement truth;
- reporting and export parity checks during controlled live traffic.

**Acceptance criteria:**

- statement and liability mismatches are machine-readable and auditable;
- payout dry-run evidence exists before any pilot payout approval path;
- partner export parity is measured before ring promotion.

## 5.5 `T8.5` Limited Pilot Activation By Lane And Surface

**Packet alignment:** `P8.4`  
**Primary owners:** product ops, partner ops, support  
**Supporting owners:** finance ops, risk ops, QA

**Scope:**

- named pilot cohorts by lane and surface;
- lane-specific go/no-go criteria;
- controlled host, partner, and channel rollout windows;
- live pilot monitoring tied back to canonical shadow evidence.
- backend-owned `pilot_cohorts` and `pilot_rollout_windows` APIs for readiness, activation, and pause control.

**Acceptance criteria:**

- each pilot cohort has explicit owner, window, lane, and rollback trigger;
- performance/media-buyer pilots remain blocked unless `T8.1` and `T8.2` are green;
- pilot traffic can be paused without corrupting canonical order or settlement truth.

## 5.6 `T8.6` Rollback, No-Go, And Owner-Runbook Hardening

**Packet alignment:** `P8.4`, `P8.5`  
**Primary owners:** platform, finance ops, risk ops, support  
**Supporting owners:** QA

**Scope:**

- operational rollback triggers tied to real shadow and pilot metrics;
- owner-by-owner cutover and no-go checklist hardening;
- backend-owned `pilot_owner_acknowledgements`, `pilot_rollback_drills`, and `pilot_go_no_go_decisions`;
- lane-specific freeze, escalation, and pause procedures.

**Acceptance criteria:**

- no-go governance is explicit, signed, and actionable;
- rollback scope is bounded per cutover unit;
- evidence archives record both pilot continuation and pilot stop decisions.

## 5.7 `T8.7` Production-Readiness Package

**Packet alignment:** `P8.5`  
**Primary owners:** platform, QA  
**Supporting owners:** finance ops, risk ops, support, partner ops

**Scope:**

- signed production-readiness bundle;
- reconciled shadow and pilot evidence;
- canonical production bundle document linked into readiness and stabilization packages;
- final freeze checklist and residual-risk register.

**Acceptance criteria:**

- residual risks are named and owned;
- readiness bundle references the canonical replay, reconciliation, and pilot artifacts;
- production activation is impossible without signed cross-functional readiness.

## 5.8 `T8.8` Phase 8 Exit Evidence

**Packet alignment:** `P8.5`  
**Primary owners:** QA, platform  
**Supporting owners:** finance ops, risk ops, support, partner ops, product

**Scope:**

- canonical `Phase 8` exit evidence pack;
- operational-readiness sync;
- canonical `Phase 8` exit-evidence document linked into readiness, rehearsal, and stabilization packages;
- ring-promotion gate from pilot posture into broad cutover readiness.

**Acceptance criteria:**

- `Phase 8` evidence references signed shadow, pilot, and readiness artifacts;
- no rollout ring beyond approved pilot thresholds is possible without the exit pack;
- operational readiness documents point to the signed `Phase 8` evidence record.

---

## 6. Phase 8 Completion Gate

`Phase 8` is complete only when all of the following are true:

- advanced risk and governance workflows are first-class and operator-usable;
- required compliance and dispute overlays are operationally real, not portal-only placeholders;
- shadow attribution, settlement, and reporting packs are green within approved tolerances;
- limited pilots have signed lane-by-lane evidence and no-go governance;
- the production-readiness package and `Phase 8` exit evidence pack are signed.
