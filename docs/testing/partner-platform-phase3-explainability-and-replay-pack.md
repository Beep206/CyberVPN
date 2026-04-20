# CyberVPN Partner Platform Phase 3 Explainability And Replay Pack

**Date:** 2026-04-18  
**Status:** Canonical `T3.7` explainability and replay baseline  
**Purpose:** define the deterministic replay harness, support-facing explainability expectations, mismatch vocabulary, and lane evidence usage for `Phase 3`.

---

## 1. Document Role

This document defines the canonical `Phase 3` replay and inspection layer used to:

- explain why a specific order resolved to a specific commercial owner;
- show how growth rewards coexist with, but do not replace, commercial ownership;
- compare persisted attribution winners against deterministic reference logic;
- provide support and finance with lane-aware inspection baselines.

It is an evidence and validation document, not a live cutover runbook.

Use it together with:

- [../plans/2026-04-18-partner-platform-phase-3-execution-ticket-decomposition.md](../plans/2026-04-18-partner-platform-phase-3-execution-ticket-decomposition.md)
- [../plans/2026-04-17-partner-platform-operational-readiness-package.md](../plans/2026-04-17-partner-platform-operational-readiness-package.md)
- [../plans/2026-04-17-partner-platform-rehearsal-logs-and-evidence-archive-template.md](../plans/2026-04-17-partner-platform-rehearsal-logs-and-evidence-archive-template.md)

---

## 2. Inputs

The replay harness consumes a single JSON snapshot with this top-level shape:

```json
{
  "metadata": {
    "snapshot_id": "phase3-synthetic-001",
    "source": "phase3-evidence-fixture",
    "replay_generated_at": "2026-04-18T13:30:00+00:00"
  },
  "orders": [],
  "partner_codes": [],
  "touchpoints": [],
  "bindings": [],
  "attribution_results": [],
  "growth_reward_allocations": [],
  "renewal_orders": []
}
```

Required rules:

- `orders` is the canonical input family for replay cases.
- `partner_codes` must be present when touchpoint replay depends on owner-type inference.
- `metadata.replay_generated_at` should be fixed for deterministic evidence packs.
- `growth_reward_allocations` and `renewal_orders` may be empty arrays, but must not be omitted in gate fixtures.

---

## 3. Replay Semantics

The harness applies these rules:

1. reference winner resolution follows the canonical precedence:
   - `manual_override`
   - `contract_assignment`
   - `explicit_code`
   - `persistent_reseller_binding`
   - `passive_click`
   - `storefront_default`
   - `none`
2. `partner_codes.partner_account_id` determines whether a touchpoint winner is inferred as `affiliate` or `reseller`.
3. replay compares persisted `attribution_results` to reference winners at the winner level, not at the payout-ledger level.
4. replay summarizes growth rewards and lane views, but does not mutate live database state.
5. replay treats `renewal_orders` as an explainability overlay for `renewal_chain`, not as a replacement for persisted attribution results.

This harness does not:

- create or mutate live rows;
- compute statements or payouts;
- reopen immutable attribution results;
- replace settlement or finance reconciliation.

---

## 4. Outputs

The builder writes a replay pack with these major sections:

- `metadata`
- `input_summary`
- `order_cases`
- `comparison`

Each `order_case` must include:

- `persisted_attribution_result`
- `reference_attribution_result`
- `growth_reward_summary`
- `renewal_summary`
- `lane_views`
- `winner_matches`
- `mismatch_codes`

When `renewal_summary` is present it should also carry:

- `effective_partner_account_id`
- `effective_partner_code_id`

`comparison` must contain:

- `status`
- `mismatch_counts`
- `mismatches`
- `blocking_mismatches`

Status meanings:

- `green` = no mismatches
- `yellow` = only warning mismatches
- `red` = one or more blocking mismatches

---

## 5. Mismatch Vocabulary

Canonical mismatch codes for `T3.7`:

| Code | Severity | Meaning |
|---|---|---|
| `missing_attribution_result` | `blocking` | replay found a winner but persisted attribution result is missing |
| `unexpected_attribution_result_without_reference_owner` | `blocking` | persisted result exists but replay found no winner |
| `owner_type_mismatch` | `blocking` | persisted owner type differs from reference winner |
| `owner_source_mismatch` | `blocking` | persisted owner source differs from reference winner |
| `partner_code_mismatch` | `blocking` | persisted partner code differs from reference winner |
| `partner_account_mismatch` | `blocking` | persisted partner account differs from reference winner |

The report must explain every mismatch with:

- `code`
- `severity`
- `order_id`
- `message`
- `details`

---

## 6. Support-Facing Explainability Baseline

The canonical order explainability payload should expose:

- `commercial_resolution_summary`
- `growth_reward_summary`
- `lane_views`
- `linked_growth_reward_allocations`
- `renewal_order`

`renewal_order` inspection should include partner ownership identity, not only owner type and source, so downstream shadow tooling can compare renewal ownership deterministically.

`lane_views` must provide readable inspection slices for these active lanes:

- `invite_gift`
- `consumer_referral`
- `creator_affiliate`
- `reseller_distribution`
- `renewal_chain`

`performance_media_buyer` remains present in the shape even when inactive, so downstream tooling does not need to rename the payload later.

---

## 7. CLI Commands

Build a replay pack:

```bash
python backend/scripts/build_phase3_explainability_replay_pack.py \
  --input /tmp/phase3_snapshot.json \
  --output /tmp/phase3_explainability_pack.json
```

Print a compact summary:

```bash
python backend/scripts/print_phase3_explainability_replay_summary.py \
  --input /tmp/phase3_explainability_pack.json
```

---

## 8. Evidence Usage

Recommended evidence path:

```text
docs/evidence/partner-platform/<date>/<environment>/mw-phase3-explainability-replay/
```

Expected archive contents:

- replay input snapshot
- generated replay pack JSON
- compact summary transcript
- support screenshots or API responses for at least one case per active lane
- divergence review notes if status is `yellow` or `red`

Before `Phase 3` gate closes, at least one synthetic replay pack and one staging-shape explainability evidence set should exist.

---

## 9. Active Lane Coverage

Minimum executable evidence coverage:

- `invite_gift`: order explainability with `invite_reward`, `gift_bonus`, or `bonus_days`
- `consumer_referral`: order explainability with `referral_credit`
- `creator_affiliate`: resolved `affiliate` winner in explainability
- `reseller_distribution`: resolved `reseller` winner in explainability
- `renewal_chain`: explainability payload showing `renewal_order`

---

## 10. Gate Expectations

`T3.7` is considered satisfied when:

1. explainability payloads expose winner, reward, and lane summaries for support and finance;
2. identical input snapshots with fixed `replay_generated_at` produce identical replay packs;
3. replay output explains winner divergence with canonical mismatch codes;
4. executable tests cover at least one explainability case per active lane.
