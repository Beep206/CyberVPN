# CyberVPN Partner Portal And Admin Portal E2E Conformance Test Plan

**Date:** 2026-04-20  
**Status:** Integration closure test plan  
**Purpose:** define the end-to-end scenarios that prove partner portal, admin portal, auth realm logic, and backend source-of-truth all work together correctly.

---

## 1. Document Role

This is the final safety-net document for partner platform integration closure.

It turns the product, contract, and integration specs into executable validation scenarios.

It is not a generic QA checklist. It is the conformance plan for:

- partner lifecycle
- admin operational control
- realm and session isolation
- cross-surface synchronization

---

## 2. Test Principles

1. Every critical lifecycle step must be verified through real UI/API integration.
2. Negative paths are mandatory.
3. Admin and partner surfaces must be tested together, not separately only.
4. Status changes must reconcile across partner portal, admin portal, and backend APIs.
5. Audit and permission behavior are part of the acceptance scope.

---

## 3. Test Environments

Conformance must run at minimum in:

- local integrated environment
- pre-production/staging environment

Production-readiness signoff requires:

- staging pass with real host-to-realm mapping
- stable test data strategy
- representative partner workspace fixtures

---

## 4. Partner Lifecycle E2E Scenarios

## 4.1 Happy Path Lifecycle

Scenario ID: `E2E-PARTNER-001`

1. Applicant opens partner host.
2. Applicant registers in partner realm.
3. Applicant verifies email.
4. Applicant logs in and receives partner bootstrap payload.
5. Applicant creates or resumes application draft.
6. Applicant fills organization profile and lane data.
7. Applicant submits application.
8. Admin sees submitted application in review queue.
9. Admin requests more info.
10. Applicant sees `needs_info` in partner portal.
11. Applicant uploads requested evidence and responds.
12. Admin approves workspace to probation.
13. Partner sees limited portal with `approved_probation`.
14. Partner accepts required legal documents.
15. Partner creates payout account.
16. Partner submits traffic declaration.
17. Admin approves traffic declaration.
18. Partner receives or creates code according to lane policy.
19. Conversion record appears.
20. Explainability detail is visible.
21. Earning enters hold/statement pipeline.
22. Statement closes and becomes visible.
23. Payout eligibility becomes visible.
24. Admin approves payout through maker-checker flow.
25. Partner sees payout executed.

---

## 5. Negative Partner Scenarios

Required negative cases:

- `E2E-AUTH-001` partner tries admin route
- `E2E-AUTH-002` customer token tries partner route
- `E2E-AUTH-003` admin token tries partner portal
- `E2E-PERM-001` suspended partner tries create code
- `E2E-FIN-001` partner without legal acceptance tries payout action
- `E2E-FIN-002` partner without verified payout account tries payout action
- `E2E-COMP-001` unapproved performance lane tries traffic expansion
- `E2E-GOV-001` blocked governance state hides or disables restricted actions
- `E2E-COMM-001` referral credit does not appear as partner payout
- `E2E-COMM-002` non-withdrawable wallet behavior does not bootstrap partner commission

Each negative scenario must define:

- expected API response
- expected UI behavior
- expected audit or event side effect if applicable

---

## 6. Admin E2E Scenarios

Required admin flows:

1. `E2E-ADMIN-001` application review
2. `E2E-ADMIN-002` request info
3. `E2E-ADMIN-003` approve to probation
4. `E2E-ADMIN-004` waitlist
5. `E2E-ADMIN-005` reject
6. `E2E-ADMIN-006` lane approval
7. `E2E-ADMIN-007` code suspension
8. `E2E-ADMIN-008` traffic declaration review
9. `E2E-ADMIN-009` creative rejection
10. `E2E-ADMIN-010` payout account verification
11. `E2E-ADMIN-011` payout maker-checker approval
12. `E2E-ADMIN-012` risk review open and resolve
13. `E2E-ADMIN-013` governance action apply and release
14. `E2E-ADMIN-014` dispute or case workflow

---

## 7. Cross-Surface Conformance Scenarios

The following scenarios must explicitly verify partner and admin synchronization:

| Cross-Surface Scenario | Expected Result |
|---|---|
| admin requests more info | partner sees `needs_info` and linked task |
| partner uploads evidence | admin sees attachment in review detail |
| admin approves lane | partner `/programs` reflects new lane state |
| admin suspends code | partner `/codes` reflects restriction and reason |
| admin freezes payout | partner `/finance` shows blocked payout reason |
| admin rejects creative | partner `/campaigns` or `/compliance` reflects rejection notes |
| partner replies in case | admin case view shows thread event |
| notification generated after admin action | partner `/notifications` counter increments and links correctly |
| backend reporting update | partner analytics and finance views reconcile to new truth |

---

## 8. Auth And Realm Conformance Scenarios

Mandatory:

1. `E2E-AUTH-010` partner token works on partner host only
2. `E2E-AUTH-011` admin token fails on partner host
3. `E2E-AUTH-012` customer token fails on partner host
4. `E2E-AUTH-013` partner cookie is not reused by customer host
5. `E2E-AUTH-014` partner cookie is not reused by admin host
6. `E2E-AUTH-015` same email across realms does not cross-authenticate
7. `E2E-AUTH-016` revoked partner session stops bootstrap and workspace API access

---

## 9. Permission Conformance Scenarios

Required role-based tests:

- `E2E-PERM-010` workspace owner can perform all partner-safe actions
- `E2E-PERM-011` finance manager can manage finance but not traffic/compliance overrides
- `E2E-PERM-012` analyst can read reports but not mutate sensitive workspace state
- `E2E-PERM-013` traffic manager can submit traffic declarations but not change payout account
- `E2E-PERM-014` support manager can interact with cases but not manage legal acceptance
- `E2E-PERM-015` lack of permission key blocks API even if route is manually opened

---

## 10. Production-Readiness Gates

The following gates must pass before broad activation:

- auth and realm separation tests
- bootstrap payload correctness tests
- API contract tests
- workspace permission tests
- partner lifecycle happy path E2E
- negative path E2E
- admin action to partner-portal state propagation tests
- audit log verification tests
- performance smoke on partner host
- regression on admin/customer isolation

---

## 11. Evidence Requirements

Each executed scenario should capture:

- scenario id
- environment
- actor identities used
- relevant workspace id
- API traces or screenshots
- audit evidence where relevant
- pass/fail result
- defect id if failed

---

## 12. Closure Conditions

This plan is complete only when:

1. QA can execute without asking what the expected behavior is;
2. all critical lifecycle, auth, permission, and admin/partner sync paths are covered;
3. production-readiness gates are explicit and measurable.
