# Stage 3 First Partner Code Redemption, Attribution, Reporting, And Settlement Sandbox Proof

**Stage:** `S3-STAGE-17B`
**Status:** Passed with paid-conversion boundary
**Date:** 2026-05-25
**Parent stage:** `S3-STAGE-17: Controlled Partner Pilot`
**Runtime tag:** `s3-stage17-controlled-partner-pilot.3`

---

## 1. Purpose

`S3-STAGE-17B` proves that the first controlled production partner code can be redeemed by a customer-like account and that the resulting partner attribution can be inspected through production reporting and settlement sandbox surfaces.

This proof is intentionally narrow and finance-safe:

1. use one synthetic controlled customer account;
2. bind that account to the pilot partner code;
3. verify canonical customer commercial binding in the production database;
4. verify partner reporting summary access and reconciliation status;
5. verify settlement sandbox policy and payout block posture;
6. keep real payments, partner earnings, statements and payout execution untouched.

---

## 2. Pilot Objects

Production pilot workspace:

```text
workspace_id=95a59856-61ab-465f-8d56-fb10dc4e1d0b
account_key=cybervpn-internal-pilot
display_name=CyberVPN Internal Partner Pilot
status=active
```

Pilot code:

```text
code_id=b430f754-d960-472d-aed4-b6e685b69a5d
code=S3PILOT1
markup_pct=0
is_active=true
```

Partner operator:

```text
login=s2_admin_ops
role=admin
partner_workspace_role=owner
2FA=true
```

Synthetic controlled customer:

```text
user_id=066aae6e-55c0-4de3-87ff-75ce09199504
email=stage3-partner-redemption-20260525@cyber-vpn.net
status=active
```

No real customer, real payment, VPN subscription, payout account or payout instruction was created by this proof.

---

## 3. API Proof

Partner code redemption/binding:

```text
POST https://api.cyber-vpn.net/api/v1/partner/bind
Header: X-Auth-Realm: customer
Body: {"partner_code":"S3PILOT1"}
HTTP 200
status=bound
```

Partner reporting summary:

```text
GET https://api.cyber-vpn.net/api/v1/partner-workspaces/95a59856-61ab-465f-8d56-fb10dc4e1d0b/reporting-summary
Header: X-Auth-Realm: partner
HTTP 200
metric_count=8
reconciliation_status=green
```

Settlement sandbox:

```text
GET https://api.cyber-vpn.net/api/v1/partner-workspaces/95a59856-61ab-465f-8d56-fb10dc4e1d0b/settlement-sandbox
Header: X-Auth-Realm: partner
HTTP 200
mode=sandbox_only
live_payouts_enabled=false
live_payout_allowed=false
```

No auth tokens or secrets are stored in this document or evidence.

---

## 4. Attribution Proof

The bind operation updated the synthetic customer:

```text
partner_user_id=db4653a5-9a53-416d-a4c8-10694ac458c7
partner_account_id=95a59856-61ab-465f-8d56-fb10dc4e1d0b
status=active
is_active=true
```

It also created the canonical customer commercial binding:

```text
binding_type=reseller_binding
binding_status=active
owner_type=reseller
partner_account_id=95a59856-61ab-465f-8d56-fb10dc4e1d0b
partner_code_id=b430f754-d960-472d-aed4-b6e685b69a5d
reason_code=customer_partner_bind
evidence_source=partner_bind_endpoint
```

This is the S3 production attribution proof for controlled partner code redemption. It does not create a paid order attribution result because no real or synthetic paid order was created.

---

## 5. Reporting Proof

Production reporting summary returned:

```text
report_version=available
metrics=8
reconciliation.status=green
reconciliation.blocking_mismatch_count=0
```

Important metrics at this point:

```text
paid_conversions=0
paid_users=0
available_earnings=0.00 USD
refunds=0
chargebacks=0
visible_customer_count=0
```

These values are expected. `S3-STAGE-17B` used a controlled binding proof without creating a paid checkout. Paid conversion reporting should only become non-zero after a real payment or an explicitly approved synthetic finance fixture.

Partner export redaction policy was present and excludes sensitive fields:

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

## 6. Settlement Sandbox Proof

Settlement sandbox returned the expected S3 finance-safe policy:

```text
stage=S3-STAGE-11
mode=sandbox_only
payout_export_status=disabled_by_default
live_payouts_enabled=false
requires_finance_approval=true
requires_maker_checker=true
same_admin_approval_allowed=false
```

Eligibility returned:

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

This is correct for the current pilot state because there is no paid conversion, no closed positive statement and no approved payout account.

---

## 7. Database Proof

Post-operation DB snapshot:

```text
synthetic_user|066aae6e-55c0-4de3-87ff-75ce09199504|db4653a5-9a53-416d-a4c8-10694ac458c7|95a59856-61ab-465f-8d56-fb10dc4e1d0b|active|true
binding|29ac8ae7-64de-489a-bed8-8bfbaa9ecaa5|reseller_binding|active|reseller|95a59856-61ab-465f-8d56-fb10dc4e1d0b|b430f754-d960-472d-aed4-b6e685b69a5d|customer_partner_bind|partner_bind_endpoint
counts|partner_earnings=0|order_attribution_results=0|outbox_pending_or_failed=0
```

---

## 8. Boundary

This stage proves controlled code redemption and persistent attribution binding. It does not approve:

1. automatic payouts;
2. partner self-serve withdrawals;
3. broad public partner acquisition;
4. fake production revenue;
5. synthetic finance records in production without owner approval;
6. treating zero paid conversions as partner revenue evidence.

If owner wants a money-impacting proof before expanding external partners, create a separate explicit gate for a real low-value payment or owner-approved synthetic finance fixture.

---

## 9. Rollback Or Pause

Controlled pause:

```sql
update partner_codes
set is_active = false, updated_at = now()
where code = 'S3PILOT1';

update partner_accounts
set status = 'suspended', updated_at = now()
where account_key = 'cybervpn-internal-pilot';
```

Synthetic binding cleanup is safe only for the controlled synthetic customer:

```sql
delete from customer_commercial_bindings
where user_id = '066aae6e-55c0-4de3-87ff-75ce09199504';

update mobile_users
set partner_user_id = null,
    partner_account_id = null,
    updated_at = now()
where id = '066aae6e-55c0-4de3-87ff-75ce09199504';
```

Do not delete the workspace after real customer bindings, paid orders, earnings, statements or payout instructions are created.

---

## 10. Exit Decision

```text
S3-STAGE-17B_FIRST_PARTNER_CODE_REDEMPTION_ATTRIBUTION_REPORTING_SETTLEMENT_PROOF_PASSED
```

Recommended next working step:

```text
S3-STAGE-17C: Controlled External Pilot Partner/User Confirmation And Daily Watch
```

Optional finance step before expansion:

```text
S3-STAGE-17C-FINANCE: Paid Partner Conversion Evidence Or Owner Waiver
```
