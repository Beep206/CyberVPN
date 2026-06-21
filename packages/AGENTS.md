# CyberVPN Shared Packages Engineering Rules

Apply the root contract. When Codex was started from the repository root, read
this file and the nearest package-specific `AGENTS.md` before changing
`packages/`.

A shared package is a compatibility boundary. Identify every current consumer
before changing its public API, generated output, feature flags, wire format,
storage format, or runtime behavior.

## Package ownership and compatibility

- Use each package manifest, lockfile, public exports, specifications, ADRs, and
  consumer code as the source of truth.
- Determine whether the package is canonical, legacy, transitional, generated,
  or vendored before editing it. Do not mirror changes across similarly named
  packages by assumption.
- Keep one authoritative definition for shared schemas, domain contracts,
  protocol types, and generated models.
- Avoid circular dependencies and application-specific behavior in shared
  packages.
- Preserve public API and serialized compatibility by default. Intentional
  breaks require an explicit versioning/migration decision, updated consumers,
  tests, and release notes/ADR where applicable.
- Do not expose internal modules accidentally through broad barrel exports.
- Keep feature flags additive and deterministic; test relevant combinations.

## Implementation quality

- Prefer small stable interfaces and typed errors over leaking implementation
  details.
- Validate untrusted inputs at package boundaries.
- Bound parsers, buffers, collections, retries, and concurrency.
- Do not add a dependency when the workspace already provides the capability.
  Review license, maintenance, security, target support, and feature footprint
  before adding one.
- Keep platform-specific behavior behind explicit adapters/features.
- Never manually edit generated artifacts; change the generator/schema and
  prove reproducibility.
- For cryptographic, protocol, parser, and VPN packages, follow the nearest
  threat model/specification and do not invent cryptography.

## Consumer-driven testing

Add package tests plus tests from representative consumers:

- API/ABI and public export tests;
- serialization/golden/vector compatibility tests;
- malformed/boundary/property/fuzz tests for parsers;
- feature-matrix and target tests;
- generated-output reproducibility tests;
- integration tests proving at least one real consumer path;
- migration tests for persisted/wire/config formats.

A package's own unit tests are insufficient when a change can break multiple
applications or services. Build and test every affected consumer.

## Validation

Use manifest-scoped commands and the nearest CI workflow.

- Rust: `cargo fmt --check`, clippy with warnings denied, workspace tests, and
  relevant feature/target/fuzz/interop checks.
- TypeScript: lint, strict typecheck, tests, build, exports/package validation,
  and consumer checks.
- Flutter/Dart: generation, format, analyze, tests, and affected app checks.

`packages/verta-protocol/AGENTS.md` and `packages/verta-protocol/docs/spec/`
remain authoritative for Verta protocol, wire format, bridge, security, and
interop behavior.
