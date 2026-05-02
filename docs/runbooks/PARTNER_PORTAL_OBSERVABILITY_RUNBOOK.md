# Partner Portal Observability Runbook

This runbook covers the first production observability slice for the partner platform runtime:

- partner auth / realm / session
- partner bootstrap
- application / onboarding runtime
- notifications / cases
- finance / payouts / statements
- attribution
- outbox publishing
- partner/admin frontend UX runtime

## Primary Dashboard

Use Grafana dashboard `partner-platform-runtime`.
Use Grafana dashboard `partner-platform-frontend-ux` for browser-side route load, submit path, API latency, route guard, and frontend error signals.

Primary signals:
- auth success ratio and cross-realm denials
- bootstrap success ratio and p95 latency
- application submission throughput
- notification generation and case actions
- statement close / payout execution throughput
- payout failures
- outbox publish lag and failure ratio
- attribution no-owner ratio

Frontend UX signals:
- route-load p95 by surface
- browser API p95 by surface
- web-vitals p75 by surface: LCP / INP / CLS / TTFB / FCP
- submit attempts vs submit failures
- route guard blocks
- unhandled/render error rate

## Alert Triage Order

1. `PartnerPlatformBootstrapFailureRateCritical`
Check partner login, partner realm resolution, and `GET /api/v1/partner-session/bootstrap`.
If bootstrap is failing with live traffic, treat this as the highest-priority partner runtime issue.

2. `PartnerPlatformCrossRealmDeniedSpike` / `PartnerPlatformWrongHostTokenSpike`
Check host-to-realm mapping, token audience, client routing, and recent auth/session changes.
Look for deploy regressions before assuming hostile traffic.

3. `PartnerPlatformPayoutFailuresSpike`
Check statement state, payout account eligibility, payout instruction approval, and payout execution logs.
Confirm whether failures are isolated to one rail or systemic.

4. `PartnerPlatformOutboxFailureRateHigh` / `PartnerPlatformOutboxLagHigh`
Check outbox publication claims, failed consumers, retry loops, and downstream publisher health.
Correlate with worker and database saturation before replaying events manually.

5. `PartnerPlatformAttributionNoOwnerRateHigh`
Check touchpoint recording, code validity, attribution inputs, and recent checkout/order changes.
Confirm whether the issue is partner-specific, storefront-specific, or global.

6. `PartnerPlatformFrontendRouteLoadLatencyHigh` / `PartnerPlatformFrontendSubmitFailuresHigh` / `PartnerPlatformFrontendErrorSpike` / `PartnerPlatformFrontendLCPHigh` / `PartnerPlatformFrontendINPHigh`
Check browser-side route load, web-vitals, API latency, submit path regressions, and Sentry/frontend breadcrumbs before assuming backend-only degradation.
Correlate the affected `surface` label with the latest frontend deploy and the matching backend mutation/API path.

## Immediate Checks

### Auth / Realm

Run:

```bash
curl -s http://localhost:9094/api/v1/query --data-urlencode 'query=partner_platform:auth_cross_realm_denied:increase15m'
curl -s http://localhost:9094/api/v1/query --data-urlencode 'query=partner_platform:auth_wrong_host_rejected:increase15m'
```

Check:
- recent auth deploys
- partner host routing
- cookie / session namespace separation
- wrong-host clients or stale sessions

### Bootstrap

Run:

```bash
curl -s http://localhost:9094/api/v1/query --data-urlencode 'query=partner_platform:bootstrap_success_ratio:5m'
curl -s http://localhost:9094/api/v1/query --data-urlencode 'query=partner_platform:bootstrap_duration_seconds:p95_15m'
```

Check:
- backend API errors
- workspace resolution
- blocked-reason/readiness overlays
- DB latency

### Finance / Payouts

Run:

```bash
curl -s http://localhost:9094/api/v1/query --data-urlencode 'query=partner_platform:payout_failures:increase15m'
curl -s http://localhost:9094/api/v1/query --data-urlencode 'query=partner_platform:statement_closes:rate1h'
```

