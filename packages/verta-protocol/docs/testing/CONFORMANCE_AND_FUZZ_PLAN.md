# Verta Conformance And Fuzz Plan

This document records the initial negative-test, fixture, fuzzing, and interoperability scaffold for the v0.1 baseline.
It is intentionally implementation-facing: the protocol documents in `docs/spec/` remain normative.

## Status Note

As of `2026-04-13`, the active sustained CI source of truth is no longer the long-planned `.github/workflows/udp-optional-gates.yml`.
`Phase K` replaces that planned path with the real root workflows `.github/workflows/verta-udp-bounded-verification.yml`, `.github/workflows/verta-udp-scheduled-verification.yml`, and `.github/workflows/verta-udp-release-evidence.yml`, with the exact branch or release gate map in `docs/development/SUSTAINED_VERIFICATION_GATES.md`.

## Scope

- Keep wire compatibility checks isolated from transport-specific behavior.
- Exercise malformed input handling before optimizing live carrier behavior.
- Make bridge, token, manifest, and webhook edge cases explicit instead of implicit.
- Build fixture IDs and fuzz targets that can grow without changing naming conventions later.

## Fixture Tree

The baseline repository now reserves these fixture paths:

- `fixtures/wire/v1/valid/`
- `fixtures/wire/v1/invalid/`
- `fixtures/manifest/v1/valid/`
- `fixtures/manifest/v1/invalid/`
- `fixtures/token/jws/valid/`
- `fixtures/token/jws/invalid/`
- `fixtures/bridge/bootstrap/`
- `fixtures/remnawave/webhook/`
- `fixtures/interop/transcripts/`

Use these directories for authoritative golden fixtures, malformed inputs, and transcript captures.
Do not mix speculative cases with normative fixtures; each file should clearly map to a spec section or threat-model scenario.

## Fixture Naming

Use stable, reviewable identifiers:

- `NS-FX-HELLO-001`
- `NS-FX-HELLO-ACK-001`
- `NS-FX-PING-001`
- `NS-FX-PONG-001`
- `NS-FX-ERR-001`
- `NS-FX-STREAM-OPEN-001`
- `NS-FX-STREAM-ACCEPT-001`
- `NS-FX-UDP-OPEN-001`
- `NS-FX-UDP-OK-001`
- `NS-FX-UDP-DGRAM-001`

When adding new fixtures, keep the prefix stable and increment the numeric suffix instead of renaming older artifacts.

## Negative Cases To Materialize First

Prioritize these malformed or hostile cases:

- Truncated control-frame envelopes
- Declared payload lengths larger than the available bytes
- Reserved-bit violations in stream or datagram flags
- Illegal pre-hello control frames
- Unknown enum values where the wire spec requires rejection
- Empty token, manifest, or device identifiers
- Malformed UDP relay lengths
- Tampered detached manifest signatures
- Unsupported manifest schema versions
- Expired, wrong-issuer, or wrong-audience session tokens
- Tokens bound to the wrong device, manifest, or carrier profile
- Duplicate or replayed webhook deliveries

## Conformance Suites

Use these suite IDs when adding fixture-backed or integration-backed coverage:

- `WC`: wire codec and envelope conformance
- `SM`: session state-machine conformance
- `AU`: auth and trust-material conformance
- `MF`: manifest validation and profile selection conformance
- `BG`: bridge contract and Remnawave adapter conformance

Each test or fixture import should note which suite it belongs to.

## Implemented Through Milestone 46

The repository now has fixture-backed or integration-backed coverage for:

