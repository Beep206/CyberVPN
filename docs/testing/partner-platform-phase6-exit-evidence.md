# CyberVPN Partner Platform Phase 6 Exit Evidence

**Date:** 2026-04-18  
**Status:** Phase 6 gate evidence pack  
**Purpose:** define the canonical automated evidence, surface-boundary proof, and sign-off checklist required to declare `Phase 6` complete.

---

## 1. Gate Role

This document is the concrete exit-evidence companion to:

- [../plans/2026-04-17-partner-platform-detailed-phased-implementation-plan.md](../plans/2026-04-17-partner-platform-detailed-phased-implementation-plan.md)
- [../plans/2026-04-18-partner-platform-phase-6-execution-ticket-decomposition.md](../plans/2026-04-18-partner-platform-phase-6-execution-ticket-decomposition.md)
- [../plans/2026-04-17-partner-platform-operational-readiness-package.md](../plans/2026-04-17-partner-platform-operational-readiness-package.md)
- [../plans/2026-04-17-partner-platform-rehearsal-logs-and-evidence-archive-template.md](../plans/2026-04-17-partner-platform-rehearsal-logs-and-evidence-archive-template.md)

It converts the generic `Phase 6` readiness requirements into a named closure package.

This pack is complete only when:

1. required backend, partner, admin, and official-web validation packs are executed for the frozen `Phase 6` surfaces;
2. the committed OpenAPI export includes the frozen portal, admin, and explainability overlays used by `Phase 6`;
3. partner portal proves statement, payout-account, and traffic-declaration visibility from backend-owned workspace contracts;
4. official web, partner storefront, partner portal, and admin prove distinct surface boundaries rather than local policy copies;
5. named owners sign off or explicitly record residual non-blocking gaps.

Current execution status for the 2026-04-18 closure run:

- targeted backend `Phase 6` verification pack passed with `3 passed in 8.74s`;
- targeted backend lint passed with `All checks passed!`;
- committed OpenAPI export was refreshed successfully for the frozen `Phase 6` surface;
- partner `Phase 6` validation pack passed with `24 passed`;
- admin `Phase 6` validation pack passed with `5 passed`;
- official-web generated-contract pack passed with `2 passed`;
- official-web targeted lint passed;
- combined official-web Vitest pack was blocked at the 2026-04-18 closure run by the pre-existing `cssstyle -> @asamuzakjp/css-color` worker issue; this historical residual was later retired by `RB-009` on 2026-04-19 after the frontend Vitest runtime moved to `happy-dom`.

---

## 2. Canonical Phase 6 Evidence Scope

`Phase 6` exit evidence must prove all of the following:

- official web purchase and service-access flows read canonical `quote`, `checkout_session`, `order`, `payment_attempt`, `entitlements/current`, and `current/service-state` contracts;
- partner storefront resolves host, realm, storefront legal context, and branded customer auth without collapsing into portal or official-web assumptions;
- partner portal runtime state is backend-owned for workspace, statements, payout accounts, cases, report exports, analytics overlays, and traffic declarations;
- admin customer-operations insight aggregates attribution, settlement, service access, and risk from canonical contracts rather than local stitching;
- surface-policy enforcement prevents official-web markup leakage, partner-portal admin leakage, and storefront/operator leakage;
- support and legal routing stay surface-aware and do not silently reuse the wrong communication profile.

Important clarification:

- `Phase 6` does not require complete feature parity for every later partner-portal workflow action;
- `Phase 6` does require backend-owned read visibility for finance-critical and compliance-critical portal sections;
- `Phase 6` does require formal surface-boundary proof before any `Phase 6` surface becomes rollout-ring input for pilots or production promotion.

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
  backend/tests/contract/test_phase6_api_surface_contract.py \
  backend/tests/contract/test_partner_statement_openapi_contract.py \
  backend/tests/integration/test_partner_portal_reporting_reads.py \
  -q
