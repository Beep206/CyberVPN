# CyberVPN Partner Platform Open Residuals Execution Backlog

**Date:** 2026-04-19  
**Status:** Execution backlog for open residuals after `Phase 8`  
**Purpose:** translate `OPEN-001` through `OPEN-013` from the central residual register into executable backlog items with ownership, sequencing, workboard alignment, and closure evidence.

---

## 1. Document Role

This document is the execution bridge between:

- [2026-04-19-partner-platform-central-residuals-and-follow-up-register.md](2026-04-19-partner-platform-central-residuals-and-follow-up-register.md)
- [2026-04-18-partner-platform-phase-6-execution-ticket-decomposition.md](2026-04-18-partner-platform-phase-6-execution-ticket-decomposition.md)
- [2026-04-18-partner-portal-phase-and-workboard-decomposition.md](2026-04-18-partner-portal-phase-and-workboard-decomposition.md)
- [2026-04-17-partner-platform-operational-readiness-package.md](2026-04-17-partner-platform-operational-readiness-package.md)
- [../testing/partner-platform-phase8-production-readiness-bundle.md](../testing/partner-platform-phase8-production-readiness-bundle.md)
- [../testing/partner-platform-phase8-exit-evidence.md](../testing/partner-platform-phase8-exit-evidence.md)

It exists so the remaining tails discovered during `Phase 0` through `Phase 8` are no longer tracked only as residual prose. They now have executable backlog ownership.

This document intentionally covers:

- portal and admin completion slices that were deferred after baseline closure;
- engineering environment and dependency hygiene residuals;
- rollout-blocking operational follow-ups that must be completed before broad activation.

This document intentionally does not convert `OPEN-014` into a ticket, because that item is an explicit operating boundary, not deferred implementation scope.

---

## 2. Backlog Rules

Execution for the residual backlog follows these rules:

1. Portal and admin completion slices must stay on canonical backend objects already frozen by `Phase 6`, `Phase 7`, and `Phase 8`.
2. Rollout blockers may be tracked in backlog form even when they are primarily documentation or approval work, because they still require explicit closure ownership.
3. No backlog item here may reopen business rules, canonical data models, or already-frozen API semantics without updating the canonical package first.
4. `OPEN-011` and `OPEN-012` are rollout blockers and may remain late-bound operational tasks, but they may not disappear into “we will handle this later”.
5. Portal and admin completion items should close before anyone claims those surfaces are feature-complete.

Recommended backlog labels:

- `post-phase8`
- `residual-closure`
- `partner-portal`
- `admin-ops`
- `engineering-hygiene`
- `rollout-blocker`

---

## 3. Workstream Model

| Workstream | Scope | Primary owners |
|---|---|---|
| `RS1` | partner portal completion residuals | frontend platform, partner ops, finance ops |
| `RS2` | admin operations completion residuals | admin platform, finance ops, support enablement, risk ops |
| `RS3` | engineering environment and dependency hygiene | frontend platform, platform engineering, desktop/client owners |
| `RS4` | rollout-blocking operational closure | platform, QA, finance ops, risk ops, support, product |

Portal-aligned workboards reused from the portal package:

- `WB-LEGAL-COMPLIANCE`
- `WB-NOTIFICATIONS-CASES`
- `WB-WORKSPACE-OPS`
- `WB-ANALYTICS-FINANCE`
- `WB-PLATFORM-QA`

---

## 4. Sequencing Summary

