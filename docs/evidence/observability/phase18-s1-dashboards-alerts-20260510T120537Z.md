# Phase 18 S1 Dashboards And Alerts Evidence

Date: `2026-05-10`

Host: `cybervpn-h-ops`

Server: `10.10.10.34`

## Scope

Phase 18 provisions the first operational S1 dashboard and alert layer for CyberVPN:

- application and platform dashboards from repo-controlled Grafana JSON files
- Prometheus alert rules for host, service, business-flow, Sentry, VPN, and TLS signals
- Alertmanager rendering prepared for Telegram primary and optional SMTP/email fallback
- local Alertmanager smoke evidence while live Telegram credentials are pending

## Remote Evidence

Remote evidence directory:

```text
/srv/cybervpn-h/evidence/observability/phase18-s1-dashboards-alerts-20260510T120537Z
```

Captured files:

```text
alertmanager-smoke-local.tsv
alertmanager-status.json
dashboard-files.txt
grafana-dashboard-reload.out
grafana-dashboard-search.json
grafana-dashboard-search.tsv
observability-compose-ps.out
prometheus-rule-groups.tsv
prometheus-active-alerts.tsv
prometheus-rules.json
prometheus-status-config.json
prometheus-targets.json
prometheus-targets.tsv
promtool-check-config.out
rule-files.txt
sentry-smoke-query.json
test-alert-20260510T121820Z.json
test-alert-20260510T121820Z.response
test-alert-20260510T121820Z.status.json
```

## Dashboards

Grafana folder:

```text
CyberVPN h
```

Provisioned dashboards:

```text
customer-growth-notification-delivery    Customer Growth Notification Delivery
cybervpn-api                             CyberVPN Remnawave Runtime
cybervpn-application                     CyberVPN Application Metrics
cybervpn-auth-registration               Auth & Registration
cybervpn-control-plane-observability     CyberVPN Control Plane Observability
cybervpn-edge-observability              CyberVPN Edge Observability
cybervpn-error-monitoring                CyberVPN Remnawave Runtime Monitoring
cybervpn-h-hardware                      CyberVPN h Hardware & Host
cybervpn-helix                           CyberVPN Helix
cybervpn-infrastructure                  CyberVPN Infrastructure
cybervpn-miniapp-runtime                 CyberVPN Mini App Runtime
cybervpn-otp                             CyberVPN OTP Email Verification
cybervpn-postgres                        CyberVPN PostgreSQL
cybervpn-redis                           CyberVPN Redis
cybervpn-telegram-native-login           Telegram Native Login
cybervpn-worker                          CyberVPN Task Worker
logs-overview                            Logs Overview
partner-platform-frontend-ux             Partner Platform Frontend UX
partner-platform-runtime                 Partner Platform Runtime
slo-tracking                             Remnawave SLO Tracking
stage1-controlled-public-beta            Stage 1 Controlled Public Beta
traces-overview                          Traces Overview
```

## Alert Rules

Prometheus config validation passed with:

```text
host-alerts.yml
s1-home-alerts.yml
stage1_alerts.yml
stage1_dashboard_recording_rules.yml
```

Phase 18 home alert coverage:

```text
CyberVPNHostDown
CyberVPNDiskUsage80
CyberVPNDiskUsage90
CyberVPNSwapUsageAbove1GiB
CyberVPNIOWaitHigh
CyberVPNDockerContainerRestarting
CyberVPNGitLabUnavailable
CyberVPNSentryUnavailable
CyberVPNSentryIngestionFailing
CyberVPNPaymentErrorsElevated
CyberVPNWebhookRetriesElevated
CyberVPNVpnNodeUnavailable
CyberVPNTLSCertificateNearExpiry
```

## Prometheus Targets

Verified targets:

```text
alertmanager                                                   up
blackbox-exporter                                              up
alerts.h.cyber-vpn.net edge health                             up
gitlab.h.cyber-vpn.net edge health                             up
grafana.h.cyber-vpn.net edge health                            up
prometheus.h.cyber-vpn.net edge health                         up
sentry.h.cyber-vpn.net edge health                             up
uptime.h.cyber-vpn.net edge health                             up
gitlab.h.cyber-vpn.net/users/sign_in                           up
sentry.h.cyber-vpn.net/_health/                                up
cadvisor                                                       up
grafana                                                        up
loki                                                           up
node-exporter                                                  up
prometheus                                                     up
```

## Sentry Ingestion Smoke

Sentry ingestion smoke is published by:

```text
/srv/cybervpn-h/scripts/write-sentry-ingestion-smoke.sh
cybervpn-sentry-ingestion-smoke.timer
```

Prometheus query result:

```text
cybervpn_h_sentry_ingestion_smoke_success 1
node_textfile_scrape_error 0
```

## Alertmanager

Alertmanager was changed from static local/no-op config to a rendered config:

```text
/srv/cybervpn-h/configs/alertmanager/render-alertmanager.sh
/srv/cybervpn-h/configs/alertmanager/alertmanager.yml.template
/srv/cybervpn-h/configs/alertmanager/templates/telegram.tmpl
/srv/cybervpn-h/secrets/alertmanager.env
```

Current mode:

```text
local-log-only
```

Reason:

```text
ALERTMANAGER_TELEGRAM_BOT_TOKEN and ALERTMANAGER_TELEGRAM_CHAT_ID are not installed yet.
```

Local Alertmanager smoke:

```text
CyberVPNPhase18TelegramDeliverySmoke    p1    active
```

## Current Active Alerts

Current active alerts after Phase 18:

```text
CyberVPNSwapInUse                  firing    warning     Swap usage above 1 GiB
CyberVPNSwapUsageAbove1GiB         firing    warning     CyberVPN swap usage above 1 GiB
Stage1NoHealthyRemnawaveNodes      firing    critical    Stage 1 has no healthy Remnawave nodes
```

Interpretation:

- Swap alert is expected until the overnight memtester/swap pressure state settles or the host is rebooted/cleared after review.
- Remnawave node alert is expected because production VPN node metrics are not connected to this Prometheus yet.

## Acceptance Status

- [x] Dashboards imported or provisioned.
- [ ] Test alert reaches Telegram.
- [x] Alert evidence saved.

Telegram delivery is the only open acceptance item. The server-side renderer and smoke script are ready; completing it requires placing the Telegram bot token and chat ID into `/srv/cybervpn-h/secrets/alertmanager.env`, recreating Alertmanager, and rerunning `/srv/cybervpn-h/scripts/send-alertmanager-test-alert.sh`.

## Backup

Configuration backup completed after Phase 18:

```text
restic snapshot: 7e6ecd48
repository: /srv/storage/backups/restic/cybervpn-h-local
```
