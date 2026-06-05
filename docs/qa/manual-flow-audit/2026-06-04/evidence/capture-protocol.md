# Sanitized Browser Evidence Capture Protocol

Date: `2026-06-04`

Source issue: [CYBA-454](/CYBA/issues/CYBA-454)

## Scope

Use this protocol for browser evidence collected for [CYBA-451](/CYBA/issues/CYBA-451) across:

- client frontend;
- partner portal;
- admin panel;
- cross-surface flows.

This protocol is for local, staging, or test data only. Do not use it against production customer/payment data unless Board gives explicit approval for a specific run.

## Pre-Capture Checklist

- Confirm environment: `local`, `staging`, or named `test`.
- Confirm user role/state: anonymous, customer, partner owner, partner operator, admin owner, admin operator, support, finance, viewer, blocked user, expired user, or other explicit state.
- Confirm locale and viewport before capture.
- Use a fresh browser context or test profile for each role/state.
- Do not save Playwright `storageState`, persistent browser profiles, cookies, localStorage snapshots, or raw auth/session dumps.
- Avoid screenshots that expose browser devtools storage/cookies, `.env` values, payment secrets, Telegram `initData`, production PII, or VPN subscription/config URLs.
- If testing auth/payment/security flows, prefer synthetic accounts and synthetic payment/provider IDs.

## Artifact Naming

Use stable case IDs so screenshots, trace/video references, console notes, and bug packets can be joined later:

```text
<case-id>__<surface>__<role>__<locale>__<viewport>__<result>__<timestamp>
```

Example:

```text
MF-ADM-LOGIN-001__admin-panel__admin-owner__en-EN__desktop-1440__fail__20260604T160000Z.png
```

Allowed `result` values:

- `pass`
- `fail`
- `blocked`
- `not-tested`
- `info`

## Capture Levels

### Baseline Visual Evidence

Use screenshots for visible UI state, responsive layout, i18n/RTL rendering, a11y-visible regressions, and product-flow state transitions.

Minimum metadata:

- route;
- surface;
- browser/channel;
- viewport;
- locale;
- user role/state;
- data fixture;
- timestamp;
- capture command or manual capture method.

### P0/P1 Reproduction Evidence

P0/P1 evidence must include screenshot or stronger sanitized evidence.

Required packet:

- exact steps to reproduce;
- expected result;
- actual result;
- environment;
- browser/channel and viewport;
- user role/state;
- severity and rationale;
- sanitized screenshot/video/trace reference;
- console notes if relevant;
- network notes if relevant;
- data-safety review result.

### Trace, Video, And Network Evidence

Playwright traces, videos, and HAR/network artifacts can include sensitive request data. Treat every raw trace, video, HAR, browser profile, cookie jar, and storage snapshot as unsafe until manually reviewed.

Rules:

- do not commit raw `storageState`;
- do not commit raw trace/HAR/video if it contains auth headers, cookies, JWTs, refresh tokens, payment/customer data, or Telegram `initData`;
- prefer sanitized console/network markdown notes over raw HAR;
- if a trace/video is needed for P0/P1 triage, keep only the sanitized artifact in this directory and record the review in `evidence-index.md`;
- if an artifact is rejected, record the reason in `rejected-artifacts.md`.

## Evidence Index Update

Every accepted artifact needs one row in `evidence-index.md` with:

- evidence ID;
- related issue/finding;
- surface;
- flow;
- role/state;
- environment;
- locale;
- viewport;
- artifact type;
- relative path;
- sensitivity review;
- status.

## Docs Evidence Line

Context7 docs checked: unavailable - Context7 quota exceeded. Fallback official docs checked: Playwright screenshots, trace viewer/tracing, videos, and network/HAR docs at `playwright.dev`.