```

Expected result:

- all tests pass;
- failures block `Phase 6` closure;
- the portal reporting-read pack must include backend-owned `traffic-declarations` visibility together with statements, exports, and cases.

## 3.2 Surface Validation Packs

The canonical partner validation command is:

```bash
npm run test:run -w partner -- \
  src/lib/api/__tests__/phase6-generated-contract.test.ts \
  src/lib/api/__tests__/partner-portal.test.ts \
  src/features/partner-portal-state/lib/runtime-state.test.ts \
  src/features/partner-compliance/components/compliance-center-page.test.tsx \
  src/shared/lib/__tests__/surface-policy.test.ts \
  src/__tests__/proxy.test.ts
```

The canonical admin validation command is:

```bash
npm run test:run -w admin -- \
  src/lib/api/__tests__/phase6-generated-contract.test.ts \
  src/shared/lib/__tests__/surface-policy.test.ts \
  src/features/customers/components/__tests__/customer-operations-insight.test.tsx
```

The canonical official-web generated-contract command is:

```bash
npm run test:run -w frontend -- \
  src/lib/api/__tests__/phase6-generated-contract.test.ts
```

The canonical official-web targeted lint command is:

```bash
npm run lint -w frontend -- \
  src/lib/api/__tests__/phase6-generated-contract.test.ts \
  src/shared/lib/__tests__/surface-policy.test.ts
```

These packs must prove:

- partner storefront and partner portal consume generated contract types aligned with the frozen backend surface;
- partner portal compliance pages render backend-owned `traffic_declarations` rather than local placeholders;
- admin customer-insight and internal policy surfaces remain distinct from partner surfaces;
- official web keeps canonical commerce and service-access contracts even when full Vitest coverage is constrained by a pre-existing workspace issue.

## 3.3 Lint And Contract Hygiene

The canonical backend lint command is:

```bash
backend/.venv/bin/ruff check \
  backend/src/presentation/api/v1/partners/routes.py \
  backend/src/presentation/api/v1/partners/schemas.py \
  backend/tests/contract/test_partner_statement_openapi_contract.py \
  backend/tests/contract/test_phase6_api_surface_contract.py \
  backend/tests/integration/test_partner_portal_reporting_reads.py
