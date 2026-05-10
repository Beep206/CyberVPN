# CyberVPN H Public Launch Readiness

Date: `2026-05-10`

Source implementation plan:

```text
docs/plans/2026-05-09-cybervpn-h-public-server-implementation.md
```

Server:

```text
10.10.10.34
cybervpn-h-ops
Ubuntu 24.04.4 LTS
Public edge: 95.82.233.131
Public DNS zone: cyber-vpn.net
Public service namespace: *.h.cyber-vpn.net
```

This document summarizes what has already been prepared on the home server and what the CyberVPN project must still do before it can be launched publicly.

No live passwords, tokens, API keys, DSNs, or private keys are stored here. Use the private local access sheet for credentials:

```text
.private/cybervpn-h-10.10.10.34-access.md
```

The private access sheet is ignored by Git through `.private/`.

---

## Executive Summary

The server `10.10.10.34` is now prepared as the public CyberVPN home operations server. It has:

- hardened SSH and firewall baseline;
- Caddy public HTTPS edge;
- Cloudflare DNS-01 certificate automation;
- Docker Engine with data root on `/srv/docker`;
- GitLab, GitLab Registry, GitLab Runner;
- Grafana, Prometheus, Alertmanager, Loki, Promtail, Blackbox Exporter, Uptime Kuma;
- Sentry Self-Hosted with GeoIP;
- local backup foundation with restic on HDD;
- hardware/host monitoring;
- evidence archive;
- security pipeline scripts and CI jobs;
- restore runbooks and restore drill evidence;
- Stage 2 analytics/reporting scaffolding;
- Stage 3 partner/reseller scaffolding.

The server is infrastructure-ready. The main remaining work is to prepare and deploy the CyberVPN application services themselves: API/backend, worker, Telegram bot, payment integration, Remnawave/VPN node integration, app metrics, production env files, CI release flow, and final public go-live checks.

---

## Prepared Public Entry

### Router And WAN

Prepared:

- Router NAT forwards public `80/tcp` and `443/tcp` to `10.10.10.34`.
- SSH is not publicly forwarded.
- Application service ports are not publicly forwarded.
- MikroTik split-DNS maps CyberVPN h-domains to `10.10.10.34` for LAN clients.

Public edge:

```text
95.82.233.131 -> router -> 10.10.10.34:80/443 -> Caddy
```

LAN edge:

```text
*.h.cyber-vpn.net -> 10.10.10.34 -> Caddy
```

Current note:

- MikroTik UPnP is still enabled and creates unrelated dynamic forwards for other home devices. Review it before treating the home WAN as a hardened edge.

### Cloudflare DNS

Prepared records for core services:

```text
gitlab.h.cyber-vpn.net      -> 95.82.233.131
registry.h.cyber-vpn.net    -> 95.82.233.131
grafana.h.cyber-vpn.net     -> 95.82.233.131
sentry.h.cyber-vpn.net      -> 95.82.233.131
prometheus.h.cyber-vpn.net  -> 95.82.233.131
loki.h.cyber-vpn.net        -> 95.82.233.131
alerts.h.cyber-vpn.net      -> 95.82.233.131
uptime.h.cyber-vpn.net      -> 95.82.233.131
```

Prepared records for Stage 3:

```text
partner.h.cyber-vpn.net     -> 95.82.233.131
storefront.h.cyber-vpn.net  -> 95.82.233.131
reseller.h.cyber-vpn.net    -> 95.82.233.131
```

Recommended Cloudflare mode before public launch:

- `gitlab.h` and `registry.h`: DNS-only first.
- Admin/observability UIs: proxy only after access controls are confirmed.
- Enable WAF/rate limiting before exposing customer-facing app routes.
- Keep Cloudflare TLS mode `Full strict`.

Credential note:

- Cloudflare API token was used for Caddy DNS-01 and must be rotated because it was shared during setup.

### Caddy Edge

Prepared:

