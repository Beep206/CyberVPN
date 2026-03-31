# Frontend Mobile Adaptation Audit

## Goal

Bring the Next.js frontend to a stable mobile baseline without sacrificing the current cyberpunk visual identity or desktop performance.

## Execution Backlog

The implementation backlog for this audit is documented in `docs/plans/2026-03-30-frontend-mobile-adaptation-implementation.md`.

## Implementation Status

- Task 1 complete: mobile standards, telemetry enrichment, and device bucketing were added.
- Task 2 complete: document scroll ownership and shared overlay locking were restored.
- Task 3 complete: dashboard shell, header, and navigation now follow a deterministic mobile contract.
- Tasks 4-6 complete: split shells, long-form content routes, and dense data views now have mobile-safe layouts.
- Task 7 complete: capability-based visual tiers now gate premium 3D and motion.
- Task 8 complete: touch targets, safe-area handling, keyboard-safe forms, and auth flows were standardized.
- Task 9 complete: automated mobile regression and budget gates now exist through `mobile-layout-regressions.test.tsx` and `mobile-performance-budget.mjs`.

## Executive Summary

The mobile breakage is systemic, not page-local. The frontend repeatedly combines:

- global `body` scroll suppression
- route-level `h-screen` / `100vh` shells
- nested `overflow-y-auto` content areas
- sticky/fixed chrome
- large decorative 3D canvases

That pattern works only while viewport height, browser chrome, and scroll ownership remain predictable. On mobile browsers they do not, so the app ends up with trapped scroll, clipped content, broken sticky behavior, and compressed layouts.

## High Severity Findings

