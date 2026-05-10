# Phase 22 Stage 2 Analytics And Quality Gates Evidence

**Timestamp:** `2026-05-10T14:09:15Z`  
**Server:** `10.10.10.34`  
**Scope:** CyberVPN `*.h.cyber-vpn.net` only.

---

## Implemented Artifacts

Local source of truth:

- `docs/plans/2026-05-10-cybervpn-stage2-analytics-quality-gates-plan.md`
- `docs/runbooks/STAGE2_ANALYTICS_AND_REPORTING.md`
- `infra/prometheus/rules/stage2_analytics_alerts.yml`
- `infra/prometheus/targets/stage2-public-endpoints.json`
- `infra/blackbox/blackbox.yml`
- `infra/grafana/dashboards/stage2-payment-reconciliation-dashboard.json`
- `infra/grafana/dashboards/stage2-refund-renewal-dashboard.json`
- `infra/grafana/dashboards/stage2-subscription-expiry-dashboard.json`
- `infra/grafana/dashboards/stage2-support-sla-dashboard.json`
- `infra/grafana/dashboards/stage2-status-page-dashboard.json`
- `infra/grafana/dashboards/stage2-product-analytics-dashboard.json`
- `infra/grafana/dashboards/stage2-release-quality-dashboard.json`
- `scripts/validate-stage2-analytics-artifacts.py`
- `scripts/release/generate-release-comparison-report.sh`
- `scripts/status/export-status-page-data.sh`
- `scripts/sentry/upload-frontend-sourcemaps.sh`
- `scripts/restore/run-scheduled-restore-drill.sh`

Server installed paths:

- `/srv/cybervpn-h/configs/grafana/dashboards/stage2-*.json`
- `/srv/cybervpn-h/configs/prometheus/rules/stage2_analytics_alerts.yml`
- `/srv/cybervpn-h/configs/prometheus/targets/stage2-public-endpoints.json`
- `/srv/cybervpn-h/runbooks/STAGE2_ANALYTICS_AND_REPORTING.md`
- `/srv/cybervpn-h/scripts/export-status-page-data.sh`
- `/srv/cybervpn-h/scripts/generate-release-comparison-report.sh`
- `/srv/cybervpn-h/scripts/upload-frontend-sourcemaps.sh`
- `/srv/cybervpn-h/scripts/run-scheduled-restore-drill.sh`
- `/etc/systemd/system/cybervpn-restore-drill.service`
- `/etc/systemd/system/cybervpn-restore-drill.timer`

Server evidence pack:

```text
/srv/storage/evidence/releases/phase22-stage2-analytics-20260510T140915Z
```

---

## Validation

Local Stage 2 artifact validator:

```text
PASS: Stage 2 analytics dashboards, rules, targets, runbooks, and CI gates are wired.
```

Local Prometheus rule validation:

```text
Checking infra/prometheus/rules/stage2_analytics_alerts.yml
  SUCCESS: 42 rules found
```

Server Prometheus rule validation:

```text
Checking /etc/prometheus/rules/stage2_analytics_alerts.yml
  SUCCESS: 42 rules found
```

Server Prometheus config validation:

```text
SUCCESS: /etc/prometheus/prometheus.yml is valid prometheus config file syntax
```

Prometheus rule groups after reload:

```text
cybervpn_stage2_analytics_alerts
cybervpn_stage2_analytics_recording_rules
```

Stage 2 synthetic targets after scrape:

```text
up https://grafana.h.cyber-vpn.net/.well-known/cybervpn-edge-health
up https://sentry.h.cyber-vpn.net/_health/
up https://prometheus.h.cyber-vpn.net/.well-known/cybervpn-edge-health
up https://alerts.h.cyber-vpn.net/.well-known/cybervpn-edge-health
up https://uptime.h.cyber-vpn.net/.well-known/cybervpn-edge-health
up https://gitlab.h.cyber-vpn.net/users/sign_in
up https://registry.h.cyber-vpn.net/.well-known/cybervpn-edge-health
```

Grafana provisioned dashboards:

```text
stage2-payment-reconciliation  Stage 2 Payment Reconciliation
stage2-product-analytics       Stage 2 Product Analytics
stage2-refund-renewal          Stage 2 Refund And Renewal
stage2-release-quality         Stage 2 Release Quality Gates
stage2-status-page             Stage 2 Status Page Data Source
stage2-subscription-expiry     Stage 2 Subscription Expiry
stage2-support-sla             Stage 2 Support SLA
```

Status page data source sample:

```json
{
  "public_endpoint_success_ratio_5m": "1",
  "tls_cert_min_days": "89.05824358796356",
  "synthetic_failures_15m": "0",
  "synthetic_slow_probes_15m": "0"
}
```

Scheduled restore drill timer:

```text
Active: active (waiting)
Trigger: Mon 2026-06-01 00:18:32 UTC
```

Security and CI validation:

```text
PASS: static syntax checks for new shell/Python scripts
PASS: GitLab CI contract is ready for initial GitLab import
PASS: gitleaks redacted scan, no leaks found
PASS: npm audit high threshold
PASS: pip-audit for backend, telegram-bot, and task-worker locks
PASS: Stage 2 artifact validator
```

---

## Notes

- Stage 2 dashboards are intentionally provision-safe before every future metric exists. Missing future metrics render as zero through `or vector(0)`.
- Public synthetic targets are CyberVPN-only; non-project domains are not included.
- Sentry source map upload is available as an explicit CI opt-in via `SENTRY_UPLOAD_SOURCEMAPS=true`.
- Source maps are not stored as GitLab job artifacts.
