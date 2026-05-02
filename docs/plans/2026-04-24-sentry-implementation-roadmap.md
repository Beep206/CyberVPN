# Sentry Implementation Roadmap

Status: draft
Owner: platform
Last updated: 2026-04-25
Scope: phased execution plan for monorepo-wide Sentry rollout
Depends on: `../observability/sentry/README.md`
Related paths: `2026-04-24-sentry-rollout-tracker.md`, `../observability/sentry/surfaces/`

## Phase 0: documentation and governance baseline

- Create the Sentry documentation package.
- Freeze project registry, environment contract, privacy policy and rollout waves.
- Confirm self-hosted platform ownership and bootstrap boundary.
- Confirm team ownership and alert channels.

## Wave 1: core user and service coverage

Surfaces:

- `frontend`
- `admin`
- `partner`
- `backend`
- `services/task-worker`
- `cybervpn_mobile`

Primary outcomes:

- fix environment contract where current config is ambiguous
- align release naming and runtime DSN handling
- close `.env.example` and CI/CD config gaps
- verify source maps and mobile debug-file coverage

Implemented steps:

- `Step 1/5`: align web env/release contract in `frontend`, `admin`, `partner`
- `Step 2/5`: align backend and worker release contract
- `Step 3/5`: standardize web/mobile CI release metadata and artifact handling
- `Step 4/5`: add reusable Sentry smoke validation and targeted CI/runtime proof
- `Step 5/5`: close wave docs, status vocabulary, DoD and carryover handling

Wave 1 exit snapshot:

- `baseline_complete`: `frontend`, `admin`, `partner`, `backend`, `services/task-worker`, `cybervpn_mobile`
- carryover into the next wave: alert routing, final privacy approval, and deploy-marker/release-finalization closure

## Wave 2: bot, desktop, TV and controller

Surfaces:

- `services/telegram-bot`
- `apps/desktop-client`
- `apps/android-tv`
- `services/node-fleet-controller`

Primary outcomes:

- add missing SDK coverage
- define artifact upload for desktop and Android TV
- introduce bot and controller-specific tags and smoke paths

Implemented steps:

- `Step 1/4`: close dedicated `admin`/`partner` smoke carryover and add initial `services/telegram-bot` Sentry foundation with CI validation
- `Step 2/4`: add `services/node-fleet-controller` baseline with FastAPI SDK init, protected runtime probe, workflow/reconcile spans and HTTP smoke validation
- `Step 3/4`: carry `services/telegram-bot` from `contract_aligned` to `baseline_complete` with live webhook smoke, protected runtime contract and smoke-safe startup mode
- `Step 4/4`: add `apps/android-tv` baseline with Sentry Android SDK + Gradle plugin, canonical packaged-app release contract, CI validation, release assemble proof and mapping upload path

Wave 2 exit snapshot:

- `baseline_complete`: `services/telegram-bot`, `services/node-fleet-controller`, `apps/android-tv`
- explicit carryover into the next wave: `apps/desktop-client` renderer/native split, sourcemaps and native symbols

## Wave 3: desktop and native completion

Surfaces:

- `apps/desktop-client`
- `services/helix-adapter`
- `services/helix-node`

Primary outcomes:

- add Rust-native error coverage
- define symbol policy
- add control-plane correlation and native rollout rules

Implemented steps:

- `Step 1/4`: move `apps/desktop-client` from `pending` to `contract_aligned` by splitting renderer/native Sentry foundation, wiring shared desktop release naming, adding desktop-specific DSN vars and validating the contract locally for both layers
- `Step 2/4`: move `apps/desktop-client` from `contract_aligned` to `baseline_complete` by wiring renderer sourcemaps and native debug-file upload into CI/release workflows and adding packaged desktop smoke validation
- `Step 3/4`: move `services/helix-adapter` from `pending` to `baseline_complete` by adding Rust-native `sentry` init, per-request hub binding, protected runtime probe, smoke-safe startup, targeted tracing spans, CI contract validation and live HTTP smoke proof
- `Step 4/4`: move `services/helix-node` from `pending` to `baseline_complete` by adding Rust-native `sentry` init, protected runtime probe, smoke-safe daemon startup, lifecycle spans, CI contract validation and live HTTP smoke proof

## Cross-wave rule

Do not start the next wave until:

- rollout tracker for the current wave is updated
- smoke validation is proven for every surface marked `baseline_complete`
- privacy, alerting or volume items that are still open are explicitly carried forward in the decision log and tracker

## Wave 4: governance and production acceptance

Surfaces:

- all direct Sentry projects

Primary outcomes:

- freeze repo-local ownership and alert-tier policy
- validate governance metadata in CI
- close privacy and org-level scrub approval
- prepare real-project symbolication and production acceptance closure

Implemented steps:

- `Step 1/4`: add `governance-registry.json`, validate it in CI and freeze logical ownership plus baseline alert tiers before live Sentry setup
- `Step 2/4`: add `privacy-baseline.json`, validate privacy expectations in CI and align web/backend/worker runtimes with explicit minimal-PII defaults, replay masking and request scrubbing hooks
- `Step 3/4`: add `release-proof-registry.json`, validate release-proof expectations in CI, emit evidence manifests for mobile/desktop/Android TV/native Rust surfaces, and record deploy markers only for repo-owned release workflows
- `Step 4/4`: add `production-acceptance-registry.json`, validate final live blockers in CI, split rollout baseline from real production acceptance, and close the repo-owned Sentry implementation roadmap without false `accepted` claims

Next planned steps:

- none inside the repo-owned implementation roadmap; remaining work is live self-hosted Sentry acceptance and external deployer follow-through

## Roadmap closure

`Wave 4` closes the repo-owned implementation roadmap. Remaining work now lives in the production acceptance registry and operational follow-up, not in additional monorepo rollout waves.
