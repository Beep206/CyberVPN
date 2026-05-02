# Sentry Project Registry

Status: draft
Owner: platform (proposed)
Last updated: 2026-04-25
Scope: all direct Sentry projects in the monorepo
Depends on: `01-target-architecture-and-scope.md`, `05-environment-and-release-contract.md`
Related paths: `surfaces/`, `../../plans/2026-04-24-sentry-rollout-tracker.md`

Production acceptance is tracked separately in `production-acceptance-registry.json`. This registry only describes direct Sentry projects and rollout baseline status.

## Proposed registry

| Project | Surface | Repo path | Proposed owner | DSN env var(s) | Release model | Rollout wave | Status |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `web-frontend` | customer web | `frontend/` | web | `NEXT_PUBLIC_SENTRY_DSN`, `SENTRY_DSN` | `frontend@<git-sha>` | 1 | baseline_complete |
| `web-admin` | admin web | `admin/` | web | `NEXT_PUBLIC_SENTRY_DSN`, `SENTRY_DSN` | `admin@<git-sha>` | 1 | baseline_complete |
| `web-partner` | partner web | `partner/` | web | `NEXT_PUBLIC_SENTRY_DSN`, `SENTRY_DSN` | `partner@<git-sha>` | 1 | baseline_complete |
| `backend-api` | FastAPI API | `backend/` | core | `SENTRY_DSN` | `backend@<git-sha>` | 1 | baseline_complete |
| `task-worker` | TaskIQ worker | `services/task-worker/` | core | `SENTRY_DSN` | `task-worker@<git-sha>` | 1 | baseline_complete |
| `cybervpn-mobile` | Flutter app | `cybervpn_mobile/` | client-apps | `SENTRY_DSN` | `cybervpn-mobile@<version>+<build>` | 1 | baseline_complete |
| `telegram-bot` | aiogram bot | `services/telegram-bot/` | core | `SENTRY_DSN` | `telegram-bot@<git-sha>` | 2 | baseline_complete |
| `desktop-renderer` | desktop renderer | `apps/desktop-client/src/` | client-apps | `VITE_SENTRY_DSN` | `desktop@<version>+<build>` | 3 | baseline_complete |
| `desktop-native` | desktop native | `apps/desktop-client/src-tauri/` | client-apps | `DESKTOP_SENTRY_DSN` | `desktop@<version>+<build>` | 3 | baseline_complete |
| `android-tv` | Android TV app | `apps/android-tv/` | client-apps | `SENTRY_DSN` | `android-tv@<version>+<build>` | 2 | baseline_complete |
| `node-fleet-controller` | control-plane FastAPI | `services/node-fleet-controller/` | platform | `SENTRY_DSN` | `node-fleet-controller@<git-sha>` | 2 | baseline_complete |
| `helix-adapter` | Rust/Axum adapter | `services/helix-adapter/` | platform | `SENTRY_DSN` | `helix-adapter@<git-sha>` | 3 | baseline_complete |
| `helix-node` | Rust node daemon | `services/helix-node/` | platform | `SENTRY_DSN` | `helix-node@<git-sha>` | 3 | baseline_complete |

## Registry rules

- One row per Sentry project.
- Rollout status must match the live tracker.
- Any new runtime surface must be added here before implementation starts.

## Status meanings

- `baseline_complete`: release/env contract, config docs, CI validation and targeted smoke proof are in place.
- `contract_aligned`: release/env contract is implemented, but dedicated smoke or operational closure is still pending.
- `pending`: no direct Sentry integration exists yet.
