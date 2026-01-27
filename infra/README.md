# Infrastructure

Local Docker Compose stack that mirrors the launch plan in `plan/vpn-business-deployment-guide.md`.

## Quick start
1. Review and edit `infra/.env` (generated for local use) or copy `infra/.env.example`.
2. Start the core services:

```bash
cd infra
docker compose up -d
```

Optional services are enabled via profiles:

```bash
docker compose --profile proxy --profile subscription --profile bot --profile monitoring up -d
```

## Local endpoints
- Panel: http://localhost:3000 (or http://panel.localhost with the proxy profile)
- Metrics: http://localhost:3001/metrics
- Postgres: localhost:6767
- Subscription page: http://localhost:3010 (subscription profile)
- Prometheus: http://localhost:9090 (monitoring profile)
- Grafana: http://localhost:3002 (monitoring profile)

## Notes
- If you change `METRICS_PASS` in `infra/.env`, update `infra/prometheus/prometheus.yml`.
- `infra/postgres/init/001-create-remnashop.sql` auto-creates the `remnashop` database.
- Remnashop and Subscription Page require a Remnawave API token from the panel.
