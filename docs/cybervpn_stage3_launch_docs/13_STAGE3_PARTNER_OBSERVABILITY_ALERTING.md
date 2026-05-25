# Stage 3 Partner Observability And Alerting

**Stage:** `S3-STAGE-13`
**Status:** Passed for local code/config/evidence gate
**Date:** 2026-05-25
**Product stage:** CyberVPN Partner / Reseller Platform
**Prior gate:** `S3-STAGE-12: Partner Support, Admin Ops, And Audit`

---

## 1. Назначение

S3-STAGE-13 делает partner/reseller контур видимым до controlled partner pilot.

Цель этапа: подготовить Prometheus, Grafana, Alertmanager, Loki/Sentry operating contract и backend runtime metrics так, чтобы owner/support/finance/admin видели:

- partner portal readiness;
- storefront synthetic probes;
- outbox lag, publish failures and dead letters;
- partner application and support queues;
- attribution failures;
- settlement and payout sandbox anomalies;
- payout review backlog;
- audit/risk/anti-fraud signals;
- frontend partner/admin UX errors;
- sensitive logging risks.

Этот этап не включает публичное открытие партнёрки и не включает real payouts.

---

## 2. Operating Decision

Observability остаётся на домашнем сервере как non-critical control-plane:

```text
home observability can fail without breaking customer runtime
customer runtime must not depend on Grafana/Prometheus/Loki/Sentry availability
production VPN node remains node-only
partner features remain disabled-by-default until S3-STAGE-16/17
```

S3-STAGE-13 разрешает:

- загрузить Stage 3 rules/dashboards;
- включить blackbox scrape для Stage 3 synthetic targets после DNS/edge readiness;
- собирать partner runtime metrics из backend;
- использовать Loki/Sentry для расследования, но не как source of truth для settlement.

S3-STAGE-13 не разрешает:

- реальные partner payouts;
- публичный partner storefront без disabled-state gate;
- хранение raw payment payloads, VPN subscription URLs or payout secrets в логах/evidence;
- перенос customer-critical runtime на домашний observability host.

---

## 3. Prometheus Coverage

### 3.1 Config wiring

Prometheus now loads:

```text
/etc/prometheus/rules/stage3_partner_reseller_alerts.yml
```

and scrapes:

```text
job_name=stage3-storefront-endpoints
target_file=/etc/prometheus/targets/stage3-storefront-endpoints.json
blackbox_module=http_2xx_3xx_4xx
```

The Stage 3 target file is prepared for:

```text
partner.h.cyber-vpn.net
storefront.h.cyber-vpn.net
reseller.h.cyber-vpn.net
```

The targets remain `requires_dns_before_live_scrape` until the S3 production disabled-state deploy/edge gate.

### 3.2 Recording rules

Stage 3 recording rules cover:

| Area | Recording rule |
|---|---|
| Bootstrap | `stage3:partner_bootstrap_success_ratio:5m` |
| Auth denials | `stage3:partner_auth_denials:15m` |
| Frontend UX | `stage3:partner_frontend_route_p95_seconds`, `stage3:partner_frontend_api_p95_seconds` |
| Frontend errors | `stage3:partner_frontend_error_events:15m` |
| Attribution | `stage3:partner_attribution_no_owner_ratio:5m`, `stage3:partner_touchpoint_rejects:1h` |
| Storefront | `stage3:storefront_synthetic_success_ratio:5m`, `stage3:storefront_synthetic_failures:15m` |
| Outbox | `stage3:partner_outbox_lag_p95_seconds`, `stage3:partner_outbox_publish_failures:15m`, `stage3:partner_outbox_dead_letters:24h` |
| Settlement/payout | `stage3:partner_payout_failures:15m`, `stage3:partner_settlement_dry_run_failures:24h`, `stage3:partner_payout_simulation_failures:24h` |
| Finance queue | `stage3:partner_payout_review_queue_items` |
| Support queue | `stage3:partner_support_cases_open`, `stage3:partner_cases_created:24h` |
| Audit/risk | `stage3:partner_risk_reviews_open`, `stage3:partner_audit_log_failures:1h`, `stage3:partner_antifraud_flags:24h` |
| Webhook lab | `stage3:partner_webhook_receiver_failures:15m` |

