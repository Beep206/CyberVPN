# CYBA-631 Manual Flow Audit Report

Дата: `2026-06-10`
Issue: [CYBA-631](/CYBA/issues/CYBA-631)
Parent: [CYBA-630](/CYBA/issues/CYBA-630)
Prepared by: `qa-lead-flow-mapper`

## Executive Summary

CYBA-631 is complete as a read-only QA triage deliverable. The 20 CYBA-630 user-reported points are mapped to routes, components/APIs/events, severity, evidence status, and owner child issues.

No source code, dependencies, `.env`, API contracts, migrations, business logic, production data, payment data, Telegram secrets, cookies, JWT, refresh tokens, or passwords were changed or stored.

Context7 docs checked: N/A - QA/read-only report and manual UI/business-flow findings; code changes не выполнялись.

## Deliverables

- `docs/qa/manual-flow-audit/2026-06-10-cyba-631/flow-map.md`
- `docs/qa/manual-flow-audit/2026-06-10-cyba-631/coverage-matrix.md`
- `docs/qa/manual-flow-audit/2026-06-10-cyba-631/manual-flow-audit-report.md`

## Coverage Result

| Category | Count | Notes |
|---|---:|---|
| Total CYBA-630 points | 20 | All points covered as `CYBA-630-01` through `CYBA-630-20`. |
| Source-confirmed / source-candidate | 14 | Enough for owner handoff, but not all are final runtime bugs. |
| Current fix candidates needing runtime proof | 3 | Language/timezone labels, notification toggle knob, user menu localization/display name. |
| Needs safe runtime evidence | 5 | Logout, dashboard dimming, support notification delivery, provisioning correctness, Telegram binding. |
| Product gaps | 4 | Settings IA, currency icons, subscriptions grouping/filtering, active sessions vs VPN device-limit semantics. |
| Confirmed P0 | 0 | None found in this read-only pass. |

## Severity Normalization

P1 candidates:

- `CYBA-630-01`: public UID/internal UUID exposure on customer surfaces.
- `CYBA-630-07`: customer logout/session ejection, pending safe customer auth proof.
- `CYBA-630-11`: support reply notification delivery, pending safe support fixture.
- `CYBA-630-12`: provisioning pending despite active/working VPN, pending state fixture.
- `CYBA-630-20`: Telegram binding failure, pending safe bot/staging evidence.

P2 focus:

- Settings IA/delete flow/security modal localization.
- Public/cabinet header navigation and disabled notification behavior.
- Subscription URL display request with security review.
- Active sessions using VPN entitlement limit semantics.
- Notification badge empty-panel mismatch.

P3 / product polish:

- Currency selector affordance.
- Plan catalog grouping/filtering.
- Notification outside-click close.
- Dashboard subscription switcher visual dimming if screenshot confirms contrast issue.

## Recommended Fix Order

1. [CYBA-633](/CYBA/issues/CYBA-633): public UID contract and customer/admin display replacement. This reduces identity/privacy risk and affects multiple surfaces.
2. [CYBA-634](/CYBA/issues/CYBA-634), [CYBA-640](/CYBA/issues/CYBA-640), [CYBA-639](/CYBA/issues/CYBA-639): logout, account deletion, 2FA/password/anti-phishing safety and security review.
3. [CYBA-635](/CYBA/issues/CYBA-635): support reply notification delivery plus badge/panel semantics.
4. [CYBA-636](/CYBA/issues/CYBA-636): provisioning state correctness for active subscription/VPN config.
5. [CYBA-637](/CYBA/issues/CYBA-637): Telegram binding with safe bot fixture and sanitized logs.
6. [CYBA-632](/CYBA/issues/CYBA-632): frontend shell/settings/header/i18n/product UX items that are not blocked by backend/security contracts.
7. [CYBA-638](/CYBA/issues/CYBA-638): final release evidence after A-G owners provide MR/pipeline/test/evidence links.

## Bugs, Gaps, And Not-Tested Areas

Confirmed source-level bugs or mismatches:

- Internal UUID-like identifiers are still used in customer account/profile/header display paths.
- Delete-account action leaves cabinet and is labelled as privacy flow.
- Security modals still contain hardcoded English.
- Public authenticated header uses disabled notification button and relative user-menu links.
- Notification badge can count conversations while the notification panel renders empty.
- Notification dropdown has no outside-click close path.

Product gaps:

- Settings page IA is still a large combined page.
- Currency selector needs better visual affordance.
- Subscription catalog needs grouping/filtering.
- Active web sessions should not be framed as VPN device entitlement usage if product policy says the limit applies only to VPN devices.

Blocked or not safely tested here:

- Customer logout session revocation/ejection.
- Support reply -> customer notification delivery for real/safe ticket.
- Active VPN but pending provisioning mismatch.
- Telegram bot binding failure.
- Dashboard switcher dimming screenshot comparison.

## Evidence Bar

The matrix respects the QA evidence bar:

- P0/P1 candidates are not marked as fully reproduced without screenshot/network/stronger evidence.
- Existing evidence references are sanitized packs only.
- No secrets, cookies, JWT, refresh tokens, passwords, `.env` values, payment secrets, production PII, production customer data, or real Telegram `initData` were stored.
- Findings are separated from product gaps and blocked/not-tested areas.

## Handoff To Child Owners

| Child issue | Handoff |
|---|---|
| [CYBA-632](/CYBA/issues/CYBA-632) | Own settings IA, header/public header layout, i18n screenshots, currency UX, plan catalog UX, notification outside-click if implemented in frontend shell. |
| [CYBA-633](/CYBA/issues/CYBA-633) | Own numeric public UID allocator/API/display contract; verify no customer-facing UUID remains. |
| [CYBA-634](/CYBA/issues/CYBA-634) | Own logout/delete/security account flows and safe auth evidence; coordinate with [CYBA-639](/CYBA/issues/CYBA-639) and [CYBA-640](/CYBA/issues/CYBA-640). |
| [CYBA-635](/CYBA/issues/CYBA-635) | Own support reply notification delivery, realtime/SSE/sync, badge/panel semantics, public-header notification parity. |
| [CYBA-636](/CYBA/issues/CYBA-636) | Own service-state/provisioning correctness and Remnawave/provider state reconciliation evidence. |
| [CYBA-637](/CYBA/issues/CYBA-637) | Own Telegram binding, safe bot fixture, sanitized bot/browser evidence; currently blocked until safe test path is available. |
| [CYBA-638](/CYBA/issues/CYBA-638) | Consume this matrix and child evidence after A-G complete. |

## Verification Performed

This heartbeat verified artifact creation and matrix coverage only. No browser/dev-server run was started because the issue deliverable is QA triage/matrix and several P1 candidates need child-owned safe fixtures.

Required local checks for this deliverable:

- `test -f docs/qa/manual-flow-audit/2026-06-10-cyba-631/flow-map.md`
- `test -f docs/qa/manual-flow-audit/2026-06-10-cyba-631/coverage-matrix.md`
- `test -f docs/qa/manual-flow-audit/2026-06-10-cyba-631/manual-flow-audit-report.md`
- `rg -n "CYBA-630-(0[1-9]|1[0-9]|20)" docs/qa/manual-flow-audit/2026-06-10-cyba-631/coverage-matrix.md`

## Final Disposition

CYBA-631 can be marked `done`: the QA triage and reproduction matrix deliverable is complete, all 20 parent points are covered, child owners and next actions are explicit, evidence is sanitized, and remaining runtime proof belongs to the active child implementation/QA issues.
