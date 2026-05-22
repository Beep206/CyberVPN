# S2 Stage 09 Evidence: Support And Admin Operations

**Stage:** `S2-STAGE-09`
**Date:** 2026-05-22
**Status:** Passed locally with production role gap
**Scope:** CyberVPN Public Release 1.0 support/admin operations

---

## 1. Purpose

This evidence records the S2 support/admin operations baseline.

Goal: support must be able to handle normal public-release issues without raw secrets, raw VPN configs, raw subscription URLs or developer-only database access.

---

## 2. Files Changed

| File | Purpose |
|---|---|
| `backend/src/presentation/api/shared/stage2_support_admin_ops.py` | New side-effect-free S2 support/admin role, lookup, redaction and readiness contract |
| `backend/src/presentation/api/shared/__init__.py` | Exports S2 support/admin contract symbols |
| `backend/src/presentation/api/v1/admin/customer_support.py` | Redacts subscription resync response/audit details |
| `backend/src/presentation/api/v1/admin/customer_support_schemas.py` | Adds `*_present` booleans for subscription resync response |
| `backend/tests/security/test_stage2_support_admin_ops.py` | Security/product-policy tests for S2 support/admin operations |
| `docs/cybervpn_stage2_launch_docs/08_STAGE2_SUPPORT_ADMIN_OPERATIONS.md` | Stage 2 support/admin operations specification |
| `docs/plans/2026-05-22-cybervpn-stage2-public-release-master-plan.md` | Marks `S2-STAGE-09` completed with production role gap |
| `docs/evidence/releases/s2-stage-09-support-admin-ops-20260522.md` | This evidence file |

---

## 3. Support Case Coverage

Covered S2 support cases:

1. cannot login;
2. payment succeeded but no access;
3. VPN does not connect;
4. refund request;
5. subscription expired;
6. referral/promo/gift/autoprolongation issue.

Hard SLA retained:

```text
No paid-but-no-access case may remain unresolved older than 24 hours.
```

Contacts retained:

```text
support@cyber-vpn.net
refund@cyber-vpn.net
abuse@cyber-vpn.net
```

---

## 4. Redaction Evidence

The new S2 redaction contract redacts:

```text
passwords
password hashes
OTP/TOTP material
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

Additional fix:

```text
customer_subscription_resynced no longer returns raw subscription URLs.
```

Response now uses redacted placeholders and presence booleans:

```text
previous_subscription_url=[REDACTED]
stored_subscription_url=[REDACTED]
upstream_subscription_url=[REDACTED]
previous_subscription_url_present=true
stored_subscription_url_present=true
upstream_subscription_url_present=true
```

Audit details store presence booleans rather than raw URLs.

---

## 5. Production Runtime Preflight

Command:

```bash
ssh prod-app-1 'hostname; docker ps; curl https://api.cyber-vpn.net/health; curl -I https://admin.cyber-vpn.net'
```

Observed:

```text
prod-app-1
frontend: healthy
backend: healthy
telegram-bot: healthy
Remnawave: healthy
Remnawave PostgreSQL: healthy
Remnawave Valkey: healthy
scheduler: healthy
worker: healthy
admin: healthy
PostgreSQL exporter: healthy
Redis exporter: healthy
CyberVPN PostgreSQL: healthy
CyberVPN Valkey: healthy
```

Public probes:

```text
https://api.cyber-vpn.net/health -> {"status":"ok"}
https://admin.cyber-vpn.net -> HTTP/2 307
alt-svc: h3=":443"
```

HTTP/3/QUIC remains advertised and must not be disabled.

---

## 6. Production DB Preflight

Observed support/admin-related tables:

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

Observed counts:

```text
admin_users|2
audit_logs|3
mobile_users|4
payments|0
payment_attempts|0
payment_disputes|0
support_profiles|1
```

Observed admin role/2FA summary:

```text
viewer|active=true|totp_enabled=false|2
```

Interpretation:

1. production runtime and DB support/admin surfaces exist;
2. no privileged production support/admin role is currently proven;
3. privileged production users must be created/promoted and protected with 2FA before unrestricted S2 public opening.

---

## 7. Test Evidence

Lint:

```bash
cd backend
uv run ruff check \
  src/presentation/api/shared/stage2_support_admin_ops.py \
  src/presentation/api/shared/__init__.py \
  src/presentation/api/v1/admin/customer_support.py \
  src/presentation/api/v1/admin/customer_support_schemas.py \
  tests/security/test_stage2_support_admin_ops.py
```

Result:

```text
All checks passed
```

Security/admin tests:

```bash
cd backend
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

DB-backed integration test attempted:

```bash
cd backend
uv run pytest tests/integration/test_admin_customer_operations_insight.py -q --no-cov
```

Result:

```text
4 failed
pytest test DB bootstrap skipped: [Errno 111] Connect call failed ('127.0.0.1', 6767)
```

Interpretation:

The local integration test requires an intentional local PostgreSQL test DB. Docker/test DB was not running during this stage. Repeat this proof when local Docker/test DB is deliberately started.

---

## 8. Security Review Notes

Positive findings:

1. S2 support/admin contract is side-effect free.
2. Support case routing is explicit.
3. Paid-but-no-access keeps the 24h hard rule.
4. Manual support grants remain outside support role.
5. Financial refund review remains finance/admin+.
6. Dangerous support actions require audit.
7. Subscription resync output no longer exposes raw URLs.

Residual risks:

1. production privileged support/admin account is not yet present;
2. production privileged admin 2FA evidence is not yet present;
3. DB-backed admin operations integration proof must be rerun with local/staging DB;
4. growth/autoprolongation support reversal is documented but must be rechecked when those gates are enabled.

---

## 9. Decision

`S2-STAGE-09` is closed for local code/docs/test baseline.

Do not treat it as approval for unrestricted S2 opening until:

1. privileged production support/admin roles are configured;
2. 2FA is enabled;
3. DB-backed operations insight proof is rerun;
4. redacted support workflow evidence is captured with a real internal support/admin operator.
