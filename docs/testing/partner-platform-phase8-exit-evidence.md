# CyberVPN Partner Platform Phase 8 Exit Evidence

**Date:** 2026-04-19  
**Status:** Phase 8 gate evidence pack  
**Purpose:** define the canonical automated evidence, shadow and pilot closure proof, and cross-functional sign-off checklist required to declare `Phase 8` complete and allow broad cutover readiness beyond approved pilot posture.

---

## 1. Gate Role

This document is the concrete exit-evidence companion to:

- [../plans/2026-04-17-partner-platform-detailed-phased-implementation-plan.md](../plans/2026-04-17-partner-platform-detailed-phased-implementation-plan.md)
- [../plans/2026-04-19-partner-platform-phase-8-execution-ticket-decomposition.md](../plans/2026-04-19-partner-platform-phase-8-execution-ticket-decomposition.md)
- [../plans/2026-04-17-partner-platform-operational-readiness-package.md](../plans/2026-04-17-partner-platform-operational-readiness-package.md)
- [../plans/2026-04-17-partner-platform-rehearsal-logs-and-evidence-archive-template.md](../plans/2026-04-17-partner-platform-rehearsal-logs-and-evidence-archive-template.md)
- [../plans/2026-04-19-partner-platform-environment-command-inventory-sheet.md](../plans/2026-04-19-partner-platform-environment-command-inventory-sheet.md)
- [partner-platform-phase8-production-readiness-bundle.md](partner-platform-phase8-production-readiness-bundle.md)
- [partner-platform-phase8-attribution-shadow-pack.md](partner-platform-phase8-attribution-shadow-pack.md)
- [partner-platform-phase8-settlement-shadow-pack.md](partner-platform-phase8-settlement-shadow-pack.md)
- [partner-platform-broad-activation-sign-off-tracker.md](partner-platform-broad-activation-sign-off-tracker.md)

It converts the generic `Phase 8` completion gate into a named closure package.

This pack is complete only when:

1. required backend governance, overlay, and pilot-control validation packs are executed for the frozen `Phase 8` surfaces;
2. the committed OpenAPI export includes the frozen risk, operational-overlay, and pilot-governance surfaces used by `Phase 8`;
3. signed attribution-shadow and settlement-shadow artifacts are green within approved tolerances;
4. the signed production-readiness bundle exists for the exact lanes, surfaces, cutover units, and rollout windows being promoted;
5. no rollout ring beyond approved pilot thresholds is possible without this exit-evidence record;
6. named owners sign off or explicitly record residual non-blocking gaps.

Current execution status for the 2026-04-19 closure baseline:

- targeted risk and governance validation pack passed with `21 passed in 10.07s`;
- risk and outbox regression pack passed with `3 passed in 10.11s`;
- targeted operational-overlay validation pack passed with `21 passed`;
- partner-portal overlay regression passed with `1 passed`;
- attribution shadow contract and regression pack passed with `5 passed`;
- settlement shadow contract and regression pack passed with `6 passed`;
- pilot governance and runbook-hardening validation pack passed with `23 passed`;
- committed OpenAPI export was refreshed successfully for the latest pilot-governance surface;
- production-readiness bundle was assembled, but human sign-off remains pending and is intentionally not auto-completed by this document.

---

## 2. Canonical Phase 8 Evidence Scope

`Phase 8` exit evidence must prove all of the following:

- advanced risk review, evidence attachment, and governance-action workflows are real operator tools rather than placeholders;
- traffic declarations, creative approvals, dispute-case overlays, and policy-acceptance retrieval are canonical operational objects and not portal-only synthetic rows;
- attribution, explainability, renewal ownership, settlement, payout dry-run, and partner export shadow comparisons are deterministic and green within approved tolerances;
- limited pilots stay bounded by explicit owner acknowledgements, rollback-drill proof, and approved go/no-go records;
- broad activation readiness is impossible without both the signed production-readiness bundle and this signed `Phase 8` exit-evidence record;
- any residual gaps are explicit, owned, and classified instead of being silently accepted.

Important clarification:

