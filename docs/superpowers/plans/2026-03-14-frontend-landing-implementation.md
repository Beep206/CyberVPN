# Implementation Plan: Frontend Landing Redesign (Anti-DPI Focus)

**Design Doc Reference:** `docs/superpowers/specs/2026-03-14-frontend-landing-redesign.md`
**Date:** March 14, 2026
**Tech Stack:** Next.js 16 (App Router), Tailwind CSS 4, Motion, next-intl (39 locales).

---

## Phase 1: Localization & Data Schema
**Goal:** Prepare the translation files with new technical keys.

- [ ] **Task 1.1:** Update `frontend/messages/en-EN/landing.json`.
    - Add `hero.protocol_badge`, `hero.cta_telegram`, `hero.cta_app`.
    - Replace `features` descriptions with technical specs (Reality, 10Gbps, RAM-only).
    - Add new sections: `how_it_works`, `comparison_table`, `status_board`, `quick_start`, `network_stats`.
- [ ] **Task 1.2:** Update `frontend/messages/ru-RU/landing.json` (Mirror of Task 1.1).
- [ ] **Task 1.3:** Propagate new keys to other 37 locales (using placeholder or auto-translation script to avoid build errors).

---

## Phase 2: Shared UI Components
**Goal:** Build the atomic units for the new sections.

- [ ] **Task 2.1:** Create `frontend/src/shared/ui/comparison-table.tsx`.
    - Features: Responsive design, Matrix Green highlights for CyberVPN column.
- [ ] **Task 2.2:** Create `frontend/src/shared/ui/status-badge-live.tsx`.
    - Features: Pulsing indicator, real-time data look (Mock for now).
- [ ] **Task 2.3:** Create `frontend/src/shared/ui/tech-data-grid.tsx`.
    - Features: Low-noise, high-density grid for Cipher/Transport/Uplink info.

---

## Phase 3: Widget Refactoring
**Goal:** Integrate new components into functional widgets.

- [ ] **Task 3.1:** Refactor `LandingHero` (`frontend/src/widgets/landing-hero.tsx`).
    - Change headline/subtitle to use new i18n keys.
    - Add `StatusBadge` above the headline with "PROTOCOL: VLESS-REALITY".
    - Update CTA buttons to "Telegram" and "App Store/Play Store".
- [ ] **Task 3.2:** Refactor `LandingFeatures` (`frontend/src/widgets/landing-features.tsx`).
    - Map new `featureConfig` based on the Design Doc (Stealth, Backbone, RAM-only, etc.).
- [ ] **Task 3.3:** Create `LandingTechnical` widget.
    - Integrate `ComparisonTable` and `TechSpecsGrid`.
- [ ] **Task 3.4:** Create `QuickStart` widget.
    - 3-step guide for Telegram Bot activation.

---

## Phase 4: Page Assembly & Polish
**Goal:** Finalize the main page layout.

- [ ] **Task 4.1:** Update `frontend/src/app/[locale]/page.tsx`.
    - Reorder sections: Hero -> Features -> How It Works -> Comparison -> Status -> SpeedTunnel -> Pricing -> QuickStart.
- [ ] **Task 4.2:** Animations & Transitions.
    - Ensure smooth scroll using Lenis.
    - Add ScrambleText effect to technical stats.
- [ ] **Task 4.3:** Responsive & RTL Check.
    - Verify layout on mobile.
    - Check RTL support for Arabic, Hebrew, Persian, Urdu, and Kurdish.

---

## Phase 5: Testing & Validation
- [ ] **Task 5.1:** Run `npm run lint`.
- [ ] **Task 5.2:** Run `npm run build`.
- [ ] **Task 5.3:** E2E Check: Verify CTA buttons point to correct URLs (Telegram Bot/App links).

---

## Deployment Strategy
1. Apply i18n changes first (Backwards compatible).
2. Deploy UI components to a dev-branch for visual review.
3. Final merge to main.
