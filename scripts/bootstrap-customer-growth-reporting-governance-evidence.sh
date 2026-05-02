#!/usr/bin/env bash

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DATE_VALUE="${1:-$(date +%F)}"
ENVIRONMENT="${2:-staging}"
RUN_ID="${3:-growth-reporting-governance-run01}"
RELEASE_RING="${4:-R2}"
OWNER_VALUE="${5:-pending owner}"

TARGET_DIR="${REPO_ROOT}/docs/evidence/customer-growth/${DATE_VALUE}/${ENVIRONMENT}/growth-reporting-governance/${RUN_ID}"
README_PATH="${TARGET_DIR}/README.md"

mkdir -p \
  "${TARGET_DIR}/api" \
  "${TARGET_DIR}/screenshots" \
  "${TARGET_DIR}/logs" \
  "${TARGET_DIR}/exports" \
  "${TARGET_DIR}/approvals"

cat > "${README_PATH}" <<EOF
# Customer Growth Reporting Governance Evidence

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

- [ ] customer growth reporting governance conformance workflow green
- [ ] required check \`All Customer Growth Reporting Governance Checks Passed\` green
- [ ] committed OpenAPI spec in sync
- [ ] committed admin generated API types in sync
- [ ] committed frontend generated API types in sync
- [ ] committed partner generated API types in sync
- [ ] governance alert rules loaded in Prometheus
- [ ] governance runbook reviewed by operator
- [ ] evidence directory created

---

## Scenario Matrix

| Scenario ID | Description | Status | Evidence Link | Notes |
|---|---|---|---|---|
| GRG-001 | \`delivery_suppressed\` subscription appears in governance overview | pending | ./api/grg-001/ | |
| GRG-002 | \`recipient_domain_blocked\` subscription appears in governance overview | pending | ./api/grg-002/ | |
| GRG-003 | governance snapshot export captured and attached | pending | ./exports/grg-003-governance-export.json | |
| GRG-004 | governance audit timeline matches recipient or policy change | pending | ./api/grg-004/ | |

---

## CI Gate Evidence

| Check | Result | Evidence Link |
|---|---|---|
| backend conformance pack | pending | ./logs/backend-conformance.txt |
| admin surface readiness | pending | ./logs/admin-conformance.txt |
| governance asset validation | pending | ./logs/assets-conformance.txt |

---

## Alert And Export Proof

| Signal | Result | Evidence Link | Notes |
|---|---|---|---|
| governance gap metric visible | pending | ./exports/governance-gap-metric.json | |
| recipient-domain-blocked metric visible | pending | ./exports/recipient-domain-blocked-metric.json | |
| governance overview export available | pending | ./exports/governance-overview.json | |
| governance handoff check prepared | pending | ./approvals/github-gate-handoff.md | |

---

## Final Decision

**Decision:** pending
**Decision Owner:** pending
**Timestamp:** pending
**Summary:** pending
**Gate Readiness Artifact:** ./approvals/gate-readiness.md
**Gate Readiness JSON:** ./approvals/gate-readiness.json
EOF

printf '[OK] Customer growth reporting governance evidence pack initialized at %s\n' "${TARGET_DIR}"
