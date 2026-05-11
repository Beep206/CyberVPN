# Stage 1 Stabilization Daily Evidence

Date: 2026-05-11T07:35:00Z

Stage: `STAGE1-PUB-16`

Result:

```text
CONTINUE internal smoke / pre-beta stabilization.
NO-GO for external beta cohort expansion.
```

## Scope

This is the first Stage 1 stabilization loop after public-domain internal smoke.

No real beta users were invited during this check. Payments, public registration, backend trial provisioning and paid provisioning stayed disabled.

## Runtime Summary

Server:

```text
host=cybervpn-h-ops
checked_at=2026-05-11T07:35:00Z
```

Stage 1 runtime containers are running and healthy:

```text
cybervpn-frontend              healthy
cybervpn-admin                 healthy
cybervpn-backend               healthy
cybervpn-scheduler             healthy
cybervpn-worker                healthy
cybervpn-telegram-bot          healthy
cybervpn-postgres              healthy
cybervpn-valkey                healthy
cybervpn-remnawave             healthy
cybervpn-remnawave-node-local  healthy
cybervpn-remnawave-postgres    healthy
cybervpn-remnawave-valkey      healthy
```

Public endpoint smoke:

```text
200 1.080213 https://cyber-vpn.net/en-EN/status
200 1.132238 https://cyber-vpn.net/ru-RU/privacy-policy
200 0.894371 https://admin.cyber-vpn.net/ru-RU/login
200 0.982949 https://api.cyber-vpn.net/healthz
301 0.664635 https://cyber-vpn.org/en-EN/status
301 0.678754 https://admin.cyber-vpn.org/ru-RU/login
```

Backend direct health:

```text
GET http://127.0.0.1:18080/health -> 200 {"status":"ok"}
GET http://127.0.0.1:18080/ready -> 404
```

`/ready` is still not exposed on the direct backend port. This was already observed during `STAGE1-PUB-15A`; public `api.cyber-vpn.net/healthz` and backend `/health` are healthy.

## Daily Checks

| # | Check | Result | Evidence / Interpretation |
|---:|---|---:|---|
| 1 | Sentry critical errors | LIMITED PASS | Sentry health returns `200`; Sentry web log critical/fatal/traceback/error count in last sampled logs was `0`. App container logs show no `level=error/critical/fatal` or traceback in the last sampled logs. Sentry issue list was not queried because no Sentry API token was used for this gate. |
| 2 | Alertmanager firing alerts | WARN | Two firing host alerts: `CyberVPNSwapInUse` and `CyberVPNSwapUsageAbove1GiB`. |
| 3 | Payment reconciliation | SAFE / NO DATA | Payments are disabled. DB: `payments_total=0`, `payment_attempts_total=0`. Metrics: `stage1:payment_reconciliation_items:current=0`, `stage1:payment_reconciliation_p0_items:current=0`, `cybervpn_stage1_payment_reconciliation_launch_blocked=0`. |
| 4 | Provisioning failures | BLOCKED / NO DATA | Backend provisioning flags are disabled. `stage1:remnawave_external_error_ratio:5m=NO_DATA`. No real trial/paid provisioning events exist yet. |
| 5 | Paid-but-no-access / orphan queue | PASS for current paused state | DB has no payments/attempts. Metrics show zero current and P0 reconciliation items. No orphan payment can exist while paid flow remains disabled. |
| 6 | Support tickets | LIMITED | No support ticket table is active in current S1 runtime. DB: `payment_disputes_open=0`, `notifications_pending=0`, `notifications_failed=0`, `support_profiles_active=0`. Public support mailbox DNS still has no MX/DMARC evidence. |
| 7 | VPN node health | PASS for lab / BLOCKED for users | Remnawave API returns one connected node: `stage1-lab-home-node`, internal hostname, port `22230`, `connected=True`, `disabled=False`. This remains lab-only and does not close production VPN node proof. |
| 8 | Worker lag / retry / dead-letter | PASS for current paused state | Worker Prometheus target up, `stage1:worker_queue_depth:current=0`, Redis `XLEN taskiq:stream=0`, queue gauges for `email` and `result_backend` are `0`. |
| 9 | Backups | PASS with access note | Latest backup/restore evidence from `STAGE1-PUB-14` exists at `2026-05-11T06:46:30Z`. Backup directories exist under `/srv/storage/backups/cybervpn-stage1/` and are root-only. Current non-sudo SSH user can verify directories, not list root-only backup files. |
| 10 | Frontend/public endpoint probes | PASS | Customer site, legal page, admin login, API health and mirror redirects return expected `200`/`301`. |
| 11 | Telegram Bot / Mini App metrics | PASS for bot webhook smoke | Telegram `getWebhookInfo`: `ok=True`, webhook URL set, pending updates `0`, last error absent, allowed updates count `3`. Bot Prometheus target is up. Real Telegram client/Mini App user-flow smoke is still pending. |
| 12 | PostgreSQL and Redis/Valkey health | PASS | App PostgreSQL `pg_isready` accepts connections; Remnawave PostgreSQL accepts connections; app Valkey and Remnawave Valkey return `PONG`. App DB has `120` public tables. |
| 13 | Home-server hardware dashboard | WARN | SMART metrics report NVMe/HDD healthy, no pending/reallocated sectors, NVMe temperature `38C`, HDD temperature `36C`. Root filesystem has `814G` available, `/srv/storage` has `1.8T` available. Memory pressure exists: `46Gi` total, `17Gi` available, `12Gi` swap used. GitLab container is at `15.99GiB / 16GiB`. |
| 14 | Loki logs and sensitive payload logging | FAIL | Loki is receiving logs, but a sensitive-header query returned at least one match in the last hour. The observed issue is request-header logging for GitLab runner polling. No secret value is copied into this evidence. Caddy/Loki header redaction must be fixed before widening beta or sharing log exports. |
| 15 | S1 success metrics and cohort criteria | NO-GO | No beta cohort exists yet. `stage1:registrations:24h=0`; `stage1:payment_success_ratio:1h=NO_DATA`; `stage1:api_http_p95_seconds:5m=NaN`; `stage1:remnawave_healthy_nodes:current=1` lab-only. Success metrics cannot be judged until real trial/payment/provisioning events exist. |
| 16 | Known issues updated | PASS | Known issues are recorded below and mirrored into the remaining-work document. |

