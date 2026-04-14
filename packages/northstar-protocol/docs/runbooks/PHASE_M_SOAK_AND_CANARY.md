# Phase M Soak And Canary Discipline

`Phase M` is not a new transport track.
It is the point where we prove that the already accepted protocol/runtime surfaces stay stable over repeated live promotion checkpoints on the maintained local supported deployment.

## Agreed Environment

- deployment label: `remnawave-local-docker`
- environment kind: `local_supported_staging`
- supported-upstream access path: `scripts/with-local-remnawave-supported-upstream-env.*` plus the maintained local `caddy` proxy
- rollback evidence path: `scripts/operator-rollout-rollback-drill.*`
- operator readiness cross-check: `phase_l_operator_readiness_signoff`

## Agreed Soak Duration

- minimum stage count: `3`
- stage ids: `canary_5`, `canary_25`, `canary_100`
- minimum elapsed duration across the full loop: `20` seconds
- stage pause: `5` seconds between promotion checkpoints

This is intentionally bounded.
The stop bar is not “wait forever”.
The stop bar is repeated live success across the exact canary stages with rollback proof and no open `P0`/`P1` regressions.

## Stage Contract

Each canary stage must leave behind three artifacts under `target/northstar/phase-m-soak/<stage-id>/`:

- `lifecycle-summary.json`
- `rollback-summary.json`
- `phase-l-summary.json`

Each stage is only considered promotable when:

- the supported-upstream lifecycle lane reports `verdict = ready`
- the rollback drill reports `verdict = ready`
- the stage-local Phase L signoff reports `phase_l_state = honestly_complete`

## Rollback Triggers

Rollback is mandatory for any of the following:

- lifecycle verification leaves `ready`
- rollback drill leaves `ready`
- Phase L stage signoff leaves `honestly_complete`
- a `P0` or `P1` regression opens
- the WAN baseline or Phase I baseline is no longer `ready`

## Comparison Baseline

The Phase M loop compares against the already accepted ready baselines:

- `target/northstar/remnawave-supported-upstream-phase-i-signoff-summary.json`
- `target/northstar/udp-wan-staging-interop-summary.json`
- `target/northstar/udp-net-chaos-campaign-summary.json`

If any of those baselines regress to non-ready, Phase M is blocked even if the current canary stages pass.
