# CyberVPN Partner Platform: Phase 8 Settlement, Payout, And Reporting Shadow Pack

**Date:** 2026-04-19  
**Status:** canonical validation pack for `Phase 8 / T8.4`  
**Purpose:** define the deterministic finance shadow artifact used to compare canonical settlement truth, dry-run payout behavior, and partner export observations before pilot payout approval or ring promotion.

---

## 1. Document Role

This pack is the canonical `Phase 8` finance bridge between:

- `Phase 4` settlement reconciliation truth;
- `Phase 7` analytical reporting truth;
- pilot-facing shadow observations for statements, liability, payout dry-runs, and partner exports.

It exists so finance, partner ops, QA, and rollout owners do not judge shadow settlement readiness from portal counters, spreadsheet calculations, or one-off API screenshots.

This pack is deterministic. identical input snapshots with fixed `replay_generated_at` produce identical packs.

---

## 2. Inputs

The builder consumes a single JSON snapshot with this top-level shape:

```json
{
  "metadata": {
    "snapshot_id": "phase8-settlement-001",
    "source": "phase8-settlement-fixture",
    "replay_generated_at": "2026-04-19T18:00:00+00:00",
    "default_max_amount_delta": "0.00"
  },
  "phase4_snapshot": {},
  "analytical_snapshot": {},
  "statement_shadow_observations": [],
  "liability_shadow_observations": [],
  "payout_dry_run_observations": [],
  "partner_export_observations": [],
  "amount_tolerances": [],
  "approved_divergences": []
}
```

Required rules:

- `phase4_snapshot` must be valid input for the `Phase 4 / T4.6` reconciliation builder.
- `analytical_snapshot` must be valid input for the `Phase 7 / T7.2` reporting mart builder.
- `statement_shadow_observations` is the finance/reference observation layer for canonical statements.
- `liability_shadow_observations` is the partner-account-scoped observation layer for payout liability.
- `payout_dry_run_observations` is the observed dry-run execution layer used before any pilot payout approval path.
- `partner_export_observations` is the partner-facing export layer compared against `partner_reporting_mart`.
- `amount_tolerances` defines metric-specific tolerances for shadow deltas.

---

## 3. Output Sections

The generated pack contains these top-level sections:

- `metadata`
- `input_summary`
- `phase4_reference`
- `analytical_reference`
- `statement_shadow_views`
- `liability_shadow_views`
- `payout_dry_run_views`
- `partner_export_views`
- `pilot_finance_gate`
- `reconciliation`

`phase4_reference` does not create a second settlement truth layer. It embeds the canonical settlement reconciliation status required for `T8.4`.

`analytical_reference` does not create a second reporting truth layer. It embeds the canonical partner reporting mart status required for export parity review.

`pilot_finance_gate` is the machine-readable finance decision surface for pilot promotion.

---

## 4. Tolerance Model

`amount_tolerances[]` rows must include:

- `comparison_family`
- `metric_key`
- `max_delta_amount`

Supported comparison families:

- `statement`
- `liability`
- `payout_dry_run`
- `partner_export`

Supported metric keys in `T8.4`:

- `available_amount`
- `reserve_amount`
- `adjustment_net_amount`
- `outstanding_statement_liability_amount`
- `completed_payout_amount`
- `total_active_reserve_amount`
- `available_earnings_amount`
- `statement_liability_amount`

If a metric does not have an explicit row, `metadata.default_max_amount_delta` is used. If that is also absent, the effective tolerance is `0.00`.

---

## 5. Canonical Mismatch Vocabulary

Canonical `T8.4` mismatch codes include:

