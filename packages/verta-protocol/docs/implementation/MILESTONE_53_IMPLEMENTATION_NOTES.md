# Milestone 53 Implementation Notes

Milestone 53 closes the biggest `Phase K` gap by turning Verta's release-facing verification posture into actual repository-level automation instead of a long-documented optional workflow that never landed in the root repo.

## What Changed

- Added real root-level GitHub Actions workflows:
  - `.github/workflows/verta-udp-bounded-verification.yml`
  - `.github/workflows/verta-udp-scheduled-verification.yml`
  - `.github/workflows/verta-udp-release-evidence.yml`
- Activated repository rulesets in `Beep206/CyberVPN` so the bounded gate is enforced on `main` and the full release-evidence gate is enforced on `release/**` and `rc/**`.
- Added `scripts/udp-release-evidence-chain.ps1` and `scripts/udp-release-evidence-chain.sh` so release-facing consumers can be driven in one maintained order instead of copy-pasted CI steps.
- Added `docs/development/SUSTAINED_VERIFICATION_GATES.md` as the active `Phase K` gate map, required-check list, artifact-retention policy, and baseline-comparison rule set.
- Updated active verification docs to point at the real sustained workflows instead of the planned `.github/workflows/udp-optional-gates.yml`.

## Why This Matters

Before this milestone, the repository had strong local harnesses and release-shaped consumers, but the sustained CI discipline was still mostly documentary.
`Phase K` required a durable split between bounded protected-branch gates, scheduled longer-running verification, and release-promotion evidence.
This milestone makes that split real.

## Sustained Gate Shape

- bounded protected-branch path:
  - workspace baseline
  - Linux rollout-readiness with host-labeled smoke, perf, interop, rollout-validation, rollout-comparison, and interop-catalog artifacts
- scheduled path:
  - active-fuzz-backed Linux staged-rollout recipe
  - packet-capture-backed Linux net-chaos campaign
- release-evidence path:
  - Linux, macOS, and Windows host-labeled readiness evidence
  - Linux and macOS staged-rollout evidence
  - one fail-closed release chain ending at `udp-release-candidate-certification`

## Local Verification

- `bash packages/verta-protocol/scripts/udp-rollout-readiness.sh`
- `bash packages/verta-protocol/scripts/udp-release-evidence-chain.sh` fail-closed smoke when host artifacts are missing
- YAML parse validation for the three new workflows

## Remaining Boundaries

- This milestone does not invent new datagram semantics or new release consumers.
- Historical milestone notes still reference the planned optional workflow because they record what each milestone intended at the time; the active source of truth is now the sustained gate map and the real root-level workflows.
