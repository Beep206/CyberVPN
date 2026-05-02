# Android TV

Status: draft
Owner: client-apps
Last updated: 2026-04-24
Scope: `apps/android-tv/`
Depends on: `../05-environment-and-release-contract.md`, `../10-ci-cd-release-artifacts-and-deploy-markers.md`
Related paths: `apps/android-tv/app/build.gradle.kts`, `apps/android-tv/app/src/main/java/com/cybervpn/tv/observability/AndroidTvSentry.kt`, `.github/workflows/android-tv-ci.yml`, `.github/workflows/android-tv-release.yml`

## Current state

- Android TV now initializes Sentry in `CyberVpnApplication` through a dedicated `AndroidTvSentry` runtime wrapper.
- Build-time `SENTRY_DSN`, `SENTRY_ENVIRONMENT` and `SENTRY_RELEASE` are baked into `BuildConfig`.
- The Sentry Android Gradle plugin is enabled for release builds and generates ProGuard mapping metadata.
- `android-tv-ci.yml` validates the runtime contract and runs `detekt`, `ktlintCheck`, `testReleaseUnitTest` and `assembleRelease`.
- `android-tv-release.yml` resolves canonical release metadata, summarizes it, assembles the release and uploads the mapping artifact; mapping upload is enabled automatically when Sentry CI credentials are present.

## Target

- keep crash and error baseline in place
- prove staged symbolication against a real Sentry project
- add release health and consider ANR/performance tracing in a later phase

## Safe context

- `platform=android-tv`
- `app_version`
- `build_number`
- `device_class`
- `session_type`

## Implementation checklist

- done: add SDK init with minimal-PII defaults and event scrubbing
- done: add canonical release naming and Gradle mapping path
- done: add staged validation build and CI contract checks
- next: prove symbolicated staged event against the real self-hosted project
- next: keep rollout in internal or beta until crash pipeline is proven
