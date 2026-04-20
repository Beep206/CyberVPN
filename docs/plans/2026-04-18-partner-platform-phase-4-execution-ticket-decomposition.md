# CyberVPN Partner Platform Phase 4 Execution Ticket Decomposition

**Date:** 2026-04-18  
**Status:** Execution ticket decomposition for `Phase 4` implementation start  
**Purpose:** translate `Phase 4` from the detailed phased implementation plan into executable backlog tickets with clear ownership, repository touchpoints, dependencies, acceptance criteria, and evidence requirements.

---

## 1. Document Role

This document is the `Phase 4` execution bridge between:

- the canonical specification package;
- the domain dependency matrix;
- the detailed phased implementation plan;
- the operational readiness package;
- the completed `Phase 3` gate evidence pack.

It exists so finance platform, backend commerce, risk, QA, and partner-operations teams do not invent incompatible settlement boundaries on top of the now-canonical order and attribution domains.

This document does not reopen:

- order-domain rules frozen in `Phase 2`;
- attribution, growth-reward, stacking, and renewal rules frozen in `Phase 3`;
- service identity and entitlement semantics reserved for `Phase 5`;
- partner portal finance UX reserved for later surface phases.

If a proposed `Phase 4` ticket changes any of those, the canonical documents must be updated first.

---

## 2. Execution Rules

Execution for `Phase 4` follows these rules:

1. `Phase 4` starts only after `Phase 3` gate evidence is green.
2. `earning_events`, `earning_holds`, `reserves`, `partner_statements`, `settlement_periods`, `partner_payout_accounts`, `payout_instructions`, and `payout_executions` remain separate entity families.
3. `wallet` remains operationally separate from partner settlement accounting even while compatibility dual-write exists.
4. One financial earning accrual must resolve back to one commercial order lineage and one payout owner lineage.
5. Holds, reserves, and adjustments may constrain payout availability, but they do not mutate immutable order or attribution history.
6. Statement generation must aggregate canonical accrual and adjustment objects, not recompute finance from raw clicks or mutable dashboard totals.
7. Payout destinations are first-class entities; payout execution objects must not become the identity of the payout destination.
8. `Phase 4` may dual-write with legacy partner earning surfaces, but the new settlement layer is the canonical target.
9. Every `Phase 4` ticket must produce at least one of:
   - merged code;
   - frozen API contract updates;
   - executable tests;
   - reconciliation or dry-run evidence.

---

## 3. Ticket Naming And Board Model

Ticket identifiers use the format:

- `T4.x` for `Phase 4`

Recommended workboards:

| Board | Scope | Primary owners |
|---|---|---|
| `B11` | accruals, holds, reserves, hold-release policies | finance platform, backend commerce |
| `B12` | statements, settlement periods, adjustments | finance platform, finance ops |
| `B13` | payout accounts, payout instructions, payout executions | finance platform, risk, admin/platform |
| `B14` | reconciliation, dry-run evidence, gate closure | QA, finance ops, data/BI |

Suggested backlog labels:

- `phase-4`
- `settlement`
- `earnings`
- `holds`
- `reserves`
- `statements`
- `payout-accounts`
- `payouts`
- `adjustments`
- `reconciliation`
- `blocking`

---

## 4. Sequencing Summary

| Ticket | Packet alignment | Primary board | Size | Hard blockers |
|---|---|---|---|---|
| `T4.1` | `P4.1` | `B11` | `L` | `Phase 3 gate` |
| `T4.2` | `P4.2` | `B12` | `L` | `T4.1`, `T2.5` |
| `T4.3` | `P4.3` | `B13` | `M` | `T4.1`, `T1.3`, `T1.6`, `T1.7` |
| `T4.4` | `P4.4` | `B13` | `L` | `T4.2`, `T4.3` |
| `T4.5` | `P4.5` | `B12` | `L` | `T2.5`, `T4.1`, `T4.2` |
| `T4.6` | `P4.6` | `B14` | `M` | `T4.2`, `T4.4`, `T4.5` |
| `T4.7` | dry-run payout and settlement replay evidence | `B14` | `M` | `T4.2`, `T4.4`, `T4.5`, `T4.6` |
| `T4.8` | phase-exit evidence | `B14` | `M` | `T4.1`, `T4.2`, `T4.3`, `T4.4`, `T4.5`, `T4.6`, `T4.7` |

`T4.1` is the only valid starting point for `Phase 4` implementation.

---

## 5. Ticket Decomposition

## 5.1 `T4.1` Earning Events, Holds, Reserves, And Hold-Release Policy Foundation