Check:
- payout execution logs
- verified payout account availability
- instruction approval / maker-checker chain
- settlement period / statement status

### Outbox

Run:

```bash
curl -s http://localhost:9094/api/v1/query --data-urlencode 'query=partner_platform:outbox_publish_failure_ratio:5m'
curl -s http://localhost:9094/api/v1/query --data-urlencode 'query=partner_platform:outbox_lag_seconds:p95_15m'
```

Check:
- consumer lease ownership
- failed publication rows
- retry / dead-letter posture
- worker saturation or DB contention

### Attribution

Run:

```bash
curl -s http://localhost:9094/api/v1/query --data-urlencode 'query=partner_platform:attribution_no_owner_ratio:5m'
```

Check:
- touchpoint capture rate
- partner code validity
- order attribution resolution logs
- recent checkout / order deploys

### Frontend UX

Run:

```bash
curl -s http://localhost:9094/api/v1/query --data-urlencode 'query=partner_platform:frontend_route_load_duration_seconds:p95_15m'
curl -s http://localhost:9094/api/v1/query --data-urlencode 'query=partner_platform:frontend_submit_failure_ratio:15m'
curl -s http://localhost:9094/api/v1/query --data-urlencode 'query=partner_platform:frontend_error_events:rate15m'
curl -s http://localhost:9094/api/v1/query --data-urlencode 'query=partner_platform:frontend_lcp_seconds:p75_30m'
curl -s http://localhost:9094/api/v1/query --data-urlencode 'query=partner_platform:frontend_inp_seconds:p75_30m'
curl -s http://localhost:9094/api/v1/query --data-urlencode 'query=partner_platform:frontend_cls_ratio:p75_30m'
```

Check:
- whether the issue is isolated to `partner_portal` or `admin_portal`
- recent frontend deploys and route-level changes
- whether the regression is route-load only or also visible in field web-vitals
- browser-side API p95 versus backend API latency
- route-guard block spikes after access-policy or release-ring changes
- Sentry breadcrumbs for `submit_failure`, `render_error`, and `unhandled_error`

## Staging Verification

For staging or pre-cutover validation of frontend observability, run:

```bash
export EVIDENCE_DIR="docs/evidence/partner-platform/2026-04-20/staging/partner-observability/observability-run01"
npm run evidence:partner-observability:init -- 2026-04-20 staging observability-run01 R2 "pending owner"

export CYBERVPN_PARTNER_HOST="https://partners.staging.cybervpn.example"
export CYBERVPN_ADMIN_HOST="https://admin.staging.cybervpn.example"
export PROMETHEUS_URL="https://prometheus.staging.cybervpn.example"
export GRAFANA_URL="https://grafana.staging.cybervpn.example"
export GRAFANA_USER="admin"
export GRAFANA_PASSWORD="replace-me"
export ALERTMANAGER_URL="https://alertmanager.staging.cybervpn.example"

npm run staging:partner-observability:smoke
```

This smoke verifies:
- partner/admin app routes accept synthetic frontend runtime and web-vitals events;
- Prometheus receives direct metrics and recording rules for route load plus web-vitals;
- Grafana serves the `partner-platform-frontend-ux` dashboard;
- Alertmanager is reachable and exposes configured receivers.

## Evidence To Capture

For every incident or alert spike, capture:
- Grafana screenshot from `partner-platform-runtime`
- if frontend-involved, a screenshot from `partner-platform-frontend-ux`
- matching Prometheus query output
- one correlated trace or structured log sample
- affected deployment SHA or release window
- final root cause and remediation

Use template:
- `docs/evidence/partner-platform/templates/partner-observability-evidence-template.md`

GitHub protection handoff:
- `docs/runbooks/PARTNER_OBSERVABILITY_GITHUB_PROTECTION_HANDOFF.md`

## Escalation

- `critical` alerts: backend owner + partner ops immediately
- finance-affecting alerts: include finance ops
- attribution or outbox alerts that affect partner earnings or payout correctness: include product + finance + backend

Do not silence partner finance or bootstrap alerts without capturing evidence and a root-cause hypothesis.