## Selected Metrics

```text
stage1:target_up:
  cybervpn-telegram-bot=1
  remnawave=1
  redis=1
  cybervpn-worker=1
  cybervpn-local-backend=1
  postgres=1

stage1:registrations:24h=0
stage1:payment_reconciliation_items:current=0
stage1:payment_reconciliation_p0_items:current=0
stage1:worker_queue_depth:current=0
stage1:postgres_rollback_ratio:5m=0
stage1:redis_memory_used_bytes=1556248
stage1:remnawave_healthy_nodes:current=1
```

```text
cybervpn_stage1_payment_reconciliation_max_age_minutes=0
cybervpn_stage1_payment_reconciliation_launch_blocked=0
cybervpn_queue_depth{queue="email"}=0
cybervpn_queue_depth{queue="result_backend"}=0
redis_connected_clients=7
redis_rejected_connections_total=0
pg_stat_database_numbackends{datname="cybervpn"}=2
```

## Database Snapshot

```text
payments_total=0
payments_paid_like=0
payment_attempts_total=0
payment_attempts_nonterminal=0
payment_disputes_open=0
notifications_pending=0
notifications_failed=0
partner_bot_provisioning_open=0
audit_logs_24h=5
mobile_users_total=0
active_mobile_users=0
active_plans=0
support_profiles_active=0
```

## Hardware Snapshot

```text
Mem: 46Gi total, 29Gi used, 17Gi available
Swap: 31Gi total, 12Gi used, 19Gi free
Root filesystem: 814G available, 9% used
/srv/storage: 1.8T available, 1% used
Load average: 0.58, 0.60, 0.64
```

Container pressure:

```text
cybervpn-backend               310.5MiB / 768MiB   40.43%
cybervpn-worker                163.4MiB / 512MiB   31.91%
cybervpn-scheduler             102.8MiB / 256MiB   40.16%
cybervpn-telegram-bot          186.5MiB / 384MiB   48.57%
cybervpn-remnawave             471.2MiB / 768MiB   61.35%
cybervpn-remnawave-node-local   91.45MiB / 512MiB  17.86%
cybervpn-gitlab                15.99GiB / 16GiB    99.94%
sentry-web                       1.33GiB / 3GiB    44.32%
prometheus                     135.9MiB / 3GiB      4.42%
grafana                        112.3MiB / 1GiB     10.97%
```

