# Verta Protocol Workspace

This folder contains the imported Verta Rust workspace inside the CyberVPN monorepo.
The canonical package path is `packages/verta-protocol`.

It keeps the protocol project together under one package-style directory while preserving the original workspace structure:

- `apps/` for the internal app packages behind the public binaries `verta-bridge`, `verta-clientd`, `verta-gatewayd`, and `verta`
- `crates/` for the protocol, bridge, manifest, session, storage, carrier, and testkit crates
- `docs/` for specs, implementation notes, and operator-facing guidance
- `fixtures/`, `fuzz/`, `integration/`, `scripts/`, and `tests/` for verification and release work

Important boundaries:

- Remnawave stays external and non-fork.
- Session core stays transport-agnostic.
- `0-RTT` stays disabled.
- This import does not widen CyberVPN's public API surface by itself.

Canonical naming note:

- `Verta` is the public protocol name.
- `VERTA_*` env vars and `target/verta/` artifact paths are the maintained repository-level identifiers.
- Internal crate and binary identifiers such as `ns-*` remain stable until an explicit internal-ID migration is approved.

Repository-level metadata from the original workspace such as `.git/`, local `target/`, and editor/agent caches were intentionally not imported.

To work with the protocol from this directory:

```powershell
cd C:\project\CyberVPN\packages\verta-protocol
cargo fmt --all
cargo clippy --workspace --all-targets --all-features -- -D warnings
cargo test --workspace
```
