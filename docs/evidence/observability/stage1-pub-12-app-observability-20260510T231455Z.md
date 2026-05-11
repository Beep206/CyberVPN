# STAGE1-PUB-12 — Observability Integration Evidence

Date: 2026-05-10T23:14:55Z
Scope: Stage 1 public internet runtime on `10.10.10.34`
Result: `PASS_WITH_NOTES`

## Summary

STAGE1-PUB-12 connected the live Stage 1 app runtime to the prepared home observability stack:

- Prometheus now scrapes backend, worker, Telegram bot, PostgreSQL exporter, Redis/Valkey exporter, Remnawave and public blackbox probes.
- Grafana has the Stage 1 dashboard and companion CyberVPN dashboards provisioned.
- Loki receives Docker JSON logs from Stage 1 containers.
- Sentry runtime DSN is configured on backend, worker, Telegram bot, frontend and admin using the existing self-hosted smoke DSN.
- Alertmanager accepted a synthetic Stage 1 alert and exposed successful Telegram/email notification counters with zero notification failures.

## Changes Applied

| Area | Change |
|---|---|
| App compose | Added `cybervpn-postgres-exporter` and `cybervpn-redis-exporter` to the `local-data` profile. |
| Observability compose | Attached `cybervpn-prometheus` to `cybervpn_stage1_metrics` in addition to the existing observability/backend networks. |
| Prometheus config | Added Stage 1 jobs: `cybervpn-local-backend`, `cybervpn-worker`, `postgres`, `redis`. |
| Runtime env | Replaced invalid non-URL Sentry DSN placeholders with the valid self-hosted smoke DSN for S1 runtime proof. |
| Telegram bot env | Added `TELEGRAM_BOT_OBSERVABILITY_INTERNAL_SECRET` for protected contract probing. |

Server-side backups were created before overwriting root-owned configs:

- `/srv/cybervpn-h/compose/app/docker-compose.yml.stage1-pub-12.<timestamp>.bak`
- `/srv/cybervpn-h/compose/observability/compose.yml.stage1-pub-12.<timestamp>.bak`
- `/srv/cybervpn-h/configs/prometheus/prometheus.yml.stage1-pub-12.<timestamp>.bak`
- `/srv/cybervpn-h/secrets/*.stage1-pub-12*.bak`

## Runtime Health

All Stage 1 runtime and observability containers were healthy/running after the change:

| Container | State |
|---|---|
| `cybervpn-stage1-cybervpn-backend-1` | healthy |
| `cybervpn-stage1-cybervpn-worker-1` | healthy |
| `cybervpn-stage1-cybervpn-scheduler-1` | healthy |
| `cybervpn-stage1-cybervpn-telegram-bot-1` | healthy |
| `cybervpn-stage1-cybervpn-frontend-1` | healthy |
| `cybervpn-stage1-cybervpn-admin-1` | healthy |
| `cybervpn-stage1-cybervpn-postgres-exporter-1` | healthy |
| `cybervpn-stage1-cybervpn-redis-exporter-1` | healthy |
| `cybervpn-prometheus` | running |
| `cybervpn-grafana` | running |
| `cybervpn-loki` | running |
| `cybervpn-alertmanager` | running |

## Prometheus Targets

Required Stage 1 targets were `up`:

| Job | Instance | Health |
|---|---|---|
| `cybervpn-local-backend` | `cybervpn-stage1-cybervpn-backend-1:9091` | `up` |
| `cybervpn-worker` | `cybervpn-stage1-cybervpn-worker-1:9091` | `up` |
| `cybervpn-telegram-bot` | `cybervpn-stage1-cybervpn-telegram-bot-1:8080` | `up` |
| `postgres` | `cybervpn-stage1-cybervpn-postgres-exporter-1:9187` | `up` |
| `redis` | `cybervpn-stage1-cybervpn-redis-exporter-1:9121` | `up` |
| `remnawave` | `remnawave:3001` | `up` |

Useful live series observed:

| Query | Result |
|---|---|
| `stage1:target_up` | backend, worker, bot, postgres, redis and Remnawave are `1` |
| `stage1:redis_memory_used_bytes` | non-empty, live Redis memory value |
| `stage1:postgres_rollback_ratio:5m` | non-empty, live PostgreSQL exporter value |
| `stage1:remnawave_healthy_nodes:current` | `1` |
| `probe_success{job="blackbox-stage1-public-web"}` | all S1 public probes returned `1` |

Prometheus validation:

```text
promtool check config /etc/prometheus/prometheus.yml
SUCCESS: 7 rule files found
SUCCESS: /etc/prometheus/prometheus.yml is valid prometheus config file syntax
SUCCESS: stage1_alerts.yml, 21 rules found
SUCCESS: stage1_dashboard_recording_rules.yml, 15 rules found
```

## Sentry

Sentry runtime DSN is present in all S1 runtime containers:

| Surface | DSN present | Release |
|---|---:|---|
| Backend API | yes | `stage1-beta-rc.1` |
| Task worker | yes | `stage1-beta-rc.1` |
| Telegram bot | yes | `stage1-beta-rc.1` |
| Frontend | yes | `stage1-beta-rc.1` |
| Admin | yes | `stage1-beta-rc.1` |

Protected runtime contracts:

| Surface | Contract result |
|---|---|
| Frontend | `dsnConfigured=true`, `publicDsnConfigured=true`, `environment=production`, `release=stage1-beta-rc.1` |
| Admin | `dsnConfigured=true`, `publicDsnConfigured=true`, `environment=production`, `release=stage1-beta-rc.1` |
| Telegram bot | `dsn_configured=true`, `environment=production`, `release=stage1-beta-rc.1`, `bot_mode=webhook` |

Self-hosted ingestion smoke:

| Field | Result |
|---|---|
| HTTP status | `200` |
| Success metric | `cybervpn_h_sentry_ingestion_smoke_success 1` |
| Project | `2` |
| Event ID | `d38ded85371a75771306657abce640bd` |

Note: per-service Sentry project DSNs were not proven. S1 currently uses the valid self-hosted smoke DSN for runtime proof. Replace with real per-surface DSNs before a stricter public release gate.

## Loki

Loki is ready and receives Docker JSON logs:

| Check | Result |
|---|---|
| `GET /ready` | `ready` |
| Docker log job | `docker-json` series present |
| Worker sample | `queue_depth_monitoring_complete` entries visible |
| Blackbox sample | `Probe succeeded` entries visible |

Note: Promtail currently labels Docker logs primarily by `job`, `filename`, `host`, `stream` and `service_name=docker-json`. This is enough for emergency search, but service/container label enrichment should be added later for better dashboards.

## Grafana

Grafana API health is OK and the following dashboards are provisioned:

| Dashboard | UID |
|---|---|
| `Stage 1 Controlled Public Beta` | `stage1-controlled-public-beta` |
| `CyberVPN Application Metrics` | `cybervpn-application` |
| `CyberVPN Control Plane Observability` | `cybervpn-control-plane-observability` |
| `CyberVPN Edge Observability` | `cybervpn-edge-observability` |
| `CyberVPN h Hardware & Host` | `cybervpn-h-hardware` |
| `CyberVPN Infrastructure` | `cybervpn-infrastructure` |
| `CyberVPN Mini App Runtime` | `cybervpn-miniapp-runtime` |
| `CyberVPN PostgreSQL` | `cybervpn-postgres` |
| `CyberVPN Redis` | `cybervpn-redis` |
| `CyberVPN Remnawave Runtime` | `cybervpn-api` |
| `CyberVPN Task Worker` | `cybervpn-worker` |

Static repo validation also passed:

```text
python3 scripts/validate-s1-observability-dashboards.py
PASS: S1 observability dashboard, recording rules and scrape jobs are wired.

python3 scripts/validate-s1-alerting.py
PASS: S1 alert rules and Alertmanager Telegram/email routing are wired.
```

## Alertmanager

Alertmanager live config includes Stage 1 Telegram and email receivers:

- Telegram chat: `-5173727789`
- Email receiver: `alerts@cyber-vpn.net`
- SMTP: configured through server secret file, value redacted

Synthetic alert:

| Check | Result |
|---|---|
| Posted alert | `Stage1Pub12AlertDeliveryTest` |
| Alertmanager state after post | `active`, `p1`, `warning`, `observability` |
| `increase(alertmanager_notifications_total[5m])` | non-zero for `telegram` and `email` |
| `increase(alertmanager_notifications_failed_total[5m])` | `0` for `telegram` and `email` |
| Synthetic alert cleanup | resolved after test |

Current Prometheus alerts after cleanup:

- No Stage 1 app alert is firing.
- Existing host alerts remain for swap usage: `CyberVPNSwapInUse`, `CyberVPNSwapUsageAbove1GiB`.

## Notes And Recommendations

1. Keep `PAYMENTS_ENABLED=false` until payment-provider credentials and payment evidence are real. Payment dashboards are wired, but real payment traffic is intentionally blocked.
2. Replace the shared Sentry smoke DSN with per-service DSNs for `backend-api`, `task-worker`, `telegram-bot`, `web-frontend` and `web-admin` before S2 or before a stricter S1 go-live gate.
3. Add Promtail Docker metadata enrichment later so Loki labels include service/container names directly.
4. Review host swap alerts before inviting a larger beta cohort. They are not S1 app blockers, but they reduce observability headroom on the home server.

## Acceptance Result

`STAGE1-PUB-12` is complete enough for the current no-cost Stage 1 deployment path.

The next stage is `STAGE1-PUB-13: Security, Legal And Support Gate`.

## Security Review

| Check | Result |
|---|---|
| `git diff --check` on touched Stage 1 observability files | PASS |
| Secret-pattern scan on touched files | PASS |
| Dangerous runtime pattern scan on touched files | PASS |
| `npm audit --omit=dev --audit-level=high` | PASS for high/critical; existing moderate Next/PostCSS advisory remains tracked separately |