| Code | Default severity | Meaning |
|---|---|---|
| `phase4_reference_red` | `blocking` | `Phase 4` settlement reference is red |
| `phase4_reference_not_green` | `warning` | `Phase 4` settlement reference is not green |
| `analytical_reference_red` | `blocking` | `Phase 7` analytical reference is red |
| `analytical_reference_not_green` | `warning` | `Phase 7` analytical reference is not green |
| `duplicate_statement_shadow_observation` | `blocking` | more than one statement observation exists for one statement |
| `missing_statement_shadow_observation` | `blocking` | canonical statement has no shadow observation |
| `unexpected_statement_shadow_observation_without_canonical_statement` | `blocking` | observed statement shadow references no canonical statement |
| `statement_status_mismatch` | `blocking` | observed statement status differs from canonical state |
| `statement_available_amount_delta_exceeded` | `blocking` | observed statement available amount differs beyond tolerance |
| `statement_reserve_amount_delta_exceeded` | `blocking` | observed statement reserve amount differs beyond tolerance |
| `statement_adjustment_net_amount_delta_exceeded` | `blocking` | observed statement adjustment net amount differs beyond tolerance |
| `duplicate_liability_shadow_observation` | `blocking` | more than one liability observation exists for one partner account |
| `missing_liability_shadow_observation` | `blocking` | canonical liability view has no shadow observation |
| `unexpected_liability_shadow_observation_without_canonical_partner` | `blocking` | observed liability shadow references no canonical partner account |
| `liability_outstanding_statement_amount_delta_exceeded` | `blocking` | observed outstanding liability differs beyond tolerance |
| `liability_completed_payout_amount_delta_exceeded` | `blocking` | observed completed payout amount differs beyond tolerance |
| `liability_total_active_reserve_amount_delta_exceeded` | `blocking` | observed active reserve total differs beyond tolerance |
| `duplicate_payout_dry_run_observation` | `blocking` | more than one dry-run observation exists for one instruction |
| `missing_payout_dry_run_observation` | `blocking` | canonical dry-run instruction has no observed dry-run record |
| `unexpected_payout_dry_run_observation_without_instruction` | `blocking` | dry-run observation references no canonical instruction |
| `payout_dry_run_missing_canonical_execution` | `blocking` | canonical snapshot has no dry-run execution for the instruction |
| `payout_dry_run_completed_instruction_unexpected` | `blocking` | canonical dry-run instruction is already completed |
| `payout_dry_run_instruction_status_mismatch` | `blocking` | observed dry-run instruction status differs from canonical state |
| `payout_dry_run_execution_status_mismatch` | `blocking` | observed dry-run execution statuses differ from canonical execution state |
| `payout_dry_run_completed_payout_amount_delta_exceeded` | `blocking` | observed completed payout amount differs beyond tolerance |
| `payout_dry_run_outstanding_liability_amount_delta_exceeded` | `blocking` | observed outstanding liability differs beyond tolerance |
| `duplicate_partner_export_observation` | `blocking` | more than one export observation exists for one export key |
| `partner_export_missing_partner_row` | `blocking` | export observation references no canonical partner reporting row |
| `partner_export_paid_conversion_count_mismatch` | `blocking` | export paid-conversion count differs from canonical reporting |
| `partner_export_available_earnings_amount_mismatch` | `blocking` | export available earnings differs beyond tolerance |
| `partner_export_statement_liability_amount_mismatch` | `blocking` | export statement liability differs beyond tolerance |
| `partner_export_currency_codes_mismatch` | `blocking` | export currency coverage differs from canonical reporting |

Approved divergences do not rename codes. They only downgrade specific instances to tolerated warning state and must carry `approval_reference`.

---

## 6. Expected Reconciliation Behavior

The builder must:

1. rebuild canonical settlement truth from `phase4_snapshot`;
2. rebuild canonical partner reporting truth from `analytical_snapshot`;
3. compare statement observations to canonical statement totals and status;
4. compare partner-account liability observations to canonical liability views;
5. compare dry-run payout observations to canonical payout instruction and dry-run execution state;
6. compare partner export observations to `partner_reporting_mart`;
7. produce machine-readable blocking and tolerated mismatches suitable for pilot finance decisions.

This pack does not execute payouts. It proves whether finance shadow evidence is clean enough to move toward pilot approval.

---

## 7. CLI Usage

Build the pack:

```bash
backend/.venv/bin/python backend/scripts/build_phase8_settlement_shadow_pack.py \
  --input /path/to/phase8-settlement-shadow-snapshot.json \
  --output backend/docs/evidence/partner-platform/phase8-settlement-shadow-pack.json
```

Print a compact summary:

```bash
backend/.venv/bin/python backend/scripts/print_phase8_settlement_shadow_summary.py \
  --input backend/docs/evidence/partner-platform/phase8-settlement-shadow-pack.json
```

---

## 8. Gate Usage

`T8.4` is considered satisfied when:

1. statement and liability mismatches are machine-readable and auditable;
2. payout dry-run evidence exists before any pilot payout approval path;
3. partner export parity is measured against canonical reporting truth before ring promotion;
4. identical input snapshots with fixed `replay_generated_at` produce identical packs.

If the pack is `red`, payout-bearing pilots are not ready for widening.
