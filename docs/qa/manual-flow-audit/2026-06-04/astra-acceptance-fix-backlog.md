# CYBA-462 Astra Acceptance And Fix Backlog Proposal

Date: 2026-06-05T05:32:00Z
Parent issue: [CYBA-451](/CYBA/issues/CYBA-451)
Input report: `docs/qa/manual-flow-audit/2026-06-04/final-scribe-summary.md`

## Decision

Accept CYBA-451 as QA audit complete. Do not accept CyberVPN as real-prod ready.

This decision closes the audit workflow, not the release. It does not authorize production deploy, production secret usage, production data access, direct push to main, or merge to main.

## Acceptance Basis

Accepted:

- All recursive worker/fix/retest issues except the Astra/parent closure path are done.
- Final Scribe evidence summary exists and is readable without verbal context.
- Major P1 auth/session/security findings found during the audit were either resolved and retested, or explicitly carried into residual risk/backlog.
- No pending approvals remain.
- Evidence handling remains sanitized.

Not accepted as release-ready:

- Automated release-readiness gate [CYBA-455](/CYBA/issues/CYBA-455) is FAIL.
- Business-flow fixture coverage remains incomplete for client subscriptions, wallet/payment/referral, VPN/service access and Telegram Mini App signed/config states.
- Partner business-flow coverage beyond auth/session remains incomplete.
- Branch/worktree/MR review is still outstanding before any merge.

## Required P0/P1 Fix Backlog Before Production Go/No-Go

1. Turn CYBA-455 automated release gates green, or get explicit Board approval for any scoped-out gate.
2. Resolve frontend/admin/partner generated OpenAPI/type drift and rerun type-sensitive conformance checks.
3. Resolve backend ruff errors, pytest collection conflicts, required settings/env setup, Redis-dependent conformance failures and backend conformance login failures.
4. Provide approved safe fixture pack for client active/trial/expired subscriptions, non-empty wallet/payment history, referral/promo/partner-code outcomes, subscription-backed Mini App config, VPN service state, service identity and device credential shapes.
5. Provide approved partner stage/runtime fixture pack for dashboard, codes, finance, attribution, role-boundary and withdrawal/business flows.
6. Define safe payment and VPN provisioning test policy: checkout commit/payment capture and VPN config delivery must be either sandbox-tested with no real capture/provider secrets or explicitly out of scope by Board approval.
7. Inspect all GitLab branches/MRs and the dirty worktree, resolve discussions, run CI and only then consider merge under Autonomy Policy v1.
8. Re-run final Scribe/Astra acceptance after green CI and complete fixture coverage.

## P2 / Follow-Up Backlog

- Finish remaining localization/responsive/accessibility polish from CYBA-460 where not already merged.
- Track dependency hygiene, including the existing moderate PostCSS advisory via Next noted during child validation.
- Normalize all final evidence under the canonical `docs/qa/manual-flow-audit/2026-06-04/evidence/` tree if desired for archive consistency.

## Operational Constraints

Until the P0/P1 backlog is complete:

- Real-prod readiness status: NO-GO.
- Merge to main: NO-GO.
- Production deploy: NO-GO.
- Production secrets/customer/payment data: forbidden.
- Allowed next work: fix backlog implementation on feature branches, sanitized local/stage QA, CI, GitLab MR review, and explicit Board approval requests where required.

## Final CYBA-462 Disposition

CYBA-462 can close as accepted audit/backlog proposal. CYBA-451 can close as QA audit complete only if its final comment preserves the production NO-GO and backlog constraints above.