| Ticket | Source residual | Workstream | Main workboard | Priority | Size | Hard blockers |
|---|---|---|---|---|---|---|
| `RB-001` | `OPEN-001` | `RS1` | `WB-LEGAL-COMPLIANCE` | `P1` | `L` | canonical `T8.2` overlay APIs |
| `RB-002` | `OPEN-002` | `RS1` | `WB-NOTIFICATIONS-CASES` | `P1` | `L` | canonical `review_requests / cases` contracts |
| `RB-003` | `OPEN-003` | `RS1` | `WB-WORKSPACE-OPS` | `P1` | `M` | lane capability and readiness overlays stay backend-owned |
| `RB-004` | `OPEN-004` | `RS1` | `WB-WORKSPACE-OPS` | `P2` | `M` | canonical `partner-workspaces/me` runtime state |
| `RB-005` | `OPEN-005` | `RS1` | `WB-ANALYTICS-FINANCE` | closed | `M` | `Phase 7` reporting/export contracts |
| `RB-006` | `OPEN-006` | `RS2` | closed | `P1` | `M` | customer-operations aggregate stays canonical while action rail now orchestrates payout account and payout instruction maker-checker flows |
| `RB-007` | `OPEN-007` | `RS2` | closed | `P1` | `L` | risk/case/dispute APIs stayed canonical during closure |
| `RB-008` | `OPEN-008` | `RS2` | internal admin reporting board | closed | `M` | statement and payout evidence exports remain backend-owned |
| `RB-009` | `OPEN-009` | `RS3` | closed | `P1` | `M` | frontend Vitest runtime now starts previously blocked official-web/browser-oriented packs |
| `RB-010` | `OPEN-010` | `RS3` | closed | `P2` | `M` | root and workspace dependency trees refreshed to zero prod audit advisories |
| `RB-011` | `OPEN-011` | `RS4` | rollout governance board | `P0` | `S` | named human approvers |
| `RB-012` | `OPEN-012` | `RS4` | rollout governance board | `P0` | `M` | environment owners and filled production window registration record |
| `RB-013` | `OPEN-013` | `RS3` | desktop/client ops board | closed | `S` | WSL/system-package prerequisites |

Recommended execution order:

1. `RB-011`, `RB-012` immediately before pilot widening or broad activation

`RB-001` through `RB-007` were completed later and are intentionally left in the backlog as closed execution records rather than active queue items.

---

## 5. Ticket Decomposition

## 5.1 `RB-001` Partner Portal Action Rails For Traffic Declarations And Creative Approvals

**Source residual:** `OPEN-001`  
**Status:** closed on `2026-04-19`  
**Workstream:** `RS1`  
**Main workboard:** `WB-LEGAL-COMPLIANCE`  
**Primary owners:** frontend platform, legal/compliance backend, partner ops  
**Supporting owners:** QA

**Scope:**

- turn portal read-only compliance visibility into explicit partner-facing actions;
- add action-capable UX for declaration submission, status follow-up, and creative approval handling;
- keep partner-facing actions scoped to workspace-safe operations rather than internal moderation controls.

**Suggested repository touchpoints:**

- `partner/src/features/partner-compliance/`
- `partner/src/lib/api/partner-portal.ts`
- `backend/src/presentation/api/v1/traffic_declarations/`
- `backend/src/presentation/api/v1/creative_approvals/`
- `backend/src/presentation/api/v1/partners/routes.py`

**Acceptance criteria:**

- partner portal no longer stops at read-only declaration and approval state;
- partner actions remain constrained to canonical backend workflows;
- no admin-only moderation actions leak into the partner surface.

**Closure evidence:**

- partner UI validation pack for declaration and approval actions;
- backend contract/integration proof for action-capable workflow endpoints.

**Closure notes:**

- backend now exposes workspace-scoped partner-facing POST rails for `traffic_declarations` and `creative_approvals`;
- partner portal compliance center now submits canonical actions instead of stopping at read-only visibility;
- targeted backend and partner validation packs were re-run at closure.

## 5.2 `RB-002` Partner Inbox And Workflow Actions On Canonical Review And Case Objects

**Source residual:** `OPEN-002`  
**Workstream:** `RS1`  
**Main workboard:** `WB-NOTIFICATIONS-CASES`  
**Primary owners:** frontend platform, support backend, partner ops  
**Supporting owners:** QA

**Scope:**

- replace passive case visibility with partner-operable inbox and workflow actions;
- add explicit case transitions, response actions, and thread context on canonical `review_requests` and `cases`;
- preserve the boundary between workspace support and customer storefront support.