- `WC`: wire codec and envelope conformance in `crates/ns-wire/tests/conformance_fixtures.rs`
- `MF`: manifest verification, frozen-schema enforcement, and client/runtime trust enforcement in `crates/ns-manifest/tests/conformance_fixtures.rs` and `crates/ns-client-runtime/tests/manifest_fixtures.rs`
- `AU`: token verification profile checks plus stale-JWKS, revoked-subject, and stale-policy admission coverage in `crates/ns-auth/tests/token_fixtures.rs`
- `BG`: bridge manifest-auth parsing, thin HTTP service composition, verified webhook handling, and bridge-domain replay or device-policy checks in `crates/ns-bridge-api/tests/bridge_fixtures.rs`, `crates/ns-remnawave-adapter/tests/webhook_fixtures.rs`, and `crates/ns-bridge-domain/src/lib.rs`
- shared-store replay and device-policy coordination coverage in `crates/ns-bridge-domain/tests/shared_store_replay_and_policy.rs`
- targeted `SM` admission negatives in `crates/ns-session/tests/admission_from_fixture.rs`
- replay-cache and single-use guards in `crates/ns-storage/src/lib.rs`
- durable local bridge-store reopen coverage in `crates/ns-storage/src/lib.rs`
- HTTP-backed service-store round-trip, health, and timeout coverage in `crates/ns-storage/src/service.rs`
- authenticated remote/shared service-store coverage in `crates/ns-storage/src/service.rs`
- unauthorized health/command access and internal-failure redaction coverage in `crates/ns-storage/src/service.rs`
- ordered remote/shared service-store endpoint failover coverage plus unauthorized-no-failover coverage in `crates/ns-storage/src/service.rs`
- live QUIC/H3 control-stream hello, relay-stream preamble, reusable raw relay forwarding, clean relay EOF handling, and oversized-hello rejection coverage in `crates/ns-carrier-h3/tests/live_control.rs`
- live QUIC/H3 relay idle-timeout release and overload-rejection coverage in `crates/ns-carrier-h3/tests/live_control.rs`, including emitted `STREAM_REJECT` compatibility on overload
- reusable relay-runtime half-close, timeout, overflow, and stable close-reason coverage in `crates/ns-carrier-h3/src/lib.rs`
- frozen protocol error-registry lock coverage in `crates/ns-core/src/lib.rs`
- UDP control-frame and datagram fixture coverage in `crates/ns-wire/tests/conformance_fixtures.rs`
- UDP flow-open policy and error-mapping coverage in `crates/ns-session/src/lib.rs`
- bridge HTTP composition coverage for refresh-path `ETag` handling and route-scoped JSON body limits in `crates/ns-bridge-api/src/lib.rs`
- explicit bridge-app HTTP runtime composition coverage over both shared durable local backends and the remote/shared service-store path in `apps/ns-bridge/src/main.rs`
- deployment-topology startup, health, shutdown, auth-mismatch, and realistic HTTP Remnawave adapter flow coverage in `apps/ns-bridge/src/main.rs`
- initial real HTTP Remnawave adapter coverage in `crates/ns-remnawave-adapter/src/http.rs`
- stable relay-guard structured-event assertions in `crates/ns-gateway-runtime/src/lib.rs`
- stable datagram-selection and datagram-guard structured-event assertions in `crates/ns-observability/src/lib.rs`
- live localhost H3 datagram success, rollout-disabled and carrier-unavailable stream-fallback success, repeated bounded-loss continuation, bounded reordering, delayed-delivery plus short-black-hole continuation without silent fallback, MTU-ceiling success, payload-oversize rejection with stable post-guard recovery, wrong-associated-stream rejection, queue-overflow observability, and datagram-unavailable rejection coverage in `crates/ns-carrier-h3/tests/live_udp.rs`
- prolonged datagram-impairment, repeated queue-pressure, and clean-shutdown no-silent-fallback coverage in `crates/ns-carrier-h3/tests/live_udp.rs` and `crates/ns-carrier-h3/src/lib.rs`
- post-`SERVER_HELLO` session drift coverage for `policy_epoch`, negotiated datagram mode, UDP flow limits, payload limits, unusable zero-valued limits, and negotiated UDP-limit clamping in `crates/ns-session/src/lib.rs`
- startup and planning rejection coverage for rollout-enabled local posture versus signed datagram-disabled profiles in `crates/ns-client-runtime/src/lib.rs` and `crates/ns-carrier-h3/src/lib.rs`
- transport-mode-aware UDP validation coverage for unknown-flow datagrams, post-close datagrams, and wrong fallback flow ids in `crates/ns-session/src/lib.rs` and `crates/ns-carrier-h3/tests/live_udp.rs`
- CLI-level startup and negotiated datagram-validation coverage across `apps/ns-clientd/src/main.rs`, `apps/nsctl/src/main.rs`, and `apps/ns-gatewayd/src/main.rs`
- comparison-friendly startup and negotiated datagram-validation output coverage across `apps/ns-clientd/src/main.rs`, `apps/nsctl/src/main.rs`, and `apps/ns-gatewayd/src/main.rs`, including stable `comparison_family`, `comparison_label`, `comparison_schema`, `comparison_schema_version`, `comparison_scope`, `comparison_profile`, `evidence_state`, `gate_state`, `verdict`, `required_input_count`, `required_input_present_count`, `required_input_passed_count`, `required_input_missing_count`, `required_input_failed_count`, `all_required_inputs_present`, `all_required_inputs_passed`, `degradation_hold_count`, `blocking_reason_count`, `blocking_reason_key`, and `blocking_reason_family` fields in both text and JSON modes
- UDP-specific fuzz targets in `fuzz/cargo-fuzz/fuzz_targets/udp_datagram_decoder.rs` and `fuzz/cargo-fuzz/fuzz_targets/udp_fallback_frame_decoder.rs`
- UDP fixture-derived corpus and regression seeds under `fuzz/cargo-fuzz/corpus/udp_datagram_decoder`, `fuzz/cargo-fuzz/corpus/udp_fallback_frame_decoder`, `fuzz/cargo-fuzz/corpus/control_frame_decoder`, and `fuzz/cargo-fuzz/fuzz_regressions`
- active local UDP corpus-sync and smoke-replay coverage via `crates/ns-testkit/examples/sync_udp_fuzz_corpus.rs`, `crates/ns-testkit/examples/udp_fuzz_smoke.rs`, and `scripts/fuzz-udp-smoke.*`
- active local UDP interoperability-lab coverage via `crates/ns-testkit/examples/udp_interop_lab.rs` plus `scripts/udp-wan-lab.*`, including machine-readable summary output for named impairment profiles
- active local and compatible-host rollout-validation coverage via `crates/ns-testkit/examples/udp_rollout_validation_lab.rs` plus `.github/workflows/udp-optional-gates.yml`, including machine-readable summary output for staged rollout validation and longer-impairment recovery evidence
- active local and compatible-host rollout-comparison coverage via `crates/ns-testkit/examples/udp_rollout_compare.rs`, `scripts/udp-rollout-readiness.*`, and `.github/workflows/udp-optional-gates.yml`, including `readiness` and `staged_rollout` verdict profiles plus a stable operator-verdict schema with evidence or gate state and blocking reasons per host or lane
- workflow-backed cross-host rollout-matrix coverage via `crates/ns-testkit/examples/udp_rollout_matrix.rs` and `.github/workflows/udp-optional-gates.yml`, including machine-readable operator matrix verdicts across compatible-host comparison artifacts for both host-level readiness and staged-rollout evidence
- workflow-backed release-workflow coverage via `crates/ns-testkit/examples/udp_release_workflow.rs`, `scripts/udp-release-workflow.*`, and `.github/workflows/udp-optional-gates.yml`, including machine-readable operator release-workflow verdicts that consume readiness and staged-rollout matrix evidence on the shared operator-verdict schema
- workflow-backed deployment-signoff coverage via `crates/ns-testkit/examples/udp_deployment_signoff.rs`, `scripts/udp-deployment-signoff.*`, and `.github/workflows/udp-optional-gates.yml`, including machine-readable deployment-candidate signoff verdicts that consume release-workflow and compatible-host rollout-validation evidence on that same shared operator-verdict schema
- workflow-backed release-prep coverage via `crates/ns-testkit/examples/udp_release_prep.rs`, `scripts/udp-release-prep.*`, and `.github/workflows/udp-optional-gates.yml`, including machine-readable release-prep verdicts that consume deployment-signoff plus Linux, macOS, and Windows rollout-validation evidence on that same shared operator-verdict schema
- workflow-backed release-candidate-signoff coverage via `crates/ns-testkit/examples/udp_release_candidate_signoff.rs`, `scripts/udp-release-candidate-signoff.*`, and `.github/workflows/udp-optional-gates.yml`, including machine-readable release-candidate signoff verdicts that consume release-prep plus Windows rollout-readiness, compatible-host Windows interop, and compatible-host macOS interop evidence on that same shared operator-verdict schema
- workflow-backed release-burn-in coverage via `crates/ns-testkit/examples/udp_release_burn_in.rs`, `scripts/udp-release-burn-in.*`, and `.github/workflows/udp-optional-gates.yml`, including machine-readable release-burn-in verdicts that consume release-candidate-signoff plus Linux/macOS/Windows rollout-readiness and staged-rollout matrix evidence on that same shared operator-verdict schema
- workflow-backed release-soak coverage via `crates/ns-testkit/examples/udp_release_soak.rs`, `scripts/udp-release-soak.*`, and `.github/workflows/udp-optional-gates.yml`, including machine-readable release-soak verdicts that consume release-burn-in plus Linux/macOS/Windows interop evidence on that same shared operator-verdict schema
- workflow-backed release-gate coverage via `crates/ns-testkit/examples/udp_release_gate.rs`, `scripts/udp-release-gate.*`, and `.github/workflows/udp-optional-gates.yml`, including machine-readable release-gate verdicts that consume release-soak plus Linux/macOS/Windows compatible-host interop catalogs on that same shared operator-verdict schema
- workflow-backed release-readiness-burndown coverage via `crates/ns-testkit/examples/udp_release_readiness_burndown.rs`, `scripts/udp-release-readiness-burndown.*`, and `.github/workflows/udp-optional-gates.yml`, including machine-readable release-readiness-burndown verdicts that consume release-gate plus Linux/macOS/Windows rollout-readiness evidence on that same shared operator-verdict schema
- workflow-backed release-stability-signoff coverage via `crates/ns-testkit/examples/udp_release_stability_signoff.rs`, `scripts/udp-release-stability-signoff.*`, and `.github/workflows/udp-optional-gates.yml`, including machine-readable release-stability-signoff verdicts that consume release-readiness-burndown plus Linux/macOS/Windows compatible-host interop evidence on that same shared operator-verdict schema
- workflow-backed release-candidate-consolidation coverage via `crates/ns-testkit/examples/udp_release_candidate_consolidation.rs`, `scripts/udp-release-candidate-consolidation.*`, and `.github/workflows/udp-optional-gates.yml`, including machine-readable release-candidate-consolidation verdicts that consume release-stability-signoff plus Linux/macOS/Windows compatible-host interop catalogs on that same shared operator-verdict schema
- workflow-backed release-candidate-hardening coverage via `crates/ns-testkit/examples/udp_release_candidate_hardening.rs`, `scripts/udp-release-candidate-hardening.*`, and `.github/workflows/udp-optional-gates.yml`, including machine-readable release-candidate-hardening verdicts that consume release-candidate-consolidation plus Linux/macOS/Windows rollout-validation evidence and exact compatible-host interop-catalog `source_lane` semantics on that same shared operator-verdict schema
- workflow-backed release-candidate-evidence-freeze coverage via `crates/ns-testkit/examples/udp_release_candidate_evidence_freeze.rs`, `scripts/udp-release-candidate-evidence-freeze.*`, and `.github/workflows/udp-optional-gates.yml`, including machine-readable release-candidate-evidence-freeze verdicts that consume release-candidate-hardening plus Linux/macOS/Windows compatible-host interop catalogs and fail closed on exact `source_lane`, failed-profile-count, and summary-contract-invalid drift
- workflow-backed release-candidate-signoff-closure coverage via `crates/ns-testkit/examples/udp_release_candidate_signoff_closure.rs`, `scripts/udp-release-candidate-signoff-closure.*`, and `.github/workflows/udp-optional-gates.yml`, including machine-readable release-candidate-signoff-closure verdicts that consume release-candidate-evidence-freeze plus Linux/macOS/Windows rollout-readiness evidence and fail closed on exact `source_lane`, failed-profile-count, host-label-set, and policy-disabled-fallback round-trip drift
- workflow-backed release-candidate-stabilization coverage via `crates/ns-testkit/examples/udp_release_candidate_stabilization.rs`, `scripts/udp-release-candidate-stabilization.*`, and `.github/workflows/udp-optional-gates.yml`, including machine-readable release-candidate-stabilization verdicts that consume release-candidate-signoff-closure plus Linux/macOS/Windows compatible-host interop catalogs and fail closed on exact `source_lane`, failed-profile-count, host-label-set, readiness-set, and policy-disabled-fallback round-trip drift
- workflow-backed release-candidate-readiness coverage via `crates/ns-testkit/examples/udp_release_candidate_readiness.rs`, `scripts/udp-release-candidate-readiness.*`, and `.github/workflows/udp-optional-gates.yml`, including machine-readable release-candidate-readiness verdicts that consume release-candidate-stabilization plus Linux/macOS/Windows rollout-readiness evidence and fail closed on exact `source_lane`, failed-profile-count, host-label-set, readiness-set, blocked-fallback surface, and policy-disabled-fallback round-trip drift
- workflow-backed release-candidate-acceptance coverage via `crates/ns-testkit/examples/udp_release_candidate_acceptance.rs`, `scripts/udp-release-candidate-acceptance.*`, and `.github/workflows/udp-optional-gates.yml`, including machine-readable release-candidate-acceptance verdicts that consume release-candidate-readiness plus Linux/macOS/Windows rollout-readiness evidence and fail closed on exact `source_lane`, failed-profile-count, host-label-set, readiness-set, blocked-fallback surface, and transport-fallback-integrity drift
- workflow-backed release-candidate-certification coverage via `crates/ns-testkit/examples/udp_release_candidate_certification.rs`, `scripts/udp-release-candidate-certification.*`, and `.github/workflows/udp-optional-gates.yml`, including machine-readable release-candidate-certification verdicts that consume release-candidate-acceptance plus Linux/macOS/Windows compatible-host interop catalogs and fail closed on exact `source_lane`, failed-profile-count, host-label-set, blocked-fallback surface, and transport-fallback-integrity drift
- a machine-readable compatible-host interop profile catalog path via `cargo run -p ns-testkit --example udp_interop_lab -- --list --format json`, including the exact required-no-silent-fallback profile inventory expected by release-facing consumers
- host-specific compatible-host interop profile catalog artifacts for Linux, macOS, and Windows via `.github/workflows/udp-optional-gates.yml`
- compatible-host macOS interop-lab coverage with uploaded machine-readable summary artifacts via `.github/workflows/udp-optional-gates.yml`
- compatible-host Windows interop-lab coverage with uploaded machine-readable summary artifacts via `.github/workflows/udp-optional-gates.yml`
- opt-in short active UDP fuzz coverage via `scripts/fuzz-udp-active.*`
- opt-in workspace check-wrapper UDP fuzz and performance gates via `scripts/check.*`
- repo-native optional UDP smoke, perf, WAN-lab, interop-lab, rollout-readiness, staged-rollout, active-fuzz, release-workflow, deployment-signoff, release-prep, release-candidate-signoff, release-burn-in, release-soak, release-gate, release-readiness-burndown, release-stability-signoff, release-candidate-consolidation, release-candidate-hardening, release-candidate-evidence-freeze, release-candidate-signoff-closure, release-candidate-stabilization, release-candidate-readiness, release-candidate-acceptance, and release-candidate-certification workflow coverage via `.github/workflows/udp-optional-gates.yml`
- compatible-host Linux interop-lab coverage with uploaded machine-readable summary artifacts via `.github/workflows/udp-optional-gates.yml`
- compatible-host Linux staged-rollout coverage with uploaded active-fuzz and rollout-comparison summary artifacts via `.github/workflows/udp-optional-gates.yml`
- compatible-host macOS staged-rollout coverage with uploaded active-fuzz and rollout-comparison summary artifacts via `.github/workflows/udp-optional-gates.yml`
- compatible-host Windows rollout-validation coverage with uploaded machine-readable summary artifacts via `.github/workflows/udp-optional-gates.yml`
- compatible-host Windows rollout-readiness coverage with uploaded fuzz-smoke, perf, interop, rollout-validation, and rollout-comparison summary artifacts via `.github/workflows/udp-optional-gates.yml`
- ratio-based UDP performance threshold coverage via `crates/ns-testkit/examples/udp_perf_gate.rs`, including a machine-readable summary output for staged rollout review

