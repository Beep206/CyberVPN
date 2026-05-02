#!/usr/bin/env bash

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DATE_VALUE="${1:-$(date +%F)}"
ENVIRONMENT="${2:-staging}"
RUN_ID="${3:-partner-observability-run01}"
RELEASE_RING="${4:-R2}"
OWNER_VALUE="${5:-pending owner}"

TARGET_DIR="${REPO_ROOT}/docs/evidence/partner-platform/${DATE_VALUE}/${ENVIRONMENT}/partner-observability/${RUN_ID}"
README_PATH="${TARGET_DIR}/README.md"

mkdir -p \
  "${TARGET_DIR}/prometheus" \
  "${TARGET_DIR}/grafana" \
  "${TARGET_DIR}/alertmanager" \
  "${TARGET_DIR}/frontend-runtime" \
  "${TARGET_DIR}/web-vitals" \
  "${TARGET_DIR}/traces" \
  "${TARGET_DIR}/logs" \
  "${TARGET_DIR}/screenshots" \
  "${TARGET_DIR}/approvals"

cat > "${README_PATH}" <<EOF
# Partner Observability Evidence

**Run ID:** ${RUN_ID}
**Date:** ${DATE_VALUE}
**Environment:** ${ENVIRONMENT}
**Release Ring:** ${RELEASE_RING}
**Owner:** ${OWNER_VALUE}
**Participants:** pending participants
**CI Workflow URL:** pending workflow url
**Result:** pending

---

## Preconditions

- [ ] observability CI workflow green
- [ ] observability assets conformance green
- [ ] staging hosts reachable
- [ ] staging synthetic accounts prepared
- [ ] Grafana credentials verified
- [ ] rollback owner online
- [ ] evidence directory created

---

## Synthetic Signal Matrix

| Signal ID | Description | Status | Evidence Link | Notes |
|---|---|---|---|---|
| OBS-SYN-001 | partner route_load event ingested and recorded | pending | ./frontend-runtime/partner-route-load.json | |
| OBS-SYN-002 | admin render_error event ingested and recorded | pending | ./frontend-runtime/admin-render-error.json | |
| OBS-SYN-003 | partner LCP web vital ingested and recorded | pending | ./web-vitals/partner-lcp.json | |
| OBS-SYN-004 | admin INP web vital ingested and recorded | pending | ./web-vitals/admin-inp.json | |

---

## Prometheus Proof

| Check | Result | Evidence Link | Notes |
|---|---|---|---|
| frontend route-load direct metric present | pending | ./prometheus/partner-route-load-count.json | |
| frontend render-error direct metric present | pending | ./prometheus/admin-render-error-count.json | |
| frontend LCP direct metric present | pending | ./prometheus/partner-lcp-count.json | |
| frontend INP direct metric present | pending | ./prometheus/admin-inp-count.json | |
| route-load recording rule present | pending | ./prometheus/frontend-route-load-p95.json | |
| LCP recording rule present | pending | ./prometheus/frontend-lcp-p75.json | |
| INP recording rule present | pending | ./prometheus/frontend-inp-p75.json | |
| alert rules loaded in Prometheus | pending | ./prometheus/rules.json | |

---

## Grafana Proof

| Check | Result | Evidence Link | Notes |
|---|---|---|---|
| frontend UX dashboard discoverable | pending | ./grafana/frontend-ux-dashboard-search.json | |
| frontend UX dashboard resolvable by uid | pending | ./grafana/frontend-ux-dashboard.json | |
| runtime dashboard screenshot captured | pending | ./screenshots/runtime-dashboard.png | |
| frontend UX dashboard screenshot captured | pending | ./screenshots/frontend-ux-dashboard.png | |

---

## Alertmanager Proof

| Check | Result | Evidence Link | Notes |
|---|---|---|---|
| Alertmanager health endpoint reachable | pending | ./alertmanager/health.txt.json | |
| Alertmanager status endpoint reachable | pending | ./alertmanager/status.json | |
| receivers API returns configured receivers | pending | ./alertmanager/receivers.json | |

---

## Fire-Drill Register

| Drill ID | Alert | Trigger Method | Result | Evidence Link | Notes |
|---|---|---|---|---|---|
| OBS-FD-001 | PartnerPlatformFrontendErrorSpike | pending | pending | ./alertmanager/fire-drill-001/ | |

---

## Dashboard Freshness

| Dashboard | Query Window | Expected Freshness | Result | Evidence Link |
|---|---|---|---|---|
| partner-platform-runtime | 5m / 15m | < 5 minutes | pending | ./grafana/runtime-dashboard-freshness.json |
| partner-platform-frontend-ux | 15m / 30m | < 5 minutes | pending | ./grafana/frontend-dashboard-freshness.json |

---

## Divergence Register

| ID | Category | Description | Severity | Owner | Blocking | Disposition |
|---|---|---|---|---|---|---|

---

## Final Decision

**Decision:** pending
**Decision Owner:** pending
**Timestamp:** pending
**Summary:** pending
EOF

printf '[OK] Observability evidence pack initialized at %s\n' "${TARGET_DIR}"
