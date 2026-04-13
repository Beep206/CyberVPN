# Northstar Cargo Fuzz Scaffold

This directory holds the cargo-fuzz targets for Northstar parser, UDP fallback-frame, and manifest hardening work.

## Active targets

- `control_frame_decoder`
- `udp_fallback_frame_decoder`
- `udp_datagram_decoder`
- `manifest_json_parser`

## Local runnable verification path

Northstar keeps the first UDP fuzz path runnable even when `cargo fuzz` is not installed.

PowerShell first:

```powershell
.\scripts\fuzz-udp-smoke.ps1
```

Bash second:

```bash
./scripts/fuzz-udp-smoke.sh
```

Those wrappers run:

```text
cargo run -p ns-testkit --example sync_udp_fuzz_corpus
cargo run -p ns-testkit --example udp_fuzz_smoke
```

The sync step derives corpus and regression seeds from reviewed wire fixtures under `fixtures/wire/v1/`.
The smoke step replays those seeds through normal Cargo binaries so regression coverage is available on Windows-first developer machines without requiring libFuzzer tooling.

Milestone 15 additionally makes the smoke path easy to opt into through the normal repo check wrappers:

PowerShell:

```powershell
$env:NORTHSTAR_ENABLE_UDP_FUZZ_SMOKE = "1"
.\scripts\check.ps1
```

Bash:

```bash
NORTHSTAR_ENABLE_UDP_FUZZ_SMOKE=1 ./scripts/check.sh
```

The same wrappers can also opt into the UDP perf threshold gate with `NORTHSTAR_ENABLE_UDP_PERF_GATE=1`.
Milestone 17 additionally makes the deterministic UDP WAN-lab path available through the same wrappers with `NORTHSTAR_ENABLE_UDP_WAN_LAB=1`.
Milestone 18 additionally makes a short active `cargo fuzz` path available through the same repo-native verification lane, with the Windows-first wrapper keeping that path explicit and the compatible-host workflow running it end to end.

Milestone 16 additionally adds a repo-native optional workflow path for the same gates:

- `.github/workflows/udp-optional-gates.yml`
- manual `workflow_dispatch`
- reusable `workflow_call`
- Windows-first execution through `.\scripts\check.ps1`
- optional `run_wan_lab` input for the deterministic CI-safe UDP WAN-lab profile set
- optional `run_active_fuzz` input for a short `cargo fuzz` campaign
- explicit workflow summary output for the enabled UDP verification surfaces

## Deterministic UDP WAN-lab path

Northstar now keeps a reusable CI-safe UDP WAN-lab profile catalog in `ns-testkit`.

PowerShell first:

```powershell
.\scripts\udp-wan-lab.ps1
```

Bash second:

```bash
./scripts/udp-wan-lab.sh
```

Those wrappers run the machine-readable interoperability harness:

```text
cargo run -p ns-testkit --example udp_interop_lab -- --all --summary-path target/northstar/udp-interop-lab-summary.json
```

Use the catalog example when you only want the named profile set and filters:

```text
cargo run -p ns-testkit --example udp_wan_lab
```

The interoperability harness runs the matching live localhost QUIC/H3 tests for:

- bounded loss
- bounded reordering
- delayed delivery plus short degradation
- MTU pressure
- carrier-unavailable fallback

and writes a machine-readable summary to `target/northstar/udp-interop-lab-summary.json` by default.

Northstar also keeps a staged-rollout validation harness for compatible hosts:

```text
cargo run -p ns-testkit --example udp_rollout_validation_lab -- --summary-path target/northstar/udp-rollout-validation-summary.json
```

That harness replays the maintained CLI validation surfaces plus sticky-selection live UDP checks and writes a machine-readable summary to `target/northstar/udp-rollout-validation-summary.json` by default.
It now also records `longer_impairment_recovery_stable`, `reordering_no_silent_fallback_passed`, `mtu_ceiling_delivery_stable`, `udp_blocked_fallback_surface_passed`, `policy_disabled_fallback_round_trip_stable`, and `transport_fallback_integrity_surface_passed` so staged rollout review is not limited to a happy-path shutdown proof.

The ratio-based UDP perf gate now writes a companion machine-readable summary to `target/northstar/udp-perf-gate-summary.json` by default:

```text
cargo run -p ns-testkit --example udp_perf_gate
```

Northstar now also keeps a staged-rollout comparison harness for compatible hosts:

```text
cargo run -p ns-testkit --example udp_rollout_compare -- --summary-path target/northstar/udp-rollout-comparison-summary.json
```

That harness consumes the maintained smoke, perf, interop, and rollout-validation summaries and emits one machine-readable staged-rollout verdict per host or lane.
It now fails closed on unsupported upstream summary versions and carries required-input counts, queue-pressure hold accounting, and stable blocking-reason key aggregation for wrapper and workflow consumers on shared operator-verdict schema version `18`.

Northstar now also keeps a workflow-backed cross-host rollout matrix harness:

```text
cargo run -p ns-testkit --example udp_rollout_matrix -- --input target/northstar/udp-rollout-comparison-summary.json
```

That harness consumes one or more rollout-comparison summaries and emits a machine-readable cross-host verdict for staged operator rollout review.
It now also fails closed on unsupported operator-verdict schema versions and carries the same required-input counts plus stable blocking-reason key aggregation as the host-level comparison surface.

Northstar now also keeps a release-workflow aggregation harness:

```text
cargo run -p ns-testkit --example udp_release_workflow -- --input target/northstar/udp-rollout-matrix-summary.json
```

That harness consumes readiness and staged-rollout matrix summaries and emits a machine-readable release-workflow verdict for operator release review.
It fails closed on unsupported matrix summary versions, missing readiness or staged evidence, degradation holds, or missing active-fuzz-backed staged inputs.

Northstar now also keeps a deployment-signoff aggregation harness:

```text
cargo run -p ns-testkit --example udp_deployment_signoff -- --release-workflow target/northstar/udp-release-workflow-summary.json --validation target/northstar/udp-rollout-validation-summary-windows.json
```

That harness consumes release-workflow evidence plus compatible-host rollout-validation summaries and emits a machine-readable deployment-candidate signoff verdict for operator release review.
It fails closed when release-workflow evidence is missing or not ready, when compatible-host rollout-validation evidence is missing, drifted, or degraded, or when missing-input and blocking-reason accounting is inconsistent.

Northstar now also keeps a release-prep aggregation harness:

```text
cargo run -p ns-testkit --example udp_release_prep -- --deployment-signoff target/northstar/udp-deployment-signoff-summary.json --validation target/northstar/udp-rollout-validation-summary-linux.json --validation target/northstar/udp-rollout-validation-summary-macos.json --validation target/northstar/udp-rollout-validation-summary-windows.json
```

That harness consumes deployment-signoff evidence plus Linux, macOS, and Windows rollout-validation summaries and emits a machine-readable release-prep verdict for operator release review.
It fails closed when deployment-signoff evidence is missing or not ready, when any required compatible-host rollout-validation summary is missing, drifted, degraded, or not ready, or when missing-input and blocking-reason accounting is inconsistent.

Northstar now also keeps a release-candidate-signoff aggregation harness:

```text
cargo run -p ns-testkit --example udp_release_candidate_signoff -- --release-prep target/northstar/udp-release-prep-summary.json --windows-readiness target/northstar/udp-rollout-comparison-summary-windows.json --windows-interop target/northstar/udp-interop-lab-summary-windows.json --macos-interop target/northstar/udp-interop-lab-summary-macos.json
```

That harness consumes release-prep evidence plus Windows rollout-readiness, compatible-host Windows interop, and compatible-host macOS interop summaries and emits a machine-readable release-candidate signoff verdict for operator release review.
It fails closed when release-prep evidence is missing or not ready, when the Windows rollout-readiness summary is missing, drifted, degraded, or not ready, when the compatible-host Windows or macOS interop summaries are missing, drifted, degraded, or not ready, when required-input and blocking-reason accounting is inconsistent, when the supported compatible-host interop profile inventory drifts, or when the maintained policy-disabled fallback, queue-pressure, or transport-fallback-integrity surfaces do not pass.

Northstar now also keeps a release-burn-in aggregation harness:

```text
cargo run -p ns-testkit --example udp_release_burn_in -- --release-candidate-signoff target/northstar/udp-release-candidate-signoff-summary.json --linux-readiness target/northstar/udp-rollout-comparison-summary-linux.json --macos-readiness target/northstar/udp-rollout-comparison-summary-macos.json --windows-readiness target/northstar/udp-rollout-comparison-summary-windows.json --staged-matrix target/northstar/udp-rollout-matrix-summary-staged.json
```

That harness consumes release-candidate-signoff plus Linux, macOS, and Windows rollout-readiness evidence together with the staged-rollout matrix and emits a machine-readable release-burn-in verdict for operator release review.
It fails closed when any required release-facing summary is missing, drifted, degraded, or not ready, when exact interop-profile-contract accounting drifts, or when queue-headroom-missing, queue-tight-hold, or transport-fallback-integrity evidence remains unresolved.

Northstar now also keeps a release-soak aggregation harness:

```text
cargo run -p ns-testkit --example udp_release_soak -- --release-burn-in target/northstar/udp-release-burn-in-summary.json --linux-interop target/northstar/udp-interop-lab-summary-linux.json --macos-interop target/northstar/udp-interop-lab-summary-macos.json --windows-interop target/northstar/udp-interop-lab-summary-windows.json
```