Active fixture IDs:

- `WC`: `NS-FX-PING-001`, `NS-FX-HELLO-001`, `NS-FX-HELLO-NOOVERLAP-002`, `NS-FX-UDP-OPEN-001`, `NS-FX-UDP-OK-001`, `NS-FX-UDP-OK-FALLBACK-002`, `NS-FX-UDP-DGRAM-001`, `NS-FX-UDP-DGRAM-MTU-002`, `NS-FX-UDP-FLOW-CLOSE-001`, `NS-FX-UDP-FLOW-CLOSE-DGRAMUNAVAIL-002`, `NS-FX-UDP-FLOW-CLOSE-PROTOVIOL-003`, `NS-FX-UDP-STREAM-OPEN-001`, `NS-FX-UDP-STREAM-ACCEPT-001`, `NS-FX-UDP-STREAM-PACKET-001`, `NS-FX-UDP-STREAM-CLOSE-001`, `NS-FX-UDP-STREAM-CLOSE-IDLE-002`, `WC-HELLO-TRUNCATED-001`, `WC-HELLO-MINMAX-002`, `WC-HELLO-EMPTYTOKEN-003`, `WC-PING-NONCANONVARINT-004`, `WC-HELLO-BADCARRIER-005`, `WC-UDP-OPEN-RESERVEDFLAGS-007`, `WC-UDP-DGRAM-RESERVEDFLAGS-008`, `WC-UDP-OK-BADMODE-009`, `WC-UDP-STREAM-PACKET-LEN-010`, `WC-UDP-STREAM-CLOSE-BADCODE-011`, `WC-UDP-FLOW-CLOSE-BADCODE-012`, `WC-UDP-STREAM-OPEN-TRUNCATED-013`, `WC-UDP-STREAM-PACKET-TRUNCATED-014`, `WC-UDP-DGRAM-TRUNCATED-015`, `WC-UDP-FLOW-CLOSE-TRUNCATED-016`, `WC-UDP-STREAM-CLOSE-TRUNCATED-017`, `WC-UDP-OK-TRUNCATED-018`, `WC-UDP-STREAM-ACCEPT-TRUNCATED-019`, `WC-UDP-OPEN-TRUNCATED-020`, `WC-UDP-DGRAM-NONCANONFLOW-021`, `WC-UDP-STREAM-CLOSE-BADCODE-022`, `WC-UDP-FLOW-CLOSE-NONCANONCODE-024`, `WC-UDP-STREAM-OPEN-NONCANONFLOW-025`, `WC-UDP-STREAM-ACCEPT-NONCANONFLOW-026`, `WC-UDP-DGRAM-NONCANONFLAGS-027`, `WC-UDP-STREAM-CLOSE-NONCANONCODE-028`, `WC-UDP-OK-NONCANONPAYLOAD-029`, `WC-UDP-OK-NONCANONFLOW-030`, `WC-UDP-STREAM-PACKET-NONCANONLEN-031`, `WC-UDP-FLOW-CLOSE-NONCANONFLOW-032`, `WC-UDP-STREAM-CLOSE-NONCANONFLOW-033`, `WC-UDP-OPEN-NONCANONFLOW-034`, `WC-UDP-OPEN-NONCANONFLAGS-035`, `WC-UDP-OPEN-NONCANONTIMEOUT-036`, `WC-UDP-OK-NONCANONTIMEOUT-037`, `WC-UDP-OPEN-IPV4LEN-038`, `WC-UDP-OPEN-BADTARGETTYPE-039`, `WC-UDP-OPEN-IPV6LEN-040`, `WC-UDP-OPEN-EMPTYDOMAIN-041`, `WC-UDP-OK-NONCANONMODE-042`, `WC-UDP-OPEN-NONCANONTARGETTYPE-043`, `WC-UDP-OPEN-NONCANONPORT-044`, `WC-UDP-FLOW-CLOSE-NONCANONMSGLEN-045`, `WC-UDP-STREAM-CLOSE-NONCANONMSGLEN-046`, `WC-UDP-OPEN-ZEROPORT-047`, `WC-UDP-OPEN-BADUTF8DOMAIN-048`, `WC-UDP-OK-ZEROMAXPAYLOAD-049`, `WC-UDP-STREAM-CLOSE-BADUTF8-050`, `WC-UDP-OK-ZEROIDLETIMEOUT-051`, `WC-UDP-FLOW-CLOSE-BADUTF8-052`, `WC-UDP-STREAM-OPEN-BADMETACOUNT-053`, `WC-UDP-STREAM-ACCEPT-BADMETACOUNT-054`, `WC-UDP-OK-BADMETACOUNT-055`, `WC-UDP-OPEN-BADMETACOUNT-056`, `WC-UDP-OPEN-NONCANONMETACOUNT-057`, `WC-UDP-OK-NONCANONMETACOUNT-058`, `WC-UDP-STREAM-OPEN-NONCANONMETACOUNT-059`, `WC-UDP-STREAM-ACCEPT-NONCANONMETACOUNT-060`, `WC-UDP-OPEN-NONCANONMETALEN-061`, `WC-UDP-OK-NONCANONMETALEN-062`, `WC-UDP-STREAM-OPEN-NONCANONMETALEN-063`, `WC-UDP-STREAM-ACCEPT-NONCANONMETALEN-064`, `WC-UDP-OPEN-BADMETALEN-065`, `WC-UDP-OK-BADMETALEN-066`, `WC-UDP-STREAM-OPEN-BADMETALEN-067`, `WC-UDP-STREAM-ACCEPT-BADMETALEN-068`, `WC-UDP-OPEN-NONCANONMETATYPE-069`, `WC-UDP-OK-NONCANONMETATYPE-070`, `WC-UDP-STREAM-OPEN-NONCANONMETATYPE-071`, `WC-UDP-STREAM-ACCEPT-NONCANONMETATYPE-072`, `WC-UDP-OPEN-NONCANONFRAMELEN-073`, `WC-UDP-OK-NONCANONFRAMELEN-074`, `WC-UDP-STREAM-OPEN-NONCANONFRAMELEN-075`, `WC-UDP-STREAM-ACCEPT-NONCANONFRAMELEN-076`, `WC-UDP-FLOW-CLOSE-NONCANONFRAMELEN-077`, `WC-UDP-STREAM-CLOSE-NONCANONFRAMELEN-078`, `WC-UDP-STREAM-PACKET-NONCANONFRAMELEN-079`, `WC-UDP-STREAM-PACKET-BADFRAMELEN-080`, `WC-UDP-STREAM-OPEN-BADFRAMELEN-081`, `WC-UDP-STREAM-ACCEPT-BADFRAMELEN-082`, `WC-UDP-STREAM-CLOSE-BADFRAMELEN-083`, `WC-UDP-FLOW-CLOSE-BADFRAMELEN-084`, `WC-UDP-OK-BADFRAMELEN-085`, `WC-UDP-OPEN-BADFRAMELEN-086`, `WC-UDP-FLOW-CLOSE-DGRAMUNAVAIL-BADFRAMELEN-087`
- `MF`: `MF-MANIFEST-VALID-001`, `MF-MANIFEST-BADSIG-002`, `MF-MANIFEST-EXPIRED-003`, `MF-MANIFEST-SCHEMA-004`, `MF-DISABLEDPROFILE-006`, `MF-EMPTYINVENTORY-007`
- `AU`: `AU-TOKEN-VALID-001`, `AU-TOKEN-EXPIRED-002`, `AU-TOKEN-NBF-FUTURE-003`, `AU-TOKEN-WRONGISS-004`, `AU-TOKEN-WRONGAUD-005`, `AU-TOKEN-WRONGALG-006`, `AU-TOKEN-UNKNOWNKID-007`, `AU-TOKEN-WRONGTYP-008`, `AU-TOKEN-MALFORMED-009`, `AU-TOKEN-NOTYP-010`, `AU-TOKEN-STALEJWKS-011`, `AU-TOKEN-REVOKEDSUB-012`, `AU-TOKEN-STALEPOLICY-013`
- `BG`: `BG-MANIFEST-FETCH-BOOTSTRAP-001`, `BG-MANIFEST-FETCH-REFRESH-002`, `BG-MANIFEST-FETCH-CONFLICT-003`, `BG-DEVICE-REGISTER-VALID-004`, `BG-DEVICE-REGISTER-UNKNOWNFIELD-005`, `BG-TOKEN-EXCHANGE-VALID-006`, `BG-TOKEN-EXCHANGE-MISSINGREFRESH-007`, `BG-DEVICE-REGISTER-LIMIT-008`, `BG-TOKEN-EXCHANGE-REVOKEDDEVICE-009`, `BG-WEBHOOK-VALID-001`, `BG-WEBHOOK-STALE-002`, `BG-WEBHOOK-BADSIG-003`, `BG-WEBHOOK-MISSINGSIG-004`, `BG-WEBHOOK-BADTIMESTAMP-005`, `BG-WEBHOOK-DUPLICATE-006`

