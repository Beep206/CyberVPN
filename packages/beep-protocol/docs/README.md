# Beep Documentation Set

Updated: 2026-04-08

This directory defines the initial architecture for `Beep`, a VPN protocol and runtime stack designed from scratch. The documents below replace the previous `Helix` framing and normalize the design around a stable session core, multiple standards-based outer transports, and Rust-first implementation boundaries.

Recommended reading order:

1. `01-final-position.md` — validated conclusions and corrected thesis.
2. `02-beep-architecture.md` — system architecture and component boundaries.
3. `03-session-core-v1.md` — RFC-style blueprint for the Beep session core.
4. `04-transport-profiles.md` — transport profiles, policy model, and path selection.
5. `05-rust-implementation-plan.md` — Rust monorepo layout, crate boundaries, runtime model.
6. `06-rollout-observability-and-lab.md` — rollout model, telemetry, benchmark matrix, lab plan.
7. `07-source-validation.md` — source-by-source validation of the underlying arguments.

Core design decisions used across all files:

- `Beep` is not a single outer wire image. It is a session core plus transport profiles.
- `HTTP/2 over TLS/TCP` is a first-class compatibility baseline, not a shameful fallback.
- `HTTP/3 + MASQUE` is a first-class performance baseline, not the only way to operate.
- A separate `native-fast` mode exists for friendly networks where low overhead matters more than maximum compatibility.
- Cryptographic agility belongs inside the session core and control-plane artifacts.
- Presentation and transport policy must be deployable as signed artifacts independent of binary releases.
- Exact browser impersonation is not a v1 dependency. The architecture keeps room for an alternate edge implementation if that ever becomes mandatory.