That harness consumes release-burn-in plus Linux, macOS, and Windows interop summaries and emits a machine-readable release-soak verdict for operator release review.
It fails closed when any required release-facing summary is missing, drifted, degraded, or not ready, when exact interop-profile-contract accounting drifts, or when queue-headroom-missing, queue-tight-hold, queue-pressure-hold, policy-disabled-fallback, or transport-fallback-integrity evidence remains unresolved.

Northstar now also keeps a release-gate aggregation harness:

```text
cargo run -p ns-testkit --example udp_release_gate -- --release-soak target/northstar/udp-release-soak-summary.json --linux-interop-catalog target/northstar/udp-interop-profile-catalog-linux.json --macos-interop-catalog target/northstar/udp-interop-profile-catalog-macos.json --windows-interop-catalog target/northstar/udp-interop-profile-catalog-windows.json
```

That harness consumes release-soak plus Linux, macOS, and Windows compatible-host interop catalogs and emits a machine-readable release-gate verdict for operator release review.
It fails closed when release-soak evidence is missing, drifted, degraded, or not ready, when any required compatible-host interop catalog is missing or contract-invalid, when exact supported interop-profile inventory drifts, or when queue-headroom-missing, queue-tight-hold, queue-pressure-hold, policy-disabled-fallback, or transport-fallback-integrity evidence remains unresolved.

Northstar now also keeps a release-readiness-burndown aggregation harness:

```text
cargo run -p ns-testkit --example udp_release_readiness_burndown -- --release-gate target/northstar/udp-release-gate-summary.json --linux-readiness target/northstar/udp-rollout-comparison-summary-linux.json --macos-readiness target/northstar/udp-rollout-comparison-summary-macos.json --windows-readiness target/northstar/udp-rollout-comparison-summary-windows.json
```

That harness consumes release-gate plus Linux, macOS, and Windows rollout-readiness summaries and emits a machine-readable release-readiness-burndown verdict for operator release review.
It fails closed when release-gate evidence is missing, drifted, degraded, or not ready, when any required compatible-host rollout-readiness summary is missing, drifted, degraded, or not ready, when exact compatible-host interop-catalog host-label accounting drifts, or when queue-hold-input and summary-contract accounting remains unresolved.

Northstar now also keeps a release-stability-signoff aggregation harness:

```text
cargo run -p ns-testkit --example udp_release_stability_signoff -- --release-readiness-burndown target/northstar/udp-release-readiness-burndown-summary.json --linux-interop target/northstar/udp-interop-lab-summary-linux.json --macos-interop target/northstar/udp-interop-lab-summary-macos.json --windows-interop target/northstar/udp-interop-lab-summary-windows.json
```

That harness consumes release-readiness-burndown plus Linux, macOS, and Windows compatible-host interop summaries and emits a machine-readable release-stability-signoff verdict for operator release review.
It fails closed when release-readiness-burndown evidence is missing, drifted, degraded, or not ready, when any required compatible-host interop summary is missing, drifted, degraded, or not ready, when exact compatible-host interop inventory or catalog-host coverage drifts, or when queue-hold-input, queue-hold-host, policy-disabled-fallback, or transport-fallback-integrity evidence remains unresolved.

Northstar now also keeps a release-candidate-consolidation aggregation harness:

```text
cargo run -p ns-testkit --example udp_release_candidate_consolidation -- --release-stability-signoff target/northstar/udp-release-stability-signoff-summary.json --linux-interop-catalog target/northstar/udp-interop-profile-catalog-linux.json --macos-interop-catalog target/northstar/udp-interop-profile-catalog-macos.json --windows-interop-catalog target/northstar/udp-interop-profile-catalog-windows.json
```

That harness consumes release-stability-signoff plus Linux, macOS, and Windows compatible-host interop catalogs and emits a machine-readable release-candidate-consolidation verdict for operator release review.
It fails closed when release-stability-signoff evidence is missing, drifted, degraded, or not ready, when any required compatible-host interop catalog is missing or contract-invalid, when exact supported interop inventory, required-no-silent-fallback profile accounting, or Linux/macOS/Windows host-label coverage drifts, or when queue-hold-input, queue-hold-host, policy-disabled-fallback, or transport-fallback-integrity evidence remains unresolved.

Northstar now also keeps a release-candidate-hardening aggregation harness:

```text
cargo run -p ns-testkit --example udp_release_candidate_hardening -- --release-candidate-consolidation target/northstar/udp-release-candidate-consolidation-summary.json --linux-validation target/northstar/udp-rollout-validation-summary-linux.json --macos-validation target/northstar/udp-rollout-validation-summary-macos.json --windows-validation target/northstar/udp-rollout-validation-summary-windows.json
```

That harness consumes release-candidate-consolidation plus Linux, macOS, and Windows rollout-validation summaries and emits a machine-readable release-candidate-hardening verdict for operator release review.
It fails closed when release-candidate-consolidation evidence is missing, drifted, degraded, or not ready, when any required rollout-validation summary is missing, drifted, degraded, or not ready, when exact compatible-host interop-catalog `source_lane` provenance drifts through release-facing consumers, or when `mtu_ceiling_delivery_stable`, `fallback_flow_guard_rejection_stable`, queue-headroom-missing, queue-tight-hold, queue-pressure-hold, policy-disabled-fallback, or transport-fallback-integrity evidence remains unresolved.

Northstar now also keeps a release-candidate-evidence-freeze aggregation harness:

```text
cargo run -p ns-testkit --example udp_release_candidate_evidence_freeze -- --release-candidate-hardening target/northstar/udp-release-candidate-hardening-summary.json --linux-interop-catalog target/northstar/udp-interop-profile-catalog-linux.json --macos-interop-catalog target/northstar/udp-interop-profile-catalog-macos.json --windows-interop-catalog target/northstar/udp-interop-profile-catalog-windows.json
```

That harness consumes release-candidate-hardening plus Linux, macOS, and Windows compatible-host interop catalogs and emits a machine-readable release-candidate-evidence-freeze verdict for operator release review.
It fails closed when release-candidate-hardening evidence is missing, drifted, degraded, or not ready, when any required compatible-host interop catalog is missing or contract-invalid, when exact compatible-host interop-catalog `source_lane` provenance drifts, when `interop_failed_profile_count` drifts from the failed-profile inventory, or when a passed compatible-host interop contract still carries failed profiles.

Northstar now also keeps a release-candidate-signoff-closure aggregation harness:

```text
cargo run -p ns-testkit --example udp_release_candidate_signoff_closure -- --release-candidate-evidence-freeze target/northstar/udp-release-candidate-evidence-freeze-summary.json --linux-readiness target/northstar/udp-rollout-comparison-summary-linux.json --macos-readiness target/northstar/udp-rollout-comparison-summary-macos.json --windows-readiness target/northstar/udp-rollout-comparison-summary-windows.json
```

That harness consumes release-candidate-evidence-freeze plus Linux, macOS, and Windows rollout-readiness summaries and emits a machine-readable release-candidate-signoff-closure verdict for operator release review.
It fails closed when release-candidate-evidence-freeze evidence is missing, drifted, degraded, or not ready, when any required rollout-readiness summary is missing, drifted, degraded, or not ready, when exact compatible-host interop-catalog `source_lane` provenance drifts, when `interop_failed_profile_count` drifts from the failed-profile inventory, when a passed compatible-host interop contract still carries failed profiles, when the exact Linux/macOS/Windows host-label set drifts, or when `policy_disabled_fallback_round_trip_stable` remains unresolved.

Northstar now also keeps a release-candidate-stabilization aggregation harness:

```text
cargo run -p ns-testkit --example udp_release_candidate_stabilization -- --release-candidate-signoff-closure target/northstar/udp-release-candidate-signoff-closure-summary.json --linux-interop-catalog target/northstar/udp-interop-profile-catalog-linux.json --macos-interop-catalog target/northstar/udp-interop-profile-catalog-macos.json --windows-interop-catalog target/northstar/udp-interop-profile-catalog-windows.json
```

That harness consumes release-candidate-signoff-closure plus Linux, macOS, and Windows compatible-host interop catalogs and emits a machine-readable release-candidate-stabilization verdict for operator release review.
It fails closed when release-candidate-signoff-closure evidence is missing, drifted, degraded, or not ready, when any required compatible-host interop catalog is missing or contract-invalid, when exact compatible-host interop-catalog `source_lane` provenance drifts, when `interop_failed_profile_count` drifts from the failed-profile inventory, when the exact Linux/macOS/Windows host-label set drifts, when the carried readiness set drifts, or when `policy_disabled_fallback_round_trip_stable` remains unresolved.

Northstar now also keeps a release-candidate-readiness aggregation harness:

```text
cargo run -p ns-testkit --example udp_release_candidate_readiness -- --release-candidate-stabilization target/northstar/udp-release-candidate-stabilization-summary.json --linux-readiness target/northstar/udp-rollout-comparison-summary-linux.json --macos-readiness target/northstar/udp-rollout-comparison-summary-macos.json --windows-readiness target/northstar/udp-rollout-comparison-summary-windows.json
```

