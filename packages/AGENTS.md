# CyberVPN Shared Packages Rules

Apply the root completion contract plus these package rules.

- Shared packages are compatibility boundaries. Avoid breaking public APIs;
  version and document intentional breaks.
- Keep generated artifacts reproducible and do not duplicate domain contracts
  across applications.
- Add consumer-oriented tests for changes that affect multiple surfaces.
- For Rust packages run workspace fmt, clippy and tests. For TypeScript
  packages run lint/typecheck/tests/build as available.
- `packages/verta-protocol/AGENTS.md` and `docs/spec/` remain authoritative for
  Verta protocol, wire format, bridge and security behavior.
