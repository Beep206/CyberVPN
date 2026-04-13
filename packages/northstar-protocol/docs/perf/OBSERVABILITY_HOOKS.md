# Northstar v0.1 Observability Hooks

## Purpose

This document defines the minimum observability hooks for the current Northstar baseline.
It is not an exporter design.
It records which stable counters, gauges, histograms, and structured events must exist so rollout, performance, reliability, and abuse behavior are diagnosable without widening protocol or bridge contracts.

This document is grounded in:

- `docs/spec/northstar_implementation_spec_rust_workspace_plan_v0_1.md`
  - section 10.7, `ns-observability`
  - section 17, observability implementation rules
  - section 18.3, resource budget discipline
  - section 26, benchmarking and performance engineering plan
- `docs/spec/northstar_blueprint_v0.md`
  - section 27, observability blueprint
  - section 28.3, backpressure and memory discipline
  - section 30.4, success reporting
- `docs/spec/northstar_threat_model_v0_1.md`
  - section 13.8, privacy and observability threats
  - TM-DS-02, token exchange flood
  - TM-DS-03, gateway handshake flood
- `docs/spec/northstar_wire_format_freeze_candidate_v0_1.md`
  - timer and payload limits that shape alert thresholds
  - metadata and error semantics that constrain public signals

## Design Rules

- Use structured tracing throughout the workspace.
- Keep field names standardized through `ns-observability`.
- Default to privacy-safe identifiers and redaction-aware wrappers.
- Separate transport symptoms from auth, policy, or bridge failures.
- Record queue depth and shed or drop behavior anywhere bounded work can saturate.
- Keep high-cardinality labels under explicit review.
- Keep qlog disabled by default and enable it only per run, per endpoint, or per development workflow.
- Keep rollout and verification summaries as summary-layer artifacts; do not turn host-specific workflow output into new runtime event families.

## Standard Field Set

The first baseline should standardize these field families across spans and structured events:

- `session.id`
- `device.id`
- `manifest.id`
- `policy.epoch`
- `bridge.req_id`
- `carrier.kind`
- `stream.id`
- `flow.id`
- `error.code`
- `close.reason`
- `reason`
- `limit.name`
- `limit.value`

Recommended supporting fields:

- `http.route`
- `backend.name`
- `backend.scope`
- `endpoint.hash`
- `available`
- `operation`
- `failure.kind`
- `status.code`
- `queue.name`
- `queue.depth`
- `queue.capacity`
- `queue.action`

All identifier fields must be privacy-safe by default.
Raw account ids, bootstrap materials, tokens, and hardware identifiers must not be emitted.

## Redaction Rules

Treat the following as sensitive:

- bootstrap URLs and bootstrap credentials
- raw session tokens
- signing keys and secret material
- raw hardware identifiers
- raw target domains when policy marks them sensitive
- full manifest bodies in normal logs

Required behavior:

- tokens and secrets are always redacted
- debug logging is explicit and time-bounded
- crash reports are scrubbed
- support bundles require affirmative export
- observability pipelines are treated as sensitive systems

## Metric Families

### Gateway metrics

The gateway baseline should expose:

- `sessions_opened_total`
- `sessions_rejected_total`
- `session_duration_seconds`
- `relay_streams_opened_total`
- `udp_flows_opened_total`
- `udp_datagrams_in_total`
- `udp_datagrams_out_total`
- `udp_datagram_drop_total`
- `hello_failures_total{code=...}`
- `control_body_too_large_total`
- `pre_auth_deadline_exceeded_total`
- `token_verify_failures_total`
- `policy_denials_total`
- `target_resolution_failures_total`
- `upstream_connect_failures_total`
- `active_sessions`
- `active_streams`
- `active_udp_flows`

### Client metrics

The client baseline should expose:

- `manifest_fetch_total`
- `manifest_verify_failures_total`
- `token_exchange_total`
- `carrier_connect_failures_total`
- `session_establish_latency_ms`
- `reconnect_total`
- `endpoint_switch_total`
- `profile_switch_total`
- `local_proxy_accept_total`
- `network_change_events_total`

### Bridge metrics

The bridge path should expose:

- `bridge_manifest_requests_total`
- `bridge_manifest_compile_failures_total`
- `bridge_token_exchange_total`
- `bridge_token_exchange_failures_total`
- `bridge_device_register_total`
- `bridge_webhook_verify_failures_total`
- `bridge_webhook_duplicates_total`
- `bridge_device_limit_denials_total`
- `bridge_signer_queue_depth`
- `bridge_signer_queue_rejections_total`
- `bridge_remnawave_ingest_age_seconds`