That harness consumes release-candidate-stabilization plus Linux, macOS, and Windows rollout-readiness summaries and emits a machine-readable release-candidate-readiness verdict for operator release review.
It fails closed when release-candidate-stabilization evidence is missing, drifted, degraded, or not ready, when any required rollout-readiness summary is missing, drifted, degraded, or not ready, when exact compatible-host interop-catalog `source_lane` provenance drifts, when `interop_failed_profile_count` drifts from the failed-profile inventory, when the exact Linux/macOS/Windows host-label set or carried readiness set drifts, when `udp_blocked_fallback_surface_passed` remains unresolved through rollout-comparison consumers, or when `policy_disabled_fallback_round_trip_stable` or transport-fallback-integrity evidence remains unresolved.

Northstar now also keeps a release-candidate-acceptance aggregation harness:

```text
cargo run -p ns-testkit --example udp_release_candidate_acceptance -- --release-candidate-readiness target/northstar/udp-release-candidate-readiness-summary.json --linux-readiness target/northstar/udp-rollout-comparison-summary-linux.json --macos-readiness target/northstar/udp-rollout-comparison-summary-macos.json --windows-readiness target/northstar/udp-rollout-comparison-summary-windows.json
```

That harness consumes release-candidate-readiness plus Linux, macOS, and Windows rollout-readiness summaries and emits a machine-readable release-candidate-acceptance verdict for operator release review.
It fails closed when release-candidate-readiness evidence is missing, drifted, degraded, or not ready, when any required rollout-readiness summary is missing, drifted, degraded, or not ready, when exact compatible-host interop-catalog `source_lane` provenance drifts, when `interop_failed_profile_count` drifts from the failed-profile inventory, when the exact Linux/macOS/Windows host-label set or carried readiness set drifts, or when `udp_blocked_fallback_surface_passed`, `policy_disabled_fallback_round_trip_stable`, or transport-fallback-integrity evidence remains unresolved.

Northstar now also keeps a release-candidate-certification aggregation harness:

```text
cargo run -p ns-testkit --example udp_release_candidate_certification -- --release-candidate-acceptance target/northstar/udp-release-candidate-acceptance-summary.json --linux-interop-catalog target/northstar/udp-interop-profile-catalog-linux.json --macos-interop-catalog target/northstar/udp-interop-profile-catalog-macos.json --windows-interop-catalog target/northstar/udp-interop-profile-catalog-windows.json
```

That harness consumes release-candidate-acceptance plus Linux, macOS, and Windows compatible-host interop catalogs and emits a machine-readable release-candidate-certification verdict for operator release review.
It fails closed when release-candidate-acceptance evidence is missing, drifted, degraded, or not ready, when any required compatible-host interop catalog is missing or contract-invalid, when exact compatible-host interop-catalog `source_lane` provenance drifts, when `interop_failed_profile_count` drifts from the failed-profile inventory, when the exact Linux/macOS/Windows host-label set drifts, or when `udp_blocked_fallback_surface_passed`, `policy_disabled_fallback_round_trip_stable`, or transport-fallback-integrity evidence remains unresolved.

The maintained compatible-host interop catalog can also be captured directly:

```text
cargo run -p ns-testkit --example udp_interop_lab -- --list --format json > target/northstar/udp-interop-profile-catalog.json
```

That catalog records the exact required-no-silent-fallback compatible-host profile set expected by release-facing consumers.
Compatible-host lanes should also emit host-specific copies at `target/northstar/udp-interop-profile-catalog-linux.json`, `...-macos.json`, and `...-windows.json` for workflow-backed release consumers.

## Optional active fuzz commands

If `cargo fuzz` is installed locally and the nightly toolchain is available, these targets are ready:

```powershell
cargo +nightly fuzz run control_frame_decoder
cargo +nightly fuzz run udp_fallback_frame_decoder
cargo +nightly fuzz run udp_datagram_decoder
```

Northstar also keeps short wrappers for that opt-in path:

PowerShell:

```powershell
.\scripts\fuzz-udp-active.ps1
```

Bash:

```bash
./scripts/fuzz-udp-active.sh
```

The active wrappers replay `udp_fuzz_smoke` first, then run `control_frame_decoder`, `udp_fallback_frame_decoder`, and `udp_datagram_decoder` for a short bounded campaign.
Before fuzzing, they sync the maintained reviewed corpus so compatible-host runs stay aligned with the checked-in seed set.
They fail clearly if either `cargo-fuzz` or the nightly toolchain is missing.
The Windows-first default is `NORTHSTAR_UDP_ACTIVE_FUZZ_SANITIZER=none` so the optional lane stays runnable without extra ASAN runtime setup; override it explicitly if you want a sanitizer-backed run on a machine that supports it.
Set `NORTHSTAR_UDP_ACTIVE_FUZZ_SECONDS` to tune runtime locally or in the optional workflow.
Compatible-host runs now also write `target/northstar/udp-active-fuzz-summary.json` by default unless `NORTHSTAR_UDP_ACTIVE_FUZZ_SUMMARY_PATH` overrides it.

The maintained reviewed UDP wire corpus now also includes:

- `WC-UDP-OK-ZEROIDLETIMEOUT-051`
- `WC-UDP-FLOW-CLOSE-BADUTF8-052`
- `WC-UDP-STREAM-OPEN-BADMETACOUNT-053`
- `WC-UDP-STREAM-ACCEPT-BADMETACOUNT-054`
- `WC-UDP-OK-BADMETACOUNT-055`
- `WC-UDP-OPEN-BADMETACOUNT-056`
- `WC-UDP-OPEN-NONCANONMETACOUNT-057`
- `WC-UDP-OK-NONCANONMETACOUNT-058`
- `WC-UDP-STREAM-OPEN-NONCANONMETACOUNT-059`
- `WC-UDP-STREAM-ACCEPT-NONCANONMETACOUNT-060`
- `WC-UDP-OPEN-NONCANONMETALEN-061`
- `WC-UDP-OK-NONCANONMETALEN-062`
- `WC-UDP-STREAM-OPEN-NONCANONMETALEN-063`
- `WC-UDP-STREAM-ACCEPT-NONCANONMETALEN-064`
- `WC-UDP-OPEN-BADMETALEN-065`
- `WC-UDP-OK-BADMETALEN-066`
- `WC-UDP-STREAM-OPEN-BADMETALEN-067`
- `WC-UDP-STREAM-ACCEPT-BADMETALEN-068`
- `WC-UDP-OPEN-NONCANONMETATYPE-069`
- `WC-UDP-OK-NONCANONMETATYPE-070`
- `WC-UDP-STREAM-OPEN-NONCANONMETATYPE-071`
- `WC-UDP-STREAM-ACCEPT-NONCANONMETATYPE-072`
- `WC-UDP-OPEN-NONCANONFRAMELEN-073`
- `WC-UDP-OK-NONCANONFRAMELEN-074`
- `WC-UDP-STREAM-OPEN-NONCANONFRAMELEN-075`
- `WC-UDP-STREAM-ACCEPT-NONCANONFRAMELEN-076`

On the current Windows-first local path, `scripts/check.ps1` keeps active fuzz explicit but does not treat it as a normal local prerequisite.
Use the compatible-host workflow lane or `./scripts/fuzz-udp-active.sh` on a supported nightly cargo-fuzz host for end-to-end active runs.

Compatible-host recipe:

```bash
cargo run -p ns-testkit --example sync_udp_fuzz_corpus
./scripts/fuzz-udp-active.sh
```

Compatible-host rollout-readiness recipe:

```bash
./scripts/udp-rollout-readiness.sh
```

That recipe now produces:

- `target/northstar/udp-fuzz-smoke-summary.json`
- `target/northstar/udp-perf-gate-summary.json`
- `target/northstar/udp-interop-lab-summary.json`
- `target/northstar/udp-rollout-validation-summary.json`
- `target/northstar/udp-rollout-comparison-summary.json`

Compatible-host staged-rollout recipe:

```bash
NORTHSTAR_ENABLE_UDP_ACTIVE_FUZZ=1 \
NORTHSTAR_UDP_ROLLOUT_COMPARE_PROFILE=staged_rollout \
./scripts/udp-rollout-readiness.sh
```

That recipe additionally produces:

- `target/northstar/udp-active-fuzz-summary.json`

and makes `udp_rollout_compare` fail closed unless the active-fuzz summary passes.

Compatible-host staged-rollout comparison recipe:

```bash
cargo run -p ns-testkit --example sync_udp_fuzz_corpus
NORTHSTAR_ENABLE_UDP_ACTIVE_FUZZ=1 \
NORTHSTAR_UDP_ROLLOUT_COMPARE_PROFILE=staged_rollout \
./scripts/udp-rollout-readiness.sh
cargo run -p ns-testkit --example udp_rollout_matrix -- \
  --input target/northstar/udp-rollout-comparison-summary.json
```

That recipe combines corpus sync, smoke replay, perf, interop, rollout-validation, active fuzz, per-host comparison, and a final cross-host matrix verdict.

Release-burn-in recipe:

```bash
cargo run -p ns-testkit --example sync_udp_fuzz_corpus
NORTHSTAR_ENABLE_UDP_ACTIVE_FUZZ=1 \
NORTHSTAR_UDP_ROLLOUT_COMPARE_PROFILE=staged_rollout \
./scripts/udp-rollout-readiness.sh
./scripts/udp-release-burn-in.sh
```

That recipe combines corpus sync, smoke replay, perf, interop, rollout-validation, active fuzz, per-host comparison, staged matrix, release-candidate signoff, and a final release-burn-in verdict.

