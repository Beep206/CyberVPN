# Phase 13 Hardware And Host Monitoring Evidence

Date: 2026-05-10
Host: `cybervpn-h-ops`
Server: `10.10.10.34`

## Scope

Phase 13 enabled host and hardware monitoring before GitLab, Sentry and the full observability stack are deployed.

RAM is not treated as a phase blocker, but memory visibility is monitored and recorded.

## Host Services

Active services/timers:

```text
smartmontools.service
rasdaemon.service
sysstat.service
cybervpn-node-textfile-metrics.timer
cybervpn-host-health-snapshot.timer
```

`sysstat` collection was enabled in:

```text
/etc/default/sysstat
```

## Exporters

Compose file:

```text
/srv/cybervpn-h/compose/observability/phase13-exporters.compose.yml
```

Docker network:

```text
cybervpn-prometheus
```

Containers:

```text
cybervpn-node-exporter
cybervpn-cadvisor
```

Pinned images:

```text
quay.io/prometheus/node-exporter@sha256:0f422f62c15f154af8d8572b23d623aebfb10cec73a5c654d18f911f3f9df241
gcr.io/cadvisor/cadvisor@sha256:3de2bd5203120b866d74a9b283b2ffb8ec382fbf9dc321814700c6ea6f44ec57
```

Host port bindings:

```text
/cybervpn-node-exporter {"9100/tcp":null}
/cybervpn-cadvisor {"8080/tcp":null}
```

Host listener check for `9100/8080`:

```text
no listeners
```

cAdvisor security posture:

```text
privileged=false
security=["no-new-privileges:true"]
ports={"8080/tcp":null}
```

cAdvisor keeps the standard read-only `/var/run:/var/run:ro` mount because the narrower Docker socket-only mount removed per-container metrics. The service is not published on the host and is only reachable from `cybervpn-prometheus`.

## Metrics Verified

Node exporter was reachable from the Docker monitoring network:

```text
http://node-exporter:9100/metrics
```

Verified metric examples:

```text
cybervpn_h_smart_device_healthy{device="/dev/sda",type="sat"} 1
cybervpn_h_smart_device_healthy{device="/dev/nvme0",type="nvme"} 1
cybervpn_h_nvme_percentage_used{device="/dev/nvme0",type="nvme"} 0
cybervpn_h_ras_memory_errors_present 0
node_memory_MemAvailable_bytes
node_filesystem_avail_bytes
```

cAdvisor was reachable from the Docker monitoring network:

```text
http://cadvisor:8080/metrics
```

Verified metric examples:

```text
container_cpu_usage_seconds_total
container_memory_working_set_bytes
container_last_seen
```

## Hardware Health Snapshot

SMART HDD health:

```text
/dev/sda: PASSED
```

SMART NVMe health:

```text
/dev/nvme0: PASSED
```

NVMe quick values:

```text
temperature: 36 C
available_spare: 100%
percentage_used: 0%
media_errors: 0
num_err_log_entries: 0
```

RAS summary:

```text
No Memory errors.
No PCIe AER errors.
No Extlog errors.
No MCE errors.
```

## Files Installed

Metrics script:

```text
/srv/cybervpn-h/scripts/write-node-exporter-textfile.sh
```

Daily evidence snapshot:

```text
/srv/cybervpn-h/scripts/host-health-snapshot.sh
```

Runbook:

```text
/srv/cybervpn-h/runbooks/hardware-and-host-monitoring.md
```

Prometheus target template for Phase 14:

```text
/srv/cybervpn-h/configs/prometheus/phase13-scrape-targets.yml
```

## Evidence Paths On Server

Final Phase 13 evidence:

```text
/srv/cybervpn-h/evidence/monitoring/phase13-final-after-cadvisor-mount-20260510T052310Z/
```

Host health snapshot:

```text
/srv/cybervpn-h/evidence/monitoring/host-health-20260510T051959Z/
```

Other setup evidence:

```text
/srv/cybervpn-h/evidence/monitoring/phase13-exporters-compose-config.yml
/srv/cybervpn-h/evidence/monitoring/phase13-exporters-compose-config-pinned.yml
/srv/cybervpn-h/evidence/monitoring/phase13-exporters-compose-config-final.yml
/srv/cybervpn-h/evidence/monitoring/phase13-image-digests.txt
```

## Backup

After Phase 13 verification, the host config backup was run manually so the new monitoring compose, systemd units, scripts and runbook are already in restic:

```text
snapshot f4718d89
status=ok
```

## Acceptance Criteria

- `smartd` active: yes.
- `rasdaemon` active: yes.
- Node exporter reachable from Prometheus network only: yes.
- cAdvisor reachable from Prometheus network only: yes.

## Notes For Phase 14

Prometheus should join the existing `cybervpn-prometheus` Docker network and scrape:

```text
node-exporter:9100
cadvisor:8080
```

Do not publish `9100` or `8080` on the host.