---

## 4. Backend Runtime Metrics Added

S3-STAGE-13 adds partner admin/support metrics that are emitted when internal users read the admin ops overview:

```text
cybervpn_partner_admin_ops_overview_requests_total{surface,workspace_status,result}
cybervpn_partner_support_cases_open{surface,case_status}
cybervpn_partner_payout_review_queue_items{surface,kind,status}
cybervpn_partner_audit_events_observed_total{surface,action_kind,result}
```

These metrics intentionally do not include:

- partner workspace id;
- customer id;
- email;
- Telegram id;
- payment provider payload;
- VPN subscription URL;
- payout destination details.

The labels are low-cardinality operational categories only.

---

## 5. Alert Coverage

Stage 3 alert families now cover:

| Alert | Priority | Reason |
|---|---|---|
| `Stage3PartnerBootstrapFailureRate` | P1 | Partner portal readiness regression. |
| `Stage3PartnerFrontendErrors` | P1 | Partner/admin browser runtime errors. |
| `Stage3PartnerAttributionNoOwnerHigh` | P1 | Attribution correctness risk. |
| `Stage3PartnerPayoutFailure` | P0 | Real payout failure must stop rollout. |
| `Stage3PartnerCommissionLedgerMismatch` | P0 | Finance correctness blocker. |
| `Stage3PartnerSettlementDryRunFailed` | P1 | Sandbox settlement/payout simulation failed. |
| `Stage3PartnerOutboxLagHigh` | P1 | Event delivery delay threatens partner operations. |
| `Stage3PartnerOutboxPublishFailure` | P1 | Event publish failure requires replay/retry review. |
| `Stage3PartnerOutboxDeadLetter` | P0 | Dead-letter event blocks expansion until classified. |
| `Stage3PartnerPayoutReviewBacklog` | P1 | Finance queue too large for controlled pilot. |
| `Stage3PartnerRiskReviewBacklog` | P1 | Risk queue too large for pilot expansion. |
| `Stage3PartnerAuditLogFailure` | P0 | Sensitive admin actions may be unaudited. |
| `Stage3PartnerWebhookReceiverFailures` | P1 | Webhook lab/signature/JSON path failed. |
| `Stage3StorefrontSyntheticFailure` | P1 | Partner/storefront/reseller synthetic route failed. |

---

## 6. Grafana Coverage

Stage 3 dashboards:

```text
infra/grafana/dashboards/stage3-partner-staging-readiness-dashboard.json
infra/grafana/dashboards/stage3-partner-attribution-storefront-dashboard.json
infra/grafana/dashboards/stage3-partner-settlement-payout-dashboard.json
infra/grafana/dashboards/stage3-partner-support-audit-risk-dashboard.json
```

Updated panels:

| Dashboard | Added/confirmed coverage |
|---|---|
| Stage 3 Partner Staging Readiness | Outbox lag P95 and outbox dead letters. |
| Stage 3 Partner Support Audit Risk | Support cases open and payout review queue items. |
| Stage 3 Partner Attribution And Storefront | Storefront synthetic failures and attribution no-owner signals. |
| Stage 3 Partner Settlement And Payout | Payout failures, settlement dry-run failures and ledger mismatch signals. |

Existing drilldown dashboards remain part of the S3 view:

```text
Partner Platform Runtime
Partner Platform Frontend UX
Logs Dashboard
Traces Dashboard
Sentry projects/issues
```

---

## 7. Loki/Sentry Sensitive Logging Rule

Do not send these into Loki, Sentry, Grafana annotations or release evidence:

```text
raw payment provider payloads
payment provider secrets
webhook signatures
payout destination account numbers
payout wallet addresses unless masked
VPN subscription URLs
VPN config links
Telegram initData
access/refresh tokens
OAuth authorization codes
TOTP secrets
raw email verification codes
raw customer email lists
raw partner import files
```

Allowed in logs/evidence:

```text
request_id
trace_id
span_id
workspace_status
case_type
payout review kind/status
masked customer label
aggregate counts
redacted error code
```

---

## 8. Exit Criteria Check

