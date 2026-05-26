# S3-STAGE-18 Evidence: Live Partner Surface Runtime Check

**Date:** 2026-05-26  
**Stage:** `S3-STAGE-18`  
**Scope:** partner runtime publication and live surface verification  
**Production partner tag:** `main-9b907151`  
**Previous partner tag:** `main-406f867f`  
**Pipeline:** GitLab `#130` on `main` / `9b90715111216254fe00b97bf6a5b462d1417249`

## Purpose

Continue publication and verification of the partner runtime as a live S3 surface without expanding the external partner cohort yet.

This check stays inside the existing `S3-STAGE-18` stabilization scope:

- continue controlled/internal partner pilot;
- keep live payouts blocked;
- keep live postback delivery blocked;
- do not create `S3-STAGE-19`;
- do not expand external partners until owner provides the pilot list.

## Runtime Change

A production runtime cache permission issue was found after deploying `main-406f867f`:

```text
Failed to update prerender cache for /ru-RU/partner Error: EACCES: permission denied, mkdir '/app/.next/server/app/ru-RU/partner.segments'
```

Root cause:

- Next.js Cache Components/PPR can write runtime prerender/cache segment files under `.next/server/app`.
- The workspace Docker image switched to non-root user `node`, but `.next` was still owned by root after build.

Fix:

```text
infra/deploy/stage1/Dockerfile.next-workspace
RUN chown -R node:node /app/.next
```

Local image permission proof:

```text
uid=1000(node) gid=1000(node) groups=1000(node),1000(node)
node:node 755 /app/.next
node:node 755 /app/.next/server
node:node 755 /app/.next/server/app
```

## Deploy Evidence

Detailed deploy transcript:

```text
docs/evidence/releases/s3-partner-live-surface-20260526T132301Z/stage1-gitlab-deploy-main-9b907151.md
```

Deploy summary:

```text
current tag: main-406f867f
new tag: main-9b907151
services: partner
cybervpn-partner recreated
deployment complete
```

## Production Container Health

```text
cybervpn-partner    cybervpn/cybervpn-partner:main-9b907151    healthy
cybervpn-backend    cybervpn/cybervpn-backend:main-1ae18f32     healthy
cybervpn-frontend   cybervpn/cybervpn-frontend:main-1ae18f32    healthy
cybervpn-admin      cybervpn/cybervpn-admin:main-1ae18f32       healthy
cybervpn-nats       nats:2.12.7-alpine                          healthy
cybervpn-worker     cybervpn/cybervpn-task-worker:main-1ae18f32 healthy
cybervpn-scheduler  cybervpn/cybervpn-task-worker:main-1ae18f32 healthy
```

## Public Smoke

```text
https://partner.cyber-vpn.net/healthz          200 0.677859
https://partner.cyber-vpn.net/ru-RU/login      200 0.817092
https://partner.cyber-vpn.net/ru-RU/dashboard  200 0.974239
https://partner.cyber-vpn.net/ru-RU/register   200 0.815064
https://partner.cyber-vpn.net/ru-RU/partner    200 0.941544
https://partner.cyber-vpn.net/ru-RU/codes      200 0.918056
https://partner.cyber-vpn.net/ru-RU/finance    200 0.924925
https://partner.cyber-vpn.net/ru-RU/settings   200 1.151278
https://cyber-vpn.net/ru-RU/partner            302 0.574063
https://my.cyber-vpn.net/ru-RU/partner         302 0.647547
```

## Edge / HTTP/3 Check

```text
HTTP/2 200
alt-svc: h3=":443"; ma=86400
cf-cache-status: DYNAMIC
server: cloudflare
```

Result: Cloudflare HTTP/3/QUIC advertisement remains enabled.

## Runtime Log Check

Command checked partner logs after live traffic:

```text
sudo docker logs --since 15m --tail 500 cybervpn-stage1-cybervpn-partner-1
```

Filtered patterns:

```text
EACCES|error|exception|fatal|warn|denied|failed
```

Result:

```text
No matching log lines after deploying main-9b907151.
```

The previous `.next` prerender cache permission error is no longer present.

## GitLab Pipeline

Pipeline `#130` was created for `main` commit `9b90715111216254fe00b97bf6a5b462d1417249`.

Final status:

```text
manual
```

Automatic required jobs:

```text
secret-pattern-scan            success
security:gitleaks              success
npm-audit:high                 success
pip-audit:python-locks         success
container-scan:trivy-grype     success after retry
sbom:release-candidate         success
stage2:release-evidence-pack   success
stage2:deploy:dry-run          success
```

Note:

- The first `container-scan:trivy-grype` attempt failed while downloading Grype from GitHub with `curl: (35) Recv failure: Connection reset by peer`.
- The failed attempt was retried as job `1682`.
- Retry passed.
- The final pipeline is `manual` only because deploy/preflight jobs are intentionally manual.

## Decision

```text
S3-STAGE-18_LIVE_PARTNER_SURFACE_CHECK_PASSED
S3-STAGE-18_PARTNER_RUNTIME_PUBLISHED_AS_LIVE_SURFACE
S3-STAGE-18_CACHE_PERMISSION_TAIL_CLOSED
S3-STAGE-18_KEEP_LIVE_PAYOUTS_BLOCKED
S3-STAGE-18_KEEP_LIVE_POSTBACKS_BLOCKED
S3-STAGE-18_WAIT_FOR_EXTERNAL_PARTNER_LIST_BEFORE_EXPANSION
```

## Next Work

Continue inside `S3-STAGE-18`:

1. Daily live partner surface watch.
2. Owner-provided external pilot partner/user list intake.
3. Finance profile/postback classification for each external pilot candidate.
4. Manual support watch for first external partner actions.
5. No live payout or postback delivery until a separate owner decision.
