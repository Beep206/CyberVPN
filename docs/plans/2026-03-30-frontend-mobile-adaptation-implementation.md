# Frontend Mobile Adaptation Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Bring the frontend to a premium mobile baseline with correct scrolling, robust viewport behavior, touch-first UX, and capability-aware performance without degrading the desktop cyberpunk design.

**Architecture:** Fix the mobile experience in layers, not page-by-page hacks. First establish a mobile contract and a single scroll owner, then refactor the dashboard and repeated split-screen shells onto shared responsive primitives, then add mobile data-density variants, capability-based 3D degradation, and finally lock the gains in with regression tests, budgets, and observability. Use @nextjs-senior-dev, @cache-components, @code-review, and @security-review-2 during execution, and fetch official library docs via Context7 before touching Next.js, React, Motion, Tailwind, R3F, or TanStack APIs.

**Tech Stack:** Next.js 16.1.5, React 19.2, TypeScript 5.9, Tailwind CSS 4.1, Motion 12, @react-three/fiber 9, next-intl 4.7, TanStack Table 8, Vitest, Testing Library

---

## Strict Execution Order

1. Task 1 is mandatory before any layout refactor.
2. Task 2 must land before Tasks 3-8.
3. Task 3 must land before Tasks 4-6.
4. Tasks 4, 5, and 6 can run in parallel only after Task 3 is complete.
5. Task 7 depends on Tasks 4-6 being complete enough to profile real mobile behavior.
6. Task 8 depends on Tasks 2-7.
7. Task 9 is the final acceptance gate and must not be skipped.

## Non-Negotiable Rules

- Do not reintroduce `body`-level `overflow-hidden` as a general layout strategy.
- Do not use `100vh`/`h-screen` for route shells unless the route is truly full-screen and owns scroll intentionally.
- Do not solve narrow layouts with blanket `overflow-x-auto`.
- Do not flatten the visual language into generic mobile UI.
- Do not ship new motion or 3D behavior without capability gating.
- Before modifying library code patterns, fetch fresh official docs via Context7 per repo policy.

## Acceptance Gates

- Core routes must scroll correctly on iPhone Safari, Android Chrome, and Telegram WebView.
- No overlay may leave the page in a locked-scroll or broken-focus state.
- Dense data views must have a usable mobile presentation without horizontal clipping.
- Mobile visual fidelity must remain intentional, branded, and performant.
- `npm run lint`, targeted Vitest coverage, and production build must pass at the end.

---

### Task 1: Mobile Standards, Device Matrix, and Telemetry Baseline

**Blocked by:** nothing  
**Unlocks:** all later tasks

**Files:**
- Create: `docs/plans/2026-03-30-mobile-qa-matrix.md`
- Create: `frontend/src/shared/config/mobile-standards.ts`
- Create: `frontend/src/shared/lib/mobile-device-bucket.ts`
- Modify: `frontend/src/shared/lib/web-vitals.ts`
- Modify: `frontend/src/shared/ui/atoms/web-vitals-reporter.tsx`
- Modify: `frontend/src/app/globals.css`
- Test: `frontend/src/shared/lib/__tests__/mobile-device-bucket.test.ts`

**Step 1: Write the failing test for device bucketing**

- Add `frontend/src/shared/lib/__tests__/mobile-device-bucket.test.ts`.
- Cover:
  - iPhone Safari -> `mobile-touch`
  - Android Chrome low-memory -> `mobile-low-power`
  - tablet portrait -> `tablet-touch`
  - desktop fine pointer -> `desktop`

Run:

```bash
cd frontend && npm run test:run -- src/shared/lib/__tests__/mobile-device-bucket.test.ts
```

Expected: FAIL because the bucket helper does not exist yet.

**Step 2: Create the mobile standards source of truth**

- Add `frontend/src/shared/config/mobile-standards.ts` with:
  - mobile breakpoints policy
  - touch target minimums
  - safe-area spacing tokens
  - keyboard/viewport rules
  - acceptable mobile performance budgets
- Add `frontend/src/shared/lib/mobile-device-bucket.ts` to classify viewport + device capability for telemetry.

**Step 3: Extend telemetry to tag mobile context**

