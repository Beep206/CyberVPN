# S2-STAGE-17 Public Release 1.0 Go/No-Go Evidence

**Stage:** `S2-STAGE-17: Public Release 1.0 Go/No-Go`
**Date:** 2026-05-23
**Owner decision:** approved in chat by project owner
**Runtime host:** `prod-app-1`
**Runtime release tag:** `stage2-public-rc.5`
**Runtime commit:** `3c3a7b1a95019252e91550ffb08e754bbc794c98`
**VPN node:** `de-1.cyber-vpn.org`
**Decision:** `GO_PUBLIC_RELEASE_1_0_WITH_CONTROLLED_RESIDUALS`

---

## 1. Decision Summary

CyberVPN is opened from S2 production canary into Public Release 1.0 with controlled residuals.

The public runtime is not expanded into every planned S2 option at once. The release opens the B2C public entry path while keeping unsafe or unproven paths gated:

- public registration is open without invite requirement;
- Telegram Stars remains enabled for Telegram Bot/Mini App paid flow;
- generic payment rails remain disabled until provider-specific live callback evidence exists;
- Google/GitHub OAuth remains disabled until production credentials and callback evidence exist;
- `.org` remains node/subscription-boundary only and is not used as a public customer mirror;
- the production VPN node remains node-only.

This decision is based on owner approval plus the runtime, route, backup, rollback, observability, VPN boundary and payment/orphan checks below.

---

## 2. Release Inputs

| Item | Value |
|---|---|
| Previous stage | `S2-STAGE-16: Production Canary Release` |
| Canary evidence | `docs/evidence/releases/s2-stage-16-production-canary-20260523.md` |
| Runtime tag | `stage2-public-rc.5` |
| GitLab tag pipeline | pipeline 68 passed all hard jobs |
| Pre-open backup | `/srv/cybervpn/backups/daily-20260523T100609Z` |
| Legal/trust pack | public routes return HTTP 200 |
| Observability | active on home observability server |
| Owner approval | received in chat on 2026-05-23 |

Pre-open backup transcript:

```text
started_at_utc=2026-05-23T10:06:09+00:00
backup_dir=/srv/cybervpn/backups/daily-20260523T100609Z
cybervpn_table_count=121
remnawave_table_count=36
finished_at_utc=2026-05-23T10:06:11+00:00
status=ok
```

Backup artifacts observed:

```text
/srv/cybervpn/backups/daily-20260523T100609Z/cybervpn-20260523T100609Z.dump
/srv/cybervpn/backups/daily-20260523T100609Z/remnawave-20260523T100609Z.dump
```

Rollback evidence remains available from S2 backup/DR gate:

```text
/srv/cybervpn/backups/s2-stage12-20260523T050454Z/rollback-command.txt
/srv/cybervpn/backups/s2-stage12-20260523T050454Z/rollback-dry-run.log
```

---

## 3. Runtime Change Applied

The public registration gate was opened on `prod-app-1`.

Runtime state after the change:

```text
environment=production
registration_enabled=True
registration_invite_required=False
oauth_enabled_login_providers=
payments_enabled=False
telegram_stars_enabled=True
```

Runtime env snapshot:

```text
REGISTRATION_ENABLED=true
REGISTRATION_INVITE_REQUIRED=false
OAUTH_ENABLED_LOGIN_PROVIDERS=
PAYMENTS_ENABLED=false
TELEGRAM_STARS_ENABLED=true
PAYMENT_AUTORENEWAL_ENABLED=false
PAYMENT_ORPHAN_MAX_AGE_HOURS=24
```

Interpretation:

- users can register publicly without an invite;
- email verification still applies;
- Google/GitHub OAuth buttons must remain hidden/disabled;
- Telegram Stars XTR checkout paths are allowed where implemented;
- generic checkout/payment rails remain paused;
- autoprolongation remains disabled.

---

## 4. Runtime Health

Observed on `prod-app-1` after opening public registration:

```text
cybervpn-admin                running   healthy
cybervpn-backend              running   healthy
cybervpn-frontend             running   healthy
cybervpn-postgres             running   healthy
cybervpn-postgres-exporter    running   healthy
cybervpn-redis-exporter       running   healthy
cybervpn-remnawave            running   healthy
cybervpn-remnawave-postgres   running   healthy
cybervpn-remnawave-valkey     running   healthy
cybervpn-scheduler            running   healthy
cybervpn-telegram-bot         running   healthy
cybervpn-valkey               running   healthy
cybervpn-worker               running   healthy
```

