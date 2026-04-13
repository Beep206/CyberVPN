# Milestone 34 Implementation Notes

Milestone 34 extends the datagram rollout toolchain from release-readiness signoff discipline toward release-burn-in operator workflow with stronger sustained compatible-host evidence, while keeping Remnawave non-fork, bridge contracts unchanged, the session core transport-agnostic, and `0-RTT` disabled.

## Governing Inputs

- `docs/spec/northstar_wire_format_freeze_candidate_v0_1.md`
- `docs/spec/northstar_security_test_and_interop_plan_v0_1.md`
- `docs/spec/northstar_threat_model_v0_1.md`

## Scope

- keep Remnawave on the external bridge boundary
- keep bridge deployment topology unchanged
- keep transport selection, fallback, and rollout rules spec-driven and fail closed
- add one more workflow-backed datagram verification surface without changing Windows-first local wrapper expectations
- strengthen release-facing operator verdicts around exact interop profile contracts, queue-headroom accounting, and transport-fallback integrity
- grow the maintained reviewed UDP corpus and active-fuzz inputs

## Implemented

- Added a workflow-backed Linux `release_burn_in` lane to `.github/workflows/udp-optional-gates.yml` plus `scripts/udp-release-burn-in.ps1` and `scripts/udp-release-burn-in.sh`.
- Added `crates/ns-testkit/examples/udp_release_burn_in.rs`, which consumes release-candidate signoff plus Linux/macOS/Windows readiness and staged-rollout matrix artifacts and emits a fail-closed machine-readable operator verdict.
- Advanced the shared operator-verdict schema to version `13` in release-facing consumers and carried explicit `queue_guard_headroom_missing_count`, `queue_guard_tight_hold_count`, exact interop-profile-contract, and transport-fallback-integrity semantics into the new release-burn-in surface.
- Extended the maintained compatible-host interop catalog with the `post-close-rejection` profile so downstream consumers can require explicit no-silent-fallback proof for unknown datagrams after close.
- Added reviewed malformed UDP fixtures `WC-UDP-OPEN-ZEROPORT-047`, `WC-UDP-OPEN-BADUTF8DOMAIN-048`, `WC-UDP-OK-ZEROMAXPAYLOAD-049`, and `WC-UDP-STREAM-CLOSE-BADUTF8-050`, then synchronized them into the maintained corpora and conformance suite.
- Fixed a real wire-validation gap in `crates/ns-wire/src/codec.rs`: `UDP_FLOW_OPEN.target_port = 0` now fails closed instead of decoding as a silently accepted unusable target.
- Preserved bridge-domain, adapter, and bridge-app boundaries; milestone 34 does not widen Remnawave or bridge contracts.

## Verification Notes

- The new `udp_release_burn_in` example tests pass with both a fully ready operator-verdict path and a fail-closed missing-staged-matrix path.
- The maintained conformance suite caught the real zero-port acceptance bug; the decoder fix was applied and the rerun passed.
- The maintained rollout and release-facing wrappers remain intentionally fail closed when required compatible-host artifacts are missing or drifted.

## Deferred

- broader WAN or real cross-network datagram interoperability beyond deterministic lab and compatible-host lanes
- default-on CI enforcement for UDP fuzz, perf, interop, and release-facing workflow lanes
- larger maintained UDP corpora and longer-running fuzz campaigns
- richer operator rollout workflow beyond the current CLI, wrapper, and summary surfaces
