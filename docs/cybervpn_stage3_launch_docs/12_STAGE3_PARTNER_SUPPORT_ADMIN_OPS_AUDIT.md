# Stage 3 Partner Support, Admin Ops, And Audit

**Stage:** `S3-STAGE-12`
**Status:** Passed for local code/evidence gate
**Date:** 2026-05-25
**Product stage:** CyberVPN Partner / Reseller Platform
**Prior gate:** `S3-STAGE-11: Settlement Sandbox And Payout Policy`

---

## 1. Назначение

S3-STAGE-12 закрывает операционный слой для партнёров: support, finance и admin должны сопровождать partner/reseller flows через backend/admin API, без shell-доступа к production и без ручного изменения данных в базе.

Цель этапа: дать внутренним ролям безопасный обзор partner workspace, очередь finance review, базовые admin actions и audit trail для чувствительных действий.

Этот этап не включает реальные выплаты и не открывает partner portal для публичного production-пилота.

---

## 2. Decision

S3-STAGE-12 фиксирует следующий operational contract:

```text
support: может диагностировать partner workspace и видеть операционный обзор
finance: может читать payout review queue
admin: может менять status workspace и отключать partner code
manual grant/revoke: только через отдельный customer/support flow, не через partner ops endpoint
live payouts: disabled
all sensitive admin operations: audit/workflow event required
```

Production defaults остаются консервативными:

```text
PARTNER_PORTAL_ENABLED=false
PARTNER_PAYOUTS_ENABLED=false
PARTNER_SETTLEMENT_SANDBOX_ENABLED=false
```

Даже если read-only support/admin surfaces включаются позже, реальные payout actions остаются заблокированы до S3-STAGE-14, S3-STAGE-15 и S3-STAGE-17.

---

## 3. Входит

| Area | S3-STAGE-12 result |
|---|---|
| Partner support cases | Existing workspace cases are surfaced in admin ops overview. |
| Admin partner overview | Added internal admin overview endpoint for support/operator/admin diagnostics. |
| Workspace freeze/unfreeze | Existing status route now writes audit/workflow event. |
| Code disable | Added admin-only partner code status endpoint with audit/workflow event. |
| Manual grant/revoke | Explicitly marked as deferred to customer support flow, not partner ops. |
| Payout review queue | Added finance-only queue based on partner cases, payout history and settlement sandbox signals. |
| Escalation path | Response declares support, finance, admin and technical ops handoff. |
| Audit | Sensitive actions produce workflow events with stage marker `S3-STAGE-12`. |

---

## 4. Backend Changes

### 4.1 Admin ops overview

Added:

```http
GET /api/v1/admin/partner-workspaces/{workspace_id}/ops-overview
```

Access:

```text
support/operator/admin/super_admin
```

The endpoint returns:

```text
workspace
open_cases
waiting_on_ops_cases
payout_review_items
recent_review_requests
recent_audit_events
admin_actions
escalation_path
redaction_notes
```

The endpoint is diagnostic. It does not mutate workspace state and does not expose raw payment provider payloads.

### 4.2 Finance payout review queue

Added:

```http
GET /api/v1/admin/partner-workspaces/{workspace_id}/payout-review-queue
```

Access:

```text
finance/admin/super_admin
```

The queue includes:

```text
finance_onboarding cases
payout_dispute cases
statement_question cases
payout history items requiring attention
settlement sandbox blocks such as stage_blocks_live_payout
```

Support role is intentionally denied for this route.

### 4.3 Workspace status audit

Existing route:

```http
PATCH /api/v1/admin/partner-workspaces/{workspace_id}/status
```

now writes a workflow/audit event:

```text
subject_kind=admin_ops
action=workspace_status_changed
payload.old_status
payload.new_status
payload.reason
payload.stage=S3-STAGE-12
```

This covers workspace freeze/unfreeze/suspension actions.

### 4.4 Partner code status audit

Added:

```http
PATCH /api/v1/admin/partner-workspaces/{workspace_id}/codes/{code_id}/status
```

Access:

```text
admin/super_admin
```

The endpoint:

1. verifies that `code_id` belongs to `workspace_id`;
2. changes `is_active`;
3. writes a workflow/audit event:

```text
subject_kind=partner_code
action=partner_code_status_changed
payload.old_is_active
payload.new_is_active
payload.reason
payload.stage=S3-STAGE-12
```

---

## 5. Role Boundary

| Operation | Support | Finance | Admin |
|---|---:|---:|---:|
| Read partner ops overview | Yes | No by default | Yes |
| Read payout review queue | No | Yes | Yes |
| Freeze/unfreeze workspace | No | No | Yes |
| Disable/enable partner code | No | No | Yes |
| Manual user grant/revoke | Deferred | Deferred | Deferred |
| Execute live payout | No | No | No in S3-STAGE-12 |

`manual_grant_revoke` is visible as an admin action but marked:

```text
status=deferred_to_customer_support_flow
stage_dependency=S2 support/customer grant flow
```

This avoids adding a second entitlement/grant path inside partner ops.

---

## 6. Redaction And Privacy

Admin ops overview declares redaction notes:

```text
Raw payment provider payloads are not exposed in partner ops overview.
Customer VPN subscription URLs are not exposed in partner ops overview.
Partner payout account secrets are not exposed in partner ops overview.
```

The endpoint may include operational IDs, case IDs and masked partner/user labels, but it must not expose:

- raw provider webhook payloads;
- full payment credentials;
- VPN subscription URLs;
- partner payout account secrets;
- raw customer private data not required for support diagnosis.

---

## 7. Exit Criteria Check

| Exit criterion | Result |
|---|---|
| Support can diagnose partner issue | Passed locally through admin ops overview route. |
| Finance actions require correct role | Passed: finance queue allows finance, denies support. |
| Audit log covers sensitive actions | Passed: workspace status and code status changes produce workflow events. |
| Code disable exists without shell access | Passed locally through admin-only code status route. |
| Workspace freeze/unfreeze exists without shell access | Passed locally through audited workspace status route. |
| Live payouts remain blocked | Passed by S3-STAGE-11 policy and S3-STAGE-12 queue-only design. |
| Manual grant/revoke does not create hidden entitlement path | Passed: action is deferred to existing support/customer flow. |

---

## 8. Validation

Commands:

```bash
cd backend

.venv/bin/python -m py_compile \
  src/presentation/api/v1/partners/routes.py \
  src/presentation/api/v1/partners/schemas.py \
  tests/integration/test_partner_portal_reporting_reads.py \
  tests/contract/test_partner_statement_openapi_contract.py

.venv/bin/python -m ruff check \
  src/presentation/api/v1/partners/routes.py \
  src/presentation/api/v1/partners/schemas.py \
  tests/integration/test_partner_portal_reporting_reads.py \
  tests/contract/test_partner_statement_openapi_contract.py

.venv/bin/python -m pytest \
  tests/contract/test_partner_statement_openapi_contract.py \
  -q --no-cov

.venv/bin/python -m pytest \
  tests/integration/test_partner_portal_reporting_reads.py::test_partner_workspace_reporting_and_cases_are_visible_to_workspace_members \
  -q --no-cov
```

Observed result:

```text
py_compile: passed
ruff: All checks passed
pytest OpenAPI contract: 1 passed
pytest partner reporting/support/admin ops integration: 1 passed
```

---

## 9. Production Notes

Before production pilot:

1. keep partner portal/storefront/payout kill switches disabled unless the matching S3 gate explicitly enables them;
2. verify that real admin users have 2FA enabled;
3. verify that support and finance roles are assigned to named users only;
4. confirm audit event visibility in admin logs or Grafana/Loki during S3-STAGE-13;
5. keep live payouts disabled until controlled partner pilot approval.

---

## 10. Next

```text
S3-STAGE-13: Partner Observability And Alerting
```