- Caddy is installed as a systemd service.
- Caddy listens publicly on `80/tcp` and `443/tcp`.
- TLS for `*.h.cyber-vpn.net` is issued with Cloudflare DNS-01.
- Caddy admin API is localhost-only.
- Health endpoint works:

```text
/.well-known/cybervpn-edge-health
```

Current route map:

| Domain | Upstream |
|---|---|
| `gitlab.h.cyber-vpn.net` | `127.0.0.1:8929` / GitLab through Caddy |
| `registry.h.cyber-vpn.net` | `127.0.0.1:5050` |
| `grafana.h.cyber-vpn.net` | `127.0.0.1:3000` |
| `sentry.h.cyber-vpn.net` | `127.0.0.1:9000` |
| `prometheus.h.cyber-vpn.net` | `127.0.0.1:9090` |
| `loki.h.cyber-vpn.net` | `127.0.0.1:3100` |
| `alerts.h.cyber-vpn.net` | `127.0.0.1:9093` |
| `uptime.h.cyber-vpn.net` | `127.0.0.1:3001` |
| `partner.h.cyber-vpn.net` | health/reserved |
| `storefront.h.cyber-vpn.net` | health/reserved |
| `reseller.h.cyber-vpn.net` | health/reserved |

Observability UIs are protected by Caddy Basic Auth.

---

## Prepared Host Foundation

### OS And Hardware Baseline

Prepared:

- Ubuntu `24.04.4 LTS`.
- Hostname: `cybervpn-h-ops`.
- Kernel: `6.8.0-111-generic`.
- CPU: `2 x Intel Xeon E5-2699 v3`, `36` physical cores, `72` threads.
- NVMe root disk for hot data.
- 2 TB HDD mounted at `/srv/storage` with `noatime`.
- Swap: `/swap.img`, `32 GB`.
- CPU performance governor enabled.
- BIOS updated to official JGINYUE BIOS.

Known hardware note:

- Linux currently sees about `46 GiB` RAM, with NUMA roughly `16 GB / 32 GB`.
- RAM is not a current software blocker, but it should be physically corrected before heavy production load.

### Directory Layout

Prepared orchestration root:

```text
/srv/cybervpn-h
/srv/cybervpn-h/compose
/srv/cybervpn-h/configs
/srv/cybervpn-h/evidence
/srv/cybervpn-h/runbooks
/srv/cybervpn-h/scripts
/srv/cybervpn-h/secrets
```

Prepared hot-data paths on NVMe:

```text
/srv/docker
/srv/gitlab
/srv/observability
/srv/sentry
```

Prepared cold/large-data paths on HDD:

```text
/srv/storage/backups
/srv/storage/gitlab-artifacts
/srv/storage/gitlab-packages
/srv/storage/gitlab-lfs
/srv/storage/gitlab-uploads
/srv/storage/gitlab-registry
/srv/storage/gitlab-cache
/srv/storage/sentry-attachments
/srv/storage/observability-cold
/srv/storage/archives/logs
/srv/storage/evidence
```

### Base Packages

Prepared package baseline includes:

```text
git
git-lfs
ufw
fail2ban
openssh-server
smartmontools
nvme-cli
lm-sensors
sysstat
htop
iotop
iftop
restic
rclone
jq
yq
make
curl
wget
ca-certificates
gnupg
lsb-release
unattended-upgrades
rasdaemon
acl
```

---

## Prepared Security Baseline

Prepared:

- SSH key-only access.
- SSH password login disabled.
- Root SSH login disabled.
- UFW enabled.
- Default incoming policy denied.
- SSH allowed from LAN.
- Public HTTP/HTTPS allowed to Caddy.
- Fail2ban enabled for SSH.
- Service ports are bound to localhost or Docker internal networks where practical.

Current public exposure:

```text
80/tcp
443/tcp
```

Do not expose directly:

```text
22/tcp
Docker daemon
PostgreSQL
Redis
ClickHouse
Kafka
GitLab internal ports
Sentry component ports
Prometheus component ports
Loki component ports
```

