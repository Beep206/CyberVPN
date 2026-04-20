# CyberVPN Partner Platform Phase 7 Exit Evidence

**Date:** 2026-04-19  
**Status:** Phase 7 gate evidence pack  
**Purpose:** define the canonical automated evidence, analytical freeze proof, parity evidence, and sign-off checklist required to declare `Phase 7` complete.

---

## 1. Gate Role

This document is the concrete exit-evidence companion to:

- [../plans/2026-04-17-partner-platform-detailed-phased-implementation-plan.md](../plans/2026-04-17-partner-platform-detailed-phased-implementation-plan.md)
- [../plans/2026-04-18-partner-platform-phase-7-execution-ticket-decomposition.md](../plans/2026-04-18-partner-platform-phase-7-execution-ticket-decomposition.md)
- [../plans/2026-04-17-partner-platform-operational-readiness-package.md](../plans/2026-04-17-partner-platform-operational-readiness-package.md)
- [partner-platform-phase7-analytical-marts-and-reconciliation-pack.md](partner-platform-phase7-analytical-marts-and-reconciliation-pack.md)
- [partner-platform-phase7-parity-and-evidence-pack.md](partner-platform-phase7-parity-and-evidence-pack.md)

It converts the generic `Phase 7` readiness requirements into a named closure package.

This pack is complete only when:

1. required backend, partner, Telegram, and desktop validation packs are executed for the frozen `Phase 7` surfaces;
2. the committed OpenAPI export includes the frozen `Phase 7` reporting, outbox, and partner-integration surfaces;
3. canonical analytical marts reconcile to OLTP truth and produce deterministic replay output;
4. parity evidence proves `official_web` plus at least two additional channels from explicit evidence, not from informal assertions;
5. named owners sign off or explicitly record residual non-blocking gaps.

Current execution status for the 2026-04-19 closure run:

- targeted backend `Phase 7` verification pack passed with `15 passed in 25.01s`;
- targeted backend lint passed with `All checks passed!`;
- committed OpenAPI export was refreshed successfully for the frozen `Phase 7` surface;
- partner `Phase 7` validation pack passed with `10 passed`;
- partner targeted lint passed;
- Telegram Bot parity unit pack passed with `2 passed in 0.05s`;
- Telegram Bot targeted lint passed with `All checks passed!`;
- desktop parity production build passed successfully;
- official-web miniapp targeted lint passed.

---

## 2. Canonical Phase 7 Evidence Scope

`Phase 7` exit evidence must prove all of the following:

- canonical `outbox_events` and `outbox_publications` exist as the replay-safe event backbone for order, attribution, settlement, risk, entitlement, and reporting transitions;
- analytical marts reconstruct reporting truth from canonical platform objects rather than frontend counters or portal-local aggregates;
- partner dashboards, exports, and token-scoped reporting snapshots consume canonical mart truth and preserve workspace isolation;
- external integration readiness for reporting API tokens and postback credentials is visible through backend-owned readiness and delivery overlays;
- Telegram, Mini App, and desktop surfaces consume canonical order, entitlement, and service-state truth instead of channel-specific business semantics;
- parity evidence across channels is machine-readable and anchored to explicit mismatch vocabulary rather than operator judgement.

Important clarification:

- `Phase 7` does not require broad production rollout of all channels;
- `Phase 7` does require evidence that the channels already wired in `T7.4` and `T7.5` can be compared against canonical truth in a replay-safe way;
- `Phase 7` does require signed analytical and parity evidence before `Phase 8` shadow and pilot promotion can consume these foundations.

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
  backend/tests/contract/test_reporting_outbox_openapi_contract.py \
  backend/tests/contract/test_partner_integrations_openapi_contract.py \
  backend/tests/contract/test_phase7_api_surface_contract.py \
  backend/tests/contract/test_phase7_reporting_marts_pack.py \
  backend/tests/contract/test_phase7_parity_evidence_pack.py \
  backend/tests/integration/test_reporting_outbox.py \
  backend/tests/integration/test_partner_portal_reporting_reads.py \
  backend/tests/integration/test_partner_workspace_integrations.py \
  backend/tests/integration/api/v1/telegram/test_telegram_channel_parity.py \
  -q
```

Expected result:

- all tests pass;
- failures block `Phase 7` closure;
- the pack must cover outbox, marts, partner reporting, partner integrations, and Telegram parity through canonical contracts.

## 3.2 Lint And Contract Hygiene

The canonical backend lint command is:

```bash
backend/.venv/bin/ruff check \
  backend/src/application/events/outbox.py \
  backend/src/application/services/phase7_reporting_marts.py \
  backend/src/application/services/phase7_parity_evidence.py \
  backend/src/application/use_cases/reporting/outbox.py \
  backend/src/application/use_cases/reporting/workspace_reporting.py \
  backend/src/application/use_cases/reporting/workspace_integrations.py \
  backend/src/presentation/api/v1/reporting/routes.py \
  backend/src/presentation/api/v1/partners/routes.py \
  backend/tests/contract/test_phase7_api_surface_contract.py \
  backend/tests/contract/test_phase7_reporting_marts_pack.py \
  backend/tests/contract/test_phase7_parity_evidence_pack.py \
  backend/tests/integration/test_reporting_outbox.py \
  backend/tests/integration/test_partner_portal_reporting_reads.py \
  backend/tests/integration/test_partner_workspace_integrations.py \
  backend/tests/integration/api/v1/telegram/test_telegram_channel_parity.py
