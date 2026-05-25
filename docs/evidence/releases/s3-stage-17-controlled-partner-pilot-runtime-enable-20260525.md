# S3-STAGE-17 Evidence: Controlled Partner Pilot Runtime Enablement

**Date:** 2026-05-25
**Stage:** `S3-STAGE-17`
**Status:** Runtime enablement passed; pilot partner onboarding pending
**Stage document:** `docs/cybervpn_stage3_launch_docs/17_STAGE3_CONTROLLED_PARTNER_PILOT.md`

---

## 1. Summary

Stage 3 partner/reseller runtime was enabled in production for controlled pilot preparation.

Final production runtime:

```text
CYBERVPN_IMAGE_TAG=s3-stage17-controlled-partner-pilot.3
```

Final release commit:

```text
ea0ccca2
```

Production runtime was changed from disabled-state Stage 3 code to S3 controlled pilot runtime.

---

## 2. GitLab Tag Pipeline

Primary S3-STAGE-17 tag:

```text
s3-stage17-controlled-partner-pilot.1
Pipeline: 96
Status: success
```

Follow-up tags:

```text
s3-stage17-controlled-partner-pilot.2
Purpose: backend event-backbone startup logging fix
```

```text
s3-stage17-controlled-partner-pilot.3
Purpose: final runtime alignment, including PARTNER_EXPORTS_ENABLED backend env visibility
Pipeline: 102
Status: success
```

`.2` and `.3` contain narrow runtime-enablement fixes after the `.1` green tag pipeline.

---

## 3. Local And CI Checks Before Deploy

Local checks:

```text
docker compose config --quiet with temporary required env files: passed
stage1 deploy dry-run for backend/frontend: passed
frontend partner/Mini App targeted tests: 3 files passed, 25 tests passed
backend route-boundary targeted test: 4 passed
backend ruff for nats_partner_runtime.py: passed
logger extra smoke: passed
git diff --check: clean
npm audit --audit-level=high: passed, no high/critical findings; known moderate advisories remain
gitleaks secret scan: passed, no leaks found
changed-file dangerous-pattern scan: passed, no matches
```

GitLab hard pipeline for `.1`:

```text
Pipeline 96: success
```

GitLab hard pipeline for final runtime tag `.3`:

```text
Pipeline 102: success
```

Allowed-failure warnings remain the known Stage 3 debt:

```text
partner:test allow_failure=true
task-worker:lint allow_failure=true
task-worker:test:smoke allow_failure=true
```

---

## 4. Runtime Flags

Production `.env` was backed up before enablement:

```text
.env.pre-s3-stage17-controlled-partner-pilot-20260525T125101Z
```

Final production flag snapshot:

```text
NATS_URL=nats://cybervpn-nats:4222
NEXT_PUBLIC_PARTNER_PILOT_ENABLED=true
NEXT_PUBLIC_PARTNER_PORTAL_ENABLED=true
NEXT_PUBLIC_PARTNER_STOREFRONTS_ENABLED=true
PARTNER_APPLICATIONS_ENABLED=true
PARTNER_ATTRIBUTION_ENABLED=true
PARTNER_CODES_ENABLED=true
PARTNER_EVENT_BACKBONE_ENABLED=true
PARTNER_EXPORTS_ENABLED=true
PARTNER_PAYOUTS_ENABLED=true
PARTNER_PORTAL_ENABLED=true
PARTNER_REPORTING_ENABLED=true
PARTNER_SETTLEMENT_SANDBOX_ENABLED=true
PARTNER_STOREFRONTS_ENABLED=true
PARTNER_WEBHOOKS_ENABLED=true
PAUSE_PARTNER_EXPANSION=false
```

Backend container env proof:

```text
NATS_URL=nats://cybervpn-nats:4222
PARTNER_APPLICATIONS_ENABLED=true
PARTNER_ATTRIBUTION_ENABLED=true
PARTNER_CODES_ENABLED=true
PARTNER_EVENT_BACKBONE_ENABLED=true
PARTNER_EXPORTS_ENABLED=true
PARTNER_PAYOUTS_ENABLED=true
PARTNER_PORTAL_ENABLED=true
PARTNER_REPORTING_ENABLED=true
PARTNER_SETTLEMENT_SANDBOX_ENABLED=true
PARTNER_STOREFRONTS_ENABLED=true
PARTNER_WEBHOOKS_ENABLED=true
```

---

## 5. Deployment Attempts

### Tag `.1`

Services deployed:

```text
backend
frontend
```

NATS was added and became healthy, frontend became healthy, but backend failed startup.

Root cause:

```text
Logger._log() got an unexpected keyword argument 'consumers'
```

Resolution:

```text
backend/src/infrastructure/messaging/nats_partner_runtime.py
```

changed the startup log call to use `extra={"consumers": ...}`.

### Tag `.2`

Services deployed:

```text
backend
```

Result:

```text
backend health: passed
B2C public smoke: passed
```

### Tag `.3`

Services deployed:

```text
backend
```

Result:

```text
backend health: passed
B2C public smoke: passed
PARTNER_EXPORTS_ENABLED visible in backend container env
```

Deploy script evidence:

```text
docs/evidence/releases/s3-stage-17-deploy/stage1-gitlab-deploy-s3-stage17-controlled-partner-pilot.2.md
docs/evidence/releases/s3-stage-17-deploy/stage1-gitlab-deploy-s3-stage17-controlled-partner-pilot.3.md
```

---

## 6. Container Health

Final production container state:

```text
cybervpn-stage1-cybervpn-admin-1 running healthy
cybervpn-stage1-cybervpn-backend-1 running healthy
cybervpn-stage1-cybervpn-frontend-1 running healthy
cybervpn-stage1-cybervpn-nats-1 running healthy
cybervpn-stage1-cybervpn-postgres-1 running healthy
cybervpn-stage1-cybervpn-postgres-exporter-1 running healthy
cybervpn-stage1-cybervpn-redis-exporter-1 running healthy
cybervpn-stage1-cybervpn-remnawave-1 running healthy
cybervpn-stage1-cybervpn-remnawave-postgres-1 running healthy
cybervpn-stage1-cybervpn-remnawave-valkey-1 running healthy
cybervpn-stage1-cybervpn-scheduler-1 running healthy
cybervpn-stage1-cybervpn-telegram-bot-1 running healthy
cybervpn-stage1-cybervpn-valkey-1 running healthy
cybervpn-stage1-cybervpn-worker-1 running healthy
```

Backend log proof:

```text
Partner event backbone runtime started
```

---

## 7. NATS/JetStream Proof

NATS health:

```text
{"status":"ok"}
```

JetStream snapshot:

```text
streams=1
consumers=2
messages=0
bytes=0
api.errors=0
```

NATS is internal-only and has no public published port.

---

## 8. B2C Smoke

Final public smoke:

```text
200 https://api.cyber-vpn.net/healthz
200 https://cyber-vpn.net/ru-RU/miniapp/home
200 https://admin.cyber-vpn.net/ru-RU/login
200 https://cyber-vpn.net/ru-RU/pricing
200 https://cyber-vpn.net/ru-RU/status
```

---

## 9. Partner Boundary Smoke

The expected result after enablement is not necessarily `200` for unauthenticated requests. The important proof is that S3 disabled-boundary headers are gone and routes now reach auth, method or domain-level handling.

```text
/api/v1/partner/dashboard -> 401, boundary=none, INVALID_TOKEN
/api/v1/partner/codes -> 401, boundary=none, INVALID_TOKEN
/api/v1/partner-application-drafts -> 405, boundary=none, Method Not Allowed
/api/v1/storefronts/demo/preview -> 404, boundary=none, Storefront not found
/api/v1/partner-payout-accounts/ -> 401, boundary=none, Not authenticated
/api/v1/payouts/instructions -> 401, boundary=none, Not authenticated
/api/v1/attribution/touchpoints -> 401, boundary=none, Not authenticated
/api/v1/reporting/outbox-events -> 401, boundary=none, Not authenticated
```

Frontend unauthenticated `/ru-RU/partner` still returns `404` because the dashboard route guard hides operator/partner dashboard routes from unauthenticated or unauthorized users.

---

## 10. Pilot Data State

Current production DB counts:

```text
partner_accounts=0
partner_account_users=0
partner_codes=0
storefronts=1
partner_payout_accounts=0
outbox_events_pending=0
```

This is intentional for runtime enablement: the platform is open at runtime level, but the first pilot partner/workspace/code still needs to be created under owner control.

---

## 11. Rollback Evidence

Rollback targets:

```text
s3-stage16-disabled-state.3
.env.pre-s3-stage17-controlled-partner-pilot-20260525T125101Z
docker-compose.yml.pre-s3-stage17-controlled-partner-pilot.3
```

Rollback action:

```text
Set partner flags back to false, set PAUSE_PARTNER_EXPANSION=true, redeploy backend/frontend or restore disabled-state tag.
```

---

## 12. Security Review

Post-deploy local security review was executed against the Stage 17 change set.

```text
npm audit --audit-level=high: passed
Known residual npm audit output: 5 moderate advisories
Gitleaks scan: passed, no leaks found
Static dangerous-pattern scan over changed runtime/docs files: passed
git diff --check: clean
```

The moderate npm advisories are not introduced by the Stage 17 runtime enablement and remain tracked as dependency maintenance debt.

---

## 13. Decision

```text
S3-STAGE-17_RUNTIME_ENABLEMENT_PASSED
S3-STAGE-17_PILOT_PARTNER_ONBOARDING_PENDING
```

Next working step:

```text
S3-STAGE-17A: First Pilot Partner Workspace And Code Proof
```
