# Helix Node

Rust node daemon for CyberVPN Helix rollout consumption.

Responsibilities:

- fetch versioned node assignments from the Helix adapter
- persist bundle and runtime state locally
- apply assignments behind a health gate
- roll back to last-known-good bundle when apply or health checks fail
- expose `/healthz`, `/readyz`, and `/metrics`

This service is intentionally protocol-runtime agnostic in the first implementation pass. The
current supervisor models apply and rollback behavior so we can validate assignment lifecycle and
state restoration before wiring the final transport binary.
