# Milestone 47 Implementation Notes

Milestone 47 advances `Phase I` of the production-ready plan by adding the first supported-upstream verification harness for the non-fork Remnawave path, while keeping Remnawave external, bridge deployment topology unchanged, the session core transport-agnostic, and `0-RTT` disabled.

## Governing Inputs

- `docs/spec/northstar_remnawave_bridge_spec_v0_1.md`
- `docs/spec/northstar_security_test_and_interop_plan_v0_1.md`
- `docs/spec/northstar_threat_model_v0_1.md`
- `docs/spec/northstar_implementation_spec_rust_workspace_plan_v0_1.md`

## Scope

- keep Remnawave on the external control-plane boundary
- keep bridge-owned policy authority and the public `/v0/*` bridge surface unchanged
- add one fail-closed supported-upstream verification harness over the existing HTTP adapter and bridge runtime boundaries
- classify missing environment, unsupported upstream version, upstream auth failure, timeout, response-shape drift, webhook-signature failure, unavailable, stale, and incompatible-contract states explicitly
- preserve existing CLI/startup validation surfaces across `ns-clientd`, `nsctl`, and `ns-gatewayd`
- document what milestone 47 proves and what still blocks `Phase I` exit

## Implemented

- Added `crates/ns-testkit/examples/remnawave_supported_upstream_verification.rs`, a machine-readable supported-upstream verification harness that:
  - verifies a real configured `HttpRemnawaveAdapter` against a supported upstream environment
  - enforces the supported version floor of `2.7.0+` and records the preferred `2.7.4+` band without widening bridge contracts
  - exercises the maintained bridge path through bootstrap manifest fetch, device registration, token exchange, refresh manifest fetch, and verified webhook ingress
  - emits a fail-closed operator-facing summary at `target/northstar/remnawave-supported-upstream-summary.json` by default
- Added Windows-first and Bash wrappers in `scripts/remnawave-supported-upstream-verify.ps1` and `scripts/remnawave-supported-upstream-verify.sh`.
- Added reviewed adapter-level schema-drift regression coverage with `fixtures/remnawave/account/BG-UPSTREAM-ACCOUNT-SCHEMADRIFT-010.json` and the `http_adapter_fails_closed_on_upstream_schema_drift` test in `crates/ns-remnawave-adapter/src/http.rs`.
- Added example-level tests that cover:
  - ready supported-upstream verification against a local supported-upstream-shaped HTTP server
  - missing environment fail-closed behavior
  - unsupported upstream version fail-closed behavior
  - upstream auth failure as `required_inputs_unready`
- Preserved bridge-domain, bridge-app, adapter, wire, and session-core boundaries; milestone 47 does not widen public bridge APIs or introduce panel-internal coupling.

## Verification Notes

- The new adapter schema-drift regression passes and keeps upstream response-shape drift fail closed.
- The new supported-upstream example compiles and its example-local test suite passes.
- The supported-upstream wrapper is intentionally fail closed when required environment variables or upstream evidence are missing.

## Assumptions And Limits

- Milestone 47 validates the current configured webhook signature gate plus timestamp freshness on the bridge boundary; it does not by itself prove full production webhook signing-format alignment against every supported upstream deployment.
- The supported-upstream harness proves the maintained adapter and bridge flow composition against a real configured upstream endpoint, but it does not yet close full lifecycle reconciliation, revoke/disable propagation, or deployment-grade remote/shared-store reality validation.
- The supported-upstream harness treats snapshot freshness as an operator-configurable check with a default of `300` seconds for this verification lane; this is a harness assumption, not a new protocol rule.

## Deferred

- full real lifecycle and reconciliation coverage against supported upstream environments
- explicit revoke/disable and entitlement-change propagation evidence through the supported-upstream lane
- deployment-grade remote/shared-store validation against a real supported upstream environment
- broader WAN-grade datagram evidence and sustained default-on release gating beyond the current optional lanes
