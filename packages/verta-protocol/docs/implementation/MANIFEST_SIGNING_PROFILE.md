# Manifest Signing Profile

This note records the current reference implementation profile for Verta manifest signatures.
The durable rationale lives in `docs/adr/0001-manifest-signing-reference-profile.md`.

## Current Profile

- Canonical renderer: RFC 8785 JCS via `serde_jcs`
- Signature algorithm: `EdDSA`
- Signable payload: the manifest JSON object with `signature.value` removed from the `signature` object
- Signature text encoding: base64url without padding of the raw 64-byte Ed25519 signature
- Verification point: the client/runtime path must verify the embedded manifest signature before trusting endpoints, carrier profiles, token-service metadata, or client constraints

## Code Paths

- Bridge/compiler signing: `crates/ns-bridge-domain`
- Manifest canonicalization and verification: `crates/ns-manifest`
- Client enforcement: `crates/ns-client-runtime`
- Fixture generation and trust helpers: `crates/ns-testkit`, `apps/ns-bridge`, `apps/nsctl`

## Scope Boundary

This note describes the current reference profile only.
It does not replace the authoritative spec set under `docs/spec/`.
