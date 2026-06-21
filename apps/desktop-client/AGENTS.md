# CyberVPN Desktop/Tauri Rules

Apply the root completion contract plus these desktop rules.

- Keep privileged/system operations in typed Rust commands and narrow service
  boundaries; presentation code must not own VPN or credential policy.
- Validate every IPC payload and return explicit typed failure states.
- Avoid shell-string construction and command injection. Use argument arrays,
  canonical paths, bounded timeouts and controlled child-process cleanup.
- Store credentials only through approved secure storage; never expose VPN
  configuration or tokens to frontend logs.
- Rust changes require fmt, clippy with warnings denied, tests and target smoke.
- Frontend changes require lint/typecheck/tests/build. Cross-boundary changes
  require an IPC integration test or deterministic harness.
