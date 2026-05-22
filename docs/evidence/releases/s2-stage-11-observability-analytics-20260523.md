# S2-STAGE-11 Observability And Analytics Evidence

**Date:** 2026-05-23
**Stage:** `S2-STAGE-11`
**Result:** `PASS_WITH_CONTROLLED_GAP`
**Owner:** `@Sasha_Beep`

---

## 1. Scope

This evidence closes the Stage 2 observability and analytics preparation gate for Public Release 1.0.

Covered surfaces:

- payment reconciliation dashboard;
- refund/renewal dashboard;
- subscription expiry dashboard;
- support SLA dashboard;
- status-page data source dashboard;
- product analytics dashboard;
- release quality gates dashboard;
- Prometheus recording rules and alerts;
- public synthetic probes for `.net` customer paths;
- subscription route synthetic probe;
- `.org` VPN node TCP probes;
- home ops public probes;
- Sentry/source map operating contract;
- sensitive logging boundaries.

---

## 2. Source Artifacts

Updated/created source artifacts:

- `docs/cybervpn_stage2_launch_docs/10_STAGE2_OBSERVABILITY_ANALYTICS.md`
- `docs/runbooks/STAGE2_ANALYTICS_AND_REPORTING.md`
- `docs/plans/2026-05-10-cybervpn-stage2-analytics-quality-gates-plan.md`
- `infra/prometheus/rules/stage2_analytics_alerts.yml`
- `infra/prometheus/prometheus.yml`
- `infra/prometheus/targets/stage2-public-endpoints.json`
- `infra/prometheus/targets/stage2-subscription-route.json`
- `infra/prometheus/targets/stage2-vpn-node-tcp.json`
- `infra/blackbox/blackbox.yml`
- `infra/grafana/dashboards/stage2-status-page-dashboard.json`
- `scripts/grafana/generate-stage2-dashboards.py`
- `scripts/status/export-status-page-data.sh`
- `scripts/validate-stage2-analytics-artifacts.py`
- `backend/tests/contract/test_stage2_observability_assets_contract.py`

---

## 3. Local Validation

Stage 2 artifact validator:

```text
PASS: Stage 2 analytics dashboards, rules, targets, runbooks, and CI gates are wired.
```

Dashboard and target JSON validation:

```text
jq empty infra/grafana/dashboards/stage2-*.json infra/prometheus/targets/stage2-*.json
PASS
```

Prometheus rule validation:

```text
Checking /rules/stage2_analytics_alerts.yml
  SUCCESS: 50 rules found
```

Prometheus config validation:

```text
SUCCESS: /etc/prometheus/prometheus.yml is valid prometheus config file syntax
SUCCESS: 17 rule files found
```

Blackbox config validation:

```text
Config file is ok exiting...
```

Contract tests:

```text
cd backend && uv run pytest --no-cov tests/contract/test_stage2_observability_assets_contract.py
4 passed in 0.21s
```

---

## 4. Public Route Smoke

Workspace public HTTP smoke:

```text
https://cyber-vpn.net/ -> 200
https://www.cyber-vpn.net/ -> 200
https://cyber-vpn.net/en-EN -> 200
https://cyber-vpn.net/ru-RU -> 200
https://cyber-vpn.net/ru-RU/miniapp/home -> 200
https://cyber-vpn.net/ru-RU/miniapp/plans -> 200
https://api.cyber-vpn.net/health -> 200
https://api.cyber-vpn.net/healthz -> 200
https://admin.cyber-vpn.net/ru-RU/login -> 200
https://status.cyber-vpn.net/ -> 200
https://cyber-vpn.net/.well-known/cybervpn-edge-health -> 200
https://api.cyber-vpn.net/.well-known/cybervpn-edge-health -> 200
https://admin.cyber-vpn.net/.well-known/cybervpn-edge-health -> 200
https://status.cyber-vpn.net/.well-known/cybervpn-edge-health -> 200
```

Workspace subscription route smoke:

```text
https://cyber-vpn.org/api/sub/stage2-observability-synthetic-probe -> 404
https://cyber-vpn.net/api/sub/stage2-observability-synthetic-probe -> 404
```

The `404` is expected for a synthetic unknown subscription token. Timeout or `5xx` would be a failure.

Workspace VPN node TCP smoke:

```text
de-1.cyber-vpn.org:443 -> tcp_ok
de-1.cyber-vpn.org:8443 -> tcp_ok
```

DNS summary:

```text
cyber-vpn.net -> Cloudflare A records
api.cyber-vpn.net -> Cloudflare A records
admin.cyber-vpn.net -> Cloudflare A records
status.cyber-vpn.net -> Cloudflare A records
cyber-vpn.org -> 45.87.41.146
de-1.cyber-vpn.org -> 77.90.13.29
```

---

## 5. Home Observability Deployment

Home server: `10.10.10.34`

Applied server-side artifacts:

- Stage 2 Prometheus rules;
- Stage 2 public endpoint targets;
- Stage 2 subscription route target;
- Stage 2 VPN node TCP target;
- Blackbox module `http_2xx_3xx_4xx`;
- Stage 2 Grafana dashboards;
- Stage 2 runbook;
- status-page exporter script.

Environment fix applied:

- added `/srv/cybervpn-h/configs/prometheus/targets:/etc/prometheus/targets:ro` to the home observability compose;
- backup created as `/srv/cybervpn-h/compose/observability/compose.yml.s2-stage11-targets-20260523.bak`;
- Prometheus was recreated through `docker compose -f /srv/cybervpn-h/compose/observability/compose.yml up -d prometheus`;
- Blackbox exporter, Prometheus and Grafana were restarted/reloaded as needed.

Remote validation:

```text
docker exec cybervpn-prometheus promtool check config /etc/prometheus/prometheus.yml
SUCCESS: /etc/prometheus/prometheus.yml is valid prometheus config file syntax
SUCCESS: 7 rule files found
SUCCESS: stage2_analytics_alerts.yml, 50 rules found
```

Remote blackbox validation:

```text
blackbox_exporter --config.file=/etc/blackbox_exporter/config.yml --config.check
Config file is ok exiting...
```

---

## 6. Home Prometheus Live State

Active Stage 2 targets after scrape:

```text
stage2-public-endpoints / customer-edge / all .net website, API, admin, status and Mini App targets -> up
stage2-public-endpoints / home-ops-edge / GitLab, registry, Grafana, Sentry, Prometheus, Alertmanager, Uptime Kuma -> up
stage2-subscription-route / subscription-route / https://cyber-vpn.net/api/sub/stage2-observability-synthetic-probe -> up
stage2-vpn-node-tcp / vpn-node / de-1.cyber-vpn.org:443 -> up
stage2-vpn-node-tcp / vpn-node / de-1.cyber-vpn.org:8443 -> up
```

Recording rule values:

```text
stage2:customer_edge_success_ratio:5m -> 1
stage2:subscription_route_success_ratio:5m -> 1
stage2:vpn_node_tcp_success_ratio:5m -> 1
stage2:home_ops_edge_success_ratio:5m -> 1
stage2:status_public_endpoint_success_ratio:5m -> 1
stage2:tls_cert_min_days -> 70.59957460648208
```

Active S2 alerts:

```text
none
```

Status-page data sample:

```json
{
  "project": "cybervpn",
  "public_scope": "cyber-vpn.net customer edge, cyber-vpn.org subscription/VPN delivery, and *.h.cyber-vpn.net home ops",
  "status": {
    "public_endpoint_success_ratio_5m": "1",
    "customer_edge_success_ratio_5m": "1",
    "subscription_route_success_ratio_5m": "1",
    "vpn_node_tcp_success_ratio_5m": "1",
    "home_ops_edge_success_ratio_5m": "1",
    "tls_cert_min_days": "70.59957460648208",
    "synthetic_failures_15m": "0",
    "synthetic_slow_probes_15m": "0"
  }
}
```

---

## 7. Controlled Gap

Direct home-server probing to `https://cyber-vpn.org/api/sub/...` currently times out against `45.87.41.146`, while the same route returns expected `404` from the workspace network.

Decision for S2-STAGE-11:

- continuous home Prometheus monitoring uses the Cloudflare-proxied subscription route at `https://cyber-vpn.net/api/sub/...`;
- `.org` remains the intended product delivery zone for subscription links and VPN node records;
- `.org` subscription delivery must be proven with a real user subscription URL from an external network before unrestricted S2 opening;
- do not reintroduce `.org` as a general website mirror.

This gap does not block Stage 2 observability preparation, but it must remain visible in the S2 release rehearsal.

---

## 8. Security And Privacy Notes

Sensitive payload boundaries are documented in the Stage 2 observability doc and runbook.

Do not send these into Loki, Grafana, Sentry, analytics or release evidence:

- payment provider secrets;
- Telegram bot token or raw Telegram `initData`;
- JWTs and refresh tokens;
- subscription URL tokens;
- raw VPN config links;
- full payment webhook bodies;
- private support notes;
- full auth/payment/subscription request or response bodies.

Product analytics must be asynchronous and must not block auth, checkout, provisioning, Mini App rendering or VPN config display.

Security review commands:

```text
npm audit --audit-level=high --omit=dev
Result: no high/critical npm findings; existing moderate findings remain in dependency tree.

diff-only secret-value scan
Result: no new secret-looking added lines.

static dangerous-pattern scan for changed scripts/tests
Result: no eval/exec/shell=True/dangerouslySetInnerHTML matches.
```

---

## 9. Exit Assessment

`S2-STAGE-11` is accepted as complete for Stage 2 preparation.

Remaining work moves to later S2 gates:

- S2-STAGE-12: restore/rollback/DR proof;
- S2-STAGE-13: security, abuse and privacy gate;
- S2-STAGE-15: full release rehearsal, including real `.org` subscription URL config delivery proof.
