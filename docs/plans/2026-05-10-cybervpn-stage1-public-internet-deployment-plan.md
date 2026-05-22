# CyberVPN Stage 1 Public Internet Deployment Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Prepare and deploy CyberVPN Stage 1 as a controlled public beta on the internet with customer web, Telegram, payment, provisioning, support, observability, backup and rollback evidence.

**Architecture:** The prepared home server `cybervpn-h-ops` is the current no-cost public operations edge for Stage 1 deployment work. GitHub remains the external source-of-truth/fallback, home GitLab runs protected CI/evidence jobs, Caddy is the public HTTPS edge, and observability/Sentry/GitLab live under `*.h.cyber-vpn.net`. Customer-facing Stage 1 domains must be routed through Caddy or an approved external edge, but no secret, database, payment or Remnawave credential may be committed to the repository.

**Tech Stack:** Ubuntu 24.04, Docker Compose, Caddy, Cloudflare DNS/TLS, GitHub, home GitLab, GitLab Runner, GitLab Registry, Next.js 16/React 19, FastAPI/Python 3.13, PostgreSQL 17, Valkey/Redis, Telegram Bot, CryptoBot-first payment path, Remnawave, Prometheus/Grafana/Loki/Alertmanager, Sentry Self-Hosted, restic backups.

---

## Source Documents

Read these before execution:

- `docs/plans/2026-05-10-cybervpn-h-public-launch-readiness.md`
- `.private/cybervpn-h-10.10.10.34-access.md`
- `docs/cybervpn_stage1_launch_docs/06_STAGE1_IMPLEMENTATION_BACKLOG.md`
- `docs/cybervpn_stage1_launch_docs/07_STAGE1_ACCEPTANCE_GATES.md`
- `docs/cybervpn_stage1_launch_docs/08_STAGE1_GO_LIVE_RUNBOOK.md`
- `docs/cybervpn_stage1_launch_docs/91_STAGE1_REL_007_EVIDENCE_PACK_INDEX.md`
- `docs/gitlab/README.md`
- `docs/gitlab/HOME_SERVER_GITLAB_PREP.md`

Security rule: `.private/cybervpn-h-10.10.10.34-access.md` is for local execution only. Do not copy values from it into docs, GitLab issues, CI logs, shell history, screenshots or release evidence.

## Current Readiness Summary

Infrastructure state:

```text
GO with known risks
```

Application state:

```text
NO-GO until CyberVPN application services, Remnawave/VPN node health, payment checks, app metrics, release evidence and rollback evidence are completed.
```

Known blockers before public beta:

- Rotate setup-shared credentials: Cloudflare DNS token, MaxMind license key, Telegram alert bot token and Resend API key.
- Review/disable MikroTik UPnP exposure.
- Add offsite backup target or explicitly accept the no-offsite risk for a tiny beta.
- Triage high/critical security scan findings and record accepted risks.
- Fix RAM visibility/balance or explicitly accept the hardware risk.
- Deploy CyberVPN app services.
- Connect Remnawave and at least one healthy VPN node.
- Clear `Stage1NoHealthyRemnawaveNodes`.
- Prove payment sandbox/live path before enabling paid beta.
- Capture a real Stage 1 Grafana baseline before inviting beta users: app metrics, payment/provisioning metrics, support/admin signals, Sentry events, Loki logs and alert delivery.

## Deployment Domain Model

Keep operations and customer surfaces separated.

| Domain | Purpose | Stage 1 target |
|---|---|---|
| `gitlab.h.cyber-vpn.net` | Home GitLab | Already prepared |
| `registry.h.cyber-vpn.net` | Home GitLab registry/cache | Already prepared |
| `grafana.h.cyber-vpn.net` | Observability UI | Already prepared |
| `sentry.h.cyber-vpn.net` | Sentry UI/ingest | Already prepared |
| `prometheus.h.cyber-vpn.net` | Internal metrics UI | Already prepared, protected |
| `loki.h.cyber-vpn.net` | Internal logs UI/API | Already prepared, protected |
| `alerts.h.cyber-vpn.net` | Alertmanager UI/API | Already prepared, protected |
| `uptime.h.cyber-vpn.net` | Uptime Kuma | Already prepared, protected |
| `cyber-vpn.net` / `www.cyber-vpn.net` | Public marketing + customer cabinet | Add Caddy route and Cloudflare rules |
| `api.cyber-vpn.net` | Backend API, payment webhooks, Telegram webhooks | Add Caddy route and no-challenge webhook exceptions |
| `admin.cyber-vpn.net` | Admin UI/API entry | Add protected route, 2FA/RBAC/audit required |
| `status.cyber-vpn.net` | Status page | Add static/status route or Uptime-backed public page |
| `cyber-vpn.org` | VPN node/subscription zone | Serve only approved `/api/sub*` subscription delivery; all other customer web traffic redirects to `.net` |
| `admin.cyber-vpn.org` | Not used for S1 admin | Must not serve an independent admin session; redirect or refuse traffic |

Do not publish customer-facing services under `*.h.cyber-vpn.net` except for temporary internal smoke tests.

## Stage Execution Overview

| Stage | Name | Exit condition |
|---|---|---|
| STAGE1-PUB-00 | Freeze And Risk Review | No accidental secrets, no uncontrolled worktree, owner accepts home-public beta risks |
| STAGE1-PUB-01 | Runtime Access And Edge Safety | Temporary bootstrap values are rotated; firewall/WAF posture documented |
| STAGE1-PUB-02 | GitLab And CI Alignment | Home GitLab mirror/pipeline runs on protected runner tags |
| STAGE1-PUB-03 | Release Candidate Packaging | RC tag, image digests, SBOM and security scan evidence exist |
| STAGE1-PUB-04 | Runtime Secrets And Env | Server env files exist with `0600 root root`, no values in Git |
| STAGE1-PUB-05 | App Compose And Internal Network | App containers defined with healthchecks/resource limits and no direct public ports |
| STAGE1-PUB-06 | Data Services | PostgreSQL/Valkey ready, migrations and backup/restore proven |
| STAGE1-PUB-07 | Backend/API/Admin Deploy | API/admin healthy, Swagger off, CORS/cookies/CSRF/rate limits verified |
| STAGE1-PUB-08 | Frontend And Public Web Deploy | Marketing/cabinet/status pages reachable over HTTPS |
| STAGE1-PUB-09 | Telegram Bot And Mini App Deploy | Webhook, bot commands, Mini App routes and linking smoke pass |
| STAGE1-PUB-10 | Remnawave And VPN Node Deploy | Control-plane and node metrics healthy; trial provisioning works |
| STAGE1-PUB-11 | Payment Path Deploy | Sandbox/live minimal payment path, webhook signature and idempotency proven |
| STAGE1-PUB-12 | Observability Integration | Logs, metrics, Sentry events, alerts and dashboards show real app data |
| STAGE1-PUB-13 | Security/Legal/Support Gate | Legal pages, support mailboxes, templates, RBAC, 2FA and scans are ready |
| STAGE1-PUB-14 | Backup, Restore And Rollback Gate | App backup/restore and rollback dry-run evidence exist |
| STAGE1-PUB-15 | Final Go/No-Go And Beta Cohort | Owner go/no-go signed, first beta cohort can be invited |
| STAGE1-PUB-16 | Stabilization Loop | Daily review proves Stage 1 can continue or expand |

---

## Stage 1 Metrics Contract

This contract is based on the current `10.10.10.34` Grafana/Prometheus server state. The server already has the following relevant dashboards provisioned:

- `stage1-controlled-public-beta`
- `cybervpn-h-hardware`
- `cybervpn-infrastructure`
- `logs-overview`
- `cybervpn-api`
- `cybervpn-application`
- `cybervpn-auth-registration`
- `cybervpn-otp`
- `telegram-native-login`
- `cybervpn-miniapp-runtime`
- `cybervpn-worker`
- `cybervpn-postgres`
- `cybervpn-redis`
- `slo-tracking`
- `cybervpn-error-monitoring`
- `cybervpn-edge-observability`
- `cybervpn-control-plane-observability`

Stage 2/Stage 3/Helix dashboards may stay provisioned for planning and lab work, but they must not imply Stage 1 runtime enablement.

For Stage 1, Grafana must collect and display these metric families from the first public beta day:

| Area | Required Stage 1 signals |
|---|---|
| Service availability | `up`/target health for backend, worker, Telegram bot, frontend/admin edge, PostgreSQL, Redis/Valkey, Remnawave, Grafana, Prometheus, Loki, Alertmanager, Sentry, GitLab, Uptime Kuma, blackbox probes |
| Public edge | HTTPS probe success, latency, TLS expiry, Caddy/upstream 4xx/5xx, no-challenge webhook routes, mirror redirect health |
| Product funnel | registrations, auth attempts/success ratio, OTP sent/verified/error, Telegram identity/linking, trial activations, plan/checkout starts, Mini App bootstrap/config delivery |
| Payments | provider invoice created/paid/expired/failed, webhook received/verified/rejected, duplicate webhook idempotency, payment success ratio, paid-but-no-access queue size, max orphan age, reconciliation launch blocker |
| VPN provisioning | `trial/pay -> VPN ready` success ratio, median/p95 latency, Remnawave API errors, retry queue, QR/subscription/config generation, credential regeneration, expiry/grace disable |
| Remnawave/VPN node | Remnawave API up, healthy node count, node status, online users, total users, node traffic where available, process RSS/heap/event-loop p99 |
| API/backend | request rate, p95/p99 latency, 5xx ratio, route-level failures for auth/payments/provisioning/support/admin, rate-limit hits, Sentry errors by service/release |
| Worker/scheduler | queue depth, tasks in progress, task duration p50/p95, error ratio, retry/dead-letter count, payment reconciliation task, provisioning retry task, expiry disable task |
| PostgreSQL | target up, active connections, hit ratio, commit/rollback rate, rollback ratio, slow/error indicators where available, backup freshness |
| Redis/Valkey | target up, memory used/max memory, rejected connections, evicted keys, connected/blocked clients, command rate, hit/miss ratio |
| Telegram/Mini App | bot update rate by type/status, bot error ratio, webhook health, Mini App checkout commits, payment status checks, config delivery success/failure |
| Admin/support | support open items, paid-but-no-access escalations, support SLA first response, admin privileged actions, audit-log write failures, refund/support contact readiness |
| Logs/traces | Loki logs by service/level with safe labels, correlated synthetic incident log sample, traces only if Tempo/span pipeline is actually enabled |
| Sentry | redacted event from backend, worker, bot, frontend and admin; release/environment tags; no PII/secrets in event payloads |
| Home host hardware | SMART health, NVMe wear, disk temperature, RAS/MCE/AER errors, RAM available, swap used, disk usage, iowait, network errors, container CPU/memory, Docker JSON log size |
| Backup/restore | backup age, restore drill evidence age, restic snapshot evidence, app DB backup freshness, Remnawave backup/export/rebuild evidence |
| Alert delivery | Alertmanager active alerts, Telegram delivery smoke, backup email smoke, P0/P1 routing and silence policy |

Stage 1 beta expansion is blocked if the `stage1-controlled-public-beta` dashboard is not showing real app data for payments, provisioning, Remnawave, worker queues and paid-but-no-access reconciliation.

## STAGE1-PUB-00: Freeze And Risk Review

**Purpose:** Lock the deployment scope before touching live public routes.

**Latest evidence:** `docs/evidence/releases/stage1-pub-00-freeze-20260510T154942Z.md`  
**Latest result:** GO to `STAGE1-PUB-01` with known risks.

**Files:**

- Read: `docs/cybervpn_stage1_launch_docs/22_STAGE1_REL_002_DIRTY_WORKTREE_SCOPE_MAP.md`
- Read: `docs/plans/2026-05-10-cybervpn-h-public-launch-readiness.md`
- Read: `.private/cybervpn-h-10.10.10.34-access.md`
- Modify if needed: `docs/cybervpn_stage1_launch_docs/21_STAGE1_EXECUTION_PLAN_AND_WORK_QUEUE.md`
- Create evidence: `docs/evidence/releases/stage1-pub-00-freeze-YYYYMMDDTHHMMSSZ.md`

**Steps:**

1. Run `git status --short` and save the output.
2. Confirm `.private/` is ignored: `rg -n '^\\.private/?$|\\.private/' .gitignore`.
3. Run current-tree secret scan.
4. Confirm no Stage 3/partner/mobile/desktop/Helix runtime is enabled for Stage 1.
5. Record owner risk acceptance for home-public controlled beta if customer runtime is deployed on the home server.

**Commands:**

```bash
git status --short
rg -n '^\.private/?$|\.private/' .gitignore
bash scripts/security/scan-secrets.sh
python scripts/validate_gitlab_ci_contract.py
```

**Exit criteria:**

- Worktree state is known.
- `.private/` stays untracked.
- No new secret leak is present.
- Stage 1 scope is frozen.

---

## STAGE1-PUB-01: Runtime Access And Edge Safety

**Purpose:** Close the highest-risk infrastructure issues before public customer routing.

**Latest evidence:**

- `docs/evidence/security/stage1-pub-01-token-rotation-redacted-20260510T161807Z.md`
- `docs/evidence/routeros/stage1-pub-01-upnp-firewall-review-20260510T161807Z.md`

**Latest result:** GO for deployment preparation. Owner decision after review: setup-key rotation is not required for the current controlled/tiny beta, provided secret files remain root-only, values stay out of Git/evidence/CI logs, and any future suspected exposure triggers immediate rotation.

**Files:**

- Read: `.private/cybervpn-h-10.10.10.34-access.md`
- Update private only: `.private/cybervpn-h-10.10.10.34-access.md`
- Create evidence: `docs/evidence/security/stage1-pub-01-token-rotation-redacted-YYYYMMDDTHHMMSSZ.md`
- Create evidence: `docs/evidence/routeros/stage1-pub-01-upnp-firewall-review-YYYYMMDDTHHMMSSZ.md`

**Steps:**

1. Confirm whether Cloudflare DNS API token, MaxMind license key, Telegram alert bot token and Resend API key require rotation.
2. If owner says rotation is not required, record that decision and keep the values server-side only.
3. If rotation is required later, update only server-side secret files and the private access sheet.
4. Confirm secret files are `0600 root root`.
5. Confirm no secret value appears in Git, CI logs or evidence.
6. Restart affected services.
7. Validate Caddy DNS-01 renewal path.
8. Review MikroTik UPnP and remove/disable unrelated dynamic forwards.
9. Add/verify Cloudflare WAF/rate-limit baseline for customer routes.

**Server commands:**

```bash
ssh beep@10.10.10.34
sudo -v
sudo caddy validate --config /etc/caddy/Caddyfile
sudo systemctl reload caddy
sudo systemctl status caddy --no-pager
sudo ufw status verbose
docker ps --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}'
```

**Exit criteria:**

- Owner rotation decision exists with values redacted.
- Public `80/tcp` and `443/tcp` are the only intended public forwards.
- Caddy validates and reloads.
- Cloudflare WAF/rate limiting plan is attached.

---

## STAGE1-PUB-02: GitLab And CI Alignment

