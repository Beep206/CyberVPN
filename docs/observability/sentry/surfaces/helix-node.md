# Helix Node

Status: implemented
Owner: platform
Last updated: 2026-04-24
Scope: `services/helix-node/`
Depends on: `../05-environment-and-release-contract.md`, `../11-smoke-tests-and-validation.md`
Related paths: `services/helix-node/`, `docs/helix/`

## Current state

- Rust daemon with node lifecycle, health, heartbeat and rollback logic.
- Rust-native `sentry` init is wired in `src/observability.rs` and started from `src/main.rs`.
- Protected `/observability/sentry-contract` is exposed from the local daemon HTTP server.
- `HELIX_NODE_SMOKE_MODE=true` skips the control-plane loop so CI can validate the runtime contract without a live adapter.
- Restore, assignment sync and heartbeat generation now emit tracing spans that Sentry can ingest when traces are enabled.

## Implemented baseline

- runtime tags: `runtime_surface`, `service.name`, `node_id`, `daemon_version`, `instance_id`
- release/env contract: `ENVIRONMENT`, `SENTRY_DSN`, `SENTRY_RELEASE`, `SENTRY_TRACES_SAMPLE_RATE`
- protected smoke contract: `HELIX_NODE_OBSERVABILITY_INTERNAL_SECRET`
- smoke-safe startup: `HELIX_NODE_SMOKE_MODE`
- CI proof: `helix-node-ci.yml` runs `cargo fmt`, `cargo clippy`, `cargo test`, contract validation and live HTTP smoke

## Carryover

- native symbol upload and symbolication proof are still a future wave
- any offline buffering policy for unstable-network nodes remains a design follow-up, not part of the current baseline
