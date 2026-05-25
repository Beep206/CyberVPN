# S3-STAGE-11 Evidence: Settlement Sandbox And Payout Policy

**Date:** 2026-05-25
**Stage:** `S3-STAGE-11`
**Status:** Passed for local code/evidence gate
**Stage document:** `docs/cybervpn_stage3_launch_docs/11_STAGE3_SETTLEMENT_SANDBOX_PAYOUT_POLICY.md`

---

## 1. Summary

S3-STAGE-11 proves the settlement sandbox and payout policy contract locally:

```text
settlement sandbox has a dedicated disabled-state flag
sandbox route stays hidden until PARTNER_SETTLEMENT_SANDBOX_ENABLED=true
real payout routes remain controlled by PARTNER_PAYOUTS_ENABLED=false
workspace-scoped sandbox exposes statement, hold, reserve and adjustment amounts
refund and chargeback impact is visible from reporting mart data
payout eligibility explains why payout cannot proceed
live payouts are always blocked in S3-STAGE-11
payout export is disabled by policy
OpenAPI exposes the settlement sandbox contract
outsider workspace access is denied
```

This does not enable production settlement, payout export, partner withdrawal, or live payout execution.

---

## 2. Changed Files

```text
backend/.env.example
backend/src/config/settings.py
backend/src/presentation/middleware/partner_disabled_boundary.py
backend/src/presentation/api/v1/partners/routes.py
backend/src/presentation/api/v1/partners/schemas.py
backend/tests/unit/presentation/middleware/test_partner_disabled_boundary.py
backend/tests/integration/test_partner_portal_reporting_reads.py
backend/tests/contract/test_partner_statement_openapi_contract.py
docs/cybervpn_stage3_launch_docs/11_STAGE3_SETTLEMENT_SANDBOX_PAYOUT_POLICY.md
docs/evidence/releases/s3-stage-11-settlement-sandbox-payout-policy-20260525.md
docs/plans/2026-05-23-cybervpn-s3-stage-roadmap-ru.md
```

---

## 3. Proof Matrix

| Proof | Result |
|---|---|
| `PARTNER_SETTLEMENT_SANDBOX_ENABLED=false` is default | Passed |
| Sandbox route hidden when sandbox flag is off | Passed |
| Sandbox route hidden when portal flag is off | Passed |
| Sandbox route passes when portal and sandbox flags are enabled | Passed |
| OpenAPI exposes settlement sandbox route and schemas | Passed |
| Workspace owner can read sandbox simulation | Passed |
| Outsider cannot read another workspace sandbox | Passed |
| Available statement amount shown from `partner_statements` | Passed |
| Hold and reserve amounts shown from `partner_statements` | Passed |
| Refund and chargeback impact shown from reporting mart | Passed |
| Live payout remains blocked by `stage_blocks_live_payout` | Passed |
| Unapproved payout account blocks payout instruction | Passed |
| Payout export is disabled by policy | Passed |

---

## 4. Commands

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
  src/presentation/api/v1/partners/routes.py \
  src/presentation/api/v1/partners/schemas.py \
  src/presentation/middleware/partner_disabled_boundary.py \
  tests/integration/test_partner_portal_reporting_reads.py \
  tests/contract/test_partner_statement_openapi_contract.py \
  tests/unit/presentation/middleware/test_partner_disabled_boundary.py
```

Observed result:

```text
pytest disabled-boundary middleware: 22 passed
pytest OpenAPI contract: 1 passed
pytest partner reporting/settlement integration: 1 passed
ruff: All checks passed
py_compile: passed
```

---

## 5. Final Hygiene And Security Review

```text
git diff --check: passed
npm audit --audit-level=high: passed; 5 moderate advisories remain outside this S3-11 gate
dangerous pattern scan: no matches for eval/exec/os.system/subprocess/shell=True/raw f-string SQL patterns
docker ps: no running containers reported
```

Secret scan result:

```text
No real secret material found in S3-STAGE-11 changes.
Expected false positives:
- test-only passwords in backend/tests/integration/test_partner_portal_reporting_reads.py
- SecretStr normalization code in backend/src/config/settings.py
```

---

## 6. Sample Sandbox Policy

Expected S3-STAGE-11 policy response shape:

```json
{
  "stage": "S3-STAGE-11",
  "mode": "sandbox_only",
  "payout_export_status": "disabled_by_default",
  "live_payouts_enabled": false,
  "requires_finance_approval": true,
  "requires_maker_checker": true,
  "same_admin_approval_allowed": false
}
```

Expected blocked reasons for the local proof fixture:

```text
stage_blocks_live_payout
payout_account_not_approved
no_approved_instruction_for_dry_run
```

---

## 7. Production Notes

Production must keep:

```text
PARTNER_SETTLEMENT_SANDBOX_ENABLED=false
PARTNER_PAYOUTS_ENABLED=false
```

until S3-STAGE-12, S3-STAGE-14, S3-STAGE-15 and S3-STAGE-17 gates are complete.

If finance needs read-only review earlier, enable only:

```text
PARTNER_SETTLEMENT_SANDBOX_ENABLED=true
```

and keep:

```text
PARTNER_PAYOUTS_ENABLED=false
```

---

## 8. Next

```text
S3-STAGE-12: Partner Support, Admin Ops, And Audit
```
