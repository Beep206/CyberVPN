#!/usr/bin/env bash

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DATE_VALUE="${1:-$(date +%F)}"
ENVIRONMENT="${2:-staging}"
RUN_ID="${3:-growth-notification-rollout-run01}"
RELEASE_RING="${4:-R2}"
OWNER_VALUE="${5:-pending owner}"

TARGET_DIR="${REPO_ROOT}/docs/evidence/customer-growth/${DATE_VALUE}/${ENVIRONMENT}/growth-notification-rollout/${RUN_ID}"
README_PATH="${TARGET_DIR}/README.md"

mkdir -p \
  "${TARGET_DIR}/api" \
  "${TARGET_DIR}/screenshots" \
  "${TARGET_DIR}/logs" \
  "${TARGET_DIR}/exports" \
  "${TARGET_DIR}/approvals"

cat > "${README_PATH}" <<EOF
# Customer Growth Notification Rollout Evidence

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

- [ ] customer growth notification conformance workflow green
- [ ] committed OpenAPI spec in sync
- [ ] committed frontend generated API types in sync
- [ ] committed admin generated API types in sync
- [ ] dashboard \`customer-growth-notification-delivery\` available
- [ ] alert rules loaded in Prometheus
- [ ] rollback owner online
- [ ] evidence directory created

---

## Scenario Matrix

| Scenario ID | Description | Status | Evidence Link | Notes |
|---|---|---|---|---|
| GCN-REPAIR-001 | preferences reenabled auto-recovers email delivery | pending | ./api/gcn-repair-001/ | |
| GCN-REPAIR-002 | contact data corrected re-arms blocked email delivery | pending | ./api/gcn-repair-002/ | |
| GCN-REPAIR-003 | telegram linked re-arms blocked Telegram delivery | pending | ./api/gcn-repair-003/ | |
| GCN-REPAIR-004 | support resolved closes escalation and emits closure notice | pending | ./api/gcn-repair-004/ | |

---

## CI Gate Evidence

| Check | Result | Evidence Link |
|---|---|---|
| backend conformance pack | pending | ./logs/backend-conformance.txt |
| frontend surface readiness | pending | ./logs/frontend-conformance.txt |
| admin surface readiness | pending | ./logs/admin-conformance.txt |
| rollout asset validation | pending | ./logs/assets-conformance.txt |

---

## Dashboard And Alert Proof

| Signal | Result | Evidence Link | Notes |
|---|---|---|---|
| unresolved backlog delta visible | pending | ./screenshots/unresolved-backlog.png | |
| recovery ratio visible | pending | ./screenshots/recovery-ratio.png | |
| unresolved backlog alert loaded | pending | ./exports/alert-rule-unresolved.json | |
| recovery ratio alert loaded | pending | ./exports/alert-rule-recovery-ratio.json | |

---

## Final Decision

**Decision:** pending
**Decision Owner:** pending
**Timestamp:** pending
**Summary:** pending
EOF

printf '[OK] Customer growth notification evidence pack initialized at %s\n' "${TARGET_DIR}"
