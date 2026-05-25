# S3-STAGE-06 Evidence: Partner Application And Onboarding Flow

**Date:** 2026-05-24
**Stage:** `S3-STAGE-06`
**Status:** Passed for local code/evidence gate
**Stage document:** `docs/cybervpn_stage3_launch_docs/06_STAGE3_PARTNER_APPLICATION_ONBOARDING_FLOW.md`

---

## 1. Summary

S3-STAGE-06 proves controlled partner onboarding locally:

```text
partner applications remain disabled by default
application routes require both portal and applications flags
applicant draft/submit path works
admin request-info and review queue work
approve probation path works
reject path is visible to applicant
partner application observability remains healthy
```

This does not open partner onboarding in production.

---

## 2. Changed Files

```text
backend/.env.example
backend/src/config/settings.py
backend/src/presentation/middleware/partner_disabled_boundary.py
backend/src/application/use_cases/partners/partner_applications.py
backend/src/presentation/api/v1/partners/routes.py
backend/src/infrastructure/monitoring/instrumentation/partner_runtime.py
backend/tests/unit/presentation/middleware/test_partner_disabled_boundary.py
backend/tests/e2e/test_partner_admin_conformance.py
backend/tests/integration/test_partner_runtime_observability.py
docs/cybervpn_stage3_launch_docs/05_STAGE3_PARTNER_PORTAL_DISABLED_STATE_BOUNDARY.md
docs/cybervpn_stage3_launch_docs/06_STAGE3_PARTNER_APPLICATION_ONBOARDING_FLOW.md
docs/plans/2026-05-23-cybervpn-s3-stage-roadmap-ru.md
```

---

## 3. Proof Matrix

| Proof | Result |
|---|---|
| `PARTNER_APPLICATIONS_ENABLED=false` with portal enabled returns `partner_applications_disabled` | Passed |
| Application routes stay hidden when portal is disabled | Passed |
| Application routes pass when both flags are enabled | Passed |
| OpenAPI exposes application onboarding contract routes | Passed |
| Runtime metrics increment for login/draft/submit/bootstrap | Passed |
| Applicant request-info/resubmit/approve probation loop | Passed |
| Reject path returns `rejected` workspace and `declined` lane | Passed |
| Bootstrap shows rejected blocked reason | Passed |

---

## 4. Commands

```bash
cd backend

./.venv/bin/python -m ruff check \
  src/config/settings.py \
  src/presentation/middleware/partner_disabled_boundary.py \
  src/application/use_cases/partners/partner_applications.py \
  src/presentation/api/v1/partners/routes.py \
  src/infrastructure/monitoring/instrumentation/partner_runtime.py \
  tests/unit/presentation/middleware/test_partner_disabled_boundary.py \
  tests/e2e/test_partner_admin_conformance.py \
  tests/integration/test_partner_runtime_observability.py

./.venv/bin/python -m pytest \
  tests/unit/presentation/middleware/test_partner_disabled_boundary.py \
  tests/contract/test_partner_application_onboarding_openapi_contract.py \
  tests/integration/test_partner_runtime_observability.py::test_partner_runtime_metrics_increment_for_login_draft_submit_and_bootstrap \
  -q --no-cov

SKIP_TEST_DB_BOOTSTRAP=1 ./.venv/bin/python -m pytest \
  tests/e2e/test_partner_admin_conformance.py::test_e2e_partner_001_application_review_probation_legal_and_notification_loop \
  tests/e2e/test_partner_admin_conformance.py::test_e2e_partner_002_application_reject_state_is_visible \
  -q --no-cov
```

Observed result:

```text
ruff: All checks passed
pytest middleware/OpenAPI/runtime metrics: 10 passed
pytest e2e approve/reject onboarding: 2 passed
```

---

## 5. Bugs Closed During Proof

| Bug | Impact | Status |
|---|---|---|
| Helper methods were unreachable outside `PartnerApplicationWorkflowUseCase`. | Admin request-info/approve/reject could crash. | Fixed |
| Bootstrap used non-existent blocked reason field. | Partner bootstrap could crash for blocked/needs-info states. | Fixed |
| Decision metric duration mixed naive/aware datetimes. | Admin decision could fail during observability emission. | Fixed |
| Decision duration histogram got wrong labels. | Admin decision returned `Incorrect label names`. | Fixed |

---

## 6. Remaining Gate

Production enablement is still blocked until later S3 production gate.

Required production flags stay:

```text
PARTNER_PORTAL_ENABLED=false
PARTNER_APPLICATIONS_ENABLED=false
```

Next:

```text
S3-STAGE-07: Partner Workspace, Team, And RBAC
```
