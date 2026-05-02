# Customer Growth Reporting Governance Staging Rollout Runbook

**Date:** 2026-04-22  
**Status:** Release-readiness runbook  
**Purpose:** execute the canonical staging validation pass for customer growth reporting governance before protected-gate activation or merge-governance widening.

---

## 1. Document Role

This runbook is the operational companion to:

- [customer growth reporting runbook](./CUSTOMER_GROWTH_REPORTING_RUNBOOK.md)
- [customer growth reporting governance GitHub protection handoff](./CUSTOMER_GROWTH_REPORTING_GOVERNANCE_GITHUB_PROTECTION_HANDOFF.md)
- `.github/workflows/customer-growth-reporting-governance-staging-smoke.yml`
- [customer growth codes implementation plan](../InviteRefferalPartnersPromo-codes/2026-04-21-growth-codes-implementation-plan.md)
- [customer growth reporting governance evidence template](../evidence/customer-growth/templates/customer-growth-reporting-governance-evidence-template.md)

Use this runbook when a live staging window must prove:

- a `delivery_suppressed` reporting subscription is visible in governance coverage and recent decisions;
- a `recipient_domain_blocked` reporting subscription is visible in governance coverage and recent decisions;
- governance export is downloadable and stable for evidence capture;
- governance audit events explain the policy state that created the coverage gap;
- the required CI gate is ready before protected-gate activation.

This runbook does not replace per-environment deploy procedures. It defines the minimum governance rollout loop required before growth reporting governance can become a protected merge gate.

---

## 2. Required Inputs

Prepare before the window:

- exact staging API base URL
- disposable staging admin operator account
- backend internal secret for reporting-delivery claim and completion path
- evidence archive path under `docs/evidence/customer-growth/<date>/staging/growth-reporting-governance/`
- latest green CI run of `.github/workflows/customer-growth-reporting-governance-conformance.yml`
- rollout ring under validation, normally `R1` or `R2`
- Prometheus base URL if governance metrics proof is required from the same shell session

Recommended environment variables:

```bash
export CYBERVPN_API_BASE="https://api.staging.cybervpn.example"
export CYBERVPN_ADMIN_SMOKE_EMAIL="admin-smoke@example.com"
export CYBERVPN_ADMIN_SMOKE_PASSWORD="replace-me"
export CYBERVPN_GROWTH_REPORTING_INTERNAL_SECRET="replace-me"
export CYBERVPN_GROWTH_REPORTING_ALLOWED_DOMAIN="example.com"
export CYBERVPN_PROMETHEUS_BASE="https://prometheus.staging.cybervpn.example"
export EVIDENCE_DIR="docs/evidence/customer-growth/2026-04-22/staging/growth-reporting-governance/growth-reporting-governance-run01"
```

---

## 3. Preconditions

Do not start the live window if any item below is false.

- [ ] staging deploy for backend and `admin` is complete
- [ ] latest `Customer Growth Reporting Governance Conformance` CI workflow is green
- [ ] committed OpenAPI and generated `admin/frontend/partner` API types are in sync
- [ ] smoke admin account is confirmed disposable for reporting subscriptions
- [ ] evidence directory for this run exists
- [ ] rollback owner and governance owner are online for the rollout window
- [ ] governance metrics are reachable from Prometheus or a monitoring exception is pre-approved
- [ ] no unrelated high-risk rollout is sharing the same window

---

## 4. CI Gate Verification

Start with the standalone conformance gate:

```bash
npm run conformance:customer-growth-reporting-governance
```

If the evidence pack for this exact run is not initialized yet:

```bash
npm run evidence:customer-growth-reporting-governance:init -- 2026-04-22 staging growth-reporting-governance-run01 R2 "growth governance ops"
```

Minimum archived evidence from this checkpoint:

- workflow URL or local transcript
- backend governance contract and integration results
- `admin` build result
- asset validation result
- proof that regenerated OpenAPI and generated client types stayed in sync

If this checkpoint fails, stop the window. Do not move to staging-host validation.

---

## 5. Staging Runtime Validation

Run the canonical staging smoke:

```bash
npm run staging:customer-growth-reporting-governance:smoke
```

Or run the managed GitHub workflow:

- workflow: `Customer Growth Reporting Governance Staging Smoke`
- file: `.github/workflows/customer-growth-reporting-governance-staging-smoke.yml`