```

The canonical OpenAPI export command is:

```bash
REMNAWAVE_TOKEN=test-remnawave-token \
JWT_SECRET=0123456789abcdef0123456789abcdef \
CRYPTOBOT_TOKEN=test-cryptobot-token \
backend/.venv/bin/python backend/scripts/export_openapi.py
```

The exported file `backend/docs/api/openapi.json` remains the frozen contract source for downstream surface consumers.

## 3.4 Host, Realm, And Surface-Boundary Proof

The attached validation output must demonstrate:

- partner host resolution is enforced in runtime and proxy tests;
- partner portal runtime state only receives `trafficDeclarations` when backend permissions include `traffic_read`;
- official web does not gain partner markup or payout controls through `Phase 6` integrations;
- partner portal does not gain admin-only moderation or maker-checker controls;
- partner storefront legal acceptance remains storefront-aware and customer-session-aware.

---

## 4. Required Artifact Set

The following artifacts must be attached to the evidence archive:

| Artifact | Source | Mandatory |
|---|---|---|
| backend gate test output | pytest command transcript | yes |
| backend lint output | ruff transcript | yes |
| committed OpenAPI export diff | `backend/docs/api/openapi.json` | yes |
| partner validation output | Vitest transcript | yes |
| admin validation output | Vitest transcript | yes |
| official-web generated-contract output | Vitest transcript | yes |
| official-web targeted lint output | eslint transcript | yes |
| host and surface-boundary proof | proxy, runtime-state, and compliance test output | yes |
| divergence register | issue list for non-blocking residuals | yes |
| sign-off block | named approvers | yes |

Recommended archive location:

```text
docs/evidence/partner-platform/<YYYY-MM-DD>/phase6-gate/
```

---

## 5. Acceptance Mapping

The `Phase 6` completion gate is considered satisfied only when the evidence maps to the frozen requirements below.

| Requirement | Evidence source |
|---|---|
| official web reads canonical commerce and service-access contracts | `frontend/src/lib/api/__tests__/phase6-generated-contract.test.ts`, targeted eslint output |
| partner storefront and proxy resolve branded surface behavior from canonical runtime and host rules | `src/shared/lib/__tests__/surface-policy.test.ts`, `src/__tests__/proxy.test.ts` in `partner` |
| partner portal finance, reporting, cases, and traffic declarations are backend-owned | `backend/tests/integration/test_partner_portal_reporting_reads.py`, `partner/src/lib/api/__tests__/partner-portal.test.ts`, `partner/src/features/partner-portal-state/lib/runtime-state.test.ts`, `partner/src/features/partner-compliance/components/compliance-center-page.test.tsx` |
| admin customer-operations insight is canonical-contract-driven | `admin/src/lib/api/__tests__/phase6-generated-contract.test.ts`, `admin/src/features/customers/components/__tests__/customer-operations-insight.test.tsx` |
| surface policy boundaries are enforced across official web, partner, and admin | `partner/src/shared/lib/__tests__/surface-policy.test.ts`, `admin/src/shared/lib/__tests__/surface-policy.test.ts`, targeted official-web lint output |
| exported OpenAPI contains the frozen `Phase 6` surface families | `backend/tests/contract/test_phase6_api_surface_contract.py`, committed `openapi.json` |

## 5.1 Closure Run Record

The closure run attached to this document produced the following results:

| Evidence item | Result |
|---|---|
| targeted backend `Phase 6` verification pack | `3 passed in 8.74s` |
| backend targeted lint | `All checks passed!` |
| OpenAPI export | refreshed successfully, frozen schema confirmed |
| partner `Phase 6` validation pack | `24 passed` |
| admin `Phase 6` validation pack | `5 passed` |
| official-web generated-contract pack | `2 passed` |
| official-web targeted lint | passed |

---

## 6. Divergence Policy

Allowed non-blocking residuals:

- deferred partner-portal action rails for `traffic_declarations`, `creative_approvals`, richer inbox actions, lane-readiness overlays, workspace switcher UX, and export scheduling;
- repo-wide security advisories unrelated to the touched `Phase 6` paths;
- human sign-off still pending after automated closure evidence is complete;
- the then-open official-web Vitest worker issue described below, as recorded for the 2026-04-18 closure run before later workspace remediation by `RB-009`.

Recorded non-blocking residuals for this closure run:

- at the time of the 2026-04-18 closure run, combined official-web Vitest execution that included `src/shared/lib/__tests__/surface-policy.test.ts` was blocked by the pre-existing `cssstyle -> @asamuzakjp/css-color` `ERR_REQUIRE_ASYNC_MODULE` worker issue; that runtime blocker was later retired by `RB-009` on 2026-04-19;
- at the time of the 2026-04-18 closure run, repo-wide `npm audit --omit=dev` still reported pre-existing production advisories in `hono`, `@hono/node-server`, `path-to-regexp`, `follow-redirects`, and `brace-expansion`; that historical residual was later retired by `RB-010` on 2026-04-19;
- sign-off remains human-controlled and must be completed separately from automated validation.

Blocking residuals:

- stale or missing OpenAPI export for portal, admin-insight, or `Phase 6` explainability surfaces;
- any proof that partner portal still depends on local mock-only finance or compliance state for statements, payout accounts, or traffic declarations;
- any proof that official web renders partner markup, payout, or workspace-operator controls;
- any proof that partner portal or partner storefront renders admin-only moderation or maker-checker controls;
- missing host-resolution or realm-isolation proof for branded partner surfaces.

---

## 7. Sign-Off Block

| Function | Owner | Decision | Timestamp | Notes |
|---|---|---|---|---|
| platform architecture |  |  |  |  |
| frontend platform |  |  |  |  |
| partner ops |  |  |  |  |
| finance ops |  |  |  |  |
| support enablement |  |  |  |  |
