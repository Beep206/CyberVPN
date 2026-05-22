# Stage 2 Support And Admin Operations

**Stage:** `S2-STAGE-09`
**Status:** Approved with owner-operated production admin/2FA proof
**Date:** 2026-05-22
**Product stage:** CyberVPN Public Release 1.0

---

## 1. Purpose

This document freezes the S2 support/admin operations contract.

S2 support must not depend on developer-only database access. A support/admin operator must be able to diagnose common public-release issues from protected admin surfaces, with audit logs and redacted outputs.

---

## 2. Required Support Cases

| Case | Priority | Required lookups | Contact | Queue |
|---|---:|---|---|---|
| Cannot login | `P1` | customer, auth diagnostics, audit timeline | `support@cyber-vpn.net` | `s2_auth_support_review` |
| Payment succeeded but no access | `P0` | customer, payment, subscription, provisioning, audit timeline | `support@cyber-vpn.net` | `s2_paid_no_access_review` |
| VPN does not connect | `P1` | customer, subscription, provisioning, audit timeline | `support@cyber-vpn.net` | `s2_vpn_connectivity_support` |
| Refund request | `P1` | customer, payment, refund/dispute, audit timeline | `refund@cyber-vpn.net` | `s2_payment_finance_review` |
| Subscription expired | `P2` | customer, payment, subscription, audit timeline | `support@cyber-vpn.net` | `s2_customer_support` |
| Referral/promo/gift/autoprolongation issue | `P1` | customer, payment, growth/reward, audit timeline | `support@cyber-vpn.net` | `s2_growth_billing_support` |

Hard rule:

```text
No paid-but-no-access case may remain unresolved older than 24 hours.
```

---

## 3. Role Contract

| Action | Support | Finance | Operator | Admin+ |
|---|---:|---:|---:|---:|
| Read customer diagnostics | yes | yes | yes | yes |
| Create ticket / staff note | yes | yes | yes | yes |
| Payment reconciliation review | no | yes | no | yes |
| Refund review | no | yes | no | yes |
| Manual support grant | no | no | yes | yes |
| Reprovision/resync | yes, audited | no | yes, audited | yes, audited |
| VPN credential regeneration | yes, audited | no | no | yes, audited |
| Account recovery | yes, audited | no | no | yes, audited |
| Growth reward reversal | no | no | no | yes, audited |

The existing S1 RBAC allows support to run some recovery actions. For S2 this is acceptable only when:

1. action requires authenticated admin access;
2. action writes an audit log;
3. output is redacted;
4. reason/context is captured where the endpoint supports it;
5. support does not execute financial state changes or manual grants.

---

## 4. Redaction Contract

Support/admin outputs must not expose:

```text
password
password_hash
OTP/TOTP secrets or codes
access/refresh tokens
Telegram init data
provider secrets/tokens
webhook signatures
raw provider payloads
raw subscription URLs
raw vless:// configs
private keys / seed phrases
full payment instrument data
```

S2 implementation adds a side-effect-free support/admin contract:

```text
backend/src/presentation/api/shared/stage2_support_admin_ops.py
```

It also tightens `customer_subscription_resynced` output:

1. raw subscription URLs are not returned to admin/support responses;
2. response contains redacted values plus `*_present` booleans;
3. audit details store presence booleans instead of raw URLs.

---

## 5. Existing Runtime Surfaces

| Surface | Current path / source | S2 state |
|---|---|---|
| Customer lookup | `GET /api/v1/admin/mobile-users` and mobile-user admin routes | Exists |
| Customer timeline | `GET /api/v1/admin/mobile-users/{user_id}/timeline` | Exists |
| VPN user lookup | `GET /api/v1/admin/mobile-users/{user_id}/vpn-user` | Exists |
| Subscription resync | `POST /api/v1/admin/mobile-users/{user_id}/subscription/resync` | Exists, now redacted |
| Manual support grant | `POST /api/v1/admin/mobile-users/{user_id}/subscription/manual-grant` | Exists, audited, not support role |
| Credential regeneration | `POST /api/v1/admin/mobile-users/{user_id}/vpn-user/regenerate-credentials` | Exists, audited |
| Staff notes | `GET/POST /api/v1/admin/mobile-users/{user_id}/notes` | Exists, audited on create |
| Payment/order/settlement insight | `GET /api/v1/admin/mobile-users/{user_id}/operations-insight` | Exists |
| Audit log | `audit_logs` table and admin audit routes | Exists |
| Support profile | `support_profiles` table | Exists |