This smoke captures:

- `GRG-001` a `delivery_suppressed` subscription generated from a future suppression window
- `GRG-002` a `recipient_domain_blocked` subscription generated from allowlist mismatch
- a healthy subscription path so claim and completion flow are not falsely green only through skipped decisions
- `GRG-003` governance overview and governance export artifacts
- `GRG-004` governance audit trail and delivery ledger proof
- optional Prometheus proof for governance gap and recipient-domain-blocked metrics
- automatic gate-readiness recommendation in `approvals/gate-readiness.{md,json}`

Required evidence artifacts from the smoke:

- admin login trace
- refresh transcript
- subscription creation traces for suppressed, healthy, and blocked recipients
- delivery claim trace
- governance overview JSON
- governance export JSON
- recent deliveries JSON
- optional Prometheus metric proof
- gate-readiness recommendation artifacts
- cleanup trace showing smoke subscriptions paused after capture

---

## 6. Monitoring Proof

When Prometheus is available to the operator shell, capture at least:

```bash
curl -s "${CYBERVPN_PROMETHEUS_BASE%/}/api/v1/query" --get --data-urlencode 'query=customer_growth:reporting_governance_gap_subscriptions'
curl -s "${CYBERVPN_PROMETHEUS_BASE%/}/api/v1/query" --get --data-urlencode 'query=customer_growth:reporting_recipient_domain_blocked_subscriptions'
```

Archive:

- governance gap metric proof
- recipient-domain-blocked metric proof
- screenshots for the governance dashboard or admin surface when available

If Prometheus access is unavailable from the shell but Grafana or admin is available, capture screenshots manually and keep the monitoring gap in the divergence register.

---

## 7. Exit Criteria

The staging run is `pass` only if all conditions below are true:

- customer-growth reporting governance CI conformance gate is green
- `GRG-001` shows `delivery_suppressed` in governance coverage and recent decisions
- `GRG-002` shows `recipient_domain_blocked` in governance coverage and recent decisions
- `GRG-003` captures a valid governance export with subscription payload
- `GRG-004` shows audit evidence explaining the current policy posture
- governance gap metrics are queryable or a monitoring exception is recorded
- no unresolved blocker remains in the divergence register

If any critical step fails:

1. stop gate-activation work immediately
2. preserve exports, logs, and screenshots
3. classify the run as `hold` or `rollback`
4. attach exact failing scenario IDs to the evidence pack

After smoke completion, review:

- `./approvals/gate-readiness.md`
- `./approvals/gate-readiness.json`

The recommendation may be `enable` only if:

- `delivery_suppressed` and `recipient_domain_blocked` are both proven
- healthy delivery claim and completion are proven
- governance export and audit evidence are present
- monitoring proof is attached or explicitly waived

---

## 8. Governance Gate

The protected-merge companion for this rollout is:

- workflow: `.github/workflows/customer-growth-reporting-governance-conformance.yml`
- required check: `All Customer Growth Reporting Governance Checks Passed`

Repo-managed governance assets:

- `.github/rulesets/customer-growth-reporting-governance-main-gate.disabled.json`
- `scripts/sync-customer-growth-reporting-governance-ruleset.sh`
- `docs/runbooks/CUSTOMER_GROWTH_REPORTING_GOVERNANCE_GITHUB_PROTECTION_HANDOFF.md`

Use the handoff document before creating or enabling the ruleset in GitHub.

Repo-side helper for post-run decisioning:

```bash
npm run staging:customer-growth-reporting-governance:assess -- "$EVIDENCE_DIR"
```

---

## 9. Required Evidence Manifest

Attach the following to the run record:

- CI run URL for `.github/workflows/customer-growth-reporting-governance-conformance.yml`
- command transcript for `npm run conformance:customer-growth-reporting-governance`
- command transcript for `npm run staging:customer-growth-reporting-governance:smoke`
- governance overview export for `GRG-003`
- governance overview JSON showing `delivery_suppressed` and `recipient_domain_blocked`
- recent deliveries JSON with governance decisions
- audit evidence JSON for policy changes
- monitoring proof or explicit monitoring-access exception
- cleanup trace
- final rollout decision block with named owner
- gate-readiness recommendation artifacts