- Update `frontend/src/shared/lib/web-vitals.ts` to attach:
  - viewport bucket
  - device bucket
  - route group
  - reduced-motion state
- Update `frontend/src/shared/ui/atoms/web-vitals-reporter.tsx` to report the enriched payload.
- Add matching CSS custom properties and comments in `frontend/src/app/globals.css` for safe-area and mobile density tokens.

**Step 4: Create the QA matrix document**

- Add `docs/plans/2026-03-30-mobile-qa-matrix.md` with the minimum required matrix:
  - iPhone Safari
  - Android Chrome
  - small Android
  - large iPhone
  - tablet portrait
  - tablet landscape
  - Telegram WebView
- For each device, define:
  - routes to verify
  - scroll checks
  - overlay checks
  - keyboard checks
  - visual fidelity checks

**Step 5: Verify and commit**

Run:

```bash
cd frontend && npm run test:run -- src/shared/lib/__tests__/mobile-device-bucket.test.ts
cd frontend && npm run lint
```

Expected: PASS, then commit.

```bash
git add docs/plans/2026-03-30-mobile-qa-matrix.md frontend/src/shared/config/mobile-standards.ts frontend/src/shared/lib/mobile-device-bucket.ts frontend/src/shared/lib/web-vitals.ts frontend/src/shared/ui/atoms/web-vitals-reporter.tsx frontend/src/app/globals.css frontend/src/shared/lib/__tests__/mobile-device-bucket.test.ts
git commit -m "feat(frontend): add mobile standards and telemetry baseline"
```

---

### Task 2: Restore a Single Scroll Owner and Normalize Scroll Locking

**Blocked by:** Task 1  
**Unlocks:** Tasks 3-8

**Files:**
- Modify: `frontend/src/app/layout.tsx`
- Modify: `frontend/src/app/globals.css`
- Create: `frontend/src/shared/lib/scroll-lock.ts`
- Modify: `frontend/src/shared/ui/modal.tsx`
- Modify: `frontend/src/app/[locale]/miniapp/components/MiniAppBottomSheet.tsx`
- Modify: `frontend/src/app/providers/smooth-scroll-provider.tsx`
- Test: `frontend/src/shared/ui/__tests__/modal-scroll-lock.test.tsx`
- Test: `frontend/src/app/[locale]/miniapp/components/__tests__/MiniAppBottomSheet.test.tsx`

**Step 1: Write failing overlay lock tests**

- Add `frontend/src/shared/ui/__tests__/modal-scroll-lock.test.tsx`.
- Extend `frontend/src/app/[locale]/miniapp/components/__tests__/MiniAppBottomSheet.test.tsx`.
- Assert:
  - opening overlay applies a shared lock
  - nested overlay count is tracked
  - closing one overlay does not unlock if another remains open
  - closing the last overlay restores scroll cleanly

Run:

```bash
cd frontend && npm run test:run -- src/shared/ui/__tests__/modal-scroll-lock.test.tsx src/app/[locale]/miniapp/components/__tests__/MiniAppBottomSheet.test.tsx
```

Expected: FAIL because there is no shared scroll lock manager.

**Step 2: Create a shared scroll lock primitive**

- Add `frontend/src/shared/lib/scroll-lock.ts`.
- Implement:
  - reference-counted lock/unlock
  - `body` + `documentElement` synchronization
  - safe cleanup on unmount
  - optional interop with Lenis start/stop events

**Step 3: Remove root-level scroll suppression**

- Update `frontend/src/app/layout.tsx` to remove `overflow-hidden` from the root body class.
- Update `frontend/src/app/globals.css` so document scroll is the default again.
- Update `frontend/src/shared/ui/modal.tsx` and `frontend/src/app/[locale]/miniapp/components/MiniAppBottomSheet.tsx` to use `scroll-lock.ts` instead of direct DOM mutation.
- Verify `frontend/src/app/providers/smooth-scroll-provider.tsx` only manages smooth scrolling, not ownership of page scroll.

**Step 4: Verify the single scroll-owner model**

Run:

```bash
cd frontend && npm run test:run -- src/shared/ui/__tests__/modal-scroll-lock.test.tsx src/app/[locale]/miniapp/components/__tests__/MiniAppBottomSheet.test.tsx
cd frontend && npm run lint
```

