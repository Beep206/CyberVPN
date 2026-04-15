# Verta Spec Index

This directory contains the authoritative input set for Verta.
Treat these files as normative for protocol and integration behavior.

Naming note:

- The canonical protocol name is `Verta`.
- The canonical spec filenames now use the `verta_*` prefix.

| File | Status | Governs |
| --- | --- | --- |
| `adaptive_proxy_vpn_protocol_master_plan.md` | present | Overall roadmap, phase ordering, and long-horizon delivery plan. |
| `verta_blueprint_v0.md` | present | First buildable Verta architecture baseline, layering, and system shape. |
| `verta_wire_format_freeze_candidate_v0_1.md` | present | Frozen Verta wire format, manifest schema, token profile, and compatibility-sensitive public API rules. |
| `verta_remnawave_bridge_spec_v0_1.md` | present | External control-plane bridge contract, manifest delivery, and adapter boundaries for Verta. |
| `verta_threat_model_v0_1.md` | present | Verta threat boundaries, attacker capabilities, abuse paths, and security assumptions. |
| `verta_security_test_and_interop_plan_v0_1.md` | present | Verta security validation, negative testing, fuzzing, interop, and chaos-testing expectations. |
| `verta_implementation_spec_rust_workspace_plan_v0_1.md` | present | Verta Rust workspace layout, crate planning, and staged implementation structure. |
| `verta_protocol_rfc_draft_v0_1.md` | present | RFC-style Verta protocol description and externally legible protocol semantics. |

No authoritative inputs were missing at setup time.
If a listed file is missing in a future run, create or update `docs/spec/MISSING_INPUTS.md` and do not invent replacement normative content.
