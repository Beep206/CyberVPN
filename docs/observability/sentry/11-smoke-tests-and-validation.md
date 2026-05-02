# Smoke Tests And Validation

Status: draft
Owner: platform + QA + runtime owners
Last updated: 2026-04-24
Scope: release validation for all Sentry surfaces
Depends on: `10-ci-cd-release-artifacts-and-deploy-markers.md`
Related paths: `surfaces/`, `runbooks/release-artifact-and-symbolication-failures.md`

## Validation layers

### Build-time validation

- release name resolved correctly
- environment resolved correctly
- artifact upload completed
- CI contract validators append a compact result to `GITHUB_STEP_SUMMARY`

### Deploy-time validation

- runtime starts with DSN configured
- startup smoke event or synthetic transaction reaches the correct project and environment
- deploy marker is attached to the correct release

### Runtime validation

- a forced test error can be observed in the intended project
- symbolication works for packaged or native surfaces
- critical tags such as `runtime_surface`, `release`, `environment` and `request_id` are present

## Wave 1 implemented baseline

- `frontend`: CI validates `APP_ENV` / `SENTRY_RELEASE` / DSN, boots `next start`, verifies `/en-EN`, and probes `/api/observability/sentry-contract` behind `FRONTEND_OBSERVABILITY_INTERNAL_SECRET`
- `admin`: conformance validates route tests, lint/build, and boots `next start` to probe `/api/observability/sentry-contract` behind `FRONTEND_OBSERVABILITY_INTERNAL_SECRET`
- `partner`: conformance now includes the same protected route; local functional smoke proves the runtime contract even though the workspace still has a separate Vitest worker bootstrap defect
- `backend`: CI validates contract vars and runs targeted pytest smoke against `/health` plus resolved Sentry settings
- `task-worker`: CI validates contract vars and runs targeted startup/config smoke that proves `sentry_sdk.init(...)` receives the expected DSN, environment and release
- `telegram-bot`: CI validates `ENVIRONMENT` / `SENTRY_RELEASE` / DSN, runs targeted pytest for SDK init, webhook runtime contract and list-env parsing, then boots webhook mode and proves `/health` plus `/observability/sentry-contract`
- `node-fleet-controller`: CI validates contract vars, runs targeted pytest for SDK init, workflow span coverage and protected probe behavior, then boots `uvicorn` and proves `/api/v1/health/live` plus `/api/v1/observability/sentry-contract`
- `cybervpn_mobile`: CI validates contract vars and runs a dedicated `flutter test` file with `--dart-define` values for `API_ENV`, `SENTRY_DSN` and `SENTRY_RELEASE`
- `apps/desktop-client`: CI validates renderer/native contracts separately, runs renderer and native tests, builds the packaged Tauri app, and proves clean startup with `apps/desktop-client/scripts/run-desktop-sentry-smoke.sh`
- `apps/android-tv`: CI validates `SENTRY_ENVIRONMENT` / `SENTRY_RELEASE` / DSN, runs `detekt`, `ktlintCheck`, `testReleaseUnitTest` and `assembleRelease`, and proves the Sentry Gradle plugin reaches mapping generation for the minified release path
- `services/helix-adapter`: CI validates `ENVIRONMENT` / `SENTRY_RELEASE` / DSN, runs `cargo test` and `cargo clippy`, then boots the Rust service in `HELIX_ADAPTER_SMOKE_MODE=true` and proves `/healthz` plus `/observability/sentry-contract`
- `services/helix-node`: CI validates `ENVIRONMENT` / `SENTRY_RELEASE` / DSN, runs `cargo test` and `cargo clippy`, then boots the daemon in `HELIX_NODE_SMOKE_MODE=true` and proves `/healthz` plus `/observability/sentry-contract`

## Reusable validation tooling

- `scripts/validate-sentry-contract.py`: validates environment/release/DSN presence and writes a job summary
- `scripts/http-smoke-check.py`: polls HTTP endpoints until status/body/JSON expectations match

## Minimum smoke path by surface

- web: synthetic client error plus one server/route-handler event
- backend: startup smoke event plus one synthetic request
- worker: startup heartbeat plus one canary task
- bot: health/startup check plus one canary update path
- mobile: QA internal build with release and artifact linkage validation
- desktop and TV: staged validation build with symbolication or artifact-path proof