Expected: PASS, and no direct `document.body.style.overflow` writes remain outside the shared utility.

**Step 5: Commit**

```bash
git add frontend/src/app/layout.tsx frontend/src/app/globals.css frontend/src/shared/lib/scroll-lock.ts frontend/src/shared/ui/modal.tsx frontend/src/app/[locale]/miniapp/components/MiniAppBottomSheet.tsx frontend/src/app/providers/smooth-scroll-provider.tsx frontend/src/shared/ui/__tests__/modal-scroll-lock.test.tsx frontend/src/app/[locale]/miniapp/components/__tests__/MiniAppBottomSheet.test.tsx
git commit -m "refactor(frontend): restore single scroll owner and shared overlay locking"
```

---

### Task 3: Refactor Dashboard Shell, Header, and Navigation for Mobile

**Blocked by:** Task 2  
**Unlocks:** Tasks 4-6

**Files:**
- Modify: `frontend/src/app/[locale]/(dashboard)/layout.tsx`
- Modify: `frontend/src/app/[locale]/(dashboard)/dashboard/page.tsx`
- Modify: `frontend/src/widgets/terminal-header.tsx`
- Modify: `frontend/src/widgets/terminal-header-controls.tsx`
- Modify: `frontend/src/widgets/cyber-sidebar.tsx`
- Modify: `frontend/src/widgets/mobile-sidebar.tsx`
- Test: `frontend/src/widgets/__tests__/terminal-header.test.tsx`
- Test: `frontend/src/widgets/__tests__/cyber-sidebar.test.tsx`
- Create: `frontend/src/widgets/__tests__/mobile-sidebar.test.tsx`

**Step 1: Rewrite failing tests around the real responsive contract**

- Fix `frontend/src/widgets/__tests__/terminal-header.test.tsx` so it renders the async server component correctly.
- Update `frontend/src/widgets/__tests__/cyber-sidebar.test.tsx` to match the current menu inventory instead of stale counts.
- Add `frontend/src/widgets/__tests__/mobile-sidebar.test.tsx` for:
  - single menu trigger ownership
  - dialog semantics
  - focus trap
  - close on overlay tap

Run:

```bash
cd frontend && npm run test:run -- src/widgets/__tests__/terminal-header.test.tsx src/widgets/__tests__/cyber-sidebar.test.tsx src/widgets/__tests__/mobile-sidebar.test.tsx
```

Expected: FAIL until the shell behavior is corrected.

**Step 2: Move dashboard from fixed-height shell to document-flow layout**

- Update `frontend/src/app/[locale]/(dashboard)/layout.tsx` to remove `h-screen` shell ownership and avoid nested page scroll where not strictly required.
- Ensure the main route content participates in document flow.
- Remove redundant `min-h-screen` + `overflow-hidden` combinations from `frontend/src/app/[locale]/(dashboard)/dashboard/page.tsx`.

**Step 3: Make mobile navigation intentional**

- Update `frontend/src/widgets/terminal-header.tsx` and `frontend/src/widgets/terminal-header-controls.tsx` to create a compact mobile header:
  - one primary menu trigger
  - condensed controls
  - no dead decorative header affordances on mobile
- Update `frontend/src/widgets/cyber-sidebar.tsx` and `frontend/src/widgets/mobile-sidebar.tsx` so desktop and mobile nav share structure but not conflicting fixed ownership.

**Step 4: Verify dashboard routes**

Run:

```bash
cd frontend && npm run test:run -- src/widgets/__tests__/terminal-header.test.tsx src/widgets/__tests__/cyber-sidebar.test.tsx src/widgets/__tests__/mobile-sidebar.test.tsx
cd frontend && npm run lint
cd frontend && npm run build
```

Expected: PASS, dashboard routes build cleanly, and mobile header/sidebar behavior is deterministic.

**Step 5: Commit**

```bash
git add frontend/src/app/[locale]/(dashboard)/layout.tsx frontend/src/app/[locale]/(dashboard)/dashboard/page.tsx frontend/src/widgets/terminal-header.tsx frontend/src/widgets/terminal-header-controls.tsx frontend/src/widgets/cyber-sidebar.tsx frontend/src/widgets/mobile-sidebar.tsx frontend/src/widgets/__tests__/terminal-header.test.tsx frontend/src/widgets/__tests__/cyber-sidebar.test.tsx frontend/src/widgets/__tests__/mobile-sidebar.test.tsx
git commit -m "refactor(frontend): rebuild dashboard shell for mobile flow"
```

