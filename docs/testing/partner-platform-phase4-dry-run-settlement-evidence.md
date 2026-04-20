# CyberVPN Partner Platform: Phase 4 Dry-Run Settlement Evidence

**Date:** 2026-04-18  
**Status:** canonical dry-run evidence spec for `T4.7`  
**Purpose:** define the minimum internal settlement rehearsal that must pass before any partner-facing finance rollout can promote beyond internal validation.

---

## 1. Evidence Goal

`T4.7` proves that the settlement layer is operationally usable before broad partner payout activation.

The dry-run path must demonstrate one complete internal finance chain:

1. canonical `earning_event` accrual;
2. initial `earning_hold`;
3. open `partner_statement` generation while the event is still on hold;
4. hold release;
5. active `reserve` impact on statement totals;
6. reserve release before payout simulation if eligibility policy requires it;
7. statement close;
8. verified `partner_payout_account`;
9. maker-checker `payout_instruction` approval;
10. `dry_run` payout execution, completion, and reconciliation;
11. settlement reconciliation pack built from the resulting canonical objects.

This is an internal-only proof artifact. It is not a partner-facing payout launch signal by itself.

---

## 2. Required Assertions

The dry-run evidence must prove all of the following:

- the initial statement shows `on_hold_amount > 0` and `available_amount = 0`;
- after hold release and reserve application, the same open statement recomputes with `held_event_count = 0` and `reserve_amount > 0`;
- if reserve policy blocks payout eligibility, the reserve may be released before the dry-run payout step as long as the reserve effect was already captured in statement evidence;
- the closed statement still has positive `available_amount`;
- dry-run payout reconciliation does not mark the payout instruction `completed`;
- the canonical settlement reconciliation pack remains `green` after the dry-run execution;
- partner liability is still visible as outstanding statement liability after the dry-run, because no live payout was executed.

---

## 3. Canonical Artifacts

The minimum evidence set for `T4.7` is:

- the e2e test result for [test_phase4_settlement_foundations.py](/home/beep/projects/VPNBussiness/backend/tests/e2e/test_phase4_settlement_foundations.py)
- the deterministic reconciliation output from `phase4_reconciliation`
- statement snapshots before and after hold release / reserve application
- the dry-run payout execution result
- the post-dry-run payout instruction state

The reconciliation pack used here is defined in [partner-platform-phase4-settlement-reconciliation-pack.md](./partner-platform-phase4-settlement-reconciliation-pack.md).

---

## 4. Tolerance Rules

For this dry-run path:

- reconciliation status must be `green`;
- mismatch count must be `0`;
- outstanding statement liability must equal the closed statement available amount;
- `completed_payout_amount` must remain `0.0`;
- `payout_views[].instruction_status` must remain `approved`;
- `payout_views[].linked_execution_ids` must include the dry-run execution;
- no live payout execution may be present in the evidence path.

---

## 5. Archive Placement

Recommended evidence archive shape:

```text
docs/evidence/partner-platform/YYYY-MM-DD/<environment>/cu7/
  README.md
  metrics/
  logs/
  diffs/
  approvals/
```

The rehearsal log should reference:

- the settlement period id;
- the statement id;
- the payout instruction id;
- the dry-run payout execution id;
- the reconciliation pack path.

---

## 6. Promotion Meaning

Passing `T4.7` means:

- finance and QA can inspect a full internal statement-to-dry-run-payout chain;
- maker-checker and payout audit trails are operationally inspectable;
- dry-run payout execution does not accidentally collapse live liability;
- `T4.8` can consume this artifact as part of the `Phase 4` exit evidence pack.

Failing `T4.7` blocks payout-related promotion beyond internal validation.
