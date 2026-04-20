# CyberVPN Partner Platform: Phase 4 Settlement Reconciliation Pack

**Date:** 2026-04-18  
**Status:** canonical validation pack for `Phase 4 / T4.6`  
**Purpose:** define the deterministic reconciliation artifact for settlement liability, statements, payout instructions, and payout executions.

---

## 1. Document Role

This pack exists to prove that `Phase 4` liability can be reconstructed from canonical settlement objects without falling back to wallet balances, partner dashboard totals, or mutable operational guesswork.

The pack is a machine-generated report built from a settlement snapshot containing:

- `earning_events`
- `earning_holds`
- `reserves`
- `partner_statements`
- `statement_adjustments`
- `payout_instructions`
- `payout_executions`

The pack is deterministic. identical input snapshots with fixed `replay_generated_at` produce identical packs.

---

## 2. Output Sections

The report contains these top-level sections:

- `metadata`
- `input_summary`
- `liability_views`
- `statement_views`
- `payout_views`
- `reconciliation`

`liability_views` are partner-account-scoped summaries intended for finance operations and dry-run rollout evidence.

`statement_views` are statement-scoped explainability views showing how stored statement totals compare with the linked `earning_events`, `reserves`, and `statement_adjustments`.

`payout_views` summarize payout instructions and linked executions so finance can verify whether payout state still matches statement state.

---

## 3. Liability View Definitions

Each `liability_views[]` entry must include:

- `partner_account_id`
- `event_status_totals`
- `reserve_totals`
- `adjustment_totals`
- `statement_totals`
- `payout_totals`
- `coverage`
- `liability_totals`

Important fields:

- `event_status_totals.on_hold_amount`
- `event_status_totals.blocked_amount`
- `event_status_totals.available_unstatemented_amount`
- `reserve_totals.total_active_reserve_amount`
- `payout_totals.completed_amount`
- `liability_totals.available_statement_amount`
- `liability_totals.available_unstatemented_amount`
- `liability_totals.completed_payout_amount`
- `liability_totals.outstanding_statement_liability_amount`

`outstanding_statement_liability_amount` is the current statement-backed liability still unpaid after completed payouts are subtracted.

---

## 4. Canonical Mismatch Vocabulary

Blocking mismatches for `Phase 4` include:

- `statement_snapshot_missing_event`
- `statement_snapshot_missing_reserve`
- `statement_snapshot_missing_adjustment`
- `statement_totals_mismatch`
- `statement_count_mismatch`
- `payout_instruction_without_closed_statement`
- `payout_instruction_on_superseded_statement`
- `payout_instruction_amount_mismatch`
- `payout_execution_without_instruction`
- `payout_execution_instruction_mismatch`
- `reconciled_execution_without_completed_instruction`
- `completed_instruction_without_live_terminal_execution`
- `paid_amount_exceeds_statement_liability`

These codes are canonical and machine-readable. They are the finance-approved mismatch vocabulary for `Phase 4`.

---

## 5. Expected Reconciliation Behavior

The reconciliation builder must:

1. validate every statement against its linked snapshot object IDs;
2. recompute `accrual_amount`, `on_hold_amount`, `reserve_amount`, `adjustment_net_amount`, and `available_amount`;
3. validate count columns such as `source_event_count` and `adjustment_count`;
4. validate that payout instructions only reference closed, latest statement versions;
5. validate that payout execution identity fields agree with the linked payout instruction;
6. surface partner-level liability, not only object-level mismatches.

This pack is not a payout engine. It is a deterministic reporting and reconciliation artifact.

---

## 6. CLI Usage

Build the reconciliation pack:

```bash
backend/.venv/bin/python backend/scripts/build_phase4_settlement_reconciliation_pack.py \
  --input /path/to/phase4-settlement-snapshot.json \
  --output backend/docs/evidence/partner-platform/phase4-settlement-reconciliation-pack.json
```

Print a compact summary:

```bash
backend/.venv/bin/python backend/scripts/print_phase4_settlement_reconciliation_summary.py \
  --input backend/docs/evidence/partner-platform/phase4-settlement-reconciliation-pack.json
```

---

## 7. Gate Usage

This pack is required input for:

- `T4.7` dry-run settlement evidence;
- `T4.8` Phase 4 exit evidence;
- finance review of statement and payout liability before partner-facing payout rollout.

If the pack status is `red`, `Phase 4` is not ready for payout simulation sign-off.