- `Phase 8` does not itself require immediate `R4` broad activation;
- `Phase 8` does require proof that the platform is ready to move from bounded pilot posture into broad cutover readiness if the signatories approve;
- `Phase 8` does not mint new commercial, settlement, attribution, or entitlement truth;
- `Phase 8` must block promotion when shadow evidence, pilot controls, or operational governance are incomplete.

---

## 3. Required Automated Evidence

## 3.1 Backend Governance, Overlay, And Pilot Gate Tests

The canonical backend gate command is:

```bash
REMNAWAVE_TOKEN=test-remnawave-token \
JWT_SECRET=0123456789abcdef0123456789abcdef \
CRYPTOBOT_TOKEN=test-cryptobot-token \
SKIP_TEST_DB_BOOTSTRAP=1 \
backend/.venv/bin/pytest --no-cov \
  backend/tests/contract/test_risk_governance_workflow_openapi_contract.py \
  backend/tests/contract/test_phase8_operational_overlay_openapi_contract.py \
  backend/tests/contract/test_phase8_pilot_cohort_openapi_contract.py \
  backend/tests/contract/test_phase8_attribution_shadow_pack.py \
  backend/tests/contract/test_phase8_settlement_shadow_pack.py \
  backend/tests/integration/test_risk_governance_workflows.py \
  backend/tests/integration/test_phase8_operational_overlays.py \
  backend/tests/integration/test_phase8_pilot_cohorts.py \
  backend/tests/integration/test_partner_portal_reporting_reads.py \
  backend/tests/integration/test_reporting_outbox.py \
  -q
```

Expected result:

- all tests pass;
- failures block `Phase 8` closure;
- the pack must cover risk workflows, operational overlays, shadow pack contracts, pilot readiness, and partner-facing operational reads through canonical contracts.

## 3.2 Lint And Contract Hygiene

The canonical backend lint command is:

```bash
backend/.venv/bin/ruff check \
  backend/src/application/services/phase8_attribution_shadow.py \
  backend/src/application/services/phase8_settlement_shadow.py \
  backend/src/application/use_cases/pilots/pilot_cohorts.py \
  backend/src/presentation/api/v1/security/routes.py \
  backend/src/presentation/api/v1/security/schemas.py \
  backend/src/presentation/api/v1/pilot_cohorts/routes.py \
  backend/src/presentation/api/v1/pilot_cohorts/schemas.py \
  backend/src/presentation/api/v1/partners/routes.py \
  backend/tests/contract/test_risk_governance_workflow_openapi_contract.py \
  backend/tests/contract/test_phase8_operational_overlay_openapi_contract.py \
  backend/tests/contract/test_phase8_pilot_cohort_openapi_contract.py \
  backend/tests/contract/test_phase8_attribution_shadow_pack.py \
  backend/tests/contract/test_phase8_settlement_shadow_pack.py \
  backend/tests/integration/test_risk_governance_workflows.py \
  backend/tests/integration/test_phase8_operational_overlays.py \
  backend/tests/integration/test_phase8_pilot_cohorts.py
```

The canonical OpenAPI export command is:

```bash
REMNAWAVE_TOKEN=test-remnawave-token \
JWT_SECRET=0123456789abcdef0123456789abcdef \
CRYPTOBOT_TOKEN=test-cryptobot-token \
backend/.venv/bin/python backend/scripts/export_openapi.py
```

The exported file `backend/docs/api/openapi.json` remains the frozen contract source for downstream operational consumers.

## 3.3 Shadow And Pilot Evidence Commands

The canonical deterministic shadow evidence command is:

```bash
REMNAWAVE_TOKEN=test-remnawave-token \
JWT_SECRET=0123456789abcdef0123456789abcdef \
CRYPTOBOT_TOKEN=test-cryptobot-token \
SKIP_TEST_DB_BOOTSTRAP=1 \
backend/.venv/bin/pytest --no-cov \
  backend/tests/contract/test_phase8_attribution_shadow_pack.py \
  backend/tests/contract/test_phase8_settlement_shadow_pack.py \
  backend/tests/contract/test_phase8_pilot_cohort_openapi_contract.py \
  backend/tests/integration/test_phase8_pilot_cohorts.py \
  -q
```

