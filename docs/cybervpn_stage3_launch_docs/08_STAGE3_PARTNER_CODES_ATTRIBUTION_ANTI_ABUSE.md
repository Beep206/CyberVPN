# Stage 3 Partner Codes, Attribution, And Anti-Abuse

**Stage:** `S3-STAGE-08`
**Status:** Passed for local code/evidence gate
**Date:** 2026-05-24
**Product stage:** CyberVPN Partner / Reseller Platform
**Prior gate:** `S3-STAGE-07: Partner Workspace, Team, And RBAC`

---

## 1. Назначение

S3-STAGE-08 закрывает безопасный контур partner codes и attribution до включения partner/reseller growth в production.

Главная цель этапа: доказать, что партнёрский код можно применить к реальному customer/order flow, результат attribution объясним для support/admin, повторные операции безопасны, а очевидный self-referral уходит в risk/review path.

Этот этап не включает реальные выплаты партнёрам. Payouts, settlement, reserves, clawbacks и finance approval остаются отдельными gated-этапами S3.

---

## 2. Decision

Production default остается закрытым:

```text
PARTNER_PORTAL_ENABLED=false
PARTNER_CODES_ENABLED=false
PARTNER_ATTRIBUTION_ENABLED=false
PARTNER_PAYOUTS_ENABLED=false
PARTNER_STOREFRONTS_ENABLED=false
PARTNER_WEBHOOKS_ENABLED=false
```

Для локального proof включались только тестовые S3 flags:

```text
PARTNER_PORTAL_ENABLED=true
PARTNER_CODES_ENABLED=true
PARTNER_ATTRIBUTION_ENABLED=true
```

`PARTNER_PAYOUTS_ENABLED` не требуется для S3-STAGE-08. Attribution может быть доказан без реальных выплат.

---

## 3. Входит

| Area | S3-STAGE-08 result |
|---|---|
| Partner code lifecycle gate | Partner code create/bind/checkout surfaces закрыты флагом `PARTNER_CODES_ENABLED`. |
| Attribution gate | `/api/v1/attribution/*` закрыт флагом `PARTNER_ATTRIBUTION_ENABLED`. |
| Customer bind | Customer может привязаться к active reseller/partner code. |
| Duplicate bind | Повторная привязка к тому же partner owner/account безопасна и идемпотентна. |
| Self-referral protection | Owner не может применить собственный partner code через checkout code resolution. |
| Abuse queue | Повторные blocked-by-risk resolution events попадают в admin abuse queue. |
| Attribution result | Order получает `owner_type`, `owner_source`, `partner_code_id`, `partner_account_id`, `rule_path`. |
| Explainability | Support/admin видят resolved owner через order explainability. |
| Production safety | Флаги по умолчанию выключены, случайный public rollout не происходит. |

---

## 4. Backend Changes

### 4.1 Runtime flags

Добавлены runtime-флаги:

```text
PARTNER_CODES_ENABLED=false
PARTNER_ATTRIBUTION_ENABLED=false
```

Флаги добавлены в:

```text
backend/src/config/settings.py
backend/.env.example
```

### 4.2 Disabled-state boundary

Обновлен:

```text
backend/src/presentation/middleware/partner_disabled_boundary.py
```

Новые gated route groups:

```text
/api/v1/partner/codes
/api/v1/partner/bind
/api/v1/partner-workspaces/{workspace_id}/codes
/api/v1/partner-workspaces/{workspace_id}/reseller-voucher-batches
/api/v1/attribution/*
```

Правило:

1. partner code surfaces требуют `PARTNER_PORTAL_ENABLED=true` и `PARTNER_CODES_ENABLED=true`;
2. attribution surfaces требуют `PARTNER_ATTRIBUTION_ENABLED=true`;
3. production default возвращает disabled response, а не случайно открывает API.

### 4.3 Self-referral protection

Self-referral теперь блокируется в трех местах:

```text
backend/src/application/use_cases/partners/bind_partner.py
backend/src/application/use_cases/growth_codes/resolve_code.py
backend/src/application/use_cases/payments/checkout.py
```

Проверки учитывают:

1. direct owner: `partner_code.partner_user_id == user.id`;
2. workspace membership: `user.partner_account_id == partner_code.partner_account_id`;
3. legacy owner: `partner_accounts.legacy_owner_user_id == user.id`.

Checkout explicit `partner_code` возвращает user-facing ошибку:

```text
Partner code self-referral is blocked
```

Generic `code_input` resolution возвращает structured result:

```text
result=blocked_by_risk
reject_reason=code_blocked_by_risk
code_type=partner
```

### 4.4 Attribution touchpoints gated

Обновлен:

```text
backend/src/application/use_cases/commerce_sessions/create_quote_session.py
```

`storefront_origin` и `explicit_code` touchpoints записываются только когда:

```text
PARTNER_ATTRIBUTION_ENABLED=true
```

Это важно для staged rollout: quote/checkout остается рабочим, но partner attribution не собирается в production до явного enablement.

---

## 5. Anti-Abuse Boundary

S3-STAGE-08 фиксирует минимальный anti-abuse контракт:

| Risk | Handling |
|---|---|
| Partner owner uses own code | Blocked as `code_blocked_by_risk`. |
| Partner workspace member uses own workspace code | Blocked as self-referral. |
| Legacy owner uses own workspace code | Blocked as self-referral. |
| Duplicate bind to same code | Safe/idempotent. |
| Duplicate attribution resolve | Safe/idempotent, same attribution result returned. |
| Repeated blocked resolution attempts | Visible in admin abuse queue. |

Multi-account/device/IP fraud scoring is not fully enabled in this stage. It remains a later anti-fraud hardening lane before broad partner scale.

---

## 6. Reward And Settlement Boundary

S3-STAGE-08 intentionally does not pay partner rewards.

For this stage:

1. attribution result is persisted and explainable;
2. payout/settlement eligibility remains disabled;
3. refund/chargeback impact is deferred to `S3-STAGE-11: Settlement Sandbox And Payout Policy`;
4. no payout can be generated from S3-STAGE-08 alone while `PARTNER_PAYOUTS_ENABLED=false`.

This is the safe state: attribution can be tested without financial exposure.

---

## 7. Exit Criteria Check

| Exit criterion | Result |
|---|---|
| Partner code works in staging/local proof | Passed through customer bind + checkout + order commit. |
| Duplicate redemption/bind is safe | Passed: duplicate bind to same owner/account returns success. |
| Fraud cases enter review queue | Passed: 3 self-referral attempts produce `code_blocked_by_risk` abuse signal. |
| Attribution result is explainable | Passed: support/admin can read result and order explainability. |
| Production accidental enablement prevented | Passed: middleware blocks code/attribution routes unless flags are enabled. |

---

## 8. Validation

Commands:

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
S3 partner codes/attribution/anti-abuse e2e: 1 passed
Existing order attribution integration: 2 passed
Existing admin abuse queue integration: 1 passed
Disabled-boundary middleware: 13 passed
Ruff targeted check: passed
```

---

## 9. Production Posture

Before any production partner code enablement:

1. keep `PARTNER_CODES_ENABLED=false` until owner approves a limited partner pilot;
2. keep `PARTNER_ATTRIBUTION_ENABLED=false` until staging/public rehearsal proves order attribution;
3. keep `PARTNER_PAYOUTS_ENABLED=false` until settlement sandbox and finance approval are complete;
4. enable partner code rollout only with a kill switch and abuse queue monitoring;
5. confirm support/admin can explain every partner-owned order;
6. confirm refund/chargeback logic before any payout eligibility.

---

## 10. Next Stage

```text
S3-STAGE-09: Reseller Storefront Contract
```
