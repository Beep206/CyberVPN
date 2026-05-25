# S3-STAGE-12 Evidence: Partner Support, Admin Ops, And Audit

**Date:** 2026-05-25
**Stage:** `S3-STAGE-12`
**Status:** Passed for local code/evidence gate
**Stage document:** `docs/cybervpn_stage3_launch_docs/12_STAGE3_PARTNER_SUPPORT_ADMIN_OPS_AUDIT.md`

---

## 1. Summary

S3-STAGE-12 proves the partner support/admin operations contract locally:

```text
support can read partner workspace ops overview
finance can read payout review queue
support cannot read finance-only payout review queue
admin can disable partner code without shell/database access
admin can freeze workspace without shell/database access
workspace status change writes audit/workflow event
partner code status change writes audit/workflow event
ops overview exposes escalation path and redaction notes
manual grant/revoke is deferred to existing support/customer flow
live payouts remain disabled
OpenAPI exposes the new admin/support contract
```

This does not enable public partner portal access, real payouts, mass payout export, or uncontrolled partner storefronts.

---

## 2. Changed Files

```text
backend/src/presentation/api/v1/partners/routes.py
backend/src/presentation/api/v1/partners/schemas.py
backend/tests/integration/test_partner_portal_reporting_reads.py
backend/tests/contract/test_partner_statement_openapi_contract.py
docs/cybervpn_stage3_launch_docs/12_STAGE3_PARTNER_SUPPORT_ADMIN_OPS_AUDIT.md
docs/evidence/releases/s3-stage-12-partner-support-admin-ops-audit-20260525.md
docs/plans/2026-05-23-cybervpn-s3-stage-roadmap-ru.md
```

---

## 3. Proof Matrix

| Proof | Result |
|---|---|
| OpenAPI exposes admin partner ops overview route | Passed |
| OpenAPI exposes finance payout review queue route | Passed |
| OpenAPI exposes partner code status route | Passed |
| Support user can read ops overview | Passed |
| Ops overview includes open partner cases | Passed |
| Ops overview includes waiting-on-ops partner cases | Passed |
| Ops overview includes payout review items | Passed |
| Ops overview includes admin actions | Passed |
| Ops overview includes redaction notes | Passed |
| Finance user can read payout review queue | Passed |
| Support user is denied from payout review queue | Passed |
| Admin user can disable partner code | Passed |
| Admin user can freeze workspace | Passed |
| Frozen workspace changes admin actions from freeze to unfreeze | Passed |
| Workspace status change appears in recent audit events | Passed |
| Partner code status change appears in recent audit events | Passed |

---

## 4. Commands

```bash
cd backend

.venv/bin/python -m py_compile \
  src/presentation/api/v1/partners/routes.py \
  src/presentation/api/v1/partners/schemas.py \
  tests/integration/test_partner_portal_reporting_reads.py \
  tests/contract/test_partner_statement_openapi_contract.py

.venv/bin/python -m ruff check --fix \
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

## 5. Access Model Proven

| Route | Required internal role | Result |
|---|---|---|
| `GET /api/v1/admin/partner-workspaces/{workspace_id}/ops-overview` | support/operator/admin | Support accepted |
| `GET /api/v1/admin/partner-workspaces/{workspace_id}/payout-review-queue` | finance/admin | Finance accepted |
| `GET /api/v1/admin/partner-workspaces/{workspace_id}/payout-review-queue` | finance/admin | Support denied |
| `PATCH /api/v1/admin/partner-workspaces/{workspace_id}/codes/{code_id}/status` | admin | Admin accepted |
| `PATCH /api/v1/admin/partner-workspaces/{workspace_id}/status` | admin | Admin accepted |

---

## 6. Audit Events Proven

Expected audit/workflow actions:

```text
partner_code_status_changed
workspace_status_changed
```

Expected payload markers:

```text
stage=S3-STAGE-12
reason=<admin supplied reason>
old/new status or old/new active state
```

Integration proof confirms both events are visible through `recent_audit_events` in the admin ops overview after mutation.

---

## 7. Security And Privacy Notes

S3-STAGE-12 keeps the following boundaries:

```text
support overview is diagnostic and read-only
finance queue is separated from support access
admin-only mutation routes write audit events
raw payment payloads are not returned
VPN subscription URLs are not returned
payout secrets are not returned
manual grant/revoke remains deferred to customer support flow
live payouts remain disabled
```

---

## 8. Production Notes

Production partner operations must remain conservative until later gates:

```text
PARTNER_PORTAL_ENABLED=false unless explicitly enabled for controlled pilot
PARTNER_PAYOUTS_ENABLED=false
PARTNER_SETTLEMENT_SANDBOX_ENABLED=false unless finance read-only review is approved
```

Before S3 production pilot:

1. verify named support/finance/admin users and 2FA;
2. verify audit event visibility in observability during S3-STAGE-13;
3. verify escalation path and owner contacts;
4. keep live payouts disabled until controlled partner pilot approval.

---

## 9. Next

```text
S3-STAGE-13: Partner Observability And Alerting
```
