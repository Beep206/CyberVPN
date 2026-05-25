# S3-STAGE-16A Evidence: GitLab CI Runner And Tag Pipeline Closure

**Date:** 2026-05-25
**Stage:** `S3-STAGE-16A`
**Status:** Passed
**Product stage:** CyberVPN Partner / Reseller Platform
**Prior stage:** `S3-STAGE-16: Production Disabled-State Deploy`

---

## 1. Purpose

`S3-STAGE-16A` closes the residual GitLab CI blocker left by the production disabled-state deploy.

The production runtime was already healthy on:

```text
s3-stage16-disabled-state.3
```

But its GitLab tag pipeline remained pending because no protected runner accepted the unprotected S3 tag ref.

This stage proves:

1. the GitLab protected runner can execute S3 tag pipelines;
2. the S3 protected tag contract is configured;
3. hard GitLab CI jobs pass for the S3 disabled-state release line;
4. remaining failures are explicitly allowed-failure/non-blocking jobs.

---

## 2. Root Cause

Observed state before closure:

```text
Tag: s3-stage16-disabled-state.3
Pipeline: 87
Status: pending
Reason: no runner assigned
```

Runner state:

```text
GitLab Runner: online
Executor: docker
Runner access: protected
Tags: h-docker, protected
```

Root cause:

```text
The S3 release tag pattern was not protected in GitLab.
Protected runners do not pick up unprotected refs.
```

Fix:

```text
Protected tag pattern added: s3-stage*
Allowed creation level: maintainer/owner-controlled
```

No key rotation was required by this stage because no secret was changed or newly exposed.

---

## 3. Pipeline Attempts

| Tag | Commit | Pipeline | Result | Notes |
|---|---:|---:|---|---|
| `s3-stage16-disabled-state.3` | `e63418b4` | `87` | Pending | No runner assigned before tag protection was corrected. |
| `s3-stage16-disabled-state.4` | `e63418b4` | `89` | Failed | Runner worked; hard CI exposed stale frontend fixture date and route-boundary classification gap. |
| `s3-stage16-disabled-state.5` | `cb60e0b7` | `91` | Failed | Hard tests passed; `security:gitleaks` flagged synthetic identifiers in tests/evidence. |
| `s3-stage16-disabled-state.6` | `7ccb8bd5` | `93` | Passed | Hard jobs passed; only explicitly allowed-failure jobs remain red. |

---

## 4. Code And CI Fixes

### Frontend Test Fixture Stability

The customer-cabinet fixture used an already-expired timestamp:

```text
2026-05-24T00:00:00Z
```

Current date during closure:

```text
2026-05-25
```

The fixture was moved to a future stable test date:

```text
2030-05-24T00:00:00Z
```

Files:

```text
frontend/src/widgets/customer-cabinet/__tests__/customer-cabinet-model.test.ts
frontend/src/widgets/customer-cabinet/__tests__/customer-cabinet-dashboard.test.tsx
```

### Backend Route-Boundary Classification

The disabled-state storefront preview path is a public disabled-boundary endpoint and must be classified in S1/S2/S3 route-boundary smoke.

File:

```text
backend/tests/security/test_stage1_route_boundary.py
```

Change:

```text
/api/v1/storefronts
```

was added to the public prefix list.

### Secret Scan False Positives

`security:gitleaks` flagged synthetic `*_key` identifiers used in tests and evidence. These values are not credentials and are not runtime secrets.

File:

```text
.gitleaks.toml
```

The allowlist is narrow:

1. it targets only the `generic-api-key` rule;
2. it applies only to known Stage 3 evidence and Phase 4 e2e test files;
3. it matches only synthetic identifier names such as `event_key`, `period_key`, `idempotency_key`, and `partition_key`.

---

## 5. Local Verification

Frontend targeted tests:

```text
npm run test:run -w frontend -- src/widgets/customer-cabinet/__tests__/customer-cabinet-model.test.ts src/widgets/customer-cabinet/__tests__/customer-cabinet-dashboard.test.tsx
```

