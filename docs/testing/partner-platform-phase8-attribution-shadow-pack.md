# CyberVPN Partner Platform: Phase 8 Attribution Shadow And Explainability Comparison Pack

**Date:** 2026-04-19  
**Status:** canonical validation pack for `Phase 8 / T8.3`  
**Purpose:** define the deterministic shadow comparison artifact used to compare canonical attribution and explainability outcomes against legacy or reference observations before pilot promotion.

---

## 1. Document Role

This pack is the canonical `Phase 8` bridge between:

- `Phase 3` deterministic explainability replay;
- `Phase 7` analytical marts and reporting health;
- `Phase 8` pilot-promotion thresholds.

It exists to prove that attribution winners, binding explainability, and renewal ownership can be compared repeatedly against approved legacy or reference observations without relying on ad-hoc spreadsheets or portal screenshots.

This pack is not a live API surface and does not mutate platform truth.

---

## 2. Inputs

The builder consumes a single JSON snapshot with this top-level shape:

```json
{
  "metadata": {
    "snapshot_id": "phase8-shadow-001",
    "source": "phase8-shadow-fixture",
    "replay_generated_at": "2026-04-19T15:30:00+00:00",
    "default_max_divergence_rate": "0.25"
  },
  "phase3_snapshot": {},
  "analytical_snapshot": {},
  "legacy_shadow_observations": [],
  "approved_divergences": [],
  "lane_tolerances": []
}
```

Required rules:

- `phase3_snapshot` must be a valid `T3.7` replay input.
- `analytical_snapshot` must be a valid `T7.2` reporting-mart input.
- `legacy_shadow_observations` is the approved legacy/reference observation family for `Phase 8` shadow review.
- `approved_divergences` is optional, but every approval must include a canonical mismatch `code` and an `approval_reference`.
- `lane_tolerances` must define `max_divergence_rate` for every lane expected to enter pilot promotion.
- `metadata.replay_generated_at` should be fixed for deterministic evidence storage.

---

## 3. Comparison Semantics

The shadow builder applies these rules:

1. canonical winner and explainability reference come from the deterministic `Phase 3` replay pack, not from ad-hoc UI inspection;
2. `Phase 7` analytical marts act as the reporting-grade reference for order presence and owner propagation;
3. `legacy_shadow_observations` are compared order-by-order against canonical attribution, binding, and renewal ownership;
4. approved divergences can downgrade specific mismatch instances from blocking to tolerated warning state;
5. pilot promotion is blocked if:
   - any non-approved blocking mismatch exists;
   - a lane exceeds its `max_divergence_rate`;
   - required tolerances are missing.

This builder does not:

- rewrite attribution results;
- reopen immutable orders;
- replace settlement or payout reconciliation;
- mint a second source of truth for partner ownership.

---

## 4. Outputs

The generated pack contains these top-level sections:

- `metadata`
- `input_summary`
- `phase3_reference`
- `analytical_reference`
- `shadow_order_views`
- `lane_divergence_views`
- `pilot_promotion_gate`
- `reconciliation`

Each `shadow_order_view` must include:

- `order_id`
- `shadow_lane`
- `canonical_reference`
- `persisted_attribution_result`
- `canonical_binding`
- `renewal_summary`
- `legacy_shadow_observation`
- `reporting_mart_reference`
- `mismatch_codes`
- `blocking_mismatch_codes`
- `tolerated_mismatch_codes`

`lane_divergence_views` is the canonical lane-level threshold section used for pilot gating.

Status meanings:

- `green` = no mismatches
- `yellow` = only tolerated or warning mismatches
- `red` = one or more blocking mismatches

---

## 5. Canonical Mismatch Vocabulary

Canonical `T8.3` mismatch codes include:

