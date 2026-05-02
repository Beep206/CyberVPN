# Helix Adapter

Rust control-plane service for CyberVPN Helix.

## Responsibilities

- expose `/healthz`, `/readyz`, and `/metrics`
- wrap read-only Remnawave node inventory access
- manage service-owned registry, rollout metadata, and manifest version persistence in the `helix` PostgreSQL schema
- render and sign desktop manifests without mutating `Remnawave`

## Local Development

Populate `.env` from `.env.example`, then run:

```bash
cargo run
```

The adapter applies embedded SQLx migrations on startup.

## Sentry Baseline

- Runtime Sentry contract is driven by `ENVIRONMENT`, `SENTRY_DSN`, `SENTRY_RELEASE` and `SENTRY_TRACES_SAMPLE_RATE`.
- The protected runtime probe lives at `/observability/sentry-contract` and requires `HELIX_ADAPTER_OBSERVABILITY_INTERNAL_SECRET` via the `x-observability-secret` header.
- `HELIX_ADAPTER_SMOKE_MODE=true` starts the service with lazy runtime dependencies so CI and local smoke checks can validate `/healthz` and the Sentry contract without a live Postgres or Remnawave dependency chain.

## Verification

```bash
cargo fmt --check
cargo clippy --all-targets -- -D warnings
cargo test
```
