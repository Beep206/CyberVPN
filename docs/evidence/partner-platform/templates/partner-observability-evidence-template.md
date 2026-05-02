# Partner Observability Evidence Template

**Template Date:** 2026-04-20  
**Use for:** staging or pre-cutover observability windows validating synthetic signal ingestion, recording rules, dashboards, Alertmanager reachability, and fire-drill evidence for the `partner + admin + backend` observability stack.

---

## 1. Run Metadata

```md
# Partner Observability Evidence

**Run ID:** <run-id>
**Date:** <YYYY-MM-DD>
**Environment:** <local|staging|production>
**Release Ring:** <R0|R1|R2|R3|R4>
**Owner:** <name/role>
**Participants:** <list>
**CI Workflow URL:** <github-actions-url>
**Result:** <pass|pass-with-issues|hold|rollback|fail>
```

---

## 2. Preconditions

```md
## Preconditions

- [ ] observability CI workflow green
- [ ] observability assets conformance green
- [ ] staging hosts reachable
- [ ] staging synthetic accounts prepared
- [ ] Grafana credentials verified
- [ ] rollback owner online
- [ ] evidence directory created
```

---

## 3. Synthetic Signal Matrix

```md
## Synthetic Signal Matrix

| Signal ID | Description | Status | Evidence Link | Notes |
|---|---|---|---|---|
| OBS-SYN-001 | partner route_load event ingested and recorded | pass | ./frontend-runtime/partner-route-load.json | |
| OBS-SYN-002 | admin render_error event ingested and recorded | pass | ./frontend-runtime/admin-render-error.json | |
| OBS-SYN-003 | partner LCP web vital ingested and recorded | pass | ./web-vitals/partner-lcp.json | |
| OBS-SYN-004 | admin INP web vital ingested and recorded | pass | ./web-vitals/admin-inp.json | |
```

Add more rows if the run includes additional synthetic events such as `submit_failure`, `route_guard_block`, or backend-only probes.

---

## 4. Prometheus Proof

```md
## Prometheus Proof

| Check | Result | Evidence Link | Notes |
|---|---|---|---|
| frontend route-load direct metric present | pass | ./prometheus/partner-route-load-count.json | |
| frontend render-error direct metric present | pass | ./prometheus/admin-render-error-count.json | |
| frontend LCP direct metric present | pass | ./prometheus/partner-lcp-count.json | |
| frontend INP direct metric present | pass | ./prometheus/admin-inp-count.json | |
| route-load recording rule present | pass | ./prometheus/frontend-route-load-p95.json | |
| LCP recording rule present | pass | ./prometheus/frontend-lcp-p75.json | |
| INP recording rule present | pass | ./prometheus/frontend-inp-p75.json | |
| alert rules loaded in Prometheus | pass | ./prometheus/rules.json | |
```

---

## 5. Grafana Proof

```md
## Grafana Proof

| Check | Result | Evidence Link | Notes |
|---|---|---|---|
| frontend UX dashboard discoverable | pass | ./grafana/frontend-ux-dashboard-search.json | |
| frontend UX dashboard resolvable by uid | pass | ./grafana/frontend-ux-dashboard.json | |
| runtime dashboard screenshot captured | pass | ./screenshots/runtime-dashboard.png | |
| frontend UX dashboard screenshot captured | pass | ./screenshots/frontend-ux-dashboard.png | |
```

---

## 6. Alertmanager Proof

```md
## Alertmanager Proof

| Check | Result | Evidence Link | Notes |
|---|---|---|---|
| Alertmanager health endpoint reachable | pass | ./alertmanager/health.txt.json | |
| Alertmanager status endpoint reachable | pass | ./alertmanager/status.json | |
| receivers API returns configured receivers | pass | ./alertmanager/receivers.json | |
```

---

## 7. Fire-Drill Register

```md
## Fire-Drill Register

| Drill ID | Alert | Trigger Method | Result | Evidence Link | Notes |
|---|---|---|---|---|---|
| OBS-FD-001 | PartnerPlatformFrontendErrorSpike | synthetic spike or manual replay | pass | ./alertmanager/fire-drill-001/ | |
```

Keep at least one real fire-drill row before approving rollout readiness.

---

## 8. Dashboard Freshness

```md
## Dashboard Freshness

| Dashboard | Query Window | Expected Freshness | Result | Evidence Link |
|---|---|---|---|---|
| partner-platform-runtime | 5m / 15m | < 5 minutes | pass | ./grafana/runtime-dashboard-freshness.json |
| partner-platform-frontend-ux | 15m / 30m | < 5 minutes | pass | ./grafana/frontend-dashboard-freshness.json |
```

---

## 9. Divergence Register

```md
## Divergence Register

| ID | Category | Description | Severity | Owner | Blocking | Disposition |
|---|---|---|---|---|---|---|
| D-01 | dashboard | example only | low | platform | no | follow-up after rollout |
```

Remove placeholder rows if the run is clean.

---

## 10. Final Decision

```md
## Final Decision

**Decision:** <approve|hold|rollback|re-run>
**Decision Owner:** <name/role>
**Timestamp:** <ISO-8601>
**Summary:** <short conclusion>
```

---

## 11. Archive Manifest

Recommended structure:

```text
docs/evidence/partner-platform/<YYYY-MM-DD>/<environment>/partner-observability/
  README.md
  prometheus/
  grafana/
  alertmanager/
  frontend-runtime/
  web-vitals/
  traces/
  logs/
  screenshots/
  approvals/
```

Recommended file naming:

```text
<YYYY-MM-DD>_<environment>_partner-observability_<signal-or-check-id>_<artifact-type>
```