---

### Task 4: Build a Shared Responsive Split-Screen Shell and Migrate Repeated Marketing Layouts

**Blocked by:** Task 3  
**Unlocks:** Task 7

**Files:**
- Create: `frontend/src/shared/ui/layout/responsive-split-shell.tsx`
- Modify: `frontend/src/widgets/features/features-dashboard.tsx`
- Modify: `frontend/src/widgets/download/download-dashboard.tsx`
- Modify: `frontend/src/widgets/status/status-dashboard.tsx`
- Modify: `frontend/src/widgets/contact-form.tsx`
- Modify: `frontend/src/widgets/pricing/pricing-dashboard.tsx`
- Test: `frontend/src/shared/ui/layout/__tests__/responsive-split-shell.test.tsx`

**Step 1: Write the failing shell tests**

- Add `frontend/src/shared/ui/layout/__tests__/responsive-split-shell.test.tsx`.
- Assert:
  - mobile stacks content before heavy visuals
  - desktop restores side-by-side layout
  - sticky/pinned visual panes do not own scroll on mobile
  - safe-area padding can be enabled

Run:

```bash
cd frontend && npm run test:run -- src/shared/ui/layout/__tests__/responsive-split-shell.test.tsx
```

Expected: FAIL because the shell does not exist.

**Step 2: Create the shared shell**

- Implement `frontend/src/shared/ui/layout/responsive-split-shell.tsx` with slots for:
  - header
  - primary content
  - visual pane
  - mobile order
  - desktop pinning
  - safe-area/sticky behavior

**Step 3: Migrate repeated split-screen routes**

- Refactor:
  - `frontend/src/widgets/features/features-dashboard.tsx`
  - `frontend/src/widgets/download/download-dashboard.tsx`
  - `frontend/src/widgets/status/status-dashboard.tsx`
  - `frontend/src/widgets/contact-form.tsx`
  - `frontend/src/widgets/pricing/pricing-dashboard.tsx`
- Remove local ad hoc `min-h-[calc(100vh-4rem)]`, `sticky`, and nested scroll hacks where the shared shell now owns composition.

**Step 4: Verify shell migrations**

Run:

```bash
cd frontend && npm run test:run -- src/shared/ui/layout/__tests__/responsive-split-shell.test.tsx
cd frontend && npm run lint
cd frontend && npm run build
```

Expected: PASS, with no route-level layout regressions from shell migration.

**Step 5: Commit**

```bash
git add frontend/src/shared/ui/layout/responsive-split-shell.tsx frontend/src/widgets/features/features-dashboard.tsx frontend/src/widgets/download/download-dashboard.tsx frontend/src/widgets/status/status-dashboard.tsx frontend/src/widgets/contact-form.tsx frontend/src/widgets/pricing/pricing-dashboard.tsx frontend/src/shared/ui/layout/__tests__/responsive-split-shell.test.tsx
git commit -m "refactor(frontend): introduce shared responsive split shell"
```

---

### Task 5: Remove Nested-Scroll Assumptions from Content-Heavy Documentation Routes

**Blocked by:** Task 3  
**Unlocks:** Task 7

**Files:**
- Modify: `frontend/src/widgets/privacy/privacy-dashboard.tsx`
- Modify: `frontend/src/widgets/terms/terms-dashboard.tsx`
- Modify: `frontend/src/widgets/api/api-dashboard.tsx`
- Modify: `frontend/src/widgets/docs-sidebar.tsx`
- Modify: `frontend/src/widgets/docs-container.tsx`
- Modify: `frontend/src/widgets/docs-content.tsx`
- Test: `frontend/src/widgets/__tests__/docs-sidebar.test.tsx`
- Create: `frontend/src/widgets/__tests__/content-shell-scroll.test.tsx`

**Step 1: Write the failing navigation and scroll tests**

