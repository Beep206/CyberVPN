# Milestone 55 Implementation Notes

Milestone 55 closes `Phase M` by turning soak, canary, and regression burn-down from a plan into one maintained local supported-staging loop plus a fail-closed signoff summary.

## What Changed

- Added the bounded `Phase M` contract under `docs/runbooks/PHASE_M_SOAK_AND_CANARY.md` plus the machine-readable `docs/runbooks/phase-m-canary-plan.json`.
- Added the maintained regression bug bar under `docs/development/REGRESSION_BUG_BAR.md` plus the machine-readable `docs/development/phase-m-regression-ledger.json`.
- Added `phase_m_soak_canary_signoff` plus `scripts/phase-m-soak-canary.*` so `Phase M` closure is one fail-closed summary instead of scattered stage notes.
- Added helper-backed local supported-upstream env derivation and local user state helpers so the maintained Phase I and operator drills can run against the local Remnawave Docker deployment without a manually prepared shell session.
- Kept the local supported deployment path explicit through the maintained localhost proxy route and did not widen the bridge or transport contracts to make the soak pass.

## Why This Matters

`Phase M` is where Verta stops inferring stability from short targeted tests and proves it under repeated live promotion checkpoints.
That requires more than one green unit test:

- the soak environment has to be agreed and repeatable
- the canary stage inventory has to be exact
- rollback has to be proven during the same maintained loop
- regression discipline has to fail closed when `P0` or `P1` issues reopen

Milestone 55 makes all four true on the maintained local supported deployment.

## Signoff Shape

The maintained `Phase M` signoff now requires:

- the exact stage set `canary_5`, `canary_25`, and `canary_100`
- a valid canary plan and regression ledger
- a passed `Phase I` signoff summary
- a passed WAN staging summary
- passed lifecycle, rollback, and stage-local `Phase L` summaries for each canary stage
- minimum elapsed soak duration at or above the agreed floor
- zero open `P0` and `P1` regressions

## Local Verification

- `cargo test -p ns-testkit --example phase_m_soak_canary_signoff -- --nocapture`
- `cargo run -p ns-testkit --example phase_m_soak_canary_signoff -- --summary-path target/verta/phase-m-soak-canary-signoff-summary.json --stage-root target/verta/phase-m-soak --canary-plan docs/runbooks/phase-m-canary-plan.json --regression-ledger docs/development/phase-m-regression-ledger.json --phase-i target/verta/remnawave-supported-upstream-phase-i-signoff-summary.json --wan-staging target/verta/udp-wan-staging-interop-summary.json`
- `bash scripts/phase-m-soak-canary.sh`

The final summary lives at `target/verta/phase-m-soak-canary-signoff-summary.json` and currently reports `phase_m_state = "honestly_complete"` with `observed_duration_seconds = 52`.
