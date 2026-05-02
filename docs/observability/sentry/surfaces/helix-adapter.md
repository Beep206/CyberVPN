# Helix Adapter

Status: baseline_complete
Owner: platform
Last updated: 2026-04-24
Scope: `services/helix-adapter/`
Depends on: `../05-environment-and-release-contract.md`, `../06-secrets-and-config-matrix.md`, `../11-smoke-tests-and-validation.md`
Related paths: `services/helix-adapter/`, `docs/helix/`

## Current state

- Rust/Axum service now initializes native `sentry` with `send_default_pii=false`, explicit `environment`, explicit `release` and optional traces sampling.
- Per-request hub isolation is provided by `sentry-tower` so breadcrumbs and tracing context do not bleed across concurrent requests.
- Critical manifest and rollout operations are instrumented with `tracing` spans that map to Sentry performance data when traces sampling is enabled.
- Runtime smoke contract is exposed through `GET /observability/sentry-contract` and guarded by `HELIX_ADAPTER_OBSERVABILITY_INTERNAL_SECRET`.
- `HELIX_ADAPTER_SMOKE_MODE=true` starts the service with lazy runtime dependencies so CI can prove the live contract without a real Postgres or Remnawave chain.

## Implemented baseline

- `SENTRY_DSN`, `ENVIRONMENT`, `SENTRY_RELEASE` and `SENTRY_TRACES_SAMPLE_RATE` are wired in runtime config and `.env.example`.
- `AppError` captures only incident-grade server failures (`database`, `upstream`, `serialization`, `internal`) into Sentry; `unauthorized`, `bad_request` and `not_found` remain normal HTTP responses.
- `/healthz` and `/readyz` now include the resolved environment, which is used by smoke validation.
- CI runs `cargo fmt`, `cargo clippy`, full `cargo test`, contract validation and live HTTP smoke against `/healthz` plus `/observability/sentry-contract`.

## Privacy posture

- No request-body capture is enabled.
- No automatic request header capture middleware is installed.
- Protected observability secret is never supposed to appear in logs, Sentry scope data or request telemetry.
- User identity and manifest payloads remain application-controlled and are not pushed into Sentry by default.

## Carryover

- native symbol handling policy for stripped release builds is still future work
- forced-event symbolication proof against a real Sentry project is still future work
- alert routing and issue ownership remain governed by the shared platform policy, not yet by surface-specific rules