Result:

```text
2 files passed
18 tests passed
```

Backend targeted tests:

```text
cd backend && . .venv/bin/activate && pytest tests/unit/test_first_admin_bootstrap.py tests/security/test_stage1_route_boundary.py tests/security/test_stage1_webhook_idempotency.py --no-cov -q --tb=short
```

Result:

```text
21 passed
```

Backend lint:

```text
cd backend && . .venv/bin/activate && ruff check tests/security/test_stage1_route_boundary.py
```

Result:

```text
All checks passed
```

Frontend lint:

```text
npm run lint -w frontend -- src/widgets/customer-cabinet/__tests__/customer-cabinet-model.test.ts src/widgets/customer-cabinet/__tests__/customer-cabinet-dashboard.test.tsx
```

Result:

```text
Passed
```

Secret scan:

```text
SECURITY_ARTIFACT_DIR=/tmp/cybervpn-gitleaks-stage16a GITLEAKS_EXIT_CODE=1 bash scripts/security/scan-secrets.sh
```

Result:

```text
no leaks found
```

---

## 6. Passing GitLab Tag Pipeline

```text
Pipeline: https://gitlab.h.cyber-vpn.net/root/CyberVPN/-/pipelines/93
Ref: s3-stage16-disabled-state.6
SHA: 7ccb8bd51cb2191450858c2b0224eb442c9484f4
Status: success
Created: 2026-05-25T14:46:08.404+05:00
Updated: 2026-05-25T15:01:48.073+05:00
Duration: 923s
```

Required successful jobs:

| Stage | Job | Result |
|---|---|---|
| validate | `gitlab:ci-contract` | success |
| validate | `observability:stage2-artifacts` | success |
| validate | `partner:stage3-artifacts` | success |
| validate | `partner:stage3-sandbox-pack` | success |
| lint | `admin:lint` | success |
| lint | `backend:lint` | success |
| lint | `frontend:lint` | success |
| lint | `telegram-bot:lint` | success |
| lint | `partner:lint` | success |
| test | `admin:test` | success |
| test | `backend:test:smoke` | success |
| test | `frontend:test` | success |
| test | `telegram-bot:test:smoke` | success |
| build | `admin:build` | success |
| build | `frontend:build` | success |
| build | `partner:build` | success |
| security | `secret-pattern-scan` | success |
| security | `security:gitleaks` | success |
| security | `npm-audit:high` | success |
| security | `pip-audit:python-locks` | success |
| security | `container-scan:trivy-grype` | success |
| security | `sbom:release-candidate` | success |
| package | `quality:release-comparison-report` | success |

Allowed-failure warnings:

| Job | Result | Blocking? | Follow-up |
|---|---|---|---|
| `partner:test` | failed | No | Keep as S3 stabilization debt before wider partner expansion. |
| `task-worker:lint` | failed | No | Keep as worker cleanup debt before event backbone production enablement. |
| `task-worker:test:smoke` | failed | No | Keep as worker cleanup debt before event backbone production enablement. |

Manual package jobs:

```text
docker-package:* jobs remain manual/allowed and were not required for this CI closure.
```

---

## 7. Production Runtime Alignment

Production runtime remains on:

```text
s3-stage16-disabled-state.3
```

CI closure passed on:

```text
s3-stage16-disabled-state.6
```

The difference is accepted for this gate because `.6` contains only CI/test/evidence hardening after the deployed disabled-state runtime tag.

If strict tag/runtime equivalence is required later, production can be redeployed to `.6`; no partner runtime flag should be enabled by that redeploy.

---

## 8. Decision

```text
S3-STAGE-16A_GITLAB_RUNNER_PROTECTED_TAG_CLOSED
S3-STAGE-16A_TAG_PIPELINE_PASSED_WITH_ALLOWED_FAILURE_WARNINGS
S3-STAGE-16A_NO_KEY_ROTATION_REQUIRED
```

Recommended next stage:

```text
S3-STAGE-17: Controlled Partner Pilot
```
