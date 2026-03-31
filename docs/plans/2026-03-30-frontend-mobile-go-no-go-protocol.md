# Frontend Mobile Go / No-Go Protocol

## Goal

This is the shortest operational protocol for deciding whether the frontend may move from `AAA-ready in engineering` to `AAA-confirmed`.

Use this after the local gates are green.

## Entry Condition

The following must already be green:

```bash
cd frontend
npm run lint
npm run build
npm run check:mobile
```

If any of these fail, stop. Status is immediately `NO-GO`.

## P0 Device Set

Run this protocol on:

- `iPhone Safari`
- `Large iPhone Safari`
- `Android Chrome`
- `Small Android Chrome`
- `Telegram WebView`

## Critical Routes

Open and verify:

- `/dashboard`
- `/pricing`
- `/features`
- `/docs`
- `/contact`
- `/login`

If time allows, extend to:

- `/download`
- `/privacy`
- `/terms`
- `/api`
- `/register`
- `/forgot-password`

## 10-Minute Sweep

### Minute 1-2: Core Scroll

On each device:

- open `/dashboard`
- confirm the first scroll works immediately
- open mobile navigation and close it
- confirm scroll is still functional

Immediate `NO-GO` if:

- page does not scroll
- overlay closes but leaves the page locked
- content clips horizontally in portrait

### Minute 3-4: Forms

Check `/login` and `/contact`:

- focus the first input
- confirm iOS does not zoom
- open the keyboard
- confirm the primary submit action stays reachable
- trigger validation and check text readability

Immediate `NO-GO` if:

- keyboard hides the submit action
- layout jumps badly during keyboard transitions
- validation becomes unreadable

### Minute 5-6: Long Reading

Check `/docs`:

- scroll a long section
- use the sidebar or anchor navigation
- confirm the target section lands correctly
- confirm the content column remains the primary reading scroll

Immediate `NO-GO` if:

- nested scroll traps the reading path
- anchor navigation lands incorrectly
- sticky UI overlaps content or browser chrome

### Minute 7-8: Marketing Quality

Check `/pricing` and `/features`:

- confirm hero content fits cleanly in portrait
- confirm first CTA is reachable without hover
- confirm reduced/minimal visual tier still feels intentional

Immediate `NO-GO` if:

- layout looks like squeezed desktop UI
- primary CTA is hard to tap
- fallback visual tier looks broken rather than simplified

### Minute 9: Telegram WebView

Inside the Telegram shell:

- open `/miniapp` or the highest-risk flow available
- open and close one overlay
- confirm safe-area spacing
- confirm scroll remains usable

Immediate `NO-GO` if:

- capability detection crashes
- safe-area padding is visibly wrong
- overlay handling breaks scroll

### Minute 10: Screenshot Sign-Off

Capture screenshots for:

- `dashboard`
- `pricing`
- `features`
- `docs`
- `contact`
- `login`

If any one of these looks merely functional but not premium, keep status at `AAA-ready`, not `AAA-confirmed`.

## Decision Rule

### GO

Mark the release as:

`AAA-confirmed for mobile release.`

Only if:

- all local gates are green
- all P0 devices pass
- screenshots are approved
- telemetry is reviewed after deploy

### CONDITIONAL GO

Mark the release as:

`AAA-ready in engineering, pending final real-device acceptance.`

Use this only when code and automation are green, but the device sweep or telemetry window is not yet complete.

### NO-GO

Mark the release as:

`The frontend is not yet AAA on mobile; release is blocked on P0 acceptance failures.`

Use this if any P0 device shows:

- broken scroll
- broken keyboard flow
- broken overlay lock/unlock
- clipped layout
- visibly compromised premium design

## Post-Deploy Confirmation

Even after `GO`, the release becomes fully final only after the first `24h` telemetry window shows:

- no abnormal mobile Web Vitals drift
- no spike in client errors
- no scroll-lock or overlay regressions
- no budget drift beyond the current baseline