Release-candidate staged-rollout matrix recipe:

```bash
cargo run -p ns-testkit --example sync_udp_fuzz_corpus
NORTHSTAR_ENABLE_UDP_ACTIVE_FUZZ=1 \
NORTHSTAR_UDP_ROLLOUT_COMPARE_PROFILE=staged_rollout \
./scripts/udp-rollout-readiness.sh
./scripts/udp-rollout-matrix.sh \
  --input target/northstar/udp-rollout-comparison-summary.json
```

The shared operator-verdict schema now carries:

- `comparison_schema = "udp_rollout_operator_verdict"`
- `comparison_schema_version = 15`
- `all_required_inputs_present`
- `all_required_inputs_passed`
- `required_input_count`
- `required_input_present_count`
- `required_input_passed_count`
- `required_input_missing_count`
- `required_input_failed_count`
- `required_input_unready_count`
- `gate_state_reason`
- `gate_state_reason_family`
- `queue_guard_tight_hold_count`
- `degradation_hold_count`
- `blocking_reason_key_count`
- `blocking_reason_family_count`
- `blocking_reason_key_counts`
- `blocking_reason_keys`
- `blocking_reason_families`
- `policy_disabled_fallback_surface_passed`
- `transport_fallback_integrity_surface_passed`

so host-level, matrix-level, release-workflow, deployment-signoff, release-prep, and release-candidate-signoff consumers use the same required-input and blocking semantics.
The same shared operator-verdict schema now stays on version `20` for release-gate, release-readiness-burndown, release-stability-signoff, release-candidate-consolidation, release-candidate-hardening, release-candidate-evidence-freeze, and release-candidate-signoff-closure consumers as well, including exact interop-profile-catalog contract semantics, host-label accounting, exact `source_lane` provenance, queue-hold-input aggregation, queue-hold-host aggregation, and `interop_failed_profile_count`.

Release-workflow recipe:

```bash
cargo run -p ns-testkit --example sync_udp_fuzz_corpus
NORTHSTAR_ENABLE_UDP_ACTIVE_FUZZ=1 \
NORTHSTAR_UDP_ROLLOUT_COMPARE_PROFILE=staged_rollout \
./scripts/udp-rollout-readiness.sh
./scripts/udp-rollout-matrix.sh \
  --input target/northstar/udp-rollout-comparison-summary.json
./scripts/udp-release-workflow.sh \
  --input target/northstar/udp-rollout-matrix-summary.json
```

That recipe produces:

- `target/northstar/udp-fuzz-smoke-summary.json`
- `target/northstar/udp-perf-gate-summary.json`
- `target/northstar/udp-interop-lab-summary.json`
- `target/northstar/udp-rollout-validation-summary.json`
- `target/northstar/udp-active-fuzz-summary.json`
- `target/northstar/udp-rollout-comparison-summary.json`
- `target/northstar/udp-rollout-matrix-summary.json`
- `target/northstar/udp-release-workflow-summary.json`

and keeps release-workflow decisions fail closed unless readiness and staged-rollout matrix evidence both pass on the shared schema.

Deployment-candidate release recipe:

```bash
cargo run -p ns-testkit --example sync_udp_fuzz_corpus
NORTHSTAR_ENABLE_UDP_ACTIVE_FUZZ=1 \
NORTHSTAR_UDP_ROLLOUT_COMPARE_PROFILE=staged_rollout \
./scripts/udp-rollout-readiness.sh
./scripts/udp-rollout-matrix.sh \
  --input target/northstar/udp-rollout-comparison-summary.json
./scripts/udp-release-workflow.sh \
  --input target/northstar/udp-rollout-matrix-summary.json
./scripts/udp-deployment-signoff.sh \
  --release-workflow target/northstar/udp-release-workflow-summary.json \
  --validation target/northstar/udp-rollout-validation-summary.json
```

That recipe additionally produces:

- `target/northstar/udp-deployment-signoff-summary.json`

and keeps deployment-signoff decisions fail closed unless release-workflow evidence is ready and the compatible-host rollout-validation summary passes on the same shared schema.

Release-prep operator recipe:

```bash
cargo run -p ns-testkit --example sync_udp_fuzz_corpus
NORTHSTAR_ENABLE_UDP_ACTIVE_FUZZ=1 \
NORTHSTAR_UDP_ROLLOUT_COMPARE_PROFILE=staged_rollout \
./scripts/udp-rollout-readiness.sh
./scripts/udp-rollout-matrix.sh \
  --input target/northstar/udp-rollout-comparison-summary.json
./scripts/udp-release-workflow.sh \
  --input target/northstar/udp-rollout-matrix-summary.json
./scripts/udp-deployment-signoff.sh \
  --release-workflow target/northstar/udp-release-workflow-summary.json \
  --validation target/northstar/udp-rollout-validation-summary.json
./scripts/udp-release-prep.sh \
  --deployment-signoff target/northstar/udp-deployment-signoff-summary.json \
  --validation target/northstar/udp-rollout-validation-summary-linux.json \
  --validation target/northstar/udp-rollout-validation-summary-macos.json \
  --validation target/northstar/udp-rollout-validation-summary-windows.json
```

That recipe additionally produces:

- `target/northstar/udp-release-prep-summary.json`

and keeps release-prep decisions fail closed unless deployment-signoff evidence is ready and the Linux, macOS, and Windows rollout-validation summaries all pass on the same shared schema.

Release-candidate operator recipe:

```bash
cargo run -p ns-testkit --example sync_udp_fuzz_corpus
NORTHSTAR_ENABLE_UDP_ACTIVE_FUZZ=1 \
NORTHSTAR_UDP_ROLLOUT_COMPARE_PROFILE=staged_rollout \
./scripts/udp-rollout-readiness.sh
./scripts/udp-rollout-matrix.sh \
  --input target/northstar/udp-rollout-comparison-summary.json
./scripts/udp-release-workflow.sh \
  --input target/northstar/udp-rollout-matrix-summary.json
./scripts/udp-deployment-signoff.sh \
  --release-workflow target/northstar/udp-release-workflow-summary.json \
  --validation target/northstar/udp-rollout-validation-summary.json
./scripts/udp-release-prep.sh \
  --deployment-signoff target/northstar/udp-deployment-signoff-summary.json \
  --validation target/northstar/udp-rollout-validation-summary-linux.json \
  --validation target/northstar/udp-rollout-validation-summary-macos.json \
  --validation target/northstar/udp-rollout-validation-summary-windows.json
./scripts/udp-release-candidate-signoff.sh \
  --release-prep target/northstar/udp-release-prep-summary.json \
  --windows-readiness target/northstar/udp-rollout-comparison-summary-windows.json \
  --windows-interop target/northstar/udp-interop-lab-summary-windows.json \
  --macos-interop target/northstar/udp-interop-lab-summary-macos.json
```

That recipe additionally produces:

- `target/northstar/udp-release-candidate-signoff-summary.json`

and keeps release-candidate signoff decisions fail closed unless release-prep evidence is ready, Windows rollout-readiness passes on the same shared schema, the compatible-host Windows and macOS interop summaries remain healthy, the supported interop profile inventory stays exact, and the maintained policy-disabled fallback, queue-pressure, and transport-fallback-integrity surfaces remain proven.

Release-readiness burn-down operator recipe:

```bash
cargo run -p ns-testkit --example sync_udp_fuzz_corpus
NORTHSTAR_ENABLE_UDP_ACTIVE_FUZZ=1 \
NORTHSTAR_UDP_ROLLOUT_COMPARE_PROFILE=staged_rollout \
./scripts/udp-rollout-readiness.sh
./scripts/udp-rollout-matrix.sh \
  --input target/northstar/udp-rollout-comparison-summary.json
./scripts/udp-release-workflow.sh \
  --input target/northstar/udp-rollout-matrix-summary.json
./scripts/udp-deployment-signoff.sh \
  --release-workflow target/northstar/udp-release-workflow-summary.json \
  --validation target/northstar/udp-rollout-validation-summary.json
./scripts/udp-release-prep.sh \
  --deployment-signoff target/northstar/udp-deployment-signoff-summary.json \
  --validation target/northstar/udp-rollout-validation-summary-linux.json \
  --validation target/northstar/udp-rollout-validation-summary-macos.json \
  --validation target/northstar/udp-rollout-validation-summary-windows.json
./scripts/udp-release-candidate-signoff.sh \
  --release-prep target/northstar/udp-release-prep-summary.json \
  --windows-readiness target/northstar/udp-rollout-comparison-summary-windows.json \
  --windows-interop target/northstar/udp-interop-lab-summary-windows.json \
  --macos-interop target/northstar/udp-interop-lab-summary-macos.json
./scripts/udp-release-burn-in.sh
./scripts/udp-release-soak.sh
./scripts/udp-release-gate.sh \
  --release-soak target/northstar/udp-release-soak-summary.json \
  --linux-interop-catalog target/northstar/udp-interop-profile-catalog-linux.json \
  --macos-interop-catalog target/northstar/udp-interop-profile-catalog-macos.json \
  --windows-interop-catalog target/northstar/udp-interop-profile-catalog-windows.json
./scripts/udp-release-readiness-burndown.sh \
  --release-gate target/northstar/udp-release-gate-summary.json \
  --linux-readiness target/northstar/udp-rollout-comparison-summary-linux.json \
  --macos-readiness target/northstar/udp-rollout-comparison-summary-macos.json \
  --windows-readiness target/northstar/udp-rollout-comparison-summary-windows.json
```

