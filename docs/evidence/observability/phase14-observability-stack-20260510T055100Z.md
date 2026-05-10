# Phase 14 Observability Stack Evidence

Date: `2026-05-10`

Host: `cybervpn-h-ops`

Server: `10.10.10.34`

## Scope

Phase 13.1 added the first Grafana hardware/host dashboard for Phase 13 metrics.

Phase 14 deployed the observability stack:

- Grafana
- Prometheus
- Alertmanager
- Loki
- Promtail
- Blackbox Exporter
- Uptime Kuma
- Existing Phase 13 Node Exporter and cAdvisor

## Remote Files

```text
/srv/cybervpn-h/compose/observability/compose.yml
/srv/cybervpn-h/configs/prometheus/prometheus.yml
/srv/cybervpn-h/configs/prometheus/rules/host-alerts.yml
/srv/cybervpn-h/configs/alertmanager/alertmanager.yml
/srv/cybervpn-h/configs/loki/loki.yml
/srv/cybervpn-h/configs/promtail/promtail.yml
/srv/cybervpn-h/configs/blackbox/blackbox.yml
/srv/cybervpn-h/configs/grafana/provisioning/datasources/datasources.yml
/srv/cybervpn-h/configs/grafana/provisioning/dashboards/dashboard-provider.yml
/srv/cybervpn-h/configs/grafana/dashboards/cybervpn-h-hardware.json
/srv/cybervpn-h/runbooks/observability-stack.md
```

## Public Routes

All routes are handled by Caddy and protected by Caddy Basic Auth:

```text
grafana.h.cyber-vpn.net
prometheus.h.cyber-vpn.net
loki.h.cyber-vpn.net
alerts.h.cyber-vpn.net
uptime.h.cyber-vpn.net
```

Unauthenticated route checks returned `401`.

Authenticated route checks returned:

```text
grafana.h.cyber-vpn.net       302
prometheus.h.cyber-vpn.net    302
loki.h.cyber-vpn.net          200
alerts.h.cyber-vpn.net        200
uptime.h.cyber-vpn.net        302
```

`302` is expected for web applications that redirect to their UI entry point.

## Verification Summary

Remote verification evidence:

```text
/srv/cybervpn-h/evidence/observability/phase14-verify-final-20260510T055100Z
```

Local health:

```text
prometheus     200
grafana        200
loki           200
alertmanager   200
uptime_kuma    302
```

Prometheus targets:

```text
alertmanager        up
blackbox-exporter   up
blackbox-http       up
cadvisor            up
grafana             up
loki                up
node-exporter       up
prometheus          up
```

Prometheus query result counts:

```text
up{job="node-exporter"}                              1
up{job="cadvisor"}                                   1
cybervpn_h_smart_device_healthy                      2
cybervpn_h_smart_temperature_celsius{type="nvme"}    1
cybervpn_h_ras_mce_errors_present                    1
cybervpn_h_docker_json_log_bytes                     1
node_memory_MemAvailable_bytes                       1
container_cpu_usage_seconds_total{name!=""}          10
probe_success                                        5
```

Grafana provisioning:

```text
Alertmanager   alertmanager   http://alertmanager:9093
Loki           loki           http://loki:3100
Prometheus     prometheus     http://prometheus:9090
```

Provisioned dashboard:

```text
CyberVPN h Hardware & Host   cybervpn-h-hardware   dash-db
```

Loki stream checks:

```text
caddy-access   1
docker-json    1
```

Alertmanager test:

```text
CyberVPNPhase14Test   info   active
```

Telegram delivery is not enabled yet because no Telegram bot token/chat ID has been provided. Alertmanager is currently configured as local/no-op and accepts test alerts.

## Security Surface

Container service ports are bound to loopback only:

```text
127.0.0.1:3000   Grafana
127.0.0.1:3001   Uptime Kuma
127.0.0.1:9090   Prometheus
127.0.0.1:9093   Alertmanager
127.0.0.1:3100   Loki
```

Public listeners remain:

```text
80/tcp
443/tcp
22/tcp restricted to 10.10.10.0/24 by UFW
```

Secret file permissions:

```text
/srv/cybervpn-h/secrets/observability.env                    600 root:root
/srv/cybervpn-h/secrets/caddy/observability-basic-auth.env   600 root:root
/srv/cybervpn-h/secrets/caddy/cloudflare.env                 600 root:root
```

## Fix Applied During Verification

Docker data root is `/srv/docker`, not `/var/lib/docker`.

Promtail was updated to mount:

```text
/srv/docker/containers:/var/lib/docker/containers:ro
```

The node-exporter textfile script now reads Docker root from:

```text
docker info --format '{{.DockerRootDir}}'
```

This fixed both Loki `docker-json` streams and the `cybervpn_h_docker_json_log_bytes` metric.

## Backup

Configuration backup completed after Phase 14:

```text
restic snapshot: a4c07acb
repository: /srv/storage/backups/restic/cybervpn-h-local
```
