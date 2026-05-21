# STAGE1-RENT-11 - Observability And Stabilization Loop Evidence

Date: `2026-05-20T16:29:26Z`
Scope: rented Stage 1 controlled beta runtime plus home observability stack
Result: `PASS_WITH_GAPS`

## Decision

Stage 1 can continue as a controlled internal/owner beta with observability active.

Do not treat home Prometheus public HTTP probes as fully reliable yet. The home server can resolve `cyber-vpn.net` to `45.87.41.146` and TCP connect to `80/443`, but HTTPS/HTTP requests from the home host to `prod-app-1` time out during/after handshake. External probes from the working operator environment still return `200`.

Action: keep the beta small and add `STAGE1-RENT-11A` for home-to-prod-app public endpoint probe relay/network closure before widening the cohort.

## Live Runtime Snapshot

| Area | Result |
|---|---|
| `prod-app-1` containers | all Stage 1 app/control-plane containers running and healthy; restart count `0` |
| Edge | Caddy exposes `80/tcp`, `443/tcp`, `443/udp`; HTTP/3/QUIC remains enabled |
| `prod-app-1` resources | disk `/` 18% used, memory 12 GiB available, swap effectively unused, Docker logs 1.7 MiB |
| `prod-vpn-node-1` | `cybervpn-remnawave-node` running, restart count `0`, ports `443/tcp` and `8443/tcp` open |
| VPN node resources | disk 6% used, memory 3.1 GiB available, no recent node log errors |
| Home observability | Prometheus, Grafana, Loki, Alertmanager, Sentry, GitLab and exporters are running |
| Home resources | `/` 10% used, `/srv/storage` 1% used, load low, but swap usage alerts are firing |

## Public Endpoint Probes

External operator probes from the current workspace:

| Endpoint | Result |
|---|---|
| `https://cyber-vpn.net/` | `200`, redirects to locale route |
| `https://cyber-vpn.net/en-EN` | `200` |
| `https://cyber-vpn.net/ru-RU/miniapp/home` | `200` |
| `https://cyber-vpn.net/ru-RU/miniapp/plans` | `200` |
| `https://api.cyber-vpn.net/health` | `200`, `{"status":"ok"}` |
| `https://admin.cyber-vpn.net/ru-RU/login` | `200` |
| `https://status.cyber-vpn.net/` | `200`, currently redirects to `/en-EN/status` |
| `https://www.cyber-vpn.net/` | `200` |

Home Prometheus blackbox probes for the same public web/API/admin endpoints currently return `probe_success=0` because the home server cannot complete HTTP/TLS exchange with `prod-app-1`. This is an observability transport gap, not proof that the customer-facing site is down.

## Observability Changes Applied

Repository assets updated:

| File | Change |
|---|---|
| `infra/blackbox/blackbox.yml` | added `tcp_connect` module |
| `infra/prometheus/prometheus.yml` | added `stage1-vpn-node-tcp` scrape job |
| `infra/prometheus/rules/stage1_alerts.yml` | added VPN TCP probe alert; added public endpoint probe alert for source-controlled `stage1-public-web` job |
| `infra/prometheus/targets/stage1-public-web.json` | replaced stale URLs with current S1 public routes |
| `infra/prometheus/targets/stage1-vpn-node-tcp.json` | added `de-1.cyber-vpn.org:443` and `de-1.cyber-vpn.org:8443` |
| `.gitignore` | added explicit exceptions so the two Stage 1 canonical target files can be tracked |

Live home observability updated:

| Area | Result |
|---|---|
| Blackbox config | updated with `tcp_connect` module |
| Prometheus config | updated with live `stage1-vpn-node-tcp` job |
| Stage 1 alert rules | reloaded; public-web false P0 alert suppressed for the current home-only blocked job |
| Config backup | `/srv/cybervpn-h/evidence/observability/stage1-rent11-config-backup-20260520T162255Z` |
| Reload | Prometheus healthy after HUP; blackbox exporter restarted |

## Prometheus, Alerts And Dashboards

