# S3-STAGE-16 Evidence: Production Disabled-State Deploy

**Date:** 2026-05-25
**Stage:** `S3-STAGE-16`
**Status:** Runtime deploy passed; GitLab CI runner/tag pipeline closure passed in `S3-STAGE-16A`
**Stage document:** `docs/cybervpn_stage3_launch_docs/16_STAGE3_PRODUCTION_DISABLED_STATE_DEPLOY.md`

---

## 1. Summary

S3 Stage 3 partner/reseller code was deployed to production in disabled-state mode.

Production release tag:

```text
s3-stage16-disabled-state.3
```

Tag target:

```text
e63418b4
```

Services deployed:

```text
backend
frontend
```

Services retagged but not recreated:

```text
admin
telegram-bot
task-worker
```

Previous rollback tag:

```text
main-0b454923
```

---

## 2. Pre-Deploy Checks

### Current Production Tag Before Deploy

```text
current_tag=main-0b454923
```

### Rollback Images

```text
rollback_image_ok=cybervpn/cybervpn-backend:main-0b454923
rollback_image_ok=cybervpn/cybervpn-frontend:main-0b454923
rollback_image_ok=cybervpn/cybervpn-admin:main-0b454923
rollback_image_ok=cybervpn/cybervpn-telegram-bot:main-0b454923
rollback_image_ok=cybervpn/cybervpn-task-worker:main-0b454923
```

### Public Smoke Before Deploy

```text
200 https://api.cyber-vpn.net/healthz
200 https://cyber-vpn.net/ru-RU/miniapp/home
200 https://admin.cyber-vpn.net/ru-RU/login
```

---

## 3. Production Flags

Production flags were explicitly set before restart:

```text
PARTNER_APPLICATIONS_ENABLED=false
PARTNER_ATTRIBUTION_ENABLED=false
PARTNER_CODES_ENABLED=false
PARTNER_EVENT_BACKBONE_ENABLED=false
PARTNER_EXPORTS_ENABLED=false
PARTNER_PAYOUTS_ENABLED=false
PARTNER_PORTAL_ENABLED=false
PARTNER_REPORTING_ENABLED=false
PARTNER_SETTLEMENT_SANDBOX_ENABLED=false
PARTNER_STOREFRONTS_ENABLED=false
PARTNER_WEBHOOKS_ENABLED=false
PAUSE_PARTNER_EXPANSION=true
NEXT_PUBLIC_PARTNER_PILOT_ENABLED=false
NEXT_PUBLIC_PARTNER_PORTAL_ENABLED=false
NEXT_PUBLIC_PARTNER_STOREFRONTS_ENABLED=false
```

---

## 4. Deploy Command

```bash
STAGE1_PROD_HOST=45.87.41.146 \
STAGE1_PROD_USER=deploy \
STAGE1_PROD_SSH_KEY_FILE=/home/beep/.ssh/MainKey2_private_fixed.pem \
STAGE1_PROD_COMPOSE_DIR=/srv/cybervpn/compose/app \
STAGE1_PROD_RELEASE_ROOT=/srv/cybervpn/releases \
STAGE1_RELEASE_TAG=s3-stage16-disabled-state.3 \
STAGE1_DEPLOY_EVIDENCE_DIR=docs/evidence/releases/s3-stage-16-deploy \
STAGE1_PUBLIC_SMOKE_URLS='https://api.cyber-vpn.net/healthz https://cyber-vpn.net/ru-RU/miniapp/home https://admin.cyber-vpn.net/ru-RU/login' \
bash scripts/deploy/stage1-gitlab-deploy.sh backend,frontend
```

Deploy script evidence:

```text
docs/evidence/releases/s3-stage-16-deploy/stage1-gitlab-deploy-s3-stage16-disabled-state.3.md
```

Observed public smoke from deploy script:

```text
200 0.647842 https://api.cyber-vpn.net/healthz
200 0.828618 https://cyber-vpn.net/ru-RU/miniapp/home
200 1.344957 https://admin.cyber-vpn.net/ru-RU/login
```

---

## 5. Post-Deploy Runtime State

```text
TAG=s3-stage16-disabled-state.3
cybervpn-backend: healthy
cybervpn-frontend: healthy
cybervpn-admin: healthy
cybervpn-telegram-bot: healthy
cybervpn-worker: healthy
cybervpn-scheduler: healthy
cybervpn-postgres: healthy
cybervpn-valkey: healthy
cybervpn-remnawave: healthy
```

Remote release source size after deploy-scope fix:

```text
99M /srv/cybervpn/releases/src-s3-stage16-disabled-state.3
```

Production disk state:

```text
/dev/vda1 232G total, 92G used, 141G available, 40% used
```

Backend/frontend recent log scan:

```text
No new error/exception/traceback/critical lines found in latest backend/frontend compose logs.
```

