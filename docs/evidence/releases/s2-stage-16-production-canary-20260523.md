# S2-STAGE-16 Production Canary Release Evidence

**Stage:** `S2-STAGE-16: Production Canary Release`
**Date:** 2026-05-23
**Release candidate:** `stage2-public-rc.5`
**Runtime host:** `prod-app-1`
**VPN node:** `de-1.cyber-vpn.org`
**Result:** `CANARY_RUNTIME_DEPLOYED_WITH_OWNER_LIVE_FLOW_PENDING`

---

## 1. Scope

This evidence records the first Stage 2 production canary deploy.

The goal was to move the approved Stage 2 RC into the rented production app runtime, keep the VPN node node-only, keep observability active, open only invite-gated registration, and leave broad public opening for the later Go/No-Go stage.

This stage did not open unrestricted public registration.

---

## 2. Inputs

```text
RC tag: stage2-public-rc.5
RC commit: 3c3a7b1a95019252e91550ffb08e754bbc794c98
GitLab tag pipeline: 68 success
Previous production app tag: stage1-direct-suburl-refresh-20260522T091303Z
Pre-deploy backup: /srv/cybervpn/backups/daily-20260523T085847Z
```

Pre-deploy backup result:

```text
cybervpn_table_count=121
remnawave_table_count=36
status=ok
```

---

## 3. Deployment Path

The deploy was run from a detached worktree checked out exactly at `stage2-public-rc.5`.

This was intentional: the local `main` branch had a docs-only evidence commit after the immutable tag, and production runtime must be deployed from the immutable release identity, not floating `main`.

Services targeted:

```text
backend
frontend
admin
telegram-bot
worker
scheduler
```

---

## 4. Initial Deploy Blocker And Rollback

The first deploy attempt built and recreated the Stage 2 images, but backend did not become healthy.

Observed backend startup blocker:

```text
GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET are required in production when google OAuth login is enabled.
```

Impact:

```text
api.cyber-vpn.net/health returned 502 during the failed backend startup window.
```

Immediate action:

```text
Runtime was rolled back to stage1-direct-suburl-refresh-20260522T091303Z.
API /health returned 200 after rollback.
All rolled-back app services became healthy.
```

Root cause:

```text
Production runtime had OAUTH_ENABLED_LOGIN_PROVIDERS=google,github but did not have production Google/GitHub OAuth client credentials configured.
The new Stage 2 backend correctly fails closed in this state.
```

Resolution for this canary:

```text
OAUTH_ENABLED_LOGIN_PROVIDERS=
OAUTH_TRUSTED_EMAIL_LINK_PROVIDERS=
```

This matches the S2 auth readiness rule: OAuth is conditional and remains disabled until production credentials and callback evidence exist.

---

## 5. Canary Runtime State

After the OAuth runtime config correction, app services were moved back to `stage2-public-rc.5`.

Observed runtime:

```text
CYBERVPN_IMAGE_TAG=stage2-public-rc.5
cybervpn-admin          healthy
cybervpn-backend        healthy
cybervpn-frontend       healthy
cybervpn-scheduler      healthy
cybervpn-telegram-bot   healthy
cybervpn-worker         healthy
```

Runtime auth posture:

```text
environment=production
registration_enabled=True
registration_invite_required=True
oauth_enabled_login_providers=
oauth_web_base_url=https://cyber-vpn.net
```

Interpretation:

```text
Stage 2 canary is invite-gated. New public users still need invite access. OAuth login buttons must remain hidden/disabled until credentials are added and callback evidence is captured.
```

---

## 6. Public Route Probes

Observed after canary deploy:

```text
https://cyber-vpn.net/ru-RU                              http=200
https://cyber-vpn.net/ru-RU/register                     http=200
https://cyber-vpn.net/ru-RU/miniapp/home                 http=200
https://admin.cyber-vpn.net/ru-RU/login                  http=200
https://api.cyber-vpn.net/health                         http=200
https://api.cyber-vpn.net/docs                           http=404
https://cyber-vpn.org/                                   http=301 redirect=https://cyber-vpn.net/
https://cyber-vpn.org/api/sub/<redacted-invalid-token>   http=404
```

HTTP/3/QUIC remained enabled:

```text
alt-svc: h3=":443"; ma=86400
strict-transport-security: max-age=31536000; includeSubDomains; preload
```

---

## 7. Invite-Gated Registration Probe

Negative registration probe without invite:

```text
POST /api/v1/auth/register
result=http 403
body=Registration requires a valid invite token.
```

Interpretation:

```text
Registration is enabled for canary, but invite gate is enforced.
```

---

## 8. Payment And Orphan Queue Snapshot

Observed database counters:

```text
payment_attempts_nonterminal_gt24h=0
payments_nonterminal_gt24h=0
```

No real-money payment mutation was executed by automation in this step.

---

## 9. VPN Node Boundary

Observed on `de-1.cyber-vpn.org`:

```text
cybervpn-remnawave-node Up
listening ports: 22, 443, 8443, 22230
```

No app, database, observability, GitLab or payment containers were observed on the VPN node.

---

## 10. Observability

Home observability readiness checks passed:

```text
Prometheus ready
Grafana database ok
Alertmanager ready
Sentry health ok
```

Customer runtime remains on rented production infrastructure and does not depend on the home observability host for serving users.

---

## 11. Known Issues / Controlled Gaps

| Item | Status | Decision |
|---|---|---|
| Google/GitHub OAuth credentials absent | Controlled gap | OAuth providers disabled for canary; enable only after credentials and callback evidence |
| First deploy attempt triggered backend fail-closed | Resolved operationally | Rollback succeeded, then canary runtime deployed with safe OAuth config |
| Real owner/user payment or trial flow | Pending owner live check | Execute manually in canary before cohort expansion |
| Real VPN client connection proof after S2 RC deploy | Pending owner live check | Owner/internal user must confirm subscription delivery and VPN IP/protocol |
| Refund/expiry simulation | Pending | Use admin-safe simulation before broad public opening |

---

## 12. Exit Status

`S2-STAGE-16` is not a full public opening. It is a controlled production canary.

Current status:

```text
CANARY_RUNTIME_DEPLOYED_WITH_OWNER_LIVE_FLOW_PENDING
```

Proceed to broad public Go/No-Go only after:

1. owner/internal user completes live Mini App/Bot login;
2. invite-gated registration is tested with a real invite;
3. trial or selected canary payment path succeeds;
4. provisioning completes;
5. `.org` subscription URL is delivered;
6. VPN client connects and reports expected node/protocol;
7. support/admin can see the user/subscription/payment/provisioning state;
8. no P0/P1 alert remains open during the watch window.

Next stage after owner live proof:

```text
S2-STAGE-17: Public Release 1.0 Go/No-Go
```
