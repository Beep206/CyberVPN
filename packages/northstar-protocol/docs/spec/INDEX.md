# Northstar Spec Index

This directory contains the authoritative input set for Northstar.
Treat these files as normative for protocol and integration behavior.

| File | Status | Governs |
| --- | --- | --- |
| `adaptive_proxy_vpn_protocol_master_plan.md` | present | Overall roadmap, phase ordering, and long-horizon delivery plan. |
| `northstar_blueprint_v0.md` | present | First buildable architecture baseline, layering, and system shape. |
| `northstar_wire_format_freeze_candidate_v0_1.md` | present | Frozen wire format, manifest schema, token profile, and compatibility-sensitive public API rules. |
| `northstar_remnawave_bridge_spec_v0_1.md` | present | External control-plane bridge contract, manifest delivery, and adapter boundaries. |
| `northstar_threat_model_v0_1.md` | present | Threat boundaries, attacker capabilities, abuse paths, and security assumptions. |
| `northstar_security_test_and_interop_plan_v0_1.md` | present | Security validation, negative testing, fuzzing, interop, and chaos-testing expectations. |
| `northstar_implementation_spec_rust_workspace_plan_v0_1.md` | present | Rust workspace layout, crate planning, and staged implementation structure. |
| `northstar_protocol_rfc_draft_v0_1.md` | present | RFC-style protocol description and externally legible protocol semantics. |

No authoritative inputs were missing at setup time.
If a listed file is missing in a future run, create or update `docs/spec/MISSING_INPUTS.md` and do not invent replacement normative content.
