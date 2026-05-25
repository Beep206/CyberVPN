# S3-STAGE-08 Evidence: Partner Codes, Attribution, And Anti-Abuse

**Date:** 2026-05-24
**Stage:** `S3-STAGE-08`
**Status:** Passed for local code/evidence gate
**Stage document:** `docs/cybervpn_stage3_launch_docs/08_STAGE3_PARTNER_CODES_ATTRIBUTION_ANTI_ABUSE.md`

---

## 1. Summary

S3-STAGE-08 proves the controlled partner code and attribution contract locally:

```text
partner code routes are gated by runtime flags
partner attribution routes are gated by runtime flags
self-referral is blocked as risk
repeated blocked self-referral attempts are visible in admin abuse queue
customer duplicate bind to the same partner code is idempotent
bound reseller attribution survives quote -> checkout -> order commit
order attribution result is stable on duplicate resolve
support/admin explainability shows resolved reseller ownership
```

This does not enable partner payouts, storefronts, webhooks, or real settlement.

---

## 2. Changed Files

```text
backend/.env.example
backend/src/application/use_cases/commerce_sessions/create_quote_session.py
backend/src/application/use_cases/growth_codes/resolve_code.py
backend/src/application/use_cases/partners/bind_partner.py
backend/src/application/use_cases/partners/create_partner_code.py
backend/src/application/use_cases/payments/checkout.py
backend/src/config/settings.py
backend/src/presentation/middleware/partner_disabled_boundary.py
backend/tests/conftest.py
backend/tests/e2e/test_s3_partner_codes_attribution_anti_abuse.py
backend/tests/integration/test_growth_admin_signals.py
backend/tests/unit/presentation/middleware/test_partner_disabled_boundary.py
docs/cybervpn_stage3_launch_docs/08_STAGE3_PARTNER_CODES_ATTRIBUTION_ANTI_ABUSE.md
docs/evidence/releases/s3-stage-08-partner-codes-attribution-anti-abuse-20260524.md
docs/plans/2026-05-23-cybervpn-s3-stage-roadmap-ru.md
```

---

## 3. Proof Matrix

| Proof | Result |
|---|---|
| `PARTNER_CODES_ENABLED=false` hides partner code surfaces | Passed through middleware unit tests |
| `PARTNER_ATTRIBUTION_ENABLED=false` hides attribution surfaces | Passed through middleware unit tests |
| Partner owner cannot resolve own code for checkout | Passed: `blocked_by_risk` |
| Self-referral reject reason is visible | Passed: `code_blocked_by_risk` |
| Repeated self-referral attempts enter abuse queue | Passed: count `3`, severity `danger` |
| Customer can bind to active reseller code | Passed |
| Duplicate bind to same reseller code is safe | Passed |
| Bound reseller code applies to checkout quote | Passed |
| Order attribution resolves to reseller binding | Passed |
| Duplicate attribution resolution is idempotent | Passed |
| Explainability exposes resolved owner/source | Passed |
| Existing attribution happy-path remains intact | Passed |

---

## 4. Commands

```bash
cd backend

SKIP_TEST_DB_BOOTSTRAP=1 .venv/bin/python -m pytest \
  tests/e2e/test_s3_partner_codes_attribution_anti_abuse.py \
  -q --no-cov

SKIP_TEST_DB_BOOTSTRAP=1 .venv/bin/python -m pytest \
  tests/integration/test_order_attribution_resolution.py \
  -q --no-cov

SKIP_TEST_DB_BOOTSTRAP=1 .venv/bin/python -m pytest \
  tests/integration/test_growth_admin_signals.py::test_admin_growth_abuse_queue_returns_resolution_clusters_and_blocked_rewards \
  -q --no-cov

SKIP_TEST_DB_BOOTSTRAP=1 .venv/bin/python -m pytest \
  tests/unit/presentation/middleware/test_partner_disabled_boundary.py \
  -q --no-cov

.venv/bin/python -m ruff check \
  src/application/use_cases/commerce_sessions/create_quote_session.py \
  src/application/use_cases/growth_codes/resolve_code.py \
  src/application/use_cases/partners/bind_partner.py \
  src/application/use_cases/partners/create_partner_code.py \
  src/application/use_cases/payments/checkout.py \
  src/config/settings.py \
  src/presentation/middleware/partner_disabled_boundary.py \
  tests/conftest.py \
  tests/e2e/test_s3_partner_codes_attribution_anti_abuse.py \
  tests/integration/test_growth_admin_signals.py \
  tests/unit/presentation/middleware/test_partner_disabled_boundary.py
```

Observed result:

```text
pytest S3 partner codes/attribution/anti-abuse e2e: 1 passed
pytest existing order attribution integration: 2 passed
pytest existing admin abuse queue integration: 1 passed
pytest disabled-boundary middleware: 13 passed
ruff: All checks passed
```

---

## 5. Production Notes

Production remains disabled by default:

```text
PARTNER_PORTAL_ENABLED=false
PARTNER_CODES_ENABLED=false
PARTNER_ATTRIBUTION_ENABLED=false
PARTNER_PAYOUTS_ENABLED=false
PARTNER_STOREFRONTS_ENABLED=false
PARTNER_WEBHOOKS_ENABLED=false
```

Admin-host protected routes in tests require a local admin host header:

```text
Host: testserver
```

This mirrors the S1/S2 production rule that admin API surfaces are not exposed from normal public hosts.

---

## 6. Residual Boundaries

Not enabled in this stage:

1. real partner payouts;
2. settlement periods;
3. payout account verification;
4. refund/chargeback clawback execution;
5. multi-account/device/IP fraud scoring beyond self-referral and repeated-reject queueing.

These remain gated by later S3 stages.

---

## 7. Next

```text
S3-STAGE-09: Reseller Storefront Contract
```
