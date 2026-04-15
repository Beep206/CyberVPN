# Verta Protocol Workspace

This folder contains the imported Verta Rust workspace inside the CyberVPN monorepo.
The canonical package path is `packages/verta-protocol`. During the migration window, legacy technical identifiers such as `ns-*`, `VERTA_*`, and `target/verta` remain valid.

It keeps the protocol project together under one package-style directory while preserving the original workspace structure:

- `apps/` for `ns-bridge`, `ns-clientd`, `ns-gatewayd`, and `nsctl`
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
- `Verta` remains the legacy technical name in some env vars, artifact paths, and internal identifiers until the compatibility window is closed.

Repository-level metadata from the original workspace such as `.git/`, local `target/`, and editor/agent caches were intentionally not imported.

To work with the protocol from this directory:

```powershell
cd C:\project\CyberVPN\packages\verta-protocol
cargo fmt --all
cargo clippy --workspace --all-targets --all-features -- -D warnings
cargo test --workspace
```
