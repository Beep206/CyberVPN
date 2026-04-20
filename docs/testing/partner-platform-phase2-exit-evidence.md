# CyberVPN Partner Platform Phase 2 Exit Evidence

**Date:** 2026-04-18  
**Status:** Phase 2 gate evidence pack  
**Purpose:** define the canonical automated evidence, reconciliation evidence, and sign-off checklist required to declare `Phase 2` complete.

---

## 1. Gate Role

This document is the concrete exit-evidence companion to:

- [../plans/2026-04-17-partner-platform-detailed-phased-implementation-plan.md](../plans/2026-04-17-partner-platform-detailed-phased-implementation-plan.md)
- [../plans/2026-04-18-partner-platform-phase-2-execution-ticket-decomposition.md](../plans/2026-04-18-partner-platform-phase-2-execution-ticket-decomposition.md)
- [../plans/2026-04-17-partner-platform-operational-readiness-package.md](../plans/2026-04-17-partner-platform-operational-readiness-package.md)
- [partner-platform-phase2-reconciliation-pack.md](partner-platform-phase2-reconciliation-pack.md)

It converts the generic `Phase 2` readiness requirements into a named closure package.

This pack is complete only when:

1. required backend tests pass;
2. the committed OpenAPI export includes the `Phase 2` surface;
3. the replay/reconciliation harness produces deterministic output and explicit mismatch explanations;
4. named owners sign off or explicitly record residual non-blocking gaps.

Current execution status for the 2026-04-18 closure run:

- backend `Phase 2` verification pack passed with `36 passed in 36.51s`;
- targeted backend lint passed with `All checks passed!`;
- deterministic reconciliation CLI contract pack passed with `3 passed in 0.22s`;
- committed OpenAPI export refreshed successfully.

---

## 2. Canonical Phase 2 Evidence Scope

`Phase 2` exit evidence must prove all of the following:

- merchant-of-record, invoice, and billing descriptor context are explicit and snapshot-ready;
- `quote -> checkout -> order` lineage is real server behavior;
- one order can support multiple payment attempts without losing identity;
- refunds and disputes are order-linked first-class objects;
- order explainability exposes merchant, pricing, policy, refund, and dispute context for finance and support review;
- legacy payment-centric snapshots can be replayed into deterministic `Phase 2` order vocabulary with explainable mismatch reports.

Important clarification:

- `Phase 2` does not require partner payout execution;
- `Phase 2` does not require Phase 3 attribution ownership logic;
- `Phase 2` does require canonical `payment_dispute` normalization and replay evidence.

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
  backend/tests/unit/test_merchant_billing_foundations.py \
  backend/tests/unit/test_order_snapshot_reproducibility.py \
  backend/tests/contract/test_merchant_billing_openapi_contract.py \
  backend/tests/contract/test_order_openapi_contract.py \
  backend/tests/contract/test_payment_attempt_openapi_contract.py \
  backend/tests/contract/test_refunds_payment_disputes_openapi_contract.py \
  backend/tests/contract/test_order_explainability_openapi_contract.py \
  backend/tests/contract/test_phase2_api_surface_contract.py \
  backend/tests/contract/test_phase2_reconciliation_pack.py \
  backend/tests/contract/test_partner_platform_api_conventions.py \
  backend/tests/integration/test_merchant_billing_resolution.py \
  backend/tests/integration/test_quote_checkout_sessions.py \
  backend/tests/integration/test_order_commit.py \
  backend/tests/integration/test_order_payment_attempt_retries.py \
  backend/tests/integration/test_refund_and_dispute_lifecycle.py \
  backend/tests/integration/test_commissionability_scaffolding.py \
  backend/tests/e2e/test_phase2_commerce_foundations.py \
  -q
```

Expected result:

- all tests pass;
- no skipped tests are accepted without a written explanation;
- failures block `Phase 2` closure.

## 3.2 Lint And Contract Hygiene

The canonical backend lint command is:

```bash
backend/.venv/bin/ruff check \
  backend/src/application/services/phase2_reconciliation.py \
  backend/tests/contract/test_phase2_api_surface_contract.py \
  backend/tests/contract/test_phase2_reconciliation_pack.py \
  backend/tests/e2e/test_phase2_commerce_foundations.py