---

## 6. Production Preflight On 2026-05-22

Production app runtime is healthy:

```text
prod-app-1
frontend: healthy
backend: healthy
telegram-bot: healthy
Remnawave: healthy
scheduler/worker: healthy
admin: healthy
PostgreSQL/Valkey/exporters: healthy
```

Public probes:

```text
https://api.cyber-vpn.net/health -> {"status":"ok"}
https://admin.cyber-vpn.net -> HTTP/2 307 to /ru-RU, alt-svc h3 present
```

Database support/admin tables observed:

```text
admin_users
audit_logs
customer_staff_notes
dispute_cases
mobile_users
notification_queue
payment_attempts
payment_disputes
payments
support_profiles
```

Counts observed:

```text
admin_users=2
audit_logs=3
mobile_users=4
payments=0
payment_attempts=0
payment_disputes=0
support_profiles=1
```

Original role gap:

```text
admin_users role summary: viewer=2, active=true, totp_enabled=false
```

Production now has one minimal privileged owner-operated account for S2 handoff:

```text
login: s2_admin_ops
role: admin
totp_enabled: true
handoff: /root/cybervpn-admin-handoff/s2-admin-ops-20260522T173735Z.secret.json
```

The handoff file is root-only on `prod-app-1` and contains the temporary password, TOTP secret and setup URI. These values must not be copied into repository docs or chat.

Production proof:

```text
login_status=200
login_requires_2fa=true
2fa_complete_status=200
auth_realm_key=admin
principal_type=admin
admin_mobile_users_status=200
logout_status=204
```

Post-change role summary:

```text
admin|active=true|totp_enabled=true|1
viewer|active=true|totp_enabled=false|2
```

This closes the immediate owner-operated S2 admin access gap without creating unnecessary generic support/finance/operator accounts. Before a broader unrestricted S2 opening with more operators, replace this with named human `support`, `finance`, `operator` and `admin` accounts, each with individual 2FA.

---

## 7. Tests

Passed:

```text
cd backend
uv run ruff check \
  src/presentation/api/shared/stage2_support_admin_ops.py \
  src/presentation/api/shared/__init__.py \
  src/presentation/api/v1/admin/customer_support.py \
  src/presentation/api/v1/admin/customer_support_schemas.py \
  tests/security/test_stage2_support_admin_ops.py

uv run pytest \
  tests/security/test_stage2_support_admin_ops.py \
  tests/security/test_stage1_support_templates.py \
  tests/security/test_stage1_support_ticket_path.py \
  tests/security/test_stage1_support_escalation.py \
  tests/security/test_stage1_admin_rbac_matrix.py \
  tests/security/test_stage1_admin_manual_subscription_ops.py \
  tests/security/test_stage1_admin_audit_log.py \
  -q --no-cov
```

Result:

```text
59 passed
```

DB-backed admin operations integration proof:

```text
tests/integration/test_admin_customer_operations_insight.py
```

Result after starting local Docker PostgreSQL/Valkey:

```text
4 passed in 50.73s
```

Fix applied:

```text
The test now sends Host: admin.cyber-vpn.net for admin-only routes, matching AdminHostGuardMiddleware instead of using the generic http://test host.
```

---

## 8. No-Go Conditions

Do not widen S2 public release if any condition is true:

1. no privileged support/admin operator exists in production;
2. admin 2FA is not enabled for privileged users;
3. support cannot view customer/payment/subscription/provisioning timeline without developer database access;
4. manual grants or reprovisioning actions are not audited;
5. raw subscription URLs or raw `vless://` configs appear in support/admin outputs;
6. paid-but-no-access items can remain unresolved older than 24 hours;
7. refund/growth/autoprolongation support reversals require developer-only SQL.

---

## 9. Exit Decision

`S2-STAGE-09` is closed for the local S2 support/admin contract, redaction baseline, production owner-operated privileged admin proof and DB-backed operations-insight proof.

Remaining S2 scale-up requirement:

1. create/promote named human support/admin/finance/operator accounts when separate people exist;
2. enable mandatory 2FA for each account;
3. rotate the temporary `s2_admin_ops` password after owner handoff;
4. capture redacted evidence that a support/admin operator can diagnose a user without developer-only DB access.