**Purpose:** Make the repository runnable in home GitLab without depending on GitLab for emergency production recovery.

**Latest evidence:** `docs/evidence/gitlab/stage1-pub-02-gitlab-ci-20260510T162541Z.md`  
**Latest result:** PARTIAL GO for deployment preparation. GitLab server, mirror timer and protected runner are ready; real CyberVPN project pipeline proof is pending until the current GitLab CI files are committed, pushed and mirrored.

**Files:**

- Modify if needed: `.gitlab-ci.yml`
- Modify if needed: `docs/gitlab/README.md`
- Modify if needed: `infra/gitlab-runner/README.md`
- Create evidence: `docs/evidence/gitlab/stage1-pub-02-gitlab-ci-YYYYMMDDTHHMMSSZ.md`

**Steps:**

1. Confirm GitHub `main` is the current external fallback.
2. Confirm GitHub -> GitLab mirror is healthy.
3. Confirm GitLab Runner has tags `h-docker` and `protected`.
4. Ensure `.gitlab-ci.yml` jobs use the actual protected runner tags.
5. Keep DIND/manual Docker jobs disabled unless a separate protected DIND runner exists.
6. Run `gitlab:ci-contract`.
7. Run one path-based app pipeline in GitLab.

**Commands:**

```bash
git remote -v
git rev-parse HEAD
python scripts/validate_gitlab_ci_contract.py
```

**Exit criteria:**

- GitLab pipeline starts from mirrored `main`.
- Protected runner executes at least one validation job.
- CI logs do not expose secrets.
- GitHub remains usable as external fallback.

---

## STAGE1-PUB-03: Release Candidate Packaging

**Purpose:** Build a deployable Stage 1 candidate with reproducible artifacts.

**Current evidence status, 2026-05-10:** `NO-GO_FOR_IMMUTABLE_RC_TAG`.

Evidence was generated under `docs/evidence/releases/stage1-beta-rc.1/` and `docs/evidence/security/stage1-beta-rc.1/security-artifacts/`. Local S1 runtime images build successfully for backend, Telegram bot and task worker, frontend/admin production builds pass, SBOM and Trivy/Grype scan artifacts exist. The Git tag `stage1-beta-rc.1` was intentionally not created because backend/admin tests and high/critical security triage are not clean enough for an immutable public beta release candidate.

Before proceeding to `STAGE1-PUB-04`, run a short `STAGE1-PUB-03A` blocker pass:

1. Fix or owner-accept admin test failures.
2. Fix backend production Swagger/OpenAPI exposure or prove the environment-specific production gate.
3. Re-run backend tests with local Redis/PostgreSQL dependencies available.
4. Triage full-repo high/critical scan findings into S1 blocker, future-stage excluded, accepted risk or false positive.
5. Remediate or owner-accept S1-relevant admin dependency findings and task-worker container root-user misconfiguration.

**STAGE1-PUB-03A result, 2026-05-10:** `PARTIAL_GO_REPEAT_STAGING_RC_PACKAGING_AFTER_ADMIN_CONTRACT_CLEANUP`.

Evidence: `docs/evidence/releases/stage1-pub-03a-rc-blockers/STAGE1_PUB_03A_RC_BLOCKER_TRIAGE_AND_FIXES.md`.

Closed in 03A:

- Backend Stage 1 tests now pass with explicit test environment and local PostgreSQL/Valkey dependencies.
- Support template contract is aligned: five live S1 support templates remain primary, privacy deletion/export templates stay available through privacy lookup.
- S1 admin dependency high findings for `axios` and `fast-uri` are remediated.
- Task worker runtime image now runs as non-root `workeruser`.
- Admin lint/build pass, and targeted admin 2FA/touch-target tests pass.

Still blocking immutable `stage1-beta-rc.1`:

- Admin full test suite remains stale/unclean: `15 failed`, `72 passed`; `46 failed`, `502 passed`.
- Remaining admin failures are mainly copied public-marketing SEO/locale expectations, old tokenStorage-era auth expectations, and residual API/MSW contract alignment.

Run `STAGE1-PUB-03B: Admin RC Contract Cleanup` before repeating this packaging gate.

**STAGE1-PUB-03B result, 2026-05-10:** `PASS_REPEAT_STAGE1_PUB_03`.

Evidence: `docs/evidence/releases/stage1-pub-03b-admin-rc-contract-cleanup/STAGE1_PUB_03B_ADMIN_RC_CONTRACT_CLEANUP.md`.

Closed in 03B:

- Admin full test suite is clean: `87 passed`, `556 tests passed`.
- Admin lint and production build pass.
- Admin `robots.txt` and `sitemap.xml` are no longer placeholders.
- Axios 1.16 test transport is pinned to the Node `http` adapter for MSW interception while browser runtime still uses same-origin `/api/v1`.
- Admin tests now reflect S1 cookie-auth, `ru-RU` / `en-EN` locale rollout, admin canonical domain and `/payments/crypto/invoice` payment path.

Repeat `STAGE1-PUB-03` after this cleanup.

**STAGE1-PUB-03 rerun after 03B, 2026-05-10:** `PASS_ARTIFACT_CHECKS_NO_IMMUTABLE_TAG`.

Evidence: `docs/evidence/releases/stage1-beta-rc.1-rerun-after-03b/STAGE1_PUB_03_RERUN_AFTER_03B.md`.

Closed by the rerun:

- Frontend lint/tests/build pass.
- Admin lint/tests/build pass.
- Backend Stage 1 tests pass.
- Telegram bot and task-worker Stage 1 test packs pass.
- Backend, Telegram bot and task-worker local images build.
- SBOM, dependency audit, filesystem scan and secret scan evidence exist.

The immutable `stage1-beta-rc.1` tag was not created because the verified fixes/evidence are still in an uncommitted working tree. Create the tag only after committing the approved S1 snapshot.

**Files:**

- Create tag: `stage1-beta-rc.1`
- Create evidence: `docs/evidence/releases/stage1-beta-rc.1/`
- Create evidence: `docs/evidence/security/stage1-beta-rc.1/`

**Steps:**

1. Run dependency audits.
2. Run frontend/admin/backend/bot/worker targeted tests.
3. Build runtime images or production artifacts.
4. Generate SBOM.
5. Run Trivy/Grype scans.
6. Record image digests and commit SHA.
7. Create `stage1-beta-rc.1` only after scans and tests are understood.

**Commands:**

```bash
npm audit --audit-level=high
bash scripts/security/audit-dependencies.sh
bash scripts/security/generate-sbom.sh
bash scripts/security/scan-filesystem-vulnerabilities.sh
git tag stage1-beta-rc.1
```

**Exit criteria:**

- RC commit SHA is recorded.
- Image digests or artifact hashes are recorded.
- Security findings are triaged as blocker, accepted risk, or false positive.
- No production deployment uses floating `main`.

---

## STAGE1-PUB-04: Runtime Secrets And Env

**Purpose:** Materialize production-like runtime configuration on the server without putting secrets into Git.

**Files on server:**

- Create: `/srv/cybervpn-h/secrets/app.env`
- Create: `/srv/cybervpn-h/secrets/payments.env`
- Create: `/srv/cybervpn-h/secrets/telegram-bot.env`
- Create: `/srv/cybervpn-h/secrets/remnawave.env`
- Create: `/srv/cybervpn-h/secrets/sentry-runtime.env`
- Create: `/srv/cybervpn-h/secrets/frontend.env`
- Create: `/srv/cybervpn-h/secrets/admin.env`

**Repository files:**

