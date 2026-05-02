# Sentry Documentation Index

Status: draft
Owner: platform (proposed)
Last updated: 2026-04-25
Scope: all Sentry-governed runtime surfaces in the monorepo
Depends on: `00-current-state-and-discovery.md`, `01-target-architecture-and-scope.md`
Related paths: `docs/observability/sentry/`, `docs/plans/2026-04-24-sentry-implementation-roadmap.md`, `docs/plans/2026-04-24-sentry-rollout-tracker.md`

## Purpose

This directory is the canonical documentation package for Sentry rollout across the CyberVPN monorepo. It separates four layers:

1. Normative rules: target architecture, release contract, privacy policy, ownership and definition of done.
2. Surface specs: per-runtime implementation guidance.
3. Execution docs: phased roadmap and live rollout tracker.
4. Runbooks: operational response for incidents, symbolication failures, privacy exposure and self-hosted Sentry operations.

## Document map

### Normative documents

- [00-current-state-and-discovery.md](./00-current-state-and-discovery.md): confirmed current state, gaps and evidence from code.
- [01-target-architecture-and-scope.md](./01-target-architecture-and-scope.md): target coverage, boundaries and project-model principles.
- [02-open-questions-and-decision-log.md](./02-open-questions-and-decision-log.md): unknowns, decisions and follow-up actions.
- [03-self-hosted-sentry-platform-bootstrap.md](./03-self-hosted-sentry-platform-bootstrap.md): self-hosted platform baseline and bootstrap checklist.
- [04-sentry-project-registry.md](./04-sentry-project-registry.md): proposed registry of Sentry projects and rollout status.
- [05-environment-and-release-contract.md](./05-environment-and-release-contract.md): canonical environment and release naming rules.
- [06-secrets-and-config-matrix.md](./06-secrets-and-config-matrix.md): config and secret inventory for CI and runtime.
- [07-privacy-pii-scrubbing-and-replay-policy.md](./07-privacy-pii-scrubbing-and-replay-policy.md): privacy and scrubbing policy.
- [08-tags-context-correlation-and-fingerprinting-contract.md](./08-tags-context-correlation-and-fingerprinting-contract.md): tag dictionary and correlation rules.
- [09-sampling-tracing-replay-and-volume-policy.md](./09-sampling-tracing-replay-and-volume-policy.md): initial sampling and noise-control policy.
- [10-ci-cd-release-artifacts-and-deploy-markers.md](./10-ci-cd-release-artifacts-and-deploy-markers.md): CI/CD standard for releases, artifacts and deploy markers.
- [11-smoke-tests-and-validation.md](./11-smoke-tests-and-validation.md): validation steps for rollout and post-deploy checks.
- [12-alerting-ownership-routing-and-severity-policy.md](./12-alerting-ownership-routing-and-severity-policy.md): routing, ownership and alerting rules.
- [13-definition-of-done.md](./13-definition-of-done.md): global and per-surface completion criteria.
- [governance-registry.json](./governance-registry.json): machine-readable ownership, routing and alert-tier baseline.
- [privacy-baseline.json](./privacy-baseline.json): machine-readable privacy baseline, scrub markers and runtime code expectations.
- [release-proof-registry.json](./release-proof-registry.json): machine-readable release-proof and deploy-marker baseline.
- [production-acceptance-registry.json](./production-acceptance-registry.json): machine-readable final acceptance gates and honest live blockers.

### Surface specs

