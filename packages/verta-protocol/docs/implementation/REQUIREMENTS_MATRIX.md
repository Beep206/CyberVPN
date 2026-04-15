# Verta Requirements Matrix

This file is the implementation-facing reduction of the authoritative documents in `docs/spec/`.
Treat the spec set as normative and this matrix as a delivery aid.

| Area | Requirement | Governing source | Phase |
| --- | --- | --- | --- |
| Workspace | Use the normative `ns-*` workspace split and keep crate dependencies directional. | `verta_implementation_spec_rust_workspace_plan_v0_1.md` Sections 6, 9, 31 | A |
| Session core | Keep session logic transport-agnostic and independent of Quinn/H3 types. | `verta_implementation_spec_rust_workspace_plan_v0_1.md` Sections 10.3, 19; `verta_protocol_rfc_draft_v0_1.md` Sections 3, 8 | B, E |
| Wire | Freeze frame ids, field order, varint encoding, error ids, and malformed-input behavior. | `verta_wire_format_freeze_candidate_v0_1.md` Sections 4, 6, 8-13 | B |
| Auth | Use EdDSA/Ed25519 JWT tokens with strict `iss`, `aud`, `alg`, `typ`, `nbf`, and `exp` validation, plus bridge-driven revocation and stale-policy gates. | `verta_wire_format_freeze_candidate_v0_1.md` Section 16; `verta_threat_model_v0_1.md` Sections 13.3, 14.1; `verta_security_test_and_interop_plan_v0_1.md` Sections 13.3-13.4 | C |
| Manifest | Enforce the frozen schema version `1`, signed manifests, strict closed-world validation, and signed carrier-profile-driven runtime selection before activation. | `verta_wire_format_freeze_candidate_v0_1.md` Section 15; `verta_threat_model_v0_1.md` Sections 13.4, 14.4 | C, E |
| Bridge | Keep Remnawave integration isolated behind adapter and bridge-domain boundaries; do not fork Remnawave; enforce device validity, manifest binding, and replay-safe webhook ingress before token issuance. | `verta_remnawave_bridge_spec_v0_1.md` Sections 8, 11, 17, 24, 29; `verta_implementation_spec_rust_workspace_plan_v0_1.md` Sections 20, 23 | D |
| Carrier | First production carrier is `h3` over QUIC with session-core isolation and client runtime config derived from signed endpoint/profile data rather than local defaults. | `verta_implementation_spec_rust_workspace_plan_v0_1.md` Sections 8, 10.9, 19; `verta_protocol_rfc_draft_v0_1.md` Sections 8, 21 | E |
| Apps | Provide real client, gateway, and bridge composition roots with config validation, tracing, and signed-manifest trust enforcement at startup. | `verta_implementation_spec_rust_workspace_plan_v0_1.md` Sections 11, 12, 15, 17 | F |
| Testing | Start with deterministic fixtures, malformed-input coverage, auth/manifest tests, bridge replay/device-policy tests, and at least one parser fuzz target. | `verta_security_test_and_interop_plan_v0_1.md` Sections 13-18, 33; `verta_threat_model_v0_1.md` Section 17 | G |
| Docs | Keep ADRs, implementation status, and developer docs aligned with code changes. | `AGENTS.md`; `verta_implementation_spec_rust_workspace_plan_v0_1.md` Section 30 | H |

## Immediate Notes

- The workspace spec uses `ns-*` crate and app names. That overrides the looser `verta-*` examples from the task prompt.
- Manifest-signature canonicalization is resolved for the reference implementation by `docs/adr/0001-manifest-signing-reference-profile.md`.
- Manifest policy-epoch and profile-disablement handling stay on token/runtime surfaces rather than inventing new manifest fields; see `docs/implementation/MILESTONE_3_IMPLEMENTATION_NOTES.md`.
- The normative spec set still needs to absorb the ADR 0001 profile if the project wants that exact signing input and encoding to be the long-term interoperability rule.