| Check | Result |
|---|---|
| Prometheus health | `200 Prometheus Server is Healthy` |
| Prometheus `up` series | `40` series after VPN TCP job addition |
| VPN TCP probes | `de-1.cyber-vpn.org:443 = 1`, `de-1.cyber-vpn.org:8443 = 1` |
| Stage 1 VPN TCP alert | no firing/pending alert after reload |
| Stage 1 public-web alert | no firing false P0 after suppressing the home-blocked live job |
| Current firing alerts | `CyberVPNSwapInUse`, `CyberVPNSwapUsageAbove1GiB`, `Stage2StatusEndpointDown` |
| Static dashboard validation | `PASS: S1 observability dashboard, recording rules and scrape jobs are wired.` |
| Static alert validation | `PASS: S1 alert rules and Alertmanager Telegram/email routing are wired.` |

The remaining firing alerts are not direct S1 customer-runtime failures. Swap usage is a home observability capacity warning. `Stage2StatusEndpointDown` is outside S1 rented runtime.

## Alert Delivery Proof

Synthetic alert delivery was tested through Alertmanager.

| Check | Result |
|---|---|
| Alert accepted | `POST /api/v2/alerts -> 200` |
| Telegram notification counter | increased during the smoke |
| Email notification counter | increased during the smoke |
| Failed notification counter | `0` for Telegram and email |
| Synthetic alerts cleanup | `Stage1Rent11AlertDeliveryTest` and `CyberVPNPhase18TelegramDeliverySmoke` resolved, no active residue |

## Sentry And Loki

| Check | Result |
|---|---|
| Sentry health | `/_health/ -> 200`, `/api/0/ -> 200` |
| Sentry containers | self-hosted Sentry core containers running |
| Runtime Sentry env | backend/worker/bot/frontend/admin containers expose Sentry env keys |
| Loki health | `/ready -> ready` |
| Loki recent error pattern | at least one error-pattern stream exists; continue daily review |
| Loki sensitive-pattern sample | one stream matched `ApiKey` as a Sentry model name; sampled line did not expose a secret |

Do not export raw Loki lines into repo evidence. Keep using redacted counts and sanitized samples only.

## Data, Payment And Support Checks

| Check | Result |
|---|---|
| PostgreSQL | alive; 121 public tables; Alembic version `20260520_stage1_webhook_logs` |
| Mobile users | `1` |
| Admin users | `1` |
| Audit logs | `2` |
| Subscription plans | `0` |
| Payments | `0` |
| Payment attempts | `0` |
| Payment disputes | `0` |
| Webhook logs | `1` |
| Support profiles | `0` |
| Paid orphan candidates | none observed because paid flow remains disabled and no payments exist |

Notes:

- Production catalog is still empty. Real Telegram Stars or paid checkout cannot be used by users until S1 plans and approved prices are seeded.
- Support profile data remains empty. This is acceptable for owner/internal smoke but should be seeded before widening the cohort.

## Valkey And Queue Health

| Check | Result |
|---|---|
| Valkey ping | `PONG` |
| Used memory | `1.55M` |
| Max memory | `256.00M` |
| Policy | `noeviction` |
| Rejected connections | `0` |
| Evicted keys | `0` |

## Backups

| Check | Result |
|---|---|
| App backup files found | CyberVPN PostgreSQL and Remnawave PostgreSQL backups under `/srv/cybervpn/backups` |
| Gzip integrity | all checked `.sql.gz` backups returned `gzip_ok` |
| Home backup listing | no files were returned from the non-root `/srv/storage/backups` listing |
| VPN node backups | no VPN-node backup artifacts found |

Backup integrity exists for recent app DB dumps, but this RENT-11 pass is not a replacement for the restore drill evidence. Keep restore drill as a separate launch gate.

## Daily Stabilization Checklist

