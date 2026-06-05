# CYBA-451 Manual Flow Audit Evidence Zone

Date: `2026-06-04`

Owner: `qa-lead-flow-mapper`

Source issue: [CYBA-454](/CYBA/issues/CYBA-454)

Parent audit: [CYBA-451](/CYBA/issues/CYBA-451)

## Purpose

This directory is the approved QA evidence intake zone for the manual flow audit. It is for sanitized browser evidence only: screenshots, trace/video references, console/network notes, and bug packets that can be safely linked from the final audit report.

Do not store production secrets, real customer/payment data, raw auth state, raw Telegram `initData`, raw cookies, JWTs, refresh tokens, `.env` values, passwords, OTPs, passkey challenges, VPN config URLs, or payment secrets here.

## Canonical Structure

```text
docs/qa/manual-flow-audit/2026-06-04/evidence/
  README.md
  capture-protocol.md
  sanitizer-rules.md
  evidence-index.md
  rejected-artifacts.md
  bug-packets/
    BUG-PACKET-TEMPLATE.md
```

When real evidence is accepted, use these subtrees:

```text
screenshots/<surface>/<flow>/<case-id>/
traces/<surface>/<flow>/<case-id>/
videos/<surface>/<flow>/<case-id>/
console-notes/<surface>/<flow>/<case-id>.md
network-notes/<surface>/<flow>/<case-id>.md
bug-packets/<case-id>.md
```

`surface` values:

- `client-frontend`
- `partner-portal`
- `admin-panel`
- `cross-surface`

## Evidence Gate

Evidence is accepted only when:

- it was captured in local/staging/test data, not production customer/payment data;
- it has an `evidence-index.md` entry;
- it follows `sanitizer-rules.md`;
- the issue/bug packet includes exact steps, expected result, actual result, environment, role/state, severity, and sanitized evidence;
- P0/P1 entries include a screenshot or stronger sanitized artifact;
- any rejected unsafe material is listed in `rejected-artifacts.md`.

## Current Status

The evidence intake structure, sanitizer rules, and bug packet template are ready. No raw Playwright auth state, HAR, trace, video, cookie jar, or storage snapshot was committed in this setup heartbeat.

Context7 docs checked: unavailable - Context7 quota exceeded. Fallback official docs checked: Playwright screenshots, traces, videos, and network/HAR behavior at `playwright.dev`.