```

The canonical OpenAPI export command is:

```bash
REMNAWAVE_TOKEN=test-remnawave-token \
JWT_SECRET=0123456789abcdef0123456789abcdef \
CRYPTOBOT_TOKEN=test-cryptobot-token \
backend/.venv/bin/python backend/scripts/export_openapi.py
```

The exported file `backend/docs/api/openapi.json` remains the frozen contract source for downstream consumers.

## 3.3 Analytical Replay And Parity Evidence

The canonical deterministic evidence commands are:

```bash
REMNAWAVE_TOKEN=test-remnawave-token \
JWT_SECRET=0123456789abcdef0123456789abcdef \
CRYPTOBOT_TOKEN=test-cryptobot-token \
SKIP_TEST_DB_BOOTSTRAP=1 \
backend/.venv/bin/pytest --no-cov \
  backend/tests/contract/test_phase7_reporting_marts_pack.py \
  backend/tests/contract/test_phase7_parity_evidence_pack.py \
  -q
```

The harness must prove:

- identical reporting snapshots with fixed `replay_generated_at` produce identical analytical packs;
- identical parity snapshots with fixed `replay_generated_at` produce identical parity evidence packs;
- mismatch rows are explicit for reporting health, partner exports, channel parity, and postback delivery;
- channel coverage proof exists for `official_web` and at least two additional channels at evidence-pack level;
- compact summary scripts can be attached to evidence archives.

## 3.4 Surface And Channel Validation Packs

The canonical partner validation command is:

```bash
npm run test:run -w partner -- \
  src/lib/api/__tests__/phase6-generated-contract.test.ts \
  src/lib/api/__tests__/partner-portal.test.ts \
  src/features/partner-portal-state/lib/runtime-state.test.ts
```

The canonical partner targeted lint command is:

```bash
npm run lint -w partner -- \
  src/lib/api/__tests__/phase6-generated-contract.test.ts \
  src/lib/api/partner-portal.ts \
  src/lib/api/__tests__/partner-portal.test.ts \
  src/features/partner-portal-state/lib/runtime-state.ts \
  src/features/partner-portal-state/lib/runtime-state.test.ts \
  src/features/partner-portal-state/lib/use-partner-portal-runtime-state.ts \
  src/features/partner-integrations/components/integrations-console-page.tsx
```

The canonical Telegram Bot validation command is:

```bash
services/telegram-bot/.venv/bin/pytest --no-cov \
  services/telegram-bot/tests/unit/test_handlers/test_channel_parity.py \
  -q
```

The canonical Telegram Bot lint command is:

```bash
services/telegram-bot/.venv/bin/ruff check \
  services/telegram-bot/src/services/api_client.py \
  services/telegram-bot/src/handlers/menu.py \
  services/telegram-bot/src/handlers/account.py \
  services/telegram-bot/tests/unit/test_handlers/test_channel_parity.py
```

The canonical desktop validation command is:

```bash
npm run build -w apps/desktop-client
```

The canonical official-web miniapp targeted lint command is:

```bash
npm run lint -w frontend -- \
  'src/app/[locale]/miniapp/home/page.tsx' \
  'src/app/[locale]/miniapp/payments/page.tsx' \
  'src/app/[locale]/miniapp/profile/page.tsx' \
  'src/app/[locale]/miniapp/home/components/__tests__/HomeClient.test.tsx' \
  'src/app/[locale]/miniapp/payments/__tests__/page.test.tsx' \
  'src/app/[locale]/miniapp/profile/__tests__/page.test.tsx'