Required before customer launch:

- Rotate tokens shared during setup.
- Review MikroTik UPnP.
- Add Cloudflare WAF/rate limiting.
- Ensure all public app UIs have 2FA or strong access controls.

---

## Prepared Docker Foundation

Prepared:

- Docker Engine installed.
- Docker Compose plugin installed.
- Docker root moved to:

```text
/srv/docker
```

Daemon policy:

- JSON log rotation configured.
- `live-restore` enabled.
- default address pool configured.

Important application rule:

- Do not run new customer-facing containers without explicit resource limits.
- Do not mount Docker socket into untrusted app jobs.

---

## Prepared Backup Foundation

Prepared:

- Local restic repository on HDD.
- Config backup script.
- GitLab backup script.
- Sentry backup script.
- Observability backup script.
- Restic check script.
- Systemd timer for config backup.
- Systemd timer for restic check.
- Restore runbooks.
- First restore proof.

Key paths:

```text
/srv/storage/backups
/srv/storage/evidence/backups
/srv/storage/evidence/restores
/srv/cybervpn-h/scripts/backup-configs.sh
/srv/cybervpn-h/scripts/backup-gitlab.sh
/srv/cybervpn-h/scripts/backup-sentry.sh
/srv/cybervpn-h/scripts/backup-observability.sh
/srv/cybervpn-h/scripts/restic-check.sh
/srv/cybervpn-h/runbooks/restore-from-restic.md
/srv/cybervpn-h/runbooks/restore-gitlab.md
/srv/cybervpn-h/runbooks/restore-sentry.md
/srv/cybervpn-h/runbooks/restore-grafana.md
```

Retention policy:

```text
daily 14
weekly 4
monthly 3
```

Known gaps:

- No offsite backup yet.
- GitLab registry data is not fully covered by the current GitLab application backup when `SKIP=registry` is used.
- Full GitLab application restore into a separate container is still pending.

Before public launch:

- Add external disk or object storage backup target.
- Run full restore drill for the services that will be launch-critical.

---

## Prepared Observability Stack

Prepared components:

```text
Grafana
Prometheus
Alertmanager
Loki
Promtail
Blackbox Exporter
Node Exporter
cAdvisor
Uptime Kuma
```

Public URLs:

```text
https://grafana.h.cyber-vpn.net
https://prometheus.h.cyber-vpn.net
https://loki.h.cyber-vpn.net
https://alerts.h.cyber-vpn.net
https://uptime.h.cyber-vpn.net
```

Access:

- Caddy Basic Auth protects observability URLs.
- Grafana has a separate app login.
- Prometheus/Loki/Alertmanager rely on Caddy Basic Auth.

Prepared dashboards include:

- host/hardware dashboard;
- S1 dashboards and alerts;
- Stage 2 analytics/reporting dashboards;
- Stage 3 partner/reseller dashboards.

Prepared alerting:

- host down;
- disk above thresholds;
- swap usage;
- iowait high;
- Docker restart;
- GitLab unavailable;
- Sentry ingestion failing;
- payment/webhook error alerts;
- VPN/Remnawave node health alerts;
- TLS certificate expiry;
- Stage 2/3 synthetic checks.

Notification delivery:

- Telegram live delivery verified.
- Resend SMTP fallback verified through `smtp.resend.com:2587`.

Current active alert:

```text
Stage1NoHealthyRemnawaveNodes
```

Reason:

- Remnawave/VPN node metrics are not connected yet.

Before public launch:

- Connect real app metrics.
- Connect Remnawave metrics.
- Connect VPN node health metrics.
- Add app-specific SLO dashboards after the app is deployed.

---

## Prepared GitLab

Prepared:

- GitLab deployed at:

```text
https://gitlab.h.cyber-vpn.net
```

- Registry deployed at:

```text
https://registry.h.cyber-vpn.net
```

Configured:

- public signup disabled;
- private defaults applied;
- HTTPS push/clone tested;
- registry login/push/pull tested;
- GitLab backup writes to HDD;
- GitHub-to-GitLab mirror configured;
- GitLab Runner deployed.

Project mirror:

```text
GitHub -> home GitLab
```

Important operating rule:

- GitHub remains external source of truth and emergency fallback.
- Home GitLab must not be the only place where production can be deployed from.
- GHCR or another external registry should remain available for emergency deploy.

Before public launch:

- Confirm project CI in GitLab runs for the final app.
- Protect production branches/tags.
- Confirm image publishing strategy.
- Confirm production deploy does not depend only on home GitLab.

---

## Prepared GitLab Runner

Prepared:

- Docker executor runner.
- Protected refs only.
- Required tags:

```text
h-docker
protected
```

- Untagged jobs disabled.
- Privileged jobs disabled.
- Runner cache on HDD:

```text
/srv/storage/gitlab-cache
```

Current policy:

- Normal CI jobs can run.
- Docker-in-Docker/heavy build jobs are deferred to a separate future protected runner.

Before public launch:

- Make sure app `.gitlab-ci.yml` uses the right tags.
- Keep heavy jobs manual or offloaded.
- Do not let CI jobs mount Docker socket unless explicitly trusted.

---

## Prepared Sentry

Prepared:

- Sentry Self-Hosted deployed at:

```text
https://sentry.h.cyber-vpn.net
```

- Version source: official `getsentry/self-hosted`, release `26.4.2`.
- `COMPOSE_PROFILES=errors-only`.
- event retention configured.
- Sentry admin user created.
- public registration disabled.
- secure proxy headers enabled.
- attachments on HDD.
- backup script implemented.
- Sentry GeoIP configured with GeoLite2 ASN, City, Country.
- smoke project received test events.

Key paths:

```text
/srv/cybervpn-h/compose/sentry
/srv/cybervpn-h/secrets/sentry.env
/srv/cybervpn-h/secrets/sentry-smoke.env
/srv/cybervpn-h/secrets/sentry-geoip.env
/srv/sentry
/srv/storage/sentry-attachments
/srv/storage/backups/sentry
```

Before public launch:

- Create final Sentry projects for CyberVPN API, worker, Telegram bot, frontend, partner surfaces if needed.
- Add Sentry DSNs to runtime env.
- Configure release names and environment names.
- Upload frontend source maps once frontend release flow is stable.
- Rotate MaxMind license key because it was shared during setup.

---

## Prepared Hardware And Host Monitoring

Prepared:

- SMART monitoring for HDD.
- NVMe health checks.
- RAS/MCE monitoring.
- node-exporter textfile collector.
- cAdvisor for Docker metrics.
- host health evidence timer.

Tracked:

```text
NVMe temperature/wear
HDD SMART health
ECC/MCE errors
iowait
RAM available
swap usage
disk free/inodes
network errors
Docker container CPU/RAM/restarts/log size
```

Before public launch:

- Fix RAM population so the server sees expected RAM and balanced NUMA.
- Keep swap mostly unused during normal operation.
- Watch iowait after Sentry/GitLab/app load increases.

---

## Prepared Evidence Archive

Prepared tree:

```text
/srv/storage/evidence/releases
/srv/storage/evidence/backups
/srv/storage/evidence/restores
/srv/storage/evidence/security-scans
/srv/storage/evidence/incidents
/srv/storage/evidence/settlements
```

Prepared artifacts:

- baseline evidence;
- backup evidence;
- restore evidence;
- security scan evidence;
- observability evidence;
- Sentry evidence;
- GitLab evidence;
- Stage 2 evidence;
- Stage 3 evidence.

Before public launch:

- Store every release candidate evidence pack.
- Store image digests and SBOMs.
- Store security scan results.
- Store rollback dry-run output.
- Store incident/test alert evidence.

---

## Prepared Security Pipeline

Prepared tools/jobs:

```text
Gitleaks
npm audit
pip-audit
Trivy
Grype
Syft SBOM
```