| # | Check | Status | Notes |
|---:|---|---|---|
| 1 | Sentry critical errors | `PASS_WITH_NOTES` | Sentry healthy; critical issue counts require UI/API auth review during daily ops |
| 2 | Alertmanager firing alerts | `PASS_WITH_NOTES` | no S1 customer-runtime alert firing; home swap and Stage2 status alerts remain |
| 3 | Payment reconciliation | `PASS` | paid flow disabled; payments/attempts are zero |
| 4 | Provisioning failures | `PASS_WITH_NOTES` | VPN node is reachable; direct ad-hoc Remnawave API probe is rejected by Remnawave proxy/HTTPS guard and should not be used as the health contract |
| 5 | Paid-but-no-access/orphan queue | `PASS` | no paid records exist |
| 6 | Support tickets | `PASS_WITH_NOTES` | support profiles/tickets are empty; seed before wider cohort |
| 7 | VPN node health | `PASS` | container running, logs quiet, TCP probes green |
| 8 | Worker lag/retry/dead-letter | `PASS_WITH_NOTES` | worker/scheduler healthy; no 2h worker/scheduler error counts observed |
| 9 | Backups | `PASS_WITH_NOTES` | app DB backup gzip integrity OK; restore evidence remains separate |
| 10 | Frontend/public endpoint probes | `PARTIAL` | external probes pass; home Prometheus HTTPS probes to `prod-app-1` fail due network/TLS path issue |
| 11 | Telegram Bot and Mini App metrics | `PASS_WITH_NOTES` | bot healthy; real cohort metrics will appear after more traffic |
| 12 | PostgreSQL and Redis/Valkey health | `PASS` | DB alive; Valkey `PONG`, no rejected/evicted keys |
| 13 | Home hardware dashboard | `PASS_WITH_WARNINGS` | disk/load OK; swap alerts firing; SMART check needs sudo/root path in daily ops |
| 14 | Loki logs and sensitive payload check | `PASS_WITH_NOTES` | Loki ready; one sensitive-pattern sample was a Sentry `ApiKey` model name, not a secret |
| 15 | S1 success metrics/cohort criteria | `PARTIAL` | beta traffic is still too small; catalog is empty; cannot judge conversion/provisioning SLO yet |
| 16 | Known issues update | `PASS` | issues below recorded |

## Known Issues

| ID | Severity | Issue | Recommendation |
|---|---|---|---|
| `S1-RENT11-001` | `P1` | Home observability host cannot complete HTTP/TLS probes to `prod-app-1`, although external operator probes return `200` | `STAGE1-RENT-11A` relay was removed by `STAGE1-RENT-11B` because the VPN node must stay node-only. Close with provider/network route fix or an explicitly approved non-node ops path. Do not rely on home public-web blackbox until fixed. |
| `S1-RENT11-002` | `P2` | Home server swap alerts are firing | Reduce home stack pressure or tune memory/swap before relying on home observability for larger beta. |
| `S1-RENT11-003` | `P1 before paid cohort` | Production subscription catalog is empty | Seed S1 plans/prices before real Telegram Stars or paid checkout proof. |
| `S1-RENT11-004` | `P2` | Support profile/ticket data is empty | Seed support profile and confirm escalation flow before inviting non-owner users. |
| `S1-RENT11-005` | `P2` | Direct Remnawave HTTP probe from backend container triggers Remnawave proxy/HTTPS guard | Use approved Remnawave metrics/provisioning evidence as health contract; avoid noisy direct probes. |

## Validation

Commands run:

```text
python3 scripts/validate-s1-observability-dashboards.py
python3 scripts/validate-s1-alerting.py
python3 -m json.tool infra/prometheus/targets/stage1-public-web.json
python3 -m json.tool infra/prometheus/targets/stage1-vpn-node-tcp.json
promtool check config /tmp/prometheus.stage1-rent11.yml
promtool check rules /tmp/stage1_alerts.stage1-rent11.yml
blackbox_exporter --config.check --config.file=/tmp/blackbox.stage1-rent11.yml
npm audit --omit=dev --audit-level=high
```

Results:

```text
PASS: S1 observability dashboard, recording rules and scrape jobs are wired.
PASS: S1 alert rules and Alertmanager Telegram/email routing are wired.
target-json-ok
Prometheus config valid
Stage 1 rules valid
Blackbox config valid
npm audit high/critical gate passed; remaining advisories are moderate and tracked separately
```

## Next Step

```text
STAGE1-RENT-11C: Direct Home-to-Prod-App Network Path Closure
```

Purpose: close the remaining direct-route observability blind spot before widening the beta cohort.

Closure note:

```text
STAGE1-RENT-11A was superseded by docs/evidence/releases/stage1-rented-prod-11b-node-only-and-direct-home-prod-app-20260520T170051Z.md.
The VPN node relay is removed. Direct home -> prod-app-1 HTTP/TLS remains open.
```
