# CyberVPN Partner Platform Phase 4 Exit Evidence

**Date:** 2026-04-18  
**Status:** Phase 4 gate evidence pack  
**Purpose:** define the canonical automated evidence, dry-run payout evidence, reconciliation evidence, and sign-off checklist required to declare `Phase 4` complete.

---

## 1. Gate Role

This document is the concrete exit-evidence companion to:

- [../plans/2026-04-17-partner-platform-detailed-phased-implementation-plan.md](../plans/2026-04-17-partner-platform-detailed-phased-implementation-plan.md)
- [../plans/2026-04-18-partner-platform-phase-4-execution-ticket-decomposition.md](../plans/2026-04-18-partner-platform-phase-4-execution-ticket-decomposition.md)
- [../plans/2026-04-17-partner-platform-operational-readiness-package.md](../plans/2026-04-17-partner-platform-operational-readiness-package.md)
- [partner-platform-phase4-settlement-reconciliation-pack.md](partner-platform-phase4-settlement-reconciliation-pack.md)
- [partner-platform-phase4-dry-run-settlement-evidence.md](partner-platform-phase4-dry-run-settlement-evidence.md)

It converts the generic `Phase 4` readiness requirements into a named closure package.

This pack is complete only when:

1. required backend tests pass;
2. the committed OpenAPI export includes the frozen `Phase 4` surface;
3. the settlement reconciliation harness produces deterministic output and explicit blocking mismatch explanations;
4. internal dry-run payout evidence proves the statement-to-payout chain without collapsing outstanding liability;
5. named owners sign off or explicitly record residual non-blocking gaps.

Current execution status for the 2026-04-18 closure run:

- targeted backend `Phase 4` verification pack passed with `20 passed in 49.55s`;
- targeted backend lint passed with `All checks passed!`;
- committed OpenAPI export was refreshed successfully for the frozen `Phase 4` surface;
- deterministic settlement reconciliation contract pack passed with `2 passed in 0.13s`;
- `Phase 4` dry-run and finance e2e gate pack passed with `2 passed in 13.09s`.

---

## 2. Canonical Phase 4 Evidence Scope

`Phase 4` exit evidence must prove all of the following:

- earning accrual, holds, reserves, statements, payout destinations, payout instructions, payout executions, and typed statement adjustments remain separate canonical entity families;
- wallet is no longer treated as the accounting system for partner settlement;
- statement snapshots reconcile to linked earning events, reserves, and adjustments;
- payout instructions only originate from canonical closed statements and verified payout destinations;
- maker-checker approval is enforced on sensitive payout transitions;
- dry-run payout execution does not mark liability as paid or complete the payout instruction;
- deterministic reconciliation can reconstruct partner liability directly from canonical settlement objects.

Important clarification:

- `Phase 4` does not require live partner payouts;
- `Phase 4` does require dry-run payout evidence with immutable audit trail;
- `Phase 4` does require payout-account eligibility and reserve effects to be explainable through canonical APIs and reconciliation output.

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
  backend/tests/contract/test_settlement_foundation_openapi_contract.py \
  backend/tests/contract/test_partner_statement_openapi_contract.py \
  backend/tests/contract/test_partner_payout_accounts_openapi_contract.py \
  backend/tests/contract/test_payout_workflow_openapi_contract.py \
  backend/tests/contract/test_phase4_api_surface_contract.py \
  backend/tests/contract/test_phase4_reconciliation_pack.py \
  backend/tests/contract/test_partner_platform_api_conventions.py \
  backend/tests/integration/test_partner_settlement_foundations.py \
  backend/tests/integration/test_partner_statement_lifecycle.py \
  backend/tests/integration/test_partner_payout_accounts.py \
  backend/tests/integration/test_payout_execution_workflow.py \
  backend/tests/integration/test_settlement_adjustments.py \
  backend/tests/e2e/test_phase4_settlement_foundations.py \
  backend/tests/e2e/test_phase4_finance_foundations.py \
  -q
```

Expected result:

- all tests pass;
- no skipped tests are accepted without a written explanation;
- failures block `Phase 4` closure.

## 3.2 Lint And Contract Hygiene

The canonical backend lint command is:

```bash
backend/.venv/bin/ruff check \
  backend/src/application/services/phase4_reconciliation.py \
  backend/tests/contract/test_phase4_api_surface_contract.py \
  backend/tests/contract/test_phase4_reconciliation_pack.py \
  backend/tests/e2e/test_phase4_settlement_foundations.py \
  backend/tests/e2e/test_phase4_finance_foundations.py
```

The canonical OpenAPI export command is:

```bash
REMNAWAVE_TOKEN=test-remnawave-token \
JWT_SECRET=0123456789abcdef0123456789abcdef \
CRYPTOBOT_TOKEN=test-cryptobot-token \
backend/.venv/bin/python backend/scripts/export_openapi.py
```

The exported file `backend/docs/api/openapi.json` remains the frozen contract source for downstream consumers.

## 3.3 Dry-Run And Reconciliation Evidence

The canonical reconciliation and dry-run contract command is:

```bash
REMNAWAVE_TOKEN=test-remnawave-token \
JWT_SECRET=0123456789abcdef0123456789abcdef \
CRYPTOBOT_TOKEN=test-cryptobot-token \
SKIP_TEST_DB_BOOTSTRAP=1 \
backend/.venv/bin/pytest --no-cov \
  backend/tests/contract/test_phase4_reconciliation_pack.py \
  backend/tests/e2e/test_phase4_settlement_foundations.py \
  backend/tests/e2e/test_phase4_finance_foundations.py \
  -q