- [surfaces/frontend-web.md](./surfaces/frontend-web.md)
- [surfaces/admin-web.md](./surfaces/admin-web.md)
- [surfaces/partner-web.md](./surfaces/partner-web.md)
- [surfaces/backend-api.md](./surfaces/backend-api.md)
- [surfaces/task-worker.md](./surfaces/task-worker.md)
- [surfaces/telegram-bot.md](./surfaces/telegram-bot.md)
- [surfaces/node-fleet-controller.md](./surfaces/node-fleet-controller.md)
- [surfaces/helix-adapter.md](./surfaces/helix-adapter.md)
- [surfaces/helix-node.md](./surfaces/helix-node.md)
- [surfaces/cybervpn-mobile.md](./surfaces/cybervpn-mobile.md)
- [surfaces/desktop-client.md](./surfaces/desktop-client.md)
- [surfaces/android-tv.md](./surfaces/android-tv.md)

### Runbooks

- [runbooks/issue-triage-and-incident-playbook.md](./runbooks/issue-triage-and-incident-playbook.md)
- [runbooks/release-artifact-and-symbolication-failures.md](./runbooks/release-artifact-and-symbolication-failures.md)
- [runbooks/privacy-and-data-exposure-response.md](./runbooks/privacy-and-data-exposure-response.md)
- [runbooks/self-hosted-sentry-operations.md](./runbooks/self-hosted-sentry-operations.md)

### Execution docs

- [../../plans/2026-04-24-sentry-implementation-roadmap.md](../../plans/2026-04-24-sentry-implementation-roadmap.md)
- [../../plans/2026-04-24-sentry-rollout-tracker.md](../../plans/2026-04-24-sentry-rollout-tracker.md)

## Source inputs

This package was bootstrapped from two earlier discovery artifacts:

- [../../plans/2026-04-23-monorepo-sentry-integration-scope.md](../../plans/2026-04-23-monorepo-sentry-integration-scope.md)
- [../../plans/2026-04-23-sentry-discovery-answers.md](../../plans/2026-04-23-sentry-discovery-answers.md)

These source documents remain useful as evidence packs, but this directory becomes the working source of truth.

## Current execution state

`Wave 1`, `Wave 2` and `Wave 3` are closed as runtime rollout waves. `Wave 4` is now the governance follow-up track.

- `frontend`, `backend`, `services/task-worker` and `cybervpn_mobile` have implemented environment/release contract, CI validation and targeted smoke proof.
- `admin` and `partner` are baseline-complete after dedicated protected runtime smoke closure in `Wave 2`.
- `services/telegram-bot`, `services/node-fleet-controller` and `apps/android-tv` reached `baseline_complete` in `Wave 2`.
- `Wave 3` closed `apps/desktop-client`, `services/helix-adapter` and `services/helix-node` at `baseline_complete`, including packaged/native smoke proof and Rust-native runtime coverage.
- `Wave 4 / Step 1` added a machine-readable governance registry plus CI validation so ownership, routing basis and default alert tiers are now frozen in-repo before applying them in the live self-hosted Sentry organization.
- `Wave 4 / Step 2` froze a machine-readable privacy baseline in `privacy-baseline.json`, added CI validation and aligned `frontend`, `admin`, `partner`, `backend` and `services/task-worker` with explicit minimal-PII defaults and replay/request scrubbing hooks.
- `Wave 4 / Step 3` froze a machine-readable release-proof baseline in `release-proof-registry.json`, added CI validation, wired evidence manifests into `mobile`, `desktop`, `android-tv` and `helix-*` workflows, and added a reusable release/deploy-marker recorder for surfaces whose deploy event is represented inside this repository.
- `Wave 4 / Step 4` closes the repo-owned rollout roadmap with `production-acceptance-registry.json`, a dedicated acceptance validator and an explicit tracker split between `baseline_complete` runtime work and unresolved live/external acceptance gates.
- Live self-hosted application of scrub rules, alert connector setup, symbolication proof and external deployer confirmation remain operational acceptance gates, not missing runtime integration work.

## Status vocabulary

- `baseline_complete`: wave-level foundation is implemented and verified, but full production acceptance can still depend on governance, privacy or alerting closure.
- `contract_aligned`: runtime contract is implemented and tested, but dedicated smoke or operational closure is still pending.
- `pending`: implementation has not started.
