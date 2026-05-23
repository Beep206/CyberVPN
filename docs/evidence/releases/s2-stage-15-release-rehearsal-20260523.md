# S2-STAGE-15 Full Staging/Public-Release Rehearsal Evidence

**Date:** 2026-05-23
**Stage:** `S2-STAGE-15`
**Result:** `PASS_WITH_CONTROLLED_GAPS`
**Owner:** `@Sasha_Beep`

---

## 1. Scope

This evidence records the Stage 2 public-release rehearsal before production canary.

Covered:

- GitLab/GitHub synchronized baseline;
- `stage2-public-rc.1` release candidate plan;
- `stage2-public-rc.2` follow-up candidate after CI packaging blocker fix;
- `stage2-public-rc.3` follow-up candidate after backend lint blocker fix;
- `stage2-public-rc.4` follow-up candidate after frontend locale blocker fix;
- `stage2-public-rc.5` follow-up candidate after Telegram Bot smoke expectation fix;
- deploy dry-run contract for all app services;
- public route probes;
- public frontend route probes;
- HTTP/3/QUIC header preservation;
- production app container inventory;
- VPN node-only proof;
- home observability health;
- rollback artifact availability;
- controlled gap classification.

No secret values, raw VPN configs, raw subscription tokens, payment payloads or Telegram init data are stored in this evidence file.

---

## 2. Baseline

Before this stage:

```text
GitLab main c87c3526bde9963f36c1bb1a400731704bd8f554
GitHub main c87c3526bde9963f36c1bb1a400731704bd8f554
```

Working tree:

```text
tracked files clean before S2-STAGE-15 edits
untracked unrelated evidence file left untouched:
docs/evidence/releases/stage1-rented-prod-15g-telegram-allowlist-zyrianovaol-20260522T183718Z.md
```

Existing S2 RC tags before this stage:

```text
none
```

---

## 3. Deploy Dry-Run

Command:

```text
STAGE1_DEPLOY_DRY_RUN=true
STAGE1_DEPLOY_EVIDENCE_DIR=.tmp/s2-stage15-dry-run
STAGE1_RELEASE_TAG=stage2-public-rc.1
bash scripts/deploy/stage1-gitlab-deploy.sh all
```

Observed:

```text
Release tag: stage2-public-rc.1
Services: frontend,task-worker,backend,telegram-bot,admin
Host: dry-run.invalid
Dry run: true
Checked at: 2026-05-23T07:30:49Z
No SSH, rsync, Docker build, compose restart or public smoke was executed.
```

Interpretation:

```text
The S2 RC deploy contract can be validated without production network access or runtime mutation.
```

---

## 3A. GitLab Tag Pipeline Follow-Up

After `stage2-public-rc.1` was pushed, GitLab created the tag pipeline and exposed two launch-packaging issues:

```text
pipeline 59 stage2-public-rc.1 pending before tag protection
pipeline 60 stage2-public-rc.1 failed after manual rerun
failed jobs:
observability:stage2-artifacts -> Missing file: infra/prometheus/targets/stage2-public-endpoints.json
partner:stage3-artifacts       -> Missing file: infra/prometheus/targets/stage3-storefront-endpoints.json
```

Root cause:

```text
The required target JSON files existed locally but were ignored by .gitignore and were not present in the immutable RC1 repository snapshot.
```

Fix:

```text
.gitignore now explicitly allows the Stage 2 and Stage 3 Prometheus target JSON files required by CI validation.
stage2-public-rc.2 fixed the missing target files and allowed the failed validation jobs to pass.
stage2-public-rc.3 fixed the backend lint blocker and exposed a frontend locale test failure.
stage2-public-rc.4 fixed the frontend locale blocker and exposed a Telegram Bot smoke expectation failure.
stage2-public-rc.5 is the corrected follow-up RC for S2 canary after the Telegram Bot smoke expectation fix.
```

Final RC pipeline result:

```text
GitLab pipeline 68
ref=stage2-public-rc.5
sha=3c3a7b1a
status=success

Hard jobs passed:
gitlab:ci-contract
observability:stage2-artifacts
admin:lint
backend:lint
frontend:lint
telegram-bot:lint
admin:test
backend:test:smoke
frontend:test
telegram-bot:test:smoke
admin:build
frontend:build
container-scan:trivy-grype
npm-audit:high
pip-audit:python-locks
sbom:release-candidate
secret-pattern-scan
security:gitleaks
quality:release-comparison-report
stage2:release-evidence-pack
stage2:deploy:dry-run

Allowed failures observed and classified as non-blocking S2 technical debt:
task-worker:lint
partner:test
task-worker:test:smoke
```

GitLab runner/protected-tag follow-up:

```text
Protected tag pattern added in GitLab: stage2-public-rc.*
```

Backend lint follow-up:

```text
stage2-public-rc.2 exposed a backend ruff import-order failure in
backend/src/infrastructure/remnawave/stage1_trial_gateway.py.

The import order was fixed locally with ruff and will be released as stage2-public-rc.3.
```

Frontend locale follow-up:

```text
stage2-public-rc.3 exposed a frontend test failure in
frontend/src/i18n/__tests__/request.test.ts.

Root cause: frontend/messages/ru-RU/footer.json used "Privacy Policy" for Footer.links.privacy.
Fix: Footer.links.privacy now uses "Политика конфиденциальности" and will be released as stage2-public-rc.4.
```

Telegram Bot smoke follow-up:

```text
stage2-public-rc.4 exposed a smoke-test failure in
services/telegram-bot/tests/unit/test_main.py.

Root cause: the bot surface now includes the live "invites" command, while the startup command test expected the pre-invites command list.
Fix: the test now expects "invites" between "trial" and "support" and will be released as stage2-public-rc.5.
```

---

## 4. Public Route Probes

Observed:

```text
https://cyber-vpn.net/ru-RU                              http=200
https://cyber-vpn.net/ru-RU/pricing                      http=200
https://cyber-vpn.net/ru-RU/login                        http=200
https://cyber-vpn.net/ru-RU/miniapp/home                 http=200
https://admin.cyber-vpn.net/ru-RU/login                  http=200
https://api.cyber-vpn.net/health                         http=200 body={"status":"ok"}
https://api.cyber-vpn.net/docs                           http=404
https://cyber-vpn.org/                                   http=301 redirect=https://cyber-vpn.net/
https://cyber-vpn.org/api/sub/<redacted-invalid-token>   http=404
```

Interpretation:

- public customer routes are reachable;
- admin route is reachable on the admin host;
- API health is OK;
- public API docs remain disabled;
- `.org` is not used as a customer mirror and remains suitable for subscription/node delivery.

---

## 5. HTTP/3/QUIC Header Check

Observed:

```text
https://cyber-vpn.net/ru-RU
HTTP/2 200
alt-svc: h3=":443"; ma=86400
strict-transport-security: max-age=31536000; includeSubDomains; preload

https://admin.cyber-vpn.net/ru-RU/login
HTTP/2 200
alt-svc: h3=":443"; ma=86400
strict-transport-security: max-age=31536000; includeSubDomains; preload

https://api.cyber-vpn.net/health
alt-svc: h3=":443"; ma=86400
cache-control: no-store, max-age=0
strict-transport-security: max-age=31536000; includeSubDomains; preload
```

No HTTP/3/QUIC setting was disabled.

---

## 6. Production App Runtime Inventory

Host:

```text
prod-app-1
```

Observed app containers:

```text
cybervpn-edge-caddy Up 2 days
cybervpn-stage1-cybervpn-admin-1 Up 3 days (healthy)
cybervpn-stage1-cybervpn-backend-1 Up 13 hours (healthy)
cybervpn-stage1-cybervpn-frontend-1 Up 22 hours (healthy)
cybervpn-stage1-cybervpn-postgres-1 Up 3 days (healthy)
cybervpn-stage1-cybervpn-postgres-exporter-1 Up 3 days (healthy)
cybervpn-stage1-cybervpn-redis-exporter-1 Up 3 days (healthy)
cybervpn-stage1-cybervpn-remnawave-1 Up 24 hours (healthy)
cybervpn-stage1-cybervpn-remnawave-postgres-1 Up 24 hours (healthy)
cybervpn-stage1-cybervpn-remnawave-valkey-1 Up 24 hours (healthy)
cybervpn-stage1-cybervpn-scheduler-1 Up 2 days (healthy)
cybervpn-stage1-cybervpn-telegram-bot-1 Up 22 hours (healthy)
cybervpn-stage1-cybervpn-valkey-1 Up 3 days (healthy)
cybervpn-stage1-cybervpn-worker-1 Up 2 days (healthy)
```

