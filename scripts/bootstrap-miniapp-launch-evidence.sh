#!/usr/bin/env bash

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DATE_VALUE="${1:-$(date +%F)}"
ENVIRONMENT="${2:-staging}"
RUN_ID="${3:-miniapp-launch-run01}"
RELEASE_RING="${4:-R2}"
OWNER_VALUE="${5:-pending owner}"

TARGET_DIR="${REPO_ROOT}/docs/evidence/miniapp/${DATE_VALUE}/${ENVIRONMENT}/launch/${RUN_ID}"
README_PATH="${TARGET_DIR}/README.md"

mkdir -p \
  "${TARGET_DIR}/admin" \
  "${TARGET_DIR}/miniapp" \
  "${TARGET_DIR}/monitoring" \
  "${TARGET_DIR}/logs" \
  "${TARGET_DIR}/screenshots" \
  "${TARGET_DIR}/approvals"

cat > "${README_PATH}" <<EOF
# Mini App Launch Evidence

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

- [ ] miniapp launch conformance gate green
- [ ] committed OpenAPI and generated client types in sync
- [ ] Mini App runtime dashboard reachable
- [ ] launch-control dashboard reachable
- [ ] admin launch summary reviewed
- [ ] smoke customer is valid for current rollout mode
- [ ] rollback owner online
- [ ] evidence directory created

---

## API Checkpoints

| Check | Result | Evidence Link | Notes |
|---|---|---|---|
| admin runtime config | pending | ./admin/runtime.json | |
| admin launch readiness | pending | ./admin/launch-readiness.json | |
| admin launch summary | pending | ./admin/launch-summary.json | |
| admin launch timeline | pending | ./admin/launch-timeline.json | |
| customer mobile login | pending | ./miniapp/customer-login.json | |
| miniapp bootstrap | pending | ./miniapp/bootstrap.json | |
| miniapp offers | pending | ./miniapp/offers.json | |
| miniapp config | pending | ./miniapp/config.json | |
| miniapp payment status | optional | ./miniapp/payment-status.json | |
| miniapp trial activation | optional | ./miniapp/trial-activate.json | |

---

## Monitoring And Alerts

| Signal | Result | Evidence Link | Notes |
|---|---|---|---|
| launch state metric | pending | ./monitoring/launch-state.json | |
| launch blockers metric | pending | ./monitoring/launch-blockers.json | |
| runtime request rate | pending | ./monitoring/runtime-request-rate.json | |
| config failure ratio | pending | ./monitoring/config-failures.json | |

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

printf '[OK] Mini App launch evidence pack initialized at %s\n' "${TARGET_DIR}"
