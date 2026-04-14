# Production-Ready Checklist

Northstar `v0.1` is only production-ready when the maintained closure inputs below are all true at the same time.

## Required Closure Inputs

- `Phase I` is honestly complete through `target/northstar/remnawave-supported-upstream-phase-i-signoff-summary.json`.
- `Phase J` is honestly complete through `target/northstar/udp-phase-j-signoff-summary.json`.
- `Phase K` sustained verification remains active through:
  - `.github/workflows/northstar-udp-bounded-verification.yml`
  - `.github/workflows/northstar-udp-scheduled-verification.yml`
  - `.github/workflows/northstar-udp-release-evidence.yml`
  - `docs/development/SUSTAINED_VERIFICATION_GATES.md`
- `Phase L` is honestly complete through `target/northstar/phase-l-operator-readiness-signoff-summary.json`.
- `Phase M` is honestly complete through `target/northstar/phase-m-soak-canary-signoff-summary.json`.
- The supported environment matrix is explicit and reviewable.
- Known limitations are explicit and non-blocking.
- Release attribution is tied to one git branch plus one commit SHA and a clean worktree.
- Local secret-bearing `.env` files remain ignored rather than release-tracked.

## Stop Rules

Do not call the project production-ready if any of the following is true:

- any accepted phase summary is missing or no longer `ready`
- the git worktree is dirty
- the supported environment matrix or known limitations docs are missing or drifted
- a blocking limitation is still present
- sustained verification workflow definitions are missing

The final machine-readable source of truth is `target/northstar/phase-n-production-ready-signoff-summary.json`.
