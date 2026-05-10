#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
OUTPUT_DIR="${STAGE3_SANDBOX_OUTPUT_DIR:-${ROOT_DIR}/docs/evidence/partner-platform/stage3-sandbox-${STAMP}}"

mkdir -p \
  "${OUTPUT_DIR}/attribution" \
  "${OUTPUT_DIR}/commission-ledger" \
  "${OUTPUT_DIR}/payout-simulation" \
  "${OUTPUT_DIR}/settlement-dry-run" \
  "${OUTPUT_DIR}/anti-fraud" \
  "${OUTPUT_DIR}/imports" \
  "${OUTPUT_DIR}/incidents"

cat > "${OUTPUT_DIR}/README.md" <<EOF
# Stage 3 Partner Sandbox Evidence Pack

**Generated:** ${STAMP}
**Scope:** partner/reseller staging, synthetic/sandbox data only.
**Production data:** not included.

## Contents

- attribution test report template
- commission ledger test report template
- payout simulation template
- settlement dry-run template
- anti-fraud experiment template
- redacted import manifest template
- partner incident register template
EOF

cat > "${OUTPUT_DIR}/attribution/referral-attribution-test-report.md" <<'EOF'
# Referral Attribution Test Report

| Check | Expected | Actual | Result | Evidence |
|---|---|---|---|---|
| first-touch owner resolution | deterministic owner | pending | pending | |
| last-click override policy | policy-matched owner | pending | pending | |
| no-owner handling | explicit no-owner reason | pending | pending | |
| duplicate touchpoint rejection | bounded rejection reason | pending | pending | |
| cross-realm touchpoint rejection | rejected | pending | pending | |

## Required Evidence

- source touchpoint fixture hash;
- attribution policy version;
- output attribution result hash;
- no-owner and conflict counters.
EOF

cat > "${OUTPUT_DIR}/commission-ledger/commission-ledger-test-report.md" <<'EOF'
# Commission Ledger Test Report

| Check | Expected | Actual | Result | Evidence |
|---|---|---|---|---|
| paid order creates earning event | one earning event | pending | pending | |
| refund creates clawback or adjustment | typed adjustment | pending | pending | |
| chargeback creates dispute-linked adjustment | typed adjustment | pending | pending | |
| statement total equals earning events minus adjustments | exact match | pending | pending | |
| ledger contains no hard-deleted finance rows | true | pending | pending | |

## Required Evidence

- order fixture hash;
- commission policy version;
- ledger export hash;
- mismatch count.
EOF

cat > "${OUTPUT_DIR}/payout-simulation/payout-simulation-report.md" <<'EOF'
# Payout Simulation Report

| Check | Expected | Actual | Result | Evidence |
|---|---|---|---|---|
| payout eligibility computed | deterministic status | pending | pending | |
| payout account masked | no raw destination | pending | pending | |
| maker-checker required where configured | enforced | pending | pending | |
| simulated payout does not call provider | no external call | pending | pending | |
| failure reason is typed | typed reason | pending | pending | |

## Required Evidence

- payout account fixture hash;
- eligibility response hash;
- dry-run output hash;
- provider-call proof.
EOF

cat > "${OUTPUT_DIR}/settlement-dry-run/settlement-dry-run-report.md" <<'EOF'
# Settlement Dry-Run Report

| Check | Expected | Actual | Result | Evidence |
|---|---|---|---|---|
| period close dry-run completes | success | pending | pending | |
| statement generation is idempotent | stable output | pending | pending | |
| reserves/holds applied | policy-matched | pending | pending | |
| adjustments reconcile | zero mismatch | pending | pending | |
| evidence written | complete | pending | pending | |
EOF

cat > "${OUTPUT_DIR}/anti-fraud/anti-fraud-experiment-report.md" <<'EOF'
# Anti-Fraud Experiment Report

| Experiment | Signal | Action | Result | Evidence |
|---|---|---|---|---|
| self-referral detection | same-human indicator | review | pending | |
| duplicate trial farming | repeated device/payment pattern | review/block | pending | |
| partner self-purchase | partner/customer linkage | review/block | pending | |
| synthetic first-payment abuse | abnormal first-payment velocity | review | pending | |
| cross-realm payout abuse | payout identity reuse | freeze/review | pending | |

## Privacy Rule

Experiments must use hashed identifiers and redacted evidence only.
EOF

cat > "${OUTPUT_DIR}/imports/redacted-import-manifest-template.json" <<'EOF'
{
  "source": "pending",
  "redacted_output": "pending",
  "format": "jsonl",
  "records": 0,
  "redaction": "direct identifiers hashed, sensitive fields redacted",
  "approved_for_stage3_sandbox": false
}
EOF

cat > "${OUTPUT_DIR}/incidents/partner-incident-register.md" <<'EOF'
# Partner Incident Register

| Incident ID | Severity | Area | Started | Resolved | Evidence | Owner | Status |
|---|---|---|---|---|---|---|---|
EOF

printf '%s\n' "${OUTPUT_DIR}"
