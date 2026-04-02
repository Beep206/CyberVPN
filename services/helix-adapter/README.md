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

## Verification

```bash
cargo fmt --check
cargo clippy --all-targets -- -D warnings
cargo test
```
