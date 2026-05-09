# Stage 1 Admin 2FA Enforcement Evidence

> Date: 2026-05-04  
> Backlog ID: `S1-ADM-003`  
> Scope: local admin 2FA enforcement for role/permission-protected admin API surfaces  
> Status: local evidence complete; deployed browser/API persona proof remains required before go-live

## Purpose

`S1-ADM-003` proves that Stage 1 admin access can be made fail-closed when an active admin user has not enabled TOTP.

The key boundary is intentional: the enforcement is applied to role/permission-protected admin surfaces, not to the generic active-user dependency. This keeps the 2FA setup/status routes reachable for an already-authenticated admin who still needs to enroll TOTP.

## Implementation Summary

| Area | Change |
|---|---|
| Production setting | Added `ADMIN_2FA_REQUIRED`; production config rejects `false` |
| RBAC dependencies | `require_role()` and `require_permission()` now return `403 Admin 2FA required` when the gate is enabled and `totp_enabled=false` |
| Enrollment boundary | Routes that only depend on `get_current_active_user`, such as setup/status-style 2FA routes, remain reachable so an admin can enable TOTP |
| Environment checklist | `.env.example` now lists `ADMIN_2FA_REQUIRED=true` as a production checklist item |
| Existing production smoke env | Admin access protection subprocess test now explicitly sets `ADMIN_2FA_REQUIRED=true` |

## Local Proof Matrix

| Check | Local result |
|---|---|
| Production settings reject `ADMIN_2FA_REQUIRED=false` | Passed |
| Admin permission dependency rejects finance user without TOTP when required | Passed |
| Admin permission dependency allows finance user with TOTP when required | Passed |
| Local development can keep the 2FA gate disabled without breaking RBAC tests | Passed |
| Invalid stored admin role still fails closed with `403 Invalid admin role` before 2FA state is evaluated | Passed |
| FastAPI dependency pipeline returns `403 Admin 2FA required` for protected admin route without TOTP | Passed |
| FastAPI dependency pipeline returns `200` for protected admin route with TOTP | Passed |
| 2FA setup-style route using only `get_current_active_user` remains reachable without TOTP | Passed |
| Existing 2FA lifecycle security tests still pass | Passed |
| Existing admin host/access protection tests still pass with the new production env flag | Passed |
| Existing RBAC matrix tests still pass | Passed |

## Commands and Results

| Check | Command | Result |
|---|---|---|
| Targeted lint | `cd backend && .venv/bin/python -m ruff check src/config/settings.py src/presentation/dependencies/roles.py tests/unit/config/test_settings.py tests/security/test_stage1_admin_2fa_enforcement.py tests/security/test_stage1_admin_access_protection.py` | `All checks passed!` |
| Admin 2FA/RBAC/settings proof | `cd backend && .venv/bin/python -m pytest tests/unit/config/test_settings.py tests/security/test_stage1_admin_2fa_enforcement.py tests/security/test_stage1_admin_rbac_matrix.py -q --no-cov` | `45 passed` |
| Extended 2FA/admin protection proof | `cd backend && .venv/bin/python -m pytest tests/security/test_2fa_security.py tests/security/test_stage1_admin_access_protection.py tests/unit/config/test_settings.py tests/security/test_stage1_admin_2fa_enforcement.py tests/security/test_stage1_admin_rbac_matrix.py -q --no-cov` | `56 passed` |

## Source Notes

| Source | Use |
|---|---|
| FastAPI dependencies reference: <https://fastapi.tiangolo.com/reference/dependencies/> | Confirmed the dependency callable pattern used by `Depends()` |
| FastAPI OAuth2 scopes guide: <https://fastapi.tiangolo.com/advanced/security/oauth2-scopes/> | Confirmed the route-level authorization pattern used for permission-scoped checks |

## Boundaries and Remaining Evidence

This evidence closes local admin 2FA enforcement for `S1-ADM-003`, but it does not close all admin go-live proof.

Remaining before S1 go-live:

- deployed staging/prod admin login proof with a real TOTP-enabled admin;
- deployed proof that an admin without TOTP cannot access protected admin API/UI surfaces;
- first-admin bootstrap proof on the target environment with TOTP already enabled;
- redacted browser/API screenshots or transcripts for owner/support/operator/finance personas;
- audit log proof for privileged actions under `S1-ADM-004`;
- support/finance UI proof under later admin/support tasks.

## Security Notes

- No production user, provider credential, bot token, VPN node or Remnawave credential was touched.
- No Docker containers were started for this task.
- The default local setting remains development-friendly, but production startup now fails closed unless `ADMIN_2FA_REQUIRED=true`.

## Next ID

Next ID to execute: `S1-ADM-004` - audit log for privileged actions.