## Milestone 3 Through 7 Notes

- Signed carrier-profile selection is now tested in the client runtime using `MF-DISABLEDPROFILE-006`.
- Stale policy epoch remains a token/runtime concern because the frozen manifest schema has no top-level `policy_epoch`; see `docs/implementation/MILESTONE_3_IMPLEMENTATION_NOTES.md`.
- Webhook replay protection is now exercised at the verified bridge-domain ingress point, not only in storage primitives.
- Manifest-driven H3 request-template construction is now exercised through client launch planning.
- Milestone 5 extends live carrier coverage to relay-stream `STREAM_OPEN` and `STREAM_ACCEPT` on localhost after a successful hello.
- Durable replay protection coverage now proves restart persistence plus cross-instance coordination when bridge instances share the same SQLite-backed store.
- Gateway pre-auth budget enforcement is now covered both in `ns-gateway-runtime` unit tests and in the live H3 oversized-hello rejection path.
- Milestone 6 extends live carrier coverage to raw relay-byte forwarding after `STREAM_ACCEPT` and adds HTTP-composition tests for manifest fetch, device register, token exchange, and webhook dedupe over the bridge router.
- Milestone 6 refreshes the `BG-DEVICE-REGISTER-*` fixture bodies so device registration fixtures carry `manifest_id` consistently with the bridge-auth path.
- Milestone 7 moves the live raw relay behavior under the reusable `ns-carrier-h3::forward_raw_tcp_relay` runtime and keeps the integration test pinned to that reusable path instead of a test-local forwarding loop.
- Milestone 7 adds explicit bridge-router checks for refresh-path `304 Not Modified` behavior and route-scoped JSON body-limit rejection before the larger webhook budget applies.
- Milestone 8 adds direct reusable relay-runtime tests for both clean half-close directions, timeout, and oversized-client-prebuffer failure.
- Milestone 8 adds HTTP-backed service-store tests plus bridge-app runtime-composition tests over a shared durable backend so the public service shape is exercised above helper-built router fixtures.
- Milestone 9 adds authenticated remote/shared store coverage, explicit bridge runtime selection for fake vs HTTP Remnawave adapters, and relay close-reason observability assertions on the reusable H3 runtime.
- Milestone 10 adds explicit unauthorized internal store-service access checks, redacted internal-failure response-body checks, bridge-app remote-mode auth enforcement coverage, and live H3 timeout/overload release-path assertions.
- Milestone 11 adds ordered endpoint failover coverage for the remote/shared store path, deployment-topology lifecycle coverage, realistic HTTP Remnawave adapter flow coverage through that topology path, frozen error-registry lock coverage, live overload emitted-frame compatibility for `STREAM_REJECT`, and gateway-runtime structured relay-guard observability assertions.
- Milestone 12 adds frozen UDP control/datagram fixture coverage, transport-neutral UDP flow-open policy and error-mapping tests, live localhost H3 datagram exchange after hello, explicit stream-fallback integration coverage when datagrams are disabled by policy, and explicit `UDP_DATAGRAM_UNAVAILABLE` rejection coverage when datagram-only flows are requested without fallback.
- Milestone 13 adds UDP fallback frame fixtures, UDP-specific fuzz targets and seeded corpora, rollout-disabled forced-fallback coverage, bounded-loss continuation coverage, payload-oversize rejection coverage, wrong-associated-stream rejection coverage, and explicit datagram success or guard observability assertions.
- Milestone 14 adds repeated bounded-loss and bounded-reordering live coverage, MTU-ceiling success coverage, carrier-unavailable fallback coverage, queue-overflow recovery assertions, additional UDP close and truncated-fallback fixtures, and a runnable local UDP fuzz smoke path backed by reviewed corpus sync.
- Milestone 15 adds post-`SERVER_HELLO` drift validation coverage, live rejection coverage for unknown-flow datagrams after close and wrong fallback flow ids, a protocol-violation UDP close fixture, an additional malformed fallback-packet fixture, an opt-in workspace UDP fuzz gate through `scripts/check.*`, and a ratio-based UDP performance threshold harness.
- Milestone 16 adds deterministic delayed-delivery plus short-black-hole datagram coverage without silent fallback, startup/planning rejection when local rollout posture conflicts with signed datagram-disabled profiles, negotiated UDP-limit clamping coverage after `SERVER_HELLO`, and an optional repo-native workflow path for the existing UDP smoke and perf gates.
- Milestone 17 adds a reusable `ns-testkit` UDP WAN-lab profile catalog plus PowerShell and Bash wrappers, reuses the existing live H3 datagram tests as a deterministic CI-safe impairment matrix, extends degraded-path assertions so repeated bounded loss and bounded reordering also keep the established datagram selection sticky, and adds explicit workflow summary output plus an optional WAN-lab input to the repo-native UDP workflow.
- Milestone 18 adds a machine-readable UDP interoperability harness over that same deterministic profile set, makes the optional workflow capable of a short active UDP fuzz run, strengthens public client/runtime datagram-contract validation surfaces, and extends no-silent-fallback assertions to post-close datagram degradation and wrong-associated-stream recovery paths.
- Milestone 19 adds a compatible-host Linux interop-lab lane with uploaded summary artifacts, public `ns-clientd` and `ns-gatewayd` datagram validation surfaces, queue-pressure and clean-shutdown no-silent-fallback assertions, reviewed-corpus sync before active fuzz, and a machine-readable UDP perf summary surface.
- Milestone 20 adds a broader compatible-host Linux rollout-readiness lane, fail-evident summary-artifact checks for enabled UDP workflow lanes, reviewed hello or ping or UDP-control seeds for `control_frame_decoder`, startup-validation symmetry across `ns-clientd`, `ns-gatewayd`, and `nsctl`, and a maintained queue-recovery perf threshold for short datagram saturation recovery.
- Milestone 21 adds a compatible-host Windows rollout-validation lane, public CLI validation tests across `ns-clientd`, `nsctl`, and `ns-gatewayd`, prolonged-impairment and repeated queue-pressure sticky-selection coverage, reviewed MTU-boundary and truncated UDP datagram seeds, and a reusable rollout-validation summary harness in `ns-testkit`.
- Milestone 22 adds a compatible-host macOS rollout-readiness lane, consistent human-readable plus machine-readable startup or negotiated validation outputs across `ns-clientd`, `nsctl`, and `ns-gatewayd`, reviewed truncated `UDP_FLOW_CLOSE` and `UDP_STREAM_CLOSE` seeds, a combined `udp-rollout-readiness.*` recipe, and rollout-validation summary fields that incorporate smoke and perf threshold outcomes.