The attached evidence must prove:

- attribution shadow comparisons remain deterministic against the canonical `Phase 3` replay bridge;
- settlement and reporting shadow comparisons remain deterministic against the canonical `Phase 4` and `Phase 7` references;
- pilot readiness is machine-readable and blocked by missing acknowledgements, failed rollback drills, or non-approved go/no-go decisions;
- no approved pilot threshold is widened from informal screenshots, spreadsheets, or portal counters.

---

## 4. Required Artifact Set

The following artifacts must be attached to the evidence archive:

| Artifact | Source | Mandatory |
|---|---|---|
| backend gate test output | pytest command transcript | yes |
| backend lint output | ruff transcript | yes |
| committed OpenAPI export diff | `backend/docs/api/openapi.json` | yes |
| signed production-readiness bundle | [partner-platform-phase8-production-readiness-bundle.md](partner-platform-phase8-production-readiness-bundle.md) | yes |
| signed attribution shadow pack | [partner-platform-phase8-attribution-shadow-pack.md](partner-platform-phase8-attribution-shadow-pack.md) | yes |
| signed settlement shadow pack | [partner-platform-phase8-settlement-shadow-pack.md](partner-platform-phase8-settlement-shadow-pack.md) | yes |
| resolved environment command inventory sheet | [../plans/2026-04-19-partner-platform-environment-command-inventory-sheet.md](../plans/2026-04-19-partner-platform-environment-command-inventory-sheet.md) | yes |
| named production window registration record | [../evidence/partner-platform/2026-04-19/phase8-production-readiness/BA-2026-04-19-01-production-window-registration.md](../evidence/partner-platform/2026-04-19/phase8-production-readiness/BA-2026-04-19-01-production-window-registration.md) | yes |
| pilot cohort readiness output | canonical `GET /api/v1/pilot-cohorts/{id}/readiness` snapshot | yes |
| owner acknowledgement records | canonical `pilot_owner_acknowledgements` API output | yes |
| rollback drill records | canonical `pilot_rollback_drills` API output | yes |
| go/no-go decision records | canonical `pilot_go_no_go_decisions` API output | yes |
| operational overlay proof | traffic declarations, creative approvals, dispute cases, and partner-workspace reads | yes |
| divergence register | issue list for non-blocking residuals | yes |
| sign-off block | named approvers | yes |
| broad-activation sign-off tracker | [partner-platform-broad-activation-sign-off-tracker.md](partner-platform-broad-activation-sign-off-tracker.md) | yes |

Recommended archive location:

```text
docs/evidence/partner-platform/<YYYY-MM-DD>/phase8-gate/
```

---

## 5. Acceptance Mapping

The `Phase 8` completion gate is considered satisfied only when the evidence maps to the frozen requirements below.

| Requirement | Evidence source |
|---|---|
| advanced risk and governance workflows are first-class and operator-usable | `backend/tests/contract/test_risk_governance_workflow_openapi_contract.py`, `backend/tests/integration/test_risk_governance_workflows.py` |
| compliance and dispute overlays are operationally real, not portal-only placeholders | `backend/tests/contract/test_phase8_operational_overlay_openapi_contract.py`, `backend/tests/integration/test_phase8_operational_overlays.py`, `backend/tests/integration/test_partner_portal_reporting_reads.py` |
| shadow attribution and settlement packs are green within approved tolerances | signed `partner-platform-phase8-attribution-shadow-pack.md`, signed `partner-platform-phase8-settlement-shadow-pack.md`, corresponding contract outputs |
| limited pilots have signed lane-by-lane evidence and no-go governance | `backend/tests/contract/test_phase8_pilot_cohort_openapi_contract.py`, `backend/tests/integration/test_phase8_pilot_cohorts.py`, readiness and go/no-go records |
| production-readiness package and `Phase 8` exit evidence are both required before broad activation | signed `partner-platform-phase8-production-readiness-bundle.md`, this document, sections 6 and 7 below |
| exported OpenAPI contains the frozen `Phase 8` governance, overlay, and pilot surfaces | committed `backend/docs/api/openapi.json` and export transcript |

