# Stage 3 Partner Application And Onboarding Flow

**Stage:** `S3-STAGE-06`
**Status:** Passed for local code/evidence gate
**Date:** 2026-05-24
**Product stage:** CyberVPN Partner / Reseller Platform
**Prior gate:** `S3-STAGE-05: Partner Portal Disabled-State Boundary`

---

## 1. Назначение

S3-STAGE-06 закрывает controlled partner onboarding: партнёр может подать заявку, оператор/admin может вручную рассмотреть её, запросить дополнительную информацию, одобрить в probation или отклонить.

Этот этап не открывает публичную партнёрскую программу. Он делает flow технически доказанным и управляемым флагами.

---

## 2. Decision

Production default остается закрытым:

```text
PARTNER_PORTAL_ENABLED=false
PARTNER_APPLICATIONS_ENABLED=false
PARTNER_STOREFRONTS_ENABLED=false
PARTNER_WEBHOOKS_ENABLED=false
PARTNER_PAYOUTS_ENABLED=false
PARTNER_EVENT_BACKBONE_ENABLED=false
```

Для controlled onboarding нужны оба флага:

```text
PARTNER_PORTAL_ENABLED=true
PARTNER_APPLICATIONS_ENABLED=true
```

`PARTNER_APPLICATIONS_ENABLED=true` без portal flag не открывает self-serve заявки.

---

## 3. Входит

| Area | S3-STAGE-06 result |
|---|---|
| Application draft | `POST /api/v1/partner-application-drafts` creates draft/workspace and lane application. |
| Applicant submit | `POST /api/v1/partner-application-drafts/{draft_id}/submit` moves workspace to `submitted`. |
| Admin review queue | `/api/v1/admin/partner-applications` lists submitted applications behind admin auth/RBAC/host guard. |
| Request info | `/request-info` moves workspace to `needs_info` and creates review request. |
| Evidence upload | `/attachments` records requested evidence. |
| Partner response | Review request response + `resubmit` returns workspace to `submitted`. |
| Approval | `/approve-probation` moves workspace and lane to `approved_probation`. |
| Rejection | `/reject` moves workspace to `rejected`, lane to `declined`, and bootstrap shows blocked reason. |
| Legal acceptance | Approved probation flow exposes pending partner legal documents and accepts them. |
| Observability | Application, bootstrap, decision and notification metrics/logs remain functional. |

---

## 4. Не входит

- автоматическое одобрение всех партнёров;
- автоматические выплаты;
- публичные storefronts;
- массовое включение partner portal;
- partner payouts;
- partner code/reward issuance;
- S3 production enablement.

---

## 5. Backend Changes

### 5.1 Application kill switch

Added backend setting:

```text
partner_applications_enabled: bool = False
```

Added env sample:

```text
PARTNER_APPLICATIONS_ENABLED=false
```

Application draft routes are now separately gated:

```text
/api/v1/partner-application-drafts
```

Behavior:

| Portal flag | Applications flag | Result |
|---|---:|---|
| `false` | `false` | `404 partner_portal_disabled` |
| `false` | `true` | `404 partner_portal_disabled` |
| `true` | `false` | `404 partner_applications_disabled` |
| `true` | `true` | route reaches application code |

### 5.2 Existing workflow blockers fixed

The S3-STAGE-06 e2e proof found and fixed three existing backend issues:

| Issue | Fix |
|---|---|
| `PartnerApplicationWorkflowUseCase` referenced `_require_workspace` and `_require_lane_application`, but those methods were accidentally outside the class body. | Moved the helpers into the class and typed `_require_workspace`. |
| Partner bootstrap used `blocked_reasons[0].reason_code`, while the schema field is `code`. | Updated bootstrap metrics/log payload to use `.code`. |
| Partner decision observability mixed timezone-aware and timezone-naive datetimes and passed a wrong label set to the decision duration histogram. | Added UTC normalization helper and fixed histogram labels. |

---

## 6. Security Boundary

Admin review routes remain protected by existing controls:

1. admin host guard;
2. admin authentication;
3. admin RBAC;
4. admin 2FA where required by environment;
5. workflow events and partner runtime logs.

Self-serve application routes remain hidden unless both S3 flags are enabled.

---

## 7. Exit Criteria Check

| Exit criterion | Result |
|---|---|
| Applicant can submit application | Passed in e2e. |
| Admin/operator can review application | Passed in e2e via list + request-info + approve/reject. |
| Decision writes workflow/audit-style event | Passed through workflow event generation and notification feed assertions. |
| Approved state is visible | Passed: workspace/lane `approved_probation`, bootstrap shows active workspace state. |
| Rejected state is visible | Passed: workspace `rejected`, lane `declined`, bootstrap returns `workspace_status:rejected` blocked reason. |
| Public application routes do not self-launch | Passed through disabled-boundary tests. |

---

## 8. Validation

Commands:

```bash
cd backend
./.venv/bin/python -m ruff check src/config/settings.py src/presentation/middleware/partner_disabled_boundary.py src/application/use_cases/partners/partner_applications.py src/presentation/api/v1/partners/routes.py src/infrastructure/monitoring/instrumentation/partner_runtime.py tests/unit/presentation/middleware/test_partner_disabled_boundary.py tests/e2e/test_partner_admin_conformance.py tests/integration/test_partner_runtime_observability.py
./.venv/bin/python -m pytest tests/unit/presentation/middleware/test_partner_disabled_boundary.py tests/contract/test_partner_application_onboarding_openapi_contract.py tests/integration/test_partner_runtime_observability.py::test_partner_runtime_metrics_increment_for_login_draft_submit_and_bootstrap -q --no-cov
SKIP_TEST_DB_BOOTSTRAP=1 ./.venv/bin/python -m pytest tests/e2e/test_partner_admin_conformance.py::test_e2e_partner_001_application_review_probation_legal_and_notification_loop tests/e2e/test_partner_admin_conformance.py::test_e2e_partner_002_application_reject_state_is_visible -q --no-cov
```

Result:

```text
ruff: passed
middleware/OpenAPI/runtime metric tests: 10 passed
partner application e2e approve/reject tests: 2 passed
```

---

## 9. Production Posture

Do not enable this in production until S3 production gate:

```text
PARTNER_PORTAL_ENABLED=true
PARTNER_APPLICATIONS_ENABLED=true
```

Before production enablement, confirm:

1. admin users have correct roles and 2FA;
2. support/admin review process is staffed;
3. partner legal copy is approved;
4. notification/support channel is ready;
5. rollback flag plan is documented;
6. partner application rate limits are acceptable for public traffic.

---

## 10. Next Stage

```text
S3-STAGE-07: Partner Workspace, Team, And RBAC
```
