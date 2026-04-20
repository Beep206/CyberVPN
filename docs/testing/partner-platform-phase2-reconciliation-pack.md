# CyberVPN Partner Platform Phase 2 Reconciliation Pack

**Date:** 2026-04-18  
**Status:** Canonical `T2.7` replay and reconciliation baseline  
**Purpose:** define the deterministic replay harness, expected input shape, mismatch vocabulary, and evidence usage for `Phase 2` order-domain reconciliation.

---

## 1. Document Role

This document defines the canonical `Phase 2` replay layer used to:

- map legacy payment-centric history into deterministic `order` vocabulary;
- materialize replay-shaped `orders`, `payment_attempts`, `refunds`, and `payment_disputes` without live cutover;
- produce reconciliation evidence that explains mismatches, not only aggregate deltas.

It is an evidence and validation document, not a live migration runbook.

Use it together with:

- [../plans/2026-04-18-partner-platform-phase-2-execution-ticket-decomposition.md](../plans/2026-04-18-partner-platform-phase-2-execution-ticket-decomposition.md)
- [../plans/2026-04-17-partner-platform-operational-readiness-package.md](../plans/2026-04-17-partner-platform-operational-readiness-package.md)
- [../plans/2026-04-17-partner-platform-rehearsal-logs-and-evidence-archive-template.md](../plans/2026-04-17-partner-platform-rehearsal-logs-and-evidence-archive-template.md)

---

## 2. Inputs

The replay harness consumes a single JSON snapshot with this top-level shape:

```json
{
  "metadata": {
    "snapshot_id": "phase2-synthetic-001",
    "source": "legacy-payment-export",
    "replay_generated_at": "2026-04-18T10:00:00+00:00"
  },
  "payments": [],
  "refunds": [],
  "payment_disputes": []
}
```

Required rules:

- `payments` is the legacy system-of-record input for `Phase 2` replay.
- `refunds` and `payment_disputes` may be empty arrays, but must not be omitted from evidence fixtures used for gate validation.
- `metadata.replay_generated_at` should be set for deterministic packs committed as evidence.

---

## 3. Replay Semantics

The harness applies these rules:

1. One legacy payment maps to one replayed `order`.
2. One legacy payment maps to one replayed `payment_attempt` for `Phase 2` baseline replay.
3. Replayed object identifiers are deterministic string keys, not newly generated UUIDs:
   - `legacy-payment:<payment_id>`
   - `legacy-attempt:<payment_id>:1`
   - `legacy-refund:<refund_id>`
   - `legacy-dispute:<dispute_id>`
4. Replayed order settlement status is derived from:
   - legacy payment status;
   - replay-visible refund total;
   - payment amount.
5. Refunds and disputes only replay when they map to a known legacy payment.

This harness is intentionally narrow. It does not:

- create live database rows;
- infer Phase 3 attribution ownership;
- compute partner earnings;
- mutate production state.

---

## 4. Outputs

The builder writes a reconciliation pack with these major sections:

- `metadata`
- `legacy_summary`
- `replayed_summary`
- `replayed_objects`
- `reconciliation`

`reconciliation` must contain:

- `status`
- `count_parity`
- `amount_parity`
- `mismatch_counts`
- `mismatches`
- `blocking_mismatches`

Status meanings:

- `green` = no mismatches
- `yellow` = only warning mismatches
- `red` = one or more blocking mismatches

---

## 5. Mismatch Vocabulary

Canonical mismatch codes for `T2.7`:

| Code | Severity | Meaning |
|---|---|---|
| `orphan_refund_without_payment` | `blocking` | refund row cannot be mapped to a legacy payment |
| `orphan_payment_dispute_without_payment` | `blocking` | payment dispute row cannot be mapped to a legacy payment |
| `refund_total_exceeds_payment_amount` | `blocking` | mapped refund total exceeds legacy payment amount |
| `dispute_amount_exceeds_payment_amount` | `blocking` | mapped dispute amount exceeds legacy payment amount |
| `non_completed_payment_with_refund` | `blocking` | refund rows exist for a payment that is not `completed` |
| `payment_status_refunded_without_refund_rows` | `warning` | legacy payment is marked `refunded`, but no refund rows were supplied |
| `unsupported_payment_status` | `warning` | legacy payment status falls outside the canonical replay vocabulary |

The report must explain every mismatch with:

- `code`
- `severity`
- `object_family`
- `source_reference`
- `message`
- `details`

---

## 6. CLI Commands

Build a reconciliation pack:

```bash
python backend/scripts/build_phase2_order_reconciliation_pack.py \
  --input /tmp/phase2_snapshot.json \
  --output /tmp/phase2_reconciliation_pack.json
```

Print a compact summary:

```bash
python backend/scripts/print_phase2_order_reconciliation_summary.py \
  --input /tmp/phase2_reconciliation_pack.json
```

---

## 7. Evidence Usage

Recommended evidence path:

```text
docs/evidence/partner-platform/<date>/<environment>/mw-phase2-order-replay/
```

Expected archive contents:

- input snapshot used for replay
- generated reconciliation pack JSON
- summary transcript
- divergence review notes if status is `yellow` or `red`

Before `Phase 2` gate closes, at least one synthetic reconciliation pack and one staging-shape replay pack should exist in evidence storage.

---

## 8. Gate Expectations

`T2.7` is considered satisfied when:

1. the harness can build replayed `orders`, `payment_attempts`, `refunds`, and `payment_disputes`;
2. identical input snapshots with fixed `replay_generated_at` produce identical packs;
3. mismatch explanations are explicit enough for QA and finance review;
4. the contract test proves the CLI pack builder remains stable.
