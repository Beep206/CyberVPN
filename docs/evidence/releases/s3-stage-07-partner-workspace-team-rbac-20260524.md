# S3-STAGE-07 Evidence: Partner Workspace, Team, And RBAC

**Date:** 2026-05-24
**Stage:** `S3-STAGE-07`
**Status:** Passed for local code/evidence gate
**Stage document:** `docs/cybervpn_stage3_launch_docs/07_STAGE3_PARTNER_WORKSPACE_TEAM_RBAC.md`

---

## 1. Summary

S3-STAGE-07 proves the partner workspace/team/RBAC contract locally:

```text
owner can add partner team members
manager cannot change owner memberships
last active owner cannot be removed
finance and traffic roles are separated
role changes update effective permissions
workspace-level MFA blocks privileged writes
admin freeze blocks partner write actions
standalone partner payout/traffic/bot routes reuse the same enforcement
```

This does not enable partner portal, partner payouts, storefronts, webhooks or event backbone in production.

---

## 2. Changed Files

```text
backend/src/presentation/dependencies/partner_workspace.py
backend/src/presentation/api/v1/partner_bots/routes.py
backend/src/presentation/api/v1/partner_payout_accounts/routes.py
backend/src/presentation/api/v1/partners/routes.py
backend/src/presentation/api/v1/partners/schemas.py
backend/src/presentation/api/v1/traffic_declarations/routes.py
backend/tests/e2e/test_partner_admin_conformance.py
docs/cybervpn_stage3_launch_docs/07_STAGE3_PARTNER_WORKSPACE_TEAM_RBAC.md
docs/evidence/releases/s3-stage-07-partner-workspace-team-rbac-20260524.md
docs/plans/2026-05-23-cybervpn-s3-stage-roadmap-ru.md
```

---

## 3. Proof Matrix

| Proof | Result |
|---|---|
| Admin creates workspace with owner membership | Passed |
| Owner adds manager/finance/traffic operators | Passed |
| Manager cannot demote owner | Passed |
| Owner cannot remove the last active owner | Passed |
| Finance has `payouts_write` and not `traffic_write` | Passed |
| Traffic manager has `traffic_write` and not `payouts_write` | Passed |
| Finance cannot create traffic declaration | Passed |
| Traffic manager cannot create payout account | Passed |
| Owner changes finance to analyst | Passed |
| Analyst loses payout-write access | Passed |
| Workspace `require_mfa_for_workspace=true` blocks privileged write without TOTP | Passed |
| Privileged write works after `totp_enabled=true` | Passed |
| Admin sets workspace `suspended` | Passed |
| Suspended workspace rejects partner write action | Passed |
| Disabled-boundary still protects payout routes when payout flag is off | Passed through middleware tests |

---

## 4. Commands

```bash
cd backend

SKIP_TEST_DB_BOOTSTRAP=1 ./.venv/bin/python -m pytest \
  tests/e2e/test_partner_admin_conformance.py::test_e2e_perm_010_015_role_permissions_and_admin_partner_sync \
  -q --no-cov

SKIP_TEST_DB_BOOTSTRAP=1 ./.venv/bin/python -m pytest \
  tests/e2e/test_partner_admin_conformance.py::test_e2e_partner_001_application_review_probation_legal_and_notification_loop \
  tests/e2e/test_partner_admin_conformance.py::test_e2e_partner_002_application_reject_state_is_visible \
  -q --no-cov

./.venv/bin/python -m pytest \
  tests/contract/test_partner_application_onboarding_openapi_contract.py \
  tests/integration/test_partner_runtime_observability.py::test_partner_runtime_metrics_increment_for_login_draft_submit_and_bootstrap \
  -q --no-cov

./.venv/bin/python -m pytest \
  tests/unit/presentation/middleware/test_partner_disabled_boundary.py \
  -q --no-cov

./.venv/bin/python -m ruff check \
  src/presentation/dependencies/partner_workspace.py \
  src/presentation/api/v1/partners/routes.py \
  src/presentation/api/v1/partners/schemas.py \
  src/presentation/api/v1/partner_payout_accounts/routes.py \
  src/presentation/api/v1/traffic_declarations/routes.py \
  src/presentation/api/v1/partner_bots/routes.py \
  tests/e2e/test_partner_admin_conformance.py
```

Observed result:

```text
pytest partner workspace/team/RBAC e2e: 1 passed
pytest partner application approve/reject e2e: 2 passed
pytest OpenAPI + runtime metrics: 2 passed
pytest disabled-boundary middleware: 8 passed
ruff: All checks passed
```

---

## 5. Notes

The RBAC proof requires `PARTNER_PAYOUTS_ENABLED=true` only in the local e2e fixture because standalone payout verification is intentionally hidden by disabled-boundary when partner payouts are disabled.

Production remains disabled by default:

```text
PARTNER_PORTAL_ENABLED=false
PARTNER_APPLICATIONS_ENABLED=false
PARTNER_PAYOUTS_ENABLED=false
PARTNER_STOREFRONTS_ENABLED=false
PARTNER_WEBHOOKS_ENABLED=false
PARTNER_EVENT_BACKBONE_ENABLED=false
```

---

## 6. Next

```text
S3-STAGE-08: Partner Codes, Attribution, And Anti-Abuse
```
