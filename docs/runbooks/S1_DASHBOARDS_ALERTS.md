# S1 Dashboards And Alerts Runbook

Host: `cybervpn-h-ops`

Server: `10.10.10.34`

## Paths

```text
/srv/cybervpn-h/compose/observability
/srv/cybervpn-h/configs/grafana/dashboards
/srv/cybervpn-h/configs/prometheus/prometheus.yml
/srv/cybervpn-h/configs/prometheus/rules
/srv/cybervpn-h/configs/alertmanager/alertmanager.yml.template
/srv/cybervpn-h/configs/alertmanager/render-alertmanager.sh
/srv/cybervpn-h/secrets/alertmanager.env
/srv/cybervpn-h/scripts/send-alertmanager-test-alert.sh
/srv/cybervpn-h/scripts/write-sentry-ingestion-smoke.sh
```

## Enable Telegram Delivery

Edit the root-only secret file on the server:

```bash
sudo nano /srv/cybervpn-h/secrets/alertmanager.env
```

Set:

```text
ALERTMANAGER_REQUIRE_LIVE_RECEIVERS=true
ALERTMANAGER_TELEGRAM_BOT_TOKEN=<telegram-bot-token>
ALERTMANAGER_TELEGRAM_CHAT_ID=<telegram-chat-id>
```

Do not commit these values to Git.

Apply the rendered Alertmanager config:

```bash
cd /srv/cybervpn-h/compose/observability
sudo docker compose up -d --force-recreate --no-deps --wait alertmanager
```

Send the Phase 18 smoke alert:

```bash
sudo /srv/cybervpn-h/scripts/send-alertmanager-test-alert.sh
```

Verify Alertmanager:

```bash
curl -fsS http://127.0.0.1:9093/-/ready
curl -fsS http://127.0.0.1:9093/api/v2/alerts | jq .
```

Save evidence:

```bash
EV=/srv/cybervpn-h/evidence/observability/phase18-s1-dashboards-alerts-$(date -u +%Y%m%dT%H%M%SZ)
sudo mkdir -p "$EV"
sudo curl -fsS http://127.0.0.1:9093/api/v2/status | sudo tee "$EV/alertmanager-status.json" >/dev/null
sudo curl -fsS http://127.0.0.1:9090/api/v1/targets | sudo tee "$EV/prometheus-targets.json" >/dev/null
```

## Enable Email Fallback

For Resend, use the verified sender domain and STARTTLS. On `cybervpn-h-ops`, `smtp.resend.com:2587` was verified successfully; `587` timed out from this host.

```text
ALERTMANAGER_BACKUP_EMAIL=<recipient>
ALERTMANAGER_SMTP_FROM=alerts@email.cyber-vpn.net
ALERTMANAGER_SMTP_SMARTHOST=smtp.resend.com:2587
ALERTMANAGER_SMTP_AUTH_USERNAME=resend
ALERTMANAGER_SMTP_PASSWORD=<resend-api-key>
ALERTMANAGER_SMTP_REQUIRE_TLS=true
```

Then recreate Alertmanager with the same command used for Telegram.

## Validate Prometheus And Rules

```bash
cd /srv/cybervpn-h/compose/observability
sudo docker run --rm \
  -v /srv/cybervpn-h/configs/prometheus:/etc/prometheus:ro \
  prom/prometheus:v2.55.1 \
  promtool check config /etc/prometheus/prometheus.yml
sudo docker compose up -d --force-recreate --no-deps --wait prometheus
curl -fsS http://127.0.0.1:9090/-/ready
```

## Reload Grafana Dashboards

Grafana provisions dashboards from:

```text
/srv/cybervpn-h/configs/grafana/dashboards
```

After replacing dashboard JSON files, restart Grafana:

```bash
cd /srv/cybervpn-h/compose/observability
sudo docker compose up -d --force-recreate --no-deps --wait grafana
```

## Sentry Ingestion Smoke

The timer publishes `cybervpn_h_sentry_ingestion_smoke_success` through node-exporter textfile collector:

```bash
systemctl list-timers cybervpn-sentry-ingestion-smoke.timer
sudo systemctl start cybervpn-sentry-ingestion-smoke.service
curl -fsS 'http://127.0.0.1:9090/api/v1/query?query=cybervpn_h_sentry_ingestion_smoke_success' | jq .
```

The Sentry DSN is stored in:

```text
/srv/cybervpn-h/secrets/sentry-smoke.env
```

Keep the file mode `0600`.
