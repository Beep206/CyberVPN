# CyberVPN Partner Platform Phase 3 Exit Evidence

**Date:** 2026-04-18  
**Status:** Phase 3 gate evidence pack  
**Purpose:** define the canonical automated evidence, explainability replay evidence, and sign-off checklist required to declare `Phase 3` complete.

---

## 1. Gate Role

This document is the concrete exit-evidence companion to:

- [../plans/2026-04-17-partner-platform-detailed-phased-implementation-plan.md](../plans/2026-04-17-partner-platform-detailed-phased-implementation-plan.md)
- [../plans/2026-04-18-partner-platform-phase-3-execution-ticket-decomposition.md](../plans/2026-04-18-partner-platform-phase-3-execution-ticket-decomposition.md)
- [../plans/2026-04-17-partner-platform-operational-readiness-package.md](../plans/2026-04-17-partner-platform-operational-readiness-package.md)
- [partner-platform-phase3-explainability-and-replay-pack.md](partner-platform-phase3-explainability-and-replay-pack.md)

It converts the generic `Phase 3` readiness requirements into a named closure package.

This pack is complete only when:

1. required backend tests pass;
2. the committed OpenAPI export includes the frozen `Phase 3` surface;
3. the explainability replay harness produces deterministic output and explicit divergence explanations;
4. named owners sign off or explicitly record residual non-blocking gaps.

Current execution status for the 2026-04-18 closure run:

- targeted backend `Phase 3` verification pack passed with `33 passed in 69.30s`;
- targeted backend lint passed with `All checks passed!`;
- committed OpenAPI export was refreshed successfully for the frozen `Phase 3` surface;
- deterministic explainability replay contract pack passed with `3 passed in 0.99s`;
- lane-aware `Phase 3` e2e smoke passed with `1 passed`.

---

## 2. Canonical Phase 3 Evidence Scope

`Phase 3` exit evidence must prove all of the following:

- attribution touchpoints remain append-only evidence, separate from bindings and winners;
- customer commercial bindings remain persistent and precedence-aware;
- order attribution results are deterministic and immutable per order;
- growth reward allocations remain separate from commercial ownership in persistence and API shape;
- renewal lineage and renewal ownership remain explainable and traceable to prior lineage or active bindings;
- support-facing explainability exists for at least one case in every active lane;
- replay output can compare persisted attribution winners against deterministic reference logic.

Important clarification:

- `Phase 3` does not require partner payout execution or statements;
- `Phase 3` does require readable explainability for finance, support, and risk review;
- `Phase 3` does require deterministic replay evidence for attribution and growth outcomes.

---

## 3. Required Automated Evidence

## 3.1 Backend Gate Tests

The canonical backend gate command is:

```bash
REMNAWAVE_TOKEN=test-remnawave-token \
JWT_SECRET=0123456789abcdef0123456789abcdef \
CRYPTOBOT_TOKEN=test-cryptobot-token \
SKIP_TEST_DB_BOOTSTRAP=1 \
backend/.venv/bin/pytest --no-cov \
  backend/tests/contract/test_attribution_touchpoint_openapi_contract.py \
  backend/tests/contract/test_customer_commercial_bindings_openapi_contract.py \
  backend/tests/contract/test_order_attribution_result_openapi_contract.py \
  backend/tests/contract/test_growth_reward_allocations_openapi_contract.py \
  backend/tests/contract/test_policy_evaluation_openapi_contract.py \
  backend/tests/contract/test_renewal_order_openapi_contract.py \
  backend/tests/contract/test_phase3_explainability_contract.py \
  backend/tests/contract/test_order_explainability_openapi_contract.py \
  backend/tests/contract/test_partner_platform_api_conventions.py \
  backend/tests/integration/test_attribution_touchpoints.py \
  backend/tests/integration/test_customer_commercial_bindings.py \
  backend/tests/integration/test_order_attribution_resolution.py \
  backend/tests/integration/test_growth_reward_allocations.py \
  backend/tests/integration/test_stacking_and_qualifying_events.py \
  backend/tests/integration/test_renewal_ownership.py \
  backend/tests/e2e/test_phase3_attribution_foundations.py \
  -q
```

Expected result:

- all tests pass;
- no skipped tests are accepted without a written explanation;
- failures block `Phase 3` closure.

## 3.2 Lint And Contract Hygiene

The canonical backend lint command is:

```bash
backend/.venv/bin/ruff check \
  backend/src/application/use_cases/orders/explainability/get_order_explainability.py \
  backend/src/application/services/phase3_explainability_replay.py \
  backend/scripts/build_phase3_explainability_replay_pack.py \
  backend/scripts/print_phase3_explainability_replay_summary.py \
  backend/tests/contract/test_phase3_explainability_contract.py \
  backend/tests/e2e/test_phase3_attribution_foundations.py
```

The canonical OpenAPI export command is:

```bash
REMNAWAVE_TOKEN=test-remnawave-token \
JWT_SECRET=0123456789abcdef0123456789abcdef \
CRYPTOBOT_TOKEN=test-cryptobot-token \
backend/.venv/bin/python backend/scripts/export_openapi.py
```

The exported file `backend/docs/api/openapi.json` remains the frozen contract source for downstream consumers.

## 3.3 Explainability Replay Evidence

The canonical replay contract command is:

```bash
REMNAWAVE_TOKEN=test-remnawave-token \
JWT_SECRET=0123456789abcdef0123456789abcdef \
CRYPTOBOT_TOKEN=test-cryptobot-token \
SKIP_TEST_DB_BOOTSTRAP=1 \
backend/.venv/bin/pytest --no-cov \
  backend/tests/contract/test_phase3_explainability_contract.py \
  -q
```

The harness must prove:

- identical input snapshots with fixed `replay_generated_at` produce identical packs;
- the generated pack contains explicit mismatch rows and `blocking_mismatches`;
- replay output includes lane views and winner summaries;
- the compact summary script can be attached to evidence archives.

---

## 4. Required Artifact Set

The following artifacts must be attached to the evidence archive:

| Artifact | Source | Mandatory |
|---|---|---|
| backend gate test output | pytest command transcript | yes |
| backend lint output | ruff transcript | yes |
| committed OpenAPI export diff | `backend/docs/api/openapi.json` | yes |
| explainability replay CLI transcript | builder and summary script output | yes |
| explainability replay pack JSON | generated evidence file | yes |
| lane evidence responses | support/admin API payloads or screenshots | yes |
| divergence register | issue list for non-blocking residuals | yes |
| sign-off block | named approvers | yes |

Recommended archive location:

```text
docs/evidence/partner-platform/<YYYY-MM-DD>/phase3-gate/
```

---

## 5. Acceptance Mapping

The `Phase 3` completion gate is considered satisfied only when the evidence maps to the frozen requirements below.

| Requirement | Evidence source |
|---|---|
| touchpoints are append-only evidence and surfaced through API | `test_attribution_touchpoints.py`, `test_attribution_touchpoint_openapi_contract.py` |
| bindings remain separate from touchpoints and stay precedence-aware | `test_customer_commercial_bindings.py`, `test_customer_commercial_bindings_openapi_contract.py` |
| attribution winners are deterministic and immutable | `test_order_attribution_resolution.py`, `test_order_attribution_result_openapi_contract.py`, replay pack JSON |
| growth rewards stay separate from commercial ownership | `test_growth_reward_allocations.py`, `test_growth_reward_allocations_openapi_contract.py` |
| qualifying events and stacking remain executable and policy-aware | `test_stacking_and_qualifying_events.py`, `test_policy_evaluation_openapi_contract.py` |
| renewals remain explainable and payout-owner lineage is preserved | `test_renewal_ownership.py`, `test_renewal_order_openapi_contract.py` |
| support-facing explainability exists for every active lane | `test_phase3_attribution_foundations.py`, `test_phase3_explainability_contract.py` |
| exported OpenAPI contains the frozen `Phase 3` surface | committed `openapi.json`, `test_phase3_explainability_contract.py` |

## 5.1 Closure Run Record

The closure run attached to this document produced the following results:

| Evidence item | Result |
|---|---|
| targeted backend `Phase 3` verification pack | `33 passed in 69.30s` |
| backend targeted lint | `All checks passed!` |
| explainability replay contract pack | `3 passed in 0.99s` |
| `Phase 3` e2e lane smoke | `1 passed` |
| OpenAPI export | refreshed successfully, frozen schema confirmed |

---

## 6. Divergence Policy

Allowed non-blocking residuals:

- unrelated frontend, portal, or reporting adoption work that consumes frozen `Phase 3` contracts later;
- repo-wide security advisories unrelated to the touched `Phase 3` backend paths;
- human sign-off still pending after automated closure evidence is complete.

Recorded non-blocking residuals for this closure run:

- at the time of the original closure run, repo-wide `npm audit --omit=dev` still reported pre-existing production advisories in `hono`, `@hono/node-server`, `path-to-regexp`, `follow-redirects`, and `brace-expansion`; that historical residual was later retired by `RB-010` on 2026-04-19;
- sign-off remains human-controlled and must be completed separately from automated validation.

Blocking residuals:

- stale or missing OpenAPI export for attribution, growth rewards, renewal, or explainability surfaces;
- missing deterministic replay evidence for attribution winner comparison;
- missing support-facing lane evidence for any active lane;
- growth reward allocations mutating or replacing commercial owner objects instead of remaining separate evidence.

---

## 7. Sign-Off Block

| Function | Owner | Decision | Timestamp | Notes |
|---|---|---|---|---|
| platform architecture |  |  |  |  |
| backend attribution |  |  |  |  |
| growth platform |  |  |  |  |
| QA |  |  |  |  |
| finance ops |  |  |  |  |
| risk |  |  |  |  |
| support enablement |  |  |  |  |

`Phase 3` is not closed until this table is complete or an explicit waiver is attached by program governance.