## 5.1 Closure Run Record

The closure baseline attached to this document produced the following results:

| Evidence item | Result |
|---|---|
| targeted risk and governance validation pack | `21 passed in 10.07s` |
| risk and outbox regression pack | `3 passed in 10.11s` |
| targeted operational-overlay validation pack | `21 passed` |
| partner-portal overlay regression | `1 passed` |
| attribution shadow contract and regression pack | `5 passed` |
| settlement shadow contract and regression pack | `6 passed` |
| pilot governance and runbook-hardening validation pack | `23 passed` |
| OpenAPI export | refreshed successfully, frozen schema confirmed |

---

## 6. Divergence Policy

Allowed non-blocking residuals:

- the previously recorded repo-wide security advisories unrelated to the touched `Phase 8` paths, later retired by `RB-010`;
- the previously recorded `frontend` Vitest worker issue around `cssstyle -> @asamuzakjp/css-color`, which was later retired by `RB-009`, provided any remaining frontend failures remain outside the backend-led `Phase 8` gate scope;
- human sign-off still pending after automated closure evidence is complete.

Recorded non-blocking residuals for this closure baseline:

- the repo-wide `npm audit --omit=dev` advisory set previously recorded here was later retired by `RB-010`, with root plus `admin/frontend/partner` audit runs returning zero vulnerabilities;
- the pre-existing official-web Vitest worker issue from earlier phases was later retired by `RB-009` and is not treated as an active `Phase 8` residual anymore;
- sign-off remains human-controlled and must be completed separately from automated validation.

Blocking residuals:

- missing or unsigned attribution-shadow, settlement-shadow, or production-readiness artifacts;
- missing pilot owner acknowledgements, failed rollback drill, or non-approved go/no-go decision for the promoted cohort;
- stale or missing OpenAPI export for risk, overlay, or pilot-governance surfaces;
- any attempt to promote a rollout ring beyond approved pilot thresholds without this signed exit-evidence record;
- any proof that partner-facing operational overlays still depend on synthetic portal placeholders rather than canonical backend objects.

---

## 7. Sign-Off Block

The authoritative human-approval record for this gate is [partner-platform-broad-activation-sign-off-tracker.md](partner-platform-broad-activation-sign-off-tracker.md).

This section defines the required approval shape for `Phase 8`. The tracker carries the exact named approvers, exact promotion scope, accepted residuals, and final timestamps for the activation request under review.

Recommended sign-off block:

```md
## Sign-Off

| Function | Name | Decision | Timestamp | Notes |
|---|---|---|---|---|
| Platform engineering | <name> | <approve|hold|reject> | <timestamp> | <notes> |
| QA | <name> | <approve|hold|reject> | <timestamp> | <notes> |
| Support | <name> | <approve|hold|reject|n/a> | <timestamp> | <notes> |
| Finance ops | <name> | <approve|hold|reject|n/a> | <timestamp> | <notes> |
| Risk ops | <name> | <approve|hold|reject> | <timestamp> | <notes> |
| Partner ops | <name> | <approve|hold|reject|n/a> | <timestamp> | <notes> |
| Product | <name> | <approve|hold|reject> | <timestamp> | <notes> |
```

This `Phase 8` gate is not complete unless every required row is `approve`.

---

## 8. Ring-Promotion Rule

This exit-evidence pack is the canonical promotion record from bounded pilot posture into broad cutover readiness.

Therefore:

- no `R3 -> R4` broad activation may proceed without this signed record;
- no operational readiness package may treat `Phase 8` as complete without this signed record;
- no post-launch stabilization window may be entered as a planned broad activation path unless this record and the signed production-readiness bundle both exist for the exact promoted scope.

---

## 9. Exit Criteria

`Phase 8` is complete when:

- advanced risk, governance, overlay, and pilot-control foundations are proven by automated evidence;
- shadow and pilot artifacts are signed and referenced explicitly;
- residual gaps are named, owned, and classified;
- broad cutover readiness is blocked unless both the readiness bundle and this exit-evidence pack are signed;
- the package is strong enough to stop promotion when evidence, governance, or operational ownership is incomplete.