- Add `frontend/src/widgets/__tests__/content-shell-scroll.test.tsx`.
- Extend `frontend/src/widgets/__tests__/docs-sidebar.test.tsx`.
- Assert:
  - anchor navigation uses the correct scroll owner
  - mobile content does not trap scroll inside inner panes
  - sidebar/table-of-contents becomes content-first on mobile

Run:

```bash
cd frontend && npm run test:run -- src/widgets/__tests__/docs-sidebar.test.tsx src/widgets/__tests__/content-shell-scroll.test.tsx
```

Expected: FAIL because these routes currently depend on nested scroll containers.

**Step 2: Refactor route shells to content-first mobile flow**

- Update `frontend/src/widgets/privacy/privacy-dashboard.tsx`, `frontend/src/widgets/terms/terms-dashboard.tsx`, and `frontend/src/widgets/api/api-dashboard.tsx` so mobile uses document flow first.
- Keep desktop pinned sidebars only where they are still useful and do not own mobile scroll.

**Step 3: Fix docs navigation ownership**

- Update `frontend/src/widgets/docs-sidebar.tsx`, `frontend/src/widgets/docs-container.tsx`, and `frontend/src/widgets/docs-content.tsx` so anchor movement targets the actual scroll container in each mode.
- Avoid `window.scrollTo` assumptions when a local container is the intended owner.

**Step 4: Verify documentation routes**

Run:

```bash
cd frontend && npm run test:run -- src/widgets/__tests__/docs-sidebar.test.tsx src/widgets/__tests__/content-shell-scroll.test.tsx
cd frontend && npm run lint
cd frontend && npm run build
```

Expected: PASS, and docs/privacy/terms/api routes no longer rely on trapped inner scroll on mobile.

**Step 5: Commit**

```bash
git add frontend/src/widgets/privacy/privacy-dashboard.tsx frontend/src/widgets/terms/terms-dashboard.tsx frontend/src/widgets/api/api-dashboard.tsx frontend/src/widgets/docs-sidebar.tsx frontend/src/widgets/docs-container.tsx frontend/src/widgets/docs-content.tsx frontend/src/widgets/__tests__/docs-sidebar.test.tsx frontend/src/widgets/__tests__/content-shell-scroll.test.tsx
git commit -m "refactor(frontend): remove nested mobile scroll from content-heavy routes"
```

---

### Task 6: Add Mobile Data-Density Variants for Tables and Dense Controls

**Blocked by:** Task 3  
**Unlocks:** Task 7

**Files:**
- Modify: `frontend/src/shared/ui/organisms/table.tsx`
- Create: `frontend/src/shared/ui/mobile-data-list.tsx`
- Modify: `frontend/src/widgets/servers-data-grid.tsx`
- Modify: `frontend/src/widgets/users-data-grid.tsx`
- Modify: `frontend/src/shared/ui/comparison-table.tsx`
- Modify: `frontend/src/widgets/pricing/feature-matrix.tsx`
- Modify: `frontend/src/app/[locale]/(dashboard)/partner/components/PartnerClient.tsx`
- Test: `frontend/src/widgets/__tests__/servers-data-grid.test.tsx`
- Create: `frontend/src/widgets/__tests__/users-data-grid.test.tsx`
- Create: `frontend/src/shared/ui/__tests__/mobile-data-list.test.tsx`

**Step 1: Write the failing responsive-density tests**

- Repair `frontend/src/widgets/__tests__/servers-data-grid.test.tsx` so it matches the real data source and async behavior.
- Add `frontend/src/widgets/__tests__/users-data-grid.test.tsx` and `frontend/src/shared/ui/__tests__/mobile-data-list.test.tsx`.
- Assert:
  - mobile view renders card/list rows instead of clipped tables for primary workflows
  - desktop still renders the dense table
  - search/filter controls wrap instead of forcing width overflow

Run:

```bash
cd frontend && npm run test:run -- src/widgets/__tests__/servers-data-grid.test.tsx src/widgets/__tests__/users-data-grid.test.tsx src/shared/ui/__tests__/mobile-data-list.test.tsx
```

Expected: FAIL because there is no mobile data-density path yet.

**Step 2: Add a shared mobile data-list primitive**

- Create `frontend/src/shared/ui/mobile-data-list.tsx`.
- Support:
  - label/value rows
  - status badges
  - action groups
  - priority fields
  - optional secondary meta rows

