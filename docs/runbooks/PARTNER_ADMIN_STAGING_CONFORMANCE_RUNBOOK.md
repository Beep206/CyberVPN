# Partner/Admin Staging Conformance Runbook

**Date:** 2026-04-20  
**Status:** Release-readiness runbook  
**Purpose:** execute the canonical staging validation pass for the partner portal, admin portal, and backend conformance layer before partner rollout widening or cutover approval.

---

## 1. Document Role

This runbook is the operational companion to:

- [partner/admin e2e conformance test plan](../plans/2026-04-20-partner-admin-e2e-conformance-test-plan.md)
- [partner portal backend integration closure spec](../plans/2026-04-20-partner-portal-backend-integration-closure-spec.md)
- [partner realm/session/auth/access verification spec](../plans/2026-04-20-partner-realm-session-auth-access-verification-spec.md)
- [environment-specific cutover runbooks](../plans/2026-04-17-partner-platform-environment-specific-cutover-runbooks.md)
- [rehearsal logs and evidence archive template](../plans/2026-04-17-partner-platform-rehearsal-logs-and-evidence-archive-template.md)

Use this runbook for staging validation of the integrated `partner + admin + backend` stack after the `WB-INT-10` conformance pack is green.

This runbook does not replace per-service deployment procedures. It defines the minimum partner/admin validation loop required before a staging window may be marked ready.

---

## 2. Required Inputs

Before starting the window, prepare:

- staging `partner`, `admin`, and customer-facing hosts
- disposable staging accounts for:
  - partner applicant
  - partner finance operator
  - partner traffic manager
  - admin operator
- exact staging API base URL
- evidence archive path under `docs/evidence/partner-platform/<date>/staging/partner-admin-conformance/`
- latest green CI run of `.github/workflows/partner-admin-conformance.yml`
- exact release ring under validation, normally `R1` or `R2`

Recommended environment variables for shell-driven checks:

```bash
export CYBERVPN_API_BASE="https://api.staging.cybervpn.example"
export CYBERVPN_PARTNER_HOST="https://partners.staging.cybervpn.example"
export CYBERVPN_ADMIN_HOST="https://admin.staging.cybervpn.example"
export CYBERVPN_PARTNER_SMOKE_EMAIL="partner-smoke@example.com"
export CYBERVPN_PARTNER_SMOKE_PASSWORD="replace-me"
export CYBERVPN_ADMIN_SMOKE_EMAIL="admin-smoke@example.com"
export CYBERVPN_ADMIN_SMOKE_PASSWORD="replace-me"
```

---

## 3. Preconditions

Do not start the run if any item below is false.

- [ ] staging deploy for backend, `partner`, and `admin` is complete
- [ ] latest `Partner Admin Conformance` CI workflow is green
- [ ] committed OpenAPI and generated admin/partner types are in sync
- [ ] smoke accounts exist and are confirmed disposable
- [ ] rollback owner is named and online
- [ ] evidence directory for this run exists
- [ ] no unrelated high-risk staging rollout is sharing the same window

---

## 4. CI Gate Verification

Use the standalone conformance gate as the first checkpoint.

From the repository root:

```bash
npm run conformance:partner-admin
```

If you need to initialize the evidence archive for the exact run before starting:

```bash
npm run evidence:partner-admin:init -- 2026-04-20 staging partner-admin-conformance-run01 R2 "partner ops"
```

Minimum evidence to archive:

- workflow URL or local transcript
- `backend` partner/admin conformance pack result
- `admin` build result
- `partner` build result
- proof that regenerated OpenAPI and generated client types did not introduce drift

If this step fails, stop the window. Do not move to staging-host validation.

---

## 5. Staging Runtime Validation Steps

### 5.1 Realm And Host Isolation

Verify the staging hosts resolve to the correct realm behavior.

Required checks:

1. Login on the partner host yields a `partner` session.
2. Partner session can access `GET /api/v1/partner-session/bootstrap`.
3. Admin session cannot use the partner bootstrap route.
4. Partner session cannot use admin-only routes.
5. `logout-all` revokes the current partner access session.

Operator shortcut for the auth/realm smoke:

```bash
export CYBERVPN_API_BASE="https://api.staging.cybervpn.example"
export CYBERVPN_PARTNER_SMOKE_EMAIL="partner-smoke@example.com"
export CYBERVPN_PARTNER_SMOKE_PASSWORD="replace-me"
export CYBERVPN_ADMIN_SMOKE_EMAIL="admin-smoke@example.com"
export CYBERVPN_ADMIN_SMOKE_PASSWORD="replace-me"
export CYBERVPN_PARTNER_WORKSPACE_ID="<workspace-id-if-required>"
export CYBERVPN_ENABLE_LOGOUT_ALL_CHECK=true
export EVIDENCE_DIR="docs/evidence/partner-platform/2026-04-20/staging/partner-admin-conformance/partner-admin-conformance-run01"

npm run staging:partner-admin:smoke
```

Record:

- request/response traces for partner login and bootstrap
- negative response for wrong-host or wrong-realm usage
- post-revocation proof that bootstrap is rejected

### 5.2 Lifecycle Scenario Validation

Run the canonical staging lifecycle against disposable accounts. Use the scenario IDs from the e2e conformance plan:

- `E2E-PARTNER-001` applicant lifecycle: `draft -> submitted -> needs_info -> resubmit -> approved_probation`
- `E2E-PERM-010` role and permission split: `owner / finance / traffic_manager`
- `E2E-AUTH-010` partner realm isolation and revocation

For `E2E-PARTNER-001` collect:

- application draft creation proof
- submit proof
- admin `needs_info` action proof
- partner notification or review request proof
- attachment upload proof
- resubmit proof
- admin approve-to-probation proof
- partner bootstrap/status proof after approval
- legal acceptance proof

For `E2E-PERM-010` collect:

- finance-only payout action proof
- traffic-only declaration action proof
- blocked action proof for the wrong role
- admin verification result reflected back in partner UI or API

For `E2E-AUTH-010` collect:

- negative auth response when using wrong token on wrong host
- post-logout-all rejection trace

### 5.3 Partner/Admin Sync Validation

Validate cross-surface propagation:

1. Admin review action produces partner-visible notification or task.
2. Partner upload/response becomes admin-visible review evidence.
3. Admin payout review updates partner finance state.
4. Admin governance or restriction change updates partner bootstrap blocked reasons.

Archive one proof item for each propagation path.

---

## 6. Exit Criteria

The staging run is `pass` only if all conditions below are true:

- partner/admin CI conformance gate is green
- all three scenario families complete without manual DB repair
- partner bootstrap reflects backend truth after admin actions
- notification counters and partner-visible tasks update deterministically
- auth realm isolation is proven with at least one negative test
- no unresolved blocker remains in the divergence register

If any critical step fails:

1. stop widening immediately
2. preserve traces and screenshots
3. classify the run as `hold` or `rollback`
4. open a follow-up item with exact scenario ID and failing step

---

## 7. Required Evidence Manifest

Attach the following to the run record:

- CI run URL for `.github/workflows/partner-admin-conformance.yml`
- command transcript for `npm run conformance:partner-admin`
- partner bootstrap JSON snapshot
- admin review action traces
- partner notification feed traces
- role-split permission traces
- legal acceptance proof
- payout verification sync proof
- divergence register
- final decision block with named owner

Use the template at [partner-admin-conformance-evidence-template.md](../evidence/partner-platform/templates/partner-admin-conformance-evidence-template.md).