- Modify if needed: `backend/.env.example`
- Modify if needed: `services/telegram-bot/.env.example`
- Modify if needed: `services/task-worker/.env.example`
- Create evidence: `docs/evidence/security/stage1-pub-04-env-inventory-redacted-YYYYMMDDTHHMMSSZ.md`

**Steps:**

1. Create server env files as `root`.
2. Set mode `0600`.
3. Use only placeholder/redacted inventory in Git.
4. Validate each service can read its required env vars.
5. Confirm no env file appears in `git status`.

**Server commands:**

```bash
sudo install -m 0600 -o root -g root /dev/null /srv/cybervpn-h/secrets/app.env
sudo install -m 0600 -o root -g root /dev/null /srv/cybervpn-h/secrets/payments.env
sudo install -m 0600 -o root -g root /dev/null /srv/cybervpn-h/secrets/telegram-bot.env
sudo install -m 0600 -o root -g root /dev/null /srv/cybervpn-h/secrets/remnawave.env
sudo install -m 0600 -o root -g root /dev/null /srv/cybervpn-h/secrets/sentry-runtime.env
sudo ls -l /srv/cybervpn-h/secrets/*.env
```

**Exit criteria:**

- All required env categories exist.
- File modes are correct.
- Secret values are absent from Git, CI logs and evidence.

---

## STAGE1-PUB-05: App Compose And Internal Network

**Purpose:** Define the CyberVPN Stage 1 runtime on the server.

**Files:**

- Create: `infra/deploy/stage1/docker-compose.stage1.yml`
- Create: `infra/deploy/stage1/Caddyfile.stage1.snippet`
- Create on server: `/srv/cybervpn-h/compose/app/docker-compose.yml`
- Create on server: `/srv/cybervpn-h/configs/app/`
- Create evidence: `docs/evidence/releases/stage1-pub-05-compose-YYYYMMDDTHHMMSSZ.md`

**Required services:**

- `cybervpn-backend`
- `cybervpn-worker`
- `cybervpn-telegram-bot`
- `cybervpn-frontend`
- `cybervpn-admin`
- `cybervpn-postgres` if no external managed DB is used for this beta
- `cybervpn-valkey` if no external managed Valkey is used for this beta

**Rules:**

- Public traffic goes through Caddy only.
- Internal app ports bind to `127.0.0.1` or Docker internal networks.
- Every service has healthcheck.
- Every service that can emit metrics exposes an internal-only `/metrics` endpoint or a documented exporter target.
- Prometheus scrape labels must include stable `job`, `service`, `environment` and `stage` values.
- Every service has memory/CPU limits.
- Logs go to Docker JSON logs with rotation and safe labels for Loki/Promtail service filtering.
- App logs must not include secrets, raw payment payloads, raw Telegram `initData`, full subscription URLs or VPN credentials.
- No service mounts Docker socket.

**Commands:**

```bash
docker compose -f infra/deploy/stage1/docker-compose.stage1.yml config
```

**Exit criteria:**

- Compose config renders.
- No unintended `0.0.0.0` service ports are exposed.
- Service names and healthchecks are stable.
- Metrics/log labels match the Stage 1 metrics contract.

---

## STAGE1-PUB-06: Data Services

**Purpose:** Make database and queue/cache state recoverable before deploying application writes.

**Files:**

- Create on server: `/srv/cybervpn-h/compose/app/postgres/`
- Create on server: `/srv/cybervpn-h/compose/app/valkey/`
- Create evidence: `docs/evidence/backups/stage1-pub-06-app-db-backup-YYYYMMDDTHHMMSSZ.md`
- Create evidence: `docs/evidence/restores/stage1-pub-06-app-db-restore-YYYYMMDDTHHMMSSZ.md`

**Steps:**

1. Decide DB mode for this no-cost Stage 1 beta:
   - preferred production-grade: external managed PostgreSQL/Valkey;
   - accepted no-cost beta: local PostgreSQL/Valkey on `cybervpn-h-ops` with explicit risk acceptance.
2. Create separate DB/users for CyberVPN and Remnawave if Remnawave DB runs here.
3. Run clean migrations.
4. Run backup.
5. Restore into disposable DB.
6. Save redacted evidence.

**Commands:**

```bash
cd backend
alembic upgrade head
```

**Exit criteria:**

- Migrations pass on clean DB.
- Backup artifact exists.
- Restore drill passes.
- Valkey is not treated as source of truth.

---

## STAGE1-PUB-07: Backend/API/Admin Deploy

**Purpose:** Bring up the backend and admin surfaces safely.

**Files:**

- Modify if needed: `backend/src/config/settings.py`
- Modify if needed: `backend/src/main.py`
- Modify if needed: `backend/src/presentation/api/v1/router.py`
- Create evidence: `docs/evidence/releases/stage1-pub-07-backend-admin-YYYYMMDDTHHMMSSZ.md`

**Steps:**

1. Deploy backend.
2. Run health check.
3. Confirm public Swagger/OpenAPI is off.
4. Confirm CORS and cookie domains match public domains.
5. Confirm CSRF posture.
6. Confirm rate limits for auth/payment/webhooks/support.
7. Create first admin through protected bootstrap.
8. Disable bootstrap after use.
9. Confirm admin requires 2FA.
10. Confirm admin audit log records privileged actions.

**Smoke commands:**

```bash
curl -fsS https://api.cyber-vpn.net/health
curl -I https://api.cyber-vpn.net/docs
curl -I https://admin.cyber-vpn.net
```

**Exit criteria:**

- Backend health is green.
- Admin is protected before app login.
- First admin is created once.
- Bootstrap is disabled.
- No public docs endpoint is exposed.

---

## STAGE1-PUB-08: Frontend And Public Web Deploy

**Purpose:** Publish the customer-facing web surface.

**Files:**

- Modify if needed: `frontend/next.config.ts`
- Modify if needed: `frontend/src/proxy.ts`
- Modify if needed: `frontend/messages/en-EN/*`
- Modify if needed: `frontend/messages/ru-RU/*`
- Create evidence: `docs/evidence/releases/stage1-pub-08-frontend-screenshots-YYYYMMDDTHHMMSSZ.md`

**Steps:**

1. Deploy frontend.
2. Route `cyber-vpn.net` and `www.cyber-vpn.net`.
3. Route `cyber-vpn.org` as VPN subscription delivery zone: `/api/sub*` must stay reachable on `.org`; non-subscription web traffic redirects to `.net`.
4. Check legal pages.
5. Check pricing, devices, help, status.
6. Check dashboard states.
7. Check config delivery UI.
8. Run frontend bundle/env scan against deployed artifacts.
9. Add blackbox probes for `cyber-vpn.net`, `www.cyber-vpn.net`, `status.cyber-vpn.net` and `.org` redirects.
10. Enable frontend Sentry release/environment tags and web-vitals/product funnel metrics if the runtime supports them.

**Smoke commands:**

```bash
curl -fsS https://cyber-vpn.net/
curl -fsS https://cyber-vpn.net/en-EN/pricing
curl -fsS https://cyber-vpn.net/ru-RU/privacy-policy
curl -I https://cyber-vpn.org/
curl -I https://cyber-vpn.org/api/sub/health-smoke
```

**Exit criteria:**

- Public web routes load over HTTPS.
- `.org` non-subscription routes redirect to `.net`.
- `.org` subscription routes do not redirect to `.net` and are routed to Remnawave subscription delivery.
- Legal pages have no placeholders.
- No private env value appears in client bundles.
- Public endpoint probes are visible in Grafana.

**Execution evidence:**

- Completed in `docs/evidence/releases/stage1-pub-08-frontend-screenshots-20260510T201837Z.md`.
- Screenshots are stored in `docs/evidence/releases/screenshots/`.

