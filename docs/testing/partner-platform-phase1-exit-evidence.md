# CyberVPN Partner Platform Phase 1 Exit Evidence

**Date:** 2026-04-18  
**Status:** Phase 1 gate evidence pack  
**Purpose:** define the canonical automated evidence, generated-contract evidence, and sign-off checklist required to declare `Phase 1` complete.

---

## 1. Gate Role

This document is the concrete exit-evidence companion to:

- [../plans/2026-04-17-partner-platform-detailed-phased-implementation-plan.md](../plans/2026-04-17-partner-platform-detailed-phased-implementation-plan.md)
- [../plans/2026-04-17-partner-platform-operational-readiness-package.md](../plans/2026-04-17-partner-platform-operational-readiness-package.md)
- [partner-platform-phase-0-and-phase-1-validation-pack.md](partner-platform-phase-0-and-phase-1-validation-pack.md)

It converts the generic validation baseline into a named `Phase 1` closure package.

This pack is complete only when:

1. required backend tests pass;
2. the committed OpenAPI export includes the `Phase 1` surface;
3. generated admin and frontend clients validate against the same frozen contracts;
4. named owners sign off or explicitly record residual non-blocking gaps.

Current execution status for the 2026-04-18 closure run:

- backend `Phase 1` verification pack passed with `16 passed`;
- admin gate-adjacent API regression pack passed with `127 passed`;
- frontend generated-contract validation passed with `2 passed`;
- targeted admin/frontend lint and generated-type compile checks passed.

---

## 2. Canonical Phase 1 Evidence Scope

`Phase 1` exit evidence must prove all of the following:

- realm isolation exists and is observable through real request resolution;
- storefront host resolution works for official and partner surfaces;
- partner workspace roles and scope enforcement are real server behavior;
- legal acceptance evidence captures storefront, realm, principal, and channel context;
- early risk-subject linkage works without collapsing realm separation;
- the `Phase 1` API surface is exported and consumable by generated clients.

Important clarification:

- standalone storefront CRUD is not a `Phase 1` gate requirement;
- the frozen `Phase 1` storefront contract is satisfied by host-based realm resolution and storefront-bound resolve surfaces such as legal-document-set resolution and pricebook resolution.

---

## 3. Required Automated Evidence

## 3.1 Backend Gate Tests

The canonical backend gate command is:

```bash
REMNAWAVE_TOKEN=test-remnawave-token \
JWT_SECRET=0123456789abcdef0123456789abcdef \
CRYPTOBOT_TOKEN=test-cryptobot-token \
SKIP_TEST_DB_BOOTSTRAP=1 \
backend/.venv/bin/pytest --no-cov \
  backend/tests/security/test_auth_realm_isolation.py \
  backend/tests/integration/test_auth_realm_sessions.py \
  backend/tests/integration/test_partner_workspace_membership.py \
  backend/tests/security/test_partner_scope_enforcement.py \
  backend/tests/integration/test_legal_document_acceptance.py \
  backend/tests/security/test_policy_actor_attribution.py \
  backend/tests/security/test_risk_subject_linkage.py \
  backend/tests/security/test_same_email_multi_realm_abuse_guards.py \
  backend/tests/integration/test_phase1_eligibility_guards.py \
  backend/tests/e2e/test_phase1_foundations.py \
  backend/tests/contract/test_phase1_api_surface_contract.py \
  backend/tests/contract/test_partner_platform_api_conventions.py \
  -q
```

Expected result:

- all tests pass;
- no skipped tests are accepted without a written explanation;
- failures block `Phase 1` closure.

## 3.2 Lint And Contract Hygiene

The canonical backend lint command is:

```bash
backend/.venv/bin/ruff check \
  backend/src/presentation/api/v1/router.py \
  backend/tests/contract/test_partner_platform_api_conventions.py \
  backend/tests/contract/test_phase1_api_surface_contract.py \
  backend/tests/e2e/test_phase1_foundations.py \
  backend/tests/factories.py \
  backend/tests/integration/conftest.py
```

The canonical OpenAPI export command is:

```bash
REMNAWAVE_TOKEN=test-remnawave-token \
JWT_SECRET=0123456789abcdef0123456789abcdef \
CRYPTOBOT_TOKEN=test-cryptobot-token \
backend/.venv/bin/python backend/scripts/export_openapi.py
```

The exported file `backend/docs/api/openapi.json` must be the source used by generated clients.

## 3.3 Generated Client Validation

Admin generated-client validation:

```bash
npm run generate:api-types -w admin
npm run test:run -w admin -- src/lib/api/__tests__/phase1-generated-contract.test.ts
```

Admin gate-adjacent regression validation:

