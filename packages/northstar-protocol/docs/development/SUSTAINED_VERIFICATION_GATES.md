# Sustained Verification Gates

This document is the active `Phase K` gate map for Northstar.
It replaces the long-planned but never-landed `.github/workflows/udp-optional-gates.yml` with real root-level workflows and explicit branch or release expectations.

The repository-level enforcement surface is now active in `Beep206/CyberVPN` through these GitHub rulesets:

- `northstar-main-bounded-verification`
- `northstar-release-evidence-verification`

## Gate Map

| Scope | Workflow | Required Jobs | Retention | Purpose |
| --- | --- | --- | --- | --- |
| `pull_request` or `push` on `main`, `release/**`, `rc/**` | `.github/workflows/northstar-udp-bounded-verification.yml` | `workspace-baseline`, `udp-rollout-readiness-linux` | 14 days | Keep workspace correctness plus bounded UDP smoke, perf, interop, and rollout-readiness evidence sustained on protected code paths. |
| nightly schedule or manual operator run | `.github/workflows/northstar-udp-scheduled-verification.yml` | `udp-staged-rollout-linux`, `udp-net-chaos-linux` | 30 days | Keep longer-running active-fuzz-backed staged rollout and packet-capture-backed net-chaos evidence attributable over time. |
| `pull_request` or `push` on `release/**`, `rc/**`, or manual release promotion review | `.github/workflows/northstar-udp-release-evidence.yml` | `linux-readiness`, `linux-staged-readiness`, `macos-readiness`, `macos-staged-readiness`, `windows-readiness`, `release-evidence-chain` | 30 days | Produce the host-labeled release-facing evidence chain and fail closed before release-candidate promotion. |

## Required Check Names

When GitHub rulesets or branch protection are configured, require these exact job-context names:

- `workspace-baseline`
- `udp-rollout-readiness-linux`
- `linux-readiness`
- `linux-staged-readiness`
- `macos-readiness`
- `macos-staged-readiness`
- `windows-readiness`
- `release-evidence-chain`

`main` should require the bounded workflow.
`release/**` and `rc/**` should require both the bounded workflow and the full release-evidence workflow.

## Artifact Contract

The sustained workflows keep the release-facing artifact shape stable and machine-readable:

- bounded evidence keeps host-labeled smoke, perf, interop, rollout-validation, rollout-comparison, and interop-catalog summaries
- scheduled evidence keeps host-labeled staged-rollout plus active-fuzz summaries and packet-capture-backed net-chaos summaries
- release evidence keeps Linux, macOS, and Windows host-labeled readiness inputs plus the final release-facing chain ending at `udp-release-candidate-certification-summary.json`

All release-facing consumers remain fail closed when required inputs are missing, drifted, degraded, or schema-invalid.

## Baseline Comparison Rules

Release review compares the current release-evidence artifact set against the most recent prior release-candidate artifact bundle and the latest successful nightly staged-run bundle.

Promotion should stop when any of the following regresses:

- the final verdict in `udp-release-candidate-certification-summary.json` is not `ready`
- new blocking-reason families appear in any release-facing summary
- `interop_failed_profile_count` increases or a passed interop contract still carries failed profiles
- `udp_blocked_fallback_surface_passed`, `policy_disabled_fallback_round_trip_stable`, or `transport_fallback_integrity_surface_passed` stop being true in carried release evidence
- perf summaries show a materially worse limiting path or queue-guard hold posture without an approved explanation recorded in release notes

## Local Operator Recipes

- bounded Linux recipe: `bash scripts/udp-rollout-readiness.sh`
- scheduled Linux recipe: `NORTHSTAR_ENABLE_UDP_ACTIVE_FUZZ=1 NORTHSTAR_UDP_ROLLOUT_COMPARE_PROFILE=staged_rollout bash scripts/udp-rollout-readiness.sh`
- release evidence chain once host artifacts exist: `bash scripts/udp-release-evidence-chain.sh`

The PowerShell mirrors remain supported for Windows-first local operator review.