---

## STAGE1-PUB-09: Telegram Bot And Mini App Deploy

**Purpose:** Enable Telegram as a controlled Stage 1 customer channel.

**Files:**

- Modify if needed: `services/telegram-bot/src/config.py`
- Modify if needed: `services/telegram-bot/src/main.py`
- Modify if needed: `frontend/src/app/[locale]/miniapp/**`
- Create evidence: `docs/evidence/releases/stage1-pub-09-telegram-YYYYMMDDTHHMMSSZ.md`

**Steps:**

1. Install production Telegram bot token on server.
2. Set webhook to `api.cyber-vpn.net`.
3. Configure BotFather domain/Mini App URL.
4. Verify `/start`, `/menu`, `/connect`, `/plans`, `/trial`, `/support`, `/paysupport`.
5. Verify Mini App opens home/plans/payments/devices/profile/wallet.
6. Verify Telegram identity linking.
7. Verify Telegram rate limiting.
8. Verify support escalation.
9. Verify bot update metrics by `update_type` and `status`.
10. Verify Mini App bootstrap, checkout, payment status and config delivery metrics.

**Exit criteria:**

- Bot responds from Telegram client.
- Mini App loads with real Telegram initData.
- Webhook path does not require interactive challenge.
- Support escalation creates visible admin/support evidence.
- Telegram/Mini App metrics appear in Grafana without raw `initData` or PII.

**Execution evidence:**

- Runtime deploy evidence is recorded in `docs/evidence/releases/stage1-pub-09-telegram-20260510T205338Z.md`.
- `api.cyber-vpn.net` edge, TLS, Mini App route, compose contract, bot image, webhook and bot metrics target are prepared.
- `C_y_b_e_r_VPN_Bot` token was installed and Telegram `getWebhookInfo` confirms `https://api.cyber-vpn.net/webhook/telegram`.
- Full user-flow evidence still requires a real Telegram client smoke and token rotation before public beta because the token was pasted into chat during setup.

---

## STAGE1-PUB-10: Remnawave And VPN Node Deploy

**Purpose:** Prove that trial/payment can create usable VPN access.

**Latest evidence:** `docs/evidence/releases/stage1-pub-10-remnawave-vpn-20260510T214814Z.md`

**Current status:** Remnawave control-plane, API token, Prometheus metrics and one connected lab-only node are live on `cybervpn-h`. This clears the Remnawave control-plane and lab-node smoke, but it does not yet approve user-facing VPN access. Trial/paid provisioning stays disabled until a rented production VPN node is deployed and real client connection evidence is captured.

**Files:**

- Modify if needed: `backend/src/infrastructure/remnawave/*`
- Modify if needed: `services/task-worker/src/services/backend_api_client.py`
- Create evidence: `docs/evidence/releases/stage1-pub-10-remnawave-vpn-YYYYMMDDTHHMMSSZ.md`

**Steps:**

1. Install Remnawave API URL/token in server secret file.
2. Confirm Remnawave control-plane health.
3. Confirm at least one VPN node is healthy.
4. Connect Remnawave/node metrics to Prometheus.
5. Clear `Stage1NoHealthyRemnawaveNodes`.
6. Run trial provisioning.
7. Generate QR/subscription URL/config.
8. Connect from a real client or documented verification equivalent.
9. Test credential regeneration.
10. Test expiry/grace disable.
11. Measure `trial/pay -> VPN ready` median and p95 latency.
12. Verify Remnawave API error ratio and healthy node count panels.

**Exit criteria:**

- At least one node is healthy.
- Trial provisioning succeeds.
- User can connect.
- Provisioning latency is measured.
- Failure/retry path is proven.
- Remnawave/VPN panels show live data, not only `vector(0)` fallback.

---

## STAGE1-PUB-11: Payment Path Deploy

**Purpose:** Enable at least one paid path only after sandbox/live evidence.

**Files:**

- Modify if needed: `backend/src/infrastructure/payments/cryptobot/client.py`
- Modify if needed: `backend/src/presentation/api/v1/webhooks/routes.py`
- Modify if needed: `services/task-worker/src/tasks/payments/reconcile_stage1.py`
- Create evidence: `docs/evidence/releases/stage1-pub-11-payments-YYYYMMDDTHHMMSSZ.md`

**Steps:**

1. Start with CryptoBot as the first candidate path.
2. Install sandbox/test credentials.
3. Run success/failure/expired invoice samples.
4. Verify webhook signature validation.
5. Verify webhook idempotency.
6. Verify duplicate webhook does not duplicate subscription/provisioning.
7. Verify payment -> provisioning failure preserves paid state and queues retry.
8. Install production credentials only after sandbox proof.
9. Run low-value production payment if provider allows.
10. Keep other providers disabled until their evidence exists.
11. Verify payment metrics for created/paid/expired/failed invoices.
12. Verify webhook received/verified/rejected counters.
13. Verify paid-but-no-access queue size and max orphan age metrics.

**Exit criteria:**

- Enabled payment provider has real evidence.
- Paid-but-no-access/orphan policy is operational.
- No unresolved paid-but-no-access/orphan payment can exceed 24 hours without escalation.
- Providers with documentation-only placeholders are blocked.
- Payment dashboards and alerts show real data before paid beta is enabled.

**Latest execution status, 2026-05-10T22:09:26Z:**

- Evidence: `docs/evidence/releases/stage1-pub-11-payments-20260510T220926Z.md`.
- Runtime backend moved to `local/cybervpn-backend:stage1-beta-rc.2`.
- Runtime worker/scheduler moved to `local/cybervpn-task-worker:stage1-beta-rc.2` and are healthy.
- New payment runtime gates are deployed: `PAYMENTS_ENABLED=false` and `TELEGRAM_STARS_ENABLED=false` block new paid invoice/checkout creation with `503`.
- CryptoBot unsigned webhook probe returns `401 Invalid webhook signature`.
- Stage 1 reconciliation API returns zero items and `launch_blocked=false`.
- Stage 1 reconciliation worker metrics expose success/item/max-age/launch-blocked series.
- CryptoBot `getMe` currently returns `401 UNAUTHORIZED`; paid checkout remains blocked until a valid provider token and webhook evidence exist.

---

## STAGE1-PUB-12: Observability Integration

**Purpose:** Make deployed app behavior visible in the prepared observability stack.

**Files:**

- Modify if needed: `infra/prometheus/prometheus.yml`
- Modify if needed: `infra/prometheus/rules/stage1_alerts.yml`
- Modify if needed: `infra/grafana/dashboards/stage1-controlled-public-beta-dashboard.json`
- Create evidence: `docs/evidence/observability/stage1-pub-12-app-observability-YYYYMMDDTHHMMSSZ.md`

**Steps:**

1. Create Sentry projects/DSNs for backend, worker, Telegram bot, frontend and admin.
2. Add Sentry DSNs to server env files.
3. Verify test event from every service.
4. Connect Docker logs to Loki.
5. Connect backend/worker/bot metrics to Prometheus.
6. Connect frontend/admin edge probes and blackbox probes to Prometheus.
7. Connect PostgreSQL, Redis/Valkey, Remnawave and VPN node targets.
8. Verify `stage1_dashboard_recording_rules.yml` evaluates non-empty Stage 1 series.
9. Verify `stage1-controlled-public-beta` panels for availability, auth, payments, paid-but-no-access, provisioning, worker, database/cache, Remnawave, Telegram and Mini App.
10. Verify companion dashboards: hardware, infrastructure, logs, API/Remnawave, application, auth, OTP, Mini App, Telegram login, worker, PostgreSQL, Redis, SLO and error monitoring.
11. Add dashboard screenshots with no secret values visible.
12. Trigger test alerts for app failure, provisioning failure, payment failure, paid-but-no-access, Remnawave node unavailable, backup stale and restore evidence expired.
13. Verify Telegram and email alert delivery.
14. Save Prometheus targets, rules, active alerts and safe Loki/Sentry samples as evidence.