**Suggested repository touchpoints:**

- `partner/src/features/partner-portal-state/`
- `partner/src/features/partner-support/` or equivalent new slice
- `partner/src/lib/api/partner-portal.ts`
- `backend/src/presentation/api/v1/partners/routes.py`

**Acceptance criteria:**

- partner operators can act from the portal, not just inspect case status;
- workflow state remains canonical and backend-owned;
- support boundary stays surface-aware.

**Closure evidence:**

- partner workflow integration tests;
- role-scope proof for partner-visible case actions.

**Closure notes:**

- backend now exposes workspace-scoped partner-facing action rails for review-request responses, case replies, and ready-for-ops transitions;
- canonical workflow state is persisted through partner workspace thread events instead of staying synthetic/read-only in the portal shell;
- partner portal cases surface now performs canonical inbox actions while keeping workspace support explicitly separate from storefront customer support;
- targeted backend and partner validation packs were re-run at closure.

## 5.3 `RB-003` Partner Portal Lane Membership And Readiness Surface

**Source residual:** `OPEN-003`  
**Status:** closed on `2026-04-19`  
**Workstream:** `RS1`  
**Main workboard:** `WB-WORKSPACE-OPS`  
**Primary owners:** frontend platform, partner domain backend  
**Supporting owners:** partner ops, QA

**Scope:**

- expose canonical lane membership and lane-readiness posture in the portal `programs` area;
- avoid UI-local lane truth or status collapsing;
- make lane availability, probation, and readiness reasons explicit to the operator.

**Suggested repository touchpoints:**

- `partner/src/features/partner-programs/` or equivalent programs slice
- `partner/src/lib/api/partner-portal.ts`
- `backend/src/presentation/api/v1/partners/routes.py` or dedicated lane-readiness read surface

**Acceptance criteria:**

- portal operators can see backend-owned lane posture and readiness reasons;
- no local heuristic replaces canonical lane state;
- surface policy still prevents admin-only decisions leaking into partner portal.

**Closure evidence:**

- generated contract update if new read model is added;
- partner portal validation for programs/readiness rendering.

**Closure notes:**

- backend now exposes canonical workspace programs posture through `/api/v1/partner-workspaces/{workspace_id}/programs`;
- partner portal `programs` surface now renders backend-owned lane memberships and readiness items instead of relying on local scenario truth for canonical workspaces;
- targeted backend contract/integration tests and partner API/component tests were re-run at closure;
- OpenAPI export and generated partner API types were refreshed after closure.

## 5.4 `RB-004` Workspace Switcher UX On Canonical Workspace Runtime

**Source residual:** `OPEN-004`  
**Status:** closed on `2026-04-19`  
**Workstream:** `RS1`  
**Main workboard:** `WB-WORKSPACE-OPS`  
**Primary owners:** frontend platform  
**Supporting owners:** partner domain backend, QA

**Scope:**

- add explicit workspace-switcher UX on top of canonical workspace runtime state;
- remove query-param-first fallback as the primary operator pattern;
- keep host, realm, and role boundaries intact.

**Suggested repository touchpoints:**

- `partner/src/features/partner-portal-state/`
- `partner/src/app/[locale]/(dashboard)/`
- `partner/src/lib/api/partner-portal.ts`

**Acceptance criteria:**

- multi-workspace operators can switch workspace intentionally from UI;
- runtime state stays canonical and server-backed;
- workspace switching does not bypass scope or host rules.

**Closure evidence:**

- portal runtime-state tests;
- route and workspace-switch interaction tests.

**Closure notes:**

- partner portal now exposes an explicit workspace switcher in the desktop and mobile shell instead of relying on hidden query-driven fallback selection;
- canonical workspace selection is now host-scoped and persisted for the portal runtime while preserving route-aware query overrides and router-driven switching;
- heavy canonical runtime queries were not moved into the shell: a dedicated lightweight workspace-selection hook now feeds both the shell switcher and the broader portal runtime;
- targeted partner runtime, shell, and interaction tests were re-run at closure.