**Packet alignment:** `P4.1`  
**Primary owners:** finance platform, backend commerce  
**Supporting owners:** finance ops, risk, QA

**Repository touchpoints:**

- Modify: `docs/plans/2026-04-17-commerce-attribution-and-settlement-data-model-spec.md`
- Modify: `docs/plans/2026-04-17-partner-platform-api-specification-package.md`
- Create: `backend/src/domain/entities/earning_event.py`
- Create: `backend/src/domain/entities/earning_hold.py`
- Create: `backend/src/domain/entities/reserve.py`
- Create: `backend/src/infrastructure/database/models/earning_event_model.py`
- Create: `backend/src/infrastructure/database/models/earning_hold_model.py`
- Create: `backend/src/infrastructure/database/models/reserve_model.py`
- Create: `backend/src/infrastructure/database/repositories/settlement_repo.py`
- Create: `backend/src/application/use_cases/settlement/`
- Modify: `backend/src/application/use_cases/payments/post_payment.py`
- Create: `backend/src/presentation/api/v1/earning_events/`
- Create: `backend/src/presentation/api/v1/earning_holds/`
- Create: `backend/src/presentation/api/v1/reserves/`
- Create: `backend/tests/integration/test_partner_settlement_foundations.py`
- Create: `backend/tests/contract/test_settlement_foundation_openapi_contract.py`

**Scope:**

- first-class earning accrual events linked to canonical orders;
- first-class earning holds and hold-release policy baseline;
- first-class reserves and manual reserve lifecycle baseline;
- compatibility dual-write from current post-payment partner earning path into canonical settlement primitives;
- minimal finance/support visibility APIs for accrual, holds, and reserves.

**Acceptance criteria:**

- one payable partner order can emit one canonical earning event without mutating order or attribution history;
- initial payout hold is created through explicit policy, not implicit wallet timing;
- reserves are separate from holds and visible as first-class finance controls;
- compatibility dual-write preserves existing partner earning flow while canonical settlement rows are created.

## 5.2 `T4.2` Settlement Periods, Partner Statements, And Statement Lifecycle

**Packet alignment:** `P4.2`  
**Primary owners:** finance platform  
**Supporting owners:** finance ops, QA

**Repository touchpoints:**

- Create: `backend/src/domain/entities/settlement_period.py`
- Create: `backend/src/domain/entities/partner_statement.py`
- Create: `backend/src/domain/entities/statement_adjustment.py`
- Create: `backend/src/infrastructure/database/models/settlement_period_model.py`
- Create: `backend/src/infrastructure/database/models/partner_statement_model.py`
- Create: `backend/src/infrastructure/database/models/statement_adjustment_model.py`
- Create: `backend/src/presentation/api/v1/partner_statements/`
- Create: `backend/src/presentation/api/v1/settlement_periods/`
- Create: `backend/tests/integration/test_partner_statement_lifecycle.py`

**Scope:**

- settlement periods by explicit time window;
- statement generation from earning events, holds, reserves, and adjustments;
- close and reopen lifecycle;
- immutable statement snapshots with typed adjustment chains.

**Acceptance criteria:**

- statements can close and reopen without rewriting source earning history;
- statement totals reconcile to accrual, hold, reserve, and adjustment inputs;
- statement lifecycle is separate from payout execution lifecycle.

## 5.3 `T4.3` Partner Payout Accounts And Payout Eligibility

**Packet alignment:** `P4.3`  
**Primary owners:** finance platform, risk  
**Supporting owners:** admin/platform, finance ops

**Repository touchpoints:**

- Create: `backend/src/domain/entities/partner_payout_account.py`
- Create: `backend/src/infrastructure/database/models/partner_payout_account_model.py`
- Create: `backend/src/presentation/api/v1/partner_payout_accounts/`
- Create: `backend/tests/integration/test_partner_payout_accounts.py`

**Scope:**

- first-class payout destination identity;
- verification, suspension, archive, and default-selection lifecycle;
- eligibility checks against risk state, workspace state, and finance controls.

**Acceptance criteria:**

- payout destinations are managed independently from payout instructions or executions;
- risk or compliance can freeze payout destination availability without deleting history;
- default payout destination selection is auditable.

## 5.4 `T4.4` Payout Instructions, Maker-Checker, And Payout Executions

**Packet alignment:** `P4.4`  
**Primary owners:** finance platform  
**Supporting owners:** finance ops, risk, QA

**Repository touchpoints:**