**Exit criteria:**

- Grafana shows real app data, not only `vector(0)` fallbacks.
- Loki contains safe app logs.
- Sentry receives redacted app events.
- Alertmanager delivers live alerts.
- Payment/provisioning/reconciliation metrics are visible before paid beta is enabled.
- Host hardware metrics are visible because Stage 1 observability runs on the home server.

**Latest execution status, 2026-05-10T23:14:55Z:**

- Evidence: `docs/evidence/observability/stage1-pub-12-app-observability-20260510T231455Z.md`.
- Added and deployed PostgreSQL and Redis/Valkey exporters for the current no-cost `local-data` Stage 1 topology.
- Connected Prometheus to `cybervpn_stage1_metrics` and added live scrape jobs for backend, worker, PostgreSQL exporter and Redis exporter.
- Verified required Stage 1 scrape targets are `up`: backend, worker, Telegram bot, PostgreSQL, Redis/Valkey and Remnawave.
- Recreated S1 runtime containers to load Sentry runtime env; all app containers are healthy afterward.
- Replaced invalid non-URL Sentry DSN placeholders with the existing valid self-hosted Sentry smoke DSN for S1 runtime proof.
- Verified protected Sentry contracts for frontend, admin and Telegram bot; all report DSN configured and release `stage1-beta-rc.1`.
- Verified Sentry self-hosted ingestion smoke with HTTP `200` and success metric `cybervpn_h_sentry_ingestion_smoke_success=1`.
- Verified Grafana Stage 1 and companion dashboards are provisioned.
- Verified Loki receives Docker logs; service/container label enrichment remains a later hardening item.
- Triggered a synthetic Alertmanager Stage 1 alert; Telegram/email notification counters increased and failed counters remained `0`.
- No Stage 1 app alerts are firing after cleanup. Existing host swap alerts remain and should be reviewed before expanding the beta cohort.

---

## STAGE1-PUB-13: Security, Legal And Support Gate

**Purpose:** Close the public beta governance gate.

**Files:**

- Read: `docs/cybervpn_stage1_launch_docs/79_STAGE1_LEGAL_TEXT_OWNER_APPROVAL_EVIDENCE.md`
- Read: `docs/cybervpn_stage1_launch_docs/69_STAGE1_SUP_001_SUPPORT_TICKET_PATH_EVIDENCE.md`
- Read: `docs/cybervpn_stage1_launch_docs/70_STAGE1_SUP_002_SUPPORT_TEMPLATES_EVIDENCE.md`
- Read: `docs/cybervpn_stage1_launch_docs/71_STAGE1_SUP_003_ESCALATION_PROCESS_EVIDENCE.md`
- Create evidence: `docs/evidence/security/stage1-pub-13-security-legal-support-YYYYMMDDTHHMMSSZ.md`

**Steps:**

1. Run final secret scan.
2. Run final dependency scan.
3. Run frontend bundle/env scan.
4. Verify Terms, Privacy, AUP, Refund, Cookie pages.
5. Verify no absolute no-logs overpromise.
6. Verify `support@cyber-vpn.net` and `refund@cyber-vpn.net`.
7. Verify support templates.
8. Verify admin/support can inspect safe subscription/payment/provisioning state.
9. Verify admin RBAC/2FA/audit.

**Exit criteria:**

- No untriaged high/critical finding blocks RC.
- Public legal pages are final for S1.
- Support can handle `paid but no access`.
- Admin/support sensitive actions are role-gated and audited.

**Latest execution status, 2026-05-11T06:29:02Z:**

- Evidence: `docs/evidence/security/stage1-pub-13-security-legal-support-20260511T062902Z.md`.
- Result: `PASS WITH NOTES` for a controlled beta cohort.
- Removed stale launch-unsafe public copy from affected marketing/support/status/footer namespaces and regenerated locale bundles.
- Rebuilt and deployed frontend image `sha256:eadf9769f1c70c9ba73527afadda34101a181f48feb6d8acf202a0a1387d1142` under runtime tag `stage1-beta-rc.2`.
- Verified EN/RU Terms, Privacy Policy, AUP, Refund Policy and Cookie Policy routes return `200`.
- Verified `cyber-vpn.org` redirects to `cyber-vpn.net` and `admin.cyber-vpn.org` redirects to `admin.cyber-vpn.net`.
- Verified public host hides admin audit API and OpenAPI/Swagger routes.
- Verified route-level public copy scan across all locales for `status`, `pricing` and `help` has no unsafe promise markers.
- Verified frontend help copy regression test: `1 passed`, `2 tests passed`.
- Verified frontend image private-marker scan has no private runtime markers.
- Verified local high-confidence secret scan has no matches; `gitleaks`/`trivy` are not installed and should be added to CI/release host hardening.
- Verified Node/Python dependency scans have no high/critical blockers; residual low/moderate findings are non-blocking for S1 controlled beta.
- Verified admin/support/RBAC/2FA/audit local security tests: `58 passed`.
- Operational note: `support@cyber-vpn.net` and `refund@cyber-vpn.net` are present in public copy, but MX/DMARC evidence was empty during this gate. Telegram/on-call support remains the proven first-cohort path; inbound mailbox delivery must be proven before widening the cohort.

---

## STAGE1-PUB-14: Backup, Restore And Rollback Gate

**Purpose:** Prove recovery before allowing public beta users.

**Files:**

- Create evidence: `docs/evidence/backups/stage1-pub-14-app-backup-YYYYMMDDTHHMMSSZ.md`
- Create evidence: `docs/evidence/restores/stage1-pub-14-app-restore-YYYYMMDDTHHMMSSZ.md`
- Create evidence: `docs/evidence/releases/stage1-pub-14-rollback-dry-run-YYYYMMDDTHHMMSSZ.md`

**Steps:**

1. Run app DB backup.
2. Restore app DB into disposable environment.
3. Run smoke queries.
4. Run Remnawave backup/export or rebuild proof.
5. Run rollback dry-run for frontend/backend/bot/worker.
6. Verify kill switches for registration, trial, payments and provisioning.
7. Store rollback target and commands.

**Exit criteria:**

- Backup exists.
- Restore works.
- Rollback target works.
- Kill switches work without code changes.

**Latest execution status, 2026-05-11T06:46:30Z:**

- Evidence:
  - `docs/evidence/backups/stage1-pub-14-app-backup-20260511T064630Z.md`
  - `docs/evidence/restores/stage1-pub-14-app-restore-20260511T064630Z.md`
  - `docs/evidence/releases/stage1-pub-14-rollback-dry-run-20260511T064630Z.md`
