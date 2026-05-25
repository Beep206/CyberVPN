# S3-STAGE-10 Evidence: Partner Reporting And Analytics

**Date:** 2026-05-25
**Stage:** `S3-STAGE-10`
**Status:** Passed for local code/evidence gate
**Stage document:** `docs/cybervpn_stage3_launch_docs/10_STAGE3_PARTNER_REPORTING_ANALYTICS.md`

---

## 1. Summary

S3-STAGE-10 proves the partner reporting and analytics contract locally:

```text
partner reporting has a dedicated disabled-state flag
reporting routes stay hidden until PARTNER_REPORTING_ENABLED=true
workspace reporting summary exposes source-of-truth notes
trial users are explicitly not_available until a canonical partner trial mart exists
analytics metrics carry source/redaction flags
report exports expose redaction policy and excluded PII fields
outsider workspace access is denied
OpenAPI exposes the reporting summary contract
```

This does not enable production reporting, settlement, or payouts.

---

## 2. Changed Files

```text
backend/.env.example
backend/src/config/settings.py
backend/src/presentation/middleware/partner_disabled_boundary.py
backend/src/presentation/api/v1/partners/routes.py
backend/src/presentation/api/v1/partners/schemas.py
backend/tests/conftest.py
backend/tests/unit/presentation/middleware/test_partner_disabled_boundary.py
backend/tests/integration/test_partner_portal_reporting_reads.py
backend/tests/contract/test_partner_statement_openapi_contract.py
docs/cybervpn_stage3_launch_docs/10_STAGE3_PARTNER_REPORTING_ANALYTICS.md
docs/evidence/releases/s3-stage-10-partner-reporting-analytics-20260525.md
docs/plans/2026-05-23-cybervpn-s3-stage-roadmap-ru.md
```

---

## 3. Proof Matrix

| Proof | Result |
|---|---|
| `PARTNER_REPORTING_ENABLED=false` is default | Passed |
| Reporting routes hidden when reporting flag is off | Passed |
| Reporting routes hidden when portal flag is off | Passed |
| Reporting routes pass when portal and reporting are enabled | Passed |
| Reporting summary appears in OpenAPI | Passed |
| Summary includes active users, paid users, paid conversions, refunds, chargebacks and earnings | Passed |
| Trial users are not overclaimed | Passed: `trial_users=not_available` |
| Reconciliation status and mismatch counts are returned | Passed |
| Export redaction policy and excluded PII fields are returned | Passed |
| Outsider cannot read another workspace reporting data | Passed |

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
pytest disabled-boundary middleware: 19 passed
pytest OpenAPI contract: 1 passed
pytest partner reporting integration: 1 passed
ruff: All checks passed
```

Final hygiene/security review:

```text
git diff --check: passed
S3-10 secret scan: no matches
S3-10 dangerous pattern scan: no matches for eval/exec/os.system/subprocess/raw f-string SQL patterns
docker ps: no running containers reported
npm audit --audit-level=high: passed; 5 moderate advisories remain outside this S3-10 gate
```

---

## 5. Important Notes

The first run of the partner reporting integration test failed before S3-STAGE-10 assertions because the test admin workspace creation request did not send an admin host. The request was corrected to use:

```text
Host: admin.cyber-vpn.net
```

After that, the reporting feature proof passed.

---

## 6. Production Notes

Production must keep:

```text
PARTNER_REPORTING_ENABLED=false
```

until settlement sandbox, partner observability, full staging rehearsal and owner approval are completed.

---

## 7. Next

```text
S3-STAGE-11: Settlement Sandbox And Payout Policy
```