## Active Fuzz Targets

The baseline cargo-fuzz scaffold now reserves these targets:

- `control_frame_decoder`
- `udp_fallback_frame_decoder`
- `udp_datagram_decoder`
- `manifest_json_parser`

The milestone-14 local smoke path is:

- `cargo run -p ns-testkit --example sync_udp_fuzz_corpus`
- `cargo run -p ns-testkit --example udp_fuzz_smoke`
- `.\scripts\fuzz-udp-smoke.ps1`
- `./scripts/fuzz-udp-smoke.sh`

Milestone 15 additionally makes the smoke path and UDP perf gate easy to opt into through the main repo wrappers:

- PowerShell:
  - `$env:VERTA_ENABLE_UDP_FUZZ_SMOKE = "1"`
  - `$env:VERTA_ENABLE_UDP_PERF_GATE = "1"`
  - `.\scripts\check.ps1`
- Bash:
  - `VERTA_ENABLE_UDP_FUZZ_SMOKE=1 VERTA_ENABLE_UDP_PERF_GATE=1 ./scripts/check.sh`

Milestone 16 additionally adds a repo-native optional workflow path for the same gates:

- `.github/workflows/udp-optional-gates.yml`
- manual `workflow_dispatch`
- reusable `workflow_call`
- Windows-first execution through `.\scripts\check.ps1`

Milestone 17 additionally adds the deterministic WAN-lab path:

- `cargo run -p ns-testkit --example udp_wan_lab`
- `cargo run -p ns-testkit --example udp_interop_lab -- --all`
- `.\scripts\udp-wan-lab.ps1`
- `./scripts/udp-wan-lab.sh`
- `VERTA_ENABLE_UDP_WAN_LAB=1`
- optional `run_wan_lab` input on `.github/workflows/udp-optional-gates.yml`

Milestone 18 additionally adds the opt-in active fuzz and machine-readable interop lane:

- `.\scripts\fuzz-udp-active.ps1`
- `./scripts/fuzz-udp-active.sh`
- `VERTA_ENABLE_UDP_ACTIVE_FUZZ=1`
- optional `run_active_fuzz` input on `.github/workflows/udp-optional-gates.yml`
- default machine-readable interop summary at `target/verta/udp-interop-lab-summary.json`

Milestone 19 additionally tightens the maintained opt-in lane:

