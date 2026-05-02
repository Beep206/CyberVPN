# Alerting, Ownership, Routing And Severity Policy

Status: draft
Owner: platform + engineering leadership
Last updated: 2026-04-25
Scope: project ownership, issue routing and alerting model
Depends on: `04-sentry-project-registry.md`, `08-tags-context-correlation-and-fingerprinting-contract.md`
Related paths: `runbooks/issue-triage-and-incident-playbook.md`

## Repo-local governance baseline

- `governance-registry.json` is now the machine-readable source of truth for logical team ownership, routing basis and baseline alert tiers.
- This registry is validated in CI before doc changes land.
- `planned_in_sentry` in that registry means the policy is frozen in-repo but not yet applied to the live self-hosted Sentry organization.

## Proposed ownership model

| Team | Surfaces |
| --- | --- |
| `web` | `frontend`, `admin`, `partner` |
| `core` | `backend`, `task-worker`, `telegram-bot` |
| `client-apps` | `cybervpn_mobile`, `desktop-client`, `android-tv` |
| `platform` | `node-fleet-controller`, `helix-adapter`, `helix-node` |

## Routing rules

- Route issues by project first.
- Use path or runtime-layer routing only when a project is intentionally split.
- Auto-assignment should be driven by project ownership and, later, CODEOWNERS when present.

## Severity model

### Incident-grade

- production regressions on auth, payment, provisioning or subscription flows
- crash spikes on mobile, desktop or Android TV
- backend and control-plane panics or widespread error spikes
- release-health regressions on packaged clients

### Non-incident default

- staging-only regressions
- isolated browser extension noise
- known retryable transient worker and bot failures below threshold

## Channel policy

- Start with GitHub integration, email and one production ops channel.
- Keep staging alerts minimal and release-blocking only.

## Governance carryover note

- Live alert routing is still a governance carryover item and is not required for `baseline_complete` runtime status.
- `Wave 4 / Step 1` froze the repo-local ownership and alert-tier baseline; `Wave 4 / Step 4` now tracks the remaining live alert-routing blocker per project inside `production-acceptance-registry.json`.
