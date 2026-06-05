# CYBA-451 Code Change Push/Deploy Assessment

Date: 2026-06-05
Task: CYBA-451, deep pre-production QA
Repository: VPNBussiness-main
Branch inspected: `codex/cyba-386-worktree-snapshot`
Head inspected: `116407a wip(cyba-386): snapshot passkey webauthn worktree`

## Decision

Do not push the current worktree directly to `main`.
Do not deploy the current worktree to production.

The inspected tree is not documentation-only. It contains broad backend, admin, partner, and frontend code changes touching authentication, Passkey/WebAuthn, CSRF, session revocation, cookie handling, API proxying, generated API types, partner settings, and customer UI flows.

## Blocking Reasons

- The branch is behind `origin/main` by 48 commits and has 1 local commit not in `origin/main`; it needs a clean rebase or merge review before any integration.
- The release-readiness gate in `qa-artifacts/CYBA-455/release-readiness-gate-summary.md` is `FAIL`.
- Failing gates include frontend tests, partner tests, backend ruff, backend pytest collection, backend conformance packs, generated API type drift, and missing local conformance dependencies.
- The worktree includes runtime/evidence artifacts, including large untracked `partner/tmp` and `evidence` outputs, which are not suitable for a code release.
- The code changes alter high-risk security behavior around cookies, local-stage origins, passkey verification, tokenless web login responses, logout/session revocation, and BFF proxy header/cookie rewriting.
- Push credentials were not available from the inspected environment for GitLab or GitHub.

## Major Code Areas Observed

- Backend auth and Passkey/WebAuthn cookie/session behavior:
  `backend/src/presentation/api/v1/auth/*`, `backend/src/application/use_cases/auth/logout.py`, `backend/src/main.py`, `backend/src/config/settings.py`.
- Admin and partner BFF API proxying:
  `admin/src/app/api/v1/[...path]/route.ts`, `partner/src/app/api/v1/[...path]/route.ts`, and related tests.
- Admin/partner 2FA forwarding and cookie handling:
  `admin/src/app/api/auth/2fa/*`, `partner/src/app/api/auth/2fa/*`.
- Generated OpenAPI/API client type files:
  `frontend/src/lib/api/generated/types.ts`, `admin/src/lib/api/generated/types.ts`, `partner/src/lib/api/generated/types.ts`.
- Frontend, admin, and partner UX/API changes around auth, local-stage behavior, metrics, translations, partner settings, and customer flows.

## Recommended Next Step

Treat the QA documentation as mergeable only after a clean docs-only branch is prepared from current `main`.

Treat the code changes as one or more separate merge requests, rebased on current `main`, with generated artifacts cleaned up and all release-readiness gates passing before production deployment.