```

The canonical OpenAPI export command is:

```bash
REMNAWAVE_TOKEN=test-remnawave-token \
JWT_SECRET=0123456789abcdef0123456789abcdef \
CRYPTOBOT_TOKEN=test-cryptobot-token \
backend/.venv/bin/python backend/scripts/export_openapi.py
```

The exported file `backend/docs/api/openapi.json` remains the frozen contract source for downstream consumers.

## 3.3 Reconciliation And Replay Evidence

The canonical reconciliation contract command is:

```bash
REMNAWAVE_TOKEN=test-remnawave-token \
JWT_SECRET=0123456789abcdef0123456789abcdef \
CRYPTOBOT_TOKEN=test-cryptobot-token \
SKIP_TEST_DB_BOOTSTRAP=1 \
backend/.venv/bin/pytest --no-cov \
  backend/tests/contract/test_phase2_reconciliation_pack.py \
  -q
```

The harness must prove:

- identical input snapshots with fixed `replay_generated_at` produce identical packs;
- the generated pack contains explicit mismatch rows and `blocking_mismatches`;
- the compact summary script can be attached to evidence archives.

---

## 4. Required Artifact Set

The following artifacts must be attached to the evidence archive:

| Artifact | Source | Mandatory |
|---|---|---|
| backend gate test output | pytest command transcript | yes |
| backend lint output | ruff transcript | yes |
| committed OpenAPI export diff | `backend/docs/api/openapi.json` | yes |
| reconciliation CLI transcript | builder and summary script output | yes |
| reconciliation pack JSON | generated evidence file | yes |
| divergence register | issue list for non-blocking residuals | yes |
| sign-off block | named approvers | yes |

Recommended archive location:

```text
docs/evidence/partner-platform/<YYYY-MM-DD>/phase2-gate/
```

---

## 5. Acceptance Mapping

The `Phase 2` completion gate is considered satisfied only when the evidence maps to the frozen requirements below.

| Requirement | Evidence source |
|---|---|
| merchant, invoice, and billing descriptor context are explicit | `test_merchant_billing_foundations.py`, `test_merchant_billing_resolution.py`, `test_phase2_api_surface_contract.py` |
| `quote -> checkout -> order` lineage is stable | `test_quote_checkout_sessions.py`, `test_order_commit.py`, `test_phase2_commerce_foundations.py` |
| one order supports payment retries without identity loss | `test_order_payment_attempt_retries.py` |
| refunds and disputes are order-linked first-class objects | `test_refund_and_dispute_lifecycle.py`, `test_phase2_commerce_foundations.py` |
| order explainability exposes finance/support review context | `test_commissionability_scaffolding.py`, `test_phase2_commerce_foundations.py` |
| replay/reconciliation is deterministic and explainable | `test_phase2_reconciliation_pack.py`, attached reconciliation pack JSON |
| exported OpenAPI contains the frozen Phase 2 surface | `test_phase2_api_surface_contract.py`, committed `openapi.json` |

## 5.1 Closure Run Record

The closure run attached to this document produced the following results:

| Evidence item | Result |
|---|---|
| backend `Phase 2` verification pack | `36 passed in 36.51s` |
| backend targeted lint | `All checks passed!` |
| reconciliation contract pack | `3 passed in 0.22s` |
| OpenAPI export | refreshed successfully |

---

## 6. Divergence Policy

Allowed non-blocking residuals:

- unrelated frontend or admin adoption work that still consumes frozen `Phase 2` contracts later;
- repo-wide security advisories unrelated to the touched Phase 2 backend paths.

Recorded non-blocking residuals for this closure run:

- at the time of the original closure run, repo-wide `npm audit --omit=dev` still reported pre-existing production advisories in `hono`, `@hono/node-server`, `path-to-regexp`, `follow-redirects`, and `brace-expansion`; that historical residual was later retired by `RB-010` on 2026-04-19;
- sign-off remains human-controlled and must be completed separately from automated validation.

Blocking residuals:

- stale or missing OpenAPI export for the `Phase 2` surface;
- missing deterministic replay evidence for order-domain reconciliation;
- missing order history or explainability evidence with merchant and descriptor snapshots;
- refunds or disputes attached only to legacy payments instead of canonical orders.

---

## 7. Sign-Off Block

| Function | Owner | Decision | Timestamp | Notes |
|---|---|---|---|---|
| platform architecture |  |  |  |  |
| backend commerce |  |  |  |  |
| billing / finance platform |  |  |  |  |
| QA |  |  |  |  |
| finance ops |  |  |  |  |
| risk |  |  |  |  |
| support enablement |  |  |  |  |

`Phase 2` is not closed until this table is complete or an explicit waiver is attached by program governance.
