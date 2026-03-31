# Mobile QA Matrix

## Goal

Provide a fixed verification matrix for the frontend mobile adaptation rollout so regressions are checked against real device classes instead of ad hoc spot checks.

## Required Device Classes

| Device Class | Browser / Shell | Orientation | Priority |
| --- | --- | --- | --- |
| iPhone Safari | Safari | Portrait + Landscape | P0 |
| Large iPhone | Safari | Portrait | P0 |
| Android Chrome | Chrome | Portrait + Landscape | P0 |
| Small Android | Chrome | Portrait | P0 |
| Tablet Portrait | Safari or Chrome | Portrait | P1 |
| Tablet Landscape | Safari or Chrome | Landscape | P1 |
| Telegram WebView | Telegram Mini App shell | Portrait | P0 |

## Required Route Coverage

| Route Group | Representative Routes |
| --- | --- |
| Dashboard | `/dashboard`, `/servers`, `/users`, `/analytics` |
| Marketing | `/`, `/pricing`, `/features`, `/download`, `/contact` |
| Content-heavy | `/privacy`, `/terms`, `/api`, `/docs` |
| Auth | `/login`, `/register`, `/forgot-password` |
| Miniapp | `/miniapp/home`, `/miniapp/plans`, `/miniapp/profile` |

## Verification Checklist Per Device

1. Scroll
   - Page scroll starts immediately after load.
   - No trapped inner scroll on the primary reading path.
   - Opening and closing overlays restores scroll correctly.

2. Chrome and Safe Area
   - Sticky headers and bottom actions do not overlap notches or browser chrome.
   - Landscape layout still exposes primary navigation and the first content block.

3. Input and Keyboard
   - Focusing inputs does not create clipped content or unreachable CTAs.
   - iOS does not zoom inputs unexpectedly.
   - Forms remain usable after keyboard open/close.

4. Dense Data
   - Tables or dashboard summaries remain readable without horizontal clipping.
   - Primary actions are reachable with one hand in portrait mode.

5. Visual Fidelity
   - Brand styling remains intact.
   - Reduced or minimal motion tiers still preserve hierarchy and polish.
   - Background visuals never break content contrast.

6. Performance
   - First meaningful content is visible before non-critical ambient visuals settle.
   - No obvious animation hitching during scroll.
   - Route remains interactive under network fluctuation or app resume.

## Release Gate

A mobile rollout is not ready unless all P0 device classes pass:

- Dashboard scroll and navigation
- Pricing / marketing readability
- Docs / privacy / terms long-form reading
- Auth form interaction
- Telegram WebView compatibility

## Automated Gates

- `frontend/src/__tests__/mobile-layout-regressions.test.tsx`
  Verifies that the critical mobile routes still use the agreed layout contract and do not silently reintroduce `h-screen`, nested scroll ownership, or missing capability/touch-safe patterns.

- `frontend/scripts/mobile-performance-budget.mjs`
  Reads Next build diagnostics from `.next/diagnostics/route-bundle-stats.json`, recomputes gzip first-load JS for monitored routes, and fails when route budgets drift above the accepted mobile baseline.

- `npm run test:mobile-layout`
  Runs the route-contract regression suite only.

- `npm run check:mobile-performance`
  Runs the executable mobile bundle budget gate only after a production build.

- `npm run check:mobile`
  Runs both automated gates together for release readiness.
