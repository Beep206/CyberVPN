# Stage 2 Analytics And Reporting Runbook

**Scope:** CyberVPN Stage 2 analytics, reporting, synthetic checks, Sentry frontend releases, and CI quality gates.  
**Primary host:** `10.10.10.34`  
**Public domain scope:** `*.h.cyber-vpn.net`

---

## 1. Operator Summary

Stage 2 adds business and quality observability on top of S1. The important rule is that analytics must help decisions without slowing customer flows.

Use Grafana for live operational views, Prometheus/Alertmanager for alerting, Sentry for frontend/backend error details, and evidence archives for audit-grade proof.

---

## 2. Dashboards

### Payment reconciliation

Dashboard: `Stage 2 Payment Reconciliation`

Use this when:

- a customer paid but did not receive access;
- webhook retries are increasing;
- a provider says payment succeeded but CyberVPN state does not match;
- support asks for proof of payment-processing health.

Primary signals:

- `stage2:payment_success_ratio:24h`
- `stage2:payment_failures:24h`
- `stage2:paid_but_no_access:current`
- `stage2:payment_reconciliation_max_age_minutes`
- `stage2:webhook_failures:1h`
- `stage2:webhook_retries:1h`

Initial response:

1. Open the dashboard and check current paid-but-no-access count.
2. Check max reconciliation age. Anything above 60 minutes is a support risk.
3. Inspect webhook failures by provider.
4. Open Sentry for backend/worker errors at the same time window.
5. Confirm whether the issue is provider-side, webhook-side, or access-provisioning-side.
6. Record evidence under `/srv/storage/evidence/incidents/` if customer impact exists.

### Refund and renewal

Dashboard: `Stage 2 Refund And Renewal`

Use this when:

- refunds spike;
- chargebacks appear;
- renewal success falls;
- retained revenue numbers look wrong.

Primary signals:

- `stage2:refunds:24h`
- `stage2:chargebacks:24h`
- `stage2:renewal_success_ratio:24h`
- `stage2:renewal_failures:24h`

Operator notes:

- A single chargeback is review-worthy for a small S2 system.
- Refund spikes must be cross-checked against marketing campaigns, payment provider incidents, and support backlog.
- Renewal failures must be checked against payment provider errors and subscription expiry jobs.

### Subscription expiry

Dashboard: `Stage 2 Subscription Expiry`

Use this when:

- users report access lost too early;
- expired users keep access;
- renewal reminders or disable jobs are suspected to be stuck.

Primary signals:

- `stage2:subscriptions_expiring_24h`
- `stage2:subscriptions_expiring_72h`
- `stage2:subscriptions_expiring_7d`
- `stage2:expired_disable_failures:24h`

Operator notes:

- Expiry data is operationally sensitive because it affects access control and revenue.
- Never manually alter subscription state without recording who, why, and what evidence was used.

### Support SLA

Dashboard: `Stage 2 Support SLA`

Use this when:

- support backlog grows;
- P1/P0 support promises are at risk;
- payment or VPN-access incidents create follow-up load.

Primary signals:

- `stage2:support_open_items:current`
- `stage2:support_sla_overdue:current`
- `stage2:support_first_response_p95_seconds`
- `stage2:support_resolution_p95_seconds`

Operator notes:

- Support SLA breach alerts should create an incident note if tied to payment/access impact.
- Support private notes must not be exported to product analytics or public status pages.

### Status page data source

Dashboard: `Stage 2 Status Page Data Source`

Use this when:

- public endpoints look unstable;
- TLS renewal is near expiry;
- a public status page needs a machine-readable source.

Primary signals:

- `stage2:status_public_endpoint_success_ratio:5m`
- `stage2:synthetic_failures:15m`
- `stage2:synthetic_slow_probes:15m`
- `stage2:tls_cert_min_days`

Export a status sample:

```bash
scripts/status/export-status-page-data.sh
```

Server output:

```text
/srv/storage/evidence/status-page/status-page-data.json
```

### Product analytics ingestion

Dashboard: `Stage 2 Product Analytics`

Use this when:

- frontend funnel data is missing;
- checkout conversion looks wrong;
- analytics ingestion drops events;
- frontend performance regresses.

Primary signals:

- `stage2:analytics_ingestion_dropped:15m`
- `stage2:frontend_web_vitals_lcp_p75_seconds`
- `stage2:frontend_web_vitals_inp_p75_seconds`
- `stage2:frontend_web_vitals_cls_p75_ratio`
- `stage2:checkout_conversion_ratio:24h`

Rules:

1. Analytics ingestion must be asynchronous.
2. Frontend must never block page rendering on analytics.
3. Drop or sample non-critical analytics before slowing checkout, auth, or support flows.
4. Do not log tokens, payment payloads, subscription URLs, full request bodies, or PII.
5. Use stable event names and bounded label cardinality.

### Release quality gates

Dashboard: `Stage 2 Release Quality Gates`

Use this before and after releases.

Primary signals:

- `stage2:release_security_gate_failures:24h`
- `stage2:sbom_age_seconds`
- `stage2:restore_drill_age_seconds`
- `stage2:sentry_frontend_errors:1h`

Operator notes:

- A failed security quality gate is a release blocker unless the owner explicitly writes and accepts a risk exception.
- Backup success is not enough. Restore proof is required.
- Release comparison reports must be stored with release evidence.

---

## 3. Alert Response

### P0 alerts

Treat as release/customer-impact blockers:

- `Stage2StatusEndpointDown`
- `Stage2SecurityQualityGateFailed`

Actions:

