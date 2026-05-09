# Secrets And Config Matrix

Status: draft
Owner: platform
Last updated: 2026-05-06
Scope: CI and runtime Sentry-related configuration
Depends on: `05-environment-and-release-contract.md`
Related paths: `.github/workflows/`, `infra/`, `.env.example` files across surfaces

## Shared variables

| Variable | Purpose | Scope | Storage target |
| --- | --- | --- | --- |
| `SENTRY_URL` | self-hosted Sentry base URL for CLI/build integrations | CI and release automation | GitHub Actions variable |
| `SENTRY_AUTH_TOKEN` | CI artifact upload and release automation | CI only | GitHub Actions secret |
| `SENTRY_ORG` | release automation | CI only | GitHub Actions secret or repo variable |
| `SENTRY_PROJECT` | per-job project selection | CI only | workflow env or matrix value |
| `SENTRY_RELEASE` | canonical release string | CI and runtime | CI output and runtime env |
| `NEXT_PUBLIC_SENTRY_RELEASE` | browser release string for Next.js apps | web browser build/runtime | build env |
| `NEXT_PUBLIC_SENTRY_DSN` | public browser DSN | web browser build/runtime | build env |
| `APP_ENV` | server/edge environment | web server runtime | runtime env |
| `NEXT_PUBLIC_APP_ENV` | browser environment | web browser build/runtime | build env |
| `ENVIRONMENT` | server-side canonical environment | backend and service runtimes | runtime env |
| `FRONTEND_OBSERVABILITY_INTERNAL_SECRET` | protects the frontend runtime smoke contract endpoint | CI and internal smoke callers | runtime secret |
| `TELEGRAM_BOT_OBSERVABILITY_INTERNAL_SECRET` | protects the telegram bot Sentry contract endpoint | CI and internal smoke callers | runtime secret |
| `HELIX_ADAPTER_OBSERVABILITY_INTERNAL_SECRET` | protects the helix-adapter runtime smoke contract endpoint | CI and internal smoke callers | runtime secret |
| `HELIX_NODE_OBSERVABILITY_INTERNAL_SECRET` | protects the helix-node runtime smoke contract endpoint | CI and internal smoke callers | runtime secret |
| `TELEGRAM_BOT_SKIP_NETWORK_CALLS` | smoke-only switch that disables Telegram API startup calls | CI/runtime smoke only | workflow env only |
| `HELIX_ADAPTER_SMOKE_MODE` | smoke-only switch that replaces eager runtime dependencies with lazy startup wiring | CI/runtime smoke only | workflow env only |
| `HELIX_NODE_SMOKE_MODE` | smoke-only switch that starts the daemon without the control-plane loop | CI/runtime smoke only | workflow env only |

## Surface matrix