Prepared stable scripts:

```text
scripts/security/scan-secrets.sh
scripts/security/audit-dependencies.sh
scripts/security/scan-filesystem-vulnerabilities.sh
scripts/security/generate-sbom.sh
```

Prepared evidence path:

```text
/srv/storage/evidence/security-scans
```

Known issue:

- Phase 20 security reports contain high/critical Trivy and Grype findings in auxiliary SDK, desktop/Rust, and app lockfiles.

Before public launch:

- Triage high/critical findings.
- Decide which are blockers, accepted risks, or false positives.
- Do not ship a release candidate without a fresh security scan evidence pack.

---

## Prepared Restore Discipline

Prepared runbooks:

```text
/srv/cybervpn-h/runbooks/restore-from-restic.md
/srv/cybervpn-h/runbooks/restore-gitlab.md
/srv/cybervpn-h/runbooks/restore-sentry.md
/srv/cybervpn-h/runbooks/restore-grafana.md
```

Completed:

- config file restore from restic;
- Grafana dashboard restore from backup;
- GitLab backup archive extraction and validation;
- evidence saved.

Still needed:

- full GitLab restore into separate container/test instance;
- app database restore drill after CyberVPN app is deployed;
- offsite restore drill after remote backups exist.

---

## Prepared Stage 2 Analytics And Reporting

Prepared:

- expanded Grafana dashboards;
- payment reconciliation dashboard;
- refund/renewal dashboard;
- subscription expiry dashboard;
- support SLA dashboard;
- status page data source/export script;
- product analytics dashboard scaffold;
- better log retention controls;
- scheduled restore drill timer;
- release comparison report generator;
- Sentry source map upload script;
- synthetic checks for public endpoints;
- CI quality gates;
- SBOM generation.

Important:

- These assets are ready, but many panels will remain empty until real app metrics exist.

Before public launch:

- Instrument backend and worker metrics.
- Instrument payment and webhook metrics.
- Instrument support/admin actions.
- Export release metadata into Prometheus/evidence.
- Confirm product analytics does not slow frontend.

---

## Prepared Stage 3 Partner / Reseller Platform

Prepared:

- partner lab compose area;
- partner portal/staging readiness dashboard;
- attribution/storefront dashboard;
- settlement/payout dashboard;
- support/audit/risk dashboard;
- Stage 3 Prometheus rules;
- Stage 3 storefront synthetic targets;
- partner webhook test receiver;
- redacted/anonymized import tool;
- settlement evidence archive tree;
- partner incident runbook;
- sandbox report generator.

Current state:

- Stage 3 is infrastructure/scaffold only.
- Live partner portal/storefront/reseller services are not deployed yet.
- Public health routes exist.

Before public launch:

- Do not expose live partner/reseller features until S1 is stable.
- Keep partner sandbox off by default.
- Use redacted data only for partner reporting tests.

---

## What The CyberVPN Project Must Prepare Next

### 1. Runtime Compose For CyberVPN App

Create or finalize compose definitions for:

```text
backend API
task worker
Telegram bot
frontend/public web app if hosted here
payment webhook receiver
Remnawave integration service if separate
scheduled jobs
```

Decide final runtime path:

```text
/srv/cybervpn-h/compose/app
/srv/cybervpn-h/secrets/app.env
/srv/cybervpn-h/configs/app
/srv/cybervpn-h/runbooks/app-ops.md
```

Rules:

- bind public HTTP only to `127.0.0.1`;
- route public access through Caddy only;
- set memory and CPU limits;
- use Docker healthchecks;
- do not store production secrets in Git.

### 2. App Secrets

Prepare root-only env files on server:

```text
/srv/cybervpn-h/secrets/app.env
/srv/cybervpn-h/secrets/payments.env
/srv/cybervpn-h/secrets/telegram-bot.env
/srv/cybervpn-h/secrets/remnawave.env
/srv/cybervpn-h/secrets/sentry-runtime.env
```

Minimum expected secret categories:

```text
database URLs
Redis URLs
JWT/session secrets
admin bootstrap credentials
Telegram bot token
payment provider credentials
payment webhook secrets
Remnawave API URL/token
Sentry DSNs
SMTP/email credentials if used by app
encryption keys
```

File mode:

```text
0600 root root
```

### 3. Application Metrics

Expose Prometheus metrics for:

```text
API health
auth success/failure
payment success/failure
webhook duplicate/retry
paid-but-no-access/orphan payments
provisioning latency
Remnawave API health
worker queue/retry/dead-letter
Telegram bot health
admin/support actions
VPN node health
error rate by service
```

Recommended endpoint:

```text
/metrics
```

Do not expose metrics publicly. Scrape internally from Prometheus.

### 4. Application Logs

Make logs structured and safe:

```text
JSON or key-value logs
no tokens
no full payment payloads
no full config URLs with credentials
request id / trace id
service name
environment
release version
```

Loki/Promtail will collect Docker JSON logs.

### 5. Sentry Integration

Configure every runtime component:

```text
backend API
worker
Telegram bot
frontend
partner surfaces later
```

Required Sentry tags:

```text
service
environment
release
component
```

Before launch:

- verify a test event from each service;
- verify PII scrubbing;
- verify release names;
- verify frontend source maps only after stable release flow.

### 6. GitLab CI/CD

Prepare pipeline stages:

```text
lint
test
build
secret scan
dependency scan
container scan
SBOM
release evidence
deploy staging/manual
deploy production/manual
rollback dry-run
```

Runner tags:

```text
h-docker
protected
```

Do not run production deployment from unprotected branches.

### 7. Container Images

Decide source of production images:

```text
primary: external registry such as GHCR
optional internal cache: registry.h.cyber-vpn.net
```

Rule:

- Production must not depend only on the home GitLab registry.

Evidence per release:

```text
image digest
SBOM
Trivy/Grype reports
commit SHA
release tag
deployment manifest
rollback target
```

### 8. Public App Domains

Decide final customer-facing domains. Current infrastructure only covers h-domain operations surfaces.

Possible separation:

```text
*.h.cyber-vpn.net      home ops/admin/infrastructure
api.cyber-vpn.net      public API
app.cyber-vpn.net      public app/frontend
bot/webhook domain     Telegram/payment webhooks
status.cyber-vpn.net   status page
```

Before adding new public domains:

- create Cloudflare DNS;
- add Caddy route;
- add TLS;
- add WAF/rate limit;
- add synthetic check;
- add evidence.

### 9. Payment Launch Checks

Before enabling real payments:

```text
payment provider sandbox smoke
payment provider production credentials installed
webhook signature verification
idempotency keys
duplicate webhook handling
paid-but-no-access reconciliation
refund/renewal visibility
manual support runbook
test payment evidence
```

### 10. Remnawave / VPN Nodes

Before enabling paid/trial provisioning:

```text
Remnawave API URL/token installed
Remnawave health metrics exported
VPN node health metrics exported
provisioning latency metric exported
provisioning failure alert tested
manual pause/rollback procedure documented
```

Current blocker:

```text
Stage1NoHealthyRemnawaveNodes
```

This alert should remain a blocker until Remnawave/VPN node metrics are connected and healthy.

---

## Public Launch Checklist

### Infrastructure

- [x] Host hardened.
- [x] Docker ready.
- [x] Caddy public edge ready.
- [x] Core h-domains have DNS/TLS.
- [x] GitLab ready.
- [x] GitLab Runner ready.
- [x] Sentry ready.
- [x] Observability stack ready.
- [x] Telegram alert delivery verified.
- [x] Resend SMTP fallback verified.
- [x] Evidence archive ready.
- [x] Security pipeline ready.
- [ ] Offsite backup ready.
- [ ] MikroTik UPnP reviewed.
- [ ] Shared setup tokens rotated.
- [ ] RAM physically corrected or accepted as risk.

### Application

