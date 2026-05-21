# STAGE1-RENT-11B - Node-Only Policy And Direct Home-to-Prod-App Probe Evidence

Date: `2026-05-20T17:00:51Z`
Scope: remove Stage 1 public endpoint probe workload from the production VPN node and restore the direct `home -> prod-app-1` observability requirement.
Result: `NODE_ONLY_RESTORED_DIRECT_PROD_APP_HTTP_TLS_BLOCKED`

## Decision

The production VPN node must run only the VPN node runtime and the minimum host services needed to operate that node.

Allowed on `prod-vpn-node-1` for Stage 1:

- SSH/admin access;
- Remnawave node runtime;
- required VLESS/XHTTP transport listeners;
- Remnawave node control/listener ports required by the node runtime;
- standard host services such as DNS resolver/time sync/firewall.

Not allowed on `prod-vpn-node-1` for Stage 1:

- Prometheus exporters unrelated to the VPN node;
- public web/API/admin probes;
- payment, backend, worker, Telegram Bot, GitLab, Grafana, Loki, Sentry, Alertmanager or support workloads;
- temporary observability relay services for `prod-app-1`.

## Live Node Cleanup

The temporary `STAGE1-RENT-11A` external probe relay was removed from `prod-vpn-node-1`.

Removed from the node:

- `cybervpn-stage1-external-probe-exporter.service`;
- `/usr/local/bin/cybervpn-stage1-external-probe-exporter`;
- local user `stage1probe`;
- UFW allow rule for `19115/tcp`;
- source-controlled exporter/service files.

Live verification after cleanup:

| Check | Result |
|---|---|
| `systemctl is-active cybervpn-stage1-external-probe-exporter` | `inactive` |
| `ss -lntup` | no listener on `19115` |
| `docker ps` | only `cybervpn-remnawave-node` application container |
| VPN transport listeners | `443` and `8443` still present |
| Node runtime | `cybervpn-remnawave-node` still running |

## Direct Home-to-Prod-App Findings

The direct path from the home observability server to `prod-app-1` was tested without using the VPN node.

Observed facts:

| Source | Target | Result |
|---|---|---|
| home server | DNS for `cyber-vpn.net`, `api.cyber-vpn.net`, `admin.cyber-vpn.net` | resolves to `45.87.41.146` |
| home server | ICMP to `45.87.41.146` | succeeds, including large `1400` byte payload test |
| home server | TCP connect to `45.87.41.146:22/80/443` | succeeds |
| home server | HTTP request to `http://cyber-vpn.net/.well-known/cybervpn-edge-health` | TCP connects, then times out with `0` bytes received |
| home server | HTTPS request to `https://cyber-vpn.net/.well-known/cybervpn-edge-health` | TCP connects, TLS/app-connect times out |
| home server | direct `--connect-to cyber-vpn.net:443:45.87.41.146:443` | same TLS timeout |
| home server | TCP payload test to a temporary listener on `prod-app-1` | connection opens, payload is not received |
| `prod-app-1` tcpdump | home HTTP GET payload | not observed on `prod-app-1` |
| home tcpdump | same HTTP GET payload | observed leaving home server |
| home NIC offload test | temporarily disabled `tx/rx/gro` | no improvement, then restored |

Conclusion:

```text
Direct TCP handshake and ICMP work between home and prod-app-1, but TCP payload after handshake is lost before it reaches prod-app-1. This is outside the CyberVPN application containers and outside the VPN node.
```

## Operational Status

`prod-vpn-node-1` is clean again and must stay node-only.

The direct `home -> prod-app-1` public HTTP/TLS probe path is not closed yet. It remains an infrastructure/network-path blocker until one of these is completed:

1. the provider/ISP route between home public IP and `45.87.41.146` is fixed;
2. a dedicated non-node ops path is approved and documented;
3. the public web monitoring authority is moved to the customer-facing edge path, with explicit owner approval that it is not an origin-direct probe.

The VPN node must not be reused as a public app/API/admin observability relay.

## Live Home Prometheus State After Cleanup

Home Prometheus was reloaded without the VPN-node relay scrape target.

Current live state:

| Query / check | Result |
|---|---|
| Active Prometheus targets | no active `stage1-prod-app-external-probe-relay` target |
| `probe_success{job=~"stage1-public-web|blackbox-stage1-public-web"}` | 8 public endpoint probes present, all `0` from home |
| `probe_success{job="stage1-vpn-node-tcp"}` | `de-1.cyber-vpn.org:443=1`, `de-1.cyber-vpn.org:8443=1` |
| `Stage1External*` alerts | removed from active rules |
| `Stage1PublicEndpointProbeFailed` | firing for all 8 direct public endpoint probes until direct path is closed |

This is intentionally noisy: the dashboard must show the direct home-to-prod-app problem instead of hiding it behind the VPN node.

## Source-Controlled Changes

| File | Change |
|---|---|
| `infra/probes/stage1_external_probe_exporter.py` | removed |
| `infra/systemd/cybervpn-stage1-external-probe-exporter.service` | removed |
| `infra/prometheus/prometheus.yml` | removed `stage1-prod-app-external-probe-relay` job |
| `infra/prometheus/rules/stage1_alerts.yml` | removed relay-specific alerts |
| `infra/grafana/dashboards/stage1-controlled-public-beta-dashboard.json` | replaced relay panels with direct `stage1-public-web` blackbox panels |

## Follow-Up

Recommended next action:

```text
STAGE1-RENT-11C: Direct Home-to-Prod-App Network Path Closure
```

Close this by either fixing the upstream route or approving a non-node direct ops path. Do not place auxiliary monitoring workloads on VPN nodes.
