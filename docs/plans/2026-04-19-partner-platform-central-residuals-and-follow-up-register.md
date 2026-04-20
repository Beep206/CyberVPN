# CyberVPN Partner Platform Central Residuals And Follow-Up Register

**Date:** 2026-04-19  
**Status:** central residual and follow-up register  
**Purpose:** collect the implementation tails, deferred seams, environment blockers, and rollout-blocking sign-off obligations that were discovered across `Phase 0` through `Phase 8`, so they are not left scattered across commentary, decomposition notes, and phase exit evidence.

---

## 1. How To Read This Register

This register tracks two kinds of items:

- seams that were identified as non-final during an earlier phase and later closed in a subsequent slice;
- seams and residuals that still remain open after `Phase 8`.

Status meanings:

- `closed later` = discovered earlier, then explicitly closed by a later phase or package;
- `open non-blocking` = does not block development baseline closure, but still needs a named follow-up;
- `open rollout-blocking` = broad activation, cutover, or sign-off may not proceed until it is resolved;
- `by design` = not a bug or hidden debt, but an explicit boundary that should not be misread as feature completeness.

This document does not replace phase-specific evidence packs. It points to them and centralizes what remained implicit or scattered.

---

## 2. Carry-Over Seams That Were Later Closed

| ID | Original seam | First captured in | Later closure |
|---|---|---|---|
| `CARRY-001` | `partner_payout_accounts` needed to become a first-class canonical entity instead of a half-documented ops-only object | architecture/data/API review round before implementation | closed by canonical data-model/API alignment and later `Phase 4 / T4.3` implementation |
| `CARRY-002` | `payment_dispute` needed to remain the canonical dispute object, with `chargeback` as lifecycle outcome instead of a second truth | architecture/API review round before implementation | closed by `Phase 2 / T2.5` and reinforced in `Phase 8 / T8.2` via `dispute_case` overlay rules |
| `CARRY-003` | partner portal initially had only read visibility and local placeholders for compliance and case surfaces | `Phase 6` decomposition and `Phase 6` exit evidence | backend canonical overlays closed in `T6.4` and `T8.2`; portal no longer depends on synthetic backend placeholders for reads |
| `CARRY-004` | pilot governance lacked owner acknowledgements, rollback drills, and explicit go/no-go control | `Phase 8 / T8.5` baseline | closed by `Phase 8 / T8.6` hardening and the production-readiness bundle |
| `CARRY-005` | `Phase 8` broad activation gates needed explicit signed readiness and exit-evidence artifacts | `Phase 8 / T8.5-T8.6` operational hardening | closed by `T8.7` readiness bundle and `T8.8` exit evidence |

These items are listed here so later readers do not mistake them for still-open architecture gaps.

---

## 3. Open Residuals After Phase 8