### Queue and pressure metrics

These remain mandatory because the specs require bounded queues and visible pressure:

- `queue_depth{queue=...}`
- `queue_capacity{queue=...}`
- `queue_drop_total{queue=...,reason=...}`
- `queue_wait_latency_ms{queue=...}`
- `backpressure_events_total{surface=...,action=...}`
- `memory_pressure_events_total{surface=...}`

The current baseline additionally requires visible datagram and relay pressure:

- gateway pending-hello queue depth, capacity, and shed counters
- relay overload, prebuffer-limit, and idle-timeout counters
- datagram selection, fallback-selection, and unavailability counters
- datagram payload-oversize, queue-full, flow-burst, and session-burst guard counters
- remote/shared store health and failure-kind visibility for primary and fallback endpoints

## Current Structured Event Families

The stable structured event families currently implemented through `ns-observability` are:

- `northstar.bridge.store.backend_selected`
- `northstar.bridge.store.service_health`
- `northstar.bridge.store.service_failure`
- `northstar.bridge.http.body_rejected`
- `northstar.gateway.relay.guard`
- `northstar.carrier.relay.closed`
- `northstar.carrier.datagram.selection`
- `northstar.carrier.datagram.guard`
- `northstar.carrier.datagram.io`

Rules for these event families:

- keep them low-cardinality
- prefer stable reason codes such as `relay_overloaded`, `relay_prebuffer_exceeded`, `relay_idle_timeout`, `udp_datagram_queue_full`, `udp_datagram_flow_burst_exceeded`, and `udp_associated_stream_mismatch`
- keep `limit_name`, `limit_value`, and `actual_value` as the stable budget surface instead of minting new event names for each budget
- keep rollout-disabled fallback, carrier-unavailable fallback, and datagram-unavailable rejection attributable through existing datagram selection or guard surfaces instead of ad-hoc workflow events

## Public CLI Validation Surfaces

The maintained operator-facing validation commands in `ns-clientd`, `nsctl`, and `ns-gatewayd` now have stable summary-layer outputs.

Required summary fields:

- `validation_result=valid|invalid`
- `surface=startup_contract|negotiated_contract|client_plan|hello_contract`
- `comparison_family`
- `comparison_label`
- `comparison_schema`
- `comparison_schema_version`
- `comparison_scope`
- `comparison_profile`
- `evidence_state`
- `gate_state`
- `verdict`
- `required_input_count`
- `required_input_present_count`
- `required_input_passed_count`
- `required_input_missing_count`
- `required_input_failed_count`
- `required_input_unready_count`
- `all_required_inputs_present`
- `all_required_inputs_passed`
- `gate_state_reason`
- `gate_state_reason_family`
- `degradation_hold_count`
- `queue_guard_tight_hold_count`
- `queue_guard_headroom_missing_count`
- `queue_pressure_hold_count`
- `blocking_reason_count`
- `blocking_reason_key`
- `blocking_reason_family`
- `simulated_inputs=true` for manual readiness facts
- signed datagram intent, rollout stage, carrier availability, resolved datagram mode, and negotiated-limit outcomes
- stable `error_class` and `error_message` fields on fail-closed mismatch paths

These outputs are summary surfaces, not new tracing families.
They must stay consistent across text and JSON modes without adding host-specific or workflow-specific runtime labels.

## Rollout Summary Surfaces

The maintained staged-rollout recipe now emits machine-readable JSON artifacts in addition to the runtime tracing families:

- `target/northstar/udp-fuzz-smoke-summary.json`
- `target/northstar/udp-perf-gate-summary.json`
- `target/northstar/udp-interop-lab-summary.json`
- `target/northstar/udp-rollout-validation-summary.json`
- `target/northstar/udp-active-fuzz-summary.json`
- `target/northstar/udp-rollout-comparison-summary.json`
- `target/northstar/udp-rollout-matrix-summary.json`
- `target/northstar/udp-release-workflow-summary.json`
- `target/northstar/udp-deployment-signoff-summary.json`
- `target/northstar/udp-release-prep-summary.json`
- `target/northstar/udp-release-candidate-signoff-summary.json`
- `target/northstar/udp-release-burn-in-summary.json`
- `target/northstar/udp-release-soak-summary.json`
- `target/northstar/udp-release-gate-summary.json`
- `target/northstar/udp-release-readiness-burndown-summary.json`
- `target/northstar/udp-release-stability-signoff-summary.json`
- `target/northstar/udp-release-candidate-consolidation-summary.json`
- `target/northstar/udp-release-candidate-hardening-summary.json`
- `target/northstar/udp-release-candidate-evidence-freeze-summary.json`
- `target/northstar/udp-release-candidate-signoff-closure-summary.json`
- `target/northstar/udp-release-candidate-stabilization-summary.json`
- `target/northstar/udp-release-candidate-readiness-summary.json`
- `target/northstar/udp-release-candidate-acceptance-summary.json`
- `target/northstar/udp-release-candidate-certification-summary.json`
- `target/northstar/udp-interop-lab-summary-windows.json`
- `target/northstar/udp-interop-profile-catalog.json`
- `target/northstar/udp-interop-profile-catalog-linux.json`
- `target/northstar/udp-interop-profile-catalog-macos.json`
- `target/northstar/udp-interop-profile-catalog-windows.json`