That recipe combines corpus sync, smoke replay, perf, interop, rollout-validation, active fuzz, comparison, matrix, release-workflow, deployment-signoff, release-prep, release-candidate-signoff, release-burn-in, release-soak, release-gate, and release-readiness-burndown summaries for release-readiness review, with the final burn-down also consuming the maintained host-specific interop catalogs carried through release-gate.

Release-stability operator recipe:

```bash
cargo run -p ns-testkit --example sync_udp_fuzz_corpus
NORTHSTAR_ENABLE_UDP_ACTIVE_FUZZ=1 \
NORTHSTAR_UDP_ROLLOUT_COMPARE_PROFILE=staged_rollout \
./scripts/udp-rollout-readiness.sh
./scripts/udp-rollout-matrix.sh \
  --input target/northstar/udp-rollout-comparison-summary.json
./scripts/udp-release-workflow.sh \
  --input target/northstar/udp-rollout-matrix-summary.json
./scripts/udp-deployment-signoff.sh \
  --release-workflow target/northstar/udp-release-workflow-summary.json \
  --validation target/northstar/udp-rollout-validation-summary.json
./scripts/udp-release-prep.sh \
  --deployment-signoff target/northstar/udp-deployment-signoff-summary.json \
  --validation target/northstar/udp-rollout-validation-summary-linux.json \
  --validation target/northstar/udp-rollout-validation-summary-macos.json \
  --validation target/northstar/udp-rollout-validation-summary-windows.json
./scripts/udp-release-candidate-signoff.sh \
  --release-prep target/northstar/udp-release-prep-summary.json \
  --windows-readiness target/northstar/udp-rollout-comparison-summary-windows.json \
  --windows-interop target/northstar/udp-interop-lab-summary-windows.json \
  --macos-interop target/northstar/udp-interop-lab-summary-macos.json
./scripts/udp-release-burn-in.sh
./scripts/udp-release-soak.sh
./scripts/udp-release-gate.sh \
  --release-soak target/northstar/udp-release-soak-summary.json \
  --linux-interop-catalog target/northstar/udp-interop-profile-catalog-linux.json \
  --macos-interop-catalog target/northstar/udp-interop-profile-catalog-macos.json \
  --windows-interop-catalog target/northstar/udp-interop-profile-catalog-windows.json
./scripts/udp-release-readiness-burndown.sh \
  --release-gate target/northstar/udp-release-gate-summary.json \
  --linux-readiness target/northstar/udp-rollout-comparison-summary-linux.json \
  --macos-readiness target/northstar/udp-rollout-comparison-summary-macos.json \
  --windows-readiness target/northstar/udp-rollout-comparison-summary-windows.json
./scripts/udp-release-stability-signoff.sh \
  --release-readiness-burndown target/northstar/udp-release-readiness-burndown-summary.json \
  --linux-interop target/northstar/udp-interop-lab-summary-linux.json \
  --macos-interop target/northstar/udp-interop-lab-summary-macos.json \
  --windows-interop target/northstar/udp-interop-lab-summary-windows.json
```

That recipe combines corpus sync, smoke replay, perf, interop, rollout-validation, active fuzz, comparison, matrix, release-workflow, deployment-signoff, release-prep, release-candidate-signoff, release-burn-in, release-soak, release-gate, release-readiness-burndown, and release-stability-signoff summaries for release-stability review, with the final signoff consuming the maintained host-specific interop catalogs and the host-level queue-hold burn-down carried forward from release-readiness.

Release-candidate consolidation recipe:

```bash
cargo run -p ns-testkit --example sync_udp_fuzz_corpus
NORTHSTAR_ENABLE_UDP_ACTIVE_FUZZ=1 \
NORTHSTAR_UDP_ROLLOUT_COMPARE_PROFILE=staged_rollout \
./scripts/udp-rollout-readiness.sh
./scripts/udp-rollout-matrix.sh \
  --input target/northstar/udp-rollout-comparison-summary.json
./scripts/udp-release-workflow.sh \
  --input target/northstar/udp-rollout-matrix-summary.json
./scripts/udp-deployment-signoff.sh \
  --release-workflow target/northstar/udp-release-workflow-summary.json \
  --validation target/northstar/udp-rollout-validation-summary.json
./scripts/udp-release-prep.sh \
  --deployment-signoff target/northstar/udp-deployment-signoff-summary.json \
  --validation target/northstar/udp-rollout-validation-summary-linux.json \
  --validation target/northstar/udp-rollout-validation-summary-macos.json \
  --validation target/northstar/udp-rollout-validation-summary-windows.json
./scripts/udp-release-candidate-signoff.sh \
  --release-prep target/northstar/udp-release-prep-summary.json \
  --windows-readiness target/northstar/udp-rollout-comparison-summary-windows.json \
  --windows-interop target/northstar/udp-interop-lab-summary-windows.json \
  --macos-interop target/northstar/udp-interop-lab-summary-macos.json
./scripts/udp-release-burn-in.sh
./scripts/udp-release-soak.sh
./scripts/udp-release-gate.sh \
  --release-soak target/northstar/udp-release-soak-summary.json \
  --linux-interop-catalog target/northstar/udp-interop-profile-catalog-linux.json \
  --macos-interop-catalog target/northstar/udp-interop-profile-catalog-macos.json \
  --windows-interop-catalog target/northstar/udp-interop-profile-catalog-windows.json
./scripts/udp-release-readiness-burndown.sh \
  --release-gate target/northstar/udp-release-gate-summary.json \
  --linux-readiness target/northstar/udp-rollout-comparison-summary-linux.json \
  --macos-readiness target/northstar/udp-rollout-comparison-summary-macos.json \
  --windows-readiness target/northstar/udp-rollout-comparison-summary-windows.json
./scripts/udp-release-stability-signoff.sh \
  --release-readiness-burndown target/northstar/udp-release-readiness-burndown-summary.json \
  --linux-interop target/northstar/udp-interop-lab-summary-linux.json \
  --macos-interop target/northstar/udp-interop-lab-summary-macos.json \
  --windows-interop target/northstar/udp-interop-lab-summary-windows.json
./scripts/udp-release-candidate-consolidation.sh \
  --release-stability-signoff target/northstar/udp-release-stability-signoff-summary.json \
  --linux-interop-catalog target/northstar/udp-interop-profile-catalog-linux.json \
  --macos-interop-catalog target/northstar/udp-interop-profile-catalog-macos.json \
  --windows-interop-catalog target/northstar/udp-interop-profile-catalog-windows.json
./scripts/udp-release-candidate-hardening.sh \
  --release-candidate-consolidation target/northstar/udp-release-candidate-consolidation-summary.json \
  --linux-validation target/northstar/udp-rollout-validation-summary-linux.json \
  --macos-validation target/northstar/udp-rollout-validation-summary-macos.json \
  --windows-validation target/northstar/udp-rollout-validation-summary-windows.json
./scripts/udp-release-candidate-evidence-freeze.sh \
  --release-candidate-hardening target/northstar/udp-release-candidate-hardening-summary.json \
  --linux-interop-catalog target/northstar/udp-interop-profile-catalog-linux.json \
  --macos-interop-catalog target/northstar/udp-interop-profile-catalog-macos.json \
  --windows-interop-catalog target/northstar/udp-interop-profile-catalog-windows.json
```

That recipe combines corpus sync, smoke replay, perf, interop, rollout-validation, active fuzz, comparison, matrix, release-workflow, deployment-signoff, release-prep, release-candidate-signoff, release-burn-in, release-soak, release-gate, release-readiness-burndown, release-stability-signoff, release-candidate-consolidation, release-candidate-hardening, and release-candidate-evidence-freeze summaries for release-candidate evidence-freeze review, with the final freeze step consuming exact Linux/macOS/Windows compatible-host interop-catalog evidence plus the maintained interop-catalog provenance and failed-profile-count contracts.

Release-candidate signoff-closure recipe:

```bash
cargo run -p ns-testkit --example sync_udp_fuzz_corpus
NORTHSTAR_ENABLE_UDP_ACTIVE_FUZZ=1 \
NORTHSTAR_UDP_ROLLOUT_COMPARE_PROFILE=staged_rollout \
./scripts/udp-rollout-readiness.sh
./scripts/udp-rollout-matrix.sh \
  --input target/northstar/udp-rollout-comparison-summary.json
./scripts/udp-release-workflow.sh \
  --input target/northstar/udp-rollout-matrix-summary.json
./scripts/udp-deployment-signoff.sh \
  --release-workflow target/northstar/udp-release-workflow-summary.json \
  --validation target/northstar/udp-rollout-validation-summary.json
./scripts/udp-release-prep.sh \
  --deployment-signoff target/northstar/udp-deployment-signoff-summary.json \
  --validation target/northstar/udp-rollout-validation-summary-linux.json \
  --validation target/northstar/udp-rollout-validation-summary-macos.json \
  --validation target/northstar/udp-rollout-validation-summary-windows.json
./scripts/udp-release-candidate-signoff.sh \
  --release-prep target/northstar/udp-release-prep-summary.json \
  --windows-readiness target/northstar/udp-rollout-comparison-summary-windows.json \
  --windows-interop target/northstar/udp-interop-lab-summary-windows.json \
  --macos-interop target/northstar/udp-interop-lab-summary-macos.json
./scripts/udp-release-burn-in.sh
./scripts/udp-release-soak.sh
./scripts/udp-release-gate.sh \
  --release-soak target/northstar/udp-release-soak-summary.json \
  --linux-interop-catalog target/northstar/udp-interop-profile-catalog-linux.json \
  --macos-interop-catalog target/northstar/udp-interop-profile-catalog-macos.json \
  --windows-interop-catalog target/northstar/udp-interop-profile-catalog-windows.json
./scripts/udp-release-readiness-burndown.sh \
  --release-gate target/northstar/udp-release-gate-summary.json \
  --linux-readiness target/northstar/udp-rollout-comparison-summary-linux.json \
  --macos-readiness target/northstar/udp-rollout-comparison-summary-macos.json \
  --windows-readiness target/northstar/udp-rollout-comparison-summary-windows.json
./scripts/udp-release-stability-signoff.sh \
  --release-readiness-burndown target/northstar/udp-release-readiness-burndown-summary.json \
  --linux-interop target/northstar/udp-interop-lab-summary-linux.json \
  --macos-interop target/northstar/udp-interop-lab-summary-macos.json \
  --windows-interop target/northstar/udp-interop-lab-summary-windows.json
./scripts/udp-release-candidate-consolidation.sh \
  --release-stability-signoff target/northstar/udp-release-stability-signoff-summary.json \
  --linux-interop-catalog target/northstar/udp-interop-profile-catalog-linux.json \
  --macos-interop-catalog target/northstar/udp-interop-profile-catalog-macos.json \
  --windows-interop-catalog target/northstar/udp-interop-profile-catalog-windows.json
./scripts/udp-release-candidate-hardening.sh \
  --release-candidate-consolidation target/northstar/udp-release-candidate-consolidation-summary.json \
  --linux-validation target/northstar/udp-rollout-validation-summary-linux.json \
  --macos-validation target/northstar/udp-rollout-validation-summary-macos.json \
  --windows-validation target/northstar/udp-rollout-validation-summary-windows.json
./scripts/udp-release-candidate-evidence-freeze.sh \
  --release-candidate-hardening target/northstar/udp-release-candidate-hardening-summary.json \
  --linux-interop-catalog target/northstar/udp-interop-profile-catalog-linux.json \
  --macos-interop-catalog target/northstar/udp-interop-profile-catalog-macos.json \
  --windows-interop-catalog target/northstar/udp-interop-profile-catalog-windows.json
./scripts/udp-release-candidate-signoff-closure.sh \
  --release-candidate-evidence-freeze target/northstar/udp-release-candidate-evidence-freeze-summary.json \
  --linux-readiness target/northstar/udp-rollout-comparison-summary-linux.json \
  --macos-readiness target/northstar/udp-rollout-comparison-summary-macos.json \
  --windows-readiness target/northstar/udp-rollout-comparison-summary-windows.json
```

That recipe combines corpus sync, smoke replay, perf, interop, rollout-validation, active fuzz, comparison, matrix, release-workflow, deployment-signoff, release-prep, release-candidate-signoff, release-burn-in, release-soak, release-gate, release-readiness-burndown, release-stability-signoff, release-candidate-consolidation, release-candidate-hardening, release-candidate-evidence-freeze, and release-candidate-signoff-closure summaries for release-candidate signoff-closure review, with the final closure step consuming exact Linux/macOS/Windows rollout-readiness evidence plus the maintained interop-catalog provenance, failed-profile-count, host-label-set, and policy-disabled-fallback round-trip contracts.

Release-candidate stabilization recipe:

```bash
cargo run -p ns-testkit --example sync_udp_fuzz_corpus
NORTHSTAR_ENABLE_UDP_ACTIVE_FUZZ=1 \
NORTHSTAR_UDP_ROLLOUT_COMPARE_PROFILE=staged_rollout \
./scripts/udp-rollout-readiness.sh
./scripts/udp-rollout-matrix.sh \
  --input target/northstar/udp-rollout-comparison-summary.json
./scripts/udp-release-workflow.sh \
  --input target/northstar/udp-rollout-matrix-summary.json
./scripts/udp-deployment-signoff.sh \
  --release-workflow target/northstar/udp-release-workflow-summary.json \
  --validation target/northstar/udp-rollout-validation-summary.json
./scripts/udp-release-prep.sh \
  --deployment-signoff target/northstar/udp-deployment-signoff-summary.json \
  --validation target/northstar/udp-rollout-validation-summary-linux.json \
  --validation target/northstar/udp-rollout-validation-summary-macos.json \
  --validation target/northstar/udp-rollout-validation-summary-windows.json
./scripts/udp-release-candidate-signoff.sh \
  --release-prep target/northstar/udp-release-prep-summary.json \
  --windows-readiness target/northstar/udp-rollout-comparison-summary-windows.json \
  --windows-interop target/northstar/udp-interop-lab-summary-windows.json \
  --macos-interop target/northstar/udp-interop-lab-summary-macos.json
./scripts/udp-release-burn-in.sh
./scripts/udp-release-soak.sh
./scripts/udp-release-gate.sh \
  --release-soak target/northstar/udp-release-soak-summary.json \
  --linux-interop-catalog target/northstar/udp-interop-profile-catalog-linux.json \
  --macos-interop-catalog target/northstar/udp-interop-profile-catalog-macos.json \
  --windows-interop-catalog target/northstar/udp-interop-profile-catalog-windows.json
./scripts/udp-release-readiness-burndown.sh \
  --release-gate target/northstar/udp-release-gate-summary.json \
  --linux-readiness target/northstar/udp-rollout-comparison-summary-linux.json \
  --macos-readiness target/northstar/udp-rollout-comparison-summary-macos.json \
  --windows-readiness target/northstar/udp-rollout-comparison-summary-windows.json
./scripts/udp-release-stability-signoff.sh \
  --release-readiness-burndown target/northstar/udp-release-readiness-burndown-summary.json \
  --linux-interop target/northstar/udp-interop-lab-summary-linux.json \
  --macos-interop target/northstar/udp-interop-lab-summary-macos.json \
  --windows-interop target/northstar/udp-interop-lab-summary-windows.json
./scripts/udp-release-candidate-consolidation.sh \
  --release-stability-signoff target/northstar/udp-release-stability-signoff-summary.json \
  --linux-interop-catalog target/northstar/udp-interop-profile-catalog-linux.json \
  --macos-interop-catalog target/northstar/udp-interop-profile-catalog-macos.json \
  --windows-interop-catalog target/northstar/udp-interop-profile-catalog-windows.json
./scripts/udp-release-candidate-hardening.sh \
  --release-candidate-consolidation target/northstar/udp-release-candidate-consolidation-summary.json \
  --linux-validation target/northstar/udp-rollout-validation-summary-linux.json \
  --macos-validation target/northstar/udp-rollout-validation-summary-macos.json \
  --windows-validation target/northstar/udp-rollout-validation-summary-windows.json
./scripts/udp-release-candidate-evidence-freeze.sh \
  --release-candidate-hardening target/northstar/udp-release-candidate-hardening-summary.json \
  --linux-interop-catalog target/northstar/udp-interop-profile-catalog-linux.json \
  --macos-interop-catalog target/northstar/udp-interop-profile-catalog-macos.json \
  --windows-interop-catalog target/northstar/udp-interop-profile-catalog-windows.json
./scripts/udp-release-candidate-signoff-closure.sh \
  --release-candidate-evidence-freeze target/northstar/udp-release-candidate-evidence-freeze-summary.json \
  --linux-readiness target/northstar/udp-rollout-comparison-summary-linux.json \
  --macos-readiness target/northstar/udp-rollout-comparison-summary-macos.json \
  --windows-readiness target/northstar/udp-rollout-comparison-summary-windows.json
./scripts/udp-release-candidate-stabilization.sh \
  --release-candidate-signoff-closure target/northstar/udp-release-candidate-signoff-closure-summary.json \
  --linux-interop-catalog target/northstar/udp-interop-profile-catalog-linux.json \
  --macos-interop-catalog target/northstar/udp-interop-profile-catalog-macos.json \
  --windows-interop-catalog target/northstar/udp-interop-profile-catalog-windows.json
```

That recipe combines corpus sync, smoke replay, perf, interop, rollout-validation, active fuzz, comparison, matrix, release-workflow, deployment-signoff, release-prep, release-candidate-signoff, release-burn-in, release-soak, release-gate, release-readiness-burndown, release-stability-signoff, release-candidate-consolidation, release-candidate-hardening, release-candidate-evidence-freeze, release-candidate-signoff-closure, and release-candidate-stabilization summaries for release-candidate stabilization review, with the final stabilization step consuming exact Linux/macOS/Windows compatible-host interop-catalog evidence plus the maintained interop-catalog provenance, failed-profile-count, host-label-set, readiness-set, and policy-disabled-fallback round-trip contracts.

Release-candidate readiness recipe:

```bash
cargo run -p ns-testkit --example sync_udp_fuzz_corpus
NORTHSTAR_ENABLE_UDP_ACTIVE_FUZZ=1 \
NORTHSTAR_UDP_ROLLOUT_COMPARE_PROFILE=staged_rollout \
./scripts/udp-rollout-readiness.sh
./scripts/udp-rollout-matrix.sh \
  --input target/northstar/udp-rollout-comparison-summary.json
./scripts/udp-release-workflow.sh \
  --input target/northstar/udp-rollout-matrix-summary.json
./scripts/udp-deployment-signoff.sh \
  --release-workflow target/northstar/udp-release-workflow-summary.json \
  --validation target/northstar/udp-rollout-validation-summary.json
./scripts/udp-release-prep.sh \
  --deployment-signoff target/northstar/udp-deployment-signoff-summary.json \
  --validation target/northstar/udp-rollout-validation-summary-linux.json \
  --validation target/northstar/udp-rollout-validation-summary-macos.json \
  --validation target/northstar/udp-rollout-validation-summary-windows.json
./scripts/udp-release-candidate-signoff.sh \
  --release-prep target/northstar/udp-release-prep-summary.json \
  --windows-readiness target/northstar/udp-rollout-comparison-summary-windows.json \
  --windows-interop target/northstar/udp-interop-lab-summary-windows.json \
  --macos-interop target/northstar/udp-interop-lab-summary-macos.json
./scripts/udp-release-burn-in.sh
./scripts/udp-release-soak.sh
./scripts/udp-release-gate.sh \
  --release-soak target/northstar/udp-release-soak-summary.json \
  --linux-interop-catalog target/northstar/udp-interop-profile-catalog-linux.json \
  --macos-interop-catalog target/northstar/udp-interop-profile-catalog-macos.json \
  --windows-interop-catalog target/northstar/udp-interop-profile-catalog-windows.json
./scripts/udp-release-readiness-burndown.sh \
  --release-gate target/northstar/udp-release-gate-summary.json \
  --linux-readiness target/northstar/udp-rollout-comparison-summary-linux.json \
  --macos-readiness target/northstar/udp-rollout-comparison-summary-macos.json \
  --windows-readiness target/northstar/udp-rollout-comparison-summary-windows.json
./scripts/udp-release-stability-signoff.sh \
  --release-readiness-burndown target/northstar/udp-release-readiness-burndown-summary.json \
  --linux-interop target/northstar/udp-interop-lab-summary-linux.json \
  --macos-interop target/northstar/udp-interop-lab-summary-macos.json \
  --windows-interop target/northstar/udp-interop-lab-summary-windows.json
./scripts/udp-release-candidate-consolidation.sh \
  --release-stability-signoff target/northstar/udp-release-stability-signoff-summary.json \
  --linux-interop-catalog target/northstar/udp-interop-profile-catalog-linux.json \
  --macos-interop-catalog target/northstar/udp-interop-profile-catalog-macos.json \
  --windows-interop-catalog target/northstar/udp-interop-profile-catalog-windows.json
./scripts/udp-release-candidate-hardening.sh \
  --release-candidate-consolidation target/northstar/udp-release-candidate-consolidation-summary.json \
  --linux-validation target/northstar/udp-rollout-validation-summary-linux.json \
  --macos-validation target/northstar/udp-rollout-validation-summary-macos.json \
  --windows-validation target/northstar/udp-rollout-validation-summary-windows.json
./scripts/udp-release-candidate-evidence-freeze.sh \
  --release-candidate-hardening target/northstar/udp-release-candidate-hardening-summary.json \
  --linux-interop-catalog target/northstar/udp-interop-profile-catalog-linux.json \
  --macos-interop-catalog target/northstar/udp-interop-profile-catalog-macos.json \
  --windows-interop-catalog target/northstar/udp-interop-profile-catalog-windows.json
./scripts/udp-release-candidate-signoff-closure.sh \
  --release-candidate-evidence-freeze target/northstar/udp-release-candidate-evidence-freeze-summary.json \
  --linux-readiness target/northstar/udp-rollout-comparison-summary-linux.json \
  --macos-readiness target/northstar/udp-rollout-comparison-summary-macos.json \
  --windows-readiness target/northstar/udp-rollout-comparison-summary-windows.json
./scripts/udp-release-candidate-stabilization.sh \
  --release-candidate-signoff-closure target/northstar/udp-release-candidate-signoff-closure-summary.json \
  --linux-interop-catalog target/northstar/udp-interop-profile-catalog-linux.json \
  --macos-interop-catalog target/northstar/udp-interop-profile-catalog-macos.json \
  --windows-interop-catalog target/northstar/udp-interop-profile-catalog-windows.json
./scripts/udp-release-candidate-readiness.sh \
  --release-candidate-stabilization target/northstar/udp-release-candidate-stabilization-summary.json \
  --linux-readiness target/northstar/udp-rollout-comparison-summary-linux.json \
  --macos-readiness target/northstar/udp-rollout-comparison-summary-macos.json \
  --windows-readiness target/northstar/udp-rollout-comparison-summary-windows.json
```

That recipe combines corpus sync, smoke replay, perf, interop, rollout-validation, active fuzz, comparison, matrix, release-workflow, deployment-signoff, release-prep, release-candidate-signoff, release-burn-in, release-soak, release-gate, release-readiness-burndown, release-stability-signoff, release-candidate-consolidation, release-candidate-hardening, release-candidate-evidence-freeze, release-candidate-signoff-closure, release-candidate-stabilization, release-candidate-readiness, release-candidate-acceptance, and release-candidate-certification summaries for release-candidate certification review, with the final certification step consuming exact Linux/macOS/Windows compatible-host interop-catalog evidence plus the maintained interop-catalog provenance, failed-profile-count, host-label-set, blocked-fallback surface, policy-disabled-fallback round-trip, and transport-fallback-integrity contracts.

## Corpus layout

- `corpus/control_frame_decoder/`
- `corpus/udp_fallback_frame_decoder/`
- `corpus/udp_datagram_decoder/`
- `fuzz_regressions/control_frame_decoder/`
- `fuzz_regressions/udp_fallback_frame_decoder/`
- `fuzz_regressions/udp_datagram_decoder/`

Store minimized repro inputs under `fuzz_regressions/` once a crash or parser bug is fixed.

## Notes

