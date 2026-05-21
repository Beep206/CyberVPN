# STAGE1-RENT-11A - External Probe Relay Closure Evidence

> Superseded by `docs/evidence/releases/stage1-rented-prod-11b-node-only-and-direct-home-prod-app-20260520T170051Z.md`.
> The relay was removed because `prod-vpn-node-1` must stay node-only. Do not use this evidence as the current Stage 1 observability authority.

Date: `2026-05-20T16:46:32Z`
Scope: close the Stage 1 home-to-prod-app public endpoint observability blind spot
Result: `PASS`

## Decision

`S1-RENT11-001` is closed for Stage 1 operations.

The home observability server still cannot reliably complete direct HTTP/TLS requests to `prod-app-1` (`45.87.41.146`), but Stage 1 no longer depends on that path for public app/API/admin visibility. A dedicated external probe relay now runs from the rented production VPN node and is scraped by home Prometheus.

This gives home Grafana/Prometheus/Alertmanager an external rented-network view of the customer-facing routes:

```text
prod-vpn-node-1 / de-1.cyber-vpn.org
-> probes cyber-vpn.net / api / admin / Mini App
-> exposes Prometheus metrics on a restricted port
-> home Prometheus scrapes de-1.cyber-vpn.org:19115
-> Stage 1 alerts fire from relay metrics
```

## Why A Relay Was Needed

Observed failure:

| Source | Target | Result |
|---|---|---|
| home server | `45.87.41.146:443` TCP | connect succeeds |
| home server | `https://cyber-vpn.net/` | TLS/HTTP timeout |
| home Prometheus blackbox | S1 public web/API/admin targets | `probe_success=0` |
| external operator environment | same S1 public targets | `200` |
| `prod-app-1` local public probes | same S1 public targets | `200` |
| `prod-vpn-node-1` external public probes | same S1 public targets | `200` |

Conclusion:

```text
The site is not down for users. The blind spot is the home-server-to-prod-app public HTTP/TLS path.
```

## Implementation

### Production VPN Node

New runtime:

| Item | Value |
|---|---|
| Host | `de-1.cyber-vpn.org` |
| Service | `cybervpn-stage1-external-probe-exporter.service` |
| User | `stage1probe` |
| Script | `/usr/local/bin/cybervpn-stage1-external-probe-exporter` |
| Metrics endpoint | `http://de-1.cyber-vpn.org:19115/metrics` |
| Health endpoint | `http://de-1.cyber-vpn.org:19115/health` |
| Firewall | `19115/tcp` allowed only from home public IP `95.82.233.131` |
| Resource use | about `22 MiB RSS`, `0.0% CPU` during evidence check |

The exporter is dependency-free Python and does not log request headers, tokens, cookies, config URLs or customer data.

### Home Prometheus

New Prometheus job:

```text
stage1-prod-app-external-probe-relay
```

New alert coverage:

| Alert | Purpose |
|---|---|
| `Stage1ExternalProbeRelayUnavailable` | relay scrape is down |
| `Stage1ExternalPublicEndpointProbeFailed` | any required public endpoint fails from the external relay |
| `Stage1ExternalPublicProbeStale` | relay result is stale |

### Grafana

The Stage 1 dashboard now has an `External Public Probes` row with:

| Panel | Purpose |
|---|---|
| `External Relay Up` | relay scrape health |
| `Public Probes Overall` | overall endpoint health |
| `VPN Node TCP 443/8443` | VPN node port probe |
| `Probe Freshness Seconds` | stale-result visibility |
| `External Endpoint Success` | per-route success |
| `External Endpoint Latency` | per-route latency |

## Source-Controlled Files

| File | Change |
|---|---|
| `infra/probes/stage1_external_probe_exporter.py` | added external public endpoint probe exporter |
| `infra/systemd/cybervpn-stage1-external-probe-exporter.service` | added hardened systemd unit |
| `infra/prometheus/prometheus.yml` | added `stage1-prod-app-external-probe-relay` scrape job |
| `infra/prometheus/rules/stage1_alerts.yml` | added relay availability, endpoint failure and stale probe alerts |
| `infra/grafana/dashboards/stage1-controlled-public-beta-dashboard.json` | added external public probe panels |

## Live Evidence

Prometheus queries from home:

| Query | Result |
|---|---|
| `up{job="stage1-prod-app-external-probe-relay"}` | `1` |
| `cybervpn_stage1_external_public_probe_overall_success` | `1` |
| `cybervpn_stage1_external_public_probe_success` | 8 series, all `1` |
| `cybervpn_stage1_external_public_probe_http_status` | 8 series, all `200` |
| `time() - cybervpn_stage1_external_public_probe_run_unixtime` | fresh, about `23s` during evidence |
| `probe_success{job="stage1-vpn-node-tcp"}` | `443=1`, `8443=1` |
| `ALERTS{alertname=~"Stage1External.*|Stage1VpnNodeTcpProbeFailed"}` | `0` |

Endpoints covered:

| Target | Status |
|---|---|
| `site` | `200` |
| `site_en` | `200` |
| `miniapp_home` | `200` |
| `miniapp_plans` | `200` |
| `api_health` | `200` |
| `admin_login` | `200` |
| `www` | `200` |
| `status` | `200` |

Current firing alerts after RENT-11A:

| Alert | Scope |
|---|---|
| `CyberVPNSwapInUse` | home observability capacity warning |
| `CyberVPNSwapUsageAbove1GiB` | home observability capacity warning |
| `Stage2StatusEndpointDown` | Stage 2, outside S1 rented runtime |

No S1 external public endpoint or VPN-node probe alert is firing.

## Security Notes

- No provider token, bot token, JWT, VLESS URL, Remnawave token or private key is stored in evidence.
- The relay port is not broadly open; UFW allows `19115/tcp` only from `95.82.233.131`.
- The attempted SSH forced-command relay on `prod-app-1` was removed after the SSH path proved unsuitable.
- HTTP/3/QUIC was not disabled or changed.

## Validation

Commands/checks:

```text
python3 -m py_compile infra/probes/stage1_external_probe_exporter.py
python3 scripts/validate-s1-alerting.py
python3 scripts/validate-s1-observability-dashboards.py
python3 -m json.tool infra/grafana/dashboards/stage1-controlled-public-beta-dashboard.json
git diff --check
npm audit --omit=dev --audit-level=high
promtool check config /etc/prometheus/prometheus.yml
promtool check rules /etc/prometheus/rules/stage1_alerts.yml
Grafana /api/health -> database ok
Prometheus /-/healthy -> healthy
```

Result:

```text
PASS
npm audit high/critical gate passed; remaining advisories are moderate and tracked separately
```

## Remaining Notes

The direct home-origin public blackbox job may remain as diagnostic evidence of the home network issue, but it is no longer the S1 customer-runtime availability authority.

The authoritative S1 public endpoint visibility path is now:

```text
stage1-prod-app-external-probe-relay
```

## Next Step

```text
STAGE1-RENT-12: S1 production catalog/support seed and controlled beta expansion gate
```