| Surface | Required runtime vars | Required CI vars | Notes |
| --- | --- | --- | --- |
| `frontend` | `NEXT_PUBLIC_SENTRY_DSN`, `SENTRY_DSN`, `NEXT_PUBLIC_APP_ENV`, `APP_ENV`, `NEXT_PUBLIC_SENTRY_RELEASE`, `SENTRY_RELEASE`, `FRONTEND_OBSERVABILITY_INTERNAL_SECRET` | `SENTRY_AUTH_TOKEN`, `SENTRY_ORG`, `SENTRY_PROJECT=web-frontend` | `frontend` staging and CI smoke paths now use the full contract |
| `admin` | same as `frontend`, including `FRONTEND_OBSERVABILITY_INTERNAL_SECRET` for the protected runtime probe | `SENTRY_AUTH_TOKEN`, `SENTRY_ORG`, `SENTRY_PROJECT=web-admin` | dedicated Sentry runtime smoke now exists in conformance flow; browser instrumentation uses only `NEXT_PUBLIC_*` env |
| `partner` | same as `frontend`, including `FRONTEND_OBSERVABILITY_INTERNAL_SECRET` for the protected runtime probe | same as `frontend` | dedicated Sentry runtime smoke now exists; local Vitest remains separately flaky |
| `backend` | `SENTRY_DSN`, `ENVIRONMENT`, `SENTRY_RELEASE` | optional release automation vars | `.env.example` now documents DSN and release |
| `task-worker` | `SENTRY_DSN`, `ENVIRONMENT`, `SENTRY_RELEASE` | optional release automation vars | `.env.example` now documents DSN and release |
| `telegram-bot` | `SENTRY_DSN`, `ENVIRONMENT`, `SENTRY_RELEASE`, `TELEGRAM_BOT_OBSERVABILITY_INTERNAL_SECRET` | release automation vars plus `TELEGRAM_BOT_SKIP_NETWORK_CALLS` for smoke | runtime config, protected probe and webhook smoke are implemented |
| `node-fleet-controller` | `SENTRY_DSN`, `ENVIRONMENT`, `SENTRY_RELEASE`, `FLEET_CONTROLLER_OBSERVABILITY_INTERNAL_SECRET` | optional release automation vars | runtime probe and CI/local smoke now require the internal secret header |
| `helix-adapter` | `SENTRY_DSN`, `ENVIRONMENT`, `SENTRY_RELEASE`, `SENTRY_TRACES_SAMPLE_RATE`, `HELIX_ADAPTER_OBSERVABILITY_INTERNAL_SECRET` | optional release automation vars plus `HELIX_ADAPTER_SMOKE_MODE` for smoke | runtime probe, smoke-safe startup and CI/live HTTP validation are implemented |
| `helix-node` | `SENTRY_DSN`, `ENVIRONMENT`, `SENTRY_RELEASE`, `SENTRY_TRACES_SAMPLE_RATE`, `HELIX_NODE_OBSERVABILITY_INTERNAL_SECRET` | optional release automation vars plus `HELIX_NODE_SMOKE_MODE` for smoke | runtime probe, smoke-safe startup and CI/live HTTP validation are implemented |
| `cybervpn_mobile` | `SENTRY_DSN`, `SENTRY_RELEASE`, normalized env, release/build vars | `SENTRY_URL`, `SENTRY_AUTH_TOKEN`, org/project slug, artifact upload vars | Dart debug files and release contract are now wired in code and release workflow |
| `desktop-client` | `VITE_SENTRY_DSN`, `VITE_SENTRY_ENVIRONMENT`, `VITE_SENTRY_RELEASE`, `DESKTOP_SENTRY_DSN`, `DESKTOP_SENTRY_ENVIRONMENT`, `DESKTOP_SENTRY_RELEASE`, optional `*_ENABLED` and traces sample-rate vars | `SENTRY_URL`, `SENTRY_AUTH_TOKEN`, `SENTRY_ORG`, `DESKTOP_SENTRY_RENDERER_PROJECT`, `DESKTOP_SENTRY_NATIVE_PROJECT`, GitHub Actions secrets `DESKTOP_SENTRY_RENDERER_DSN` and `DESKTOP_SENTRY_NATIVE_DSN` | renderer/native split contract, CI packaged smoke and release artifact wiring are implemented |
| `android-tv` | `SENTRY_DSN`, `SENTRY_ENVIRONMENT`, `SENTRY_RELEASE` | `SENTRY_URL`, `SENTRY_AUTH_TOKEN`, `SENTRY_ORG`, `ANDROID_TV_SENTRY_PROJECT` or `SENTRY_PROJECT` | Gradle plugin now generates mapping UUIDs and uploads ProGuard mappings when CI credentials are present |

## Secret handling rules

- Runtime DSNs belong in runtime secret stores, not hardcoded CI config.
- CI auth tokens must remain CI-only and never ship into application runtime.
- Public browser DSNs are allowed to be public, but they still must be sourced through configuration, not source code.
- Self-hosted platform credentials remain under platform ownership.
- Internal smoke secrets such as `FRONTEND_OBSERVABILITY_INTERNAL_SECRET` must never be exposed to the browser bundle.
- Internal smoke secrets such as `TELEGRAM_BOT_OBSERVABILITY_INTERNAL_SECRET` must remain runtime-only and must not appear in webhook payloads, logs or Sentry request headers.
- Internal smoke secrets such as `FLEET_CONTROLLER_OBSERVABILITY_INTERNAL_SECRET` must remain runtime-only and stay out of client-visible logs and payloads.
- Internal smoke secrets such as `HELIX_ADAPTER_OBSERVABILITY_INTERNAL_SECRET` must remain runtime-only and must not be echoed into request logs, internal auth headers or Sentry contexts.
- Internal smoke secrets such as `HELIX_NODE_OBSERVABILITY_INTERNAL_SECRET` must remain runtime-only and must not be echoed into daemon logs, HTTP responses or Sentry contexts.