## 5.5 `RB-005` Partner Reporting Export Scheduling And Richer Affordances

**Source residual:** `OPEN-005`  
**Status:** closed on `2026-04-19`  
**Workstream:** `RS1`  
**Main workboard:** `WB-ANALYTICS-FINANCE`  
**Primary owners:** frontend platform, analytics backend, finance ops  
**Supporting owners:** QA, partner ops

**Scope:**

- move partner reporting/export UX from baseline visibility to richer operator affordances;
- expose export scheduling, richer status posture, and clearer delivery lifecycle on top of canonical reporting truth;
- keep workspace and role scope intact.

**Suggested repository touchpoints:**

- `partner/src/features/partner-reporting/`
- `partner/src/lib/api/partner-portal.ts`
- `backend/src/presentation/api/v1/partners/routes.py`
- `backend/src/presentation/api/v1/reporting/routes.py`

**Acceptance criteria:**

- export lifecycle is operable rather than purely visible;
- reporting/export state remains driven by canonical `Phase 7` read models;
- no synthetic client aggregation reappears.

**Closure evidence:**

- backend canonical `report-exports/{export_id}/schedule` action rail on top of workspace workflow events;
- partner portal export lifecycle UX with schedule action, request history, and canonical invalidation flow;
- backend validation:
  - `backend/tests/contract/test_partner_statement_openapi_contract.py`
  - `backend/tests/integration/test_partner_portal_reporting_reads.py`
- partner validation:
  - `partner/src/lib/api/__tests__/partner-portal.test.ts`
  - `partner/src/features/partner-reporting/components/analytics-exports-page.test.tsx`

## 5.6 `RB-006` Consolidated Admin Maker-Checker Action Rail

**Source residual:** `OPEN-006`  
**Status:** closed on `2026-04-19`  
**Workstream:** `RS2`  
**Primary owners:** admin platform, finance ops  
**Supporting owners:** support enablement, QA

**Scope:**

- consolidate customer-linked maker-checker actions into a clearer admin action rail;
- reduce operator context switching across isolated resource families while preserving canonical backend ownership;
- keep the new rail role-scoped and auditable.

**Suggested repository touchpoints:**

- `admin/src/features/customers/`
- `admin/src/lib/api/customers.ts`
- `backend/src/presentation/api/v1/admin/customer_operations.py`

**Acceptance criteria:**

- admin customer operations is no longer read-only where safe action consolidation is intended;
- maker-checker controls remain internal-only and auditable;
- original resource families remain the underlying source of truth.

**Closure evidence:**

- backend canonical route `POST /api/v1/admin/mobile-users/{user_id}/operations-insight/actions`;
- role-scoped `finance_actions_visible`, `payout_account_actions`, and `payout_instruction_actions` overlays in customer operations insight;
- admin customer-operations UI wired to the canonical action rail with confirm-dialog flow and cache invalidation;
- targeted backend/admin validation coverage for action routing, OpenAPI contract, and operator UI behavior.

## 5.7 `RB-007` Richer Admin Case, Dispute-Evidence, And Review-Queue Workflows

**Source residual:** `OPEN-007`  
**Status:** closed on `2026-04-19`  
**Workstream:** `RS2`  
**Primary owners:** admin platform, risk ops, support enablement  
**Supporting owners:** finance ops, QA

**Scope:**

- replace inspection-only cards with real operator workflow components for risk/case/dispute handling;
- keep admin workflows distinct from partner-facing case rails;
- preserve audit trail and role scoping.

**Suggested repository touchpoints:**

- `admin/src/features/customers/`
- `admin/src/features/risk/` or equivalent slice
- `backend/src/presentation/api/v1/security/`
- `backend/src/presentation/api/v1/payment_disputes/`

**Acceptance criteria:**