Summary-layer rules:

- keep `udp_rollout_compare` as a summary consumer over existing smoke, perf, interop, and rollout-validation artifacts instead of adding a new runtime event family
- keep `udp_rollout_compare --profile staged_rollout` as a summary consumer over the same artifacts plus `udp-active-fuzz-summary.json` instead of adding a new runtime event family
- keep `udp_rollout_compare` on one stable operator-verdict schema version `20` with reusable `comparison_schema`, `comparison_schema_version`, `verdict_family`, `decision_scope`, `decision_label`, `evidence_state`, `gate_state`, `gate_state_reason`, `gate_state_reason_family`, `required_inputs`, `considered_inputs`, `all_required_inputs_present`, `all_required_inputs_passed`, `required_input_count`, `required_input_present_count`, `required_input_passed_count`, `required_input_missing_count`, `required_input_failed_count`, `required_input_unready_count`, `degradation_hold_count`, `queue_guard_tight_hold_count`, `queue_guard_headroom_missing_count`, `queue_pressure_hold_count`, `blocking_reason_key_counts`, `blocking_reason_key_count`, `blocking_reason_family_count`, `blocking_reason_keys`, `blocking_reason_families`, `policy_disabled_fallback_surface_passed`, `transport_fallback_integrity_surface_passed`, `interop_required_no_silent_fallback_profile_slugs`, and blocking-reason detail fields instead of host-specific verdict formats
- keep `udp_rollout_matrix` as a summary consumer over rollout-comparison artifacts instead of adding a new runtime event family
- keep `udp_rollout_matrix` on that same shared schema vocabulary so staged-rollout matrix verdicts do not invent matrix-only required-input semantics
- keep `udp_release_workflow` as a summary consumer over readiness and staged-rollout matrix artifacts instead of adding a new runtime event family
- keep `udp_deployment_signoff` as a summary consumer over release-workflow and compatible-host rollout-validation artifacts instead of adding a new runtime event family
- keep `udp_release_prep` as a summary consumer over deployment-signoff plus Linux, macOS, and Windows rollout-validation artifacts instead of adding a new runtime event family
- keep `udp_release_candidate_signoff` as a summary consumer over release-prep plus Windows rollout-readiness, compatible-host Windows interop, and compatible-host macOS interop artifacts instead of adding a new runtime event family
- keep `udp_release_burn_in` as a summary consumer over release-candidate-signoff plus Linux/macOS/Windows rollout-readiness and staged-rollout matrix artifacts instead of adding a new runtime event family
- keep `udp_release_soak` as a summary consumer over release-burn-in plus Linux/macOS/Windows interop artifacts instead of adding a new runtime event family
- keep `udp_release_gate` as a summary consumer over release-soak plus Linux/macOS/Windows interop-profile catalogs instead of adding a new runtime event family
- keep `udp_release_readiness_burndown` as a summary consumer over release-gate plus Linux/macOS/Windows rollout-readiness artifacts instead of adding a new runtime event family
- keep `udp_release_stability_signoff` as a summary consumer over release-readiness-burndown plus Linux/macOS/Windows compatible-host interop artifacts instead of adding a new runtime event family
- keep `udp_release_candidate_consolidation` as a summary consumer over release-stability-signoff plus Linux/macOS/Windows compatible-host interop-profile catalogs instead of adding a new runtime event family
- keep `udp_release_candidate_hardening` as a summary consumer over release-candidate-consolidation plus Linux/macOS/Windows rollout-validation artifacts instead of adding a new runtime event family
- keep `udp_release_candidate_evidence_freeze` as a summary consumer over release-candidate-hardening plus Linux/macOS/Windows compatible-host interop-profile catalogs instead of adding a new runtime event family
- keep `udp_release_candidate_signoff_closure` as a summary consumer over release-candidate-evidence-freeze plus Linux/macOS/Windows rollout-readiness artifacts instead of adding a new runtime event family
- keep normalized queue-saturation comparison fields (`queue_saturation_worst_case`, `queue_saturation_worst_utilization_pct`) derived from maintained perf thresholds rather than raw host timings
- keep normalized queue-guard headroom fields (`queue_guard_headroom_passed`, `queue_guard_headroom_band`, `queue_guard_rejection_path_passed`, `queue_guard_recovery_path_passed`, `queue_guard_burst_path_passed`) derived from maintained perf thresholds rather than raw host timings
- keep `selected_datagram_lifecycle_passed`, `reordering_no_silent_fallback_passed`, `oversized_payload_guard_recovery_stable`, `reordered_after_close_rejection_stable`, `mtu_ceiling_delivery_stable`, `fallback_flow_guard_rejection_stable`, `udp_blocked_fallback_surface_passed`, `datagram_only_unavailable_rejection_stable`, `queue_pressure_surface_passed`, `policy_disabled_fallback_round_trip_stable`, `longer_impairment_recovery_stable`, `shutdown_sequence_stable`, `degradation_surface_passed`, `transport_fallback_integrity_surface_passed`, `surface_count_total`, `surface_count_passed`, `surface_count_failed`, `failed_surface_keys`, `passed_command_count`, `failed_command_count`, and `queue_guard_limiting_path` derived from maintained validation and perf evidence rather than raw host logs
- keep `udp_rollout_matrix` queue-headroom aggregation in low-cardinality `queue_guard_headroom_band_counts` instead of raw cross-host timing comparisons
- keep `udp_rollout_matrix`, `udp_release_workflow`, `udp_deployment_signoff`, `udp_release_prep`, `udp_release_candidate_signoff`, `udp_release_burn_in`, `udp_release_soak`, `udp_release_gate`, `udp_release_readiness_burndown`, `udp_release_stability_signoff`, `udp_release_candidate_consolidation`, `udp_release_candidate_hardening`, `udp_release_candidate_evidence_freeze`, `udp_release_candidate_signoff_closure`, `udp_release_candidate_stabilization`, `udp_release_candidate_readiness`, and `udp_release_candidate_acceptance` on stable low-cardinality aggregation fields such as `queue_guard_limiting_path_counts`, `queue_guard_headroom_missing_count`, `queue_guard_tight_hold_count`, `queue_pressure_hold_count`, `queue_hold_input_count`, `queue_hold_host_count`, `affected_host_count_by_reason_family`, `affected_matrix_count_by_reason_family`, `interop_failed_profile_count`, validation-surface counts, validation-command counts, interop-profile-catalog labels, exact interop-profile-catalog host labels, exact interop-profile-catalog source lanes, and blocking-reason family counts instead of host-specific release heuristics
- keep sticky-selection and rollout-surface verdicts projected from existing datagram-selection, datagram-guard, and CLI validation surfaces
- keep blocking reasons stable and low-cardinality through values such as `missing_active_fuzz_summary`, `active_fuzz_summary_failed`, `queue_guard_headroom_tight`, and `policy_disabled_fallback_surface_failed`
- keep blocking-reason family aggregation summary-only through `blocking_reason_family_counts` rather than minting new runtime event names
- do not add per-host, per-run, or workflow-specific cardinality to structured carrier or CLI events just because rollout summaries are produced

