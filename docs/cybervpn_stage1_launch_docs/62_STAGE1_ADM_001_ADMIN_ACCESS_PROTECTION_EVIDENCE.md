# Stage 1 Admin Access Protection Evidence

> Date: 2026-05-04  
> Backlog ID: `S1-ADM-001`  
> Scope: local admin host boundary, admin mirror redirect and production settings guardrails  
> Status: local evidence complete; deployed DNS/TLS/ingress/IP/private-access evidence remains required before go-live

## Purpose

`S1-ADM-001` proves that interactive admin API routes are not exposed on public customer domains during S1 Controlled Public Beta.

S1 domain rules:

| Host | S1 rule |
|---|---|
| `admin.cyber-vpn.net` | canonical admin host |
| `admin.cyber-vpn.org` | redirect-only mirror, not an allowed backend admin API host |
| `cyber-vpn.net` | public customer host, must not serve interactive admin API routes |
| `cyber-vpn.org` | public mirror/redirect host, must not serve interactive admin API routes |

## Implementation Summary

| Area | Change |
|---|---|
| Backend middleware | Added `AdminHostGuardMiddleware` for `/api/v1/admin` interactive routes |
| Backend settings | Added production validation for `ADMIN_HOST_PROTECTION_ENABLED` and `ADMIN_ALLOWED_HOSTS` |
| Allowed production admin host | `admin.cyber-vpn.net` only |
| Redirect-only admin mirror | `admin.cyber-vpn.org`, rejected by backend admin API guard |
| Public domains | `cyber-vpn.net` and `cyber-vpn.org` rejected for interactive admin API routes |
| Frontend proxy | `admin.cyber-vpn.org` redirects to `https://admin.cyber-vpn.net` before locale routing |
| Env documentation | `backend/.env.example` now records S1 admin host protection requirements |

The backend guard returns `404 {"detail": "Not found"}` for wrong-host admin API access. This intentionally hides the admin route surface instead of revealing an authentication boundary on public domains.

## Local Proof Matrix

| Check | Expected result | Local result |
|---|---|---|
| `Host: cyber-vpn.net` + `GET /api/v1/admin/audit-log` | public domain must not expose admin API | `404 Not found` |
| `Host: admin.cyber-vpn.org` + `GET /api/v1/admin/audit-log` | redirect-only mirror must not be backend admin API host | `404 Not found` |
| `Host: admin.cyber-vpn.net` + `GET /api/v1/admin/audit-log` | canonical admin host reaches auth layer | `401 Not authenticated` in local auth-disabled proof |
| Wrong-host admin CORS preflight | must not return successful CORS | `404`, no `access-control-allow-origin` |
| Canonical admin CORS preflight | admin origin allowed | `200`, `access-control-allow-origin: https://admin.cyber-vpn.net` |
| `Host: cyber-vpn.net` + `GET /api/v1/status` | public non-admin API remains reachable | `200` |
| `https://admin.cyber-vpn.org/en-EN/dashboard?tab=ops` | frontend mirror redirects to canonical admin host | `307` to `https://admin.cyber-vpn.net/en-EN/dashboard?tab=ops` |

## Commands and Results

| Check | Command | Result |
|---|---|---|
| Backend lint | `cd backend && .venv/bin/python -m ruff check src/config/settings.py src/main.py src/presentation/middleware/admin_host_guard.py tests/unit/config/test_settings.py tests/security/test_stage1_admin_access_protection.py` | `All checks passed!` |
| Backend settings + admin host proof | `cd backend && .venv/bin/python -m pytest tests/unit/config/test_settings.py tests/security/test_stage1_admin_access_protection.py -q --no-cov` | `36 passed` |
| Existing route-boundary regression | `cd backend && .venv/bin/python -m pytest tests/security/test_stage1_route_boundary.py -q --no-cov` | `4 passed` |
| Frontend proxy tests | `cd frontend && npm run test:run -- src/__tests__/proxy.test.ts` | `6 passed` |
| Frontend targeted lint | `cd frontend && npx eslint src/proxy.ts src/__tests__/proxy.test.ts` | passed with no output |
| Backend dependency consistency | `cd backend && .venv/bin/python -m pip check && uv run --with pip-audit pip-audit` | no broken requirements; no known vulnerabilities |
| Secret pattern scan | targeted high-confidence secret regex over changed code/docs | no real secret matches |

## Source Notes

| Source | Use |
|---|---|
| FastAPI middleware documentation: <https://fastapi.tiangolo.com/tutorial/middleware/> | Confirmed middleware pattern and request/response handling |
| Next.js proxy file convention: <https://nextjs.org/docs/app/api-reference/file-conventions/proxy> | Confirmed `src/proxy.ts` request interception and redirect pattern for Next.js 16+ |

## Boundaries and Remaining Evidence

This evidence closes local implementation proof for `S1-ADM-001`, but it does not close go-live deployment proof.

Remaining before S1 go-live:

- deployed DNS/TLS evidence for `admin.cyber-vpn.net`;
- deployed redirect evidence from `admin.cyber-vpn.org` to `admin.cyber-vpn.net`;
- deployed ingress proof that public hosts do not serve interactive admin API routes;
- deployed admin-origin CORS/browser auth evidence;
- IP allowlist/private-network/WAF/edge restrictions if adopted for beta;
- RBAC matrix evidence under `S1-ADM-002`;
- admin 2FA evidence under `S1-ADM-003`;
- privileged action audit coverage under `S1-ADM-004`;
- staging/prod first-admin bootstrap and 2FA login evidence under `TD-S1-ADM-001`.

Internal shared-secret routes under `/api/v1/admin/growth-reporting/internal/...` remain outside this interactive admin-host guard and still require private network or edge restriction evidence under `TD-S1-BE-003`.

## Security Notes

- No production DNS, TLS, provider credential, bot token, VPN node, Remnawave credential or user data was touched.
- No Docker containers were started for this task.
- `npm audit --omit=dev` in `frontend` still reports the known `next`/`postcss` moderate finding. `npm audit fix` suggests a breaking downgrade to `next@9.3.3`, so it remains tracked under `TD-S1-SEC-001` for the broader pre-RC dependency gate.

## Next ID

Next ID to execute: `S1-ADM-002` - RBAC matrix implemented.