1. Global scroll is disabled at the root.
   - [`frontend/src/app/layout.tsx:44`](/home/beep/projects/VPNBussiness/frontend/src/app/layout.tsx#L44) applies `overflow-hidden` to `body`.
   - This forces every route to invent its own scroll container and is the main reason mobile scroll becomes fragile.

2. Dashboard owns scroll through a fixed-height shell instead of document flow.
   - [`frontend/src/app/[locale]/(dashboard)/layout.tsx:57`](/home/beep/projects/VPNBussiness/frontend/src/app/[locale]/(dashboard)/layout.tsx#L57) uses `h-screen overflow-hidden`.
   - [`frontend/src/app/[locale]/(dashboard)/layout.tsx:83`](/home/beep/projects/VPNBussiness/frontend/src/app/[locale]/(dashboard)/layout.tsx#L83) pushes scroll into `<main>`.
   - [`frontend/src/app/[locale]/(dashboard)/dashboard/page.tsx:16`](/home/beep/projects/VPNBussiness/frontend/src/app/[locale]/(dashboard)/dashboard/page.tsx#L16) adds another `min-h-screen`, compounding height calculations.

3. Several content-heavy marketing pages use the same anti-pattern with inner scroll containers.
   - [`frontend/src/widgets/features/features-dashboard.tsx:18`](/home/beep/projects/VPNBussiness/frontend/src/widgets/features/features-dashboard.tsx#L18)
   - [`frontend/src/widgets/privacy/privacy-dashboard.tsx:39`](/home/beep/projects/VPNBussiness/frontend/src/widgets/privacy/privacy-dashboard.tsx#L39)
   - [`frontend/src/widgets/terms/terms-dashboard.tsx:41`](/home/beep/projects/VPNBussiness/frontend/src/widgets/terms/terms-dashboard.tsx#L41)
   - [`frontend/src/widgets/api/api-dashboard.tsx:28`](/home/beep/projects/VPNBussiness/frontend/src/widgets/api/api-dashboard.tsx#L28)
   - [`frontend/src/widgets/download/download-dashboard.tsx:17`](/home/beep/projects/VPNBussiness/frontend/src/widgets/download/download-dashboard.tsx#L17)

4. Modal and sheet scroll locking conflicts with route-level scroll ownership.
   - [`frontend/src/shared/ui/modal.tsx:77`](/home/beep/projects/VPNBussiness/frontend/src/shared/ui/modal.tsx#L77) mutates `document.body.style.overflow`.
   - Dashboard content is already scrolling inside `<main>`, so body locking is not the real scroll owner there.
   - Result: mobile overlays can leave the interface in a “stuck” state.

## Medium Severity Findings

1. Header chrome is too dense for narrow widths.
   - [`frontend/src/widgets/terminal-header.tsx:17`](/home/beep/projects/VPNBussiness/frontend/src/widgets/terminal-header.tsx#L17) uses `pl-20`, fixed `h-16`, and keeps multiple control groups active.
   - [`frontend/src/widgets/terminal-header-controls.tsx:30`](/home/beep/projects/VPNBussiness/frontend/src/widgets/terminal-header-controls.tsx#L30) has no mobile compaction strategy beyond hiding the login button.
   - Mobile sidebar also introduces a second fixed trigger at [`frontend/src/widgets/mobile-sidebar.tsx:88`](/home/beep/projects/VPNBussiness/frontend/src/widgets/mobile-sidebar.tsx#L88).

2. Desktop sidebars are width-fixed and height-fixed.
   - [`frontend/src/widgets/cyber-sidebar.tsx:31`](/home/beep/projects/VPNBussiness/frontend/src/widgets/cyber-sidebar.tsx#L31) uses `w-64 h-screen fixed`.
   - This is fine on desktop, but it drives the entire layout model and makes mobile branching expensive.

3. Tables are mobile-hostile by default.
   - [`frontend/src/widgets/pricing/feature-matrix.tsx:27`](/home/beep/projects/VPNBussiness/frontend/src/widgets/pricing/feature-matrix.tsx#L27) forces `min-w-[600px]`.
   - [`frontend/src/widgets/users-data-grid.tsx:130`](/home/beep/projects/VPNBussiness/frontend/src/widgets/users-data-grid.tsx#L130) uses a fixed `w-64` search field inside a row header.
   - Shared table wrapper allows overflow, but not mobile-specific density, column priority, or alternate card/list rendering.

4. Some content navigation assumes document scroll while the page actually uses nested scroll.
   - [`frontend/src/widgets/docs-sidebar.tsx:34`](/home/beep/projects/VPNBussiness/frontend/src/widgets/docs-sidebar.tsx#L34) creates an inner scroll area.
   - [`frontend/src/widgets/docs-sidebar.tsx:62`](/home/beep/projects/VPNBussiness/frontend/src/widgets/docs-sidebar.tsx#L62) scrolls `window`, which diverges from the real scroll container in several screens.

## Performance Findings

1. The project already has a good capability gate, but it is not applied consistently.
   - [`frontend/src/shared/hooks/use-motion-capability.ts:40`](/home/beep/projects/VPNBussiness/frontend/src/shared/hooks/use-motion-capability.ts#L40) checks pointer quality, memory, cores, bandwidth, and reduced motion.
   - [`frontend/src/app/[locale]/(dashboard)/dashboard/components/DashboardGlobe.tsx:27`](/home/beep/projects/VPNBussiness/frontend/src/app/[locale]/(dashboard)/dashboard/components/DashboardGlobe.tsx#L27) uses this idea manually for the globe.
   - Most other large 3D screens do not gate nearly as aggressively.

2. Several mobile layouts still mount heavy 3D scenes even when the visual value is mostly atmospheric.
   - Contact page keeps a full `<Canvas>` stack at [`frontend/src/widgets/contact-form.tsx:271`](/home/beep/projects/VPNBussiness/frontend/src/widgets/contact-form.tsx#L271).
   - The same file mixes `min-h-screen`, sticky 3D, and runtime effects at [`frontend/src/widgets/contact-form.tsx:68`](/home/beep/projects/VPNBussiness/frontend/src/widgets/contact-form.tsx#L68) and [`frontend/src/widgets/contact-form.tsx:264`](/home/beep/projects/VPNBussiness/frontend/src/widgets/contact-form.tsx#L264).

3. There are 28 files with `h-screen`, 10 with `calc(100vh`, 101 with `overflow-hidden`, and 30 with `overflow-y-auto`.
   - The issue is architectural repetition, not a couple of broken breakpoints.

## What Should Not Change

- Do not flatten the visual language into generic mobile cards.
- Do not remove neon typography, scanlines, or all motion globally.
- Do not degrade desktop layouts to fix mobile.
- Do not solve everything with `overflow-x-auto`.

## Recommended Mobile Architecture

1. Restore document scroll as the default.
   - `html/body` should scroll again.
   - Only lock body scroll for true modal states.

2. Convert fixed-height route shells into content-first flow.
   - Replace route-level `h-screen` with `min-h-screen` or `min-h-dvh`.
   - Reserve inner scroll containers for genuinely isolated panes only.

3. Split visual and content layers.
   - Treat 3D/canvas layers as optional ambience.
   - On mobile, prefer static or lower-cost variants unless the scene is core to comprehension.

4. Make navigation chrome responsive by intent.
   - One mobile header system.
   - One menu trigger.
   - Fewer simultaneous controls in the top bar.

5. Introduce mobile data-density variants.
   - Table -> horizontal scroll only as fallback.
   - Primary mobile target should be stacked rows, card rows, or column-priority collapse.

## AAA+ Additions

1. Add a real mobile viewport contract.
   - Standardize on `dvh` / `svh` usage rules.
   - Support safe areas with `env(safe-area-inset-*)`.
   - Explicitly handle virtual keyboard resize on iOS Safari, Chrome Android, and Telegram WebView.

2. Define a touch-first interaction system.
   - Set minimum target sizes, touch spacing, and thumb-zone placement rules.
   - Replace hover-only affordances with tap/press states.
   - Audit all sticky buttons, filters, and menu triggers for one-handed use.

3. Add mobile typography and density tokens.
   - Create smaller but still premium display scales for hero headings, HUD labels, chips, and tables.
   - Prevent iOS input zoom by keeping interactive text at mobile-safe sizes.
   - Define when desktop monospace density must switch to simplified mobile copy density.

4. Add motion tiers instead of a binary on/off model.
   - `full`, `reduced`, and `minimal` visual modes based on capability.
   - 3D scenes should have static poster, low-cost canvas, and full desktop variants.
   - Route transitions and ambient effects should degrade before scroll performance degrades.

5. Add route-level performance budgets.
   - Set budgets for JS, image weight, font count, and long-task thresholds on mobile.
   - Track LCP, INP, CLS, and scroll smoothness separately for dashboard, marketing, and miniapp routes.
   - Fail CI when premium visuals exceed defined mobile budgets.

6. Add poor-network and resume-state behavior.
   - Define skeletons, deferred panels, and lazy hydration rules for mobile.
   - Ensure back/forward cache, resume-from-background, and flaky connection states do not reset scroll or overlay state.
   - Make 3D and non-critical widgets load after primary content is usable.

7. Add a mobile-specific QA matrix.
   - Minimum devices: iPhone Safari, Android Chrome, small Android, large iPhone Pro Max, tablet portrait, tablet landscape, Telegram WebView.
   - Verify portrait/landscape, notch devices, low-memory devices, and reduced-motion preference.
   - Capture screenshots for the critical routes in every supported mobile shell.

8. Add premium mobile accessibility requirements.
   - Test keyboard and screen-reader paths even on mobile layouts.
   - Keep contrast stable over animated/glowing backgrounds.
   - Provide reduced-motion and low-effects behavior that still preserves hierarchy and brand feel.

9. Add observability for mobile regressions.
   - Break down Web Vitals and runtime errors by viewport bucket, device class, OS/browser, and route.
   - Log overlay lockups, layout shifts after keyboard open, and long animation frames.
   - Treat mobile regressions as first-class incidents, not visual polish issues.

## Phased Implementation Plan

### Phase 0: Establish AAA+ mobile standards and measurement

- Define viewport, safe-area, keyboard, touch-target, and density rules in the design system.
- Create route-level mobile performance budgets and acceptance criteria.
- Add a device matrix for iOS Safari, Android Chrome, tablets, and Telegram WebView.
- Instrument mobile Web Vitals and runtime diagnostics before layout refactors begin.

### Phase 1: Unblock scroll and viewport correctness

- Remove root `body overflow-hidden`.
- Refactor dashboard shell to use document scroll.
- Replace `100vh`/`h-screen` with `dvh` or content flow where needed.
- Normalize modal/sheet scroll lock against the new single scroll owner.

### Phase 2: Rebuild mobile page composition

- Dashboard: simplify header, unify menu behavior, reduce fixed chrome.
- Marketing split screens: convert to vertical-first mobile stacking.
- Docs/privacy/terms/api: eliminate nested-scroll assumptions on small screens.

### Phase 3: Preserve design while reducing mobile cost

- Create mobile-safe visual presets for 3D scenes.
- Reuse `useMotionCapability` instead of per-page ad hoc heuristics.
- Keep desktop full-fidelity visuals.

### Phase 4: Add regression protection

- Add viewport-based tests, not just class-name checks.
- Add mobile screenshots or visual diff coverage for the core routes.
- Add interaction tests for scroll, overlays, and sticky headers.

### Phase 5: Harden premium mobile UX details

- Add touch-first states, thumb-zone placement checks, and safe-area-aware sticky actions.
- Create mobile typography and density tokens for HUD, data grids, and hero sections.
- Introduce mobile variants for dense tables, filters, and dashboards.

### Phase 6: Lock in mobile performance and observability

- Enforce route-level performance budgets in CI.
- Add capability-based motion tiers and 3D fallbacks.
- Monitor Web Vitals and runtime regressions by mobile device class and route.

## Test Audit

- `npm run lint` passes.
- `npm run build` passes.
- Dedicated mobile regression coverage now exists in `frontend/src/__tests__/mobile-layout-regressions.test.tsx`.
- Dedicated mobile budget coverage now exists in `frontend/scripts/mobile-performance-budget.mjs`.
- The supporting harness now lives in:
  - `frontend/src/test/mobile-viewport.ts`
  - `frontend/src/test/mobile-route-checklist.ts`
- This means the project now has a focused automated guardrail for route contract drift and mobile bundle growth, instead of relying only on ad hoc widget tests.

## Security / Reliability Notes

- `npm audit --omit=dev` reports `0 vulnerabilities`.
- One intentional `dangerouslySetInnerHTML` use exists in JSON-LD output at `frontend/src/shared/lib/json-ld.tsx`; that is acceptable for structured data.
- No obvious leaked keys were found in source files from the quick scan.

## Final Assessment

The correct strategy is not “fix some breakpoints.” The frontend needs a mobile layout contract:

- document scroll is primary
- viewport units are used deliberately
- overlays lock the true scroll owner
- 3D is progressive enhancement
- dense desktop data views have mobile variants

That contract is now backed by explicit automated gates:

- `frontend/src/__tests__/mobile-layout-regressions.test.tsx`
- `frontend/scripts/mobile-performance-budget.mjs`
- `npm run test:mobile-layout`
- `npm run check:mobile-performance`

If these remain green alongside the QA matrix, mobile usability can keep improving without flattening the brand or letting performance regress silently.
