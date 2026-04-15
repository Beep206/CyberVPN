# ADR 0001: Manifest Signing Reference Profile

- Status: Accepted
- Date: 2026-04-01

## Context

The authoritative Verta specs require clients to verify manifest signatures before trusting endpoints, carrier profiles, token-service metadata, or client constraints. They freeze `signature.alg = EdDSA` and require `signature.key_id` to map to a trusted key, but they do not define the exact canonical byte sequence to sign or the exact text encoding used for `signature.value`.

Milestone 2 needed end-to-end manifest signature enforcement in the bridge/compiler path, the manifest library, the client runtime, and the initial conformance fixtures. Without a deterministic signing profile, those code paths would either guess silently or remain blocked.

## Decision

The Verta reference implementation uses this manifest-signing profile:

- Render the signing input with RFC 8785 JSON Canonicalization Scheme semantics using `serde_jcs`.
- Build the signing input from the manifest JSON object with the `signature.value` member removed from the `signature` object.
- Preserve the `signature` object itself so `signature.alg` and `signature.key_id` remain part of the signed payload.
- Keep `signature.alg = EdDSA`.
- Encode `signature.value` as base64url without padding for the raw 64-byte Ed25519 signature.
- Require the client/runtime path to verify the embedded manifest signature before launch planning or endpoint trust decisions.

This ADR is an implementation-scoped reference profile. It does not rewrite the normative protocol documents by itself. Any incompatible change to this profile is compatibility-sensitive and must be paired with a spec update.

## Alternatives Considered

- Option A: Sign the raw JSON bytes emitted by the bridge.
  Rejected because whitespace, field order, and serializer differences would make signatures unstable across implementations.
- Option B: Sign a manifest form where `signature.value` is present but set to an empty string.
  Rejected because omitting `signature.value` from the canonical signing input is simpler to reason about and avoids placeholder-field ambiguity in fixtures and verifiers.

## Consequences

- The bridge/compiler, manifest library, and client runtime now share one deterministic signing profile.
- Initial valid and invalid manifest fixtures can be generated and verified reproducibly.
- `signature.value` encoding is now explicit in code and docs instead of implicit.
- The public spec still needs an eventual text update if this profile is intended to be the long-term interoperable rule across independent implementations.

## Spec Links

- `docs/spec/verta_blueprint_v0.md` section `19.3 Manifest signatures`
- `docs/spec/verta_wire_format_freeze_candidate_v0_1.md` sections `15.2 Manifest signature rules`, `15.3 Manifest freshness rules`, `18.6 Bridge and manifest`
- `docs/spec/verta_implementation_spec_rust_workspace_plan_v0_1.md` section `18.2 Verification discipline`
- `docs/spec/verta_threat_model_v0_1.md` section `TM-MF-01 — unsigned or weakly validated manifest acceptance`

## Follow-Up

- Keep the implementation note in `docs/implementation/MANIFEST_SIGNING_PROFILE.md` synchronized with code changes.
- Fold this profile into the normative spec set when the project is ready to freeze independent-implementation interoperability for manifest signatures.
- Treat any future change to the signing input or `signature.value` encoding as ADR- and spec-worthy.
