# CyberVPN Partner Platform: Phase 7 Replay, Parity, And Evidence Pack

**Date:** 2026-04-19  
**Status:** canonical validation pack for `Phase 7 / T7.7`  
**Purpose:** define the deterministic evidence artifact that proves analytical truth, channel parity, partner export parity, and postback parity on top of the completed `Phase 7` foundations.

---

## 1. Document Role

This pack exists to prove that `Phase 7` adoption is measurable and replay-safe across channels and partner-facing reporting surfaces.

It is not another dashboard and it is not a browser smoke checklist. It is a machine-generated evidence artifact built from:

- a raw `analytical_snapshot` compatible with the `Phase 7 / T7.2` mart builder;
- `channel_parity_expectations`;
- `channel_parity_observations`;
- `partner_export_observations`;
- `postback_delivery_observations`.

The pack is deterministic. identical input snapshots with fixed `replay_generated_at` produce identical packs.

---

## 2. Output Sections

The report contains these top-level sections:

- `metadata`
- `input_summary`
- `analytical_reference`
- `channel_coverage`
- `channel_parity_views`
- `partner_export_views`
- `postback_delivery_views`
- `reconciliation`

`analytical_reference` embeds the canonical `Phase 7 / T7.2` truth used by the rest of the evidence pack. `T7.7` does not create a second analytical truth layer.

---

## 3. Input Contracts

### 3.1 Analytical Reference

`analytical_snapshot` must be valid input for the `Phase 7` mart builder and includes:

- `orders`
- `order_attribution_results`
- `commissionability_evaluations`
- `renewal_orders`
- `refunds`
- `payment_disputes`
- `earning_events`
- `partner_statements`
- `outbox_events`
- `outbox_publications`

### 3.2 Channel Parity

`channel_parity_expectations[]` is the canonical expectation layer for a parity scope.

Each row must define:

- `parity_key`
- `reference_channel`
- `required_channels`
- `expected_paid_order_count`
- `expected_active_entitlement_count`
- `expected_service_state_status`
- `expected_visible_order_ids`

`channel_parity_observations[]` is the observed output from real channel consumers.

Each row should define:

- `parity_key`
- `channel_key`
- `observed_paid_order_count`
- `observed_active_entitlement_count`
- `observed_service_state_status`
- `observed_visible_order_ids`

### 3.3 Partner Export Evidence

`partner_export_observations[]` is the partner-facing reporting/export layer to compare against `partner_reporting_mart`.

Each row should define:

- `export_key`
- `workspace_id`
- `partner_account_id`
- `export_status`
- `observed_paid_conversion_count`
- `observed_available_earnings_amount`
- `observed_statement_liability_amount`
- `observed_currency_codes`

### 3.4 Postback Evidence

`postback_delivery_observations[]` is the external delivery evidence layer to compare against canonical `outbox_publications`.

Each row should define:

- `delivery_key`
- `workspace_id`
- `partner_account_id`
- `outbox_event_id`
- `consumer_key`
- `observed_delivery_status`

---

## 4. Canonical Mismatch Vocabulary

Blocking mismatches include:

- `analytical_reference_red`
- `channel_parity_missing_official_reference`
- `channel_parity_missing_required_channel`
- `channel_parity_duplicate_observation`
- `channel_paid_order_count_mismatch`
- `channel_active_entitlement_count_mismatch`
- `channel_visible_order_ids_mismatch`
- `channel_service_state_status_mismatch`
- `channel_parity_additional_channel_coverage_insufficient`
- `partner_export_missing_partner_row`
- `partner_export_paid_conversion_count_mismatch`
- `partner_export_available_earnings_amount_mismatch`
- `partner_export_statement_liability_amount_mismatch`
- `partner_export_currency_codes_mismatch`
- `postback_missing_publication`
- `postback_delivery_status_mismatch`

Warning mismatches include:

- `analytical_reference_not_green`
- `postback_publication_failed`
- `postback_publication_backlog_present`

These codes are canonical and machine-readable. `T7.7` is complete only when parity and reporting evidence can be discussed in these terms instead of ad-hoc prose.

---

## 5. Expected Reconciliation Behavior

The evidence builder must:

1. rebuild canonical analytical reference from the raw `analytical_snapshot`;
2. reject parity assertions when the analytical reference itself is red;
3. prove official-web parity and at least two additional channels from explicit evidence rows;
4. compare partner export observations to `partner_reporting_mart`, not to UI counters;
5. compare postback observations to canonical `outbox_publications`, not to operator memory;
6. output machine-readable mismatch counts suitable for archive and rollout evidence.

This pack is the bridge between `Phase 7` implementation and `Phase 8` shadow and pilot gates.

---

## 6. CLI Usage

Build the parity evidence pack:

```bash
backend/.venv/bin/python backend/scripts/build_phase7_parity_evidence_pack.py \
  --input /path/to/phase7-parity-snapshot.json \
  --output backend/docs/evidence/partner-platform/phase7-parity-evidence-pack.json
```

Print a compact summary:

```bash
backend/.venv/bin/python backend/scripts/print_phase7_parity_evidence_summary.py \
  --input backend/docs/evidence/partner-platform/phase7-parity-evidence-pack.json
```

---

## 7. Gate Usage

This pack is required input for:

- `T7.8` Phase 7 exit evidence;
- `Phase 8` shadow reporting proof;
- pilot and rollout discussions that claim channel/reporting parity is already done.

If this pack is `red`, `Phase 7` parity and external reporting readiness are not closed.