- Result: `PASS` for a small controlled beta.
- Created fresh app DB backup: `711901` bytes, SHA-256 `d769a412664ef7396c3b5577328fdda877ab1a16340cbcbbd782c53fc73bb3fc`.
- Restored app DB into disposable database and verified Alembic version `20260423_p27_partner_events` and `120` public tables; disposable database was dropped.
- Created fresh Remnawave DB backup: `144481` bytes, SHA-256 `b8c85e4369524f38cf4bee789e125575eea37c38734fde68d221d7bbeedea28e`.
- Restored Remnawave DB into disposable database and verified `36` public tables; disposable database was dropped.
- Verified no disposable restore databases remain.
- Verified all Stage 1 runtime containers are still `running` and `healthy`.
- Verified live smoke routes: `cyber-vpn.net/en-EN/status`, `admin.cyber-vpn.net/ru-RU/login`, `api.cyber-vpn.net/healthz`.
- Verified public registration kill switch on the live API: `POST /api/v1/auth/register` returns `403 REGISTRATION_DISABLED`.
- Verified backend registration/payment kill switch tests: `11 passed`.
- Verified no-code kill switch compose override validates for registration, payments, trial provisioning, paid provisioning, Telegram Stars and bot-level trial pause.
- Verified rollback compose override validates and rollback image targets exist for backend, frontend, admin, Telegram bot and worker/scheduler.
- Verified final hygiene: `git diff --check` passes, targeted STAGE1-PUB-14 secret/static scans have no matches, remote temporary script was removed, `npm audit --omit=dev --audit-level=high` has no high/critical blockers.
- Residual note: worker/scheduler rollback currently uses current known-good `stage1-beta-rc.2` because no older worker image is present on the host. Keep previous immutable worker images before expanding the cohort.

---

## STAGE1-PUB-15: Final Go/No-Go And Beta Cohort

**Purpose:** Start Stage 1 only after owner sign-off.

**Files:**

- Create evidence: `docs/evidence/releases/stage1-pub-15-go-no-go-YYYYMMDDTHHMMSSZ.md`
- Create release notes from: `docs/cybervpn_stage1_launch_docs/templates/STAGE1_RELEASE_NOTES_TEMPLATE.md`

**Steps:**

1. Assemble final evidence pack.
2. Record RC tag, commit SHA, image digests, SBOM, scans and rollback target.
3. Record current open risks.
4. Owner signs go/no-go.
5. Enable internal smoke.
6. Invite 3-5 trusted beta users.
7. Expand to 10-25 users only if metrics stay healthy.

**Success metrics:**

- Median `trial/pay -> VPN ready` <= 60 seconds.
- p95 `trial/pay -> VPN ready` <= 5 minutes.
- 95%+ successful `trial/pay -> VPN ready`.
- Zero unresolved paid-but-no-access/orphan payments older than 24 hours.
- No unresolved P0 incident.
- Stage 1 dashboard baseline captured before first invite.
- Payment, provisioning, Remnawave, worker queue and support escalation panels show live data during the first 3-5 users.

**Latest execution status, 2026-05-11T07:03:41Z:**

- Evidence:
  - `docs/evidence/releases/stage1-pub-15-go-no-go-20260511T070341Z.md`
  - `docs/evidence/releases/stage1-beta-rc.2-release-notes-20260511T070341Z.md`
- Technical recommendation: `GO` for internal smoke on public domains; `NO-GO` for inviting real beta users.
- Runtime stack is healthy and public smoke routes work.
- Public registration is still paused and live API returns `403 REGISTRATION_DISABLED`.
- Payments, paid provisioning and backend trial provisioning are intentionally disabled.
- Remnawave control-plane and lab node are healthy, but user-facing production VPN node/provisioning evidence remains missing.
- CryptoBot/payment provider proof remains blocked from `STAGE1-PUB-11`; paid beta must remain disabled.
- Prometheus is reachable; Alertmanager has 2 active warning alerts for swap usage.
- Final hygiene passed: `git diff --check`, targeted secret scan, targeted static scan and `npm audit --omit=dev --audit-level=high` have no high/critical blockers.
- Owner sign-off is pending; only the owner can convert this technical recommendation into a real cohort launch decision.
- Recommended next operational step: `STAGE1-PUB-15A: Internal Smoke And Launch Blocker Closure`.

---

## STAGE1-PUB-15A: Internal Smoke And Launch Blocker Closure

**Purpose:** Run internal smoke on the public-domain runtime while keeping real-user launch blockers closed and visible.

**Files:**

- Create evidence: `docs/evidence/releases/stage1-pub-15a-internal-smoke-and-blockers-YYYYMMDDTHHMMSSZ.md`

**Steps:**

1. Verify all Stage 1 app containers are running and healthy.
2. Verify public site/admin/API smoke routes.
3. Verify internal backend, bot, Remnawave, frontend and admin health routes.
4. Verify Telegram webhook status without printing token values.
5. Verify registration, payments, trial provisioning and paid provisioning remain safely paused.
6. Verify Prometheus targets and active alerts.
7. Re-check launch blockers: production VPN node, payment provider, immutable release tag, support email DNS and host warnings.
8. Record allowed and disallowed next actions.

**Exit criteria:**

- Internal smoke is safe to continue.
- Real-user beta remains blocked unless all P0 launch blockers are closed.
- Next blocker-closure step is explicit.

**Latest execution status, 2026-05-11T07:20:11Z:**

- Evidence: `docs/evidence/releases/stage1-pub-15a-internal-smoke-and-blockers-20260511T072011Z.md`.
- Result: `PASS` for internal smoke; `NO-GO` for external beta users.
- All Stage 1 containers are running and healthy.
- Public/internal smoke routes passed, except direct backend `/ready` returns `404`; backend `/health` and public `api.cyber-vpn.net/healthz` are healthy.
- Telegram webhook info is clean: webhook URL set, pending updates `0`, no last error.
- Registration is safely paused: live registration probe returns `403 REGISTRATION_DISABLED`.
- Payments remain safely paused; CryptoBot `getMe` still returns `401 UNAUTHORIZED`.
- Backend trial/paid provisioning flags remain disabled.
- Prometheus sees Stage 1 targets up; Remnawave lab node recording rule reports `1`.
- Alertmanager still has 2 swap warning alerts.
- Support/refund email DNS remains unproven: no MX/DMARC records for `cyber-vpn.net` or `cyber-vpn.org`.
- Dirty worktree remains broad: `262` entries, including `170` tracked modified and `92` untracked.
- Final hygiene passed: `git diff --check`, targeted secret scan, targeted static scan and `npm audit --omit=dev --audit-level=high` have no high/critical blockers.
- Recommended next no-cost step: `STAGE1-PUB-15B: Approved Snapshot Commit And Immutable RC2 Tag`.
- Recommended next real-user blocker step: `STAGE1-PUB-15C: Production VPN Node And Trial Provisioning Proof`.

---

## STAGE1-PUB-15C: Production VPN Node And Trial Provisioning Proof

**Purpose:** Prove that Stage 1 has a real production VPN exit node and that trial access can be provisioned end-to-end through CyberVPN and Remnawave.

**Files:**

- Create evidence: `docs/evidence/releases/stage1-pub-15c-production-vpn-node-trial-provisioning-YYYYMMDDTHHMMSSZ.md`

**Required proof path:**

1. Confirm Remnawave control-plane health.
2. Confirm at least one rented, always-on external production VPN node is registered and connected.
3. Confirm the node is not a lab/home/local-only node.
4. Confirm node firewall/allowlist and `NODE_PORT` boundary.
5. Confirm Prometheus sees Remnawave and the production node health signal.
6. Temporarily enable trial provisioning only for a disposable controlled beta identity or smoke window.
7. Run trial activation through CyberVPN.
8. Confirm Remnawave user/profile creation or update.
9. Confirm QR/subscription URL/config delivery.
10. Confirm the user-facing subscription URL is issued under `https://cyber-vpn.org/api/sub/{short_uuid}`.
11. Confirm the subscription content includes both Stage 1 transports: VLESS Reality RAW and VLESS Reality XHTTP.
12. Import the config into a real client and capture redacted connection evidence.
13. Prove credential regeneration.
14. Prove expiry/grace disable behavior.
15. Capture median/p95 `trial/pay -> VPN ready` latency from the smoke events.
16. Re-disable trial provisioning if the production cohort is not starting immediately.

