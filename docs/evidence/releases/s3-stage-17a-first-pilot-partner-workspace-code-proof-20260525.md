# S3-STAGE-17A Evidence: First Pilot Partner Workspace And Code Proof

**Date:** 2026-05-25
**Stage:** `S3-STAGE-17A`
**Status:** Passed
**Parent stage:** `S3-STAGE-17`
**Runtime tag:** `s3-stage17-controlled-partner-pilot.3`
**Stage document:** `docs/cybervpn_stage3_launch_docs/17A_STAGE3_FIRST_PILOT_PARTNER_WORKSPACE_CODE_PROOF.md`

---

## 1. Summary

The first controlled partner pilot workspace and partner code were created in production.

This was done through production APIs, not only through direct database inserts:

```text
Admin workspace creation API: passed
Mobile partner code creation API: passed
Partner workspace/session API proof: passed
Mobile partner code/dashboard proof: passed
Outbox backlog after operation: 0 pending
```

No secrets or auth tokens are stored in this evidence.

---

## 2. Created Production Objects

Workspace:

```text
workspace_id=95a59856-61ab-465f-8d56-fb10dc4e1d0b
account_key=cybervpn-internal-pilot
display_name=CyberVPN Internal Partner Pilot
status=active
```

Operator membership:

```text
operator_login=s2_admin_ops
workspace_role=owner
membership_status=active
operator_2fa=true
```

Mobile owner:

```text
telegram_username=Sasha_Beep
is_partner=true
partner_account_id=95a59856-61ab-465f-8d56-fb10dc4e1d0b
```

Partner code:

```text
code_id=b430f754-d960-472d-aed4-b6e685b69a5d
code=S3PILOT1
markup_pct=0
is_active=true
partner_account_id=95a59856-61ab-465f-8d56-fb10dc4e1d0b
```

---

## 3. API Proof

Workspace creation:

```text
POST https://admin.cyber-vpn.net/api/v1/admin/partner-workspaces
HTTP 201
```

Partner code creation:

```text
POST https://api.cyber-vpn.net/api/v1/partner/codes
HTTP 201
```

Partner operator workspace list:

```text
GET https://api.cyber-vpn.net/api/v1/partner-workspaces/me
Header: X-Auth-Realm: partner
HTTP 200
workspace_count=1
```

Partner session bootstrap:

```text
GET https://api.cyber-vpn.net/api/v1/partner-session/bootstrap?workspace_id=95a59856-61ab-465f-8d56-fb10dc4e1d0b
Header: X-Auth-Realm: partner
HTTP 200
workspace_count=1
active_workspace_key=cybervpn-internal-pilot
```

Mobile owner partner codes:

```text
GET https://api.cyber-vpn.net/api/v1/partner/codes
HTTP 200
codes=["S3PILOT1"]
```

Mobile partner dashboard:

```text
GET https://api.cyber-vpn.net/api/v1/partner/dashboard
HTTP 200
code_count=1
```

---

## 4. Database Proof

Post-operation snapshot:

```text
partner_accounts=1
partner_account_users=1
partner_codes=1
s3_workspace=cybervpn-internal-pilot:active
s3_code=S3PILOT1:true:95a59856-61ab-465f-8d56-fb10dc4e1d0b
outbox_pending=0
```

---

## 5. Risk Notes

This is an internal pilot workspace and code proof. It does not yet prove paid conversion, attribution result, report consistency, or settlement sandbox behavior from a real customer journey.

The next proof should use a controlled test user and verify:

1. partner code redemption or binding;
2. commercial binding or attribution record;
3. reporting visibility;
4. settlement sandbox posture;
5. no payout execution without manual finance control.

---

## 6. Rollback

Controlled pause:

```sql
update partner_codes
set is_active = false, updated_at = now()
where code = 'S3PILOT1';

update partner_accounts
set status = 'suspended', updated_at = now()
where account_key = 'cybervpn-internal-pilot';
```

Full deletion is allowed only before any customer binding, earning, partner statement or payout instruction references the workspace.

---

## 7. Decision

```text
S3-STAGE-17A_FIRST_PILOT_WORKSPACE_CODE_PROOF_PASSED
```

Next working step:

```text
S3-STAGE-17B: First Partner Code Redemption, Attribution, Reporting, And Settlement Sandbox Proof
```

