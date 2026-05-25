# Stage 3 First Pilot Partner Workspace And Code Proof

**Stage:** `S3-STAGE-17A`
**Status:** Passed
**Date:** 2026-05-25
**Parent stage:** `S3-STAGE-17: Controlled Partner Pilot`
**Runtime tag:** `s3-stage17-controlled-partner-pilot.3`

---

## 1. Purpose

`S3-STAGE-17A` creates the first controlled pilot partner workspace and proves that the production partner runtime can operate real workspace and code data without reopening broad partner expansion.

This stage is intentionally narrow:

1. create one internal pilot workspace;
2. attach one trusted operator;
3. attach one existing mobile owner;
4. create one active partner code;
5. prove partner workspace/session/code APIs;
6. keep payout execution manual and controlled;
7. keep broader partner cohort expansion pending.

---

## 2. Pilot Objects

Production pilot workspace:

```text
account_key=cybervpn-internal-pilot
display_name=CyberVPN Internal Partner Pilot
status=active
```

Pilot mobile owner:

```text
telegram_username=Sasha_Beep
owner_type=internal pilot owner
```

Pilot operator:

```text
login=s2_admin_ops
role=owner
2FA=true
```

Pilot code:

```text
code=S3PILOT1
markup_pct=0
is_active=true
partner_account=cybervpn-internal-pilot
```

The code is a controlled pilot code, not a broad public acquisition code.

---

## 3. Production Proof

The workspace was created through the admin API:

```text
POST /api/v1/admin/partner-workspaces -> 201
```

The partner code was created through the mobile partner API:

```text
POST /api/v1/partner/codes -> 201
```

Partner operator workspace proof:

```text
GET /api/v1/partner-workspaces/me
X-Auth-Realm: partner
HTTP 200
workspace_count=1
```

Partner session proof:

```text
GET /api/v1/partner-session/bootstrap?workspace_id=<workspace_id>
X-Auth-Realm: partner
HTTP 200
active_workspace_key=cybervpn-internal-pilot
workspace_count=1
```

Mobile owner code proof:

```text
GET /api/v1/partner/codes
HTTP 200
codes=["S3PILOT1"]
```

Mobile partner dashboard proof:

```text
GET /api/v1/partner/dashboard
HTTP 200
code_count=1
```

Database proof:

```text
partner_accounts=1
partner_account_users=1
partner_codes=1
s3_workspace=cybervpn-internal-pilot:active
s3_code=S3PILOT1:true
outbox_pending=0
```

---

## 4. Boundaries

This stage does not approve:

1. adding external partners without owner approval;
2. automatic external payouts;
3. broad public partner marketing;
4. public reseller storefront traffic expansion;
5. disabling manual finance review;
6. skipping S3 stabilization snapshots.

`PARTNER_PAYOUTS_ENABLED=true` still means admin/manual payout workflow surface only. It does not mean automatic payout execution.

---

## 5. Rollback Or Pause

Preferred controlled pause:

```sql
update partner_codes
set is_active = false, updated_at = now()
where code = 'S3PILOT1';

update partner_accounts
set status = 'suspended', updated_at = now()
where account_key = 'cybervpn-internal-pilot';
```

Full deletion is allowed only before any real customer attribution, earning, payout, support case or settlement evidence depends on this workspace.

If a hard rollback is needed before any real traffic:

```sql
delete from partner_codes
where code = 'S3PILOT1';

delete from partner_account_users
where partner_account_id = (
  select id from partner_accounts where account_key = 'cybervpn-internal-pilot'
);

delete from partner_accounts
where account_key = 'cybervpn-internal-pilot';

update mobile_users
set is_partner = false,
    partner_account_id = null,
    partner_promoted_at = null,
    updated_at = now()
where telegram_username = 'Sasha_Beep';
```

Before full deletion, check:

```sql
select count(*) from customer_commercial_bindings where partner_account_id = '<workspace_id>';
select count(*) from partner_earnings where partner_account_id = '<workspace_id>';
select count(*) from partner_statements where partner_account_id = '<workspace_id>';
select count(*) from payout_instructions where partner_account_id = '<workspace_id>';
```

---

## 6. Exit Decision

```text
S3-STAGE-17A_FIRST_PILOT_WORKSPACE_CODE_PROOF_PASSED
```

Remaining controlled pilot work:

```text
S3-STAGE-17B: First Partner Code Redemption, Attribution, Reporting, And Settlement Sandbox Proof
```