SMART/exporter metrics:

```text
cybervpn_h_smart_device_healthy{device="/dev/nvme0"}=1
cybervpn_h_smart_device_healthy{device="/dev/sda"}=1
cybervpn_h_smart_current_pending_sectors_total{device="/dev/sda"}=0
cybervpn_h_smart_reallocated_sectors_total{device="/dev/sda"}=0
cybervpn_h_smart_temperature_celsius{device="/dev/nvme0"}=38
cybervpn_h_smart_temperature_celsius{device="/dev/sda"}=36
```

## Known Issues

| ID | Severity | Issue | Recommendation |
|---|---:|---|---|
| S1-STAB-20260511-001 | P0 | No rented/always-on production VPN node is proven. Only `stage1-lab-home-node` exists. | Do not invite external beta users. Provision production VPN node and rerun `STAGE1-PUB-15C`. |
| S1-STAB-20260511-002 | P0 for paid beta | Paid path remains disabled and no provider proof exists for a paid cohort. | Keep `PAYMENTS_ENABLED=false` until provider credentials, webhook and reconciliation evidence pass. |
| S1-STAB-20260511-003 | P1/P0 before wider beta | Loki/Caddy logs include sensitive request-header material for GitLab runner polling. | Redact sensitive headers at Caddy/log pipeline, purge or reduce retention for affected logs, and rotate runner token if logs have been exported/shared or if owner wants strict hygiene. |
| S1-STAB-20260511-004 | P1 | GitLab container is at memory limit and host swap is actively used. | Reduce GitLab memory pressure, move/limit non-customer services, or accept only tiny internal smoke until resolved. |
| S1-STAB-20260511-005 | P1 | Support/refund mailbox DNS remains unproven: no MX/DMARC output for `cyber-vpn.net` / `cyber-vpn.org`. | Configure and prove MX/SPF/DKIM/DMARC before relying on email support. |
| S1-STAB-20260511-006 | P1 | `support_profiles_active=0` and `active_plans=0` in app DB. | Seed S1 support profile and active plan catalog before enabling registration/trial/payment. |
| S1-STAB-20260511-007 | P2 | Backend direct `/ready` returns `404`. | Either expose a real readiness endpoint or keep using `/healthz`/`/health` and document the probe contract. |

## Decision

Stage 1 can continue internal smoke and operational hardening.

External beta cohort must remain paused because P0 user-facing blockers remain:

- production VPN node proof missing;
- trial provisioning proof missing;
- paid provider proof missing.

Do not expand beyond internal smoke until:

1. `STAGE1-PUB-15B` approved snapshot/immutable tag is complete;
2. sensitive header logging is redacted;
3. production VPN node and trial provisioning proof pass;
4. one payment provider path passes if paid beta is included;
5. support mailbox or Telegram-only support decision is proven for the first cohort.

## Verification

```text
git diff --check
PASS
```

```text
targeted secret scan over this evidence file, the Stage 1 remaining-work file and the Stage 1 deployment plan
PASS: no matches
```

```text
targeted static scan over this evidence file, the Stage 1 remaining-work file and the Stage 1 deployment plan
PASS: no dangerous execution-pattern matches
```

```text
npm audit --omit=dev --audit-level=high
PASS: no high/critical production npm audit blocker
NOTE: audit reports 2 moderate Next/PostCSS advisories; the suggested forced fix would install an incompatible/breaking Next version and was not applied.
```

## DEMO

Component checks:

```text
Prometheus /api/v1/alerts -> 2 firing host swap alerts
Prometheus stage1 recording rules -> core S1 targets up, queues zero, payment/provisioning no-data where flows are disabled
PostgreSQL pg_isready -> accepting connections
Valkey redis-cli ping -> PONG
Telegram getWebhookInfo -> ok=True, pending updates 0, no last error
Remnawave /api/nodes -> one connected lab-only node
```

Feature check:

```text
Public Stage 1 smoke:
  cyber-vpn.net status/legal -> 200
  admin.cyber-vpn.net login -> 200
  api.cyber-vpn.net healthz -> 200
  .org mirrors -> 301

Result:
  Internal smoke remains stable.
  Real beta users remain blocked by production VPN node, payment provider and sensitive log redaction issues.
```