```bash
npm run test:run -w admin -- \
  src/lib/api/__tests__/auth.test.ts \
  src/lib/api/__tests__/security.test.ts \
  src/lib/api/__tests__/customers-admin.test.ts \
  src/lib/api/__tests__/subscriptions.test.ts \
  src/lib/api/__tests__/phase1-generated-contract.test.ts
```

Frontend generated-client validation:

```bash
npm run generate:api-types -w frontend
npm run test:run -w frontend -- src/lib/api/__tests__/phase1-generated-contract.test.ts
```

If a future unrelated workspace runner issue blocks the frontend test process, a temporary substitute may be attached:

```bash
npx tsc --noEmit --pretty false --module esnext --moduleResolution bundler \
  --target ES2022 --lib ES2022,DOM --types vitest/globals \
  src/lib/api/generated/types.ts \
  src/lib/api/__tests__/phase1-generated-contract.test.ts
```

The substitute is acceptable only when:

- the failure is clearly outside the touched `Phase 1` API contract surface;
- the blocking issue is linked in the divergence register;
- the TypeScript compile check for generated types passes.

For the 2026-04-18 closure run this substitute was not needed. The canonical frontend vitest contract test passed directly under node environment.

---

## 4. Required Artifact Set

The following artifacts must be attached to the evidence archive:

| Artifact | Source | Mandatory |
|---|---|---|
| backend gate test output | pytest command transcript | yes |
| backend lint output | ruff transcript | yes |
| committed OpenAPI export diff | `backend/docs/api/openapi.json` | yes |
| admin gate-adjacent regression output | auth/security/customers/subscriptions plus generated-contract vitest transcript | yes |
| admin generated-client output | generator plus test transcript | yes |
| frontend generated-client output | generator plus test or compile transcript | yes |
| divergence register | issue list for non-blocking residuals | yes |
| sign-off block | named approvers | yes |

Recommended archive location:

```text
docs/evidence/partner-platform/<YYYY-MM-DD>/phase1-gate/
```

---

## 5. Acceptance Mapping

The `Phase 1` completion gate is considered satisfied only when the evidence maps to the frozen requirements below.

| Requirement | Evidence source |
|---|---|
| same-email different-realm registration or identity separation works | `test_auth_realm_isolation.py`, `test_same_email_multi_realm_abuse_guards.py` |
| cross-login across realms is blocked | `test_auth_realm_isolation.py`, `test_auth_realm_sessions.py` |
| partner workspace RBAC is enforced | `test_partner_workspace_membership.py`, `test_partner_scope_enforcement.py`, `test_phase1_foundations.py` |
| legal acceptance evidence is captured correctly | `test_legal_document_acceptance.py`, `test_phase1_foundations.py` |
| risk-subject linkage works without collapsing realm isolation | `test_risk_subject_linkage.py`, `test_same_email_multi_realm_abuse_guards.py`, `test_phase1_foundations.py` |
| `Phase 1` API surface is exported and frozen | `test_phase1_api_surface_contract.py`, committed `openapi.json`, generated-client validation |

## 5.1 Closure Run Record

The closure run attached to this document produced the following results:

| Evidence item | Result |
|---|---|
| backend `Phase 1` verification pack | `16 passed in 16.22s` |
| admin gate-adjacent regression pack | `127 passed` |
| frontend generated-contract validation | `2 passed` |
| admin targeted eslint | passed |
| frontend targeted eslint | passed |
| admin generated-type compile check | passed |
| frontend generated-type compile check | passed |

---

## 6. Divergence Policy

Allowed non-blocking residuals:

- minor documentation wording mismatches;
- optional admin/frontend wrappers not yet built on top of already frozen paths.

Recorded non-blocking residuals for this closure run:

- at the time of the original closure run, repo-wide `npm audit --omit=dev` still reported pre-existing production advisories in `hono`, `@hono/node-server`, `path-to-regexp`, `follow-redirects`, and `brace-expansion`; that historical residual was later retired by `RB-010` on 2026-04-19;
- broader repo-wide TypeScript debt outside the `Phase 1` gate surface may still exist and is not part of this evidence pack;
- sign-off remains human-controlled and must be completed separately from automated validation.

Blocking residuals:

- missing or stale OpenAPI export;
- missing `Phase 1` paths or schema names in generated clients;
- host resolution not distinguishing official and partner realms;
- missing `auth_realm_id`, `storefront_id`, or `actor_principal_id` in legal acceptance evidence;
- risk linkage not producing deterministic linked-subject output.

---

## 7. Sign-Off Block

| Function | Owner | Decision | Timestamp | Notes |
|---|---|---|---|---|
| platform architecture |  |  |  |  |
| backend platform |  |  |  |  |
| admin platform |  |  |  |  |
| frontend platform |  |  |  |  |
| QA |  |  |  |  |
| risk |  |  |  |  |
| support enablement |  |  |  |  |

`Phase 1` is not closed until this table is complete or an explicit waiver is attached by program governance.