- `scripts/fuzz-udp-active.*` now sync reviewed corpora before running active fuzz
- the compatible-host Linux workflow runs `udp_interop_lab` directly and uploads its JSON summary artifact
- `cargo run -p ns-testkit --example udp_perf_gate` now writes `target/verta/udp-perf-gate-summary.json` by default
- a compatible-host operator recipe is now: `./scripts/fuzz-udp-active.sh` after `cargo run -p ns-testkit --example sync_udp_fuzz_corpus`, or the equivalent `run_active_fuzz` workflow input on `.github/workflows/udp-optional-gates.yml`

Milestone 20 additionally broadens the maintained opt-in lane:

- `control_frame_decoder` now consumes reviewed hello, ping, and UDP-control seeds in both `corpus/` and `fuzz_regressions/`
- `scripts/fuzz-udp-active.*` now replay `udp_fuzz_smoke` before the active fuzz campaign and include `control_frame_decoder` alongside the UDP fallback and UDP datagram decoder targets
- `scripts/udp-wan-lab.*` now forward extra harness arguments while still writing a machine-readable summary and failing when that summary is missing
- `.github/workflows/udp-optional-gates.yml` now includes a broader compatible-host rollout-readiness lane that combines corpus sync, smoke replay, the UDP perf gate, the maintained interop harness, queue-pressure validation, and post-close datagram rejection coverage
- enabled WAN-lab, perf, and active-fuzz workflow lanes now fail when their expected machine-readable summary artifacts are missing, so optional verification remains fail-evident instead of best-effort

Milestone 21 additionally broadens the maintained opt-in lane:

- `cargo run -p ns-testkit --example udp_rollout_validation_lab` now replays the maintained CLI validation surfaces plus sticky-selection live tests and writes `target/verta/udp-rollout-validation-summary.json` by default
- `.github/workflows/udp-optional-gates.yml` now includes a compatible-host Windows rollout-validation lane with an uploaded JSON summary artifact
- the reviewed UDP datagram corpus now includes `NS-FX-UDP-DGRAM-MTU-002` and `WC-UDP-DGRAM-TRUNCATED-015` so `udp_datagram_decoder` stays aligned with the hardened conformance set

Milestone 22 additionally broadens the maintained opt-in lane:

- `scripts/udp-rollout-readiness.ps1` and `scripts/udp-rollout-readiness.sh` now combine reviewed-corpus sync, UDP smoke replay, the maintained perf gate, the interop harness, and the rollout-validation harness into one fail-evident compatible-host recipe
- `.github/workflows/udp-optional-gates.yml` now includes a compatible-host macOS rollout-readiness lane with the same machine-readable fuzz-smoke, perf, interop, and rollout-validation summary shape as the Linux rollout-readiness lane
- the reviewed UDP close-path corpus now includes `WC-UDP-FLOW-CLOSE-TRUNCATED-016` and `WC-UDP-STREAM-CLOSE-TRUNCATED-017` so `control_frame_decoder` and `udp_fallback_frame_decoder` stay aligned with the hardened rejection paths
- `udp_rollout_validation_lab` now records smoke and perf threshold pass/fail facts alongside the maintained CLI and live-test outcomes so staged rollout comparison stays machine-readable

Milestone 23 additionally broadens the maintained opt-in lane:

- `scripts/udp-rollout-readiness.ps1` and `scripts/udp-rollout-readiness.sh` now also run `cargo run -p ns-testkit --example udp_rollout_compare` and verify `target/verta/udp-rollout-comparison-summary.json`
- `.github/workflows/udp-optional-gates.yml` now includes a compatible-host Windows rollout-readiness lane with uploaded comparison-summary artifacts alongside the maintained smoke, perf, interop, and rollout-validation summaries
- the reviewed UDP corpus now includes `WC-UDP-OK-TRUNCATED-018` and `WC-UDP-STREAM-ACCEPT-TRUNCATED-019` so `control_frame_decoder` and `udp_fallback_frame_decoder` stay aligned with the hardened `UDP_OK` and `UDP_STREAM_ACCEPT` rejection paths
- `udp_rollout_compare` now consumes the maintained summary family and emits one staged-rollout verdict per host or lane instead of requiring operators to compare separate JSON files by hand

Milestone 24 additionally broadens the maintained opt-in lane:

- `udp_rollout_compare` now supports `--profile readiness|staged_rollout`, and the staged profile fails closed unless a passing active-fuzz summary is present alongside the maintained smoke, perf, interop, and rollout-validation summaries
- `.github/workflows/udp-optional-gates.yml` now includes a compatible-host Linux staged-rollout lane that runs the maintained rollout-readiness recipe with active fuzz enabled and uploads both active-fuzz and comparison summaries
- `udp_rollout_validation_lab` now projects normalized queue-guard headroom facts (`queue_guard_headroom_passed`, `queue_guard_headroom_band`, and path-level queue guard projections) from the maintained perf thresholds instead of forcing operators to interpret raw timing or threshold files by hand
- the reviewed UDP corpus now includes `WC-UDP-OPEN-TRUNCATED-020`, `WC-UDP-DGRAM-NONCANONFLOW-021`, and `WC-UDP-STREAM-CLOSE-BADCODE-022` so control-frame, datagram, and fallback-frame decoding stay aligned with the hardened close and malformed-flow paths

Milestone 25 additionally broadens the maintained opt-in lane:

- `udp_rollout_compare` now emits one stable reusable operator-verdict schema across readiness and staged-rollout profiles, including explicit evidence-state, gate-state, required-summary, considered-summary, and blocking-reason detail fields instead of lane-specific ad-hoc verdict parsing
- `udp_rollout_validation_lab` now projects `selected_datagram_lifecycle_passed` and `queue_guard_limiting_path` so cross-host operator review can distinguish sticky-selection stability from the currently limiting queue-guard path without raw log inspection
- `.github/workflows/udp-optional-gates.yml` now includes a workflow-backed Linux rollout-matrix lane that consumes compatible-host rollout-comparison summaries and uploads a machine-readable cross-host matrix verdict
- the reviewed UDP corpus now includes `WC-UDP-FLOW-CLOSE-NONCANONCODE-024`, `WC-UDP-STREAM-OPEN-NONCANONFLOW-025`, and `WC-UDP-STREAM-ACCEPT-NONCANONFLOW-026` so control-frame and fallback-frame decoding stay aligned with the hardened non-canonical close/open/accept rejection paths

Milestone 26 additionally broadens the maintained opt-in lane:

- `udp_rollout_validation_lab` now projects `longer_impairment_recovery_stable`, and its `clean_shutdown_stable` evidence now reuses the repeated bounded-loss degradation path instead of a simple happy-path round trip
- `.github/workflows/udp-optional-gates.yml` now includes a compatible-host macOS staged-rollout lane with uploaded active-fuzz and rollout-comparison summary artifacts
- maintained CLI validation outputs across `ns-clientd`, `nsctl`, and `ns-gatewayd` now carry `comparison_scope=surface` and `comparison_profile=validation_surface` in both text and JSON modes so rollout tooling can consume them uniformly
- the reviewed UDP corpus now includes `WC-UDP-DGRAM-NONCANONFLAGS-027`, `WC-UDP-STREAM-CLOSE-NONCANONCODE-028`, and `WC-UDP-OK-NONCANONPAYLOAD-029` so datagram, fallback-close, and `UDP_OK` decoding stay aligned with the hardened non-canonical rejection paths

Milestone 27 additionally broadens the maintained opt-in lane:

- `udp_rollout_compare` now exposes `all_required_inputs_present` and `all_required_inputs_passed` on the shared operator-verdict schema so staged host evidence can be consumed uniformly by both host-level and matrix-level rollout decisions
- `udp_rollout_matrix` now consumes that same operator-verdict shape for both `readiness` and `staged_rollout` profiles instead of relying on older comparison-local required-summary fields
- `.github/workflows/udp-optional-gates.yml` now includes a workflow-backed Linux staged-rollout matrix lane that consumes Linux and macOS staged-rollout comparison artifacts and uploads a machine-readable staged matrix verdict
- the reviewed UDP corpus now includes `WC-UDP-OK-NONCANONFLOW-030` and `WC-UDP-STREAM-PACKET-NONCANONLEN-031` so `UDP_OK` and UDP fallback-packet decoding stay aligned with the hardened non-canonical rejection paths

Milestone 28 additionally broadens the maintained opt-in lane:

- `udp_rollout_validation_lab` now projects stable degradation-surface and surface-accounting facts, including `degradation_surface_passed`, `surface_count_total`, `surface_count_passed`, `surface_count_failed`, and `failed_surface_keys`
- `udp_rollout_compare` now fails closed when rollout-validation indicates degraded shutdown or impairment evidence instead of only checking summary presence
- `udp_rollout_matrix` now carries `missing_required_inputs`, `hosts_with_degradation_hold`, `queue_guard_limiting_path_counts`, and `affected_host_count_by_reason_family` for comparison-friendly cross-host review
- `udp_release_workflow` now consumes readiness and staged-rollout matrix summaries and emits `target/verta/udp-release-workflow-summary.json`
- `.github/workflows/udp-optional-gates.yml` now includes a workflow-backed Linux release-workflow lane with uploaded release-workflow summary artifacts
- the reviewed UDP corpus now includes `WC-UDP-FLOW-CLOSE-NONCANONFLOW-032` and `WC-UDP-STREAM-CLOSE-NONCANONFLOW-033` so control-frame and fallback close decoding stay aligned with the hardened non-canonical close-flow rejection paths
- `udp_rollout_compare`, `udp_rollout_matrix`, `udp_release_workflow`, and `udp_deployment_signoff` now share operator-verdict schema version `8`, including explicit missing-input counts, degradation-hold counts, and stable blocking-reason key or family aggregation
- `udp_rollout_validation_lab` now projects `clean_shutdown_stable` and `selected_datagram_lifecycle_stable` from the maintained live datagram round-trip path instead of a mismatched degradation assertion
- `.github/workflows/udp-optional-gates.yml` now includes a workflow-backed Linux deployment-signoff lane with uploaded deployment-signoff summary artifacts
- the reviewed UDP corpus now includes `WC-UDP-OPEN-NONCANONFLOW-034` and `WC-UDP-OPEN-NONCANONFLAGS-035` so control-frame decoding stays aligned with hardened non-canonical `UDP_FLOW_OPEN` rejection paths
- milestone 30 adds reviewed non-canonical `UDP_FLOW_OPEN` and `UDP_OK` timeout seeds (`WC-UDP-OPEN-NONCANONTIMEOUT-036` and `WC-UDP-OK-NONCANONTIMEOUT-037`), shared operator-verdict schema version `9`, explicit required-input accounting on maintained CLI validation surfaces, and a workflow-backed Linux release-prep lane that extends the maintained stack through `scripts/udp-release-prep.*`
- milestone 31 adds reviewed malformed `UDP_FLOW_OPEN` IPv4-length and target-type seeds (`WC-UDP-OPEN-IPV4LEN-038` and `WC-UDP-OPEN-BADTARGETTYPE-039`), shared operator-verdict schema version `10`, explicit gate-state-reason plus required-input-unready accounting across maintained verdict consumers, policy-disabled fallback interop evidence in the maintained rollout stack, and a workflow-backed Linux release-candidate-signoff lane that extends the maintained stack through `scripts/udp-release-candidate-signoff.*`
- milestone 32 adds reviewed malformed `UDP_FLOW_OPEN` IPv6-length and empty-domain seeds plus a non-canonical `UDP_OK` mode seed (`WC-UDP-OPEN-IPV6LEN-040`, `WC-UDP-OPEN-EMPTYDOMAIN-041`, and `WC-UDP-OK-NONCANONMODE-042`), a compatible-host macOS interop-lab workflow lane with uploaded JSON summaries, rollout-validation projection of reordering and transport-fallback-integrity evidence, shared operator-verdict schema version `11`, and a release-gating operator recipe that now also requires a compatible-host macOS interop summary for `udp_release_candidate_signoff`
- milestone 33 adds reviewed malformed `UDP_FLOW_OPEN` target-type and port seeds plus malformed flow-close and stream-close message-length seeds (`WC-UDP-OPEN-NONCANONTARGETTYPE-043`, `WC-UDP-OPEN-NONCANONPORT-044`, `WC-UDP-FLOW-CLOSE-NONCANONMSGLEN-045`, and `WC-UDP-STREAM-CLOSE-NONCANONMSGLEN-046`), a compatible-host Windows interop-lab workflow lane with uploaded JSON summaries, shared operator-verdict schema version `12`, exact supported interop-profile accounting across release-facing consumers, and a release-readiness operator recipe that now also requires a compatible-host Windows interop summary for `udp_release_candidate_signoff`
- milestone 35 adds reviewed malformed `UDP_OK` zero-idle-timeout and bad-metadata-count seeds plus malformed `UDP_FLOW_CLOSE` and fallback bad-metadata-count seeds (`WC-UDP-OK-ZEROIDLETIMEOUT-051`, `WC-UDP-FLOW-CLOSE-BADUTF8-052`, `WC-UDP-STREAM-OPEN-BADMETACOUNT-053`, `WC-UDP-STREAM-ACCEPT-BADMETACOUNT-054`, and `WC-UDP-OK-BADMETACOUNT-055`), a workflow-backed Linux release-soak lane with uploaded JSON summaries, shared operator-verdict schema version `14`, a maintained interop-profile catalog capture path, and a release-soak operator recipe that now also requires Linux, macOS, and Windows interop summaries plus release-burn-in evidence
- milestone 36 adds reviewed malformed UDP metadata-count seeds for flow-open, flow-ok, stream-open, and stream-accept (`WC-UDP-OPEN-BADMETACOUNT-056`, `WC-UDP-OPEN-NONCANONMETACOUNT-057`, `WC-UDP-OK-NONCANONMETACOUNT-058`, `WC-UDP-STREAM-OPEN-NONCANONMETACOUNT-059`, and `WC-UDP-STREAM-ACCEPT-NONCANONMETACOUNT-060`), a workflow-backed Linux release-gate lane with uploaded JSON summaries, per-host compatible-host interop-catalog artifacts for Linux/macOS/Windows, shared operator-verdict schema version `15`, and a sustained release-gate operator recipe that extends the maintained stack through `scripts/udp-release-gate.*`
- milestone 37 adds reviewed malformed UDP metadata-length seeds for flow-open, flow-ok, stream-open, and stream-accept (`WC-UDP-OPEN-NONCANONMETALEN-061`, `WC-UDP-OK-NONCANONMETALEN-062`, `WC-UDP-STREAM-OPEN-NONCANONMETALEN-063`, `WC-UDP-STREAM-ACCEPT-NONCANONMETALEN-064`, `WC-UDP-OPEN-BADMETALEN-065`, `WC-UDP-OK-BADMETALEN-066`, `WC-UDP-STREAM-OPEN-BADMETALEN-067`, and `WC-UDP-STREAM-ACCEPT-BADMETALEN-068`), a workflow-backed Linux release-readiness-burndown lane with uploaded JSON summaries, host-bound compatible-host interop-catalog envelope semantics for release-facing consumers, shared operator-verdict schema version `16`, and a release-readiness burn-down operator recipe that extends the maintained stack through `scripts/udp-release-readiness-burndown.*`
- milestone 38 adds reviewed malformed UDP metadata-type seeds for flow-open, flow-ok, stream-open, and stream-accept (`WC-UDP-OPEN-NONCANONMETATYPE-069`, `WC-UDP-OK-NONCANONMETATYPE-070`, `WC-UDP-STREAM-OPEN-NONCANONMETATYPE-071`, and `WC-UDP-STREAM-ACCEPT-NONCANONMETATYPE-072`), a workflow-backed Linux release-stability-signoff lane with uploaded JSON summaries, the maintained `oversized-payload-guard-recovery` compatible-host interop profile, shared operator-verdict schema version `17`, and a release-stability operator recipe that extends the maintained stack through `scripts/udp-release-stability-signoff.*`
- milestone 39 adds reviewed malformed outer-frame-length seeds for flow-open, flow-ok, stream-open, and stream-accept (`WC-UDP-OPEN-NONCANONFRAMELEN-073`, `WC-UDP-OK-NONCANONFRAMELEN-074`, `WC-UDP-STREAM-OPEN-NONCANONFRAMELEN-075`, and `WC-UDP-STREAM-ACCEPT-NONCANONFRAMELEN-076`), a workflow-backed Linux release-candidate-consolidation lane with uploaded JSON summaries, the maintained `fallback-flow-guard-rejection` compatible-host interop profile, shared operator-verdict schema version `18`, `mtu_ceiling_delivery_stable` rollout-validation evidence, and a release-candidate-consolidation operator recipe that extends the maintained stack through `scripts/udp-release-candidate-consolidation.*`
- milestone 40 adds reviewed malformed close-frame outer-length seeds (`WC-UDP-FLOW-CLOSE-NONCANONFRAMELEN-077` and `WC-UDP-STREAM-CLOSE-NONCANONFRAMELEN-078`), a workflow-backed Linux release-candidate-hardening lane with uploaded JSON summaries, exact compatible-host interop-catalog `source_lane` contract checks in release-gate and release-candidate-consolidation consumers, shared operator-verdict schema version `19`, `fallback_flow_guard_rejection_stable` rollout-validation evidence, and a release-candidate-hardening operator recipe that extends the maintained stack through `scripts/udp-release-candidate-hardening.*`
- milestone 41 adds reviewed malformed fallback-packet outer-length seeds (`WC-UDP-STREAM-PACKET-NONCANONFRAMELEN-079` and `WC-UDP-STREAM-PACKET-BADFRAMELEN-080`) only to the maintained fallback-frame corpus and regression buckets, a workflow-backed Linux release-candidate-evidence-freeze lane with uploaded JSON summaries, exact compatible-host interop-catalog `source_lane` plus failed-profile-count contract checks, shared operator-verdict schema version `20`, `udp_blocked_fallback_surface_passed` rollout-validation evidence, and a release-candidate-evidence-freeze operator recipe that extends the maintained stack through `scripts/udp-release-candidate-evidence-freeze.*`
- milestone 42 adds reviewed malformed fallback stream-open and stream-accept outer-length seeds (`WC-UDP-STREAM-OPEN-BADFRAMELEN-081` and `WC-UDP-STREAM-ACCEPT-BADFRAMELEN-082`) only to the maintained fallback-frame corpus and regression buckets, a workflow-backed Linux release-candidate-signoff-closure lane with uploaded JSON summaries, exact compatible-host interop-catalog `source_lane` plus failed-profile-count and Linux/macOS/Windows host-label-set contract checks, rollout-validation summary version `18` projection of `policy_disabled_fallback_round_trip_stable`, and a release-candidate-signoff-closure operator recipe that extends the maintained stack through `scripts/udp-release-candidate-signoff-closure.*`
- milestone 43 adds reviewed malformed fallback and control close-frame outer-length seeds (`WC-UDP-STREAM-CLOSE-BADFRAMELEN-083` and `WC-UDP-FLOW-CLOSE-BADFRAMELEN-084`) only to the maintained fallback-frame and control-frame corpus/regression buckets, a workflow-backed Linux release-candidate-stabilization lane with uploaded JSON summaries, exact compatible-host interop-catalog `source_lane` plus failed-profile-count and Linux/macOS/Windows host-label-set and readiness-set contract checks, rollout-validation summary version `19` projection of `datagram_only_unavailable_rejection_stable`, and a release-candidate-stabilization operator recipe that extends the maintained stack through `scripts/udp-release-candidate-stabilization.*`
- milestone 44 adds reviewed malformed control-frame outer-length seed `WC-UDP-OK-BADFRAMELEN-085` only to the maintained control-frame corpus and regression buckets, a workflow-backed Linux release-candidate-readiness lane with uploaded JSON summaries, exact compatible-host interop-catalog `source_lane` plus failed-profile-count and Linux/macOS/Windows host-label-set and readiness-set contract checks, rollout-validation summary version `20` plus rollout-comparison projection of `udp_blocked_fallback_surface_passed`, and a release-candidate-readiness operator recipe that extends the maintained stack through `scripts/udp-release-candidate-readiness.*`
- milestone 45 adds reviewed malformed control-frame outer-length seed `WC-UDP-OPEN-BADFRAMELEN-086` only to the maintained control-frame corpus and regression buckets, a workflow-backed Linux release-candidate-acceptance lane with uploaded JSON summaries, exact compatible-host interop-catalog `source_lane` plus failed-profile-count and Linux/macOS/Windows host-label-set and readiness-set contract checks, preserved blocked-fallback plus transport-fallback-integrity contract handling, and a release-candidate-acceptance operator recipe that extends the maintained stack through `scripts/udp-release-candidate-acceptance.*`
- milestone 46 adds reviewed malformed control-frame outer-length seed `WC-UDP-FLOW-CLOSE-DGRAMUNAVAIL-BADFRAMELEN-087` only to the maintained control-frame corpus and regression buckets, a workflow-backed Linux release-candidate-certification lane with uploaded JSON summaries, exact compatible-host interop-catalog `source_lane` plus failed-profile-count and Linux/macOS/Windows host-label-set contract checks, preserved blocked-fallback plus policy-disabled-fallback and transport-fallback-integrity certification handling, and a release-candidate-certification operator recipe that extends the maintained stack through `scripts/udp-release-candidate-certification.*`

