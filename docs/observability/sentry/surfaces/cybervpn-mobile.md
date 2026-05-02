# CyberVPN Mobile

Status: draft
Owner: client-apps
Last updated: 2026-04-24
Scope: `cybervpn_mobile/`
Depends on: `../05-environment-and-release-contract.md`, `../10-ci-cd-release-artifacts-and-deploy-markers.md`
Related paths: `cybervpn_mobile/lib/main.dart`, `cybervpn_mobile/lib/core/analytics/sentry_user_sync_provider.dart`, `.github/workflows/ci.yml`, `.github/workflows/mobile-release.yml`

## Current state

- `sentry_flutter` is already integrated.
- Privacy defaults are stronger here than anywhere else in the repo.
- Runtime now supports explicit `SENTRY_RELEASE`.
- CI and release workflows now resolve canonical `cybervpn-mobile@<version>+<build>` release names.
- CI and release workflows now upload Dart debug files and publish release metadata in job summaries.

## Target

- keep one mobile project initially
- normalize `dev/staging/prod` into canonical Sentry environments
- standardize release as `cybervpn-mobile@<version>+<build>`
- align symbol upload behavior between CI and release workflows

## Mobile-specific considerations

- only safe internal `user.id` should be sent
- staging/internal builds should not pollute production
- QA needs an explicit release-linkage smoke scenario

## Smoke validation baseline

- CI validates `API_ENV`, `SENTRY_DSN` and `SENTRY_RELEASE` with the shared validator
- dedicated `flutter test` smoke runs with explicit `--dart-define` values and proves `EnvironmentConfig` resolves the same contract that release jobs inject

## Implementation checklist

- freeze release and environment normalization
- validate symbolication on Android and iOS paths
- add rollout tags for internal and beta builds if needed
