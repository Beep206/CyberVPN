# Phase 23 Stage 3 Partner / Reseller Evidence

**Timestamp:** `2026-05-10T14:35:00Z`  
**Server:** `10.10.10.34`  
**Scope:** CyberVPN partner/reseller preparation only.

---

## Implemented Artifacts

Local source of truth:

- `docs/plans/2026-05-10-cybervpn-stage3-partner-reseller-platform-plan.md`
- `docs/runbooks/PARTNER_RESELLER_STAGE3_RUNBOOK.md`
- `infra/partner-lab/compose.yml`
- `infra/partner-lab/README.md`
- `infra/prometheus/rules/stage3_partner_reseller_alerts.yml`
- `infra/prometheus/targets/stage3-storefront-endpoints.json`
- `infra/grafana/dashboards/stage3-partner-staging-readiness-dashboard.json`
- `infra/grafana/dashboards/stage3-partner-attribution-storefront-dashboard.json`
- `infra/grafana/dashboards/stage3-partner-settlement-payout-dashboard.json`
- `infra/grafana/dashboards/stage3-partner-support-audit-risk-dashboard.json`
- `scripts/grafana/generate-stage3-partner-dashboards.py`
- `scripts/partner/run-webhook-test-receiver.py`
- `scripts/partner/redact-stage3-import.py`
- `scripts/partner/generate-stage3-sandbox-reports.sh`
- `scripts/partner/check-storefront-synthetic-targets.sh`
- `scripts/validate-stage3-partner-artifacts.py`

Server installed paths:

- `/srv/cybervpn-h/compose/partner-lab`
- `/srv/cybervpn-h/configs/grafana/dashboards/stage3-*.json`
- `/srv/cybervpn-h/configs/prometheus/rules/stage3_partner_reseller_alerts.yml`
- `/srv/cybervpn-h/configs/prometheus/rules/partner_platform_alerts.yml`
- `/srv/cybervpn-h/configs/prometheus/targets/stage3-storefront-endpoints.json`
- `/srv/cybervpn-h/runbooks/PARTNER_RESELLER_STAGE3_RUNBOOK.md`
- `/srv/cybervpn-h/scripts/run-webhook-test-receiver.py`
- `/srv/cybervpn-h/scripts/redact-stage3-import.py`
- `/srv/cybervpn-h/scripts/generate-stage3-sandbox-reports.sh`
- `/srv/cybervpn-h/scripts/check-storefront-synthetic-targets.sh`
- `/srv/storage/evidence/settlements`

---

## Validation

Local artifact validation:

```text
PASS: Stage 3 partner/reseller artifacts are wired.
```

Local Prometheus validation:

```text
Checking infra/prometheus/rules/stage3_partner_reseller_alerts.yml
  SUCCESS: 29 rules found
```

Local supporting checks:

```text
PASS-compose-config
PASS-redaction
PASS-sandbox-pack
PASS-webhook-receiver
PASS: GitLab CI contract is ready for initial GitLab import
```

Server Prometheus validation:

```text
Checking /etc/prometheus/rules/stage3_partner_reseller_alerts.yml
  SUCCESS: 29 rules found

Checking /etc/prometheus/rules/partner_platform_alerts.yml
  SUCCESS: 43 rules found

SUCCESS: /etc/prometheus/prometheus.yml is valid prometheus config file syntax
```

Prometheus rule groups after reload:

```text
partner_platform_alerts
partner_platform_recording_rules
cybervpn_stage3_partner_reseller_alerts
cybervpn_stage3_partner_reseller_recording_rules
```

Grafana provisioned dashboards:

```text
stage3-partner-attribution-storefront  Stage 3 Partner Attribution And Storefront
stage3-partner-settlement-payout       Stage 3 Partner Settlement And Payout
stage3-partner-staging-readiness       Stage 3 Partner Staging Readiness
stage3-partner-support-audit-risk      Stage 3 Partner Support Audit Risk
```

Server partner lab compose:

```text
PASS-server-compose-config
```

Server sandbox evidence pack:

```text
/srv/storage/evidence/settlements/phase23-sandbox-20260510T143000Z
```

Server implementation evidence pack:

```text
/srv/storage/evidence/settlements/phase23-implementation-20260510T143500Z
```

Server redaction test:

```text
records=1
PASS-server-redaction
```

Server webhook receiver test:

```text
status=accepted
PASS-server-webhook-receiver
```

Final security validation:

```text
PASS-static
gitleaks_rc=0
gitleaks_findings=0
npm_audit_rc=0
python_audit_rc=0
dangerous_pattern_scan=clean
```

Storefront synthetic readiness:

```text
blocked dns_missing https://partner.h.cyber-vpn.net/.well-known/cybervpn-edge-health
blocked dns_missing https://storefront.h.cyber-vpn.net/.well-known/cybervpn-edge-health
blocked dns_missing https://reseller.h.cyber-vpn.net/.well-known/cybervpn-edge-health
```

---

## DNS Blocker

These Cloudflare records are required before live Stage 3 storefront scraping or public partner staging:

```text
partner.h.cyber-vpn.net
storefront.h.cyber-vpn.net
reseller.h.cyber-vpn.net
```

No live Prometheus scrape job was enabled for these targets because DNS currently does not resolve.

---

## Safety Notes

- Partner lab is off by default through Docker Compose `manual` profile.
- Webhook receiver binds to `127.0.0.1:9088` in compose and is not published through Caddy.
- Settlement evidence tree exists, but real payouts and real settlement close remain blocked.
- Redaction tool was tested with synthetic data and removed direct identifiers/sensitive fields.
