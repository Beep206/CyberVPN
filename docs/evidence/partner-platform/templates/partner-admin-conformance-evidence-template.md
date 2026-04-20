# Partner/Admin Conformance Evidence Template

**Template Date:** 2026-04-20  
**Use for:** staging or pre-cutover conformance windows validating the integrated `partner + admin + backend` stack.

---

## 1. Run Metadata

```md
# Partner/Admin Conformance Evidence

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

- [ ] partner/admin conformance CI workflow green
- [ ] committed OpenAPI spec in sync
- [ ] committed admin generated API types in sync
- [ ] committed partner generated API types in sync
- [ ] staging smoke accounts prepared
- [ ] rollback owner online
- [ ] evidence directory created
```

---

## 3. Scenario Matrix

```md
## Scenario Matrix

| Scenario ID | Description | Status | Evidence Link | Notes |
|---|---|---|---|---|
| E2E-PARTNER-001 | applicant draft -> submit -> needs_info -> resubmit -> approved_probation | pass | ./api/e2e-partner-001/ | |
| E2E-PERM-010 | owner / finance / traffic_manager permission split | pass | ./api/e2e-perm-010/ | |
| E2E-AUTH-010 | partner realm isolation and logout-all revocation | pass | ./api/e2e-auth-010/ | |
```

Add more scenario IDs if the run includes extra negative or cutover-specific checks.

---

## 4. CI Gate Evidence

```md
## CI Gate Evidence

| Check | Result | Evidence Link |
|---|---|---|
| backend conformance pack | pass | <ci-log-or-local-transcript> |
| admin surface readiness | pass | <ci-log-or-local-transcript> |
| partner surface readiness | pass | <ci-log-or-local-transcript> |
```

---

## 5. Auth And Realm Proof

```md
## Auth And Realm Proof

| Check | Result | Evidence Link | Notes |
|---|---|---|---|
| partner login returns partner realm session | pass | ./api/auth/partner-login.json | |
| partner bootstrap works with partner session | pass | ./api/auth/partner-bootstrap.json | |
| admin token rejected on partner bootstrap | pass | ./api/auth/admin-on-partner-bootstrap.json | |
| partner token rejected on admin surface | pass | ./api/auth/partner-on-admin.json | |
| logout-all revokes current partner access session | pass | ./api/auth/logout-all-revocation.json | |
```

---

## 6. Admin To Partner Sync Proof

```md
## Admin To Partner Sync Proof

| Admin Action | Partner Effect | Result | Evidence Link |
|---|---|---|---|
| request more info | partner sees needs_info task or notification | pass | ./api/sync/request-info/ |
| approve to probation | bootstrap status becomes approved_probation | pass | ./api/sync/approve-probation/ |
| verify payout account | finance surface reflects verified state | pass | ./api/sync/payout-verification/ |
| governance restriction applied | bootstrap blocked reasons update | pass | ./api/sync/governance/ |
```

---

## 7. Role And Permission Proof

```md
## Role And Permission Proof

| Principal | Allowed Action | Result | Evidence Link |
|---|---|---|---|
| finance | create payout account | pass | ./api/permissions/finance-create-payout.json |
| finance | submit traffic declaration | blocked | ./api/permissions/finance-traffic-blocked.json |
| traffic_manager | submit traffic declaration | pass | ./api/permissions/traffic-submit.json |
| traffic_manager | create payout account | blocked | ./api/permissions/traffic-payout-blocked.json |
```

---

## 8. Divergence Register

```md
## Divergence Register

| ID | Category | Description | Severity | Owner | Blocking | Disposition |
|---|---|---|---|---|---|---|
| D-01 | auth | example only | low | platform | no | accepted for follow-up |
```

Remove placeholder rows if the run is clean.

---

## 9. Final Decision

```md
## Final Decision

**Decision:** <approve|hold|rollback|re-run>
**Decision Owner:** <name/role>
**Timestamp:** <ISO-8601>
**Summary:** <short conclusion>
```

---

## 10. Archive Manifest

Recommended structure:

```text
docs/evidence/partner-platform/<YYYY-MM-DD>/<environment>/partner-admin-conformance/
  README.md
  api/
  screenshots/
  logs/
  approvals/
```

Recommended file naming:

```text
<YYYY-MM-DD>_<environment>_partner-admin-conformance_<scenario-id>_<artifact-type>
```
