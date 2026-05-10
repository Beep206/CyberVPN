# Stage 1 Observability Server Review

Date: 2026-05-10 16:13 UTC  
Server: `10.10.10.34`  
Host: `cybervpn-h-ops`  
Purpose: confirm that the Stage 1 public deployment plan accounts for the Grafana/Prometheus metrics already prepared on the home observability server.

## Server State Checked

Running observability/control services include:

- `cybervpn-prometheus`
- `cybervpn-grafana`
- `cybervpn-loki`
- `cybervpn-alertmanager`
- `cybervpn-promtail`
- `cybervpn-blackbox-exporter`
- `cybervpn-cadvisor`
- `cybervpn-node-exporter`
- `cybervpn-uptime-kuma`
- self-hosted Sentry services
- GitLab and GitLab Runner

## Grafana Dashboard Inventory

Dashboards currently present on the server:

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
- Stage 2 dashboards for payment reconciliation, status page, support SLA, subscription expiry, release quality and analytics
- Stage 3 partner/reseller dashboards
- Helix dashboard

Stage 2/Stage 3/Helix dashboards are treated as future/lab visibility only. They are not Stage 1 runtime approval.

## Stage 1 Dashboard Coverage Observed

The `stage1-controlled-public-beta` dashboard contains panels for:

- backend/API target health
- worker target health
- Telegram bot target health
- PostgreSQL target health
- Redis/Valkey target health
- Remnawave target health
- API HTTP p95 latency
- API error ratio
- auth success ratio
- registrations over 24h
- payment success ratio over 1h
- payment events by status/currency
- paid-but-no-access reconciliation items
- paid-but-no-access max age
- Remnawave external API error ratio
- Remnawave healthy node count
- trial activation
- Mini App config delivery failure
- worker queue depth
- worker task error ratio
- PostgreSQL active connections and rollback ratio
- Redis memory and rejected connections
- Telegram bot update rate and error ratio
- payment reconciliation launch blocker

## Host Hardware Dashboard Coverage Observed

The `cybervpn-h-hardware` dashboard contains panels for:

- SMART health
- NVMe wear
- disk temperature
- RAS/MCE/AER errors
- RAM available
- swap usage
- disk usage
- CPU iowait
- network errors
- container memory
- container CPU
- Docker JSON log size

This is important because Stage 1 observability/control-plane services run on the home server.

## Prometheus Targets Observed

Current active targets include:

- `alertmanager`
- `blackbox-exporter`
- `blackbox-http`
- `blackbox-s1-http`
- `cadvisor`
- `grafana`
- `loki`
- `node-exporter`
- `prometheus`
- `stage2-public-endpoints`

Current blackbox checks cover `gitlab.h.cyber-vpn.net`, `grafana.h.cyber-vpn.net`, `sentry.h.cyber-vpn.net`, `prometheus.h.cyber-vpn.net`, `alerts.h.cyber-vpn.net`, `uptime.h.cyber-vpn.net` and `registry.h.cyber-vpn.net`.

Stage 1 application targets are not expected to be up until the app deploy phases create backend, worker, bot, frontend/admin and Remnawave targets.

## Prometheus Rules Observed

Relevant active Stage 1 rule groups include:

- `cybervpn_h_s1_home_platform_alerts`
- `cybervpn_stage1_controlled_public_beta_alerts`
- `stage1_controlled_public_beta_dashboard`
- `cybervpn-h-host`

Current active alerts:

- `CyberVPNSwapInUse`
- `CyberVPNSwapUsageAbove1GiB`
- `Stage1NoHealthyRemnawaveNodes`

The Remnawave alert is expected until a real Remnawave node target is connected. Swap alerts should be reviewed before beta expansion but do not block documentation/plan work.

## Plan Changes Made

Updated `docs/plans/2026-05-10-cybervpn-stage1-public-internet-deployment-plan.md` to add:

- a dedicated Stage 1 Metrics Contract;
- explicit metric coverage for service availability, public edge, auth, payments, provisioning, Remnawave, worker, database/cache, Telegram/Mini App, support/admin, logs, Sentry, host hardware, backup/restore and alert delivery;
- metrics/log requirements in `STAGE1-PUB-05`;
- frontend/blackbox metrics in `STAGE1-PUB-08`;
- bot/Mini App metrics in `STAGE1-PUB-09`;
- Remnawave latency/healthy-node metrics in `STAGE1-PUB-10`;
- payment/reconciliation metrics in `STAGE1-PUB-11`;
- a much stricter observability evidence gate in `STAGE1-PUB-12`;
- dashboard-baseline requirements in `STAGE1-PUB-15`;
- expanded daily checks in `STAGE1-PUB-16`.

## Decision

The plan now requires broad metrics collection before paid beta and before expanding the first beta cohort. Stage 1 can continue to `STAGE1-PUB-01`, but public beta expansion is blocked until Grafana shows real app/payment/provisioning/Remnawave data and alert delivery works.