**Step 3: Migrate dense data views**

- Update:
  - `frontend/src/widgets/servers-data-grid.tsx`
  - `frontend/src/widgets/users-data-grid.tsx`
  - `frontend/src/shared/ui/comparison-table.tsx`
  - `frontend/src/widgets/pricing/feature-matrix.tsx`
  - `frontend/src/app/[locale]/(dashboard)/partner/components/PartnerClient.tsx`
- Keep horizontal scroll only as a fallback for truly unavoidable wide comparisons.

**Step 4: Verify data-density behavior**

Run:

```bash
cd frontend && npm run test:run -- src/widgets/__tests__/servers-data-grid.test.tsx src/widgets/__tests__/users-data-grid.test.tsx src/shared/ui/__tests__/mobile-data-list.test.tsx
cd frontend && npm run lint
```

Expected: PASS, with mobile-first dense data views no longer clipped or compressed.

**Step 5: Commit**

```bash
git add frontend/src/shared/ui/organisms/table.tsx frontend/src/shared/ui/mobile-data-list.tsx frontend/src/widgets/servers-data-grid.tsx frontend/src/widgets/users-data-grid.tsx frontend/src/shared/ui/comparison-table.tsx frontend/src/widgets/pricing/feature-matrix.tsx frontend/src/app/[locale]/(dashboard)/partner/components/PartnerClient.tsx frontend/src/widgets/__tests__/servers-data-grid.test.tsx frontend/src/widgets/__tests__/users-data-grid.test.tsx frontend/src/shared/ui/__tests__/mobile-data-list.test.tsx
git commit -m "feat(frontend): add mobile data-density variants"
```

---

### Task 7: Add Capability-Based Motion Tiers and 3D Fallbacks

**Blocked by:** Tasks 4, 5, 6  
**Unlocks:** Task 8

**Files:**
- Modify: `frontend/src/shared/hooks/use-motion-capability.ts`
- Create: `frontend/src/shared/hooks/use-visual-tier.ts`
- Modify: `frontend/src/app/[locale]/(dashboard)/dashboard/components/DashboardGlobe.tsx`
- Modify: `frontend/src/widgets/contact-form.tsx`
- Modify: `frontend/src/widgets/features/features-dashboard.tsx`
- Modify: `frontend/src/widgets/download/download-dashboard.tsx`
- Modify: `frontend/src/widgets/status/status-dashboard.tsx`
- Modify: `frontend/src/widgets/pricing/pricing-dashboard.tsx`
- Test: `frontend/src/3d/__tests__/performance-baseline.test.ts`
- Create: `frontend/src/shared/hooks/__tests__/use-visual-tier.test.ts`

**Step 1: Write the failing visual-tier tests**

- Add `frontend/src/shared/hooks/__tests__/use-visual-tier.test.ts`.
- Assert:
  - low-power mobile -> `minimal`
  - normal touch device -> `reduced`
  - desktop fine pointer + enough memory -> `full`
- Extend `frontend/src/3d/__tests__/performance-baseline.test.ts` to assert that mobile routes do not mount full-cost visuals by default.

Run:

```bash
cd frontend && npm run test:run -- src/shared/hooks/__tests__/use-visual-tier.test.ts src/3d/__tests__/performance-baseline.test.ts
```

Expected: FAIL because only partial capability gating exists today.

**Step 2: Add the shared visual tier model**

- Create `frontend/src/shared/hooks/use-visual-tier.ts`.
- Keep `frontend/src/shared/hooks/use-motion-capability.ts` as the low-level signal source.
- Define `full`, `reduced`, and `minimal` tiers.

**Step 3: Apply the tier model to heavy routes**

- Update:
  - `frontend/src/app/[locale]/(dashboard)/dashboard/components/DashboardGlobe.tsx`
  - `frontend/src/widgets/contact-form.tsx`
  - `frontend/src/widgets/features/features-dashboard.tsx`
  - `frontend/src/widgets/download/download-dashboard.tsx`
  - `frontend/src/widgets/status/status-dashboard.tsx`
  - `frontend/src/widgets/pricing/pricing-dashboard.tsx`