```

These packs must prove:

- partner reporting and integration surfaces read canonical backend overlays;
- Telegram Bot handlers consume canonical orders, entitlements, and service-state contracts;
- desktop client can still produce a distributable parity build on canonical contracts;
- official-web miniapp parity code remains lint-clean even while the known workspace Vitest issue remains outside this gate.

---

## 4. Required Artifact Set

The following artifacts must be attached to the evidence archive:

| Artifact | Source | Mandatory |
|---|---|---|
| backend gate test output | pytest command transcript | yes |
| backend lint output | ruff transcript | yes |
| committed OpenAPI export diff | `backend/docs/api/openapi.json` | yes |
| analytical marts replay transcript | builder and summary output | yes |
| analytical marts pack JSON | generated evidence file | yes |
| parity evidence transcript | builder and summary output | yes |
| parity evidence pack JSON | generated evidence file | yes |
| partner validation output | Vitest transcript | yes |
| Telegram Bot validation output | pytest transcript | yes |
| desktop build output | build transcript | yes |
| divergence register | issue list for non-blocking residuals | yes |
| sign-off block | named approvers | yes |

Recommended archive location:

```text
docs/evidence/partner-platform/<YYYY-MM-DD>/phase7-gate/
```

---

## 5. Acceptance Mapping

The `Phase 7` completion gate is considered satisfied only when the evidence maps to the frozen requirements below.

| Requirement | Evidence source |
|---|---|
| outbox publication is canonical and replay-safe | `backend/tests/integration/test_reporting_outbox.py`, `backend/tests/contract/test_reporting_outbox_openapi_contract.py` |
| analytical marts reconcile to canonical OLTP truth | `backend/tests/contract/test_phase7_reporting_marts_pack.py`, attached marts pack JSON |
| partner reporting and exports no longer depend on synthetic portal aggregates | `backend/tests/integration/test_partner_portal_reporting_reads.py`, `partner/src/lib/api/__tests__/partner-portal.test.ts`, `partner/src/features/partner-portal-state/lib/runtime-state.test.ts` |
| reporting API tokens and postback readiness remain canonical workspace-scoped contracts | `backend/tests/integration/test_partner_workspace_integrations.py`, `backend/tests/contract/test_partner_integrations_openapi_contract.py` |
| parity evidence exists across official web and at least two additional channels | `backend/tests/contract/test_phase7_parity_evidence_pack.py`, `backend/tests/integration/api/v1/telegram/test_telegram_channel_parity.py`, `services/telegram-bot/tests/unit/test_handlers/test_channel_parity.py`, desktop build transcript |
| exported OpenAPI contains the frozen `Phase 7` surface families | `backend/tests/contract/test_phase7_api_surface_contract.py`, committed `openapi.json` |

## 5.1 Closure Run Record

The closure run attached to this document produced the following results:

| Evidence item | Result |
|---|---|
| targeted backend `Phase 7` verification pack | `15 passed in 25.01s` |
| backend targeted lint | `All checks passed!` |
| OpenAPI export | refreshed successfully, frozen schema confirmed |
| analytical marts replay contract pack | covered within backend gate, deterministic output confirmed |
| parity evidence contract pack | covered within backend gate, deterministic output confirmed |
| partner `Phase 7` validation pack | `10 passed` |
| partner targeted lint | passed |
| Telegram Bot parity unit pack | `2 passed in 0.05s` |
| Telegram Bot targeted lint | `All checks passed!` |
| desktop parity build | passed |
| official-web miniapp targeted lint | passed |

---

## 6. Divergence Policy

Allowed non-blocking residuals:

- repo-wide security advisories unrelated to the touched `Phase 7` paths;
- human sign-off still pending after automated closure evidence is complete;
- the then-open official-web Vitest worker issue for miniapp/browser tests, as recorded before later workspace remediation by `RB-009`, provided parity evidence, backend contracts, and targeted lint remain green.

Recorded non-blocking residuals for this closure run:

- combined official-web Vitest execution for miniapp parity was historically constrained by the pre-existing `cssstyle -> @asamuzakjp/css-color` `ERR_REQUIRE_ASYNC_MODULE` worker issue recorded during `T7.4`; that worker-bootstrap blocker was later retired by `RB-009` on 2026-04-19, and remaining miniapp failures are no longer attributed to startup failure;
- at the time of the original closure run, repo-wide `npm audit --omit=dev` still reported pre-existing production advisories in `hono`, `@hono/node-server`, `path-to-regexp`, `follow-redirects`, and `brace-expansion`; that historical residual was later retired by `RB-010` on 2026-04-19;
- desktop build reported a non-blocking Vite chunk-size warning for large bundles, but the build completed successfully;
- sign-off remains human-controlled and must be completed separately from automated validation.

Blocking residuals:

- stale or missing OpenAPI export for outbox, partner reporting, or partner integration surfaces;
- missing deterministic analytical or parity evidence packs;
- any proof that partner reporting still depends on synthetic portal aggregates instead of canonical `Phase 7` marts;
- any proof that channel parity is being asserted without explicit evidence across `official_web` and at least two additional channels;
- any proof that reporting API tokens or postback readiness bypass workspace scope and canonical publication truth.

---

## 7. Sign-Off Block

| Function | Owner | Decision | Timestamp | Notes |
|---|---|---|---|---|
| platform architecture |  |  |  |  |
| backend platform |  |  |  |  |
| data/BI |  |  |  |  |
| partner ops |  |  |  |  |
| channel teams |  |  |  |  |
| QA |  |  |  |  |

`Phase 7` is not closed until this table is complete or an explicit waiver is attached by program governance.
