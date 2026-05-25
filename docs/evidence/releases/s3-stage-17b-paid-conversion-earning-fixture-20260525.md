# S3-STAGE-17B Evidence: Synthetic Paid Conversion And Earning Fixture

**Date:** 2026-05-25
**Stage:** `S3-STAGE-17B`
**Status:** Passed
**Runtime tag:** `s3-stage17-controlled-partner-pilot.3`
**Evidence ID:** `S3-17B-PAID-FIXTURE-20260525`

---

## 1. Summary

Owner approved creating a controlled synthetic paid conversion/earning in production so partner reporting can show non-zero paid conversion and earning behavior before broader S3 expansion.

This fixture is not real revenue and must not be used for payout execution.

---

## 2. Created Fixture Rows

```text
workspace_id=95a59856-61ab-465f-8d56-fb10dc4e1d0b
synthetic_user_id=066aae6e-55c0-4de3-87ff-75ce09199504
order_id=0008ee0f-a451-4e13-aff8-6660b65318e0
payment_id=f53021ff-143f-4541-9c85-99e95bf8d3aa
order_attribution_result_id=4dc2fe33-e66d-4923-93cb-000573997fe7
partner_earning_id=789f6bac-2554-4d63-bc91-d4838cb21e4d
earning_event_id=1bff423d-7277-4bfd-aa4f-2de128af1b74
base_price=20.00 USD
commission_pct=10.00
commission_amount=2.00 USD
```

DB count proof:

```text
fixture_counts|orders=1|payments=1|order_attribution_results=1|partner_earnings=1|earning_events=1|outbox_pending_or_failed=0
```

---

## 3. Reporting Proof

Reporting summary after fixture:

```text
active_users=1
paid_users=1
paid_conversions=1
refunds=0
chargebacks=0
available_earnings=2.00 USD
visible_customer_count=1
reconciliation.status=green
blocking_mismatch_count=0
```

Conversion records:

```text
kind=first_paid
status=commissionable
order_label=ORDER-0008EE0F
customer_label=masked
code_label=S3PILOT1
amount=20.00 USD
customer_scope=workspace_scoped
```

Analytics metrics:

```text
first_paid=1
repeat_paid=0
refund_rate=0.00%
chargeback_rate=0.00%
earnings_available=2.00 USD
```

---

## 4. Settlement Sandbox Proof

Settlement sandbox after fixture:

```text
settlement_simulation_reproducible=true
payout_instruction_allowed=false
dry_run_execution_allowed=false
live_payout_allowed=false
manual_approval_required=true
maker_checker_required=true
```

Blocked reasons:

```text
stage_blocks_live_payout
no_closed_positive_statement
payout_account_not_approved
no_approved_instruction_for_dry_run
```

This confirms that reporting and earning are visible while payout remains blocked.

---

## 5. Cleanup

Use the evidence ID for cleanup:

```text
S3-17B-PAID-FIXTURE-20260525
```

Cleanup must remove only rows carrying this evidence ID. Do not delete real partner/customer rows through broad workspace deletes after real traffic starts.

---

## 6. Decision

```text
S3-STAGE-17B_SYNTHETIC_PAID_CONVERSION_EARNING_FIXTURE_PASSED
```