- Mobile behavior:
  - `minimal`: static gradients/posters only
  - `reduced`: lightweight visual layer, no premium continuous effects
  - `full`: current desktop-grade scene quality

**Step 4: Verify build and tests**

Run:

```bash
cd frontend && npm run test:run -- src/shared/hooks/__tests__/use-visual-tier.test.ts src/3d/__tests__/performance-baseline.test.ts
cd frontend && npm run lint
cd frontend && npm run build
```

Expected: PASS, and heavy scenes become progressive enhancement instead of mobile defaults.

**Step 5: Commit**

```bash
git add frontend/src/shared/hooks/use-motion-capability.ts frontend/src/shared/hooks/use-visual-tier.ts frontend/src/app/[locale]/(dashboard)/dashboard/components/DashboardGlobe.tsx frontend/src/widgets/contact-form.tsx frontend/src/widgets/features/features-dashboard.tsx frontend/src/widgets/download/download-dashboard.tsx frontend/src/widgets/status/status-dashboard.tsx frontend/src/widgets/pricing/pricing-dashboard.tsx frontend/src/3d/__tests__/performance-baseline.test.ts frontend/src/shared/hooks/__tests__/use-visual-tier.test.ts
git commit -m "feat(frontend): add capability-based visual tiers"
```

---

### Task 8: Harden Touch, Safe-Area, Keyboard, and Mobile Form Behavior

**Blocked by:** Task 7  
**Unlocks:** Task 9

**Files:**
- Modify: `frontend/src/app/globals.css`
- Modify: `frontend/src/components/ui/button.tsx`
- Modify: `frontend/src/widgets/terminal-header-controls.tsx`
- Modify: `frontend/src/features/language-selector/language-selector.tsx`
- Modify: `frontend/src/shared/ui/modal.tsx`
- Modify: `frontend/src/widgets/contact-form.tsx`
- Modify: `frontend/src/app/[locale]/(auth)/login/page.tsx`
- Modify: `frontend/src/app/[locale]/(auth)/register/page.tsx`
- Modify: `frontend/src/app/[locale]/(auth)/forgot-password/page.tsx`
- Test: `frontend/src/features/language-selector/__tests__/language-selector.test.tsx`
- Create: `frontend/src/shared/ui/__tests__/touch-targets.test.tsx`

**Step 1: Write the failing touch and form tests**

- Add `frontend/src/shared/ui/__tests__/touch-targets.test.tsx`.
- Extend or add `frontend/src/features/language-selector/__tests__/language-selector.test.tsx`.
- Assert:
  - minimum touch targets are respected
  - primary controls are reachable without hover
  - input font sizes do not trigger iOS zoom
  - modal and picker content fits within safe areas

Run:

```bash
cd frontend && npm run test:run -- src/shared/ui/__tests__/touch-targets.test.tsx src/features/language-selector/__tests__/language-selector.test.tsx
```

Expected: FAIL because touch and safe-area rules are not centralized.

**Step 2: Add mobile-safe interaction tokens**

- Update `frontend/src/app/globals.css` with:
  - safe-area CSS vars
  - touch target utilities
  - keyboard-safe bottom spacing
  - mobile form font-size rules
- Update `frontend/src/components/ui/button.tsx` so shared buttons can opt into touch-safe sizing.

**Step 3: Migrate high-risk interactive surfaces**

- Update:
  - `frontend/src/widgets/terminal-header-controls.tsx`
  - `frontend/src/features/language-selector/language-selector.tsx`
  - `frontend/src/shared/ui/modal.tsx`
  - `frontend/src/widgets/contact-form.tsx`
  - auth pages under `frontend/src/app/[locale]/(auth)/`
- Ensure sticky bottom actions and modal content respect safe areas and keyboard resizing.

**Step 4: Verify interaction and layout stability**

Run:

```bash
cd frontend && npm run test:run -- src/shared/ui/__tests__/touch-targets.test.tsx src/features/language-selector/__tests__/language-selector.test.tsx
cd frontend && npm run lint
```

Expected: PASS, with touch and keyboard resilience standardized instead of patched per component.

**Step 5: Commit**

