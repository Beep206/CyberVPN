# S3-STAGE-17B Evidence: First Partner Code Redemption, Attribution, Reporting, And Settlement Sandbox Proof

**Date:** 2026-05-25
**Stage:** `S3-STAGE-17B`
**Status:** Passed including controlled synthetic paid conversion/earning fixture
**Parent stage:** `S3-STAGE-17`
**Runtime tag:** `s3-stage17-controlled-partner-pilot.3`
**Stage document:** `docs/cybervpn_stage3_launch_docs/17B_STAGE3_FIRST_PARTNER_CODE_REDEMPTION_ATTRIBUTION_REPORTING_SETTLEMENT_PROOF.md`

---

## 1. Summary

The first controlled partner code redemption/binding proof passed in production.

The proof used one synthetic controlled customer and the existing internal pilot partner code:

```text
workspace=cybervpn-internal-pilot
code=S3PILOT1
synthetic_customer=stage3-partner-redemption-20260525@cyber-vpn.net
```

Evidence passed:

```text
Partner code binding API: passed
Canonical customer commercial binding: passed
Partner reporting summary API: passed
Reporting reconciliation: green
Settlement sandbox API: passed
Live payout block: passed
Outbox pending/failed after operation: 0
```

No auth tokens, secrets, real customer PII, provider payloads, VPN subscription URLs, payout destinations or raw payment payloads are stored in this evidence.

---

## 2. Production Objects

Workspace:

```text
workspace_id=95a59856-61ab-465f-8d56-fb10dc4e1d0b
account_key=cybervpn-internal-pilot
status=active
```

Partner code:

```text
code_id=b430f754-d960-472d-aed4-b6e685b69a5d
code=S3PILOT1
is_active=true
```

Synthetic customer:

```text
user_id=066aae6e-55c0-4de3-87ff-75ce09199504
email=stage3-partner-redemption-20260525@cyber-vpn.net
status=active
```

Partner operator:

```text
login=s2_admin_ops
role=admin
workspace_role=owner
2FA=true
```

---

## 3. API Evidence

Partner code binding:

```text
POST https://api.cyber-vpn.net/api/v1/partner/bind
X-Auth-Realm: customer
HTTP 200
status=bound
```

Reporting summary:

```text
GET https://api.cyber-vpn.net/api/v1/partner-workspaces/95a59856-61ab-465f-8d56-fb10dc4e1d0b/reporting-summary
X-Auth-Realm: partner
HTTP 200
metrics=8
reconciliation.status=green
```

Settlement sandbox:

```text
GET https://api.cyber-vpn.net/api/v1/partner-workspaces/95a59856-61ab-465f-8d56-fb10dc4e1d0b/settlement-sandbox
X-Auth-Realm: partner
HTTP 200
policy.mode=sandbox_only
policy.live_payouts_enabled=false
eligibility.live_payout_allowed=false
```

---

## 4. Database Evidence

Synthetic user binding state:

```text
synthetic_user|066aae6e-55c0-4de3-87ff-75ce09199504|db4653a5-9a53-416d-a4c8-10694ac458c7|95a59856-61ab-465f-8d56-fb10dc4e1d0b|active|true
```

Canonical commercial binding:

```text
binding|29ac8ae7-64de-489a-bed8-8bfbaa9ecaa5|reseller_binding|active|reseller|95a59856-61ab-465f-8d56-fb10dc4e1d0b|b430f754-d960-472d-aed4-b6e685b69a5d|customer_partner_bind|partner_bind_endpoint
```

Money-impacting rows:

```text
partner_earnings=0
order_attribution_results=0
outbox_pending_or_failed=0
```

`partner_earnings=0` and `order_attribution_results=0` are expected because this proof did not create a paid checkout or synthetic finance fixture.

---

## 5. Reporting Evidence

Reporting summary returned these important metrics:

```text
active_users=0
trial_users=not_available
paid_users=0
paid_conversions=0
refunds=0
chargebacks=0
available_earnings=0.00 USD
visible_customer_count=0
```

Reconciliation:

```text
status=green
blocking_mismatch_count=0
mismatch_counts={}
```

Export redaction policy excludes:

```text
email
telegram_id
phone
raw_user_id
ip_address
payment_provider_payload
provider_customer_id
vpn_subscription_url
```

---

## 6. Settlement Sandbox Evidence

Settlement policy:

```text
stage=S3-STAGE-11
mode=sandbox_only
payout_export_status=disabled_by_default
live_payouts_enabled=false
requires_finance_approval=true
requires_maker_checker=true
same_admin_approval_allowed=false
```

Eligibility:

```text
settlement_simulation_reproducible=false
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

This is the expected safe state before any real payout or closed positive statement exists.

---

## 7. Boundary

This evidence proves:

1. partner code redemption/binding route works in production;
2. canonical reseller binding is persisted;
3. reporting summary can be read by the pilot partner operator;
4. reporting reconciliation is green;
5. settlement sandbox is reachable and keeps live payouts blocked;
6. no pending or failed outbox backlog appeared.

This evidence does not prove:

1. a real paid partner conversion;
2. partner earning accrual from a payment;
3. statement close;
4. approved payout account;
5. payout instruction;
6. live payout execution.

Those require either a real low-value payment or an explicitly approved synthetic finance fixture.

Owner approved the synthetic finance fixture after the initial binding-only proof. Additional evidence:

```text
docs/evidence/releases/s3-stage-17b-paid-conversion-earning-fixture-20260525.md
```

---

## 8. Decision

```text
S3-STAGE-17B_FIRST_PARTNER_CODE_REDEMPTION_ATTRIBUTION_REPORTING_SETTLEMENT_PROOF_PASSED
S3-STAGE-17B_SYNTHETIC_PAID_CONVERSION_EARNING_FIXTURE_PASSED
```

Next working step:

```text
S3-STAGE-17C: Controlled External Pilot Partner/User Confirmation And Daily Watch
```