```

The harness must prove:

- identical settlement snapshots with fixed `replay_generated_at` produce identical reconciliation packs;
- the generated pack contains explicit mismatch rows and `blocking_mismatches`;
- dry-run payout evidence leaves `instruction_status = approved` and `completed_payout_amount = 0.0`;
- partner liability remains visible as outstanding statement liability after the dry-run execution;
- the compact summary script can be attached to evidence archives.

---

## 4. Required Artifact Set

The following artifacts must be attached to the evidence archive:

| Artifact | Source | Mandatory |
|---|---|---|
| backend gate test output | pytest command transcript | yes |
| backend lint output | ruff transcript | yes |
| committed OpenAPI export diff | `backend/docs/api/openapi.json` | yes |
| settlement reconciliation CLI transcript | builder and summary script output | yes |
| settlement reconciliation pack JSON | generated evidence file | yes |
| dry-run payout evidence | e2e output and linked API payloads | yes |
| finance surface evidence | e2e output and linked API payloads | yes |
| divergence register | issue list for non-blocking residuals | yes |
| sign-off block | named approvers | yes |

Recommended archive location:

```text
docs/evidence/partner-platform/<YYYY-MM-DD>/phase4-gate/
```

---

## 5. Acceptance Mapping

The `Phase 4` completion gate is considered satisfied only when the evidence maps to the frozen requirements below.

| Requirement | Evidence source |
|---|---|
| earning accrual, holds, and reserves remain first-class settlement objects | `test_partner_settlement_foundations.py`, `test_settlement_foundation_openapi_contract.py`, `test_phase4_finance_foundations.py` |
| statements close, reopen, and reconcile independently from payouts | `test_partner_statement_lifecycle.py`, `test_partner_statement_openapi_contract.py` |
| payout destinations remain first-class and eligibility-aware | `test_partner_payout_accounts.py`, `test_partner_payout_accounts_openapi_contract.py`, `test_phase4_finance_foundations.py` |
| payout instructions and executions remain auditable and maker-checker controlled | `test_payout_execution_workflow.py`, `test_payout_workflow_openapi_contract.py`, `test_phase4_finance_foundations.py` |
| refund and dispute side-effects create typed settlement consequences | `test_settlement_adjustments.py` |
| deterministic reconciliation reconstructs liability from canonical settlement objects | `test_phase4_reconciliation_pack.py`, attached reconciliation pack JSON |
| dry-run payout evidence preserves outstanding liability and immutable audit trail | `test_phase4_settlement_foundations.py`, `test_phase4_finance_foundations.py`, [partner-platform-phase4-dry-run-settlement-evidence.md](./partner-platform-phase4-dry-run-settlement-evidence.md) |
| exported OpenAPI contains the frozen `Phase 4` surface | `test_phase4_api_surface_contract.py`, committed `openapi.json` |

## 5.1 Closure Run Record

The closure run attached to this document produced the following results:

| Evidence item | Result |
|---|---|
| targeted backend `Phase 4` verification pack | `20 passed in 49.55s` |
| backend targeted lint | `All checks passed!` |
| settlement reconciliation contract pack | `2 passed in 0.13s` |
| `Phase 4` dry-run and finance e2e gate pack | `2 passed in 13.09s` |
| OpenAPI export | refreshed successfully, frozen schema confirmed |

---

## 6. Divergence Policy

Allowed non-blocking residuals:

- unrelated partner portal or reporting adoption work that consumes frozen `Phase 4` contracts later;
- repo-wide security advisories unrelated to the touched `Phase 4` backend paths;
- human sign-off still pending after automated closure evidence is complete.

Recorded non-blocking residuals for this closure run:

- at the time of the original closure run, repo-wide `npm audit --omit=dev` still reported pre-existing production advisories in `hono`, `@hono/node-server`, `path-to-regexp`, `follow-redirects`, and `brace-expansion`; that historical residual was later retired by `RB-010` on 2026-04-19;
- sign-off remains human-controlled and must be completed separately from automated validation.

Blocking residuals:

- stale or missing OpenAPI export for settlement, statement, payout-account, or payout-execution surfaces;
- missing deterministic reconciliation evidence for statement and payout liability;
- dry-run payout evidence that completes live liability or collapses the instruction state to `completed`;
- any proof that partner finance still depends on wallet semantics instead of canonical settlement objects.

---

## 7. Sign-Off Block

| Function | Owner | Decision | Timestamp | Notes |
|---|---|---|---|---|
| platform architecture |  |  |  |  |
| finance platform |  |  |  |  |
| finance ops |  |  |  |  |
| QA |  |  |  |  |
| risk |  |  |  |  |
| support enablement |  |  |  |  |

`Phase 4` is not closed until this table is complete or an explicit waiver is attached by program governance.