Interpretation:

```text
The production app stack is up and healthy before S2 canary.
```

---

## 7. VPN Node-Only Proof

Host:

```text
de-1.cyber-vpn.org
```

Observed containers:

```text
cybervpn-remnawave-node Up 3 days
```

Observed public/listening ports include:

```text
22
443
8443
22230
```

Interpretation:

```text
The VPN node remains node-only. No app, GitLab, Sentry, Grafana, Prometheus, backend, frontend, admin, database or payment services were observed on the node.
```

---

## 8. Home Observability Health

Host:

```text
cybervpn-h-ops
```

Observed containers include:

```text
cybervpn-alertmanager Up 12 days
cybervpn-blackbox-exporter Up 10 hours
cybervpn-cadvisor Up 13 days (healthy)
cybervpn-gitlab Up 2 days (healthy)
cybervpn-gitlab-runner Up 12 days
cybervpn-grafana Up 10 hours
cybervpn-loki Up 13 days
cybervpn-node-exporter Up 13 days
cybervpn-prometheus Up 10 hours
cybervpn-uptime-kuma Up 13 days (healthy)
sentry-self-hosted-nginx-1 Up 2 days (healthy)
sentry-self-hosted-web-1 Up 2 days (healthy)
```

Health checks:

```text
Prometheus: Prometheus Server is Ready.
Grafana: database=ok, version=11.5.2
Alertmanager: OK
Sentry: ok
```

Interpretation:

```text
The home observability plane is available for S2 canary watch. Customer runtime still does not depend on the home host.
```

---

## 9. Rollback Availability

Current rollback artifacts:

```text
/srv/cybervpn/backups/s2-stage12-20260523T050454Z/rollback.override.yml
/srv/cybervpn/backups/s2-stage12-20260523T050454Z/rollback-command.txt
/srv/cybervpn/backups/s2-stage12-20260523T050454Z/rollback-dry-run.log
```

Observed latest rollback dry-run:

```text
started_at_utc=2026-05-23T05:05:47+00:00
compose_config_status=ok
rollback_dry_run_status=ok
finished_at_utc=2026-05-23T05:05:47+00:00
```

Interpretation:

```text
Rollback is available for the current runtime inventory. Repeat rollback dry-run if the S2 canary deploy changes image inventory materially.
```

---

## 10. Local Validation

Commands:

```text
python scripts/validate_gitlab_ci_contract.py
bash -n scripts/deploy/stage1-gitlab-deploy.sh
git diff --check
```

Observed:

```text
PASS: GitLab CI contract is ready for initial GitLab import
bash syntax check passed
git diff whitespace check passed
```

---

## 11. Controlled Gaps

| Gap | Risk | S2 decision |
|---|---|---|
| No live real-money payment was executed during this rehearsal | Provider path still needs canary proof | Execute with owner/internal user during `S2-STAGE-16` |
| No new production trial activation or new provisioning mutation was created automatically | Fresh S2 RC provisioning is not proven by automation here | Execute in canary; keep provisioning kill switch ready |
| No fresh VPN client connection was performed by this automation | Human/device proof remains manual | Owner/internal canary must connect and report IP/protocol proof |
| Refund/expiry/renewal simulation was not run against real provider data | Provider-specific operational path remains manual | Use admin-safe simulation or provider sandbox before broad public opening |
| Real deploy was dry-run only | Current runtime was observed, but no restart was performed | Accept; do not restart production unless canary deploy is approved |

---

## 12. Result

`S2-STAGE-15` passes with controlled gaps after the RC1 packaging blocker is classified in RC2, the backend lint blocker is fixed in RC3, the frontend locale blocker is fixed in RC4, and the Telegram Bot smoke expectation blocker is fixed in RC5.

The corrected release candidate `stage2-public-rc.5` has a successful GitLab tag pipeline and is ready to move to owner-controlled canary, provided the owner accepts the controlled gaps and runs the live user journey in `S2-STAGE-16`.

Next stage:

```text
S2-STAGE-16: Production Canary Release
```
