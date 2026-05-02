# Desktop Client

Status: draft
Owner: client-apps
Last updated: 2026-04-24
Scope: `apps/desktop-client/`
Depends on: `../04-sentry-project-registry.md`, `../10-ci-cd-release-artifacts-and-deploy-markers.md`
Related paths: `apps/desktop-client/package.json`, `apps/desktop-client/src-tauri/Cargo.toml`, `.github/workflows/desktop-release.yml`

## Current state

- Desktop builds as a Tauri application with separate renderer and native layers.
- `Wave 3 / Step 1` implemented split Sentry foundation in code:
  - renderer uses `@sentry/react`
  - native uses `sentry` for Rust
  - both layers share the same base release contract
  - both layers have dedicated DSN variables
- `Wave 3 / Step 2` completed the operational baseline:
  - `desktop-client-ci.yml` validates both contracts, builds the packaged app and runs dedicated smoke
  - `desktop-release.yml` now passes renderer/native Sentry env into the real release build
  - renderer sourcemap upload is wired through the Vite plugin
  - native debug-file upload is wired with `sentry-cli`
- Remaining residual proof work is end-to-end symbolication against a configured real Sentry project.

## Target project split

- `desktop-renderer`
- `desktop-native`

## Shared release contract

- both projects share the same base release: `desktop@<version>+<build>`
- `runtime_layer` distinguishes renderer from native

## Implemented contract

- renderer runtime vars:
  - `VITE_SENTRY_DSN`
  - `VITE_SENTRY_ENVIRONMENT`
  - `VITE_SENTRY_RELEASE`
  - optional `VITE_SENTRY_ENABLED`
  - optional `VITE_SENTRY_TRACES_SAMPLE_RATE`
  - optional `VITE_SENTRY_TRACE_PROPAGATION_TARGETS`
- native runtime/build vars:
  - `DESKTOP_SENTRY_DSN`
  - `DESKTOP_SENTRY_ENVIRONMENT`
  - `DESKTOP_SENTRY_RELEASE`
  - optional `DESKTOP_SENTRY_ENABLED`
  - optional `DESKTOP_SENTRY_TRACES_SAMPLE_RATE`
- CI artifact vars:
  - `SENTRY_URL`
  - `SENTRY_AUTH_TOKEN`
  - `SENTRY_ORG`
  - `DESKTOP_SENTRY_RENDERER_PROJECT`
  - `DESKTOP_SENTRY_NATIVE_PROJECT`

## Critical flows

- updater
- deep-link
- tray and lifecycle actions
- connect and disconnect flows
- startup cleanup and recovery

## Implementation checklist

- completed:
  - add renderer SDK foundation
  - add native SDK foundation
  - add shared release/environment contract
  - add `.env.example` coverage
  - add local unit/build validation for both layers
  - wire renderer sourcemap upload into CI/release workflow
  - wire native debug-file upload into CI/release workflow
  - add dedicated smoke path for packaged desktop validation
- next:
  - add correlation between renderer and native events
  - decide bounded offline caching policy
  - validate end-to-end symbolication in a real Sentry project