These are the next targets to add when the surrounding code is ready:

- `token_claims_boundary`

Fuzzing rules:

- Treat panics, OOM-like growth, or pathological allocation behavior as failures.
- Do not suppress parser errors that should be observable in normal tests.
- Keep target bodies narrow and deterministic.
- Add regression seeds under `fuzz/cargo-fuzz/fuzz_regressions/` when a crash is fixed.
- Keep UDP seeds derived from reviewed fixtures under `fuzz/cargo-fuzz/corpus/` so transport regressions stay reproducible.

## Interop And Chaos Hooks

Start with transcript-oriented interop before live multi-node tests:

- Save future client/gateway handshakes under `fixtures/interop/transcripts/`.
- Capture bridge-issued manifests and tokens used in interop runs.
- Keep transcript metadata lightweight: timestamp, crate/app version, carrier profile, and outcome.

When live carrier work begins, add:

- Connection timeout chaos cases
- Delayed control-frame delivery
- Out-of-order close handling
- Token-expiry boundary timing

## Deferred Items

These items are intentionally scaffolded but not yet implemented:

- default-on fuzz runs in CI or sustained local campaigns beyond the current smoke path
- default-on CI execution for the UDP smoke and perf gates beyond the new optional workflow path
- Cross-version interop matrix execution
- Replay-cache coordination tests for remote or service-backed shared webhook stores beyond the SQLite path
- A real upstream Remnawave adapter path for bridge-app integration tests beyond the current fake adapter
- Broader live datagram traffic over the H3 carrier beyond the current localhost success, fallback, bounded-loss, bounded-reordering, MTU, oversize, and wrong-associated-stream slice
