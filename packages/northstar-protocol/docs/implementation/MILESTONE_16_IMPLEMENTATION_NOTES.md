# Milestone 16 Implementation Notes

## Scope

Milestone 16 moves the first datagram slice from localhost-hardened validation toward deployment-candidate rollout discipline without widening bridge-domain contracts or weakening the transport-agnostic session core.

Normative behavior still comes from:

- `docs/spec/northstar_wire_format_freeze_candidate_v0_1.md`
- `docs/spec/northstar_protocol_rfc_draft_v0_1.md`
- `docs/spec/northstar_blueprint_v0.md`
- `docs/spec/northstar_threat_model_v0_1.md`
- `docs/spec/northstar_security_test_and_interop_plan_v0_1.md`

This note records implementation choices and verification scope only.

## Decisions Recorded Here

### 1. Local rollout posture may narrow signed transport intent, but it must not widen it

Milestone 16 keeps staged local rollout controls (`disabled`, `canary`, `automatic`) but now fails closed when local planning or startup tries to enable datagrams against a signed carrier profile that explicitly disables them.

This rejects the mismatch at planning or config-validation time instead of leaving a later transport bootstrap to fail less clearly.

### 2. Accepted `SERVER_HELLO` UDP limits are now part of the active session contract

The session layer already rejected incompatible drift in:

- `policy_epoch`
- negotiated `datagram_mode`
- `max_udp_flows`
- `effective_max_udp_payload`

Milestone 16 additionally makes the accepted UDP contract real for later local behavior:

- negotiated `datagram_mode` now becomes the active local datagram posture
- negotiated `max_udp_flows` now clamps later local `UDP_FLOW_OPEN` admission
- negotiated `effective_max_udp_payload` now clamps later local outbound datagram expectations

This follows the frozen rule that `SERVER_HELLO` commits the active session contract rather than acting as a hint.

### 3. Established datagram selection stays sticky across bounded degradation

Milestone 16 adds deterministic live localhost coverage for:

- delayed delivery
- a short datagram black hole

The client remains on the established datagram path across those degradations and does not silently open a fallback stream.

That is the safest interpretation of the frozen specs today because they define explicit fallback selection but do not authorize a hidden mid-flow transport-mode migration after datagrams were already selected.

### 4. UDP smoke and perf gates now have a repo-native optional workflow path

The Windows-first local paths remain:

- `.\scripts\fuzz-udp-smoke.ps1`
- `.\scripts\check.ps1`

Milestone 16 adds:

- `.github/workflows/udp-optional-gates.yml`

The workflow is intentionally:

- opt-in
- Windows-first
- aligned with the existing wrapper scripts
- not a default mandatory PR gate

### 5. Saturation validation remains deterministic instead of timing-sensitive

Milestone 16 does not turn queue or burst saturation into a fragile timing benchmark.

The maintained regression surfaces remain:

- ratio-based UDP send, receive, and oversize-reject thresholds in `crates/ns-testkit/examples/udp_perf_gate.rs`
- deterministic boundary assertions for burst and queue guards
- stable low-cardinality datagram selection and guard events

### 6. Bridge topology and Remnawave boundaries remain unchanged

Milestone 16 deliberately does not widen:

- bridge-domain contracts
- public `/v0/*` bridge surfaces
- Remnawave adapter contracts
- deployment topology or store-service behavior

The milestone stays inside datagram rollout validation, session contract hardening, deterministic datagram-degradation coverage, optional workflow plumbing, and doc sync.

## No New ADR

Milestone 16 does not add a new ADR.

The milestone tightens rollout validation, session-contract enforcement, deterministic datagram degradation coverage, and verification workflow posture, but it does not change bridge contracts, signed manifest meaning, or ADR 0001.

## Deferred On Purpose

These items remain follow-on work:

- broader WAN-like or cross-network datagram interoperability beyond the deterministic local lab
- default-on CI execution for UDP fuzz and perf gates
- larger reviewed UDP corpora and longer-running fuzz campaigns
- richer operator rollout workflows beyond the existing local staged controls
- `0-RTT`

## Verification Scope

Milestone 16 is considered complete only after:

- startup and planning rejection coverage for rollout-enabled local posture against signed datagram-disabled profiles passed
- accepted `SERVER_HELLO` UDP-limit clamping coverage passed
- deterministic delayed-delivery and short-black-hole live datagram coverage passed without fallback regression
- the optional UDP workflow file was added and documented
- full-workspace formatting, clippy, and tests passed
- implementation docs were synchronized with the new rollout-validation, contract-clamping, workflow, and degradation behavior