- admin operators can work queues and evidence from the UI;
- workflow components remain internal-only;
- canonical backend objects remain the decision source.

**Closure evidence:**

- admin workflow tests for queue/action flows;
- backend integration tests if new action endpoints are added.

**Closure notes:**

- admin now exposes an internal-only `security/review-queue` console on top of canonical `risk_reviews`, `attachments`, `governance_actions`, and `resolve` routes;
- `customer operations` now surfaces canonical payment-dispute workflow state together with linked `dispute_cases`, and can open new canonical dispute-case overlays without inventing a second dispute truth;
- targeted backend/admin validation packs, OpenAPI export, and admin API type generation were re-run at closure.

## 5.8 `RB-008` Finance-Grade Admin Export And Download Affordances

**Source residual:** `OPEN-008`  
**Status:** closed on `2026-04-19`  
**Workstream:** `RS2`  
**Primary owners:** admin platform, finance ops  
**Supporting owners:** QA

**Scope:**

- add finance-grade export and download affordances for customer-linked statement and payout evidence;
- keep evidence exports aligned with canonical statement, payout, and explainability truth;
- avoid manual SQL or external spreadsheet dependency for routine operator retrieval.

**Suggested repository touchpoints:**

- `admin/src/features/customers/`
- `admin/src/features/commerce/`
- `backend/src/presentation/api/v1/admin/`
- `backend/src/presentation/api/v1/partner_statements/`
- `backend/src/presentation/api/v1/payouts/`

**Acceptance criteria:**

- finance operators can export/download the required evidence from UI flows;
- exports remain role-scoped and audit-safe;
- no shadow evidence source is introduced.

**Closure evidence:**

- admin export tests;
- backend export contract proof where applicable.

**Closure notes:**

- backend now exposes canonical admin attachment endpoints for workspace, statement, payout-instruction, and payout-execution evidence under `/api/v1/admin/mobile-users/{user_id}/operations-insight/exports/*`;
- admin `customer operations` settlement card now downloads those backend-owned evidence packs directly, instead of relying on manual inspection or local JSON assembly;
- targeted backend contract/integration tests, admin API/component tests, OpenAPI export, and admin API type generation were re-run at closure.

## 5.9 `RB-009` Frontend Vitest Runtime Remediation

**Source residual:** `OPEN-009`  
**Workstream:** `RS3`  
**Main workboard:** `WB-PLATFORM-QA`  
**Primary owners:** frontend platform  
**Supporting owners:** QA

**Scope:**

- remove the pre-existing combined `frontend` Vitest worker failure around `cssstyle -> @asamuzakjp/css-color`;
- restore confidence in broader frontend test execution instead of relying only on targeted lint/contract packs;
- keep test bootstrap aligned with current Next.js and workspace runtime.

**Suggested repository touchpoints:**

- `frontend/vitest.config.*`
- `frontend/package.json`
- `frontend/src/test/setup.ts`
- any workspace-level Vite/Vitest bootstrap or dependency overrides

**Acceptance criteria:**

- combined frontend Vitest can start and run the previously blocked packs;
- no new frontend contract tests are downgraded to lint-only closure because of the old worker issue;
- the fix is documented for future workspace upgrades.

**Closure evidence:**

- combined frontend Vitest transcript;
- updated evidence docs if prior residual can be retired.

**Status:** closed on 2026-04-19

**Closure notes:**

- `frontend` Vitest was switched from `jsdom` to `happy-dom` in `frontend/vitest.config.ts`, following official Vitest guidance that both are supported browser-like environments and `happy-dom` can be used by setting `test.environment`;
- `happy-dom` was added to the frontend workspace so the runtime no longer depends on the failing `jsdom/cssstyle -> @asamuzakjp/css-color` worker-boot path;
- the previously blocked combined pack `src/lib/api/__tests__/phase1-generated-contract.test.ts + src/shared/lib/__tests__/surface-policy.test.ts` now runs successfully, and the historical `ERR_REQUIRE_ASYNC_MODULE` bootstrap failure is no longer reproducible;
- broader miniapp-oriented Vitest now starts and executes instead of failing at worker bootstrap, which means remaining failures are ordinary application/test debt rather than the old workspace runtime blocker;
- historical evidence and readiness docs were updated to mark the worker issue as retired rather than still open.