1. Acknowledge in Alertmanager.
2. Create an incident evidence directory.
3. Capture Grafana screenshots or API snapshots.
4. Capture relevant logs from Loki.
5. Record mitigation, owner, and rollback status.

### P1 alerts

Treat as operator action required:

- `Stage2PaymentReconciliationBacklog`
- `Stage2RefundSpike`
- `Stage2RenewalFailures`
- `Stage2SubscriptionExpiryBacklog`
- `Stage2SupportSlaBreach`
- `Stage2TlsCertificateExpiresSoon`
- `Stage2AnalyticsIngestionDroppingEvents`
- `Stage2RestoreDrillOverdue`
- `Stage2SentryFrontendErrorsElevated`

Actions:

1. Open the linked dashboard.
2. Check the matching Sentry project and Loki logs.
3. Decide if customer impact exists.
4. If impact exists, create incident evidence.
5. If no impact exists, document why the alert was benign and tune thresholds only after a repeat pattern.

---

## 4. Synthetic Checks

Targets live in:

```text
infra/prometheus/targets/stage2-public-endpoints.json
```

Server path:

```text
/srv/cybervpn-h/configs/prometheus/targets/stage2-public-endpoints.json
```

Verify Prometheus target state:

```bash
curl -fsS http://127.0.0.1:9090/api/v1/targets | jq '.data.activeTargets[] | select(.labels.job=="stage2-public-endpoints") | {health, scrapeUrl, lastError}'
```

Do not include non-CyberVPN domains in this target file.

---

## 5. Better Log Retention

Current Stage 2 policy:

- Loki hot/cold logs: 14 days on the home server unless disk pressure requires less.
- Security, backup, restore, incident, release evidence: retained separately under `/srv/storage/evidence`.
- Raw application logs must not be the only evidence for important releases or incidents.

If disk pressure rises:

1. Keep evidence archives.
2. Reduce Loki retention before deleting evidence.
3. Preserve incident windows before compaction or cleanup.

---

## 6. Scheduled Restore Drills

Monthly restore drills should run through systemd timer on `10.10.10.34`.

Expected server units:

```text
/etc/systemd/system/cybervpn-restore-drill.service
/etc/systemd/system/cybervpn-restore-drill.timer
```

Evidence target:

```text
/srv/storage/evidence/restores/
```

Manual run:

```bash
sudo systemctl start cybervpn-restore-drill.service
```

Check:

```bash
systemctl status cybervpn-restore-drill.timer --no-pager
journalctl -u cybervpn-restore-drill.service -n 80 --no-pager
```

---

## 7. Release Comparison Reports

Generate a comparison report:

```bash
scripts/release/generate-release-comparison-report.sh <old-evidence-dir-or-ref> <new-evidence-dir-or-ref>
```

CI job:

```text
quality:release-comparison-report
```

Report must include:

- compared inputs;
- release manifest file status;
- image digest file status;
- SBOM file status;
- security scan file status;
- missing mandatory evidence;
- operator checklist.

Store reports under:

```text
/srv/storage/evidence/releases/
docs/evidence/releases/
```

---

## 8. Sentry source maps

Upload source maps only from CI or a controlled release machine:

```bash
scripts/sentry/upload-frontend-sourcemaps.sh
```

Required environment:

```text
SENTRY_AUTH_TOKEN
SENTRY_ORG
SENTRY_PROJECT
SENTRY_URL
SENTRY_RELEASE
SENTRY_DIST optional
FRONTEND_SOURCEMAPS_DIR optional, default frontend/.next/static
```

Rules:

- Do not serve source maps publicly.
- Upload source maps after the frontend build and before release acceptance.
- Sentry release must match the deployed frontend release.
- Source maps are operational evidence, not a substitute for CI build artifacts.

---

## 9. Frontend error tracking through tunnel/proxy

Preferred route:

```text
https://<frontend-domain>/monitoring/sentry-tunnel -> https://sentry.h.cyber-vpn.net/api/<project-id>/envelope/
```

Requirements:

- tunnel path must rate-limit abuse;
- tunnel must not log full event bodies;
- Caddy access logs must avoid sensitive request bodies;
- Sentry client must scrub PII and payment data;
- frontend DSN and tunnel route must be environment-specific.

Initial Caddy idea:

```caddyfile
@sentry_tunnel path /monitoring/sentry-tunnel
reverse_proxy @sentry_tunnel 127.0.0.1:9000
```

Finalize the exact path after frontend domains are locked.

---

## 10. CI quality gates

Required CI gate families:

- observability artifact validation;
- secret scanning;
- dependency audit;
- container/filesystem scan;
- SBOM generation;
- release comparison report;
- optional Sentry sourcemap upload.

Gate policy:

- `Stage2SecurityQualityGateFailed` is a release blocker.
- Secret findings are release blockers unless explicitly accepted as false positives in a reviewed baseline.
- High/critical dependency or container findings require owner review.
- SBOM must exist for release candidates.
- Release comparison report must exist for production release candidates.

---

## 11. Evidence Checklist

For every Stage 2 release candidate, preserve:

- release manifest;
- image digests;
- SBOM;
- Trivy report;
- Grype report;
- npm audit report;
- pip audit report;
- gitleaks report;
- release comparison report;
- Sentry release/deploy marker evidence;
- restore drill status;
- dashboard/rule validation output.

---

## 12. Known Gaps

Some dashboards intentionally include future metric names. They are provision-safe because queries use fallbacks such as `or vector(0)`. The next backend/worker work should add full instrumentation for:

- refunds and chargebacks;
- subscription renewals;
- subscription expiry forecast and disable outcomes;
- support SLA;
- product analytics ingestion;
- CI quality gate metric export;
- Sentry frontend error metric export.