| Code | Default severity | Meaning |
|---|---|---|
| `phase3_reference_red` | `blocking` | `Phase 3` replay reference is red and cannot support shadow sign-off |
| `phase3_reference_not_green` | `warning` | `Phase 3` replay reference is not green |
| `analytical_reference_red` | `blocking` | `Phase 7` analytical reference is red |
| `analytical_reference_not_green` | `warning` | `Phase 7` analytical reference is not green |
| `duplicate_legacy_shadow_observation` | `blocking` | more than one legacy observation exists for the same order |
| `missing_legacy_shadow_observation` | `blocking` | canonical order has no legacy/reference shadow observation |
| `unexpected_legacy_shadow_observation_without_canonical_order` | `blocking` | legacy shadow references an order not present in canonical replay input |
| `legacy_owner_type_mismatch` | `blocking` | legacy winner owner type differs from canonical replay |
| `legacy_owner_source_mismatch` | `blocking` | legacy winner owner source differs from canonical replay |
| `legacy_partner_account_mismatch` | `blocking` | legacy partner account differs from canonical replay |
| `legacy_partner_code_mismatch` | `blocking` | legacy partner code differs from canonical replay |
| `legacy_rule_path_mismatch` | `warning` | legacy explainability path differs from canonical rule path |
| `legacy_binding_reference_missing` | `blocking` | canonical replay selected a binding but legacy shadow omitted it |
| `legacy_binding_reference_unexpected` | `blocking` | legacy shadow contains binding context where canonical replay selected none |
| `legacy_binding_type_mismatch` | `blocking` | legacy binding type differs from canonical winning binding |
| `legacy_binding_partner_account_mismatch` | `blocking` | legacy binding partner account differs from canonical winning binding |
| `legacy_binding_partner_code_mismatch` | `blocking` | legacy binding partner code differs from canonical winning binding |
| `legacy_renewal_reference_missing` | `blocking` | canonical renewal ownership exists but legacy shadow omitted it |
| `legacy_renewal_reference_unexpected` | `blocking` | legacy shadow reports renewal ownership for non-renewal canonical order |
| `legacy_renewal_owner_type_mismatch` | `blocking` | legacy renewal owner type differs from canonical renewal ownership |
| `legacy_renewal_owner_source_mismatch` | `blocking` | legacy renewal owner source differs from canonical renewal ownership |
| `legacy_renewal_partner_account_mismatch` | `blocking` | legacy renewal partner account differs from canonical renewal ownership |
| `legacy_renewal_partner_code_mismatch` | `blocking` | legacy renewal partner code differs from canonical renewal ownership |
| `canonical_shadow_order_missing_from_reporting_mart` | `blocking` | canonical shadow order is missing from the `Phase 7` order mart |
| `reporting_mart_owner_type_mismatch` | `blocking` | `Phase 7` owner type differs from canonical shadow reference |
| `reporting_mart_owner_source_mismatch` | `blocking` | `Phase 7` owner source differs from canonical shadow reference |
| `reporting_mart_partner_account_mismatch` | `blocking` | `Phase 7` partner account differs from canonical shadow reference |
| `lane_divergence_tolerance_missing` | `blocking` | lane-specific pilot tolerance was not supplied |
| `lane_divergence_rate_exceeded` | `blocking` | observed divergence rate exceeds approved threshold for the lane |

Approved divergences do not rename codes. They only change the specific mismatch instance from blocking to tolerated warning state, and they must carry `approval_reference`.

---

## 6. Tolerance Rules

`lane_tolerances[]` rows must include:

- `lane_key`
- `max_divergence_rate`

Supported lane keys for `T8.3`:

- `renewal_chain`
- `reseller_distribution`
- `creator_affiliate`
- `performance_media_buyer`
- `consumer_referral`
- `invite_gift`
- `direct_store`

`divergence_rate` is calculated as:

```text
divergent_orders / total_orders
```

where `divergent_orders` includes any order with one or more mismatch codes, even if some of those mismatches are approved/tolerated.

Pilot promotion rules:

1. lane divergence must remain `<= max_divergence_rate`;
2. tolerated mismatches may exist only if they have explicit `approval_reference`;
3. any non-approved blocking mismatch keeps the pack `red`.

---

## 7. CLI Usage

Build the pack:

```bash
backend/.venv/bin/python backend/scripts/build_phase8_attribution_shadow_pack.py \
  --input /path/to/phase8-attribution-shadow-snapshot.json \
  --output backend/docs/evidence/partner-platform/phase8-attribution-shadow-pack.json
```

Print a compact summary:

```bash
backend/.venv/bin/python backend/scripts/print_phase8_attribution_shadow_summary.py \
  --input backend/docs/evidence/partner-platform/phase8-attribution-shadow-pack.json
```

---

## 8. Evidence Usage

Recommended archive path:

```text
docs/evidence/partner-platform/<date>/<environment>/mw-phase8-attribution-shadow/
```

Expected contents:

- input snapshot
- generated pack JSON
- summary output
- divergence register entry for every tolerated mismatch
- owner sign-off note for every `approved_divergence`

Before `T8.5` pilot widening:

1. at least one staging-shape pack must exist for every lane under promotion;
2. the pack must be reproducible from canonical replay input;
3. blocking mismatches must be zero for the lanes being promoted.

---

## 9. Gate Expectations

`T8.3` is considered satisfied when:

1. shadow attribution can be rerun from canonical replay input and produce identical output for identical input snapshots;
2. explainability differences call out attribution, binding, and renewal ownership drift explicitly;
3. lane-level divergence views expose `max_divergence_rate` and promotion status;
4. blocking mismatches prevent pilot promotion;
5. identical input snapshots with fixed `replay_generated_at` produce identical packs.
