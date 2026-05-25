# Stage 3 Partner Workspace, Team, And RBAC

**Stage:** `S3-STAGE-07`
**Status:** Passed for local code/evidence gate
**Date:** 2026-05-24
**Product stage:** CyberVPN Partner / Reseller Platform
**Prior gate:** `S3-STAGE-06: Partner Application And Onboarding Flow`

---

## 1. Назначение

S3-STAGE-07 закрывает безопасную модель партнёрского workspace: владелец партнёра может управлять командой, роли реально ограничивают действия, finance/traffic/support/analyst не смешиваются, а admin может заморозить workspace.

Этот этап не открывает партнёрскую программу в production. Он делает RBAC-контракт доказанным и готовым для последующих S3 этапов.

---

## 2. Decision

Production default остается закрытым:

```text
PARTNER_PORTAL_ENABLED=false
PARTNER_APPLICATIONS_ENABLED=false
PARTNER_PAYOUTS_ENABLED=false
PARTNER_STOREFRONTS_ENABLED=false
PARTNER_WEBHOOKS_ENABLED=false
PARTNER_EVENT_BACKBONE_ENABLED=false
```

Для локального proof включались только тестовые S3 flags:

```text
PARTNER_PORTAL_ENABLED=true
PARTNER_APPLICATIONS_ENABLED=true
PARTNER_PAYOUTS_ENABLED=true
```

`PARTNER_PAYOUTS_ENABLED=true` нужен в proof только потому, что standalone payout verification route защищён disabled-boundary.

---

## 3. Входит

| Area | S3-STAGE-07 result |
|---|---|
| Workspace bootstrap | Admin creates workspace with an active partner owner membership. |
| Team invitations | Owner adds manager, finance and traffic operators. |
| Role assignment | Built-in roles are seeded/updated through `PartnerAccountRepository.ensure_builtin_roles()`. |
| Role changes | Owner can change member role; permissions change immediately in bootstrap and action gates. |
| Owner-role guard | Non-owner cannot change owner memberships; last active owner cannot be demoted/limited. |
| 2FA requirement | When workspace `require_mfa_for_workspace=true`, privileged write actions require `totp_enabled=true`. |
| Readonly/reporting access | Analyst keeps read/reporting permissions and loses payout-write capability. |
| Finance separation | Finance can work with payouts but cannot submit traffic declarations. |
| Traffic separation | Traffic manager can submit traffic declarations but cannot create payout accounts. |
| Admin freeze | Admin can set workspace status to `suspended`; partner write actions become blocked. |

---

## 4. Backend Changes

### 4.1 Central workspace permission enforcement

Added shared enforcement in:

```text
backend/src/presentation/dependencies/partner_workspace.py
```

The enforcement now checks:

1. requested permission exists in current role permissions;
2. write permissions are blocked for frozen statuses:

```text
suspended
rejected
terminated
```

3. workspace-level 2FA gate for sensitive write permissions when `require_mfa_for_workspace=true`.

Sensitive write permissions:

```text
operations_write
membership_write
codes_write
payouts_write
traffic_write
integrations_write
```

### 4.2 Shared enforcement applied to standalone routes

Updated standalone partner route families to reuse the same RBAC/MFA/freeze rules:

```text
backend/src/presentation/api/v1/partner_payout_accounts/routes.py
backend/src/presentation/api/v1/traffic_declarations/routes.py
backend/src/presentation/api/v1/partner_bots/routes.py
```

This prevents route-family drift where workspace routes and standalone routes enforce different permission rules.

### 4.3 Owner-role safety guard

Updated:

```text
PATCH /api/v1/partner-workspaces/{workspace_id}/members/{member_id}
```

Rules:

1. only owner can assign or change `owner` memberships;
2. workspace must keep at least one active owner;
3. role changes are applied only after guard checks pass.

### 4.4 Admin freeze route

Added:

```text
PATCH /api/v1/admin/partner-workspaces/{workspace_id}/status
```

Allowed statuses:

```text
draft
email_verified
submitted
under_review
needs_info
approved_probation
active
restricted
suspended
rejected
terminated
```

For S3-STAGE-07 the freeze proof uses:

```text
workspace_status=suspended
```

---

## 5. Security Boundary

Partner workspace RBAC now has a single backend enforcement point for common partner workspace dependencies.

Important rules:

1. internal admins keep admin override for admin workflows;
2. partner operators cannot bypass role permissions;
3. write actions are blocked when workspace is frozen;
4. workspace-level 2FA blocks privileged partner writes but does not block readonly/reporting access;
5. `owner` role cannot be removed accidentally as the last active owner.

---

## 6. Exit Criteria Check

| Exit criterion | Result |
|---|---|
| Partner owner manages team within permissions | Passed: owner adds members and changes finance to analyst. |
| Non-owner cannot control owner membership | Passed: manager cannot demote owner. |
| Last owner cannot be removed | Passed: owner self-demotion returns conflict. |
| Finance actions unavailable to support/analyst roles | Passed: analyst loses payout-write after role change. |
| Finance cannot perform traffic writes | Passed: finance traffic declaration blocked. |
| Traffic manager cannot perform payout writes | Passed: traffic payout creation blocked. |
| 2FA requirement for privileged partner users | Passed: traffic write blocked until `totp_enabled=true`. |
| Admin can freeze workspace | Passed: admin sets `suspended`; partner write action is blocked. |

---

## 7. Validation

Commands:

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

Result:

```text
partner workspace/team/RBAC e2e: 1 passed
partner application approve/reject e2e: 2 passed
OpenAPI + runtime metrics: 2 passed
disabled-boundary middleware: 8 passed
ruff: passed
```

---

## 8. Production Posture

Keep partner portal and partner payouts disabled until explicit S3 production gate.

Before any production partner workspace enablement:

1. confirm admin/operator users and 2FA;
2. confirm partner workspaces are created intentionally;
3. confirm owner users have valid auth realm and 2FA path;
4. confirm finance role is assigned only to trusted finance operators;
5. confirm workspace freeze/unfreeze playbook;
6. confirm audit/evidence capture for role and status changes.

---

## 9. Next Stage

```text
S3-STAGE-08: Partner Codes, Attribution, And Anti-Abuse
```
