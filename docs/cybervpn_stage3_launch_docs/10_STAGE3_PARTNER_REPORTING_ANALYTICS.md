# Stage 3 Partner Reporting And Analytics

**Stage:** `S3-STAGE-10`
**Status:** Passed for local code/evidence gate
**Date:** 2026-05-25
**Product stage:** CyberVPN Partner / Reseller Platform
**Prior gate:** `S3-STAGE-09: Reseller Storefront Contract`

---

## 1. Назначение

S3-STAGE-10 фиксирует partner reporting contract до settlement sandbox и controlled partner pilot.

Цель этапа: дать партнёру и внутренним операторам объяснимые workspace-scoped отчёты, не раскрывать чужие workspace данные, минимизировать PII в ответах и явно показывать, какие метрики являются source-of-truth, а какие ещё не готовы как финальный отчёт.

Этот этап не включает реальные partner payouts.

---

## 2. Decision

Production default остается закрытым:

```text
PARTNER_REPORTING_ENABLED=false
```

Reporting surfaces открываются только когда включены оба флага:

```text
PARTNER_PORTAL_ENABLED=true
PARTNER_REPORTING_ENABLED=true
```

При выключенном reporting middleware возвращает disabled-state:

```json
{
  "detail": {
    "code": "partner_reporting_disabled",
    "message": "Partner reporting is not enabled for this release.",
    "stage": "S3-STAGE-10"
  }
}
```

---

## 3. Входит

| Area | S3-STAGE-10 result |
|---|---|
| Partner dashboard | Existing analytics metrics now carry source/redaction flags. |
| Conversions | Conversion records remain workspace-scoped and customer labels stay masked. |
| Active users | Added `active_users` as paid-user activity proxy with explicit source note. |
| Trials | Marked `trial_users=not_available` because partner trial attribution is not a canonical mart yet. |
| Paid users | Added unique paid-user metric without exposing raw user identifiers. |
| Refund/chargeback impact | Summary includes refund and chargeback counts from canonical reporting mart. |
| Attribution explanation | Existing conversion explainability remains workspace-scoped. |
| Export sandbox | Export definitions now expose redaction policy and excluded PII fields. |
| Report reconciliation | Added reporting summary with reconciliation status and mismatch counts. |

---

## 4. Backend Changes

### 4.1 Kill switch

Added setting:

```text
PARTNER_REPORTING_ENABLED=false
```

Files:

```text
backend/src/config/settings.py
backend/.env.example
backend/src/presentation/middleware/partner_disabled_boundary.py
```

Protected surfaces:

```text
/api/v1/reporting/partner-workspaces/*
/api/v1/partner-workspaces/{workspace_id}/statements
/api/v1/partner-workspaces/{workspace_id}/conversion-records
/api/v1/partner-workspaces/{workspace_id}/analytics-metrics
/api/v1/partner-workspaces/{workspace_id}/reporting-summary
/api/v1/partner-workspaces/{workspace_id}/report-exports
```

### 4.2 Reporting summary endpoint

Added:

```http
GET /api/v1/partner-workspaces/{workspace_id}/reporting-summary
```

The endpoint returns:

```text
workspace_id
generated_at
report_version
metrics
reconciliation
export_redaction
source_of_truth_notes
```

It requires:

```text
earnings_read
```

and uses the existing partner workspace access dependency, so outsiders do not see another workspace report.

### 4.3 Source-of-truth notes

The reporting summary explicitly distinguishes:

```text
orders / attribution / renewal lineage / refunds / disputes -> conversion metrics
earning events / partner statements -> earnings metrics
outbox consumer health -> freshness and replay risk
trial attribution -> not available in S3-STAGE-10
```

This avoids presenting trial numbers as reliable when the backend does not yet have a canonical partner trial mart.

### 4.4 Export redaction

Partner exports expose a redaction contract:

```text
policy=redacted_partner_export
```

Excluded fields:

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

Masked fields:

```text
customer_label
geo
source
```

---

## 5. Access Isolation

S3-STAGE-10 keeps the existing workspace isolation rule:

```text
partner workspace member must have earnings_read for analytics/reporting
outsider receives 403
admin/internal override remains explicit through existing admin roles
```

The integration proof verifies outsider denial for:

```text
conversion-records
conversion-record explainability
analytics-metrics
reporting-summary
report-exports
```

---

## 6. Exit Criteria Check

| Exit criterion | Result |
|---|---|
| Reports match backend/admin truth | Passed locally through reporting mart summary and reconciliation status. |
| Access isolation proven | Passed: outsider receives 403 for workspace reporting surfaces. |
| Export redaction works | Passed: API exposes redaction policy and excluded PII fields. |
| Refund/chargeback impact visible | Passed: summary includes refund and chargeback counts. |
| Attribution explanation available | Passed: existing workspace conversion explainability remains scoped. |
| Trial metric honesty | Passed: trial users are explicitly marked `not_available` until canonical mart exists. |

---

## 7. Validation

Commands:

```bash
cd backend

SKIP_TEST_DB_BOOTSTRAP=1 .venv/bin/python -m pytest \
  tests/unit/presentation/middleware/test_partner_disabled_boundary.py \
  -q --no-cov

.venv/bin/python -m pytest \
  tests/contract/test_partner_statement_openapi_contract.py \
  -q --no-cov

.venv/bin/python -m pytest \
  tests/integration/test_partner_portal_reporting_reads.py::test_partner_workspace_reporting_and_cases_are_visible_to_workspace_members \
  -q --no-cov

.venv/bin/python -m ruff check \
  src/config/settings.py \
  src/presentation/middleware/partner_disabled_boundary.py \
  src/presentation/api/v1/partners/routes.py \
  src/presentation/api/v1/partners/schemas.py \
  tests/conftest.py \
  tests/unit/presentation/middleware/test_partner_disabled_boundary.py \
  tests/integration/test_partner_portal_reporting_reads.py \
  tests/contract/test_partner_statement_openapi_contract.py
```

Observed result:

```text
Disabled-boundary middleware: 19 passed
OpenAPI contract: 1 passed
Partner reporting integration: 1 passed
Ruff targeted check: passed
git diff --check: passed
S3-10 secret scan: no matches
S3-10 dangerous pattern scan: no matches
npm audit --audit-level=high: passed; 5 moderate advisories remain outside this S3-10 gate
```

---

## 8. Production Posture

Before production reporting enablement:

1. keep `PARTNER_REPORTING_ENABLED=false`;
2. complete `S3-STAGE-11` settlement sandbox;
3. complete `S3-STAGE-13` partner observability and alerting;
4. complete `S3-STAGE-15` full staging rehearsal;
5. validate that report exports contain no raw customer/payment/VPN config PII;
6. validate reporting freshness and outbox backlog alerts.

---

## 9. Next Stage

```text
S3-STAGE-11: Settlement Sandbox And Payout Policy
```