- Create: `backend/src/domain/entities/payout_instruction.py`
- Create: `backend/src/domain/entities/payout_execution.py`
- Create: `backend/src/infrastructure/database/models/payout_instruction_model.py`
- Create: `backend/src/infrastructure/database/models/payout_execution_model.py`
- Create: `backend/src/presentation/api/v1/payouts/`
- Create: `backend/tests/integration/test_payout_execution_workflow.py`

**Scope:**

- payout instruction creation from closed statements;
- maker-checker approval flow;
- execution status tracking and audit trail;
- dry-run execution mode before live payout rollout.

**Acceptance criteria:**

- payout instructions always reference canonical statements and payout accounts;
- sensitive payout actions require explicit approval transitions;
- payout execution history is immutable and explainable.

## 5.5 `T4.5` Refund, Dispute, Clawback, And Reserve Adjustment Policies

**Packet alignment:** `P4.5`  
**Primary owners:** finance platform, risk  
**Supporting owners:** finance ops, backend commerce

**Repository touchpoints:**

- Extend: `backend/src/application/use_cases/refunds/`
- Extend: `backend/src/application/use_cases/payment_disputes/`
- Create: `backend/src/application/use_cases/settlement/adjustments/`
- Create: `backend/tests/integration/test_settlement_adjustments.py`

**Scope:**

- typed earning adjustments on refund, dispute, chargeback, and reversal events;
- reserve extension and payout freeze hooks;
- clawback visibility without history deletion.

**Acceptance criteria:**

- refund and dispute events create explicit settlement-side consequences;
- adjustments are typed and linked back to source orders and source finance objects;
- reserve and hold changes remain auditable.

## 5.6 `T4.6` Reconciliation Views And Liability Reporting

**Packet alignment:** `P4.6`  
**Primary owners:** finance platform, data/BI  
**Supporting owners:** finance ops, QA

**Repository touchpoints:**

- Create: `backend/src/application/services/phase4_reconciliation.py`
- Create: `backend/scripts/build_phase4_settlement_reconciliation_pack.py`
- Create: `backend/scripts/print_phase4_settlement_reconciliation_summary.py`
- Create: `backend/tests/contract/test_phase4_reconciliation_pack.py`
- Create: validation docs under `docs/testing/`

**Scope:**

- liability views for on-hold, reserved, available, paid, and adjusted earnings;
- deterministic reconciliation packs for statements and payouts;
- finance-approved mismatch vocabulary.

**Acceptance criteria:**

- liability can be reconstructed from canonical settlement objects;
- reconciliation output is deterministic;
- blocking mismatches are explicit and machine-readable.

## 5.7 `T4.7` Dry-Run Settlement Evidence And Internal Payout Simulation

**Packet alignment:** dry-run evidence  
**Primary owners:** QA, finance ops  
**Supporting owners:** finance platform, risk

**Repository touchpoints:**

- Extend: `docs/testing/`
- Create: `backend/tests/e2e/test_phase4_settlement_foundations.py`

**Scope:**

- dry-run statement close and payout simulation;
- shadow evidence for holds, reserves, statement totals, and payout liability;
- internal-only operational readiness proof before any partner-facing finance rollout.

**Acceptance criteria:**

- finance can inspect at least one full accrual -> hold -> statement -> dry-run payout path;
- shadow settlement output stays within approved tolerance;
- immutable audit evidence exists for dry-run execution.

## 5.8 `T4.8` Phase 4 Gate And Evidence Pack

**Packet alignment:** phase-exit evidence  
**Primary owners:** QA, finance platform  
**Supporting owners:** finance ops, risk, support enablement

**Repository touchpoints:**

- Create: `docs/testing/partner-platform-phase4-exit-evidence.md`
- Modify: `docs/plans/2026-04-17-partner-platform-operational-readiness-package.md`
- Create: `backend/tests/e2e/test_phase4_finance_foundations.py`

**Scope:**

- freeze evidence for accrual, holds, reserves, statements, payout destinations, execution, and reconciliation;
- attach dry-run payout evidence;
- record unresolved but non-blocking residuals.

**Acceptance criteria:**

- schema and API freeze for settlement, statement, payout-account, payout-execution, and reconciliation families;
- finance signs off that partner settlement is no longer modeled as wallet behavior;
- dry-run payout evidence exists with immutable audit trail.

---

## 6. Phase 4 Completion Gate

`Phase 4` is complete only when:

1. `T4.1` through `T4.7` are merged or explicitly waived by governance;
2. canonical settlement accrual, hold, reserve, statement, and payout objects exist and remain distinct;
3. wallet is no longer treated as the accounting system for partner settlement;
4. dry-run payout evidence and reconciliation evidence are green;
5. the `Phase 4` evidence pack is green.
