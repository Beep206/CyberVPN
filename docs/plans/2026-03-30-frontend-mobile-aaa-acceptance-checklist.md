# Frontend Mobile AAA Acceptance Checklist

## Goal

This checklist defines the final acceptance gate required before the frontend can be described as `AAA-level mobile-ready` in a real release context.

Passing code-level gates is necessary, but not sufficient. `AAA` requires:

- stable mobile interaction architecture
- real-device verification on the priority matrix
- visual quality sign-off
- post-deploy telemetry sanity

## Current Status

Engineering foundation is already in place:

- Tasks 1-9 of the mobile adaptation plan are complete
- mobile regression gate exists
- mobile bundle budget gate exists
- touch, safe-area, keyboard, and capability tiers are implemented

This means the project is `AAA-ready in code`, but not yet `AAA-confirmed in production reality` until the checklist below is passed.

## Pass Definition

The frontend may be called `AAA mobile-ready` only if all four sections pass:

1. Preflight automation
2. Real-device acceptance
3. Visual/design sign-off
4. Production telemetry sanity

If any P0 device or any critical route fails, status remains `AAA-ready`, not `AAA-confirmed`.

## 1. Preflight Automation

Run all of these from `frontend/`:

```bash
npm run lint
npm run build
npm run check:mobile
```

Pass criteria:

- all commands succeed
- `test:mobile-layout` is green
- `check:mobile-performance` is green
- no new mobile route exceeds its budget

## 2. Real-Device Acceptance

### P0 Devices

These are mandatory:

| Device | Browser / Shell | Orientation |
| --- | --- | --- |
| iPhone Safari | Safari | Portrait + Landscape |
| Large iPhone | Safari | Portrait |
| Android Chrome | Chrome | Portrait + Landscape |
| Small Android | Chrome | Portrait |
| Telegram WebView | Telegram Mini App shell | Portrait |

### P1 Devices

These should pass before calling the rollout complete:

| Device | Browser / Shell | Orientation |
| --- | --- | --- |
| Tablet Portrait | Safari or Chrome | Portrait |
| Tablet Landscape | Safari or Chrome | Landscape |

### Critical Routes

These routes must be verified on every P0 device:

- `/dashboard`
- `/servers`
- `/users`
- `/pricing`
- `/features`
- `/download`
- `/contact`
- `/privacy`
- `/terms`
- `/api`
- `/docs`
- `/login`
- `/register`
- `/forgot-password`

### Route-Level Checks

For every critical route, confirm:

- first scroll works immediately after load
- no primary reading path is trapped inside nested scroll
- sticky header or sticky action does not overlap browser chrome or notch
- overlays open and close without leaving scroll locked
- content does not clip horizontally in portrait mode
- first actionable CTA is reachable without hover
- keyboard open/close does not hide submit actions or break layout
- reduced/minimal visual tiers still look intentional, not broken

### Dashboard-Specific Checks

- mobile menu has a single clear trigger
- header controls remain tappable with one hand
- data cards and tables are readable without forced horizontal scroll
- returning from overlays restores the expected scroll position

### Long-Form Content Checks

For `/privacy`, `/terms`, `/api`, `/docs`:

- document scroll remains primary
- sidebar/index does not become the only scrollable region
- anchor navigation lands on the correct content section
- long reading sessions do not cause stuck overlays or jumpy scroll

### Auth / Form Checks

For `/login`, `/register`, `/forgot-password`, `/contact`:

- iOS does not zoom inputs on focus
- keyboard does not obscure submit controls
- focus states remain visible
- validation and error messaging remain readable after keyboard transitions

### Telegram WebView Checks

These are mandatory before claiming `AAA`:

- initial render is stable
- no `matchMedia` / viewport capability crash
- scroll lock works after opening and closing overlays
- safe-area spacing is correct at top and bottom
- auth and contact forms remain usable inside the shell

## 3. Visual / Design Sign-Off

This section is about quality, not just correctness.

For each P0 device class, capture screenshots for:

- dashboard
- pricing
- features
- docs
- contact
- login

Pass criteria:

- branding still feels intentional and premium
- typography hierarchy remains clear on small screens
- background visuals do not overpower content
- reduced/minimal tiers still feel designed, not “fallback-only”
- no obvious “desktop UI squeezed into mobile”

If a screen is merely functional but visually compromised, it does not pass `AAA`.

## 4. Production Telemetry Sanity

After deployment, verify:

- mobile Web Vitals stay within expected range
- no spike in client errors for mobile Safari, Android Chrome, or Telegram WebView
- no overlay-lock or scroll-restoration regressions in session replay / logs
- no route-specific bundle drift beyond the budget gate baseline

Minimum telemetry review window:

- first 24 hours after deploy

If the deploy is fresh and telemetry has not been observed yet, the release is still `provisionally AAA-ready`, not `fully AAA-confirmed`.

## Final Sign-Off Template

Use this exact outcome language:

### If everything passed

`The frontend is AAA-confirmed for mobile release.`

### If code/tests passed, but device sweep is incomplete

`The frontend is AAA-ready in engineering, pending final real-device acceptance.`

### If any P0 device failed

`The frontend is not yet AAA on mobile; release is blocked on P0 acceptance failures.`

## Recommended Final Sequence

1. Run `npm run check:mobile`
2. Run `npm run build`
3. Execute P0 device sweep
4. Capture screenshot sign-off set
5. Deploy
6. Review first 24h telemetry
7. Mark status as `AAA-confirmed`
