# Customer Growth Notification Staging Rollout Runbook

**Date:** 2026-04-22  
**Status:** Release-readiness runbook  
**Purpose:** execute the canonical staging validation pass for the repaired customer growth notification delivery and recovery chain before rollout widening or governance approval.

---

## 1. Document Role

This runbook is the operational companion to:

- [customer growth notification delivery runbook](./CUSTOMER_GROWTH_NOTIFICATION_DELIVERY_RUNBOOK.md)
- [customer growth notification GitHub protection handoff](./CUSTOMER_GROWTH_NOTIFICATION_GITHUB_PROTECTION_HANDOFF.md)
- [customer growth codes implementation plan](../InviteRefferalPartnersPromo-codes/2026-04-21-growth-codes-implementation-plan.md)
- [customer growth notification rollout evidence template](../evidence/customer-growth/templates/customer-growth-notification-rollout-evidence-template.md)

Use this runbook when a live staging window must prove:

- a `preference_disabled` delivery can recover after preferences are re-enabled;
- an unresolved delivery can be captured as evidence without silent state drift;
- a customer escalation can be support-resolved and re-armed;
- dashboard and alert proof exists for the rollout window;
- the required CI gate is ready to back release governance.

This runbook does not replace per-environment deploy procedures. It defines the minimum customer-growth rollout loop required before the repaired delivery lifecycle may widen.

---

## 2. Required Inputs

Prepare before the window:

- exact staging API base URL
- disposable staging customer account for growth-notification repair scenarios
- disposable staging admin operator account
- evidence archive path under `docs/evidence/customer-growth/<date>/staging/growth-notification-rollout/`
- latest green CI run of `.github/workflows/customer-growth-notification-conformance.yml`
- rollout ring under validation, normally `R1` or `R2`
- Prometheus base URL if dashboard and alert proof is required from the same shell session

Recommended environment variables:

```bash
export CYBERVPN_API_BASE="https://api.staging.cybervpn.example"
export CYBERVPN_ADMIN_SMOKE_EMAIL="admin-smoke@example.com"
export CYBERVPN_ADMIN_SMOKE_PASSWORD="replace-me"
export CYBERVPN_GROWTH_CUSTOMER_SMOKE_EMAIL="growth-customer-smoke@example.com"
export CYBERVPN_GROWTH_CUSTOMER_SMOKE_PASSWORD="replace-me"
export CYBERVPN_PROMETHEUS_BASE="https://prometheus.staging.cybervpn.example"
export EVIDENCE_DIR="docs/evidence/customer-growth/2026-04-22/staging/growth-notification-rollout/growth-notification-rollout-run01"
```

---

## 3. Preconditions

Do not start the live window if any item below is false.

- [ ] staging deploy for backend, `frontend`, and `admin` is complete
- [ ] latest `Customer Growth Notification Conformance` CI workflow is green
- [ ] committed OpenAPI and generated `frontend/admin/partner` API types are in sync
- [ ] smoke accounts exist and are confirmed disposable
- [ ] evidence directory for this run exists
- [ ] rollback owner and support owner are online for the rollout window
- [ ] dashboard `customer-growth-notification-delivery` is reachable
- [ ] no unrelated high-risk rollout is sharing the same window

---

## 4. CI Gate Verification

Start with the standalone conformance gate:

```bash
npm run conformance:customer-growth-notifications
```

If the evidence pack for this exact run is not initialized yet:

```bash
npm run evidence:customer-growth-notifications:init -- 2026-04-22 staging growth-notification-rollout-run01 R2 "customer growth ops"
```

Minimum archived evidence from this checkpoint:

- workflow URL or local transcript
- backend growth-notification conformance result
- `frontend` build result
- `admin` build result
- proof that regenerated OpenAPI and generated client types stayed in sync

If this checkpoint fails, stop the window. Do not move to staging-host validation.

---

## 5. Staging Runtime Validation

Run the canonical staging smoke:

```bash
npm run staging:customer-growth-notifications:smoke
```

This smoke captures:

- `GCN-REPAIR-001` preference-disabled email delivery followed by automatic recovery after preferences are re-enabled
- unresolved paused delivery evidence for a live customer-facing notification
- guided customer support escalation
- `GCN-REPAIR-004` admin `support_resolved` recovery plus customer-visible closure notice
- optional Prometheus proof for recovery ratio and unresolved backlog delta

Required evidence artifacts from the smoke:

- customer login and admin login traces
- customer preferences before and after repair
- recovered delivery detail and export for `GCN-REPAIR-001`
- unresolved delivery export snapshot
- support escalation trace
- support-resolved delivery detail and export for `GCN-REPAIR-004`
- customer feed proof for the closure notification after support resolution

---

## 6. Monitoring Proof

When Prometheus is available to the operator shell, capture at least:

```bash
curl -s "${CYBERVPN_PROMETHEUS_BASE%/}/api/v1/query" --get --data-urlencode 'query=sum(customer_growth:notification_unresolved_backlog_delta:24h)'
curl -s "${CYBERVPN_PROMETHEUS_BASE%/}/api/v1/query" --get --data-urlencode 'query=avg(customer_growth:notification_recovery_ratio:24h)'
curl -s "${CYBERVPN_PROMETHEUS_BASE%/}/api/v1/query" --get --data-urlencode 'query=sum(customer_growth:notification_support_resolutions:increase24h)'
```

Archive:

- unresolved backlog delta proof
- recovery ratio proof
- support resolution proof
- dashboard screenshots for the same window when available

If Prometheus access is unavailable from the shell but Grafana is available, capture screenshots manually and keep the query/API gap in the divergence register.

---

## 7. Exit Criteria

The staging run is `pass` only if all conditions below are true:

- customer-growth notification CI conformance gate is green
- `GCN-REPAIR-001` shows a repaired delivery with `repair_completed` and `delivery_recovered`
- at least one unresolved delivery snapshot is preserved before operator resolution
- `GCN-REPAIR-004` shows `support_resolved` and a re-armed delivery
- customer-visible closure notification exists after support resolution
- unresolved backlog and recovery ratio remain within the active rollout thresholds
- no unresolved blocker remains in the divergence register

If any critical step fails:

1. stop widening immediately
2. preserve exports, logs, and screenshots
3. classify the run as `hold` or `rollback`
4. attach exact failing scenario IDs to the evidence pack

---

## 8. Governance Gate

The protected-merge companion for this rollout is:

- workflow: `.github/workflows/customer-growth-notification-conformance.yml`
- required check: `All Customer Growth Notification Checks Passed`

Repo-managed governance assets:

- `.github/rulesets/customer-growth-notification-main-gate.disabled.json`
- `scripts/sync-customer-growth-notification-ruleset.sh`
- `docs/runbooks/CUSTOMER_GROWTH_NOTIFICATION_GITHUB_PROTECTION_HANDOFF.md`

Use the handoff document before enabling the ruleset in GitHub.

---

## 9. Required Evidence Manifest

Attach the following to the run record:

- CI run URL for `.github/workflows/customer-growth-notification-conformance.yml`
- command transcript for `npm run conformance:customer-growth-notifications`
- command transcript for `npm run staging:customer-growth-notifications:smoke`
- recovered delivery export for `GCN-REPAIR-001`
- unresolved delivery export
- support-resolved delivery export for `GCN-REPAIR-004`
- customer support escalation proof
- customer closure-notification proof
- monitoring proof or explicit monitoring-access exception
- divergence register
- final rollout decision block with named owner
