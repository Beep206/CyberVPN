# Stage 1 Admin RBAC Matrix Evidence

> Date: 2026-05-04  
> Backlog ID: `S1-ADM-002`  
> Scope: local owner/support/ops/finance RBAC matrix, FastAPI dependency proof and role assignment guardrails  
> Status: local evidence complete; deployed admin persona/UI proof remains required before go-live

## Purpose

`S1-ADM-002` proves that S1 admin roles are separated for Controlled Public Beta operations.

S1 role mapping:

| Business role | Code role | Purpose |
|---|---|---|
| Owner | `owner/super_admin` | bootstrap owner and final emergency authority |
| Super admin | `super_admin` | full operational backup role, not bootstrap-only |
| Admin | `admin` | broad internal supervisor role |
| Ops | `operator` | infrastructure/provisioning/system operations without finance or support credential powers |
| Finance | `finance` | payment/reconciliation visibility without support or ops mutation powers |
| Support | `support` | customer support actions without finance visibility |
| Viewer | `viewer` | read-only baseline |

## Implemented Matrix

| Role | Allowed S1 permissions | Explicitly denied in tests |
|---|---|---|
| `owner/super_admin` | all `Permission` values | none |
| `super_admin` | all `Permission` values | none |
| `admin` | broad user/server/payment/monitoring/audit/webhook/plans/invites/subscription/VPN/analytics permissions, but not first-owner bootstrap | owner bootstrap via invite remains blocked |
| `operator` | `user_read`, `server_read`, `server_create`, `server_update`, `monitoring_read`, `subscription_create`, `view_analytics` | `user_update`, `user_delete`, `payment_read`, `payment_create`, `audit_read`, `webhook_read`, `vpn_credential_regenerate`, `manage_invites` |
| `finance` | `user_read`, `payment_read`, `audit_read`, `webhook_read` | `user_update`, `user_delete`, `server_read`, `server_update`, `monitoring_read`, `subscription_create`, `vpn_credential_regenerate`, `manage_invites`, `view_analytics` |
| `support` | `user_read`, `user_update`, `server_read`, `monitoring_read`, `vpn_credential_regenerate` | `payment_read`, `payment_create`, `audit_read`, `webhook_read`, `server_update`, `subscription_create`, `manage_invites` |
| `viewer` | `user_read`, `server_read`, `monitoring_read`, `view_analytics` | write/admin/payment mutation permissions |

## Implementation Summary

| Area | Change |
|---|---|
| Admin roles | Added `AdminRole.FINANCE = "finance"` |
| Permission matrix | Removed finance access from `operator`; added explicit `finance` permission set |
| Role inheritance | Replaced pure linear hierarchy with explicit `ROLE_MINIMUM_ACCESS` so `finance` is not accidentally treated as support/ops |
| Invite role assignment | Replaced local invite role list with shared `can_assign_role()` |
| FastAPI dependencies | Invalid admin role strings now fail closed with `403 Invalid admin role` instead of surfacing an unhandled enum error |
| WebSocket topics | `finance` can subscribe to `payments` and `general`, but not `servers`, `users` or `system` |

## Local Proof Matrix

| Check | Local result |
|---|---|
| Owner and super admin have all permissions | Passed |
| Support lacks finance permissions | Passed |
| Support can regenerate VPN credentials | Passed |
| Ops lacks finance and VPN credential permissions | Passed |
| Ops can update server/system-operation surfaces | Passed |
| Finance can read payment/audit/webhook state | Passed |
| Finance cannot update users, servers, VPN credentials or analytics | Passed |
| Finance is not accepted as support, ops or admin by role dependencies | Passed |
| Support and ops are not accepted as finance | Passed |
| Invalid stored admin role fails closed | Passed |
| FastAPI dependency pipeline returns expected 200/403 for finance/support/ops routes | Passed |
| WebSocket payment topic allows finance and denies operator/viewer | Passed |

## Commands and Results

| Check | Command | Result |
|---|---|---|
| Targeted lint | `cd backend && .venv/bin/python -m ruff check src/application/use_cases/auth/permissions.py src/domain/enums/enums.py src/presentation/dependencies/roles.py src/presentation/api/v1/admin/invites.py src/application/services/ws_topic_authorization.py tests/security/test_stage1_admin_rbac_matrix.py tests/unit/test_use_cases.py tests/unit/test_domain_entities.py tests/security/test_ws_topic_auth.py` | `All checks passed!` |
| RBAC component and feature tests | `cd backend && .venv/bin/python -m pytest tests/security/test_stage1_admin_rbac_matrix.py tests/unit/test_use_cases.py tests/unit/test_domain_entities.py tests/security/test_ws_topic_auth.py -q --no-cov` | `43 passed` |

## Source Notes

| Source | Use |
|---|---|
| FastAPI dependencies and `Security()` reference: <https://fastapi.tiangolo.com/reference/dependencies/> | Confirmed dependency callable pattern and FastAPI dependency execution model |
| FastAPI OAuth2 scopes guide: <https://fastapi.tiangolo.com/advanced/security/oauth2-scopes/> | Confirmed the broader FastAPI authorization pattern of declaring route-specific required scopes/permissions |

## Boundaries and Remaining Evidence

This evidence closes local RBAC matrix implementation for `S1-ADM-002`, but it does not close all admin go-live proof.

Remaining before S1 go-live:

- deployed admin persona proof with real/staging `owner/super_admin`, `support`, `operator`, `finance` users;
- admin UI visibility proof that each role sees only the intended functions;
- route-by-route proof for later dangerous actions under `S1-ADM-004`, `S1-ADM-005`, `S1-ADM-006` and `S1-ADM-007`;
- admin 2FA enforcement under `S1-ADM-003`;
- staged first-admin bootstrap/login evidence under `TD-S1-ADM-001`.

## Security Notes

- No production user, provider credential, bot token, VPN node or Remnawave credential was touched.
- No Docker containers were started for this task.
- This task reduces role blast radius by making finance non-linear and denying implicit support/ops access.

## Next ID

Next ID to execute: `S1-ADM-003` - admin 2FA enforced.