```bash
git add frontend/src/app/globals.css frontend/src/components/ui/button.tsx frontend/src/widgets/terminal-header-controls.tsx frontend/src/features/language-selector/language-selector.tsx frontend/src/shared/ui/modal.tsx frontend/src/widgets/contact-form.tsx frontend/src/app/[locale]/(auth)/login/page.tsx frontend/src/app/[locale]/(auth)/register/page.tsx frontend/src/app/[locale]/(auth)/forgot-password/page.tsx frontend/src/features/language-selector/__tests__/language-selector.test.tsx frontend/src/shared/ui/__tests__/touch-targets.test.tsx
git commit -m "feat(frontend): harden touch, safe-area, and keyboard behavior"
```

---

### Task 9: Add Mobile Regression Gates, Performance Budgets, and Final Acceptance Audit

**Blocked by:** Task 8  
**Unlocks:** release readiness

**Files:**
- Modify: `frontend/package.json`
- Create: `frontend/src/test/mobile-viewport.ts`
- Create: `frontend/src/test/mobile-route-checklist.ts`
- Create: `frontend/src/__tests__/mobile-layout-regressions.test.tsx`
- Create: `frontend/scripts/mobile-performance-budget.mjs`
- Modify: `docs/plans/2026-03-30-mobile-qa-matrix.md`
- Modify: `docs/plans/2026-03-30-frontend-mobile-adaptation-audit.md`

**Step 1: Write the failing route-regression tests**

- Add:
  - `frontend/src/test/mobile-viewport.ts`
  - `frontend/src/test/mobile-route-checklist.ts`
  - `frontend/src/__tests__/mobile-layout-regressions.test.tsx`
- Cover:
  - dashboard shell
  - features
  - pricing
  - privacy
  - download
  - contact
  - docs/api

Run:

```bash
cd frontend && npm run test:run -- src/__tests__/mobile-layout-regressions.test.tsx
```

Expected: FAIL until the harness and acceptance matrix are wired correctly.

**Step 2: Add budget and regression tooling**

- Add `frontend/scripts/mobile-performance-budget.mjs`.
- Update `frontend/package.json` with scripts such as:
  - `test:mobile`
  - `perf:mobile`
  - `check:mobile`
- Keep the budget script simple:
  - parse build output
  - assert route chunk ceilings
  - fail on obvious mobile regressions

**Step 3: Lock the QA matrix and audit against reality**

- Update `docs/plans/2026-03-30-mobile-qa-matrix.md` with actual route-by-route pass criteria.
- Update `docs/plans/2026-03-30-frontend-mobile-adaptation-audit.md` with:
  - implemented status
  - remaining risks
  - routes still needing follow-up

**Step 4: Run the final gate**

Run:

```bash
cd frontend && npm run test:mobile
cd frontend && npm run perf:mobile
cd frontend && npm run lint
cd frontend && npm run build
```

Expected: all commands pass and the QA matrix can be executed as a release checklist.

**Step 5: Commit**

```bash
git add frontend/package.json frontend/src/test/mobile-viewport.ts frontend/src/test/mobile-route-checklist.ts frontend/src/__tests__/mobile-layout-regressions.test.tsx frontend/scripts/mobile-performance-budget.mjs docs/plans/2026-03-30-mobile-qa-matrix.md docs/plans/2026-03-30-frontend-mobile-adaptation-audit.md
git commit -m "chore(frontend): add mobile regression gates and performance budgets"
```

---

## Final Release Checklist

- Task 1 complete: mobile standards and telemetry exist.
- Task 2 complete: one scroll owner, shared overlay lock.
- Task 3 complete: dashboard shell and mobile nav are stable.
- Task 4 complete: split-screen marketing routes use the shared shell.
- Task 5 complete: content-heavy routes no longer trap mobile scroll.
- Task 6 complete: dense data views have mobile variants.
- Task 7 complete: capability-based 3D degradation is active.
- Task 8 complete: touch, safe-area, and keyboard behavior are standardized.
- Task 9 complete: regression tests and budgets are enforceable.

## Recommended Execution Mode

- Critical path: Tasks 1 -> 2 -> 3.
- Parallel wave 1: Tasks 4, 5, 6 after Task 3.
- Parallel wave 2: Task 7 after 4-6 stabilize.
- Final hardening: Tasks 8 -> 9.