## 5.10 `RB-010` Dependency Advisory Remediation Pass

**Source residual:** `OPEN-010`  
**Workstream:** `RS3`  
**Primary owners:** platform engineering  
**Supporting owners:** frontend platform, partner app owners, admin app owners

**Scope:**

- remediate the pre-existing production advisories carried through the partner-platform program;
- preserve the repository rule that dependencies only move forward, never backward;
- revalidate the affected workspaces after upgrades.

**Suggested repository touchpoints:**

- root `package.json`
- workspace `package.json` files
- lockfile
- any runtime or test config touched by upgraded packages

**Acceptance criteria:**

- the named advisory set is either removed or explicitly reclassified with documented rationale;
- no downgrade is introduced;
- affected validation packs are rerun after remediation.

**Closure evidence:**

- fresh `npm audit --omit=dev` output;
- rerun transcripts for affected workspaces.

**Status:** closed on 2026-04-19

**Closure notes:**

- the stale advisory set was removed without downgrades by refreshing the existing dependency graph to safe forward versions already allowed by the repository semver ranges;
- root transitive upgrades now include `@modelcontextprotocol/sdk@1.29.0`, `@hono/node-server@1.19.14`, `hono@4.12.14`, `path-to-regexp@8.4.2`, and `brace-expansion@5.0.5` under the desktop/shadcn chain;
- workspace HTTP transport chains now resolve `follow-redirects@1.16.0` in `admin` and `frontend`;
- fresh `npm audit --omit=dev` now returns `found 0 vulnerabilities` for the repo root and for `admin`, `frontend`, and `partner`;
- validation reruns confirmed `admin` API contract/client packs and `frontend` API contract/client packs still pass after the dependency refresh, while the desktop validation path showed a pre-existing TypeScript error in `src/shared/model/connection-store.tsx` but a direct `vite build` still completed successfully, which is treated as unrelated existing debt rather than a dependency regression.

## 5.11 `RB-011` Human Sign-Off Completion For Evidence And Activation Artifacts

**Source residual:** `OPEN-011`  
**Workstream:** `RS4`  
**Primary owners:** platform, QA, product  
**Supporting owners:** finance ops, risk ops, support, partner ops

**Scope:**

- complete the named sign-off tables across the required phase and activation evidence records;
- remove the current “engineering proof exists but humans have not approved” residual;
- keep exact approval scope explicit.

**Suggested document touchpoints:**

- `docs/testing/partner-platform-broad-activation-sign-off-tracker.md`
- `docs/testing/partner-platform-phase8-production-readiness-bundle.md`
- `docs/testing/partner-platform-phase8-exit-evidence.md`
- any still-required earlier phase evidence pack sign-off blocks consumed by the activation path

**Acceptance criteria:**

- every required signatory row is completed for the exact scope being promoted;
- no broad activation remains blocked by missing human approval;
- the accepted residual set is explicit and signed.

**Closure evidence:**

- completed sign-off tables with names, timestamps, and decisions.

**Current execution note on `2026-04-19`:**

- created `docs/testing/partner-platform-broad-activation-sign-off-tracker.md` as the canonical human-approval sheet for broad activation;
- linked the tracker from the `Phase 8` production-readiness bundle and `Phase 8` exit evidence pack;
- `RB-011` remains open until real approver names, timestamps, decisions, and accepted residuals are recorded in that tracker.

## 5.12 `RB-012` Environment-Specific Production Command Inventory Resolution

**Source residual:** `OPEN-012`  
**Workstream:** `RS4`  
**Primary owners:** platform engineering, environment owners  
**Supporting owners:** QA, finance ops, support

**Scope:**