**Exit criteria:**

- Production node inventory exists and is safe to share in evidence.
- Node health is proven by Remnawave API and Prometheus.
- Trial provisioning works against the production node.
- QR/subscription URL/config are generated.
- Subscription URL uses `.org` and subscription content includes XHTTP, not only VLESS RAW.
- A real client can connect.
- Support/admin can see the resulting state.
- No trial/provisioning/payment secret is printed into evidence.

**Latest execution status, 2026-05-11T07:27:05Z:**

- Evidence: `docs/evidence/releases/stage1-pub-15c-production-vpn-node-trial-provisioning-20260511T072705Z.md`.
- Result: `BLOCKED` for production VPN node and user-facing trial provisioning proof; `PASS` for no-cost Remnawave control-plane, lab-node and safety preflight.
- Current containers are running and healthy, including backend, worker, scheduler, Telegram bot, Remnawave and the local lab node.
- Remnawave `/health` returns `200`; Prometheus reports `up{job="remnawave"}=1`.
- Remnawave node inventory currently contains one connected node: `stage1-lab-home-node`, classified as `internal-hostname`, port `22230`.
- This node remains acceptable only for control-plane/lab smoke.
- No rented/always-on external production VPN node is currently proven.
- Backend registration, payments, trial provisioning and paid provisioning remain disabled.
- Public registration probe returns `403 REGISTRATION_DISABLED`.
- `stage1:provisioning_success_ratio:current` and `stage1:paid_but_no_access_oldest_age_minutes:current` have no data because user provisioning and payments are intentionally disabled.
- Final hygiene passed: `git diff --check`, targeted secret scan, targeted static scan and `npm audit --omit=dev --audit-level=high` have no high/critical blockers.
- External beta users must not be invited until this gate is rerun with a real production node and the full trial provisioning path passes.
- Recommended no-cost continuation: `STAGE1-PUB-15B: Approved Snapshot Commit And Immutable RC2 Tag`.
- Recommended real-user blocker continuation: provision a rented production VPN node, then rerun `STAGE1-PUB-15C`.

---

## STAGE1-PUB-16: Stabilization Loop

**Purpose:** Operate the controlled beta without prematurely expanding scope.

**Files:**

- Create daily evidence: `docs/evidence/releases/stage1-stabilization-YYYYMMDD.md`
- Update if needed: `docs/cybervpn_stage1_launch_docs/77_STAGE1_REMAINING_WORK_TO_LAUNCH.md`

**Daily checks:**

1. Review Sentry critical errors.
2. Review Alertmanager firing alerts.
3. Review payment reconciliation.
4. Review provisioning failures.
5. Review paid-but-no-access/orphan queue.
6. Review support tickets.
7. Review VPN node health.
8. Review worker lag/retry/dead-letter.
9. Review backups.
10. Review frontend/public endpoint probes.
11. Review Telegram Bot and Mini App metrics.
12. Review PostgreSQL and Redis/Valkey health.
13. Review home-server hardware dashboard: SMART, disk, RAM/swap, iowait, network errors and Docker log size.
14. Review Loki logs for new error patterns and confirm no sensitive payload logging.
15. Review S1 success metrics and cohort expansion criteria.
16. Update known issues.

**Exit criteria:**

- Stage 1 remains stable with beta users.
- Known issues are classified.
- Decision is made to continue beta, expand cohort, pause, or plan S2.

**Latest execution status, 2026-05-11T07:35:00Z:**

- Evidence: `docs/evidence/releases/stage1-stabilization-20260511.md`.
- Result: `CONTINUE` internal smoke / pre-beta stabilization; `NO-GO` for external beta cohort expansion.
- Public web, admin login, API health and mirror redirects respond with expected `200`/`301`.
- Core S1 app containers are running and healthy.
- Sentry health returns `200`; sampled Sentry web logs and app logs show no critical/error-level app failures, but the Sentry issue list was not queried without an API token.
- Alertmanager has two firing host swap alerts: `CyberVPNSwapInUse` and `CyberVPNSwapUsageAbove1GiB`.
- Payment/orphan state is empty because payments remain disabled: app DB has zero payments and payment attempts; reconciliation P0/current items are zero.
- Remnawave has one connected lab-only node, `stage1-lab-home-node`; production VPN node proof remains open.
- Worker queues are empty: `stage1:worker_queue_depth:current=0` and Redis `XLEN taskiq:stream=0`.
- PostgreSQL and Valkey health checks pass; app DB has `120` public tables.
- Telegram webhook is clean: configured, pending updates `0`, no last error.
- Hardware has enough disk and SMART metrics are healthy, but GitLab is at memory limit and host swap is active.
- Loki is receiving logs, but sensitive request-header material for GitLab runner polling was observed in log search output. No value is copied into evidence. Redaction/purge/rotation decision is required before wider beta or log export sharing.
- App DB currently has `active_plans=0` and `support_profiles_active=0`; seed S1 plan/support profile before enabling registration/trial/payment.
- Support/refund mailbox DNS remains unproven: no MX/DMARC output for `cyber-vpn.net` / `cyber-vpn.org`.
- Known issues were updated in `docs/cybervpn_stage1_launch_docs/77_STAGE1_REMAINING_WORK_TO_LAUNCH.md`.

---

## Automatic No-Go Conditions

Do not launch or expand beta if any item is true:

- Auth is broken.
- Admin is not protected.
- Admin 2FA is not enforced.
- Legal pages contain placeholders.
- Support cannot process paid-but-no-access.
- Payment path is untested while payments are enabled.
- Webhook idempotency is not proven.
- Remnawave is unavailable.
- No healthy VPN node exists.
- Trial provisioning is broken.
- Paid provisioning is broken while payments are enabled.
- Critical alerts are not delivered.
- Secrets leak is suspected.
- App backup/restore evidence is missing.
- Rollback evidence is missing.
- High/critical security finding is untriaged.
- Provider documentation-derived placeholders are enabled as real providers.
- Home-public beta risk is not accepted while using the home server for customer runtime.

## First Deployment Batch Recommendation

Execute in this exact order:

1. `STAGE1-PUB-00`
2. `STAGE1-PUB-01`
3. `STAGE1-PUB-02`
4. `STAGE1-PUB-03`
5. `STAGE1-PUB-04`
6. `STAGE1-PUB-05`
7. `STAGE1-PUB-06`
8. `STAGE1-PUB-07`
9. `STAGE1-PUB-08`
10. `STAGE1-PUB-12`

Then stop and verify. Continue only after the public web/API/admin surfaces are healthy and observable:

11. `STAGE1-PUB-09`
12. `STAGE1-PUB-10`
13. `STAGE1-PUB-11`
14. `STAGE1-PUB-13`
15. `STAGE1-PUB-14`
16. `STAGE1-PUB-15`
17. `STAGE1-PUB-16`

## Implementation Notes For This Repository

- Do not downgrade package versions.
- For Next.js middleware, use `src/proxy.ts`, not `src/middleware.ts`.
- Use immutable tags or image digests for deploys.
- Keep `Helix`, partner payouts, desktop/mobile/TV releases and public partner portal out of Stage 1.
- Keep `REFERRAL_ENABLED=false` and growth features hidden unless re-approved.
- Do not promise auto-renewal in Stage 1.
- Use GitHub as emergency fallback even after GitLab import.
- Do not make home GitLab registry the only production image source.

## Final Handoff

This plan is the execution map for publishing CyberVPN Stage 1 to the internet.

Start deployment with:

```text
STAGE1-PUB-00: Freeze And Risk Review
```

After each stage, save redacted evidence and stop for review before moving to the next stage.
