# Stage 3 Production Disabled-State Deploy

**Stage:** `S3-STAGE-16`
**Status:** Runtime deploy passed; GitLab CI runner evidence pending
**Date:** 2026-05-25
**Product stage:** CyberVPN Partner / Reseller Platform
**Prior gate:** `S3-STAGE-15: Full Partner Staging Rehearsal`

---

## 1. Purpose

S3-STAGE-16 deploys Stage 3 partner/reseller code to production while keeping every public partner runtime surface disabled.

This stage is not a partner launch. It is a production compatibility and safety proof:

1. S2 B2C runtime remains available;
2. backend/frontend can run Stage 3 code in production;
3. partner portal/storefront/attribution/payout/event surfaces remain blocked;
4. rollback target exists and is usable.

---

## 2. Deployment Decision

Production disabled-state deployment used immutable tag:

```text
s3-stage16-disabled-state.3
```

Tag target:

```text
e63418b4
```

Deployment scope:

```text
backend,frontend
```

Unchanged services were retagged for compose compatibility:

```text
admin
telegram-bot
task-worker
```

No partner runtime was enabled.

---

## 3. Production Disabled-State Matrix

The following production flags must remain set exactly this way until an owner-approved S3-STAGE-17 pilot:

```text
PARTNER_PORTAL_ENABLED=false
PARTNER_APPLICATIONS_ENABLED=false
PARTNER_CODES_ENABLED=false
PARTNER_ATTRIBUTION_ENABLED=false
PARTNER_STOREFRONTS_ENABLED=false
PARTNER_REPORTING_ENABLED=false
PARTNER_SETTLEMENT_SANDBOX_ENABLED=false
PARTNER_WEBHOOKS_ENABLED=false
PARTNER_PAYOUTS_ENABLED=false
PARTNER_EVENT_BACKBONE_ENABLED=false
PARTNER_EXPORTS_ENABLED=false
PAUSE_PARTNER_EXPANSION=true
NEXT_PUBLIC_PARTNER_PORTAL_ENABLED=false
NEXT_PUBLIC_PARTNER_STOREFRONTS_ENABLED=false
NEXT_PUBLIC_PARTNER_PILOT_ENABLED=false
```

Observed production state after deploy:

```text
PARTNER_* flags: disabled
NEXT_PUBLIC_PARTNER_* flags: disabled
PAUSE_PARTNER_EXPANSION=true
```

---

## 4. Rollback Target

Rollback target before deploy:

```text
main-0b454923
```

Rollback images were verified before deploy:

```text
cybervpn/cybervpn-backend:main-0b454923
cybervpn/cybervpn-frontend:main-0b454923
cybervpn/cybervpn-admin:main-0b454923
cybervpn/cybervpn-telegram-bot:main-0b454923
cybervpn/cybervpn-task-worker:main-0b454923
```

Rollback command pattern:

```bash
cd /srv/cybervpn/compose/app
sudo sed -i 's/^CYBERVPN_IMAGE_TAG=.*/CYBERVPN_IMAGE_TAG=main-0b454923/' .env
sudo docker compose up -d cybervpn-backend cybervpn-frontend
```

---

## 5. Deploy Notes

During the first deploy attempt, the deploy rsync scope was too broad and started copying large monorepo runtime artifacts.

Closed during this stage:

1. stopped partial rsync attempts;
2. removed partial remote release directories;
3. added deploy excludes for `.venv`, `.next`, `.next-*`, build/dist/mobile/desktop/protocol trees, docs and evidence;
4. repeated deploy with `s3-stage16-disabled-state.3`;
5. final remote release source size was reduced to `99M`.

This improves release speed and reduces production disk risk.

---

## 6. Runtime Evidence

Evidence file:

```text
docs/evidence/releases/s3-stage-16-production-disabled-state-deploy-20260525.md
docs/evidence/releases/s3-stage-16-deploy/stage1-gitlab-deploy-s3-stage16-disabled-state.3.md
```

Runtime status after deploy:

```text
CYBERVPN_IMAGE_TAG=s3-stage16-disabled-state.3
backend: healthy
frontend: healthy
admin: healthy
telegram-bot: healthy
worker/scheduler: healthy
postgres/valkey/remnawave: healthy
```

Public B2C smoke:

```text
200 https://api.cyber-vpn.net/healthz
200 https://cyber-vpn.net/ru-RU/miniapp/home
200 https://admin.cyber-vpn.net/ru-RU/login
200 https://cyber-vpn.net/ru-RU/pricing
200 https://cyber-vpn.net/ru-RU/status
```

Partner disabled-boundary smoke:

```text
/api/v1/partner-session/bootstrap -> 404 partner_portal_disabled
/api/v1/partner-application-drafts -> 404 partner_portal_disabled
/api/v1/storefronts/demo/preview -> 404 partner_storefronts_disabled
/api/v1/partner-payout-accounts -> 404 partner_payouts_disabled
/api/v1/attribution/resolve -> 404 partner_attribution_disabled
```

---

## 7. CI Evidence Status

GitLab pipeline for tag `s3-stage16-disabled-state.3`:

```text
Pipeline: https://gitlab.h.cyber-vpn.net/root/CyberVPN/-/pipelines/87
Status: pending
Reason: jobs remain pending/created with no runner assigned
```

This means the runtime deploy is complete, but the formal `GitLab CI pass` requirement is not closed yet.

Before S3-STAGE-17, the GitLab runner queue must be restored and the S3 tag pipeline or an equivalent owner-approved CI pipeline must pass.

---

## 8. Exit Criteria Check

| Exit criterion | Result |
|---|---|
| Immutable tag exists | Passed: `s3-stage16-disabled-state.3`. |
| Production env flags explicit | Passed. |
| Portal hidden/gated | Passed through backend disabled boundary and frontend flags. |
| Payouts disabled | Passed. |
| Storefronts disabled | Passed. |
| Event backbone disabled | Passed. |
| Rollback target exists | Passed: `main-0b454923`. |
| Production remains stable | Passed for smoke endpoints and container health. |
| S2 B2C flow unaffected | Passed for public health, Mini App, admin login, pricing and status probes. |
| No unauthorized partner surface public | Passed for sampled public partner API routes. |
| GitLab CI pass | Pending: runner not assigned. |

---

## 9. Decision

```text
S3-STAGE-16_RUNTIME_DEPLOY_PASSED
S3-STAGE-16_CI_EVIDENCE_PENDING
```

Do not start `S3-STAGE-17: Controlled Partner Pilot` until CI runner/pass evidence is closed or owner explicitly accepts that residual risk.

Recommended next working step:

```text
S3-STAGE-16A: GitLab CI Runner And Tag Pipeline Closure
```

