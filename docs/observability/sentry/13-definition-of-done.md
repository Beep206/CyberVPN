# Definition Of Done

Status: draft
Owner: platform + runtime owners
Last updated: 2026-04-25
Scope: completion criteria for the monorepo Sentry rollout
Depends on: all normative docs in this package
Related paths: `../../plans/2026-04-24-sentry-rollout-tracker.md`

## Wave baseline definition of done

- registry, roadmap and rollout tracker are synchronized
- runtime config and `.env.example` gaps are closed for the wave surfaces
- canonical environment and release contract is implemented in code
- CI validates the Sentry contract for the surfaces covered by the wave
- targeted smoke proof exists for the highest-risk surfaces in the wave
- carryover items are explicitly recorded in the tracker and decision log

## Full production definition of done

- project exists in the registry and is owned
- DSN and environment variables are documented and provisioned
- release naming follows the shared contract
- required artifacts upload successfully
- release-evidence manifest exists for surfaces governed by `release-proof-registry.json`
- privacy and scrubbing rules are applied
- core tags and safe user context are present
- smoke validation passes in staging and production path
- alert routing is configured
- deploy marker is recorded by the repo-owned deploy workflow, or explicitly assigned to an external deployer
- residual risks are documented

## Repo-owned program closure

The repo-owned rollout can be considered complete when:

- governance, privacy, release-proof and production-acceptance registries all validate in CI
- every direct Sentry project is `baseline_complete`
- every non-code blocker is explicitly represented in `production-acceptance-registry.json`
- no project is implicitly treated as accepted without live proof

## Per-surface definition of done

A surface is considered implemented only when:

- SDK integration is merged
- runtime initialization is verified
- environment and release are correct in real events
- at least one symbolicated or sourcemap-backed event is proven where applicable
- issue ownership and alert routing are configured
- rollout tracker status is updated

## Wave 1 exit criteria

`Wave 1` is considered complete when:

- `frontend`, `backend`, `services/task-worker` and `cybervpn_mobile` are at least `baseline_complete`
- `admin` and `partner` are at least `baseline_complete`
- Wave 1 carryover items are explicitly handed to the next wave instead of being left implicit

## Wave 3 exit criteria

`Wave 3` is considered complete when:

- `apps/desktop-client` and `services/helix-adapter` are `baseline_complete`
- `services/helix-node` is `baseline_complete`
- symbol handling and release-proof carryover items are either closed or explicitly handed to a later governance/runtime wave

## Exit criterion for the program

The monorepo Sentry rollout is complete only when every direct surface in the registry is either:

- implemented, or
- explicitly marked deferred with an approved reason and follow-up date.

The broader production acceptance program is complete only when every project in `production-acceptance-registry.json` is either:

- `production_accepted`, or
- explicitly deferred with an approved owner and follow-up date.
