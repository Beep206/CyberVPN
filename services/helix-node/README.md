# Helix Node

Rust node daemon for CyberVPN Helix rollout consumption.

Responsibilities:

- fetch versioned node assignments from the Helix adapter
- persist bundle and runtime state locally
- apply assignments behind a health gate
- roll back to last-known-good bundle when apply or health checks fail
- expose `/healthz`, `/readyz`, and `/metrics`
- expose `/observability/sentry-contract` behind `HELIX_NODE_OBSERVABILITY_INTERNAL_SECRET`

This service is intentionally protocol-runtime agnostic in the first implementation pass. The
current supervisor models apply and rollback behavior so we can validate assignment lifecycle and
state restoration before wiring the final transport binary.

## Sentry baseline

- `SENTRY_DSN`, `SENTRY_RELEASE` and `ENVIRONMENT` control the daemon Sentry contract
- `SENTRY_TRACES_SAMPLE_RATE` controls Rust tracing/span capture
- `HELIX_NODE_OBSERVABILITY_INTERNAL_SECRET` protects the internal smoke probe
- `HELIX_NODE_SMOKE_MODE=true` starts the daemon without the control-plane loop so CI and local smoke can validate the runtime contract without a live adapter
