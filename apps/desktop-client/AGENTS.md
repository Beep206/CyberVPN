# CyberVPN Desktop/Tauri Engineering Rules

Apply the root contract. When Codex was started from the repository root, read
this file explicitly before changing `apps/desktop-client/`.

Use the local `package.json`, `src-tauri/Cargo.toml`, Tauri configuration, and
current source as the version and command source of truth.

## Architecture and privilege separation

- React owns presentation and user interaction. Rust/Tauri owns privileged
  filesystem, process, updater, secure-storage, VPN, and operating-system
  behavior.
- Do not duplicate security, entitlement, subscription, routing, or VPN policy
  in the frontend.
- Expose narrow typed Tauri commands/events. Validate and normalize every IPC
  payload in Rust before use.
- Return typed success/error states with stable codes; do not leak internal
  paths, command lines, stack traces, tokens, or provider output.
- Keep long-running work outside the UI thread and make cancellation/shutdown
  ownership explicit.
- Reuse the existing command, state-management, API, and component patterns
  before adding a new abstraction.

## Process, path, and filesystem safety

- Never construct a shell command string from user or remote input. Prefer
  direct process APIs with an executable plus argument array.
- Canonicalize and validate paths against an allowed root before read/write.
- Reject traversal, unsafe symlinks, unexpected file types, and untrusted
  executable locations.
- Use bounded timeouts, output limits, process-group/child cleanup, and explicit
  cancellation.
- Do not inherit or log sensitive environment variables unnecessarily.
- Use atomic writes and safe permissions for configuration/state files.
- Treat downloaded updates, helpers, and artifacts as untrusted until signature
  and integrity verification succeeds.

## VPN, credentials, updater, and lifecycle

- Store secrets only through the approved OS secure-storage path. Never expose
  raw VPN configuration, subscription URLs, refresh material, device keys, or
  private keys to React state, logs, analytics, URLs, or crash reports.
- Model connect/disconnect/reconnect, permission, daemon/helper, update,
  background/tray, startup, and shutdown behavior as explicit state machines.
- Test repeated/concurrent commands, cancellation, process death, stale state,
  permission failure, invalid config, network loss, helper crash, and recovery.
- Do not report connected, updated, authenticated, or provisioned until the
  authoritative native operation completed.
- Updater changes require signed-metadata verification, rollback/failure
  behavior, channel/version policy, and a release smoke.

## Frontend quality

- Preserve strict TypeScript and validated IPC schemas; no `any`, `@ts-ignore`,
  unchecked casts, or blanket lint disables.
- Keep render pure and clean up listeners, Tauri events, timers, requests, and
  subscriptions.
- Implement pending, success, validation, permission, offline, error, retry, and
  degraded states for changed interactions.
- Preserve keyboard navigation, focus management, semantic controls,
  localization, responsive behavior, text scaling, and reduced motion.
- Do not hard-code user-visible strings when the existing i18n system owns
  them.
- Do not optimistically claim native success before receiving the authoritative
  Rust result/event.

## Rust quality

- Avoid `unwrap`, `expect`, panics, and unchecked indexing on IPC, file,
  network, updater, VPN, or process paths.
- Use typed errors and explicit state transitions.
- Keep unsafe code absent unless unavoidable, narrowly scoped, documented with
  invariants, and covered by targeted tests/review.
- Bound channels, buffers, retries, concurrency, payload size, child output, and
  waits.
- Do not block async executors or the Tauri event loop.
- Add structured diagnostics with safe identifiers and redaction.

## Testing

Add relevant:

- React interaction tests for real user-visible state;
- Rust unit tests for validation, state machines, paths, and error mapping;
- IPC contract/integration tests proving React payload -> Rust behavior ->
  resulting state/event;
- deterministic process/helper harnesses;
- updater integrity and failure tests;
- VPN lifecycle and permission/recovery tests;
- target-platform smoke when native behavior changes.

Mocks may replace the OS/provider boundary, not the IPC/business path being
verified. A successful command invocation or rendered page is not enough.

## Required validation

The current package has no standalone `lint` script; do not invent a passing
lint result. Use the scripts and compilers that actually exist:

```bash
npm run test:unit -w apps/desktop-client
npm exec -w apps/desktop-client -- tsc --noEmit
npm run build -w apps/desktop-client
cargo fmt --manifest-path apps/desktop-client/src-tauri/Cargo.toml --all -- --check
cargo clippy --manifest-path apps/desktop-client/src-tauri/Cargo.toml --all-targets --all-features -- -D warnings
cargo test --manifest-path apps/desktop-client/src-tauri/Cargo.toml
```

`npm run test -w apps/desktop-client` may be used as the combined test gate.
Run `smoke:release`, platform packaging, updater, and VPN/native smokes when
their behavior changes. Rerun all required gates after the final relevant
change.