## qlog and Development Diagnostics

The H3 carrier should support optional qlog output during development and performance testing.

qlog rules for the current baseline:

- disabled by default
- enabled per run or per endpoint
- sampled or rotated
- stored outside normal operator logs
- scrubbed before external sharing

## Minimal Alert and Review Targets

The current baseline should make the following conditions visible enough to alert or block release review:

- rising handshake rejection rate by reason
- persistent pre-auth overload or body-size rejection spikes
- queue saturation or queue rejection on ingress-facing paths
- token verification latency regression
- manifest verification failure spikes
- bridge ingest staleness beyond target freshness
- sustained memory pressure or repeated write-budget enforcement
- unexpected increase in datagram fallback rate
- rollout comparison verdict drift or queue-saturation regression across maintained host lanes

## Verification Checklist

A new performance-sensitive or rollout-sensitive path is not observability-ready unless reviewers can verify:

- there is at least one span or structured event around the operation
- success and failure outcomes are counted
- latency is measurable where it matters
- queue saturation is visible if bounded work is involved
- sensitive fields are redacted by default
- transport symptoms and auth or policy failures are distinguishable
- operator-facing validation output stays consistent in text and JSON modes
- summary-layer rollout artifacts reuse existing low-cardinality runtime surfaces instead of inventing new ones