| Exit criterion | Result |
|---|---|
| Dashboards видны/configured | Passed locally: Stage 3 dashboard JSON validates and contains required panels. |
| Alerts загружены | Passed locally: Prometheus config loads Stage 3 rules, promtool sees 39 Stage 3 rules. |
| Synthetic probes работают/configured | Passed locally: Stage 3 blackbox job and target file are configured. Live scrape waits for DNS/edge readiness. |
| Outbox lag/failure/dead-letter visibility | Passed locally through Stage 3 recording rules and alerts. |
| Payout review backlog visibility | Passed locally through backend metrics, integration test and dashboard/rule coverage. |
| Support/admin ops visibility | Passed locally through admin ops overview metrics. |
| Sensitive logging не найден | Passed for changed files through local static scan; production Loki review remains a S3-STAGE-15/17 live evidence item. |
| Customer runtime independent from home observability | Passed by architecture decision; no customer dependency was added. |

---

## 9. Validation

Commands:

```bash
cd backend

.venv/bin/python -m py_compile \
  src/infrastructure/monitoring/partner_runtime_metrics.py \
  src/infrastructure/monitoring/instrumentation/partner_runtime.py \
  src/presentation/api/v1/partners/routes.py \
  tests/integration/test_partner_portal_reporting_reads.py \
  tests/contract/test_partner_statement_openapi_contract.py

.venv/bin/python -m ruff check \
  src/infrastructure/monitoring/partner_runtime_metrics.py \
  src/infrastructure/monitoring/instrumentation/partner_runtime.py \
  src/presentation/api/v1/partners/routes.py \
  tests/integration/test_partner_portal_reporting_reads.py

.venv/bin/python -m pytest \
  tests/contract/test_partner_statement_openapi_contract.py \
  -q --no-cov

.venv/bin/python -m pytest \
  tests/integration/test_partner_portal_reporting_reads.py::test_partner_workspace_reporting_and_cases_are_visible_to_workspace_members \
  -q --no-cov

.venv/bin/python -m pytest \
  tests/integration/test_partner_runtime_observability.py \
  -q --no-cov

jq empty \
  infra/grafana/dashboards/stage3-partner-staging-readiness-dashboard.json \
  infra/grafana/dashboards/stage3-partner-support-audit-risk-dashboard.json \
  infra/grafana/dashboards/stage3-partner-attribution-storefront-dashboard.json \
  infra/grafana/dashboards/stage3-partner-settlement-payout-dashboard.json \
  infra/prometheus/targets/stage3-storefront-endpoints.json

docker run --rm --entrypoint promtool \
  -v "$PWD/infra/prometheus:/etc/prometheus:ro" \
  prom/prometheus:v3.8.1 \
  check config /etc/prometheus/prometheus.yml

docker run --rm --entrypoint promtool \
  -v "$PWD/infra/prometheus/rules:/etc/prometheus/rules:ro" \
  prom/prometheus:v3.8.1 \
  check rules /etc/prometheus/rules/stage3_partner_reseller_alerts.yml
```

Observed result:

```text
py_compile: passed
ruff: All checks passed
pytest OpenAPI contract: 1 passed
pytest partner reporting/support/admin ops integration: 1 passed
pytest partner runtime observability: 8 passed
jq dashboard/target validation: passed
promtool config: valid; 18 rule files found; Stage 3 rules loaded
promtool Stage 3 rules: 39 rules found
```

Promtool warnings:

```text
alloy-*.json / nats-*.json / control-plane-alloy-*.json / openbao-*.json file_sd files are absent in this local source tree check.
```

These are existing optional runtime target files and are not S3-STAGE-13 blockers.

---

## 10. Production/Home Deployment Notes

Before S3 production disabled-state deploy:

1. copy/update Stage 3 dashboards on home Grafana;
2. copy/update `stage3_partner_reseller_alerts.yml` on home Prometheus;
3. copy/update `stage3-storefront-endpoints.json` under Prometheus targets;
4. reload/recreate Prometheus;
5. confirm Alertmanager route receives synthetic Stage 3 test alert;
6. confirm Loki query does not expose forbidden sensitive fields;
7. keep `PARTNER_PAYOUTS_ENABLED=false`;
8. keep public partner features gated until S3-STAGE-16/17 approval.

---

## 11. Next

```text
S3-STAGE-14: Security, Privacy, Legal, And Compliance Gate
```
