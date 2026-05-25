# S3-STAGE-13 Evidence: Partner Observability And Alerting

**Date:** 2026-05-25
**Stage:** `S3-STAGE-13`
**Status:** Passed for local code/config/evidence gate
**Stage document:** `docs/cybervpn_stage3_launch_docs/13_STAGE3_PARTNER_OBSERVABILITY_ALERTING.md`

---

## 1. Summary

S3-STAGE-13 proves local readiness for Stage 3 partner/reseller observability:

```text
Stage 3 Prometheus rules are loaded by prometheus.yml
Stage 3 storefront blackbox scrape job is configured
Stage 3 target file validates as JSON
Stage 3 dashboards validate as JSON
support/admin ops emits low-cardinality Prometheus metrics
payout review backlog has backend metric, dashboard panel and alert rule
support case backlog has backend metric and dashboard panel
outbox lag, publish failures and dead letters have Stage 3 recording/alert rules
storefront synthetic failures have Stage 3 alert rule
partner runtime observability integration tests pass
sensitive logging scan over changed files has no real secret material
customer runtime remains independent from home observability
```

This does not enable public partner pilot, real payouts, public storefronts, or production event-backbone expansion.

---

## 2. Changed Files

```text
backend/src/infrastructure/monitoring/partner_runtime_metrics.py
backend/src/infrastructure/monitoring/instrumentation/partner_runtime.py
backend/src/presentation/api/v1/partners/routes.py
backend/tests/integration/test_partner_portal_reporting_reads.py
infra/prometheus/prometheus.yml
infra/prometheus/rules/stage3_partner_reseller_alerts.yml
infra/grafana/dashboards/stage3-partner-staging-readiness-dashboard.json
infra/grafana/dashboards/stage3-partner-support-audit-risk-dashboard.json
docs/runbooks/PARTNER_RESELLER_STAGE3_RUNBOOK.md
docs/cybervpn_stage3_launch_docs/13_STAGE3_PARTNER_OBSERVABILITY_ALERTING.md
docs/evidence/releases/s3-stage-13-partner-observability-alerting-20260525.md
docs/plans/2026-05-23-cybervpn-s3-stage-roadmap-ru.md
```

---

## 3. Proof Matrix

| Proof | Result |
|---|---|
| Prometheus loads `stage3_partner_reseller_alerts.yml` | Passed |
| Stage 3 blackbox job exists in `prometheus.yml` | Passed |
| Stage 3 target file JSON validates | Passed |
| Stage 3 dashboards JSON validate | Passed |
| Stage 3 support/audit dashboard includes support cases open | Passed |
| Stage 3 support/audit dashboard includes payout review queue | Passed |
| Stage 3 readiness dashboard includes outbox lag P95 | Passed |
| Stage 3 readiness dashboard includes outbox dead letters | Passed |
| Stage 3 alerts include storefront synthetic failure | Passed |
| Stage 3 alerts include outbox lag/failure/dead-letter | Passed |
| Stage 3 alerts include payout review backlog | Passed |
| Backend emits admin ops overview request metric | Passed |
| Backend emits support cases open metric | Passed |
| Backend emits payout review queue item metric | Passed |
| Backend emits observed audit events metric | Passed |
| Partner runtime observability integration tests pass | Passed |
| Sensitive log/secret static scan finds no real secret material | Passed with expected test-only password false positives |

---

## 4. Commands

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
promtool config: valid; Stage 3 rules loaded
promtool Stage 3 rules: 39 rules found
```

Promtool local warnings:

```text
WARNING: optional file_sd files alloy-*.json, nats-*.json, control-plane-alloy-*.json and openbao-*.json do not exist in the local source-tree check.
```

These are existing optional runtime target files and are not introduced by S3-STAGE-13.

---

## 5. Backend Metrics Added

```text
cybervpn_partner_admin_ops_overview_requests_total{surface,workspace_status,result}
cybervpn_partner_support_cases_open{surface,case_status}
cybervpn_partner_payout_review_queue_items{surface,kind,status}
cybervpn_partner_audit_events_observed_total{surface,action_kind,result}
```

Label policy:

```text
low-cardinality only
no workspace_id
no customer_id
no email
no Telegram id
no raw payment payload
no VPN subscription URL
no payout destination secret
```

---

## 6. Alert Coverage Added

New/confirmed Stage 3 alerts:

```text
Stage3PartnerOutboxLagHigh
Stage3PartnerOutboxPublishFailure
Stage3PartnerOutboxDeadLetter
Stage3PartnerPayoutReviewBacklog
Stage3StorefrontSyntheticFailure
```

Existing Stage 3 alert families remain:

```text
bootstrap failure ratio
frontend errors
attribution no-owner high
payout failure
commission ledger mismatch
settlement dry-run failure
risk review backlog
audit log failure
webhook receiver failures
```

---

## 7. Dashboard Coverage Added

```text
Stage 3 Partner Staging Readiness:
- Outbox Lag P95
- Outbox Dead Letters 24h

Stage 3 Partner Support Audit Risk:
- Support Cases Open
- Payout Review Queue Items
```

---

## 8. Sensitive Logging Scan

Static scan scope:

```text
backend/src/infrastructure/monitoring/partner_runtime_metrics.py
backend/src/infrastructure/monitoring/instrumentation/partner_runtime.py
backend/src/presentation/api/v1/partners/routes.py
backend/tests/integration/test_partner_portal_reporting_reads.py
infra/prometheus/prometheus.yml
infra/prometheus/rules/stage3_partner_reseller_alerts.yml
infra/grafana/dashboards/stage3-partner-staging-readiness-dashboard.json
infra/grafana/dashboards/stage3-partner-support-audit-risk-dashboard.json
docs/runbooks/PARTNER_RESELLER_STAGE3_RUNBOOK.md
docs/cybervpn_stage3_launch_docs/13_STAGE3_PARTNER_OBSERVABILITY_ALERTING.md
docs/evidence/releases/s3-stage-13-partner-observability-alerting-20260525.md
```

Result:

```text
No real secret material found.
Expected false positives: test-only passwords in backend/tests/integration/test_partner_portal_reporting_reads.py.
```

---

## 9. Production Notes

Before live S3 pilot:

1. copy Stage 3 rules/targets/dashboards to home observability;
2. reload Prometheus and confirm rules are visible in `/api/v1/rules`;
3. confirm Grafana dashboards are visible;
4. fire one synthetic Stage 3 test alert and confirm owner channel delivery;
5. run one Loki sensitive-field query pack;
6. keep partner features gated until S3-STAGE-16/17.

---

## 10. Next

```text
S3-STAGE-14: Security, Privacy, Legal, And Compliance Gate
```