- This scaffold intentionally lives outside the main Cargo workspace.
- `manifest_json_parser` stays available, but milestone 14 focuses the actively maintained local smoke path on UDP control, datagram, and fallback-frame decoding.
- milestone 15 adds an opt-in wrapper-gate path so the same UDP smoke replay can be used in local or CI-style verification without making it the default workspace check.
- milestone 18 adds the machine-readable UDP interop harness plus the short active-fuzz wrappers and workflow input without turning either path into a default required gate.
- milestone 19 adds reviewed-corpus sync before active fuzz, a compatible-host Linux interop lane with uploaded JSON summaries, and a machine-readable UDP perf summary surface for staged rollout review.
- milestone 20 adds reviewed hello, ping, and UDP-control seeds for `control_frame_decoder`, smoke replay before active fuzz, a machine-readable active-fuzz summary surface, and a broader compatible-host rollout-readiness workflow lane.
- milestone 21 adds reviewed MTU-boundary and truncated UDP datagram seeds for `udp_datagram_decoder`, a reusable `udp_rollout_validation_lab` summary surface, and a compatible-host Windows rollout-validation workflow lane with an uploaded JSON summary artifact.
- milestone 22 adds reviewed truncated UDP close-path seeds, rollout-readiness wrappers that combine corpus sync plus smoke or perf or interop or rollout-validation summaries, and a compatible-host macOS rollout-readiness workflow lane with the same summary family as Linux.
- milestone 23 adds reviewed truncated `UDP_OK` and `UDP_STREAM_ACCEPT` seeds, a maintained `udp_rollout_compare` summary surface, and a compatible-host Windows rollout-readiness workflow lane that uploads the same comparison-summary family as the Linux and macOS readiness lanes.
- milestone 24 adds reviewed truncated `UDP_FLOW_OPEN`, non-canonical `UDP_DATAGRAM`, and invalid `UDP_STREAM_CLOSE` seeds, a stricter `udp_rollout_compare --profile staged_rollout` surface that requires active-fuzz evidence, and a compatible-host Linux staged-rollout workflow lane with uploaded active-fuzz and comparison summaries.
- milestone 25 adds reviewed non-canonical `UDP_FLOW_CLOSE`, `UDP_STREAM_OPEN`, and `UDP_STREAM_ACCEPT` seeds, a stable reusable operator-verdict schema for `udp_rollout_compare`, and a workflow-backed Linux rollout-matrix lane that consumes compatible-host comparison summaries.
- milestone 26 adds reviewed non-canonical `UDP_DATAGRAM` flags, non-canonical `UDP_STREAM_CLOSE` codes, and non-canonical `UDP_OK` payload-limit seeds, plus a compatible-host macOS staged-rollout workflow lane.
- milestone 27 adds reviewed non-canonical `UDP_FLOW_OK` flow ids and non-canonical UDP fallback-packet lengths, plus a workflow-backed Linux staged-rollout matrix lane that consumes staged Linux and macOS comparison artifacts under shared operator-verdict schema version `6`.
- milestone 28 adds reviewed non-canonical `UDP_FLOW_CLOSE` and `UDP_STREAM_CLOSE` flow-id seeds, a workflow-backed Linux release-workflow lane, and explicit degradation-surface or surface-accounting facts across rollout-validation, comparison, matrix, and release-workflow summaries.
- milestone 29 adds reviewed non-canonical `UDP_FLOW_OPEN` flow-id and flags seeds (`WC-UDP-OPEN-NONCANONFLOW-034` and `WC-UDP-OPEN-NONCANONFLAGS-035`), workflow-backed Linux deployment-signoff coverage, shared operator-verdict schema version `8`, and a deployment-candidate release recipe that extends the maintained stack through `scripts/udp-deployment-signoff.*`.
- milestone 30 adds reviewed non-canonical `UDP_FLOW_OPEN` and `UDP_OK` timeout seeds (`WC-UDP-OPEN-NONCANONTIMEOUT-036` and `WC-UDP-OK-NONCANONTIMEOUT-037`), workflow-backed Linux release-prep coverage, shared operator-verdict schema version `9`, and a release-prep operator recipe that extends the maintained stack through `scripts/udp-release-prep.*`.
- milestone 31 adds reviewed malformed `UDP_FLOW_OPEN` IPv4-length and target-type seeds (`WC-UDP-OPEN-IPV4LEN-038` and `WC-UDP-OPEN-BADTARGETTYPE-039`), workflow-backed Linux release-candidate-signoff coverage, shared operator-verdict schema version `10`, and a release-candidate operator recipe that extends the maintained stack through `scripts/udp-release-candidate-signoff.*`.
- milestone 32 adds reviewed malformed `UDP_FLOW_OPEN` IPv6-length and empty-domain seeds plus a non-canonical `UDP_OK` mode seed (`WC-UDP-OPEN-IPV6LEN-040`, `WC-UDP-OPEN-EMPTYDOMAIN-041`, and `WC-UDP-OK-NONCANONMODE-042`), a compatible-host macOS interop-lab workflow lane, shared operator-verdict schema version `11`, rollout-validation reordering and transport-fallback-integrity surfaces, and a release-gating recipe that extends the maintained stack through the macOS-backed release-candidate-signoff path.
- milestone 33 adds reviewed malformed `UDP_FLOW_OPEN` target-type and port seeds plus malformed flow-close and stream-close message-length seeds (`WC-UDP-OPEN-NONCANONTARGETTYPE-043`, `WC-UDP-OPEN-NONCANONPORT-044`, `WC-UDP-FLOW-CLOSE-NONCANONMSGLEN-045`, and `WC-UDP-STREAM-CLOSE-NONCANONMSGLEN-046`), a compatible-host Windows interop-lab workflow lane, shared operator-verdict schema version `12`, exact supported interop-profile accounting across release-facing consumers, and a release-readiness recipe that extends the maintained stack through Windows plus macOS interop-backed release-candidate signoff.
- milestone 37 adds reviewed malformed UDP metadata-length seeds for flow-open, flow-ok, stream-open, and stream-accept (`WC-UDP-OPEN-NONCANONMETALEN-061`, `WC-UDP-OK-NONCANONMETALEN-062`, `WC-UDP-STREAM-OPEN-NONCANONMETALEN-063`, `WC-UDP-STREAM-ACCEPT-NONCANONMETALEN-064`, `WC-UDP-OPEN-BADMETALEN-065`, `WC-UDP-OK-BADMETALEN-066`, `WC-UDP-STREAM-OPEN-BADMETALEN-067`, and `WC-UDP-STREAM-ACCEPT-BADMETALEN-068`), a workflow-backed Linux release-readiness-burndown lane, shared operator-verdict schema version `16`, host-bound compatible-host interop-catalog envelope semantics, and a release-readiness burn-down recipe that extends the maintained stack through `scripts/udp-release-readiness-burndown.*`.
- milestone 38 adds reviewed malformed UDP metadata-type seeds for flow-open, flow-ok, stream-open, and stream-accept (`WC-UDP-OPEN-NONCANONMETATYPE-069`, `WC-UDP-OK-NONCANONMETATYPE-070`, `WC-UDP-STREAM-OPEN-NONCANONMETATYPE-071`, and `WC-UDP-STREAM-ACCEPT-NONCANONMETATYPE-072`), a workflow-backed Linux release-stability-signoff lane, shared operator-verdict schema version `17`, the maintained `oversized-payload-guard-recovery` compatible-host profile, and a release-stability recipe that extends the maintained stack through `scripts/udp-release-stability-signoff.*`.
- milestone 39 adds reviewed malformed outer-frame-length seeds for flow-open, flow-ok, stream-open, and stream-accept (`WC-UDP-OPEN-NONCANONFRAMELEN-073`, `WC-UDP-OK-NONCANONFRAMELEN-074`, `WC-UDP-STREAM-OPEN-NONCANONFRAMELEN-075`, and `WC-UDP-STREAM-ACCEPT-NONCANONFRAMELEN-076`), a workflow-backed Linux release-candidate-consolidation lane, shared operator-verdict schema version `18`, `mtu_ceiling_delivery_stable` rollout-validation evidence, the maintained `fallback-flow-guard-rejection` compatible-host profile, and a release-candidate-consolidation recipe that extends the maintained stack through `scripts/udp-release-candidate-consolidation.*`.
- milestone 40 adds reviewed malformed close-frame outer-length seeds (`WC-UDP-FLOW-CLOSE-NONCANONFRAMELEN-077` and `WC-UDP-STREAM-CLOSE-NONCANONFRAMELEN-078`), a workflow-backed Linux release-candidate-hardening lane, shared operator-verdict schema version `19`, exact compatible-host interop-catalog `source_lane` semantics for release-gate and release-candidate-consolidation consumers, `fallback_flow_guard_rejection_stable` rollout-validation evidence, and a release-candidate-hardening recipe that extends the maintained stack through `scripts/udp-release-candidate-hardening.*`.
- milestone 41 adds reviewed malformed fallback-packet outer-length seeds (`WC-UDP-STREAM-PACKET-NONCANONFRAMELEN-079` and `WC-UDP-STREAM-PACKET-BADFRAMELEN-080`) only to the maintained fallback-frame corpus and regression buckets, a workflow-backed Linux release-candidate-evidence-freeze lane, shared operator-verdict schema version `20`, exact compatible-host interop-catalog `source_lane` plus failed-profile-count semantics, `udp_blocked_fallback_surface_passed` rollout-validation evidence, and a release-candidate-evidence-freeze recipe that extends the maintained stack through `scripts/udp-release-candidate-evidence-freeze.*`.
- milestone 42 adds reviewed malformed fallback stream-open and stream-accept outer-length seeds (`WC-UDP-STREAM-OPEN-BADFRAMELEN-081` and `WC-UDP-STREAM-ACCEPT-BADFRAMELEN-082`) only to the maintained fallback-frame corpus and regression buckets, a workflow-backed Linux release-candidate-signoff-closure lane, shared operator-verdict schema version `20`, exact compatible-host interop-catalog `source_lane` plus failed-profile-count and host-label-set semantics, `policy_disabled_fallback_round_trip_stable` rollout-validation evidence, and a release-candidate-signoff-closure recipe that extends the maintained stack through `scripts/udp-release-candidate-signoff-closure.*`.
- milestone 43 adds reviewed malformed fallback and control close-frame outer-length seeds (`WC-UDP-STREAM-CLOSE-BADFRAMELEN-083` and `WC-UDP-FLOW-CLOSE-BADFRAMELEN-084`) only to the maintained fallback-frame and control-frame corpus/regression buckets, a workflow-backed Linux release-candidate-stabilization lane, shared operator-verdict schema version `20`, exact compatible-host interop-catalog `source_lane` plus failed-profile-count and host-label-set and readiness-set semantics, `datagram_only_unavailable_rejection_stable` rollout-validation evidence, and a release-candidate-stabilization recipe that extends the maintained stack through `scripts/udp-release-candidate-stabilization.*`.
- milestone 44 adds reviewed malformed control-frame outer-length seed `WC-UDP-OK-BADFRAMELEN-085` only to the maintained control-frame corpus and regression buckets, a workflow-backed Linux release-candidate-readiness lane, shared operator-verdict schema version `20`, exact compatible-host interop-catalog `source_lane` plus failed-profile-count and host-label-set and readiness-set semantics, rollout-validation summary version `20` plus rollout-comparison projection of `udp_blocked_fallback_surface_passed`, and a release-candidate-readiness recipe that extends the maintained stack through `scripts/udp-release-candidate-readiness.*`.
- milestone 45 adds reviewed malformed control-frame outer-length seed `WC-UDP-OPEN-BADFRAMELEN-086` only to the maintained control-frame corpus and regression buckets, a workflow-backed Linux release-candidate-acceptance lane, shared operator-verdict schema version `20`, exact compatible-host interop-catalog `source_lane` plus failed-profile-count and host-label-set and readiness-set semantics, carried blocked-fallback and transport-fallback-integrity acceptance handling, and a release-candidate-acceptance recipe that extends the maintained stack through `scripts/udp-release-candidate-acceptance.*`.
- milestone 46 adds reviewed malformed datagram-unavailable close-frame outer-length seed `WC-UDP-FLOW-CLOSE-DGRAMUNAVAIL-BADFRAMELEN-087` only to the maintained control-frame corpus and regression buckets, a workflow-backed Linux release-candidate-certification lane, shared operator-verdict schema version `20`, exact compatible-host interop-catalog `source_lane` plus failed-profile-count and host-label-set semantics, carried blocked-fallback and transport-fallback-integrity certification handling, and a release-candidate-certification recipe that extends the maintained stack through `scripts/udp-release-candidate-certification.*`.
- `token_claims_boundary` remains a planned follow-up target.