- [ ] Backend/API deployed.
- [ ] Worker deployed.
- [ ] Telegram bot deployed.
- [ ] Payment webhook receiver deployed.
- [ ] Remnawave integration deployed.
- [ ] VPN node metrics connected.
- [ ] Application logs visible in Loki.
- [ ] Application metrics visible in Prometheus.
- [ ] Application errors visible in Sentry.
- [ ] App dashboards have real data.
- [ ] App alerts tested.
- [ ] Release evidence generated.
- [ ] Rollback dry-run evidence generated.

### Security

- [ ] Production secrets are not committed.
- [ ] `.env` files are `0600`.
- [ ] GitLab public signup disabled.
- [ ] GitLab admin 2FA configured.
- [ ] Grafana admin secured.
- [ ] Sentry admin secured.
- [ ] Cloudflare WAF/rate limiting enabled.
- [ ] Payment/Telegram webhooks validate signatures.
- [ ] Security scans triaged.
- [ ] No critical/high untriaged release blockers.

### Backup And Restore

- [x] Config backup works.
- [x] GitLab backup writes to HDD.
- [x] Sentry backup writes to HDD/restic.
- [x] Restore drill evidence exists.
- [ ] Offsite backup configured.
- [ ] Full GitLab containerized restore tested.
- [ ] App database restore tested after app deployment.
- [ ] Registry backup strategy decided.

---

## Recommended Next Execution Order

1. Rotate exposed setup secrets:

```text
Cloudflare API token
MaxMind license key
Telegram bot token
Resend API key
```

2. Fix or accept RAM state:

```text
current: about 46 GiB visible, NUMA about 16/32 GB
target: balanced 64/96/128 GB
```

3. Review MikroTik UPnP and public firewall posture.

4. Add offsite backup target.

5. Prepare CyberVPN app compose and env files.

6. Deploy backend/API/worker/Telegram bot/payment webhook receiver.

7. Connect Remnawave/VPN node metrics and clear:

```text
Stage1NoHealthyRemnawaveNodes
```

8. Connect app metrics/logs/Sentry.

9. Run S1 dashboard and alert smoke tests.

10. Run payment sandbox and production credential smoke tests.

11. Run release evidence generation:

```text
commit SHA
image digests
SBOM
security scans
Sentry release
deployment manifest
rollback target
```

12. Run backup and restore evidence for the actual app.

13. Enable Cloudflare WAF/rate limiting.

14. Run final external synthetic checks.

15. Launch public traffic gradually.

---

## Fast Validation Commands

Run on `10.10.10.34`:

```bash
systemctl --failed --no-pager
sudo ufw status verbose
docker ps
free -h
swapon --show
df -hT
curl -fsS http://127.0.0.1:9090/api/v1/targets | jq .
curl -fsS http://127.0.0.1:9090/api/v1/alerts | jq .
curl -fsS http://127.0.0.1:9093/-/ready
sudo /srv/cybervpn-h/scripts/send-alertmanager-test-alert.sh
sudo /srv/cybervpn-h/scripts/backup-configs.sh
```

Run from the project repository:

```bash
python3 scripts/validate_gitlab_ci_contract.py
python3 scripts/validate-s1-alerting.py
python3 scripts/validate-stage2-analytics-artifacts.py
python3 scripts/validate-stage3-partner-artifacts.py
bash scripts/security/scan-secrets.sh
```

---

## Go / No-Go Summary

Infrastructure status:

```text
GO with known risks
```

Application status:

```text
NO-GO until CyberVPN app services, metrics, Remnawave/VPN node health, payment checks, and release evidence are completed
```

Main blockers:

```text
Remnawave/VPN node metrics missing
CyberVPN app services not deployed on the host yet
No offsite backup yet
shared setup tokens still need rotation
security scan findings need triage before release candidate
RAM state should be corrected or explicitly accepted as risk
```

Once the app services are deployed and the current blockers are closed, this server is ready to operate as the public home operations edge for CyberVPN.
