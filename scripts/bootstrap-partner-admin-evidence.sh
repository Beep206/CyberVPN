#!/usr/bin/env bash

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DATE_VALUE="${1:-$(date +%F)}"
ENVIRONMENT="${2:-staging}"
RUN_ID="${3:-partner-admin-conformance-run01}"
RELEASE_RING="${4:-R2}"
OWNER_VALUE="${5:-pending owner}"

TARGET_DIR="${REPO_ROOT}/docs/evidence/partner-platform/${DATE_VALUE}/${ENVIRONMENT}/partner-admin-conformance/${RUN_ID}"
README_PATH="${TARGET_DIR}/README.md"

mkdir -p \
  "${TARGET_DIR}/api" \
  "${TARGET_DIR}/screenshots" \
  "${TARGET_DIR}/logs" \
  "${TARGET_DIR}/approvals"

cat > "${README_PATH}" <<EOF
# Partner/Admin Conformance Evidence

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

- [ ] partner/admin conformance CI workflow green
- [ ] committed OpenAPI spec in sync
- [ ] committed admin generated API types in sync
- [ ] committed partner generated API types in sync
- [ ] staging smoke accounts prepared
- [ ] rollback owner online
- [ ] evidence directory created

---

## Scenario Matrix

| Scenario ID | Description | Status | Evidence Link | Notes |
|---|---|---|---|---|
| E2E-PARTNER-001 | applicant draft -> submit -> needs_info -> resubmit -> approved_probation | pending | ./api/e2e-partner-001/ | |
| E2E-PERM-010 | owner / finance / traffic_manager permission split | pending | ./api/e2e-perm-010/ | |
| E2E-AUTH-010 | partner realm isolation and logout-all revocation | pending | ./api/e2e-auth-010/ | |

---

## CI Gate Evidence

| Check | Result | Evidence Link |
|---|---|---|
| backend conformance pack | pending | ./logs/backend-conformance.txt |
| admin surface readiness | pending | ./logs/admin-conformance.txt |
| partner surface readiness | pending | ./logs/partner-conformance.txt |

---

## Auth And Realm Proof

| Check | Result | Evidence Link | Notes |
|---|---|---|---|
| partner login returns partner realm session | pending | ./api/auth/partner-login.json | |
| partner bootstrap works with partner session | pending | ./api/auth/partner-bootstrap.json | |
| admin token rejected on partner bootstrap | pending | ./api/auth/admin-on-partner-bootstrap.json | |
| partner token rejected on admin surface | pending | ./api/auth/partner-on-admin.json | |
| logout-all revokes current partner access session | pending | ./api/auth/logout-all-revocation.json | |

---

## Admin To Partner Sync Proof

| Admin Action | Partner Effect | Result | Evidence Link |
|---|---|---|---|
| request more info | partner sees needs_info task or notification | pending | ./api/sync/request-info/ |
| approve to probation | bootstrap status becomes approved_probation | pending | ./api/sync/approve-probation/ |
| verify payout account | finance surface reflects verified state | pending | ./api/sync/payout-verification/ |
| governance restriction applied | bootstrap blocked reasons update | pending | ./api/sync/governance/ |

---

## Role And Permission Proof

| Principal | Allowed Action | Result | Evidence Link |
|---|---|---|---|
| finance | create payout account | pending | ./api/permissions/finance-create-payout.json |
| finance | submit traffic declaration | pending | ./api/permissions/finance-traffic-blocked.json |
| traffic_manager | submit traffic declaration | pending | ./api/permissions/traffic-submit.json |
| traffic_manager | create payout account | pending | ./api/permissions/traffic-payout-blocked.json |

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

printf '[OK] Evidence pack initialized at %s\n' "${TARGET_DIR}"