Production image identity:

```text
CYBERVPN_IMAGE_TAG=stage2-public-rc.5
```

The runtime is served from the immutable release candidate image set. The public-opening change is runtime configuration, not a new code build.

---

## 5. Public Route Probes

Observed after public opening:

```text
https://cyber-vpn.net/ru-RU                              http=200
https://cyber-vpn.net/ru-RU/register                     http=200
https://cyber-vpn.net/ru-RU/pricing                      http=200
https://cyber-vpn.net/ru-RU/miniapp/home                 http=200
https://admin.cyber-vpn.net/ru-RU/login                  http=200
https://api.cyber-vpn.net/health                         http=200
https://api.cyber-vpn.net/docs                           http=404
https://cyber-vpn.org/                                   http=301 redirect=https://cyber-vpn.net/
https://cyber-vpn.org/api/sub/<redacted-invalid-token>   http=404
```

HTTP/3/QUIC remained enabled and must not be disabled:

```text
alt-svc: h3=":443"; ma=86400
strict-transport-security: max-age=31536000; includeSubDomains; preload
```

---

## 6. Legal And Trust Routes

Public legal/support routes were checked as part of the Go/No-Go gate:

```text
https://cyber-vpn.net/ru-RU/terms              http=200
https://cyber-vpn.net/ru-RU/privacy-policy     http=200
https://cyber-vpn.net/ru-RU/refund-policy      http=200
https://cyber-vpn.net/ru-RU/acceptable-use     http=200
https://cyber-vpn.net/ru-RU/cookie-policy      http=200
https://cyber-vpn.net/ru-RU/contact            http=200
https://cyber-vpn.net/ru-RU/status             http=200
https://cyber-vpn.net/ru-RU/help               http=200
```

---

## 7. Public Registration Proof

No-invite registration was tested after opening `REGISTRATION_INVITE_REQUIRED=false`.

Request:

```text
POST https://api.cyber-vpn.net/api/v1/auth/register
invite token: omitted
```

Observed response:

```text
http=201
message=Registration successful. Please check your email for verification code.
is_active=false
is_email_verified=false
```

Interpretation:

- no invite token is required for public registration;
- the user is created as inactive/unverified until email verification;
- this is expected for the public auth flow.

The smoke account was created only for release proof and remains a controlled production test artifact.

---

## 8. Payment And Orphan Queue Snapshot

Runtime payment posture:

```text
PAYMENTS_ENABLED=false
TELEGRAM_STARS_ENABLED=true
CRYPTOBOT_ENABLED=false
YOOKASSA_ENABLED=false
PAYRAM_ENABLED=false
NOWPAYMENTS_ENABLED=false
DIGISELLER_ENABLED=false
PAYMENT_RECONCILIATION_ENABLED=false
PAYMENT_AUTORENEWAL_ENABLED=false
PAYMENT_ORPHAN_MAX_AGE_HOURS=24
```

Observed database counters:

```text
payment_attempts_nonterminal_gt24h|0
payments_nonterminal_gt24h|0
```

Decision:

- Telegram Stars is accepted as the limited S2 paid path for Telegram/Mini App where the Stars endpoint is used;
- all generic provider rails remain disabled until provider-specific live callback and reconciliation evidence exists;
- no paid-but-no-access or orphan backlog older than 24 hours was observed.

---

## 9. VPN Node Boundary

Observed on `de-1.cyber-vpn.org`:

```text
cybervpn-remnawave-node   Up
listening ports: 22, 443, 8443, 22230
```

No app, database, observability, GitLab or payment containers were observed on the VPN node.

This preserves the rule: the node hosts only the VPN node role.

---

## 10. Observability

Home observability remains active and is treated as operational visibility, not as a customer runtime dependency.

Observed checks:

```text
Prometheus Server is Ready.
Alertmanager ready.
Sentry health: ok.
```

Observed relevant containers on the home observability server:

```text
cybervpn-prometheus
cybervpn-alertmanager
cybervpn-grafana
cybervpn-uptime-kuma
cybervpn-loki
cybervpn-blackbox-exporter
cybervpn-cadvisor
cybervpn-node-exporter
cybervpn-gitlab-runner
sentry-self-hosted-* healthy/up
```

Risk note:

```text
If the home server or home internet is down, customer-facing runtime stays available, but observability coverage is reduced until the home stack recovers.
```

---

## 11. Go / No-Go Matrix

| Gate | Status | Evidence / Decision |
|---|---:|---|
| S2-STAGE-00 through S2-STAGE-16 complete or accepted | Pass | S2 evidence exists through `S2-STAGE-16`; owner approved moving to S2-STAGE-17 |
| Public registration | Pass | `REGISTRATION_ENABLED=true`, `REGISTRATION_INVITE_REQUIRED=false`, no-invite registration returns `201` |
| At least one limited payment path | Accepted with scope | Telegram Stars flag is enabled; generic provider rails remain disabled |
| Subscription URL delivery | Accepted from prior canary/S1 proof | `.org` subscription boundary is preserved; invalid token returns `404` |
| VLESS/XHTTP behavior | Accepted from prior owner proof | Owner previously confirmed working VPN client connection through production node; continue monitoring |
| Support can operate | Pass | Support/legal routes public; admin login route available; alert channel previously configured |
| Legal pack public | Pass | legal/trust routes return `200` |
| Observability active | Pass | Prometheus, Alertmanager and Sentry checks pass |
| Backup/restore/rollback evidence | Pass | pre-open backup completed; rollback dry-run artifacts exist |
| No high/critical security blocker | Pass with controlled residuals | OAuth disabled; generic payment rails disabled; `/docs` returns `404` |
| Owner accepts residual risks | Pass | owner explicitly approved moving to S2-STAGE-17 |

---

## 12. Residual Risks Accepted For Public Release 1.0

| Risk | Why accepted | Control |
|---|---|---|
| Generic payment providers disabled | Production callback/reconciliation evidence is not complete for CryptoBot/YooKassa/PayRam/NOWPayments/Digiseller | Keep `PAYMENTS_ENABLED=false`; open provider rails one by one with evidence |
| OAuth disabled | Production Google/GitHub credentials are absent | Keep `OAUTH_ENABLED_LOGIN_PROVIDERS=` until callback evidence exists |
| Smoke registration account remains pending verification | Expected auth behavior | Treat as controlled release artifact; remove later if desired |
| Home observability outage would reduce visibility | Home server is intentionally non-customer-critical | Customer runtime stays on rented servers; continue stabilization checks |
| Public admin login route is reachable | Admin UI is intentionally public-login, not public-data | Keep strong auth/2FA/RBAC controls and monitor logs |
| `prod-app-1` has pending OS updates | Not a runtime blocker during launch window | Schedule maintenance after stabilization |

---

## 13. Final Decision

```text
GO_PUBLIC_RELEASE_1_0_WITH_CONTROLLED_RESIDUALS
```

CyberVPN is opened for Public Release 1.0 B2C entry on 2026-05-23.

The release is intentionally conservative:

1. public registration is open;
2. Telegram/Mini App path remains available;
3. Telegram Stars is the limited enabled paid rail;
4. generic payment providers, OAuth and autoprolongation remain gated;
5. observability/stabilization must continue immediately in `S2-STAGE-18`.

---

## 14. Documentation And Security Checks

Local checks before committing this evidence:

```text
git diff --check
result=pass
```

```text
SECURITY_ARTIFACT_DIR=.tmp/s2-stage17-security-docs GITLEAKS_EXIT_CODE=1 bash scripts/security/scan-secrets.sh
result=no leaks found
scanned_bytes=159096060
```

---

## 15. Next Stage

```text
S2-STAGE-18: Post-Launch Stabilization And S3 Readiness
```

Immediate stabilization checks:

1. watch Sentry critical errors;
2. watch Alertmanager;
3. watch Telegram Bot/Mini App login and checkout;
4. watch registration verification failures;
5. watch payment/orphan queues;
6. watch provisioning failures;
7. watch support contacts;
8. watch VPN node health;
9. confirm backup continuity;
10. classify known issues before any broader marketing push.