- centralize the already-existing repo command families into one canonical environment command inventory sheet;
- retire generic production placeholder wording from the cutover package;
- keep the remaining live blocker limited to exact runtime parameters, named rollout windows, and named owners for the real activation window.

**Suggested document touchpoints:**

- `docs/plans/2026-04-19-partner-platform-environment-command-inventory-sheet.md`
- `docs/plans/2026-04-17-partner-platform-environment-specific-cutover-runbooks.md`
- `docs/plans/2026-04-17-partner-platform-rehearsal-logs-and-evidence-archive-template.md`
- `docs/testing/partner-platform-phase8-production-readiness-bundle.md`
- `docs/testing/partner-platform-phase8-exit-evidence.md`
- `docs/evidence/partner-platform/2026-04-19/phase8-production-readiness/BA-2026-04-19-01-production-window-registration.md`

**Acceptance criteria:**

- base command inventory is explicit for `local`, `staging`, and `production`;
- generic production placeholder blocks are retired from the cutover package;
- the remaining live blocker is only the named production window registration record with exact runtime values, named owners, and linked rehearsal evidence.

**Closure evidence:**

- resolved environment command inventory sheet;
- filled production window registration record;
- signed rehearsal record against the actual environment command inventory.

**Current execution note on `2026-04-19`:**

- created `docs/plans/2026-04-19-partner-platform-environment-command-inventory-sheet.md` as the canonical cross-environment command inventory;
- updated the cutover runbooks, rehearsal template, readiness bundle, and `Phase 8` exit evidence so they now require the command inventory sheet and a named production window registration record instead of generic production command placeholders;
- created `docs/evidence/partner-platform/2026-04-19/phase8-production-readiness/BA-2026-04-19-01-production-window-registration.md` as the named activation-window record and linked it from the sign-off tracker, readiness bundle, and `Phase 8` exit evidence;
- `RB-012` remains open until that production window record is filled with exact runtime values, named owners, and linked signed rehearsal evidence for the live activation scope.

## 5.13 `RB-013` Desktop WSL Prerequisites And Full Rust Validation

**Source residual:** `OPEN-013`  
**Status:** closed on `2026-04-19`  
**Workstream:** `RS3`  
**Primary owners:** desktop/client owners  
**Supporting owners:** platform engineering

**Scope:**

- document and install missing WSL prerequisites for local desktop Rust validation;
- rerun the previously blocked `cargo check`;
- retire the environment-specific residual from the central register.

**Suggested repository touchpoints:**

- desktop app README or environment bootstrap doc
- any local-dev prerequisites doc for `apps/desktop-client`

**Acceptance criteria:**

- required system packages are explicit and reproducible;
- local `cargo check` succeeds in the supported WSL environment;
- the residual is removed from the central register.

**Closure evidence:**

- bootstrap note or prerequisite doc update;
- successful `cargo check` transcript.

**Closure notes:**

- created [2026-04-19-desktop-client-wsl-bootstrap-prerequisites.md](2026-04-19-desktop-client-wsl-bootstrap-prerequisites.md) as the canonical Ubuntu/WSL bootstrap note for `apps/desktop-client`;
- added a pointer to that note in `apps/desktop-client/README.md`;
- installed the explicit Ubuntu prerequisite set for Tauri Linux development plus the previously missing `libsoup-3.0-dev` and `libjavascriptcoregtk-4.1-dev`;
- reran `cargo check` in `apps/desktop-client/src-tauri`, which now completes successfully in the validated WSL environment;
- recorded the remaining `xcap v0.0.12` future-incompatibility warning as a non-blocking note rather than leaving `RB-013` open.

---

## 6. Closure Rule

This residual backlog is considered decomposed correctly only when:

- every `OPEN-001` through `OPEN-013` has a backlog ticket;
- every ticket has a named owner group and expected closure evidence;
- rollout blockers are explicit and not mixed with product completion work;
- the central residual register can point to this backlog as the execution source of truth.
