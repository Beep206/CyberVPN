# STAGE1-PUB-03A RC Blocker Triage And Fixes

Date: 2026-05-10  
Stage: Stage 1 Controlled Public Beta  
Parent gate: `STAGE1-PUB-03 Release Candidate Packaging`  
Result: `PARTIAL_GO_REPEAT_STAGING_RC_PACKAGING_AFTER_ADMIN_CONTRACT_CLEANUP`

## Decision

Do not create `stage1-beta-rc.1` yet.

`STAGE1-PUB-03A` closed the backend RC blockers and the S1-relevant admin dependency/container security blockers that could be safely fixed locally. The remaining blocker is the admin test contract suite: it is improved but still not clean enough for an immutable RC tag.

## Fixes Applied

| Area | Fix | Evidence |
|---|---|---|
| Backend support templates | Main S1 support template list now contains the five live support cases; privacy deletion/export templates remain available by category lookup | `backend-stage1-tests-after-support-template-fix.txt` |
| Backend local test environment | Re-ran Stage 1 backend tests with explicit `ENVIRONMENT=test`, `SWAGGER_ENABLED=false`, local PostgreSQL and local Valkey/Redis | `backend-stage1-tests-after-support-template-fix.txt` |
| Admin API client tests | In `NODE_ENV=test`, admin API client uses `NEXT_PUBLIC_API_URL + /api/v1` so Vitest/happy-dom/MSW do not break on relative fetch URLs | `admin-tests-after-pub03a-fixes.txt` |
| Admin 2FA route | 2FA complete route now forwards backend cookies and falls back to JSON token payload only when test/runtime headers do not expose `Set-Cookie` | `admin-targeted-touch-2fa-final.txt` |
| Admin touch-target test contract | Admin auth touch-target test now checks the real login client instead of non-existent admin register/forgot-password pages | `admin-targeted-touch-2fa-final.txt` |
| Admin domain default | Admin production default domain moved from `admin.ozoxy.ru` to `admin.cyber-vpn.net` | `admin-build-after-pub03a-fixes.txt` |
| Admin dependency findings | `axios` upgraded to `^1.16.0`; `fast-uri` resolved to `3.1.2` through admin lockfile/override | `dependency-audit-after-fixes.txt` |
| Task worker container | Runtime image now runs as non-root `workeruser` | `docker-build-task-worker-after-nonroot-fix.txt` |

## Verification Summary

| Check | Result | Notes |
|---|---:|---|
| Backend Stage 1 tests | PASS | `436 passed` |
| Backend support/privacy targeted tests | PASS | `25 passed` |
| Admin lint | PASS | ESLint clean |
| Admin build | PASS | Next build succeeds |
| Admin touch-target + 2FA targeted tests | PASS | `6 passed` |
| Admin full test suite | FAIL | `15 failed`, `72 passed`; `46 failed`, `502 passed` |
| Admin/package npm high audit | PASS | Only moderate Next/PostCSS remains |
| Full dependency audit | PASS | NPM high threshold passes; Python audits pass |
| Task worker image build | PASS | Local image user is `workeruser` |
| Trivy full-repo scan | REVIEW | S1 admin dependency findings and task-worker root-user finding are removed |
| Grype full-repo scan | INCONCLUSIVE | Grype DB download failed with `unexpected EOF`; Trivy evidence exists |
| Final secret scan | PASS | No leaks found |
| Final static dangerous-pattern scan | PASS | No matches in touched runtime files |

## Security Triage

### Closed S1-Relevant Findings

- `admin/package-lock.json` no longer reports the previous high `axios` findings.
- `admin/package-lock.json` no longer reports the previous high `fast-uri` findings.
- `services/task-worker/Dockerfile` no longer reports the root-user Dockerfile finding; rebuilt image has `user=workeruser`.

### Remaining High/Critical Findings

Remaining Trivy high/critical findings are not part of the S1 runtime deploy scope:

- `SDK/python-sdk-production/poetry.lock`
- `apps/desktop-client/src-tauri/Cargo.lock`
- `packages/beep-protocol/Cargo.lock`
- `packages/verta-protocol/Cargo.lock`
- `services/helix-adapter/Cargo.lock`
- `services/helix-node/Cargo.lock`
- `partner/package-lock.json`

Recommended triage status for S1:

- `future-stage excluded`: desktop client, SDK, Beep/Verta/Helix and partner portal artifacts.
- `S1 blocker`: none from the high/critical dependency list after this pass.
- `S1 infra review`: Helm chart security-context findings remain, but Kubernetes/Talos/GitOps are explicitly not S1 blockers under the current topology decision.

## Remaining Admin Test Blocker

The admin full suite is still not RC-clean. Main groups:

- Old public marketing SEO expectations still reference `vpn.ozoxy.ru` and broad locale rollout behavior, while S1 admin is `admin.cyber-vpn.net` with a narrow admin locale/config surface.
- Legacy API auth tests still expect localStorage/tokenStorage-era `"No refresh token"` behavior, while the current S1 auth direction uses httpOnly cookies.
- A small set of API handler/MSW contracts still needs alignment after the axios/test-base-url fix.

Recommendation:

Do not weaken runtime behavior to satisfy stale tests. Create a focused admin contract cleanup pass that either updates these tests to the S1 admin scope or moves copied public-marketing SEO tests out of the admin RC gate.

## Local Resource Cleanup

Local `remnawave-db` and `remnawave-redis` were stopped after backend verification to avoid keeping Docker resources running.

No Docker containers are running at the end of this task.

## Next Required Step

Run `STAGE1-PUB-03B: Admin RC Contract Cleanup`, then repeat `STAGE1-PUB-03` and create `stage1-beta-rc.1` only after the admin RC gate is clean or explicitly owner-accepted.