---

## 6. B2C Smoke

```text
200 0.601479 https://api.cyber-vpn.net/healthz
200 0.779882 https://cyber-vpn.net/ru-RU/miniapp/home
200 0.722495 https://admin.cyber-vpn.net/ru-RU/login
200 0.876457 https://cyber-vpn.net/ru-RU/pricing
200 0.860615 https://cyber-vpn.net/ru-RU/status
```

---

## 7. Partner Disabled-Boundary Smoke

### Partner Session

```text
GET /api/v1/partner-session/bootstrap
HTTP 404
X-CyberVPN-Partner-Boundary: partner_portal_disabled
{"code":"partner_portal_disabled","stage":"S3-STAGE-05"}
```

### Partner Application

```text
GET /api/v1/partner-application-drafts
HTTP 404
X-CyberVPN-Partner-Boundary: partner_portal_disabled
{"code":"partner_portal_disabled","stage":"S3-STAGE-05"}
```

### Storefront

```text
GET /api/v1/storefronts/demo/preview
HTTP 404
X-CyberVPN-Partner-Boundary: partner_storefronts_disabled
{"code":"partner_storefronts_disabled","stage":"S3-STAGE-09"}
```

### Payouts

```text
GET /api/v1/partner-payout-accounts
HTTP 404
X-CyberVPN-Partner-Boundary: partner_payouts_disabled
{"code":"partner_payouts_disabled","stage":"S3-STAGE-05"}
```

### Attribution

```text
GET /api/v1/attribution/resolve
HTTP 404
X-CyberVPN-Partner-Boundary: partner_attribution_disabled
{"code":"partner_attribution_disabled","stage":"S3-STAGE-08"}
```

---

## 8. CI Status

Original GitLab tag pipeline:

```text
Pipeline: https://gitlab.h.cyber-vpn.net/root/CyberVPN/-/pipelines/87
Ref: s3-stage16-disabled-state.3
Status: pending
Reason: jobs remain pending/created with no runner assigned
```

Root cause:

```text
The GitLab runner was protected, but the S3 release tag pattern was not protected.
Protected runners do not accept unprotected refs.
```

Closure evidence:

```text
docs/evidence/releases/s3-stage-16a-gitlab-ci-runner-tag-pipeline-closure-20260525.md
```

Passing closure tag pipeline:

```text
Pipeline: https://gitlab.h.cyber-vpn.net/root/CyberVPN/-/pipelines/93
Ref: s3-stage16-disabled-state.6
SHA: 7ccb8bd51cb2191450858c2b0224eb442c9484f4
Status: success
Duration: 923s
```

Hard CI result:

```text
gitlab:ci-contract success
backend:lint success
backend:test:smoke success
frontend:lint success
frontend:test success
frontend:build success
admin:lint success
admin:test success
admin:build success
telegram-bot:lint success
telegram-bot:test:smoke success
partner:stage3-artifacts success
partner:stage3-sandbox-pack success
secret-pattern-scan success
security:gitleaks success
npm-audit:high success
pip-audit:python-locks success
container-scan:trivy-grype success
sbom:release-candidate success
quality:release-comparison-report success
```

Allowed-failure warnings:

```text
partner:test failed allow_failure=true
task-worker:lint failed allow_failure=true
task-worker:test:smoke failed allow_failure=true
```

Production runtime remains on `s3-stage16-disabled-state.3`. CI closure passed on `s3-stage16-disabled-state.6`, which contains only CI/test/evidence hardening after the deployed runtime tag.

Local gates already passed before production deploy:

```text
backend S3 pack: 31 passed in 183.04s
frontend S3 pack: 3 files passed, 30 tests passed
npm audit --audit-level=high: no high/critical advisories
changed-file secret scan: no matches
git diff --check: clean
```

---

## 9. Deploy Tooling Fixes

Two aborted deploy attempts found a practical release-speed issue:

1. initial rsync copied large local runtime artifacts and reached `35G`;
2. second attempt still copied `frontend/.next-*` scratch builds and reached `7.6G`;
3. both partial release directories were removed from production;
4. deploy script now excludes heavy non-runtime trees and scratch builds;
5. final deploy source was `99M`.

Relevant commits:

```text
3beea05f fix: narrow production deploy sync scope
e63418b4 fix: exclude next scratch builds from deploy sync
```

---

## 10. Decision

```text
S3-STAGE-16_RUNTIME_DEPLOY_PASSED
S3-STAGE-16A_GITLAB_RUNNER_PROTECTED_TAG_CLOSED
S3-STAGE-16A_TAG_PIPELINE_PASSED_WITH_ALLOWED_FAILURE_WARNINGS
```

Production is stable on the disabled-state runtime, and the CI runner/pass gap is closed through `S3-STAGE-16A`.
