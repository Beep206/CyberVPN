# AI Team

Northstar is set up for specialist delegation.
Use the smallest agent that matches the task, keep one coherent goal per thread, and have the parent agent retain final responsibility for integration and verification.

## protocol_architect

- Delegate when the task needs architecture framing, invariant review, ADR drafting, or spec conflict resolution.
- Good output is a short decision memo, ADR draft, or unresolved-question list with citations into `docs/spec/`.
- Sample prompt: `Use protocol_architect to map the governing specs for this task, identify the invariants we must preserve, and draft an ADR if a durable decision is required.`

## wire_format_guardian

- Delegate when a change touches frames, encodings, registries, manifest fields, versioning, or malformed-input behavior.
- Good output is a compatibility verdict, ordered findings, and the minimum extra tests needed before merge.
- Sample prompt: `Use wire_format_guardian to audit this diff for on-the-wire compatibility and flag any required ADR or spec updates.`

## rust_impl_engineer

- Delegate when the task is Rust workspace scaffolding, crate layout, interfaces, or stable-Rust implementation structure.
- Good output is a small patch set, a clear verification list, and explicit notes about any spec ambiguity that blocked deeper work.
- Sample prompt: `Use rust_impl_engineer to scaffold the Rust workspace pieces needed for this phase without implementing unstated protocol behavior.`

## quic_transport_engineer

- Delegate when the work is transport-specific and centers on QUIC, HTTP/3, Quinn, rustls, or carrier-side behavior.
- Good output is a transport-scoped patch or design note that preserves the transport-agnostic session core.
- Sample prompt: `Use quic_transport_engineer to design or implement the QUIC carrier boundary while keeping session-core abstractions clean.`

## remnawave_bridge_engineer

- Delegate when the task touches manifests, subscription or bootstrap flows, adapter logic, or bridge APIs that face Remnawave.
- Good output is a boundary map, a contract checklist, and a patch or plan that preserves the non-fork path.
- Sample prompt: `Use remnawave_bridge_engineer to review this bridge-facing change and confirm it stays on the external-control-plane path without panel coupling.`

## security_reviewer

- Delegate when a change affects trust boundaries, tokens, logging, limits, negotiation, or parser behavior and needs a threat-driven pass.
- Good output is a finding list tied to attacker capabilities, plus concrete mitigations and test gaps.
- Sample prompt: `Use security_reviewer to run the threat-model gates against this change and surface concrete downgrade, replay, or exhaustion risks.`

## fuzz_interop_engineer

- Delegate when a task needs malformed-input coverage, fuzz targets, conformance fixtures, interop planning, or crash repro harnesses.
- Good output is a deterministic test matrix, corpus plan, and clear next steps for CI-friendly validation.
- Sample prompt: `Use fuzz_interop_engineer to turn the relevant spec rules into a negative-test and interop coverage plan for this surface.`

## perf_engineer

- Delegate when a task needs performance budgets, benchmark scenarios, tracing hooks, or evidence before optimization.
- Good output is a measurable benchmark plan, observability requirements, and a narrow perf patch when appropriate.
- Sample prompt: `Use perf_engineer to define a reproducible benchmark plan and the tracing or metrics needed to explain bottlenecks in this subsystem.`

## docs_release_editor

- Delegate when a change affects RFC-facing docs, onboarding, examples, verification commands, or release notes.
- Good output is a synchronized doc patch or a tight drift checklist linked back to the governing specs and ADRs.
- Sample prompt: `Use docs_release_editor to sweep the affected docs, examples, and release-facing notes so they stay aligned with this change.`

## Delegation Pattern

1. Have the parent agent identify the governing specs and define the narrow sub-task.
2. Delegate to one specialist at a time unless the work is clearly independent.
3. Review the returned output against `AGENTS.md`, the relevant specs, and the diff before merging it into the main thread.
