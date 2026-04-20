# CyberVPN Partner Platform: Phase 7 Analytical Marts And Reconciliation Pack

**Date:** 2026-04-18  
**Status:** canonical validation pack for `Phase 7 / T7.2`  
**Purpose:** define the deterministic analytical artifact for order-level reporting marts, partner reporting marts, and outbox-driven reporting health views.

---

## 1. Document Role

This pack exists to prove that `Phase 7` reporting can be reconstructed from canonical platform objects without re-deriving business truth from frontend telemetry, partner-portal shortcuts, or mutable spreadsheet logic.

The pack is a machine-generated report built from a reporting snapshot containing:

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

The pack is deterministic. identical input snapshots with fixed `replay_generated_at` produce identical packs.

---

## 2. Output Sections

The report contains these top-level sections:

- `metadata`
- `input_summary`
- `order_reporting_mart`
- `partner_reporting_mart`
- `reporting_health_views`
- `reconciliation`

`order_reporting_mart` is the canonical order-grain reporting layer. It is the bridge between operational order truth and all later partner/export/reporting surfaces.

`partner_reporting_mart` is the partner-account-grain analytical layer used for dashboard and export baselines.

`reporting_health_views` is the outbox/publication health layer used to verify whether analytical refresh is actually trustworthy.

---

## 3. Canonical Mart Definitions

Each `order_reporting_mart[]` row must include:

- `order_id`
- `user_id`
- `partner_account_id`
- `partner_code_id`
- `owner_type`
- `owner_source`
- `sale_channel`
- `currency_code`
- `order_status`
- `settlement_status`
- `commissionability_status`
- `is_paid_conversion`
- `is_qualifying_first_payment`
- `is_renewal`
- `has_refund`
- `has_open_dispute`
- `has_chargeback`
- `commission_base_amount`
- `displayed_price`

Each `partner_reporting_mart[]` row must include:

- `partner_account_id`
- `paid_conversion_count`
- `qualifying_first_payment_count`
- `renewal_paid_count`
- `refund_count`
- `chargeback_count`
- `refund_rate`
- `chargeback_rate`
- `paid_conversion_commission_base_amount`
- `available_earnings_amount`
- `statement_liability_amount`
- `statement_count`
- `earning_event_count`

`statement_liability_amount` is the current statement-backed amount visible to reporting before later payout/export layers consume it.

---

## 4. Reporting Health Views

`reporting_health_views` must include:

- `consumer_health_views`
- `family_health_views`

`consumer_health_views[]` tracks publication state for canonical outbox consumers such as:

- `analytics_mart`
- `operational_replay`

Important fields:

- `published_count`
- `failed_count`
- `backlog_count`

The analytical layer is not trustworthy if the event/outbox layer is degraded. Reporting health is therefore a release gate, not a support-only diagnostic.

---

## 5. Canonical Mismatch Vocabulary

Blocking mismatches for `Phase 7 / T7.2` include:

- `attribution_result_without_order`
- `commissionability_evaluation_without_order`
- `renewal_order_without_order`
- `refund_without_order`
- `payment_dispute_without_order`
- `earning_event_without_partner_account`
- `partner_statement_without_partner_account`
- `outbox_event_missing_required_publication`

Warning mismatches include:

- `committed_order_missing_attribution_result`
- `paid_order_missing_commissionability_evaluation`
- `eligible_partner_orders_missing_earning_events`
- `reporting_publication_backlog_present`
- `reporting_publication_failed`

These codes are canonical and machine-readable. They are the reporting-approved mismatch vocabulary for `Phase 7 / T7.2`.

---

## 6. Expected Reconciliation Behavior

The analytical mart builder must:

1. validate that attribution, commissionability, renewal, refund, and dispute rows all reference valid orders;
2. compute order-grain reporting fields from canonical operational truth, not from UI state;
3. derive `qualifying_first_payment_count` deterministically from canonical paid-order lineage;
4. aggregate partner-level reporting from canonical order, settlement, and statement rows;
5. validate outbox publication coverage for required analytical consumers;
6. surface reporting-health degradation as explicit mismatch codes.

This pack is not a dashboard. It is a deterministic analytical and reconciliation artifact.

---

## 7. CLI Usage

Build the analytical marts pack:

```bash
backend/.venv/bin/python backend/scripts/build_phase7_reporting_marts_pack.py \
  --input /path/to/phase7-reporting-snapshot.json \
  --output backend/docs/evidence/partner-platform/phase7-reporting-marts-pack.json
```

Print a compact summary:

```bash
backend/.venv/bin/python backend/scripts/print_phase7_reporting_marts_summary.py \
  --input backend/docs/evidence/partner-platform/phase7-reporting-marts-pack.json
```

---

## 8. Gate Usage

This pack is required input for:

- `T7.3` partner dashboards and exports;
- `T7.7` analytical replay and parity evidence;
- `T7.8` Phase 7 exit evidence.

If the pack status is `red`, `Phase 7` is not ready for partner-facing reporting or analytical rollout sign-off.