| ID | Residual | Current status | Backlog item | Why it is still open | Canonical source | Expected closure path |
|---|---|---|---|---|---|---|
| `OPEN-001` | partner portal dedicated workflow action rails for `traffic_declarations` and `creative_approvals` | closed later | `RB-001` | this was open after `Phase 8` because partner portal only exposed read visibility on top of canonical compliance overlays | [2026-04-18-partner-platform-phase-6-execution-ticket-decomposition.md](2026-04-18-partner-platform-phase-6-execution-ticket-decomposition.md), [partner-platform-phase6-exit-evidence.md](../testing/partner-platform-phase6-exit-evidence.md) | closed by `RB-001`: workspace-scoped POST rails, portal submission UX, and backend/portal validation coverage on top of canonical `T8.2` APIs |
| `OPEN-002` | richer partner inbox and workflow actions on top of canonical `review_requests` and `cases` | closed later | `RB-002` | this was open after `Phase 8` because the portal had routing and read visibility but no canonical partner-operable workflow actions on workspace cases and review requests | [2026-04-18-partner-platform-phase-6-execution-ticket-decomposition.md](2026-04-18-partner-platform-phase-6-execution-ticket-decomposition.md) | closed by `RB-002`: workspace-scoped response and ready-for-ops rails, persisted thread events, partner portal inbox actions, and backend/portal validation coverage on top of canonical partner workspace routes |
| `OPEN-003` | canonical lane-membership and lane-readiness UX in partner portal | closed later | `RB-003` | lane capability started as documented/runtime-only posture, but the dedicated backend-owned `programs` surface was completed only in a later residual-closure slice | [2026-04-18-partner-platform-phase-6-execution-ticket-decomposition.md](2026-04-18-partner-platform-phase-6-execution-ticket-decomposition.md), [2026-04-19-partner-platform-open-residuals-execution-backlog.md](2026-04-19-partner-platform-open-residuals-execution-backlog.md) | closed by `RB-003`: canonical workspace programs API, partner portal programs surface, targeted backend/partner validation, and residual register sync |
| `OPEN-004` | explicit workspace switcher UX on top of canonical `partner-workspaces/me` | closed later | `RB-004` | runtime fallback selection existed, but the explicit canonical workspace-navigation UX landed only in a later residual-closure slice | [2026-04-18-partner-platform-phase-6-execution-ticket-decomposition.md](2026-04-18-partner-platform-phase-6-execution-ticket-decomposition.md), [2026-04-19-partner-platform-open-residuals-execution-backlog.md](2026-04-19-partner-platform-open-residuals-execution-backlog.md) | closed by `RB-004`: explicit workspace switcher surfaces in desktop/mobile portal shell, host-scoped persisted selection, route-aware switching tests, and runtime-hook validation |
| `OPEN-005` | richer export scheduling and reporting affordances in partner portal | closed later | `RB-005` | canonical reporting overlays existed after `Phase 8`, but export scheduling and richer lifecycle UX were still missing from the portal surface | [2026-04-18-partner-platform-phase-6-execution-ticket-decomposition.md](2026-04-18-partner-platform-phase-6-execution-ticket-decomposition.md), [partner-platform-phase7-exit-evidence.md](../testing/partner-platform-phase7-exit-evidence.md) | closed by `RB-005`: backend-owned scheduling rail, workflow-event audit trail, richer portal lifecycle UX, and backend/partner validation coverage on canonical `Phase 7` reporting contracts |
| `OPEN-006` | consolidated admin maker-checker action rail inside customer operations | closed later | `RB-006` | this was open after `Phase 8` because admin customer operations had canonical read aggregation but no consolidated action rail over payout-account verification/suspension and payout-instruction approve/reject flows | [2026-04-18-partner-platform-phase-6-execution-ticket-decomposition.md](2026-04-18-partner-platform-phase-6-execution-ticket-decomposition.md), [2026-04-19-partner-platform-open-residuals-execution-backlog.md](2026-04-19-partner-platform-open-residuals-execution-backlog.md) | closed by `RB-006`: canonical backend action route, role-scoped action overlays in admin customer operations, maker-checker preservation on underlying settlement use cases, and targeted backend/admin validation coverage |
| `OPEN-007` | richer admin case, dispute-evidence, and review-queue workflow components | closed later | `RB-007` | this was open after `Phase 8` because admin had only inspection baseline and no dedicated internal workflow rail for canonical risk queue and dispute-case actions | [2026-04-18-partner-platform-phase-6-execution-ticket-decomposition.md](2026-04-18-partner-platform-phase-6-execution-ticket-decomposition.md) | closed by `RB-007`: internal `security/review-queue` workflow console, canonical dispute-case actions inside customer operations, and targeted backend/admin validation coverage on existing risk/dispute contracts |
| `OPEN-008` | finance-grade export and download affordances from admin customer operations | closed later | `RB-008` | evidence was inspectable after `RB-007`, but finance operators still lacked backend-owned export/download affordances inside the customer-operations rail | [2026-04-18-partner-platform-phase-6-execution-ticket-decomposition.md](2026-04-18-partner-platform-phase-6-execution-ticket-decomposition.md) | closed by `RB-008`: canonical admin attachment endpoints for workspace, statement, payout-instruction, and payout-execution evidence packs, plus settlement-card download affordances and targeted backend/admin validation coverage |
| `OPEN-009` | combined `frontend` Vitest worker issue around `cssstyle -> @asamuzakjp/css-color` | closed later | `RB-009` | this was open because combined frontend/browser-oriented Vitest runs crashed at worker bootstrap before test execution, so official-web evidence relied on targeted lint and narrow contract packs | [partner-platform-phase6-exit-evidence.md](../testing/partner-platform-phase6-exit-evidence.md), [partner-platform-phase8-production-readiness-bundle.md](../testing/partner-platform-phase8-production-readiness-bundle.md) | closed by `RB-009`: frontend Vitest switched to `happy-dom`, previously blocked packs now start and execute, and the old worker-bootstrap blocker is retired even though some miniapp tests still expose ordinary application/test debt |
| `OPEN-010` | repo-wide `npm audit --omit=dev` advisories in `@hono/node-server`, `brace-expansion`, `follow-redirects`, `hono`, `path-to-regexp` | closed later | `RB-010` | this was open because the repository carried a stale transitive dependency set across root, `admin`, and `frontend`, even though forward semver-compatible safe versions were already available | [partner-platform-phase8-production-readiness-bundle.md](../testing/partner-platform-phase8-production-readiness-bundle.md), [partner-platform-phase8-exit-evidence.md](../testing/partner-platform-phase8-exit-evidence.md) | closed by `RB-010`: root and workspace dependency trees were refreshed to safe forward versions, fresh `npm audit --omit=dev` returned zero vulnerabilities at root plus `admin/frontend/partner`, and affected validation packs were rerun with any remaining failures explicitly classified as pre-existing non-audit debt |
| `OPEN-011` | human sign-off is still pending for phase evidence packs and `Phase 8` activation artifacts | open rollout-blocking | `RB-011` | engineering evidence is assembled, and the canonical sign-off tracker now exists, but named human approvers have not yet completed the approval sheet | [partner-platform-phase8-production-readiness-bundle.md](../testing/partner-platform-phase8-production-readiness-bundle.md), [partner-platform-phase8-exit-evidence.md](../testing/partner-platform-phase8-exit-evidence.md), [partner-platform-broad-activation-sign-off-tracker.md](../testing/partner-platform-broad-activation-sign-off-tracker.md) | complete named sign-offs in the tracker before pilot widening or broad activation |
| `OPEN-012` | production command inventory is explicit, but live rollout windows still require filled runtime parameters, named owners, and signed rehearsal records | open rollout-blocking | `RB-012` | the base command families are now centralized and a named activation record exists, but the production window registration record still contains pending live values for the exact activation scope | [2026-04-19-partner-platform-environment-command-inventory-sheet.md](2026-04-19-partner-platform-environment-command-inventory-sheet.md), [BA-2026-04-19-01-production-window-registration.md](../evidence/partner-platform/2026-04-19/phase8-production-readiness/BA-2026-04-19-01-production-window-registration.md), [2026-04-17-partner-platform-environment-specific-cutover-runbooks.md](2026-04-17-partner-platform-environment-specific-cutover-runbooks.md) | fill the production window registration record with runtime values, named owners, linked rehearsal evidence, and exact approval scope before live cutover |
| `OPEN-013` | local desktop Rust validation via `cargo check` was blocked in WSL by missing system packages `javascriptcoregtk-4.1` and `libsoup-3.0` | closed later | `RB-013` | desktop distributable build had already passed, but the local Rust bootstrap detail was not previously centralized in docs | execution commentary during `Phase 7 / T7.5` | closed by `RB-013`: explicit WSL bootstrap note, desktop README pointer, installed Ubuntu prerequisites, and successful `cargo check` in `apps/desktop-client/src-tauri` |
| `OPEN-014` | full-suite and live-migration proof were intentionally replaced by targeted gate packs during phase closure | by design | phase gates were closed by canonical targeted evidence packs, not by monorepo-wide brute-force runs; this is acceptable for engineering closure but still means pre-cutover rehearsals must use the operational packages, not rely on old per-ticket commentary | [2026-04-17-partner-platform-operational-readiness-package.md](2026-04-17-partner-platform-operational-readiness-package.md), [2026-04-17-partner-platform-rehearsal-logs-and-evidence-archive-template.md](2026-04-17-partner-platform-rehearsal-logs-and-evidence-archive-template.md) | use rehearsal and cutover packages as the mandatory pre-live proof, not ad-hoc full-suite expectations |

---

## 4. Items That Are Not Debt But Must Stay Explicit

| ID | Boundary | Current status | Why it matters |
|---|---|---|---|
| `BOUNDARY-001` | official-web legal surfaces remain marketing-first; canonical acceptance is customer-authenticated and storefront-bound | by design | prevents the team from accidentally inventing fake acceptance semantics on official marketing pages |
| `BOUNDARY-002` | `Phase 8` readiness bundle and `Phase 8` exit evidence are separate artifacts | by design | one approves broad activation readiness, the other closes the engineering and governance phase gate |
| `BOUNDARY-003` | targeted evidence packs, not every repo-wide command, are the canonical phase-gate proof | by design | keeps the program operating on reproducible contract packs instead of informal “I ran a lot of commands” closure |

---

## 5. What This Register Changes Operationally

After this document:

- residuals are no longer considered “only in commentary”;
- later execution work should update this register when an open item is closed;
- new follow-up seams should be added here and then linked from the relevant phase, not left only in ad-hoc progress notes.

This register is intentionally small and program-level. It should track real cross-slice residuals, not every local TODO.
